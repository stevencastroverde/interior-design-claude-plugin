# Claude Interior Design Plugin

A Claude Code plugin for interior design workflows, focused on FF&E scheduling, spec sheet annotation, mood board generation, and client-ready PDF protection.

## Installation

Add the marketplace to Claude:

```
/plugin marketplace add git@github.com:stevencastroverde/interior-design-claude-plugin.git
```

Install the plugin:

```
/plugin install interior-design-skills@claude-meets-interior-design
```

## Updating

Pull the latest version and reinstall:

```
/plugin marketplace update claude-meets-interior-design
/plugin install interior-design-skills@claude-meets-interior-design
```

---

## Skills

### Schedule Creator

Creates a professional Excel (.xlsx) schedule for any categorized item list — interior design FF&E, equipment, procurement, materials, or anything else with codes, images, and specs.

**Trigger phrases**

Say things like:
- "make the schedule"
- "create an FF&E schedule"
- "kitchen schedule"
- "create the Excel"
- "make a product schedule for the living room"

**What you need to provide**

- A list of items with: model number, manufacturer, dimensions, notes, quantity, and a source URL or image
- Schedule name (e.g. "Kitchen", "Phase 1 Equipment")
- Project name
- Optionally: author / studio name and date (defaults to current month/year)

**What you get**

A landscape `.xlsx` workbook with:

| Column | Description |
|--------|-------------|
| CODE | Short abbreviation code (e.g. AP-1, FURN-3) |
| IMAGE | Embedded product thumbnail |
| MODEL | Model number |
| MANUFACTURER | Brand / manufacturer name |
| DIMENSIONS | W × D × H or other format |
| NOTES | Key specs, certifications, caveats |
| QUANTITY | Item quantity |
| LINK | Hyperlinked source URL |

Items are grouped by category with colored header rows. Interior design projects use the built-in Master Abbreviation List (AP, PF, CT, CAB, FURN, AC, HW, FT, WT, PT, LF, MT, WC, MISC).

**Prerequisites**

```bash
pip install openpyxl pillow requests
```

---

### Spec Sheet Annotator

Stamps schedule codes onto spec sheet PDFs, highlights installation-critical text in yellow, and merges everything into one combined PDF.

**Trigger phrases**

Say things like:
- "annotate spec sheets"
- "add codes to spec sheets"
- "highlight specs"
- "combine spec sheets"
- "create spec package"
- "label spec PDFs from schedule"

**What you need to provide**

- The `.xlsx` schedule (must have a CODE column and a MODEL column)
- A folder containing your spec sheet PDFs
- Output path for the final combined PDF

**What you get**

A single merged PDF where every page has:
- The schedule code (e.g. `AP-1`) stamped in **red** at the top-right corner
- **Yellow highlights** on installation-critical text: dimensions, clearances, electrical specs, voltage/amperage, ducting sizes, plumbing connections, and weight

Pages are output in schedule code order by default.

**Optional flags**

| Flag | Description |
|------|-------------|
| `--schedule-sheet NAME` | Target a specific sheet if the xlsx has multiple |
| `--order schedule` | Output in schedule code order (default) |
| `--order original` | Preserve original PDF order |
| `--manual-map '{...}'` | Override page mapping for scanned/image-based PDFs |

**Prerequisites**

```bash
pip install pymupdf openpyxl
```

---

## Mood Board PDF

Creates a professional landscape PDF (11" × 8.5") from a folder of markdown product clippings — one PDF with a cover page, per-room mood board grid, and product spec pages.

**Trigger phrases**

Say things like:
- "make the moodboard"
- "generate the mood board for the kitchen"
- "create the presentation board"
- "build the FF&E visual"
- "update the moodboards"

**What you need to provide**

- A folder containing room subfolders, each with markdown product clipping files
- Project name and studio/semester info (optional)

**What you get**

A single landscape PDF with:
- Cover page — project title, studio info, room index
- Per room: one mood board page (product image grid) + product spec pages (3 per page)
- Editorial style: warm cream background, forest green accents, clean typography

**Prerequisites**

```bash
pip install pymupdf pillow requests
```

---

## AutoCAD Hatch Pattern

Generates AutoCAD-compatible `.pat` hatch pattern files from product photos or descriptions of tile, brick, or stone patterns. Visualizes the pattern interactively before generating the file.

**Trigger phrases**

Say things like:
- "make a hatch pattern from this tile"
- "create a PAT file for this brick pattern"
- "AutoCAD hatch for this stone"
- "generate a .pat from this image"

**What you need to provide**

- A product photo or screenshot of a tile/material pattern, OR
- A text description with tile names and dimensions

**What you get**

A `.pat` file compatible with AutoCAD, Revit, BricsCAD, and other CAD tools, along with a visual preview you can review before the file is written.

**Prerequisites**

None — pure Claude reasoning and file write.

---

---

## PDF Protect

Adds a visible watermark and optional permission restrictions to any PDF before client delivery — no open password required. Recipients open the file normally; editing, copying, and printing are restricted at the PDF level.

**Trigger phrases**

Say things like:
- "protect this PDF"
- "add a watermark"
- "lock down before sending to client"
- "prepare this PDF for client delivery"
- "watermark a PDF"

**What you need to provide**

- Path to any PDF file (or let the skill scan the current directory)
- Optionally: recipient name and email (embedded in watermark for traceability)
- Optionally: which restrictions to apply — editing, copying, printing (any combination)

**What you get**

A `<name>-protected.pdf` alongside the original with:
- Diagonal watermark at 15% opacity — visible but fully readable underneath
- Default text: `CONFIDENTIAL — Steven Castroverde — <date>`
- Recipient text: `CONFIDENTIAL — Prepared for Jane Doe — jane@example.com`
- PDF permission flags blocking whichever actions you chose (no user-facing password)

**Prerequisites**

```bash
pip install reportlab pypdf
```

---

## Version

0.3.0 — Added PDF Protect skill for client-ready watermarking and permission restrictions
