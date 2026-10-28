"""Menu flow: Main -> Levels -> Game, plus Settings and About. DirectGUI widgets on pixel2d.

The 3D scene is the background everywhere: the main menu, settings and About run an
attract-mode solver demo, Level Select keeps the scene still, and the Game screen
hands the scene to the player and shows the HUD.
"""
import math
from dataclasses import dataclass

from direct.gui import DirectGuiGlobals as DGG
from direct.showbase.DirectObject import DirectObject
from panda3d.core import NodePath

from src.gui import ui_theme as ui
from src.gui.ambient import Ambient
from src.gui.layout import Rect
from src.gui.level_intro import LevelIntro
from src.gui.mouse_control import controlled_cells, pick_action, pointer_over_hud
from src.gui.move_arrows import MoveAssistLayer
from src.gui.mechanics_guide import MechanicsGuide
from src.gui.mechanics_focus import MechanicsFocus
from src.gui.profile import star_rating
from src.gui.game_adapter import prepare_level
from src.gui.solver_worker import SolverJob
from src.gui.about_page import build_about


def destroy_items(items):
    from direct.gui.DirectGuiBase import DirectGuiWidget
    for item in reversed(items):
        if isinstance(item, DirectGuiWidget):
            item.destroy()
        elif isinstance(item, NodePath):
            if not item.isEmpty():
                item.removeNode()
        else:
            item.destroy()


class Screen:
    name = ''

    def __init__(self, flow):
        self.flow = flow
        self.root = flow.app.pixel2d.attachNewNode('Screen-' + self.name)
        self.root.hide()
        self.visible = False
        self._owned = []

    def own(self, item):
        self._owned.append(item)
        return item

    def button(self, text, x, y, width, height, command, **options):
        def clicked():
            self.flow.audio.play('click')
            command()
        button = ui.make_button(self.root, text, x, y, width, height, clicked, **options)
        self.own(button.border)
        self.own(button)
        return button

    def label(self, text, size, x, y, **options):
        return self.own(ui.make_label(self.root, text, size, x, y, **options))

    def card(self, x, y, width, height, alpha=.94):
        for frame in ui.make_card(self.root, x, y, width, height, alpha):
            self.own(frame)

    def clear(self):
        destroy_items(self._owned)
        self._owned = []

    def release_later(self):
        """Safe inside widget callbacks: widgets are destroyed on the next frame."""
        items, self._owned = self._owned, []
        if items:
            self.flow.retire(items)

    def build(self, width, height):
        raise NotImplementedError

    def rebuild(self):
        self.clear()
        self.build(*self.flow.size)

    def show(self):
        self.visible = True
        self.rebuild()
        self.root.show()

    def hide(self):
        self.visible = False
        self.root.hide()

    def resize(self):
        if self.visible:
            self.rebuild()

    def dispose(self):
        self.clear()
        self.root.removeNode()


class MainMenu(Screen):
    name = 'main'

    def build(self, width, height):
        left = width * UIFlow.LEFT_SHARE
        self.card(-2, -2, left + 2, height + 4, alpha=1)
        cx = left / 2
        self.label('BLOXORZ', 72, cx, height * .28, align='center')
        self.label('SOLVER', 26, cx, height * .28 + 42, color=ui.MUTED, align='center')
        bw, bh, x, y = 300, 58, cx - 150, height * .46
        self.button('Start', x, y, bw, bh, lambda: self.flow.show('levels'), primary=True, size=26)
        self.button('Settings', x, y + 76, bw, bh, lambda: self.flow.show('settings'), size=26)
        self.button('About', x, y + 152, bw, bh, lambda: self.flow.show('about'), size=26)
        self.button('Quit', x, y + 228, bw, bh, self.flow.app.userExit, size=26)


class AboutPage(Screen):
    name = 'about'

    def build(self,width,height):
        self.content=build_about(self,width,height)


class LevelSelect(Screen):
    """Lưới 4x2 = 8 level mỗi trang; nhiều hơn 8 thì có mũi tên < > để lật trang."""
    name = 'levels'
    COLS, ROWS = 4, 2
    PER_PAGE = COLS * ROWS

    def __init__(self, flow):
        super().__init__(flow)
        self.page = 0

    def show(self):
        count = len(self.flow.catalog)
        last = min(self.flow.controller.level_index, count - 1)
        self.page = last // self.PER_PAGE          # mở đúng trang chứa level vừa chơi
        super().show()

    def _go(self, delta):
        self.page += delta
        self.release_later()                       # an toàn khi đang trong callback nút
        self.build(*self.flow.size)

    def build(self, width, height):
        flow, catalog = self.flow, self.flow.catalog
        count = len(catalog)
        pages = max(1, math.ceil(count / self.PER_PAGE))
        self.page = min(max(self.page, 0), pages - 1)
        first = self.page * self.PER_PAGE
        entries = catalog.entries[first:first + self.PER_PAGE]

        cols, rows = self.COLS, self.ROWS
        gap, pad = 18, 30
        head, foot, side = 130, 70, 110           # tiêu đề / chân trang / chỗ cho mũi tên
        size = max(70, min(120,
                           (height - head - foot - 2 * pad - (rows - 1) * gap) // rows,
                           (width - 2 * pad - 2 * side - (cols - 1) * gap) // cols))
        card_w = cols * size + (cols - 1) * gap + 2 * pad
        card_h = rows * size + (rows - 1) * gap + 2 * pad
        cx0 = (width - card_w) / 2
        cy0 = head + max(0, (height - head - foot - card_h) / 2)

        # Tiêu đề nằm trên cao, ngoài khung level.
        self.label('Select Level', 44, width / 2, 62, align='center')
        ids = [entry.level_id for entry in catalog.entries]
        earned = flow.save.total_stars(ids)
        self.label(f'{earned} / {3 * count} stars', 20, width / 2, 98,
                   color=ui.MUTED, align='center')
        self.button('Back', 30, 30, 120, 48, lambda: flow.show('main'), size=22)

        for i, entry in enumerate(entries):          # không vẽ khung nền: giữ nguyên background 3D
            index = first + i
            x = cx0 + pad + (i % cols) * (size + gap)
            y = cy0 + pad + (i // cols) * (size + gap)
            supported = flow.is_supported(index)
            card = self.button(str(index + 1) if supported else '—', x, y, size, size,
                               lambda n=index: flow.start_level(n), size=int(size * .38),
                               enabled=supported, text_y=.42)
            stars = flow.save.stars_for(entry.level_id)
            for k in range(3):
                self.own(ui.make_star(card, size / 2 + (k - 1) * size * .27, size * .8,
                                      size * .1, on=k < stars))

        if pages > 1:
            ay = cy0 + card_h / 2 - 32
            self.button('<', cx0 - 84, ay, 64, 64, lambda: self._go(-1), size=34,
                        enabled=self.page > 0, primary=self.page > 0)
            self.button('>', cx0 + card_w + 20, ay, 64, 64, lambda: self._go(1), size=34,
                        enabled=self.page < pages - 1, primary=self.page < pages - 1)
            self.label(f'Page {self.page + 1} / {pages}', 20, width / 2, cy0 + card_h + 40,
                       color=ui.MUTED, align='center')


class SettingsScreen(Screen):
    name = 'settings'
    HINTS = {'keyboard': 'Arrow keys or WASD roll the block.',
             'mouse': 'Click around the block to roll. Space switches split cubes.'}

    def build(self, width, height):
        flow, settings = self.flow, self.flow.save.settings
        self._ready = False             # slider callbacks fire during construction
        cw, ch = 560, 690
        x0, y0 = (width - cw) / 2, (height - ch) / 2
        self.card(x0, y0, cw, ch, alpha=.97)
        self.label('Settings', 40, width / 2, y0 + 62, align='center')
        self.label('Controls', 20, x0 + 40, y0 + 105, color=ui.MUTED)
        self._toggles = {}
        for i, (mode, text) in enumerate((('keyboard', 'Keyboard'), ('mouse', 'Mouse'))):
            self._toggles[mode] = self.button(text, x0 + 40 + i * 250, y0 + 120, 230, 44,
                                              lambda m=mode: self._set_mode(m))
        self._hint = self.label('', 17, width / 2, y0 + 190, color=ui.MUTED, align='center')
        self._apply_mode(settings.control_mode)

        self.label('Appearance', 20, x0 + 40, y0 + 225, color=ui.MUTED)
        for i, (theme, text) in enumerate((('light', 'Light'), ('dark', 'Dark'))):
            self.button(text, x0 + 40 + i * 250, y0 + 240, 230, 44,
                        lambda t=theme: self._set_theme(t), primary=settings.theme == theme)

        self.label('Graphics quality',20,x0+40,y0+320,color=ui.MUTED)
        self._quality_buttons={}
        for i,(quality,text) in enumerate((('auto','Auto'),('high','High'),('balanced','Balanced'),('low','Low'))):
            self._quality_buttons[quality]=self.button(text,x0+40+i*123,y0+336,112,42,
                lambda q=quality:self._set_quality(q),primary=settings.quality==quality,size=18)
        from src.gui import visual_quality
        self._quality_hint=self.label(visual_quality.CURRENT.capitalize()+': '+visual_quality.EFFECTIVE.capitalize()+' / changes apply immediately',14,
            width/2,y0+402,color=ui.MUTED,align='center')

        self.label('Music', 20, x0 + 40, y0 + 435, color=ui.MUTED)
        (self._music_buttons, self._music_slider,
         self._music_text) = self._audio_row(
            x0, cw, y0 + 450, settings.music, self._set_music,
            settings.music_volume, self._on_music_volume, self._music_released)

        self.label('Sound effects', 20, x0 + 40, y0 + 530, color=ui.MUTED)
        (self._sfx_buttons, self._sfx_slider,
         self._sfx_text) = self._audio_row(
            x0, cw, y0 + 545, settings.sfx, self._set_sfx,
            settings.sfx_volume, self._on_sfx_volume, self._sfx_released)

        self.button('Back', x0 + (cw - 200) / 2, y0 + ch - 76, 200, 50,
                    lambda: flow.show('main'), primary=True)
        self._ready = True

    def _audio_row(self, x0, cw, y, enabled, set_enabled, volume, on_volume, on_release):
        """On / Off buttons + volume slider + percent text on one row."""
        buttons = {}
        for i, (value, text) in enumerate(((True, 'On'), (False, 'Off'))):
            buttons[value] = self.button(text, x0 + 40 + i * 105, y, 95, 50,
                                         lambda v=value: set_enabled(v), primary=enabled == value)
        percent = self.label(f'{round(volume * 100)}%', 20, x0 + cw - 40, y + 32, align='right')
        slider = self.own(ui.make_slider(self.root, x0 + 265, y + 19, 190, 12, volume, on_volume))
        slider.thumb.bind(DGG.B1RELEASE, on_release)
        return buttons, slider, percent

    def _apply_mode(self, mode):
        for key, button in self._toggles.items():
            ui.style_button(button, primary=key == mode)
        self._hint['text'] = self.HINTS[mode]

    def _set_mode(self, mode):
        self.flow.save.settings.control_mode = mode
        self.flow.save.save()
        self._apply_mode(mode)

    def _set_music(self, enabled):
        self.flow.save.settings.music = enabled
        self.flow.save.save()
        self.flow.audio.set_music_enabled(enabled)
        for value, button in self._music_buttons.items():
            ui.style_button(button, primary=value == enabled)

    def _set_sfx(self, enabled):
        self.flow.save.settings.sfx = enabled
        self.flow.save.save()
        self.flow.audio.set_sfx_enabled(enabled)
        for value, button in self._sfx_buttons.items():
            ui.style_button(button, primary=value == enabled)

    def _set_quality(self, quality):
        self.flow.app.dashboard.set_quality(quality)
        self.flow.save.settings.quality=quality
        self.flow.save.save()
        from src.gui import visual_quality
        for name,button in self._quality_buttons.items():
            ui.style_button(button,primary=name==quality)
        self._quality_hint['text']=quality.capitalize()+': '+visual_quality.EFFECTIVE.capitalize()+' / changes apply immediately'

    def _set_theme(self, theme):
        self.flow.save.settings.theme = theme
        self.flow.save.save()
        ui.set_theme(theme)
        self.flow.apply_scene_theme(theme)
        self.flow.ambient.set_theme(theme)
        self.flow.app.dashboard.hud.restyle()
        self.release_later()                 # old widgets are destroyed next frame
        self.build(*self.flow.size)

    def _on_music_volume(self):
        if not self._ready:
            return
        value = float(self._music_slider['value'])
        self.flow.save.settings.music_volume = value
        self.flow.audio.set_music_volume(value)
        self._music_text['text'] = f'{round(value * 100)}%'

    def _on_sfx_volume(self):
        if not self._ready:
            return
        value = float(self._sfx_slider['value'])
        self.flow.save.settings.sfx_volume = value
        self.flow.audio.set_sfx_volume(value)
        self._sfx_text['text'] = f'{round(value * 100)}%'

    def _music_released(self, event=None):
        self.flow.save.save()

    def _sfx_released(self, event=None):
        self.flow.save.save()
        self.flow.audio.play('click')     # nghe thử mức tiếng hiệu ứng


@dataclass(frozen=True)
class ResultDialog:
    """Captured outcome; resizing only redraws it, without recording progress."""
    kind: str
    moves: int
    stars: int = 0
    par: int | None = None
    next_level: int | None = None


class GameScreen(Screen):
    """The HUD belongs to HudShell; this screen hosts win/failure dialogs."""
    name = 'game'

    def __init__(self, flow):
        super().__init__(flow)
        self._result = None

    @property
    def result_visible(self):
        return self._result is not None

    def build(self, width, height):
        if self._result is not None:
            if self._result.kind == 'win':
                self._build_win(width, height, self._result)
            else:
                self._build_fail(width, height, self._result)

    def show(self):
        self.visible = True
        self.hide_result()
        self.root.show()

    def hide(self):
        self.visible = False
        self.hide_result()
        self.root.hide()

    def hide_result(self):
        self._result = None
        self.release_later()

    def show_result(self):
        flow, controller = self.flow, self.flow.controller
        entry = flow.catalog[controller.level_index]
        par = flow.save.par.get(entry.level_id)
        stars = star_rating(controller.moves, par)
        if controller.used_guide:          # watched a solution: capped at 1 star
            stars = 1
        flow.save.record(entry.level_id, controller.moves, stars)
        flow.save.save()
        nxt = controller.level_index + 1
        has_next = nxt < len(flow.catalog) and flow.is_supported(nxt)
        self._result = ResultDialog('win', controller.moves, stars, par, nxt if has_next else None)
        self.release_later()
        self.build(*flow.size)

    def _build_win(self, width, height, result):
        flow, controller = self.flow, self.flow.controller
        cw, ch = 400, 310
        x, y = (width - cw) / 2, (height - ch) / 2
        self.card(x, y, cw, ch, alpha=.97)
        self.label('Level Complete!', 36, width / 2, y + 62, align='center')
        for k in range(3):
            self.own(ui.make_star(self.root, width / 2 + (k - 1) * 74, y + 125, 30, on=k < result.stars))
        detail = f'Moves {result.moves}' + (f'     Par {result.par}' if result.par is not None else '')
        self.label(detail, 20, width / 2, y + 190, color=ui.MUTED, align='center')
        bw, gap = 112, 10
        bx, by = x + (cw - (3 * bw + 2 * gap)) / 2, y + 222
        self.button('Next', bx, by, bw, 52,
                    lambda: flow.start_level(result.next_level) if result.next_level is not None else None,
                    primary=True, enabled=result.next_level is not None)
        self.button('Retry', bx + bw + gap, by, bw, 52, controller.restart_level)
        self.button('Levels', bx + 2 * (bw + gap), by, bw, 52, lambda: flow.show('levels'))

    def show_fail(self):
        """Khung thua: block rơi khỏi bản đồ. Retry hoặc Exit về chọn màn."""
        flow, controller = self.flow, self.flow.controller
        self._result = ResultDialog('fail', controller.moves)
        self.release_later()
        self.build(*flow.size)

    def _build_fail(self, width, height, result):
        flow, controller = self.flow, self.flow.controller
        cw, ch = 400, 250
        x, y = (width - cw) / 2, (height - ch) / 2
        self.card(x, y, cw, ch, alpha=.97)
        self.label('Level Failed', 36, width / 2, y + 62, align='center')
        self.label(f'Moves {result.moves}', 20, width / 2, y + 108,
                   color=ui.MUTED, align='center')
        bw, gap = 150, 12
        bx, by = x + (cw - (2 * bw + gap)) / 2, y + 150
        self.button('Retry', bx, by, bw, 52, controller.restart_level, primary=True)
        self.button('Exit', bx + bw + gap, by, bw, 52, lambda: flow.show('levels'))


class UIFlow:
    LEFT_SHARE = .4          # main menu: buttons on the left 40%, scene on the right

    def __init__(self, app, controller, catalog, save, audio, attract):
        self.app, self.controller, self.catalog = app, controller, catalog
        self.save, self.audio, self.attract = save, audio, attract
        self.size = (app.win.getXSize(), app.win.getYSize())
        self.name = None
        self._supported, self._disposed = {}, False
        self._later_tasks = set()
        self._retired = []
        self._par_job = self._par_task = None

        ui.set_theme(save.settings.theme)
        self.apply_scene_theme(save.settings.theme)
        # Created before the screens so the particles sit underneath the menus.
        self.ambient = Ambient(app.pixel2d, app.taskMgr, lambda: self.size)
        self.ambient.set_theme(ui.CURRENT)

        self.screens = {cls.name: cls(self)
                        for cls in (MainMenu, AboutPage, LevelSelect, SettingsScreen, GameScreen)}
        self.intro = LevelIntro(app, self._intro_done)
        import os
        self.arrows = MoveAssistLayer(app, controller, self._arrows_visible,
            enabled=os.environ.get('BLOXORZ_MOVE_ASSIST_DEBUG')=='1')
        self.mechanics = MechanicsGuide(app.pixel2d,on_change=self._mechanics_changed)
        app.mechanics_guide=self.mechanics
        self.mechanics.apply_layout(*self.size)
        self.mechanics_focus=MechanicsFocus(app,controller,app.presentation.camera,self.mechanics,
            views=getattr(app,'game_views',None),allowed=self._mechanics_focus_allowed,
            safe_rect=self._mechanics_safe_rect)

        self._listener = DirectObject()
        self._listener.accept('window-event', self._window_event)
        self._listener.accept('escape', self.back)
        self._listener.accept('mouse1', self._click)
        self._listener.accept('m', self.toggle_music)      # phím tắt bật/tắt nhạc
        hud = app.dashboard.hud
        hud.restyle()
        hud.bind_action('Exit', self._with_click(lambda: self.show('levels')))
        hud.bind_action('Restart', self._with_click(controller.restart_level))
        hud.bind_action('Guide', self._with_click(self.toggle_guide))

    # ---------------------------------------------------------------- helpers
    def _with_click(self, command):
        def run():
            self.audio.play('click')
            command()
        return run

    def later(self, function):
        def run(task):
            self._later_tasks.discard(task)
            if not self._disposed:
                function()
            return task.done
        task = self.app.taskMgr.doMethodLater(0.0, run, f'ui-later-{id(self)}')
        self._later_tasks.add(task)

    def retire(self, items):
        self._retired.append(items)
        def release():
            if items in self._retired:
                destroy_items(items)
                self._retired.remove(items)
        self.later(release)

    def is_supported(self, index):
        """Validate both Advanced board data and the initial Core snapshot."""
        entry = self.catalog[index]
        if entry.level_id not in self._supported:
            try:
                from src.core.board import Board
                prepare_level(Board(str(entry.path)), level_id=entry.level_id, session_id='capability')
                self._supported[entry.level_id] = True
            except Exception:
                self._supported[entry.level_id] = False
        return self._supported[entry.level_id]

    def _ensure_par(self):
        """Optimal move count (BFS) is the 3-star threshold; cached in the save file."""
        entry = self.catalog[self.controller.level_index]
        if entry.level_id in self.save.par:
            return
        self._cancel_par()
        try:
            self._par_job = SolverJob(self.controller.board, 'src.solvers.bfs', 'BFSSolver')
        except Exception:
            return
        def poll(task):
            try:
                outcome = self._par_job.poll()
            except Exception:
                self._par_job.cancel()
                self._par_job = self._par_task = None
                return task.done
            if outcome is None:
                return task.cont
            self._par_job = self._par_task = None
            ok, result = outcome
            if ok and result.success:
                self.save.par[entry.level_id] = result.solution_length
                self.save.save()
            return task.done
        self._par_task = self.app.taskMgr.add(poll, f'ParSolver-{id(self)}')

    def _cancel_par(self):
        if self._par_task is not None:
            self.app.taskMgr.remove(self._par_task)
        if self._par_job is not None:
            self._par_job.cancel()
        self._par_job = self._par_task = None

    def apply_scene_theme(self, theme):
        """Recolour backdrop, lights, floor, block and special tiles for the theme."""
        if hasattr(self, 'mechanics'):
            self.mechanics.apply_theme(theme)
        from src.gui.scene_style import (SceneStyle, FLOOR_TINT, BLOCK_TINT,
                                         apply_block_theme, apply_tile_theme)
        from src.gui.scene_lighting import SceneLightingController
        try:
            values = list(vars(self.app.presentation).values())
        except TypeError:
            return
        for value in values:
            if isinstance(value, (SceneStyle, SceneLightingController)):
                value.set_theme(theme)
        self.app.static_board_root.setColorScale(*FLOOR_TINT.get(theme, FLOOR_TINT['light']))
        self.app.block_root.setColorScale(*BLOCK_TINT.get(theme, BLOCK_TINT['light']))
        apply_block_theme(self.app.block_root, theme)
        apply_tile_theme(self.app.dynamic_tile_root, theme)

    # ---------------------------------------------------------------- intro / arrows
    def _intro_done(self):
        self.controller.input_enabled = self.name == 'game'

    def _arrows_visible(self):
        c = self.controller
        return (self.name == 'game' and c.input_enabled
                and not self.intro.active and not self.screens['game'].result_visible
                and c.manager is not None and c.is_idle and c.phase == 'READY'
                and not c.guide_active and self.app.dashboard.viewport.layout.supported)

    # ---------------------------------------------------------------- navigation
    def _left_region(self, width, height):
        left = int(width * self.LEFT_SHARE)
        return Rect(left, 0, width - left, height)

    @staticmethod
    def _full_region(width, height):
        return Rect(0, 0, width, height)

    def _mechanics_focus_allowed(self):
        tutorial=getattr(self.app,'game_tutorial',None)
        return (self.name=='game' and not self.intro.active
                and not (tutorial is not None and tutorial.visible))

    def _mechanics_safe_rect(self):
        width,height=self.size
        card=self.mechanics.layout.card
        right=card.x-24 if card else width-self.mechanics.reserved_width-32
        if self.screens['game'].result_visible:right=min(right,(width-400)/2-24)
        return (32,140,max(80,right-32),max(80,height-250))

    def _mechanics_changed(self):
        # Guide owns its overlay layout. No camera/viewport refit on card clicks.
        pass

    def _game_region(self,width,height):
        self.mechanics.apply_layout(width,height)
        available=max(1,width-self.mechanics.reserved_width)
        self.app.presentation.style.set_background_canvas(width/height,available/width)
        return Rect(0,0,available,height)

    def show(self, name):
        if self._disposed:
            return
        if self.name!=name and self.name in ('main','about') and name in ('main','about'):
            # These pages share one preview. Do not cancel/reset its running
            # solver, restart attract mode or refit its unchanged viewport.
            self.screens[self.name].hide()
            self.name=name
            self.screens[name].show()
            return
        self.intro.finish(notify=False)
        if self.name:
            self.screens[self.name].hide()
        self.name = name
        game = name == 'game'
        self.mechanics.set_visible(game)
        if not game:self.app.presentation.style.set_background_canvas()
        if not game:
            self.mechanics_focus.reset()
            self._cancel_par()
            self.controller.cancel_guide()      # leaving the level drops any guide state
        self.ambient.set_intensity(.45 if game else 1.0)
        self.ambient.show()
        hud, viewport = self.app.dashboard.hud, self.app.dashboard.viewport
        hud.root.show() if game else hud.root.hide()
        viewport.set_region_override({'main': self._left_region, 'about': self._left_region, 'levels': self._full_region,
                                      'settings': self._full_region,
                                      'game': self._game_region}.get(name))
        self.controller.input_enabled = game
        self.controller.keyboard_enabled = self.save.settings.control_mode == 'keyboard'
        hud.set_guide_visible(False)
        if game:
            hud.restyle()
            self.attract.stop()
        elif name == 'levels':
            self.attract.stop()                 # background stays, animation stops
            self.controller.restart_level()     # put the block back at the start
        else:
            self.attract.start()
        scene = (self.app.static_board_root, self.app.dynamic_tile_root, self.app.block_root)
        for node in scene:                      # chọn level: ẩn block + map 3D phía sau
            node.hide() if name == 'levels' else node.show()
        self.audio.start_music()
        self.screens[name].show()

    def back(self):
        # One Escape dispatcher: closing help must not also leave the level.
        tutorial = getattr(self.app, 'game_tutorial', None)
        if tutorial is not None and tutorial.visible:
            tutorial.hide()
            return
        target = {'levels': 'main', 'settings': 'main', 'about': 'main', 'game': 'levels'}.get(self.name)
        if target:
            self.show(target)

    def toggle_music(self):
        """Phím M: bật/tắt nhạc ở mọi màn hình và lưu lại lựa chọn."""
        on = self.audio.toggle_music()
        self.save.settings.music = on
        self.save.save()
        if self.name == 'settings':
            self.screens['settings'].rebuild()   # cập nhật nút On/Off

    def start_level(self, index):
        if not self.is_supported(index):
            return
        self.mechanics_focus.reset()
        self._cancel_par()
        self.attract.stop()
        self.screens['game'].hide_result()
        if self.controller.load_level(index):
            self._ensure_par()
            self.show('game')
            board = self.controller.board_data
            self.intro.play(board.rows, board.cols)
            self.controller.input_enabled = False      # unlocked by _intro_done

    def toggle_guide(self):
        hud = self.app.dashboard.hud
        if hud.guide_open:
            self.controller.deselect_solver()
            hud.set_guide_visible(False)
        else:
            if self.intro.active:
                self.intro.finish()
            hud.set_guide_visible(True)

    def _finish_guide(self):
        """Solution finished: preserve the solved state and show the result."""
        self.controller.end_guide()
        self.app.dashboard.hud.set_guide_visible(False)
        if self.name == 'game' and self.controller.phase == 'GOAL':
            self.screens['game'].show_result()

    # ---------------------------------------------------------------- events
    def on_game_event(self, name):
        if name == 'restart':
            self.mechanics_focus.reset(restore=True)
            self.screens['game'].hide_result()
            return
        if self.name != 'game':
            return                       # attract mode stays silent
        if name in ('roll', 'goal', 'fall'):
            self.audio.play(name)
        if name == 'fall':
            self.screens['game'].show_fail()            # khung thua: Retry / Exit
        if name == 'goal':
            if self.controller.guide_active:
                session, revision = self.controller.session_id, self.controller.revision
                def finish_current():
                    if (self.controller.session_id == session
                            and self.controller.revision == revision
                            and self.controller.phase == 'GOAL'):
                        self._finish_guide()
                self.later(finish_current)
            else:
                self.screens['game'].show_result()      # the player finished it

    def _window_event(self, window):
        if window != self.app.win:
            return
        size = (window.getXSize(), window.getYSize())
        if size[0] > 0 and size[1] > 0 and size != self.size:
            self.size = size
            self.mechanics.apply_layout(*size)
            if self.name:
                self.screens[self.name].resize()

    def _click(self):
        controller = self.controller
        if (self.name != 'game' or not controller.input_enabled
                or self.save.settings.control_mode != 'mouse'
                or self.intro.active
                or self.screens['game'].result_visible or controller.manager is None
                or controller.manager.is_busy or controller.phase != 'READY'):
            return
        # A DirectGUI click must not also become a move on the board behind it.
        from direct.gui.DirectGuiBase import DirectGuiWidget
        region = self.app.mouseWatcherNode.getOverRegion()
        if (region is not None and region.getName() in DirectGuiWidget.guiDict
                or pointer_over_hud(self.app)):
            return
        action = pick_action(self.app, self.app.dashboard.viewport.region,
                             self.app.presentation.camera.current_fit,
                             controlled_cells(controller.state),
                             controller.board_data.rows, controller.board_data.cols)
        if action:
            controller.manual_move(action)

    def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        self._cancel_par()
        for task in self._later_tasks:
            self.app.taskMgr.remove(task)
        self._later_tasks.clear()
        for items in self._retired:
            destroy_items(items)
        self._retired.clear()
        self._listener.ignoreAll()
        self.attract.stop()
        self.intro.finish(notify=False)
        self.arrows.dispose()
        self.mechanics_focus.dispose()
        self.mechanics.dispose()
        if getattr(self.app,'mechanics_guide',None) is self.mechanics:
            del self.app.mechanics_guide
        self.ambient.dispose()
        for screen in self.screens.values():
            screen.dispose()
