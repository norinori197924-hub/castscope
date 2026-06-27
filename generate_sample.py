#!/usr/bin/env python3
"""
generate_sample.py
CastScope タレント好感度調査 サンプルデータ生成
  docs/sample_rawdata.txt  ... 6,000サンプル × 353列
  docs/sample_layout.txt   ... For Survey 標準形式レイアウト
"""
import re, ast, os, sys, random, datetime, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

random.seed(42)

# ── TALENTS を collect_sns.py から取得 ───────────────────────
def load_talents():
    with open("collect_sns.py", encoding="utf-8") as f:
        lines = f.readlines()
    start = next(
        (i for i, l in enumerate(lines) if re.match(r"\s*TALENTS\s*=\s*\[", l)), None
    )
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

# ── 定数 ────────────────────────────────────────────────────
N_PAT     = 60
N_PER_PAT = 100     # 6000 / 60
N_SS      = N_PAT * N_PER_PAT
SLOTS     = 5
N_GEN     = 5       # ジャンル選択肢数
GENRE_LBL = ["ドラマ・映画", "バラエティ", "音楽", "情報・スポーツ", "ネット・配信"]

# ── パターン割り当て（全300人を60パターン×5スロットに均等配分）
idx = list(range(N))
random.shuffle(idx)
patterns = [idx[i * SLOTS:(i + 1) * SLOTS] for i in range(N_PAT)]

# ── タレントプロファイル ─────────────────────────────────────
# SNSスコア上位（TALENTS先頭）ほど認知率・好感度が高い想定
rng = random.Random(99)
profiles = []
for i in range(N):
    pop = 1.0 - i / N   # 1.0(最上位)→0.0(最下位)

    awareness = max(0.06, min(0.97,
        0.10 + pop * 0.87 + rng.gauss(0, 0.055)))

    # 好感度 SA 5段階 (1=非常に好き, 5=非常に嫌い)
    fav_mu = max(1.4, min(4.6,
        1.75 + (1 - pop) * 2.3 + rng.gauss(0, 0.22)))
    fav_sd = max(0.55, min(1.35, 0.75 + rng.uniform(0, 0.55)))

    # 視聴意向
    int_mu = max(1.4, min(4.6, fav_mu + rng.gauss(0.22, 0.14)))

    # ジャンル適性（各ジャンル 選択確率 0-1）
    g_fit = [max(0.08, min(0.92, rng.gauss(0.44, 0.20))) for _ in range(N_GEN)]

    profiles.append(dict(
        awareness=awareness, fav_mu=fav_mu, fav_sd=fav_sd,
        int_mu=int_mu, g_fit=g_fit
    ))

# ── ヘッダー生成 ─────────────────────────────────────────────
header = (
    ["MID", "START", "END", "TIME", "F1", "F2", "F3", "PAT"]
    + [f"T{s+1}"      for s in range(SLOTS)]
    + [f"Q1c{s+1}"    for s in range(SLOTS)]
    + [f"Q2s{s+1}"    for s in range(SLOTS)]
    + [f"Q3s{s+1}"    for s in range(SLOTS)]
    + [f"Q4s{s+1}c{g+1}" for s in range(SLOTS) for g in range(N_GEN)]
    + [f"Q2c{i+1:03d}" for i in range(N)]
)

# ── ローデータ生成 ────────────────────────────────────────
BASE_DT = datetime.datetime(2025, 11, 1, 9, 0, 0)
rows = []
for resp in range(N_SS):
    pat_idx  = resp // N_PER_PAT
    slots_ti = patterns[pat_idx]        # 5 talent indices (0-based)

    mid = resp + 1
    f1  = 1 + resp % 2                 # 1=男 2=女 均等
    f2  = 1 + (resp // 2) % 5          # 1-5 年代 均等
    f3  = 1 + resp % 8                 # 1-8 地域

    sec      = random.randint(0, 7 * 24 * 3600)
    start_dt = BASE_DT + datetime.timedelta(seconds=sec)
    dur      = random.randint(280, 950)
    end_dt   = start_dt + datetime.timedelta(seconds=dur)

    t_ids = [TALENTS[ti]["id"] for ti in slots_ti]

    # Q1: 認知 (1=知っている 2=知らない)
    q1 = [1 if random.random() < profiles[ti]["awareness"] else 2
          for ti in slots_ti]

    # Q2s: 好感度 per slot (0=未回答)
    q2s = []
    for s, ti in enumerate(slots_ti):
        if q1[s] == 1:
            v = round(random.gauss(profiles[ti]["fav_mu"], profiles[ti]["fav_sd"]))
            q2s.append(max(1, min(5, v)))
        else:
            q2s.append(0)

    # Q3s: 視聴意向 per slot
    q3s = []
    for s, ti in enumerate(slots_ti):
        if q1[s] == 1:
            v = round(random.gauss(profiles[ti]["int_mu"], profiles[ti]["fav_sd"]))
            q3s.append(max(1, min(5, v)))
        else:
            q3s.append(0)

    # Q4: ジャンル適性 MA per slot per genre (0=未回答)
    q4 = []
    for s, ti in enumerate(slots_ti):
        if q1[s] == 1:
            q4.extend(
                1 if random.random() < profiles[ti]["g_fit"][g] else 2
                for g in range(N_GEN)
            )
        else:
            q4.extend([0] * N_GEN)

    # Q2c: per-talent 好感度（rated=1-5, unrated=""）
    q2c = [""] * N
    for s, ti in enumerate(slots_ti):
        if q2s[s] > 0:
            q2c[ti] = str(q2s[s])

    row = (
        [mid,
         start_dt.strftime("%Y/%m/%d %H:%M:%S"),
         end_dt.strftime("%Y/%m/%d %H:%M:%S"),
         dur, f1, f2, f3, pat_idx + 1]
        + t_ids + q1 + q2s + q3s + q4 + q2c
    )
    rows.append(row)

# 書き出し
os.makedirs("docs", exist_ok=True)
raw_path = os.path.join("docs", "sample_rawdata.txt")
with open(raw_path, "w", encoding="utf-8", newline="\n") as f:
    f.write("\t".join(header) + "\n")
    for row in rows:
        f.write("\t".join(str(v) for v in row) + "\n")

sz_kb = os.path.getsize(raw_path) // 1024
print(f"[raw]    {raw_path}  {len(rows)} 行  {sz_kb} KB")

# ── レイアウトファイル生成 ────────────────────────────────
# 列順: 質問番号/質問タイプ/アイテム名/ラベル/回答タイプ/カテゴリ数/カラム/選択肢番号/質問文

def lr(qn, qt, item, lbl, at, cats, col, ch, qtxt):
    return "\t".join([qn, qt, item, lbl, at, str(cats), col, str(ch), qtxt])

lrows = []

# ── 属性 ──
for ch, lbl in enumerate(["男性", "女性"], 1):
    lrows.append(lr("F1","SA","性別","性別","カテゴリ",2,"F1",ch,
                    "あなたの性別をお選びください"))
for ch, lbl in enumerate(["10代","20代","30代","40代","50代以上"], 1):
    lrows.append(lr("F2","SA","年代","年代","カテゴリ",5,"F2",ch,
                    "あなたの年代をお選びください"))
for ch, lbl in enumerate(
        ["北海道","東北","関東","中部","近畿","中国","四国","九州・沖縄"], 1):
    lrows.append(lr("F3","SA","地域","地域","カテゴリ",8,"F3",ch,
                    "お住まいの地域をお選びください"))
lrows.append(lr("PAT","SA","パターン","パターン","カテゴリ",60,"PAT",1,
                "提示パターン番号（1〜60）"))

# ── Q1: 認知 MA（スロットベース）──
for s in range(SLOTS):
    col = f"Q1c{s+1}"
    for ch, lbl in [(1, "知っている"), (2, "知らない")]:
        lrows.append(lr("Q1","MA",f"スロット{s+1}認知",f"スロット{s+1}",
                        "カテゴリ",2,col,ch,
                        f"提示された{s+1}人目のタレントをご存知ですか？"))

# ── Q2: 好感度 SA（タレント個別列 — アップロード機能対応）──
# アイテム名 = タレント名  →  uploader が自動照合するキー列
for i, t in enumerate(TALENTS):
    col = f"Q2c{i+1:03d}"
    for ch, lbl in enumerate(
            ["非常に好き","やや好き","どちらでもない","やや嫌い","非常に嫌い"], 1):
        lrows.append(lr("Q2","SA",t["name"],t["name"],"カテゴリ",5,col,ch,
                        "このタレントへの好感度をお教えください"
                        "（1＝非常に好き ～ 5＝非常に嫌い）"))

# ── Q3: 視聴意向 SA（スロットベース）──
for s in range(SLOTS):
    col = f"Q3s{s+1}"
    for ch, lbl in enumerate(
            ["非常に見たい","やや見たい","どちらでもない",
             "あまり見たくない","全く見たくない"], 1):
        lrows.append(lr("Q3","SA",f"スロット{s+1}視聴意向",f"スロット{s+1}",
                        "カテゴリ",5,col,ch,
                        f"{s+1}人目のタレントが出演する番組をどの程度見たいですか？"))

# ── Q4: 合うジャンル MA（スロット × ジャンル）──
for s in range(SLOTS):
    for g, genre in enumerate(GENRE_LBL, 1):
        col = f"Q4s{s+1}c{g}"
        for ch, lbl in [(1, "合う"), (2, "合わない")]:
            lrows.append(lr("Q4","MA",f"スロット{s+1}_{genre}",genre,
                            "カテゴリ",2,col,ch,
                            f"{s+1}人目のタレントに合うジャンルをお選びください（{genre}）"))

layout_path = os.path.join("docs", "sample_layout.txt")
with open(layout_path, "w", encoding="utf-8", newline="\n") as f:
    for row in lrows:
        f.write(row + "\n")

sz2_kb = os.path.getsize(layout_path) // 1024
print(f"[layout] {layout_path}  {len(lrows)} 行  {sz2_kb} KB")
print("完了！")
