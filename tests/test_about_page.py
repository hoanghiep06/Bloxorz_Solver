"""About data, font coverage, navigation without resetting preview, and lifetime."""
import threading,unittest,tempfile
from pathlib import Path
from unittest.mock import patch,Mock
from src.gui import about_page as about
from test_gui_stage3_6_integration import SceneFixture

VIDEO='https://www.youtube.com/watch?v=AbCdEf123_-'

class AboutDataTests(unittest.TestCase):
    def test_team_exactly_as_supplied_and_vietnamese_glyphs_exist(self):
        self.assertEqual(about.TEAM,(('24122015','Mai Hoàng Hiệp'),('24122022','Nguyễn Hoài Phước'),
            ('24122035','Phan Nguyễn Gia Huy'),('24122009','Phan Thế Phong'),('24122051','Nguyễn Đức Tài')))
        font=about.about_font()
        for char in ''.join(name for _,name in about.TEAM):
            if char!=' ':self.assertEqual(type(font.getGlyph(ord(char))).__name__,'DynamicTextGlyph',char)
        self.assertIsNone(about.DEMO_YOUTUBE_URL)

    def test_video_url_formats_and_invalid_hosts(self):
        for url in (VIDEO,'https://youtu.be/AbCdEf123_-','https://youtube.com/shorts/AbCdEf123_-'):
            self.assertTrue(about.valid_demo_url(url))
        for url in (None,'','https://example.com/video','javascript:alert(1)',
                    'https://youtube.com.evil.test/watch?v=AbCdEf123_-',
                    'https://user@youtube.com/watch?v=AbCdEf123_-',
                    'https://youtube.com/watch?v=bad','https://youtube.com:bad/watch?v=AbCdEf123_-',
                    'https://youtube.com/playlist?list=123',VIDEO+'\n'):
            self.assertFalse(about.valid_demo_url(url))

    def test_browser_launch_is_off_the_gui_thread_and_missing_url_does_nothing(self):
        entered=threading.Event();release=threading.Event();threads=[]
        def browser(url,new):
            self.assertEqual(url,VIDEO);self.assertEqual(new,2)
            threads.append(threading.get_ident());entered.set();release.wait(2)
        with patch.object(about.webbrowser,'open',side_effect=browser) as opened:
            self.assertIsNone(about.open_demo(None));opened.assert_not_called()
            worker=about.open_demo(VIDEO)
            try:
                self.assertTrue(entered.wait(1));self.assertTrue(worker.is_alive())
                self.assertNotEqual(threads[0],threading.get_ident())
            finally:release.set();worker.join(2)

class AboutWidgetTests(SceneFixture):
    def setUp(self):
        super().setUp()
        from src.gui.controller import LevelCatalog
        from src.gui.profile import SaveData
        from src.gui.screens import UIFlow
        from gui_task_support import TaskManagerDouble
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app.render=self.host;self.app.userExit=Mock();self.app.taskMgr=TaskManagerDouble()
        self.before=self.counts()
        self.c=Mock(level_index=0,guide_active=False,manager=None,phase='READY')
        self.flow=UIFlow(self.app,self.c,LevelCatalog(Path(__file__).resolve().parents[1]/'levels'),
                         SaveData(Path(self.temp.name)/'save.json'),Mock(),Mock())
        self.addCleanup(self.flow.dispose)

    def counts(self):
        from direct.gui.DirectGuiBase import DirectGuiWidget
        from direct.showbase.MessengerGlobal import messenger
        return (len(DirectGuiWidget.guiDict),
                sum(len(messenger.whoAccepts(e) or {}) for e in messenger.getEvents()))

    def test_main_order_callbacks_and_same_settings_about_dimensions(self):
        self.flow.show('main');screen=self.flow.screens['main']
        buttons=[w for w in screen._owned if hasattr(w,'dims')]
        self.assertEqual([b['text'] for b in buttons],['Start','Settings','About','Quit'])
        self.assertEqual(buttons[1].dims,buttons[2].dims)
        buttons[2]['command']();self.assertEqual(self.flow.name,'about')
        self.flow.screens['about'].content['back']['command']();self.assertEqual(self.flow.name,'main')
        self.flow.back();self.assertEqual(self.flow.name,'main')
        self.flow.screens['main'].rebuild()
        buttons=[w for w in self.flow.screens['main']._owned if hasattr(w,'dims')]
        buttons[0]['command']();self.assertEqual(self.flow.name,'levels')
        self.flow.show('main');buttons=[w for w in self.flow.screens['main']._owned if hasattr(w,'dims')]
        buttons[1]['command']();self.assertEqual(self.flow.name,'settings')
        self.flow.show('main');buttons=[w for w in self.flow.screens['main']._owned if hasattr(w,'dims')]
        buttons[3]['command']();self.app.userExit.assert_called_once()

    def test_about_back_does_not_reset_preview_controller_or_attract(self):
        self.flow.show('main');self.c.reset_mock();self.flow.attract.reset_mock()
        region=self.app.dashboard.viewport.region.getDimensions()
        self.flow.show('about');self.flow.back()
        self.assertEqual(self.flow.name,'main')
        self.c.cancel_guide.assert_not_called();self.c.restart_level.assert_not_called();self.c.load_level.assert_not_called()
        self.flow.attract.start.assert_not_called();self.flow.attract.stop.assert_not_called()
        self.assertEqual(self.app.dashboard.viewport.region.getDimensions(),region)

    def test_about_fits_all_target_sizes_themes_and_keeps_demo_disabled(self):
        from src.gui import ui_theme as ui
        from direct.gui import DirectGuiGlobals as DGG
        self.flow.show('about');page=self.flow.screens['about']
        for theme in ('light','dark'):
            ui.set_theme(theme)
            for size in ((1024,720),(1280,720),(1366,768),(1920,1080)):
                self.flow.size=size;page.rebuild();content=page.content
                self.assertLess(content['bottom'],size[1]-16)
                self.assertEqual(content['watch']['state'],DGG.DISABLED)
                self.assertEqual(content['status']['text'],'Coming soon')
                for pair,record in zip(content['team'],about.TEAM):
                    self.assertEqual(tuple(w['text'] for w in pair),record)
                for label in content['labels']:
                    text=label.component('text0').textNode
                    scale=label['text_scale'][0]
                    # Text metrics + widget translation, relative to the menu root.
                    self.assertGreaterEqual(label.getX()+text.getLeft()*scale,-1)
                    self.assertLessEqual(label.getX()+text.getRight()*scale,content['left']-12)
                    self.assertGreaterEqual(-label.getZ()-text.getTop()*scale,0)
                    self.assertLessEqual(-label.getZ()-text.getBottom()*scale,size[1]-16)

    def test_configured_demo_enables_watch_and_dispatches_only_valid_url(self):
        from direct.gui import DirectGuiGlobals as DGG
        with patch.object(about,'DEMO_YOUTUBE_URL',VIDEO),patch.object(about,'open_demo') as launch:
            self.flow.show('about');page=self.flow.screens['about']
            self.assertEqual(page.content['watch']['state'],DGG.NORMAL)
            page.content['watch']['command']();launch.assert_called_once_with(VIDEO)

    def test_repeated_about_menu_resize_and_theme_cycles_release_widgets(self):
        from src.gui import ui_theme as ui
        self.flow.show('about');self.flow.show('main');baseline=self.counts()
        for _ in range(20):
            self.flow.show('about');page=self.flow.screens['about']
            ui.set_theme('dark');page.rebuild();ui.set_theme('light');page.rebuild()
            self.flow.show('main');self.app.taskMgr.tick(deferred_only=True)
            self.assertEqual(self.counts(),baseline)
        self.flow.dispose();self.assertEqual(self.counts(),self.before)
