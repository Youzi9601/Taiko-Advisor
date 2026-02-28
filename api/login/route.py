"""
登入 API 路由 - /api/login
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import time
import config
from lib.auth.validators import sanitize_input
from lib.services.user_service import load_users, save_users, create_user

router = APIRouter()


class LoginRequest(BaseModel):
    code: str


@router.post("")
async def login(req: LoginRequest):
    """
    用戶登入端點
    """
    # 驗證 access code
    code = sanitize_input(req.code, max_length=config.ACCESS_CODE_MAX_LENGTH)
    if not code:
        return JSONResponse(status_code=400, content={"error": "存取代碼不能為空"})
    
    users = load_users()
    
    # 如果用戶不存在，回傳未授權錯誤以維持白名單機制
    if code not in users:
        return JSONResponse(status_code=401, content={"error": "無效的存取代碼"})
    
    user_data = users[code]
    
    
    # 檢查令牌是否已過期
    created_at = user_data.get("created_at")
    if created_at is None:
        user_data["created_at"] = time.time()
        save_users(users)
    else:
        expiry_time = created_at + (config.TOKEN_EXPIRY_DAYS * 86400)
        if time.time() > expiry_time:
            # 過期用戶已在 validate_token 中被刪除
            return JSONResponse(status_code=401, content={"error": "存取代碼已過期，請重新申請"})
    
    # 回傳是否需要填寫 profile
    needs_profile = user_data.get("profile") is None
    return {
        "success": True,
        "needs_profile": needs_profile,
        "profile": user_data.get("profile"),
        "expires_in": config.TOKEN_EXPIRY_DAYS * 24 * 3600
    }
