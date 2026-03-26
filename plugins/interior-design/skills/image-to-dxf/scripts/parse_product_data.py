#!/usr/bin/env python3
"""
parse_product_data.py — Extract FF&E product data from a markdown clipping file.

Supports both YAML frontmatter and freeform markdown body text.
Outputs a JSON object with the standard FF&E attribute fields.

Usage:
    python scripts/parse_product_data.py --input /path/to/product.md
    python scripts/parse_product_data.py --input /path/to/product.md --output /tmp/product.json
"""

import argparse
import json
import re
import sys
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Extract product data from a markdown clipping")
    p.add_argument("--input",  required=True, help="Path to .md product file")
    p.add_argument("--output", default=None,  help="Optional: write JSON to this path")
    return p.parse_args()


def parse_frontmatter(text):
    """Extract YAML frontmatter from markdown text. Returns (frontmatter_dict, body_text)."""
    fm = {}
    body = text

    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            yaml_block = text[3:end].strip()
            body = text[end + 4:].strip()
            for line in yaml_block.split("\n"):
                if ":" in line:
                    key, _, val = line.partition(":")
                    fm[key.strip().lower()] = val.strip().strip('"').strip("'")

    return fm, body


def extract_price(text):
    """Find a dollar amount in text. Returns the first match or empty string."""
    m = re.search(r'\$[\d,]+(?:\.\d{2})?', text)
    return m.group(0) if m else ""


def extract_dimensions(text):
    """Find a W×D×H or W×H dimension string in text."""
    patterns = [
        r'(\d[\d./]*"?\s*[Ww][\s×xX]+\d[\d./]*"?\s*[Dd][\s×xX]+\d[\d./]*"?\s*[Hh])',
        r'(\d[\d./]*"?\s*[Ww][\s×xX]+\d[\d./]*"?\s*[Hh])',
        r'(\d[\d./]*\s*[Ww]\s*[×xX]\s*\d[\d./]*\s*[Dd]\s*[×xX]\s*\d[\d./]*\s*[Hh])',
        r'(\d+\s*mm\s*[Ww][\s×xX]+\d+\s*mm\s*[Dd][\s×xX]+\d+\s*mm\s*[Hh])',
        r'(\d+\s*cm\s*[Ww][\s×xX]+\d+\s*cm\s*[Hh])',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def infer_category(title, tags, body):
    """Guess the category code from product title, tags, and body text."""
    combined = f"{title} {' '.join(tags)} {body}".lower()

    rules = [
        (["pendant", "chandelier"], "PF"),
        (["sconce", "wall light", "wall fixture"], "WF"),
        (["flush mount", "ceiling fixture", "ceiling light", "recessed"], "CF"),
        (["table lamp", "desk lamp"], "TL"),
        (["floor lamp", "arc lamp", "torchiere"], "FL"),
        (["faucet", "tap"], "FA"),
        (["sink", "toilet", "bathtub", "tub", "shower"], "PL"),
        (["cabinet", "vanity", "built-in", "kitchen unit"], "CAB"),
        (["rug", "area rug", "runner"], "RUG"),
        (["mirror"], "MIR"),
        (["wallpaper", "grasscloth", "wall covering"], "WP"),
        (["tile", "ceramic", "porcelain"], "CT"),
        (["hardwood", "wood floor", "parquet", "engineered wood"], "WD"),
        (["appliance", "refrigerator", "range", "dishwasher", "oven"], "AP"),
        (["sofa", "couch", "sectional", "chair", "ottoman", "bench", "stool",
          "table", "desk", "dresser", "bookshelf", "bookcase", "bed",
          "nightstand", "console"], "FURN"),
        (["fabric", "textile", "velvet", "linen", "bouclé"], "TX"),
        (["art", "print", "painting", "photograph"], "ART"),
        (["plant", "planter", "botanical"], "PLT"),
    ]

    for keywords, code in rules:
        if any(kw in combined for kw in keywords):
            return code

    return "ACC"  # default: decorative accessory


def parse_product(md_path):
    """Parse a product markdown file and return a normalized product dict."""
    text = Path(md_path).read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)

    # Product name
    name = fm.get("title") or fm.get("name") or ""
    if not name:
        # Try first H1 heading
        m = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
        name = m.group(1).strip() if m else Path(md_path).stem.replace("-", " ").title()

    # Manufacturer / brand
    manufacturer = (
        fm.get("manufacturer") or
        fm.get("brand") or
        fm.get("author") or
        fm.get("maker") or ""
    )

    # Model / SKU
    model = fm.get("model") or fm.get("sku") or fm.get("model_number") or ""
    if not model:
        m = re.search(r'(?:model|sku|item)[#:\s]+([A-Z0-9][-A-Z0-9_./]{2,20})', body, re.IGNORECASE)
        model = m.group(1) if m else ""

    # Finish / Material
    finish = (
        fm.get("finish") or
        fm.get("material") or
        fm.get("color") or
        fm.get("finish_color") or ""
    )

    # Dimensions
    dimensions = fm.get("dimensions") or fm.get("size") or ""
    if not dimensions:
        dimensions = extract_dimensions(body)

    # Price
    price = fm.get("price") or ""
    if not price:
        price = extract_price(body)

    # Tags for category inference
    tags_raw = fm.get("tags", "")
    if isinstance(tags_raw, str):
        tags = [t.strip().strip("[]") for t in tags_raw.split(",")]
    elif isinstance(tags_raw, list):
        tags = tags_raw
    else:
        tags = []

    # Category code
    category = fm.get("category") or fm.get("type") or infer_category(name, tags, body)

    # Source URL (for reference, not an attribute field)
    source = fm.get("source") or fm.get("url") or fm.get("link") or ""

    return {
        "name":         name,
        "manufacturer": manufacturer,
        "model":        model,
        "finish":       finish,
        "dimensions":   dimensions,
        "price":        price,
        "category":     category.upper(),
        "source":       source,
    }


def main():
    args = parse_args()

    if not Path(args.input).exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    product = parse_product(args.input)
    output_json = json.dumps(product, indent=2)

    if args.output:
        Path(args.output).write_text(output_json)
        print(f"Product data written to {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
