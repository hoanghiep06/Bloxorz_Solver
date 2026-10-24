"""Reproducible Stage 3.6 desktop validation (stdlib + existing Panda3D only).

Run from the repository root with .venv/bin/python -B -m tools.gui_stage3_6_smoke.
Importing this module creates no host/window. Fixtures are rendering test data,
not new production levels or claims of solvable gameplay.
"""

import argparse
from dataclasses import replace
import gc
import json
import math
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc

from src.gui.contracts import BasicOrientation, BasicTileKind, GameSnapshot, StaticBoardData


SIZES = ((1280, 720), (1366, 768), (1920, 1080), (1024, 768), (1024, 720))
SHAPES = {'wide': (3, 15), 'tall': (15, 3), 'square': (10, 10),
          'basic': (4, 7), 'sparse': (6, 9), 'tiny': (1, 1), 'edge-goal': (3, 5)}


def make_fixture(name):
    rows, cols = SHAPES[name]
    sparse_cells = {(1, 1), (1, 2), (2, 1), (2, 2), (4, 7), (4, 8)}
    tiles = tuple(tuple(BasicTileKind.FLOOR if name != 'sparse' or (r, c) in sparse_cells
                        else BasicTileKind.VOID for c in range(cols)) for r in range(rows))
    goal = (4, 8) if name == 'sparse' else (0, cols - 1) if name == 'edge-goal' else (rows - 1, cols - 1)
    return StaticBoardData(1, 'qa-' + name, 'qa-' + name + '-v1', rows, cols, tiles, (goal,))


def make_snapshot(data, pose=BasicOrientation.STANDING, *, revision=0, session='stage3-6'):
    anchor = (min(1, data.rows - 1), min(1, data.cols - 1))
    row, col = anchor
    occupied = {BasicOrientation.STANDING: (anchor,),
                BasicOrientation.HORIZONTAL: (anchor, (row, col + 1)),
                BasicOrientation.VERTICAL: (anchor, (row + 1, col))}[pose]
    return GameSnapshot(1, session, revision, data.board_revision, 'WHOLE', pose, anchor, occupied)


def _step(app, frames=12):
    for _ in range(frames):
        app.taskMgr.step()
    app.graphicsEngine.syncFrame()


def _present(app):
    """Wait for the asynchronous native map/focus event before framebuffer QA."""
    from panda3d.core import WindowProperties
    properties = WindowProperties()
    properties.setMinimized(False)
    properties.setForeground(True)
    app.win.requestProperties(properties)
    deadline = time.perf_counter() + 5
    while time.perf_counter() < deadline:
        _step(app, 1)
        current = app.win.getProperties()
        if current.getOpen() and current.getForeground() and not current.getMinimized() and app.win.isActive():
            _step(app, 3)
            return
        time.sleep(.01)
    raise RuntimeError('Native window was not mapped/foreground; desktop capture would be invalid.')


def _resize(app, size):
    from panda3d.core import WindowProperties
    properties = WindowProperties()
    properties.setSize(*size)
    app.win.requestProperties(properties)
    deadline = time.perf_counter() + 5
    while time.perf_counter() < deadline:
        _step(app, 1)
        if (app.win.getXSize(), app.win.getYSize()) == size:
            _step(app, 3)
            return
        # In fallback there is no 3D draw to pace frames; allow the native WM
        # to process its asynchronous configure event instead of busy-spinning.
        time.sleep(.005)
    raise AssertionError(f'Window manager did not provide client size {size}.')


def _iconify_x11(window):
    """Optional native minimize for X11 WMs ignoring Panda's property request.

    Uses the existing system X11 library and only our observed window handle;
    no dependency is installed and no foreign window is modified.
    """
    import ctypes
    from ctypes.util import find_library
    library = find_library('X11')
    if not library:
        return False
    x11 = ctypes.CDLL(library)
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XDefaultScreen.argtypes = [ctypes.c_void_p]
    x11.XDefaultScreen.restype = ctypes.c_int
    x11.XIconifyWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int]
    x11.XIconifyWindow.restype = ctypes.c_int
    x11.XFlush.argtypes = x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    display = x11.XOpenDisplay(None)
    if not display:
        return False
    try:
        result = x11.XIconifyWindow(display, window.getWindowHandle().getIntHandle(),
                                   x11.XDefaultScreen(display))
        x11.XFlush(display)
        return bool(result)
    finally:
        x11.XCloseDisplay(display)


def resources(app):
    from direct.showbase.MessengerGlobal import messenger
    from panda3d.core import GraphicsWindow
    windows = list(app.graphicsEngine.getWindows())
    return {'scene_paths': app.scene_root.findAllMatches('**').getNumPaths(),
            'static_paths': app.static_board_root.findAllMatches('**').getNumPaths(),
            'block_paths': app.block_root.findAllMatches('**').getNumPaths(),
            'hud_widgets': len(app.dashboard.hud._widgets),
            'hud_paths': app.dashboard.hud.root.findAllMatches('**').getNumPaths(),
            'main_regions': sum(r.getCamera() == app.cam for r in app.win.getDisplayRegions()),
            'window_regions': len(app.win.getDisplayRegions()),
            'native_windows': sum(isinstance(w, GraphicsWindow) for w in windows),
            'graphics_outputs': len(windows),
            'shadow_buffers': int(app.presentation.lighting.key.node().getShadowBuffer(app.win.getGsg()) is not None),
            'light_nodes': app.scene_root.findAllMatches('**/+Light').getNumPaths(),
            'window_subscriptions': len(messenger.whoAccepts('window-event') or {}),
            'aspect_subscriptions': len(messenger.whoAccepts('aspectRatioChanged') or {}),
            'total_subscriptions': sum(len(messenger.whoAccepts(event) or {}) for event in messenger.getEvents())}


def _vertices(root, relative):
    from panda3d.core import GeomVertexReader, Point3
    points = []
    for path in root.findAllMatches('**/+GeomNode'):
        for geom in path.node().getGeoms():
            reader = GeomVertexReader(geom.getVertexData(), 'vertex')
            while not reader.isAtEnd():
                points.append(tuple(relative.getRelativePoint(path, Point3(reader.getData3f()))))
    return points


def occupancy(app):
    """Project actual geometry, separately from the conservative camera envelope."""
    from src.gui.camera import project_point
    fit = app.presentation.camera.current_fit
    viewport = app.dashboard.viewport.layout.viewport
    result = {}
    for name, points in (('board', _vertices(app.static_board_root, app.render)),
                         ('board_and_block', _vertices(app.static_board_root, app.render)
                          + _vertices(app.block_root, app.render))):
        projected = [project_point(point, fit) for point in points]
        assert all(max(abs(x), abs(y)) < 1 and fit.near < depth < fit.far
                   for x, y, depth in projected), 'Geometry is outside the visible frustum.'
        xs = [(x + 1) * viewport.width / 2 for x, _, _ in projected]
        ys = [(1 - y) * viewport.height / 2 for _, y, _ in projected]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        result[name] = {'rect_in_viewport': [x0, y0, x1 - x0, y1 - y0],
                        'width_fraction': (x1 - x0) / viewport.width,
                        'height_fraction': (y1 - y0) / viewport.height,
                        'margins_lrtb': [x0, viewport.width - x1, y0, viewport.height - y1]}
    return result


def _validate_frame(app):
    from src.gui.camera import project_point
    from src.gui.hud import UNKNOWN
    layout = app.dashboard.viewport.layout
    region = app.dashboard.viewport.region
    assert sum(r.getCamera() == app.cam for r in app.win.getDisplayRegions()) == 1
    if layout.supported:
        rect = layout.viewport
        assert (region.getPixelWidth(), region.getPixelHeight()) == (rect.width, rect.height)
        assert abs(app.camLens.getAspectRatio() - rect.width / rect.height) < 1e-5
        assert abs(app.camLens.getVfov() - 45) < 1e-4
        fit = app.presentation.camera.current_fit
        for corner in fit.bounds.corners():
            x, y, depth = project_point(corner, fit)
            assert max(abs(x), abs(y)) <= .74001
            assert fit.near < depth < fit.far
    else:
        assert not region.isActive() and not app.dashboard.hud.warning.isHidden()
    hud = app.dashboard.hud
    for widget in (*hud.buttons.values(), hud.speed, hud.speed.component('thumb')):
        assert not widget.guiItem.getActive() and widget['command'] is None
    assert [label['text'] for label in hud.metric_values] == [UNKNOWN] * 5


def _capture(app, output, name, *, shape, pose, shadows, aa):
    _step(app)
    _validate_frame(app)
    path = output / (name + '.png')
    assert app.win.saveScreenshot(str(path))
    return {'path': str(path), 'client': [app.win.getXSize(), app.win.getYSize()],
            'shape': shape, 'pose': pose, 'shadow_status': app.presentation.lighting.shadow_status,
            'shadows_requested': shadows, 'aa_requested': aa,
            'actual_samples': app.win.getFbProperties().getMultisamples(),
            'occupancy': occupancy(app) if app.dashboard.viewport.layout.supported else None,
            'technical_checks': 'PASS', 'visual_review': 'PENDING'}


def visual(app, renderer, output):
    from panda3d.core import WindowProperties
    data, initial = renderer._board_data, renderer._snapshot
    images = []
    for size in SIZES:
        _resize(app, size)
        images.append(_capture(app, output, f'real-standing-{size[0]}x{size[1]}',
                               shape='real-4x7', pose='STANDING', shadows=False, aa=True))
    _resize(app, (640, 480))
    images.append(_capture(app, output, 'small-fallback-640x480',
                           shape='real-4x7', pose='STANDING', shadows=False, aa=True))
    _resize(app, (1280, 720))
    for revision, pose in enumerate((BasicOrientation.HORIZONTAL, BasicOrientation.VERTICAL), 1):
        renderer.show_snapshot(make_snapshot(data, pose, revision=revision))
        images.append(_capture(app, output, 'real-' + pose.value.lower(),
                               shape='real-4x7', pose=pose.value, shadows=False, aa=True))
    for name, shape in SHAPES.items():
        fixture = make_fixture(name)
        renderer.load_board(fixture)
        renderer.show_snapshot(make_snapshot(fixture))
        rect = app.dashboard.viewport.layout.viewport
        app.presentation.camera.fit_board(fixture, rect.width, rect.height)
        images.append(_capture(app, output, 'fixture-' + name,
                               shape=f'{name}-{shape[0]}x{shape[1]}', pose='STANDING', shadows=False, aa=True))
    renderer.load_board(data)
    renderer.show_snapshot(initial)
    rect = app.dashboard.viewport.layout.viewport
    app.presentation.camera.fit_board(data, rect.width, rect.height)
    # Exercise real minimized/restore properties without changing engine handlers.
    properties = WindowProperties(); properties.setMinimized(True)
    app.win.requestProperties(properties)
    deadline = time.perf_counter() + 3
    while time.perf_counter() < deadline and not app.win.getProperties().getMinimized():
        _step(app, 1); time.sleep(.01)
    minimize_method = 'Panda WindowProperties'
    if not app.win.getProperties().getMinimized() and sys.platform.startswith('linux'):
        if _iconify_x11(app.win):
            minimize_method = 'XIconifyWindow (Panda request not acknowledged by this WM)'
            deadline = time.perf_counter() + 3
            while time.perf_counter() < deadline and not app.win.getProperties().getMinimized():
                _step(app, 1); time.sleep(.01)
    minimized = app.win.getProperties().getMinimized()
    properties = WindowProperties(); properties.setMinimized(False); properties.setForeground(True)
    app.win.requestProperties(properties)
    if minimized and minimize_method.startswith('XIconifyWindow'):
        subprocess.run(['wmctrl', '-ia', hex(app.win.getWindowHandle().getIntHandle())], check=True)
    deadline = time.perf_counter() + 3
    while time.perf_counter() < deadline and app.win.getProperties().getMinimized():
        _step(app, 1); time.sleep(.01)
    _step(app, 5)
    _validate_frame(app)
    return {'images': images, 'native_minimize_readback': minimized,
            'native_minimize_method': minimize_method,
            'native_restore_readback': not app.win.getProperties().getMinimized()}


def stress(app, renderer, output, cycles, recreates):
    from direct.gui.DirectGuiBase import DirectGuiWidget
    from src.gui.dashboard_preview import DashboardPresentation
    from src.gui.hud import HudShell, HudViewModel
    data = renderer._board_data
    block = app.block_root.find('MainBlockVisual').node()
    content = app.static_board_root.find('BasicBoardContent').node()
    prototypes = (renderer._floor_mesh, renderer._goal_mesh, renderer._block_mesh)
    camera_transform = app.camera.getTransform()
    _step(app, 30)
    tracemalloc.start()
    gc.collect()
    start_current, _ = tracemalloc.get_traced_memory()
    baseline = resources(app)
    batches = []
    for batch in range(3):
        for i in range(500):
            pose = tuple(BasicOrientation)[i % 3]
            renderer.show_snapshot(make_snapshot(data, pose, revision=batch * 500 + i + 1))
        assert app.block_root.find('MainBlockVisual').node() == block
        assert app.static_board_root.find('BasicBoardContent').node() == content
        assert prototypes == (renderer._floor_mesh, renderer._goal_mesh, renderer._block_mesh)
        assert app.camera.getTransform() == camera_transform
        _step(app, 3); gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        counts = resources(app)
        assert counts == baseline, (baseline, counts)
        batches.append({'snapshots_total': (batch + 1) * 500, 'python_current_bytes': current,
                        'python_peak_bytes': peak, 'resources': counts})
    for i in range(70):
        fixture = make_fixture(tuple(SHAPES)[i % len(SHAPES)])
        fixture = replace(fixture, board_revision=f'{fixture.board_revision}-{i}')
        renderer.load_board(fixture); renderer.load_board(fixture)
        renderer.show_snapshot(make_snapshot(fixture))
        assert app.static_board_root.getNumChildren() == 1
        assert app.block_root.getNumChildren() == 1
    renderer.load_board(data); renderer.show_snapshot(make_snapshot(data))
    resize_baseline = resources(app)
    for _ in range(cycles):
        for size in (*SIZES, (640, 480), (1280, 720)):
            _resize(app, size); _validate_frame(app)
            assert resources(app) == resize_baseline
    lifecycle_batches = []
    for batch in range(recreates // 20):
        for _ in range(20):
            app.dashboard.dispose(); app.dashboard.dispose()
            assert tuple(app.cam.node().getDisplayRegion(0).getDimensions()) == (0, 1, 0, 1)
            app.dashboard = DashboardPresentation(app, HudViewModel())
            _step(app, 2)
            assert resources(app) == resize_baseline
        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        lifecycle_batches.append({'dashboard_recreations_total': (batch + 1) * 20,
                                  'python_current_bytes': current, 'python_peak_bytes': peak,
                                  'registered_gui_widgets': len(DirectGuiWidget.guiDict),
                                  'live_hud_shells': sum(isinstance(obj, HudShell) for obj in gc.get_objects())})
    _step(app, 5); gc.collect()
    current, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    return {'snapshot_batches': batches, 'board_reloads': 70, 'resize_requests': cycles * 7,
            'dashboard_recreations': recreates, 'lifecycle_batches': lifecycle_batches,
            'python_start_bytes': start_current,
            'python_end_bytes': current, 'python_peak_bytes': peak,
            'final_resources': resources(app), 'status': 'PASS'}


def profile(app, output, frames, warmup, name):
    from panda3d.core import ConfigVariableBool, WindowProperties
    properties = WindowProperties()
    properties.setMinimized(False)
    properties.setForeground(True)
    app.win.requestProperties(properties)
    _step(app, warmup)
    counts_before = resources(app)
    durations = []
    minimized_frames = foreground_frames = 0
    start = time.perf_counter()
    for _ in range(frames):
        before = time.perf_counter()
        app.taskMgr.step()
        app.graphicsEngine.syncFrame()
        durations.append(time.perf_counter() - before)
        minimized_frames += int(app.win.getProperties().getMinimized() or app.mainWinMinimized)
        foreground_frames += int(app.win.getProperties().getForeground())
    elapsed = time.perf_counter() - start
    ordered = sorted(durations)
    return {'profile': name, 'client': [app.win.getXSize(), app.win.getYSize()],
            'pose': 'STANDING', 'level': 'levels/level_01.json', 'frames': frames,
            'warmup_frames': warmup, 'elapsed_seconds': elapsed, 'mean_fps': frames / elapsed,
            'mean_ms': statistics.mean(durations) * 1000,
            'median_ms': statistics.median(durations) * 1000,
            'p95_ms': ordered[math.ceil(.95 * frames) - 1] * 1000,
            'minimized_frames': minimized_frames, 'foreground_frames': foreground_frames,
            'measurement_status': 'INVALID_MINIMIZED' if minimized_frames else 'VALID',
            'sync_video_request': ConfigVariableBool('sync-video').getValue(),
            'samples': app.win.getFbProperties().getMultisamples(),
            'shadow_status': app.presentation.lighting.shadow_status,
            'resources_before': counts_before, 'resources_after': resources(app),
            'note': 'Wall-clock taskMgr.step + syncFrame, includes CPU/driver/compositor; not GPU-only.'}


def entrypoints(output):
    results = []
    for module in ('src.gui.app', 'src.gui.board_preview', 'src.gui.dashboard_preview'):
        process = subprocess.Popen([sys.executable, '-B', '-m', module],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            window_id = None
            for _ in range(150):
                listing = subprocess.check_output(['wmctrl', '-lp'], text=True)
                found = [line.split()[0] for line in listing.splitlines()
                         if int(line.split()[2]) == process.pid]
                if found:
                    window_id = found[0]; break
                if process.poll() is not None:
                    break
                time.sleep(.03)
            assert window_id, f'{module} did not create a native window.'
            time.sleep(.3)
            title = subprocess.check_output(['xprop', '-id', window_id, '_NET_WM_NAME', 'WM_NAME'], text=True).strip()
            subprocess.run(['wmctrl', '-ic', window_id], check=True)
            stdout, stderr = process.communicate(timeout=15)
            assert process.returncode == 0 and 'Traceback' not in stderr, stderr
            results.append({'module': module, 'native_window': window_id, 'title': title,
                            'exit_code': process.returncode, 'stderr': stderr})
        finally:
            if process.poll() is None:
                process.terminate(); process.communicate(timeout=5)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('visual', 'stress', 'profile', 'entrypoints'), default='visual')
    parser.add_argument('--output', type=Path, default=Path('/tmp/bloxorz-stage3-6'))
    parser.add_argument('--profile', choices=('basic', 'enhanced', 'no-aa'), default='basic')
    parser.add_argument('--frames', type=int, default=360)
    parser.add_argument('--warmup', type=int, default=80)
    parser.add_argument('--cycles', type=int, default=5)
    parser.add_argument('--recreates', type=int, default=60,
                        help='Dashboard lifecycle repetitions, a positive multiple of 20.')
    args = parser.parse_args(argv)
    if args.frames < 1 or args.warmup < 0 or args.cycles < 1:
        parser.error('frames/cycles must be positive and warmup nonnegative.')
    if args.recreates < 20 or args.recreates % 20:
        parser.error('recreates must be a positive multiple of 20.')
    if args.mode in ('visual', 'stress') and args.profile != 'basic':
        parser.error('Use --mode profile for enhanced/no-aa; visual/stress use the Basic baseline.')
    args.output.mkdir(parents=True, exist_ok=True)
    if args.mode == 'entrypoints':
        result = entrypoints(args.output)
    else:
        from panda3d.core import GraphicsWindow, PandaSystem, loadPrcFileData
        from src.gui.dashboard_preview import create_dashboard
        from src.gui.board_preview import dispose_presentation
        # Match the historical 3.4 harness request; actual compositor pacing is reported.
        loadPrcFileData('stage3-6-harness', 'sync-video false')
        app, renderer = create_dashboard(shadows=args.profile == 'enhanced',
                                         antialiasing=args.profile != 'no-aa')
        try:
            assert isinstance(app.win, GraphicsWindow), 'Desktop evidence requires onscreen GraphicsWindow.'
            _present(app)
            environment = {'python': sys.version, 'panda': PandaSystem.getVersionString(),
                           'platform': platform.platform(), 'window_class': type(app.win).__name__,
                           'vendor': app.win.getGsg().getDriverVendor(),
                           'renderer': app.win.getGsg().getDriverRenderer(),
                           'driver': app.win.getGsg().getDriverVersion()}
            if args.mode == 'visual':
                result = visual(app, renderer, args.output)
            elif args.mode == 'stress':
                result = stress(app, renderer, args.output, args.cycles, args.recreates)
            else:
                result = profile(app, args.output, args.frames, args.warmup, args.profile)
                result['screenshot'] = _capture(app, args.output, 'profile-' + args.profile,
                    shape='real-4x7', pose='STANDING', shadows=args.profile == 'enhanced',
                    aa=args.profile != 'no-aa')
            result['environment'] = environment
        except SystemExit as error:
            raise RuntimeError('Preview closed before validation finished; no successful run is recorded.') from error
        finally:
            try:
                app.dashboard.dispose()
            finally:
                try:
                    dispose_presentation(app)
                finally:
                    try:
                        renderer.dispose()
                    finally:
                        app.destroy()
        from panda3d.core import GraphicsEngine
        result['graphics_outputs_after_destroy'] = GraphicsEngine.getGlobalPtr().getNumWindows()
        assert result['graphics_outputs_after_destroy'] == 0
    filename = args.mode + ('-' + args.profile if args.mode == 'profile' else '') + '.json'
    (args.output / filename).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
