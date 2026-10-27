"""Rebuild original deterministic visual assets (authoring only: numpy, Pillow).

Runtime consumes the checked-in PNG files; it does not require these libraries.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1] / 'assets/materials'
SIZE = 512

def noise(rng, scale):
    a = rng.integers(0, 256, (scale, scale), dtype=np.uint8)
    return np.asarray(Image.fromarray(a).resize((SIZE, SIZE), Image.Resampling.BICUBIC), dtype=float)/255

def build():
    ROOT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42716)
    y,x = np.mgrid[:SIZE,:SIZE]/SIZE
    coarse=noise(rng,16); fine=noise(rng,128); grain=noise(rng,SIZE)
    # Periodic warped Voronoi boundaries: connected irregular fissures rather
    # than painted straight lines. Texture mask is also actual emission data.
    wx=x+.012*np.sin(y*21)+.006*np.sin(y*51+x*12)
    wy=y+.012*np.sin(x*26)+.006*np.sin(x*53+y*10)
    distances=[]
    for i in range(3):
        for j in range(3):
            px=(i+rng.uniform(.1,.9))/3;py=(j+rng.uniform(.1,.9))/3
            dx=np.abs(wx-px);dy=np.abs(wy-py)
            distances.append(np.minimum(dx,1-dx)**2+np.minimum(dy,1-dy)**2)
    nearest=np.partition(np.stack(distances),1,axis=0)[:2]
    fissure=(np.sqrt(nearest[1])-np.sqrt(nearest[0]))
    crack=np.clip(1-fissure/.009,0,1)
    halo=np.exp(-fissure*95)*.48
    rock=(.055+.12*coarse+.055*fine+.035*grain)
    base=np.stack((rock*1.05,rock*.97,rock*.89),axis=-1)
    hot=np.stack((np.ones_like(x),.18+.62*crack**2,.015+.12*crack**5),axis=-1)
    rgb=base*(1-crack[...,None])+hot*crack[...,None]
    rgb+=np.stack((halo*.4,halo*.045,halo*.004),axis=-1)
    save('magma',rgb,np.maximum(crack,halo*.15))
    height=np.clip(coarse*.35+fine*.22+grain*.08-crack*.38,0,1)
    Image.fromarray((height*255).astype('uint8')).save(ROOT/'magma-height.png')
    # Natural broad stone grain with irregular fine veins and subtle moss.
    vein=np.exp(-np.abs(np.sin(x*17+y*12+coarse*8))*65)
    v=.56+.21*coarse+.12*fine+.05*grain-.16*vein
    moss=np.clip((noise(rng,10)-.48)*3,0,1)*np.clip((coarse-.35)*2,0,1)
    veins=np.clip(1-fissure/.006,0,1)
    v=v-.24*veins
    stone=np.stack((v*.96,v*.98,v*.90),axis=-1)
    stone=stone*(1-moss[...,None]*.27)+np.array([.16,.23,.08])*moss[...,None]*.27
    save('stone-light',stone)
    snow=np.stack((v*.79,v*.91,v*1.07),axis=-1)
    save('stone-dark',snow)
    Image.fromarray((np.clip(coarse*.55+fine*.25+grain*.1-vein*.2,0,1)*255).astype('uint8')).save(ROOT/'stone-height.png')
    # Fractured warm stone shares the same fissure topology as the basalt.
    warm=np.stack((v*.78,v*.40,v*.15),axis=-1)
    save('fragile',warm*(1-crack[...,None])+hot*crack[...,None],crack)
    metal=np.stack((v*.43,v*.51,v*.52),axis=-1)
    save('metal',metal)

def save(name,rgb,emission=None):
    if emission is None:emission=np.zeros(rgb.shape[:2])
    rgba=np.dstack((np.clip(rgb,0,1),np.clip(emission,0,1)))
    Image.fromarray((rgba*255).astype('uint8'),'RGBA').save(ROOT/(name+'.png'))

if __name__=='__main__':build()
