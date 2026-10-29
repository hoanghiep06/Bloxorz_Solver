"""Visual asset contracts: support envelope, UV stability and owned resources."""
from dataclasses import replace
import hashlib
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from panda3d.core import GeomVertexReader, NodePath, TextureAttrib
from gui_animation_support import AnimationSceneCase
from src.gui.mesh_factory import make_themed_block_mesh, make_themed_cube_mesh, make_floor_mesh
from src.gui.advanced_mesh_factory import make_fragile_mesh, make_bridge_mesh


def values(mesh,column):
    out=[]
    for geom in mesh.getGeoms():
        reader=GeomVertexReader(geom.getVertexData(),column)
        while not reader.isAtEnd():
            out.append(tuple(reader.getData3f()) if column!='texcoord' else tuple(reader.getData2f()))
    return out


class MaterialGeometryTests(unittest.TestCase):
    def test_both_themes_have_uvs_textures_and_exact_rigid_envelopes(self):
        for theme in ('light','dark'):
            for factory,dimensions in ((make_themed_block_mesh,(1,1,2)),(make_themed_cube_mesh,(1,1,1))):
                mesh=factory(theme)
                p=values(mesh,'vertex');uv=values(mesh,'texcoord')
                self.assertEqual(len(p),len(uv))
                self.assertGreater(len(set(uv)),12)
                for axis,size in enumerate(dimensions):
                    self.assertAlmostEqual(max(v[axis] for v in p)-min(v[axis] for v in p),size,places=6)
                self.assertTrue(mesh.getGeomState(0).hasAttrib(TextureAttrib))

    def test_floor_support_and_goal_semantics_stay_unchanged(self):
        for theme in ('light','dark'):
            mesh=make_floor_mesh(theme=theme)
            p=values(mesh,'vertex')
            self.assertAlmostEqual(max(v[2] for v in p),0,places=6)
            self.assertAlmostEqual(min(v[2] for v in p),-.18,places=6)
            self.assertAlmostEqual(max(v[0] for v in p)-min(v[0] for v in p),.96,places=6)

    def test_combined_special_meshes_retain_material_states(self):
        for factory in (make_fragile_mesh,make_bridge_mesh):
            for theme in ('light','dark'):
                self.assertTrue(factory(theme=theme).getGeomState(0).hasAttrib(TextureAttrib))
        broken=make_fragile_mesh(broken=True)
        self.assertLess(max(v[2] for v in values(broken,'vertex')),-.10)

    def test_composition_bounds_include_potential_bridge_and_complete_actor_height(self):
        from src.gui.advanced_fixtures import get_visual_fixture
        from src.gui.temple_environment import visible_board_bounds
        from src.gui.geometry_math import cell_to_world
        from src.gui.advanced_contracts import AdvancedTileKind
        board=get_visual_fixture().board
        bounds=visible_board_bounds(board)
        for r,row in enumerate(board.tiles):
            for c,kind in enumerate(row):
                if kind is AdvancedTileKind.VOID:continue
                x,y=cell_to_world(r,c,rows=board.rows,cols=board.cols)
                self.assertLessEqual(bounds.minimum[0],x-.5)
                self.assertGreaterEqual(bounds.maximum[0],x+.5)
                self.assertLessEqual(bounds.minimum[1],y-.5)
                self.assertGreaterEqual(bounds.maximum[1],y+.5)
        self.assertLessEqual(bounds.minimum[2],-.18)
        self.assertGreaterEqual(bounds.maximum[2],2.3)

    def test_textured_fallback_removes_emission_alpha_without_disabling_assets(self):
        from src.gui import visual_materials as m
        with patch.object(m,'_shader',None):
            m.texture.cache_clear();m.state.cache_clear()
            tex=m.texture('magma')
            self.assertEqual(tex.getNumComponents(),3)
            self.assertTrue(tex.hasRamImage())
            self.assertTrue(m.state('magma').hasAttrib(TextureAttrib))
        m.texture.cache_clear();m.state.cache_clear()

    def test_unsupported_gpu_reports_and_keeps_fixed_function_materials(self):
        from src.gui import visual_materials as m
        with self.assertLogs(m.log,level='WARNING'):
            status=m.configure(SimpleNamespace(getSupportsBasicShaders=lambda:False))
        self.assertEqual(status,'FIXED_FUNCTION')
        self.assertEqual(m.texture('magma').getNumComponents(),3)

    def test_shader_compilation_failure_reports_and_falls_back(self):
        from src.gui import visual_materials as m
        with patch.object(m,'Shader') as shader,self.assertLogs(m.log,level='ERROR'):
            shader.load.side_effect=RuntimeError('QA compilation failure')
            status=m.configure(SimpleNamespace(getSupportsBasicShaders=lambda:True))
        self.assertEqual(status,'FIXED_FUNCTION')
        self.assertTrue(m.state('stone').hasAttrib(TextureAttrib))

    def test_growth_only_under_existing_floor_not_goal_or_void(self):
        from src.gui.advanced_fixtures import get_visual_fixture
        from src.gui.temple_environment import add_edge_growth
        root=NodePath('test-growth')
        self.addCleanup(root.removeNode)
        board=get_visual_fixture().board
        growth=add_edge_growth(root,board)
        for path in growth.findAllMatches('**/+GeomNode'):
            self.assertLess(max(v[2] for v in values(path.node(),'vertex')),0)
            points=values(path.node(),'vertex')
            self.assertGreaterEqual(min(v[2] for v in points),-.8)
            # Every decoration vertex belongs to an existing permanent floor,
            # excluding the goal and every void/bridge/fragile footprint.
            from src.gui.geometry_math import cell_to_world
            from src.gui.advanced_contracts import AdvancedTileKind as Tile
            allowed=[cell_to_world(r,c,rows=board.rows,cols=board.cols)
                     for r,row in enumerate(board.tiles) for c,kind in enumerate(row)
                     if kind is Tile.FLOOR and (r,c) not in board.goal_cells]
            for x,y,z in points:
                self.assertTrue(any(abs(x-cx)<=.5 and abs(y-cy)<=.5 for cx,cy in allowed))


class VisualLifecycleTests(AnimationSceneCase):
    def test_ten_rolls_keep_local_vertices_uvs_and_shared_texture_identity(self):
        self.build('basic-roll')
        def digest():
            result=[]
            for key,mesh in sorted(self.manager._rig._meshes.items()):
                result.append((key,values(mesh,'vertex'),values(mesh,'texcoord'),str(mesh.getGeomState(0))))
            return hashlib.sha256(repr(result).encode()).hexdigest()
        before=digest()
        from src.gui.animation_math import RollDirection
        template=self.fixture.requests[0]
        for index in range(10):
            endpoint=template.after_snapshot if index%2==0 else template.before_snapshot
            request=replace(template,request_id=f'uv-roll-{index}',
                before_snapshot=self.manager.current_snapshot,
                after_snapshot=replace(endpoint,state_revision=index+1),
                direction=RollDirection.RIGHT if index%2==0 else RollDirection.LEFT)
            self.manager.submit(request)
            for _ in range(30):self.manager.advance(request.duration/30)
            self.manager.advance(.001)
            self.assertEqual(digest(),before)
            self.assertFalse(self.manager.is_busy)

    def test_goal_flag_remains_visible_during_surface_effect_and_cancel(self):
        self.build('bridge')
        flags=self.renderer._flags
        self.assertTrue(flags)
        copies=tuple(flags.values())+tuple(self.layer._flags.values())
        self.assertEqual(sum(not f.isHidden() for f in copies),len(flags))
        self.manager.submit(self.fixture.requests[0]);self.manager.advance(.1)
        self.assertTrue(self.layer.renderer_root.isHidden())
        self.assertEqual(sum(not f.isHidden() for f in copies),len(flags))
        self.manager.cancel()
        self.assertEqual(sum(not f.isHidden() for f in copies),len(flags))


class VisualQualityTests(unittest.TestCase):
    def test_auto_uses_balanced_for_software_and_high_for_hardware(self):
        from src.gui.visual_quality import resolve
        for gpu in ('llvmpipe (LLVM 15)','SoftPipe','SwiftShader','software rasterizer'):
            self.assertEqual(resolve('auto',gpu),'balanced')
        self.assertEqual(resolve('auto','NVIDIA'),'high')
        self.assertEqual(resolve('high','llvmpipe'),'high')
        self.assertEqual(resolve('low','NVIDIA'),'low')
        with self.assertRaises(ValueError):resolve('bad')

    def test_quality_defaults_high_and_migrates_old_preferences_without_losing_settings(self):
        import json,tempfile
        from src.gui.profile import SaveData
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'save.json'
            self.assertEqual(SaveData(path).settings.quality,'high')
            for old in ('auto','high','balanced','low','invalid'):
                path.write_text(json.dumps({'settings':{'quality':old,'theme':'dark',
                    'control_mode':'mouse','music_volume':.4},'stars':{'level_01':3}}))
                save=SaveData(path)
                self.assertEqual(save.settings.quality,'high')
                self.assertEqual(save.settings.theme,'dark')
                self.assertEqual(save.settings.control_mode,'mouse')
                self.assertEqual(save.settings.music_volume,.4)
                self.assertEqual(save.stars_for('level_01'),3)
                self.assertTrue(save.save())
                self.assertEqual(json.loads(path.read_text())['settings']['quality'],'high')

    def test_quality_changes_preserve_cloth_clock(self):
        from src.gui import visual_materials as m,visual_quality as q
        previous=q.CURRENT
        self.addCleanup(m.set_quality,previous)
        old=m._quality[0]
        m._quality[0]=type(old)(old[0],42,0,0)
        m.set_quality('low')
        self.assertEqual(tuple(m._quality[0])[:2],(0.,42.))
        m.set_quality('high')
        self.assertEqual(tuple(m._quality[0])[:2],(1.,42.))

    def test_atmosphere_owns_one_task_and_releases_idempotently(self):
        from unittest.mock import Mock
        from src.gui.visual_materials import TempleAtmosphere
        manager=Mock()
        atmosphere=TempleAtmosphere(SimpleNamespace(taskMgr=manager))
        manager.add.assert_called_once()
        token=atmosphere._task
        atmosphere.dispose();atmosphere.dispose()
        manager.remove.assert_called_once_with(token)
        no_task=TempleAtmosphere(SimpleNamespace())
        no_task.dispose()

    def test_flag_is_subdivided_without_changing_pole_or_cell_envelope(self):
        from src.gui.advanced_mesh_factory import make_flag_mesh,FLAG_POLE_XY
        flag=make_flag_mesh()
        names=[g.getVertexData().getName() for g in flag.getGeoms()]
        cloth=flag.getGeom(names.index('FlagCloth')).getVertexData()
        self.assertGreaterEqual(cloth.getNumRows(),90)
        points=values(flag,'vertex')
        self.assertLessEqual(max(abs(v[0]) for v in points),.5)
        self.assertLessEqual(max(abs(v[1]) for v in points)+.035,.6)
        self.assertGreaterEqual(min(v[2] for v in points),0)
        self.assertLessEqual(max(v[2] for v in points),2.3)

    def test_intro_hides_foundation_until_tiles_have_landed(self):
        from unittest.mock import Mock
        from src.gui.level_intro import LevelIntro
        root=NodePath('IntroScene')
        self.addCleanup(root.removeNode)
        app=SimpleNamespace(static_board_root=root.attachNewNode('static'),
                            dynamic_tile_root=root.attachNewNode('dynamic'),
                            block_root=root.attachNewNode('block'),taskMgr=Mock())
        growth=app.static_board_root.attachNewNode('TempleEdgeGrowth')
        child=growth.attachNewNode('TileTheme-dark');child.hide()
        intro=LevelIntro(app)
        intro.play(2,2)
        self.assertTrue(growth.isHidden())
        intro.finish()
        self.assertFalse(growth.isHidden())
        self.assertTrue(child.isHidden())
        intro.finish()
