"""
服務層單元測試

測試 user_service 中的業務邏輯。

注意：這些測試使用了實際的用戶數據庫文件，需要小心處理並發測試。
在實際的生產環境中，應該使用 mock 或 monkeypatch 來避免文件系統交互。
"""
from lib.services.user_service import (
    load_users, get_user_profile, update_user_profile,
    user_exists, get_user_sessions, create_user, delete_user, save_users, delete_session
)
from lib.auth.token_manager import validate_token
import config


class TestUserServiceBasic:
    """用戶服務基本功能測試"""
    
    def test_load_users_returns_dict(self):
        """測試 load_users 返回字典"""
        result = load_users()
        assert isinstance(result, dict)
    
    def test_user_exists_callable(self):
        """測試 user_exists 函數可調用"""
        # 測試函數可用性，不依賴實際數據
        result = user_exists("nonexistent_test_code_12349999")
        assert isinstance(result, bool)
    
    def test_get_user_profile_nonexistent(self):
        """測試獲取不存在的用戶"""
        result = get_user_profile("nonexistent_test_code_12349999")
        assert result is None
    
    def test_get_user_sessions_nonexistent(self):
        """測試獲取不存在用戶的會話"""
        result = get_user_sessions("nonexistent_test_code_12349999")
        assert isinstance(result, list)
        assert len(result) == 0


class TestUserServiceDataIntegrity:
    """用戶服務數據完整性測試"""
    
    def test_update_profile_returns_bool(self):
        """測試 update_user_profile 返回布林值"""
        # 使用不存在的用戶測試返回類型
        result = update_user_profile("nonexistent_123asd", {"name": "Test"})
        assert isinstance(result, bool)
    
    def test_create_and_delete_user(self):
        """測試用戶創建和刪除功能"""
        # 使用一個不太可能存在的測試代碼
        test_code = "test_code_for_unit_test_99999"
        
        try:
            # 確保測試前用戶不存在
            if user_exists(test_code):
                delete_user(test_code)
            
            # 測試創建用戶
            result = create_user(test_code)
            assert isinstance(result, bool)
            assert result is True, "創建用戶應該返回 True"
            
            # 驗證用戶確實被創建
            assert user_exists(test_code), "用戶創建後應該存在"
            
            # 測試刪除用戶
            delete_result = delete_user(test_code)
            assert isinstance(delete_result, bool)
            assert delete_result is True, "刪除用戶應該返回 True"
            
            # 驗證用戶確實被刪除
            assert not user_exists(test_code), "用戶刪除後應該不存在"
            
        finally:
            # 確保清理測試用戶以防止測試污染
            if user_exists(test_code):
                delete_user(test_code)


class TestUserServiceEdgeCases:
    """用戶服務邊界條件測試"""

    def test_validate_token_with_malformed_created_at(self, temp_db_path, monkeypatch):
        """測試 created_at 格式錯誤時不應拋例外且會清除無效用戶"""
        monkeypatch.setattr(config, "USERS_DB_PATH", temp_db_path)
        save_users(
            {
                "bad_token_user": {
                    "created_at": "invalid_timestamp",
                    "profile": None,
                    "chat_sessions": [],
                }
            }
        )

        assert validate_token("bad_token_user") is False
        assert user_exists("bad_token_user") is False

    def test_delete_session_with_malformed_session_entries(self, temp_db_path, monkeypatch):
        """測試刪除對話時遇到缺少 id 的資料不應觸發 KeyError"""
        monkeypatch.setattr(config, "USERS_DB_PATH", temp_db_path)
        save_users(
            {
                "session_user": {
                    "created_at": 1700000000,
                    "profile": None,
                    "chat_sessions": [
                        {"title": "missing-id"},
                        {"id": "target-id", "title": "to-delete"},
                    ],
                }
            }
        )

        assert delete_session("session_user", "target-id") is True
        remaining_sessions = get_user_sessions("session_user")
        assert len(remaining_sessions) == 1
        assert remaining_sessions[0].get("title") == "missing-id"
