# Visualization Reference

## Widget Architecture

The visualization is a single HTML artifact with:
- **Left panel**: SVG tile pattern canvas (scales to fill available width)
- **Right/bottom panel**: Editable parameter inputs
- **Footer**: "Generate .pat File" button

Use inline JavaScript — no external libraries needed.

---

## Canvas Rendering

### Scale calculation
Pick a display scale so the full horizontal repeat fits comfortably in ~500px:

```javascript
const DISPLAY_SCALE = Math.min(500 / horizPeriod, 40); // px per inch, max 40
const canvasW = Math.round(horizPeriod * 3 * DISPLAY_SCALE);
const canvasH = Math.round(vertRepeat * 3 * DISPLAY_SCALE);
```

### Drawing order
1. Fill canvas background with grout color (`#c8c0b0` for typical stone grout)
2. For each row in the visible range:
   - Calculate x_shift = rowIndex × offset × horizPeriod
   - Draw each tile as a filled rect at the correct x, y position
   - Inset each tile by `grout/2 × DISPLAY_SCALE` from the grout grid lines
3. Repeat enough rows/columns to fill the canvas (tile seamlessly)

### Tile colors
- Single tile type: `#f5f0e8` (warm white / field tile)
- Two tile types: field = `#f5f0e8`, accent = `#d4cfc8` (slightly darker)
- Three+ tile types: use a stepped gray ramp

### Grout color
- Standard: `#c8c0b0`
- Dark grout option: `#4a4540`

---

## Parameter Panel

Always include these fields (pre-filled from the analyzed image):

```html
<div class="params">
  <label>Tile Width(s) <span class="hint">(inches)</span></label>
  <!-- For mixed tiles, one input per tile type in the row sequence -->
  <input type="number" id="fieldW" value="24" step="0.125" min="0.5">
  <input type="number" id="accentW" value="4" step="0.125" min="0.5">  <!-- if accent tile -->

  <label>Tile Height <span class="hint">(inches)</span></label>
  <input type="number" id="tileH" value="12" step="0.125" min="0.5">

  <label>Grout Joint <span class="hint">(inches)</span></label>
  <input type="number" id="grout" value="0.0625" step="0.0625" min="0.0625">

  <label>Row Offset</label>
  <select id="offset">
    <option value="0">None (stack bond)</option>
    <option value="0.5">1/2 running bond</option>
    <option value="0.333">1/3 offset</option>
    <option value="0.25">1/4 offset</option>
    <option value="custom">Custom...</option>
  </select>
  <input type="number" id="customOffset" value="0.333" step="0.001" min="0" max="1"
         style="display:none"> <!-- show when 'custom' selected -->

  <label>Pattern Name <span class="hint">(≤31 chars)</span></label>
  <input type="text" id="patName" value="TILE_24X12_ACCENT" maxlength="31">
</div>
```

Attach `input` event listeners to all fields to call `renderPattern()` on any change.

---

## Full Widget Template

```html
<style>
  body { font-family: var(--font-sans); background: transparent; }
  .container { display: flex; gap: 20px; flex-wrap: wrap; padding: 12px 0; }
  .canvas-wrap { flex: 1; min-width: 300px; }
  canvas { border: 1px solid var(--color-border-tertiary); border-radius: 6px;
           max-width: 100%; }
  .params { width: 220px; display: flex; flex-direction: column; gap: 8px; }
  .params label { font-size: 12px; color: var(--color-text-secondary);
                  margin-top: 4px; }
  .params input, .params select {
    border: 1px solid var(--color-border-secondary);
    border-radius: 4px; padding: 4px 8px; font-size: 13px;
    background: var(--color-background-secondary);
    color: var(--color-text-primary); width: 100%; box-sizing: border-box;
  }
  .hint { font-size: 10px; opacity: 0.6; }
  .generate-btn {
    margin-top: 12px; padding: 10px 0; background: var(--color-background-info);
    color: var(--color-text-info); border: 1px solid var(--color-border-info);
    border-radius: 6px; font-size: 14px; cursor: pointer; width: 100%;
  }
  .generate-btn:hover { opacity: 0.85; }
  .info-bar { font-size: 11px; color: var(--color-text-secondary);
              margin-top: 6px; }
</style>

<div class="container">
  <div class="canvas-wrap">
    <canvas id="patCanvas"></canvas>
    <div class="info-bar" id="infoBar"></div>
  </div>
  <div class="params">
    <!-- parameter inputs here -->
    <button class="generate-btn" onclick="sendPrompt('generate the pat file now')">
      Generate .pat File
    </button>
  </div>
</div>

<script>
const canvas = document.getElementById('patCanvas');
const ctx = canvas.getContext('2d');

function getParams() {
  return {
    fieldW:  parseFloat(document.getElementById('fieldW').value) || 24,
    accentW: parseFloat(document.getElementById('accentW')?.value) || 0,
    tileH:   parseFloat(document.getElementById('tileH').value) || 12,
    grout:   parseFloat(document.getElementById('grout').value) || 0.0625,
    offset:  getOffsetValue(),
    patName: document.getElementById('patName').value || 'TILE_PATTERN',
  };
}

function getOffsetValue() {
  const sel = document.getElementById('offset').value;
  if (sel === 'custom') return parseFloat(document.getElementById('customOffset').value);
  return parseFloat(sel);
}

function renderPattern() {
  const p = getParams();
  const rowH = p.tileH + p.grout;

  // Build tile sequence for one horizontal period
  // e.g. [accentW, fieldW] for mixed pattern; [fieldW] for single
  const tileSeq = p.accentW > 0 ? [p.accentW, p.fieldW] : [p.fieldW];
  const period = tileSeq.reduce((s, w) => s + w + p.grout, 0);

  const numRows = p.offset === 0 ? 1 : (p.offset === 0.5 ? 2 : 3);
  const vertRepeat = numRows * rowH;

  const SCALE = Math.min(480 / (period * 3), 36);
  const W = Math.round(period * 3 * SCALE);
  const H = Math.round(vertRepeat * 3 * SCALE);

  canvas.width = W;
  canvas.height = H;

  // Grout background
  ctx.fillStyle = '#c8c0b0';
  ctx.fillRect(0, 0, W, H);

  const tileColors = ['#f5f0e8', '#d4cfc8', '#e8e0d8'];

  // Draw tiles
  for (let row = -1; row < Math.ceil(H / (rowH * SCALE)) + 1; row++) {
    const xShift = (row * p.offset * period) % period;
    const y = row * rowH * SCALE;

    for (let col = -1; col < Math.ceil(W / (period * SCALE)) + 2; col++) {
      let xCursor = col * period * SCALE + xShift * SCALE;

      tileSeq.forEach((w, ti) => {
        const tx = xCursor + (p.grout / 2) * SCALE;
        const ty = y + (p.grout / 2) * SCALE;
        const tw = w * SCALE - p.grout * SCALE;
        const th = p.tileH * SCALE - p.grout * SCALE;
        ctx.fillStyle = tileColors[ti % tileColors.length];
        ctx.fillRect(tx, ty, tw, th);
        xCursor += (w + p.grout) * SCALE;
      });
    }
  }

  // Update info bar
  document.getElementById('infoBar').textContent =
    `Period: ${period.toFixed(4)}" × ${vertRepeat.toFixed(4)}" | ` +
    `Row height: ${rowH.toFixed(4)}" | Offset: ${(p.offset * 100).toFixed(1)}%`;
}

// Wire up all inputs
document.querySelectorAll('input, select').forEach(el => {
  el.addEventListener('input', () => {
    if (el.id === 'offset') {
      const show = el.value === 'custom';
      document.getElementById('customOffset').style.display = show ? 'block' : 'none';
    }
    renderPattern();
  });
});

renderPattern();
</script>
```

---

## Adapting for Different Pattern Types

### Single tile type (stack bond or running bond)
Remove the `accentW` input. `tileSeq = [fieldW]`.

### Three or more tile types per row
Add inputs for each tile width. `tileSeq = [w1, w2, w3, ...]`.

### Vertical orientation
Swap width/height roles in the canvas rendering and in the .pat math. Horizontal joints become 90° families and vertical joints become 0° families.

### Herringbone
Requires diagonal rendering (transforms on the canvas context). See `pat-math.md` for the math — herringbone is significantly more complex.

---

## UX Notes

- The canvas should feel instant — re-render on every keystroke
- If the canvas would be extremely large (>800px wide), add `overflow: hidden` and let the user scroll or reduce repeat count
- Show the period dimensions prominently — these confirm the math is right
- The "Generate" button should be prominent and visually distinct from the parameter fields
