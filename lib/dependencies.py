"""
FastAPI 依賴注入 - 全局資源管理

此模塊管理所有全局資源，使其可以通過 FastAPI 的依賴注入系統傳遞到路由。
"""
from typing import Optional
import chromadb
from google import genai
import json
import logging

logger = logging.getLogger(__name__)

# 全局資源存儲
_client: Optional[genai.Client] = None
_collection: Optional[chromadb.Collection] = None
_all_songs: list = []


def init_resources(gemini_key: str, chroma_path: str, collection_name: str, songs_path: str):
    """初始化全局資源 - 在應用啟動時調用"""
    global _client, _collection, _all_songs
    
    # 初始化 Gemini
    if gemini_key:
        try:
            _client = genai.Client(api_key=gemini_key)
            logger.info("✅ Gemini 客戶端初始化成功")
        except Exception as e:
            logger.error(f"❌ Gemini 初始化失敗: {e}")
            _client = None
    else:
        logger.warning("⚠️ 未提供 GEMINI_API_KEY，聊天功能將無法使用")
        _client = None
    
    # 初始化 ChromaDB
    try:
        chroma_client = chromadb.PersistentClient(path=chroma_path)
        _collection = chroma_client.get_collection(name=collection_name)
        logger.info(f"✅ ChromaDB 連接成功 (collection: {collection_name})")
    except Exception as e:
        logger.error(f"❌ ChromaDB 初始化失敗: {e}")
        _collection = None
    
    # 讀取歌曲數據
    try:
        with open(songs_path, "r", encoding="utf-8") as f:
            _all_songs = json.load(f)
        logger.info(f"✅ 載入歌曲數據成功 ({len(_all_songs)} 首)")
    except Exception as e:
        logger.error(f"❌ 無法載入歌曲數據: {e}")
        _all_songs = []


def cleanup_resources():
    """清理全局資源 - 在應用關閉時調用"""
    global _client, _collection, _all_songs
    
    _client = None
    _collection = None
    _all_songs = []
    logger.info("資源清理完成")


def get_client() -> Optional[genai.Client]:
    """獲取 Gemini 客戶端"""
    return _client


def get_collection() -> Optional[chromadb.Collection]:
    """獲取 ChromaDB 集合"""
    return _collection


def get_all_songs() -> list:
    """獲取所有歌曲"""
    return _all_songs
