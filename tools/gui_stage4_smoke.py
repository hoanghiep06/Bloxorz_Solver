"""Reproducible onscreen Stage 4 fixture QA; never invoke Core or gameplay.

Run with .venv/bin/python -B -m tools.gui_stage4_smoke. Screenshots and JSON
are local evidence under /tmp/bloxorz-stage4 by default, not production assets.
"""
import argparse
from dataclasses import replace
import gc
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc

from src.gui.advanced_fixtures import SCENARIOS, get_visual_fixture
from src.gui.advanced_preview import (
    AdvancedPreviewPresentation, create_advanced_preview, dispose_advanced_preview, build_framing_data,
)
from src.gui.advanced_renderer import AdvancedSceneRenderer
from src.gui.dashboard_preview import DashboardPresentation
from src.gui.hud import HudViewModel
from tools.gui_stage3_6_smoke import _present, _resize, _step, _validate_frame, resources, _vertices


def counts(app):
    result = resources(app)
    result['dynamic_paths'] = app.dynamic_tile_root.findAllMatches('**').getNumPaths()
    result['dynamic_mesh_instances'] = app.dynamic_tile_root.findAllMatches('**/+GeomNode').getNumPaths()
    return result


def load_fixture(app, renderer, fixture, variant):
    renderer.load_board(fixture.board)
    renderer.show_snapshot(variant.snapshot)
    rect = app.dashboard.viewport.layout.viewport
    app.presentation.camera.fit_board(build_framing_data(fixture.board), rect.width, rect.height)
    app.dashboard.hud.update_view_model(HudViewModel(
        level_label='VISUAL DEMO DATA / ' + fixture.name.upper(), runtime_status=variant.label))


def capture(app, output, name):
    from src.gui.camera import project_point
    _step(app, 12)
    # Explicitly complete fresh draws before reading the onscreen buffer; rapid
    # fixture changes must not capture an earlier buffered image.
    app.graphicsEngine.renderFrame()
    app.graphicsEngine.renderFrame()
    app.graphicsEngine.syncFrame()
    _validate_frame(app)
    fit = app.presentation.camera.current_fit
    points = [p for root in (app.static_board_root, app.dynamic_tile_root, app.block_root)
              for p in _vertices(root, app.render)]
    for point in points:
        x, y, depth = project_point(point, fit)
        assert max(abs(x), abs(y)) < 1 and fit.near < depth < fit.far
    path = output / (name + '.png')
    assert app.win.saveScreenshot(str(path)), 'GraphicsWindow screenshot failed.'
    return {'path': str(path), 'size': [app.win.getXSize(), app.win.getYSize()],
            'actual_samples': app.win.getFbProperties().getMultisamples(),
            'shadow_status': app.presentation.lighting.shadow_status,
            'technical_checks': 'PASS', 'visual_review': 'PENDING'}


def visual(app, renderer, output):
    images = []
    for name in SCENARIOS:
        fixture = get_visual_fixture(name)
        for variant in fixture.variants:
            load_fixture(app, renderer, fixture, variant)
            images.append(capture(app, output, f'{name}-{variant.name}-1280x720'))
    _resize(app, (1024, 720))
    for name, state in (('switches', 'inactive'), ('switches', 'activated'),
                        ('combined', 'cube-a'), ('combined', 'cube-b')):
        fixture = get_visual_fixture(name)
        load_fixture(app, renderer, fixture, fixture.variant(state))
        images.append(capture(app, output, f'{name}-{state}-1024x720'))
    return {'images': images}


def stress(app, renderer):
    fixture = get_visual_fixture()
    load_fixture(app, renderer, fixture, fixture.variants[0])
    _step(app, 20)
    baseline = counts(app)
    static = renderer._contents[0].node()
    meshes = renderer._meshes.copy()
    camera = app.camera.getTransform()
    tracemalloc.start()
    gc.collect()
    start_current, _ = tracemalloc.get_traced_memory()
    batches = []
    for batch in range(3):
        for i in range(500):
            variant = fixture.variants[i % len(fixture.variants)]
            renderer.show_snapshot(replace(variant.snapshot, state_revision=batch * 500 + i + 1))
        _step(app, 3)
        gc.collect()
        assert counts(app) == baseline
        assert static == renderer._contents[0].node()
        assert meshes == renderer._meshes
        assert camera == app.camera.getTransform()
        current, peak = tracemalloc.get_traced_memory()
        batches.append({'updates': (batch + 1) * 500, 'resources': counts(app),
                        'python_current_bytes': current, 'python_peak_bytes': peak})
    for i in range(36):
        f = get_visual_fixture(SCENARIOS[i % len(SCENARIOS)])
        renderer.load_board(f.board)
        renderer.load_board(f.board)
        renderer.show_snapshot(f.variants[0].snapshot)
        assert all(root.getNumChildren() == 1 for root in renderer._roots)
    load_fixture(app, renderer, fixture, fixture.variants[0])
    assert counts(app) == baseline
    for _ in range(20):
        app.dashboard.dispose()
        app.presentation.dispose()
        app.presentation = AdvancedPreviewPresentation(app, build_framing_data(fixture.board))
        app.dashboard = DashboardPresentation(app, HudViewModel(level_label='VISUAL DEMO DATA'))
        _step(app, 2)
        assert counts(app) == baseline
    # Exercise actual renderer dispose/recreate, including dynamic content cleanup.
    for _ in range(12):
        renderer.dispose()
        assert all(root.getNumChildren() == 0 for root in (
            app.static_board_root, app.dynamic_tile_root, app.block_root))
        renderer = AdvancedSceneRenderer(app.static_board_root, app.dynamic_tile_root, app.block_root)
        load_fixture(app, renderer, fixture, fixture.variants[0])
        assert counts(app) == baseline
    gc.collect()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return renderer, {'status': 'PASS', 'snapshot_batches': batches, 'reloads': 36,
        'presentation_recreations': 20, 'renderer_recreations': 12,
        'python_start_bytes': start_current, 'python_end_bytes': current, 'python_peak_bytes': peak,
        'final_resources': counts(app),
        'note': 'Finite stress observation, not a zero-leak claim; tracemalloc is Python heap only.'}


def profile(app, output):
    _step(app, 60)
    before = counts(app)
    durations = []
    minimized = 0
    foreground = 0
    for _ in range(240):
        start = time.perf_counter()
        app.taskMgr.step()
        app.graphicsEngine.syncFrame()
        durations.append(time.perf_counter() - start)
        minimized += int(app.win.getProperties().getMinimized() or app.mainWinMinimized)
        foreground += int(app.win.getProperties().getForeground())
    assert counts(app) == before
    return {'frames': len(durations), 'warmup_frames': 60,
        'mean_fps': 1 / statistics.mean(durations), 'mean_ms': statistics.mean(durations) * 1000,
        'median_ms': statistics.median(durations) * 1000,
        'p95_ms': sorted(durations)[227] * 1000, 'minimized_frames': minimized,
        'foreground_frames': foreground, 'status': 'VALID' if not minimized else 'INVALID_MINIMIZED',
        'resources': before, 'capture': capture(app, output, 'profile'),
        'note': 'TaskMgr.step + syncFrame wall clock includes CPU, driver and compositor, not GPU-only.'}


def native_entrypoint():
    process = subprocess.Popen([sys.executable, '-B', '-m', 'src.gui.advanced_preview',
        '--scenario', 'bridge', '--state', 'absent'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        window_id = None
        for _ in range(150):
            listing = subprocess.check_output(['wmctrl', '-lp'], text=True)
            found = [line.split()[0] for line in listing.splitlines() if int(line.split()[2]) == process.pid]
            if found:
                window_id = found[0]
                break
            if process.poll() is not None:
                break
            time.sleep(.03)
        assert window_id, 'Advanced entrypoint did not open a native window.'
        time.sleep(.3)
        subprocess.run(['wmctrl', '-ic', window_id], check=True)
        stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == 0 and 'Traceback' not in stderr, stderr
        return {'module': 'src.gui.advanced_preview', 'scenario': 'bridge/absent',
                'window_id': window_id, 'exit_code': process.returncode, 'stderr': stderr}
    finally:
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=5)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('visual', 'stress', 'profile', 'entrypoint'), default='visual')
    parser.add_argument('--output', type=Path, default=Path('/tmp/bloxorz-stage4'))
    parser.add_argument('--shadows', action='store_true')
    parser.add_argument('--no-aa', action='store_true')
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    if args.mode == 'entrypoint':
        result = native_entrypoint()
    else:
        from panda3d.core import GraphicsEngine, GraphicsWindow, PandaSystem
        app, renderer = create_advanced_preview(shadows=args.shadows, antialiasing=not args.no_aa)
        try:
            assert isinstance(app.win, GraphicsWindow)
            _present(app)
            environment = {'platform': platform.platform(), 'python': sys.version,
                'panda': PandaSystem.getVersionString(), 'window': type(app.win).__name__,
                'vendor': app.win.getGsg().getDriverVendor(), 'renderer': app.win.getGsg().getDriverRenderer(),
                'driver': app.win.getGsg().getDriverVersion()}
            if args.mode == 'visual':
                result = visual(app, renderer, args.output)
            elif args.mode == 'stress':
                renderer, result = stress(app, renderer)
            else:
                result = profile(app, args.output)
            result['environment'] = environment
        finally:
            dispose_advanced_preview(app, renderer)
        result['graphics_outputs_after_destroy'] = GraphicsEngine.getGlobalPtr().getNumWindows()
        assert result['graphics_outputs_after_destroy'] == 0
    (args.output / (args.mode + '.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
