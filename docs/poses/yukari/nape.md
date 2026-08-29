# nape

The back of her neck, seen by someone standing behind her while she sits.

```
(solo:1.55), (from behind:1.45), (from above:1.45), (yokozuwari:1.4),
(nape of neck:1.45), (hair over shoulder:1.35), (head down:1.25), (back focus:1.3)
```

Framing was the whole problem and the answer was not to move the camera
closer. `(upper body:1.35)` lost to `from behind` every time, and the
obvious fix -- `close-up` and `head and shoulders`, which the portrait uses
-- draws a character reference sheet instead: two figures side by side,
front view and back view, the back one in a strapless dress. A composition
guard in the negative does not stop it. Neither tag is usable in a shot that
is already looking at her from behind.

Seating her is what solved it. She is below the camera, so the nape is what
faces it, and `(upper body:1.3)` is enough. `from above` tilted a standing
figure diagonally and behaves against a seated one, which has somewhere for
the angle to land.

`(nape of neck:1.45)` does not come down. Dropped to 1.25 it does not merely
soften -- the pose collapses and she turns to face the camera. The exposure
it brings has to be answered in the negative instead.

`yokozuwari`, not `sitting on floor`. The thighs read too long under the
latter and no amount of describing them fixed it: `thick thighs` down to
1.15, `(long legs:1.4)` in the negative, `(petite:1.35)`, and the camera
angle eased to 1.3 all changed nothing. They could not, because the length
was never asserted -- `sitting on floor` extends the legs, and a leg
extended away from a camera looking down runs the frame. Naming the sitting
folds them, and the knee lands where the eye expects it.

## Record

Canvas `(1024, 1024)`.

Turned away from the camera, `looking at viewer` has no referent -- it
either argues with the pose or spins her back around. `face_edits` removes
`, looking at viewer`.

The bow at the nape, which only this pose is looking at. `character_edits`
replaces `(drawstring:1.4), ` with `(drawstring:1.4), (halterneck:1.45),
(black straps:1.35), ` (gated `dressed`). The pair is documented as costing
every other pose its coat.

The coat pulled off the shoulders is what uncovers the nape. It rides with
the hood rather than the pose block: that block is at eight tags and a
ninth is where the hair clips broke last time. `hood_suffix` appends `,
(off shoulder:1.25)`.

`from behind` invites a turnaround sheet; and `nape of neck` reads as skin
to uncover -- it took the coat off in three of four. What this must NOT
forbid is the coat slipping: (off-shoulder)/(bare shoulders) here banned the
look itself. `negative_base` prepends `(character sheet:1.4), (multiple
views:1.4), reference sheet, turnaround, (undressing:1.4), topless, (bare
back:1.3), `.
