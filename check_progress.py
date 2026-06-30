"""
CastScope 収集進捗確認スクリプト
実行: python check_progress.py
"""

import sqlite3
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

DB_PATH    = "castscope.db"
CACHE_FILE = "channel_cache.json"


def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] {DB_PATH} が見つかりません")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 総タレント数
    c.execute("SELECT COUNT(*) FROM talent_master")
    total = c.fetchone()[0]

    # 各指標の取得済み件数
    c.execute("""
        SELECT
            COUNT(*)                                          AS total_scores,
            SUM(CASE WHEN yt_avg_views   > 0 THEN 1 ELSE 0 END) AS yt_views_ok,
            SUM(CASE WHEN yt_subscribers > 0 THEN 1 ELSE 0 END) AS yt_subs_ok,
            SUM(CASE WHEN trend_score    > 0 THEN 1 ELSE 0 END) AS trends_ok
        FROM (
            SELECT talent_id,
                   MAX(yt_avg_views)   AS yt_avg_views,
                   MAX(yt_subscribers) AS yt_subscribers,
                   MAX(trend_score)    AS trend_score
            FROM sns_scores
            GROUP BY talent_id
        )
    """)
    row = c.fetchone()
    scored, yt_views, yt_subs, trends = row

    def pct(n):
        return f"{n / total * 100:.1f}%" if total else "-"

    print()
    print("=" * 44)
    print("  CastScope 収集進捗")
    print("=" * 44)
    print(f"  総タレント数            : {total} 人")
    print(f"  スコアレコードあり      : {scored} 人")
    print()
    print(f"  YT再生数  取得済        : {yt_views} 人  ({pct(yt_views)})")
    print(f"  YT登録者  取得済        : {yt_subs} 人  ({pct(yt_subs)})")
    print(f"  Trends    取得済        : {trends} 人  ({pct(trends)})")

    # channel_cache.json
    print()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            cache = json.load(f)
        print(f"  channel_cache.json      : {len(cache)} 件")
    else:
        print(f"  channel_cache.json      : なし（未生成）")

    # YT再生数が未取得のタレント（先頭10件）
    c.execute("""
        SELECT m.id, m.name
        FROM talent_master m
        LEFT JOIN (
            SELECT talent_id, MAX(yt_avg_views) AS yt_avg_views
            FROM sns_scores
            GROUP BY talent_id
        ) s ON s.talent_id = m.id
        WHERE s.yt_avg_views IS NULL OR s.yt_avg_views = 0
        ORDER BY m.id
        LIMIT 10
    """)
    unresolved = c.fetchall()

    print()
    print(f"  YT再生数 未取得（先頭10件）")
    print("  " + "-" * 30)
    if unresolved:
        for tid, name in unresolved:
            print(f"    [{tid:>3}] {name}")
    else:
        print("    （全員取得済み）")

    print("=" * 44)
    print()

    conn.close()


if __name__ == "__main__":
    main()
