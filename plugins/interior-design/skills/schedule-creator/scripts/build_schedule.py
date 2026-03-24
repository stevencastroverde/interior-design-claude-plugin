#!/usr/bin/env python3
"""
build_schedule.py — Interior Design Room Schedule Excel Generator

Usage:
  python3 build_schedule.py \
    --output "/path/to/Kitchen Schedule.xlsx" \
    --data   "/path/to/products.json" \
    [--room "Kitchen"] \
    [--project "Intersecting Stories"] \
    [--studio "ARCH X482.2 — Design Studio II"] \
    [--semester "SPRING 2026"]

Or import build_schedule() and call directly from Python.
"""

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
    from openpyxl.drawing.xdr import XDRPositiveSize2D
    from openpyxl.utils.units import pixels_to_EMU
    from PIL import Image as PILImage
    import requests
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install openpyxl pillow requests --break-system-packages")
    raise

# ── Layout constants ──────────────────────────────────────────────────────────
COL_WIDTHS  = {'A': 10, 'B': 17, 'C': 28, 'D': 20, 'E': 30, 'F': 40, 'G': 10, 'H': 30}
HDR_ROW_H   = 22    # header row height (pts)
CAT_ROW_H   = 18    # category row height (pts)
PROD_ROW_H  = 90    # product row height (pts)
IMG_MAX_W   = 110   # thumbnail max width (px)
IMG_MAX_H   = 78    # thumbnail max height (px)
COL_B_PX    = 128   # approx column B width in pixels (17 chars × 7.5px)
ROW_PROD_PX = 120   # approx product row height in pixels (90pt × 1.33)

# ── Style helpers ─────────────────────────────────────────────────────────────
def _thin():   return Side(style='thin',   color='CCCCCC')
def _med():    return Side(style='medium', color='999999')

def _border(left_med=False, right_med=False):
    return Border(
        top=_thin(), bottom=_thin(),
        left=_med()  if left_med  else _thin(),
        right=_med() if right_med else _thin(),
    )

def _fill(hex_color): return PatternFill('solid', fgColor=hex_color)
def _bold(sz=9):  return Font(name='Arial', bold=True,  size=sz)
def _reg(sz=8):   return Font(name='Arial', bold=False, size=sz)
def _link(sz=8):  return Font(name='Arial', size=sz, color='0563C1', underline='single')
def _center(wrap=True):  return Alignment(horizontal='center', vertical='center', wrap_text=wrap)
def _left(wrap=False):   return Alignment(horizontal='left',   vertical='center', wrap_text=wrap)


# ── Image utilities ───────────────────────────────────────────────────────────
def download_image(url, dest_path):
    """Try multiple User-Agent strategies to download an image."""
    if not url or not str(url).startswith('http'):
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
            if r.status_code == 200:
                content = b''.join(r.iter_content(8192))
                if len(content) > 2000:
                    with open(dest_path, 'wb') as f:
                        f.write(content)
                    if os.path.getsize(dest_path) > 2000:
                        return True
        except Exception:
            continue
    return False


def make_thumbnail(src_path, tmp_dir, max_w=IMG_MAX_W, max_h=IMG_MAX_H):
    """Resize image to thumbnail, save to tmp_dir. Returns (path, w, h) or None."""
    if not src_path or not os.path.exists(str(src_path)):
        return None
    try:
        pil = PILImage.open(str(src_path)).convert('RGB')
        pil.thumbnail((max_w, max_h), PILImage.LANCZOS)
        name = 'thumb_' + Path(src_path).name.replace(' ', '_') + '.png'
        dst = Path(tmp_dir) / name
        pil.save(str(dst), 'PNG')
        return str(dst), pil.width, pil.height
    except Exception as e:
        print(f'  Thumbnail error {src_path}: {e}')
        return None


def embed_image(ws, img_path, img_w, img_h, col_idx, row_idx):
    """
    Embed a thumbnail image centered in a cell.
    col_idx and row_idx are 0-based (col B = 1, first data row - 1).
    """
    try:
        xl_img  = XLImage(img_path)
        xl_img.width  = img_w
        xl_img.height = img_h

        x_off = max(0, (COL_B_PX  - img_w) // 2)
        y_off = max(0, (ROW_PROD_PX - img_h) // 2)

        marker = AnchorMarker(
            col=col_idx, colOff=pixels_to_EMU(x_off),
            row=row_idx, rowOff=pixels_to_EMU(y_off),
        )
        size = XDRPositiveSize2D(pixels_to_EMU(img_w), pixels_to_EMU(img_h))
        xl_img.anchor = OneCellAnchor(_from=marker, ext=size)
        ws.add_image(xl_img)
        return True
    except Exception as e:
        print(f'  Image embed error: {e}')
        return False


# ── Main build function ───────────────────────────────────────────────────────
def build_schedule(categories, output_path,
                   room='', project='', studio='', semester='',
                   cache_dir=None):
    """
    Build the room schedule Excel file.

    categories: list of dicts:
      {
        'label': 'APPLIANCES',
        'items': [
          {
            'code': 'AP-1',
            'img':  '/path/to/image.jpg',   # local path or URL
            'model': '...',
            'mfr': '...',
            'dims': '...',
            'notes': '...',
            'qty': '',
            'link': 'https://...',
          }, ...
        ]
      }
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Working dirs
    tmp_dir = tempfile.mkdtemp()
    if cache_dir:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)

    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f'{room} Schedule' if room else 'Room Schedule'

        # Column widths
        for col, w in COL_WIDTHS.items():
            ws.column_dimensions[col].width = w

        # ── Header row ────────────────────────────────────────────────────────
        ws.row_dimensions[1].height = HDR_ROW_H
        headers = ['CODE', 'IMAGE', 'MODEL', 'MANUFACTURER', 'DIMENSIONS', 'NOTES', 'QUANTITY', 'LINK']
        for ci, h in enumerate(headers, 1):
            c = ws.cell(row=1, column=ci, value=h)
            c.font      = _bold(9)
            c.fill      = _fill('E0E0E0')
            c.alignment = _center(wrap=False)
            c.border    = Border(top=_med(), bottom=_med(), left=_med(), right=_med())
        ws.freeze_panes = 'A2'

        # ── Data rows ─────────────────────────────────────────────────────────
        cur_row = 2
        images_embedded = 0

        for cat in categories:
            # Category header
            ws.row_dimensions[cur_row].height = CAT_ROW_H
            ws.merge_cells(start_row=cur_row, start_column=1,
                           end_row=cur_row,   end_column=8)
            c = ws.cell(row=cur_row, column=1, value=cat['label'])
            c.font      = _bold(9)
            c.fill      = _fill('D6E4F0')
            c.alignment = _left()
            c.border    = Border(top=_med(), bottom=_med(), left=_med(), right=_med())
            cur_row += 1

            for i, item in enumerate(cat['items']):
                alt  = (i % 2 == 1)
                fill = _fill('F4F4F4' if alt else 'FFFFFF')
                ws.row_dimensions[cur_row].height = PROD_ROW_H

                def write(col, val='', fnt=None, algn=None, hyper=None):
                    c = ws.cell(row=cur_row, column=col, value=val)
                    c.font      = fnt  or _reg()
                    c.alignment = algn or _center()
                    c.fill      = fill
                    c.border    = _border(left_med=(col == 1), right_med=(col == 8))
                    if hyper:
                        c.hyperlink = hyper
                    return c

                write(1, item.get('code',''), fnt=_bold(9))
                write(2, '')   # image cell — populated below
                write(3, item.get('model',''))
                write(4, item.get('mfr',''))
                write(5, item.get('dims',''))
                write(6, item.get('notes',''))
                write(7, item.get('qty',''))

                link_val = item.get('link','')
                if link_val:
                    write(8, 'LINK', fnt=_link(), hyper=link_val)
                else:
                    write(8, '')

                # ── Image ─────────────────────────────────────────────────────
                img_src = item.get('img')
                if img_src:
                    # If it's a URL, download to cache first
                    if str(img_src).startswith('http'):
                        if cache_dir:
                            slug = item.get('code','img').replace('-','_').lower()
                            cached = Path(cache_dir) / f'{slug}.jpg'
                            if not (cached.exists() and cached.stat().st_size > 2000):
                                download_image(img_src, str(cached))
                            img_src = str(cached) if cached.exists() else None
                        else:
                            dl_path = Path(tmp_dir) / f'dl_{cur_row}.jpg'
                            download_image(img_src, str(dl_path))
                            img_src = str(dl_path) if dl_path.exists() else None

                    if img_src and os.path.exists(img_src):
                        result = make_thumbnail(img_src, tmp_dir)
                        if result:
                            thumb_path, img_w, img_h = result
                            # col B = index 1 (0-based), row is cur_row-1 (0-based)
                            ok = embed_image(ws, thumb_path, img_w, img_h,
                                             col_idx=1, row_idx=cur_row - 1)
                            if ok:
                                images_embedded += 1

                cur_row += 1

        # ── Page setup ────────────────────────────────────────────────────────
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToPage   = True
        ws.page_setup.fitToWidth  = 1
        ws.page_setup.fitToHeight = 0
        ws.print_title_rows       = '1:1'

        header_text = f'{room.upper()} SCHEDULE'
        if project:
            header_text += f' — {project.upper()}'
        ws.oddHeader.center.text = header_text

        footer_left = studio
        if semester:
            footer_left += f' — {semester}'
        ws.oddFooter.left.text  = footer_left
        ws.oddFooter.right.text = 'RESIDENTIAL INTERIOR DESIGN'

        wb.save(str(output_path))
        size = output_path.stat().st_size
        print(f'✅ Schedule saved: {output_path}  ({size // 1024} KB)')
        print(f'   {cur_row - 2 - len(categories)} product rows, {images_embedded} images embedded')
        return str(output_path)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── CLI entry point ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Build interior design room schedule Excel.')
    parser.add_argument('--output',   required=True, help='Output .xlsx path')
    parser.add_argument('--data',     required=True, help='JSON file with categories/items data')
    parser.add_argument('--room',     default='',    help='Room name (e.g. Kitchen)')
    parser.add_argument('--project',  default='',    help='Project name')
    parser.add_argument('--studio',   default='',    help='Studio / course name')
    parser.add_argument('--semester', default='',    help='Semester / season')
    parser.add_argument('--cache-dir',default=None,  help='Directory to cache downloaded images')
    args = parser.parse_args()

    with open(args.data) as f:
        data = json.load(f)

    categories = data.get('categories', data) if isinstance(data, dict) else data

    build_schedule(
        categories=categories,
        output_path=args.output,
        room=args.room or data.get('room', ''),
        project=args.project or data.get('project', ''),
        studio=args.studio or data.get('studio', ''),
        semester=args.semester or data.get('semester', ''),
        cache_dir=args.cache_dir,
    )


if __name__ == '__main__':
    main()
