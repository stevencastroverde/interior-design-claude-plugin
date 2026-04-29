"""
build_moodboard_html.py — HTML/CSS Grid moodboard renderer for interior-design-skills.

Produces a single-page PDF per room using WeasyPrint. Called by build_moodboard.py
when --layout grid is used. Row layout and spec pages remain in ReportLab.
"""

import base64
import os
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


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def image_to_data_uri(img_path) -> str:
    """
    Read an image file and return a base64 data URI string.
    Returns '' if path is None or file does not exist.
    Always re-encodes as JPEG at quality=90 for consistent output.
    """
    if not img_path or not os.path.exists(img_path):
        return ''
    try:
        from PIL import Image as PILImage
        from io import BytesIO
        img = PILImage.open(img_path).convert('RGB')
        buf = BytesIO()
        img.save(buf, 'JPEG', quality=90)
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        return f'data:image/jpeg;base64,{b64}'
    except Exception:
        return ''


# ─────────────────────────────────────────────────────────────────────────────
# HTML RENDERER
# ─────────────────────────────────────────────────────────────────────────────

_BG        = '#EAE5DC'
_DARK      = '#1C1E18'
_CAPTION   = '#7A7065'
_MARGIN_IN = 0.45


def _render_cell(slot: dict, prod) -> str:
    """Return the HTML string for a single grid cell."""
    col_style = f'grid-column: {slot["col"]}; grid-row: {slot["row"]};'

    if slot['dark']:
        return f'<div style="{col_style} background:{_DARK};"></div>\n'

    if prod is None:
        return f'<div style="{col_style} background:{_BG};"></div>\n'

    uri = image_to_data_uri(prod.get('img'))
    title = (prod.get('title') or '').upper()[:30]

    if uri:
        img_tag = (
            f'<img src="{uri}" style="width:100%;height:100%;'
            f'object-fit:contain;background:{_BG};display:block;" '
            f'alt="{title}">'
        )
    else:
        img_tag = (
            f'<div style="width:100%;height:100%;background:{_BG};'
            f'display:flex;align-items:center;justify-content:center;">'
            f'<span style="font-size:8pt;color:{_CAPTION};">{title}</span></div>'
        )

    return (
        f'<div style="{col_style} overflow:hidden; position:relative;">\n'
        f'  {img_tag}\n'
        f'  <div style="position:absolute;bottom:0;left:0;right:0;'
        f'text-align:center;padding:3pt 0;font-family:Helvetica,Arial,sans-serif;'
        f'font-size:5.5pt;color:{_CAPTION};letter-spacing:.04em;">'
        f'{title}</div>\n'
        f'</div>\n'
    )


def render_moodboard_html(room: dict, template_name: str,
                          palette: list = None) -> str:
    """
    Return a complete HTML string for the moodboard page.

    room: dict with 'name', 'subtitle', 'products'
    template_name: key into TEMPLATES
    palette: list of hex strings, or None
    """
    tmpl = TEMPLATES[template_name]
    products = room.get('products', [])
    subtitle = room.get('subtitle', '').lower()

    assignments = assign_products_to_slots(products, template_name)

    # Build grid cells HTML
    slots = tmpl['slots']
    cells_html = ''.join(
        _render_cell(slots[i], assignments[i])
        for i in range(len(slots))
    )

    # Palette strip
    palette_html = ''
    if palette:
        swatches = ''.join(
            f'<div style="flex:1;background:{h.strip()};"></div>'
            for h in palette
        )
        palette_html = (
            f'<div class="palette-strip" style="display:flex;height:40pt;'
            f'margin-top:4pt;gap:0;">{swatches}</div>'
        )

    m = f'{_MARGIN_IN}in'

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: 17in 11in landscape;
    margin: 0;
  }}
  html, body {{
    margin: 0; padding: 0;
    width: 17in; height: 11in;
    background: {_BG};
    font-family: Helvetica, Arial, sans-serif;
  }}
  .page-inner {{
    padding: {m};
    box-sizing: border-box;
    width: 100%; height: 100%;
    display: flex;
    flex-direction: column;
  }}
  .heading {{
    margin-bottom: 10pt;
  }}
  .heading .room-type {{
    font-size: 7.5pt;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: {_CAPTION};
  }}
  .heading .room-word {{
    font-family: 'Times New Roman', Times, serif;
    font-style: italic;
    font-size: 28pt;
    color: #1A1A18;
    line-height: 1.1;
    margin: 0;
  }}
  .grid {{
    display: grid;
    grid-template-columns: {tmpl['css_columns']};
    grid-template-rows: {tmpl['css_rows']};
    gap: 4pt;
    flex: 1;
  }}
</style>
</head>
<body>
<div class="page-inner">
  <div class="heading">
    <div class="room-type">room</div>
    <div class="room-word">{subtitle}</div>
  </div>
  <div class="grid">
{cells_html}  </div>
  {palette_html}
</div>
</body>
</html>"""
    return html


# ─────────────────────────────────────────────────────────────────────────────
# WEASYPRINT PDF CONVERSION
# ─────────────────────────────────────────────────────────────────────────────

try:
    import weasyprint as _wp
    _weasyprint_available = True
except ImportError:
    _weasyprint_available = False


def render_room_to_pdf(room: dict, output_path: str,
                       template_name: str = None,
                       palette: list = None) -> str:
    """
    Render one room's moodboard page to a PDF file via WeasyPrint.

    template_name: override template; if None, auto-selected by product count.
    palette: list of hex strings, or None.
    Returns output_path on success.
    Raises RuntimeError if WeasyPrint is not installed.
    """
    if not _weasyprint_available:
        raise RuntimeError(
            'WeasyPrint is not installed. Run:\n'
            '  pip install weasyprint --break-system-packages\n'
            'On macOS you may also need: brew install pango'
        )

    products = room.get('products', [])
    tmpl_name = select_template(len(products), override=template_name)
    html = render_moodboard_html(room, tmpl_name, palette=palette)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    _wp.HTML(string=html).write_pdf(output_path)
    return output_path
