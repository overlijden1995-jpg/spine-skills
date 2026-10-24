# Four-character modular art set

The ten production-target sheets in this folder are dedicated body-part/gear categories for **four total fighters** (silver knight, russet rogue, blue guard, burgundy mage). Each sheet uses a magenta key background and presents the same four variants where possible:

1. `heads.png` — four manually selected/cropped head concepts from the generated head sheet.
2. `torsos.png` — torso armor and clothing.
3. `upper_arms.png` — shoulders and upper arms.
4. `forearms.png` — forearms/bracers.
5. `hands.png` — hands/gauntlets.
6. `upper_legs.png` — thighs.
7. `lower_legs.png` — greaves and lower legs.
8. `boots.png` — footwear.
9. `weapons.png` — each fighter's signature weapon.
10. `accessories.png` — shield, pouch, cape, and satchel.

These are AI-generated concept assets, not production-clean cutouts: dimensions and exact pivots may differ, and the head sheet is assembled from selected regions of the initial generated sheet. Run `python scripts/extract_magenta.py assets/sheets/<sheet>.png --out assets/extracted/<name>` to remove the key; review output and hand-correct borders/overlap before rigging.
