"""
對話歷史 API 路由 - /api/sessions

認證方式說明：
- GET/DELETE: 使用 Authorization header (Bearer token)
- POST: 支援 Authorization header 或 body 中的 code 欄位（向下相容）
"""
from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
import logging
import config
from lib.auth import validate_token
from lib.auth.validators import sanitize_input
from lib.services.user_service import (
    get_user_sessions,
    add_session,
    delete_session,
)
from lib.exceptions import AuthenticationError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


class MessageItem(BaseModel):
    role: str
    content: str


class SaveSessionRequest(BaseModel):
    code: str
    title: str
    messages: list[MessageItem]


@router.get("")
async def get_sessions(authorization: str = Header(None)) -> dict:
    """
    獲取用戶所有對話歷史\n    
    Authorization header 格式: Bearer <access_code>
    """
    if not authorization:
        raise ValidationError("缺少 Authorization header")
    
    # 從 Authorization header 提取 token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValidationError("無效的 Authorization header 格式")
    
    code = sanitize_input(parts[1], max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    # 驗證令牌
    if not validate_token(code):
        raise AuthenticationError("無效或已過期的存取代碼")
    
    sessions = get_user_sessions(code)
    return {"sessions": sessions}


@router.post("")
async def save_session(req: SaveSessionRequest, authorization: str = Header(None)) -> dict:
    """
    保存對話
    
    支援兩種認證方式（向下相容）：
    1. Authorization header: Bearer <access_code>
    2. Request body 中的 code 欄位
    """
    # 優先使用 Authorization header
    code = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            code = sanitize_input(parts[1], max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    # Fallback 到 body 中的 code（向下相容）
    if not code:
        code = sanitize_input(req.code, max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    if not code:
        raise ValidationError("缺少存取代碼")
    
    # 驗證令牌
    if not validate_token(code):
        raise AuthenticationError("無效或已過期的存取代碼")
    
    # 驗證對話內容
    title = sanitize_input(req.title, max_length=100)
    if not title:
        raise ValidationError("標題不能為空")
    
    if len(req.messages) == 0:
        raise ValidationError("對話內容不能為空")
    
    # 限制每則訊息的長度，防止過大的 payload
    sanitized_messages = []
    for m in req.messages:
        sanitized_content = sanitize_input(m.content, max_length=config.CHAT_MESSAGE_MAX_LENGTH)
        sanitized_messages.append({"role": m.role, "content": sanitized_content})
    
    # 檢查是否超過上限
    sessions = get_user_sessions(code)
    if len(sessions) >= config.MAX_SESSIONS_PER_USER:
        raise ValidationError(
            f"已達到儲存對話數量上限 ({config.MAX_SESSIONS_PER_USER}個)，請先刪除舊的對話。"
        )
    
    # 創建新對話
    new_session = {
        "id": str(uuid.uuid4()),
        "title": title,
        "messages": sanitized_messages,
    }
    
    if add_session(code, new_session):
        logger.info(f"對話已儲存 (code: {code[:8]}..., session_id: {new_session['id']})")
        return {"success": True, "session_id": new_session["id"]}
    else:
        raise ValidationError("無法保存對話")


@router.delete("/{session_id}")
async def delete_session_endpoint(session_id: str, authorization: str = Header(None)) -> dict:
    """
    刪除對話\n    
    Authorization header 格式: Bearer <access_code>
    """
    if not authorization:
        raise ValidationError("缺少 Authorization header")
    
    # 從 Authorization header 提取 token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValidationError("無效的 Authorization header 格式")
    
    code = sanitize_input(parts[1], max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    # 驗證令牌
    if not validate_token(code):
        raise AuthenticationError("無效或已過期的存取代碼")
    
    if delete_session(code, session_id):
        logger.info(f"對話已刪除 (code: {code[:8]}..., session_id: {session_id})")
        return {"success": True}
    else:
        raise ValidationError("無法刪除對話")
