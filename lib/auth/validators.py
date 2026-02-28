"""
輸入驗證和清理模塊
"""
import re


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    驗證和清理用戶輸入的基礎函數。
    
    功能：
    - 限制長度
    - 移除控制字符
    - 壓縮過多的換行
    
    注意：這個函數只能做一般性的輸入清理，無法單獨「防止」或「抵禦」
    Prompt Injection 等複雜攻擊場景，實際使用時仍需搭配嚴謹的系統設計、
    權限隔離與模型提示設計等其他安全措施。
    """
    if not text or not isinstance(text, str):
        return ""
    
    # 限制長度
    text = text[:max_length]
    
    # 移除控制字符和危險字符
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # 移除過多的換行符（防止用戶填充大量換行符）
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def validate_required_field(value: str, field_name: str, max_length: int = 50) -> tuple[bool, str]:
    """
    驗證必需字段
    返回: (是否有效, 錯誤信息或清理後的值)
    """
    if not value:
        return False, f"{field_name}不能為空"
    
    cleaned = sanitize_input(value, max_length=max_length)
    if not cleaned:
        return False, f"{field_name}包含無效字符"
    
    return True, cleaned
