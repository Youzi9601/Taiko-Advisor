"""
自定義異常類 - Taiko Advisor Exception Classes
"""
from uuid import uuid4


class TaikoAdvisorException(Exception):
    """基礎異常類"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        self.error_id = str(uuid4())[:8].upper()  # 簡短的唯一 ID 用於日誌追蹤
        super().__init__(self.message)


class AuthenticationError(TaikoAdvisorException):
    """認證失敗異常"""
    def __init__(self, message: str = "認證失敗"):
        super().__init__(message, 401)


class ValidationError(TaikoAdvisorException):
    """驗證失敗異常"""
    def __init__(self, message: str):
        super().__init__(message, 400)


class ResourceNotFoundError(TaikoAdvisorException):
    """資源不存在異常"""
    def __init__(self, message: str = "資源不存在"):
        super().__init__(message, 404)


class RateLimitError(TaikoAdvisorException):
    """速率限制異常"""
    def __init__(self, message: str = "請求過於頻繁，請稍後再試"):
        super().__init__(message, 429)
