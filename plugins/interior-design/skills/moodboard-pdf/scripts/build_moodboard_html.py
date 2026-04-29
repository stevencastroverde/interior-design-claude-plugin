"""
build_moodboard_html.py — HTML/CSS Grid moodboard renderer for interior-design-skills.

Produces a single-page PDF per room using WeasyPrint. Called by build_moodboard.py
when --layout grid is used. Row layout and spec pages remain in ReportLab.
"""

import base64        # used by Task 5 (image_to_data_uri)
import os            # used by Task 5 (image_to_data_uri)
import tempfile      # used by Task 7 (render_room_to_pdf)
from pathlib import Path  # used by Task 7 (render_room_to_pdf)

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY DETECTION
# ─────────────────────────────────────────────────────────────────────────────

_KEYWORDS = {
    'furniture': ['sofa', 'sectional', 'chair', 'armchair', 'table', 'desk',
                  'cabinet', 'dresser', 'bed', 'ottoman', 'bench', 'bookcase', 'shelf'],
    'lighting':  ['lamp', 'pendant', 'sconce', 'chandelier', 'fixture', 'lantern'],
    'textile':   ['rug', 'curtain', 'drape', 'pillow', 'cushion', 'throw', 'blanket'],
    'accessory': ['vase', 'bowl', 'tray', 'artwork', 'mirror', 'plant', 'basket',
                  'candle', 'frame', 'sculpture', 'object'],
}

_CATEGORY_PRIORITY = ['furniture', 'lighting', 'textile', 'accessory']


def detect_category(product: dict) -> str:
    """
    Return the product category string.

    Reads 'category' frontmatter field first; falls back to keyword inference
    from the product title. Returns 'accessory' if nothing matches.
    """
    explicit = (product.get('category') or '').strip().lower()
    if explicit in _CATEGORY_PRIORITY:
        return explicit

    title = (product.get('title') or '').lower()
    for cat in _CATEGORY_PRIORITY:
        if any(kw in title for kw in _KEYWORDS[cat]):
            return cat

    return 'accessory'


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE DEFINITIONS
# Each slot: col (CSS grid-column), row (CSS grid-row), size_rank (1=largest)
# col/row values are CSS grid-column/grid-row shorthand strings, e.g. "1 / 3"
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATES = {
    'anchor-left': {
        'css_columns': '1.5fr 1fr 1fr 0.8fr',
        'css_rows':    '1fr 1fr',
        'slots': [
            {'col': '1',     'row': '1 / 3', 'size_rank': 1, 'dark': False},  # hero
            {'col': '4',     'row': '1 / 3', 'size_rank': 3, 'dark': True},   # dark accent
            {'col': '2',     'row': '1',     'size_rank': 2, 'dark': False},
            {'col': '3',     'row': '1',     'size_rank': 2, 'dark': False},
            {'col': '2',     'row': '2',     'size_rank': 2, 'dark': False},
            {'col': '3',     'row': '2',     'size_rank': 2, 'dark': False},
        ],
    },
    'feature-top': {
        'css_columns': '1.8fr 1fr 1fr',
        'css_rows':    '1.2fr 1fr',
        'slots': [
            {'col': '1 / 3', 'row': '1',     'size_rank': 1, 'dark': False},  # wide hero
            {'col': '3',     'row': '1',     'size_rank': 2, 'dark': True},   # dark accent
            {'col': '1',     'row': '2',     'size_rank': 2, 'dark': False},
            {'col': '2',     'row': '2',     'size_rank': 2, 'dark': False},
            {'col': '3',     'row': '2',     'size_rank': 2, 'dark': False},
        ],
    },
    'collage': {
        'css_columns': '1fr 1.3fr 1fr 1fr',
        'css_rows':    '1fr 1.1fr 0.9fr',
        'slots': [
            {'col': '1',     'row': '1 / 3', 'size_rank': 1, 'dark': False},  # tall hero
            {'col': '2',     'row': '1',     'size_rank': 2, 'dark': False},
            {'col': '3 / 5', 'row': '1',     'size_rank': 1, 'dark': False},  # wide span
            {'col': '2',     'row': '2',     'size_rank': 3, 'dark': True},   # dark accent
            {'col': '3',     'row': '2',     'size_rank': 3, 'dark': False},
            {'col': '4',     'row': '2',     'size_rank': 3, 'dark': False},
            {'col': '1 / 3', 'row': '3',     'size_rank': 2, 'dark': False},  # wide bottom
            {'col': '3',     'row': '3',     'size_rank': 3, 'dark': False},
            {'col': '4',     'row': '3',     'size_rank': 3, 'dark': False},
        ],
    },
}


def select_template(product_count: int, override: str = None) -> str:
    """
    Choose the grid template name for this room.

    override: if set and a valid template name, use it regardless of count.
    Auto-selection: anchor-left for ≤6 products, collage for 7+.
    """
    if override and override in TEMPLATES:
        return override
    return 'anchor-left' if product_count <= 6 else 'collage'


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT → SLOT ASSIGNMENT
# ─────────────────────────────────────────────────────────────────────────────

_CATEGORY_RANK = {'furniture': 1, 'lighting': 2, 'textile': 2, 'accessory': 3}


def assign_products_to_slots(products: list, template_name: str) -> list:
    """
    Assign products to template slots. Returns a list parallel to template slots,
    where each entry is either a product dict or None.

    Rules:
    - Dark slots (accent cells) always receive None — they render as solid #1C1E18.
    - Non-dark slots are ranked by size_rank (1=largest first).
    - Products are sorted by category priority (furniture first, accessories last).
    - Products fill slots in size_rank order; extras are dropped, empties are None.
    """
    tmpl = TEMPLATES[template_name]
    slots = tmpl['slots']

    # Sort products: furniture (rank 1) → lighting/textile (rank 2) → accessory (rank 3)
    sorted_products = sorted(
        products,
        key=lambda p: _CATEGORY_RANK.get(detect_category(p), 3)
    )

    # Sort non-dark slot indices by size_rank ascending (largest cells first)
    fillable = sorted(
        [i for i, s in enumerate(slots) if not s['dark']],
        key=lambda i: slots[i]['size_rank']
    )

    product_iter = iter(sorted_products)
    result = [None] * len(slots)

    for slot_idx in fillable:
        prod = next(product_iter, None)
        result[slot_idx] = prod  # None if we ran out of products

    return result
