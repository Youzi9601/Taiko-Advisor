"""
用戶數據服務模塊
"""
import os
import json
import time
import tempfile
import logging
from typing import Optional, Dict, List, Any
from filelock import FileLock
import config

logger = logging.getLogger(__name__)


def load_users() -> Dict[str, Any]:
    """載入用戶數據"""
    if not os.path.exists(config.USERS_DB_PATH):
        return {}
    lock_path = config.USERS_DB_PATH + ".lock"
    with FileLock(lock_path):
        try:
            with open(config.USERS_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"讀取用戶數據失敗: {e}")
            return {}


def save_users(users_data: Dict[str, Any]) -> None:
    """保存用戶數據"""
    dir_path = os.path.dirname(config.USERS_DB_PATH)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    lock_path = config.USERS_DB_PATH + ".lock"
    with FileLock(lock_path):
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=dir_path if dir_path else None,
            suffix=".tmp",
        ) as tmp_file:
            json.dump(users_data, tmp_file, indent=2, ensure_ascii=False)
            tmp_path = tmp_file.name

        os.replace(tmp_path, config.USERS_DB_PATH)
        logger.debug("用戶數據已保存")


def get_user(code: str) -> Optional[Dict[str, Any]]:
    """獲取單個用戶數據"""
    users = load_users()
    return users.get(code)


def user_exists(code: str) -> bool:
    """檢查用戶是否存在"""
    users = load_users()
    return code in users


def create_user(code: str) -> bool:
    """創建新用戶"""
    users = load_users()
    if code in users:
        return False
    
    users[code] = {
        "created_at": time.time(),
        "profile": None,
        "chat_sessions": []
    }
    save_users(users)
    return True


def delete_user(code: str) -> bool:
    """刪除用戶"""
    users = load_users()
    if code not in users:
        return False
    
    del users[code]
    save_users(users)
    return True


def update_user_profile(code: str, profile_data: dict) -> bool:
    """更新用戶個人資料"""
    users = load_users()
    if code not in users:
        return False
    
    users[code]["profile"] = profile_data
    save_users(users)
    return True


def get_user_profile(code: str) -> Optional[Dict[str, Any]]:
    """獲取用戶個人資料"""
    users = load_users()
    if code not in users:
        return None
    
    return users[code].get("profile")


def get_user_sessions(code: str) -> List[Dict[str, Any]]:
    """獲取用戶的所有對話"""
    users = load_users()
    if code not in users:
        return []
    
    return users[code].get("chat_sessions", [])


def add_session(code: str, session: dict) -> bool:
    """添加對話"""
    users = load_users()
    if code not in users:
        return False
    
    sessions = users[code].get("chat_sessions", [])
    if len(sessions) >= config.MAX_SESSIONS_PER_USER:
        return False
    
    sessions.append(session)
    users[code]["chat_sessions"] = sessions
    save_users(users)
    return True


def delete_session(code: str, session_id: str) -> bool:
    """刪除對話"""
    users = load_users()
    if code not in users:
        return False
    
    sessions = users[code].get("chat_sessions", [])
    new_sessions = [s for s in sessions if s["id"] != session_id]
    
    # 如果沒有任何對話被刪除，返回 False
    if len(new_sessions) == len(sessions):
        return False
    
    users[code]["chat_sessions"] = new_sessions
    save_users(users)
    return True
