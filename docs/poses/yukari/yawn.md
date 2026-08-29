# yawn

Stretching and yawning, looked down on.

```
(solo:1.5), (stretching:1.4), (arms up:1.35), (yawning:1.4),
(open mouth:1.35), (from above:1.4), sitting, looking at viewer,
full body
```

The pose text comes from `pick/yk-yawn-full`, which was settled on the older
`queue_dq3` recipe against the same base and sampler, and carries two
measured constraints:

- the block must stay at eight tags after `(solo:1.5)` -- a ninth pushes the
  pale thighhighs out;
- `(closed eyes:1.35)` drew a second figure on four seeds of four, so the
  eyes stay open even though a yawn would close them.

`closed mouth` comes out of FACE for this pose; it is the direct opposite of
what a yawn needs.

## Record

Canvas `(1024, 1536)`, `own_eyes=True`, `open_mouth=True`.

No further edits are recorded on this pose's record entry beyond those
parameters.
