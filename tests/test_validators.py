"""
輸入驗證器單元測試

測試 lib.auth.validators 模塊中的所有驗證函數。
"""
from lib.auth.validators import sanitize_input, validate_required_field


class TestSanitizeInput:
    """sanitize_input() 函數測試組"""

    def test_normal_input(self):
        """測試正常文本輸入"""
        assert sanitize_input("hello world") == "hello world"

    def test_empty_input(self):
        """測試空字符串"""
        assert sanitize_input("") == ""

    def test_max_length_limit(self):
        """測試長度限制"""
        long_text = "a" * 600
        result = sanitize_input(long_text, max_length=50)
        assert len(result) == 50

    def test_control_character_removal(self):
        """測試控制字符移除"""
        text = "hello\x00world\x1ftest"
        result = sanitize_input(text)
        assert "\x00" not in result
        assert "\x1f" not in result
        assert "helloworld" in result or "hello" in result

    def test_excessive_newlines_compression(self):
        """測試過多換行符壓縮"""
        text = "line1\n\n\n\nline2"
        result = sanitize_input(text)
        # 應該只有最多 2 個連續換行
        assert result.count("\n\n\n") == 0

    def test_strip_whitespace(self):
        """測試前後空白移除"""
        text = "  hello world  \n"
        result = sanitize_input(text)
        assert result == "hello world"

    def test_chinese_text(self):
        """測試中文文本支援"""
        text = "你好世界"
        result = sanitize_input(text)
        assert result == "你好世界"

    def test_special_characters(self):
        """測試特殊字符保留"""
        text = "test@email.com"
        result = sanitize_input(text)
        assert "@" in result


class TestValidateRequiredField:
    """validate_required_field() 函數測試組"""

    def test_valid_field(self):
        """測試有效字段"""
        is_valid, result = validate_required_field("valid_name", "名稱")
        assert is_valid is True
        assert result == "valid_name"

    def test_empty_field(self):
        """測試空字段"""
        is_valid, result = validate_required_field("", "名稱")
        assert is_valid is False
        assert "名稱" in result
        assert "不能為空" in result

    def test_max_length_enforcement(self):
        """測試最大長度限制"""
        long_name = "a" * 100
        is_valid, result = validate_required_field(long_name, "名稱", max_length=50)
        # 結果應該被截斷到 50 字符
        assert len(result) <= 50

    def test_invalid_characters_handling(self):
        """測試無效字符處理"""
        # 只有控制字符的輸入
        is_valid, result = validate_required_field("\x00\x1f", "名稱")
        assert is_valid is False
        assert "無效字符" in result

    def test_whitespace_only_field(self):
        """測試只有空白的字段"""
        is_valid, result = validate_required_field("   ", "名稱")
        # sanitize_input 會 strip，所以結果為空
        assert is_valid is False


# 集成測試
class TestValidatorIntegration:
    """驗證器的集成測試"""

    def test_full_validation_pipeline(self):
        """測試完整驗證流程"""
        # 模擬用戶名驗證
        user_input = "  玩家123  "
        is_valid, name = validate_required_field(user_input, "玩家名稱", max_length=50)
        assert is_valid is True
        assert name == "玩家123"

    def test_multi_field_validation(self):
        """測試多字段驗證"""
        fields = [
            ("玩家名稱", "有效名稱"),
            ("段位", "十段"),
            ("偏好", "高BPM")
        ]
        
        for field_name, value in fields:
            is_valid, result = validate_required_field(value, field_name, max_length=50)
            assert is_valid is True, f"{field_name} 驗證失敗"
