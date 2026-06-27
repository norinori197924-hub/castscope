import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

conn = sqlite3.connect("castscope.db")
c = conn.cursor()

c.execute("""
    SELECT m.name, s.trend_score, s.yt_avg_views, s.news_count, s.wiki_pageviews, s.sns_score_total
    FROM sns_scores s
    JOIN talent_master m ON m.id = s.talent_id
    WHERE s.id IN (SELECT MAX(id) FROM sns_scores GROUP BY talent_id)
    ORDER BY s.sns_score_total DESC NULLS LAST
    LIMIT 20
""")
rows = c.fetchall()

c.execute("SELECT COUNT(*) FROM sns_scores s WHERE s.id IN (SELECT MAX(id) FROM sns_scores GROUP BY talent_id) AND s.sns_score_total IS NOT NULL")
scored = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM sns_scores s WHERE s.id IN (SELECT MAX(id) FROM sns_scores GROUP BY talent_id) AND s.wiki_pageviews IS NOT NULL")
wiki_ok = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM sns_scores s WHERE s.id IN (SELECT MAX(id) FROM sns_scores GROUP BY talent_id) AND s.news_count IS NOT NULL")
news_ok = c.fetchone()[0]
conn.close()

print(f"スコア算出成功: {scored}/300  Wikipedia: {wiki_ok}/300  News: {news_ok}/300")
print("-" * 72)
print(f"{'順位':>3}  {'名前':<14} {'Trends':>7} {'YT avg':>10} {'News':>5} {'Wiki':>8} {'スコア':>7}")
print("-" * 72)
for i, r in enumerate(rows, 1):
    trend = str(r[1]) if r[1] is not None else "-"
    yt    = f"{r[2]:,}" if r[2] is not None else "-"
    news  = str(r[3]) if r[3] is not None else "-"
    wiki  = f"{r[4]:,}" if r[4] is not None else "-"
    sc    = str(r[5]) if r[5] is not None else "-"
    print(f"{i:>3}. {r[0]:<14} {trend:>7} {yt:>10} {news:>5} {wiki:>8} {sc:>7}")
