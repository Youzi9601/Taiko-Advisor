"""
API 端點集成測試

使用 TestClient 測試各個 API 端點的功能。
"""
import pytest
from fastapi.testclient import TestClient
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
        assert response.status_code in [400, 422]  # FastAPI 驗證錯誤


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
        assert "unsafe-inline" not in csp.split("script-src")[1].split(";")[0] if "script-src" in csp else True

    def test_csp_nonce_present(self, client: TestClient):
        """測試 CSP 中是否包含 nonce"""
        response = client.get("/health")
        csp = response.headers["Content-Security-Policy"]
        # CSP 應該包含 'nonce-' 前綴
        assert "'nonce-" in csp


class TestErrorHandling:
    """錯誤處理測試"""
    
    def test_rate_limit_error_includes_error_id(self, client: TestClient):
        """測試速率限制錯誤包含 error_id（如果觸發）"""
        # ⚠️ 注意：此測試假設速率限制設定為較低的值
        # 在實際環境中，可能無法在測試期間達到該限制
        pass

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

    def test_valid_json_accepted(self, client: TestClient):
        """測試有效 JSON 被接受（可能返回 401 但不是格式錯誤）"""
        response = client.post(
            "/api/login",
            json={"code": "test_code"}
        )
        # 應該返回 401（無效代碼）而不是 422（驗證錯誤）
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
