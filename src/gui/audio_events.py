"""Presentation audio contracts. Read only validated visual DTOs, never Core rules."""
from dataclasses import dataclass
from enum import Enum


class AudioEvent(str, Enum):
    OPENING_LANDING='opening_landing'
    OPENING_WIND='opening_wind'
    ROLL_START='roll_start'
    ROLL_IMPACT='roll_impact'
    SPLIT_CUBE_IMPACT='split_cube_impact'
    EDGE_SLIDE='edge_slide'
    FALL_WIND='fall_wind'
    GOAL_ENERGY='goal_energy'
    GOAL_COMPLETE='goal_complete'
    SOFT_SWITCH='soft_switch'
    HEAVY_SWITCH='heavy_switch'
    SPLIT_SWITCH='split_switch'
    TELEPORT_CHARGE='teleport_charge'
    TELEPORT_DISASSEMBLE='teleport_disassemble'
    TELEPORT_TRAVEL='teleport_travel'
    TELEPORT_ARRIVAL='teleport_arrival'
    TELEPORT_MATERIALIZE='teleport_materialize'
    BRIDGE_OPEN='bridge_open'
    BRIDGE_CLOSE='bridge_close'
    FRAGILE_CRACK='fragile_crack'
    FRAGILE_BREAK='fragile_break'
    UI_CLICK='ui_click'
    UI_CONFIRM='ui_confirm'
    UI_BACK='ui_back'
    JUNGLE='jungle'
    SNOW='snow'


@dataclass(frozen=True)
class SoundSpec:
    files: tuple[str,...]
    gain: float=.6
    priority: int=2
    group: str='gameplay'
    loop: bool=False


SOUND_BANK={e:SoundSpec((e.value,)) for e in AudioEvent}
SOUND_BANK.update({
    AudioEvent.OPENING_LANDING:SoundSpec(('landing',),.8,4),
    AudioEvent.OPENING_WIND:SoundSpec(('fall_wind',),.13),
    AudioEvent.ROLL_START:SoundSpec(('roll_scrape',),.28,1),
    AudioEvent.ROLL_IMPACT:SoundSpec(tuple(f'impact_{i}' for i in range(3)),.68,3),
    AudioEvent.SPLIT_CUBE_IMPACT:SoundSpec(('cube_impact',),.35,3),
    AudioEvent.EDGE_SLIDE:SoundSpec(('edge_slide',),.28,1),
    AudioEvent.FALL_WIND:SoundSpec(('fall_wind',),.45,3,loop=True),
    AudioEvent.GOAL_COMPLETE:SoundSpec(('victory',),.65,5),
    **{e:SoundSpec((e.value,),.45,4) for e in (AudioEvent.TELEPORT_DISASSEMBLE,AudioEvent.TELEPORT_ARRIVAL,AudioEvent.TELEPORT_MATERIALIZE)},
    AudioEvent.TELEPORT_CHARGE:SoundSpec(('teleport_charge',),.35,4),
    AudioEvent.TELEPORT_TRAVEL:SoundSpec(('teleport_travel',),.4,4),
    AudioEvent.FRAGILE_CRACK:SoundSpec(('fragile_crack',),.35,3),
    AudioEvent.FRAGILE_BREAK:SoundSpec(('fragile_break',),.48,3),
    **{e:SoundSpec((e.value,),.32,1,'ui') for e in (AudioEvent.UI_CLICK,AudioEvent.UI_CONFIRM,AudioEvent.UI_BACK)},
    **{e:SoundSpec((e.value,),.18,0,'ambience',True) for e in (AudioEvent.JUNGLE,AudioEvent.SNOW)},
})


# Cosmetic skins keep the same authoritative cue identity, mixer and lifecycle.
THEME_SOUND_FILES={
    'dark':{AudioEvent.SOFT_SWITCH:('soft_switch_ice',),
            AudioEvent.HEAVY_SWITCH:('heavy_switch_ice',),
            AudioEvent.SPLIT_SWITCH:('split_switch_ice',)},
}


@dataclass(frozen=True,order=True)
class AudioCue:
    progress: float
    event: AudioEvent
    stop: bool=False


def _supported_landing(request,board):
    from src.gui.animation_contracts import as_visual_snapshot
    from src.gui.advanced_contracts import AdvancedTileKind as T
    from src.gui.contracts import BasicOrientation as O
    snap=as_visual_snapshot(request.after_snapshot)
    if request.actor_id is not None:
        cells=[c.cell for c in snap.cubes if c.cube_id==request.actor_id]
    else:
        pose=snap.whole_pose;r,c=pose.anchor_cell
        cells=[(r,c)]
        if pose.orientation is O.HORIZONTAL:cells.append((r,c+1))
        elif pose.orientation is O.VERTICAL:cells.append((r+1,c))
    present={b.bridge_id for b in snap.bridge_states if b.present}
    bridges={cell for b in board.bridges if b.bridge_id in present for cell in b.cells}
    return bool(cells) and all(cell not in board.goal_cells and cell not in snap.broken_fragile_cells
        and (board.tiles[cell[0]][cell[1]] in (T.FLOOR,T.FRAGILE) or cell in bridges) for cell in cells)


def animation_cues(request,board,fall=None):
    """Thresholds derived from the *same* visual event windows and phase constants."""
    from src.gui.animation_contracts import AnimationKind as K,EventKind as E
    from src.gui.advanced_contracts import SwitchVisualKind
    from src.gui.split_teleport_math import CHARGE_END,DISASSEMBLY_END,ARRIVAL_START,MATERIALIZE_END
    A=AudioEvent;cues=[]
    def add(p,e):cues.append(AudioCue(p,e))
    if request.kind is K.ROLL:
        add(0,A.ROLL_START)
        if _supported_landing(request,board):
            add(1,A.SPLIT_CUBE_IMPACT if request.actor_id is not None else A.ROLL_IMPACT)
    if fall is not None:
        if fall.roll is not None:add(0,A.ROLL_START)
        if fall.pivot is not None:add(fall.roll_end/request.duration,A.EDGE_SLIDE)
        add(fall.tip_end/request.duration,A.FALL_WIND)
    for e in request.events:
        def at(u,event):add(e.start+(e.end-e.start)*u,event)
        if e.kind is E.SWITCH_ACTIVATE:
            kind=next(s.kind for s in board.switches if s.switch_id==e.target_id)
            if kind is not SwitchVisualKind.SPLIT:
                at(0,{SwitchVisualKind.SOFT:A.SOFT_SWITCH,SwitchVisualKind.HEAVY:A.HEAVY_SWITCH}[kind])
        elif e.kind in (E.BRIDGE_PRESENT,E.BRIDGE_ABSENT):
            event=A.BRIDGE_OPEN if e.kind is E.BRIDGE_PRESENT else A.BRIDGE_CLOSE
            at(0,event);cues.append(AudioCue(e.end,event,stop=True))
        elif e.kind is E.FRAGILE_BREAK:at(0,A.FRAGILE_CRACK);at(1,A.FRAGILE_BREAK)
        elif e.kind in (E.SPLIT,E.MERGE):
            if e.kind is E.SPLIT:at(0,A.SPLIT_SWITCH)
            points=(0,CHARGE_END,DISASSEMBLY_END,ARRIVAL_START,MATERIALIZE_END) if e.kind is E.SPLIT else (0,.22,.42,.66,.85)
            for u,event in zip(points,(A.TELEPORT_CHARGE,A.TELEPORT_DISASSEMBLE,A.TELEPORT_TRAVEL,A.TELEPORT_ARRIVAL,A.TELEPORT_MATERIALIZE)):at(u,event)
        elif e.kind is E.GOAL_COMPLETE:at(.35,A.GOAL_ENERGY);at(1,A.GOAL_COMPLETE)
    return tuple(sorted(cues,key=lambda cue:cue.progress))


class AnimationAudioTrack:
    """Consumes animation elapsed samples exactly once; owns no clock/task or gameplay."""
    def __init__(self,audio,request,board,fall=None):
        self.audio,self.request,self.fall=audio,request,fall
        self.scope=('animation',request.session_id,request.request_id)
        self.cues=animation_cues(request,board,fall);self.cursor=0;self.handles=[];self.closed=False
        self.wind=None

    def sample(self,progress):
        if self.closed:return
        while self.cursor<len(self.cues) and self.cues[self.cursor].progress<=progress+1e-12:
            cue=self.cues[self.cursor];self.cursor+=1
            if cue.stop:
                self.audio.stop_scope(self.scope,events={cue.event})
                continue
            handle=self.audio.play_sfx(cue.event,scope=self.scope)
            self.handles.append(handle)
            if cue.event is AudioEvent.FALL_WIND:self.wind=handle
        if self.wind is not None:
            sample=self.fall.sample(progress*self.request.duration)
            t=max(0,progress-self.fall.tip_end/self.request.duration)
            self.audio.set_voice_gain(self.wind,min(1,.2+2*t)*sample.opacity)

    def pause(self):self.audio.pause_gameplay_audio()
    def resume(self):self.audio.resume_gameplay_audio()
    def finish(self,completed):
        if self.closed:return
        self.closed=True
        self.audio.stop_scope(self.scope,loops_only=completed)
        # Bridge movement must stop with the corresponding visible surface motion.
        if completed:self.audio.stop_scope(self.scope,events={AudioEvent.BRIDGE_OPEN,AudioEvent.BRIDGE_CLOSE})
