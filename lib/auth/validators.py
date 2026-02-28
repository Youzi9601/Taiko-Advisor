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
    
    # 統一換行符：將 Windows 風格的換行符 \r\n 以及單獨的 \r 視為 \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 壓縮連續換行符（3 個以上壓縮為 2 個）
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 限制最大行數，避免極端長的多行內容
    max_lines = 50
    lines = text.split('\n')
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        text = '\n'.join(lines)
    
    # 移除大部分控制字符（\x00-\x09, \x0b-\x0c, \x0e-\x1f, \x7f-\x9f），其中刻意排除 \x0a，
    # 以保留換行符 \n (\x0a)，維持多行輸入（如提示詞、程式碼片段等）的結構與可讀性。
    # 此處已對多行內容做了基本限制（統一換行符與限制最大行數），實際使用時仍需搭配
    # 更高層級的 Prompt Injection 防護與權限隔離。
    text = re.sub(r'[\x00-\x09\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
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
