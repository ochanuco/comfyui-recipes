# cackle

指を指してケタケタ笑う。体は `hype` の立ち骨格 -- `(standing:1.45),
(from front:1.3), (leaning forward:1.35), (full body:1.45)` -- をそのまま
使い、腕の仕事だけ差し替える。

```
(solo:1.5), (standing:1.45), (from front:1.3),
(leaning forward:1.35), (pointing at viewer:1.5),
(outstretched arm:1.3), (hand on own hip:1.15), (laughing:1.45),
(open mouth:1.4), (smug:1.35), (half-closed eyes:1.3),
(full body:1.45)
```

`(pointing at viewer:1.5)` が構図の主。腕がカメラへ出る分は
`(outstretched arm:1.3)` が持ち、空いた側は `(hand on own hip:1.15)` --
指差し笑いの立ち姿の定番で、遊んだ手が顔へ行くのを軽く止める。重みが低いの
は `tehe` の頬手 1.05 と同じ理由: 主役の腕と張り合わせない。

笑いは `(laughing:1.45)` + `(open mouth:1.4)`。`open_mouthed` で FACE の
`closed mouth` を落とす (`hype` と同型)。目はドヤ配線 (`sly` と同じ):
`own_eyes` で `unamused` を落とし、`(half-closed eyes:1.3)` を自前で持って
FACE の `tareme` と合わせて neki8u の組にする。態度は `(smug:1.35)` --
ケタケタの見下ろし成分は目と態度のこの2枚で作り、嘲りの冷たさは `laughing`
側に持たせない。

## Record

Canvas `(832, 1664)`, `own_eyes=True`, `open_mouth=True`.

832 は `hype` / `roar` の立ち幅。指差しの人差し指は `HAND_BAN` の守備範囲。

初回2バッチ (`7mvsj4` / `a53vkq`) の服はシード次第でボタン前立てシャツワン
ピに振れた (`dux7xp`)。`boss` が測った通り犯人は `oversized shirt`で、服の
正解 (`c8a3ik`) はリボン+素の紫ワンピース。除去は positive 側、ボタンの
名指し ban は新規生成なら効く (`glo2s4` の「消えない」は既存画素の話)。
`character_edits` removes `(oversized shirt:1.3), ` (gated `dressed`).

`negative_edits` prepends `HAND_BAN` at stage `S_POSE_GUARDS`, and prepends
`(buttons:1.5), (button placket:1.4), ` at stage `S_POSE_GUARDS`.

`hires_negative=HAND_BAN + "(buttons:1.5), (button placket:1.4), "`.
