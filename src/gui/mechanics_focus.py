"""Read-only mechanic locator and a cancellable lease of the existing camera."""
from dataclasses import dataclass,replace
import math
from panda3d.core import ClockObject,LineSegs,TransparencyAttrib,Vec3
from src.gui.geometry_math import cell_to_world
from src.gui.animation_math import smoothstep,lerp,slerp
from src.gui.advanced_contracts import SwitchVisualKind
from src.gui.mechanics_guide_data import BY_ID

FOCUS_DURATION=.55
HIGHLIGHT_DURATION=1.1


@dataclass(frozen=True)
class FocusTarget:
    mechanic: str
    identity: str
    cells: tuple
    cell: tuple


def mechanic_targets(board,key):
    """Use immutable Basic/Advanced definitions, never pixels or actor poses."""
    if key not in BY_ID:raise KeyError(key)
    result=[]
    def target(identity,cells):
        cells=tuple(sorted(cells))
        if not cells:return
        mean=tuple(sum(p[i] for p in cells)/len(cells) for i in (0,1))
        cell=min(cells,key=lambda p:((p[0]-mean[0])**2+(p[1]-mean[1])**2,p))
        result.append(FocusTarget(key,str(identity),cells,cell))
    if key=='goal':
        for cell in board.goal_cells:target(f'goal:{cell}',(cell,))
    elif key=='bridge':
        for bridge in getattr(board,'bridges',()):target(bridge.bridge_id,bridge.cells)
    elif key.endswith('_switch'):
        kind={'soft_switch':SwitchVisualKind.SOFT,'heavy_switch':SwitchVisualKind.HEAVY,
              'split_switch':SwitchVisualKind.SPLIT}[key]
        for switch in getattr(board,'switches',()):
            if switch.kind is kind:target(switch.switch_id,(switch.cell,))
    else:
        value='FRAGILE' if key=='fragile' else 'VOID'
        for r,row in enumerate(board.tiles):
            for c,kind in enumerate(row):
                if kind.value==value:target(f'{key}:{r}:{c}',((r,c),))
    return tuple(sorted(result,key=lambda item:(item.cell,item.identity)))


def target_status(target,snapshot):
    if target.mechanic=='bridge':
        states={s.bridge_id:s.present for s in getattr(snapshot,'bridge_states',())}
        if states.get(target.identity) is False:return 'Currently inactive'
    if target.mechanic=='fragile' and target.cell in getattr(snapshot,'broken_fragile_cells',()):
        return 'Currently broken'
    return ''


def focused_view(view,point,pixel_rect,viewport_rect):
    """Project the tile to the centre of the unobscured UI rectangle.

    Reuse the lens and actual orientation, with at most a 14% approach. No
    viewport resize or geometry creation is involved in camera focusing.
    """
    from panda3d.core import Quat
    quat=Quat(*view.quaternion)
    right=tuple(quat.xform(Vec3(1,0,0)));up=tuple(quat.xform(Vec3(0,0,1)))
    forward=tuple(quat.xform(Vec3(0,1,0)))
    vx,vy,vw,vh=viewport_rect
    x,y,w,h=pixel_rect
    nx=2*((x+w/2-vx)/vw)-1;ny=1-2*((y+h/2-vy)/vh)
    distance=max(view.fit.distance*.86,min(view.fit.distance,6.0))
    sx=nx*distance*math.tan(math.radians(view.fov[0])/2)
    sy=ny*distance*math.tan(math.radians(view.fov[1])/2)
    target=tuple(point[i]-right[i]*sx-up[i]*sy for i in range(3))
    position=tuple(target[i]-forward[i]*distance for i in range(3))
    near=min(view.near_far[0],max(.01,distance*.12))
    far=max(view.near_far[1],distance+math.dist(view.fit.bounds.minimum,view.fit.bounds.maximum)*2)
    fit=replace(view.fit,position=position,target=target,right=right,up=up,forward=forward,
                distance=distance,near=near,far=far)
    return replace(view,fit=fit,position=position,near_far=(near,far))


def interpolate_view(start,end,t):
    u=smoothstep(min(1,max(0,t)))
    pos=lerp(start.position,end.position,u)
    fit=replace(end.fit,position=pos,target=lerp(start.fit.target,end.fit.target,u),
        distance=start.fit.distance+(end.fit.distance-start.fit.distance)*u,
        near=start.near_far[0]+(end.near_far[0]-start.near_far[0])*u,
        far=start.near_far[1]+(end.near_far[1]-start.near_far[1])*u)
    return replace(end,fit=fit,position=pos,quaternion=slerp(start.quaternion,end.quaternion,u),
        fov=tuple(a+(b-a)*u for a,b in zip(start.fov,end.fov)),near_far=(fit.near,fit.far))


class MechanicsFocus:
    def __init__(self,app,controller,camera,guide,*,views=None,allowed=lambda:True,safe_rect=None):
        self.app,self.controller,self.camera,self.guide=app,controller,camera,guide
        self.views,self.allowed,self.safe_rect=views,allowed,safe_rect
        self._saved=self._animation=self._expected=None
        self._elapsed=0.;self._returning=False;self._disposed=False
        self._indices={};self._context=self._current_context();self._highlight=None
        self._highlight_elapsed=0.;self.target=None
        self._prior_hook=camera.on_user_view_change
        camera.on_user_view_change=self.user_camera_input
        guide._on_select=self.select;guide._on_close=self.restore;guide._on_back=self.restore
        self._task=app.taskMgr.add(self._update,f'MechanicsFocus-{id(self)}')

    def _current_context(self):
        data=getattr(self.controller,'board_data',None)
        return (id(data),getattr(self.controller,'session_id',None))

    def _sync_context(self,close=True):
        context=self._current_context()
        if context!=self._context:
            # Restart has the same Board DTO; new levels already refit the camera.
            self.cancel(restore=context[0]==self._context[0])
            self._indices.clear();self._context=context
            if close:self.guide.close_card()

    @property
    def has_focus(self):return self._saved is not None

    def _ready(self):
        c=self.controller
        return (self.allowed() and c.manager is not None and not c.manager.is_busy
            and getattr(c,'_current_plan',None) is None and c.phase in ('READY','GOAL','FELL')
            and not c.guide_active and getattr(getattr(c,'_mode',None),'value','IDLE')=='IDLE')

    def _viewport(self):
        width,height=self.app.win.getXSize(),self.app.win.getYSize()
        left,right,bottom,top=self.app.dashboard.viewport.region.getDimensions()
        return left*width,(1-top)*height,(right-left)*width,(top-bottom)*height

    def _safe_area(self):
        if self.safe_rect:return self.safe_rect()
        vx,vy,vw,vh=self._viewport();card=self.guide.layout.card
        right=min(vx+vw-32,card.x-24 if card else vx+vw-32)
        return (vx+32,140,max(80,right-vx-32),max(80,self.app.win.getYSize()-250))

    def select(self,key):
        if self._disposed:return
        self._sync_context(close=False)
        board=self.controller.board_data
        targets=mechanic_targets(board,key)
        if not targets:
            self._animation=None;self.target=None;self._clear_highlight()
            self.guide.set_focus_info('Not present in this level',self.has_focus)
            return
        if not self._ready():
            self.guide.set_focus_info('Focus unavailable during animation or replay.',self.has_focus)
            return
        index=self._indices.get(key,0)%len(targets);self._indices[key]=index+1
        self.target=targets[index]
        snapshot=self.controller.manager.current_snapshot
        status=target_status(self.target,snapshot)
        if self._saved is None:self._saved=self.camera.capture_presentation()
        if self._saved is None:return
        self.guide.set_focus_info(f'{index+1} / {len(targets)}'+(f'\n{status}' if status else ''),True)
        if self.views:self.views.acquire_presentation(self)
        xy=cell_to_world(*self.target.cell,rows=board.rows,cols=board.cols,pitch=1.)
        end=focused_view(self._saved,(*xy,.06),self._safe_area(),self._viewport())
        self._animate(end)
        self._highlight_target(self.target)

    def _animate(self,end,returning=False):
        self._animation=(self.camera.capture_presentation(),end)
        self._elapsed=0.;self._returning=returning
        self._expected=self._actual()

    def restore(self):
        if self._disposed or self._saved is None:return
        self._clear_highlight();self.target=None
        if not self._ready():
            self.cancel(restore=True)
            self.guide.set_focus_info('Focus unavailable during animation or replay.',False)
            return
        self._animate(self._saved,returning=True)
        self.guide.set_focus_info('Returning to board',False)

    def _actual(self):
        view=self.camera.capture_presentation()
        return None if view is None else (view.position,view.quaternion,view.fov,view.near_far)

    def user_camera_input(self):
        if self.has_focus:self.cancel(restore=False)
        if self._prior_hook:self._prior_hook()

    def cancel(self,restore=False):
        if restore and self._saved is not None:self.camera.apply_presentation(self._saved)
        self._saved=self._animation=self._expected=None;self.target=None
        self._clear_highlight()
        if self.views:self.views.release_presentation(self)
        self.guide.set_focus_info('',False)

    def advance(self,dt):
        if self._disposed:return
        self._sync_context()
        if not self.has_focus:return
        if not self._ready():
            self.cancel(restore=True)
            self.guide.set_focus_info('Focus unavailable during animation or replay.',False)
            return
        # Direct setHpr/setPos/lens input also cancels our lease, even when a
        # camera input system doesn't use BoardCameraController's public methods.
        if self._expected is not None and self._actual()!=self._expected:
            self.cancel(restore=False);return
        if self._animation:
            self._elapsed=min(FOCUS_DURATION,self._elapsed+max(0,dt))
            start,end=self._animation
            view=end if self._elapsed>=FOCUS_DURATION else interpolate_view(start,end,self._elapsed/FOCUS_DURATION)
            self.camera.apply_presentation(view);self._expected=self._actual()
            if self._elapsed>=FOCUS_DURATION:
                self._animation=None
                if self._returning:
                    self._saved=self._expected=None
                    if self.views:self.views.release_presentation(self)
                    self.guide.set_focus_info('',False)
        if self._highlight is not None:
            self._highlight_elapsed+=max(0,dt)
            if self._highlight_elapsed>=HIGHLIGHT_DURATION:self._clear_highlight()
            else:
                u=self._highlight_elapsed/HIGHLIGHT_DURATION
                self._highlight.setAlphaScale((.65+.35*math.sin(math.pi*u))*(1-u*u))

    def _highlight_target(self,target):
        from src.gui.scene_style import SHADOW_MASK
        from src.gui import ui_theme
        self._clear_highlight()
        lines=LineSegs('GuideTileLocator');lines.setThickness(3)
        lines.setColor(*ui_theme.rgba(BY_ID[target.mechanic].accent))
        board=self.controller.board_data
        for cell in target.cells:
            x,y=cell_to_world(*cell,rows=board.rows,cols=board.cols,pitch=1.)
            corners=((-.47,-.47),(.47,-.47),(.47,.47),(-.47,.47),(-.47,-.47))
            lines.moveTo(x+corners[0][0],y+corners[0][1],.065)
            for a,b in corners[1:]:lines.drawTo(x+a,y+b,.065)
        self._highlight=self.app.effects_root.attachNewNode(lines.create())
        self._highlight.setLightOff(1);self._highlight.setShaderOff(1)
        self._highlight.setDepthWrite(False);self._highlight.setTransparency(TransparencyAttrib.MAlpha)
        self._highlight.hide(SHADOW_MASK);self._highlight_elapsed=0.

    def _clear_highlight(self):
        if self._highlight is not None:self._highlight.removeNode()
        self._highlight=None

    def _update(self,task):
        self.advance(ClockObject.getGlobalClock().getDt());return task.cont

    def reset(self,restore=False):
        self.cancel(restore=restore);self._indices.clear();self._context=self._current_context()
        self.guide.close_card()

    def dispose(self):
        if self._disposed:return
        self.cancel(restore=False);self._disposed=True
        self.app.taskMgr.remove(self._task)
        self.camera.on_user_view_change=self._prior_hook
        self.guide._on_select=self.guide._on_close=self.guide._on_back=None
