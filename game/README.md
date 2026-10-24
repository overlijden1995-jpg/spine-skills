# Medieval Motion Lab (Godot 4)

A runnable proof-of-concept for the requested sidescroller comparison. Four distinct fighters share one obstacle course and are animated with individual phase offsets. The demo draws proxy characters in GDScript so it runs without a Spine runtime/plugin.

## Run

Open this folder in Godot 4.2+ and press **F6/F5**. Controls: **Space** pause/resume, **R** reset, **L** toggle labels. The built-in course scrolls continuously; each warrior runs, jumps and attacks.

## Art and rig pipeline

AI-generated concept sheets are in `../assets/`: `concept_body_parts.png`, `concept_torsos.png`, and `concept_limbs.png`. They use a magenta key background. The concept generation is exploratory: generated art can contain inconsistent anatomy, merged parts, and edge artifacts. See `../scripts/extract_magenta.py` for deterministic color-key extraction into transparent PNGs. Review and hand-correct crops before using them in a production rig.

`spine/warrior_config.json` describes a hierarchical 2D skeleton, attachment regions and idle/walk/run/jump/attack animations. Generate a Spine 4.2 JSON file with:

```sh
python ../scripts/build_spine_json.py --config spine/warrior_config.json --output spine/warrior.json
```

That output is a Spine authoring interchange file, not a compiled Spine binary. Open/import it in Spine Editor, assign the extracted attachments, tune pivots/weights, and export using the Spine Editor/runtime version you license. This repository does not bundle Spine Editor, a Spine runtime, or a Godot Spine plugin. Godot's demo currently uses the standalone vector proxy animation rather than claiming to play the Spine JSON.

## Deliverable scope

The modular art set is now organized as ten dedicated sheets for four total fighters: heads, torsos, upper arms, forearms, hands, upper legs, lower legs, boots, weapons, and accessories. See `../assets/sheets/README.md` for the sheet inventory and extraction guidance. The art still needs cleanup and consistent pivoting before production use. `scripts/build_spine_json.py` is the repository's existing Spine 4.2 skeleton/animation builder. The video can be captured from the running Godot project with Godot's Movie Maker mode or a screen recorder; no video is included because a Godot executable is not installed in this workspace.
