# Medieval Sidescroller — Spine Cast PoC

One obstacle course, **10 medieval heroes**, each with different movement
(speed / jump / gravity, plus glide & double-jump specials) and a different
attack. Built end-to-end with this repo's Spine skill pipeline.

## ▶ The film
**`output/poc_video.mp4`** — 104 s, 960×540, 30 fps. Title card, then each
hero in turn: title idle → run → gap jump → platform climbs → attack the
training dummy (melee slash/chop/thrust/slam or arrow/bolt/magic/holy/soul
projectile) → spike-pit jump → finish-banner celebration. `poster.png` and
`contact_sheet.png` are stills from the film.

## The cast
| # | Hero | Weapon | Movement signature | Attack |
|---|------|--------|--------------------|--------|
| 1 | Ser Aldric, Knight | Longsword + Shield | balanced | Sword Slash |
| 2 | Brunhild, Barbarian | Great Axe | slow, heavy gravity, +10% scale | Overhead Chop |
| 3 | Elyra, Archer | Longbow | fast, light | Arrow Shot |
| 4 | Merlinor, Wizard | Arcane Staff | slow, **glide** (capped fall) | Magic Bolt |
| 5 | Shade, Rogue | Twin Daggers | fastest, **double-jump** the spike pit | Dagger Flurry |
| 6 | Sister Mira, Cleric | Holy Mace | medium | Holy Smite (projectile) |
| 7 | Ser Roland, Lancer | War Spear | fast, longest melee reach | Spear Thrust |
| 8 | Pietro, Crossbowman | Heavy Crossbow | heavy, fastest projectile | Crossbow Bolt |
| 9 | Morvain, Necromancer | Soul Scythe | **glide** | Soul Bolt |
| 10 | Dame Aveline, Paladin | Warhammer | tank, heaviest gravity | Hammer Slam |

All numbers live in **`characters.json`** — the single source of truth read
by the sheet generator, the Godot project (`godot_project/data/`) and the
video renderer, so the three can never drift apart.

## Pipeline (steps 1–3 of the brief)
```bash
pip install Pillow numpy opencv-python-headless imageio imageio-ffmpeg
bash poc/run_pipeline.sh        # everything below, in order
```
1. **Sprite sheets (magenta)** — `generate_sheets.py` draws 10 deconstructed
   sheets on pure `#FF00FF` (`sheets/<hero>_sheet.png` + `manifest.json`
   with exact part cells/pivots, plus an assembled preview per sheet).
   Drawing is deterministic vector art (Pillow): AI raster sheets smear the
   chroma key and break connected-component extraction, so parts are drawn
   as clean flat-shaded shapes with per-hero palettes, headgear and weapons.
2. **Programmatic extraction** — `extract_sprites.py` chroma-keys the
   magenta to alpha (with despill), runs OpenCV connected-components per
   cell to verify exactly one sprite per cell, trims to the component bbox
   and remaps pivots → `extracted/<hero>/*.png` (15 parts each) +
   `extracted/extraction_report.json`.
3. **Spine rigging** — `build_spine_rigs.py` feeds the extracted parts to
   this repo's own `scripts/build_spine_json.py`, `scripts/make_atlas.py`
   and `scripts/generate_spine_player.py`. Every hero gets a 16-bone /
   15-slot **Spine 4.2** skeleton (`spine/<hero>/skeleton.json/.atlas/.png`)
   with `idle, walk, run, jump, attack` (plus `shoot` for ranged heroes)
   and a self-contained `preview.html` (official Spine Web Player).

## Step 4 — Godot
`godot_project/` is a complete **Godot 4.3** project:
`Main.tscn` + `scripts/Main.gd` (course, camera, HUD, state machine,
projectiles, dummy) + `scripts/Character.gd` (a Node2D bone hierarchy with
the same bone names as the Spine skeletons, Sprite2D parts from
`assets/<hero>/`, pose curves mirroring the Spine presets).

```bash
godot --path poc/godot_project                                   # play
godot --path poc/godot_project --write-movie poc/output/poc_video.avi --fixed-fps 30
godot --path poc/godot_project -- --record-frames                 # or PNG frames
```

### How the shipped MP4 was rendered (transparency note)
This build sandbox cannot download the Godot binary (GitHub *release*
CDN is outside its network allow-list; the source hosts are reachable but
release assets are not), so the shipped film was rendered by
`render_video.py`: a fixed-step (30 fps) deterministic mirror of the Godot
scene that consumes the **same** `characters.json`, course geometry,
physics constants and pose curves, and draws the **same** extracted parts
with the same FK bone hierarchy. Running the Godot project with
`--write-movie` reproduces the same run inside the engine.

## Validation
`python3 poc/validate_poc.py` checks all sheets, extractions, Spine 4.2
wire format (no 3.8 `angle` keys, per-property beziers), Godot project
completeness and the video file. Course physics are simulated head-less
with `python3 poc/render_video.py --simulate-only` (all 10 heroes finish).
