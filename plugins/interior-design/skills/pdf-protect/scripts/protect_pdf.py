#!/usr/bin/env python3
"""
protect_pdf.py — Add watermark and optional permission restrictions to a PDF.

Dependencies:
    pip install pypdf reportlab
"""

import argparse
import io
import secrets
import sys
from datetime import date
from pathlib import Path

try:
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader, PdfWriter
    from pypdf.constants import UserAccessPermissions
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install reportlab pypdf")
    sys.exit(1)


def build_watermark_page(width: float, height: float, text: str):
    """Return a pypdf Page containing a diagonal watermark at 15% opacity."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    c.setFillColorRGB(0x1C / 255, 0x1E / 255, 0x18 / 255)
    c.setFillAlpha(0.15)
    c.setFont("Helvetica-Bold", 48)
    c.saveState()
    c.translate(width / 2, height / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, text)
    c.restoreState()
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def protect_pdf(
    input_path: str,
    output_path: str,
    watermark_text: str,
    restrict_editing: bool,
    restrict_copying: bool,
    restrict_printing: bool,
) -> str:
    """Merge watermark onto each page, optionally encrypt with permission flags."""
    reader = PdfReader(input_path)
    writer = PdfWriter()

    for page in reader.pages:
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        wm_page = build_watermark_page(w, h, watermark_text)
        page.merge_page(wm_page)
        writer.add_page(page)

    if restrict_editing or restrict_copying or restrict_printing:
        # Start with all permissions enabled
        perms = (
            UserAccessPermissions.PRINT
            | UserAccessPermissions.MODIFY
            | UserAccessPermissions.EXTRACT
            | UserAccessPermissions.ADD_OR_MODIFY
            | UserAccessPermissions.FILL_FORM_FIELDS
            | UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS
            | UserAccessPermissions.ASSEMBLE_DOC
            | UserAccessPermissions.PRINT_TO_REPRESENTATION
        )

        if restrict_printing:
            perms &= ~UserAccessPermissions.PRINT
            perms &= ~UserAccessPermissions.PRINT_TO_REPRESENTATION
        if restrict_editing:
            perms &= ~UserAccessPermissions.MODIFY
            perms &= ~UserAccessPermissions.ADD_OR_MODIFY
            perms &= ~UserAccessPermissions.FILL_FORM_FIELDS
            perms &= ~UserAccessPermissions.ASSEMBLE_DOC
        if restrict_copying:
            perms &= ~UserAccessPermissions.EXTRACT
            perms &= ~UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS

        writer.encrypt(
            user_password="",
            owner_password=secrets.token_hex(16),
            permissions_flag=perms,
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Watermark and optionally restrict permissions on a PDF."
    )
    parser.add_argument("--input", required=True, help="Path to the input PDF file")
    parser.add_argument(
        "--output",
        default=None,
        help="Path for the output PDF (default: <stem>-protected.pdf alongside input)",
    )
    parser.add_argument(
        "--watermark-text",
        default=None,
        help='Watermark string (default: "CONFIDENTIAL — Steven Castroverde — <date>")',
    )
    parser.add_argument("--recipient-name", default=None, help="Recipient's display name")
    parser.add_argument("--recipient-email", default=None, help="Recipient's email address")
    parser.add_argument(
        "--restrict",
        nargs="*",
        choices=["editing", "copying", "printing"],
        default=[],
        help="Permission restrictions to apply (any combination of: editing copying printing)",
    )

    args = parser.parse_args()

    # Resolve input path
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Resolve output path
    if args.output:
        output_path = str(Path(args.output).expanduser().resolve())
    else:
        output_path = str(input_path.parent / f"{input_path.stem}-protected.pdf")

    # Warn if email provided without name
    if args.recipient_email and not args.recipient_name:
        print("Warning: --recipient-email ignored because --recipient-name was not provided.", file=sys.stderr)

    # Assemble watermark text
    if args.recipient_name:
        parts = [f"CONFIDENTIAL \u2014 Prepared for {args.recipient_name}"]
        if args.recipient_email:
            parts.append(args.recipient_email)
        watermark_text = " \u2014 ".join(parts)
    else:
        watermark_text = (
            args.watermark_text
            or f"CONFIDENTIAL \u2014 Steven Castroverde \u2014 {date.today()}"
        )

    # Parse restriction flags
    restrict_list = args.restrict
    restrict_editing = "editing" in restrict_list
    restrict_copying = "copying" in restrict_list
    restrict_printing = "printing" in restrict_list

    try:
        result = protect_pdf(
            input_path=str(input_path),
            output_path=output_path,
            watermark_text=watermark_text,
            restrict_editing=restrict_editing,
            restrict_copying=restrict_copying,
            restrict_printing=restrict_printing,
        )
    except Exception as e:
        print(f"Error: failed to process PDF — {e}", file=sys.stderr)
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()
