"""Procedural Advanced visual assets, all dimensions scaled by logical pitch.

Tiles have a supporting top at Z=0; raised markings are separated from that
plane. Broken debris remains below it. No collision or state logic lives here.

Mỗi loại ô đặc biệt có một màu nhận diện riêng, không trùng với sàn (xám xanh / be):
    ô cam vỡ    : cam + vết nứt nâu đậm
    cầu         : tím + gân sáng
    nút tròn    : vàng, nằm trong vòng đen
    nút chéo    : dấu cộng đỏ trên đế đen
    nút tách    : hai tấm hồng/magenta trên đế đen
    đã kích hoạt: xanh lá sáng (mọi loại nút)
"""

import math
from panda3d.core import GeomNode, Mat4, Vec3

from src.gui.advanced_contracts import SwitchVisualKind
from src.gui.mesh_factory import (
    MeshBuilder, make_beveled_box_mesh, BLOCK_MAIN, BLOCK_DARK, BLOCK_HIGHLIGHT,
    FLOOR_SIDE,
)


def _c(r, g, b):
    return (r / 255, g / 255, b / 255, 1.0)


# Ô cam vỡ
FRAGILE = _c(240, 160, 75)
FRAGILE_SIDE = _c(168, 101, 40)
FRAGILE_EDGE = _c(255, 205, 130)
CRACK = _c(92, 52, 20)

# Cầu
BRIDGE_TOP = _c(132, 100, 210)
BRIDGE_SIDE = _c(74, 58, 128)
BRIDGE_EDGE = _c(190, 172, 242)
BRIDGE_RIB = _c(200, 186, 248)

# Nút bấm
SWITCH_BASE = _c(34, 36, 46)
SWITCH_BASE_EDGE = _c(120, 124, 140)
SOFT_COLOR = _c(250, 200, 30)
SOFT_SIDE = _c(150, 112, 10)
HEAVY_COLOR = _c(228, 70, 60)
SPLIT_COLOR = _c(230, 82, 160)
SUCCESS = _c(52, 200, 120)          # đã kích hoạt / khối đang chọn
SUCCESS_SIDE = _c(24, 120, 70)

# Cờ ở ô đích
FLAG_POLE = _c(236, 240, 246)
FLAG_CLOTH = _c(226, 50, 48)
FLAG_GOLD = _c(245, 194, 48)
# Vị trí cột cờ trong ô đích: nằm trên phần viền (rim) ở góc, không chắn miệng hố.
# Đổi dấu x/y nếu muốn cờ đứng ở góc khác.
FLAG_POLE_XY = (-.43, .43)
FLAG_HEIGHT = 1.4          # chiều cao cột (đơn vị ô); khối đứng cao 2 nên vẫn thấp hơn khối
FLAG_POLE_THICK = .07
FLAG_CLOTH_WIDTH = .78     # vải cờ dài, mũi cờ vẫn nằm trong ô (cột ở x=-.43 -> mũi ở x≈.37)
FLAG_CLOTH_HEIGHT = .52


def _pitch(pitch):
    if type(pitch) not in (int, float) or not math.isfinite(pitch) or pitch <= 0:
        raise ValueError('pitch must be finite and positive (not bool).')


def _box(name, dimensions, center, pitch, top, side=BLOCK_DARK, edge=BLOCK_HIGHLIGHT,
         angle=0):
    node = make_beveled_box_mesh(name=name, dimensions=tuple(v * pitch for v in dimensions),
        bevel=min(.02, min(dimensions) / 5) * pitch,
        top_color=top, side_color=side, edge_color=edge)
    transform = Mat4.rotateMat(angle, Vec3(0, 0, 1)) * Mat4.translateMat(
        *(v * pitch for v in center))
    node.modifyGeom(0).transformVertices(transform)
    return node


def _combine(name, parts):
    node = GeomNode(name)
    for part in parts:
        for index in range(part.getNumGeoms()):
            node.addGeom(part.modifyGeom(index))
    return node


def make_fragile_mesh(*, pitch=1.0, broken=False):
    _pitch(pitch)
    if type(broken) is not bool:
        raise TypeError('broken must be bool.')
    if broken:
        # Three small remnants below the vanished supporting plane; no full floor.
        return _combine('BrokenFragileMesh', [
            _box('Debris', (.18, .13, .06), center, pitch, FRAGILE, CRACK, FRAGILE, angle)
            for center, angle in (((-.32, -.30, -.14), 18),
                                  ((.29, .31, -.14), -23), ((.30, -.32, -.14), 37))])
    parts = [_box('FragileSurface', (.96, .96, .18), (0, 0, -.09), pitch,
                  FRAGILE, FRAGILE_SIDE, FRAGILE_EDGE)]
    # Vết nứt dày hơn, tối hơn để thấy rõ; đáy cách mặt đỡ .002.
    for a, b in (((-.36, -.32), (0, -.04)), ((0, -.04), (.32, .34)),
                 ((0, -.04), (-.24, .30)), ((.12, .10), (.37, .03))):
        length = math.dist(a, b)
        center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, .008)
        angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        parts.append(_box('Crack', (length, .045, .012), center, pitch, CRACK, CRACK, CRACK, angle))
    return _combine('IntactFragileMesh', parts)


def make_bridge_mesh(*, pitch=1.0):
    _pitch(pitch)
    return _combine('BridgePlatformMesh', [
        _box('BridgePlatform', (.96, .96, .18), (0, 0, -.09), pitch,
             BRIDGE_TOP, BRIDGE_SIDE, BRIDGE_EDGE),
        *[_box('BridgeRib', (.78, .06, .02), (0, y, .011), pitch,
               BRIDGE_RIB, BRIDGE_SIDE, BRIDGE_RIB) for y in (-.28, 0, .28)]])


def _disc(pitch, color, side, *, radius=.30, z0=.015, z1=.07, name='SoftSwitchDisc'):
    builder = MeshBuilder(name)
    points = [(radius * math.cos(i * math.tau / 24), radius * math.sin(i * math.tau / 24))
              for i in range(24)]
    def point(xy, z):
        return (xy[0] * pitch, xy[1] * pitch, z * pitch)
    builder.face([point(p, z1) for p in points], (0, 0, 1), color)
    builder.face([point(p, z0) for p in points], (0, 0, -1), side)
    for i, a in enumerate(points):
        b = points[(i + 1) % len(points)]
        builder.face((point(a, z0), point(b, z0), point(b, z1), point(a, z1)),
                     (a[0] + b[0], a[1] + b[1], 0), side)
    return builder.finish()


def make_switch_mesh(kind, *, activated=False, pitch=1.0):
    _pitch(pitch)
    if type(kind) is not SwitchVisualKind or type(activated) is not bool:
        raise TypeError('Expected SwitchVisualKind and bool activated.')
    if kind is SwitchVisualKind.SOFT:
        color, side = (SUCCESS, SUCCESS_SIDE) if activated else (SOFT_COLOR, SOFT_SIDE)
        # Vòng đen bên ngoài làm nổi nút tròn trên mọi màu sàn.
        return _combine('SoftSwitchMesh', [
            _disc(pitch, SWITCH_BASE, SWITCH_BASE, radius=.40, z0=.005, z1=.035,
                  name='SoftSwitchRing'),
            _disc(pitch, color, side, radius=.29, z0=.03, z1=.105)])
    if kind is SwitchVisualKind.HEAVY:
        color = SUCCESS if activated else HEAVY_COLOR
        # Đế đen vuông + dấu cộng lớn: khác hẳn nút tròn và nút tách.
        return _combine('HeavySwitchMesh', [
            _box('HeavyBase', (.74, .74, .06), (0, 0, .03), pitch,
                 SWITCH_BASE, SWITCH_BASE, SWITCH_BASE_EDGE),
            _box('HeavyCrossV', (.17, .56, .04), (0, 0, .08), pitch, color, color, color),
            _box('HeavyCrossH', (.56, .17, .04), (0, 0, .08), pitch, color, color, color)])
    color = SUCCESS if activated else SPLIT_COLOR
    return _combine('SplitSwitchMesh', [
        _box('SplitBase', (.76, .62, .04), (0, 0, .02), pitch,
             SWITCH_BASE, SWITCH_BASE, SWITCH_BASE_EDGE),
        *[_box('SplitPlate', (.24, .50, .07), (x, 0, .07), pitch,
               color, SWITCH_BASE, color) for x in (-.19, .19)]])


def make_split_cube_mesh(*, pitch=1.0):
    _pitch(pitch)
    return _box('SplitCubeMesh', (1, 1, 1), (0, 0, 0), pitch,
                BLOCK_MAIN, BLOCK_MAIN, BLOCK_HIGHLIGHT)


def make_active_cube_mesh(*, pitch=1.0):
    """Four top corner brackets, inside the cube's nominal footprint; no pulse."""
    _pitch(pitch)
    parts = []
    for x in (-1, 1):
        for y in (-1, 1):
            parts.extend((
                _box('ActiveBracket', (.24, .045, .03), (x * .33, y * .425, .525),
                     pitch, SUCCESS, SUCCESS, SUCCESS),
                _box('ActiveBracket', (.045, .19, .03), (x * .425, y * .3075, .525),
                     pitch, SUCCESS, SUCCESS, SUCCESS)))
    return _combine('ActiveCubeIndicatorMesh', parts)


def make_flag_mesh(*, pitch=1.0):
    """Cờ đuôi nheo cắm ở góc viền ô đích: cột trắng, đỉnh vàng, vải đỏ hướng vào miệng hố."""
    _pitch(pitch)
    px, py = FLAG_POLE_XY
    h = FLAG_HEIGHT
    parts = [
        _box('FlagPole', (FLAG_POLE_THICK, FLAG_POLE_THICK, h), (px, py, h / 2), pitch,
             FLAG_POLE, FLAG_POLE, FLAG_POLE),
        _box('FlagFinial', (.14, .14, .14), (px, py, h + .05), pitch,
             FLAG_GOLD, FLAG_GOLD, FLAG_GOLD),
    ]
    # Vải cờ: tam giác nằm trong mặt phẳng XZ, vẽ hai mặt để nhìn được từ mọi phía.
    cloth = MeshBuilder('FlagCloth')
    x0 = px + FLAG_POLE_THICK / 2
    z_top, z_bottom = h - .03, h - .03 - FLAG_CLOTH_HEIGHT
    tip = (x0 + FLAG_CLOTH_WIDTH, py, (z_top + z_bottom) / 2)
    triangle = [(x0, py, z_top), (x0, py, z_bottom), tip]
    triangle = [(x * pitch, y * pitch, z * pitch) for x, y, z in triangle]
    cloth.face(triangle, (0, 1, 0), FLAG_CLOTH)
    cloth.face(triangle, (0, -1, 0), FLAG_CLOTH)
    parts.append(cloth.finish())
    return _combine('GoalFlagMesh', parts)