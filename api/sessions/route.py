"""
對話歷史 API 路由 - /api/sessions
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
import config
from lib.auth import validate_token
from lib.auth.validators import sanitize_input
from lib.services.user_service import (
    get_user_sessions,
    add_session,
    delete_session,
)

router = APIRouter()


class MessageItem(BaseModel):
    role: str
    content: str


class SaveSessionRequest(BaseModel):
    code: str
    title: str
    messages: list[MessageItem]


@router.get("")
async def get_sessions(code: str):
    """
    獲取用戶所有對話歷史
    """
    code = sanitize_input(code, max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    # 驗證令牌
    if not validate_token(code):
        return JSONResponse(status_code=401, content={"error": "無效或已過期的存取代碼"})
    
    sessions = get_user_sessions(code)
    return {"sessions": sessions}


@router.post("")
async def save_session(req: SaveSessionRequest):
    """
    保存對話
    """
    code = sanitize_input(req.code, max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    # 驗證令牌
    if not validate_token(code):
        return JSONResponse(status_code=401, content={"error": "無效或已過期的存取代碼"})
    
    # 驗證對話內容
    title = sanitize_input(req.title, max_length=100)
    if not title:
        return JSONResponse(status_code=400, content={"error": "標題不能為空"})
    
    if len(req.messages) == 0:
        return JSONResponse(status_code=400, content={"error": "對話內容不能為空"})
    
    # 檢查是否超過上限
    sessions = get_user_sessions(code)
    if len(sessions) >= config.MAX_SESSIONS_PER_USER:
        return JSONResponse(
            status_code=400,
            content={"error": f"已達到儲存對話數量上限 ({config.MAX_SESSIONS_PER_USER}個)，請先刪除舊的對話。"}
        )
    
    # 創建新對話
    new_session = {
        "id": str(uuid.uuid4()),
        "title": title,
        "messages": [{"role": m.role, "content": m.content} for m in req.messages],
    }
    
    if add_session(code, new_session):
        return {"success": True, "session_id": new_session["id"]}
    else:
        return JSONResponse(status_code=400, content={"error": "無法保存對話"})


@router.delete("/{session_id}")
async def delete_session_endpoint(session_id: str, code: str):
    """
    刪除對話
    """
    code = sanitize_input(code, max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    # 驗證令牌
    if not validate_token(code):
        return JSONResponse(status_code=401, content={"error": "無效或已過期的存取代碼"})
    
    if delete_session(code, session_id):
        return {"success": True}
    else:
        return JSONResponse(status_code=400, content={"error": "無法刪除對話"})
