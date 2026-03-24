---
name: schedule-creator
description: >
  Creates a professional schedule as an Excel (.xlsx) spreadsheet for any domain —
  interior design, procurement, FF&E, equipment, inventory, materials, or any other
  categorized product or item list.
  Use this skill whenever a user wants a schedule, product list, equipment list, or
  any organized Excel file with codes, images, dimensions, and links —
  even if they just say "make the schedule" or "create the Excel."
  Trigger when the user mentions: schedule, FF&E schedule, product schedule, equipment
  schedule, material schedule, spec schedule, procurement list, or when they have a
  list of items and want an organized Excel file with codes, images, and specs.
  Items are grouped by category with short abbreviation codes and embedded images.
---

# Schedule Creator Skill

You create a professional schedule as an Excel (.xlsx) file for any type of categorized
item list — interior design, procurement, equipment, materials, or any other domain.

**Output:** A landscape Excel workbook with one sheet containing:
- Column header row: CODE | IMAGE | MODEL | MANUFACTURER | DIMENSIONS | NOTES | QUANTITY | LINK
- Category header rows (colored) grouping items by type
- Item rows with embedded thumbnail images, full specs, and hyperlinked source URLs

---

## Workflow

### Step 1 — Gather item data

You need:
- **Items** — title, model number, manufacturer, dimensions, notes/specs, quantity, source URL, and an image (URL or local file path)
- **Schedule name** — e.g. "Kitchen", "Server Room", "Phase 1 Equipment"
- **Project name** — e.g. "Acme Office Renovation"
- **Date** — defaults to today's date if not provided
- **Author / Studio** — optional name shown in the header/footer (e.g., "John Doe", "Acme Design Studio")

Items most commonly come from:
- A list the user provides directly
- Markdown or text clippings in a folder
- A previously generated document or spreadsheet

### Step 2 — Assign abbreviation codes

Assign a short code prefix to each item. If the user is working on an interior design project, use the **Master Abbreviation List** below. For other domains, derive codes from the category names (e.g., EQUIP, MATL, SVC) or ask the user. Standard interior design categories:

| Code   | Category              | Examples |
|--------|-----------------------|---------|
| AP     | Appliance             | Range, refrigerator, dishwasher, microwave, hood, beverage cooler |
| PF     | Plumbing Fixtures     | Sink, faucet, toilet, shower valve |
| CT     | Countertop            | Granite, quartz, marble slabs |
| CAB    | Cabinetry             | Cabinet fronts, door styles |
| FURN   | Furniture             | Chairs, stools, sofas, tables |
| AC     | Accessories           | Fabric, pulls, hardware, décor |
| HW     | Hardwood              | Flooring |
| FT     | Floor Tile            | Porcelain, stone floor tile |
| WT     | Wall Tile             | Backsplash, shower tile |
| PT     | Paint                 | Paint colors |
| LF     | Light Fixtures        | Pendants, recessed, sconces |
| MT     | Metal                 | Metal trim, metal accents |
| WC     | Wall Coverings        | Wallpaper, wall panels |
| MISC   | Miscellaneous         | Anything that doesn't fit above |

Number items sequentially within each category: AP-1, AP-2, CT-1, etc.

If a Master Abbreviation List PDF is available in `./references/`, read it first and use those codes — they override the defaults above. For non-design domains, keep codes short (3–6 chars) and descriptive.

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

### Step 4 — Build the Excel file

Use the build script at `scripts/build_schedule.py`:

```bash
python3 scripts/build_schedule.py \
  --output "/path/to/Schedule Name.xlsx" \
  --room "Kitchen" \
  --project "Project Name" \
  --date "March 2026" \
  --author "Studio or Author Name" \
  --data "/path/to/items.json"
```

Or call `build_schedule()` directly from Python — see the script for the data format.

`--date` defaults to the current month and year if omitted. `--author` is optional — omit if not provided by the user.

**Output filename convention:** `[Schedule Name] Schedule.xlsx`

### Step 5 — Deliver

Save to the workspace folder. Share a direct link.

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
- Header row: 22pt
- Category rows: 18pt
- Product rows: 90pt (tall enough for thumbnail images)

### Colors
- Header row fill: `#E0E0E0` (light gray)
- Category row fill: `#D6E4F0` (light blue)
- Alternating product rows: `#FFFFFF` / `#F4F4F4`
- Link text: `#0563C1` with underline

### Font
Arial throughout. Bold for codes and category headers, regular for data.

### Image embedding
Use `openpyxl`'s `XLImage` with `OneCellAnchor` for proper cell anchoring:

```python
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.utils.units import pixels_to_EMU

# Column B = index 1 (0-based), row is cur_row-1 (0-based)
col_px = 128   # ~17 char column at ~7.5px/char
row_px = 120   # 90pt row at 1.33px/pt
x_off  = max(0, (col_px - img_w) // 2)
y_off  = max(0, (row_px - img_h) // 2)

marker = AnchorMarker(
    col=1, colOff=pixels_to_EMU(x_off),
    row=cur_row - 1, rowOff=pixels_to_EMU(y_off)
)
size = XDRPositiveSize2D(pixels_to_EMU(img_w), pixels_to_EMU(img_h))
xl_img.anchor = OneCellAnchor(_from=marker, ext=size)
ws.add_image(xl_img)
```

This centers each image within its cell. Always save thumbnails to temp files first — BytesIO buffers are unreliable for image anchoring.

### Page setup
```python
ws.page_setup.orientation = 'landscape'
ws.page_setup.fitToPage   = True
ws.page_setup.fitToWidth  = 1
ws.print_title_rows       = '1:1'
```

---

## Product Data JSON Format

When calling the build script directly, pass product data as JSON:

```json
{
  "room": "Kitchen",
  "project": "Project Name",
  "date": "March 2026",
  "author": "Studio or Author Name",
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
          "qty": "",
          "link": "https://..."
        }
      ]
    }
  ]
}
```

---

## Notes column content

The NOTES column should contain the most useful spec details for whoever will act on the schedule (contractor, purchasing agent, installer, etc.). Good notes include:
- Item type / description in ALL CAPS on the first line
- Key specs relevant to the domain (capacity, dimensions, finish, power requirements, etc.)
- Certifications or compliance notes where applicable
- Important caveats (SPECIAL ORDER, LEAD TIME, CONTACT VENDOR, etc.)

Keep each note line short — it wraps within the cell.
