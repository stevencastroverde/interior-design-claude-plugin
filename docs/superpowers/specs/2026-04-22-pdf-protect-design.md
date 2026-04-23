# pdf-protect Skill Design

**Date:** 2026-04-22
**Status:** Implemented

## Problem

Interior design deliverables (moodboards, proposals, concept decks) need protection before client delivery. The risk is unauthorized sharing and idea theft. Standard PDF password protection requires recipients to enter a password, which is friction. The goal is transparent protection: watermarks that deter sharing + permission restrictions that block editing/copying/printing — with no open password required.

## Approach

Layered protection without an open password:

1. **Visible diagonal watermark** — semi-transparent (15% opacity), diagonal 45°, stamped on every page. Large enough to be a deterrent, light enough to read through.
2. **PDF permission restrictions** — invisible owner password (random, never shown) enforces restrictions. No user-facing password prompt.
3. **Recipient-specific watermarks** — optional; embeds client name/email in the watermark text to make leaks traceable.

## Architecture

```
skills/pdf-protect/
├── SKILL.md              # trigger scenarios + interactive workflow
└── scripts/
    └── protect_pdf.py    # CLI + Python API
```

**Dependencies:** `reportlab` (watermark rendering) + `pypdf` (page merging, permissions). Both pure Python; no system dependencies.

## Watermark Design

- Font: Helvetica-Bold, 48pt
- Color: `#1C1E18` (matches plugin palette)
- Opacity: 15% via ReportLab `setFillAlpha(0.15)`
- Rotation: 45° diagonal, centered on each page
- Per-page overlay (handles variable page sizes)

**Text logic:**
- Default: `CONFIDENTIAL — Steven Castroverde — <date>`
- With recipient: `CONFIDENTIAL — Prepared for Jane Doe — jane@example.com`

## Permissions

Uses `pypdf`'s `UserAccessPermissions` flags. Owner password is `secrets.token_hex(16)` — random, never surfaced. User password is `""` — PDF opens freely.

Restrictions are opt-in per run: editing, copying, printing (any combination).

## Interactive Workflow

1. Accept PDF path or scan CWD for `.pdf` files
2. Ask: recipient name? (optional)
3. If name given, ask: recipient email? (optional)
4. Ask: which restrictions? (editing / copying / printing / none)
5. Run script, report output path (`<stem>-protected.pdf`)

## Key Decisions

- **Standalone skill** (not integrated into moodboard-pdf) — works on any PDF, more reusable
- **No open password** — friction-free for legitimate recipients; protection is deterrent-based
- **15% opacity** — visible but not obstructing; tuned to keep content fully readable
- **Per-page watermark generation** — handles PDFs with mixed page sizes correctly
