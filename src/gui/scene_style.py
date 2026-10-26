
"""Matte materials, an unlit image backdrop and verified framebuffer AA state.

Backdrop images:
    assets/backgrounds/night.png -> dark theme
    assets/backgrounds/day.png   -> light theme

If an image is missing, a two-colour gradient is used.
"""

import math
from pathlib import Path

from panda3d.core import (
    AntialiasAttrib,
    BitMask32,
    Filename,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    Material,
    MaterialAttrib,
    Texture,
)


SHADOW_MASK = BitMask32.bit(29)

GRADIENTS = {
    "light": ((241, 244, 247), (231, 239, 245)),
    "dark": ((8, 12, 32), (30, 44, 84)),
}

ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "backgrounds"
BACKGROUND_NAMES = {"light": "day", "dark": "night"}

FLOOR_TINT = {
    "light": (1.0, 0.90, 0.68, 1.0),
    "dark": (0.80, 0.80, 1.0, 1.0),
}

BLOCK_TINT = {
    "light": (1.0, 1.0, 1.0, 1.0),
    "dark": (1.0, 1.0, 1.0, 1.0),
}

BLOCK_THEME = "light"
TILE_THEME = "light"


def _normalise_theme(theme):
    return theme if theme in ("light", "dark") else "light"


def sync_block_theme(block_root):
    """Show only the block mesh variant matching BLOCK_THEME."""
    if block_root is None or block_root.isEmpty():
        return

    for name in ("light", "dark"):
        found = block_root.findAllMatches(f"**/BlockTheme-{name}")
        if name == BLOCK_THEME:
            found.show()
        else:
            found.hide()


def apply_block_theme(block_root, theme):
    """Update the active block theme and synchronise existing nodes."""
    global BLOCK_THEME
    BLOCK_THEME = _normalise_theme(theme)
    sync_block_theme(block_root)




def sync_tile_theme(dynamic_root):
    """Show only tile variants matching TILE_THEME.

    Search the common ancestor of the static and dynamic scene branches,
    because goal tiles are created under static content.
    """
    if dynamic_root is None or dynamic_root.isEmpty():
        return

    # Find the highest ancestor containing this scene's tile variants.
    # The search starts from the parent because dynamic_root may be nested.
    search_root = dynamic_root
    while not search_root.getParent().isEmpty():
        search_root = search_root.getParent()

    for name in ("light", "dark"):
        matches = search_root.findAllMatches("**/TileTheme-" + name)
        if name == TILE_THEME:
            matches.show()
        else:
            matches.hide()


def apply_tile_theme(dynamic_root, theme):
    """Set the active tile theme and synchronise existing tile variants."""
    global TILE_THEME

    TILE_THEME = theme if theme in ("light", "dark") else "light"
    sync_tile_theme(dynamic_root)


def _restore(node, attribute_type, value):
    if not node.isEmpty():
        if value is None:
            node.clearAttrib(attribute_type.getClassType())
        else:
            node.setAttrib(value)


def _find_image(theme):
    name = BACKGROUND_NAMES.get(theme, "day")
    for ext in (".png", ".jpg", ".jpeg"):
        path = ASSET_DIR / (name + ext)
        if path.is_file():
            return path
    return None


class SceneStyle:
    """Apply presentation states without editing vertices or mesh origins."""

    def __init__(
        self,
        static_root,
        block_root,
        camera,
        *,
        multisamples=0,
        antialiasing=True,
    ):
        self._camera = camera
        self._theme = "light"
        self._fit = None
        self._states = []
        self._background = None
        self._image_aspect = None
        self._textures = {}
        self.aa_status = "DISABLED"

        try:
            for node, name, specular, shininess in (
                (static_root, "MatteComposite", 0.025, 12),
                (block_root, "MatteSteelBlue", 0.055, 24),
            ):
                self._states.append(
                    (node, MaterialAttrib, node.getAttrib(MaterialAttrib))
                )
                self._states.append(
                    (node, AntialiasAttrib, node.getAttrib(AntialiasAttrib))
                )

                material = Material(name)
                material.setSpecular((specular, specular, specular, 1))
                material.setShininess(shininess)

                node.setMaterial(material)
                node.setAntialias(
                    AntialiasAttrib.MMultisample
                    if antialiasing and multisamples > 1
                    else AntialiasAttrib.MNone
                )

            if antialiasing:
                self.aa_status = (
                    f"MSAA_{multisamples}X"
                    if multisamples > 1
                    else "UNAVAILABLE"
                )

            self._background = self._make_background()

        except BaseException:
            self.dispose()
            raise

    @staticmethod
    def _gradient_mesh(theme="light"):
        top, bottom = GRADIENTS[theme]

        data = GeomVertexData(
            "PresentationGradient",
            GeomVertexFormat.getV3c4(),
            Geom.UHStatic,
        )
        data.setNumRows(4)

        vertex = GeomVertexWriter(data, "vertex")
        color = GeomVertexWriter(data, "color")

        for x, z in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            vertex.addData3f(x, 1, z)
            rgb = bottom if z < 0 else top
            color.addData4f(*(component / 255 for component in rgb), 1)

        primitive = GeomTriangles(Geom.UHStatic)
        for indices in ((0, 1, 2), (0, 2, 3)):
            primitive.addVertices(*indices)
            primitive.closePrimitive()

        geom = Geom(data)
        geom.addPrimitive(primitive)

        node = GeomNode("PresentationGradient")
        node.addGeom(geom)
        return node

    def _load_texture(self, theme):
        if theme in self._textures:
            return self._textures[theme]

        texture = None
        path = _find_image(theme)

        if path is not None:
            tex = Texture("Backdrop-" + theme)
            if tex.read(Filename.fromOsSpecific(str(path))) and tex.getYSize() > 0:
                tex.setMinfilter(Texture.FTLinearMipmapLinear)
                tex.setMagfilter(Texture.FTLinear)
                tex.setAnisotropicDegree(4)
                tex.setWrapU(Texture.WMClamp)
                tex.setWrapV(Texture.WMClamp)
                texture = tex
        else:
            print(
                f"[SceneStyle] Missing background: "
                f"{ASSET_DIR / (BACKGROUND_NAMES.get(theme, 'day') + '.png')}"
            )

        self._textures[theme] = texture
        return texture

    def _textured_quad(self, texture):
        data = GeomVertexData(
            "PresentationBackdropQuad",
            GeomVertexFormat.getV3t2(),
            Geom.UHDynamic,
        )
        data.setNumRows(4)

        vertex = GeomVertexWriter(data, "vertex")
        uv = GeomVertexWriter(data, "texcoord")

        for x, z, u, v in (
            (-1, -1, 0, 0),
            (1, -1, 1, 0),
            (1, 1, 1, 1),
            (-1, 1, 0, 1),
        ):
            vertex.addData3f(x, 1, z)
            uv.addData2f(u, v)

        primitive = GeomTriangles(Geom.UHStatic)
        for indices in ((0, 1, 2), (0, 2, 3)):
            primitive.addVertices(*indices)
            primitive.closePrimitive()

        geom = Geom(data)
        geom.addPrimitive(primitive)

        node = GeomNode("PresentationBackdrop")
        node.addGeom(geom)

        background = self._camera.attachNewNode(node)
        background.setTexture(texture, 1)
        return background

    def _make_background(self):
        texture = self._load_texture(self._theme)
        self._image_aspect = None

        if texture is not None:
            background = self._textured_quad(texture)
            self._image_aspect = texture.getXSize() / texture.getYSize()
        else:
            background = self._camera.attachNewNode(
                self._gradient_mesh(self._theme)
            )

        background.setLightOff(1)
        background.setShaderOff(1)
        background.setDepthTest(False)
        background.setDepthWrite(False)
        background.setBin("background", 0)
        background.hide(SHADOW_MASK)
        return background

    def _set_cover_uv(self, aspect):
        """Cover the view without distorting the image."""
        image = self._image_aspect
        su, sv = (
            (1.0, image / aspect)
            if aspect > image
            else (aspect / image, 1.0)
        )

        u0, u1 = (1 - su) / 2, (1 + su) / 2
        v0, v1 = (1 - sv) / 2, (1 + sv) / 2

        vdata = self._background.node().modifyGeom(0).modifyVertexData()
        writer = GeomVertexWriter(vdata, "texcoord")

        for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)):
            writer.addData2f(u, v)

    def set_theme(self, theme):
        theme = _normalise_theme(theme)

        if theme == self._theme or self._background is None:
            return

        self._theme = theme
        self._background.removeNode()
        self._background = self._make_background()

        if self._fit is not None:
            self.update_background(self._fit)

    def update_background(self, fit):
        """Cover the frustum behind the fitted envelope."""
        if self._background is None:
            raise RuntimeError("Scene style is disposed.")

        self._fit = fit
        depths = [
            sum(
                (point[i] - fit.position[i]) * fit.forward[i]
                for i in range(3)
            )
            for point in fit.bounds.corners()
        ]

        distance = (max(depths) + fit.far) / 2

        self._background.setPos(0, distance - 1, 0)
        self._background.setScale(
            distance * math.tan(math.radians(fit.horizontal_fov) / 2) * 1.01,
            1,
            distance * math.tan(math.radians(fit.vertical_fov) / 2) * 1.01,
        )

        if self._image_aspect:
            self._set_cover_uv(fit.aspect)

    def dispose(self):
        """Restore owned material and AA attributes."""
        if self._background is not None:
            self._background.removeNode()

        self._background = None
        self._textures.clear()

        for node, kind, value in reversed(self._states):
            _restore(node, kind, value)

        self._states.clear()
