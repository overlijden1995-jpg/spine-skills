#!/usr/bin/env bash
# Full PoC pipeline: sheets -> extraction -> Spine rigs -> video.
# Requires: pip install Pillow numpy opencv-python-headless imageio imageio-ffmpeg
set -e
cd "$(dirname "$0")"
python3 generate_sheets.py
python3 extract_sprites.py
python3 build_spine_rigs.py
python3 render_video.py
python3 validate_poc.py
echo "DONE -> output/poc_video.mp4"
