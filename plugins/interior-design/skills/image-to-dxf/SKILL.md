---
name: image-to-dxf
description: >
  Converts a product photograph or render into a DXF block file (.dxf) with embedded FF&E
  attributes for use in AutoCAD, Revit, Rhino, BricsCAD, and other CAD tools. The block contains
  clean CAD geometry (lines, arcs, polylines) derived from the image, plus standard FF&E attributes
  (product name, manufacturer, model, finish, dimensions, price, category code) that can be
  scheduled, tagged, and extracted in CAD software.
  Use this skill whenever the user wants to: convert a product image to CAD, create a DXF or DWG
  block from a product photo, make a CAD symbol for a furniture piece or fixture, export a product
  to AutoCAD or Revit, create a block with attributes from a spec sheet, generate a DXF from a
  product clipping or markdown file, or prepare a product for insertion into a floor plan or
  elevation drawing. Trigger on: "convert to DXF", "make a DWG block", "product to CAD", "create
  a CAD block", "AutoCAD block", "DXF with attributes", "block with FF&E data", or any mention of
  wanting a product in a format that can be used in CAD software.
---

# Image-to-DXF Block Skill

You convert product images into DXF block files with embedded FF&E attributes. The result is a
`.dxf` file containing a named block definition — clean CAD geometry derived from the product
image, plus attribute tags populated with product data — ready to insert into any CAD drawing.

---

## What You Produce

A single `.dxf` file containing:
- A **block definition** with geometry on named layers (`0-OUTLINE`, `0-DETAIL`, `0-CENTERLINE`)
- **ATTDEF** fields for: `PRODUCT_NAME`, `MANUFACTURER`, `MODEL_NUMBER`, `FINISH`, `DIMENSIONS`,
  `PRICE`, `CATEGORY_CODE`
- A **block insert** at the origin with all attributes populated
- **Real-world units** (inches by default) when product dimensions are provided

The file opens in AutoCAD, Revit, Rhino, BricsCAD, and any other DXF-compatible application.

---

## Inputs

1. **A product image** — photograph, render, or spec sheet scan (PNG, JPG, WEBP)
2. **Product data** — from one of two sources, auto-detected:
   - **Markdown clipping** (`.md` file) — same format as the moodboard/room-schedule skills;
     read with `parse_product_data.py`
   - **Manual input** — user provides details in conversation (name, dimensions, price, etc.)

If the user provides a markdown file path, read it now using `scripts/parse_product_data.py`.
If they provide details inline, extract them from the conversation.

See `references/attribute-schema.md` for the complete attribute field definitions and formatting
rules, including category code lookup.

---

## Workflow

### Step 1 — Collect and Parse Inputs

Run the parser if a markdown file was provided:
```bash
python scripts/parse_product_data.py --input "/path/to/product.md"
```
This prints a JSON object with all FF&E fields. Use those values to populate the block attributes.

If data comes from conversation text, extract: name, manufacturer, model, finish, dimensions
(W×D×H), price, and category code. Refer to `references/attribute-schema.md` for category codes.

### Step 2 — Analyze the Image (Vision-First Approach)

Before writing any geometry, study the image carefully. This analysis step is what separates
clean CAD output from noisy traced outlines — you're reasoning about the product's intended
geometry, not just tracing pixels.

**2a. Identify the view type:**
- Front elevation → work directly in 2D XY
- Side elevation → work in 2D XY (different proportions)
- Plan/top view → work in 2D XY
- Perspective photo → mentally flatten to the most informative orthographic view
  (usually front elevation for furniture, plan for floor elements like rugs and tables)

When given a perspective photo, decide which view to produce and note it in your output filename
(e.g., `chair-front-elevation.dxf`). A front elevation is usually most useful for furniture;
a plan view most useful for tables, rugs, and area elements.

**2b. Establish the coordinate system:**
Use product dimensions to set up the drawing space. If dimensions are provided (e.g., 24"W × 18"D × 36"H):
- Place the origin (0, 0) at the **bottom-left** of the product's bounding box
- X axis runs left → right (width)
- Y axis runs bottom → top (height for elevation; depth for plan)
- All geometry coordinates are in inches (or mm if the product uses metric)

If no dimensions are provided, use a normalized space where the longest dimension = 100 units,
and note this in the block attributes.

**2c. Identify geometric zones:**
Break the product into logical regions. Think structurally, not decoratively:
- For a chair: seat platform, backrest, legs (×4 or ×2), armrests, stretchers
- For a pendant light: canopy/ceiling plate, cord/rod, shade or globe, hardware details
- For a faucet: body/spout, handle(s), base escutcheon, aerator
- For a sofa: seat cushion zone, back cushion zone, arms (×2), legs, overall frame

Each zone maps to one or more geometric entities. See `references/product-patterns.md` for
common patterns by product category.

**2d. Identify geometric primitives:**
For each zone, choose the right primitive:
- Straight runs → **line** or closed **lwpolyline**
- Round elements (knobs, circular bases, globes) → **circle**
- Curved elements (arcs, rounded corners, half-rounds) → **arc**
- Complex outlines (irregular silhouettes, tapered legs) → **lwpolyline** with multiple points
- Do NOT use free-form splines for standard products — clean polylines are more useful in CAD

**2e. Apply symmetry:**
Most products are bilaterally symmetric. Draw one side accurately, then mirror the geometry for
the other. This keeps the geometry mathematically consistent.

### Step 3 — Describe the Geometry as JSON

Build a geometry description JSON object. This is the input to `build_block.py`:

```json
{
  "block_name": "FURN-1-CHAIR-SAARINEN",
  "units": "inches",
  "width": 26.0,
  "height": 31.0,
  "entities": [
    {"type": "lwpolyline", "points": [[0,0],[26,0],[26,18],[0,18]], "closed": true, "layer": "0-OUTLINE"},
    {"type": "lwpolyline", "points": [[3,18],[5,31],[21,31],[23,18]], "closed": true, "layer": "0-DETAIL"},
    {"type": "arc", "center": [13,0], "radius": 10, "start_angle": 180, "end_angle": 360, "layer": "0-DETAIL"},
    {"type": "line", "start": [13,0], "end": [13,31], "layer": "0-CENTERLINE"}
  ]
}
```

**Layer assignments:**
- `0-OUTLINE` — outer silhouette and primary bounding geometry
- `0-DETAIL` — internal features, secondary structure, decorative elements
- `0-CENTERLINE` — symmetry axes and reference lines (use sparingly)

**Entity types supported by `build_block.py`:**
- `lwpolyline` → `points: [[x,y],...]`, `closed: true/false`
- `circle` → `center: [x,y]`, `radius: r`
- `arc` → `center: [x,y]`, `radius: r`, `start_angle: deg`, `end_angle: deg`
- `line` → `start: [x,y]`, `end: [x,y]`

Save this JSON to a temp file at `/tmp/geometry.json`.

### Step 4 — Assemble the DXF Block

Run the build script:
```bash
pip install ezdxf --break-system-packages -q
python scripts/build_block.py \
  --geometry /tmp/geometry.json \
  --name "PRODUCT NAME" \
  --manufacturer "MANUFACTURER" \
  --model "MODEL-SKU" \
  --finish "Finish / Material" \
  --dimensions "24\"W × 18\"D × 36\"H" \
  --price "$1,200" \
  --category "FURN" \
  --output "/path/to/output.dxf"
```

The script creates the DXF with the full block definition, ATTDEF fields, and a block insert
with populated ATTRIB values. It also sets `$INSUNITS` to inches (or mm) in the file header.

### Step 5 — Deliver

Save the `.dxf` file to the user's workspace folder. Use a descriptive filename based on the
category code and product name — for example:
- `AP-1-solis-pendant-front-elev.dxf`
- `FURN-2-saarinen-chair-front-elev.dxf`
- `CAB-1-shaker-upper-plan.dxf`

Tell the user which view was generated (front elevation, plan, etc.) and note any significant
simplifications made during geometry construction.

---

## Path B: Automated Tracing (Optional)

If the user explicitly requests automated tracing, or the product has complex organic geometry
where interpretation is difficult (sculptural objects, irregular hand-crafted forms), use the
tracing pipeline instead of manual geometry construction:

```bash
pip install vtracer --break-system-packages -q
python scripts/trace_image.py --input "/path/to/image.jpg" --output /tmp/traced.svg
python scripts/svg_to_dxf.py --input /tmp/traced.svg --output /tmp/traced_geometry.json \
  --width 24 --height 36
```

Then feed the resulting `traced_geometry.json` to `build_block.py` as the `--geometry` argument.

Note that automated tracing produces noisier, less geometrically clean output than manual
interpretation — warn the user that cleanup in CAD may be needed.

---

## Quality Checklist

Before delivering, verify:
- [ ] Block name follows the pattern `CATEGORY-NUM-PRODUCTNAME` (e.g., `PF-1-SOLIS-PENDANT`)
- [ ] All 7 attribute fields are populated (not left as empty strings)
- [ ] Geometry is to scale — if dimensions were provided, check that bounding box matches
- [ ] At least one entity is on layer `0-OUTLINE`
- [ ] The `.dxf` file was created without errors from `build_block.py`
- [ ] Filename is descriptive and includes the view type

---

## Reference Files

- `references/attribute-schema.md` — FF&E attribute field definitions, category code list,
  formatting rules for each field. Read this when you need the full category code lookup or
  are unsure how to format a field value.
- `references/product-patterns.md` — Common geometry patterns for furniture, lighting, plumbing,
  cabinetry, and accessories. Read this when you're unsure how to break down a specific product
  type into geometric primitives.
