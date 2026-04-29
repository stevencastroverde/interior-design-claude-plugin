"""
build_moodboard_html.py — HTML/CSS Grid moodboard renderer for interior-design-skills.

Produces a single-page PDF per room using WeasyPrint. Called by build_moodboard.py
when --layout grid is used. Row layout and spec pages remain in ReportLab.
"""

import base64
import os
import tempfile
from pathlib import Path

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
