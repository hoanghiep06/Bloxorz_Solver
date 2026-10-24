"""Panda3D application foundation; run with ``python -m src.gui.app``."""

from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFileData


WINDOW_TITLE = "Bloxorz Solver — Renderer Foundation"
WINDOW_SIZE = (1280, 720)
BACKGROUND_RGB = (241 / 255, 244 / 255, 247 / 255)


class BloxorzPreviewApp(ShowBase):
    """Own the single application window and the empty renderer scene roots."""

    def __init__(self, *, audio: bool = False) -> None:
        audio_line = "" if audio else "audio-library-name null\n"
        loadPrcFileData("bloxorz-foundation", f"window-title {WINDOW_TITLE}\n"
                                              f"win-size {WINDOW_SIZE[0]} {WINDOW_SIZE[1]}\nfullscreen false\n"
                                              "win-fixed-size false\n" + audio_line)
        super().__init__(windowType="onscreen")
        self.disableMouse()
        self.setBackgroundColor(*BACKGROUND_RGB, 1.0)

        self.scene_root = self.render.attachNewNode("SceneRoot")
        self.static_board_root = self.scene_root.attachNewNode("StaticBoardRoot")
        self.dynamic_tile_root = self.scene_root.attachNewNode("DynamicTileRoot")
        self.block_root = self.scene_root.attachNewNode("BlockRoot")
        self.effects_root = self.scene_root.attachNewNode("EffectsRoot")

    def destroy(self) -> None:
        """Detach our scene before Panda3D releases its window and tasks."""
        scene_root = getattr(self, "scene_root", None)
        if scene_root is not None:
            scene_root.removeNode()
        super().destroy()


def main() -> None:
    """Run one host, cleaning up even when the engine loop raises."""
    app = BloxorzPreviewApp()
    try:
        app.run()
    finally:
        app.destroy()


if __name__ == "__main__":
    main()
