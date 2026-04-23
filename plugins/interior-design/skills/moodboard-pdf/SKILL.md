---
name: moodboard-pdf
version: "0.4.0"
description: >
  Creates a professional interior design mood board PDF from a folder of product
  markdown clippings. Use this skill whenever a user wants a mood board, moodboard,
  inspiration board, presentation board, FF&E visual, or product specification PDF
  for an interior design project — even if they just say "make the moodboard" or
  "generate the board for the kitchen." Trigger when the user mentions: mood board,
  moodboard, inspiration board, concept board, furniture board, product spec PDF,
  FF&E presentation, design board, room board, spec pages, or when they have a folder
  of markdown product files and want to turn them into a visual PDF. Also trigger when
  the user asks to "update" or "regenerate" moodboards after adding new products.
  Do NOT use for Excel schedules, room schedules, or FF&E spreadsheets — use the
  schedule-creator skill for those.
---

# Mood Board PDF Skill

You create a professional interior design PDF from a project folder of markdown product
clippings. The output is a tabloid landscape PDF (17" × 11") with:

- **Cover page** — project title, studio info, room index
- **Per room:** one mood board page + product specification pages (3 products per page)

The visual style is editorial and minimal: warm linen background (`#EAE5DC`), serif italic
room headings, dark full-width header bars on spec pages, olive-green field labels.

---

## Layout Modes

### Row layout (`--layout row`, default)
Use for **material boards, finish boards, fabric/sample boards**.
- Heading: "materials" in Times-Italic
- Images: single horizontal row of portrait cells, filling the page height
- Trigger phrases: "material board", "finishes", "fabrics", "samples", "swatches"

### Grid layout (`--layout grid`)
Use for **inspiration boards, furniture boards, fixture boards, concept boards**.
- Heading: "inspiration" in Times-Italic
- Images: uniform grid — 2 columns for ≤3 images, 3 columns for 4+ images, auto rows
- Optional color palette swatch row above images
- Trigger phrases: "inspiration board", "mood board", "furniture board", "fixtures",
  "concept board", or user uploads a mix of room/lifestyle photos

---

## Workflow

### Step 0 — Clarify layout and preferences (ask once, don't block)

**Layout:** Based on the user's request, choose `row` or `grid` (see Layout Modes above).

**Color palette (grid only):** Ask "Do you have a color palette for this board? If so,
share the hex codes or describe the colors and I'll convert them." Skip if layout is `row`.

**Colors:** Default palette is warm linen background with dark header bar and olive green labels. Keep or change?

**Spec fields shown:** All are on by default — material, finish, dimensions, price, application, sustainability, specs, source/SKU. Anything to leave out?

If the user says "keep defaults" or doesn't respond, proceed immediately.

### Step 1 — Gather project info

You need:
- **Project root path** — folder containing room subfolders with `.md` files
- **Project name** — e.g. "Smith Residence" (appears in spec page header bar)
- **Studio / author** — e.g. "Steven Castroverde" (appears in header + footer; year is automatic)
- **Logo image** (optional) — small PNG/JPG for cover page. If none, the script auto-generates a badge.

If the user points you to an existing folder, scan it to discover rooms automatically (any subfolder containing `.md` files is a room). The folder name becomes the room label.

### Step 2 — Parse product data

Each `.md` file in a room folder is a product clipping. The script extracts:
- **title** — from frontmatter `title:` or filename
- **subtitle / variant** — from frontmatter `subtitle:`
- **mfr** — from frontmatter `author:` or bold `**manufacturer:**` in body
- **material** — from inline `MATERIAL  value` row
- **finish** — from inline `FINISH  value` row
- **dims** — from `SIZE / DIMS` or `DIMENSIONS` label
- **price** — scans for `$` patterns
- **application** — from inline `APPLICATION  value` row
- **desc** — from frontmatter `description:`
- **sustain** — any mention of FSC, GREENGUARD, CARB, LEED, FloorScore, Red List Free, etc.
- **specs** — from inline `SPECS  value` row
- **sku** — from `SOURCE / SKU` label
- **image** — prefers local `![[filename]]` embeds; falls back to first `![](URL)` in body

### Step 3 — Download and cache images

All images are cached to `_image_cache/` in the working directory (never inside the user's vault).
If an image fails, log it and use a placeholder — never crash.

### Step 4 — Build the PDF

The build script lives at `$CLAUDE_PLUGIN_ROOT/skills/moodboard-pdf/scripts/build_moodboard.py`. Call it directly:

```bash
# Row layout (material/finish boards)
python3 "$CLAUDE_PLUGIN_ROOT/skills/moodboard-pdf/scripts/build_moodboard.py" \
  --project-dir "/path/to/project" \
  --output "/path/to/Material Specification - ProjectName.pdf" \
  --project-name "Smith Residence" \
  --studio "Steven Castroverde" \
  --layout row \
  --logo "/path/to/logo.png"

# Grid layout (inspiration/furniture boards)
python3 "$CLAUDE_PLUGIN_ROOT/skills/moodboard-pdf/scripts/build_moodboard.py" \
  --project-dir "/path/to/project" \
  --output "/path/to/Inspiration Board - ProjectName.pdf" \
  --project-name "Smith Residence" \
  --studio "Steven Castroverde" \
  --layout grid \
  --palette "#3D5A40,#EAE5DC,#1C1E18,#7A7065,#C8BFB2"
```

Or use the Python API directly for more control:

```python
import sys
sys.path.insert(0, '$CLAUDE_PLUGIN_ROOT/skills/moodboard-pdf/scripts')
from build_moodboard import build_pdf

rooms = [
  {
    'name': 'LIVING ROOM',      # all-caps room name (used in spec header)
    'subtitle': 'living room',  # lowercase label on mood board page
    'products': [
      {
        'title': 'Venezia Terrazzo',
        'subtitle': 'Venezia Terrazzo Cream',
        'mfr': 'Artistic Tile',
        'material': 'Cement terrazzo with stone chips',
        'finish': 'Honed',
        'price': '$22.00 per SF',
        'dims': '16 × 16 in · 1.78 SF/PC',
        'desc': 'Made in Italy following Venetian traditions...',
        'application': 'All public dining & entry floor areas',
        'sustain': 'Recycled stone content · LEED credits',
        'specs': 'DCOF 0.55–0.57 · 7.1 LB/SF',
        'sku': 'YVENCRMH16',
        'img': '/path/to/cached/image.jpg',
        'source': 'https://...',
      },
    ]
  }
]

build_pdf(
    rooms,
    output_path='/path/to/output.pdf',
    project_name='Smith Residence',
    studio='Steven Castroverde',
    logo_path='/path/to/logo.png',   # optional
    layout='grid',                   # 'row' or 'grid'
    palette=['#3D5A40', '#EAE5DC'],  # optional list of hex strings
)
```

**Output filename convention:**
- Row layout: `Material Specification - [Project Name].pdf`
- Grid layout: `Inspiration Board - [Project Name].pdf`

### Step 5 — Deliver

Save the PDF to the workspace folder. Share a direct link.

---

## Design Reference

### Color palette
```
Background:      #EAE5DC   warm linen
Header bar:      #1C1E18   near-black (full-width, spec pages only)
Field labels:    #4A5C38   olive green (MATERIAL, FINISH, etc.)
Caption:         #7A7065   muted warm gray
Body text:       #1A1A18   near-black
Dividers:        #C8BFB2   warm gray rules
Cover accent:    #3D5A40   forest green (stripe + badge)
Subtitle muted:  #9A9080   subdued mfr/collection text
```

### Mood board layout
- **Heading:** two lines top-left — room type in small sans (7.5pt), heading word in Times-Italic (28pt)
- **Palette row** (grid only, optional): filled circles, 0.55" diameter, evenly spaced, 0.75" strip height
- **Row mode:** single row of portrait cells, caption strip below
- **Grid mode:** equal cells in 2 or 3 columns, captions below each cell, empty slots left blank
- **Captions:** 5.5pt Helvetica uppercase, centered below each cell, max 30 chars
- No header bar, no footer, no logo chrome on mood board pages — extremely clean

### Spec page layout (3-column, 17"×11")
- **Header bar:** full-width dark bar (#1C1E18) at top — project name left, year right (auto)
- **3 product cards** per page, left to right; remaining slots on the last page left empty
- **Card structure:** large image (57% of card height, white bg) → product name (Times-Bold 12pt) → "mfr · collection" (Helvetica muted) → description → thin rule → spec field rows
- **Spec field rows:** "LABEL  value" inline — label in Helvetica-Bold 6pt olive, value in Helvetica 6pt
- **Footer:** "Author · Year" left, "Product Specification" right

### CLI flags
```
--layout row|grid                            # mood board layout (default: row)
--palette "#hex,#hex,..."                    # color swatches above images (grid)
--spec-fields "material,finish,dims,price"   # show only these fields (default: all)
--color-bg "#EAE5DC"                         # override background
--color-accent "#3D5A40"                     # override cover accent
--color-text "#1A1A18"                       # override body text
--color-dark "#1C1E18"                       # override header bar
--color-rule "#C8BFB2"                       # override dividers
--color-caption "#7A7065"                    # override caption text
```

---

## Common Issues

**Images blocked (403):** The script automatically retries with `User-Agent: curl/7.68.0` and then no agent.

**Too many products on mood board:** Grid layout handles large counts gracefully. For 10+ items in row mode consider splitting into sub-rooms (separate subfolders).

**Missing sustainability info:** Search `"{manufacturer}" sustainability certifications` for FSC, GREENGUARD, CARB, GoodWeave, FloorScore, Red List Free. Only include verifiable claims.

**No logo:** The script auto-generates a green square badge with white initials on the cover page.

**Fewer than 3 products on last spec page:** Remaining cards fill from the left slot; unused slots stay blank.
