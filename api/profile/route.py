"""個人資料 API 路由。"""
from fastapi import APIRouter, Header
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
    name: str
    level: str
    star_pref: str
    style: str


@router.post("")
async def save_profile(req: ProfileRequest, authorization: str = Header(None)) -> dict:
    """儲存用戶個人資料（Authorization: Bearer <access_code>）。"""
    if not authorization:
        raise ValidationError("缺少 Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValidationError("無效的 Authorization header 格式")

    code = sanitize_input(parts[1], max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    if not validate_token(code):
        raise AuthenticationError("無效或已過期的存取代碼")
    
    # 驗證與清理用戶輸入。
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
    
    # 更新用戶資料。
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
    """取得用戶個人資料（Authorization: Bearer <access_code>）。"""
    if not authorization:
        raise ValidationError("缺少 Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValidationError("無效的 Authorization header 格式")

    code = sanitize_input(parts[1], max_length=config.ACCESS_CODE_MAX_LENGTH)
    
    if not validate_token(code):
        raise AuthenticationError("無效或已過期的存取代碼")
    
    profile = get_user_profile(code)
    return {"profile": profile}
