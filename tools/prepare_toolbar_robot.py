"""Offline preparation of the user-supplied robot (Pillow, no runtime import).

Usage: python3 -m tools.prepare_toolbar_robot SOURCE.png
Border-connected white is removed; enclosed white highlights are preserved.
Only the largest non-background component is kept, excluding the floor shadow.
"""
from collections import deque
from pathlib import Path
import argparse

def main():
    from PIL import Image
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,default=Path('assets/icons/ai-robot.png'))
    args=parser.parse_args()
    image=Image.open(args.source).convert('RGB');w,h=image.size;pixels=image.load()
    background=set();queue=deque()
    for x in range(w):queue.extend(((x,0),(x,h-1)))
    for y in range(h):queue.extend(((0,y),(w-1,y)))
    def adjacent(x,y):return ((x-1,y),(x+1,y),(x,y-1),(x,y+1))
    while queue:
        x,y=queue.popleft()
        if not(0<=x<w and 0<=y<h) or (x,y) in background:continue
        if min(pixels[x,y])<246:continue
        background.add((x,y));queue.extend(adjacent(x,y))
    unseen={(x,y) for y in range(h) for x in range(w)}-background
    components=[]
    while unseen:
        first=unseen.pop();component={first};queue=deque([first])
        while queue:
            for point in adjacent(*queue.popleft()):
                if point in unseen:unseen.remove(point);component.add(point);queue.append(point)
        components.append(component)
    body=max(components,key=len)
    # Fill enclosed highlights even when a tiny white region touches the outside
    # mask: do not threshold/recolour the interior of the robot.
    output=Image.new('RGBA',(w,h));out=output.load()
    for x,y in body:
        edge=any(p in background or not(0<=p[0]<w and 0<=p[1]<h) for p in adjacent(x,y))
        alpha=min(1.,(255-min(pixels[x,y]))/24) if edge else 1.
        color=tuple(round(max(0,min(255,(c-255*(1-alpha))/alpha))) for c in pixels[x,y])
        out[x,y]=(*color,round(alpha*255))
    bounds=output.getbbox();pad=6
    cropped=output.crop((max(0,bounds[0]-pad),max(0,bounds[1]-pad),min(w,bounds[2]+pad),min(h,bounds[3]+pad)))
    args.output.parent.mkdir(parents=True,exist_ok=True);cropped.save(args.output)
    print(args.output,cropped.size,'RGBA; robot component',len(body),'pixels')

if __name__=='__main__':main()
