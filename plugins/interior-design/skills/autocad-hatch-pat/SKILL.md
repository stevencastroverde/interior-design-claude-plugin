---
name: autocad-hatch-pat
version: "0.2.0"
description: Generate AutoCAD-compatible .pat hatch pattern files from images or descriptions of tile/brick/stone patterns. Use this skill whenever the user mentions: PAT file, hatch pattern, AutoCAD hatch, tile pattern, brick pattern, stone pattern, repeating pattern for CAD, Revit pattern, custom hatch, or any request to create a .pat file. Also trigger when the user uploads a screenshot or photo of a tile/material pattern and wants to use it in CAD. The skill visualizes the pattern interactively BEFORE generating the file so the user can adjust dimensions and confirm before output.
---

# AutoCAD Hatch Pattern Generator

Converts images or descriptions of repeating tile/brick/stone patterns into production-ready AutoCAD `.pat` files. Always shows a live visual preview and gets user approval before generating the file.

---

## Workflow

### Step 1 — Gather Input

Accept one of:
- **Screenshot or photo** of a tile/material pattern (preferred)
- **Text description** with tile names and dimensions

If an image is provided, analyze it carefully:
- Count tile types (e.g., one field tile + one accent tile)
- Estimate the aspect ratio and relative sizes of each tile
- Identify the offset pattern (none / 1/2 / 1/3 / custom)
- Note if tiles run horizontally or vertically

Ask for any missing critical information. The minimum needed is:
- Tile width(s) and height(s) in inches
- Grout joint width in inches
- Row offset amount (0, 1/2, 1/3, etc.)
- Orientation (tiles run horizontal = landscape, or vertical = portrait)
- Pattern name for the file (suggest one from context, ≤31 chars, no spaces/slashes)

**Always ask about grout joint width** — this is the most commonly forgotten dimension and makes a big difference to output quality. Common values: 1/16" (0.0625), 1/8" (0.125), 3/16" (0.1875), 1/4" (0.25).

---

### Step 2 — Visualize the Pattern

Before generating any file, build an **interactive HTML visualization** using the `show_widget` tool. If `show_widget` is unavailable, present a text table of the pattern dimensions (tile sizes, grout width, offset, repeat unit) and ask the user to confirm before proceeding to Step 3.

Read `references/visualization.md` (in this skill's directory) for full widget implementation details and the editable parameter panel spec.

The visualization must:
- Render the tile pattern to approximate scale in a canvas (600×400px minimum)
- Show grout joints as a contrasting color (light gray on white tiles, or vice versa)
- Display at least 3 full repeat cycles horizontally and 3 vertically
- For mixed-tile patterns (e.g., accent + field), shade each tile type differently
- Include an editable parameter panel alongside or below the canvas with fields for all key dimensions
- Update the pattern live when parameters change
- Show a "Generate .pat File" button that, when clicked, sends a message like "generate the pat file now" to proceed

**Do not proceed to Step 3 until the user approves the visualization or clicks generate.**

---

### Step 3 — Generate the .pat File

Use the proven formula from `references/pat-math.md`. For standard tile patterns the algorithm is:

```
row_height = tile_height + grout
horiz_period = sum of (tile_width + grout) for each tile in one horizontal unit
offset_per_row = horiz_period × offset_fraction
vert_repeat = num_offset_rows × row_height

# Line 1: horizontal grout joints (continuous, one family covers all rows)
"0, 0, 0, 0, {row_height}"

# Lines 2+: one vertical line family per joint per row
for each row in range(num_offset_rows):
    y0 = row × row_height
    x_shift = row × offset_per_row
    for each grout joint in this row's tile sequence:
        x_joint = x_shift + (accumulated tile widths + grouts up to this joint)
        dash = row_height
        gap = -(vert_repeat - row_height)
        "90, {x_joint}, {y0}, 0, {horiz_period}, {dash}, {gap}"
```

For full math details and edge cases (herringbone, diagonal, mixed tiles, non-standard offsets), read `references/pat-math.md`.

**File format rules** (all mandatory — violations break AutoCAD):
- Plain ASCII only — no em dashes, curly quotes, or any non-ASCII character
- Windows CRLF line endings (`\r\n`) throughout
- Pattern name ≤ 31 characters, no spaces, no punctuation except underscore/hyphen
- File must end with a blank line
- No comments or semicolons in the data lines

**Always write the file using Python** to guarantee encoding and line endings:

```python
content = "*PATTERN_NAME, description\r\n"
content += "0, 0,0, 0,{row_height}\r\n"
# ... add all vertical line families ...
content += "\r\n"  # mandatory trailing blank line

assert all(ord(c) < 128 for c in content), "Non-ASCII found!"

with open('/path/to/output/PATTERN_NAME.pat', 'w', newline='') as f:
    f.write(content)
```

Verify with `python3 -c "data=open('file.pat','rb').read(); print('ASCII:', all(b<128 for b in data)); print('CRLF:', b'\\r\\n' in data)"` before presenting.

---

### Step 4 — Present and Install Instructions

Present the file using `present_files`. Then include AutoCAD installation steps:

1. Copy the `.pat` file to AutoCAD's Support folder (usually `C:\Users\[name]\AppData\Roaming\Autodesk\AutoCAD 20xx\[version]\Support\`)
2. Restart AutoCAD
3. Use `HATCH` command → select "Custom" pattern type → browse for the file
4. Set Scale = 1 for inch drawings, Scale = 12 for foot drawings
5. If the hatch looks too dense/sparse, adjust scale accordingly

For **Revit** users: Import via Manage → Additional Settings → Fill Patterns → New → Import. Choose "Model" pattern type for real-world dimensions.

---

## Common Pattern Types

Read `references/pat-math.md` for the specific formulas for each type.

| Pattern | Rows | Offset | Vertical families needed |
|---|---|---|---|
| Stack bond | 1 | 0 | 1 per grout joint |
| Running bond (1/2) | 2 | 0.5 | 2 per grout joint |
| Running bond (1/3) | 3 | 0.333 | 3 per grout joint |
| Mixed tiles (accent+field, 1/3) | 3 | 0.333 | 6 (2 joints × 3 rows) |
| Herringbone | Complex | — | See pat-math.md |

---

## Error Handling

If the user reports the pattern looks wrong in AutoCAD:

- **Lines in wrong position**: Check x_joint calculation — verify x_shift is applied correctly per row
- **Pattern too dense / rejected**: Tell user to increase HPMAXLINES via `(setenv "MaxHatch" "10000000")` in AutoCAD console, or simplify the pattern
- **Pattern tiles but with gaps**: The horiz_period or vert_repeat is incorrect — recalculate
- **Lines run continuously instead of per-tile**: The dash/gap values are wrong — gap must be large enough to skip non-active rows
- **File not recognized**: Check for non-ASCII characters, missing trailing blank line, or name > 31 chars
