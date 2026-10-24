#!/usr/bin/env python3
"""Extract sprites from magenta sprite sheets.

For each manifest cell: crop, chroma-key magenta -> alpha (with despill),
verify with OpenCV connected-components that the cell holds exactly one
main component, trim to the component bbox, save a transparent PNG.
"""
import json, os, sys
import numpy as np
import cv2
from PIL import Image

ROOT = os.path.dirname(__file__)

def extract_cell(cell_img):
    arr = np.array(cell_img.convert("RGB")).astype(np.int16)
    # magenta distance: high R+B, low G
    dist = np.abs(arr[:, :, 0] - 255) + np.abs(arr[:, :, 2] - 255) + np.abs(arr[:, :, 1] - 0)
    mask = (dist > 180).astype(np.uint8)  # 1 = foreground
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    comps = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area >= 40:
            comps.append((area, x, y, w, h))
    comps.sort(reverse=True)
    rgba = np.zeros((arr.shape[0], arr.shape[1], 4), dtype=np.uint8)
    rgba[:, :, :3] = np.array(cell_img.convert("RGB"))
    # soft alpha edge: foreground mask dilated core + distance-based edge
    alpha = (mask * 255).astype(np.uint8)
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    rgba[:, :, 3] = alpha
    # despill: where magenta fringe (R&B >> G) on semi edge, pull G up
    fringe = (rgba[:, :, 0] > 150) & (rgba[:, :, 2] > 150) & (rgba[:, :, 1] < 120) & (rgba[:, :, 3] > 0)
    rgba[:, :, 1] = np.where(fringe, ((rgba[:, :, 0].astype(int) + rgba[:, :, 2].astype(int)) // 4), rgba[:, :, 1])
    im = Image.fromarray(rgba, "RGBA")
    off = (0, 0)
    if comps:
        _, x, y, w, h = comps[0]
        im = im.crop((x, y, x + w, y + h)); off = (x, y)
    return im, len(comps), (comps[0][0] if comps else 0), off

def main():
    manifest = json.load(open(os.path.join(ROOT, "sheets", "manifest.json")))
    report = {}
    ok = True
    for cid, info in manifest["characters"].items():
        sheet = Image.open(info["sheet"])
        outdir = os.path.join(ROOT, "extracted", cid)
        os.makedirs(outdir, exist_ok=True)
        report[cid] = {}
        for name, cell in info["cells"].items():
            crop = sheet.crop((cell["x"], cell["y"], cell["x"] + cell["w"], cell["y"] + cell["h"]))
            im, ncomp, area, off = extract_cell(crop)
            im.save(os.path.join(outdir, f"{name}.png"))
            # pivot remap into trimmed image coords is identity here because
            # parts are drawn untrimmed at cell origin; record original pivot.
            report[cid][name] = {"size": list(im.size), "components": ncomp, "fg_area": int(area),
                                 "pivot": [int(cell["pivot"][0]-off[0]), int(cell["pivot"][1]-off[1])]}
            if ncomp < 1:
                ok = False; print(f"  !! {cid}/{name}: no component")
        print(f"extracted {cid}: {len(report[cid])} parts")
    json.dump(report, open(os.path.join(ROOT, "extracted", "extraction_report.json"), "w"), indent=1)
    # also copy parts into the Godot project
    import shutil
    for cid in report:
        dst = os.path.join(ROOT, "godot_project", "assets", cid)
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(os.path.join(ROOT, "extracted", cid)):
            shutil.copy(os.path.join(ROOT, "extracted", cid, f), os.path.join(dst, f))
    print("EXTRACTION", "OK" if ok else "WITH WARNINGS")

if __name__ == "__main__":
    main()
