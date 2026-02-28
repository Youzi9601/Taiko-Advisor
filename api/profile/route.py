"""
個人資料 API 路由 - /api/profile

認證方式說明：
- GET: 使用 Authorization header (Bearer token)
- POST: 支援 Authorization header 或 body 中的 code 欄位（向下相容）
"""
from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
import config
from lib.auth import validate_token
from lib.auth.validators import sanitize_input, validate_required_field
from lib.services.user_service import (
    get_user_profile,
    update_user_profile,
)
from lib.exceptions import AuthenticationError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


class ProfileRequest(BaseModel):
    code: str
    name: str
    level: str
    star_pref: str
    style: str


@router.post("")
async def save_profile(req: ProfileRequest, authorization: str = Header(None)) -> dict:
    """
    保存用戶個人資料
    
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
    
    # 驗證和清理用戶輸入
    is_valid, name = validate_required_field(
        req.name, "玩家名稱", max_length=config.USER_NAME_MAX_LENGTH
    )
    if not is_valid:
        raise ValidationError(name)
    
    is_valid, level = validate_required_field(
        req.level, "最高段位", max_length=config.USER_NAME_MAX_LENGTH
    )
    if not is_valid:
        raise ValidationError(level)
    
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
        logger.info(f"用戶資料已更新 (code: {code[:8]}...)")
        return {"success": True, "message": "個人資料已儲存！"}
    else:
        raise AuthenticationError("無效的存取代碼。")


@router.get("")
async def get_profile(authorization: str = Header(None)) -> dict:
    """
    獲取用戶個人資料

    Authorization header 格式: Bearer <access_code>
    """
    if not authorization:
        raise ValidationError("缺少 Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValidationError("無效的 Authorization header 格式")

    code = sanitize_input(parts[1], max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    # 驗證令牌
    if not validate_token(code):
        raise AuthenticationError("無效或已過期的存取代碼")
    
    profile = get_user_profile(code)
    return {"profile": profile}
