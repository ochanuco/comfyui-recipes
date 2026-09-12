# bust

正面からのプレーンなバストアップ. A `yukari-sketch` pose with no parent:
the default costume, the shared `FACE`, no props and no gesture -- only a
framing block.

```
(portrait:1.5), (head and shoulders:1.4), (upper body:1.35),
(face focus:1.3), (from front:1.2)
```

The `proportion`, `legwear` and `body` parts are overridden to `adult`,
nothing and `pale skin`. With the shared blocks in place, `(long legs:1.2),
(tall:1.1)`, the pantyhose tags and `(wide hips:1.2), (thick thighs:1.3),
(soft thighs:1.2)` each ask for something below the chest, and the model
widens the frame to draw it: a `(upper body:1.35), (portrait:1.2),
(bust:1.1)` patch over `stand` on a `1024x1280` canvas came back as a
thigh-up cowboy shot on every seed (chimera v62nt8). `bust` is not a
framing tag on the model's vocabulary; `head and shoulders` and `face
focus` are.

The canvas is `1024x1024`: a head-and-shoulders frame has nothing to put in
the lower half of a portrait canvas, and the square is what the bust-up
reference (chimera 0zqtgl, the `yukari` recipe) was drawn on.
