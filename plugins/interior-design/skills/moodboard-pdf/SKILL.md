---
name: moodboard-pdf
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
  room-schedule skill for those.
---

# Mood Board PDF Skill

You create a professional interior design mood board PDF from a project folder of
markdown product clippings. The output is a landscape PDF (11" × 8.5") with:

- **Cover page** — project title, studio info, room index
- **Per room:** one mood board page (all product images in a grid) + product specification pages (3 products per page)

The visual style is editorial and minimal: warm cream background (`#F5F2EE`), forest green accents (`#3D5A40`), product images floating at natural proportions, clean Helvetica typography.

---

## Workflow

### Step 0 — Clarify preferences (ask once, don't block)

Ask two quick questions before starting:

**Colors:** Default palette is warm cream background with forest green accents. Keep or change?

**Spec fields shown:** All are on by default — manufacturer, price, dimensions, description, sustainability. Anything to leave out?

If the user says "keep defaults" or doesn't respond, proceed immediately.

### Step 1 — Gather project info

You need:
- **Project root path** — folder containing room subfolders with `.md` files
- **Project name** — e.g. "Intersecting Stories"
- **Studio / course** — e.g. "ARCH X482.2 — Design Studio II"
- **Semester** — e.g. "SPRING 2026"
- **Logo image** (optional) — small PNG/JPG for page headers. If none, the script auto-generates a text badge.

If the user points you to an existing folder, scan it to discover rooms automatically (any subfolder containing `.md` files is a room).

### Step 2 — Parse product data

Each `.md` file in a room folder is a product clipping. The script extracts:
- **title** — from frontmatter `title:` or filename
- **subtitle / variant** — from frontmatter or first body line
- **manufacturer** — from frontmatter `author:` or body text
- **price** — scans for `$` patterns
- **dimensions** — scans for measurement patterns
- **description** — from frontmatter `description:` + body prose
- **sustainability** — any mention of FSC, GREENGUARD, CARB, CertiPUR, LEED, zero-VOC, recycled, etc.
- **image** — prefers local `![[filename]]` embeds; falls back to first `![](URL)` in body

For inspiration images (images with headings but no product specs), treat each heading + image as a product entry with the heading as the title and `subtitle: Design Inspiration`. These appear on the mood board and spec pages.

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
  --output "/path/to/Mood Board - ProjectName.pdf" \
  --project-name "Intersecting Stories" \
  --studio "ARCH X482.2 — Design Studio II" \
  --semester "SPRING 2026" \
  --logo "/path/to/logo.png"
```

Or use the Python API directly for more control:

```python
import sys
sys.path.insert(0, 'path/to/moodboard-pdf/scripts')
from build_moodboard import build_pdf

rooms = [
  {
    'name': 'KITCHEN',
    'subtitle': 'Intersecting Stories',
    'products': [
      {
        'title': 'Fisher & Paykel OR30SCI6X1',
        'subtitle': '30" Induction Range',
        'mfr': 'FISHER & PAYKEL',
        'price': '$5,649.00',
        'dims': '30"W × 25-1/4"D × 35-3/4"H',
        'desc': 'Free-standing induction range...',
        'sustain': 'ENERGY STAR certified.',
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
    project_name='Intersecting Stories',
    studio='ARCH X482.2 — Design Studio II',
    semester='SPRING 2026',
    logo_path='/path/to/logo.png',  # optional
)
```

**Output filename convention:** `Mood Board - [Project Name].pdf`

### Step 5 — Deliver

Save the PDF to the workspace folder. Share a direct link.

---

## Design Reference

### Palette
```
Background:   #F5F2EE   warm cream
Dark (cover): #1C1E18   near-black
Accent:       #3D5A40   forest green
Rule:         #C5BAA8   warm gray
Caption:      #6B6B60   medium gray
Text:         #1A1A18   near-black
```

### Grid sizing by product count
```
1–2:   1 row,  n cols = n
3–4:   2×2
5–6:   3×2
7–9:   3×3
10–12: 4×3
13–16: 4×4
17+:   5×4
```

Images are **scale-to-fit** (not cropped) — they float on the cream background.

### CLI flags
```
--spec-fields "mfr,dims,sustain"   # show only these fields (default: all)
--color-bg "#F5F2EE"               # override background color
--color-accent "#3D5A40"           # override accent / headings
--color-text "#1A1A18"             # override body text
--color-dark "#1C1E18"             # override cover panel
--color-rule "#C5BAA8"             # override rules/dividers
```

---

## Common Issues

**Images blocked (403):** Try `User-Agent: curl/7.68.0`.

**Too many products on mood board:** The grid auto-sizes up to 5×4 (20 items). Beyond that, consider splitting into sub-rooms.

**Missing sustainability info:** Search `"{manufacturer}" sustainability certifications` for FSC, GREENGUARD, CARB, GoodWeave, CertiPUR. Only include verifiable claims.

**No logo:** The script auto-generates a green square badge with white initials.
