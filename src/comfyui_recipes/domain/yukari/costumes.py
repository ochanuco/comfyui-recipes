"""The wardrobe: who she is, and the four sets of clothes hung on it.

A costume owns three blocks -- character, legwear, hood -- and its own staged
negative edits below. Everything else (FACE, SURFACE, BODY, THIN, every pose,
the rest of the negative) is shared: what changes between costumes is the
clothes, not her and not the drawing.
"""

from __future__ import annotations

from .models import S_BARE_LEGS, S_FABRIC, S_KNOT, S_MIDRIFF, S_SEAM, S_TINT_RELEASE, Edit

# Who she is, as against what she is wearing -- the half every costume keeps.
# The split out of CHARACTER moved no text and no token order;
# costume_check.py's fingerprint is the proof. `hair ornament` is weighted
# because an unweighted tag in a prompt this crowded is indistinguishable
# from an absent one -- her clips kept vanishing until it was.
IDENTITY = (
    "yuzuki yukari, (light purple hair:1.25), (short hair with long locks:1.45), "
    "(very long sidelocks:1.3), sidelocks, (purple eyes:1.25), hair between eyes, "
    "(hair ornament:1.4), "
)

CHARACTER = IDENTITY + (
    # The hem answers only to the garment NOUN -- no weight, guard or
    # body-block change ever moved it; the cardigan measures longest of the
    # hooded family. Tags naming the garment's FIT fail (they loosen the
    # drawing, not the cloth); tags naming a PART's state pass -- the sleeve
    # pair below is what boxes the body out and drops the hem.
    "(black hooded cardigan:1.45), open cardigan, (rabbit hood:1.55), "
    # The dress hem does not respond to length tags -- the costume likely
    # comes from `yuzuki yukari` itself, so a length tag argues with the
    # character prior and loses; lengthening it needs a different garment
    # noun or inpainting. `(purple dress:1.45)` is weighted because lower it
    # is drawn as a two-piece (skirt plus separate frill). `drawstring` --
    # the coat's cord with the pink bead -- must stay weighted or it is not
    # drawn. The dress's halter fastening is NOT here: globally it pulls the
    # coat off her shoulders; `positive` adds it for the pose that sees it.
    "animal hood, long sleeves, (drawstring:1.4), (purple dress:1.45), short dress, "
    # The frilled collar, ribbon ties and beaded cords. Below 1.0 in a prompt
    # where everything else is 1.3+ has meant ABSENT every time it was tried;
    # 1.25 is the floor that draws them without touching the backdrop. A
    # COSTUME value, therefore every pose.
    "(frills:1.25), vocaloid, voiceroid, "
    # The oversized silhouette: boxy body, hem at the hip. Neither tag works
    # alone -- each destroys the stroke on its own; together at 1.3 each the
    # stroke holds and the lower back is covered. They hold each other in
    # place: do not drop one.
    # `past wrists`, not `past fingers`: fingers-length sleeves bury the
    # hands and they are drawn as lumps; letting the hands out draws real
    # fingers. Weighting the hand guards instead did nothing -- the fix was
    # removing what hid them, not forbidding the failure.
    "(oversized shirt:1.3), (sleeves past wrists:1.3)"
)

# rabbit print is deliberately absent: paired with `sticker` it drew a rabbit
# decal on her cheek in the 1024x1024 portrait. `sticker` earns its place --
# it is half of the white-outline idiom -- so the print is the one that goes.

# Hood down at 1.25 -- the picked render's value. The pinned alternative
# measured no better in either direction.
HOOD = "(hood down:1.25), (visible hair:1.2), (purple eyes:1.2)"

# RETIRED, kept because scripts/yukari_recipe.py still re-exports it: the
# pale-socks-over-tights layering the one-garment LEGWEAR below replaced.
# Its history is in docs/yukari/costumes.md; read that before proposing two
# garments on the leg again.
LEGWEAR_LAYERED = (
    "(grey pantyhose:1.45), pantyhose, (opaque pantyhose:1.3), "
    "(very pale purple thighhighs:1.5), (white thighhighs:1.2), "
    "(lavender tint:1.3), "
    "(thighhighs over pantyhose:1.55)"
)

# ONE garment on the leg, and it is the pantyhose -- the official V6 sheet
# draws one. Layering was abandoned, not deferred: seen from behind,
# whichever layer covers the buttock ends in a hem, and the model can only
# put that boundary on the thigh.

# The gradient runs purple at the thigh to black at the ankle; no directional
# tag exists, so the top colour is named and black falls to the rest, with
# black first at 1.5 as the garment's stated colour. FOUR tags where a
# garment block tolerates three: if the coat grows or the dress loses its
# frills, suspect the fourth tag first. The purple end cannot be desaturated
# from the prompt (the pale dress and hair imply it); take it off afterwards
# with `.local/desat.py`.
LEGWEAR = ("(black pantyhose:1.5), (pale purple pantyhose:1.35), "
           "(gradient legwear:1.4), (opaque pantyhose:1.4)")

# The second garment banned by name -- the model reaches for these on its
# own. Six guards is allowed here because each names a DISTINCT garment;
# palette damage comes from stacking guards that all point at ONE defect.
LEGWEAR_BAN = (
    "(thighhighs:1.5), (kneehighs:1.5), (socks:1.45), (over-kneehighs:1.45), "
    "(two-tone legwear:1.4), (legwear hem:1.3)"
)

# THE SECOND COSTUME: grey oversized tee, denim shorts, plain black tights,
# white high-tops -- another set of garments hung on the same IDENTITY,
# reached with `--costume sporty`; the original stays one flag away. It keeps
# three settled decisions: IDENTITY whole, ONE garment on the leg, and shoes
# named in the costume rather than in a pose (see `pose_block`).
SPORTY = IDENTITY + (
    "(grey shirt:1.45), (t-shirt:1.45), (oversized shirt:1.4), short sleeves, "
    "(denim shorts:1.45), (short shorts:1.25), "
    "vocaloid, voiceroid, "
    "(white footwear:1.4), (sneakers:1.45), (high tops:1.3)"
)

# One garment on the leg, exactly as LEGWEAR is -- this one is plain.
# LEGWEAR_BAN still applies: the reference runs the tights straight into the
# shoe, so the guards keeping a second garment off are as load-bearing here.
SPORTY_LEGWEAR = "(black pantyhose:1.5), (opaque pantyhose:1.4)"

# HOOD minus the hood. `(hood down:1.25)` is an instruction about a garment
# this costume does not have, and naming an absent garment is how it gets
# drawn.
SPORTY_HOOD = "(visible hair:1.2), (purple eyes:1.2)"

# The third costume: a gym kit. `light purple` is IDENTITY's own spelling for
# the shade, borrowed rather than invented, and one colour tag in one slot.
# `(high-waist pants:1.4)` sits here and not in the legwear block on purpose:
# it is the waistband, a thing the SHIRT sits on -- without it the oversized
# tee hangs to mid-thigh and swallows whatever is under it.
FITNESS = IDENTITY + (
    # Plain jersey, deliberately not ribbed: a ribbed knit falls against the
    # body, so it reads as a sweater dress when long and a tucked shirt when
    # short, and the hem can never settle between those readings.
    "(light purple shirt:1.45), (t-shirt:1.45), "
    # 1.55 is the weight at which the hem clears the crotch -- this is the
    # tag that decides where the hem lands, and the hem is what covers her.
    "(oversized shirt:1.55), short sleeves, "
    "(high-waist pants:1.4), (sportswear:1.35), "
    "vocaloid, voiceroid, "
    "(white footwear:1.4), (sneakers:1.45), (high tops:1.3)"
)

# Still ONE garment on the leg, and here the garment is the trousers:
# ankle-length compression leggings ARE the legwear. The stripe tag pins the
# side stripe's PRESENCE (unnamed, the model rarely draws it); its COLOUR is
# not pinned and nothing here pretends otherwise. The tag names clothes, not
# trousers, so it needs the striped-shirt guard in `negative()`.
FITNESS_LEGWEAR = ("(leggings:1.45), (black leggings:1.4), (skin tight:1.45), "
                   "(vertical-striped clothes:1.35)")

# No hood here either, for SPORTY_HOOD's reason.
FITNESS_HOOD = "(visible hair:1.2), (purple eyes:1.2)"

# The fourth costume, and the only one that keeps the settled costume's coat:
# summer, air-conditioned room, off-duty -- the cardigan is on her because
# the room is cold. It carries CHARACTER's cardigan/hood/sleeve text VERBATIM
# rather than a respelling, which is what would let a later session widen a
# `dressed`-gated splice onto this costume: the needle would be there to
# match. Under it: a white oversized tee and dolphin shorts. No footwear tag
# -- this costume is barefoot, not shod.
ROOMWEAR = IDENTITY + (
    "(black hooded cardigan:1.45), open cardigan, (rabbit hood:1.55), "
    "animal hood, long sleeves, (drawstring:1.4), "
    "(white shirt:1.4), (t-shirt:1.45), (oversized shirt:1.3), "
    "(dolphin shorts:1.4), (short shorts:1.25), "
    "vocaloid, voiceroid, "
    "(sleeves past wrists:1.3)"
)

# One garment on the leg, LEGWEAR's rule -- here the garment is none.
# LEGWEAR_BAN still bans the second garment by name (socks, thighhighs), and
# `negative()` separately bans the settled costume's own pantyhose by name:
# that costume WEARS one, so the shared negative leaves the plain colour
# unbanned, and this costume does not wear it at all.
ROOMWEAR_LEGWEAR = "(bare legs:1.45), (barefoot:1.35)"

# HOOD, unchanged and reused rather than respelled: the cardigan is here and
# open, so `(hood down:1.25)` names a garment this costume actually has --
# unlike SPORTY_HOOD/FITNESS_HOOD, which drop the line because those two
# costumes have no hood to be down.
ROOMWEAR_HOOD = HOOD

# The costumes that bring shoes of their own. Three gates below are about
# footwear and NONE of them is about being `sporty` -- an equality test on
# one costume name is exactly the kind of gate a third costume walks past in
# silence, and the failure is quiet: two pairs of shoes on `stand`, a sneaker
# floating in a head framing's backdrop.
SHOD = ("sporty", "fitness")

# The three blocks a costume owns. Everything else -- FACE, SURFACE, BODY,
# THIN, every pose and the whole negative -- is shared, which is the claim
# this split is making: what changes between costumes is the clothes.
COSTUMES = {
    "default": {"character": CHARACTER, "legwear": LEGWEAR, "hood": HOOD},
    "sporty": {"character": SPORTY, "legwear": SPORTY_LEGWEAR, "hood": SPORTY_HOOD},
    "fitness": {"character": FITNESS, "legwear": FITNESS_LEGWEAR,
                "hood": FITNESS_HOOD},
    "roomwear": {"character": ROOMWEAR, "legwear": ROOMWEAR_LEGWEAR,
                 "hood": ROOMWEAR_HOOD},
}

# What each costume does to the negative, in the slots the picked renders were
# drawn in. The rule that put most of these here: a tag that names how cloth
# behaves (skin tight, vertical stripes) goes wherever there is fabric, so it
# needs a guard on every garment it was not meant for -- and that guard
# belongs to the WARDROBE, not to whichever pose first needed it.
COSTUME_NEGATIVE_EDITS = {
    "default": (),
    "sporty": (
        # Denim is blue; the whole-picture tint guard would argue with the
        # clothes. `(blue background:1.5)` stays -- the backdrop is set
        # afterwards by recolor_bg.py and a blue one is still a defect.
        Edit("remove", "(blue tint:1.4), ", stage=S_TINT_RELEASE),
    ),
    "fitness": (
        # Carried, not earned: nothing in this costume is blue, but the
        # picked renders were swept without the guard, and one guard is the
        # size of difference that changes an output. If a blue cast turns up
        # here, this is the line to take back.
        Edit("remove", "(blue tint:1.4), ", stage=S_TINT_RELEASE),
        # The tee knots itself and a knotted tee rides up: no weight on
        # `oversized shirt` could win until the knot was named. A knot is a
        # drawn object, so this works in pass 2 as well (see render-notes).
        Edit("prepend", new="(tied shirt:1.5), (front-tie top:1.5), ",
             stage=S_KNOT),
        # `(skin tight:1.45)` draws the seam it implies; `cameltoe` is that
        # seam's name, and a drawn thing is what a guard reaches. The shirt
        # covering her is the other half and lives in the hem weight.
        Edit("prepend", new="(cameltoe:1.6), ", stage=S_SEAM),
        # The provenance tail's midriff pair never did work; `(crop top:1.5)`
        # is the garment name that was missing. `replace_if_present`,
        # deliberately: `swelter` RELEASES these two tags, and a fitness
        # swelter must keep that release rather than have it silently undone.
        Edit("replace_if_present", ", (midriff:1.35), (navel:1.3)",
             ", (midriff:1.5), (navel:1.45), (crop top:1.5)",
             stage=S_MIDRIFF),
        # The side stripe's tag names CLOTHES, not trousers, so the tee this
        # costume spent three tags keeping plain comes back striped without
        # this. Costume-gated on purpose -- the guard belongs to the wardrobe.
        Edit("append", new=", (striped shirt:1.5)", stage=S_FABRIC),
        # `skin tight` again, on the shirt this time -- the shirt must not
        # cling. Third property-tag leak in one costume; that is the rule
        # above, not a surprise.
        Edit("append", new=", (taut clothes:1.45), (taut shirt:1.5)",
             stage=S_FABRIC),
    ),
    "roomwear": (
        # The settled costume's own garment, banned by name: the shared
        # negative bans pantyhose DEFECTS (brown, blue...) because LEGWEAR
        # wears one, so the plain colour was never forbidden there. This
        # costume's legs are bare. `(shoes:1.4)` is a partial fix -- `stand`'s
        # positive footwear text is not spliced out for this costume (that
        # needs a matching COSTUME_ONLY declaration in costume_check.py), so
        # the guard argues with a tag it cannot reach.
        Edit("append",
             new=", (pantyhose:1.5), (black pantyhose:1.45), (shoes:1.4)",
             stage=S_BARE_LEGS),
    ),
}
