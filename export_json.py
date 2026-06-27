"""
castscope.db から docs/scores.json を生成する
"""
import sqlite3, json, datetime, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH     = "castscope.db"
OUTPUT_PATH = os.path.join("docs", "scores.json")

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
GENRE_OVERRIDES = {1:"女優", 2:"俳優", 3:"女優", 4:"俳優", 5:"女優"}

def get_genre(tid):
    if tid in GENRE_OVERRIDES:
        return GENRE_OVERRIDES[tid]
    for rng, genre in GENRE_RANGES:
        if tid in rng:
            return genre
    return "その他"

def export():
    if not os.path.exists(DB_PATH):
        print(f"[export] {DB_PATH} が見つかりません", file=sys.stderr)
        sys.exit(1)

    os.makedirs("docs", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # タレントマスター
    c.execute("SELECT id, name, name_en FROM talent_master ORDER BY id")
    masters = {r["id"]: dict(r) for r in c.fetchall()}

    # 最新スコア（スコアがある人は降順、ない人を末尾に）
    c.execute("""
        SELECT s.talent_id, s.collected_at,
               s.trend_score, s.yt_avg_views, s.yt_subscribers,
               s.news_count, s.news_sentiment, s.wiki_pageviews, s.sns_score_total
        FROM sns_scores s
        WHERE s.id IN (SELECT MAX(id) FROM sns_scores GROUP BY talent_id)
        ORDER BY s.sns_score_total DESC NULLS LAST, s.talent_id
    """)
    latest_rows = c.fetchall()

    # 全時系列
    c.execute("""
        SELECT talent_id, collected_at,
               trend_score, yt_avg_views, yt_subscribers,
               news_count, news_sentiment, wiki_pageviews, sns_score_total
        FROM sns_scores
        ORDER BY talent_id, collected_at
    """)
    history_map = {}
    for r in c.fetchall():
        tid = r["talent_id"]
        history_map.setdefault(tid, []).append({
            "date":           r["collected_at"][:10] if r["collected_at"] else None,
            "trend_score":    r["trend_score"],
            "yt_avg_views":   r["yt_avg_views"],
            "yt_subscribers": r["yt_subscribers"],
            "news_count":     r["news_count"],
            "news_sentiment": r["news_sentiment"],
            "wiki_pageviews": r["wiki_pageviews"],
            "score":          r["sns_score_total"],
        })

    conn.close()

    talents      = []
    genre_map    = {}   # ジャンル別タレントリスト（ランキング用）

    for rank, row in enumerate(latest_rows, 1):
        tid   = row["talent_id"]
        m     = masters.get(tid, {})
        genre = get_genre(tid)
        l = {
            "collected_at":   row["collected_at"][:10] if row["collected_at"] else None,
            "trend_score":    row["trend_score"],
            "yt_avg_views":   row["yt_avg_views"],
            "yt_subscribers": row["yt_subscribers"],
            "news_count":     row["news_count"],
            "news_sentiment": row["news_sentiment"],
            "wiki_pageviews": row["wiki_pageviews"],
            "score":          row["sns_score_total"],
        }
        talents.append({
            "rank":    rank,
            "id":      tid,
            "name":    m.get("name", ""),
            "name_en": m.get("name_en", ""),
            "genre":   genre,
            "latest":  l,
            "history": history_map.get(tid, []),
        })
        genre_map.setdefault(genre, []).append({
            "rank":  len(genre_map.get(genre, [])) + 1,
            "id":    tid,
            "name":  m.get("name", ""),
            "score": row["sns_score_total"],
        })

    out = {
        "updated_at":     datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "total":          len(talents),
        "scored":         sum(1 for t in talents if t["latest"]["score"] is not None),
        "talents":        talents,
        "genre_rankings": genre_map,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = os.path.getsize(OUTPUT_PATH) // 1024
    print(f"[export] {OUTPUT_PATH}  {len(talents)} 件  {size_kb} KB")

if __name__ == "__main__":
    export()
