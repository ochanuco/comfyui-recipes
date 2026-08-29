# costumes

The wardrobe: who she is, and the four sets of clothes hung on it. A costume
owns three blocks -- character, legwear, hood -- and its own staged negative
edits; everything else (FACE, SURFACE, BODY, THIN, every pose, the rest of
the negative) is shared: what changes between costumes is the clothes, not
her and not the drawing.

## IDENTITY: the hair ornament

`IDENTITY` was split out of `CHARACTER` the day a second costume arrived:
the garments are one of two sets, and IDENTITY is the half both sets keep.
The split moved no text and no token order -- `IDENTITY + <garments>` is
byte-identical to the CHARACTER that shipped, and `costume_check.py`'s
fingerprint is the proof: it did not move when the line was drawn.

`hair ornament` carried no weight until the nape renders, where it lost
every time -- her clips were missing from a dozen straight renders. It is
not that the tag is wrong, it is that an unweighted tag in a prompt this
crowded is indistinguishable from an absent one: everything around it is at
1.3+. Same disease and same fix as `drawstring` in CHARACTER (below):
weighting it (to `1.4`) brought it back. Same diagnosis, no separate sweep
recorded.

## CHARACTER: the coat/hoodie/cardigan length

The hem was the one thing that answered to nothing else. Raising `(black
hoodie)` to 1.55 did nothing, `(cropped jacket)` in the negative did
nothing, `(oversized clothes)` destroyed the costume, and deleting the body
block did nothing. Swapping the garment NOUN moved it, because these read
as different garments to the model rather than one garment with a length.

Dark pixels measured by garment noun:

| garment | dark-pixel band |
|---|---|
| hoodie | 13.6-18.4% |
| hooded jacket / hooded coat | 16.6-25.1% |
| hooded cardigan | 17.9-26.1% (longest) |

Against the coat, the cardigan took the lower back from 46.6% to 58.0%
covered. The coat sat in the block because `ns-1117511306` -- prompt
`7d231c4f`, the render this recipe is aimed at -- wears a coat; the cardigan
measured longest of all and was the one flagged to try if the hem wanted to
go further (there is a leftover, unresolved fragment in the source at this
point reading "hooded cardigan, and sleeves that say 'too big' without
naming the garment" -- kept here for the record, its referent is not
recoverable from the comment alone). The garment now shipped is `(black
hooded cardigan:1.45)`.

## CHARACTER: the oversized silhouette

The target is an oversized hoodie: boxy body, big soft hood on the
shoulders, hem at the hip. Every tag that names the garment's FIT failed:

- `(oversized clothes)` destroyed the costume at both 1.35 and 1.15 (stroke
  width 1.91 -> 3.82 both times).
- `(loose clothes)` loosened the drawing rather than the cloth (stroke to
  7.64).
- `(coattails)` drew narrow jointed straps.
- `(wind)` summoned floating white shapes.

Tags naming a PART's state passed where tags naming the garment's fit did
not: `(sleeves past wrists)` + `(wide sleeves)` took the lower-back coverage
from 54.6% to 78.5%, boxed out the body and dropped the hem, at 1.91px
stroke.

Later, the same "nouns and part-states pass, fit words fail" reading was
tested again and did NOT generalise. `(oversized shirt:1.35)` alone broke
the stroke to 3.82 and 13.69px; `(sleeves past fingers:1.4)` alone broke it
to 4.65 and 7.64 -- a noun and a part-state, both destroying the drawing on
their own. Together, at 1.3 each, the stroke held at 1.91 on both seeds and
lower-back coverage went 54.6% -> 79.8% and 96.2%. That is the same shape as
the sock-length finding below: two competing tags holding each other in
place, dropping either one making things worse. The earlier rule was
generalised from two tags that happened to work, and it does not hold as a
rule.

`past wrists`, not `past fingers`: fingers-length sleeves cover the hands
entirely and they got drawn as shapeless lumps in five renders of five.
Letting the hands out put real fingers on the coins in four of five, and
dropped the colour count from 26-50 to 16-22 as a bonus. Weighting the hand
guards already in the negative (`(bad hands:1.4)`, `(extra fingers:1.4)`)
did nothing -- all five still had the hands inside the sleeves; the fix was
removing what hid them, not forbidding the failure. (Swapping this same tag
once left her back bare, in a block without `(coin:1.3)` in the pose -- it
does not here; the same substitution is not the same change in a different
block.)

## CHARACTER: the dress hem

The hem does not respond to length tags. Asked to cover the buttocks, three
renders moved bare skin in the upper-leg band 37.4% -> 40.1% -> 38.3%:
`(medium dress:1.3)`, then `(medium dress:1.45)` with `(short dress:1.4)`,
`(microdress:1.4)` opposing it in the negative. All noise. `short dress` per
its wiki already spans "the middle of the thighs at the lowest to just
below the crotch and ass at the highest" and the render sits at the top of
that range and stays there.

The likely reason -- untested -- is that the costume comes from `yuzuki
yukari` itself rather than from these garment tags, so a length tag is
arguing with the character prior and losing. Lengthening it further would
need something with more authority than a tag: a different garment noun, or
inpainting the hem.

Weight history on `(frills:1.25)`: 1.2 -> 1.45 by way of intermediate
values. At 1.2 the purple was being drawn as a pleated skirt with a
separate white frill under it -- a two-piece where the design is one.
Naming the wrong reading in the negative instead, `(skirt:1.35)`,
`(pleated skirt:1.4)`, deleted the lower half of the garment outright on one
of two seeds: hoodie and tights, no dress. Third time a guard tag cost more
than it bought (after the duplicate guards that wrecked the palette, and
the `(thighhighs:1.3)` that removed the socks -- see NEGATIVE in
`prompt_style.py`).

`drawstring` -- the coat's cord, with the pink bead on the end -- was
unweighted and therefore not drawn. Weighted, it comes back.

The dress's own fastening (the halter that ties at the back of the neck in
black straps) is deliberately NOT in CHARACTER; `positive()` adds it for the
one pose that can see it. Globally it is destructive: measured on `sip`,
`(halterneck:1.45)` + `(black straps:1.35)` pulled the coat off her
shoulders and bared her back, and lowering the weights to 1.15/1.1 still
bared a shoulder. Naming a halter is apparently read as naming a garment
that leaves the shoulders out, and the coat gets out of its way.

## CHARACTER: frills 0.85 -> 1.25

"Weighted down rather than deleted" was the intent, and 0.85 did not deliver
it: below 1 in a prompt where everything else is 1.3+ has meant ABSENT
three times in this file, and this was the fourth. `boss` had already
spliced it to 1.25 for a session and got the frilled collar, the ribbon ties
and the beaded cords back for nothing measurable -- so the value was proven
and simply never promoted (until now, 2026-08-18).

「ワンピースを正しく見直す」. Measured on 555666777 and 1886970040: the
frilled hem returns, the coat's cord shows its pink bead, the backdrop stays
clean. It is a COSTUME change and therefore applies to every pose.

## rabbit print / sticker

`rabbit print` is deliberately absent: paired with `sticker` it drew a
rabbit decal on her cheek in the 1024x1024 portrait. `sticker` earns its
place -- it is half of the white-outline idiom (see `SURFACE` in
`prompt_style.py`) -- so the print is the tag that goes.

## HOOD

Reset to `b1258b0c`: hood down at 1.25, not pinned behind her head. The
alternative -- `(hood down:1.5), (hood behind head:1.3)` -- was measured and
is not better: unpinning changed neither the colour count nor the clutter,
and pinning it back did not recover anything. `b1258b0c`'s value is the one
that stands.

## LEGWEAR_LAYERED (retired)

RETIRED, kept whole in the source. Everything below was measured and none
of it was wrong; the design it serves is the one that changed. It is the
record of what the two-garment layering costs and of the four things that
do not move the sock colour.

Pale thighhighs over opaque black tights. The layering had already failed
once with `(sheer black pantyhose:1.5)` underneath -- the sheer tights
vanished and left the socks alone. Solid black was tried as a much stronger
ask.

`(lavender tint:1.3)` and the pale sock colours are not only leg tags:
dropping them took the whole palette darker and flatter, because they were
where the pale cast came from.

What did have to go was the see-through set -- `(see-through
pantyhose:1.45)`, `(skin visible through pantyhose:1.4)` never stayed on the
legs and left the dress sheer over her stomach.

Grey, not black, for the tights: `grey pantyhose` is the canonical
danbooru spelling (`gray_` has no page) and its wiki warns of "considerable
overlap" with black and brown -- brown is guarded in the negative already.
Chosen over red: the hoodie lining measures `#bc616a`, and `(red
pantyhose)` landed at hue 338 / saturation 152 against the lining's 313 /
126 -- close enough to read as the same intent, far enough to read as a
second red. Grey sits inside a range the palette already has.

The cost of grey was the layering: the dark band at the top of the thigh
went from 28.7-41.6% of the measured strip on black to 10.2-28.6% on grey,
because the socks are pale and the contrast under them shrank.

Nothing found made it darker, and two things made it lighter. Band value
(lower = darker), over three seeds:

| combination | band value (3 seeds) |
|---|---|
| `(grey pantyhose:1.45)` alone | 52.9 / 73.1 / 76.3 |
| + `(black pantyhose:1.1)` | 80.1 / 81.4 / 84.9 |
| + `(black pantyhose:1.25)` | 85.8 / 92.2 / 83.8 |
| `(charcoal pantyhose:1.35)` alongside | 57.5 / 73.1 / 84.9 |

Mixing in the darker colour name lightens it, and more of it lightens it
further: two colour words land on neither, somewhere between. Competing
tags held each other in place for sock LENGTH (dropping one there made
things worse), and that finding did not carry over to colour -- grey alone
was the darkest of everything tried.

`over-kneehighs` ends just above the knee and, per its danbooru wiki,
exists to "leave a larger gap between the stocking and the skirt or dress"
-- the shortening that was wanted. It was ADDED, not substituted: swapping
the whole block to over-kneehighs removed the socks entirely, because
`thighhighs over pantyhose` is a real tag carrying the layering and
`over-kneehighs over pantyhose` is a phrase that is not.

1.2/1.5 measured sock saturation 22.9 against fb-b's 12.2, and 1.45/1.25
overshot to 8.7. Left at the first setting, because the second cost dress
hue (306 -> 280 against a 300 target) and whiteness was the cheaper of the
two to fix afterwards. The background moved too -- #d0d0c0, #a0a0a0,
#909090 across 1.2/1.5, 1.45/1.25 and 1.35/1.35 -- and the middle setting
was the darkest of the three; that was read as the backdrop being unstable
under any small perturbation rather than these tags controlling it (see
`scripts/recolor_bg.py --color`; fb-b's backdrop is `#d0d0c0`).

`over-kneehighs` was ruled OUT. This is `lyC-555666777` (prompt `9d24700e`),
checked afterwards across seven seeds: all seven put pale socks over black
tights on both legs, with the tights showing as a band at the top of the
thigh.

It had briefly been written up as the least consistent arm, on the strength
of a left/right brightness difference that peaked at 73.9. That measure was
later found to read pose and overlap, not sock length -- `737373737`,
reported as having lost a sock, has both -- and it had already been found
unfit for judging legwear one arm earlier. The number was wrong, not the
recipe; judge this block by looking at it.

Dropping `(over-kneehighs:1.4)` alongside was also tried and was much worse:
worst-case leg difference 73.9, with one sock nearly gone at `737373737`.
Two competing length tags were apparently holding each other in place.

## LEGWEAR: one garment on the leg

ONE garment on the leg, and it is the pantyhose. This is the live block.
The official V6 character sheet draws one pantyhose. The layered pair above
was this repo's own invention and it held up for a while -- `lyC-555666777`
put pale socks over grey tights on seven seeds out of seven. What broke it
was the `prone` pose: seen from behind, whichever layer covers the buttock
ends in a hem, and a fitted shape bounded by a hem above legs of another
colour reads as a pair of bike shorts. 「スパッツになってる」. Six lexical
attempts, a regional conditioning pass and a hand-drawn hem later, the
finding was that the model only knows `thighhighs over pantyhose` -- which
puts the boundary on the THIGH, the exact geometry the `prone` pose threw
out.

「タイツ1本にするか」. Abandoned, not deferred: dropping the second garment
removes the boundary, so there is nothing left to hold -- no hem to draw,
no region to condition, no two greys to keep apart.

The gradient direction is the sheet's own reading, and it runs the other
way from the layered tights it replaced -- purple at the thigh, black at
the ankle, one surface the whole way. That was once called inverted and
`(gradient legwear)` was dropped on the strength of it; the purple end at
the thigh is what was actually wanted.

Three tags is the count a garment block was said to tolerate here before
the coat starts sprawling. Six attempts could not lower the purple end from
the prompt: `(muted colors)` + `(desaturated)` DOUBLED the leg's saturation
(37.7 to 75.6), `(dusty purple)` raised it, and a vividness guard left the
mean flat and pushed the peak up. The reading: when the tag describing the
defect does nothing at any weight, the defect is implied by something else
-- here the pale purple dress and hair, pulling the top of the leg toward
them. The fix used instead: take the saturation off afterwards with
`.local/desat.py` (HSV S alone, so the gradient and the line survive); x0.55
matches the older palette.

Then the direction had to be said out loud (2026-08-18). 「グラデーションの
向きが逆ですね。足先を黒に。これは固定化」. The three-tag block describes the
garment and says nothing about which end is which, and left to itself the
model put the black at the THIGH and faded it pale at the ankle -- the
exact reverse of the intended design. Six seeds of `stand` all drew it that
way, so it was never a seed issue.

There is no directional tag; `gradient legwear` is the only gradient word
the model has and it carries no orientation. The direction had to be bought
by naming the colour that goes at the top and letting the black fall to
what is left -- `pale purple pantyhose` was already measured, one design
ago, for exactly this property: it gets DRAWN on the thigh where `grey
pantyhose` does not. That finding, originally recorded as an explanation of
an accident (the wrong colour was buying thigh coverage), became what the
block is built on.

Measured on 1886970040, three wordings, one seed, `stand`:

| wording | result |
|---|---|
| black, gradient, opaque | black thigh, pale ankle (reversed) |
| black, PALE PURPLE, gradient, opaque | purple thigh, black ankle -- kept |
| PALE PURPLE, black, gradient, opaque | also right-way-up, and the whole composition moved (see `stand`) |

The last two both fix the direction, so order is not what carries it -- the
colour being named at all is. Black stays first and at 1.5, keeping it the
garment's stated colour with the purple as the thing done to one end of it.

The current block is FOUR tags, one more than the three-tag tolerance
stated above -- spent knowingly, and flagged as the first suspect if the
coat starts growing or the dress loses its frills later.

## LEGWEAR_BAN

Six tags -- more guards than this file usually allows itself. The rule it
looks like it is breaking is a different one: the palette damage in earlier
attempts came from stacking guards that all pointed at ONE defect,
outvoting each other's neighbours. These six each name a distinct garment.
Measured across the one-tights arms with the whole list present: palette
intact, hair violet, backdrop grey, no colour drift.

## SPORTY

The reference is a grey oversized tee, denim shorts, plain black tights and
white high-top sneakers. Three things it keeps from the settled (default)
costume on purpose: IDENTITY whole, ONE garment on the leg, and its shoes
named in the costume rather than in a pose.

## FITNESS

Arrived at by subtraction from SPORTY over one session: the tee lost its
print and its colour, the denim and the tights came off as 夏っぽくない, a
skirt was tried in six shapes and abandoned (「スカート案をやめた方が良さそ
う」), and what was left is a gym kit.

「無地でリブ生地がいいな。夏っぽさを出すなら少し薄めの紫」 was the ask for the
top. `light purple` is IDENTITY's own spelling for the shade, borrowed
rather than invented, and it is one colour tag in one slot -- `purple shirt`
is NOT stacked beside it.

`(high-waist pants:1.4)` is deliberately in the character block and not in
the legwear block: it is the waistband, a thing the SHIRT sits on. Without
it the oversized tee hangs to mid-thigh and swallows whatever is under it,
which is how two rounds of skirt-length measurement got thrown away before
anyone noticed the hem was not the variable.

`(ribbed shirt:1.35)` was tried and removed, and the removal is the more
interesting half of the story. 「リブ柄を指定したがスポーツ着としては合ってな
いから」 -- but the rib was also the reason the hem could not be settled. A
ribbed knit falls against the body, so it read as a sweater dress when long
and as a shirt tucked in when short: 1.4 drew 「少し服が長すぎる」 while 1.3
drew 「服を中に入れるのは違う」. There was no window between them because the
dial was the wrong one. Plain jersey had neither failure, and the hem then
went the OTHER way from where two rounds of weight-sweeping were pushing
it: settling at 1.45, longer than the 1.4 that had already been called too
long -- what a wrong dial looks like from the far side.

`(oversized shirt:...)` weight history: 1.45 -> 1.55. 「股を出さずに服で隠
すこと」. Third and last value tried on this dial: it is the tag that
decides where the hem lands, the hem is what covers her, and 1.55 is the
weight at which it clears the crotch.

## FITNESS_LEGWEAR

`(vertical-striped clothes:1.35)` is the side stripe, and it is the one tag
in this costume that was bought with a hit rate rather than a look. The
line arrived unasked on ONE seed of four under `(sportswear:1.35)` alone --
`33f5fd9d`, 「白のラインが良い！！！！」 -- which is this file's usual warning
sign: a value the model has no way to hold on its own. Naming the stripe
took the hit rate to three of four. The COLOUR did not come along: the
picked pair is purple-lined and the render that started it is white-lined.
Presence is pinned; hue is not, and nothing here pretends otherwise.

The cost is a guard in `negative()` (see `COSTUME_NEGATIVE_EDITS` below),
because the tag names clothes and not trousers.

## ROOMWEAR

The fourth costume, and the only one that keeps the settled costume's coat:
summer, air-conditioned room, off-duty. 寒いから羽織っている -- the cardigan
is on her because the room is cold, not because this is a variant of the
dress costume, so it carries CHARACTER's cardigan/hood/sleeve text VERBATIM
rather than a respelling. That is what lets a later session widen one of
the `dressed`-gated splices onto this costume too, if a pose ever wants to:
the needle would already be there to match. None does yet -- see the notes
at those gates in `recipe.py`'s `positive()`.

Under the cardigan: a white oversized tee and dolphin shorts, in the same
slot SPORTY's denim and FITNESS's high-waist pants sit in. No footwear tag,
unlike either of those two -- this costume is barefoot, not shod.

## COSTUME_NEGATIVE_EDITS

What each costume does to the shared negative, in the slots the picked
renders were drawn in. The rule behind most of these: a tag that names how
cloth behaves (skin tight, vertical stripes) goes wherever there is fabric,
so it needs a guard on every garment it was not meant for -- and that guard
belongs to the WARDROBE, not to whichever pose first needed it.

- **sporty**: `(blue tint:1.4)` removed from the tint-release stage. Denim
  is blue, and the whole-picture tint guard would argue with the clothes.
  `(blue background:1.5)` stays in the negative -- the backdrop is set
  afterwards by `recolor_bg.py`, and a blue one is still a defect there.
- **fitness**: the same `(blue tint:1.4)` removal, carried rather than
  earned -- nothing in this costume is blue, but the picked renders
  (`d218afdc`, `e8dacf7e`) were swept under `sporty` without the guard, and
  one guard is the size of difference that changes an output. Flagged as
  the line to take back if a blue cast turns up here.
- **fitness**: `(tied shirt:1.5), (front-tie top:1.5)` prepended at the knot
  stage. The tee knots itself and a knotted tee rides up: no weight on
  `oversized shirt` could win until the knot was named. A knot is a drawn
  object, so this also works in the second pass (see render-notes).
- **fitness**: `(cameltoe:1.6)` prepended at the seam stage. `(skin
  tight:1.45)` draws the seam it implies; `cameltoe` is that seam's name,
  and a drawn thing is what a guard can reach. The shirt covering her is
  the other half of the fix and lives in the hem weight above.
- **fitness**: midriff tail rewritten (`replace_if_present`), from
  `, (midriff:1.35), (navel:1.3)` to `, (midriff:1.5), (navel:1.45), (crop
  top:1.5)`. 「お腹が見えてるのも not for me」. The provenance tail's
  1.35/1.30 never did the job; `(crop top:1.5)` is the garment name that
  was missing. `replace_if_present` deliberately, because `swelter`
  RELEASES these two tags and a fitness `swelter` must keep that release
  rather than have it silently undone here.
- **fitness**: `, (striped shirt:1.5)` appended at the fabric stage. The
  side stripe's tag names CLOTHES, not trousers, so the tee this costume
  spent three tags keeping plain comes back striped without this guard.
- **fitness**: `, (taut clothes:1.45), (taut shirt:1.5)` appended at the
  fabric stage. 「シャツが股間で凹むのも望んでいない」 -- `skin tight` again,
  on the shirt this time. Third property-tag leak in one costume, which is
  the rule above at work rather than a surprise.
- **roomwear**: `, (pantyhose:1.5), (black pantyhose:1.45), (shoes:1.4)`
  appended at the bare-legs stage. The settled costume's own garment,
  banned by name: the shared negative bans pantyhose DEFECTS (brown,
  blue...) because LEGWEAR wears one, so the plain colour was never
  forbidden there -- this costume's legs are bare. The `(shoes:1.4)` guard
  is a partial fix: `stand`'s positive footwear text is not spliced out for
  this costume (that would need a matching `COSTUME_ONLY` declaration in
  `costume_check.py`), so the guard argues with a tag it cannot reach.
