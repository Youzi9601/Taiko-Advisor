"""
令牌管理系統 - Token Management System
"""
import time
import math
import logging
import config

# 令牌過期時間（天數）
TOKEN_EXPIRY_DAYS = config.TOKEN_EXPIRY_DAYS
logger = logging.getLogger(__name__)


def logout_user(code: str) -> bool:
    """登出用戶（刪除用戶記錄）"""
    from lib.services.user_service import delete_user
    return delete_user(code)


def validate_token(code: str) -> bool:
    """
    驗證令牌是否有效
    - 檢查用戶是否存在
    - 檢查是否過期
    - 自動清理過期用戶
    """
    from .validators import sanitize_input
    from lib.services.user_service import load_users, save_users, delete_user
    
    # 清理輸入
    code = sanitize_input(code, max_length=100)
    if not code:
        return False
    
    # 檢查用戶是否存在
    users = load_users()
    if code not in users:
        return False
    
    # 檢查令牌創建時間是否超過過期時限
    user_data = users[code]
    created_at = user_data.get("created_at")
    
    if created_at is None:
        # 舊的用戶數據沒有時間戳，設置當前時間
        user_data["created_at"] = time.time()
        save_users(users)
        return True

    try:
        created_at = float(created_at)
        if not math.isfinite(created_at):
            raise ValueError("created_at is not finite")
    except (TypeError, ValueError):
        logger.warning(f"偵測到無效 token 時間戳，已清理用戶資料 (code: {code[:8]}...)")
        delete_user(code)
        return False
    
    # 檢查是否超過過期時間
    expiry_time = created_at + (TOKEN_EXPIRY_DAYS * 86400)
    if time.time() > expiry_time:
        # 令牌已過期，刪除用戶
        delete_user(code)
        return False
    
    return True
