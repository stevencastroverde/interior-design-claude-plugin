#!/usr/bin/env python3
"""
trace_image.py — Path B: Preprocess a product image and trace it to SVG vector paths.

Uses OpenCV for preprocessing and vtracer for vectorization. Best suited for products
with clean (white or uniform) backgrounds, or when literal silhouette tracing is preferred
over geometric interpretation.

Usage:
    python scripts/trace_image.py --input /path/to/image.jpg --output /tmp/traced.svg
    python scripts/trace_image.py --input /path/to/image.jpg --output /tmp/traced.svg --bg-remove

Requirements:
    pip install vtracer opencv-python-headless --break-system-packages
"""

import argparse
import sys
import tempfile
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Trace a product image to SVG vector paths")
    p.add_argument("--input",     required=True,      help="Input image path (PNG/JPG/WEBP)")
    p.add_argument("--output",    required=True,      help="Output SVG path")
    p.add_argument("--bg-remove", action="store_true", help="Attempt background removal before tracing")
    p.add_argument("--threshold", type=int, default=128, help="Binary threshold (0-255, default 128)")
    return p.parse_args()


def preprocess_with_opencv(image_path, threshold=128):
    """
    Preprocess image for tracing: grayscale → blur → threshold → morphological cleanup.
    Returns the binary image as bytes (PNG).
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("OpenCV not available. Install: pip install opencv-python-headless --break-system-packages")
        sys.exit(1)

    img = cv2.imread(str(image_path))
    if img is None:
        print(f"Error: Could not load image: {image_path}")
        sys.exit(1)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive threshold for variable lighting conditions
    binary = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=21,
        C=5
    )

    # Simple threshold as alternative if adaptive gives messy result
    # _, binary = cv2.threshold(blurred, threshold, 255, cv2.THRESH_BINARY_INV)

    # Morphological cleanup: close small gaps, remove small specks
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  kernel, iterations=1)

    # Convert back to PNG bytes
    _, png_bytes = cv2.imencode(".png", binary)
    return png_bytes.tobytes()


def remove_background(image_path):
    """Attempt background removal using rembg (if available)."""
    try:
        from rembg import remove
        from PIL import Image
        import io

        img = Image.open(image_path)
        result = remove(img)

        # Convert to grayscale binary for tracing
        gray = result.convert("L")
        buf = io.BytesIO()
        gray.save(buf, format="PNG")
        return buf.getvalue()

    except ImportError:
        print("  rembg not available — skipping background removal.")
        print("  Install with: pip install rembg --break-system-packages")
        return None


def trace_with_vtracer(image_bytes, output_path):
    """Vectorize a binary PNG image using vtracer."""
    try:
        import vtracer
    except ImportError:
        print("vtracer not available. Install: pip install vtracer --break-system-packages")
        sys.exit(1)

    svg_str = vtracer.convert_raw_image_to_svg(
        image_bytes,
        img_format="png",
        colormode="binary",         # clean binary tracing
        hierarchical="cutout",      # handles nested shapes (holes in objects)
        filter_speckle=6,           # remove noise smaller than 6px²
        color_precision=6,
        layer_difference=16,
        corner_threshold=60,        # how sharp corners need to be to preserve them
        length_threshold=4.0,       # simplify paths: merge segments shorter than this
        max_iterations=10,
        splice_threshold=45,
        path_precision=3,
    )

    Path(output_path).write_text(svg_str, encoding="utf-8")
    return svg_str


def fallback_opencv_contours(image_path, output_path, min_area=500):
    """
    Fallback: extract contours with OpenCV and write a basic SVG.
    Less smooth than vtracer but works without it.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("OpenCV not available for fallback.")
        sys.exit(1)

    img = cv2.imread(str(image_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    significant = [c for c in contours if cv2.contourArea(c) > min_area]

    h, w = img.shape[:2]
    paths = []
    for contour in significant:
        approx = cv2.approxPolyDP(contour, 2.0, True)
        pts = approx.reshape(-1, 2)
        if len(pts) < 3:
            continue
        d = f"M {pts[0][0]} {pts[0][1]}"
        for pt in pts[1:]:
            d += f" L {pt[0]} {pt[1]}"
        d += " Z"
        paths.append(d)

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">\n'
    for path_d in paths:
        svg += f'  <path d="{path_d}" fill="black" stroke="none"/>\n'
    svg += '</svg>\n'

    Path(output_path).write_text(svg, encoding="utf-8")
    print(f"Fallback SVG written with {len(paths)} contours.")
    return svg


def main():
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: image not found: {input_path}")
        sys.exit(1)

    print(f"Processing image: {input_path}")

    # Step 1: optionally remove background
    preprocessed_bytes = None
    if args.bg_remove:
        print("  Attempting background removal...")
        preprocessed_bytes = remove_background(input_path)

    # Step 2: OpenCV preprocessing
    if preprocessed_bytes is None:
        print("  Preprocessing with OpenCV...")
        preprocessed_bytes = preprocess_with_opencv(input_path, args.threshold)

    # Step 3: Trace with vtracer
    try:
        print("  Tracing with vtracer...")
        trace_with_vtracer(preprocessed_bytes, args.output)
        print(f"✅ SVG saved: {args.output}")
    except Exception as e:
        print(f"  vtracer failed ({e}), falling back to OpenCV contours...")
        # Write preprocessed image to temp file for fallback
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(preprocessed_bytes)
            tmp_path = tmp.name
        fallback_opencv_contours(tmp_path, args.output)
        print(f"✅ Fallback SVG saved: {args.output}")


if __name__ == "__main__":
    main()
