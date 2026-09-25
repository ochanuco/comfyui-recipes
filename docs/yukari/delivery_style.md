# delivery_style

`src/comfyui_recipes/domain/yukari/delivery_style.py` holds what happens to a
render after the model: the delivery identity and the finalize defaults.
Every tool reads its values from there, and `scripts/delivery_check.py`
fingerprints them. The values live in the code; the reasons behind them are
in [`findings/delivery.md`](../findings/delivery.md).

## Constant groups

| Group | Read by |
|---|---|
| `BACKDROP`, `STROKE`, `WHITE_WIDTH_PCT`, `STROKE_WIDTH_*` | band drawing in `infrastructure/imaging/delivery.py` |
| `STROKE_CUT_EPS_PCT`, `STROKE_EDGE_SMOOTH` | `band_alphas`: hand-cut outline and edge rounding |
| `STROKE_LIGHT_*`, `STROKE_LIGHTS` | the `stroke_light` finalize option |
| `STRIPES_*`, `WAVEFORM_*`, `EARS_*`, `BACKDROP_*` | named backdrops in `infrastructure/imaging/backdrops.py` |
| `SAT_BAND`, `BG_SAT_MAX`, `FIGURE_SAT_*`, `BACKDROP_SPREAD_MAX` | `measure`/`verdict` in `palette.py`: the gate at ingest and in `palette_check.py` |
| `FIGURE_LIGHT_*`, `PALETTE_WINDOWS`, `REPIN_*` | `repin` in `infrastructure/imaging/palette.py` |
| `RECOLOR_*` | `--recolor` in `infrastructure/imaging/recolor.py` |
| `MATTE_*`, `KEY_*`, `ENCLOSED_*`, `FRAME_LINE_*` | matte, keyed edge and pocket cuts in `delivery.py` |
| `FINALIZE_*`, `ROUGH_STYLE`, `FINALIZE_DEFAULTS` | finalize: the opt-in IL redraw and the catalog's defaults |

## Contracts

- The delivered backdrop is always `BACKDROP`, repainted after the render.
  The render's own backdrop is not stable enough to keep.
- Stroke width is the larger of a share of the white band and a share of the
  canvas. The canvas share is a floor.
- `STROKE_CUT_EPS_PCT = 0` reproduces the smooth ramp exactly, and
  `band_alphas` branches on it. The epsilon stays well under
  `WHITE_WIDTH_PCT`. With `stroke_light`, the purple band is shaded first and
  then simplified. The white band is never shaded.
- `STROKE_EDGE_SMOOTH` counts 2x-supersample pixels, not band widths.
- A palette gate pass is not an approval; a FAIL never goes forward.
  `FIGURE_SAT_*` measures only pixels at V ≥ `FIGURE_MIDTONE_V`, so black
  tights and coat are exempt.
- The repin factor is at most 1.0, so a pale render is never pushed up.
  Palette windows do not overlap. The dark band greys every hue except
  `REPIN_DARK_EXEMPT`.
- The matte is cut from the raw render, never from repinned colour.
- Only the outermost `KEY_EDGE_RING_PX` of the figure is soft. Despill runs
  on the rim only, and only when the corner key's dominant channel clears the
  others by `KEY_DESPILL_MIN_EXCESS`.
- `enclosed_cut` runs only on a green key. When the corners are not green (a
  drawn frame line), the key comes from the figure's own green pixels once
  there are `ENCLOSED_POCKET_MIN_AREA` of them. The backdrop is then painted
  only inside the frame, and the frame line stays figure.
