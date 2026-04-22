---
name: moodboard-pdf
version: "0.3.0"
description: >
  Creates a professional interior design mood board PDF from a folder of product
  markdown clippings. Use this skill whenever a user wants a mood board, moodboard,
  presentation board, FF&E visual, or product specification PDF for an interior design
  project — even if they just say "make the moodboard" or "generate the board for the
  kitchen." Trigger when the user mentions: mood board, moodboard, product spec PDF,
  FF&E presentation, design board, room board, spec pages, or when they have a folder
  of markdown product files and want to turn them into a visual PDF. Also trigger when
  the user asks to "update" or "regenerate" moodboards after adding new products.
  Do NOT use for Excel schedules, room schedules, or FF&E spreadsheets — use the
  schedule-creator skill for those.
---

# Mood Board PDF Skill

You create a professional interior design material specification PDF from a project
folder of markdown product clippings. The output is a landscape PDF (11" × 8.5") with:

- **Cover page** — project title, studio info, room index
- **Per room:** one mood board page + product specification pages (2 products per page)

The visual style is editorial and minimal: warm linen background (`#EAE5DC`), serif italic
room headings, portrait image rows on mood boards, dark full-width header bars on spec pages,
olive-green field labels, clean Helvetica body text.

---

## Workflow

### Step 0 — Clarify preferences (ask once, don't block)

Ask two quick questions before starting:

**Colors:** Default palette is warm linen background with dark header bar and olive green labels. Keep or change?

**Spec fields shown:** All are on by default — material, finish, dimensions, price, application, sustainability, specs, source/SKU. Anything to leave out?

If the user says "keep defaults" or doesn't respond, proceed immediately.

### Step 1 — Gather project info

You need:
- **Project root path** — folder containing room subfolders with `.md` files
- **Project name** — e.g. "Restaurant" (appears in spec page header bar)
- **Studio / author** — e.g. "Steven" or "Building Components & Systems" (appears in header + footer)
- **Semester / year** — e.g. "2026"
- **Logo image** (optional) — small PNG/JPG for cover page. If none, the script auto-generates a badge.

If the user points you to an existing folder, scan it to discover rooms automatically (any subfolder containing `.md` files is a room). The folder name becomes the room label (e.g. folder `restaurant/` → mood board shows "restaurant" / "materials").

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

```python
headers_to_try = [
    {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0'},
    {'User-Agent': 'curl/7.68.0'},
    {},
]
```

If an image fails, log it and use a placeholder — never crash.

### Step 4 — Build the PDF

The build script lives at `scripts/build_moodboard.py`. Call it directly:

```bash
python3 scripts/build_moodboard.py \
  --project-dir "/path/to/project" \
  --output "/path/to/Material Specification - ProjectName.pdf" \
  --project-name "Restaurant" \
  --studio "Steven" \
  --semester "2026" \
  --logo "/path/to/logo.png"
```

Or use the Python API directly for more control:

```python
import sys
sys.path.insert(0, 'path/to/moodboard-pdf/scripts')
from build_moodboard import build_pdf

rooms = [
  {
    'name': 'RESTAURANT',       # all-caps room name (used in spec header)
    'subtitle': 'restaurant',   # lowercase label on mood board page
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
      # ... more products
    ]
  }
]

build_pdf(
    rooms,
    output_path='/path/to/output.pdf',
    project_name='Restaurant',
    studio='Steven',
    semester='2026',
    logo_path='/path/to/logo.png',  # optional
)
```

**Output filename convention:** `Material Specification - [Project Name].pdf`

### Step 5 — Deliver

Save the PDF to the workspace folder. Share a direct link.

---

## Design Reference

### Palette
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
- **Heading:** two lines top-left — room type in small sans (7.5pt), "materials" in large Times-Italic (28pt)
- **Images:** single row of portrait cells filling the remaining page height
- **Cell sizing:** `cell_w = (available_width − gaps) / n_products` — portrait aspect, fixed height
- **Captions:** 5.5pt Helvetica uppercase, centered below each cell
- No header bar, no footer, no logo chrome on mood board pages — extremely clean

### Spec page layout (2-column)
- **Header bar:** full-width dark bar (#1C1E18) at top — "PROJECT — MATERIAL SPECIFICATION" left, "STUDIO · YEAR" right
- **2 product cards** per page, side by side, divided by a thin warm-gray rule at page center
- **Card structure:** large image (57% of card height, white bg) → product name (Times-Bold 12pt) → "mfr · collection" (Helvetica muted) → description → thin rule → spec field rows
- **Spec field rows:** "LABEL  value" inline — label in Helvetica-Bold 6pt olive, value in Helvetica 6pt near-black
- **Footer:** "Author · Year" left, "Product Specification" right

### Spec fields displayed (in order)
```
MATERIAL       material composition
FINISH         surface treatment
SIZE / DIMS    dimensions
PRICE          unit price
APPLICATION    recommended use locations
SUSTAINABILITY certifications and environmental claims
SPECS          technical performance data
SOURCE / SKU   manufacturer source code or SKU
```

### CLI flags
```
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

**Too many products on mood board:** Single-row layout scales gracefully. For 10+ items per room consider splitting into sub-rooms (separate subfolders).

**Missing sustainability info:** Search `"{manufacturer}" sustainability certifications` for FSC, GREENGUARD, CARB, GoodWeave, FloorScore, Red List Free. Only include verifiable claims.

**No logo:** The script auto-generates a green square badge with white initials on the cover page.

**Odd product count:** If a room has an odd number of products, the last spec page will show a single centered card at 62% page width.
