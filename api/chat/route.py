"""
聊天 API 路由 - /api/chat 和 /api/logout
"""
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional
import json
import logging
import chromadb
from google import genai
import config
from lib.auth import validate_token
from lib.auth.token_manager import logout_user
from lib.auth.validators import sanitize_input
from lib.services.user_service import load_users, get_user_profile
from lib.services.chat_service import (
    get_candidate_songs,
    build_profile_context,
    build_history_context,
    build_chat_prompt,
)
from lib.dependencies import get_client, get_collection, get_all_songs
from lib.exceptions import AuthenticationError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


class MessageItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    code: str
    history: list[MessageItem] = []


class LogoutRequest(BaseModel):
    code: str


@router.post("/chat")
async def chat(
    request: Request,
    req: ChatRequest,
    client: Optional[genai.Client] = Depends(get_client),
    collection: Optional[chromadb.Collection] = Depends(get_collection),
    all_songs: list = Depends(get_all_songs),
) -> Response:
    """
    聊天端點 - 與 AI 顧問交互
    
    速率限制: 10 次/分鐘
    """
    message = sanitize_input(req.message, max_length=config.CHAT_MESSAGE_MAX_LENGTH)
    code = sanitize_input(req.code, max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    if not message:
        raise ValidationError("訊息不能為空")
    if not code:
        raise ValidationError("存取代碼不能為空")
    
    # 驗證令牌（validate_token 內部已經檢查用戶是否存在）
    if not validate_token(code):
        raise AuthenticationError("無效或已過期的存取代碼")
    
    if client is None:
        logger.error("找不到 Gemini API Key")
        return JSONResponse(status_code=500, content={"error": "找不到 Gemini API Key"})
    
    logger.info(f"接收到聊天請求 (code: {code[:8]}..., message_length: {len(message)})")
    
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
                model=config.GEMINI_MODEL,
                contents=prompt,
            )
            for chunk in responseStream:
                if chunk.text:
                    yield chunk.text
        
        logger.info(f"開始串流回傳 (code: {code[:8]}...)")
        return StreamingResponse(stream_generator(), media_type="text/plain")
    
    except Exception as e:
        logger.error(f"LLM 發生錯誤: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": f"LLM 發生錯誤: {str(e)}"}
        )


@router.post("/logout")
async def logout(req: LogoutRequest, authorization: str = Header(None)) -> dict:
    """
    登出端點 - 刪除用戶記錄
    
    支援兩種認證方式（向下相容）：
    1. Authorization header: Bearer <access_code>（推薦）
    2. Request body 中的 code 欄位
    """
    # 優先使用 Authorization header
    code = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            code = sanitize_input(parts[1], max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    # Fallback 到 body
    if not code:
        code = sanitize_input(req.code, max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    if not code:
        raise ValidationError("缺少存取代碼")
    
    # 登出不需要驗證 token 是否過期，允許過期 token 登出
    users = load_users()
    if code not in users:
        logger.warning(f"嘗試登出不存在的用戶 (code: {code[:8]}...)")
        raise AuthenticationError("用戶不存在")
    
    logout_user(code)
    logger.info(f"用戶登出成功 (code: {code[:8]}...)")
    
    return {"success": True, "message": "已成功登出"}
