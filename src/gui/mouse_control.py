"""Mouse control: clicking around the block rolls it toward the click.

direction_from_click is pure math; pick_action is the thin Panda3D adapter.
World directions come from controller.ACTION_TO_ROLL, so one mapping drives both
keyboard rolls and mouse picking.
"""
import math


def controlled_cells(state):
    """Footprint of the actor receiving input, not all occupied board cells.

    Split cubes keep independent positions. Only the selected cube determines
    mouse directions and arrow placement; a merged block uses its full footprint.
    """
    if state.is_split():
        return [state.cubes[state.active_cube]]
    return state.get_occupied_cells()


def direction_from_click(click, center, projected, aspect, dead_zone=.03):
    """click/center are viewport NDC (x, y); projected maps action -> NDC of the
    block centre moved one cell along that action. Returns an action or None."""
    cx, cy = (click[0] - center[0]) * aspect, click[1] - center[1]
    length = math.hypot(cx, cy)
    if length < dead_zone:
        return None
    best, best_cos = None, -2.0
    for action, (px, py) in projected.items():
        vx, vy = (px - center[0]) * aspect, py - center[1]
        norm = math.hypot(vx, vy)
        if norm == 0:
            continue
        cosine = (cx * vx + cy * vy) / (length * norm)
        if cosine > best_cos:
            best, best_cos = action, cosine
    return best


def pick_action(app, region, fit, cells, rows, cols, pitch=1.0):
    """Return 'U'/'D'/'L'/'R' for the current mouse position, or None."""
    from src.gui.camera import project_point
    from src.gui.controller import ACTION_TO_ROLL
    from src.gui.geometry_math import cell_to_world

    watcher = app.mouseWatcherNode
    if fit is None or not watcher.hasMouse():
        return None
    mouse = watcher.getMouse()
    left, right, bottom, top = region.getDimensions()
    u, v = (mouse[0] + 1) / 2, (mouse[1] + 1) / 2
    if not (left <= u <= right and bottom <= v <= top):
        return None
    click = (2 * (u - left) / (right - left) - 1, 2 * (v - bottom) / (top - bottom) - 1)
    points = [cell_to_world(r, c, rows=rows, cols=cols, pitch=pitch) for r, c in cells]
    x = sum(p[0] for p in points) / len(points)
    y = sum(p[1] for p in points) / len(points)
    z = pitch / 2
    center = project_point((x, y, z), fit)[:2]
    projected = {}
    for action, direction in ACTION_TO_ROLL.items():
        dx, dy, _ = direction.value
        projected[action] = project_point((x + dx * pitch, y + dy * pitch, z), fit)[:2]
    return direction_from_click(click, center, projected, fit.aspect)


def pointer_over_hud(app):
    """HUD includes passive labels/metrics, which have no MouseWatcher region."""
    hud = getattr(app.dashboard, 'hud', None)
    watcher = app.mouseWatcherNode
    if hud is None or not watcher.hasMouse():
        return False
    mouse = watcher.getMouse()
    x = (mouse[0]+1)*app.win.getXSize()/2
    y = (1-mouse[1])*app.win.getYSize()/2
    return hud.contains_pointer_pixels(x,y)
