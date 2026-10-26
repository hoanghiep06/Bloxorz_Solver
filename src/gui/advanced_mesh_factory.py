"""Procedural Advanced visual assets, all dimensions scaled by logical pitch.

Tiles have a supporting top at Z=0; raised markings are separated from that
plane. Broken debris remains below it. No collision or state logic lives here.

Mỗi theme có một bảng màu riêng cho ô đặc biệt (xem PALETTES):
    Sáng (light): tone vàng - cam - trắng
    Tối (dark)  : tone xanh - tím - trắng, điểm chút đỏ
    đã kích hoạt: xanh lá (sáng) / xanh ngọc (tối)
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


# Mỗi theme một bảng màu. Sáng: vàng - cam - trắng. Tối: xanh - tím - trắng, điểm chút đỏ.
PALETTES = {
    'light': dict(
        FRAGILE=_c(214, 98, 52), FRAGILE_SIDE=_c(140, 62, 28),
        FRAGILE_EDGE=_c(255, 190, 130), CRACK=_c(84, 36, 14),
        BRIDGE_TOP=_c(255, 196, 64), BRIDGE_SIDE=_c(170, 112, 18),
        BRIDGE_EDGE=_c(255, 230, 150), BRIDGE_RIB=_c(255, 248, 224),
        SWITCH_BASE=_c(52, 38, 30), SWITCH_BASE_EDGE=_c(176, 142, 110),
        SOFT_COLOR=_c(255, 250, 236), SOFT_SIDE=_c(176, 150, 110),
        HEAVY_COLOR=_c(222, 58, 48),
        SPLIT_COLOR=_c(244, 128, 28),
        ACTIVE=_c(96, 204, 96), ACTIVE_SIDE=_c(40, 120, 50)),
    'dark': dict(
        FRAGILE=_c(228, 84, 108), FRAGILE_SIDE=_c(128, 38, 72),
        FRAGILE_EDGE=_c(255, 165, 182), CRACK=_c(58, 14, 40),
        BRIDGE_TOP=_c(166, 142, 255), BRIDGE_SIDE=_c(86, 66, 168),
        BRIDGE_EDGE=_c(222, 212, 255), BRIDGE_RIB=_c(246, 242, 255),
        SWITCH_BASE=_c(22, 20, 44), SWITCH_BASE_EDGE=_c(132, 132, 196),
        SOFT_COLOR=_c(240, 244, 255), SOFT_SIDE=_c(112, 124, 186),
        HEAVY_COLOR=_c(238, 66, 92),
        SPLIT_COLOR=_c(110, 202, 255),
        ACTIVE=_c(90, 228, 196), ACTIVE_SIDE=_c(30, 128, 118)),
}
THEMES = ('light', 'dark')


def _palette(theme):
    if theme not in PALETTES:
        raise ValueError('theme must be light or dark.')
    return PALETTES[theme]


# Giữ tên hằng cũ (bảng sáng) để code/test khác import vẫn chạy.
FRAGILE, FRAGILE_SIDE, FRAGILE_EDGE, CRACK = (PALETTES['light'][k] for k in
    ('FRAGILE', 'FRAGILE_SIDE', 'FRAGILE_EDGE', 'CRACK'))
BRIDGE_TOP, BRIDGE_SIDE, BRIDGE_EDGE, BRIDGE_RIB = (PALETTES['light'][k] for k in
    ('BRIDGE_TOP', 'BRIDGE_SIDE', 'BRIDGE_EDGE', 'BRIDGE_RIB'))
SWITCH_BASE, SWITCH_BASE_EDGE = PALETTES['light']['SWITCH_BASE'], PALETTES['light']['SWITCH_BASE_EDGE']
SOFT_COLOR, SOFT_SIDE = PALETTES['light']['SOFT_COLOR'], PALETTES['light']['SOFT_SIDE']
HEAVY_COLOR, SPLIT_COLOR = PALETTES['light']['HEAVY_COLOR'], PALETTES['light']['SPLIT_COLOR']
# Khung chỉ thị khối đang chọn (giữ xanh lá, không đổi theo theme)
SUCCESS = _c(52, 200, 120)
SUCCESS_SIDE = _c(24, 120, 70)

# Cờ ở ô đích (màu sáng, rực; cờ được render không ăn đèn nên giữ đúng màu này)
FLAG_POLE = _c(255, 255, 255)
FLAG_CLOTH = _c(255, 38, 38)      # đỏ thuần, sáng
FLAG_GOLD = _c(255, 214, 59)
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


def make_fragile_mesh(*, pitch=1.0, broken=False, theme='light'):
    _pitch(pitch)
    if type(broken) is not bool:
        raise TypeError('broken must be bool.')
    p = _palette(theme)
    if broken:
        # Three small remnants below the vanished supporting plane; no full floor.
        return _combine('BrokenFragileMesh', [
            _box('Debris', (.18, .13, .06), center, pitch,
                 p['FRAGILE'], p['CRACK'], p['FRAGILE'], angle)
            for center, angle in (((-.32, -.30, -.14), 18),
                                  ((.29, .31, -.14), -23), ((.30, -.32, -.14), 37))])
    parts = [_box('FragileSurface', (.96, .96, .18), (0, 0, -.09), pitch,
                  p['FRAGILE'], p['FRAGILE_SIDE'], p['FRAGILE_EDGE'])]
    # Vết nứt dày hơn, tối hơn để thấy rõ; đáy cách mặt đỡ .002.
    for a, b in (((-.36, -.32), (0, -.04)), ((0, -.04), (.32, .34)),
                 ((0, -.04), (-.24, .30)), ((.12, .10), (.37, .03))):
        length = math.dist(a, b)
        center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, .008)
        angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        parts.append(_box('Crack', (length, .045, .012), center, pitch,
                          p['CRACK'], p['CRACK'], p['CRACK'], angle))
    return _combine('IntactFragileMesh', parts)


def make_bridge_mesh(*, pitch=1.0, theme='light'):
    _pitch(pitch)
    p = _palette(theme)
    return _combine('BridgePlatformMesh', [
        _box('BridgePlatform', (.96, .96, .18), (0, 0, -.09), pitch,
             p['BRIDGE_TOP'], p['BRIDGE_SIDE'], p['BRIDGE_EDGE']),
        *[_box('BridgeRib', (.78, .06, .02), (0, y, .011), pitch,
               p['BRIDGE_RIB'], p['BRIDGE_SIDE'], p['BRIDGE_RIB']) for y in (-.28, 0, .28)]])


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


def make_switch_mesh(kind, *, activated=False, pitch=1.0, theme='light'):
    _pitch(pitch)
    if type(kind) is not SwitchVisualKind or type(activated) is not bool:
        raise TypeError('Expected SwitchVisualKind and bool activated.')
    p = _palette(theme)
    base, base_edge = p['SWITCH_BASE'], p['SWITCH_BASE_EDGE']
    if kind is SwitchVisualKind.SOFT:
        color, side = ((p['ACTIVE'], p['ACTIVE_SIDE']) if activated
                       else (p['SOFT_COLOR'], p['SOFT_SIDE']))
        # Vòng tối bên ngoài làm nổi nút tròn trên mọi màu sàn.
        return _combine('SoftSwitchMesh', [
            _disc(pitch, base, base, radius=.40, z0=.005, z1=.035, name='SoftSwitchRing'),
            _disc(pitch, color, side, radius=.29, z0=.03, z1=.105)])
    if kind is SwitchVisualKind.HEAVY:
        color = p['ACTIVE'] if activated else p['HEAVY_COLOR']
        # Đế vuông + dấu cộng lớn: khác hẳn nút tròn và nút tách.
        return _combine('HeavySwitchMesh', [
            _box('HeavyBase', (.74, .74, .06), (0, 0, .03), pitch, base, base, base_edge),
            _box('HeavyCrossV', (.17, .56, .04), (0, 0, .08), pitch, color, color, color),
            _box('HeavyCrossH', (.56, .17, .04), (0, 0, .08), pitch, color, color, color)])
    color = p['ACTIVE'] if activated else p['SPLIT_COLOR']
    return _combine('SplitSwitchMesh', [
        _box('SplitBase', (.76, .62, .04), (0, 0, .02), pitch, base, base, base_edge),
        *[_box('SplitPlate', (.24, .50, .07), (x, 0, .07), pitch,
               color, base, color) for x in (-.19, .19)]])


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