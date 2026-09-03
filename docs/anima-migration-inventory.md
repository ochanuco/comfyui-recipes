# What the Illustrious checkpoint bought, and what is left holding the bill

An inventory taken while moving off `hassaku-il-v22` (Illustrious UNet) to the
Anima DiT checkpoints. Every constant in this recipe was arrived at by
rendering, and a large share of them were arrived at by rendering *on that
checkpoint*. This is the list of which ones, so the next session can tell a
design decision from a patch over a model's defect.

Three categories, and the useful question is different for each.

- **Patch over a checkpoint defect.** Delete it and re-measure. Keeping it
  costs weight in the prompt and may guard against something the new model
  never does.
- **Measured threshold.** The intent survives; the number does not. Re-measure
  before trusting it.
- **Identity.** The character, the costume, the pose. Unaffected.

The raw table, with the evidence trail for each row, is in
`.local/_inventory_raw.md`.

## Patches over a defect this checkpoint had

| where | what | what it was patching |
|---|---|---|
| `prompt_style.py` `NEGATIVE` | `(disembodied eye:1.4)` | Hassaku drew a ghost figure and clusters of eyes into the empty backdrop; nine other wordings failed first |
| `prompt_style.py` `NEGATIVE` | `(brown legwear:1.5)`, `brown thighhighs`, `brown pantyhose` | `(black thighhighs:1.3)` came out dark brown on Hassaku, and raising the weight did not fix it |
| `prompt_style.py` `NEGATIVE` | `(latex:1.45)`, `(rubber:1.45)`, `(leather legwear:1.45)` | asking for gloss crossed a material threshold on Hassaku and turned the fabric to leather |
| `prompt_style.py` `SURFACE` | `sticker` deliberately absent | the tag drew a sticker as an object, and a second chibi figure |
| `prompt_style.py` `EYE_BAN` | the four sparkle tags | a pass that skips `positive()` lets Hassaku's own detailed eyes walk in |
| `prompt_style.py` | the skirt / mismatched-legwear cluster | the model would not hold sock lengths apart, and a length guard deleted the garment |
| `costumes.py` `LEGWEAR_BAN` | six sock nouns | "the model reaches for these on its own" |
| `costumes.py` fitness | `(cameltoe:1.6)` | `(skin tight:1.45)` made the model draw the seam, so the seam had to be named |
| `poses.py` `_LIMB_TRIO` | weighted `extra arms/legs/limbs` | the unweighted `extra limbs` already in NEGATIVE measured inert |
| `poses.py` `kick`, `reach` | `(toes:1.55)` in `hires_negative` | six toes. **Already contradicted**: the delivery-side guard was turned off on 2026-09-02 because the Anima checkpoints draw five, and these two were not |
| `recipe.py` | the 1024-wide first pass, and `stand`/`ride` at 832 | a second figure appeared at 1280x1920 — the model leaving the sizes it was trained on |

## Numbers measured on that checkpoint

| where | what | why the number is suspect |
|---|---|---|
| `recipe.py` | `steps=30, cfg=5.0, dpmpp_2m, karras` | fixed as the one combination that suppressed the clone defect, and every `settled_seed` in the repo reproduces only under it |
| `recipe.py` | every `settled_seed` | a seed's meaning does not survive a change of sampler, let alone of architecture |
| `recipe.py` | `model_path="hassaku-il-v22"` | the migration itself: the recipe still builds a `DiffusersLoader` graph |
| `prompt_style.py` | `HIRES_DENOISE = 0.60` | a denoise response curve, which is a property of the sampler and the architecture |
| `delivery_style.py` | `FINALIZE_DENOISE = 0.55` | same, and the 0.45-is-too-clean finding it encodes was measured on Illustrious |
| `delivery_style.py` | `PALETTE_WINDOWS`, `REPIN_LIGHT/MID/DARK`, `ACCENT_RAMP`, `RECOLOR_TARGETS`, `RECOLOR_LEG_STOPS`, the skin-pin bounds | all of them are one render's measurements frozen as numbers — `tv639u` and `stand`, both Hassaku |
| `delivery_style.py` | `SAT_BAND`, `FIGURE_MIDTONE_V`, `FIGURE_SAT_*`, `FIGURE_LIGHT_*` | the acceptance gate, drawn around what that checkpoint's approved renders measured |

The palette group is not theoretical. Every Anima delivery this session
reported `accent kept 0.0%`: repin is reaching for a band that the new
checkpoint's renders do not put pixels in.

## What is not affected

`IDENTITY`, the `CHARACTER` costume text, the pose blocks, `BACKDROP`,
`STROKE` and the band geometry, `MATTE_MODEL`. These say what the picture is
of and what the delivered frame looks like. A different checkpoint draws them
differently; it does not make them wrong.

## The order to take them in

1. `poses.py`'s two `(toes:1.55)` bans, because they already contradict a
   decision this repo has taken. Nothing needs measuring; they are leftovers.
2. `recipe.py`'s loader, sampler and canvas, because until they move, the
   recipe cannot produce what this session has been delivering by hand.
3. The `delivery_style.py` colour group, because it is failing loudly and its
   basis render can be re-taken on the new checkpoint (`tv639u` is already
   ported: `hnmm43` raw, `yxwzc9` delivered).
4. The defect patches, one ablation each. They cost prompt weight and guard
   against defects that may no longer exist. `(disembodied eye:1.4)` and the
   brown-legwear trio are the cheapest to test and the most clearly named.
5. `settled_seed` everywhere, which cannot be carried over and has to be
   re-drawn rather than re-measured.
