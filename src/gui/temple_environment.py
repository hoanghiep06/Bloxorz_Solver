"""Deterministic edge-only botanical details; never support geometry over void."""
import random
from panda3d.core import TextureStage,ShaderInput,LVecBase4f
from src.gui.mesh_factory import MeshBuilder
from src.gui.geometry_math import cell_to_world
from src.gui.advanced_contracts import AdvancedTileKind as Tile


def vary_tile(node, row, col):
    """Variation is baked on each instance, stable across sessions and effects."""
    seed = (row*73856093 ^ col*19349663) & 0xffffffff
    rng = random.Random(seed)
    node.setTexOffset(TextureStage.getDefault(),rng.random(),rng.random())
    value = rng.uniform(.88,1.05)
    node.setColorScale(value,value,value,1)
    dark=node.find('TileTheme-dark')
    if not dark.isEmpty():
        # Unique instance parent, never modify the shared prototype/material.
        dark.setTexRotate(TextureStage.getDefault(),rng.choice((0,90,180,270)))
        # Legacy Jungle tint remains on the parent. Snow has its own restrained
        # variation; do not double-darken white snow with the Jungle multiplier.
        dark.setColorScaleOff(1)
        dark.setShaderInput(ShaderInput('snow_variation',
            LVecBase4f(rng.uniform(.97,1.04),rng.uniform(.45,.95),0.,0.),1))


def add_edge_growth(parent, board, *, pitch=1.):
    """Batched foundations/vines only beneath permanent, exposed floor cells.

    No geometry touches z=0 or extends into another cell. Fragile, bridge, goal
    and void cells never receive a hidden platform beneath them.
    """
    root = parent.attachNewNode('TempleEdgeGrowth')
    stones = {t:MeshBuilder('EdgeFoundation-'+t) for t in ('light','dark')}
    plants = {t:MeshBuilder('EdgeBotany-'+t) for t in ('light','dark')}
    for r,row in enumerate(board.tiles):
        for c,kind in enumerate(row):
            if kind is not Tile.FLOOR or (r,c) in board.goal_cells:
                continue
            edges=[]
            for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
                nr,nc=r+dr,c+dc
                if not (0<=nr<board.rows and 0<=nc<board.cols) or board.tiles[nr][nc] is Tile.VOID:
                    edges.append((dr,dc))
            if not edges:continue
            rng=random.Random(r*1031+c*8731+51)
            x,y=cell_to_world(r,c,rows=board.rows,cols=board.cols,pitch=pitch)
            depth=rng.uniform(.45,.64)
            corners=((-1,-1),(1,-1),(1,1),(-1,1))
            upper=[(x+a*.465*pitch,y+b*.465*pitch,-.175*pitch) for a,b in corners]
            lower=[(x+a*.40*pitch,y+b*.40*pitch,-depth*pitch) for a,b in corners]
            for theme,b in stones.items():
                b.uv_offset=(rng.random(),rng.random())
                if theme=='light':
                    color=(.70,.75,.54,1)
                else:
                    from src.gui.visual_materials import SNOW_PALETTE
                    color=SNOW_PALETTE['side']
                for i in range(4):
                    j=(i+1)%4
                    a,bb=corners[i],corners[j]
                    b.face((upper[i],upper[j],lower[j],lower[i]),(a[0]+bb[0],a[1]+bb[1],-.15),color)
                b.face(lower,(0,0,-1),color if theme=='light' else SNOW_PALETTE['underside'])
            for dr,dc in edges:
                # Leaves extend vertically, within the existing slab's XY footprint.
                for j in range(3):
                    off=rng.uniform(-.32,.32); length=rng.uniform(.33,.70)
                    xx=x+(dc*.47+(off if dr else 0))*pitch
                    yy=y+(-dr*.47+(off if dc else 0))*pitch
                    tangent=(1,0) if dr else (0,1)
                    def point(u,z):return (xx+tangent[0]*u*pitch,yy+tangent[1]*u*pitch,z*pitch)
                    light=plants['light'];dark=plants['dark']
                    light.face((point(-.009,-.07),point(.009,-.07),point(.009,-length),point(-.009,-length)),(dc,-dr,0),(.22,.30,.07,1))
                    for k in range(3):
                        z=-.16-k*(length-.16)/3
                        side=(-1 if k%2 else 1)
                        light.face((point(0,z+.025),point(side*.10,z-.03),point(side*.065,z-.10),point(0,z-.06)),(dc,-dr,.2),(.29,.44,.10,1))
                    dark.face((point(-.045,-.07),point(.045,-.07),point(.009,-length*.65)),(dc,-dr,0),(.71,.84,.98,1))
    from src.gui.scene_style import TILE_THEME
    from src.gui.visual_materials import apply
    for theme in ('light','dark'):
        holder=root.attachNewNode('TileTheme-'+theme)
        holder.attachNewNode(apply(stones[theme].finish(),'stone',theme,pitch=pitch))
        holder.attachNewNode(plants[theme].finish()).setTwoSided(True)
        if theme!=TILE_THEME:holder.hide()
    return root


def visible_board_bounds(board, *, pitch=1.):
    """Frame all potential floor/bridge cells, excluding only empty outer rows.

    Includes every complete cuboid pose + flag, and retains generous margins.
    Void holes inside the rectangle are still void; this only chooses a lens fit.
    """
    from src.gui.camera import SceneBounds
    cells=[(r,c) for r,row in enumerate(board.tiles) for c,kind in enumerate(row) if kind is not Tile.VOID]
    if not cells:
        return None
    points=[cell_to_world(r,c,rows=board.rows,cols=board.cols,pitch=pitch) for r,c in cells]
    xs,ys=zip(*points)
    return SceneBounds((min(xs)-.6*pitch,min(ys)-.6*pitch,-.8*pitch),
                       (max(xs)+.6*pitch,max(ys)+.6*pitch,2.3*pitch))
