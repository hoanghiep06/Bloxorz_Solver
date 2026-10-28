"""Author deterministic Snow stone maps; numpy/Pillow are authoring-only.

Runtime needs only the checked-in PNGs and Panda3D. Original procedural assets,
no third-party images. Does not rebuild or modify any Jungle/special-tile asset.
"""
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
from src.gui.snow_palette import SNOW_PALETTE,SNOW_COVERAGE_TARGET

ROOT=Path(__file__).resolve().parents[1]/'assets/materials'
SIZE=1024


def noise(rng,cells):
    # Wrapped lattice: interpolation has matching edge neighbourhoods.
    lattice=rng.integers(0,256,(cells,cells),dtype=np.uint8)
    tiled=np.tile(lattice,(3,3))
    full=Image.fromarray(tiled).resize((SIZE*3,SIZE*3),Image.Resampling.BICUBIC)
    return np.asarray(full.crop((SIZE,SIZE,SIZE*2,SIZE*2)),dtype=float)/255


def smoothstep(low,high,value):
    t=np.clip((value-low)/(high-low),0,1)
    return t*t*(3-2*t)


def build():
    rng=np.random.default_rng(28102026)
    y,x=np.mgrid[:SIZE,:SIZE]/SIZE
    broad=noise(rng,4);medium=noise(rng,14);small=noise(rng,64)
    grain=noise(rng,256)
    wx=x+.045*np.sin(y*6.283)+.022*(medium-.5)
    wy=y+.035*np.sin(x*12.566)+.022*(medium-.5)
    distances=[]
    for px,py in rng.uniform(0,1,(5,2)):
        dx=np.abs(wx-px);dy=np.abs(wy-py)
        distances.append(np.minimum(dx,1-dx)**2+np.minimum(dy,1-dy)**2)
    nearest=np.partition(np.stack(distances),1,axis=0)[:2]
    gap=np.sqrt(nearest[1])-np.sqrt(nearest[0])
    # Sparse hairline fractures; no dense pebble/grain mosaic at distant views.
    crack=np.exp(-(gap/.0018)**2)
    vein=np.exp(-(np.sin(wx*11+wy*7+broad*4)/.095)**2)
    # Connected snowbanks with soft shorelines, not white noise/sticker blobs.
    # Calibrate the median transition to 80% occupied snow across the atlas.
    field=.65*broad+.25*noise(rng,7)+.08*noise(rng,18)+.02*small
    threshold=float(np.quantile(field,1-SNOW_COVERAGE_TARGET))
    mask=smoothstep(threshold-.050,threshold+.050,field)
    rock=.64+.35*broad+.20*medium+.012*(small-.5)-.13*vein-.30*crack
    rock+=.045*np.sin((x+y*.4)*11+medium*4)
    stone=np.asarray(SNOW_PALETTE['variation'][:3])*rock[...,None]
    stone=stone*.88+np.asarray(SNOW_PALETTE['wear'][:3])*.12
    dunes=noise(rng,11);powder=noise(rng,110)
    snow_light=.30+.64*dunes+.035*(powder-.5)
    snow=np.asarray(SNOW_PALETTE['wear'][:3])*(1-snow_light[...,None])+np.asarray(
        SNOW_PALETTE['top'][:3])*snow_light[...,None]
    snow*=1.+.018*(powder[...,None]-.5)+.003*(grain[...,None]-.5)
    # A colder, softly occluded toe where a snowbank meets exposed stone.
    bank=4*mask*(1-mask)
    snow=snow*(1-bank[...,None]*.03)+np.asarray(SNOW_PALETTE['wear'][:3])*bank[...,None]*.03
    rgb=stone*(1-mask[...,None])+snow*mask[...,None]
    rgba=np.dstack((np.clip(rgb,0,1),mask))
    ROOT.mkdir(parents=True,exist_ok=True)
    Image.fromarray((rgba*255).astype('uint8')).save(ROOT/'snow-stone.png')
    rock_height=.40+.075*broad+.035*medium-.045*vein-.11*crack
    snow_height=.59+.045*dunes+.012*noise(rng,32)+.008*powder
    # Virtual accumulation: normal slopes only, never displace the Z=0 mesh.
    height=rock_height*(1-mask)+snow_height*mask
    height=np.asarray(Image.fromarray((np.clip(height,0,1)*255).astype('uint8')).filter(
        ImageFilter.GaussianBlur(1.2)),dtype=float)/255
    dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*SIZE*.12
    dy=(np.roll(height,1,axis=0)-np.roll(height,-1,axis=0))*SIZE*.12
    dx=.65*np.tanh(dx/.65);dy=.65*np.tanh(dy/.65)
    normals=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1)
    normals/=np.linalg.norm(normals,axis=-1)[...,None]
    roughness=np.clip((.84+.09*medium)*(1-mask)+(.93+.04*powder)*mask,0,1)
    normal_roughness=np.dstack((normals*.5+.5,roughness))
    Image.fromarray((normal_roughness*255).astype('uint8')).save(ROOT/'snow-stone-normal.png')
    print('Snow coverage >= 0.5:',round(float(np.mean(mask>=.5))*100,2),'%; weighted:',
          round(float(np.mean(mask))*100,2),'%')


if __name__=='__main__':build()
