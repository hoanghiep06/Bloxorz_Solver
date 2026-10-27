"""Guide layout, real DirectGUI lifecycle and read-only game integration."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from src.gui.mechanics_guide_data import MECHANICS,BY_ID
from src.gui.mechanics_guide import MechanicsGuide,guide_layout
from src.gui.layout import Rect
from test_gui_stage3_6_integration import SceneFixture


class GuideLayoutTests(unittest.TestCase):
    def test_all_items_fit_four_required_sizes_clear_of_header_and_metrics(self):
        for width,height in ((1024,720),(1280,720),(1366,768),(1920,1080)):
            for selected in (None,*(m.id for m in MECHANICS)):
                for card_height in (190,260,310):
                    layout=guide_layout(width,height,selected,card_height)
                    for rect in (layout.rail,layout.card):
                        if rect is None:continue
                        self.assertGreaterEqual(rect.y,136)
                        self.assertLess(rect.bottom,height-94)
                        self.assertLessEqual(rect.right,width-20)
                        self.assertGreater(rect.x,0)
                    if layout.card:self.assertFalse(layout.card.intersects(layout.rail))
                    left=width-layout.reserved
                    self.assertLess(left,(layout.card or layout.rail).x)
                    self.assertGreater(left,600)

    def test_undersized_window_hides_instead_of_clipping(self):
        self.assertIsNone(guide_layout(900,600,'goal'))
        self.assertIsNone(guide_layout(0,0))

    def test_registry_has_seven_unique_short_english_entries(self):
        self.assertEqual(len(BY_ID),7)
        self.assertEqual(len(set(m.id for m in MECHANICS)),7)
        self.assertIn('whole block upright',BY_ID['goal'].description)
        self.assertIn('small',BY_ID['heavy_switch'].note)
        self.assertIn('Space',BY_ID['split_switch'].note)
        for m in MECHANICS:
            self.assertLess(len(m.description),150)
            self.assertLess(len(m.note),100)


class GuideWidgetTests(SceneFixture):
    def setUp(self):
        super().setUp()
        self.on_change=Mock()
        self.guide=MechanicsGuide(self.app.pixel2d,on_change=self.on_change)
        self.addCleanup(self.guide.dispose)
        self.guide.apply_layout(1280,720);self.guide.set_visible(True)

    def counts(self):
        from direct.gui.DirectGuiBase import DirectGuiWidget
        from direct.showbase.MessengerGlobal import messenger
        return (len(DirectGuiWidget.guiDict),sum(len(messenger.whoAccepts(e) or {}) for e in messenger.getEvents()))

    def test_default_is_rail_only_then_replace_toggle_and_close(self):
        g=self.guide
        self.assertIsNone(g.selected);self.assertTrue(g.card.isHidden())
        self.assertEqual(set(g.buttons),set(BY_ID))
        self.assertFalse(g.root.isHidden())
        for key in BY_ID:
            g.buttons[key]['command']()
            self.assertEqual(g.selected,key)
            self.assertEqual(g.title['text'],BY_ID[key].name)
            self.assertEqual(g.body['text'],BY_ID[key].description)
            self.assertFalse(g.card.isHidden())
            self.assertEqual(g.large_icon.getNumChildren(),1)
        g.buttons['void']['command']();self.assertIsNone(g.selected)
        self.assertTrue(g.card.isHidden())
        g.show_mechanic('goal');g.close_button['command']()
        self.assertIsNone(g.selected)

    def test_theme_changes_in_place_preserve_card_and_semantic_accents(self):
        g=self.guide;g.show_mechanic('split_switch')
        widgets=self.counts();buttons=tuple(g.buttons.values())
        for theme in ('dark','light')*10:
            g.apply_theme(theme)
            self.assertEqual(g.selected,'split_switch')
            self.assertEqual(tuple(g.buttons.values()),buttons)
            self.assertEqual(self.counts(),widgets)
            self.assertAlmostEqual(g._icons['soft_switch'].getColor()[0],0x4e/255,delta=1/1024)  # Panda ColorAttrib quantization
            self.assertFalse(g.card.isHidden())
        self.assertEqual(g._ink[:3],tuple(v/255 for v in (0x18,0x32,0x4b)))

    def test_resize_keeps_selected_card_and_passive_click_guard(self):
        g=self.guide;g.show_mechanic('split_switch')
        self.app.mechanics_guide=g
        self.app.mouseWatcherNode=Mock()
        from src.gui.mouse_control import pointer_over_hud
        for width,height in ((1024,720),(1366,768),(1920,1080),(1280,720)):
            self.app.win.width,self.app.win.height=width,height
            g.apply_layout(width,height)
            rect=g.layout.card
            x,y=rect.x+20,rect.y+90
            self.app.mouseWatcherNode.hasMouse.return_value=True
            self.app.mouseWatcherNode.getMouse.return_value=(2*x/width-1,1-2*y/height)
            self.assertTrue(pointer_over_hud(self.app))
            self.assertTrue(g.contains_pointer_pixels(x,y))
            self.assertFalse(g.contains_pointer_pixels(100,300))
            self.assertEqual(g.selected,'split_switch')
        g.set_visible(False)
        self.assertFalse(pointer_over_hud(self.app))
        self.assertFalse(g.contains_pointer_pixels(x,y))

    def test_repeated_open_resize_close_keeps_widget_and_node_counts_bounded(self):
        g=self.guide;g.show_mechanic('goal')
        count=self.counts();nodes=g.root.findAllMatches('**').getNumPaths()
        for i in range(30):
            g.show_mechanic(MECHANICS[i%7].id)
            g.apply_layout(1024 if i%2 else 1280,720)
            g.close_card()
            self.assertEqual(self.counts(),count)
            self.assertLessEqual(g.root.findAllMatches('**').getNumPaths(),nodes)

    def test_guide_does_not_mutate_board_snapshot_or_install_tasks_keys(self):
        import copy
        before=copy.deepcopy(vars(self.board));snapshot=self.snapshot
        camera=self.app.presentation.camera.current_fit
        for item in MECHANICS:self.guide.show_mechanic(item.id)
        self.guide.close_card();self.guide.apply_theme('dark')
        self.assertEqual(vars(self.board),before)
        self.assertEqual(self.snapshot,snapshot)
        self.assertEqual(self.app.presentation.camera.current_fit,camera)

    def test_dispose_removes_only_owned_widgets_events_and_is_idempotent(self):
        g=self.guide
        from direct.gui.DirectGui import DirectButton
        other=DirectButton(parent=self.app.pixel2d,text='Foreign',command=lambda:None)
        self.addCleanup(other.destroy)
        foreign_id=other.guiId
        owned=[w.guiId for w in g._widgets]
        g.dispose();g.dispose()
        from direct.gui.DirectGuiBase import DirectGuiWidget
        self.assertTrue(g.root.isEmpty())
        self.assertFalse(any(key in DirectGuiWidget.guiDict for key in owned))
        self.assertIn(foreign_id,DirectGuiWidget.guiDict)

    def test_unknown_id_is_rejected_without_altering_selection(self):
        self.guide.show_mechanic('bridge')
        with self.assertRaises(KeyError):self.guide.show_mechanic('unknown')
        self.assertEqual(self.guide.selected,'bridge')
