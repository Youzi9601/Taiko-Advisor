"""
個人資料 API 路由 - /api/profile
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import config
from lib.auth import validate_token
from lib.auth.validators import sanitize_input, validate_required_field
from lib.services.user_service import (
    get_user_profile,
    update_user_profile,
)

router = APIRouter()


class ProfileRequest(BaseModel):
    code: str
    name: str
    level: str
    star_pref: str
    style: str


@router.post("")
async def save_profile(req: ProfileRequest):
    """
    保存用戶個人資料
    """
    code = sanitize_input(req.code, max_length=config.ACCESS_CODE_MAX_LENGTH)
    if not code:
        return JSONResponse(status_code=400, content={"error": "存取代碼不能為空"})
    
    # 驗證令牌
    if not validate_token(code):
        return JSONResponse(status_code=401, content={"error": "無效或已過期的存取代碼"})
    
    # 驗證和清理用戶輸入
    is_valid, name = validate_required_field(
        req.name, "玩家名稱", max_length=config.USER_NAME_MAX_LENGTH
    )
    if not is_valid:
        return JSONResponse(status_code=400, content={"error": name})
    
    is_valid, level = validate_required_field(
        req.level, "最高段位", max_length=config.USER_NAME_MAX_LENGTH
    )
    if not is_valid:
        return JSONResponse(status_code=400, content={"error": level})
    
    star_pref = sanitize_input(req.star_pref, max_length=config.USER_NAME_MAX_LENGTH)
    style = sanitize_input(req.style, max_length=config.USER_NAME_MAX_LENGTH)
    
    # 更新用戶資料
    profile_data = {
        "name": name,
        "level": level,
        "star_pref": star_pref,
        "style": style,
    }
    
    if update_user_profile(code, profile_data):
        return {"success": True, "message": "個人資料已儲存！"}
    else:
        return JSONResponse(status_code=401, content={"error": "無效的存取代碼。"})


@router.get("")
async def get_profile(code: str):
    """
    獲取用戶個人資料
    """
    code = sanitize_input(code, max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    # 驗證令牌
    if not validate_token(code):
        return JSONResponse(status_code=401, content={"error": "無效或已過期的存取代碼"})
    
    profile = get_user_profile(code)
    return {"profile": profile}
