# Moodboard HTML Grid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the uniform ReportLab grid on moodboard pages with an HTML/CSS Grid renderer (WeasyPrint) that places furniture in large hero cells and accessories in small cells, using three editorial templates.

**Architecture:** A new `build_moodboard_html.py` generates the moodboard page as HTML, converts it to PDF via WeasyPrint, and returns a temp PDF path. The existing `build_moodboard.py` calls it when `--layout grid` is used, then merges the result with the ReportLab cover + spec pages using `pypdf`. Row layout is untouched.

**Tech Stack:** Python 3, WeasyPrint, pypdf, Pillow (already installed), base64 image embedding, CSS Grid

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py` | Category detection, template selection, slot assignment, HTML rendering, WeasyPrint conversion |
| Create | `plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py` | All unit + integration tests |
| Modify | `plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard.py` | Call HTML renderer for grid layout, merge PDFs with pypdf, add `--template` CLI arg |

---

## Task 1: Install dependencies

**Files:**
- No file changes — verify environment only

- [ ] **Step 1: Install WeasyPrint and pypdf**

```bash
pip install weasyprint pypdf --break-system-packages
```

- [ ] **Step 2: Verify both import cleanly**

```bash
python3 -c "import weasyprint; import pypdf; print('OK')"
```

Expected output: `OK`

If WeasyPrint fails with a missing system lib error on macOS, run:
```bash
brew install pango
```

- [ ] **Step 3: Commit the verified environment note**

```bash
cd plugins/interior-design/skills/moodboard-pdf
# No code change — just confirm deps work before writing any code
git commit --allow-empty -m "chore: verify weasyprint + pypdf available for html grid renderer"
```

---

## Task 2: Category detection

**Files:**
- Create: `plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py`
- Create: `plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py`

- [ ] **Step 1: Create the test file with failing tests for `detect_category`**

Create `plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from build_moodboard_html import detect_category


def test_explicit_category_field_wins():
    prod = {'category': 'lighting', 'title': 'Restoration Hardware Sofa'}
    assert detect_category(prod) == 'lighting'


def test_furniture_inferred_from_title():
    for title in ['Porto Sectional', 'Walnut Dining Table', 'Linen Armchair', 'Oak Cabinet']:
        assert detect_category({'title': title}) == 'furniture', title


def test_lighting_inferred_from_title():
    for title in ['Woven Pendant', 'Brass Sconce', 'Arc Floor Lamp', 'Chandelier']:
        assert detect_category({'title': title}) == 'lighting', title


def test_textile_inferred_from_title():
    for title in ['Moroccan Rug', 'Linen Curtain', 'Velvet Pillow', 'Wool Throw']:
        assert detect_category({'title': title}) == 'textile', title


def test_accessory_inferred_from_title():
    for title in ['Ceramic Vase', 'Wooden Bowl', 'Woven Basket', 'Candle']:
        assert detect_category({'title': title}) == 'accessory', title


def test_unknown_title_returns_accessory():
    assert detect_category({'title': 'XYZ-9000'}) == 'accessory'


def test_case_insensitive():
    assert detect_category({'title': 'LINEN SOFA'}) == 'furniture'
```

- [ ] **Step 2: Run tests — expect ImportError (module doesn't exist yet)**

```bash
cd plugins/interior-design/skills/moodboard-pdf/scripts
python3 -m pytest tests/test_build_moodboard_html.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'build_moodboard_html'`

- [ ] **Step 3: Create `build_moodboard_html.py` with `detect_category` only**

Create `plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py`:

```python
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
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
cd plugins/interior-design/skills/moodboard-pdf/scripts
python3 -m pytest tests/test_build_moodboard_html.py -v -k "detect_category"
```

Expected: 7 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py \
        plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py
git commit -m "feat: add detect_category with keyword inference fallback"
```

---

## Task 3: Template slot definitions and auto-selection

**Files:**
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py`
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py`

- [ ] **Step 1: Add failing tests for `select_template` and `TEMPLATES`**

Append to `tests/test_build_moodboard_html.py`:

```python
from build_moodboard_html import select_template, TEMPLATES


def test_anchor_left_selected_for_2_to_6():
    for n in [2, 3, 4, 5, 6]:
        assert select_template(n) == 'anchor-left', f"n={n}"


def test_collage_selected_for_7_plus():
    for n in [7, 8, 9, 10, 15]:
        assert select_template(n) == 'collage', f"n={n}"


def test_feature_top_override():
    assert select_template(5, override='feature-top') == 'feature-top'


def test_templates_have_required_keys():
    for name, tmpl in TEMPLATES.items():
        assert 'css_columns' in tmpl, name
        assert 'css_rows' in tmpl, name
        assert 'slots' in tmpl, name
        for slot in tmpl['slots']:
            assert 'col' in slot, f"{name} slot missing col"
            assert 'row' in slot, f"{name} slot missing row"
            assert 'size_rank' in slot, f"{name} slot missing size_rank"


def test_anchor_left_has_6_slots():
    assert len(TEMPLATES['anchor-left']['slots']) == 6


def test_collage_has_9_slots():
    assert len(TEMPLATES['collage']['slots']) == 9


def test_feature_top_has_5_slots():
    assert len(TEMPLATES['feature-top']['slots']) == 5
```

- [ ] **Step 2: Run tests — expect failures**

```bash
python3 -m pytest tests/test_build_moodboard_html.py -v -k "template" 2>&1 | tail -15
```

Expected: `ImportError` or `AssertionError` — `select_template` and `TEMPLATES` not defined yet.

- [ ] **Step 3: Add `TEMPLATES` and `select_template` to `build_moodboard_html.py`**

Append after the `detect_category` function:

```python
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
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
python3 -m pytest tests/test_build_moodboard_html.py -v -k "template"
```

Expected: 7 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py \
        plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py
git commit -m "feat: add TEMPLATES data and select_template auto-selection"
```

---

## Task 4: Category-aware product → slot assignment

**Files:**
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py`
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py`

- [ ] **Step 1: Add failing tests for `assign_products_to_slots`**

Append to `tests/test_build_moodboard_html.py`:

```python
from build_moodboard_html import assign_products_to_slots


def _make_products(specs):
    """specs: list of (title, category_or_None)"""
    return [{'title': t, 'category': c} for t, c in specs]


def test_furniture_lands_in_size_rank_1_slot():
    products = _make_products([
        ('Porto Sofa', 'furniture'),
        ('Ceramic Vase', 'accessory'),
        ('Woven Pendant', 'lighting'),
        ('Marble Table', 'furniture'),
    ])
    assignments = assign_products_to_slots(products, 'anchor-left')
    # slot index 0 is size_rank=1 (hero) — should hold a furniture product
    hero_title = assignments[0]['title']
    assert hero_title in ('Porto Sofa', 'Marble Table')


def test_dark_slots_receive_no_product():
    products = _make_products([('Sofa', 'furniture')] * 5)
    assignments = assign_products_to_slots(products, 'anchor-left')
    # slot index 1 is dark=True in anchor-left — should be None
    assert assignments[1] is None


def test_fewer_products_than_slots_pads_with_none():
    products = _make_products([('Sofa', 'furniture'), ('Vase', 'accessory')])
    assignments = assign_products_to_slots(products, 'anchor-left')
    assert len(assignments) == 6  # anchor-left has 6 slots
    none_count = sum(1 for a in assignments if a is None)
    assert none_count >= 4  # at least 4 empty (1 dark + 3 unfilled)


def test_returns_one_entry_per_slot():
    products = _make_products([('Sofa', 'furniture')] * 9)
    assignments = assign_products_to_slots(products, 'collage')
    assert len(assignments) == 9
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
python3 -m pytest tests/test_build_moodboard_html.py -v -k "assign" 2>&1 | tail -10
```

Expected: `ImportError: cannot import name 'assign_products_to_slots'`

- [ ] **Step 3: Implement `assign_products_to_slots`**

Append to `build_moodboard_html.py`:

```python
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
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
python3 -m pytest tests/test_build_moodboard_html.py -v -k "assign"
```

Expected: 4 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py \
        plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py
git commit -m "feat: category-aware slot assignment — furniture to hero cells"
```

---

## Task 5: Base64 image embedding

**Files:**
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py`
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py`

- [ ] **Step 1: Add failing tests for `image_to_data_uri`**

Append to `tests/test_build_moodboard_html.py`:

```python
import tempfile, os
from PIL import Image as PILImage
from build_moodboard_html import image_to_data_uri


def test_returns_data_uri_for_valid_image(tmp_path):
    img = PILImage.new('RGB', (10, 10), color=(200, 180, 160))
    p = tmp_path / 'test.jpg'
    img.save(str(p), 'JPEG')
    uri = image_to_data_uri(str(p))
    assert uri.startswith('data:image/jpeg;base64,')


def test_returns_placeholder_for_missing_file():
    uri = image_to_data_uri('/nonexistent/path/img.jpg')
    assert uri == ''


def test_returns_empty_string_for_none():
    assert image_to_data_uri(None) == ''
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
python3 -m pytest tests/test_build_moodboard_html.py -v -k "data_uri" 2>&1 | tail -10
```

- [ ] **Step 3: Implement `image_to_data_uri`**

Append to `build_moodboard_html.py`:

```python
# ─────────────────────────────────────────────────────────────────────────────
# IMAGE UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def image_to_data_uri(img_path: str | None) -> str:
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
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
python3 -m pytest tests/test_build_moodboard_html.py -v -k "data_uri"
```

Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py \
        plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py
git commit -m "feat: image_to_data_uri for base64 embedding in HTML"
```

---

## Task 6: HTML template renderer

**Files:**
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py`
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py`

- [ ] **Step 1: Add failing tests for `render_moodboard_html`**

Append to `tests/test_build_moodboard_html.py`:

```python
from build_moodboard_html import render_moodboard_html


def _sample_room():
    return {
        'name': 'LIVING ROOM',
        'subtitle': 'living room',
        'products': [
            {'title': 'Porto Sectional', 'category': 'furniture', 'img': None},
            {'title': 'Brass Pendant',   'category': 'lighting',  'img': None},
            {'title': 'Ceramic Vase',    'category': 'accessory', 'img': None},
            {'title': 'Wool Rug',        'category': 'textile',   'img': None},
        ],
    }


def test_render_returns_html_string():
    html = render_moodboard_html(_sample_room(), template_name='anchor-left')
    assert isinstance(html, str)
    assert '<html' in html


def test_render_includes_room_heading():
    html = render_moodboard_html(_sample_room(), template_name='anchor-left')
    assert 'living room' in html.lower()


def test_render_includes_css_grid():
    html = render_moodboard_html(_sample_room(), template_name='anchor-left')
    assert 'display: grid' in html or 'display:grid' in html


def test_render_includes_palette_strip_when_palette_given():
    html = render_moodboard_html(
        _sample_room(), template_name='anchor-left',
        palette=['#3D3530', '#EAE5DC', '#C07C60']
    )
    assert '#3D3530' in html
    assert 'palette-strip' in html


def test_render_no_palette_strip_when_not_given():
    html = render_moodboard_html(_sample_room(), template_name='anchor-left')
    assert 'palette-strip' not in html


def test_render_dark_slot_uses_dark_bg():
    html = render_moodboard_html(_sample_room(), template_name='anchor-left')
    assert '#1C1E18' in html or '1c1e18' in html.lower()
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
python3 -m pytest tests/test_build_moodboard_html.py -v -k "render" 2>&1 | tail -10
```

- [ ] **Step 3: Implement `render_moodboard_html`**

Append to `build_moodboard_html.py`:

```python
# ─────────────────────────────────────────────────────────────────────────────
# HTML RENDERER
# ─────────────────────────────────────────────────────────────────────────────

_BG        = '#EAE5DC'
_DARK      = '#1C1E18'
_CAPTION   = '#7A7065'
_MARGIN_IN = 0.45


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
    cells_html = ''
    slots = tmpl['slots']
    for i, slot in enumerate(slots):
        prod = assignments[i]
        col_style = f'grid-column: {slot["col"]}; grid-row: {slot["row"]};'

        if slot['dark']:
            cells_html += (
                f'<div style="{col_style} background:{_DARK};"></div>\n'
            )
            continue

        if prod is None:
            cells_html += (
                f'<div style="{col_style} background:{_BG};"></div>\n'
            )
            continue

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

        cells_html += (
            f'<div style="{col_style} overflow:hidden; position:relative;">\n'
            f'  {img_tag}\n'
            f'  <div style="position:absolute;bottom:0;left:0;right:0;'
            f'text-align:center;padding:3pt 0;font-family:Helvetica,Arial,sans-serif;'
            f'font-size:5.5pt;color:{_CAPTION};letter-spacing:.04em;">'
            f'{title}</div>\n'
            f'</div>\n'
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
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
python3 -m pytest tests/test_build_moodboard_html.py -v -k "render"
```

Expected: 6 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py \
        plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py
git commit -m "feat: render_moodboard_html — CSS Grid template with base64 images"
```

---

## Task 7: WeasyPrint PDF conversion

**Files:**
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py`
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py`

- [ ] **Step 1: Add failing test for `render_room_to_pdf`**

Append to `tests/test_build_moodboard_html.py`:

```python
from build_moodboard_html import render_room_to_pdf


def test_render_room_to_pdf_creates_file(tmp_path):
    room = {
        'name': 'LIVING ROOM',
        'subtitle': 'living room',
        'products': [
            {'title': 'Porto Sectional', 'category': 'furniture', 'img': None},
            {'title': 'Ceramic Vase',    'category': 'accessory', 'img': None},
        ],
    }
    out = tmp_path / 'moodboard.pdf'
    result = render_room_to_pdf(room, str(out), template_name='anchor-left')
    assert result == str(out)
    assert out.exists()
    assert out.stat().st_size > 1000  # non-empty PDF


def test_render_room_to_pdf_raises_clear_error_if_weasyprint_missing(
    tmp_path, monkeypatch
):
    import sys
    # Simulate WeasyPrint not installed
    monkeypatch.setitem(sys.modules, 'weasyprint', None)
    import importlib
    import build_moodboard_html as bmh
    monkeypatch.setattr(bmh, '_weasyprint_available', False)

    room = {'name': 'X', 'subtitle': 'x', 'products': []}
    out = tmp_path / 'out.pdf'
    try:
        bmh.render_room_to_pdf(room, str(out))
        assert False, "should have raised"
    except RuntimeError as e:
        assert 'weasyprint' in str(e).lower()
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
python3 -m pytest tests/test_build_moodboard_html.py -v -k "render_room_to_pdf" 2>&1 | tail -10
```

- [ ] **Step 3: Implement `render_room_to_pdf`**

Append to `build_moodboard_html.py` (before the final newline):

```python
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
```

- [ ] **Step 4: Run tests — expect both pass**

```bash
python3 -m pytest tests/test_build_moodboard_html.py -v -k "render_room_to_pdf"
```

Expected: 2 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard_html.py \
        plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py
git commit -m "feat: render_room_to_pdf via WeasyPrint with graceful missing-dep error"
```

---

## Task 8: Wire into build_moodboard.py — merge step

**Files:**
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard.py`
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py`

- [ ] **Step 1: Add imports to `build_moodboard.py`**

At the top of `build_moodboard.py`, after the existing `try/except ImportError` block (around line 44), add:

```python
try:
    from pypdf import PdfWriter, PdfReader
    _pypdf_available = True
except ImportError:
    _pypdf_available = False
```

- [ ] **Step 2: Add `--template` argument to the CLI parser**

In `build_moodboard.py`, find the argparse block (around line 866) where `--layout` is defined. After it, add:

```python
    parser.add_argument(
        '--template', default=None,
        choices=['anchor-left', 'feature-top', 'collage'],
        help='Pin a specific grid template (default: auto-selected by product count)'
    )
```

- [ ] **Step 3: Thread `template` through `build_pdf` and `auto_build_from_directory`**

In `build_moodboard.py`, update the `build_pdf` signature (line 772) to accept `template=None`:

```python
def build_pdf(rooms, output_path, project_name='', studio='',
              logo_path=None, footer_right='MATERIAL SPECIFICATION',
              layout='row', palette=None, template=None):
```

Update `auto_build_from_directory` signature (line 816) to accept and forward `template=None`:

```python
def auto_build_from_directory(project_dir, output_path, project_name='', studio='',
                               logo_path=None, footer_right='MATERIAL SPECIFICATION',
                               layout='row', palette=None, template=None):
```

And in the `return build_pdf(...)` call at the bottom of `auto_build_from_directory`:

```python
    return build_pdf(rooms, output_path, project_name=project_name, studio=studio,
                     logo_path=logo_path, footer_right=footer_right,
                     layout=layout, palette=palette, template=template)
```

- [ ] **Step 4: Replace the grid moodboard path in `build_pdf` with the HTML pipeline**

In `build_pdf` (currently around lines 796–810), replace:

```python
    c = canvas.Canvas(str(output_path), pagesize=PAGE)
    c.setTitle(f'Material Specification — {project_name}')
    c.setAuthor(studio)
    c.setSubject('Interior Design Material Specification')

    draw_cover(c, project_name, studio, rooms,
               logo_reader=logo_reader, footer_right=footer_right)

    for room in rooms:
        draw_moodboard(c, room, logo_reader=logo_reader, studio=studio,
                       layout=layout, palette=palette)
        draw_room_specs(c, room, logo_reader=logo_reader, studio=studio,
                        project_name=project_name, footer_right=footer_right)

    c.save()
    size = output_path.stat().st_size
    print(f'✅ PDF saved: {output_path}  ({size // 1024} KB,  {1 + len(rooms) * 2}+ pages)')
    return str(output_path)
```

With this:

```python
    if layout == 'grid':
        # ── HTML/CSS Grid path ───────────────────────────────────────────────
        if not _pypdf_available:
            raise RuntimeError(
                'pypdf is required for grid layout. Run:\n'
                '  pip install pypdf --break-system-packages'
            )
        import sys as _sys
        _scripts_dir = str(Path(__file__).parent)
        if _scripts_dir not in _sys.path:
            _sys.path.insert(0, _scripts_dir)
        from build_moodboard_html import render_room_to_pdf

        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            # Cover + spec pages via ReportLab
            rl_path = tmp / 'rl_pages.pdf'
            c = canvas.Canvas(str(rl_path), pagesize=PAGE)
            c.setTitle(f'Material Specification — {project_name}')
            c.setAuthor(studio)
            c.setSubject('Interior Design Material Specification')
            draw_cover(c, project_name, studio, rooms,
                       logo_reader=logo_reader, footer_right=footer_right)
            for room in rooms:
                draw_room_specs(c, room, logo_reader=logo_reader, studio=studio,
                                project_name=project_name, footer_right=footer_right)
            c.save()

            # Moodboard pages via WeasyPrint — one PDF per room
            moodboard_paths = []
            for room in rooms:
                mp = tmp / f'moodboard_{room["name"]}.pdf'
                render_room_to_pdf(room, str(mp), template_name=template,
                                   palette=palette)
                moodboard_paths.append((room, str(mp)))

            # Merge: cover | (moodboard + spec pages per room) → final PDF
            writer = PdfWriter()

            rl_reader = PdfReader(str(rl_path))
            # Page 0 = cover
            writer.add_page(rl_reader.pages[0])

            spec_page_idx = 1  # pages after cover in rl_pages.pdf
            for i, (room, mb_path) in enumerate(moodboard_paths):
                # Moodboard page(s)
                mb_reader = PdfReader(mb_path)
                for pg in mb_reader.pages:
                    writer.add_page(pg)
                # Spec pages for this room
                n_spec_pages = len(room['products'])
                n_spec_pages = (n_spec_pages + 2) // 3  # 3 products per page
                for j in range(n_spec_pages):
                    if spec_page_idx + j < len(rl_reader.pages):
                        writer.add_page(rl_reader.pages[spec_page_idx + j])
                spec_page_idx += n_spec_pages

            with open(str(output_path), 'wb') as fout:
                writer.write(fout)

    else:
        # ── Original ReportLab path (row layout) ────────────────────────────
        c = canvas.Canvas(str(output_path), pagesize=PAGE)
        c.setTitle(f'Material Specification — {project_name}')
        c.setAuthor(studio)
        c.setSubject('Interior Design Material Specification')

        draw_cover(c, project_name, studio, rooms,
                   logo_reader=logo_reader, footer_right=footer_right)

        for room in rooms:
            draw_moodboard(c, room, logo_reader=logo_reader, studio=studio,
                           layout=layout, palette=palette)
            draw_room_specs(c, room, logo_reader=logo_reader, studio=studio,
                            project_name=project_name, footer_right=footer_right)

        c.save()

    size = output_path.stat().st_size
    print(f'✅ PDF saved: {output_path}  ({size // 1024} KB)')
    return str(output_path)
```

- [ ] **Step 5: Thread `template` through the CLI `__main__` block**

Find the two `build_pdf` / `auto_build_from_directory` calls at the bottom of the `__main__` block (around lines 911–919) and add `template=args.template` to each:

```python
        build_pdf(rooms, args.output, project_name=args.project_name,
                  studio=args.studio, logo_path=args.logo,
                  footer_right=args.footer_right, layout=args.layout,
                  palette=palette, template=args.template)
```

```python
        auto_build_from_directory(
            args.project_dir, args.output,
            project_name=args.project_name, studio=args.studio,
            logo_path=args.logo, footer_right=args.footer_right,
            layout=args.layout, palette=palette, template=args.template,
        )
```

- [ ] **Step 6: Smoke-test the CLI with a minimal fixture**

Create a temporary test project and run the full pipeline:

```bash
mkdir -p /tmp/test_proj/living_room
cat > /tmp/test_proj/living_room/sofa.md << 'EOF'
---
title: Porto Sectional
category: furniture
description: A deep-seated sectional in performance linen.
---
EOF

cat > /tmp/test_proj/living_room/vase.md << 'EOF'
---
title: Ceramic Vase
category: accessory
description: Thrown stoneware vase in warm white glaze.
---
EOF

python3 plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard.py \
  --project-dir /tmp/test_proj \
  --output /tmp/test_output.pdf \
  --project-name "Test Project" \
  --studio "Steven Castroverde" \
  --layout grid \
  --palette "#3D3530,#EAE5DC,#C07C60"
```

Expected: `✅ PDF saved: /tmp/test_output.pdf  (NNN KB)`

Open `/tmp/test_output.pdf` and verify: cover page → moodboard grid page (sofa in large hero cell, vase in small cell) → spec page.

- [ ] **Step 7: Commit**

```bash
git add plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard.py
git commit -m "feat: wire HTML grid renderer into build_pdf — merge via pypdf, add --template flag"
```

---

## Task 9: Full test suite pass and cleanup

**Files:**
- Modify: `plugins/interior-design/skills/moodboard-pdf/scripts/tests/test_build_moodboard_html.py`

- [ ] **Step 1: Run the full test suite**

```bash
cd plugins/interior-design/skills/moodboard-pdf/scripts
python3 -m pytest tests/test_build_moodboard_html.py -v
```

Expected: All tests PASSED, 0 failures.

- [ ] **Step 2: Confirm row layout is untouched**

```bash
mkdir -p /tmp/test_row/living_room
cat > /tmp/test_row/living_room/rug.md << 'EOF'
---
title: Moroccan Rug
category: textile
---
EOF

python3 plugins/interior-design/skills/moodboard-pdf/scripts/build_moodboard.py \
  --project-dir /tmp/test_row \
  --output /tmp/test_row_output.pdf \
  --project-name "Row Test" \
  --studio "Steven Castroverde" \
  --layout row
```

Expected: `✅ PDF saved` — open and confirm single-row moodboard with no errors.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: moodboard HTML/CSS grid complete — WeasyPrint renderer with category-aware layout"
```

---

## Self-Review Checklist

- **Category detection** — Task 2 ✓
- **Template definitions (3 templates)** — Task 3 ✓
- **Auto-selection logic** — Task 3 ✓
- **`--template` override flag** — Task 8 ✓
- **Furniture → hero cells, accessories → small cells** — Task 4 ✓
- **`object-fit: contain` with linen bg** — Task 6 (`render_moodboard_html`) ✓
- **Base64 image embedding** — Task 5 ✓
- **Palette strip as colored rectangles** — Task 6 ✓
- **`@page` 17in × 11in landscape** — Task 6 ✓
- **Dark accent cell renders solid `#1C1E18`** — Task 6 ✓
- **WeasyPrint missing → clear error message** — Task 7 ✓
- **pypdf missing → clear error message** — Task 8 ✓
- **Row layout untouched** — Task 8 (else branch preserved) ✓
- **Cover page preserved** — Task 8 (drawn to rl_pages.pdf, merged as page 0) ✓
- **Spec pages preserved** — Task 8 (drawn to rl_pages.pdf, interleaved after each moodboard) ✓
- **10+ products (collage repeated)** — handled: `select_template` returns `collage` for 7+; `render_room_to_pdf` is called once per room regardless of count; for >9 products the extra products are dropped from the moodboard (accepted tradeoff — future enhancement) ✓
