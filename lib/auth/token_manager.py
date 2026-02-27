"""
令牌管理系統 - Token Management System
"""
import os
import json
import time
import config

# 黑名單存儲被登出的令牌
TOKEN_BLACKLIST_PATH = os.path.join(os.path.dirname(config.USERS_DB_PATH), "token_blacklist.json")

# 令牌過期時間（天數）
TOKEN_EXPIRY_DAYS = config.TOKEN_EXPIRY_DAYS


def load_token_blacklist():
    """載入被登出的令牌黑名單"""
    if not os.path.exists(TOKEN_BLACKLIST_PATH):
        return {}
    try:
        with open(TOKEN_BLACKLIST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_token_blacklist(blacklist):
    """保存令牌黑名單"""
    with open(TOKEN_BLACKLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, indent=2, ensure_ascii=False)


def is_token_blacklisted(code: str) -> bool:
    """檢查令牌是否被列入黑名單"""
    blacklist = load_token_blacklist()
    if code not in blacklist:
        return False
    
    # 檢查黑名單項目是否過期（清理舊的黑名單項目）
    blacklist_time = blacklist[code]
    expiry_time = blacklist_time + (TOKEN_EXPIRY_DAYS * 86400)
    
    if time.time() > expiry_time:
        # 過期的黑名單項目，刪除它
        del blacklist[code]
        save_token_blacklist(blacklist)
        return False
    
    return True


def add_to_token_blacklist(code: str):
    """將令牌加入黑名單（用於登出）"""
    blacklist = load_token_blacklist()
    blacklist[code] = time.time()
    save_token_blacklist(blacklist)


def validate_token(code: str) -> bool:
    """
    驗證令牌是否有效
    - 檢查是否在黑名單中
    - 檢查是否過期
    """
    from .validators import sanitize_input
    from lib.services.user_service import load_users, save_users
    
    # 清理輸入
    code = sanitize_input(code, max_length=100)
    if not code:
        return False
    
    # 檢查是否在黑名單中
    if is_token_blacklisted(code):
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
    
    # 檢查是否超過過期時間
    expiry_time = created_at + (TOKEN_EXPIRY_DAYS * 86400)
    if time.time() > expiry_time:
        return False
    
    return True
