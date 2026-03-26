# FF&E Attribute Schema

This document defines the 7 standard attribute fields embedded in every DXF block produced by
the image-to-dxf skill, plus the category code reference list.

---

## Attribute Fields

These become ATTDEF entities in the block definition and ATTRIB entities on the block insert.
They appear below the geometry in the drawing and can be extracted into schedules in AutoCAD.

| Tag            | Prompt (shown in CAD) | Format / Notes                                              |
|----------------|----------------------|-------------------------------------------------------------|
| PRODUCT_NAME   | Product Name         | Title case. Full product name as marketed. Max ~60 chars.   |
| MANUFACTURER   | Manufacturer         | Brand name as officially written (e.g., "Herman Miller").   |
| MODEL_NUMBER   | Model / SKU          | Exact SKU or model string. Use "N/A" if unknown.            |
| FINISH         | Finish / Material    | Material first, then color/finish (e.g., "Oak / Natural").  |
| DIMENSIONS     | Dimensions (W×D×H)   | Use × symbol. Include units (e.g., `24"W × 18"D × 36"H`).  |
|                |                      | For 2D items (rugs, art): `W × H`. Metric: `600W × 450D`.  |
| PRICE          | Unit Price           | With dollar sign and commas (e.g., `$1,200`). "TBD" if unknown. |
| CATEGORY_CODE  | Category Code        | From the Master Abbreviation List below (e.g., `FURN`).     |

### Formatting rules

**PRODUCT_NAME**: Capitalize each word. Don't include the manufacturer prefix (that's in
MANUFACTURER). Example: "Solis Pendant", not "Pablo Designs Solis Pendant".

**DIMENSIONS**: Always use the format `WW"W × DD"D × HH"H` for 3D items. For hanging fixtures
where depth isn't meaningful, use `WW"W × HH"H`. If the user provides metric, keep metric
(e.g., `600mm W × 450mm D × 900mm H`).

**PRICE**: Include the `$` symbol and use commas for thousands. If price is a range, use the
lower bound (e.g., `$800`). If truly unknown, use `TBD`.

**CATEGORY_CODE**: Use the code from the list below without a number suffix — the block name
includes the number (e.g., block name `FURN-1-SAARINEN-CHAIR`, category code `FURN`).

---

## Master Abbreviation List (Category Codes)

### Furniture
| Code  | Category                    | Examples                                     |
|-------|-----------------------------|----------------------------------------------|
| FURN  | Furniture (general)         | Chairs, tables, sofas, ottomans, benches     |
| SEATING | Seating                   | Use FURN for most cases                      |
| BED   | Beds & bedroom              | Beds, headboards, nightstands                |
| CASE  | Casegoods                   | Dressers, armoires, bookshelves              |
| DESK  | Desks & work surfaces       | Desks, credenzas, workstations               |

### Lighting
| Code  | Category                    | Examples                                     |
|-------|-----------------------------|----------------------------------------------|
| PF    | Pendant fixture             | Pendant lights, chandeliers                  |
| WF    | Wall fixture / sconce       | Wall sconces, picture lights                 |
| CF    | Ceiling fixture             | Flush mounts, semi-flush, recessed           |
| TL    | Table lamp                  | Table lamps, desk lamps                      |
| FL    | Floor lamp                  | Floor lamps, arc lamps, torchieres           |

### Plumbing & Fixtures
| Code  | Category                    | Examples                                     |
|-------|-----------------------------|----------------------------------------------|
| PL    | Plumbing fixture            | Sinks, toilets, tubs, showers               |
| FA    | Faucet                      | Kitchen faucets, bathroom faucets, pot fillers|
| HW    | Hardware                    | Cabinet pulls, knobs, hinges, towel bars     |

### Cabinetry & Millwork
| Code  | Category                    | Examples                                     |
|-------|-----------------------------|----------------------------------------------|
| CAB   | Cabinetry                   | Kitchen cabinets, vanities, built-ins        |
| MW    | Millwork                    | Shelving, wainscoting, crown molding         |

### Applied Finishes & Surfaces
| Code  | Category                    | Examples                                     |
|-------|-----------------------------|----------------------------------------------|
| CT    | Ceramic / porcelain tile    | Floor tile, wall tile, mosaic                |
| ST    | Stone                       | Marble, granite, quartzite countertops       |
| WD    | Wood flooring               | Hardwood, engineered wood, parquet           |
| VIN   | Vinyl / LVT                 | Luxury vinyl plank, sheet vinyl              |
| CAR   | Carpet                      | Broadloom, carpet tiles                      |
| WP    | Wallpaper / wall covering   | Wallpaper, grasscloth, fabric wall covering  |
| PNT   | Paint                       | Interior paint colors and sheens             |

### Textiles & Soft Goods
| Code  | Category                    | Examples                                     |
|-------|-----------------------------|----------------------------------------------|
| TX    | Textile / fabric            | Upholstery fabric, drapery fabric, trim      |
| RUG   | Area rug                    | Area rugs, runners, mats                     |
| WIN   | Window treatment            | Curtains, shades, blinds, shutters           |
| BED   | Bedding                     | Duvet covers, shams, throw pillows           |

### Appliances & Equipment
| Code  | Category                    | Examples                                     |
|-------|-----------------------------|----------------------------------------------|
| AP    | Appliance                   | Refrigerators, ranges, dishwashers           |
| AC    | AV / tech / equipment       | TVs, speakers, thermostats, outlets          |

### Accessories & Décor
| Code  | Category                    | Examples                                     |
|-------|-----------------------------|----------------------------------------------|
| ACC   | Decorative accessory        | Vases, sculptures, candles, trays            |
| ART   | Artwork                     | Framed prints, paintings, photographs        |
| MIR   | Mirror                      | Wall mirrors, floor mirrors                  |
| PLT   | Plant / greenery            | Indoor plants, planters, dried botanicals    |

### If uncertain:
Use the most specific code that fits. When in doubt between two categories, use the one that
corresponds to how the item would be sourced (e.g., a vanity mirror is `MIR`, not `PL`).

---

## Block Naming Convention

Block names follow this pattern:
```
{CATEGORY_CODE}-{NUMBER}-{PRODUCT-SLUG}
```

Examples:
- `PF-1-SOLIS-PENDANT` — first pendant fixture, Solis model
- `FURN-3-SAARINEN-WOMB-CHAIR` — third furniture item, Saarinen Womb Chair
- `FA-1-BRIZO-LITZE-FAUCET` — first faucet, Brizo Litze
- `CAB-2-SHAKER-UPPER-30` — second cabinetry item, 30" shaker upper cabinet

The number is typically the item's position in the room schedule. If no number is known, use `1`.

Slug rules: UPPERCASE, hyphens between words, no spaces or special characters.
