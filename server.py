"""
太鼓之達人 AI 顧問 - 主應用程式入口點
簡化版本：所有業務邏輯已模塊化到 lib/ 和 api/ 目錄

目錄結構：
lib/
  ├── auth/          # 身份驗證模塊
  │   ├── token_manager.py
  │   └── validators.py
  ├── services/      # 業務邏輯服務
  │   ├── user_service.py
  │   └── chat_service.py
  └── utils/         # 工具函數

api/                 # API 路由
  ├── login/
  │   └── route.py
  ├── profile/
  │   └── route.py
  ├── sessions/
  │   └── route.py
  └── chat/
      └── route.py
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
import os
import json
import logging
from uuid import uuid4

import config
from lib.dependencies import init_resources, cleanup_resources
from lib.exceptions import TaikoAdvisorException
from api.login.route import router as login_router
from api.profile.route import router as profile_router
from api.sessions.route import router as sessions_router
from api.chat.route import router as chat_router

logger = logging.getLogger(__name__)

# ============================================================================
# 生命週期管理
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時初始化資源
    logger.info("啟動 Taiko AI Advisor...")
    init_resources(
        gemini_key=config.GEMINI_API_KEY or "",
        chroma_path=config.CHROMA_DB_PATH,
        collection_name=config.CHROMA_COLLECTION_NAME,
        songs_path=config.SONGS_DB_PATH,
    )
    logger.info("資源初始化完成")
    
    yield
    
    # 關閉時清理資源
    logger.info("清理資源...")
    cleanup_resources()
    logger.info("Taiko AI Advisor 已關閉")

# ============================================================================
# 初始化 FastAPI 應用
# ============================================================================
app = FastAPI(
    title=config.API_TITLE,
    description="""
    ## 太鼓之達人 AI 遊玩顧問 API
    
    ### 認證
    大部分端點需要 `Authorization: Bearer <access_code>` header
    
    ### 速率限制
    - 聊天端點: 10 次/分鐘
    - 其他端點: 30 次/分鐘
    """,
    version="2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "auth", "description": "認證相關端點"},
        {"name": "profile", "description": "用戶個人資料管理"},
        {"name": "sessions", "description": "對話歷史管理"},
        {"name": "chat", "description": "AI 聊天與推薦"}
    ]
)

# ============================================================================
# 速率限制
# ============================================================================
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: Exception) -> Response:
    """處理速率限制異常"""
    error_id = str(uuid4())[:8].upper()
    logger.warning(f"[{error_id}] Rate limit exceeded for {request.client.host if request.client else 'unknown'} (path: {request.url.path})")
    return Response(
        content=json.dumps({
            "error": "請求次數過多",
            "detail": "請稍後再試",
            "error_id": error_id
        }),
        status_code=429,
        media_type="application/json"
    )

# ============================================================================
# 統一異常處理
# ============================================================================
@app.exception_handler(TaikoAdvisorException)
async def taiko_exception_handler(request: Request, exc: TaikoAdvisorException):
    """處理自定義異常"""
    logger.warning(f"[{exc.error_id}] {exc.__class__.__name__}: {exc.message} (path: {request.url.path})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "error_id": exc.error_id  # 返回 error_id 供客戶端日誌記錄
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """處理未預期的異常"""
    error_id = str(uuid4())[:8].upper()
    logger.error(f"[{error_id}] Unhandled exception: {exc} (path: {request.url.path})", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "伺服器內部錯誤",
            "error_id": error_id  # 返回 error_id 供客戶端追蹤
        }
    )


# ============================================================================
# 安全中間件
# ============================================================================
class LimitRequestSizeMiddleware(BaseHTTPMiddleware):
    """限制請求體積大小"""
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > config.MAX_REQUEST_SIZE:
                logger.warning(f"請求體積過大: {content_length} bytes (path: {request.url.path})")
                return JSONResponse(
                    status_code=413,
                    content={"error": "請求體積過大，上限為 1MB"}
                )
        return await call_next(request)

app.add_middleware(LimitRequestSizeMiddleware)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """添加安全 HTTP Headers。
    
    安全說明：
    - 外部腳本（CDN）：允許加載
    - 內聯腳本：已移除 'unsafe-inline'
    - 內聯樣式：使用 nonce 機制保護
    """
    # 為此請求生成唯一的 CSP nonce
    nonce = str(uuid4())[:12]
    request.state.csp_nonce = nonce
    
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Content-Security-Policy: 增強安全，移除對 'unsafe-inline' 的依賴
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "  # ✅ 移除 'unsafe-inline'
        f"style-src 'self' 'nonce-{nonce}' 'unsafe-inline'; "  # ⚠️ 過渡方案
        "img-src 'self' data: https:; "
        "font-src 'self' https:; "
        "connect-src 'self' https://cdn.jsdelivr.net https://generativelanguage.googleapis.com; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return response


# CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS if isinstance(config.CORS_ORIGINS, list) else ["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Trusted Host 中間件
# 在開發環境（DEBUG=True）下停用 TrustedHostMiddleware，以支持 LAN IP、容器網域或反向代理存取
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
if not DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=config.TRUSTED_HOSTS
    )


# ============================================================================
# 資源初始化
# ============================================================================
os.makedirs(config.STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


# ============================================================================
# 註冊 API 路由
# ============================================================================
# /api/login
app.include_router(login_router, prefix="/api/login", tags=["auth"])

# /api/profile
app.include_router(profile_router, prefix="/api/profile", tags=["profile"])

# /api/sessions
app.include_router(sessions_router, prefix="/api/sessions", tags=["sessions"])

# /api/chat 和 /api/logout
app.include_router(chat_router, prefix="/api", tags=["chat"])


# ============================================================================
# 主頁路由
# ============================================================================
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """提供前端 HTML"""
    try:
        index_path = os.path.join(config.STATIC_DIR, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>找不到 index.html 檔案</h1>"


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    from lib.dependencies import get_client, get_collection, get_all_songs
    import sys
    
    client = get_client()
    collection = get_collection()
    all_songs = get_all_songs()
    
    # 檢查所有依賴
    checks = {
        "gemini": client is not None,
        "chromadb": collection is not None,
        "songs_loaded": len(all_songs) > 0,
        "user_db_writable": os.access(config.USERS_DB_PATH, os.W_OK) if os.path.exists(config.USERS_DB_PATH) else True
    }
    
    all_healthy = all(checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": "2.0",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "checks": checks,
        "songs_count": len(all_songs)
    }


# ============================================================================
# 應用啟動
# ============================================================================
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
