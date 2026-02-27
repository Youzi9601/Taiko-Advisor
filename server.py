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
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
import os

import config
from lib.dependencies import init_resources
from api.login.route import router as login_router
from api.profile.route import router as profile_router
from api.sessions.route import router as sessions_router
from api.chat.route import router as chat_router

# ============================================================================
# 初始化 FastAPI 應用
# ============================================================================
app = FastAPI(
    title=config.API_TITLE,
    description="太鼓之達人 AI 遊玩顧問 API",
    version="2.0"
)


# ============================================================================
# 安全中間件
# ============================================================================
@app.middleware("http")
async def add_security_headers(request, call_next):
    """添加安全 HTTP Headers"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
        "font-src 'self' https:;"
    )
    return response


# CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS if isinstance(config.CORS_ORIGINS, list) else ["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

# Trusted Host 中間件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=config.TRUSTED_HOSTS if hasattr(config, 'TRUSTED_HOSTS') else ["localhost", "127.0.0.1"]
)


# ============================================================================
# 資源初始化
# ============================================================================
os.makedirs(config.STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

# 初始化全局資源（通過依賴注入系統提供給路由）
init_resources(
    gemini_key=config.GEMINI_API_KEY or "",
    chroma_path=config.CHROMA_DB_PATH,
    collection_name=config.CHROMA_COLLECTION_NAME,
    songs_path=config.SONGS_DB_PATH,
)


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
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>找不到 index.html 檔案</h1>"


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    from lib.dependencies import get_client, get_collection, get_all_songs
    
    client = get_client()
    collection = get_collection()
    all_songs = get_all_songs()
    
    return {
        "status": "healthy",
        "version": "2.0",
        "gemini_available": client is not None,
        "chromadb_available": collection is not None,
        "songs_loaded": len(all_songs) > 0,
    }


# ============================================================================
# 應用啟動
# ============================================================================
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
