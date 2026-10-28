"""Animated menu background: the real scene replays a BFS solution in a loop."""


class AttractMode:
    RESTART_DELAY = 1.5

    def __init__(self, controller, task_mgr, level_index=0):
        self.controller, self._task_mgr = controller, task_mgr
        self.level_index = level_index
        self.active = False
        self._task = None
        self._wait = 0.0

    def start(self):
        if self.active:
            return
        self.active, self._wait = True, 0.0
        controller = self.controller
        if controller.level_index != self.level_index:
            controller.load_level(self.level_index)
        else:
            controller.restart_level()
        self._task = self._task_mgr.add(self._update, 'AttractMode')

    def stop(self):
        self.active = False
        if self._task is not None:
            self._task_mgr.remove(self._task)
            self._task = None

    def _update(self, task):
        from panda3d.core import ClockObject
        controller = self.controller
        result = controller.search
        gave_up = result is not None and not result.success   # unsolvable by BFS: stay idle
        if self.active and controller.is_idle and not gave_up:
            self._wait += ClockObject.getGlobalClock().getDt()
            if self._wait >= self.RESTART_DELAY:
                self._wait = 0.0
                # Only the menu demo loops. Gameplay Solve never rewinds.
                if controller.phase == 'GOAL':
                    controller.restart_level()
                controller.run_solver('BFS')
        else:
            self._wait = 0.0
        return task.cont