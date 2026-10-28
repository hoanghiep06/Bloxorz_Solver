"""Snow-only material isolation, true shader bindings and unchanged support."""
import hashlib
import math
import unittest
from unittest.mock import patch

from panda3d.core import (ColorScaleAttrib,GeomVertexReader,LightAttrib,NodePath,PNMImage,
                          Point3,Shader,ShaderAttrib,TexMatrixAttrib,Texture,TextureAttrib,TextureStage)
from src.gui import visual_materials as materials
from src.gui.mesh_factory import make_floor_mesh
from src.gui.temple_environment import vary_tile


def column(mesh,name):
    data=mesh.getGeom(0).getVertexData();reader=GeomVertexReader(data,name);out=[]
    while not reader.isAtEnd():
        out.append(tuple(reader.getData2f() if name=='texcoord' else reader.getData3f()))
    return out


def texture_name(state):
    attr=state.getAttrib(TextureAttrib)
    return attr.getOnTexture(attr.getOnStage(0)).getName()


class SnowFloorMaterialTests(unittest.TestCase):
    def tearDown(self):
        materials.state.cache_clear();materials.texture.cache_clear()

    def test_light_floor_vertex_buffer_is_identical_to_pre_upgrade_baseline(self):
        mesh=make_floor_mesh(theme='light')
        raw=bytes(mesh.getGeom(0).getVertexData().getArray(0).getHandle().getData())
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
            '0bc449b5b248c9295d52aa5487e1fa6fbcd70cadf90284bc446fc5e05ca6a81e')
        self.assertEqual(texture_name(mesh.getGeomState(0)),'temple-stone')

    def test_snow_has_exact_same_support_vertices_normals_and_uvs_at_three_pitches(self):
        for pitch in (.5,1.,2.5):
            light=make_floor_mesh(theme='light',pitch=pitch)
            dark=make_floor_mesh(theme='dark',pitch=pitch)
            for name in ('vertex','normal','texcoord'):
                self.assertEqual(column(light,name),column(dark,name))
            self.assertAlmostEqual(max(p[2] for p in column(dark,'vertex')),0,places=6)
            self.assertAlmostEqual(min(p[2] for p in column(dark,'vertex')),-.18*pitch,places=6)

    def test_snow_palette_gives_distinct_top_bevel_side_and_underside(self):
        palette=materials.SNOW_PALETTE
        self.assertGreater(sum(palette['bevel'][:3]),sum(palette['top'][:3]))
        self.assertGreater(sum(palette['top'][:3]),sum(palette['side'][:3])*1.8)
        self.assertGreater(sum(palette['side'][:3]),sum(palette['underside'][:3]))
        reader=GeomVertexReader(make_floor_mesh(theme='dark').getGeom(0).getVertexData(),'color')
        colors=[]
        while not reader.isAtEnd():colors.append(tuple(reader.getData4f()))
        for key in ('top','bevel','side','underside'):
            self.assertTrue(any(max(abs(a-b) for a,b in zip(c,palette[key]))<.005 for c in colors))

    def test_snow_texture_is_mipmapped_cached_and_not_applied_to_specials(self):
        self.assertEqual(texture_name(materials.state('stone','dark')),'snow-stone')
        for kind,asset in (('magma','magma'),('fragile','fragile'),('metal','metal'),('glow','white')):
            self.assertEqual(texture_name(materials.state(kind,'dark')),asset)
        tex=materials.texture('snow-stone')
        self.assertEqual(tex,materials.texture('snow-stone'))
        self.assertEqual(tex.getMinfilter(),Texture.FTLinearMipmapLinear)
        self.assertEqual((tex.getXSize(),tex.getYSize()),(1024,1024))

    def test_packed_normal_map_contains_unit_normals_and_rough_stone(self):
        image=PNMImage();self.assertTrue(image.read(str(materials.ROOT/'materials/snow-stone-normal.png')))
        normals=[]
        for y in range(0,image.getYSize(),47):
            for x in range(0,image.getXSize(),43):
                n=[v*2-1 for v in image.getXel(x,y)]
                self.assertAlmostEqual(math.sqrt(sum(v*v for v in n)),1,delta=.02)
                self.assertGreater(n[2],.5);self.assertGreater(image.getAlpha(x,y),.8)
                normals.append(tuple(round(v,2) for v in n))
        self.assertGreater(len(set(normals)),20)

    def test_shader_binds_real_normal_roughness_frost_and_pitch_without_touching_jungle(self):
        shader=Shader.load(Shader.SL_GLSL,str(materials.ROOT/'shaders/snow-floor.vert'),
                           str(materials.ROOT/'shaders/snow-floor.frag'))
        self.assertIsNotNone(shader)
        with patch.object(materials,'_snow_shader',shader),patch.object(materials,'_shader',shader):
            materials.state.cache_clear();materials.texture.cache_clear()
            state=make_floor_mesh(theme='dark',pitch=2.).getGeomState(0)
            attr=state.getAttrib(ShaderAttrib)
            self.assertEqual(attr.getShader(),shader)
            self.assertEqual(attr.getShaderInput('normal_roughness_map').getTexture().getName(),'snow-stone-normal')
            self.assertAlmostEqual(attr.getShaderInput('floor_pitch').getVector()[0],2.)
            self.assertNotEqual(materials.state('stone','light'),state)

    def test_snow_fallback_stays_opaque_even_when_common_shader_is_available(self):
        common=Shader.load(Shader.SL_GLSL,str(materials.ROOT/'shaders/temple.vert'),
                           str(materials.ROOT/'shaders/temple.frag'))
        with patch.object(materials,'_snow_shader',None),patch.object(materials,'_shader',common):
            materials.state.cache_clear();materials.texture.cache_clear()
            state=materials.state('stone','dark')
            tex=state.getAttrib(TextureAttrib).getOnTexture(TextureStage.getDefault())
            self.assertEqual(tex.getNumComponents(),3)
            self.assertFalse(state.hasAttrib(ShaderAttrib))
            self.assertTrue(state.getAttrib(LightAttrib).hasAllOff())

    def test_instance_rotation_is_deterministic_and_does_not_mutate_shared_prototype(self):
        root=NodePath('qa');self.addCleanup(root.removeNode)
        prototype=make_floor_mesh(theme='dark');before=column(prototype,'texcoord')
        instances=[]
        for _ in range(2):
            floor=root.attachNewNode('Floor');floor.attachNewNode('TileTheme-dark').attachNewNode(prototype)
            floor.attachNewNode('TileTheme-light');vary_tile(floor,3,5);instances.append(floor)
        a,b=instances
        self.assertEqual(a.getState(),b.getState())
        self.assertEqual(a.find('TileTheme-dark').getState(),b.find('TileTheme-dark').getState())
        self.assertEqual(column(prototype,'texcoord'),before)
        self.assertTrue(a.find('TileTheme-light').getState().isEmpty())
        rotations=set()
        for col in range(12):
            floor=root.attachNewNode('OtherFloor');dark=floor.attachNewNode('TileTheme-dark')
            vary_tile(floor,3,col);rotations.add(dark.getTexRotate(TextureStage.getDefault()))
        self.assertGreater(len(rotations),1)

    def test_repeated_mesh_builds_reuse_cached_material_not_per_snapshot_textures(self):
        materials.state.cache_clear();materials.texture.cache_clear()
        first=make_floor_mesh(theme='dark').getGeomState(0)
        cache=materials.texture.cache_info().misses
        for _ in range(25):self.assertEqual(make_floor_mesh(theme='dark').getGeomState(0),first)
        self.assertEqual(materials.texture.cache_info().misses,cache)

    def test_per_tile_frost_parameters_override_geom_defaults_without_editing_shared_state(self):
        shader=Shader.load(Shader.SL_GLSL,str(materials.ROOT/'shaders/snow-floor.vert'),
                           str(materials.ROOT/'shaders/snow-floor.frag'))
        with patch.object(materials,'_snow_shader',shader):
            materials.state.cache_clear()
            prototype=make_floor_mesh(theme='dark');state=prototype.getGeomState(0)
            root=NodePath('floor');self.addCleanup(root.removeNode)
            dark=root.attachNewNode('TileTheme-dark');dark.attachNewNode(prototype)
            vary_tile(root,3,5)
            combined=dark.getNetState().compose(state).getAttrib(ShaderAttrib)
            chosen=combined.getShaderInput('snow_variation').getVector()
            self.assertNotEqual(tuple(chosen),tuple(state.getAttrib(ShaderAttrib).getShaderInput('snow_variation').getVector()))
            self.assertGreaterEqual(chosen[1],.45);self.assertLessEqual(chosen[1],.95)
            self.assertEqual(prototype.getGeomState(0),state)

    def test_snow_atlas_is_eighty_percent_coverage_with_soft_transitions(self):
        image=PNMImage();self.assertTrue(image.read(str(materials.ROOT/'materials/snow-stone.png')))
        alpha=[image.getAlpha(x,y) for y in range(0,1024,4) for x in range(0,1024,4)]
        classified=sum(a>=.5 for a in alpha)/len(alpha)
        self.assertAlmostEqual(classified,.80,delta=.006)
        self.assertTrue(.78<sum(alpha)/len(alpha)<.83)
        self.assertGreater(sum(.05<a<.95 for a in alpha)/len(alpha),.10)

    def test_actual_uv_transforms_keep_sixty_four_tiles_within_coverage_target(self):
        image=PNMImage();self.assertTrue(image.read(str(materials.ROOT/'materials/snow-stone.png')))
        mesh=make_floor_mesh(theme='dark')
        uvs=[uv for uv,n in zip(column(mesh,'texcoord'),column(mesh,'normal')) if n[2]>.999]
        u0,u1=min(uv[0] for uv in uvs),max(uv[0] for uv in uvs)
        v0,v1=min(uv[1] for uv in uvs),max(uv[1] for uv in uvs)
        root=NodePath('qa');self.addCleanup(root.removeNode);coverage=[]
        for row in range(8):
            for col in range(8):
                floor=root.attachNewNode('Floor');dark=floor.attachNewNode('TileTheme-dark')
                vary_tile(floor,row,col)
                mat=dark.getNetState().getAttrib(TexMatrixAttrib).getTransform(TextureStage.getDefault()).getMat()
                samples=[]
                for y in range(40):
                    for x in range(40):
                        p=mat.xformPoint(Point3(u0+(x+.5)*(u1-u0)/40,v0+(y+.5)*(v1-v0)/40,0))
                        samples.append(image.getAlpha(int((p.x%1)*1024),int((p.y%1)*1024)))
                fraction=sum(a>=.5 for a in samples)/len(samples)
                self.assertTrue(.75<=fraction<=.85,(row,col,fraction))
                coverage.append(fraction)
        self.assertAlmostEqual(sum(coverage)/len(coverage),.80,delta=.02)

    def test_snow_has_silver_dunes_and_visible_stone_not_flat_white_fill(self):
        image=PNMImage();self.assertTrue(image.read(str(materials.ROOT/'materials/snow-stone.png')))
        snow=[];rock=[]
        for y in range(0,1024,11):
            for x in range(0,1024,13):
                if image.getAlpha(x,y)>.98:snow.append(tuple(image.getXel(x,y)))
                if image.getAlpha(x,y)<.02:rock.append(tuple(image.getXel(x,y)))
        self.assertTrue(snow and rock)
        self.assertGreater(sum(v[0] for v in snow)/len(snow),.84)
        self.assertLess(sum(v[0] for v in rock)/len(rock),.75)
        self.assertGreater(max(v[0] for v in snow)-min(v[0] for v in snow),.025)
        self.assertGreater(len(set(snow)),100)

    def test_snow_does_not_inherit_legacy_jungle_darkening_multiplier(self):
        floor=NodePath('qa');self.addCleanup(floor.removeNode)
        dark=floor.attachNewNode('TileTheme-dark');light=floor.attachNewNode('TileTheme-light')
        vary_tile(floor,3,5)
        self.assertEqual(tuple(dark.getNetState().getAttrib(ColorScaleAttrib).getScale()),(1,1,1,1))
        self.assertEqual(light.getNetState().getAttrib(ColorScaleAttrib),floor.getAttrib(ColorScaleAttrib))


if __name__=='__main__':unittest.main()
