"""
聊天 API 路由 - /api/chat 和 /api/logout
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import chromadb
from google import genai
import config
from lib.auth import validate_token
from lib.auth.token_manager import add_to_token_blacklist
from lib.auth.validators import sanitize_input
from lib.services.user_service import load_users, get_user_profile
from lib.services.chat_service import (
    get_candidate_songs,
    build_profile_context,
    build_history_context,
    build_chat_prompt,
)
from lib.dependencies import get_client, get_collection, get_all_songs

router = APIRouter()


class MessageItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    code: str
    history: list[MessageItem] = []


@router.post("/chat")
async def chat(
    req: ChatRequest,
    client: Optional[genai.Client] = Depends(get_client),
    collection: Optional[chromadb.Collection] = Depends(get_collection),
    all_songs: list = Depends(get_all_songs),
):
    """
    聊天端點 - 與 AI 顧問交互
    """
    message = sanitize_input(req.message, max_length=config.CHAT_MESSAGE_MAX_LENGTH)
    code = sanitize_input(req.code, max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    if not message:
        return JSONResponse(status_code=400, content={"error": "訊息不能為空"})
    if not code:
        return JSONResponse(status_code=400, content={"error": "存取代碼不能為空"})
    
    # 驗證令牌
    if not validate_token(code):
        return JSONResponse(status_code=401, content={"error": "無效或已過期的存取代碼"})
    
    users = load_users()
    if code not in users:
        return JSONResponse(status_code=401, content={"error": "無效的存取代碼。"})
    
    if client is None:
        return JSONResponse(status_code=500, content={"error": "找不到 Gemini API Key"})
    
    # 構建上下文
    profile = get_user_profile(code)
    profile_context = build_profile_context(profile)
    history_context = build_history_context(req.history)
    
    # 獲取候選歌曲
    candidate_songs = get_candidate_songs(message, collection, all_songs)
    songs_context = json.dumps(candidate_songs, ensure_ascii=False)
    
    # 構建 prompt
    prompt = build_chat_prompt(message, profile_context, history_context, songs_context)
    
    try:
        def stream_generator():
            responseStream = client.models.generate_content_stream(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )
            for chunk in responseStream:
                if chunk.text:
                    yield chunk.text
        
        return StreamingResponse(stream_generator(), media_type="text/plain")
    
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"LLM 發生錯誤: {str(e)}"}
        )


@router.post("/logout")
async def logout(code: str):
    """
    登出端點 - 使令牌失效
    """
    code = sanitize_input(code, max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    if not code:
        return JSONResponse(status_code=400, content={"error": "存取代碼不能為空"})
    
    users = load_users()
    if code not in users:
        return JSONResponse(status_code=401, content={"error": "無效的存取代碼。"})
    
    # 將令牌加入黑名單
    add_to_token_blacklist(code)
    
    return {"success": True, "message": "已成功登出"}
