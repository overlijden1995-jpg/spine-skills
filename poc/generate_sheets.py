#!/usr/bin/env python3
"""Generate 10 medieval character sprite sheets on magenta (#FF00FF).

Each sheet is a deconstructed Spine-style layout: individual body parts in
known grid cells (recorded in the manifest) plus an assembled preview.
Deterministic vector drawing with Pillow so chroma-key extraction is exact.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

MAGENTA = (255, 0, 255, 255)
OUT = os.path.join(os.path.dirname(__file__), "sheets")
os.makedirs(OUT, exist_ok=True)

def font(sz):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def hx(c):
    c = c.lstrip('#'); return tuple(int(c[i:i+2], 16) for i in (0, 2, 4)) + (255,)

def shade(col, f):
    return tuple(max(0, min(255, int(v * f))) for v in col[:3]) + (255,)

OUTLINE = (20, 16, 24, 255)

# ---- part painters (each returns RGBA image, pivot noted in PARTS) ----
def draw_head(p, cid):
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    skin, hair, prim, sec, acc, metal = (hx(p[k]) for k in ("skin", "hair", "primary", "secondary", "accent", "metal"))
    # face (profile, facing right)
    d.ellipse([14, 14, 52, 54], fill=skin, outline=OUTLINE, width=3)
    d.polygon([(48, 36), (58, 40), (48, 44)], fill=skin, outline=OUTLINE)  # nose
    d.ellipse([40, 30, 46, 36], fill=(30, 30, 40, 255))  # eye
    d.arc([36, 38, 52, 50], 0, 120, fill=(120, 70, 50, 255), width=2)  # mouth
    if cid == "knight":
        d.pieslice([12, 4, 54, 40], 180, 360, fill=metal, outline=OUTLINE, width=3)
        d.rectangle([12, 22, 54, 27], fill=shade(metal, .8))
        d.polygon([(30, 4), (38, -2), (40, 10), (30, 12)], fill=acc)
        d.polygon([(28, 2), (36, -6), (38, 6), (28, 8)], fill=(200, 40, 50, 255))
    elif cid == "barbarian":
        d.pieslice([10, 8, 56, 44], 180, 330, fill=hair)
        d.polygon([(12, 18), (2, 8), (16, 10)], fill=(230, 220, 200, 255), outline=OUTLINE)  # horn L
        d.polygon([(50, 14), (60, 4), (52, 22)], fill=(230, 220, 200, 255), outline=OUTLINE)  # horn R
        d.rectangle([14, 34, 54, 58], fill=hair)  # beard
        d.rectangle([14, 34, 54, 40], fill=skin)
    elif cid == "archer":
        d.pieslice([10, 2, 56, 46], 180, 360, fill=prim, outline=OUTLINE, width=3)
        d.polygon([(12, 20), (12, 52), (24, 40), (20, 18)], fill=shade(prim, .75))  # hood tail
        d.ellipse([16, 44, 24, 56], fill=hair)  # braid
    elif cid == "wizard":
        d.polygon([(8, 30), (34, -14), (50, 30)], fill=prim, outline=OUTLINE, width=3)
        d.ellipse([4, 26, 58, 36], fill=shade(prim, .7), outline=OUTLINE, width=2)  # brim
        d.polygon([(28, 2), (32, -6), (36, 2), (32, 6)], fill=acc)  # star
        d.rectangle([22, 40, 52, 62], fill=(235, 235, 235, 255))  # beard
        d.rectangle([22, 40, 52, 45], fill=skin)
    elif cid == "rogue":
        d.pieslice([10, 2, 56, 46], 180, 360, fill=prim, outline=OUTLINE, width=3)
        d.rectangle([14, 34, 56, 50], fill=shade(prim, .65))  # mask
        d.ellipse([40, 30, 47, 36], fill=acc)
    elif cid == "cleric":
        d.pieslice([12, 6, 54, 42], 180, 360, fill=hair)
        d.arc([14, 6, 52, 30], 180, 360, fill=acc, width=4)  # circlet
        d.ellipse([30, 8, 38, 16], fill=acc, outline=OUTLINE)
        d.rectangle([16, 42, 26, 62], fill=hair)
    elif cid == "lancer":
        d.pieslice([12, 4, 54, 40], 180, 360, fill=metal, outline=OUTLINE, width=3)
        d.polygon([(14, 16), (0, 8), (16, 26)], fill=acc)  # wing
        d.rectangle([30, 2, 36, 14], fill=acc, outline=OUTLINE)
    elif cid == "crossbowman":
        d.pieslice([12, 8, 54, 38], 180, 360, fill=prim, outline=OUTLINE, width=3)
        d.rectangle([10, 24, 56, 30], fill=shade(prim, .7))
        d.ellipse([44, 6, 54, 16], fill=acc)  # cap badge
    elif cid == "necromancer":
        d.pieslice([10, 2, 56, 48], 180, 360, fill=prim, outline=OUTLINE, width=3)
        d.ellipse([36, 28, 44, 36], fill=acc); d.ellipse([24, 40, 52, 58], fill=shade(prim, .7))  # cowl shadow
        d.ellipse([40, 30, 46, 36], fill=acc)
    elif cid == "paladin":
        d.pieslice([12, 4, 54, 40], 180, 360, fill=metal, outline=OUTLINE, width=3)
        d.arc([16, -4, 50, 18], 180, 360, fill=acc, width=4)  # halo arc
        d.rectangle([14, 42, 24, 62], fill=hair)
    return im

def draw_torso(p, cid):
    im = Image.new("RGBA", (56, 72), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    prim, sec, acc, metal = hx(p["primary"]), hx(p["secondary"]), hx(p["accent"]), hx(p["metal"])
    dark = hx(p["dark"])
    d.rounded_rectangle([8, 4, 48, 68], 8, fill=prim, outline=OUTLINE, width=3)
    d.rounded_rectangle([14, 10, 42, 40], 5, fill=sec)
    if cid in ("knight", "paladin"):
        d.rectangle([25, 10, 31, 52], fill=acc); d.rectangle([16, 22, 40, 28], fill=acc)  # cross
    elif cid == "cleric":
        d.ellipse([20, 14, 36, 30], fill=acc, outline=OUTLINE); d.rectangle([26, 8, 30, 38], fill=(255, 255, 255, 255))
    elif cid == "barbarian":
        d.polygon([(8, 4), (48, 4), (40, 30), (16, 30)], fill=sec)  # fur pelt
        for x in (14, 24, 34): d.line([x, 26, x + 3, 34], fill=dark, width=2)
    elif cid == "wizard":
        for x, y in ((18, 18), (32, 28), (22, 42)): d.polygon([(x, y-5), (x+2, y), (x, y+5), (x-2, y)], fill=acc)
        d.rectangle([8, 52, 48, 58], fill=acc)  # sash
    elif cid == "necromancer":
        d.line([16, 14, 40, 44], fill=acc, width=3); d.line([40, 14, 16, 44], fill=acc, width=3)
        d.ellipse([23, 24, 33, 34], fill=(230, 230, 220, 255), outline=OUTLINE)  # skull amulet
    elif cid == "archer":
        d.line([10, 8, 46, 56], fill=hx(p["hair"]), width=5)  # strap
    elif cid == "rogue":
        d.rectangle([8, 30, 48, 38], fill=dark); d.rectangle([24, 30, 32, 38], fill=acc)
    elif cid == "lancer":
        d.polygon([(8, 4), (28, 4), (28, 68), (8, 68)], fill=shade(prim, .8))
    elif cid == "crossbowman":
        for y in (16, 28, 40): d.line([12, y, 44, y], fill=dark, width=3)  # padded gambeson
    d.rectangle([8, 60, 48, 68], fill=dark)  # belt
    d.rectangle([24, 60, 32, 68], fill=acc, outline=OUTLINE)
    return im

def draw_hip(p, cid):
    im = Image.new("RGBA", (52, 28), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    prim, sec, dark = hx(p["primary"]), hx(p["secondary"]), hx(p["dark"])
    d.rounded_rectangle([4, 2, 48, 24], 6, fill=shade(prim, .8), outline=OUTLINE, width=3)
    if cid in ("knight", "paladin", "lancer"):
        for x in (10, 22, 34): d.polygon([(x, 22), (x+8, 22), (x+6, 28), (x+2, 28)], fill=sec, outline=OUTLINE)  # tassets
    if cid in ("wizard", "necromancer", "cleric"):
        d.polygon([(4, 20), (48, 20), (44, 28), (8, 28)], fill=sec)  # robe skirt
    return im

def limb(p, w, h, colkey, boot=False, glove=False):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    col, dark, skin = hx(p[colkey]), hx(p["dark"]), hx(p["skin"])
    d.rounded_rectangle([3, 2, w-3, h-(10 if glove else 4)], 6, fill=col, outline=OUTLINE, width=3)
    d.rectangle([3, h//2, w-3, h//2+4], fill=shade(col, .7))
    if glove: d.ellipse([3, h-14, w-3, h-1], fill=skin, outline=OUTLINE, width=2)
    return im

def draw_foot(p, cid):
    im = Image.new("RGBA", (34, 16), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    col = hx(p["dark"]) if cid not in ("knight", "paladin", "lancer") else hx(p["metal"])
    d.rounded_rectangle([2, 4, 22, 14], 4, fill=col, outline=OUTLINE, width=2)
    d.polygon([(20, 6), (32, 10), (32, 14), (20, 14)], fill=col, outline=OUTLINE)
    return im

WEAPON_SIZE = {"sword": (24, 92), "axe": (52, 92), "bow": (52, 96), "staff": (26, 112),
               "dagger": (18, 58), "mace": (32, 72), "spear": (26, 132), "crossbow": (62, 42),
               "scythe": (62, 112), "hammer": (46, 82)}
# grip point (pivot) inside weapon canvas
WEAPON_GRIP = {"sword": (12, 70), "axe": (16, 66), "bow": (26, 48), "staff": (13, 74),
               "dagger": (9, 42), "mace": (16, 52), "spear": (13, 86), "crossbow": (18, 22),
               "scythe": (16, 78), "hammer": (14, 58)}

def draw_weapon(p, wtype):
    w, h = WEAPON_SIZE[wtype]
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    metal, acc, dark = hx(p["metal"]), hx(p["accent"]), hx(p["dark"])
    wood = (122, 82, 48, 255)
    if wtype == "sword":
        d.polygon([(12, 0), (17, 12), (15, 62), (9, 62), (7, 12)], fill=metal, outline=OUTLINE)
        d.rectangle([3, 62, 21, 68], fill=acc, outline=OUTLINE); d.rectangle([9, 68, 15, 84], fill=dark, outline=OUTLINE); d.ellipse([8, 82, 16, 90], fill=acc)
    elif wtype == "axe":
        d.rectangle([13, 20, 19, 90], fill=wood, outline=OUTLINE)
        d.polygon([(18, 8), (48, 18), (48, 44), (18, 52)], fill=metal, outline=OUTLINE, width=3)
        d.polygon([(18, 52), (40, 58), (18, 64)], fill=shade(metal, .8), outline=OUTLINE)
    elif wtype == "bow":
        d.arc([-18, 4, 44, 92], -80, 80, fill=wood, width=5)
        d.line([30, 8, 30, 88], fill=(240, 240, 230, 255), width=2)
        d.line([26, 48, 50, 48], fill=wood, width=3); d.polygon([(50, 48), (44, 44), (44, 52)], fill=metal)
    elif wtype == "staff":
        d.rectangle([10, 22, 16, 110], fill=wood, outline=OUTLINE)
        d.ellipse([4, 2, 22, 22], fill=acc, outline=OUTLINE, width=2); d.ellipse([9, 7, 17, 17], fill=(255, 255, 255, 255))
    elif wtype == "dagger":
        d.polygon([(9, 0), (13, 10), (12, 36), (6, 36), (5, 10)], fill=metal, outline=OUTLINE)
        d.rectangle([4, 36, 14, 41], fill=acc); d.rectangle([7, 41, 11, 54], fill=dark)
    elif wtype == "mace":
        d.rectangle([13, 26, 19, 70], fill=wood, outline=OUTLINE)
        d.ellipse([4, 2, 28, 28], fill=metal, outline=OUTLINE, width=3)
        for x, y in ((16, 0), (2, 13), (28, 13), (16, 26)): d.ellipse([x-3, y-3, x+3, y+3], fill=acc)
    elif wtype == "spear":
        d.rectangle([11, 28, 15, 130], fill=wood, outline=OUTLINE)
        d.polygon([(13, 0), (19, 12), (16, 30), (10, 30), (7, 12)], fill=metal, outline=OUTLINE)
        d.polygon([(15, 30), (24, 38), (15, 44)], fill=acc)  # pennant
    elif wtype == "crossbow":
        d.rectangle([4, 16, 58, 24], fill=wood, outline=OUTLINE, width=2)
        d.arc([34, 2, 62, 38], -90, 90, fill=metal, width=4)
        d.rectangle([8, 8, 16, 32], fill=dark, outline=OUTLINE); d.line([52, 6, 52, 34], fill=(240, 240, 230, 255), width=2)
    elif wtype == "scythe":
        d.rectangle([13, 24, 19, 110], fill=dark, outline=OUTLINE)
        d.arc([8, -18, 66, 44], -20, 110, fill=metal, width=6)
        d.ellipse([10, 16, 22, 28], fill=acc)
    elif wtype == "hammer":
        d.rectangle([11, 22, 17, 80], fill=wood, outline=OUTLINE)
        d.rounded_rectangle([2, 2, 44, 24], 4, fill=metal, outline=OUTLINE, width=3)
        d.rectangle([19, 2, 27, 24], fill=acc)
    return im

def draw_accessory(p, cid):
    im = Image.new("RGBA", (44, 56), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    prim, sec, acc, metal = hx(p["primary"]), hx(p["secondary"]), hx(p["accent"]), hx(p["metal"])
    if cid in ("knight", "paladin"):
        d.rounded_rectangle([6, 2, 38, 50], 8, fill=prim, outline=OUTLINE, width=3)
        d.rectangle([20, 8, 24, 42], fill=acc); d.rectangle([12, 18, 32, 22], fill=acc)  # shield cross
    elif cid == "cleric":
        d.rounded_rectangle([10, 8, 34, 46], 3, fill=(240, 235, 220, 255), outline=OUTLINE, width=3)  # holy book
        d.rectangle([20, 14, 24, 32], fill=acc); d.rectangle([15, 20, 29, 24], fill=acc)
    elif cid == "archer":
        d.rounded_rectangle([14, 6, 32, 50], 4, fill=(140, 100, 60, 255), outline=OUTLINE, width=3)  # quiver
        for i in range(3): d.line([18+i*6, 14, 20+i*6, 2], fill=metal, width=3)
    elif cid in ("wizard", "necromancer"):
        d.ellipse([10, 14, 34, 38], fill=acc, outline=OUTLINE, width=2); d.ellipse([17, 21, 27, 31], fill=(255, 255, 255, 255))  # orb
    elif cid == "barbarian":
        d.ellipse([8, 10, 36, 38], fill=(235, 225, 200, 255), outline=OUTLINE, width=3)  # skull trophy
        d.ellipse([15, 20, 21, 27], fill=(30, 30, 30, 255)); d.ellipse([25, 20, 31, 27], fill=(30, 30, 30, 255))
    elif cid == "rogue":
        d.rounded_rectangle([12, 16, 32, 40], 4, fill=sec, outline=OUTLINE, width=3)  # satchel
        d.rectangle([12, 16, 32, 22], fill=acc)
    elif cid == "lancer":
        d.polygon([(22, 2), (38, 28), (22, 54), (6, 28)], fill=acc, outline=OUTLINE, width=2)  # banner diamond
        d.polygon([(22, 12), (30, 28), (22, 44), (14, 28)], fill=prim)
    elif cid == "crossbowman":
        d.rounded_rectangle([8, 18, 36, 42], 4, fill=sec, outline=OUTLINE, width=3)  # bolt case
        for i in range(3): d.line([14+i*8, 18, 14+i*8, 6], fill=metal, width=3)
    return im

PART_DEFS = [
    ("head", draw_head), ("torso", draw_torso), ("hip", draw_hip),
    ("left-upper-arm", lambda p, c: limb(p, 26, 48, "secondary")),
    ("left-lower-arm", lambda p, c: limb(p, 24, 44, "primary", glove=True)),
    ("right-upper-arm", lambda p, c: limb(p, 26, 48, "secondary")),
    ("right-lower-arm", lambda p, c: limb(p, 24, 44, "primary", glove=True)),
    ("left-upper-leg", lambda p, c: limb(p, 28, 50, "dark")),
    ("left-lower-leg", lambda p, c: limb(p, 26, 48, "secondary")),
    ("right-upper-leg", lambda p, c: limb(p, 28, 50, "dark")),
    ("right-lower-leg", lambda p, c: limb(p, 26, 48, "secondary")),
    ("left-foot", draw_foot), ("right-foot", draw_foot),
]
PIVOTS = {"head": (32, 54), "torso": (28, 66), "hip": (26, 4),
          "left-upper-arm": (13, 5), "left-lower-arm": (12, 5),
          "right-upper-arm": (13, 5), "right-lower-arm": (12, 5),
          "left-upper-leg": (14, 5), "left-lower-leg": (13, 5),
          "right-upper-leg": (14, 5), "right-lower-leg": (13, 5),
          "left-foot": (8, 6), "right-foot": (8, 6), "accessory": (22, 6)}

def build_parts(char):
    p, cid = char["palette"], char["id"]
    parts = {}
    for name, fn in PART_DEFS:
        parts[name] = fn(p, cid)
    parts["weapon"] = draw_weapon(p, char["weapon_type"])
    parts["accessory"] = draw_accessory(p, cid)
    return parts

def paste_rot(base, part, center, angle_deg, pivot):
    if angle_deg:
        part = part.rotate(angle_deg, resample=Image.BICUBIC, center=pivot)
    base.alpha_composite(part, (int(center[0] - pivot[0]), int(center[1] - pivot[1])))

def assembled_preview(parts, char):
    """Simple idle pose composed from the same parts (facing right)."""
    im = Image.new("RGBA", (220, 260), (0, 0, 0, 0))
    cx, hip_y = 105, 150
    # far limbs
    paste_rot(im, parts["left-upper-leg"], (cx - 8, hip_y), 6, PIVOTS["left-upper-leg"])
    paste_rot(im, parts["left-lower-leg"], (cx - 11, hip_y + 46), -4, PIVOTS["left-lower-leg"])
    paste_rot(im, parts["left-foot"], (cx - 10, hip_y + 90), 0, PIVOTS["left-foot"])
    paste_rot(im, parts["left-upper-arm"], (cx - 16, hip_y - 58), 10, PIVOTS["left-upper-arm"])
    paste_rot(im, parts["accessory"], (cx - 34, hip_y - 52), 6, PIVOTS["accessory"])
    paste_rot(im, parts["hip"], (cx, hip_y), 0, PIVOTS["hip"])
    paste_rot(im, parts["torso"], (cx, hip_y - 2), 0, PIVOTS["torso"])
    paste_rot(im, parts["head"], (cx + 2, hip_y - 66), 0, PIVOTS["head"])
    paste_rot(im, parts["right-upper-leg"], (cx + 8, hip_y), -6, PIVOTS["right-upper-leg"])
    paste_rot(im, parts["right-lower-leg"], (cx + 11, hip_y + 46), 4, PIVOTS["right-lower-leg"])
    paste_rot(im, parts["right-foot"], (cx + 12, hip_y + 90), 0, PIVOTS["right-foot"])
    paste_rot(im, parts["right-upper-arm"], (cx + 16, hip_y - 58), -14, PIVOTS["right-upper-arm"])
    paste_rot(im, parts["right-lower-arm"], (cx + 24, hip_y - 18), -10, PIVOTS["right-lower-arm"])
    paste_rot(im, parts["weapon"], (cx + 28, hip_y + 6), -18, WEAPON_GRIP[char["weapon_type"]])
    return im

def main():
    chars = json.load(open(os.path.join(os.path.dirname(__file__), "characters.json")))["characters"]
    manifest = {"magenta": "#FF00FF", "characters": {}}
    F_TITLE, F_LAB = font(30), font(17)
    for char in chars:
        parts = build_parts(char)
        sheet = Image.new("RGBA", (1400, 920), MAGENTA)
        d = ImageDraw.Draw(sheet)
        d.rectangle([0, 0, 1400, 64], fill=(24, 18, 32, 255))
        d.text((18, 14), f"{char['name']}  -  {char['title']}  -  {char['weapon_label']}", font=F_TITLE, fill=(255, 255, 255, 255))
        cells = {}
        names = list(parts.keys())
        cols, cw, chh, x0, y0 = 5, 190, 200, 16, 84
        for i, name in enumerate(names):
            cx, cy = x0 + (i % cols) * cw, y0 + (i // cols) * chh
            d.rectangle([cx, cy, cx + cw - 10, cy + 30], fill=(24, 18, 32, 255))
            d.text((cx + 8, cy + 6), name, font=F_LAB, fill=(255, 255, 255, 255))
            part = parts[name]
            px, py = cx + (cw - 10 - part.width) // 2, cy + 42
            sheet.alpha_composite(part, (px, py))
            cells[name] = {"x": px, "y": py, "w": part.width, "h": part.height,
                           "pivot": list(WEAPON_GRIP[char["weapon_type"]] if name == "weapon" else PIVOTS[name])}
        prev = assembled_preview(parts, char)
        sheet.alpha_composite(prev, (1140, 92))
        d.rectangle([1140, 64 + 8, 1360, 102], fill=(24, 18, 32, 255))
        d.text((1148, 78), "ASSEMBLED", font=F_LAB, fill=(255, 255, 255, 255))
        d.rectangle([16, 884, 900, 912], fill=(24, 18, 32, 255))
        d.text((24, 890), f"speed {char['speed']}  jump {char['jump_velocity']}  attack: {char['attack']['label']}", font=F_LAB, fill=(255, 255, 255, 255))
        path = os.path.join(OUT, f"{char['id']}_sheet.png")
        sheet.convert("RGB").save(path)
        manifest["characters"][char["id"]] = {"sheet": path, "cells": cells,
                                              "weapon_grip": list(WEAPON_GRIP[char["weapon_type"]])}
        print(f"sheet: {path} ({len(cells)} parts)")
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print("manifest saved")

if __name__ == "__main__":
    main()
