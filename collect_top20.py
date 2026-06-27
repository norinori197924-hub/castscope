"""ジャンルバランスを考慮した代表20名を再収集して結果を表示する"""
import collect_sns, sqlite3, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TARGET_IDS = [
    1,   # 綾瀬はるか  (女優)
    4,   # 菅田将暉    (俳優)
    11,  # 広瀬すず    (女優)
    47,  # 小栗旬      (俳優)
    57,  # 福山雅治    (俳優・歌手)
    86,  # 明石家さんま (バラエティ)
    90,  # 浜田雅功    (バラエティ)
    111, # 桜井翔      (ジャニーズ/嵐)
    119, # 山下智久    (ジャニーズ)
    137, # 平野紫耀    (ジャニーズ/Number_i)
    146, # 前田敦子    (女性アイドル/元AKB)
    156, # 白石麻衣    (女性アイドル/乃木坂)
    164, # 平手友梨奈  (女性アイドル/元欅坂)
    187, # 宇多田ヒカル (歌手)
    188, # 米津玄師    (歌手)
    213, # Ado         (歌手)
    230, # 若林正恭    (お笑い/オードリー)
    244, # 千鳥ノブ    (お笑い)
    266, # 目黒蓮      (若手/Snow Man)
    272, # 長尾謙杜    (若手/なにわ男子)
]

collect_sns.TALENTS = [t for t in collect_sns.TALENTS if t["id"] in TARGET_IDS]
collect_sns.TALENTS.sort(key=lambda t: TARGET_IDS.index(t["id"]))

collect_sns.collect_all()

# ランキング表示
conn = sqlite3.connect(collect_sns.DB_PATH)
c = conn.cursor()
c.execute("""
    SELECT m.name, s.trend_score, s.yt_avg_views, s.news_count, s.wiki_pageviews, s.sns_score_total
    FROM sns_scores s
    JOIN talent_master m ON m.id = s.talent_id
    WHERE s.id IN (SELECT MAX(id) FROM sns_scores GROUP BY talent_id)
      AND s.talent_id IN ({})
    ORDER BY s.sns_score_total DESC NULLS LAST
""".format(",".join(str(i) for i in TARGET_IDS)))
rows = c.fetchall()
conn.close()

print("\n===== 代表20名 SNSスコアランキング =====")
print(f"{'順位':<4} {'名前':<14} {'Trends':>7} {'YT avg':>10} {'News':>5} {'Wiki':>8} {'スコア':>7}")
print("-" * 65)
for i, r in enumerate(rows, 1):
    trend = str(r[1]) if r[1] is not None else "-"
    yt    = f"{r[2]:,}" if r[2] is not None else "-"
    news  = str(r[3]) if r[3] is not None else "-"
    wiki  = f"{r[4]:,}" if r[4] is not None else "-"
    sc    = str(r[5]) if r[5] is not None else "-"
    print(f"{i:<4} {r[0]:<14} {trend:>7} {yt:>10} {news:>5} {wiki:>8} {sc:>7}")
