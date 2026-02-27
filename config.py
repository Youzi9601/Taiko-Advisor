"""Taiko AI Advisor 配置檔案"""

import os
from dotenv import load_dotenv

load_dotenv()

SONGS_DB_PATH = os.getenv("SONGS_DB_PATH", "data/songs.json")
USERS_DB_PATH = os.getenv("USERS_DB_PATH", "data/users.json")

CHROMA_DB_PATH = os.path.join(os.path.dirname(SONGS_DB_PATH), "chroma_db")
CHROMA_COLLECTION_NAME = "taiko_songs"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
HTTP_TIMEOUT = 10
HTTP_DELAY_MIN = 3
HTTP_DELAY_MAX = 5

API_TITLE = "Taiko AI Advisor API"
STATIC_DIR = "static"

CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

TRUSTED_HOSTS = ["localhost", "127.0.0.1"]

TOKEN_EXPIRY_DAYS = 7
MAX_SESSIONS_PER_USER = 3

CHAT_MESSAGE_MAX_LENGTH = 500
USER_NAME_MAX_LENGTH = 50
ACCESS_CODE_MAX_LENGTH = 100
CHROMA_QUERY_LIMIT = 30
FALLBACK_SONGS_COUNT = 15

# ============================================================================
# 太鼓之達人歌曲類別配置
# ============================================================================
TAIKO_CATEGORIES = [
    "ポップス",
    "キッズ",
    "アニメ",
    "ボーカロイド™曲",
    "ゲームミュージック",
    "バラエティ",
    "クラシック",
    "ナムコオリジナル",
    "段位道場課題曲",
]

# 類別與 ID 前綴對應
CATEGORY_PREFIXES = {
    "ポップス": 100000,
    "キッズ": 200000,
    "アニメ": 300000,
    "ボーカロイド™曲": 400000,
    "ゲームミュージック": 500000,
    "バラエティ": 600000,
    "クラシック": 700000,
    "ナムコオリジナル": 800000,
    "段位道場課題曲": 900000,
}

# ============================================================================
# 網頁爬蟲設定
# ============================================================================
TAIKO_WIKI_BASE_URL = "https://wikiwiki.jp/taiko-fumen/%E4%BD%9C%E5%93%81/%E6%96%B0AC/"

# ============================================================================
# ChromaDB 嵌入模型設定
# ============================================================================
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# ChromaDB 批次寫入大小
CHROMA_BATCH_SIZE = 500

# ============================================================================
# AI 生成標籤設定
# ============================================================================
GEMINI_MODEL = "gemini-2.5-flash"
TAG_GENERATION_PROMPT_TEMPLATE = """請閱讀以下「太鼓之達人」的歌曲譜面攻略心得，並從中萃取出 1 到 4 個簡潔的遊戲特色標籤。
【重要規則】：
1. 嚴厲禁止自行想像或過度解讀，標籤必須是針對太鼓之達人常見的客觀譜面特徵，例如：三連音為主、長複合、節奏複雜、變速、體力向等。
2. 嚴禁出現與譜面客觀事實無關的主觀感受詞彙（例如「現場感」、「激昂」等）。
3. 嚴格使用繁體中文標記。
4. 只能輸出標籤，以逗號分隔，絕對不要輸出其它任何文字或解釋。

【攻略內容】：
{strategy_text}
"""
