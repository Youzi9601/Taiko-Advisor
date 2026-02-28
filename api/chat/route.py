"""聊天與登出 API 路由。"""
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel, Field
from typing import Optional
import json
import logging
from uuid import uuid4
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
from lib.rate_limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


class MessageItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[MessageItem] = Field(default_factory=list)


@router.post("/chat")
@limiter.limit("10/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    authorization: str = Header(None),
    client: Optional[genai.Client] = Depends(get_client),
    collection: Optional[chromadb.Collection] = Depends(get_collection),
    all_songs: list = Depends(get_all_songs),
) -> Response:
    """聊天端點（速率限制：10 次/分鐘）。"""
    message = sanitize_input(req.message, max_length=config.CHAT_MESSAGE_MAX_LENGTH)
    if not authorization:
        raise ValidationError("缺少 Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValidationError("無效的 Authorization header 格式")

    code = sanitize_input(parts[1], max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    if not message:
        raise ValidationError("訊息不能為空")
    if not code:
        raise ValidationError("存取代碼不能為空")
    
    # validate_token 內部會檢查用戶是否存在與是否過期。
    if not validate_token(code):
        raise AuthenticationError("無效或已過期的存取代碼")
    
    if client is None:
        logger.error("找不到 Gemini API Key")
        return JSONResponse(status_code=500, content={"error": "找不到 Gemini API Key"})
    
    logger.info(f"接收到聊天請求 (code: {code[:8]}..., message_length: {len(message)})")
    
    # 構建上下文。
    profile = get_user_profile(code)
    profile_context = build_profile_context(profile)
    sanitized_history: list[MessageItem] = []
    for history_item in req.history:
        role = sanitize_input(history_item.role, max_length=20)
        if role not in config.ALLOWED_MESSAGE_ROLES:
            raise ValidationError("歷史對話包含無效角色")
        content = sanitize_input(
            history_item.content, max_length=config.CHAT_MESSAGE_MAX_LENGTH
        )
        if not content:
            raise ValidationError("歷史對話內容不能為空")
        sanitized_history.append(MessageItem(role=role, content=content))

    history_context = build_history_context(sanitized_history)
    
    # 取得候選歌曲。
    candidate_songs = get_candidate_songs(message, collection, all_songs)
    songs_context = json.dumps(candidate_songs, ensure_ascii=False)
    
    # 構建 prompt。
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
        error_id = str(uuid4())[:8].upper()
        logger.error(f"[{error_id}] LLM 發生錯誤: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "LLM 服務暫時無法使用", "error_id": error_id},
        )


@router.post("/logout")
async def logout(authorization: str = Header(None)) -> dict:
    """登出端點（Authorization: Bearer <access_code>）。"""
    if not authorization:
        raise ValidationError("缺少 Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValidationError("無效的 Authorization header 格式")

    code = sanitize_input(parts[1], max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    # 登出允許過期 token，僅檢查用戶是否存在。
    users = load_users()
    if code not in users:
        logger.warning(f"嘗試登出不存在的用戶 (code: {code[:8]}...)")
        raise AuthenticationError("用戶不存在")
    
    logout_user(code)
    logger.info(f"用戶登出成功 (code: {code[:8]}...)")
    
    return {"success": True, "message": "已成功登出"}
