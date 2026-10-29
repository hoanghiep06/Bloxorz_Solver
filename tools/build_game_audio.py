"""Original deterministic layered sound design; offline WAV authoring, no dependencies.

Broadband stone/grit transients, damped inharmonic body resonances, filtered wind,
FM/granular energy and a restrained harmonic flourish. Not sampled from recordings.
"""
import math
import random
import struct
import wave
from pathlib import Path

RATE=48000
ROOT=Path(__file__).resolve().parents[1]/'assets/audio'


def design(kind,duration,seed):
    rng=random.Random(seed);n=round(duration*RATE);noise=[rng.uniform(-1,1) for _ in range(n)]
    slow=mid=last=0.;out=[]
    modes=[(f*(.96+rng.random()*.08),rng.random()*6.28) for f in (63,107,179,293,431)]
    for i,w in enumerate(noise):
        t=i/RATE;u=t/duration
        slow+=.012*(w-slow);mid+=.16*(w-mid);grain=w-mid
        body=sum(math.sin(2*math.pi*f*t+p)*math.exp(-t*(8+j*5)) / (j+2)
                 for j,(f,p) in enumerate(modes))
        if kind in ('landing','impact','cube','heavy','arrival'):
            v=.70*body+.95*mid*math.exp(-t*15)+.16*grain*math.exp(-t*65)
            v+=.15*slow*math.exp(-t*4)
        elif kind in ('scrape','slide','bridge','retract'):
            env=math.sin(math.pi*u)**.7
            grit=(mid+.28*grain)*(.45+.55*math.sin(2*math.pi*(23*t+35*t*t))**4)
            v=grit*env*.7+.12*body*math.sin(math.pi*u)
        elif kind in ('wind','jungle','snow'):
            env=1. if kind in ('jungle','snow') else math.sin(math.pi*u)**.65
            v=(slow*4+mid*.35)*env*(.65+.20*math.sin(2*math.pi*.7*t))
            if kind=='jungle':v+=.16*mid*(.6+.4*math.sin(t*2.3)**2)
        elif kind in ('soft_ice','heavy_ice','split_ice'):
            # Inharmonic ice resonances over a restrained pressure/energy body.
            env=math.sin(math.pi*u)**.65
            ice=sum(math.sin(2*math.pi*f*t)*math.exp(-t*(9+j*4))/(j+2)
                    for j,f in enumerate((641,1093,1807,2683)))
            v=.28*ice+.18*grain*math.exp(-t*45)+env*(.12*mid+.04*math.sin(2*math.pi*223*t))
            if kind=='heavy_ice':v+=.48*body+.28*mid*math.exp(-t*18)
            if kind=='split_ice':v+=.12*env*math.sin(2*math.pi*(280*t+400*t*t))
        elif kind in ('crack','break'):
            burst=sum(math.exp(-max(0,t-c)*80) if t>=c else 0 for c in (.0,.045,.11,.18,.25))
            v=(grain*.35+mid*.8)*burst+.22*body
        elif kind in ('charge','disassemble','travel','materialize','goal_energy','soft','split'):
            env=math.sin(math.pi*u)**.6
            carrier=math.sin(2*math.pi*(140*t+150*t*t)+2.8*math.sin(2*math.pi*43*t))
            shimmer=sum(math.sin(2*math.pi*f*t+2*math.sin(11*t)) for f in (487,733,1103))/3
            v=env*(.18*carrier+.12*shimmer+.6*mid*(.4+.6*math.sin(2*math.pi*37*t)**8))
            if kind=='disassemble':v+=grain*.25*math.exp(-u*7)
            if kind=='travel':v+=slow*2*env
        elif kind=='victory':
            v=0.
            for j,f in enumerate((261.63,392.,523.25,659.25,783.99)):
                dt=t-j*.12
                if dt>=0:
                    v+=.12*math.exp(-dt*2.7)*(math.sin(2*math.pi*f*dt)+.25*math.sin(2*math.pi*f*2.013*dt))
            v+=.1*slow*math.sin(math.pi*u)
        else: # a tactile, filtered UI click; no high-pitched beep
            v=(.8*mid+.1*grain+.25*body)*math.exp(-t*55)
        last+=.65*(v-last);out.append(last)
    peak=max(abs(v) for v in out) or 1
    target=.50 if kind in ('jungle','snow') else .72
    out=[v*target/peak for v in out]
    if kind in ('jungle','snow'):
        k=RATE//3
        for i in range(k):
            u=i/(k-1);out[n-k+i]=out[n-k+i]*(1-u)+out[i]*u
        out=out[k:]
    else:
        for i in range(len(out)):
            out[i]*=min(1,i/(RATE*.002),(len(out)-1-i)/(RATE*.018))
    return out


ASSETS={
    'landing':('landing',.65),'roll_scrape':('scrape',.28),
    **{f'impact_{i}':('impact',.38+i*.025) for i in range(3)},
    'cube_impact':('cube',.25),'edge_slide':('slide',.24),'fall_wind':('wind',1.2),
    'goal_energy':('goal_energy',.65),'victory':('victory',2.1),
    'soft_switch':('soft',.18),'heavy_switch':('heavy',.25),'split_switch':('split',.30),
    'teleport_charge':('charge',.45),'teleport_disassemble':('disassemble',.32),
    'teleport_travel':('travel',.65),'teleport_arrival':('arrival',.38),
    'teleport_materialize':('materialize',.38),
    'bridge_open':('bridge',.28),'bridge_close':('retract',.28),
    'fragile_crack':('crack',.12),'fragile_break':('break',.48),
    'ui_click':('click',.075),'ui_confirm':('click',.11),'ui_back':('click',.10),
    'jungle':('jungle',8.34),'snow':('snow',8.34),
    'soft_switch_ice':('soft_ice',.22),'heavy_switch_ice':('heavy_ice',.30),
    'split_switch_ice':('split_ice',.33),
}


def main():
    for index,(name,(kind,duration)) in enumerate(ASSETS.items()):
        out=design(kind,duration,83107+index*97)
        folder=ROOT/('ambience' if name in ('jungle','snow') else 'sfx');folder.mkdir(parents=True,exist_ok=True)
        # Stereo micro-delay produces width while keeping a centred heavy transient.
        delay=round(.0017*RATE)
        stereo=[int(max(-.95,min(.95,v)) * 32767) for i,left in enumerate(out)
                for v in (left,.97*out[(i-delay)%len(out) if kind in ('jungle','snow') else max(0,i-delay)] + .03*left)]
        with wave.open(str(folder/(name+'.wav')),'wb') as f:
            f.setparams((2,2,RATE,0,'NONE','not compressed'))
            f.writeframes(struct.pack('<%dh'%len(stereo),*stereo))
    print(f'Authored {len(ASSETS)} original layered stereo WAV assets at {RATE} Hz.')


if __name__=='__main__':main()
