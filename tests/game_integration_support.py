"""Real renderer/animation scene graph; no window or graphics driver required."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from panda3d.core import NodePath
from src.gui.controller import GameController, LevelCatalog, LevelEntry
from src.gui.game_scene import GameScene

LEVELS = Path(__file__).resolve().parents[1] / 'levels'

class GameIntegrationCase(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=NodePath('GameIntegrationFixture')
        self.app=SimpleNamespace(taskMgr=None,
            static_board_root=self.root.attachNewNode('static'),
            dynamic_tile_root=self.root.attachNewNode('dynamic'),
            block_root=self.root.attachNewNode('block'))
        self.hud=Mock();self.events=[]
        self.catalog=LevelCatalog(LEVELS)
        self.controller=GameController(catalog=self.catalog,hud=self.hud,
            prepare_scene=lambda board,snapshot:GameScene(self.app,board,snapshot),
            on_event=self.events.append)
        self.assertTrue(self.controller.start())
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.root.removeNode)
        self.addCleanup(self.controller.dispose)

    def load(self,stem):
        index=next(i for i,e in enumerate(self.catalog.entries) if e.level_id==stem)
        self.assertTrue(self.controller.load_level(index),self.controller._status)

    def custom(self,data):
        path=Path(self.temp.name)/f'custom_{len(self.catalog.entries)}.json'
        path.write_text(json.dumps(data),encoding='utf-8')
        self.catalog.entries.append(LevelEntry(path.stem,path,path.stem))
        return len(self.catalog.entries)-1

    def drain(self):
        for _ in range(2000):
            if not self.controller.manager.is_busy:return
            self.controller.manager.advance(2)
        self.fail('Animation/replay failed to become idle.')

    def move(self,action):
        self.assertTrue(self.controller.manual_move(action),self.controller._status)
        self.drain()
