# LS-DYNA K-file Mass Editor

LS-DYNA の K-file を解析し、指定した複数の Part に属する Node に対して追加質量を分配し、指定した X-Z 重心位置を実現する `*ELEMENT_MASS` を生成する Python ツールです。

## 目的

ユーザーが以下を指定します。

- 対象 Part ID（PID）
- 追加する総質量
- 追加質量の目標重心 X 座標
- 追加質量の目標重心 Z 座標

K-file から対象 Part に属する Node を抽出し、それぞれの Node に追加質量を割り当てます。

最終的に、計算された質量を LS-DYNA の

```text
*ELEMENT_MASS
```

として別の K-file に出力します。

Y方向については、対象となるモデル・Node 群が X-Z 面に対して対称であることを前提とし、今回の質量最適化では X-Z 重心のみを対象とします。

---

## 処理の流れ

```text
Input K-file
    ↓
*ELEMENT_SHELL セクション抽出
    ↓
ELEMENT情報取得
(EID / PID / NODE)
    ↓
指定PID群のELEMENTを抽出
    ↓
使用NODE IDを統合
    ↓
*NODE セクション抽出
    ↓
NODE座標取得
(NID / X / Y / Z)
    ↓
対象NODE群を作成
    ↓
2Dランプによる質量分布最適化
    ↓
各NODEの追加質量を計算
    ↓
総質量を正規化
    ↓
*ELEMENT_MASS を出力
```

---

# 対象 Part の指定

複数のPIDをまとめて指定できます。

例：

```python
target_pids = {
    100,
    101,
    102,
    200,
}
```

各Partを個別に質量計算するのではなく、指定されたすべてのPartに含まれるNodeを一つのNode群として扱います。

複数のElementから共有されているNodeについては、Node IDを `set` で管理することで重複を除去します。

したがって、

```text
PID 100 ─┐
PID 101 ─┤
PID 102 ─┼→ NODE統合 → 一つの質量分布として計算
PID 200 ─┘
```

となります。

---

# K-file の解析

## `*ELEMENT_SHELL`

今回使用しているK-fileでは、`*ELEMENT_SHELL` を8文字固定幅として解析します。

概念的には、

```text
EID     PID     N1      N2      N3      N4 ...
```

を取得し、

```python
{
    "eid": 1,
    "pid": 100,
    "nodes": [437, 32, 1, 3]
}
```

のようなデータとして保持します。

K-file内に複数の `*ELEMENT_SHELL` セクションが存在する場合にも対応し、すべてのセクションをまとめて解析します。

---

## `*NODE`

今回使用しているK-fileでは、Nodeデータを以下の固定幅として解析します。

```text
NID :  8
X   : 16
Y   : 16
Z   : 16
```

後続する `TC`, `RC` は今回使用しないため無視します。

Node情報は、

```python
{
    nid: {
        "x": x,
        "y": y,
        "z": z
    }
}
```

の形式で保持します。

---

# 追加質量の計算

## 基本方針

追加質量には以下の条件があります。

1. 全Nodeの追加質量の合計が指定総質量になること
2. 追加質量によるX方向重心が目標値に近づくこと
3. 追加質量によるZ方向重心が目標値に近づくこと
4. Nodeに与える質量が負にならないこと

単純な一次式

```text
mass = a + bX + cZ
```

では、目標重心によって負質量が発生するため、現在は2次元ランプ分布を使用しています。

---

# 2D Ramp Mass Distribution

NodeのX-Z座標に対して、以下のランプ関数から相対質量を計算します。

```text
w_i = max(
    0,
    cos(theta) * x'_i
    + sin(theta) * z'_i
    - d
)
```

ここで、

```text
theta : ランプが増加する方向
d     : ランプの立ち上がり位置
x'    : 正規化されたX座標
z'    : 正規化されたZ座標
w_i   : Node i の相対質量
```

です。

X-Z-W空間で考えると、

```text
w = cos(theta) * x'
  + sin(theta) * z'
  - d
```

は平面を表します。

負の領域を

```text
max(0, ...)
```

によって0へ切ることで、質量が必ず0以上になるランプ分布を作ります。

---

## theta

`theta` はX-Z平面上でランプが増加する方向を表します。

```text
theta = 0 deg
→ +X方向へ質量増加

theta = 90 deg
→ +Z方向へ質量増加

theta = 180 deg
→ -X方向へ質量増加

theta = 270 deg
→ -Z方向へ質量増加
```

---

## d

`d` はランプの立ち上がり位置を表します。

`d` が大きくなると、一部のNodeだけに質量が集中します。

`d` が小さくなると、より広い範囲のNodeに質量が分布します。

したがって、同程度に目標重心を実現できる解が複数存在する場合には、`d` が小さい解を優先します。

これは必須の物理条件ではなく、解を一意に決めるための副目的です。

---

# 最適化

探索する変数は、

```text
theta
d
```

の2変数のみです。

Node数が増えても最適化変数の数は増えません。

大量のNodeに対する質量・重心計算はNumPy配列演算で処理します。

そのため、複数Partを指定して数十万Node規模になった場合にも対応できる構成としています。

---

## 最適化の優先順位

最適化は以下の考え方で行います。

### 第1目的

目標重心に可能な限り近づけます。

```text
Target CG
    ↓
CG X
CG Z
```

XとZのモデル寸法差の影響を抑えるため、重心誤差は座標範囲で正規化して評価します。

### 第2目的

重心誤差が許容範囲内となる解が存在する場合、その中で `d` が小さい解を優先します。

つまり、

```text
重心条件を満たす
        ↓
その中で d を小さくする
        ↓
より広いNODEへ質量を分散
```

という方針です。

---

# 実現できない重心

Nodeに与える質量を0以上に制限すると、任意の重心位置を実現できるわけではありません。

例えば対象NodeのX座標範囲が、

```text
X = 600 ～ 2500
```

の場合、

```text
Target X = 300
```

を正の質量だけで実現することはできません。

その場合、最適化は失敗として停止するのではなく、現在の質量分布モデルで実現可能な範囲で目標重心に最も近い解を探索します。

計算結果には、

```text
指定重心
計算重心
X重心誤差
Z重心誤差
CG誤差
許容値内かどうか
```

を表示します。

---

# 総質量の正規化

ランプから得られる `w_i` は相対的な質量です。

最終的なNode質量は、

```text
mass_i = TotalMass * w_i / sum(w)
```

として正規化します。

これにより、

```text
sum(mass_i) = TotalMass
```

となります。

全Nodeに同じ倍率を掛けるだけなので、この正規化によってX-Z重心位置は変化しません。

---

# 出力

計算されたNode質量は、

```python
result["nodal_masses"]
```

に、

```python
{
    nid: mass
}
```

の形式で格納されます。

これを `*ELEMENT_MASS` としてK-fileへ出力します。

例：

```text
*KEYWORD
*ELEMENT_MASS
$      EID     NID            MASS
 9000000       1  1.23456789E-03
 9000001       2  1.34567890E-03
 9000002       5  2.45678901E-03
*END
```

質量が0のNodeについては `*ELEMENT_MASS` を生成しません。

ELEMENT IDは指定された開始IDから連番で採番します。

---

# ファイル構成

現在の主な構成は以下です。

```text
kfile_editer/
│
├─ main.py
│
├─ k_parser.py
│
├─ node_utils.py
│
├─ mass_utils.py
│
├─ k_writer.py
│
├─ input/
│   └─ input_model.k
│
├─ output/
│   └─ element_mass.k
│
├─ .gitignore
└─ README.md
```

## `main.py`

処理全体の実行とユーザー設定を担当します。

主な設定：

```python
target_pids = {
    100,
    101,
    102,
    200,
}

additional_mass = 100.0

target_cg_x = 1000.0
target_cg_z = 50.0
```

## `k_parser.py`

LS-DYNA K-fileの解析を担当します。

主な処理：

```text
K-file読み込み
Keyword section抽出
固定幅文字列分割
ELEMENT_SHELL解析
NODE解析
```

## `node_utils.py`

対象Element・Nodeの抽出を担当します。

主な処理：

```text
PIDによるELEMENT抽出
NODE IDの重複除去
対象NODE座標の取得
```

## `mass_utils.py`

追加質量分布の計算を担当します。

主な処理：

```text
NODEデータのNumPy配列化
X-Z座標正規化
2Dランプ計算
theta / d 最適化
重心計算
総質量正規化
NODEごとの質量生成
```

## `k_writer.py`

計算されたNode質量から、

```text
*ELEMENT_MASS
```

のK-fileを生成します。

---

# 必要ライブラリ

Pythonのほか、現在以下を使用します。

```text
numpy
scipy
```

インストール：

```powershell
pip install numpy scipy
```

仮想環境を使用することを推奨します。

---

# 実行

`input` フォルダへ対象K-fileを配置し、

```powershell
python main.py
```

を実行します。

処理結果として、対象Element数、対象Node数、計算重心、重心誤差、ランプパラメータ、Node質量範囲などを確認できます。

その後、計算された質量分布が `*ELEMENT_MASS` のK-fileとして `output` フォルダへ出力されます。

---

# 現在の前提・制約

- `*ELEMENT_SHELL` を対象とする
- Elementデータは現在8文字固定幅を想定
- `*NODE` は `8 / 16 / 16 / 16` の固定幅を想定
- 質量重心の最適化対象はX-Z方向
- Y方向は対象Node群の対称性を前提とする
- 追加質量は0以上
- 複数PIDは一つのNode群として扱う
- 質量0のNodeには `*ELEMENT_MASS` を生成しない
- 出力用ELEMENT IDは既存モデルと重複しない値を指定する必要がある

---

# 今後の拡張候補

- 既存ELEMENT IDを確認し、`*ELEMENT_MASS` のEIDを自動採番
- 入力K-fileの複数選択への対応
- K-fileフォーマットの追加対応
- ユーザー入力部分の整理
- 計算結果のログ出力
- 質量分布・対象Node・目標重心の可視化