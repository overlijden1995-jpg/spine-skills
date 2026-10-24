#!/usr/bin/env python3
"""Remove magenta key color from AI concept sheets; optionally save connected crops.

Requires Pillow and (only for --components) OpenCV: pip install Pillow opencv-python.
Example: python scripts/extract_magenta.py assets/concept_body_parts.png --out assets/extracted/heads --components
"""
import argparse
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    p.add_argument('image')
    p.add_argument('--out',required=True)
    p.add_argument('--tolerance',type=int,default=75,help='Distance threshold from pure magenta')
    p.add_argument('--components',action='store_true',help='Save each connected foreground region as a padded PNG')
    a=p.parse_args()
    try:
        from PIL import Image
    except ImportError as e:
        raise SystemExit('Install Pillow: python -m pip install Pillow') from e
    im=Image.open(a.image).convert('RGBA')
    px=im.load(); w,h=im.size; tol=a.tolerance
    mask=bytearray(w*h)
    for y in range(h):
        for x in range(w):
            r,g,b,alpha=px[x,y]
            keyed=(r>255-tol and b>255-tol and g<tol*2)
            if keyed: px[x,y]=(r,g,b,0)
            elif alpha: mask[y*w+x]=1
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    if not a.components:
        dest=out/(Path(a.image).stem+'_transparent.png'); im.save(dest); print(dest); return
    try:
        import cv2
        import numpy as np
    except ImportError as e:
        raise SystemExit('Install OpenCV and numpy for --components: python -m pip install opencv-python numpy') from e
    binary=np.frombuffer(mask,dtype=np.uint8).reshape(h,w)*255
    count,labels,stats,_=cv2.connectedComponentsWithStats(binary,8)
    idx=0
    for i in range(1,count):
        x,y,cw,ch,area=map(int,stats[i])
        if area<90: continue
        pad=5; x0=max(0,x-pad); y0=max(0,y-pad); x1=min(w,x+cw+pad); y1=min(h,y+ch+pad)
        crop=im.crop((x0,y0,x1,y1)); lab=labels[y0:y1,x0:x1]
        crop.putalpha(Image.fromarray(np.where(lab==i, np.asarray(crop)[:,:,3], 0).astype('uint8')))
        crop.save(out/f'part_{idx:03d}.png'); idx+=1
    print(f'Saved {idx} components to {out}')

if __name__=='__main__': main()
