"""Actual sculpted geometry, event-gated VFX, theme lifecycle and Core integration."""
from dataclasses import replace
import math
import unittest
from unittest.mock import Mock,patch
from panda3d.core import GeomVertexReader,NodePath,ShaderAttrib,LightAttrib,Shader
from src.gui.advanced_contracts import SwitchVisualKind as K
from src.gui.advanced_mesh_factory import make_switch_mesh
from src.gui.elemental_switches import switch_parts,switch_icon_polygons,PALETTE,BAR_CENTRES,CRYSTAL_CENTRES
from src.gui.switch_vfx import switch_frame
from src.gui.animation_contracts import EventKind as E,AnimationEvent
from src.gui import switch_materials


def vertices(mesh,column='vertex'):
    values=[]
    for geom in mesh.getGeoms():
        reader=GeomVertexReader(geom.getVertexData(),column)
        while not reader.isAtEnd():values.append(tuple(reader.getData4f() if column=='color' else reader.getData3f()))
    return values


class ElementalGeometryTests(unittest.TestCase):
    def test_both_families_all_switches_fit_tile_with_no_added_support_or_collision(self):
        for theme in ('light','dark'):
            for kind in K:
                for pitch in (.5,1.,2.):
                    mesh=make_switch_mesh(kind,theme=theme,pitch=pitch);v=vertices(mesh)
                    self.assertLessEqual(max(abs(a) for p in v for a in p[:2]),.46*pitch)
                    self.assertGreaterEqual(min(p[2] for p in v),-1e-7)
                    self.assertLessEqual(max(p[2] for p in v),.151*pitch)
                    self.assertEqual(NodePath(mesh).findAllMatches('**/+CollisionNode').getNumPaths(),0)

    def test_emerald_and_sapphire_have_different_geometry_not_only_vertex_colour(self):
        for kind in K:
            self.assertNotEqual(vertices(make_switch_mesh(kind,theme='light')),vertices(make_switch_mesh(kind,theme='dark')))
            self.assertNotEqual(vertices(make_switch_mesh(kind,theme='light'),'color'),vertices(make_switch_mesh(kind,theme='dark'),'color'))

    def test_shared_parts_have_ring_two_long_bars_and_two_separate_faceted_gems(self):
        for theme in ('light','dark'):
            base,ring=switch_parts(K.SOFT,theme);self.assertEqual(len(ring),1)
            self.assertEqual(ring[0].getName(),'EnergyRing')
            base,bars=switch_parts(K.HEAVY,theme);self.assertEqual(len(bars),2)
            for mesh,x in zip(bars,BAR_CENTRES):
                vs=vertices(mesh)
                self.assertAlmostEqual((min(v[0] for v in vs)+max(v[0] for v in vs))/2,x,places=5)
                self.assertGreater(max(v[1] for v in vs)-min(v[1] for v in vs),.50)
            base,gems=switch_parts(K.SPLIT,theme);self.assertEqual(len(gems),2)
            self.assertLess(max(v[0] for v in vertices(gems[0])),min(v[0] for v in vertices(gems[1])))
            for gem in gems:self.assertGreater(len(set(vertices(gem,'normal'))),8)

    def test_material_fallback_is_opaque_and_distinct_active_state(self):
        with patch.object(switch_materials,'_shader',None):
            switch_materials.state.cache_clear()
            for theme in ('light','dark'):
                state=switch_materials.state(theme,2,True)
                self.assertTrue(state.hasAttrib(LightAttrib))
                self.assertFalse(state.hasAttrib(ShaderAttrib))
        for theme in ('light','dark'):
            for kind in K:
                off,on=make_switch_mesh(kind,theme=theme),make_switch_mesh(kind,theme=theme,activated=True)
                self.assertEqual(vertices(off),vertices(on))
                self.assertNotEqual(vertices(off,'color'),vertices(on,'color'))

    def test_shader_family_and_authoritative_active_inputs_bind_without_affecting_other_materials(self):
        shader=Shader.load(Shader.SL_GLSL,str(switch_materials.ROOT/'elemental-switch.vert'),str(switch_materials.ROOT/'elemental-switch.frag'))
        with patch.object(switch_materials,'_shader',shader):
            switch_materials.state.cache_clear()
            for theme in ('light','dark'):
                attr=switch_materials.state(theme,2,True).getAttrib(ShaderAttrib)
                values=attr.getShaderInput('elemental_settings').getVector()
                self.assertEqual(tuple(values),(float(theme=='dark'),2.,1.,1.))
        switch_materials.state.cache_clear()

    def test_guide_uses_same_socket_bar_gem_specs_and_preserves_other_icon_semantics(self):
        from src.gui.mechanics_icons import icon_polygons
        for theme in ('light','dark'):
            for kind in K:
                self.assertEqual(icon_polygons(kind.value.lower()+'_switch',theme),switch_icon_polygons(kind,theme))
                self.assertIn(PALETTE[theme]['energy'],[colour for poly,colour in switch_icon_polygons(kind,theme)])

    def test_guide_faces_come_from_real_themed_mesh_with_moss_or_frost_details(self):
        for theme in ('light','dark'):
            for kind in K:
                mesh=make_switch_mesh(kind,theme=theme)
                xy={tuple(round(a,6) for a in point[:2]) for point in vertices(mesh)}
                polygons=switch_icon_polygons(kind,theme)
                self.assertTrue(all(len(points)==3 for points,colour in polygons))
                self.assertTrue(all(tuple(round(a,6) for a in point) in xy
                    for points,colour in polygons for point in points))
                self.assertIn(PALETTE[theme]['detail'],[colour for points,colour in polygons])
                self.assertIs(polygons,switch_icon_polygons(kind,theme))

    def test_mesh_and_material_cache_reuses_objects_without_per_sample_builds(self):
        for kind in K:
            self.assertEqual(make_switch_mesh(kind),make_switch_mesh(kind))
        self.assertNotEqual(switch_frame(K.SOFT,.4),switch_frame(K.HEAVY,.4))
        self.assertGreater(switch_frame(K.SPLIT,.5).spread,0)


from game_integration_support import GameIntegrationCase
from src.gui.scene_style import apply_tile_theme


class ElementalGameplayTests(GameIntegrationCase):
    def setUp(self):
        super().setUp();apply_tile_theme(self.app.dynamic_tile_root,'light')
        self.audio=Mock();self.app.game_audio=self.audio;self.cues=[]
        self.audio.play_sfx.side_effect=lambda event,**kw:self.cues.append(event)
        self.addCleanup(apply_tile_theme,self.app.dynamic_tile_root,'light')

    def activate(self,stem):
        self.load(stem);self.move('R');self.controller.manual_move('R')
        self.controller.manager.advance(.08)
        return self.controller.manager.surface_layer

    def test_soft_and_heavy_only_confirmed_events_drive_actuators_and_effects(self):
        for stem,kind in (('level_03_soft_bridge',K.SOFT),('level_04_heavy_bridge',K.HEAVY)):
            layer=self.activate(stem)
            self.assertGreater(layer._switch_fx.active,0)
            rig=next(iter(layer._switch_rigs.values()));self.assertEqual(rig.kind,kind)
            self.assertTrue(any(actor.getZ()<0 for holder,actor,i in rig.actuators))
            self.assertTrue(all(root.getZ()==0 for root in rig.roots))
            self.drain();self.assertEqual(self.controller.state.bridges_state,(True,))
            self.assertEqual(layer._switch_fx.active,0)
            self.assertTrue(all(root.isHidden() for root,variants in layer._switch_fx.slots))

    def test_split_switch_marker_alone_cannot_start_charging_or_teleport_audio(self):
        from src.gui.audio_events import animation_cues,AudioEvent
        from src.gui.animation_contracts import AnimationRequest,AnimationKind,as_visual_snapshot
        self.load('level_05_split');self.move('R')
        c=self.controller;c.manual_move('R');request=c.manager._request
        self.assertEqual(request.kind,AnimationKind.ROLL)
        c.manager.advance(.08)
        self.assertEqual(c.manager.surface_layer._switch_fx.active,0)
        self.assertNotIn(AudioEvent.SPLIT_SWITCH,[cue.event for cue in animation_cues(request,c.board_data)])
        c.manager.advance(1)
        self.assertTrue(any(e.kind is E.SPLIT for e in c.manager._request.events))
        c.manager.advance(.15)
        self.assertGreater(c.manager.surface_layer._switch_fx.active,0)
        self.assertEqual(self.cues.count(AudioEvent.SPLIT_SWITCH),1)
        self.assertIsNotNone(c.manager._split_plan)
        self.drain();self.assertEqual(c.moves,2);self.assertTrue(c.state.is_split())

    def test_many_dt_samples_pause_cancel_restart_and_level_change_leave_no_transient_nodes(self):
        layer=self.activate('level_03_soft_bridge');c=self.controller
        count=self.root.findAllMatches('**').getNumPaths();c.manager.pause()
        poses=[n.getTransform() for n in layer._switch_fx.root.findAllMatches('**')]
        c.manager.advance(10)
        self.assertEqual(poses,[n.getTransform() for n in layer._switch_fx.root.findAllMatches('**')])
        c.manager.resume()
        for _ in range(20):
            if not c.manager.is_busy:break
            c.manager.advance(.01)
        self.assertEqual(self.root.findAllMatches('**').getNumPaths(),count)
        c.restart_level();self.assertEqual(layer._switch_fx.active,0)
        self.assertTrue(all(actor.getZ()==0 for rig in layer._switch_rigs.values() for holder,actor,i in rig.actuators))
        old=layer._switch_fx.root;self.load('level_01');self.assertTrue(old.isEmpty())

    def test_mid_animation_and_paused_theme_change_cancel_cosmetics_only_preserving_core(self):
        layer=self.activate('level_03_soft_bridge');c=self.controller;c.manager.pause()
        state,moves,request,progress=c.state,c.moves,c.manager.current_request_id,c.manager.progress
        apply_tile_theme(self.app.dynamic_tile_root,'dark')
        self.assertTrue(all(root.isHidden() for root,variants in layer._switch_fx.slots))
        self.assertEqual((c.state,c.moves,c.manager.current_request_id,c.manager.progress),(state,moves,request,progress))
        c.manager.resume();c.manager.advance(.02)
        self.assertEqual(layer._switch_fx.active,0)
        self.drain();self.assertEqual(c.state.bridges_state,(True,))

    def test_repeated_theme_switches_preserve_state_and_node_resource_count(self):
        self.load('level_11_advanced_sandbox');c=self.controller
        state,moves,snapshot=c.state,c.moves,c.manager.current_snapshot
        count=self.root.findAllMatches('**').getNumPaths()
        for theme in ('dark','light')*15:
            apply_tile_theme(self.app.dynamic_tile_root,theme)
            self.assertEqual((c.state,c.moves,c.manager.current_snapshot),(state,moves,snapshot))
            self.assertEqual(self.root.findAllMatches('**').getNumPaths(),count)
            visible=[n for n in self.app.dynamic_tile_root.findAllMatches('**/TileTheme-'+theme) if not n.isHidden()]
            self.assertTrue(visible)

    def test_heavy_laying_contact_does_not_charge_or_play_pressure_cue(self):
        from src.gui.audio_events import AudioEvent
        index=self.custom({'grid':[[1,5,1,1,7,7,2]],'start':[0,0],'goal':[0,6],
            'bridges':[{'id':1,'cells':[[0,4],[0,5]],'initial_state':False}],
            'switches':[{'cell':[0,1],'type':'heavy','target':1,'action':'open'}]})
        self.assertTrue(self.controller.load_level(index))
        self.controller.manual_move('R');self.controller.manager.advance(.12)
        self.assertEqual(self.controller.manager.surface_layer._switch_fx.active,0)
        self.assertNotIn(AudioEvent.HEAVY_SWITCH,self.cues)
        self.drain();self.assertEqual(self.controller.state.bridges_state,(False,))
        self.assertFalse(self.controller.manager.current_snapshot.activated_switch_ids)

    def test_fps_and_replay_rates_preserve_same_switch_pose_and_committed_result(self):
        for stem,kind in (('level_03_soft_bridge',K.SOFT),('level_04_heavy_bridge',K.HEAVY),('level_05_split',K.SPLIT)):
            expected_pose=expected_state=None
            for fps,rate in ((30,.25),(60,1),(120,4)):
                self.load(stem);c=self.controller;c.set_speed(1);self.move('R');c.manual_move('R')
                if kind is K.SPLIT:c.manager.advance(c.manager._request.duration)  # finish roll; supplied SPLIT starts at zero
                c.set_speed(rate);duration=c.manager._request.duration
                target=.15 if kind is K.SPLIT else .45
                remaining=duration*target/rate
                while remaining>1e-12:
                    dt=min(1/fps,remaining);c.manager.advance(dt);remaining-=dt
                self.assertAlmostEqual(c.manager.progress,target,places=7)
                layer=c.manager.surface_layer
                pose=tuple(tuple(round(v,5) for row in actor.getMat() for v in row)
                    for rig in layer._switch_rigs.values() for holder,actor,i in rig.actuators)
                if expected_pose is None:expected_pose=pose
                self.assertEqual(pose,expected_pose)
                self.drain();self.assertEqual(c.moves,2)
                if expected_state is None:expected_state=c.state
                self.assertEqual(c.state,expected_state)
                self.assertEqual(layer._switch_fx.active,0)

    def test_switch_pool_is_bounded_and_sampling_does_not_create_particles(self):
        layer=self.activate('level_03_soft_bridge')
        self.assertLessEqual(len(layer._switch_fx.slots),3)
        count=layer._switch_fx.root.findAllMatches('**').getNumPaths()
        request=self.controller.manager._request
        for i in range(100):layer.sample(request.before_snapshot,request.events,(i%99)/100)
        self.assertEqual(layer._switch_fx.root.findAllMatches('**').getNumPaths(),count)
        self.assertLessEqual(layer._switch_fx.active,3)
