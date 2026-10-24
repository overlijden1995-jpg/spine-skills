#!/usr/bin/env python3
"""Validate every PoC deliverable: sheets, extraction, Spine 4.2 rigs, Godot project, video."""
import json, os, subprocess, sys

ROOT = os.path.dirname(__file__)
chars = json.load(open(os.path.join(ROOT, "characters.json")))["characters"]
fails = []
def check(cond, msg):
    print(("  OK  " if cond else "FAIL  ") + msg)
    if not cond: fails.append(msg)

for c in chars:
    cid = c["id"]
    check(os.path.exists(f"{ROOT}/sheets/{cid}_sheet.png"), f"{cid} magenta sheet")
    rep = json.load(open(f"{ROOT}/extracted/extraction_report.json"))[cid]
    check(len(rep) == 15 and all(v["components"] >= 1 for v in rep.values()), f"{cid} 15 extracted parts, 1 component each")
    d = json.load(open(f"{ROOT}/spine/{cid}/skeleton.json"))
    check(d["skeleton"]["spine"] == "4.2.0" and len(d["bones"]) == 16 and len(d["slots"]) == 15,
          f"{cid} Spine 4.2 skeleton (16 bones / 15 slots)")
    need = {"idle", "walk", "run", "jump", "attack"} | ({"shoot"} if c["attack"]["kind"] == "projectile" else set())
    check(need <= set(d["animations"]), f"{cid} animations {sorted(d['animations'])}")
    raw = open(f"{ROOT}/spine/{cid}/skeleton.json").read()
    check('"angle"' not in raw, f"{cid} no 3.8-style 'angle' keys (4.2 wire format)")
    for ext in ("skeleton.atlas", "skeleton.png", "preview.html"):
        check(os.path.exists(f"{ROOT}/spine/{cid}/{ext}"), f"{cid} spine/{ext}")
    check(len([f for f in os.listdir(f"{ROOT}/godot_project/assets/{cid}") if f.endswith(".png")]) == 15,
          f"{cid} Godot assets (15 PNGs)")

for f in ("project.godot", "Main.tscn", "scripts/Main.gd", "scripts/Character.gd", "data/characters.json", "data/pivots.json"):
    check(os.path.exists(f"{ROOT}/godot_project/{f}"), f"godot_project/{f}")
vid = f"{ROOT}/output/poc_video.mp4"
check(os.path.exists(vid) and os.path.getsize(vid) > 500_000, f"poc_video.mp4 ({os.path.getsize(vid)//1024} KB)")
ff = subprocess.run([sys.executable, "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
                    capture_output=True, text=True).stdout.strip()
info = subprocess.run([ff, "-i", vid], capture_output=True, text=True).stderr
dur = [l for l in info.splitlines() if "Duration" in l]
check(bool(dur), f"video probe: {dur[0].strip() if dur else 'n/a'}")
print("\nVALIDATION", "FAILED: " + str(fails) if fails else "PASSED (all checks)")
sys.exit(1 if fails else 0)
