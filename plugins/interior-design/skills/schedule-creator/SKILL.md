---
name: schedule-creator
description: >
  Creates a professional interior design schedule as an Excel (.xlsx) workbook —
  for a single room or an entire multi-room project at once.
  Use this skill whenever a user wants a room schedule, FF&E schedule, product schedule,
  kitchen schedule, bathroom schedule, project schedule, or any design schedule in
  spreadsheet form — even if they just say "make the schedule", "create the Excel for
  the kitchen and baths", or "build the full project schedule."
  Always produces three sheets:
  (1) a main schedule sheet with all rooms on one workbook, each separated by a
  blue section header — handles any number of rooms in a single pass,
  (2) a "Materials & Finishes" sheet that automatically pulls out paint, tile, hardwood,
  wallcovering, stone/countertop, moulding, and metal items from every room and
  organizes them by material type, and
  (3) a "Room Finish Schedule" sheet in plain CAD/Revit-compatible formatting showing
  which finishes are applied to each surface (floor, base, N/E/S/W walls, ceiling)
  per room — suitable for importing into AutoCAD and Revit technical drawings.
  Trigger when the user mentions: schedule, room schedule, FF&E schedule, product
  schedule, design schedule, material schedule, spec schedule, room finish schedule,
  finish schedule, project schedule, or when they have a list of design products and
  want an organized Excel file with codes, images, dimensions, and links.
  The schedule uses Master Abbreviation List codes (AP, PF, ST, CAB, FURN, AC, HW, etc.)
  and groups items by category with embedded product images.
  Do NOT use for mood board PDFs or product spec PDFs — use the moodboard-pdf skill for those.
---

# Schedule Creator Skill

You create a professional interior design schedule as an Excel (.xlsx) workbook —
for a single room or an entire multi-room project at once, matching the style of
the Kitchen Schedule reference format.

**Output:** A landscape Excel workbook with **three sheets**:
1. **`[Project] Schedule`** — all rooms on one sheet, each room separated by a blue section header, then light-blue category sub-headers, then product rows
2. **`Materials & Finishes`** — all material/finish items pulled from every room, organized by type (PAINT, MOULDING, HARDWOOD, TILE, WALLCOVERING, STONE, METAL)
3. **`Room Finish Schedule`** — plain CAD/Revit-compatible table listing which finish codes apply to each surface (floor, base, N, E, S, W walls, ceiling) for every room

---

## Workflow

### Step 1 — Gather product data

For each room you need:
- **Products** — title, model number, manufacturer, dimensions, notes/specs, quantity, source URL, and an image (URL or local file path)
- **Room name(s)** — e.g. "Kitchen", "Powder Room", "Primary Bath"
- **Project name** — e.g. "Intersecting Stories"
- **Studio / semester** — for the page header/footer

Products most commonly come from:
- Markdown product clippings in a folder (same format as the moodboard-pdf skill)
- A list the user provides directly
- A previously generated mood board PDF

### Step 2 — Assign abbreviation codes

Use the **Master Abbreviation List** to assign a code prefix to each product. Standard categories:

| Code   | Category              | Sheet          | Examples |
|--------|-----------------------|----------------|---------|
| AP     | Appliance             | Schedule       | Range, refrigerator, dishwasher, microwave, hood, beverage cooler |
| PF     | Plumbing Fixtures     | Schedule       | Sink, faucet, toilet, shower valve, drain |
| CAB    | Cabinetry             | Schedule       | Cabinet fronts, door styles |
| FURN   | Furniture             | Schedule       | Chairs, stools, sofas, tables, vanities |
| AC     | Accessories           | Schedule       | Pulls, hardware, mirrors, grab bars, décor |
| LF     | Light Fixtures        | Schedule       | Pendants, recessed, sconces, flush mounts |
| TXT    | Textiles              | Schedule       | Upholstery fabric, drapery (tied to a specific furniture item) |
| MISC   | Miscellaneous         | Schedule       | Anything that doesn't fit above |
| PT     | Paint                 | Mat & Fin      | Paint colors |
| BB     | Moulding / Baseboard  | Mat & Fin      | Base moulding, crown, trim |
| HW     | Hardwood              | Mat & Fin      | Wood flooring |
| FT     | Floor / Wall Tile     | Mat & Fin      | Porcelain, stone, mosaic tile |
| WT     | Wall Tile             | Mat & Fin      | Backsplash, large-format wall tile |
| WC     | Wall Coverings        | Mat & Fin      | Wallpaper, wall panels |
| ST     | Stone                 | Mat & Fin      | Countertop slabs — granite, quartz, marble (replaces legacy CT code) |
| MT     | Metal                 | Mat & Fin      | Metal trim, metal accents |

> **Stone / Countertop:** Always use **ST** (not CT) for countertop slabs. If source data uses CT codes, the build script auto-renames them to ST on the Materials & Finishes sheet.

Number items sequentially **per code prefix, globally across all rooms**: AP-1, AP-2, ST-1, ST-2, etc.

If a Master Abbreviation List PDF is available in the project folder, read it first and use those codes — they override the defaults above.

### Step 3 — Download and cache images

For each product with a URL image, download it to `_image_cache/` before building the Excel:

```python
headers_to_try = [
    {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0'},
    {'User-Agent': 'curl/7.68.0'},
    {},
]
```

Resize to thumbnail (max 110×78px) before embedding. If an image can't be downloaded, leave the cell empty — don't crash.

### Step 4 — Assign surfaces for Room Finish Schedule (interactive)

Before building the Excel, Claude must interactively ask the user to map finish codes to room surfaces. This step populates Sheet 3.

**For each room:**
1. Collect the finish codes present in that room (all PT, BB, HW, FT, WT, WC, ST, MT items).
2. Present the available codes to the user and ask which apply to each surface:
   - FLOOR
   - BASE (baseboard)
   - NORTH wall
   - EAST wall
   - SOUTH wall
   - WEST wall
   - CEILING (material / finish)
3. Multiple codes can apply to one surface — e.g. `HW-1 / FT-2` for a floor with hardwood and tile.
4. For ceiling height: ask the user to provide the height (e.g. `9'-0"`) or offer the option to leave it blank and fill in later.
5. Any surface left unassigned should remain blank in the sheet — don't guess.

**Example prompt to user:**
```
For the Kitchen (Room 101), the available finish codes are:
  HW-1  — Hardwood flooring
  FT-1  — Floor tile (entry zone)
  ST-1  — Granite countertop
  PT-1  — Wall paint
  BB-1  — Base moulding

Which codes apply to each surface?
  FLOOR  →
  BASE   →
  NORTH  →
  EAST   →
  SOUTH  →
  WEST   →

What is the ceiling height? (or leave blank)
What is the ceiling material / finish? (or leave blank)
Any notes for this room?
```

Store the user's answers in the `surfaces`, `ceiling_height`, `ceiling_finish`, and `rfs_notes` fields of the room JSON (see format below).

### Step 5 — Build the Excel file

Use the build script at `scripts/build_schedule.py`:

```bash
python3 scripts/build_schedule.py \
  --output "/path/to/Project Schedule.xlsx" \
  --project "Intersecting Stories" \
  --studio "ARCH X482.2 — Design Studio II" \
  --semester "SPRING 2026" \
  --data "/path/to/products.json"
```

Or call `build_schedule()` directly from Python — see the script for the data format.

**Output filename convention:**
- Single room: `[Room Name] Schedule.xlsx`
- Multiple rooms: `[Project Name] Schedule.xlsx`

### Step 6 — Deliver

Save to the workspace folder. Share a direct link.

---

## Three-Sheet Output

### Sheet 1 — Main Schedule

All rooms appear on one sheet in the order provided. Each room gets a **blue section header** (merged A:H), followed by light-blue category sub-headers and product rows.

```
Row 1:  CODE | IMAGE | MODEL | MANUFACTURER | DIMENSIONS | NOTES | QUANTITY | LINK  (gray header)
Row 2:  KITCHEN                    (blue section header, merged A:H)
Row 3:    APPLIANCES               (light-blue category header)
Row 4:    AP-1  ...
Row 5:    AP-2  ...
Row 6:    PLUMBING FIXTURES
Row 7:    PF-1  ...
Row N:  POWDER ROOM                (blue section header for next room)
...
```

Materials/finish items (PT, BB, HW, FT, WT, WC, ST, MT) are **not written to this sheet** — they go to Sheet 2 only.

### Sheet 2 — Materials & Finishes

All material/finish items from all rooms, organized by type:

```
Row 1:  CODE | IMAGE | ... | LINK  (gray header)
Row 2:  MATERIALS & FINISHES       (blue section header)
Row 3:    PAINT
Row 4:    PT-1  ...
Row 5:    MOULDING
Row 6:    BB-1  ...
Row 7:    HARDWOOD
...
        TILE
        WALLCOVERING
        STONE
        METAL
```

CT-x codes from the input data are automatically renamed to ST-x on this sheet.

### Sheet 3 — Room Finish Schedule

Plain CAD/Revit-compatible table. No fill colors (except a subtle `#F2F2F2` on the header row), no special formatting — just clean black borders and Arial font.

```
Row 1:  ROOM NO. | ROOM NAME | FLOOR | BASE | NORTH | EAST | SOUTH | WEST | HEIGHT | CEILING MATERIAL / FINISH | NOTES
Row 2:  101  Kitchen    HW-1   BB-1   PT-1   PT-1   PT-1   PT-1   9'-0"   PT-2
Row 3:  102  Powder Rm  FT-1   BB-1   WC-1   PT-1   WC-1   PT-1   8'-0"   PT-1
...
```

Rooms are auto-numbered starting at **101** in the order they appear in the data. If a room has a `room_no` override field, that value is used instead.

Multiple finishes on one surface are joined with ` / `: e.g. `HW-1 / FT-2`.

---

## Excel Format Spec

### Column widths
```
A (CODE):          10 chars
B (IMAGE):         17 chars
C (MODEL):         28 chars
D (MANUFACTURER):  20 chars
E (DIMENSIONS):    30 chars
F (NOTES):         40 chars
G (QUANTITY):      10 chars
H (LINK):          30 chars
```

### Row heights
- Column header row: 22pt
- Room section header rows: 22pt
- Category header rows: 18pt
- Product rows: 90pt (tall enough for thumbnail images)

### Colors
- Column header fill: `#E0E0E0` (light gray)
- Room section header fill: `#2C5F8A` (dark blue), white text, Arial 10pt bold
- Category header fill: `#D6E4F0` (light blue), Arial 9pt bold
- Alternating product rows: `#FFFFFF` / `#F4F4F4` — **global** across the entire sheet (does not reset between categories or rooms)
- Link text: Arial 11pt, no color change (plain text with hyperlink)

### Font
Arial throughout. Bold for codes (col A) and headers; regular 8pt for all other data cells.

### Borders
- Header rows (column header, section, category): medium border all sides
- Product rows: medium border on left (col A) and right (col H), thin on all other sides

### Image embedding
Use `openpyxl`'s `XLImage` with `OneCellAnchor` for proper cell anchoring:

```python
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.utils.units import pixels_to_EMU

col_px = 128
row_px = 120
x_off  = max(0, (col_px - img_w) // 2)
y_off  = max(0, (row_px - img_h) // 2)

marker = AnchorMarker(col=1, colOff=pixels_to_EMU(x_off), row=cur_row - 1, rowOff=pixels_to_EMU(y_off))
size = XDRPositiveSize2D(pixels_to_EMU(img_w), pixels_to_EMU(img_h))
xl_img.anchor = OneCellAnchor(_from=marker, ext=size)
ws.add_image(xl_img)
```

Always save thumbnails to temp files first — BytesIO buffers are unreliable for image anchoring.

### Page setup
```python
ws.page_setup.orientation = 'landscape'
ws.page_setup.fitToPage   = True
ws.page_setup.fitToWidth  = 1
ws.print_title_rows       = '1:1'
```

---

## Room Finish Schedule Format Spec

### Columns (A–K)

```
A (ROOM NO.):                  9 chars
B (ROOM NAME):                22 chars
C (FLOOR):                    14 chars
D (BASE):                     12 chars
E (NORTH):                    14 chars
F (EAST):                     14 chars
G (SOUTH):                    14 chars
H (WEST):                     14 chars
I (HEIGHT):                   10 chars
J (CEILING MATERIAL / FINISH): 26 chars
K (NOTES):                    28 chars
```

### Row heights
- Header row: 30pt
- Data rows: 18pt

### Styling (CAD-compatible — no decorative colors)
- Header row fill: `#F2F2F2` (subtle gray only), all other rows no fill
- All text: Arial 9pt, black
- Header row: bold; data rows: regular weight
- Borders: medium black (`000000`) on outer edges; thin black on interior borders
- All cells: horizontal center, vertical center alignment
- No hyperlinks, no images on this sheet

### Page setup
```python
ws.page_setup.orientation = 'landscape'
ws.page_setup.fitToPage   = True
ws.page_setup.fitToWidth  = 1
ws.print_title_rows       = '1:1'
```

---

## Product Data JSON Format

### Multi-room (preferred)

```json
{
  "project": "Intersecting Stories",
  "studio": "ARCH X482.2 — Design Studio II",
  "semester": "SPRING 2026",
  "rooms": [
    {
      "name": "Kitchen",
      "room_no": "101",
      "surfaces": {
        "floor":  ["HW-1"],
        "base":   ["BB-1"],
        "north":  ["PT-1"],
        "east":   ["PT-1"],
        "south":  ["PT-1"],
        "west":   ["PT-1"]
      },
      "ceiling_height": "9'-0\"",
      "ceiling_finish": "PT-2",
      "rfs_notes": "",
      "categories": [
        {
          "label": "APPLIANCES",
          "items": [
            {
              "code": "AP-1",
              "img": "/path/to/cached/image.jpg",
              "model": "OR30SCI6X1",
              "mfr": "FISHER & PAYKEL",
              "dims": "30\"W × 25-1/4\"D × 35-3/4\"H",
              "notes": "FREE-STANDING INDUCTION RANGE\n3.5 CU. FT. | ENERGY STAR",
              "qty": "1",
              "link": "https://..."
            }
          ]
        }
      ]
    },
    {
      "name": "Powder Room",
      "room_no": "102",
      "surfaces": {
        "floor":  ["FT-1"],
        "base":   ["BB-1"],
        "north":  ["WC-1"],
        "east":   ["PT-1"],
        "south":  ["WC-1"],
        "west":   ["PT-1"]
      },
      "ceiling_height": "8'-0\"",
      "ceiling_finish": "PT-1",
      "rfs_notes": "",
      "categories": []
    }
  ]
}
```

#### Room Finish Schedule fields (per room)

| Field            | Type   | Description |
|------------------|--------|-------------|
| `room_no`        | string | Room number override (e.g. `"101"`). Auto-assigned if omitted. |
| `surfaces`       | object | Keys: `floor`, `base`, `north`, `east`, `south`, `west`. Values: list of finish codes. Multiple codes joined with ` / `. |
| `ceiling_height` | string | e.g. `"9'-0\""`. Leave `""` if not yet known. |
| `ceiling_finish` | string | Finish code(s) for ceiling. Leave `""` if not yet known. |
| `rfs_notes`      | string | Notes shown in the NOTES column on Sheet 3. |

All five fields are optional — omit or leave blank for rooms where surface data hasn't been gathered yet.

---

### Single-room (legacy, still supported)

```json
{
  "room": "Kitchen",
  "project": "Intersecting Stories",
  "studio": "ARCH X482.2 — Design Studio II",
  "semester": "SPRING 2026",
  "categories": [
    {
      "label": "APPLIANCES",
      "items": [...]
    }
  ]
}
```

---

## Notes column content

The NOTES column should contain the most useful spec details for a contractor or purchasing agent:
- Product type / description in ALL CAPS on the first line
- Key specs (capacity, CFM, GPM, dBA, finish, color) on subsequent lines
- Certifications (ENERGY STAR, ADA, ANSI, UPC, etc.)
- Important caveats (PANEL READY, CONTACT DEALER, etc.)

Keep each note line short — it wraps within the cell.

---

## Materials & Finishes routing reference

| Prefix | Routes to M&F as     |
|--------|----------------------|
| PT     | PAINT                |
| BB     | MOULDING             |
| HW     | HARDWOOD             |
| FT     | TILE                 |
| WT     | TILE                 |
| WC     | WALLCOVERING         |
| CT     | STONE (renamed ST-x) |
| ST     | STONE                |
| MT     | METAL                |

All other prefixes (AP, PF, CAB, FURN, AC, LF, TXT, MISC, etc.) stay on the main schedule sheet.
