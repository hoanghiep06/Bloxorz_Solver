"""One cached GLSL material family for Emerald/Sapphire switch ornaments only."""
from functools import lru_cache
from pathlib import Path
import logging
import os
from panda3d.core import NodePath,Shader,Filename

ROOT=Path(__file__).resolve().parents[2]/'assets/shaders'
_shader=None
STATUS='FIXED_FUNCTION'


def configure(gsg):
    global _shader,STATUS
    _shader=None;STATUS='FIXED_FUNCTION';state.cache_clear()
    from src.gui.elemental_switches import switch_parts,switch_mesh
    switch_parts.cache_clear();switch_mesh.cache_clear()
    if os.environ.get('BLOXORZ_MATERIALS')=='fixed' or gsg is None or not gsg.getSupportsBasicShaders():return STATUS
    try:
        shader=Shader.load(Shader.SL_GLSL,Filename.fromOsSpecific(str(ROOT/'elemental-switch.vert')),
                           Filename.fromOsSpecific(str(ROOT/'elemental-switch.frag')))
        if shader is None or shader.prepareNow(gsg.getPreparedObjects(),gsg) is None or shader.getErrorFlag():
            raise RuntimeError('Elemental switch shader did not compile/link.')
        _shader=shader;STATUS='GLSL_EMERALD_SAPPHIRE'
    except Exception:logging.getLogger(__name__).exception('Switch shader unavailable; opaque sculpted fallback retained.')
    return STATUS


@lru_cache(maxsize=32)
def state(theme,role,active):
    node=NodePath('ElementalSwitchMaterial')
    if _shader is not None:
        node.setShader(_shader,5)
        node.setShaderInput('elemental_settings',(float(theme=='dark'),float(role),float(active),1.))
        node.setShaderInput('elemental_pulse',(0.,0.,0.,0.))
    else:
        # Colours contain the full identity even without GLSL or bloom.
        node.setLightOff(1)
    result=node.getState();node.removeNode();return result


def apply(mesh,theme,role=0,active=False):
    material=state(theme,role,active)
    for i in range(mesh.getNumGeoms()):mesh.setGeomState(i,mesh.getGeomState(i).compose(material))
    return mesh
