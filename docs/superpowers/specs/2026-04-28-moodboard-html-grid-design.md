# Moodboard HTML Grid Design

**Date:** 2026-04-28  
**Status:** Approved  
**Scope:** `interior-design-skills:moodboard-pdf` — grid layout mode only

---

## Problem

The current grid layout in `build_moodboard.py` uses ReportLab to place equal-size rectangular cells in a uniform 2–3 column grid. Every product gets the same box regardless of type. The result looks generic and lacks the editorial quality of professional interior design mood boards, where furniture commands large hero cells and accessories fill smaller supporting slots.

---

## Decision

Replace the moodboard grid page renderer with an HTML/CSS pipeline using **WeasyPrint**. The spec pages (3-up product cards) remain unchanged in ReportLab. The final PDF is assembled by merging both outputs with `pypdf`.

---

## Architecture

```
.md files (per room)
    │
    ▼
Existing parser (build_moodboard.py)
    │  extracts product data, downloads images to _image_cache/
    │
    ├──► build_moodboard_html.py   (new)
    │        HTML template → WeasyPrint → moodboard.pdf
    │
    └──► build_moodboard.py        (existing, small additions)
             ReportLab → spec_pages.pdf
                 │
                 ▼
             pypdf merge → Final PDF         ← new merge step added here
             (cover + moodboard + spec pages)
```

### New file: `scripts/build_moodboard_html.py`

Responsible for:
1. Receiving parsed room data (product list with image paths already resolved)
2. Selecting the appropriate grid template
3. Sorting products by category (furniture first → large cells, accessories last → small cells)
4. Rendering the HTML template string with embedded base64 images
5. Converting to PDF via WeasyPrint
6. Returning the output PDF path

### Merge step (in `build_moodboard.py`)

When `--layout grid` is used:
1. Generate moodboard page via `build_moodboard_html.py` → `moodboard_page.pdf`
2. Generate spec pages via existing ReportLab code → `spec_pages.pdf`
3. Merge with `pypdf`: `cover + moodboard_page + spec_pages` → final output PDF
4. Delete temp files

---

## Grid Templates

Three templates, selected automatically by product count. Overridable per room with `--template <name>`.

### Template: `anchor-left` (default for 4–6 products)

```
┌──────────┬──────┬──────┬──────┐
│          │  B   │  C   │      │
│    A     ├──────┼──────│  D   │
│  (hero)  │  E   │  F   │(dark)│
└──────────┴──────┴──────┴──────┘
  col: 1.5   1     1    0.8
```

- A: furniture hero — `grid-column: 1; grid-row: 1 / 3`
- D: dark accent cell (`background: #1C1E18`) — `grid-column: 4; grid-row: 1 / 3`
- B, C, E, F: remaining products in category order

### Template: `feature-top` (pin-only via `--template feature-top`)

```
┌────────────────┬──────┐
│       A        │  B   │
│   (wide hero)  │(dark)│
├──────┬──────┬──────────┤
│  C   │  D   │    E    │
└──────┴──────┴──────────┘
  col: 1.8    1     1
```

- A: furniture hero — `grid-column: 1 / 3; grid-row: 1`
- B: dark accent — `grid-column: 3; grid-row: 1`
- C, D, E: remaining products

### Template: `collage` (default for 7–9 products)

```
┌──────┬──────┬───────────┐
│      │  B   │    C      │
│  A   ├──────┼──────┬────┤
│(hero)│  D   │  E   │ F  │
├──────┴──────┼──────┼────┤
│      G      │  H   │ I  │
└─────────────┴──────┴────┘
  col: 1    1.3    1    1
```

- A: furniture hero — `grid-column: 1; grid-row: 1 / 3`
- C: wide span — `grid-column: 3 / 5; grid-row: 1`
- G: wide span bottom — `grid-column: 1 / 3; grid-row: 3`
- Remaining: single cells in category order

### Auto-selection logic

| Product count | Template auto-selected |
|---|---|
| 2–6 | `anchor-left` (unused slots left blank for counts < 6) |
| 7+ | `collage` (products split into groups of 9, each group gets its own moodboard page) |

`feature-top` is never auto-selected — it is only used when the user explicitly passes `--template feature-top`. It supports 4–5 products; unused slots are left blank.

---

## Category-Aware Cell Assignment

Products are sorted into a priority queue before slot assignment:

| Priority | Category | Assigned to |
|---|---|---|
| 1 | `furniture` | Large spanning cells (hero slots) |
| 2 | `lighting` | Medium single cells |
| 3 | `textile` | Medium single cells |
| 4 | `accessory` | Small cells |
| 5 | (uncategorized) | Remaining slots |

### Category detection

1. Read `category:` field from product frontmatter (explicit, preferred)
2. Fall back to keyword inference from product title:
   - **furniture**: sofa, sectional, chair, armchair, table, desk, cabinet, dresser, bed, ottoman, bench, bookcase, shelf
   - **lighting**: lamp, pendant, sconce, chandelier, floor lamp, table lamp, fixture
   - **textile**: rug, curtain, drape, pillow, cushion, throw, blanket
   - **accessory**: vase, bowl, tray, artwork, mirror, plant, basket, candle, frame

---

## Image Rendering

All cells use `object-fit: contain` with the linen background (`#EAE5DC`) filling any letterbox gaps. This preserves product silhouettes — critical for furniture where legs, arms, and profiles are key design details.

Images are embedded as base64 data URIs in the rendered HTML so WeasyPrint has zero network dependency at render time. The existing `_image_cache/` directory is used — no change to the download/caching logic.

---

## Palette Strip

- Rendered as a row of full-width `<div>` rectangles below the grid
- Height: 40px total, rectangles fill the full strip with no gaps
- Only rendered when `--palette` hex codes are passed
- Matches the rectangular swatch style in reference image 1

---

## Page Spec

```css
@page {
  size: 17in 11in landscape;
  margin: 0;
}
```

- Background: `#EAE5DC` (warm linen) — full bleed
- Room heading: top-left, two lines — room type in Helvetica 7.5pt, heading word in Times-Italic 28pt
- Gap between grid cells: 4px
- Page margin inside grid: 0.45in on all sides (matching existing ReportLab margin)

---

## WeasyPrint Dependency

```bash
pip install weasyprint --break-system-packages
```

Required system libraries (pre-installed on macOS/Linux): `libpango`, `libcairo`, `libgdk-pixbuf`.

The skill's build script checks for WeasyPrint at runtime and prints a clear install message if missing — it does not crash silently.

---

## CLI Interface (unchanged)

The existing `--layout grid` flag triggers the new HTML pipeline. No new flags required beyond `--template` (optional override).

```bash
python3 build_moodboard.py \
  --project-dir "/path/to/project" \
  --output "Inspiration Board - Smith Residence.pdf" \
  --project-name "Smith Residence" \
  --studio "Steven Castroverde" \
  --layout grid \
  --palette "#3D3530,#9A7B5A,#EAE5DC,#C07C60"
```

---

## Out of Scope

- Spec pages (3-up product cards) — remain ReportLab, no changes
- Row layout mode — remains ReportLab, no changes
- Cover page — remains ReportLab, no changes
- Playwright/Chromium as an alternative renderer
