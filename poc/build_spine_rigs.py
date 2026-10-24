#!/usr/bin/env python3
"""Build Spine 4.2 rigs for all 10 characters using the repo's own scripts
(scripts/build_spine_json.py + scripts/make_atlas.py + generate_spine_player.py).
Bone/slot names match the presets in build_spine_json.py so its
idle/walk/run/jump/attack generators animate every character.
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(__file__)
REPO = os.path.dirname(ROOT)
REPORT = json.load(open(os.path.join(ROOT, "extracted", "extraction_report.json")))
CHARS = json.load(open(os.path.join(ROOT, "characters.json")))["characters"]

BONES = [
    {"name": "root"},
    {"name": "hip", "parent": "root", "x": 0, "y": 98, "length": 14},
    {"name": "torso", "parent": "hip", "x": 0, "y": 6, "length": 58},
    {"name": "neck", "parent": "torso", "x": 0, "y": 60, "length": 8},
    {"name": "head", "parent": "neck", "x": 0, "y": 6, "length": 30},
    {"name": "left-upper-arm", "parent": "torso", "x": -11, "y": 50, "length": 40},
    {"name": "left-lower-arm", "parent": "left-upper-arm", "x": 0, "y": -40, "length": 38},
    {"name": "right-upper-arm", "parent": "torso", "x": 11, "y": 50, "length": 40},
    {"name": "right-lower-arm", "parent": "right-upper-arm", "x": 0, "y": -40, "length": 38},
    {"name": "left-upper-leg", "parent": "hip", "x": -7, "y": 0, "length": 44},
    {"name": "left-lower-leg", "parent": "left-upper-leg", "x": 0, "y": -44, "length": 42},
    {"name": "left-foot", "parent": "left-lower-leg", "x": 0, "y": -42, "length": 16},
    {"name": "right-upper-leg", "parent": "hip", "x": 7, "y": 0, "length": 44},
    {"name": "right-lower-leg", "parent": "right-upper-leg", "x": 0, "y": -44, "length": 42},
    {"name": "right-foot", "parent": "right-lower-leg", "x": 0, "y": -42, "length": 16},
    {"name": "weapon-bone", "parent": "right-lower-arm", "x": 0, "y": -38, "length": 20},
]
SLOT_BONE = {
    "left-upper-arm": "left-upper-arm", "left-lower-arm": "left-lower-arm",
    "right-upper-arm": "right-upper-arm", "right-lower-arm": "right-lower-arm",
    "left-upper-leg": "left-upper-leg", "left-lower-leg": "left-lower-leg",
    "right-upper-leg": "right-upper-leg", "right-lower-leg": "right-lower-leg",
    "left-foot": "left-foot", "right-foot": "right-foot",
    "hip": "hip", "torso": "torso", "head": "head",
    "weapon": "weapon-bone", "accessory": "left-lower-arm",
}
DRAW_ORDER = ["left-upper-arm", "left-lower-arm", "accessory", "left-upper-leg",
              "left-lower-leg", "left-foot", "hip", "torso", "head",
              "right-upper-leg", "right-lower-leg", "right-foot",
              "right-upper-arm", "right-lower-arm", "weapon"]

def shoot_anim():
    kf = lambda t, a: {"time": t, "angle": a}
    return {"bones": {
        "right-upper-arm": {"rotate": [kf(0, 0), kf(0.15, -78), kf(0.55, -78), kf(0.8, 0)]},
        "left-upper-arm": {"rotate": [kf(0, 0), kf(0.15, -52), kf(0.55, -52), kf(0.8, 0)]},
        "left-lower-arm": {"rotate": [kf(0, 0), kf(0.15, -18), kf(0.55, -18), kf(0.8, 0)]},
        "torso": {"rotate": [kf(0, 0), kf(0.15, 6), kf(0.55, 6), kf(0.8, 0)]},
        "head": {"rotate": [kf(0, 0), kf(0.15, -4), kf(0.8, 0)]},
    }}

def main():
    for char in CHARS:
        cid = char["id"]
        rep = REPORT[cid]
        attachments = {}
        for name, info in rep.items():
            w, h = info["size"]; px, py = info["pivot"]
            attachments[name] = {"width": w, "height": h,
                                 "x": round(w / 2 - px, 1), "y": round(py - h / 2, 1)}
        slots = [{"name": n, "bone": SLOT_BONE[n], "attachment": n} for n in DRAW_ORDER if n in rep]
        custom = {}
        if char["attack"]["kind"] == "projectile":
            custom["shoot"] = shoot_anim()
        config = {
            "skeleton": {"name": cid, "width": 200, "height": 230},
            "bones": BONES, "slots": slots, "attachments": attachments,
            "animations": ["idle", "walk", "run", "jump", "attack"],
            "custom_animations": custom,
        }
        outdir = os.path.join(ROOT, "spine", cid)
        os.makedirs(outdir, exist_ok=True)
        cfg_path = os.path.join(outdir, "config.json")
        json.dump(config, open(cfg_path, "w"), indent=1)
        parts_dir = os.path.join(ROOT, "extracted", cid)
        for cmd in (
            [sys.executable, os.path.join(REPO, "scripts", "build_spine_json.py"),
             "--config", cfg_path, "--output", os.path.join(outdir, "skeleton.json")],
            [sys.executable, os.path.join(REPO, "scripts", "make_atlas.py"),
             "--parts", parts_dir, "--output", outdir, "--name", "skeleton"],
            [sys.executable, os.path.join(REPO, "scripts", "generate_spine_player.py"),
             "--skeleton", os.path.join(outdir, "skeleton.json"),
             "--atlas", os.path.join(outdir, "skeleton.atlas"),
             "--output", os.path.join(outdir, "preview.html"),
             "--title", f"{char['name']} - {char['title']} (Spine 4.2)"],
        ):
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stdout, r.stderr); sys.exit(1)
        d = json.load(open(os.path.join(outdir, "skeleton.json")))
        print(f"spine {cid}: bones={len(d['bones'])} slots={len(d['slots'])} "
              f"anims={list(d['animations'])} spine={d['skeleton']['spine']}")

if __name__ == "__main__":
    main()
