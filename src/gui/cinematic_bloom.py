"""Small warm-emission bloom after the 3D viewport, before the GUI.

Two bounded offscreen targets. No simulation task. FilterManager's one native
resize subscription is explicitly released, together with both output buffers.
"""
import logging
import os
from panda3d.core import Shader,Texture,ATSNone
from src.gui.visual_materials import ROOT


class CinematicBloom:
    def __init__(self, app):
        self.manager = self.quad = self.extract = None
        self.status = 'UNAVAILABLE'
        self._textures = ()
        if os.environ.get('BLOXORZ_BLOOM') == '0':
            self.status = 'DISABLED'
            return
        from src.gui import visual_materials, visual_quality
        if visual_quality.EFFECTIVE != 'high':
            self.status='DISABLED_QUALITY'
            return
        gsg = app.win.getGsg() if hasattr(app.win,'getGsg') else None
        if gsg is None or visual_materials.STATUS != 'GLSL_DETAIL_EMISSION':
            return
        try:
            shaders=[]
            for name in ('bloom-extract','bloom-composite'):
                shader=Shader.load(Shader.SL_GLSL,str(ROOT/'shaders/bloom.vert'),str(ROOT/'shaders'/f'{name}.frag'))
                if shader is None or shader.prepareNow(gsg.getPreparedObjects(),gsg) is None or shader.getErrorFlag():
                    raise RuntimeError('Bloom GLSL compile failed: '+name)
                shaders.append(shader)
            from direct.filter.FilterManager import FilterManager
            self.manager=FilterManager(app.win,app.cam)
            color,glow=Texture('TempleSceneColor'),Texture('TempleWarmGlow')
            for tex in (color,glow):
                tex.setAutoTextureScale(ATSNone)
                tex.setWrapU(Texture.WMClamp);tex.setWrapV(Texture.WMClamp)
            self._textures=(color,glow)
            self.quad=self.manager.renderSceneInto(colortex=color)
            if self.quad is None:raise RuntimeError('Scene framebuffer unavailable.')
            self.extract=self.manager.renderQuadInto(name='TempleBloom',colortex=glow,div=2)
            if self.extract is None:raise RuntimeError('Bloom framebuffer unavailable.')
            self.extract.setShader(shaders[0]);self.extract.setShaderInput('scene_color',color)
            self.quad.setShader(shaders[1]);self.quad.setShaderInput('scene_color',color)
            self.quad.setShaderInput('glow_color',glow)
            self.manager.accept('window-event', self._window_event)
            self.resize(app.win.getXSize(),app.win.getYSize())
            self.status='ENABLED'
        except Exception:
            logging.getLogger(__name__).exception('Bloom unavailable; retaining textured material emission.')
            self.dispose()
            self.status='UNAVAILABLE'

    def _window_event(self,win):
        if self.manager is not None:
            self.manager.windowEvent(win)
            self.resize(self.manager.win.getXSize(),self.manager.win.getYSize())

    def resize(self,width,height):
        if self.extract is not None:
            self.extract.setShaderInput('scene_size',(float(width),float(height)))
            self.quad.setShaderInput('scene_size',(float(width),float(height)))
            self.extract.setShaderInput('pixel_size',(1/max(1,width),1/max(1,height)))

    def dispose(self):
        if self.manager is not None:
            self.manager.cleanup()
            self.manager.ignoreAll()
            self.manager=None
        for node in (self.quad,self.extract):
            if node is not None:node.removeNode()
        self.quad=self.extract=None
        self._textures=()
