"""
登入 API 路由 - /api/login
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import time
import logging
import config
from lib.auth import validate_token
from lib.auth.validators import sanitize_input
from lib.services.user_service import load_users, save_users
from lib.exceptions import AuthenticationError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    code: str


@router.post("")
async def login(req: LoginRequest) -> dict:
    """
    用戶登入端點
    """
    # 驗證 access code
    code = sanitize_input(req.code, max_length=config.ACCESS_CODE_MAX_LENGTH)
    if not code:
        raise ValidationError("存取代碼不能為空")
    
    users = load_users()
    
    # 如果用戶不存在，回傳未授權錯誤以維持白名單機制
    if code not in users:
        logger.warning(f"嘗試登入不存在的用戶 (code: {code[:8]}...)")
        raise AuthenticationError("無效的存取代碼")
    
    # 使用集中式的 token 驗證（會自動處理過期檢查和清理）
    if not validate_token(code):
        logger.warning(f"用戶 token 已過期 (code: {code[:8]}...)")
        raise AuthenticationError("存取代碼已過期，請重新申請")
    
    # 重新讀取以獲取 validate_token 可能更新的數據
    users = load_users()
    user_data = users.get(code)
    if not user_data:
        raise AuthenticationError("無效的存取代碼")
    
    logger.info(f"用戶登入成功 (code: {code[:8]}...)")
    
    # 回傳是否需要填寫 profile
    needs_profile = user_data.get("profile") is None
    return {
        "success": True,
        "needs_profile": needs_profile,
        "profile": user_data.get("profile"),
        "expires_in": config.TOKEN_EXPIRY_DAYS * 24 * 3600
    }
