"""
輸入驗證和清理模塊
"""
import re


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    驗證和清理用戶輸入，防止 Prompt Injection 攻擊
    - 限制長度
    - 移除控制字符
    - 驗證編碼
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
