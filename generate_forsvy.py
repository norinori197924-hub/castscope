#!/usr/bin/env python3
"""generate_forsvy.py
CastScope タレント好感度調査 For Survey標準形式サンプルデータ生成
出力:
  docs/castscope_layout.txt  ... Shift-JIS タブ区切り
  docs/castscope_rawdata.txt ... Shift-JIS タブ区切り 6,000行
"""
import re, ast, os, random, datetime

# ── TALENTS ロード ─────────────────────────────────────────────
def load_talents():
    with open("collect_sns.py", encoding="utf-8") as f:
        lines = f.readlines()
    start = next((i for i,l in enumerate(lines) if re.match(r"\s*TALENTS\s*=\s*\[",l)), None)
    if start is None:
        raise RuntimeError("TALENTS not found")
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

# ── ジャンル判定 ────────────────────────────────────────────────
GENRE_RANGES = [
    (range(6,46),"女優"),(range(46,86),"俳優"),(range(86,111),"バラエティ"),
    (range(111,146),"ジャニーズ系"),(range(146,186),"女性アイドル"),
    (range(186,226),"歌手・アーティスト"),(range(226,266),"お笑い芸人"),
    (range(266,301),"若手・注目株"),
]
GENRE_OV = {1:"女優",2:"俳優",3:"女優",4:"俳優",5:"女優"}

def get_genre(tid):
    if tid in GENRE_OV: return GENRE_OV[tid]
    for rng,g in GENRE_RANGES:
        if tid in rng: return g
    return "その他"

# ── 定数 ─────────────────────────────────────────────────────────
N_PAT, N_PER_PAT, N_SS, SLOTS, N_Q4G = 60, 100, 6000, 5, 5
Q4_GENRE_NAMES = ["ドラマ・ドキュメンタリー","バラエティ・情報","映画","配信・動画","CM・広告"]

# ── パターン割り当て ────────────────────────────────────────────
random.seed(42)
tidx = list(range(N))
random.shuffle(tidx)
patterns = [tidx[i*SLOTS:(i+1)*SLOTS] for i in range(N_PAT)]

# ── タレントプロファイル ─────────────────────────────────────────
GENRE_PROF = {
    "女優":              {"aw":(0.72,0.09),"fav_mu":3.55},
    "俳優":              {"aw":(0.66,0.09),"fav_mu":3.40},
    "バラエティ":        {"aw":(0.58,0.09),"fav_mu":3.20},
    "ジャニーズ系":      {"aw":(0.76,0.10),"fav_mu":3.60},
    "女性アイドル":      {"aw":(0.52,0.09),"fav_mu":3.15},
    "歌手・アーティスト":{"aw":(0.58,0.09),"fav_mu":3.30},
    "お笑い芸人":        {"aw":(0.56,0.09),"fav_mu":3.10},
    "若手・注目株":      {"aw":(0.42,0.09),"fav_mu":3.00},
}
GENRE_Q4 = {
    "女優":              [0.80,0.38,0.76,0.50,0.62],
    "俳優":              [0.75,0.32,0.80,0.45,0.52],
    "バラエティ":        [0.32,0.90,0.22,0.44,0.58],
    "ジャニーズ系":      [0.63,0.78,0.55,0.62,0.82],
    "女性アイドル":      [0.44,0.72,0.34,0.66,0.78],
    "歌手・アーティスト":[0.38,0.55,0.44,0.62,0.72],
    "お笑い芸人":        [0.28,0.87,0.18,0.40,0.50],
    "若手・注目株":      [0.55,0.52,0.50,0.78,0.56],
}
prng = random.Random(99)
profiles = []
for i, t in enumerate(TALENTS):
    genre = get_genre(t["id"])
    gp = GENRE_PROF.get(genre, {"aw":(0.50,0.09),"fav_mu":3.20})
    rb = (1.0 - i/N) * 0.18
    aw  = min(0.97, max(0.30, prng.gauss(gp["aw"][0]+rb*0.55, gp["aw"][1])))
    fm  = min(4.80, max(2.00, prng.gauss(gp["fav_mu"]+rb*0.90, 0.22)))
    fs  = max(0.70, min(1.40, prng.gauss(1.00, 0.18)))
    bq  = GENRE_Q4.get(genre, [0.50]*5)
    qf  = [min(0.95, max(0.05, f+prng.gauss(0,0.07))) for f in bq]
    profiles.append({"awareness":aw,"fav_mu":fm,"fav_sd":fs,"q4_fit":qf})

# ── カラム定義（56列）───────────────────────────────────────────
# 1-4:  MID START END TIME
# 5-8:  F1 F2t1 F3 PATt1
# 9-13: T1t1-T5t1
# 14-18: Q1c1-Q1c5
# 19-23: Q2s1-Q2s5
# 24-28: Q3s1-Q3s5
# 29-53: Q4s1c1-Q4s5c5
# 54-56: STA 性別 年齢
HEADER = (
    ["MID","START","END","TIME","F1","F2t1","F3","PATt1"]
    + [f"T{s+1}t1"          for s in range(SLOTS)]
    + [f"Q1c{s+1}"          for s in range(SLOTS)]
    + [f"Q2s{s+1}"          for s in range(SLOTS)]
    + [f"Q3s{s+1}"          for s in range(SLOTS)]
    + [f"Q4s{g+1}c{s+1}"   for g in range(N_Q4G) for s in range(SLOTS)]
    + ["STA","性別","年齢"]
)
COL = {h: i+1 for i,h in enumerate(HEADER)}

# ── Rawdata生成 ─────────────────────────────────────────────────
AGE_RANGE = {1:(20,29),2:(30,39),3:(40,49),4:(50,59),5:(60,69)}
age_rng   = random.Random(77)
BASE_DT   = datetime.datetime(2025, 11, 1, 9, 0, 0)
rows = []

for resp in range(N_SS):
    pi  = resp // N_PER_PAT
    pos = resp  % N_PER_PAT
    cell = pos // 10
    f1   = 1 + cell // 5
    f3   = 1 + cell  % 5
    lo, hi = AGE_RANGE[f3]
    f2   = age_rng.randint(lo, hi)

    sti   = patterns[pi]
    t_ids = [TALENTS[ti]["id"] for ti in sti]
    pat   = pi + 1

    sec = random.randint(0, 6*24*3600)
    sdt = BASE_DT + datetime.timedelta(seconds=sec)
    dur = random.randint(240, 900)
    edt = sdt + datetime.timedelta(seconds=dur)
    hh, rem = divmod(dur, 3600)
    mm, ss  = divmod(rem, 60)
    time_str = f"{hh}:{mm}:{ss}"

    q1  = [1 if random.random() < profiles[ti]["awareness"] else 0 for ti in sti]

    q2s = []
    for s2, ti in enumerate(sti):
        if q1[s2] == 1:
            v = round(random.gauss(profiles[ti]["fav_mu"], profiles[ti]["fav_sd"]))
            q2s.append(max(1, min(5, v)))
        else:
            q2s.append(0)

    q3s = []
    for s2 in range(SLOTS):
        if q2s[s2] in (4, 5):
            if random.random() < 0.75:
                v = random.choices([4,5], weights=[0.45,0.55])[0]
            else:
                v = random.choices([1,2,3], weights=[0.25,0.45,0.30])[0]
            q3s.append(v)
        else:
            q3s.append(0)

    q4 = []
    for g in range(N_Q4G):
        for s2, ti in enumerate(sti):
            if q2s[s2] in (4, 5):
                q4.append(1 if random.random() < profiles[ti]["q4_fit"][g] else 0)
            else:
                q4.append(0)

    row = (
        [resp+1,
         sdt.strftime("%Y/%m/%d-%H:%M:%S"),
         edt.strftime("%Y/%m/%d-%H:%M:%S"),
         time_str, f1, f2, f3, pat]
        + t_ids + q1 + q2s + q3s + q4
        + ["COMP", f1, f2]
    )
    rows.append(row)

os.makedirs("docs", exist_ok=True)
RAW = os.path.join("docs", "castscope_rawdata.txt")
with open(RAW, "w", encoding="cp932", newline="\r\n") as f:
    f.write("\t".join(HEADER) + "\r\n")
    for row in rows:
        f.write("\t".join(str(v) for v in row) + "\r\n")
sz = os.path.getsize(RAW) // 1024
print(f"[raw] {RAW}  {len(rows)}行  {len(HEADER)}列  {sz}KB")

# ── Layout生成 ───────────────────────────────────────────────────
# For Survey レイアウト形式:
#   行1: メタデータ（タブ区切りキー値ペア）
#   行2: カラムヘッダ（10列 + 空4列 = 14列）
#   データ行: 14列（10内容列 + 空4列）
#
# 列順: 質問番号/質問タイプ/アイテム名/ラベル/回答タイプ/カテゴリ数/カラム/選択肢番号/質問文/設問タイトル

def row14(c1="",c2="",c3="",c4="",c5="",c6="",c7="",c8="",c9="",c10=""):
    return "\t".join([str(x) for x in [c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,"","","",""]])

LAY = os.path.join("docs", "castscope_layout.txt")
with open(LAY, "w", encoding="cp932", newline="\r\n") as f:
    def wr(c1="",c2="",c3="",c4="",c5="",c6="",c7="",c8="",c9="",c10=""):
        f.write(row14(c1,c2,c3,c4,c5,c6,c7,c8,c9,c10) + "\r\n")

    # 行1 メタデータ
    f.write("castscope_Layout\tcastscope_GT\t調査名\tCastScopeタレント好感度調査"
            "\t調査ID\t99990001\t調査方法\tインターネットリサーチ"
            "\t商品種別\tクローズドモニタ\t実施期間\t\t有効サンプル数\t6000\r\n")
    # 行2 ヘッダ
    f.write("質問番号\t質問タイプ\tアイテム名\tラベル\t回答タイプ\tカテゴリ数"
            "\tカラム\t選択肢番号\t質問文／選択肢\t設問タイトル／選択肢グループキャプション"
            "\t\t\t\t\r\n")

    # ── システム列 ──
    wr("MID","MID","MID","MID","MID","",1,"","MID")
    wr("START","D","START","START","D","",2,"","開始日時")
    wr("END","D","END","END","D","",3,"","終了日時")
    wr("TIME","D","TIME","TIME","D","",4,"","回答時間")

    # ── F1 性別 SA 2択 ──
    wr("F1","S","F1","F1","SA",2,COL["F1"],"","あなたの性別をお答えください。")
    wr(c8=1,c9="男性")
    wr(c8=2,c9="女性")

    # ── F2 年齢 NUM ──
    wr("F2","NUM","F2",c9="あなたの現在のお年齢を半角数字でご記入ください（20〜69歳）。")
    wr(c4="F2t1",c5="NUM",c7=COL["F2t1"],c8=1)

    # ── F3 年代 SA 5択 ──
    wr("F3","S","F3","F3","SA",5,COL["F3"],"","あなたの年代をお答えください。")
    for ch, lbl in enumerate(["20代","30代","40代","50代","60代"], 1):
        wr(c8=ch, c9=lbl)

    # ── PAT パターン NUM ──
    wr("PAT","NUM","PAT",c9="提示パターン番号（1〜60、システム自動割付）。")
    wr(c4="PATt1",c5="NUM",c7=COL["PATt1"],c8=1)

    # ── T1〜T5 タレントID NUM ──
    for s in range(SLOTS):
        qn = f"T{s+1}"
        wr(qn,"NUM",qn,c9=f"提示タレントID（スロット{s+1}）。")
        wr(c4=f"T{s+1}t1",c5="NUM",c7=COL[f"T{s+1}t1"],c8=1)

    # ── Q1 認知 MA 5択 ──
    wr("Q1","M","Q1","","MA",5,"","",
       "提示された5名のタレントの中でお名前をご存じの方をすべてお選びください。")
    for s in range(SLOTS):
        wr(c4=f"Q1c{s+1}",c7=COL[f"Q1c{s+1}"],c8=s+1,c9=f"スロット{s+1}のタレント")

    # ── Q2 好感度 MTS (SA 5択 × 5スロット) ──
    wr("Q2","MTS",c9="各タレントへの好感度をお聞きします。（ご存じの方のみ回答）")
    q2_choices = ["全く好感が持てない","好感が持てない","どちらでもない",
                  "好感が持てる","非常に好感が持てる"]
    for s in range(SLOTS):
        wr(c3=f"Q2S{s+1}",c4=f"Q2s{s+1}",c5="SA",c6=5,
           c7=COL[f"Q2s{s+1}"],c9=f"スロット{s+1}のタレント")
        for ch, lbl in enumerate(q2_choices, 1):
            wr(c8=ch, c9=lbl)

    # ── Q3 視聴意向 MTS (SA 5択 × 5スロット) ──
    wr("Q3","MTS",c9="各タレントが出演する番組をどの程度見たいですか？"
       "（好感度4または5の方のみ）")
    q3_choices = ["全く見たくない","あまり見たくない","どちらでもない",
                  "やや見たい","ぜひ見たい"]
    for s in range(SLOTS):
        wr(c3=f"Q3S{s+1}",c4=f"Q3s{s+1}",c5="SA",c6=5,
           c7=COL[f"Q3s{s+1}"],c9=f"スロット{s+1}のタレント")
        for ch, lbl in enumerate(q3_choices, 1):
            wr(c8=ch, c9=lbl)

    # ── Q4 合うジャンル MTX (MA 5択スロット × 5ジャンル) ──
    wr("Q4","MTX",c9="各タレントに合うと思う出演ジャンルをすべてお選びください。"
       "（好感度4または5の方のみ）")
    for g, gname in enumerate(Q4_GENRE_NAMES):
        wr(c3=f"Q4S{g+1}",c5="MA",c6=5,c9=gname)
        for s in range(SLOTS):
            wr(c4=f"Q4s{g+1}c{s+1}",c7=COL[f"Q4s{g+1}c{s+1}"],
               c8=s+1,c9=f"スロット{s+1}")

    # ── STA ──
    wr("STA","D","STA","STA","D","",COL["STA"],"","STA")

    # ── 性別（集計用） ──
    wr("性別","S","性別","性別","SA",3,COL["性別"],"","性別")
    wr(c8=1,c9="男性")
    wr(c8=2,c9="女性")
    wr(c8=0,c9="無回答")

    # ── 年齢（集計用） ──
    wr("年齢","NUM","年齢",c9="年齢")
    wr(c4="年齢",c5="NUM",c7=COL["年齢"],c8=1,c9="年齢")

sz2 = os.path.getsize(LAY) // 1024
print(f"[layout] {LAY}  {sz2}KB")
print("完了！")
