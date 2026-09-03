"""Yukari's delivery policy: what happens to a render after the model.

The prompt cannot hold these values -- the backdrop is not prompt-stable and
the purple marker is a post-process -- but they are identity all the same,
applied by the delivery tools instead of the graph. Every tool reads its
default from here, so the value a delivered picture actually wears has one
source. Changing a value here changes every picture delivered after it --
`costume_check.py` fingerprints this file alongside the prompt blocks for
that reason.

The calibration measurements behind each number are in
docs/yukari/delivery_style.md.
"""

# The backdrop every delivered picture is set to. The render's own backdrop
# is unstable under any perturbation, so the delivered colour is set after
# the fact by recolor_bg.repaint, always to this. recolor_bg itself stays
# general (its --color is required, not defaulted): the identity belongs to
# the delivery, not to the tool.
BACKDROP = "#c7e5e9"

# The white band drawn directly against the figure's die-cut edge, as a
# share of the longest side. Both this and the purple band outside it are
# computed by the delivery, not carried by the prompt.
WHITE_WIDTH_PCT = 1.3

# The purple marker drawn outside the white band, at Yukari's own hue,
# deliberately darker than the hair accent.
STROKE = "#6a3494"
# Width as a share of the white band's own width, both computed together.
STROKE_WIDTH_BAND = 0.80
# The acceptance band, from measured approved work. A pass is not approval
# -- the human still judges -- but a FAIL never goes forward. The frame mean
# moves with the figure's share of the canvas, so the upper bound is only an
# explosion detector; the composition-independent guard is the FIGURE_SAT
# pair below.
SAT_BAND = (30.0, 95.0)
BG_SAT_MAX = 60.0

# The figure's own saturation, measured where colour is actually visible:
# non-backdrop pixels at V >= FIGURE_MIDTONE_V. The V floor is the
# tights-exempt rule made mechanical -- the black tights and coat sit below
# it, so deep black stays exempt while the midtones carry the
# high-saturation guard. The bands split the picked arms from the rejected
# gradient renders with margin on the picked side.
FIGURE_MIDTONE_V = 80
FIGURE_SAT_MEAN_MAX = 95.0
FIGURE_SAT_P90_MAX = 230.0

# Saturation normalization, applied to the raw render (scripts/desat.py, HSV
# S alone) before the layered delivery. Poses drift by different amounts and
# no prompt lever moves it, so the delivery normalizes instead of holding a
# per-pose factor table: measure the figure's LIGHT band (the pale dress and
# hair, V >= FIGURE_LIGHT_V), scale saturation by target/measured, clamped
# to at most 1.0 so a pale render is never pushed up. The target is stand's
# own measured light band -- stand IS the palette reference.
FIGURE_LIGHT_V = 150
FIGURE_LIGHT_SAT_TARGET = 28.0

# The palette proper: per-material colour targets, applied by scripts/repin.py
# (V untouched -- the brushwork is the render's own; hue and saturation are
# the delivery's). Values are stand's measurement frozen as numbers, and each
# window's saturation target is per V band (light >= FIGURE_LIGHT_V / mid
# below), blended continuously so no band boundary shows. Chosen over the
# uniform S scale because the materials drift by different amounts, which one
# global factor can only average.
PALETTE_WINDOWS = (
    {"name": "purple", "hue": (170.0, 225.0), "hue_target": 191.0,
     "sat_light": 50.4, "sat_mid": 45.1},
    {"name": "skin", "hue": (0.0, 48.0), "hue_target": 17.8,
     "sat_light": 45.0, "sat_mid": 75.0},
)

# Where the skin is. The 2048 redraw re-decides it and lands it in the
# purple window, so the region cannot be read off the redraw -- it is read
# off the render the redraw was made from, which still has the skin the base
# drew. The window's hue is the reference stand's measured skin; its
# saturations are pin targets above that reference, and the pin only ever
# raises saturation -- pinning down washed the lips out with the cheek.
SKIN_SOURCE_S_MIN = 20.0
# The lips are warm and sit inside the skin window, so the hue pin turns
# them orange unless the field is separated from the accent. The cheek
# measures S 25-29 and the lips above 80; the ceiling splits them.
SKIN_SOURCE_S_MAX = 60.0
SKIN_SOURCE_V_MIN = 110.0
SKIN_PIN_BLEND = 1.0
# Below this share of the frame the base did not draw skin, it drew the
# hair's lavender over the face. The fragments left in the mask are
# speckle, and pinning them puts cream blotches on a lavender cheek --
# worse than leaving the face alone. The delivery does not invent skin.
SKIN_PIN_MIN_SHARE = 0.08
# One coherent field, not the warm grain along every line.
SKIN_PIN_MIN_AREA = 4096

# repin's compression curve, per V band: (knee, ratio). Saturation below the
# knee is untouched; only the excess is kept, at the ratio. A single factor
# per band was rejected twice by eye: tuned for the vivid skirt it crushed
# the hair to white, and the near-black hoodie carries saturation up to 180
# that the old V floor exempted. Knees are tv639u's own band measurements --
# the picked reference for the whole palette. The dark band applies on every
# hue except warm skin shadows (REPIN_WARM_EXEMPT).
REPIN_LIGHT = (28.0, 0.25)   # V >= FIGURE_LIGHT_V
REPIN_MID = (60.0, 0.15)     # midtones inside the purple window
REPIN_DARK = (29.0, 0.08)    # V < 80, any hue
REPIN_WARM_EXEMPT = (0.0, 48.0)

# Accents -- the iris and the hair pins -- sit far above any field's
# saturation (iris ~211 vs skirt ~130), so a ramp over this S range lets
# them keep ACCENT_KEEP of their excess and their own hue while the fields
# pin pale. Without it the eyes wash out to white.
ACCENT_RAMP = (150.0, 60.0)  # start, width
ACCENT_KEEP = 0.65
# Saturation alone does not identify an accent. Some renders carry the black
# hoodie and tights at saturation 250 in the dark band, and the S ramp then
# reads the whole garment as an iris and preserves it -- the picture ships
# with a navy hoodie and purple tights. An accent is bright as well as
# saturated, so the ramp is gated on value at the same floor that defines
# the dark band, and the dark band never claims accent protection.
ACCENT_VALUE_RAMP = (FIGURE_MIDTONE_V, 40.0)  # start, width

# The backdrop flatness screen, on the RAW render's corner brightness spread.
# A gradient backdrop starves the flood mask palette.py measures through, so
# every figure number it reports is against a backdrop leak. Measured flat
# renders sit under 10 and gradient failures at 40+, so the bound splits them
# mid-gap. It screens the numbers, not the delivery: the cut-out comes from
# the matte and does not care what the backdrop does.
BACKDROP_SPREAD_MAX = 25.0

# The worker-side model that cuts the figure out. The silhouette has to come
# from something other than colour, because repin moves the figure's colours
# into the backdrop's tolerance before the delivery ever sees them.
MATTE_MODEL = "birefnet.safetensors"
# The band either side of the matte's edge, as a share of the longest side,
# inside which a pixel is figure when it differs from the backdrop by more
# than MATTE_EDGE_TOLERANCE on any channel.
MATTE_EDGE_BAND_PCT = 0.6
MATTE_EDGE_TOLERANCE = 20

# finalize's masked refine, the denoise a 2048 print's touch-up runs at.
FINALIZE_DENOISE = 0.45

# The delivery redraw's own sampler (sampler_name, scheduler).
FINALIZE_SAMPLER = ("euler", "normal")

# Lineart-preserving recolour (infrastructure/imaging/recolor.py). Where
# repin nudges the render's own saturation, recolor asserts a material's
# colour outright and can therefore fix value too -- a washed-out black that
# repin leaves alone by design. Everything below is measured from tv639u.

# A line pixel is darker than its own neighbourhood, not merely dark, so a
# flat dark fill is never mistaken for linework; and darkness is the
# brightest channel, so a magenta stroke does not qualify however dark it
# reads. The bound keeps 99 percent of the reference's own line.
RECOLOR_LINE_MAX = 140
RECOLOR_LINE_RELIEF = 40
RECOLOR_LINE_WINDOW = 7

# Per-material HSV targets, PIL's 0-255 scale, tv639u's own measured fills.
RECOLOR_TARGETS = {
    "hair":   (188, 15, 234),
    "hoodie": (221, 23, 64),
    "dress":  (185, 34, 209),
    "skin":   (16, 27, 249),
    "white":  (0, 0, 255),
}

# How much of a region's own value survives the repaint, against the target
# V, so the render's own shading still reads under the asserted colour.
RECOLOR_KEEP_V = {
    "hoodie": 0.8, "hair": 0.6, "dress": 0.6,
    "skin": 0.5, "white": 0.5, "tights": 0.45,
}

# The same for hue and saturation, and it is not optional: pinning a region
# to one hue and one saturation flattens the drawing. This render's shading
# lives there rather than in value -- the purple strokes through the hair,
# the blush on the cheek -- and asserting the target alone turned the hair,
# the face and the dress into one grey mass with no edge between them. The
# target moves the material; the deviation around it stays the render's.
RECOLOR_KEEP_HS = 0.7

# Kept deviation is bounded, or the magenta strokes some renders draw over
# the hands and the face come through: they are correctly not line, so they
# ride along inside the skin, and enough of their own saturation survives to
# still read hot pink. Hue is bounded on both sides for the same reason --
# keeping most of a magenta stroke's hue does not make it skin, it makes it
# teal. A blush and a hair stroke sit inside these bounds; a stroke that
# does not is pulled onto its material's colour.
RECOLOR_S_CEILING = 50
RECOLOR_H_SPREAD = 20

# Legwear does not take one target: it is painted from this gradient,
# interpolated per pixel row against height share so the purple comes up
# the leg the same way regardless of how tall the labelled region is --
# neutral black through the knee, the purple only showing near the foot.
RECOLOR_LEG_STOPS = (
    (0.72, (219, 23, 64)),
    (0.82, (0, 6, 32)),
    (0.90, (212, 69, 57)),
    (1.00, (229, 117, 129)),
)
# Below this height (as a share of the figure's own bounding box, not the
# canvas) a dark fill is legwear; above it, the same darkness is the hoodie.
RECOLOR_LEG_CY = 0.72
# Value cannot find the legs on a washed-out render -- one measured pair put
# them at 239 and 255, brighter than the dress -- so a fill this large sitting
# below RECOLOR_LEG_CY is legwear whatever its value. The share separates the
# leg masses, which run from 8 percent of the figure upward, from the hands
# and the stray hair that also fall that low at under 2.
RECOLOR_LEG_MIN_AREA = 0.05

# classify's remaining thresholds. A fill this saturated is an accent --
# the iris, a hair pin -- and keeps its own colour rather than a target.
# Outside this hue window a fill reads as skin regardless of saturation.
# Below RECOLOR_WHITE_S at high value it is a frill; below RECOLOR_HAIR_S
# it is hair; otherwise it is the dress. Below RECOLOR_DARK_V a fill is a
# dark garment, split into hoodie or tights by RECOLOR_LEG_CY above.
RECOLOR_ACCENT_S = 150
# Saturation alone keeps the wrong things. Some renders draw the interior
# detail -- the creases between fingers, the mouth, the collarbone -- as thin
# magenta strokes rather than dark line, and those strokes are saturated
# enough to be held back as accents, so a corrected picture still ships with
# hot pink fingers. A real accent is thick as well as saturated: the iris and
# the hair pins survive this many erosions where a stroke a few pixels wide
# does not, and a stroke that fails takes the colour of whatever surrounds it.
RECOLOR_ACCENT_ERODE = 3
RECOLOR_SKIN_HUE = (48, 240)
RECOLOR_WHITE_S = 8
RECOLOR_HAIR_S = 45
RECOLOR_DARK_V = 120
