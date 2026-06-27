#!/usr/bin/env python3
"""
generate_sample.py  v2
CastScope タレント好感度調査 サンプルデータ生成

出力:
  docs/sample_rawdata.txt    ... 6,001行 53列 タブ区切り UTF-8
  docs/sample_layout.txt     ... For Survey 標準レイアウト
  docs/pattern_master.txt    ... パターン × タレントID 対応表
"""
import re, ast, os, sys, random, datetime, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 再現性のためシードを固定
random.seed(42)

# ================================================================
# 1. TALENTS ロード
# ================================================================
def load_talents():
    with open("collect_sns.py", encoding="utf-8") as f:
        lines = f.readlines()
    start = next(
        (i for i, l in enumerate(lines) if re.match(r"\s*TALENTS\s*=\s*\[", l)), None
    )
    if start is None:
        raise RuntimeError("TALENTS not found in collect_sns.py")
    clean, depth = [], 0
    for i, line in enumerate(lines[start:], start):
        stripped = re.sub(r"#.*$", "", line)
        clean.append(stripped)
        depth += stripped.count("[") - stripped.count("]")
        if depth <= 0 and i > start:
            break
    src = "".join(clean)
    m = re.match(r"\s*TALENTS\s*=\s*(\[[\s\S]*\])\s*$", src)
    if not m:
        raise RuntimeError("TALENTS parse failed")
    return ast.literal_eval(m.group(1))

TALENTS = load_talents()
N = len(TALENTS)
print(f"タレント数: {N}")

# ================================================================
# 2. ジャンル判定（export_json.py と同じロジック）
# ================================================================
GENRE_RANGES = [
    (range(6,  46),  "女優"),
    (range(46, 86),  "俳優"),
    (range(86, 111), "バラエティ"),
    (range(111,146), "ジャニーズ系"),
    (range(146,186), "女性アイドル"),
    (range(186,226), "歌手・アーティスト"),
    (range(226,266), "お笑い芸人"),
    (range(266,301), "若手・注目株"),
]
GENRE_OV = {1:"女優", 2:"俳優", 3:"女優", 4:"俳優", 5:"女優"}

def get_genre(tid):
    if tid in GENRE_OV:
        return GENRE_OV[tid]
    for rng, g in GENRE_RANGES:
        if tid in rng:
            return g
    return "その他"

# ================================================================
# 3. 定数
# ================================================================
N_PAT     = 60
N_PER_PAT = 100
N_SS      = N_PAT * N_PER_PAT   # 6,000
SLOTS     = 5
N_Q4G     = 5                   # Q4 ジャンル数
Q4_LABELS = ["ドラマ", "バラエティ", "映画", "配信", "CM"]

# ================================================================
# 4. パターン割り当て（300人 ÷ 5 = 60パターン）
# ================================================================
tidx = list(range(N))
random.shuffle(tidx)           # シャッフルして偏りなく配分
patterns = [tidx[i * SLOTS:(i + 1) * SLOTS] for i in range(N_PAT)]
# patterns[p] = [0-indexed talent indices × 5]

# ================================================================
# 5. タレントプロファイル生成
# ================================================================
# ジャンル別 認知率(mean, sd)・好感度平均
GENRE_PROF = {
    "女優":             {"aw": (0.72, 0.09), "fav_mu": 3.55},
    "俳優":             {"aw": (0.66, 0.09), "fav_mu": 3.40},
    "バラエティ":       {"aw": (0.58, 0.09), "fav_mu": 3.20},
    "ジャニーズ系":     {"aw": (0.76, 0.10), "fav_mu": 3.60},
    "女性アイドル":     {"aw": (0.52, 0.09), "fav_mu": 3.15},
    "歌手・アーティスト":{"aw":(0.58, 0.09), "fav_mu": 3.30},
    "お笑い芸人":       {"aw": (0.56, 0.09), "fav_mu": 3.10},
    "若手・注目株":     {"aw": (0.42, 0.09), "fav_mu": 3.00},
}
# Q4ジャンル適性確率 [ドラマ, バラエティ, 映画, 配信, CM]
GENRE_Q4 = {
    "女優":             [0.80, 0.38, 0.76, 0.50, 0.62],
    "俳優":             [0.75, 0.32, 0.80, 0.45, 0.52],
    "バラエティ":       [0.32, 0.90, 0.22, 0.44, 0.58],
    "ジャニーズ系":     [0.63, 0.78, 0.55, 0.62, 0.82],
    "女性アイドル":     [0.44, 0.72, 0.34, 0.66, 0.78],
    "歌手・アーティスト":[0.38, 0.55, 0.44, 0.62, 0.72],
    "お笑い芸人":       [0.28, 0.87, 0.18, 0.40, 0.50],
    "若手・注目株":     [0.55, 0.52, 0.50, 0.78, 0.56],
}
DEFAULT_Q4 = [0.50, 0.50, 0.50, 0.50, 0.50]

prng = random.Random(99)   # プロファイル用に別シード
profiles = []
for i, t in enumerate(TALENTS):
    genre = get_genre(t["id"])
    gp    = GENRE_PROF.get(genre, {"aw": (0.50, 0.09), "fav_mu": 3.20})

    # リスト上位ほど認知率・好感度が高くなるボーナス
    rank_bonus = (1.0 - i / N) * 0.18

    aw = min(0.97, max(0.30,
             prng.gauss(gp["aw"][0] + rank_bonus * 0.55, gp["aw"][1])))
    fav_mu = min(4.80, max(2.00,
             prng.gauss(gp["fav_mu"] + rank_bonus * 0.90, 0.22)))
    fav_sd = max(0.70, min(1.40, prng.gauss(1.00, 0.18)))

    # Q4 適性に個体差
    base_q4 = GENRE_Q4.get(genre, DEFAULT_Q4)
    q4_fit  = [min(0.95, max(0.05, f + prng.gauss(0, 0.07))) for f in base_q4]

    profiles.append(dict(
        awareness=aw, fav_mu=fav_mu, fav_sd=fav_sd, q4_fit=q4_fit, genre=genre
    ))

# ================================================================
# 6. ヘッダー定義
# ================================================================
# 計 53 列
#   MID/START/END/TIME/F1/F2/F3/PAT : 8
#   T1〜T5                           : 5
#   Q1c1〜Q1c5                       : 5
#   Q2s1〜Q2s5                       : 5
#   Q3s1〜Q3s5                       : 5
#   Q4s1c1〜Q4s5c5                   : 25
HEADER = (
    ["MID", "START", "END", "TIME", "F1", "F2", "F3", "PAT"]
    + [f"T{s+1}"        for s in range(SLOTS)]
    + [f"Q1c{s+1}"      for s in range(SLOTS)]
    + [f"Q2s{s+1}"      for s in range(SLOTS)]
    + [f"Q3s{s+1}"      for s in range(SLOTS)]
    + [f"Q4s{g+1}c{s+1}" for g in range(N_Q4G) for s in range(SLOTS)]
)

# ================================================================
# 7. ローデータ生成
# ================================================================
# 均等割付:
#   100人/パターン × 10セル(F1×F3) = 10人/セル/パターン
#   F1: 1=男(cells 0-4), 2=女(cells 5-9)
#   F3: 1=20代 〜 5=60代 (cell%5 + 1)

AGE_RANGE = {1:(20,29), 2:(30,39), 3:(40,49), 4:(50,59), 5:(60,69)}
age_rng = random.Random(77)

BASE_DT = datetime.datetime(2025, 11, 1, 9, 0, 0)
rows = []

for resp in range(N_SS):
    pat_idx  = resp // N_PER_PAT   # 0-59
    pos      = resp  % N_PER_PAT   # 0-99 within pattern

    # セル → 属性
    cell = pos // 10               # 0-9
    f1   = 1 + cell // 5           # 1=男, 2=女
    f3   = 1 + cell  % 5           # 1-5
    lo, hi = AGE_RANGE[f3]
    f2   = age_rng.randint(lo, hi) # 実年齢

    slots_ti = patterns[pat_idx]
    t_ids    = [TALENTS[ti]["id"] for ti in slots_ti]
    pat      = pat_idx + 1

    # 時刻（1週間以内にランダム分散）
    sec      = random.randint(0, 6 * 24 * 3600)
    s_dt     = BASE_DT + datetime.timedelta(seconds=sec)
    dur      = random.randint(240, 900)
    e_dt     = s_dt + datetime.timedelta(seconds=dur)

    # ── Q1: 認知 (0=知らない / 1=知っている) ──────────────
    q1 = [1 if random.random() < profiles[ti]["awareness"] else 0
          for ti in slots_ti]

    # ── Q2s: 好感度 SA 1-5 (Q1=0 なら 0) ──────────────────
    # 1=全く好感が持てない … 5=非常に好感が持てる
    q2s = []
    for s, ti in enumerate(slots_ti):
        if q1[s] == 1:
            v = round(random.gauss(profiles[ti]["fav_mu"], profiles[ti]["fav_sd"]))
            q2s.append(max(1, min(5, v)))
        else:
            q2s.append(0)

    # ── Q3s: 視聴意向 SA 1-5 (Q2s≠4,5 なら 0) ────────────
    # 好感者(4or5)の 75% が「見たい以上」(Q3≥4)
    q3s = []
    for s in range(SLOTS):
        if q2s[s] in (4, 5):
            if random.random() < 0.75:
                v = random.choices([4, 5], weights=[0.45, 0.55])[0]
            else:
                v = random.choices([1, 2, 3], weights=[0.25, 0.45, 0.30])[0]
            q3s.append(v)
        else:
            q3s.append(0)

    # ── Q4: ジャンル適性 MA 0/1 (Q2s≠4,5 なら 0) ─────────
    # 列順: Q4s{genre}c{slot} = g=0..4, s=0..4
    q4 = []
    for g in range(N_Q4G):
        for s, ti in enumerate(slots_ti):
            if q2s[s] in (4, 5):
                q4.append(1 if random.random() < profiles[ti]["q4_fit"][g] else 0)
            else:
                q4.append(0)

    mid = resp + 1
    row = (
        [mid,
         s_dt.strftime("%Y/%m/%d %H:%M:%S"),
         e_dt.strftime("%Y/%m/%d %H:%M:%S"),
         dur, f1, f2, f3, pat]
        + t_ids + q1 + q2s + q3s + q4
    )
    rows.append(row)

# ================================================================
# 8. ローデータ書き出し
# ================================================================
os.makedirs("docs", exist_ok=True)
RAW_PATH = os.path.join("docs", "sample_rawdata.txt")
with open(RAW_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write("\t".join(HEADER) + "\n")
    for row in rows:
        f.write("\t".join(str(v) for v in row) + "\n")

sz_raw = os.path.getsize(RAW_PATH) // 1024
print(f"[raw]     {RAW_PATH}  {len(rows)} 行  {sz_raw} KB  {len(HEADER)} 列")

# ================================================================
# 9. パターンマスター書き出し
# ================================================================
PAT_PATH = os.path.join("docs", "pattern_master.txt")
with open(PAT_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write("PAT\tT1\tT2\tT3\tT4\tT5\n")
    for p, slots_ti in enumerate(patterns):
        ids = [TALENTS[ti]["id"] for ti in slots_ti]
        names = [TALENTS[ti]["name"] for ti in slots_ti]
        # タレントID + タレント名も付記（確認用）
        cells = [f"{ids[i]}:{names[i]}" for i in range(SLOTS)]
        f.write(f"{p+1}\t" + "\t".join(cells) + "\n")

print(f"[pattern] {PAT_PATH}  {N_PAT} パターン")

# ================================================================
# 10. レイアウトファイル生成
#     列順: 質問番号/質問タイプ/アイテム名/ラベル/回答タイプ/カテゴリ数/カラム/選択肢番号/質問文
# ================================================================
def lr(qn, qt, item, lbl, at, cats, col, ch, qtxt):
    return "\t".join([str(x) for x in [qn, qt, item, lbl, at, cats, col, ch, qtxt]])

lrows = []

# ── 属性 ─────────────────────────────────────────────────────────
# F1 性別
for ch, lbl in [(1, "男性"), (2, "女性")]:
    lrows.append(lr("F1","SA","性別","性別","カテゴリ",2,"F1",ch,
                    "あなたの性別をお選びください"))

# F2 年齢（実数 / FA）
lrows.append(lr("F2","FA","年齢","年齢（実数）","数値",0,"F2",0,
                "あなたの現在のお年齢を半角数字でご記入ください（20〜69歳）"))

# F3 年代
for ch, lbl in enumerate(["20代","30代","40代","50代","60代"], 1):
    lrows.append(lr("F3","SA","年代","年代","カテゴリ",5,"F3",ch,
                    "あなたの年代をお選びください"))

# PAT
lrows.append(lr("PAT","SA","パターン","PAT","カテゴリ",60,"PAT",0,
                "提示パターン番号（1〜60、システム自動割付）"))

# ── Q1: 認知 MA (0=知らない / 1=知っている) ──────────────────────
for s in range(SLOTS):
    col = f"Q1c{s+1}"
    for ch, lbl in [(0, "知らない"), (1, "知っている")]:
        lrows.append(lr("Q1","MA",f"スロット{s+1}",f"スロット{s+1}","カテゴリ",2,col,ch,
                        f"提示された{s+1}人目のタレントをご存じですか？"
                        "（0=知らない / 1=知っている）"))

# ── Q2s: 好感度 SA (0=非表示 / 1-5) ─────────────────────────────
for s in range(SLOTS):
    col = f"Q2s{s+1}"
    for ch, lbl in enumerate(
            ["全く好感が持てない","好感が持てない","どちらでもない",
             "好感が持てる","非常に好感が持てる"], 1):
        lrows.append(lr("Q2","SA",f"スロット{s+1}好感度",f"スロット{s+1}","カテゴリ",5,col,ch,
                        f"{s+1}人目のタレントへの好感度をお教えください"
                        "（Q1=1のタレントのみ表示 / 0=非表示）"))

# ── Q3s: 視聴意向 SA (0=非表示 / 1-5) ───────────────────────────
for s in range(SLOTS):
    col = f"Q3s{s+1}"
    for ch, lbl in enumerate(
            ["全く見たくない","あまり見たくない","どちらでもない",
             "やや見たい","ぜひ見たい"], 1):
        lrows.append(lr("Q3","SA",f"スロット{s+1}視聴意向",f"スロット{s+1}","カテゴリ",5,col,ch,
                        f"{s+1}人目のタレントが出演する番組をどの程度見たいですか？"
                        "（Q2=4か5のタレントのみ表示 / 0=非表示）"))

# ── Q4: 合うジャンル MA (0=合わない / 1=合う) ────────────────────
# Q4s{genre}c{slot}: s=1-5→ジャンル, c=1-5→スロット
for g, genre in enumerate(Q4_LABELS, 1):
    for s in range(SLOTS):
        col = f"Q4s{g}c{s+1}"
        for ch, lbl in [(0, "合わない"), (1, "合う")]:
            lrows.append(lr("Q4","MA",f"{genre}×スロット{s+1}",genre,"カテゴリ",2,col,ch,
                            f"このタレントに合うジャンルをすべてお選びください"
                            f"【{genre}】（Q2=4か5のタレントのみ表示 / 0=合わない / 1=合う）"))

LAY_PATH = os.path.join("docs", "sample_layout.txt")
with open(LAY_PATH, "w", encoding="utf-8", newline="\n") as f:
    for row in lrows:
        f.write(row + "\n")

sz_lay = os.path.getsize(LAY_PATH) // 1024
print(f"[layout]  {LAY_PATH}  {len(lrows)} 行  {sz_lay} KB")

# ================================================================
# 11. 簡易集計（確認用）
# ================================================================
print("\n── 簡易集計 ──")
# 認知率（全体）
aware_cnt = sum(
    1 for row in rows
    for s in range(SLOTS)
    if row[8 + 5 + s] == 1      # Q1c1-Q1c5 は列13-17 (0-indexed 8+5+s)
)
total_slot = N_SS * SLOTS
print(f"認知率（全体平均）: {aware_cnt/total_slot*100:.1f}%")

# Q2 平均（認知者のみ）
q2_vals = []
for row in rows:
    for s in range(SLOTS):
        v = row[8 + 5 + 5 + s]  # Q2s列
        if v > 0:
            q2_vals.append(v)
print(f"好感度（認知者平均）: {sum(q2_vals)/len(q2_vals):.2f}  "
      f"（N={len(q2_vals):,}）")

fav45 = sum(1 for v in q2_vals if v >= 4)
print(f"好感者（4-5）比率: {fav45/len(q2_vals)*100:.1f}%")

# Q3 平均（好感者のみ）
q3_vals = []
for row in rows:
    for s in range(SLOTS):
        v = row[8 + 5 + 5 + 5 + s]  # Q3s列
        if v > 0:
            q3_vals.append(v)
fav_intent = sum(1 for v in q3_vals if v >= 4)
print(f"視聴意向「見たい以上」比率（好感者中）: {fav_intent/len(q3_vals)*100:.1f}%  "
      f"（N={len(q3_vals):,}）")

print("\n完了！")
