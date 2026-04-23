# Changelog

## 0.2.0 — 2026-04-18

### Added
- **Mood Board PDF** (`moodboard-pdf`) — generates a landscape PDF with cover page, per-room mood board grid, and product spec pages from markdown product clippings
- **AutoCAD Hatch Pattern** (`autocad-hatch-pat`) — converts product photos or tile descriptions into AutoCAD-compatible `.pat` files with an interactive visual preview before file generation

### Changed
- **Schedule Creator** (`schedule-creator`) — upgraded to three-sheet output: Main Schedule, Materials & Finishes, and Room Finish Schedule (CAD/Revit-compatible)
- `marketplace.json` and `plugin.json` now include `version` and `repository` fields to support consumer update detection
- All skill `SKILL.md` frontmatters now include a `version` field

## 0.1.0 — 2026-03-01

### Added
- **Schedule Creator** (`schedule-creator`) — FF&E Excel schedule with codes, embedded images, dimensions, and links
- **Spec Sheet Annotator** (`spec-sheet-annotator`) — stamps schedule codes onto spec sheet PDFs, highlights critical specs, and merges into a single PDF
- **Image to DXF** (`image-to-dxf`) — converts product photos into DXF block files for AutoCAD
