"""One cancellable solver process; no Panda imports and no shared tracemalloc state."""
import importlib
import multiprocessing


def _run(connection, board, module, class_name):
    try:
        solver = getattr(importlib.import_module(module), class_name)(board)
        connection.send((True, solver.solve()))
    except BaseException as error:
        try:
            connection.send((False, f'{type(error).__name__}: {error}'))
        except (BrokenPipeError, EOFError, OSError):
            pass  # The UI may have cancelled this job and closed its end.
    finally:
        connection.close()


class SolverJob:
    def __init__(self, board, module, class_name):
        context = multiprocessing.get_context('spawn')
        self.connection, child = context.Pipe(duplex=False)
        self.process = context.Process(target=_run, args=(child, board, module, class_name), daemon=True)
        self._closed = False
        try:
            self.process.start()
        except BaseException:
            self.connection.close()
            child.close()
            raise
        child.close()

    def poll(self):
        if self._closed:
            return None
        if self.connection.poll():
            try:
                value = self.connection.recv()
            except EOFError:
                value = (False, 'Solver process exited without a result.')
            self.close()
            return value
        if not self.process.is_alive():
            self.close()
            return False, 'Solver process exited without a result.'
        return None

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.connection.close()
        self.process.join(timeout=.02)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=.2)
        if not self.process.is_alive():
            self.process.close()

    cancel = close
