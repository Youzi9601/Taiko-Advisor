"""
聊天服務模塊
"""
import json
import random
import logging
from typing import Optional, List, Dict, Any
import chromadb
import config
from lib.auth.validators import sanitize_input

logger = logging.getLogger(__name__)


def get_candidate_songs(
    message: str, 
    collection: Optional[chromadb.Collection] = None, 
    all_songs: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    獲取候選歌曲列表
    """
    candidate_songs = []
    
    if collection:
        try:
            # 進行語意查詢，取出前 N 筆
            results = collection.query(query_texts=[message], n_results=config.CHROMA_QUERY_LIMIT)
            if results and results["metadatas"] and len(results["metadatas"][0]) > 0:
                for meta in results["metadatas"][0]:
                    json_data = meta.get("json")
                    if isinstance(json_data, str):
                        song_obj = json.loads(json_data)
                    else:
                        song_obj = json_data
                    if song_obj:
                        candidate_songs.append(song_obj)
        except Exception as e:
            logger.error(f"ChromaDB 查詢發生錯誤: {e}")
    
    # Fallback 機制
    if not candidate_songs and all_songs:
        candidate_songs = random.sample(all_songs, min(config.FALLBACK_SONGS_COUNT, len(all_songs)))
        logger.warning(f"使用 Fallback 機制，隨機選取 {len(candidate_songs)} 首歌")
    
    return candidate_songs


def build_profile_context(profile: Optional[Dict[str, Any]] = None) -> str:
    """
    構建玩家實力上下文文本
    """
    if not profile:
        return ""
    
    profile_name = sanitize_input(str(profile.get("name", "玩家")), max_length=50)
    profile_level = sanitize_input(str(profile.get("level", "未知")), max_length=50)
    profile_star = sanitize_input(str(profile.get("star_pref", "未知")), max_length=50)
    profile_style = sanitize_input(str(profile.get("style", "未知")), max_length=50)
    
    return f"""【玩家實力與偏好設定】
玩家名稱: {profile_name}
最高段位: {profile_level}
偏好星級: {profile_star}
打法偏好: {profile_style}
"""


def build_history_context(history: List[Any]) -> str:
    """
    構建對話歷史上下文文本
    """
    if not history:
        return ""
    
    history_text = "【之前的對話紀錄】\n"
    for msg in history:
        role_name = "玩家: " if msg.role == "user" else "顧問: "
        content = sanitize_input(str(msg.content), max_length=500)
        history_text += f"{role_name}{content}\n"
    history_text += "\n"
    
    return history_text


def build_chat_prompt(
    message: str,
    profile_context: str,
    history_context: str,
    songs_context: str
) -> str:
    """
    構建發送給 LLM 的 prompt
    """
    prompt = f"""你是一個專業、有耐心的「太鼓之達人」遊玩顧問。
請根據玩家的需求，從以下的【候選歌曲資料庫】中挑選出最適合的歌曲來推薦。
{profile_context}
{history_context}
- 如果玩家只是閒聊，請普通地回應他。
- 如果推薦的要求帶有難度要求，輸出時請直接輸出該難度的資訊，不要輸出其他難度的資訊。
- 若【玩家實力與偏好設定】有資料，請在推薦歌曲時，務必將這些偏好納入考量，挑選符合他實力與打法的歌曲。
- 請記得參考【之前的對話紀錄】(如果有)，接續之前的脈絡進行回覆。
- 推薦的歌曲以3首為上限。
- 如果是要求推薦，請將推薦出來的歌曲以漂亮地排版，包含曲名(使用橙色標記)、歌曲類別、難度&星級()、BPM。不要使用任何表情符號。
- 務必只能推薦存在於資料庫中的歌曲，如果資料庫中沒有完全匹配的，可以推薦最相近的歌曲，並委婉說明。
- 務必使用繁體中文回應。

【候選歌曲資料庫】：
{songs_context}

【玩家需求】：
{message}
"""
    return prompt
