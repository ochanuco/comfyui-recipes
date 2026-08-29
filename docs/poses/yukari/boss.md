# boss

`chair` with the smirk on, and grown up.

```
(solo:1.5), (sitting on chair:1.4), (crossed legs:1.2), (smug:1.15),
(gaming chair:1.4), swivel chair, backrest, full body
```

Built on `ykchairD-chair-555666777` (prompt `c1629d37`), the square render
that lost the front view and sank her into the seat instead -- which is the
wrong result for `chair` and the right starting point for this. Same canvas,
same seed family.

`(front view:1.35), facing viewer` are what pay for the smirk. That seed
never delivered them anyway, so the two tags were being bought and not
collected; the pair that replaces them is the one `lounge`, `peace` and
`invite` all already carry, at the weights they carry it at. Nine in, nine
out.

`(smug:1.15)`, not 1.4. At 1.4 it is gloating; at 1.15 it is composed, and
the chin lift and the head-spine-hip arc that `sip` measured `smug` doing
both survive the drop. The weight is the lever and the tag is not: swapped
for `(light smile:1.3)` the face arrives in roughly the same place and takes
a stocking off her foot on the way, and easing `half-closed eyes` to 1.15
alongside it changed nothing visible at all.

SEED MATTERS MORE THAN THE BLOCK HERE. On `555666777` -- the render this
pose was built on -- her feet come up to head height, which no chair
supports. That is a property of the composition and not of any tag: `feet on
floor` was tried in two donor slots and both weighted and bare, `crossed
legs` was deleted outright and the knees stayed up regardless, the sitting
was raised to 1.6 against the crossing at 1.05, and `(feet up:1.45), (legs
up:1.4), (knees up:1.35)` went into the negative alone and alongside the
positive. Twelve renders, nothing moved.

`1886970040` and `2557902837` seat her properly with the same block, so use
those. The nape session's rule applies: when a defect survives that many
prompt levers, stop diagnosing and change tools -- and the tool here is the
seed.

Ground contact is not available at all on this canvas. The square crops at
the shins, so the floor is never in frame; the best the pose can do is send
the feet downward out of it. Showing a foot planted needs the floor, which
needs the camera back, which is the tall canvas this pose gave up to get its
shading.

`half-closed eyes` is gone and the block is eight. It was half of the smirk
pair every other pose carries, and once `smug` came down to 1.15 the lids
were the only thing still reading as attitude rather than composure. F3
measured easing it from 1.3 to 1.15 as changing nothing, which was true and
beside the point: the tag is not gradual, it is present or not.

To open them further on a picture that is already settled, chain a pass with
`(half-closed eyes:1.4), (closed eyes:1.4)` in the negative -- measured, and
it opens them fully. Do NOT put that pair in the negative here: from scratch
it stacks with the buttons guard and `979797979` grows a second chair with a
rabbit on it. Guards are cheap in a late pass, which only gets to delete, and
expensive in a first pass, which gets to rearrange the picture around them.

## Record

Canvas `(1024, 1024)`, `own_eyes=True`.

Grown up by ONE substitution: the rest of BODY is already adult proportion
and was only held down by `petite`. Dropping the eye tag instead drew a
second empty chair; `(tsurime:1.1)` is the middle if a trace is ever wanted.
`body_edits` replaces `(petite:1.2)` with `(mature female:1.35)`.

`mature female` brings a chest the negative could not finish alone (1.25 ->
1.5 -> 1.75 all left too much); naming `small breasts` positively lands it
in one step. `body_edits` also replaces `(narrow waist:1.25)` with `(narrow
waist:1.25), (small breasts:1.35)`.

`mature female` recruits `oversized shirt` into a button-front shirt dress;
dropping the competing garment restores the dress while keeping the
proportions (`character_edits` removes `(oversized shirt:1.3), ` gated
`dressed`). `sleeves past wrists` stays.

The approved render's coat is off the shoulders -- a deliberate exception to
the docstring's hood rule. `character_edits` replaces `open cardigan` with
`open cardigan, (off shoulder:1.3)` (gated `dressed`). Drop this to get the
hood and ears back.

`character_edits` also carries the shared `_CRISS_CROSS` edit (see
`shared.md`).

The rib is what her legwear is, and the block draws it only on some seeds
unaided. `legwear_edits` ADDS `(ribbed legwear:1.35)` beside `(opaque
pantyhose:1.4)`, not a substitution: substituting from the grey side removed
the tights on every seed, from the pale side cost the colour. If a later
change starts losing the legwear, this extra tag is the first suspect.

`negative_base`: the `(large breasts:1.25)` guard was already in NEGATIVE
and was being outvoted; raising it to 1.5 adds no tag. Guard-stacking has
cost this recipe its palette twice and (here) a rabbit silhouette on the
chair back.

Her dress has no buttons; they arrive from the cardigan being read as a
shirt. One guard is the whole fix -- two and four both bought the backdrop
intruder. `negative_base` prepends `(buttons:1.4), `.
