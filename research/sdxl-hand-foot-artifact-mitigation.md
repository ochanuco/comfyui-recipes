# SDXL / Illustrious 系での手足の指アーティファクト対策

6本指、親指が他の指より太い、中指が最長になる、足裏の指が溶けて塊になる——こうした破綻に何が効くのかを、一次情報を優先して洗い出した。結論を先に置き、根拠を後ろに回す。効かなかった・裏付けが取れなかったという結果も、効くという結果と同じ扱いで書く。

末尾に、本リポジトリの案件(hassaku-il-v22、足裏が画面の3割を占める構図)への当てはめと、優先順位を付けた次の一手を置く。

## 結論

一次情報で機構まで説明できるものは少ない。以下は確度順。

| 対策 | 評価 | 根拠の強さ |
|------|------|-----------|
| 領域をクロップして単独でinpaintし貼り戻す | 機構が説明できる。ただし後述の通り本案件では理由が変わる | 一次(論文 + 実装README) |
| ControlNet depth による空間拘束 | 手では実証済み。足は前例なし | 一次(手のみ) |
| `depth_hand_refiner` / HandRefiner | 本案件では使えない。SD1.5専用 | 一次(README に明記) |
| negative / positive の指タグ | 効かない。強めると別の破綻を誘発 | 一次(SDXL論文) + 自前実測 |
| negative embedding / 手LoRA | 配布元自身が効果を保証していない | 一次(配布元の記述) |
| 足・つま先の学習済み検出モデル | 公式には存在しない。コミュニティ製が1件のみ | 一次(モデル一覧 + メンテナ発言) |
| OpenPose の足指キーポイント | 存在しない | 一次 |
| 「足は手より学習データが少ない」説 | 裏付けを見つけられなかった | 根拠なし |

### 機構が説明できるもの

破綻領域だけを切り出し、単独でinpaintして貼り戻す構造。ADetailer と ComfyUI Impact Pack が採る方式で、動作は README の3ステップに明記されている。効く理由は FairHuman 論文([arXiv:2507.02714](https://arxiv.org/abs/2507.02714))が定量的に説明していて、拡散モデルの学習損失は画像全体で計算されるため、面積の小さい顔・手は損失への寄与が小さく、結果として最適化の注意が向かない。論文の言葉では "face and hand regions with smaller areas contribute less to the loss, thus leading to insufficient attention and resulting in poorer generation quality"。裏を返せば、クローズアップで大きく写る手・顔は生成品質が良い、という非対称性がある。

この非対称性は本案件の読み解きに直結する。詳細は5節。

### 効かない、または本案件では使えないもの

プロンプト側の対策。SDXL論文([arXiv:2307.01952](https://arxiv.org/abs/2307.01952)) Appendix B の Limitations が、手の破綻をモデルの構造的限界として記述している。"the model may encounter challenges when synthesizing intricate structures, such as human hands" とし、理由を "hands and similar objects appear with very high variance in photographs and it is hard for the model to extract the knowledge of the real 3D shape and physical limitations in that case" と説明する。学習データ中の見え方のばらつきが大きく3D形状の知識を抽出しにくい、という問題であって、テキスト条件付けで介入できる層の話ではない。

`depth_hand_refiner`(HandRefiner)。手に限れば論文レベルで機構が説明されているが、[README](https://github.com/wenquanlu/HandRefiner) が SD1.5 専用と明記しており、SDXL の画像は 512×512 にリサイズしてから処理せよとしている。1024×1536 で作った Illustrious 系の足に当てる道具ではない。加えて手専用で、足への言及は論文にもREADMEにも一切ない。

足・つま先の学習済み検出モデル。ADetailer にも Impact Pack にも公式には存在しない(3節)。

OpenPose の足指キーポイント。標準スケルトンに定義がなく、`openpose_hand` に相当する足指版は存在しない。

### 裏付けが取れなかったもの

「足は手より訓練データに現れる量が少ないから壊れやすい」という説明。一次情報でも信頼できる二次情報でも裏付けを見つけられなかった。6節に調べた範囲を書く。推測として扱う。

## 1. negative / positive のタグは効くか

SDXL論文の Limitations(上記引用)が根拠になる。手が壊れる原因は学習データ中のばらつきと3D構造の抽出困難であり、プロンプトが介入する意味論的条件付けとは層が違う。CLIP のテキスト条件付けは「何が写っているか」を合わせる仕組みで、「指が何本あるか」という離散的・幾何学的な制約を強制する経路を持たない。

本リポジトリの実測もこれと整合する。`(five toes)` 系で無変化、`(extra toes)` / `(extra digits)` で分節ごとに指が溶ける方向へ悪化、`(toes:1.55)` でつま先が肉球状の塊になった。重みを 1.0〜1.45 で掃引しても解決点はなかった。指の本数を制御できないどころか、強い重みが別の破綻モードを誘発している。

なお「negativeタグは効かない」と明言した公式ドキュメントは見つけられなかった。上は論文の記述と自前の実測からの読み取りである。

## 2. ControlNet: depth / openpose / depth_hand_refiner

`depth_hand_refiner` の実体は [wenquanlu/HandRefiner](https://github.com/wenquanlu/HandRefiner)([論文 arXiv:2311.17957](https://arxiv.org/abs/2311.17957), ACM MM 2024)。MeshGraphormer で画像中の手に3Dメッシュをフィットさせ、指の本数と形状が正しい深度マップを生成し、それを深度ControlNetに渡して inpaint を誘導する。プロンプトを介さず、ピクセルレベルの構造情報で拘束する点が本質。

README が挙げる運用上の制約:

- control strength は 0.4〜0.8 を推奨。1.0 に近づけるとテクスチャが失われる。
- 手の領域は 60px × 60px 以上を推奨。
- ベースは SD v1.5。SDXL の画像は 512×512 にリサイズして処理する必要がある。
- チェックポイントは `inpaint_depth_control.ckpt`。

ComfyUI では [Fannovel16/comfyui_controlnet_aux](https://github.com/Fannovel16/comfyui_controlnet_aux) が "MeshGraphormer Hand Refiner" ノードとして移植している。適用は一次生成 → 壊れた手を手動マスク → preprocessor に `depth_hand_refiner` → 対応する深度ControlNetモデル → inpaint、という順。

足への言及は論文・実装のどこにもない。MeshGraphormer 自体は身体メッシュも扱うモデルだが、HandRefiner としての応用は手に限定して切り出されている。

OpenPose 側は、v1.1 で手・顔のキーポイント検出が追加され手の精度が改善された。ただしキーポイントは関節位置のガイドであって、そこに正しい本数の指を描くのは拡散モデル自身の仕事である。標準スケルトンに足指の定義はない。

## 3. 検出+inpaint ツールと、足検出モデルの有無

ここが本調査で最も重要な確認事項だった。

ADetailer([Bing-su/adetailer](https://github.com/Bing-su/adetailer))の README が挙げる検出モデルは以下の8つ。

`face_yolov8n.pt` / `face_yolov8s.pt` / `hand_yolov8n.pt` / `person_yolov8n-seg.pt` / `person_yolov8s-seg.pt` / `mediapipe_face_full` / `mediapipe_face_short` / `mediapipe_face_mesh`

foot / feet / toe という語は README のどこにも現れない。顔と手と人物と、あとは服(deepfashion系が別途配布される)で、足は対象外である。

動作は README の記述通り "ADetailer works in three simple steps. 1. Create an image. 2. Detect object with a detection model and create a mask image. 3. Inpaint using the image from 1 and the mask from 2."

足モデルを求める声は上がっている。[Discussion #275 "Feets module ?"](https://github.com/Bing-su/adetailer/discussions/275) では足の検出モジュール追加が要望され、返答は "Sure, but do you have one that's been trained in mind?"(学習済みのものに心当たりがあるのか)だった。既存の足検出モデルの不在を裏返しに示している。[Discussion #667 "I need a model specialized in repairing feet and toes"](https://github.com/Bing-su/adetailer/discussions/667) でも同じ要望が出て、別ユーザーが "There is one here on CivitAI, but don't know how good it is, never tried it." と外部の1件を紹介するにとどまる。メンテナからの実装計画は確認できなかった。

ComfyUI 側の Impact Pack([ltdrdata/ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack))も同様で、`FaceDetailer` / `DetailerForEach` が検出→切り出し→拡大→inpaint→合成を行うが、README が案内する検出手段は顔検出、`SAMLoader` によるセグメンテーション、人物セグメンテーション、そして汎用の `BBOX Detector` / `SEGM Detector` である。足専用モデルへの言及はない。

ただし [ComfyUI-Impact-Subpack](https://github.com/ltdrdata/ComfyUI-Impact-Subpack) の `UltralyticsDetectorProvider` は、`models/ultralytics/bbox` または `models/ultralytics/segm` に置かれた任意の YOLO 学習済みモデルを読み込める汎用ローダーである。つまり足検出モデルさえ用意できれば、パイプライン自体は組める。

そのモデルが1件だけ存在する。[Civitai: ADetailer (After Detailer) Foot Model](https://civitai.com/models/1940545/adetailer-after-detailer-foot-model)。配布ページの記述は "Replace those wonky feet with something a little more realistic!" で、作者自身が "I only annotated and trained it on about 50 similar images" と、約50枚の自前アノテーションで学習させた小規模モデルであることを認めている。配置先は `models/ultralytics/bbox` で、Impact Pack の `UltralyticsDetectorProvider` からそのまま読める。定量的な比較検証はページ上にない。

セキュリティ上の注意: このモデルは PickleTensor 形式で、配布ページ自身が deprecated かつ insecure な形式だと注記している。Impact-Subpack 側もモデル読み込みがコード実行を伴いうる旨を明記しており、PyTorch 2.6 以降は安全でない形式の読み込みが既定で制限される。読み込むなら `model-whitelist.txt` への明示登録が要る。

MeshGraphormer / HandRefiner が足をカバーするかは2節の通りで、しない。

要するに、手には学習済み検出モデルもメッシュ推定による矯正パイプラインも揃っているが、足には対応物が存在しない。研究側も同じで、FairHuman は顔と手を扱い、足は "For future work, we plan to further design and optimize corresponding objective functions for more attributes related to humans, such as feet and eyes." と将来課題に置いている。足は道具立てが無い領域である。

## 4. LoRA / negative embedding の実証

配布元自身の記述を読むと、効果は保証されていない。

[badhandv4](https://huggingface.co/EvilEngine/badhandv4) のモデルカードは "improve the hand details of AI-generated images with less impact on the style of painting" と主張し、CFG 11 以上でより効果的とする。一方で "If it makes your model behave worse than before, please do not use it." という注記があり、モデルによっては悪化することを作者が認めている。設計対象は AnimeIllustDiffusion で、Illustrious 系での検証ではない。

[Bad-Hands-5](https://civitai.com/models/116230/bad-hands-5) の配布ページには効果の説明も before/after 比較も技術文書もなく、ダウンロード数とレビュー評価という間接指標しかない。

手LoRA側も同様で、EnvyBetterHands 系の配布ページでは作者が掲載作例を cherry-pick だと明言し、8枚生成して使えるのは1〜2枚という趣旨の注記を置いている。

加えてこれらの多くは SD1.5 期に SD1.5 の破綻パターンを前提に作られている。SDXL / Illustrious 系への転用実績を示す一次情報は見つけられなかった。人気指標は高いが、検証根拠は薄い、という位置づけが妥当。

## 5. 解像度と被写体占有率

FairHuman([arXiv:2507.02714](https://arxiv.org/abs/2507.02714))が、この論点について最も明確な一次情報になる。標準的な潜在拡散の損失は画像全体で計算され、領域ごとの難易度を区別しない。したがって面積の小さい顔・手は損失への寄与が小さく、最適化の注意が向かず、品質が落ちる。論文は逆側も述べていて、クローズアップで大きく写る場合の顔・手は問題なく生成される。

つまり文献が説明しているのは「小さく写ると壊れる」方向であって、「大きく写ると壊れる」方向ではない。ADetailer の検出→クロップ→拡大→inpaint→貼り戻しという構造は、この小面積問題を解消する道具である。対象領域を単独の生成対象に切り出すことで、その領域が損失と注意の全体を占めるようになる。解剖学的な知識を追加しているのではなく、面積による希釈を外している。

本案件のように対象が画面の3割を占める場合、この機構はそのままでは当てはまらない。足はすでに十分大きく、ピクセル予算は足りている。「大きく写っているのに壊れる」ケースを扱った一次情報は見つけられなかった。SDXL論文が挙げる根本原因(見え方のばらつきと3D構造の抽出困難)は占有率と独立に成立する理屈なので、大きく写る場合も同じ理由で壊れうる、と読むのが妥当だが、これは論文記述からの外挿であって直接の一次情報ではない。

## 6. 足・つま先に固有の事情

「訓練データで足が手より少ない」という説明の裏付けは取れなかった。

Illustrious / NoobAI-XL 系のモデルカードを見ても、anatomy や foot / toe の学習データ量に関する記述はない。Danbooru のタグ件数(`feet` 約27.2万件、`toes` 約23.8万件)は決して少なくないが、Danbooru のタグは「構図上の見どころとして意識的に付けられたか」を反映するもので、単に写り込んでいるだけでは付かないことが多い。手はほぼ全画像に写るのにタグとして明示されない。したがってタグ件数を訓練上の露出量の代理指標に使うのは妥当でない。

LAION 中の手の画像に関する比率の数値が検索途中に現れたが、出典を確認できなかったので採用しない。

状況証拠としては、[Discussion #275](https://github.com/Bing-su/adetailer/discussions/275) や [#667](https://github.com/Bing-su/adetailer/discussions/667) に足の破綻を訴える声が集まっていること、コミュニティが自前で足検出モデルを学習させて配布していること、FairHuman が足を将来課題に置いていることが挙がる。ただしこれらは「足が難しい」ことの傍証であって、「訓練データが少ないから」という因果の証拠ではない。

## 7. プロンプトだけでは直せないというコンセンサスはあるか

「プロンプトでは直せない」と一箇所で明言した一次情報は見つけられなかった。ただし複数の一次情報が同じ方向へ収斂している。

SDXL論文は手の破綻をモデルの構造的限界として記述し、プロンプトによる回避を示唆していない。FairHuman は損失関数側の設計変更で解こうとしている。ADetailer / Impact Pack / HandRefiner / depth_hand_refiner という主要な解決策は、いずれも検出→マスク→空間的条件付け→局所再生成という、プロンプトを介さない経路を採る。prompt-only のアプローチを主要な解決策として提示している一次情報は、エコシステム内に見当たらなかった。

道具立てがそちらに寄っていること自体が、実務上の合意を反映していると読める。ただしこれは収斂的な読み取りであり、明示的な宣言の引用ではない。

## この案件への適用

前提: ComfyUI + hassaku-il-v22(Illustrious系SDXL)。座って片脚をカメラへ突き出し、足裏が画面の3割を占める構図。1024×1536 で生成し、2048 へ img2img で描き直して納品。ControlNet と ADetailer 相当は未導入。

### 失敗した6項目の読み解き

既に試した対策は、テキスト条件付け経由(1・2・3・4・6)か、マスクなしの全体denoise(5)のどちらかに分類できる。前者が効かないのは1節と7節の通りで、指の本数という離散的構造にテキストは届かない。`(toes:1.55)` が肉球状の塊を生んだのも、強い重みが別の破綻モードを誘発した例として整合する。

5(全体 img2img の denoise 0.35〜0.55 掃引)が効かなかった理由は、二段に分けて考える必要がある。

ひとつは、全体 img2img は足の領域に追加のピクセル予算を割り当てないこと。ただし5節の通り、足はすでに画面の3割を占めていてピクセル予算は足りている。したがって「解像度不足」は本案件の主因ではない可能性が高く、2048 パスが効かなかったのはむしろ当然である。ここは他の多くの手指の事例と事情が違う。

もうひとつが本質的で、denoise 0.35〜0.55 という帯は、全体にかける以上それ以上上げられないという制約から来ている。全体に高い denoise をかけると構図もキャラクターも作り直しになる。しかし指の本数を作り直すには、その領域の構造をいったん壊して再サンプルする必要がある。つまりこの掃引は、必要な強度に届く前に上限で頭打ちになっていた。

根本原因の当てはめとしては、「足の構造を作り直せる強度の denoise が、足の領域に一度もかかっていない」と読むのが、一次情報と実測の両方に整合する。

### 優先順位を付けた次の一手

1. 足の領域だけをマスクして、高い denoise で局所 inpaint する

   確度: 高(機構は一次情報で裏付け。ただし足への適用は手からの外挿)

   Impact Pack を導入し、足裏の領域を手動マスク(標準のマスクエディタ、または `SAMDetector` に手動ポイント)して、その領域だけを `DetailerForEach` 系で切り出し→inpaint→貼り戻す。学習済み検出モデルは要らない。この構図は固定なので足の位置は毎回大きくは変わらず、手動マスクの運用コストは許容範囲に収まるはず。

   既に試した5と決定的に違うのは denoise の帯である。局所マスクなら構図を壊す心配がないので、0.7〜1.0 まで上げられる。全体掃引では原理的に到達できなかった領域で、まだ試していない変数はここ。まずは 0.75 前後から始めて、足の形が作り直される強度を探る。あわせてクロップ側の解像度を上げる(足だけを 1024 相当の単独キャンバスに拡大してから inpaint)と、FairHuman の言う「クローズアップ regime」に足を置くことになり、面積による希釈も同時に外れる。

   この2つ(高denoise・単独キャンバス化)は独立に効きうるので、切り分けて振ること。

2. 足クロップの inpaint に汎用 SDXL depth ControlNet を併用する

   確度: 中〜低(手では実証済み、足は前例なし。外挿)

   1 が「作り直す」だけだと、作り直した結果がまた6本指になる可能性がある。HandRefiner の教訓は、正しい構造を深度マップという空間情報で与えれば収束するという点にある。`depth_hand_refiner` 自体は SD1.5 専用で使えないが(2節)、機構は汎用である。hassaku-il-v22 と互換の SDXL 用 depth ControlNet に、足の深度マップを与えて inpaint を拘束する。

   問題は正しい足の深度マップをどこから持ってくるか。生成画像から `Depth_Midas` 等で抽出すると壊れた足の深度をそのまま写してしまう。実写の足裏写真や3Dモデルのレンダーを参照にして深度を作る、あるいは抽出した深度マップのつま先部分を手で修正する、という手間が要る。ここまでやれば HandRefiner が手でやっていることの足版に相当するが、自動化された前例はない。

3. コミュニティ製の足検出モデルで 1 を自動化する

   確度: 中(モデルの存在は確認済み、品質は未知)

   [Civitai の ADetailer Foot Model](https://civitai.com/models/1940545/adetailer-after-detailer-foot-model) を `models/ultralytics/bbox` に置き、`UltralyticsDetectorProvider` から読む。ただし学習画像が約50枚と小規模で、足裏を正面から見た本案件の構図で当たるかは未知数。PickleTensor 形式なのでセキュリティ上の判断も要る(3節)。

   1 の手動マスクが回り始めてから、手間を減らす目的で検討すればよい。最初に入れる依存ではない。

4. 見送り: depth_hand_refiner / HandRefiner そのもの

   SD1.5 専用で、SDXL 画像は 512×512 へ落とさないと動かない(2節)。1024×1536 の納品パイプラインに組み込む意味がない。手専用でもある。

5. 見送り: OpenPose の足指キーポイント

   標準スケルトンに足指の定義がない(2節)。足全体の向きは拘束できても、指の本数には届かない。

6. 打ち切り: prompt / negative の追加調整、negative embedding、手LoRA

   確度: 高(打ち切ってよい、という判断について)

   1節・4節の通り、テキスト条件付けは指の本数に届かず、配布物側も効果を保証していない。既に4パターン試して無変化か悪化という実測とも整合する。この方向への追加投資は根拠が薄い。

7. 補助: 生成解像度を上げるだけの対策は単独では期待しない

   5節の通り、足はすでに画面の3割を占めておりピクセル予算は主因ではない。局所的な高denoise inpaint と組み合わせない限り、解像度を上げるだけでは同じ失敗を繰り返す公算が大きい。
