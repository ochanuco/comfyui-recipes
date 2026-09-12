# smug

ジト目に、ほんの少しだけ自信が滲む口元のバストアップ. A `yukari-sketch` pose
derived from `bust`: the same framing, costume and canvas, with only the
face changed.

```
(tareme:1.2), (jitome:1.4), (half-closed eyes:1.2), (confident:1.18),
(tiny one-corner smirk:1.1), closed mouth, looking at viewer
```

`jitome` over `tareme` is the eye; `unamused` is replaced by `confident`
plus a one-corner smirk at a weight low enough to stay a closed-mouth
upturn rather than the `date` smirk. On the source render's seed
(12091204, chimera m9kcre) the same mouth rated good alongside four
sibling mouths (noxwcd, 8ujtjc, 8xpemh, ywz03s); a fully straight mouth
and a catlike one rated neutral. The face is a prompt effect, not a seed
effect: on four other `bust` seeds the expression carried on every one
(chimera 2azlvf, scafj4).

`jitome` at 1.4 is what reads as ジト目 here: the eye stays large and the
upper lid goes straight (d5vakc, ugbbmn, rated good on both seeds). The
alternatives all rated neutral against it -- `half-closed eyes` at 1.3
narrows the eye into a slit instead (kbweaq, 65pd2v), adding `unamused`
on top of that does the same (aiqnlb, u6ul8t), and `narrowed eyes`
changes nothing (j1232h, yua1m9). `half-closed eyes` stays at the shared
`FACE` weight of 1.2; at 1.25 the eyes fell shut on the narrowest-eyed
seed of the sweep (0i9269, 5t6d7l).

The phrase tags (`confident`, `tiny one-corner smirk`) are not
danbooru vocabulary; they read as natural language and their low
weights are what keep the mouth subtle.
