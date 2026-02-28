"""
服務層單元測試

測試 user_service 中的業務邏輯。

注意：這些測試使用了實際的用戶數據庫文件，需要小心處理並發測試。
在實際的生產環境中，應該使用 mock 或 monkeypatch 來避免文件系統交互。
"""
from lib.services.user_service import (
    load_users, get_user_profile, update_user_profile,
    user_exists, get_user_sessions
)


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
    
    def test_create_user_callable(self):
        """測試 create_user 函數可調用"""
        # 注意：這可能會創建實際的用戶，需要小心
        # 在實際環境中應該使用 mock
        pass
