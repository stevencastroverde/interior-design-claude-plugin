#!/usr/bin/env python3
"""
build_block.py — Assemble a DXF block with FF&E attributes from geometry JSON + product data.

Usage:
    python scripts/build_block.py \
        --geometry /tmp/geometry.json \
        --name "Solis Pendant" \
        --manufacturer "Pablo Designs" \
        --model "SOLI-24" \
        --finish "White Oak" \
        --dimensions '24"W × 24"D × 16"H' \
        --price "$1,200" \
        --category "PF" \
        --output /path/to/output.dxf

The geometry JSON format:
{
  "block_name": "PF-1-SOLIS-PENDANT",
  "units": "inches",
  "width": 24.0,
  "height": 16.0,
  "entities": [
    {"type": "lwpolyline", "points": [[x,y],...], "closed": true, "layer": "0-OUTLINE"},
    {"type": "circle",     "center": [x,y], "radius": r, "layer": "0-DETAIL"},
    {"type": "arc",        "center": [x,y], "radius": r, "start_angle": 0, "end_angle": 90, "layer": "0-DETAIL"},
    {"type": "line",       "start": [x,y], "end": [x,y], "layer": "0-CENTERLINE"}
  ]
}
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import ezdxf
    from ezdxf import units
except ImportError:
    print("ezdxf not installed. Run: pip install ezdxf --break-system-packages")
    sys.exit(1)


# --- Layer definitions ---
LAYERS = [
    ("0-OUTLINE",    7,   "Continuous"),  # white/black, outer silhouette
    ("0-DETAIL",     253, "Continuous"),  # light gray, internal features
    ("0-CENTERLINE", 1,   "CENTER"),      # red, symmetry and reference lines
    ("ATTRIBUTES",   3,   "Continuous"),  # green, attribute text
]

# FF&E attribute definitions: (tag, prompt, default_value)
ATTRIB_DEFS = [
    ("PRODUCT_NAME",  "Product Name",       ""),
    ("MANUFACTURER",  "Manufacturer",       ""),
    ("MODEL_NUMBER",  "Model / SKU",        ""),
    ("FINISH",        "Finish / Material",  ""),
    ("DIMENSIONS",    "Dimensions (W×D×H)", ""),
    ("PRICE",         "Unit Price",         ""),
    ("CATEGORY_CODE", "Category Code",      ""),
]

TEXT_HEIGHT = 0.75    # attribute text height in drawing units (inches)
LINE_SPACING = 1.1    # vertical spacing between attribute lines


def parse_args():
    p = argparse.ArgumentParser(description="Build a DXF block from geometry JSON + product data")
    p.add_argument("--geometry",     required=True,  help="Path to geometry JSON file")
    p.add_argument("--name",         required=True,  help="Product name (PRODUCT_NAME attribute)")
    p.add_argument("--manufacturer", default="",     help="Manufacturer name")
    p.add_argument("--model",        default="",     help="Model / SKU")
    p.add_argument("--finish",       default="",     help="Finish / Material")
    p.add_argument("--dimensions",   default="",     help='Dimensions string, e.g. 24"W × 18"D × 36"H')
    p.add_argument("--price",        default="",     help="Unit price, e.g. $1,200")
    p.add_argument("--category",     default="FURN", help="Category code from Master Abbreviation List")
    p.add_argument("--output",       required=True,  help="Output .dxf file path")
    return p.parse_args()


def load_geometry(path):
    with open(path) as f:
        return json.load(f)


def setup_document(units_str="inches"):
    """Create a new DXF R2013 document with proper unit settings."""
    doc = ezdxf.new("R2013")

    # Set drawing units in the header
    unit_code = 1 if units_str.lower() in ("in", "inches", "inch") else 4  # 4 = mm
    doc.header["$INSUNITS"] = unit_code
    doc.header["$LUNITS"] = 2   # decimal
    doc.header["$LUPREC"] = 3   # 3 decimal places

    return doc


def add_layers(doc):
    """Add the standard layer set to the document."""
    lt = doc.linetypes
    # Ensure CENTER linetype exists (may already be present)
    if "CENTER" not in [l.dxf.name for l in lt]:
        lt.add("CENTER", pattern=[0.75, 0.5, -0.25], description="Center ____ _ ____")

    for name, color, linetype in LAYERS:
        if name not in doc.layers:
            doc.layers.add(name, color=color, linetype=linetype)


def build_geometry(block, entities):
    """Add geometry entities to the block from the JSON description."""
    for ent in entities:
        etype = ent.get("type", "").lower()
        layer = ent.get("layer", "0-OUTLINE")

        try:
            if etype == "lwpolyline":
                pts = [tuple(p) for p in ent["points"]]
                closed = ent.get("closed", False)
                block.add_lwpolyline(pts, close=closed, dxfattribs={"layer": layer})

            elif etype == "circle":
                cx, cy = ent["center"]
                r = ent["radius"]
                block.add_circle((cx, cy), r, dxfattribs={"layer": layer})

            elif etype == "arc":
                cx, cy = ent["center"]
                r = ent["radius"]
                sa = ent.get("start_angle", 0)
                ea = ent.get("end_angle", 90)
                block.add_arc((cx, cy), r, sa, ea, dxfattribs={"layer": layer})

            elif etype == "line":
                sx, sy = ent["start"]
                ex, ey = ent["end"]
                block.add_line((sx, sy), (ex, ey), dxfattribs={"layer": layer})

            else:
                print(f"  Warning: Unknown entity type '{etype}' — skipped.")

        except Exception as e:
            print(f"  Warning: Failed to add entity {ent}: {e}")


def add_attdefs(block, product_height):
    """Add ATTDEF entities below the product geometry."""
    # Attributes start below the product bounding box with a small gap
    gap = TEXT_HEIGHT * 1.5
    y_start = -(gap + TEXT_HEIGHT)

    for i, (tag, prompt, default) in enumerate(ATTRIB_DEFS):
        y = y_start - (i * TEXT_HEIGHT * LINE_SPACING)
        block.add_attdef(
            tag=tag,
            insert=(0, y),
            dxfattribs={
                "prompt": prompt,
                "text": default,
                "height": TEXT_HEIGHT,
                "layer": "ATTRIBUTES",
                "color": 256,  # by layer
            }
        )


def insert_block_with_attribs(msp, block_name, attr_values):
    """Insert the block at the origin and populate its attributes."""
    block_ref = msp.add_blockref(block_name, insert=(0, 0))
    block_ref.add_auto_attribs(attr_values)
    return block_ref


def main():
    args = parse_args()

    # Load geometry
    geom_path = Path(args.geometry)
    if not geom_path.exists():
        print(f"Error: geometry file not found: {geom_path}")
        sys.exit(1)

    geom = load_geometry(geom_path)
    block_name = geom.get("block_name", f"BLOCK-{args.category.upper()}")
    units_str  = geom.get("units", "inches")
    entities   = geom.get("entities", [])
    prod_h     = geom.get("height", 36.0)

    print(f"Building DXF block: {block_name}")
    print(f"  Units: {units_str}")
    print(f"  Entities: {len(entities)}")

    # Build document
    doc = setup_document(units_str)
    add_layers(doc)

    # Create block definition
    block = doc.blocks.new(name=block_name)
    build_geometry(block, entities)
    add_attdefs(block, prod_h)

    # Populate attribute values
    attr_values = {
        "PRODUCT_NAME":  args.name,
        "MANUFACTURER":  args.manufacturer,
        "MODEL_NUMBER":  args.model,
        "FINISH":        args.finish,
        "DIMENSIONS":    args.dimensions,
        "PRICE":         args.price,
        "CATEGORY_CODE": args.category,
    }

    # Insert block in model space with populated attributes
    msp = doc.modelspace()
    insert_block_with_attribs(msp, block_name, attr_values)

    # Save
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(output))

    print(f"\n✅ DXF saved: {output}")
    print(f"   Block name: {block_name}")
    print(f"   Attributes: {', '.join(attr_values.keys())}")
    print(f"   Entities:   {len(entities)} geometry objects")


if __name__ == "__main__":
    main()
