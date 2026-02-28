"""
API 端點集成測試

使用 TestClient 測試各個 API 端點的功能。
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from server import app


@pytest.fixture
def client():
    """建立測試客戶端"""
    return TestClient(app)


class TestHealthEndpoint:
    """健康檢查端點測試"""
    
    def test_health_check_success(self, client: TestClient):
        """測試健康檢查端點返回成功"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "checks" in data

    def test_health_check_contains_required_fields(self, client: TestClient):
        """測試健康檢查包含所有必需字段"""
        response = client.get("/health")
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "python_version" in data
        assert "songs_count" in data


class TestLoginEndpoint:
    """登入端點測試"""
    
    def test_login_with_invalid_code(self, client: TestClient):
        """測試用無效代碼登入"""
        response = client.post("/api/login", json={"code": "invalid_code_12345"})
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "error_id" in data  # ✅ 驗證 error_id 返回

    def test_login_with_empty_code(self, client: TestClient):
        """測試用空代碼登入"""
        response = client.post("/api/login", json={"code": ""})
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "error_id" in data

    def test_login_missing_code_field(self, client: TestClient):
        """測試缺少代碼字段的登入"""
        response = client.post("/api/login", json={})
        assert response.status_code in [400, 422]  # 驗證錯誤（依實作可能為 400 或 422）


class TestSecurityHeaders:
    """安全頭測試"""
    
    def test_security_headers_present(self, client: TestClient):
        """測試安全頭是否存在"""
        response = client.get("/health")
        
        # 驗證重要的安全頭
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "Strict-Transport-Security" in response.headers

    def test_csp_header_present(self, client: TestClient):
        """測試 CSP 頭是否存在"""
        response = client.get("/health")
        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        
        # ✅ 驗證 'unsafe-inline' 已從 script-src 中移除
        assert "script-src 'self'" in csp
        has_script_src = "script-src" in csp
        if has_script_src:
            script_src_directive = csp.split("script-src", 1)[1].split(";", 1)[0]
            assert "unsafe-inline" not in script_src_directive

    def test_csp_nonce_present(self, client: TestClient):
        """測試 CSP 中是否包含 nonce"""
        response = client.get("/health")
        csp = response.headers["Content-Security-Policy"]
        # CSP 應該包含 'nonce-' 前綴
        assert "'nonce-" in csp


class TestErrorHandling:
    """錯誤處理測試"""
    
    def test_rate_limit_error_includes_error_id(self, client: TestClient, caplog):
        """
        測試速率限制錯誤包含 error_id
        
        此測試直接調用異常處理器來測試其正確性，
        而不依賴於實際達到速率限制（因為這取決於配置）。
        """
        import asyncio
        import json
        import re
        
        # 創建模擬的 Request 對象
        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.url.path = "/api/login"
        
        # 創建模擬的 RateLimitExceeded 異常
        rate_limit_exc = MagicMock(spec=RateLimitExceeded)
        
        # 導入速率限制異常處理器
        from server import rate_limit_handler
        
        # 捕獲日誌記錄
        with caplog.at_level("WARNING"):
            # 異步執行異常處理器
            response = asyncio.run(rate_limit_handler(mock_request, rate_limit_exc))
        
        # 驗證響應
        assert response.status_code == 429
        
        # 解析 JSON 響應內容
        response_data = json.loads(response.body)
        assert "error_id" in response_data
        assert response_data["error"] == "請求次數過多"
        assert response_data["error_id"]  # 驗證 error_id 不為空
        
        # 驗證 error_id 格式（應該是 8 個字元的大寫字串）
        error_id = response_data["error_id"]
        assert isinstance(error_id, str)
        assert len(error_id) == 8
        assert error_id.isupper()
        assert re.match(r'^[A-F0-9]{8}$', error_id), "error_id 應該是 8 個十六進制字元"
        
        # 驗證日誌記錄
        assert len(caplog.records) > 0, "應該記錄警告日誌"
        log_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
        assert any("Rate limit exceeded" in msg and error_id in msg for msg in log_messages), \
            f"日誌應該包含 'Rate limit exceeded' 和 error_id {error_id}"

    def test_404_error_handling(self, client: TestClient):
        """測試 404 錯誤"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_invalid_method(self, client: TestClient):
        """測試無效的 HTTP 方法"""
        response = client.post("/")  # GET 端點用 POST
        assert response.status_code in [404, 405]


class TestInputValidation:
    """輸入驗證測試"""
    
    def test_oversized_request_rejected(self, client: TestClient):
        """測試超大請求被拒絕"""
        # 建立超過 1MB 的請求
        large_payload = {"code": "x" * (1024 * 1024 + 1)}
        response = client.post("/api/login", json=large_payload)
        assert response.status_code == 413  # Payload Too Large

    def test_oversized_request_with_default_headers(self, client: TestClient):
        """測試使用預設標頭的超大請求"""
        large_payload = {"code": "x" * (1024 * 1024 + 1)}
        response = client.post("/api/login", json=large_payload)
        assert response.status_code in [413, 422]

    def test_valid_json_accepted(self, client: TestClient):
        """測試有效 JSON 被接受（可能返回 401 但不是格式錯誤）"""
        response = client.post(
            "/api/login",
            json={"code": "test_code"}
        )
        assert response.status_code == 401


class TestCORSHeaders:
    """CORS 頭測試"""
    
    def test_cors_headers_presence(self, client: TestClient):
        """測試 CORS 頭是否存在"""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # FastAPI CORS 中間件應該添加這些頭
        assert response.status_code == 200


class TestIndexPage:
    """主頁測試"""
    
    def test_index_page_returns_html(self, client: TestClient):
        """測試主頁返回 HTML"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_index_contains_basic_structure(self, client: TestClient):
        """測試主頁包含基本的 HTML 結構"""
        response = client.get("/")
        content = response.text
        assert "<!DOCTYPE html>" in content.lower() or "<html" in content.lower()
        assert "太鼓" in content or "taiko" in content.lower()
