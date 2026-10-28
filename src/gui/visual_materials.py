"""Shared UV textures + capability-checked GLSL materials; no gameplay or tasks.

Assets are original generated PNGs (procedural magma + authored stone albedo). Meshes keep their exact support envelope.
RGBA alpha stores material data (emission, Snow frost or normal-map roughness),
never object transparency. Fixed-function fallback uses opaque RGB albedo.
"""
from functools import lru_cache
import logging
import os
from pathlib import Path
from panda3d.core import Filename, NodePath, Shader, Texture, PNMImage, PTALVecBase4f, LVecBase4f
from src.gui.snow_palette import SNOW_PALETTE

ROOT = Path(__file__).resolve().parents[2] / 'assets'
STATUS = 'FIXED_FUNCTION'
_shader = None
_snow_shader = None
SNOW_STATUS = 'FIXED_FUNCTION'
log = logging.getLogger(__name__)
_quality = PTALVecBase4f.emptyArray(1)
_quality[0] = LVecBase4f(1,0,0,0)


def set_quality(choice):
    from src.gui import visual_quality as q
    effective=q.choose(choice)
    _quality[0]=LVecBase4f(q.DETAIL[effective],_quality[0][1],0,0)
    return effective


def configure(gsg):
    """Compile in the actual context before use, fall back with an explicit log."""
    global _shader, _snow_shader, STATUS, SNOW_STATUS
    from src.gui import visual_quality as q
    q.configure(gsg)
    set_quality(q.CURRENT)
    state.cache_clear()
    texture.cache_clear()
    _shader = None
    _snow_shader = None
    SNOW_STATUS = 'FIXED_FUNCTION'
    STATUS = 'FIXED_FUNCTION'
    if os.environ.get('BLOXORZ_MATERIALS') == 'fixed':
        log.info('Temple materials: fixed-function requested.')
        return STATUS
    if gsg is None or not gsg.getSupportsBasicShaders():
        log.warning('Temple materials: GLSL unavailable; textured fallback enabled.')
        return STATUS
    try:
        candidate = Shader.load(Shader.SL_GLSL, str(ROOT/'shaders/temple.vert'),
                                 str(ROOT/'shaders/temple.frag'))
        if candidate is None:
            raise RuntimeError('Shader source could not be loaded.')
        context = candidate.prepareNow(gsg.getPreparedObjects(), gsg)
        if context is None or candidate.getErrorFlag():
            raise RuntimeError('GLSL compile/link failed; see Panda shader log.')
        _shader = candidate
        STATUS = 'GLSL_DETAIL_EMISSION'
    except Exception:
        log.exception('Temple material shader failed; textured fallback enabled.')
    if _shader is not None:
        try:
            candidate=Shader.load(Shader.SL_GLSL,str(ROOT/'shaders/snow-floor.vert'),
                                  str(ROOT/'shaders/snow-floor.frag'))
            if candidate is None or candidate.prepareNow(gsg.getPreparedObjects(),gsg) is None or candidate.getErrorFlag():
                raise RuntimeError('Snow Floor GLSL compile/link failed.')
            _snow_shader=candidate
            SNOW_STATUS='GLSL_NORMAL_ROUGHNESS_FROST'
        except Exception:
            log.exception('Snow Floor shader failed; opaque textured stone fallback enabled.')
    return STATUS


@lru_cache(maxsize=16)
def texture(name, *, opaque=False):
    tex = Texture(name)
    image = PNMImage()
    if name=='white':
        image=PNMImage(1,1,4)
        image.fill(1,1,1);image.alphaFill(1)
    elif not image.read(Filename.fromOsSpecific(str(ROOT/'materials'/f'{name}.png'))):
        raise RuntimeError(f'Missing visual material asset: {name}')
    if (_shader is None or opaque) and image.hasAlpha():
        image.removeAlpha()
    tex.load(image)
    tex.setMinfilter(Texture.FTLinearMipmapLinear)
    tex.setMagfilter(Texture.FTLinear)
    tex.setAnisotropicDegree(8)
    tex.setWrapU(Texture.WMRepeat); tex.setWrapV(Texture.WMRepeat)
    # Fixed-function must not interpret an emission mask as surface opacity.
    return tex


@lru_cache(maxsize=32)
def state(kind, theme='light', pitch=1.):
    node = NodePath('TempleMaterial')
    if kind=='stone' and theme=='dark':
        node.setTexture(texture('snow-stone',opaque=_snow_shader is None),1)
        if _snow_shader is not None:
            node.setShader(_snow_shader,2)
            node.setShaderInput('quality_settings',_quality)
            node.setShaderInput('normal_roughness_map',texture('snow-stone-normal'))
            node.setShaderInput('floor_pitch',float(pitch))
            node.setShaderInput('snow_variation',(1.,.7,0.,0.))
            node.setShaderInput('frost_color',SNOW_PALETTE['frost'])
            node.setShaderInput('snow_color',SNOW_PALETTE['top'])
            node.setShaderInput('seam_color',SNOW_PALETTE['seam'])
        else:
            # Preserve neutral stone even on a fixed-function backend: global
            # blue moon lights must not undo the Snow palette in this fallback.
            # Baked face/bevel colours still provide top/side/underside depth.
            node.setLightOff(1)
        result=node.getState();node.removeNode();return result
    name = {'stone': 'temple-stone', 'magma':'magma','fragile':'fragile','metal':'metal','glow':'white','flag':'white'}[kind]
    node.setTexture(texture(name), 1)
    if _shader is not None:
        node.setShader(_shader, 2)
        node.setShaderInput('quality_settings',_quality)
        node.setShaderInput('detail_map', texture('magma-height' if kind=='magma' else name if kind=='stone' else 'stone-height'))
        node.setShaderInput('emission_strength', 1.45 if kind=='magma' else .8 if kind=='fragile' else .6 if kind=='glow' else .12 if kind=='flag' else 0.)
        node.setShaderInput('emission_color_mode',float(kind in ('glow','flag')))
        node.setShaderInput('motion_parameters',(0.,0.,0.,0.))
        node.setShaderInput('detail_strength', 1.8 if kind=='magma' else 0. if kind in ('glow','flag') else 1.2)
        node.setShaderInput('night_material', float(theme=='dark'))
    result = node.getState()
    node.removeNode()
    return result


def apply(node, kind, theme='light', *, pitch=1.):
    """Bake state per Geom so combining meshes preserves the material contract."""
    material = state(kind,theme,pitch)
    for i in range(node.getNumGeoms()):
        node.setGeomState(i,node.getGeomState(i).compose(material))
    return node


def flag_motion(node, *, origin, width, pitch):
    """Only cloth Geoms deform; pole and all gameplay meshes stay rigid."""
    apply(node,'flag')
    if _shader is not None:
        holder=NodePath('FlagMotion')
        holder.setShaderInput('motion_parameters',(origin,width,.035*pitch,1.))
        for i in range(node.getNumGeoms()):
            node.setGeomState(i,node.getGeomState(i).compose(holder.getState()))
        holder.removeNode()
    return node


class TempleAtmosphere:
    """One presentation-owned clock for cosmetic cloth, no actor/state mutation."""
    def __init__(self, app):
        self._manager=getattr(app,'taskMgr',None)
        self._task=None
        self.elapsed=0.
        if self._manager is not None:
            self._task=self._manager.add(self._update,'TempleAtmosphere')

    def _update(self, task):
        from panda3d.core import ClockObject
        self.elapsed+=max(0.,min(.1,ClockObject.getGlobalClock().getDt()))
        v=_quality[0]
        _quality[0]=LVecBase4f(v[0],self.elapsed,v[2],v[3])
        return task.cont

    def dispose(self):
        if self._task is not None:
            self._manager.remove(self._task)
        self._task=self._manager=None
