# Interior Design Skills — Claude Code Plugin

Workflow skills for interior designers: FF&E schedules, mood board PDFs, spec sheet annotation, CAD block generation, hatch patterns, and PDF protection.

## Skills

| Skill | Purpose |
|---|---|
| `moodboard-pdf` | Generates a branded PDF mood board from product markdown clippings |
| `schedule-creator` | Builds Excel FF&E room schedules from product data |
| `spec-sheet-annotator` | Annotates manufacturer spec sheets with project-specific callouts |
| `image-to-dxf` | Converts a product photo into a DXF block with embedded FF&E attributes |
| `autocad-hatch-pat` | Generates AutoCAD-compatible `.pat` hatch pattern files from tile/material patterns |
| `pdf-protect` | Watermarks and applies permission restrictions to PDFs before client delivery |

## Installation

```bash
# Install via Claude Code plugin manager, or run locally:
cc --plugin-dir /path/to/plugins/interior-design
```

## Python Dependencies

Install before using script-based skills:

```bash
pip install reportlab pypdf ezdxf openpyxl pymupdf fpdf2 vtracer
```

## Setup Notes

- `autocad-hatch-pat` uses the `show_widget` tool for interactive preview; falls back to a text table if unavailable.
- `image-to-dxf` requires `ezdxf` and optionally `vtracer` for automated tracing.
- `pdf-protect` requires `pypdf` and `reportlab`.
