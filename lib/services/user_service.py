"""
用戶數據服務模塊
"""
import os
import json
import time
import config


def load_users():
    """載入用戶數據"""
    if not os.path.exists(config.USERS_DB_PATH):
        return {}
    with open(config.USERS_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users_data):
    """保存用戶數據"""
    with open(config.USERS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(users_data, f, indent=2, ensure_ascii=False)


def get_user(code: str):
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


def update_user_profile(code: str, profile_data: dict) -> bool:
    """更新用戶個人資料"""
    users = load_users()
    if code not in users:
        return False
    
    users[code]["profile"] = profile_data
    save_users(users)
    return True


def get_user_profile(code: str):
    """獲取用戶個人資料"""
    users = load_users()
    if code not in users:
        return None
    
    return users[code].get("profile")


def get_user_sessions(code: str):
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
    
    users[code]["chat_sessions"] = new_sessions
    save_users(users)
    return True
