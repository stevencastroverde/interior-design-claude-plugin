#!/usr/bin/env python3
"""
build_moodboard.py — Interior Design Mood Board & Material Specification PDF Generator

Style v2 (2026):
  - Warm linen background (#EAE5DC)
  - Mood boards: serif-italic heading, single-row ('row') or uniform-grid ('grid') images
  - Optional color palette swatch row above images
  - Spec pages: full-width dark header bar, 3-up card layout on 17×11 tabloid
  - Spec fields: MATERIAL, FINISH, SIZE/DIMS, PRICE, APPLICATION, SUSTAINABILITY, SPECS, SOURCE/SKU

Usage:
  python3 build_moodboard.py \
    --project-dir "/path/to/project" \
    --output "board.pdf" \
    --project-name "Smith Residence" \
    --studio "Steven Castroverde" \
    [--layout grid] \
    [--palette "#3D5A40,#EAE5DC,#1C1E18"] \
    [--logo "/path/to/logo.png"]
"""

import argparse
import datetime
import json
import math
import os
import re
import sys
from io import BytesIO
from pathlib import Path

try:
    import requests
    from PIL import Image as PILImage
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import landscape, TABLOID
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install reportlab Pillow requests --break-system-packages")
    sys.exit(1)

try:
    from pypdf import PdfWriter, PdfReader
    _pypdf_available = True
except ImportError:
    _pypdf_available = False

# ─────────────────────────────────────────────────────────────────────────────
# PAGE & LAYOUT CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
PAGE = landscape(TABLOID)  # 1224 × 792 pts  (17 × 11 inches)
W, H = PAGE
M    = 0.45 * inch         # page margin
GAP  = 0.08 * inch         # gap between mood board image cells

SPEC_HEADER_H = 0.42 * inch   # dark header bar height
SPEC_FOOTER_H = 0.22 * inch   # footer strip height
IMG_FRAC      = 0.57          # fraction of spec card height used for image
PALETTE_H     = 0.75 * inch   # height of palette swatch row

PRODUCTS_PER_SPEC_PAGE = 3

# Auto-detected year — no --project flag needed
YEAR = str(datetime.date.today().year)

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN TOKENS — edit to restyle
# ─────────────────────────────────────────────────────────────────────────────
C_BG      = colors.HexColor('#EAE5DC')   # warm linen background
C_DARK    = colors.HexColor('#1C1E18')   # near-black (header bar, cover panel)
C_LABEL   = colors.HexColor('#4A5C38')   # olive green spec field labels
C_CAPTION = colors.HexColor('#7A7065')   # muted captions / secondary text
C_TEXT    = colors.HexColor('#1A1A18')   # main body text
C_RULE    = colors.HexColor('#C8BFB2')   # warm gray dividers
C_WHITE   = colors.white
C_ACCENT  = colors.HexColor('#3D5A40')   # forest green (cover accents)
C_MUTED   = colors.HexColor('#9A9080')   # subdued subtitle text

F_SERIF_B = 'Times-Bold'
F_SERIF_I = 'Times-Italic'
F_SERIF   = 'Times-Roman'
F_SANS_B  = 'Helvetica-Bold'
F_SANS    = 'Helvetica'

# ─────────────────────────────────────────────────────────────────────────────
# SPEC FIELD VISIBILITY
# ─────────────────────────────────────────────────────────────────────────────
ALL_SPEC_FIELDS = {
    'subtitle', 'mfr', 'material', 'finish', 'dims', 'price',
    'desc', 'application', 'sustain', 'specs', 'sku',
}
SPEC_FIELDS = set(ALL_SPEC_FIELDS)

# Ordered list of (key, display_label) for spec cards
SPEC_FIELDS_ORDER = [
    ('material',    'MATERIAL'),
    ('finish',      'FINISH'),
    ('dims',        'SIZE / DIMS'),
    ('price',       'PRICE'),
    ('application', 'APPLICATION'),
    ('sustain',     'SUSTAINABILITY'),
    ('specs',       'SPECS'),
    ('sku',         'SOURCE / SKU'),
]


def set_spec_fields(fields_str):
    global SPEC_FIELDS
    SPEC_FIELDS = {f.strip().lower() for f in fields_str.split(',') if f.strip()}


def apply_theme(bg=None, accent=None, text=None, dark=None, rule=None, caption=None):
    global C_BG, C_ACCENT, C_TEXT, C_DARK, C_RULE, C_CAPTION
    if bg:      C_BG      = colors.HexColor(bg)
    if accent:  C_ACCENT  = colors.HexColor(accent)
    if text:    C_TEXT    = colors.HexColor(text)
    if dark:    C_DARK    = colors.HexColor(dark)
    if rule:    C_RULE    = colors.HexColor(rule)
    if caption: C_CAPTION = colors.HexColor(caption)


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
def load_pil(path):
    if not path or not os.path.exists(path):
        return None
    try:
        return PILImage.open(path).convert('RGBA')
    except Exception:
        return None


def pil_to_reader(pil_img, bg_rgb=(255, 255, 255)):
    """Convert PIL image to ReportLab ImageReader, compositing RGBA onto bg_rgb."""
    if pil_img is None:
        return None
    try:
        if pil_img.mode == 'RGBA':
            bg = PILImage.new('RGB', pil_img.size, bg_rgb)
            bg.paste(pil_img, mask=pil_img.split()[3])
            pil_img = bg
        else:
            pil_img = pil_img.convert('RGB')
        buf = BytesIO()
        pil_img.save(buf, 'JPEG', quality=92)
        buf.seek(0)
        return ImageReader(buf)
    except Exception:
        return None


def place_image_fit(c, pil_img, cell_x, cell_y, cell_w, cell_h, bg_rgb=(234, 229, 220)):
    """
    Draw pil_img scale-to-fit inside the cell, centered.
    Fills cell background with bg_rgb first. Returns True if image drawn.
    """
    c.setFillColor(colors.Color(bg_rgb[0] / 255, bg_rgb[1] / 255, bg_rgb[2] / 255))
    c.rect(cell_x, cell_y, cell_w, cell_h, fill=1, stroke=0)

    if pil_img is None:
        c.setFont(F_SANS, 7)
        c.setFillColor(C_CAPTION)
        c.drawCentredString(cell_x + cell_w / 2, cell_y + cell_h / 2 - 3.5, 'Image Unavailable')
        return False

    img_ar  = pil_img.width / pil_img.height
    cell_ar = cell_w / cell_h

    if img_ar > cell_ar:
        draw_w = cell_w
        draw_h = cell_w / img_ar
    else:
        draw_h = cell_h
        draw_w = cell_h * img_ar

    draw_x = cell_x + (cell_w - draw_w) / 2
    draw_y = cell_y + (cell_h - draw_h) / 2

    reader = pil_to_reader(pil_img, bg_rgb=bg_rgb)
    if reader is None:
        return False
    c.drawImage(reader, draw_x, draw_y, draw_w, draw_h, preserveAspectRatio=False)
    return True


def draw_text_wrapped(c, text, x, y, max_w, font, size, color, leading=None):
    """Word-wrap and draw text. Returns y after the last line drawn."""
    if not text:
        return y
    if leading is None:
        leading = size * 1.40
    c.setFont(font, size)
    c.setFillColor(color)
    words = str(text).split()
    lines, current = [], []
    for w in words:
        test = ' '.join(current + [w])
        if c.stringWidth(test, font, size) <= max_w:
            current.append(w)
        else:
            if current:
                lines.append(' '.join(current))
            current = [w]
    if current:
        lines.append(' '.join(current))
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


# ─────────────────────────────────────────────────────────────────────────────
# PALETTE SWATCH ROW
# ─────────────────────────────────────────────────────────────────────────────
def draw_palette(c, palette_colors, avail_w, palette_y):
    """Draw a horizontal row of filled color circles centered vertically in PALETTE_H."""
    n = len(palette_colors)
    if n == 0:
        return
    spacing = avail_w / n
    r = 0.275 * inch
    for i, hex_color in enumerate(palette_colors):
        cx = M + spacing * i + spacing / 2
        cy = palette_y + PALETTE_H / 2
        hex_str = hex_color.strip()
        if not hex_str.startswith('#'):
            hex_str = f'#{hex_str}'
        c.setFillColor(colors.HexColor(hex_str))
        c.circle(cx, cy, r, fill=1, stroke=0)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED PAGE CHROME
# ─────────────────────────────────────────────────────────────────────────────
def draw_bg(c):
    c.setFillColor(C_BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)


def draw_spec_header(c, room_name, project_name):
    """Full-width dark header bar — project info left, studio/year right."""
    c.setFillColor(C_DARK)
    c.rect(0, H - SPEC_HEADER_H, W, SPEC_HEADER_H, fill=1, stroke=0)

    bar_cy = H - SPEC_HEADER_H / 2

    proj  = (project_name or 'PROJECT').upper()
    title = f'{proj} \u2014 MATERIAL SPECIFICATION'
    c.setFont(F_SANS_B, 9)
    c.setFillColor(C_WHITE)
    c.drawString(M, bar_cy + 2, title)

    c.setFont(F_SANS, 7)
    c.setFillColor(colors.HexColor('#AAAAAA'))
    c.drawString(M, bar_cy - 9, (room_name or '').upper())

    right_label = YEAR
    c.setFont(F_SANS, 6.5)
    c.setFillColor(colors.HexColor('#CCCCCC'))
    rw = c.stringWidth(right_label, F_SANS, 6.5)
    c.drawString(W - M - rw, bar_cy - 3, right_label)


def draw_spec_footer(c, studio):
    """Simple footer: 'Author · Year' left, 'Product Specification' right."""
    fy = M * 0.50

    c.setStrokeColor(C_RULE)
    c.setLineWidth(0.3)
    c.line(M, fy + 10, W - M, fy + 10)

    author    = (studio or 'Steven').split('\u00b7')[0].strip()
    left_text = f'{author} \u00b7 {YEAR}'

    c.setFont(F_SANS, 6)
    c.setFillColor(C_CAPTION)
    c.drawString(M, fy, left_text)

    right_text = 'Product Specification'
    rw = c.stringWidth(right_text, F_SANS, 6)
    c.drawString(W - M - rw, fy, right_text)


# ─────────────────────────────────────────────────────────────────────────────
# COVER PAGE
# ─────────────────────────────────────────────────────────────────────────────
def draw_cover(c, project_name, studio, rooms, logo_reader=None,
               footer_right='MATERIAL SPECIFICATION'):
    draw_bg(c)
    PANEL_W = 3.1 * inch

    c.setFillColor(C_DARK)
    c.rect(0, 0, PANEL_W, H, fill=1, stroke=0)

    c.setFillColor(C_ACCENT)
    c.rect(PANEL_W, 0, 0.04 * inch, H, fill=1, stroke=0)

    if logo_reader:
        LOGO_SZ = 0.55 * inch
        c.drawImage(logo_reader, M, H - M - LOGO_SZ, LOGO_SZ, LOGO_SZ,
                    preserveAspectRatio=True, mask='auto')
    else:
        c.setFillColor(C_ACCENT)
        c.roundRect(M, H - M - 0.48 * inch, 0.48 * inch, 0.48 * inch, 2, fill=1, stroke=0)
        c.setFont(F_SANS_B, 10)
        c.setFillColor(C_WHITE)
        c.drawCentredString(M + 0.24 * inch, H - M - 0.28 * inch, 'MB')

    mid_y = H / 2 + 0.5 * inch
    c.setFillColor(C_WHITE)
    c.setFont(F_SANS_B, 8)
    parts = (studio or '').split('\u2014') if '\u2014' in (studio or '') else \
            (studio or '').split('—') if '—' in (studio or '') else [studio or '']
    c.drawString(M, mid_y + 0.58 * inch, parts[0].strip())
    if len(parts) > 1:
        c.setFont(F_SANS_B, 9)
        c.drawString(M, mid_y + 0.36 * inch, parts[1].strip())

    c.setStrokeColor(C_ACCENT)
    c.setLineWidth(0.8)
    c.line(M, mid_y + 0.20 * inch, PANEL_W - M, mid_y + 0.20 * inch)

    c.setFont(F_SANS_B, 7)
    c.setFillColor(colors.HexColor('#A08858'))
    c.drawString(M, mid_y + 0.01 * inch, YEAR)

    c.setFont(F_SANS, 6)
    c.setFillColor(colors.HexColor('#88887A'))
    c.drawString(M, M + 0.50 * inch, footer_right.upper())
    c.drawString(M, M + 0.30 * inch, project_name or '')

    # Right panel
    rx = PANEL_W + 0.60 * inch
    rw = W - rx - M

    c.setFillColor(C_DARK)
    c.setFont(F_SERIF_B, 30)
    c.drawString(rx, H / 2 + 0.72 * inch, 'MATERIAL')
    c.setFont(F_SERIF_I, 30)
    c.setFillColor(colors.HexColor('#5C6B4A'))
    c.drawString(rx, H / 2 + 0.30 * inch, 'specifications')

    c.setStrokeColor(C_RULE)
    c.setLineWidth(0.4)
    c.line(rx, H / 2 + 0.12 * inch, rx + rw, H / 2 + 0.12 * inch)

    ry = H / 2 - 0.06 * inch
    c.setFont(F_SANS, 7.5)
    c.setFillColor(C_CAPTION)
    for room in rooms:
        label = room['name'] + '  \u2014  ' + room.get('subtitle', '')
        c.drawString(rx, ry, label)
        ry -= 0.22 * inch

    c.showPage()


# ─────────────────────────────────────────────────────────────────────────────
# MOOD BOARD PAGE — row or grid layout with optional palette
# ─────────────────────────────────────────────────────────────────────────────
def draw_moodboard(c, room, logo_reader=None, studio='', layout='row', palette=None):
    """
    Mood board page. layout='row': single horizontal row of portrait images.
    layout='grid': uniform grid (2 or 3 cols) auto-sized to image count.
    palette: list of hex strings drawn as circles above the image area.
    """
    draw_bg(c)

    products = room['products']
    n = len(products)

    # Two-line room label top-left
    room_type = (room.get('subtitle', '') or room['name']).lower()
    LABEL_TOP  = H - M
    LABEL_USED = 0.82 * inch

    c.setFont(F_SANS, 7.5)
    c.setFillColor(C_CAPTION)
    c.drawString(M, LABEL_TOP - 13, room_type)

    heading_text = 'inspiration' if layout == 'grid' else 'materials'
    c.setFont(F_SERIF_I, 28)
    c.setFillColor(C_TEXT)
    c.drawString(M, LABEL_TOP - 42, heading_text)

    if n == 0:
        c.showPage()
        return

    CAP_H   = 0.17 * inch
    avail_w = W - 2 * M

    # Palette row — sits immediately below heading
    pal_h = 0
    if palette:
        pal_h   = PALETTE_H
        pal_y   = H - M - LABEL_USED - pal_h
        draw_palette(c, palette, avail_w, pal_y)

    avail_h = H - M - LABEL_USED - pal_h - M

    if layout == 'grid':
        cols = 2 if n <= 3 else 3
        rows = math.ceil(n / cols)
        cell_w = (avail_w - GAP * (cols - 1)) / cols
        cell_h = (avail_h - CAP_H * rows - GAP * (rows - 1)) / rows

        for i, prod in enumerate(products):
            row_i = i // cols
            col_i = i % cols
            # rb = distance from the bottom row (0 = bottom row)
            rb    = rows - 1 - row_i
            y_cap = M + rb * (cell_h + CAP_H + GAP)
            y_img = y_cap + CAP_H
            cx    = M + col_i * (cell_w + GAP)

            pil_img = load_pil(prod.get('img'))
            place_image_fit(c, pil_img, cx, y_img, cell_w, cell_h)

            cap = prod.get('title', '').upper()
            if len(cap) > 30:
                cap = cap[:28] + '\u2026'
            c.setFont(F_SANS, 5.5)
            c.setFillColor(C_CAPTION)
            c.drawCentredString(cx + cell_w / 2, y_cap + CAP_H * 0.38, cap)

    else:
        # Single-row layout
        img_h  = avail_h - CAP_H
        cell_w = (avail_w - GAP * (n - 1)) / max(n, 1)
        row_y  = M + CAP_H

        for i, prod in enumerate(products):
            cx = M + i * (cell_w + GAP)

            pil_img = load_pil(prod.get('img'))
            place_image_fit(c, pil_img, cx, row_y, cell_w, img_h)

            cap = prod.get('title', '').upper()
            if len(cap) > 30:
                cap = cap[:28] + '\u2026'
            c.setFont(F_SANS, 5.5)
            c.setFillColor(C_CAPTION)
            c.drawCentredString(cx + cell_w / 2, row_y - CAP_H * 0.55, cap)

    c.showPage()


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT SPEC CARD
# ─────────────────────────────────────────────────────────────────────────────
def draw_spec_card(c, prod, card_x, card_y, card_w, card_h):
    """
    Draw one product card at lower-left (card_x, card_y) with size (card_w x card_h).
    Large image fills the top IMG_FRAC of the card; text block below.
    """
    # Image
    img_h   = card_h * IMG_FRAC
    img_y   = card_y + card_h - img_h
    pil_img = load_pil(prod.get('img'))
    place_image_fit(c, pil_img, card_x, img_y, card_w, img_h, bg_rgb=(255, 255, 255))

    # Text block
    PAD = 0.06 * inch
    tx  = card_x + PAD
    tw  = card_w - 2 * PAD
    ty  = img_y - 0.14 * inch

    # Product name (Times-Bold)
    title = prod.get('title', '')
    c.setFont(F_SERIF_B, 12)
    c.setFillColor(C_TEXT)
    while title and c.stringWidth(title, F_SERIF_B, 12) > tw:
        title = title[:-1]
    c.drawString(tx, ty, title)
    ty -= 0.175 * inch

    # Subtitle: mfr · collection (sans muted)
    sub_parts = []
    if prod.get('mfr') and 'mfr' in SPEC_FIELDS:
        sub_parts.append(prod['mfr'])
    if prod.get('subtitle') and 'subtitle' in SPEC_FIELDS:
        sub_parts.append(prod['subtitle'])
    if sub_parts:
        sub_str = ' \u00b7 '.join(sub_parts)
        c.setFont(F_SANS, 7.5)
        c.setFillColor(C_MUTED)
        while sub_str and c.stringWidth(sub_str, F_SANS, 7.5) > tw:
            sub_str = sub_str[:-1]
        c.drawString(tx, ty, sub_str)
        ty -= 0.16 * inch

    # Description paragraph
    if prod.get('desc') and 'desc' in SPEC_FIELDS:
        ty -= 0.02 * inch
        ty = draw_text_wrapped(c, prod['desc'], tx, ty, tw, F_SANS, 7, C_TEXT, leading=10)
        ty -= 0.07 * inch

    # Thin rule divider before spec rows
    c.setStrokeColor(C_RULE)
    c.setLineWidth(0.25)
    c.line(tx, ty + 3, tx + tw, ty + 3)
    ty -= 0.09 * inch

    # Spec field rows — inline "LABEL  value"
    for field_key, field_label in SPEC_FIELDS_ORDER:
        if field_key not in SPEC_FIELDS:
            continue
        value = prod.get(field_key)
        if not value or str(value).strip() in ('TBD', 'N/A', ''):
            continue
        if ty < card_y + 0.04 * inch:
            break

        label_w = c.stringWidth(field_label, F_SANS_B, 6) + 5
        val_x   = tx + label_w
        val_w   = tw - label_w

        c.setFont(F_SANS_B, 6)
        c.setFillColor(C_LABEL)
        c.drawString(tx, ty, field_label)

        c.setFont(F_SANS, 6)
        c.setFillColor(C_TEXT)
        val_str = str(value)
        if c.stringWidth(val_str, F_SANS, 6) <= val_w:
            c.drawString(val_x, ty, val_str)
            ty -= 0.115 * inch
        else:
            ty = draw_text_wrapped(c, val_str, val_x, ty, val_w, F_SANS, 6, C_TEXT, leading=8.5)
            ty -= 0.03 * inch


# ─────────────────────────────────────────────────────────────────────────────
# SPEC PAGE — 3-column layout
# ─────────────────────────────────────────────────────────────────────────────
def draw_spec_page(c, room, page_products, page_num, total_pages,
                   logo_reader=None, studio='', project_name='',
                   footer_right='MATERIAL SPECIFICATION'):
    draw_bg(c)
    draw_spec_header(c, room.get('name', ''), project_name)
    draw_spec_footer(c, studio)

    content_top = H - SPEC_HEADER_H
    content_bot = SPEC_FOOTER_H + 0.14 * inch
    content_h   = content_top - content_bot

    CARD_GAP = 0.12 * inch
    avail_w  = W - 2 * M
    card_w   = (avail_w - 2 * CARD_GAP) / 3

    card_x = [
        M,
        M + card_w + CARD_GAP,
        M + 2 * (card_w + CARD_GAP),
    ]
    div_x = [
        M + card_w + CARD_GAP / 2,
        M + 2 * card_w + 1.5 * CARD_GAP,
    ]

    for i, prod in enumerate(page_products):
        draw_spec_card(c, prod, card_x[i], content_bot, card_w, content_h)

    # Divider lines between occupied slots
    c.setStrokeColor(C_RULE)
    c.setLineWidth(0.3)
    if len(page_products) >= 2:
        c.line(div_x[0], content_bot + 4, div_x[0], content_top - 4)
    if len(page_products) >= 3:
        c.line(div_x[1], content_bot + 4, div_x[1], content_top - 4)

    c.showPage()


def draw_room_specs(c, room, logo_reader=None, studio='',
                    project_name='', footer_right='MATERIAL SPECIFICATION'):
    products = room['products']
    pages = [products[i:i + PRODUCTS_PER_SPEC_PAGE]
             for i in range(0, len(products), PRODUCTS_PER_SPEC_PAGE)]
    for pnum, batch in enumerate(pages, 1):
        draw_spec_page(c, room, batch, pnum, len(pages),
                       logo_reader=logo_reader, studio=studio,
                       project_name=project_name, footer_right=footer_right)


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE DOWNLOAD HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def slugify(text):
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')[:40]


def download_image(url, dest_path):
    """Try multiple User-Agent strategies to download an image."""
    if not url or not url.startswith('http'):
        return False
    agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0',
        'curl/7.68.0',
        '',
    ]
    for agent in agents:
        try:
            headers = {'User-Agent': agent} if agent else {}
            r = requests.get(url, headers=headers, timeout=20, stream=True)
            if r.status_code == 200 and int(r.headers.get('content-length', '10000')) > 2000:
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                if os.path.getsize(dest_path) > 3000:
                    return True
        except Exception:
            continue
    return False


# ─────────────────────────────────────────────────────────────────────────────
# MARKDOWN PARSER
# ─────────────────────────────────────────────────────────────────────────────
def _extract_field(text, patterns):
    """Try each regex pattern; return first match group(1), stripped."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip().rstrip('.')
    return None


def parse_markdown_file(md_path, room_slug, cache_dir):
    """
    Parse a product markdown clipping. Returns a product dict with all spec fields.
    Handles Obsidian frontmatter + inline spec rows (FIELD  value format).
    """
    text = Path(md_path).read_text(encoding='utf-8', errors='replace')

    # YAML frontmatter
    fm = {}
    fm_match = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            if ':' in line:
                k, _, v = line.partition(':')
                fm[k.strip()] = v.strip().strip('"').strip("'")

    title  = fm.get('title', Path(md_path).stem)
    source = fm.get('source', '')
    desc   = fm.get('description', '')

    # Image extraction
    img_local = None

    local_match = re.search(r'!\[\[([^\]]+\.(jpg|jpeg|png|webp|gif))\]\]', text, re.IGNORECASE)
    if local_match:
        local_file = Path(md_path).parent / local_match.group(1)
        if local_file.exists():
            img_local = str(local_file)

    img_url = None
    if not img_local:
        url_match = re.search(r'!\[.*?\]\((https?://[^)]+\.(jpg|jpeg|png|webp))[^)]*\)', text, re.IGNORECASE)
        if not url_match:
            url_match = re.search(r'!\[.*?\]\((https?://[^\s)>"]{20,})\)', text)
        if url_match:
            img_url = url_match.group(1)

    if not img_local and img_url:
        prod_slug  = slugify(title)
        cache_path = cache_dir / f'{room_slug}_{prod_slug}.jpg'
        if cache_path.exists() and cache_path.stat().st_size > 3000:
            img_local = str(cache_path)
        else:
            if download_image(img_url, str(cache_path)):
                img_local = str(cache_path)

    def field(patterns_list):
        return _extract_field(text, patterns_list)

    material = field([
        r'\bMATERIAL\b[\s:·]+([^\n|]{3,120})',
        r'\*\*[Mm]aterial\**[:\s]+([^\n]+)',
    ])
    finish = field([
        r'\bFINISH\b[\s:·]+([^\n|]{3,80})',
        r'\*\*[Ff]inish\**[:\s]+([^\n]+)',
    ])
    application = field([
        r'\bAPPLICATION\b[\s:·]+([^\n|]{3,250})',
        r'\*\*[Aa]pplication\**[:\s]+([^\n]+)',
    ])
    specs = field([
        r'\bSPECS\b[\s:·]+([^\n|]{3,250})',
        r'\*\*[Ss]pecs\**[:\s]+([^\n]+)',
    ])
    sku = field([
        r'\bSOURCE\s*/\s*SKU\b[\s:·]+([^\n|]{2,80})',
        r'\bSKU\b[\s:·]+([^\n|]{2,60})',
        r'\*\*[Ss][Kk][Uu]\**[:\s]+([^\n]+)',
    ])

    # Dimensions
    dim_match = re.search(
        r'(?:SIZE\s*/?\s*DIMS?|DIMS?|overall\s+dimensions?|dimensions?|size)[:\s·]+([^\n|]{5,80})',
        text, re.IGNORECASE
    )
    dims = dim_match.group(1).strip().rstrip('.') if dim_match else 'TBD'

    # Price
    price_match = re.search(r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:per\s+\w+)?\s*\w{0,8})?', text)
    price = price_match.group(0).strip() if price_match else None

    # Manufacturer
    mfr = fm.get('author', '')
    if isinstance(mfr, str):
        mfr = mfr.strip().strip('[]').replace('[[', '').replace(']]', '')
    if not mfr:
        mfr_match = re.search(
            r'\*\*(?:brand|manufacturer|by|designed by)[:\s]*\*\*\s*(.+)', text, re.IGNORECASE
        )
        if mfr_match:
            mfr = mfr_match.group(1).strip()

    # Sustainability
    sustain_keywords = [
        r'FSC[®\s-]*certified', r'GoodWeave', r'GREENGUARD', r'CARB', r'CertiPUR',
        r'ETL\s+[Ll]isted', r'LEED', r'recycled material', r'zero[- ]VOC',
        r'B\s+Corporation', r'ISO\s+14001', r'Made in USA', r'responsibly managed',
        r'100%\s+recycled', r'hand[- ]crafted', r'organic', r'sustainable', r'low[- ]emission',
        r'FloorScore', r'declare\s+certified', r'Red\s+List\s+Free', r'Zero\s+Collection',
        r'buy\s+american\s+act', r'USGBC', r'BioPreferred', r'NSF\s+\d+',
    ]
    sustain_sentences = []
    for kw in sustain_keywords:
        for m in re.finditer(rf'[^.!?\n]*{kw}[^.!?\n]*[.!?]?', text, re.IGNORECASE):
            s = m.group(0).strip()
            if 10 < len(s) < 200 and s not in sustain_sentences:
                sustain_sentences.append(s)
    sustain = ' '.join(sustain_sentences[:3]).strip() or None

    return {
        'title':       title,
        'subtitle':    fm.get('subtitle', None),
        'mfr':         mfr or None,
        'material':    material,
        'finish':      finish,
        'price':       price,
        'dims':        dims,
        'desc':        desc[:300] if desc else None,
        'application': application,
        'sustain':     sustain,
        'specs':       specs,
        'sku':         sku,
        'img':         img_local,
        'source':      source,
    }


def parse_room_folder(room_path, cache_dir):
    """Parse all markdown files in a room folder."""
    room_path = Path(room_path)
    room_slug = slugify(room_path.name)
    products  = []
    for md_file in sorted(room_path.glob('*.md')):
        prod = parse_markdown_file(md_file, room_slug, cache_dir)
        if prod:
            products.append(prod)
    return products


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUILD FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
def build_pdf(rooms, output_path, project_name='', studio='',
              logo_path=None, footer_right='MATERIAL SPECIFICATION',
              layout='row', palette=None, template=None):
    """
    Build the moodboard + spec PDF.

    rooms: list of dicts with 'name', 'subtitle', and 'products' keys.
    layout: 'row' (single-row portrait) or 'grid' (uniform grid).
    palette: list of hex strings for color swatches, or None.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logo_reader = None
    if logo_path and os.path.exists(logo_path):
        try:
            pil = PILImage.open(logo_path).convert('RGBA')
            buf = BytesIO()
            pil.save(buf, 'PNG')
            buf.seek(0)
            logo_reader = ImageReader(buf)
        except Exception:
            logo_reader = None

    if layout == 'grid':
        # \u2500\u2500 HTML/CSS Grid path \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        if not _pypdf_available:
            raise RuntimeError(
                'pypdf is required for grid layout. Run:\n'
                '  pip install pypdf --break-system-packages'
            )
        import sys as _sys
        import tempfile as _tempfile
        _scripts_dir = str(Path(__file__).parent)
        if _scripts_dir not in _sys.path:
            _sys.path.insert(0, _scripts_dir)
        from build_moodboard_html import render_room_to_pdf

        with _tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            # Cover + spec pages via ReportLab
            rl_path = tmp / 'rl_pages.pdf'
            c = canvas.Canvas(str(rl_path), pagesize=PAGE)
            c.setTitle(f'Material Specification \u2014 {project_name}')
            c.setAuthor(studio)
            c.setSubject('Interior Design Material Specification')
            draw_cover(c, project_name, studio, rooms,
                       logo_reader=logo_reader, footer_right=footer_right)
            for room in rooms:
                draw_room_specs(c, room, logo_reader=logo_reader, studio=studio,
                                project_name=project_name, footer_right=footer_right)
            c.save()

            # Moodboard pages via WeasyPrint \u2014 one PDF per room
            moodboard_paths = []
            for room in rooms:
                mp = tmp / f'moodboard_{room["name"]}.pdf'
                render_room_to_pdf(room, str(mp), template_name=template,
                                   palette=palette)
                moodboard_paths.append((room, str(mp)))

            # Merge: cover | (moodboard + spec pages per room) \u2192 final PDF
            writer = PdfWriter()
            rl_reader = PdfReader(str(rl_path))

            # Page 0 = cover
            writer.add_page(rl_reader.pages[0])

            spec_page_idx = 1  # pages after cover in rl_pages.pdf
            for room, mb_path in moodboard_paths:
                # Moodboard page(s)
                mb_reader = PdfReader(mb_path)
                for pg in mb_reader.pages:
                    writer.add_page(pg)
                # Spec pages for this room (3 products per spec page)
                n_spec_pages = math.ceil(len(room['products']) / PRODUCTS_PER_SPEC_PAGE)
                for j in range(n_spec_pages):
                    if spec_page_idx + j < len(rl_reader.pages):
                        writer.add_page(rl_reader.pages[spec_page_idx + j])
                spec_page_idx += n_spec_pages

            with open(str(output_path), 'wb') as fout:
                writer.write(fout)

    else:
        # \u2500\u2500 Original ReportLab path (row layout) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        c = canvas.Canvas(str(output_path), pagesize=PAGE)
        c.setTitle(f'Material Specification \u2014 {project_name}')
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
    print(f'\u2705 PDF saved: {output_path}  ({size // 1024} KB)')
    return str(output_path)


def auto_build_from_directory(project_dir, output_path, project_name='', studio='',
                               logo_path=None, footer_right='MATERIAL SPECIFICATION',
                               layout='row', palette=None, template=None):
    """
    Auto-discover rooms from subfolders and build the PDF.
    Any subfolder containing .md files is treated as a room.
    """
    project_dir = Path(project_dir)
    cache_dir   = project_dir / '_image_cache'
    cache_dir.mkdir(exist_ok=True)

    room_dirs = sorted([
        d for d in project_dir.iterdir()
        if d.is_dir() and not d.name.startswith('.') and d.name != '_image_cache'
        and any(d.glob('*.md'))
    ])

    rooms = []
    for rd in room_dirs:
        products = parse_room_folder(rd, cache_dir)
        if products:
            rooms.append({
                'name':     rd.name.upper(),
                'subtitle': rd.name.lower(),
                'products': products,
            })
        print(f'  Room: {rd.name} \u2014 {len(products)} products')

    if not project_name:
        project_name = project_dir.name

    return build_pdf(rooms, output_path, project_name=project_name, studio=studio,
                     logo_path=logo_path, footer_right=footer_right,
                     layout=layout, palette=palette, template=template)


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate interior design material specification PDF'
    )
    parser.add_argument('--project-dir',  required=True,  help='Root folder with room subfolders')
    parser.add_argument('--output',       required=True,  help='Output PDF path')
    parser.add_argument('--project-name', default='',     help='Project name shown in spec page header')
    parser.add_argument('--studio',       default='',     help='Studio/author name for header and footer')
    parser.add_argument('--logo',         default=None,   help='Path to logo PNG/JPG (optional)')
    parser.add_argument('--footer-right', default='MATERIAL SPECIFICATION')
    parser.add_argument(
        '--layout', default='row', choices=['row', 'grid'],
        help='Mood board layout: row (single-row portrait, default) or grid (uniform grid)'
    )
    parser.add_argument(
        '--template', default=None,
        choices=['anchor-left', 'feature-top', 'collage'],
        help='Pin a specific grid template (default: auto-selected by product count)'
    )
    parser.add_argument(
        '--palette', default=None,
        help='Comma-separated hex color swatches above images (e.g. "#3D5A40,#EAE5DC,#1C1E18")'
    )
    parser.add_argument(
        '--spec-fields', default=None,
        help=(
            'Comma-separated list of spec fields to show. '
            'Available: subtitle, mfr, material, finish, dims, price, desc, '
            'application, sustain, specs, sku. Default: all.'
        )
    )
    parser.add_argument('--color-bg',      default=None, help='Background hex (default #EAE5DC)')
    parser.add_argument('--color-accent',  default=None, help='Accent hex (default #3D5A40)')
    parser.add_argument('--color-text',    default=None, help='Body text hex (default #1A1A18)')
    parser.add_argument('--color-dark',    default=None, help='Header bar hex (default #1C1E18)')
    parser.add_argument('--color-rule',    default=None, help='Divider hex (default #C8BFB2)')
    parser.add_argument('--color-caption', default=None, help='Caption text hex')
    parser.add_argument('--rooms-json',    default=None,
                        help='Path to rooms JSON file (overrides auto-discovery)')

    args = parser.parse_args()

    if args.spec_fields:
        set_spec_fields(args.spec_fields)

    apply_theme(
        bg=args.color_bg,
        accent=args.color_accent,
        text=args.color_text,
        dark=args.color_dark,
        rule=args.color_rule,
        caption=args.color_caption,
    )

    palette = None
    if args.palette:
        palette = [c.strip() for c in args.palette.split(',') if c.strip()]

    if args.rooms_json:
        with open(args.rooms_json) as f:
            rooms = json.load(f)
        build_pdf(rooms, args.output, project_name=args.project_name,
                  studio=args.studio, logo_path=args.logo,
                  footer_right=args.footer_right, layout=args.layout, palette=palette,
                  template=args.template)
    else:
        auto_build_from_directory(
            args.project_dir, args.output,
            project_name=args.project_name, studio=args.studio,
            logo_path=args.logo, footer_right=args.footer_right,
            layout=args.layout, palette=palette, template=args.template,
        )
