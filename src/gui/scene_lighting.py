"""Owned ambient/key/fill rig and an optional, capability-checked shadow profile."""

import math

from panda3d.core import (
    AmbientLight, DepthOffsetAttrib, DirectionalLight, Point3, RenderState, ShaderAttrib, Vec3,
)

from src.gui.scene_style import SHADOW_MASK, _restore


class SceneLightingController:
    """Light one scene subtree without taking ownership of renderer/host nodes."""

    def __init__(self, scene_root, fit, *, shadows=False, gsg=None):
        self._scene = scene_root
        self._rig = scene_root.attachNewNode('PresentationLights')
        self._shader_before = scene_root.getAttrib(ShaderAttrib)
        self._shader_owned = False
        self._lights = []
        self.shadow_status = 'DISABLED'
        self._fit = fit
        try:
            ambient = AmbientLight('PresentationAmbient')
            ambient.setColor((.42, .43, .44, 1))
            self.ambient = self._rig.attachNewNode(ambient)
            key = DirectionalLight('PresentationKey')
            key.setColor((.55, .55, .54, 1))
            self.key = self._rig.attachNewNode(key)
            fill = DirectionalLight('PresentationFill')
            fill.setColor((.10, .115, .13, 1))
            self.fill = self._rig.attachNewNode(fill)
            self._lights = [self.ambient, self.key, self.fill]
            for node in self._lights:
                scene_root.setLight(node)
            self.fit_bounds(fit)
            self.set_shadows(shadows, gsg=gsg)
        except BaseException:
            self.dispose()
            raise

    def fit_bounds(self, fit):
        """Place the key above-left in camera basis and bound its orthographic shadow lens."""
        if self._rig is None:
            raise RuntimeError('Lighting is disposed.')
        self._fit = fit
        # Source positions, not ray directions: negative right = screen-left.
        source = Vec3(*( -.6*fit.right[i] + .65*fit.up[i] - .9*fit.forward[i] for i in range(3)))
        source.normalize()
        diagonal = math.sqrt(sum((b-a)**2 for a, b in zip(fit.bounds.minimum, fit.bounds.maximum)))
        target = Point3(*fit.target)
        self.key.setPos(target + source * (diagonal + 5))
        self.key.lookAt(target)
        fill_source = Vec3(*( .8*fit.right[i] + .1*fit.up[i] - .2*fit.forward[i] for i in range(3)))
        self.fill.setPos(target + fill_source * (diagonal + 5))
        self.fill.lookAt(target)
        corners = [self.key.getRelativePoint(self._scene, Point3(*p)) for p in fit.bounds.corners()]
        x0, x1 = min(p.x for p in corners), max(p.x for p in corners)
        z0, z1 = min(p.z for p in corners), max(p.z for p in corners)
        depth0, depth1 = min(p.y for p in corners), max(p.y for p in corners)
        lens = self.key.node().getLens()
        lens.setFilmSize((x1-x0)*1.10, (z1-z0)*1.10)
        lens.setFilmOffset((x0+x1)/2, (z0+z1)/2)
        lens.setNearFar(max(.01, depth0*.5), depth1 + max(1, diagonal*.1))
        self.key.node().setScene(self._scene)
        self.key.node().setCameraMask(SHADOW_MASK)

    def set_shadows(self, enabled, *, gsg=None):
        """Best effort: preserve basic lighting when depth textures/shaders are unavailable.

        ENABLED means requested/enabled in the engine, not a claim of visual PASS.
        Callers must validate the image on target hardware.
        """
        if self._rig is None:
            raise RuntimeError('Lighting is disposed.')
        if enabled and (gsg is None or not gsg.getSupportsBasicShaders() or not gsg.getSupportsDepthTexture()):
            self.set_shadows(False)
            self.shadow_status = 'UNAVAILABLE'
            return False
        if enabled:
            self.key.node().setShadowCaster(True, 2048, 2048)
            # Negative Panda depth offset pushes the caster depth away from the
            # light, avoiding self-shadow acne. Positive offset darkens receivers.
            self.key.node().setInitialState(RenderState.make(DepthOffsetAttrib.make(-2)))
            self._scene.setShaderAuto()
            self._shader_owned = True
            self.shadow_status = 'ENABLED_UNVERIFIED'
        else:
            self.key.node().setShadowCaster(False)
            if self._shader_owned:
                _restore(self._scene, ShaderAttrib, self._shader_before)
            self._shader_owned = False
            self.shadow_status = 'DISABLED'
        return bool(enabled)

    def dispose(self):
        """Clear only these lights, release shadow buffers and restore prior shader state."""
        if self._rig is None:
            return
        if hasattr(self, 'key'):
            self.key.node().setShadowCaster(False)
        if not self._scene.isEmpty():
            for light in self._lights:
                self._scene.clearLight(light)
            if self._shader_owned:
                _restore(self._scene, ShaderAttrib, self._shader_before)
        self._rig.removeNode()
        self._rig = self._scene = self._fit = None
        self._shader_before = None
        self.ambient = self.key = self.fill = None
        self._lights.clear()
