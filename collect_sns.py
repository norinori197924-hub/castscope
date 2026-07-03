"""
CastScope SNS Data Collector - 無料版
収集対象: Google Trends / YouTube Data API v3 / NewsAPI / Wikipedia API
実行: python collect_sns.py
定期実行: cron or GitHub Actions (毎週月曜 AM 6:00)
"""

import sqlite3
import json
import time
import datetime
import urllib.request
import urllib.parse
import os
import sys

# ============================================================
# 設定 — ここだけ編集する
# ============================================================

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
NEWS_API_KEY    = os.environ.get("NEWS_API_KEY",    "YOUR_NEWS_API_KEY")

DB_PATH    = "castscope.db"
CACHE_FILE = "channel_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

# タレントリスト（本番は300名）
TALENTS = [
    # ── 既存5名 ──────────────────────────────────────────────
    {"id": 1,   "name": "綾瀬はるか",       "name_en": "Haruka Ayase"},
    {"id": 2,   "name": "木村拓哉",         "name_en": "Takuya Kimura"},
    {"id": 3,   "name": "新垣結衣",         "name_en": "Gakki Aragaki"},
    {"id": 4,   "name": "菅田将暉",         "name_en": "Masaki Suda"},
    {"id": 5,   "name": "石原さとみ",       "name_en": "Satomi Ishihara"},
    # ── 女優 ─────────────────────────────────────────────────
    {"id": 6,   "name": "長澤まさみ",       "name_en": "Masami Nagasawa"},
    {"id": 7,   "name": "深田恭子",         "name_en": "Kyoko Fukada"},
    {"id": 8,   "name": "北川景子",         "name_en": "Keiko Kitagawa"},
    {"id": 9,   "name": "吉高由里子",       "name_en": "Yuriko Yoshitaka"},
    {"id": 10,  "name": "有村架純",         "name_en": "Kasumi Arimura"},
    {"id": 11,  "name": "広瀬すず",         "name_en": "Suzu Hirose"},
    {"id": 12,  "name": "橋本環奈",         "name_en": "Kanna Hashimoto"},
    {"id": 13,  "name": "浜辺美波",         "name_en": "Minami Hamabe"},
    {"id": 14,  "name": "今田美桜",         "name_en": "Mio Imada"},
    {"id": 15,  "name": "永野芽郁",         "name_en": "Mei Nagano"},
    {"id": 16,  "name": "清原果耶",         "name_en": "Kaya Kiyohara"},
    {"id": 17,  "name": "川口春奈",         "name_en": "Haruna Kawaguchi"},
    {"id": 18,  "name": "松岡茉優",         "name_en": "Mayu Matsuoka"},
    {"id": 19,  "name": "小松菜奈",         "name_en": "Nana Komatsu"},
    {"id": 20,  "name": "本田翼",           "name_en": "Tsubasa Honda"},
    {"id": 21,  "name": "戸田恵梨香",       "name_en": "Erika Toda"},
    {"id": 22,  "name": "井上真央",         "name_en": "Mao Inoue"},
    {"id": 23,  "name": "宮崎あおい",       "name_en": "Aoi Miyazaki"},
    {"id": 24,  "name": "上野樹里",         "name_en": "Juri Ueno"},
    {"id": 25,  "name": "満島ひかり",       "name_en": "Hikari Mitsushima"},
    {"id": 26,  "name": "松たか子",         "name_en": "Takako Matsu"},
    {"id": 27,  "name": "天海祐希",         "name_en": "Yuki Amami"},
    {"id": 28,  "name": "米倉涼子",         "name_en": "Ryoko Yonekura"},
    {"id": 29,  "name": "篠原涼子",         "name_en": "Ryoko Shinohara"},
    {"id": 30,  "name": "杉咲花",           "name_en": "Hana Sugisaki"},
    {"id": 31,  "name": "芳根京子",         "name_en": "Kyoko Yoshine"},
    {"id": 32,  "name": "土屋太鳳",         "name_en": "Tao Tsuchiya"},
    {"id": 33,  "name": "黒島結菜",         "name_en": "Yuina Kuroshima"},
    {"id": 34,  "name": "山本美月",         "name_en": "Mizuki Yamamoto"},
    {"id": 35,  "name": "飯豊まりえ",       "name_en": "Marie Iitoyo"},
    {"id": 36,  "name": "木村文乃",         "name_en": "Fumino Kimura"},
    {"id": 37,  "name": "仲間由紀恵",       "name_en": "Yukie Nakama"},
    {"id": 38,  "name": "仲里依紗",         "name_en": "Riisa Naka"},
    {"id": 39,  "name": "菜々緒",           "name_en": "Nanao"},
    {"id": 40,  "name": "武井咲",           "name_en": "Emi Takei"},
    {"id": 41,  "name": "蒼井優",           "name_en": "Yu Aoi"},
    {"id": 42,  "name": "尾野真千子",       "name_en": "Machiko Ono"},
    {"id": 43,  "name": "柴咲コウ",         "name_en": "Ko Shibasaki"},
    {"id": 44,  "name": "水川あさみ",       "name_en": "Asami Mizukawa"},
    {"id": 45,  "name": "倉科カナ",         "name_en": "Kana Kurashina"},
    # ── 俳優 ─────────────────────────────────────────────────
    {"id": 46,  "name": "佐藤健",           "name_en": "Ken Sato"},
    {"id": 47,  "name": "小栗旬",           "name_en": "Shun Oguri"},
    {"id": 48,  "name": "妻夫木聡",         "name_en": "Satoshi Tsumabuki"},
    {"id": 49,  "name": "西島秀俊",         "name_en": "Hidetoshi Nishijima"},
    {"id": 50,  "name": "阿部寛",           "name_en": "Hiroshi Abe"},
    {"id": 51,  "name": "坂口健太郎",       "name_en": "Kentaro Sakaguchi"},
    {"id": 52,  "name": "横浜流星",         "name_en": "Ryusei Yokohama"},
    {"id": 53,  "name": "吉沢亮",           "name_en": "Ryo Yoshizawa"},
    {"id": 54,  "name": "向井理",           "name_en": "Osamu Mukai"},
    {"id": 55,  "name": "竹内涼真",         "name_en": "Ryoma Takeuchi"},
    {"id": 56,  "name": "堺雅人",           "name_en": "Masato Sakai"},
    {"id": 57,  "name": "福山雅治",         "name_en": "Masaharu Fukuyama"},
    {"id": 58,  "name": "岡田准一",         "name_en": "Junichi Okada"},
    {"id": 59,  "name": "福士蒼汰",         "name_en": "Sota Fukushi"},
    {"id": 60,  "name": "賀来賢人",         "name_en": "Kento Kaku"},
    {"id": 61,  "name": "高橋一生",         "name_en": "Issei Takahashi"},
    {"id": 62,  "name": "斎藤工",           "name_en": "Takumi Saito"},
    {"id": 63,  "name": "玉木宏",           "name_en": "Hiroshi Tamaki"},
    {"id": 64,  "name": "藤木直人",         "name_en": "Naohito Fujiki"},
    {"id": 65,  "name": "内野聖陽",         "name_en": "Masaharu Uchino"},
    {"id": 66,  "name": "江口洋介",         "name_en": "Yosuke Eguchi"},
    {"id": 67,  "name": "森山未來",         "name_en": "Mirai Moriyama"},
    {"id": 68,  "name": "岡田将生",         "name_en": "Masaki Okada"},
    {"id": 69,  "name": "松坂桃李",         "name_en": "Tori Matsuzaka"},
    {"id": 70,  "name": "鈴木亮平",         "name_en": "Ryohei Suzuki"},
    {"id": 71,  "name": "綾野剛",           "name_en": "Go Ayano"},
    {"id": 72,  "name": "瑛太",             "name_en": "Eita"},
    {"id": 73,  "name": "大泉洋",           "name_en": "Yo Oizumi"},
    {"id": 74,  "name": "山田涼介",         "name_en": "Ryosuke Yamada"},
    {"id": 75,  "name": "田中圭",           "name_en": "Kei Tanaka"},
    {"id": 76,  "name": "間宮祥太朗",       "name_en": "Shotaro Mamiya"},
    {"id": 77,  "name": "山崎賢人",         "name_en": "Kento Yamazaki"},
    {"id": 78,  "name": "北村匠海",         "name_en": "Takumi Kitamura"},
    {"id": 79,  "name": "板垣李光人",       "name_en": "Rihito Itagaki"},
    {"id": 80,  "name": "鈴鹿央士",         "name_en": "Oji Suzuka"},
    {"id": 81,  "name": "神尾楓珠",         "name_en": "Fuuju Kamio"},
    {"id": 82,  "name": "中川大志",         "name_en": "Taishi Nakagawa"},
    {"id": 83,  "name": "赤楚衛二",         "name_en": "Eiji Akaso"},
    {"id": 84,  "name": "眞栄田郷敦",       "name_en": "Goud Maeda"},
    {"id": 85,  "name": "磯村勇斗",         "name_en": "Hayato Isomura"},
    # ── バラエティタレント ───────────────────────────────────
    {"id": 86,  "name": "明石家さんま",     "name_en": "Sanma Akashiya"},
    {"id": 87,  "name": "タモリ",           "name_en": "Tamori"},
    {"id": 88,  "name": "所ジョージ",       "name_en": "George Tokoro"},
    {"id": 89,  "name": "松本人志",         "name_en": "Hitoshi Matsumoto"},
    {"id": 90,  "name": "浜田雅功",         "name_en": "Masatoshi Hamada"},
    {"id": 91,  "name": "内村光良",         "name_en": "Mitsuyoshi Uchimura"},
    {"id": 92,  "name": "出川哲朗",         "name_en": "Tetsuro Degawa"},
    {"id": 93,  "name": "東野幸治",         "name_en": "Koji Higashino"},
    {"id": 94,  "name": "有田哲平",         "name_en": "Teppei Arita"},
    {"id": 95,  "name": "博多大吉",         "name_en": "Daikichi Hakata"},
    {"id": 96,  "name": "博多華丸",         "name_en": "Hanamaru Hakata"},
    {"id": 97,  "name": "関根勤",           "name_en": "Tsutomu Sekine"},
    {"id": 98,  "name": "劇団ひとり",       "name_en": "Gekidan Hitori"},
    {"id": 99,  "name": "千原ジュニア",     "name_en": "Junior Chihara"},
    {"id": 100, "name": "今田耕司",         "name_en": "Koji Imada"},
    {"id": 101, "name": "麒麟川島明",       "name_en": "Akira Kawashima"},
    {"id": 102, "name": "岡村隆史",         "name_en": "Takashi Okamura"},
    {"id": 103, "name": "加藤浩次",         "name_en": "Koji Kato"},
    {"id": 104, "name": "宮川大輔",         "name_en": "Daisuke Miyagawa"},
    {"id": 105, "name": "田村淳",           "name_en": "Atsushi Tamura"},
    {"id": 106, "name": "太田光",           "name_en": "Hikari Ota"},
    {"id": 107, "name": "田中裕二",         "name_en": "Yuji Tanaka"},
    {"id": 108, "name": "上田晋也",         "name_en": "Shinya Ueda"},
    {"id": 109, "name": "品川祐",           "name_en": "Tasuku Shinagawa"},
    {"id": 110, "name": "勝俣州和",         "name_en": "Kunikazu Katsumata"},
    # ── ジャニーズ系アイドル ─────────────────────────────────
    {"id": 111, "name": "桜井翔",           "name_en": "Sho Sakurai"},
    {"id": 112, "name": "相葉雅紀",         "name_en": "Masaki Aiba"},
    {"id": 113, "name": "大野智",           "name_en": "Satoshi Ohno"},
    {"id": 114, "name": "香取慎吾",         "name_en": "Shingo Katori"},
    {"id": 115, "name": "稲垣吾郎",         "name_en": "Goro Inagaki"},
    {"id": 116, "name": "草彅剛",           "name_en": "Tsuyoshi Kusanagi"},
    {"id": 117, "name": "中居正広",         "name_en": "Masahiro Nakai"},
    {"id": 118, "name": "亀梨和也",         "name_en": "Kazuya Kamenashi"},
    {"id": 119, "name": "山下智久",         "name_en": "Tomohisa Yamashita"},
    {"id": 120, "name": "国分太一",         "name_en": "Taichi Kokubun"},
    {"id": 121, "name": "長瀬智也",         "name_en": "Tomoya Nagase"},
    {"id": 122, "name": "松岡昌宏",         "name_en": "Masahiro Matsuoka"},
    {"id": 123, "name": "堂本光一",         "name_en": "Koichi Domoto"},
    {"id": 124, "name": "堂本剛",           "name_en": "Tsuyoshi Domoto"},
    {"id": 125, "name": "錦戸亮",           "name_en": "Ryo Nishikido"},
    {"id": 126, "name": "大倉忠義",         "name_en": "Tadayoshi Ohkura"},
    {"id": 127, "name": "丸山隆平",         "name_en": "Ryuhei Maruyama"},
    {"id": 128, "name": "村上信五",         "name_en": "Shingo Murakami"},
    {"id": 129, "name": "中丸雄一",         "name_en": "Yuichi Nakamaru"},
    {"id": 130, "name": "上田竜也",         "name_en": "Tatsuya Ueda"},
    {"id": 131, "name": "二宮和也",         "name_en": "Kazunari Ninomiya"},
    {"id": 132, "name": "松本潤",           "name_en": "Jun Matsumoto"},
    {"id": 133, "name": "知念侑李",         "name_en": "Yuri Chinen"},
    {"id": 134, "name": "有岡大貴",         "name_en": "Daiki Arioka"},
    {"id": 135, "name": "菊池風磨",         "name_en": "Fuma Kikuchi"},
    {"id": 136, "name": "中島健人",         "name_en": "Kento Nakajima"},
    {"id": 137, "name": "平野紫耀",         "name_en": "Sho Hirano"},
    {"id": 138, "name": "永瀬廉",           "name_en": "Ren Nagase"},
    {"id": 139, "name": "高橋海人",         "name_en": "Kaito Takahashi"},
    {"id": 140, "name": "岸優太",           "name_en": "Yuta Kishi"},
    {"id": 141, "name": "神宮寺勇太",       "name_en": "Yuta Jinguji"},
    {"id": 142, "name": "道枝駿佑",         "name_en": "Shunsuke Michieda"},
    {"id": 143, "name": "大西流星",         "name_en": "Ryusei Onishi"},
    {"id": 144, "name": "西畑大吾",         "name_en": "Daigo Nishihata"},
    {"id": 145, "name": "高橋恭平",         "name_en": "Kyohei Takahashi"},
    # ── 女性アイドル ─────────────────────────────────────────
    {"id": 146, "name": "前田敦子",         "name_en": "Atsuko Maeda"},
    {"id": 147, "name": "大島優子",         "name_en": "Yuko Oshima"},
    {"id": 148, "name": "渡辺麻友",         "name_en": "Mayu Watanabe"},
    {"id": 149, "name": "指原莉乃",         "name_en": "Rino Sashihara"},
    {"id": 150, "name": "柏木由紀",         "name_en": "Yuki Kashiwagi"},
    {"id": 151, "name": "横山由依",         "name_en": "Yui Yokoyama"},
    {"id": 152, "name": "向井地美音",       "name_en": "Mion Mukaichi"},
    {"id": 153, "name": "松井珠理奈",       "name_en": "Jurina Matsui"},
    {"id": 154, "name": "須田亜香里",       "name_en": "Akari Suda"},
    {"id": 155, "name": "生田絵梨花",       "name_en": "Erika Ikuta"},
    {"id": 156, "name": "白石麻衣",         "name_en": "Mai Shiraishi"},
    {"id": 157, "name": "西野七瀬",         "name_en": "Nanase Nishino"},
    {"id": 158, "name": "齋藤飛鳥",         "name_en": "Asuka Saito"},
    {"id": 159, "name": "山下美月",         "name_en": "Mizuki Yamashita"},
    {"id": 160, "name": "賀喜遥香",         "name_en": "Haruka Kaki"},
    {"id": 161, "name": "遠藤さくら",       "name_en": "Sakura Endo"},
    {"id": 162, "name": "与田祐希",         "name_en": "Yuki Yoda"},
    {"id": 163, "name": "久保史緒里",       "name_en": "Shiori Kubo"},
    {"id": 164, "name": "平手友梨奈",       "name_en": "Yurina Hirate"},
    {"id": 165, "name": "森田ひかる",       "name_en": "Hikaru Morita"},
    {"id": 166, "name": "藤吉夏鈴",         "name_en": "Karin Fujiyoshi"},
    {"id": 167, "name": "小坂菜緒",         "name_en": "Nao Kosaka"},
    {"id": 168, "name": "加藤史帆",         "name_en": "Shiho Kato"},
    {"id": 169, "name": "佐々木久美",       "name_en": "Kumi Sasaki"},
    {"id": 170, "name": "上村ひなの",       "name_en": "Hinano Kamimura"},
    {"id": 171, "name": "鈴木愛理",         "name_en": "Airi Suzuki"},
    {"id": 172, "name": "矢島舞美",         "name_en": "Maimi Yajima"},
    {"id": 173, "name": "三吉彩花",         "name_en": "Ayaka Miyoshi"},
    {"id": 174, "name": "池田エライザ",     "name_en": "Elaiza Ikeda"},
    {"id": 175, "name": "今泉佑唯",         "name_en": "Yui Imaizumi"},
    {"id": 176, "name": "道重さゆみ",       "name_en": "Sayumi Michishige"},
    {"id": 177, "name": "田中れいな",       "name_en": "Reina Tanaka"},
    {"id": 178, "name": "上白石萌音",       "name_en": "Mone Kamishiraishi"},
    {"id": 179, "name": "上白石萌歌",       "name_en": "Moka Kamishiraishi"},
    {"id": 180, "name": "南沙良",           "name_en": "Sara Minami"},
    {"id": 181, "name": "守屋茜",           "name_en": "Akane Moriya"},
    {"id": 182, "name": "佐々木莉佳子",     "name_en": "Rikako Sasaki"},
    {"id": 183, "name": "出口夏希",         "name_en": "Natsuki Deguchi"},
    {"id": 184, "name": "古川琴音",         "name_en": "Kotone Furukawa"},
    {"id": 185, "name": "山田杏奈",         "name_en": "Anna Yamada"},
    # ── 歌手・アーティスト ───────────────────────────────────
    {"id": 186, "name": "浜崎あゆみ",       "name_en": "Ayumi Hamasaki"},
    {"id": 187, "name": "宇多田ヒカル",     "name_en": "Hikaru Utada"},
    {"id": 188, "name": "米津玄師",         "name_en": "Kenshi Yonezu"},
    {"id": 189, "name": "星野源",           "name_en": "Gen Hoshino"},
    {"id": 190, "name": "あいみょん",       "name_en": "Aimyon"},
    {"id": 191, "name": "椎名林檎",         "name_en": "Ringo Sheena"},
    {"id": 192, "name": "倉木麻衣",         "name_en": "Mai Kuraki"},
    {"id": 193, "name": "西野カナ",         "name_en": "Kana Nishino"},
    {"id": 194, "name": "中島みゆき",       "name_en": "Miyuki Nakajima"},
    {"id": 195, "name": "松任谷由実",       "name_en": "Yumi Matsutoya"},
    {"id": 196, "name": "竹内まりや",       "name_en": "Mariya Takeuchi"},
    {"id": 197, "name": "坂本真綾",         "name_en": "Maaya Sakamoto"},
    {"id": 198, "name": "平井堅",           "name_en": "Ken Hirai"},
    {"id": 199, "name": "桑田佳祐",         "name_en": "Keisuke Kuwata"},
    {"id": 200, "name": "越智志帆",         "name_en": "Shiho Ochi"},
    {"id": 201, "name": "三浦大知",         "name_en": "Daichi Miura"},
    {"id": 202, "name": "清水翔太",         "name_en": "Shota Shimizu"},
    {"id": 203, "name": "今市隆二",         "name_en": "Ryuji Imaichi"},
    {"id": 204, "name": "登坂広臣",         "name_en": "Hiroomi Tosaka"},
    {"id": 205, "name": "藤原聡",           "name_en": "Satoshi Fujiwara"},
    {"id": 206, "name": "常田大希",         "name_en": "Daiki Tsuneta"},
    {"id": 207, "name": "Ayase",            "name_en": "Ayase"},
    {"id": 208, "name": "ikura",            "name_en": "Ikura"},
    {"id": 209, "name": "安室奈美恵",       "name_en": "Namie Amuro"},
    {"id": 210, "name": "大黒摩季",         "name_en": "Maki Oguro"},
    {"id": 211, "name": "一青窈",           "name_en": "Yo Hitoto"},
    {"id": 212, "name": "藤井風",           "name_en": "Kaze Fujii"},
    {"id": 213, "name": "Ado",             "name_en": "Ado"},
    {"id": 214, "name": "Vaundy",          "name_en": "Vaundy"},
    {"id": 215, "name": "優里",             "name_en": "Yuri"},
    {"id": 216, "name": "長屋晴子",         "name_en": "Haruko Nagaya"},
    {"id": 217, "name": "野田洋次郎",       "name_en": "Yojiro Noda"},
    {"id": 218, "name": "北川悠仁",         "name_en": "Yujin Kitagawa"},
    {"id": 219, "name": "井口理",           "name_en": "Satoru Iguchi"},
    {"id": 220, "name": "R-指定",           "name_en": "R-Shitei"},
    {"id": 221, "name": "DJ松永",           "name_en": "DJ Matsunaga"},
    {"id": 222, "name": "大森元貴",         "name_en": "Motoki Omori"},
    {"id": 223, "name": "瑛人",             "name_en": "Eito"},
    {"id": 224, "name": "RYUHEI",          "name_en": "Ryuhei"},
    {"id": 225, "name": "MAKO",            "name_en": "Mako"},
    # ── お笑い芸人 ───────────────────────────────────────────
    {"id": 226, "name": "西野亮廣",         "name_en": "Akihiro Nishino"},
    {"id": 227, "name": "梶原雄太",         "name_en": "Yuta Kajiwara"},
    {"id": 228, "name": "日村勇紀",         "name_en": "Yuuki Himura"},
    {"id": 229, "name": "設楽統",           "name_en": "Osamu Shitara"},
    {"id": 230, "name": "若林正恭",         "name_en": "Masayasu Wakabayashi"},
    {"id": 231, "name": "春日俊彰",         "name_en": "Toshiaki Kasuga"},
    {"id": 232, "name": "伊達みきお",       "name_en": "Mikio Date"},
    {"id": 233, "name": "富澤たけし",       "name_en": "Takeshi Tomizawa"},
    {"id": 234, "name": "石田明",           "name_en": "Akira Ishida"},
    {"id": 235, "name": "井上裕介",         "name_en": "Yusuke Inoue"},
    {"id": 236, "name": "澤部佑",           "name_en": "Yu Sawabe"},
    {"id": 237, "name": "岩井勇気",         "name_en": "Yuki Iwai"},
    {"id": 238, "name": "せいや",           "name_en": "Seiya"},
    {"id": 239, "name": "粗品",             "name_en": "Soshina"},
    {"id": 240, "name": "駒場孝",           "name_en": "Takashi Komaba"},
    {"id": 241, "name": "内海崇",           "name_en": "Takashi Utsumi"},
    {"id": 242, "name": "長谷川雅紀",       "name_en": "Masanori Hasegawa"},
    {"id": 243, "name": "渡辺隆",           "name_en": "Takashi Watanabe"},
    {"id": 244, "name": "千鳥ノブ",         "name_en": "Nobu Chidori"},
    {"id": 245, "name": "千鳥大悟",         "name_en": "Daigo Chidori"},
    {"id": 246, "name": "シュウペイ",       "name_en": "Shupei"},
    {"id": 247, "name": "松陰寺太勇",       "name_en": "Tayu Shoin-ji"},
    {"id": 248, "name": "山内健司",         "name_en": "Kenji Yamauchi"},
    {"id": 249, "name": "濱家隆一",         "name_en": "Ryuichi Hamaya"},
    {"id": 250, "name": "盛山晋太郎",       "name_en": "Shintaro Moriyama"},
    {"id": 251, "name": "リリー",           "name_en": "Lily"},
    {"id": 252, "name": "かたまり",         "name_en": "Katamari"},
    {"id": 253, "name": "もぐら",           "name_en": "Mogura"},
    {"id": 254, "name": "藤本敏史",         "name_en": "Toshifumi Fujimoto"},
    {"id": 255, "name": "原西孝幸",         "name_en": "Takayuki Haranishi"},
    {"id": 256, "name": "田村亮",           "name_en": "Ryo Tamura"},
    {"id": 257, "name": "笑い飯哲夫",       "name_en": "Tetsuo Waraiji"},
    {"id": 258, "name": "西田幸治",         "name_en": "Koji Nishida"},
    {"id": 259, "name": "長田庄平",         "name_en": "Shohei Osada"},
    {"id": 260, "name": "松尾駿",           "name_en": "Shun Matsuo"},
    {"id": 261, "name": "兼近大樹",         "name_en": "Taiki Kanechika"},
    {"id": 262, "name": "りんたろー。",     "name_en": "Rintaro"},
    {"id": 263, "name": "髙比良くるま",     "name_en": "Kuruma Takahira"},
    {"id": 264, "name": "ケムリ",           "name_en": "Kemuri"},
    {"id": 265, "name": "令和ロマン・くるま", "name_en": "Kuruma"},
    # ── 若手・注目株 ─────────────────────────────────────────
    {"id": 266, "name": "目黒蓮",           "name_en": "Ren Meguro"},
    {"id": 267, "name": "向井康二",         "name_en": "Koji Mukai"},
    {"id": 268, "name": "ラウール",         "name_en": "Raul"},
    {"id": 269, "name": "佐久間大介",       "name_en": "Daisuke Sakuma"},
    {"id": 270, "name": "阿部亮平",         "name_en": "Ryohei Abe"},
    {"id": 271, "name": "渡辺翔太",         "name_en": "Shota Watanabe"},
    {"id": 272, "name": "長尾謙杜",         "name_en": "Kento Nagao"},
    {"id": 273, "name": "藤原丈一郎",       "name_en": "Joichiro Fujiwara"},
    {"id": 274, "name": "大橋和也",         "name_en": "Kazuya Ohashi"},
    {"id": 275, "name": "奈緒",             "name_en": "Nao"},
    {"id": 276, "name": "福本莉子",         "name_en": "Riko Fukumoto"},
    {"id": 277, "name": "桜田ひより",       "name_en": "Hiyori Sakurada"},
    {"id": 278, "name": "松本穂香",         "name_en": "Honoka Matsumoto"},
    {"id": 279, "name": "新木優子",         "name_en": "Yuko Araki"},
    {"id": 280, "name": "吉川愛",           "name_en": "Ai Yoshikawa"},
    {"id": 281, "name": "仲野太賀",         "name_en": "Taiga Nakano"},
    {"id": 282, "name": "満島真之介",       "name_en": "Shinnosuke Mitsushima"},
    {"id": 283, "name": "松村北斗",         "name_en": "Hokuto Matsumura"},
    {"id": 284, "name": "田中樹",           "name_en": "Juri Tanaka"},
    {"id": 285, "name": "髙地優吾",         "name_en": "Yugo Kochi"},
    {"id": 286, "name": "ジェシー",         "name_en": "Jesse"},
    {"id": 287, "name": "京本大我",         "name_en": "Taiga Kyomoto"},
    {"id": 288, "name": "森本慎太郎",       "name_en": "Shintaro Morimoto"},
    {"id": 289, "name": "岩本照",           "name_en": "Hikaru Iwamoto"},
    {"id": 290, "name": "SHUNTO",          "name_en": "Shunto"},
    {"id": 291, "name": "MANATO",          "name_en": "Manato"},
    {"id": 292, "name": "望月琉叶",         "name_en": "Ruka Mochizuki"},
    {"id": 293, "name": "菅原咲月",         "name_en": "Sazuki Sugawara"},
    {"id": 294, "name": "井上咲楽",         "name_en": "Sakura Inoue"},
    {"id": 295, "name": "渡邊圭祐",         "name_en": "Keisuke Watanabe"},
    {"id": 296, "name": "福本大晴",         "name_en": "Hirosumi Fukumoto"},
    {"id": 297, "name": "小瀧望",           "name_en": "Nozomu Kotaki"},
    {"id": 298, "name": "岡崎紗絵",         "name_en": "Sae Okazaki"},
    {"id": 299, "name": "池田美優",         "name_en": "Miyu Ikeda"},
    {"id": 300, "name": "橋本涼",           "name_en": "Ryo Hashimoto"},
]

# ============================================================
# DB初期化
# ============================================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS talent_master (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            name_en TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sns_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            talent_id INTEGER NOT NULL,
            collected_at TEXT NOT NULL,
            -- Google Trends
            trend_score INTEGER,
            trend_peak INTEGER,
            -- YouTube
            yt_video_count INTEGER,
            yt_total_views INTEGER,
            yt_avg_views INTEGER,
            yt_subscribers INTEGER,
            yt_sub_score REAL,
            -- News
            news_count INTEGER,
            news_sentiment INTEGER,
            -- Wikipedia
            wiki_pageviews INTEGER,
            -- 総合スコア
            sns_score_total REAL,
            FOREIGN KEY (talent_id) REFERENCES talent_master(id)
        )
    """)
    # 既存DBへの列追加（ALTER TABLE は列が無い場合のみ実行）
    for col, typedef in [
        ("yt_subscribers",  "INTEGER"),
        ("yt_sub_score",    "REAL"),
        ("news_sentiment",  "INTEGER"),
    ]:
        try:
            c.execute(f"ALTER TABLE sns_scores ADD COLUMN {col} {typedef}")
        except Exception:
            pass
    c.execute("""
        CREATE TABLE IF NOT EXISTS collect_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT,
            status TEXT,
            message TEXT
        )
    """)
    # タレントマスター投入
    for t in TALENTS:
        c.execute("""
            INSERT OR IGNORE INTO talent_master (id, name, name_en)
            VALUES (?, ?, ?)
        """, (t["id"], t["name"], t["name_en"]))
    conn.commit()
    conn.close()
    print("[DB] 初期化完了")

# ============================================================
# 1. Google Trends（pytrends）
# ============================================================

def fetch_google_trends(talent_name):
    """
    Google Trends から過去7日の検索関心度を取得
    返り値: {"score": 平均値, "peak": 最大値}
    レート制限対策: リクエスト直前15秒待機 + 429時は45秒待って1回だけリトライ
    # 300人 × 15秒 = 75分（Trends成功時）
    # 429発生時 +45秒/人（最大）
    # 合計：最大約150分（2時間30分）以内
    """
    print(f"[TRENDS START] {talent_name}")
    for attempt in range(3):
        try:
            time.sleep(15)
            from pytrends.request import TrendReq
            pt = TrendReq(hl="ja-JP", tz=540, timeout=(10, 25))
            pt.build_payload([talent_name], timeframe="now 7-d", geo="JP")
            df = pt.interest_over_time()
            if df.empty or talent_name not in df.columns:
                return {"score": None, "peak": None}
            series = df[talent_name]
            return {
                "score": int(series.mean()),
                "peak":  int(series.max()),
            }
        except Exception as e:
            print(f"[TRENDS ERROR] {talent_name} (attempt {attempt + 1}/3): {type(e).__name__}: {e}")
            if "429" in str(e) or "TooManyRequests" in str(e):
                if attempt == 0:
                    print(f"[TRENDS WAIT] {talent_name}: 45秒待機してリトライ")
                    time.sleep(45)
                    continue  # 1回だけリトライ
                else:
                    print(f"[TRENDS SKIP] {talent_name}: レート制限のためスキップ")
                    break
            if attempt < 2:
                time.sleep(20)
    return {"score": None, "peak": None}

# ============================================================
# 2. YouTube Data API v3（無料）
# ============================================================

def fetch_youtube_data(talent_name, cache):
    """
    チャンネルID（キャッシュ優先）→ 登録者数 → 最新動画再生数 を一括取得
    キャッシュあり: channels.list(1) + playlistItems.list(1) + videos.list(1) = 3 units
    キャッシュなし: search.list(100) + 上記 = 103 units
    返り値: {video_count, total_views, avg_views, subscribers, sub_score}
    """
    null_result = {
        "video_count": None, "total_views": None, "avg_views": None,
        "subscribers": None, "sub_score": None,
    }
    if not YOUTUBE_API_KEY:
        print(f"  [YouTube] APIキー未設定 → スキップ")
        return null_result

    print(f"[YOUTUBE START] {talent_name}")
    import math

    # ① チャンネルID取得（キャッシュ優先: search.list 100units をスキップ）
    channel_id = cache.get(talent_name)
    if not channel_id:
        try:
            q = urllib.parse.quote(talent_name)
            url = (
                f"https://www.googleapis.com/youtube/v3/search"
                f"?part=id&q={q}&type=channel&regionCode=JP&maxResults=3&key={YOUTUBE_API_KEY}"
            )
            with urllib.request.urlopen(url, timeout=10) as r:
                items = json.loads(r.read())["items"]
            if items:
                channel_id = items[0]["id"]["channelId"]
                cache[talent_name] = channel_id
                save_cache(cache)
        except Exception as e:
            print(f"[YOUTUBE ERROR] {talent_name} channel search: {type(e).__name__}: {e}")

    if not channel_id:
        return null_result

    # ② チャンネル統計（登録者数 + uploadsプレイリストID）: channels.list 1unit
    subscribers = None
    sub_score = None
    uploads_playlist = None
    try:
        stats_url = (
            f"https://www.googleapis.com/youtube/v3/channels"
            f"?part=statistics,contentDetails&id={channel_id}&key={YOUTUBE_API_KEY}"
        )
        with urllib.request.urlopen(stats_url, timeout=10) as r:
            ch_items = json.loads(r.read())["items"]
        if ch_items:
            subs = int(ch_items[0]["statistics"].get("subscriberCount", 0))
            if subs > 0:
                subscribers = subs
                sub_score = round(min(math.log10(subs + 1) / 7 * 100, 100), 1)
            uploads_playlist = (
                ch_items[0].get("contentDetails", {})
                           .get("relatedPlaylists", {})
                           .get("uploads")
            )
    except Exception as e:
        print(f"[YOUTUBE ERROR] {talent_name} channels.list: {type(e).__name__}: {e}")

    # ③ 最新10動画の再生数: playlistItems.list(1) + videos.list(1) = 2units
    video_count = None
    total_views = None
    avg_views = None
    if uploads_playlist:
        try:
            pl_url = (
                f"https://www.googleapis.com/youtube/v3/playlistItems"
                f"?part=contentDetails&playlistId={uploads_playlist}"
                f"&maxResults=10&key={YOUTUBE_API_KEY}"
            )
            with urllib.request.urlopen(pl_url, timeout=10) as r:
                pl_items = json.loads(r.read())["items"]
            if pl_items:
                video_ids = ",".join(i["contentDetails"]["videoId"] for i in pl_items)
                v_url = (
                    f"https://www.googleapis.com/youtube/v3/videos"
                    f"?part=statistics&id={video_ids}&key={YOUTUBE_API_KEY}"
                )
                with urllib.request.urlopen(v_url, timeout=10) as r:
                    videos = json.loads(r.read())["items"]
                total = sum(int(v["statistics"].get("viewCount", 0)) for v in videos)
                count = len(videos)
                video_count = count
                total_views = total
                avg_views = total // count if count else 0
        except Exception as e:
            print(f"[YOUTUBE ERROR] {talent_name} videos: {type(e).__name__}: {e}")

    return {
        "video_count": video_count,
        "total_views": total_views,
        "avg_views":   avg_views,
        "subscribers": subscribers,
        "sub_score":   sub_score,
    }

# ============================================================
# 3. NewsAPI（無料 開発者プラン: 月100件）
# ============================================================

_POS_WORDS = ["主演","出演","受賞","1位","話題","人気","決定","共演","初","新",
              "映画","ドラマ","CM","写真集","ツアー","コンサート","結婚","おめでとう"]
_NEG_WORDS = ["炎上","批判","謝罪","スキャンダル","降板","問題","騒動","疑惑",
              "不倫","逮捕","書類送検","暴行","ハラスメント","引退","解雇","契約解除"]

def fetch_news(talent_name):
    """
    過去7日のニュース件数と感情スコアを取得
    Google News RSS（無料・認証不要）を使用。
    返り値: {"count": N, "sentiment": 0-100}
    """
    try:
        import xml.etree.ElementTree as ET
        q = urllib.parse.quote(talent_name)
        url = f"https://news.google.com/rss/search?q={q}&hl=ja&gl=JP&ceid=JP:ja"
        req = urllib.request.Request(url, headers={"User-Agent": "CastScope/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            tree = ET.parse(r)
        items = tree.findall(".//item")
        count = len(items)
        pos = neg = 0
        for item in items:
            title = (item.findtext("title") or "") + (item.findtext("description") or "")
            pos += any(w in title for w in _POS_WORDS)
            neg += any(w in title for w in _NEG_WORDS)
        if pos + neg > 0:
            sentiment = round(pos / (pos + neg) * 100)
        else:
            sentiment = 50
        return {"count": count, "sentiment": sentiment}
    except Exception as e:
        print(f"  [News ERROR] {talent_name}: {e}")
        return {"count": None, "sentiment": None}

# ============================================================
# 4. Wikipedia Pageviews API（完全無料・認証不要）
# ============================================================

def fetch_wikipedia(talent_name):
    """
    直近30日のWikipedia閲覧数を取得（認証不要）
    返り値: {"pageviews": N}
    """
    try:
        import requests
        end   = datetime.datetime.now(datetime.timezone.utc)
        start = end - datetime.timedelta(days=30)
        s_str = start.strftime("%Y%m%d")
        e_str = end.strftime("%Y%m%d")
        encoded = urllib.parse.quote(talent_name.replace(" ", "_"), safe='')
        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
            f"/ja.wikipedia/all-access/all-agents/{encoded}/daily/{s_str}/{e_str}"
        )
        r = requests.get(url, headers={"User-Agent": "CastScope/1.0"}, timeout=10)
        r.raise_for_status()
        items = r.json().get("items", [])
        total = sum(i.get("views", 0) for i in items)
        return {"pageviews": total}
    except Exception as e:
        print(f"  [Wikipedia ERROR] {talent_name}: {e}")
        return {"pageviews": None}

# ============================================================
# 5. SNSスコア統合計算
# ============================================================

def calc_score(trends, youtube, news, wiki, sentiment=None, yt_sub=None):
    """
    各指標を0-100に正規化して加重平均
    weights: Trends 25% / YTavg 25% / News件数 15% / Wiki 10% / News感情 15% / YT登録者 10%
    """
    import math
    scores = []
    weights = []

    # Google Trends (0-100 が元々の単位)
    if trends["score"] is not None:
        scores.append(min(trends["score"], 100))
        weights.append(25)

    # YouTube avg_views を対数スケールで0-100化
    if youtube["avg_views"] is not None and youtube["avg_views"] > 0:
        yt_score = min(100, math.log10(youtube["avg_views"] + 1) / 6 * 100)
        scores.append(yt_score)
        weights.append(25)

    # News件数 (300件以上で満点)
    if news["count"] is not None:
        scores.append(min(news["count"] / 3, 100))
        weights.append(15)

    # Wikipedia (月10万PV以上で満点)
    if wiki["pageviews"] is not None:
        scores.append(min(wiki["pageviews"] / 1000, 100))
        weights.append(10)

    # News感情スコア (0-100)
    sent = (sentiment or {}).get("sentiment") if isinstance(sentiment, dict) else sentiment
    if sent is None and news.get("sentiment") is not None:
        sent = news["sentiment"]
    if sent is not None:
        scores.append(sent)
        weights.append(15)

    # YouTube登録者スコア (0-100)
    sub_score = None
    if yt_sub is not None:
        sub_score = yt_sub.get("sub_score")
    if sub_score is not None:
        scores.append(sub_score)
        weights.append(10)

    if not scores:
        return None
    total_w = sum(weights)
    return round(sum(s * w for s, w in zip(scores, weights)) / total_w, 1)

# ============================================================
# メイン処理
# ============================================================

def collect_all():
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*50}")
    print(f"CastScope SNS収集開始: {today}")
    print(f"{'='*50}")

    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    success_count = 0
    cache = load_cache()
    print(f"[CACHE] チャンネルキャッシュ読み込み: {len(cache)}件")

    BATCH_SIZE = 50
    total_batches = (len(TALENTS) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(0, len(TALENTS), BATCH_SIZE):
        batch = TALENTS[batch_idx:batch_idx + BATCH_SIZE]
        batch_num = batch_idx // BATCH_SIZE + 1
        print(f"\n{'─'*50}")
        print(f"バッチ {batch_num}/{total_batches}（{batch[0]['name']} ～ {batch[-1]['name']}）")
        print(f"{'─'*50}")

        for talent in batch:
            name = talent["name"]
            tid  = talent["id"]
            print(f"\n[{tid}] {name} を収集中...")
            print(f"[START] {name} の収集開始")

            trends  = fetch_google_trends(name)
            yt      = fetch_youtube_data(name, cache)
            youtube = {"video_count": yt["video_count"], "total_views": yt["total_views"], "avg_views": yt["avg_views"]}
            yt_sub  = {"subscribers": yt["subscribers"], "sub_score": yt["sub_score"]}
            news    = fetch_news(name)
            wiki    = fetch_wikipedia(name)
            score   = calc_score(trends, youtube, news, wiki, yt_sub=yt_sub)

            c.execute("""
                INSERT INTO sns_scores (
                    talent_id, collected_at,
                    trend_score, trend_peak,
                    yt_video_count, yt_total_views, yt_avg_views,
                    yt_subscribers, yt_sub_score,
                    news_count, news_sentiment,
                    wiki_pageviews,
                    sns_score_total
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                tid, today,
                trends["score"],  trends["peak"],
                youtube["video_count"], youtube["total_views"], youtube["avg_views"],
                yt_sub["subscribers"], yt_sub["sub_score"],
                news["count"], news["sentiment"],
                wiki["pageviews"],
                score,
            ))
            conn.commit()

            print(f"  Trends: {trends}")
            print(f"  YouTube: {youtube}")
            print(f"  YT Subscribers: {yt_sub}")
            print(f"  News: {news}")
            print(f"  Wikipedia: {wiki}")
            print(f"  ★ SNSスコア: {score}")
            success_count += 1

        save_cache(cache)
        print(f"[CACHE] channel_cache.json を保存しました（{len(cache)}件）")

        if batch_idx + BATCH_SIZE < len(TALENTS):
            print(f"\n  [バッチ {batch_num} 完了 → 30秒待機]")
            time.sleep(30)

    # 実行ログ
    c.execute("""
        INSERT INTO collect_log (run_at, status, message)
        VALUES (?, ?, ?)
    """, (today, "success", f"{success_count}/{len(TALENTS)}件 収集完了"))
    conn.commit()
    conn.close()

    print(f"\n{'='*50}")
    print(f"完了: {success_count}/{len(TALENTS)}件")
    print(f"DB: {DB_PATH}")
    print(f"{'='*50}\n")

# ============================================================
# レポート表示（確認用）
# ============================================================

def show_report():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    print("\n===== 最新SNSスコア一覧 =====")
    c.execute("""
        SELECT m.name, s.collected_at,
               s.trend_score, s.yt_avg_views,
               s.news_count, s.wiki_pageviews,
               s.sns_score_total
        FROM sns_scores s
        JOIN talent_master m ON m.id = s.talent_id
        WHERE s.id IN (
            SELECT MAX(id) FROM sns_scores GROUP BY talent_id
        )
        ORDER BY s.sns_score_total DESC NULLS LAST
    """)
    rows = c.fetchall()
    print(f"{'名前':<12} {'収集日':>12} {'Trends':>7} {'YT avg':>10} {'News':>6} {'Wiki':>8} {'スコア':>7}")
    print("-" * 70)
    for r in rows:
        print(f"{r[0]:<12} {r[1][:10]:>12} {str(r[2] or '-'):>7} {str(r[3] or '-'):>10} {str(r[4] or '-'):>6} {str(r[5] or '-'):>8} {str(r[6] or '-'):>7}")
    conn.close()

if __name__ == "__main__":
    if "--report" in sys.argv:
        show_report()
    else:
        collect_all()
        show_report()
