#!/usr/bin/env python3
"""
svg_to_dxf.py — Convert SVG paths (from vtracer/trace_image.py) into the geometry JSON
format expected by build_block.py.

Handles SVG path commands: M (moveto), L (lineto), H (horizontal), V (vertical),
C (cubic bezier), Q (quadratic bezier), A (arc), Z (closepath).
Bezier curves are approximated as polyline segments.

Usage:
    python scripts/svg_to_dxf.py \
        --input /tmp/traced.svg \
        --output /tmp/geometry.json \
        --block-name "FURN-1-MY-PRODUCT" \
        --width 24.0 \
        --height 36.0 \
        --units inches \
        --min-area 50
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Convert SVG paths to DXF geometry JSON")
    p.add_argument("--input",      required=True,        help="Input SVG file path")
    p.add_argument("--output",     required=True,        help="Output geometry JSON file path")
    p.add_argument("--block-name", default="BLOCK-1",    help="DXF block name")
    p.add_argument("--width",      type=float, default=0, help="Real-world width in units")
    p.add_argument("--height",     type=float, default=0, help="Real-world height in units")
    p.add_argument("--units",      default="inches",      help="Drawing units (inches or mm)")
    p.add_argument("--min-area",   type=float, default=50, help="Minimum path area in px² to keep")
    return p.parse_args()


# --- SVG path parsing ---

def tokenize_path(d):
    """Tokenize an SVG path d string into a list of (command, args) tuples."""
    tokens = re.findall(r'([MmLlHhVvCcQqAaZz])|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)', d)
    result = []
    for cmd, num in tokens:
        if cmd:
            result.append(cmd)
        elif num:
            result.append(float(num))
    return result


def parse_svg_path(d):
    """Parse an SVG path d string into a list of absolute polyline point arrays."""
    tokens = tokenize_path(d)
    polylines = []
    current_polyline = []
    cx, cy = 0.0, 0.0
    start_x, start_y = 0.0, 0.0
    i = 0
    cmd = None

    def consume(n):
        nonlocal i
        vals = tokens[i:i+n]
        i += n
        return vals

    bezier_steps = 12  # segments per bezier approximation

    def cubic_bezier_points(p0, p1, p2, p3):
        pts = []
        for t_i in range(bezier_steps + 1):
            t = t_i / bezier_steps
            u = 1 - t
            x = u**3*p0[0] + 3*u**2*t*p1[0] + 3*u*t**2*p2[0] + t**3*p3[0]
            y = u**3*p0[1] + 3*u**2*t*p1[1] + 3*u*t**2*p2[1] + t**3*p3[1]
            pts.append((x, y))
        return pts

    def quadratic_bezier_points(p0, p1, p2):
        pts = []
        for t_i in range(bezier_steps + 1):
            t = t_i / bezier_steps
            u = 1 - t
            x = u**2*p0[0] + 2*u*t*p1[0] + t**2*p2[0]
            y = u**2*p0[1] + 2*u*t*p1[1] + t**2*p2[1]
            pts.append((x, y))
        return pts

    while i < len(tokens):
        tok = tokens[i]

        if isinstance(tok, str):
            cmd = tok
            i += 1
        # else: repeat the previous command with new args

        if cmd in ('M', 'm'):
            if current_polyline:
                polylines.append(list(current_polyline))
            x, y = consume(2)
            if cmd == 'm':
                cx += x; cy += y
            else:
                cx, cy = x, y
            start_x, start_y = cx, cy
            current_polyline = [(cx, cy)]
            cmd = 'L' if cmd == 'M' else 'l'  # subsequent coords are lineto

        elif cmd in ('L', 'l'):
            x, y = consume(2)
            if cmd == 'l':
                cx += x; cy += y
            else:
                cx, cy = x, y
            current_polyline.append((cx, cy))

        elif cmd in ('H', 'h'):
            x, = consume(1)
            if cmd == 'h':
                cx += x
            else:
                cx = x
            current_polyline.append((cx, cy))

        elif cmd in ('V', 'v'):
            y, = consume(1)
            if cmd == 'v':
                cy += y
            else:
                cy = y
            current_polyline.append((cx, cy))

        elif cmd in ('C', 'c'):
            x1, y1, x2, y2, x, y = consume(6)
            if cmd == 'c':
                p1 = (cx+x1, cy+y1); p2 = (cx+x2, cy+y2); ep = (cx+x, cy+y)
            else:
                p1 = (x1, y1); p2 = (x2, y2); ep = (x, y)
            pts = cubic_bezier_points((cx, cy), p1, p2, ep)
            current_polyline.extend(pts[1:])
            cx, cy = ep

        elif cmd in ('Q', 'q'):
            x1, y1, x, y = consume(4)
            if cmd == 'q':
                p1 = (cx+x1, cy+y1); ep = (cx+x, cy+y)
            else:
                p1 = (x1, y1); ep = (x, y)
            pts = quadratic_bezier_points((cx, cy), p1, ep)
            current_polyline.extend(pts[1:])
            cx, cy = ep

        elif cmd in ('A', 'a'):
            # Skip arc for now — just add endpoint
            rx, ry, rot, large, sweep, x, y = consume(7)
            if cmd == 'a':
                cx += x; cy += y
            else:
                cx, cy = x, y
            current_polyline.append((cx, cy))

        elif cmd in ('Z', 'z'):
            if current_polyline:
                current_polyline.append((start_x, start_y))
                polylines.append(list(current_polyline))
                current_polyline = []
            cx, cy = start_x, start_y

    if current_polyline:
        polylines.append(current_polyline)

    return polylines


def path_area(pts):
    """Compute the unsigned area of a polyline via the shoelace formula."""
    n = len(pts)
    if n < 3:
        return 0
    area = 0
    for j in range(n):
        x1, y1 = pts[j]
        x2, y2 = pts[(j+1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2


def extract_svg_paths(svg_text):
    """Extract all path d attributes from an SVG string."""
    return re.findall(r'<path[^>]*\sd="([^"]+)"', svg_text, re.IGNORECASE)


def get_svg_dimensions(svg_text):
    """Get SVG canvas width and height in pixels."""
    w = h = 0
    m = re.search(r'<svg[^>]*\swidth="([^"]+)"', svg_text)
    if m:
        try: w = float(re.sub(r'[^\d.]', '', m.group(1)))
        except: pass
    m = re.search(r'<svg[^>]*\sheight="([^"]+)"', svg_text)
    if m:
        try: h = float(re.sub(r'[^\d.]', '', m.group(1)))
        except: pass
    return w, h


def simplify_polyline(pts, tolerance=0.5):
    """Simple Ramer–Douglas–Peucker polyline simplification."""
    if len(pts) <= 2:
        return pts

    def perp_distance(pt, line_start, line_end):
        lx, ly = line_end[0]-line_start[0], line_end[1]-line_start[1]
        length = math.sqrt(lx**2 + ly**2)
        if length == 0:
            return math.dist(pt, line_start)
        return abs(lx*(line_start[1]-pt[1]) - (line_start[0]-pt[0])*ly) / length

    dmax, idx = 0, 0
    for i in range(1, len(pts)-1):
        d = perp_distance(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax, idx = d, i

    if dmax > tolerance:
        left  = simplify_polyline(pts[:idx+1], tolerance)
        right = simplify_polyline(pts[idx:], tolerance)
        return left[:-1] + right
    return [pts[0], pts[-1]]


def scale_polyline(pts, scale_x, scale_y, flip_y, img_height):
    """Scale pixel coordinates to real-world units, flipping Y axis."""
    result = []
    for x, y in pts:
        rx = x * scale_x
        ry = (img_height - y) * scale_y if flip_y else y * scale_y
        result.append([round(rx, 3), round(ry, 3)])
    return result


def assign_layer(area, total_area):
    """Assign layer based on relative area."""
    ratio = area / total_area if total_area > 0 else 0
    if ratio > 0.3:
        return "0-OUTLINE"
    return "0-DETAIL"


def main():
    args = parse_args()

    svg_path = Path(args.input)
    if not svg_path.exists():
        print(f"Error: SVG not found: {svg_path}")
        sys.exit(1)

    svg_text = svg_path.read_text(encoding="utf-8")
    img_w, img_h = get_svg_dimensions(svg_text)

    if img_w == 0 or img_h == 0:
        img_w, img_h = 100, 100  # fallback

    # Compute scale factors
    real_w = args.width if args.width > 0 else img_w
    real_h = args.height if args.height > 0 else img_h
    scale_x = real_w / img_w
    scale_y = real_h / img_h

    print(f"SVG canvas: {img_w}×{img_h}px → Real: {real_w}×{real_h} {args.units}")

    # Extract and parse paths
    path_ds = extract_svg_paths(svg_text)
    print(f"Found {len(path_ds)} path elements")

    all_polylines = []
    for d in path_ds:
        try:
            polys = parse_svg_path(d)
            all_polylines.extend(polys)
        except Exception as e:
            print(f"  Warning: path parse error: {e}")

    # Filter by minimum area
    areas = [(pts, path_area(pts)) for pts in all_polylines]
    significant = [(pts, area) for pts, area in areas if area >= args.min_area]
    print(f"Significant paths (area ≥ {args.min_area}px²): {len(significant)}")

    if not significant:
        print("Warning: no significant paths found. Try lowering --min-area.")

    # Compute total area for layer assignment
    total_area = sum(a for _, a in significant)

    # Build entities
    entities = []
    for pts, area in significant:
        simplified = simplify_polyline(pts, tolerance=1.0)
        scaled = scale_polyline(simplified, scale_x, scale_y, flip_y=True, img_height=img_h)

        if len(scaled) < 2:
            continue

        layer = assign_layer(area, total_area)
        closed = (abs(pts[0][0]-pts[-1][0]) < 2 and abs(pts[0][1]-pts[-1][1]) < 2)

        entities.append({
            "type":   "lwpolyline",
            "points": scaled,
            "closed": closed,
            "layer":  layer,
        })

    # Build geometry JSON
    geom = {
        "block_name": args.block_name,
        "units":      args.units,
        "width":      real_w,
        "height":     real_h,
        "entities":   entities,
    }

    Path(args.output).write_text(json.dumps(geom, indent=2))
    print(f"✅ Geometry JSON saved: {args.output} ({len(entities)} entities)")


if __name__ == "__main__":
    main()
