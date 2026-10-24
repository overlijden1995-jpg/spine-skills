#!/usr/bin/env python3
"""Render the PoC video.

This is a deterministic, fixed-step (30 fps) mirror of the Godot scene in
poc/godot_project (scripts/Main.gd + scripts/Character.gd): it reads the
SAME res data (characters.json), runs the SAME course state machine
(title -> run/jump -> attack -> run -> celebrate), the SAME physics
(speed / jump_velocity / gravity / glide & double-jump specials) and the
SAME pose curves as the Spine presets. It exists so the film can be
rendered head-less; in Godot the identical run is recorded with
`--write-movie` (see poc/README.md).
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(__file__)
W, H, FPS = 960, 540, 30
SC = W / 1152.0            # Godot viewport is 1152x648
DATA = json.load(open(os.path.join(ROOT, "characters.json")))
REPOR = json.load(open(os.path.join(ROOT, "extracted", "extraction_report.json")))
COURSE = DATA["course"]

def font(sz, bold=True):
    p = f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf"
    return ImageFont.truetype(p, sz)

def hx(c):
    c = c.lstrip('#'); return tuple(int(c[i:i+2], 16) for i in (0, 2, 4)) + (255,)

# ---------- part cache ----------
PARTS = {}
def parts_for(char):
    if char["id"] in PARTS: return PARTS[char["id"]]
    out = {}
    s = SC * float(char.get("scale", 1.0))
    for name, info in REPOR[char["id"]].items():
        im = Image.open(os.path.join(ROOT, "extracted", char["id"], f"{name}.png")).convert("RGBA")
        nw, nh = max(1, round(im.width * s)), max(1, round(im.height * s))
        im = im.resize((nw, nh), Image.LANCZOS)
        pad = max(nw, nh)  # rotation-safe padding
        padded = Image.new("RGBA", (nw + 2 * pad, nh + 2 * pad), (0, 0, 0, 0))
        padded.alpha_composite(im, (pad, pad))
        pv = (info["pivot"][0] * s + pad, info["pivot"][1] * s + pad)
        out[name] = (padded, pv)
    PARTS[char["id"]] = out
    return out

def paste_rot(base, part, joint, ang_deg):
    """Draw part so its pivot lands on `joint`. Parts are pre-padded in
    parts_for() so rotation never clips a tall part (e.g. a sword)."""
    im, pv = part
    if abs(ang_deg) > 0.01:
        im = im.rotate(ang_deg, resample=Image.BICUBIC, center=pv, expand=False)
    base.alpha_composite(im, (round(joint[0] - pv[0]), round(joint[1] - pv[1])))

def rot_vec(v, deg):
    r = math.radians(deg); c, s = math.cos(r), math.sin(r)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)   # screen coords, +deg = clockwise visually

def add(a, b): return (a[0] + b[0], a[1] + b[1])
def mul(v, k): return (v[0] * k, v[1] * k)

# ---------- poses (mirror Character.gd / Spine presets) ----------
def pose_angles(state, t, phase, char, attack_k=0.0):
    A = dict(torso=0, head=0, lua=0, lla=0, rua=0, rla=0, lul=0, lll=0, rul=0, rll=0,
             lfoot=0, rfoot=0, hip_dy=0, weapon=-20)
    s, c = math.sin(phase), math.cos(phase)
    if state == "idle":
        A.update(torso=1.5 * math.sin(t * 3.9), head=-2 * math.sin(t * 3.9 + .4),
                 rua=3 * math.sin(t * 3.9), lua=-3 * math.sin(t * 3.9),
                 rul=2, lul=-2, rll=2, lll=2, hip_dy=1.5 * math.sin(t * 7.8), weapon=-160 + 180)
    elif state in ("run", "walk"):
        amp = 38 if state == "run" else 26
        A.update(rul=amp * s, lul=-amp * s, rll=max(0, -52 * c) + 6, lll=max(0, 52 * c) + 6,
                 rfoot=-amp * .4 * s, lfoot=amp * .4 * s, rua=-amp * .8 * s, lua=amp * .8 * s,
                 rla=-18 - 10 * c, lla=-18 + 10 * c, torso=7 + 3 * math.sin(phase * 2),
                 head=-5, hip_dy=-abs(s) * 6, weapon=30 + 8 * s)
    elif state == "air":
        A.update(rul=-28, lul=14, rll=42, lll=18, rua=-52, lua=40, rla=-24, lla=-14,
                 torso=-4, head=-6, weapon=40)
    elif state == "attack":
        atk = char["attack"]
        if atk["kind"] == "projectile":
            aim = math.sin(min(attack_k * 3, 1) * math.pi / 2)
            A.update(rua=78 * aim, lua=52 * aim, lla=18 * aim, torso=6 * aim, head=-4 * aim,
                     rul=10, lul=-12, rll=8, lll=10, weapon=95 * aim)
        else:
            k = attack_k
            if k < .35: ang = -55 * (k / .35)          # wind-up (arm back)
            elif k < .6: ang = -55 + 150 * ((k - .35) / .25)  # strike forward
            else: ang = 95 - 95 * ((k - .6) / .4)      # recover
            A.update(rua=ang, rla=ang * .35 - 10, torso=ang * .12, rul=10, lul=-12,
                     rll=8, lll=10, weapon=ang + 95)
    elif state == "celebrate":
        A.update(rua=150 + 12 * math.sin(t * 10), lua=130 - 12 * math.sin(t * 10),
                 torso=3 * math.sin(t * 5), head=-4, hip_dy=-abs(math.sin(t * 6)) * 8, weapon=150)
    return A
    # NB weapon angle: weapon art extends UP from its grip, so `weapon` is the
    # absolute screen angle of the weapon's up-axis relative to straight-up.

def draw_character(base, char, pos, state, t, phase, attack_k=0.0):
    """pos = feet position (screen px). FK mirroring Character.gd."""
    P = parts_for(char)
    s = SC * float(char.get("scale", 1.0))
    A = pose_angles(state, t, phase, char, attack_k)
    x, feet = pos
    hip = (x, feet - 98 * s + A["hip_dy"] * SC)
    up = rot_vec((0, -1), A["torso"])                    # torso up-axis
    perp = rot_vec((1, 0), A["torso"])
    shoulder_c = add(hip, mul(up, 56 * s))
    neck = add(hip, mul(up, 66 * s))
    def limb(joint, ang, length):
        d = rot_vec((0, 1), ang)                         # down-axis rotated
        return add(joint, mul(d, length * s / float(char.get("scale", 1.0)) * float(char.get("scale", 1.0)) / 1.0 * (SC / SC))), d
    # simpler: lengths already in Godot px -> scale by SC*char_scale via s/len ratio
    def seg(joint, ang, godot_len):
        d = rot_vec((0, 1), -ang)  # +ang swings the limb forward (+x)
        return add(joint, mul(d, godot_len * SC * float(char.get("scale", 1.0)))), d
    sh_l = add(shoulder_c, mul(perp, -11 * SC * float(char.get("scale", 1.0))))
    sh_r = add(shoulder_c, mul(perp, 11 * SC * float(char.get("scale", 1.0))))
    hip_l = add(hip, mul(perp, -7 * SC)); hip_r = add(hip, mul(perp, 7 * SC))
    el_l, _ = seg(sh_l, A["lua"], 40); ha_l, d_lf = seg(el_l, A["lua"] + A["lla"], 38)
    el_r, _ = seg(sh_r, A["rua"], 40); ha_r, d_rf = seg(el_r, A["rua"] + A["rla"], 38)
    kn_l, _ = seg(hip_l, A["lul"], 44); an_l, _ = seg(kn_l, A["lul"] + A["lll"], 42)
    kn_r, _ = seg(hip_r, A["rul"], 44); an_r, _ = seg(kn_r, A["rul"] + A["rll"], 42)
    # draw order = Spine slot order
    paste_rot(base, P["left-upper-arm"], sh_l, A["lua"])
    paste_rot(base, P["left-lower-arm"], el_l, A["lua"] + A["lla"])
    paste_rot(base, P["accessory"], ha_l, A["lua"] + A["lla"])
    paste_rot(base, P["left-upper-leg"], hip_l, A["lul"])
    paste_rot(base, P["left-lower-leg"], kn_l, A["lul"] + A["lll"])
    paste_rot(base, P["left-foot"], an_l, A["lul"] + A["lll"] + A["lfoot"])
    paste_rot(base, P["hip"], hip, A["torso"])
    paste_rot(base, P["torso"], add(hip, mul(up, 6 * SC)), A["torso"])
    paste_rot(base, P["head"], neck, A["torso"] + A["head"])
    paste_rot(base, P["right-upper-leg"], hip_r, A["rul"])
    paste_rot(base, P["right-lower-leg"], kn_r, A["rul"] + A["rll"])
    paste_rot(base, P["right-foot"], an_r, A["rul"] + A["rll"] + A["rfoot"])
    paste_rot(base, P["right-upper-arm"], sh_r, A["rua"])
    paste_rot(base, P["right-lower-arm"], el_r, A["rua"] + A["rla"])
    # weapon paste angle per type (art is drawn grip-down, blade/bolt forward)
    wt = char["weapon_type"]
    if state == "attack" and char["attack"]["kind"] == "projectile":
        wrot = {"bow": 0, "crossbow": 0, "staff": -12, "scythe": -70}.get(wt, -60)
    elif state == "attack":
        wrot = -(A["rua"] + 55)  # wind-up: blade up/back; strike: blade forward
    elif wt in ("bow", "crossbow"):
        wrot = -18
    elif wt in ("staff", "scythe"):
        wrot = -24
    else:
        wrot = -A["weapon"]
    paste_rot(base, P["weapon"], ha_r, wrot)
    hand = ha_r
    return hand

# ---------- world background (pre-rendered, camera crops it) ----------
def build_world():
    ww = int(COURSE["world_width"] * SC)
    im = Image.new("RGBA", (ww, H), (23, 18, 51, 255)); d = ImageDraw.Draw(im)
    for i in range(160):  # stars
        sx, sy = (i * 613) % ww, (i * 271) % 200
        d.ellipse([sx, sy, sx + 2, sy + 2], fill=(200, 200, 230, 160))
    d.ellipse([ww - 260, 30, ww - 200, 90], fill=(232, 227, 216, 255))  # moon
    # distant castle + hills (parallax baked)
    for bx in range(200, ww, 900):
        d.rectangle([bx, 210, bx + 150, 330], fill=(38, 32, 66, 255))
        d.rectangle([bx + 16, 180, bx + 44, 330], fill=(38, 32, 66, 255))
        d.rectangle([bx + 106, 180, bx + 134, 330], fill=(38, 32, 66, 255))
        d.polygon([(bx + 16, 180), (bx + 30, 158), (bx + 44, 180)], fill=(90, 40, 60, 255))
        d.polygon([(bx + 106, 180), (bx + 120, 158), (bx + 134, 180)], fill=(90, 40, 60, 255))
        for wy in (240, 280):
            d.rectangle([bx + 62, wy, bx + 74, wy + 12], fill=(242, 194, 48, 255))
    d.polygon([(0, 434)] + [(x, 434 - 40 * math.sin(x / 500.0)) for x in range(0, ww, 60)] + [(ww, 434)], fill=(30, 42, 54, 255))
    gy = lambda v: v * SC
    for p in COURSE["platforms"]:
        X, Y, Wd, Ht = p["x"] * SC, p["y"] * SC, p["w"] * SC, p["h"] * SC
        if p["type"] == "ground":
            d.rectangle([X, Y, X + Wd, Y + Ht], fill=(87, 65, 42, 255))
            d.rectangle([X, Y, X + Wd, Y + 13], fill=(63, 122, 58, 255))
            d.rectangle([X, Y + 13, X + Wd, Y + 18], fill=(46, 92, 44, 255))
            for gx in range(int(X) + 14, int(X + Wd), 46): d.line([gx, Y + 3, gx - 4, Y - 5], fill=(80, 150, 74, 255), width=2)
        else:
            d.rectangle([X, Y, X + Wd, Y + Ht], fill=(110, 81, 54, 255))
            d.rectangle([X, Y, X + Wd, Y + 5], fill=(138, 106, 68, 255))
            d.line([X + 12, Y + Ht, X + 4, Y + Ht + 46], fill=(74, 56, 38, 255), width=5)
            d.line([X + Wd - 12, Y + Ht, X + Wd - 4, Y + Ht + 46], fill=(74, 56, 38, 255), width=5)
    # start + finish banners
    d.rectangle([50, 316, 58, 434], fill=(138, 106, 68, 255))
    d.polygon([(58, 320), (116, 330), (58, 342)], fill=(201, 55, 44, 255))
    fx = (COURSE["finish_x"] + 40) * SC
    d.rectangle([fx, 300, fx + 8, 434], fill=(138, 106, 68, 255))
    for r in range(4):
        for c_ in range(4):
            d.rectangle([fx + 8 + c_ * 11, 304 + r * 11, fx + 19 + c_ * 11, 315 + r * 11],
                        fill=(255, 255, 255, 255) if (r + c_) % 2 == 0 else (28, 28, 38, 255))
    sp = COURSE["spikes"]  # spikes at the pit floor
    for i in range(int(sp["w"] // 20)):
        sx = (sp["x"] + i * 20) * SC
        d.polygon([(sx, H), (sx + 8, H - 34), (sx + 16, H)], fill=(200, 204, 216, 255))
    # torches on ground segments
    for tx in (300, 1000, 2000, 2900):
        X = tx * SC; d.rectangle([X, 386, X + 4, 434], fill=(90, 64, 36, 255))
        d.ellipse([X - 5, 368, X + 9, 388], fill=(255, 166, 48, 255)); d.ellipse([X - 1, 374, X + 5, 386], fill=(255, 226, 138, 255))
    return im

WORLD = build_world()

def draw_dummy(d, cam, dummy_x, hit_t):
    dx = dummy_x * SC - cam; gy = COURSE["ground_y"] * SC
    tilt = min(max(hit_t, 0) * 3, 1) * 30 if hit_t >= 0 else 0
    d.line([dx, gy, dx, gy - 74], fill=(110, 81, 54, 255), width=7)
    hc = (dx + tilt * .5, gy - 92 + tilt * .25)
    d.ellipse([hc[0] - 17, hc[1] - 17, hc[0] + 17, hc[1] + 17], fill=(217, 176, 106, 255), outline=(48, 36, 26, 255), width=2)
    d.ellipse([hc[0] + 4, hc[1] - 4, hc[0] + 8, hc[1]], fill=(48, 36, 26, 255))
    d.arc([hc[0] - 25, hc[1] - 25, hc[0] + 25, hc[1] + 25], 0, 360, fill=(168, 50, 66, 255), width=4)
    d.line([dx - 28, gy - 56, dx + 28, gy - 56], fill=(110, 81, 54, 255), width=6)
    if 0 <= hit_t < .35:
        a = int(255 * (1 - hit_t * 2.5))
        d.arc([dx - 44, gy - 100, dx + 44, gy - 12], -40, 80, fill=(255, 255, 255, a), width=5)

def draw_projectile(d, pos, color, cam, wtype="staff"):
    if pos is None: return
    x, y = pos[0] * SC - cam, pos[1] * SC
    if wtype in ("bow", "crossbow"):  # arrow / bolt
        d.line([x - 26, y, x + 8, y], fill=(210, 180, 130, 255), width=3)
        d.polygon([(x + 8, y), (x - 2, y - 5), (x - 2, y + 5)], fill=(220, 224, 235, 255))
        d.polygon([(x - 26, y), (x - 18, y - 6), (x - 16, y)], fill=(200, 60, 60, 255))
        d.polygon([(x - 26, y), (x - 18, y + 6), (x - 16, y)], fill=(200, 60, 60, 255))
    else:  # magic / soul / holy orb
        d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=color[:3] + (70,))
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=color)
        d.line([x - 24, y, x - 8, y], fill=color, width=3)

# ---------- simulation (mirrors Main.gd _process) ----------
def surface_y(x, feet_y):
    best = None
    for p in COURSE["platforms"]:
        if p["x"] <= x <= p["x"] + p["w"]:
            top = p["y"]
            if top >= feet_y - 12 and (best is None or top < best): best = top
    return best

def stop_x(char):
    atk = char["attack"]; dx = COURSE["attack_trigger"]["dummy_x"]
    return dx - 380 if atk["kind"] == "projectile" else dx - atk["range"] - 24

def simulate(char):
    """Yield frame dicts at 30fps for one character's run."""
    dt = 1 / FPS
    x, y = float(COURSE["start_x"]), float(COURSE["ground_y"])
    vy, grounded, phase = 0.0, True, 0.0
    state, t = "title", 0.0
    used, dbl = set(), False
    surf, feet = None, y
    proj, hit_t, attack_done = None, -1.0, False
    run_time, total_t = 0.0, 0.0
    while True:
        total_t += dt; t += dt
        atk = char["attack"]; ev = {"x": x, "y": y, "state": state, "phase": phase,
                                    "proj": proj, "hit_t": hit_t, "grounded": grounded, "t": t}
        if state == "title":
            if t > .9: state, t = "run", 0.0
        elif state in ("run", "attack"):
            if state == "run": run_time += dt
            if state == "attack":
                ev["attack_k"] = min(t / atk["duration"], 1.0)
                if atk["kind"] == "projectile" and t >= .3 and proj is None:
                    proj = [x + 54, y - 118]
                if t >= atk["duration"]: state, t = "run", 0.0
            else:
                x += char["speed"] * dt; phase += dt * char["speed"] / 34.0
                for i, tr in enumerate(COURSE["jump_triggers"]):
                    if i not in used and grounded and x >= tr["x"]:
                        used.add(i); vy = -char["jump_velocity"] * tr["vy"]; grounded = False
                if not grounded and char.get("special") == "double_jump" and not dbl \
                        and x > COURSE["spikes"]["x"] - 40 and vy > -80:
                    vy = -char["jump_velocity"] * .72; dbl = True
                if x >= stop_x(char) and not attack_done:
                    state, t, attack_done = "attack", 0.0, True
            if state == "attack":
                vy = 0.0  # hover in place while attacking / casting
            else:
                vy += char["gravity"] * dt
                if char.get("special") == "glide" and not grounded and vy > 130: vy = 130.0
                feet = y; y += vy * dt
                surf = surface_y(x, feet)
            if surf is not None and y >= surf and vy >= 0: y, vy, grounded = surf, 0.0, True
            elif surf is None or y < (surf if surf is not None else 1e9) - 14: grounded = False
            if y > 660: y, vy, grounded = float(COURSE["ground_y"]), 0.0, True
            if x >= COURSE["finish_x"]: state, t = "done", 0.0
        elif state == "done":
            if t > 1.0: ev["last"] = True
        if proj is not None:
            proj[0] += atk.get("projectile_speed", 600) * dt
            if proj[0] >= COURSE["attack_trigger"]["dummy_x"]:
                proj = None; hit_t = 0.0
            ev["proj"] = proj
        if state == "attack" and atk["kind"] == "melee" and t >= .3 and hit_t < 0: hit_t = 0.0
        if hit_t >= 0: hit_t += dt; ev["hit_t"] = hit_t
        ev.update(x=x, y=y, state=state, grounded=grounded)
        yield ev
        if ev.get("last"): break
        if total_t > 25: break
    return run_time

# ---------- frame rendering ----------
F_TITLE, F_SUB, F_HUD, F_SMALL = font(44), font(24), font(21), font(16)

def hud(frame, char, i, ev):
    d = ImageDraw.Draw(frame, "RGBA")
    d.rectangle([0, 0, W, 86], fill=(10, 8, 20, 128))
    d.text((18, 10), f"{i+1}/10  {char['name']} — {char['title']}", font=F_HUD, fill=(255, 255, 255, 255))
    st = "ATTACK" if ev["state"] == "attack" else ("JUMP" if not ev["grounded"] else ev["state"].upper())
    d.text((18, 40), f"ANIM: {st}   WEAPON: {char['weapon_label']}   ATTACK: {char['attack']['label']}",
           font=F_SMALL, fill=(210, 210, 225, 255))
    d.rectangle([18, 66, 268, 74], fill=(0, 0, 0, 140))
    d.rectangle([18, 66, 18 + 250 * min(ev["x"] / COURSE["finish_x"], 1), 74], fill=(242, 194, 48, 255))
    if ev["state"] == "title":
        d.rectangle([W/2 - 300, H - 150, W/2 + 300, H - 62], fill=(10, 8, 20, 200))
        d.text((W/2 - 284, H - 138), f"{char['name']}  ·  {char['title']}", font=font(28), fill=(242, 194, 48, 255))
        d.text((W/2 - 284, H - 102), f"{char['weapon_label']} — {char['attack']['label']}   speed {char['speed']} · jump {char['jump_velocity']}",
               font=F_SMALL, fill=(255, 255, 255, 255))

def render_run(char, i):
    frames = []
    sim = simulate(char)
    for ev in sim:
        cam = max(0.0, min(ev["x"] * SC - 316, COURSE["world_width"] * SC - W))
        frame = WORLD.crop((int(cam), 0, int(cam) + W, H)).copy()
        d = ImageDraw.Draw(frame, "RGBA")
        draw_dummy(d, cam, COURSE["attack_trigger"]["dummy_x"], ev["hit_t"])
        state = ev["state"]
        pose = "idle" if state == "title" else ("celebrate" if state == "done" else
               ("attack" if state == "attack" else ("run" if ev["grounded"] else "air")))
        hand = draw_character(frame, char, (ev["x"] * SC - cam, ev["y"] * SC), pose,
                              ev["t"], ev["phase"], ev.get("attack_k", 0.0))
        if ev.get("proj"): draw_projectile(d, ev["proj"], hx(char["attack"]["color"]), cam, char["weapon_type"])
        hud(frame, char, i, ev)
        frames.append(frame)
    return frames

def title_card():
    im = Image.new("RGBA", (W, H), (23, 18, 51, 255)); d = ImageDraw.Draw(im)
    d.text((W/2, 92), "MEDIEVAL SIDESCROLLER", font=F_TITLE, fill=(242, 194, 48, 255), anchor="ma")
    d.text((W/2, 148), "10 Spine-rigged heroes · one obstacle course", font=F_SUB, fill=(235, 235, 245, 255), anchor="ma")
    d.text((W/2, 182), "sprite sheets (magenta) → extracted parts → Spine 4.2 rigs → Godot", font=F_SMALL, fill=(170, 170, 200, 255), anchor="ma")
    for i, char in enumerate(DATA["characters"]):
        cx = 86 + i * 88
        draw_character(im, char, (cx, 452), "idle", i * .6, 0.0)
        d.text((cx, 466), char["title"], font=font(12), fill=(255, 255, 255, 255), anchor="ma")
    d.text((W/2, 506), "same course · different speed, jump, glide / double-jump and attacks", font=F_SMALL, fill=(170, 170, 200, 255), anchor="ma")
    return im

def end_card(times):
    im = Image.new("RGBA", (W, H), (23, 18, 51, 255)); d = ImageDraw.Draw(im)
    d.text((W/2, 54), "COURSE COMPLETE — ALL 10 HEROES", font=font(32), fill=(242, 194, 48, 255), anchor="ma")
    y = 118
    for i, (char, tm) in enumerate(zip(DATA["characters"], times)):
        col = i % 2; row = i // 2
        X, Y = 70 + col * 440, y + row * 66
        draw_character(im, char, (X + 24, Y + 48), "idle", i * .5, 0.0)
        d.text((X + 56, Y + 4), f"{char['name']} — {char['title']}", font=F_SMALL, fill=(255, 255, 255, 255))
        d.text((X + 56, Y + 24), f"{char['attack']['label']}  ·  run {tm:.1f}s", font=font(13), fill=(170, 170, 200, 255))
    d.text((W/2, 478), "Built with the Spine Animation AI skill · Godot 4 project in poc/godot_project", font=F_SMALL, fill=(170, 170, 200, 255), anchor="ma")
    return im

def main():
    if "--simulate-only" in sys.argv:
        for c in DATA["characters"]:
            n, last = 0, None
            for ev in simulate(c): n += 1; last = ev
            print(f"{c['id']:14s} frames={n:4d} end_x={last['x']:.0f} state={last['state']}")
        return
    out = os.path.join(ROOT, "output", "poc_video.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ffmpeg = subprocess.run(["python3", "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
                            capture_output=True, text=True).stdout.strip()
    proc = subprocess.Popen([ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                             "-preset", "medium", out], stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    def push(im, count=1):
        raw = np.asarray(im.convert("RGB"), dtype=np.uint8).tobytes()
        for _ in range(count): proc.stdin.write(raw)
    total = 0
    push(title_card(), FPS * 2); total += FPS * 2
    times = []
    for i, char in enumerate(DATA["characters"]):
        frames = render_run(char, i)
        # estimate course run time from frames in run state
        times.append(max(1, len(frames)) / FPS)
        for fr in frames: push(fr)
        total += len(frames)
        print(f"rendered {char['id']}: {len(frames)} frames ({len(frames)/FPS:.1f}s)")
    push(end_card(times), FPS * 3); total += FPS * 3
    proc.stdin.close(); proc.wait()
    print(f"VIDEO {out}  {total} frames  {total/FPS:.1f}s")

if __name__ == "__main__":
    main()
