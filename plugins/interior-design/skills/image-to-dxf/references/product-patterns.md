# Product Geometry Patterns

Common geometry breakdowns for interior design products. Use these as starting points when
analyzing a product image — adapt based on what you actually see.

In all patterns below, assume the coordinate origin (0, 0) is at the **bottom-left** of the
bounding box, with X going right (width) and Y going up (height). W = product width, H = product height.

---

## Seating (FURN)

### Side Chair / Dining Chair (Front Elevation)
```
Zones: seat, back, two front legs, two back legs (hidden or visible), stretchers
Typical entities:
  - Seat: lwpolyline rect, e.g. [(1, 17), (W-1, 17), (W-1, 20), (1, 20)], layer 0-OUTLINE
  - Back: lwpolyline from seat top to chair top, e.g. [(4, 20), (W-4, 20), (W-3, H), (3, H)]
  - Front legs: two vertical rects, ~1–2" wide, from floor to seat bottom
    e.g. [(1, 0), (3, 0), (3, 17), (1, 17)] and mirror on right
  - Back legs: often angled, e.g. [(4, 0), (5.5, 0), (W-3, H), (W-4.5, H)] (tapered lwpolyline)
  - Centerline: line from (W/2, 0) to (W/2, H), layer 0-CENTERLINE
Note: Apply bilateral symmetry — draw one leg accurately, mirror for the other.
```

### Lounge Chair / Armchair (Front Elevation)
```
Same as dining chair but add:
  - Arms: horizontal elements at armrest height, extending ~3-4" beyond seat width on each side
  - Seat is typically deeper and lower
  - Cushion division line on seat and back (lwpolyline or line, layer 0-DETAIL)
```

### Sofa (Front Elevation)
```
Zones: seat platform, back, two arms, legs (4–6), seat/back cushion divisions
  - Overall frame: outer lwpolyline rect
  - Arms: raised sections at each end, typically ~8" wide × full back height
  - Seat cushion divisions: vertical lines dividing seat into 2–3 sections
  - Back cushion divisions: corresponding vertical lines on back
  - Legs: small rects at floor level, typically 4 visible from front
```

### Stool / Counter Stool (Front Elevation)
```
  - Seat: circle or rect at top (depends on seat shape)
  - Column/stem: vertical rect or tapered lwpolyline below seat center
  - Base: wider rect or circular footprint at floor level
  - Footrest: horizontal line at mid-height if present
```

---

## Tables (FURN)

### Dining Table (Plan View — most useful for tables)
```
In plan: show top surface + leg positions
  - Top: rect or oval (use lwpolyline approximation for oval with many points)
  - Legs: four small circles or rects at corners, typically 3–4" inset from edges
  - Centerlines optional
```

### Dining Table (Front Elevation)
```
  - Tabletop: thin horizontal rect, full width × ~1" thick
  - Apron: rect below top, typically inset ~2" from each end
  - Legs: two visible from front, rectangular, from floor to apron underside
```

### Coffee Table (Plan View)
```
  - Top: rect or rounded rect
  - Shelf (if present): smaller rect centered below, in 0-DETAIL layer
  - Legs: small rects or circles at corners
```

---

## Pendant Lighting (PF)

### Globe / Sphere Pendant (Front Elevation)
```
  - Canopy: small rect or semicircle at top, e.g. 4" wide × 1" tall
  - Cord/rod: vertical line from canopy center to shade top
  - Shade (sphere): circle centered on cord bottom
  - Socket/hardware: small rect inside sphere top (0-DETAIL)
```

### Drum Shade Pendant (Front Elevation)
```
  - Canopy: small rect at top
  - Cord: vertical line
  - Shade: trapezoid (top narrower or equal) — lwpolyline
  - Interior diffuser: optional horizontal line at shade midpoint, 0-DETAIL
```

### Linear / Bar Pendant (Front Elevation)
```
  - Canopy or two canopies: small rects at top
  - Rods: two vertical lines hanging down
  - Bar: horizontal rect connecting rod bottoms
  - Shade or lens: rect below bar (0-DETAIL)
```

### Chandelier (Front Elevation)
```
  - Ceiling canopy: rect at top
  - Central stem: vertical line
  - Arms: radiating lines from stem at various heights (typically symmetric)
  - Shades/bobeches: small shapes at each arm end
  - Use 0-OUTLINE for overall silhouette, 0-DETAIL for arms and shades
```

---

## Wall Sconces (WF)

### Arm Sconce (Front Elevation)
```
  - Backplate: small rect against imaginary wall at left edge
  - Arm: horizontal or angled line extending right from backplate
  - Shade: shape at arm end (cone, drum, globe)
  - Hinge/socket: small detail at backplate-arm junction
```

---

## Plumbing & Faucets (PL / FA)

### Single-Handle Basin Faucet (Front Elevation)
```
  - Base/escutcheon: rect at bottom, ~4" wide × 1" tall
  - Body/spout: vertical rect from base rising then curving over
    (use lwpolyline for the arc at top of spout)
  - Aerator: small circle at spout tip
  - Handle: separate rect or oval to the side of body, 0-DETAIL
  - Lever handle: horizontal rect at top of handle stem
```

### Undermount Sink (Plan View — most useful)
```
  - Outer edge (mounting cutout): rounded rect
  - Basin interior: rounded rect slightly smaller, 0-DETAIL
  - Drain: small circle centered in basin, 0-DETAIL
  - For double bowl: two basins side by side
```

### Freestanding Bathtub (Front Elevation)
```
  - Main body: wide horizontal oval or rect with rounded ends (lwpolyline)
  - Interior basin: smaller oval/rect inside, 0-DETAIL
  - Feet: 4 small rects below body, 0-DETAIL
  - Overflow/drain: small circle on tub face, 0-DETAIL
  - Rim: thin horizontal rect at top of body
```

---

## Cabinetry (CAB)

### Upper Cabinet (Front Elevation)
```
  - Cabinet box: outer rect
  - Door reveal: inner rect inset ~3/4" from edges, 0-DETAIL
  - Door gap: thin vertical line at center for two-door cabinets, 0-DETAIL
  - Hinge marks: two small rects on door stile (optional), 0-DETAIL
  - Pulls: small horizontal rect centered on each door face, 0-DETAIL
```

### Base Cabinet with Drawer (Front Elevation)
```
  - Cabinet box: outer rect, floor to counter height
  - Drawer bank or door(s): inset rect(s), 0-DETAIL
  - Toe kick: rect at bottom ~3.5" tall × full width, 0-OUTLINE
  - Counter: thin rect at top of cabinet, 0-OUTLINE
  - Pulls: small horizontal rects, 0-DETAIL
```

---

## Appliances (AP)

### Range / Stove (Front Elevation)
```
  - Body: large outer rect
  - Door (oven): rect in lower portion, inset slightly
  - Door handle: horizontal rect across door, 0-DETAIL
  - Control panel: rect across top or on backsplash
  - Burner knobs: 4–6 small circles in a row, 0-DETAIL
```

### Range Hood (Front Elevation)
```
  - Hood body: trapezoid (wider at bottom, narrowing toward ceiling), lwpolyline
  - Filter area: rect in center of hood face, 0-DETAIL
  - Controls: small rects at front edge, 0-DETAIL
```

---

## Mirrors (MIR)

### Rectangular Wall Mirror (Front Elevation)
```
  - Frame outer edge: outer rect, 0-OUTLINE
  - Frame inner edge: inner rect (frame width ~1–3"), 0-OUTLINE
  - Mirror glass: rect (fill of frame interior implied by inner rect), 0-DETAIL
  - Hanging hardware: small rect or circle at top center back, 0-DETAIL (optional)
```

### Round Mirror (Front Elevation)
```
  - Frame: circle (outer diameter), 0-OUTLINE
  - Glass: circle (inner diameter = outer minus 2x frame width), 0-DETAIL
```

---

## General Tips

**When the product has no right angles:**
Use lwpolyline with enough points to approximate the curve smoothly. For a gentle curve, 6–10
points is usually sufficient. For a tight curve, use an arc entity instead.

**When you can't determine a dimension:**
Estimate proportionally from the image. A chair seat is typically 17–18" from floor. A dining
table is typically 30" tall. Use these as sanity checks even when dimensions are provided.

**When the product has repeating elements (e.g., legs, pickets, slats):**
Draw one instance accurately, then describe the pattern (e.g., "3 slats spaced 4" apart starting
at x=2"). `build_block.py` accepts repeated elements in the entities array — just list each one.

**When product is shown at an angle:**
Choose the front elevation interpretation. A slightly angled product photo should be drawn as
if viewed straight-on. Use the proportions visible in the photo as your guide.
