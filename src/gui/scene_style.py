"""Matte materials, an unlit camera backdrop and verified framebuffer AA state."""

import math

from panda3d.core import (
    AntialiasAttrib, BitMask32, Geom, GeomNode, GeomTriangles, GeomVertexData,
    GeomVertexFormat, GeomVertexWriter, Material, MaterialAttrib,
)


SHADOW_MASK = BitMask32.bit(29)
GRADIENTS = {'light': ((241, 244, 247), (231, 239, 245)),   # (trên, dưới)
             'dark': ((8, 12, 32), (30, 44, 84))}

def _restore(node, attribute_type, value):
    if not node.isEmpty():
        if value is None:
            node.clearAttrib(attribute_type.getClassType())
        else:
            node.setAttrib(value)


class SceneStyle:
    """Apply presentation states without editing vertices, transforms or mesh origins."""

    def __init__(self, static_root, block_root, camera, *, multisamples=0, antialiasing=True):
        self._camera, self._theme, self._fit = camera, 'light', None
        self._states = []
        self._background = None
        self.aa_status = 'DISABLED'
        try:
            for node, name, specular, shininess in (
                (static_root, 'MatteComposite', .025, 12),
                (block_root, 'MatteSteelBlue', .055, 24),
            ):
                self._states.append((node, MaterialAttrib, node.getAttrib(MaterialAttrib)))
                self._states.append((node, AntialiasAttrib, node.getAttrib(AntialiasAttrib)))
                material = Material(name)
                # Leave ambient/diffuse UNSET: vertex colors remain their source.
                material.setSpecular((specular, specular, specular, 1))
                material.setShininess(shininess)
                node.setMaterial(material)
                node.setAntialias(AntialiasAttrib.MMultisample if antialiasing and multisamples > 1
                                  else AntialiasAttrib.MNone)
            if antialiasing:
                self.aa_status = f'MSAA_{multisamples}X' if multisamples > 1 else 'UNAVAILABLE'
            self._background = self._make_background()
        except BaseException:
            self.dispose()
            raise

    @staticmethod
    def _gradient_mesh(theme='light'):
        top, bottom = GRADIENTS[theme]
        data = GeomVertexData('PresentationGradient', GeomVertexFormat.getV3c4(), Geom.UHStatic)
        data.setNumRows(4)
        vertex, color = GeomVertexWriter(data, 'vertex'), GeomVertexWriter(data, 'color')
        for x, z in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            vertex.addData3f(x, 1, z)
            color.addData4f(*((c / 255 for c in (bottom if z < 0 else top))), 1)
        primitive = GeomTriangles(Geom.UHStatic)
        for indices in ((0, 1, 2), (0, 2, 3)):
            primitive.addVertices(*indices)
            primitive.closePrimitive()
        geom = Geom(data)
        geom.addPrimitive(primitive)
        node = GeomNode('PresentationGradient')
        node.addGeom(geom)
        return node

    def _make_background(self):
        background = self._camera.attachNewNode(self._gradient_mesh(self._theme))
        background.setLightOff(1)
        background.setShaderOff(1)
        background.setDepthTest(False)
        background.setDepthWrite(False)
        background.setBin('background', 0)
        background.hide(SHADOW_MASK)
        return background

    def set_theme(self, theme):
        theme = theme if theme in GRADIENTS else 'light'
        if theme == self._theme or self._background is None:
            return
        self._theme = theme
        self._background.removeNode()
        self._background = self._make_background()
        if self._fit is not None:
            self.update_background(self._fit)

    def update_background(self, fit):
        """Cover the frustum behind the fitted envelope, outside its camera bounds."""
        if self._background is None:
            raise RuntimeError('Scene style is disposed.')
        self._fit = fit
        depths = [sum((p[i] - fit.position[i]) * fit.forward[i] for i in range(3))
                  for p in fit.bounds.corners()]
        distance = (max(depths) + fit.far) / 2
        # Geometry's forward coordinate is already +1; parent Y shift is distance-1.
        self._background.setPos(0, distance - 1, 0)
        self._background.setScale(distance * math.tan(math.radians(fit.horizontal_fov)/2) * 1.01,
                                  1, distance * math.tan(math.radians(fit.vertical_fov)/2) * 1.01)

    def dispose(self):
        """Restore only owned material/AA attributes; preserve foreign lights and nodes."""
        if self._background is not None:
            self._background.removeNode()
        self._background = None
        for node, kind, value in reversed(self._states):
            _restore(node, kind, value)
        self._states.clear()
