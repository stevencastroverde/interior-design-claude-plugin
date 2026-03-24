---
name: spec-sheet-annotator
description: >
  Annotates spec sheet PDFs with codes from any schedule — interior design, equipment,
  procurement, or any other domain. Stamps every page with its schedule code in red at
  the top-right corner, highlights critical text (dimensions, tolerances, electrical/power
  specs, clearances, weights) in yellow, then merges all spec sheets into one combined PDF.

  Use this skill whenever the user wants to add codes to spec sheets, highlight critical
  specs or requirements in a PDF, combine multiple spec PDFs into one document, create an
  annotated spec package, or prep spec sheets for contractors, installers, or purchasing.

  Trigger on: "annotate spec sheets", "add codes to spec sheets", "highlight specs",
  "combine spec sheets", "label spec PDFs from schedule", "create spec package", or any
  mention of a schedule alongside spec sheet PDFs.
---

# Spec Sheet Annotator

You have access to a bundled annotation script at `scripts/annotate_spec_sheets.py`
that handles all the heavy lifting. Your job is to:

1. Identify the input files
2. Run the script with the right arguments
3. Deliver the output PDF

---

## Step 1 — Identify the inputs

Ask the user (or infer from context) for:

| Input | Description | Example |
|-------|-------------|---------|
| **Schedule** | Any schedule as `.xlsx` | `Kitchen Schedule.xlsx`, `Equipment List.xlsx` |
| **Spec sheets dir** | Folder containing spec sheet PDF(s) | `Project/Spec Sheets/` |
| **Output path** | Where to save the final PDF | `Project - Spec Sheets.pdf` |

If a `Spec Sheets` folder exists inside the project folder, use it. The script will
scan **all PDFs** in that directory automatically.

The schedule must have a `CODE` column (e.g., AP-1, EQUIP-3) and a `MODEL` column.

---

## Step 2 — Install dependencies (if needed)

```bash
pip install pymupdf openpyxl --break-system-packages -q
```

---

## Step 3 — Run the script

```bash
python3 /path/to/scripts/annotate_spec_sheets.py \
  --schedule  "/path/to/Schedule.xlsx" \
  --spec-dir  "/path/to/Spec Sheets" \
  --output    "/path/to/output/Project - Spec Sheets.pdf"
```

**Optional flags:**
- `--schedule-sheet NAME` — if the xlsx has multiple sheets, specify the one to read (default: first sheet)
- `--order schedule` — output pages in schedule code order (default, recommended)
- `--order original` — preserve original PDF order

---

## Step 4 — What the script does automatically

1. **Reads the schedule** — extracts `CODE → MODEL` pairs in schedule order,
   skipping category headers and blank rows.

2. **Maps pages to codes** — scans each PDF page for model numbers. The first
   page where a model number appears starts a new item "section"; all
   following pages until the next match inherit that code. Multi-page specs
   are handled correctly.

3. **Labels every page** — stamps the code (e.g., `AP-1`) in **red** at the
   top-right corner with a white background for legibility.

4. **Highlights critical text** in **yellow**:
   - Dimensions (overall, cutout, rough-in, mounting)
   - Clearance and tolerance requirements
   - Electrical specs (voltage, amperage, circuit, plug type)
   - Power and data requirements
   - Ducting / ventilation sizes
   - Plumbing (hole size, drain connection)
   - Weight (net, shipping)

5. **Combines** all annotated pages into a single PDF in schedule order.

---

## Step 5 — Troubleshooting

**Some pages didn't get a code label:**
→ The model number from the schedule wasn't found in the PDF text. This can
  happen with scanned/image-based PDFs. In that case, the script will print a
  warning. You can pass `--manual-map` to provide a JSON override:
```bash
--manual-map '{"AP-4": [{"file": "bosch_spec.pdf", "pages": [0, 1, 2]}]}'
```

**No highlights on a page:**
→ That page may not contain critical keywords, or the text may not
  be selectable. This is normal for marketing/overview pages.

**File permissions error on save:**
→ Save to a temp location first, then copy:
```bash
--output /tmp/annotated.pdf
# then copy to destination
```

---

## Output summary to user

After the script succeeds, share the link to the output PDF and mention:
- Total page count
- Which codes were annotated (list them)
- Any items that had no spec sheet found (from the warning output)
