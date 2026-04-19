#!/usr/bin/env python3
"""
build_moodboard.py — Interior Design Mood Board & Product Specification PDF Generator

Usage:
  python3 build_moodboard.py \
    --project-dir "/path/to/Design Studio 2" \
    --output "/path/to/Mood Board.pdf" \
    --project-name "Spring 2026" \
    --studio "ARCH X482.2 — Design Studio II" \
    [--logo "/path/to/logo.png"]
    [--footer-right "RESIDENTIAL INTERIOR DESIGN"]

Or import and call build_pdf() directly from Python.
"""

import argparse
import json
import math
import os
import re
import sys
from io import BytesIO
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# DEPENDENCIES CHECK
# ─────────────────────────────────────────────────────────────────────────────
try:
    import requests
    from PIL import Image as PILImage
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install reportlab Pillow requests --break-system-packages")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE & LAYOUT CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
PAGE     = landscape(letter)      # 792 × 612 pts  (11 × 8.5 inches)
W, H     = PAGE
M        = 0.45 * inch            # page margin
HEADER_H = 0.72 * inch            # header band height (logo + room name)
FOOTER_H = 0.22 * inch            # footer strip height
GAP      = 0.09 * inch            # gap between image grid cells
CAP_H    = 0.20 * inch            # caption text strip (no background)

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN TOKENS  — edit these to restyle
# ─────────────────────────────────────────────────────────────────────────────
C_BG      = colors.HexColor('#F5F2EE')   # warm cream background
C_DARK    = colors.HexColor('#1C1E18')   # near-black (cover panel, text)
C_ACCENT  = colors.HexColor('#3D5A40')   # forest green
C_RULE    = colors.HexColor('#C5BAA8')   # warm gray rules
C_CAPTION = colors.HexColor('#6B6B60')   # caption / secondary text
C_TEXT    = colors.HexColor('#1A1A18')   # main body text
C_WHITE   = colors.white
C_COVER_R = colors.HexColor('#F5F2EE')   # right panel on cover

F_BOLD    = 'Helvetica-Bold'
F_REG     = 'Helvetica'
F_OBL     = 'Helvetica-Oblique'

PRODUCTS_PER_SPEC_PAGE = 3

# ─────────────────────────────────────────────────────────────────────────────
# SPEC FIELD VISIBILITY  — controls which fields appear on product spec pages
# ─────────────────────────────────────────────────────────────────────────────
ALL_SPEC_FIELDS = {'subtitle', 'mfr', 'price', 'dims', 'desc', 'sustain'}
SPEC_FIELDS = set(ALL_SPEC_FIELDS)  # show all by default


def set_spec_fields(fields_str):
    """Override which spec fields are shown. fields_str is comma-separated, e.g. 'mfr,dims,sustain'."""
    global SPEC_FIELDS
    SPEC_FIELDS = {f.strip().lower() for f in fields_str.split(',') if f.strip()}


def apply_theme(bg=None, accent=None, text=None, dark=None, rule=None, caption=None):
    """Override design token colors at runtime. Pass hex strings like '#3D5A40'."""
    global C_BG, C_ACCENT, C_TEXT, C_DARK, C_RULE, C_CAPTION, C_COVER_R
    if bg:
        C_BG = colors.HexColor(bg)
        C_COVER_R = colors.HexColor(bg)  # cover right panel matches background
    if accent:
        C_ACCENT = colors.HexColor(accent)
    if text:
        C_TEXT = colors.HexColor(text)
    if dark:
        C_DARK = colors.HexColor(dark)
    if rule:
        C_RULE = colors.HexColor(rule)
    if caption:
        C_CAPTION = colors.HexColor(caption)

# ─────────────────────────────────────────────────────────────────────────────
# IMAGE UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
def load_pil(path):
    """Load a PIL image from a file path. Returns None on failure."""
    if not path or not os.path.exists(path):
        return None
    try:
        im = PILImage.open(path)
        im = im.convert('RGBA')  # keep transparency for product shots
        return im
    except Exception:
        return None


def pil_to_reader(pil_img, force_white_bg=True):
    """
    Convert a PIL image to a ReportLab ImageReader.
    If force_white_bg=True, composite RGBA images onto white before encoding.
    Returns an ImageReader or None.
    """
    if pil_img is None:
        return None
    try:
        if pil_img.mode == 'RGBA' and force_white_bg:
            bg = PILImage.new('RGB', pil_img.size, (255, 255, 255))
            bg.paste(pil_img, mask=pil_img.split()[3])
            pil_img = bg
        else:
            pil_img = pil_img.convert('RGB')
        buf = BytesIO()
        pil_img.save(buf, 'JPEG', quality=90)
        buf.seek(0)
        return ImageReader(buf)
    except Exception:
        return None


def place_image_fit(c, pil_img, cell_x, cell_y, cell_w, cell_h, bg_fill=True):
    """
    Draw pil_img scaled to fit inside (cell_w × cell_h) at lower-left (cell_x, cell_y).
    Preserves aspect ratio — does NOT crop. Image is centered in the cell.
    If bg_fill, fills the cell with C_BG first.
    Returns True if image was drawn.
    """
    if bg_fill:
        c.setFillColor(C_BG)
        c.rect(cell_x, cell_y, cell_w, cell_h, fill=1, stroke=0)

    if pil_img is None:
        # Draw placeholder
        c.setFillColor(colors.HexColor('#E8E4DF'))
        c.rect(cell_x, cell_y, cell_w, cell_h, fill=1, stroke=0)
        c.setFont(F_OBL, 7)
        c.setFillColor(C_CAPTION)
        c.drawCentredString(cell_x + cell_w / 2, cell_y + cell_h / 2, 'Image Unavailable')
        return False

    img_ar = pil_img.width / pil_img.height
    cell_ar = cell_w / cell_h

    if img_ar > cell_ar:
        # Image wider → fit to width
        draw_w = cell_w
        draw_h = cell_w / img_ar
    else:
        # Image taller → fit to height
        draw_h = cell_h
        draw_w = cell_h * img_ar

    # Centre in cell
    draw_x = cell_x + (cell_w - draw_w) / 2
    draw_y = cell_y + (cell_h - draw_h) / 2

    reader = pil_to_reader(pil_img, force_white_bg=False)
    if reader is None:
        return False

    # For RGBA images (product shots on transparent/white bg), draw with mask
    if pil_img.mode == 'RGBA':
        # Composite onto cream background for the actual draw area
        bg = PILImage.new('RGB', pil_img.size, (245, 242, 238))  # C_BG as RGB
        bg.paste(pil_img, mask=pil_img.split()[3])
        reader2 = pil_to_reader(bg, force_white_bg=False)
        if reader2:
            c.drawImage(reader2, draw_x, draw_y, draw_w, draw_h, preserveAspectRatio=False)
    else:
        c.drawImage(reader, draw_x, draw_y, draw_w, draw_h, preserveAspectRatio=False)

    return True


def draw_text_wrapped(c, text, x, y, max_w, font, size, color, leading=None):
    """Wrap and draw text. Returns the y position after the last line."""
    if not text:
        return y
    if leading is None:
        leading = size * 1.40
    c.setFont(font, size)
    c.setFillColor(color)
    words = text.split()
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
# PAGE CHROME  — header / footer shared across all interior pages
# ─────────────────────────────────────────────────────────────────────────────
def draw_bg(c):
    c.setFillColor(C_BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)


def draw_page_header(c, room_name, subtitle, page_type, logo_reader=None,
                     page_num=None, total_pages=None,
                     studio='', semester='', footer_right='RESIDENTIAL INTERIOR DESIGN'):
    """Draw the consistent header and footer on every interior page."""
    LOGO_SZ = 0.50 * inch
    LOGO_X  = M
    LOGO_Y  = H - M - LOGO_SZ

    # ── Logo / badge ──
    if logo_reader:
        c.drawImage(logo_reader, LOGO_X, LOGO_Y, LOGO_SZ, LOGO_SZ, preserveAspectRatio=True, mask='auto')
    else:
        # Text badge: filled square with initials
        initials = ''.join(w[0] for w in room_name.split()[:2]) if room_name else 'MB'
        c.setFillColor(C_ACCENT)
        c.roundRect(LOGO_X, LOGO_Y, LOGO_SZ * 0.75, LOGO_SZ * 0.75, 2, fill=1, stroke=0)
        c.setFont(F_BOLD, 9)
        c.setFillColor(C_WHITE)
        c.drawCentredString(LOGO_X + LOGO_SZ * 0.375, LOGO_Y + LOGO_SZ * 0.22, initials)

    # ── Top horizontal rule ──
    rule_x = LOGO_X + LOGO_SZ + 0.10 * inch
    c.setStrokeColor(C_RULE)
    c.setLineWidth(0.5)
    c.line(rule_x, H - M, W - M, H - M)

    # ── Room name ──
    text_x = M
    name_y  = H - M - 0.28 * inch
    c.setFont(F_BOLD, 11)
    c.setFillColor(C_TEXT)
    c.drawString(text_x, name_y, room_name)

    # ── Subtitle ──
    if subtitle:
        c.setFont(F_REG, 7)
        c.setFillColor(C_CAPTION)
        c.drawString(text_x, name_y - 0.155 * inch, subtitle.upper())

    # ── Page type label top-right ──
    if page_type == 'spec':
        label = 'PRODUCT SPECIFICATIONS'
        if page_num and total_pages:
            label += f'   {page_num} / {total_pages}'
    else:
        label = 'MOOD BOARD'
    c.setFont(F_REG, 6.5)
    c.setFillColor(C_ACCENT)
    lw = c.stringWidth(label, F_REG, 6.5)
    c.drawString(W - M - lw, name_y, label)

    # ── Header bottom rule ──
    c.setStrokeColor(C_RULE)
    c.setLineWidth(0.35)
    c.line(M, H - M - HEADER_H, W - M, H - M - HEADER_H)

    # ── Footer ──
    fy = M - 0.01 * inch
    c.setStrokeColor(C_RULE)
    c.setLineWidth(0.25)
    c.line(M, M + 0.14 * inch, W - M, M + 0.14 * inch)

    footer_left = studio or 'DESIGN STUDIO'
    c.setFont(F_REG, 5.5)
    c.setFillColor(C_ACCENT)
    c.drawString(M, fy, footer_left)
    frw = c.stringWidth(footer_right, F_REG, 5.5)
    c.drawString(W - M - frw, fy, footer_right)


# ─────────────────────────────────────────────────────────────────────────────
# COVER PAGE
# ─────────────────────────────────────────────────────────────────────────────
def draw_cover(c, project_name, studio, semester, rooms, logo_reader=None, footer_right='RESIDENTIAL INTERIOR DESIGN'):
    draw_bg(c)
    PANEL_W = 3.1 * inch

    # Left dark panel
    c.setFillColor(C_DARK)
    c.rect(0, 0, PANEL_W, H, fill=1, stroke=0)

    # Thin accent stripe on right edge of dark panel
    c.setFillColor(C_ACCENT)
    c.rect(PANEL_W, 0, 0.04 * inch, H, fill=1, stroke=0)

    # Logo on left panel
    if logo_reader:
        LOGO_SZ = 0.55 * inch
        c.drawImage(logo_reader, M, H - M - LOGO_SZ, LOGO_SZ, LOGO_SZ,
                    preserveAspectRatio=True, mask='auto')
    else:
        # Badge
        c.setFillColor(C_ACCENT)
        c.roundRect(M, H - M - 0.52 * inch, 0.52 * inch, 0.52 * inch, 2, fill=1, stroke=0)
        c.setFont(F_BOLD, 11)
        c.setFillColor(C_WHITE)
        c.drawCentredString(M + 0.26 * inch, H - M - 0.30 * inch, 'MB')

    # Left panel text
    mid_y = H / 2 + 0.5 * inch
    c.setFillColor(C_WHITE)
    c.setFont(F_BOLD, 8)
    c.drawString(M, mid_y + 0.60 * inch, studio.split('—')[0].strip() if '—' in studio else studio)
    if '—' in studio:
        c.setFont(F_BOLD, 9)
        c.drawString(M, mid_y + 0.38 * inch, studio.split('—', 1)[1].strip())

    c.setStrokeColor(C_ACCENT)
    c.setLineWidth(0.8)
    c.line(M, mid_y + 0.22 * inch, PANEL_W - M, mid_y + 0.22 * inch)

    c.setFont(F_BOLD, 7)
    c.setFillColor(colors.HexColor('#A08858'))  # warm gold
    c.drawString(M, mid_y + 0.03 * inch, semester.upper() if semester else '')

    # Bottom-left caption
    c.setFont(F_REG, 6)
    c.setFillColor(colors.HexColor('#88887A'))
    c.drawString(M, M + 0.55 * inch, footer_right.upper())
    c.drawString(M, M + 0.35 * inch, project_name)

    # Right panel
    rx = PANEL_W + 0.60 * inch
    rw = W - rx - M

    # Big title
    c.setFillColor(C_DARK)
    c.setFont(F_BOLD, 34)
    c.drawString(rx, H / 2 + 0.75 * inch, 'MOOD BOARDS')

    c.setFont(F_BOLD, 12)
    c.setFillColor(C_ACCENT)
    c.drawString(rx, H / 2 + 0.35 * inch, '& PRODUCT SPECIFICATIONS')

    c.setStrokeColor(C_RULE)
    c.setLineWidth(0.45)
    c.line(rx, H / 2 + 0.13 * inch, rx + rw, H / 2 + 0.13 * inch)

    # Room index
    ry = H / 2 - 0.05 * inch
    c.setFont(F_REG, 7.5)
    c.setFillColor(C_CAPTION)
    for room in rooms:
        label = room['name'] + '  —  ' + room.get('subtitle', '')
        c.drawString(rx, ry, label)
        ry -= 0.215 * inch

    # Bottom rule + footer
    c.setStrokeColor(C_ACCENT)
    c.setLineWidth(0.5)
    c.line(rx, M + 0.22 * inch, rx + rw, M + 0.22 * inch)

    c.showPage()


# ─────────────────────────────────────────────────────────────────────────────
# MOOD BOARD PAGE
# ─────────────────────────────────────────────────────────────────────────────
def draw_moodboard(c, room, logo_reader=None, studio='', footer_right='RESIDENTIAL INTERIOR DESIGN'):
    draw_bg(c)
    draw_page_header(c, room['name'], room.get('subtitle', ''), 'moodboard',
                     logo_reader=logo_reader, studio=studio, footer_right=footer_right)

    products = room['products']
    n = len(products)
    if n == 0:
        c.showPage()
        return

    # Available image area (below header, above footer)
    ax = M
    ay = M + FOOTER_H
    aw = W - 2 * M
    ah = H - 2 * M - HEADER_H - FOOTER_H

    # Determine grid dimensions
    if n <= 2:
        n_cols, n_rows = n, 1
    elif n <= 4:
        n_cols, n_rows = 2, 2
    elif n <= 6:
        n_cols, n_rows = 3, 2
    elif n <= 9:
        n_cols, n_rows = 3, 3
    else:
        n_cols, n_rows = 4, math.ceil(n / 4)

    cell_w = (aw - GAP * (n_cols - 1)) / n_cols
    cell_h = (ah - GAP * (n_rows - 1)) / n_rows

    for i, prod in enumerate(products):
        row = i // n_cols
        col = i % n_cols

        # Centre partial last row
        items_in_row = min(n_cols, n - row * n_cols)
        if items_in_row < n_cols:
            row_offset = (aw - items_in_row * (cell_w + GAP) + GAP) / 2
        else:
            row_offset = 0

        cx = ax + row_offset + col * (cell_w + GAP)
        # Canvas y=0 is bottom; rows go top-to-bottom
        cy = ay + (n_rows - 1 - row) * (cell_h + GAP)

        # Image area (cell minus caption strip at bottom)
        img_h = cell_h - CAP_H

        pil_img = load_pil(prod.get('img'))
        place_image_fit(c, pil_img, cx, cy + CAP_H, cell_w, img_h)

        # Caption — clean text, no background strip
        cap = prod['title']
        if len(cap) > 34:
            cap = cap[:32] + '…'
        c.setFont(F_REG, 6.5)
        c.setFillColor(C_CAPTION)
        c.drawCentredString(cx + cell_w / 2, cy + CAP_H * 0.30, cap)

    c.showPage()


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT SPEC PAGE
# ─────────────────────────────────────────────────────────────────────────────
def draw_spec_page(c, room, page_products, page_num, total_pages,
                   logo_reader=None, studio='', footer_right='RESIDENTIAL INTERIOR DESIGN'):
    draw_bg(c)
    draw_page_header(c, room['name'], room.get('subtitle', ''), 'spec',
                     logo_reader=logo_reader, page_num=page_num, total_pages=total_pages,
                     studio=studio, footer_right=footer_right)

    # Content area
    content_top = H - 2 * M - HEADER_H
    content_bot = M + FOOTER_H
    content_h   = content_top - content_bot

    IMG_COL_W = 1.55 * inch
    IMG_PAD   = 0.10 * inch
    TEXT_X    = M + IMG_COL_W + 0.20 * inch
    TEXT_W    = W - TEXT_X - M

    row_h = content_h / PRODUCTS_PER_SPEC_PAGE

    for idx, prod in enumerate(page_products):
        row_top = content_top - idx * row_h
        row_bot = row_top - row_h

        # Separator (not before first item)
        if idx > 0:
            c.setStrokeColor(C_RULE)
            c.setLineWidth(0.3)
            c.line(M, row_top + 0.01 * inch, M + W - 2 * M, row_top + 0.01 * inch)

        # ── Thumbnail ──
        thumb_y = row_bot + IMG_PAD
        thumb_h = row_h - 2 * IMG_PAD
        thumb_w = IMG_COL_W - IMG_PAD

        # Light panel behind thumbnail
        c.setFillColor(colors.HexColor('#EDEAE5'))
        c.rect(M, thumb_y, thumb_w, thumb_h, fill=1, stroke=0)

        pil_img = load_pil(prod.get('img'))
        if pil_img:
            place_image_fit(c, pil_img, M, thumb_y, thumb_w, thumb_h, bg_fill=False)
        else:
            c.setFont(F_OBL, 6)
            c.setFillColor(C_CAPTION)
            c.drawCentredString(M + thumb_w / 2, thumb_y + thumb_h / 2, 'No Image')

        # Light border around thumbnail
        c.setStrokeColor(C_RULE)
        c.setLineWidth(0.2)
        c.rect(M, thumb_y, thumb_w, thumb_h, fill=0, stroke=1)

        # ── Text block ──
        ty = row_top - 0.17 * inch

        # Product name — always shown
        c.setFont(F_BOLD, 9.5)
        c.setFillColor(C_TEXT)
        c.drawString(TEXT_X, ty, prod['title'])
        ty -= 0.17 * inch

        # Subtitle in accent italic
        if 'subtitle' in SPEC_FIELDS and prod.get('subtitle'):
            c.setFont(F_OBL, 7.5)
            c.setFillColor(C_ACCENT)
            c.drawString(TEXT_X, ty, prod['subtitle'])
            ty -= 0.155 * inch

        # Manufacturer (all-caps) + price on the right
        show_mfr   = 'mfr'   in SPEC_FIELDS and prod.get('mfr')
        show_price = 'price' in SPEC_FIELDS and prod.get('price')
        if show_mfr:
            c.setFont(F_BOLD, 6.5)
            c.setFillColor(C_CAPTION)
            c.drawString(TEXT_X, ty, prod['mfr'].upper())
        if show_price:
            pw = c.stringWidth(prod['price'], F_BOLD, 7)
            c.setFont(F_BOLD, 7)
            c.setFillColor(C_TEXT)
            c.drawString(TEXT_X + TEXT_W - pw, ty, prod['price'])
        if show_mfr or show_price:
            ty -= 0.145 * inch

        # Dimensions
        dims = prod.get('dims', '')
        if 'dims' in SPEC_FIELDS and dims and dims not in ('TBD', 'N/A', ''):
            c.setFont(F_REG, 6.5)
            c.setFillColor(C_CAPTION)
            c.drawString(TEXT_X, ty, f'DIMENSIONS:  {dims}')
            ty -= 0.14 * inch

        # Rule
        c.setStrokeColor(C_RULE)
        c.setLineWidth(0.2)
        c.line(TEXT_X, ty + 0.04 * inch, TEXT_X + TEXT_W, ty + 0.04 * inch)
        ty -= 0.07 * inch

        # Description
        if 'desc' in SPEC_FIELDS and prod.get('desc'):
            ty = draw_text_wrapped(c, prod['desc'], TEXT_X, ty, TEXT_W, F_REG, 6.8, C_TEXT, leading=9.5)
            ty -= 0.05 * inch

        # Sustainability
        if 'sustain' in SPEC_FIELDS and prod.get('sustain'):
            c.setFont(F_BOLD, 6.5)
            c.setFillColor(C_ACCENT)
            c.drawString(TEXT_X, ty, '■  SUSTAINABILITY:')
            ty -= 0.115 * inch
            ty = draw_text_wrapped(c, prod['sustain'], TEXT_X + 0.14 * inch, ty,
                                   TEXT_W - 0.14 * inch, F_OBL, 6.5, C_ACCENT, leading=9.0)

    c.showPage()


def draw_room_specs(c, room, logo_reader=None, studio='', footer_right='RESIDENTIAL INTERIOR DESIGN'):
    products = room['products']
    pages = [products[i:i + PRODUCTS_PER_SPEC_PAGE]
             for i in range(0, len(products), PRODUCTS_PER_SPEC_PAGE)]
    for pnum, batch in enumerate(pages, 1):
        draw_spec_page(c, room, batch, pnum, len(pages),
                       logo_reader=logo_reader, studio=studio, footer_right=footer_right)


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
def parse_markdown_file(md_path, room_slug, cache_dir):
    """
    Parse a product markdown clipping. Returns a product dict.
    Handles Obsidian frontmatter + body image references.
    """
    text = Path(md_path).read_text(encoding='utf-8', errors='replace')

    # ── YAML frontmatter ──
    fm = {}
    fm_match = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            if ':' in line:
                k, _, v = line.partition(':')
                fm[k.strip()] = v.strip().strip('"').strip("'")

    title = fm.get('title', Path(md_path).stem)
    source = fm.get('source', '')
    desc = fm.get('description', '')

    # ── Image extraction ──
    img_local = None

    # 1. Local embed: ![[filename.ext]]
    local_match = re.search(r'!\[\[([^\]]+\.(jpg|jpeg|png|webp|gif))\]\]', text, re.IGNORECASE)
    if local_match:
        local_file = Path(md_path).parent / local_match.group(1)
        if local_file.exists():
            img_local = str(local_file)

    # 2. Markdown image URL: ![alt](url)
    img_url = None
    if not img_local:
        url_match = re.search(r'!\[.*?\]\((https?://[^)]+\.(jpg|jpeg|png|webp))[^)]*\)', text, re.IGNORECASE)
        if not url_match:
            # Try without extension filter (CDN URLs often have no extension)
            url_match = re.search(r'!\[.*?\]\((https?://[^\s)>"]{20,})\)', text)
        if url_match:
            img_url = url_match.group(1)

    # Download URL image if needed
    if not img_local and img_url:
        prod_slug = slugify(title)
        cache_path = cache_dir / f"{room_slug}_{prod_slug}.jpg"
        if cache_path.exists() and cache_path.stat().st_size > 3000:
            img_local = str(cache_path)
        else:
            ok = download_image(img_url, str(cache_path))
            if ok:
                img_local = str(cache_path)

    # ── Dimension extraction ──
    dim_match = re.search(
        r'(?:overall\s+dimensions?|dimensions?|size)[:\s]+([^\n|]{5,60})',
        text, re.IGNORECASE
    )
    dims = dim_match.group(1).strip().rstrip('.') if dim_match else 'TBD'

    # ── Price extraction ──
    price_match = re.search(r'\$[\d,]+(?:\.\d{2})?', text)
    price = price_match.group(0) if price_match else None

    # ── Manufacturer ──
    # Try frontmatter author field
    mfr = fm.get('author', '')
    if isinstance(mfr, str):
        mfr = mfr.strip().strip('[]').replace('[[', '').replace(']]', '')
    # If empty, try body
    if not mfr:
        mfr_match = re.search(r'\*\*(?:brand|manufacturer|by|designed by)[:\s]*\*\*\s*(.+)', text, re.IGNORECASE)
        if mfr_match:
            mfr = mfr_match.group(1).strip()

    # ── Sustainability ──
    sustain_keywords = [
        r'FSC[®\s-]*certified', r'GoodWeave', r'GREENGUARD', r'CARB',
        r'CertiPUR', r'ETL\s+[Ll]isted', r'LEED', r'recycled material',
        r'zero[- ]VOC', r'B\s+Corporation', r'ISO\s+14001', r'Made in USA',
        r'responsibly managed', r'100%\s+recycled', r'hand[- ]crafted',
        r'organic', r'sustainable', r'low[- ]emission'
    ]
    sustain_sentences = []
    for kw in sustain_keywords:
        matches = re.finditer(rf'[^.!?\n]*{kw}[^.!?\n]*[.!?]?', text, re.IGNORECASE)
        for m in matches:
            s = m.group(0).strip()
            if 10 < len(s) < 200 and s not in sustain_sentences:
                sustain_sentences.append(s)

    sustain = ' '.join(sustain_sentences[:3]).strip() or None

    return {
        'title': title,
        'subtitle': None,
        'mfr': mfr or None,
        'price': price,
        'dims': dims,
        'desc': desc[:300] if desc else None,
        'sustain': sustain,
        'img': img_local,
        'source': source,
    }


def parse_room_folder(room_path, cache_dir):
    """Parse all markdown files in a room folder."""
    room_path = Path(room_path)
    room_slug = slugify(room_path.name)
    products = []
    for md_file in sorted(room_path.glob('*.md')):
        prod = parse_markdown_file(md_file, room_slug, cache_dir)
        if prod:
            products.append(prod)
    return products


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUILD FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
def build_pdf(rooms, output_path, project_name='', studio='', semester='',
              logo_path=None, footer_right='RESIDENTIAL INTERIOR DESIGN'):
    """
    Build the moodboard PDF.

    rooms: list of dicts:
      {
        'name': 'ENTRY',
        'subtitle': 'Foyer & Mudroom',
        'products': [
          {
            'title': '...', 'subtitle': '...', 'mfr': '...', 'price': '...',
            'dims': '...', 'desc': '...', 'sustain': '...', 'img': '/path/to/img.jpg'
          }, ...
        ]
      }
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load logo
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

    c = canvas.Canvas(str(output_path), pagesize=PAGE)
    c.setTitle(f'Mood Boards & Product Specifications — {project_name}')
    c.setAuthor(studio)
    c.setSubject('Residential Interior Design Mood Board')

    # Cover
    draw_cover(c, project_name, studio, semester, rooms,
               logo_reader=logo_reader, footer_right=footer_right)

    # Rooms
    for room in rooms:
        draw_moodboard(c, room, logo_reader=logo_reader, studio=studio, footer_right=footer_right)
        draw_room_specs(c, room, logo_reader=logo_reader, studio=studio, footer_right=footer_right)

    c.save()
    size = output_path.stat().st_size
    print(f'✅ PDF saved: {output_path}  ({size // 1024} KB,  pages: cover + {len(rooms)} rooms)')
    return str(output_path)


def auto_build_from_directory(project_dir, output_path, project_name='', studio='',
                               semester='', logo_path=None, footer_right='RESIDENTIAL INTERIOR DESIGN'):
    """
    Automatically discover rooms from subfolders and build the PDF.
    Any subfolder containing .md files is treated as a room.
    """
    project_dir = Path(project_dir)
    cache_dir = project_dir / '_image_cache'
    cache_dir.mkdir(exist_ok=True)

    # Discover room subfolders (skip hidden dirs and _image_cache)
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
                'name': rd.name.upper(),
                'subtitle': '',
                'products': products,
            })
        print(f'  Room: {rd.name} — {len(products)} products')

    if not project_name:
        project_name = project_dir.name

    return build_pdf(rooms, output_path, project_name=project_name, studio=studio,
                     semester=semester, logo_path=logo_path, footer_right=footer_right)


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate interior design mood board PDF')
    parser.add_argument('--project-dir', required=True, help='Root folder with room subfolders')
    parser.add_argument('--output', required=True, help='Output PDF path')
    parser.add_argument('--project-name', default='', help='Project name for cover page')
    parser.add_argument('--studio', default='', help='Studio/course name for headers')
    parser.add_argument('--semester', default='', help='Semester/date for cover page')
    parser.add_argument('--logo', default=None, help='Path to logo PNG/JPG (optional)')
    parser.add_argument('--footer-right', default='RESIDENTIAL INTERIOR DESIGN')
    parser.add_argument('--rooms-json', default=None,
                        help='Path to rooms JSON file (overrides auto-discovery)')

    # ── Spec field visibility ──────────────────────────────────────────────────
    parser.add_argument(
        '--spec-fields', default=None,
        help=(
            'Comma-separated list of spec fields to include on product pages. '
            'Available: subtitle, mfr, price, dims, desc, sustain. '
            'Omit to include all fields. Example: --spec-fields "mfr,dims,sustain"'
        )
    )

    # ── Color overrides ────────────────────────────────────────────────────────
    parser.add_argument('--color-bg',      default=None, help='Page background color (hex, e.g. #F5F2EE)')
    parser.add_argument('--color-accent',  default=None, help='Accent / heading color (hex, e.g. #3D5A40)')
    parser.add_argument('--color-text',    default=None, help='Body text color (hex, e.g. #1A1A18)')
    parser.add_argument('--color-dark',    default=None, help='Cover panel / near-black color (hex)')
    parser.add_argument('--color-rule',    default=None, help='Rule / divider color (hex)')
    parser.add_argument('--color-caption', default=None, help='Secondary / caption text color (hex)')

    args = parser.parse_args()

    # Apply user preferences before generating
    if args.spec_fields is not None:
        set_spec_fields(args.spec_fields)

    apply_theme(
        bg=args.color_bg,
        accent=args.color_accent,
        text=args.color_text,
        dark=args.color_dark,
        rule=args.color_rule,
        caption=args.color_caption,
    )

    if args.rooms_json:
        with open(args.rooms_json) as f:
            rooms = json.load(f)
        build_pdf(rooms, args.output, project_name=args.project_name,
                  studio=args.studio, semester=args.semester,
                  logo_path=args.logo, footer_right=args.footer_right)
    else:
        auto_build_from_directory(
            args.project_dir, args.output,
            project_name=args.project_name, studio=args.studio,
            semester=args.semester, logo_path=args.logo,
            footer_right=args.footer_right
        )
