# Taiko AI Advisor (太鼓之達人 AI 遊玩顧問)

這是一個基於 Python 與 FastAPI 的太鼓之達人 AI 遊玩顧問系統。利用最新的網頁爬蟲與 Gemini 大語言模型，系統會學習海量的譜面特徵，並透過向量搜尋 (ChromaDB) 幫助玩家根據難度段位、打法偏好、BPM等自定義需求推薦合適的遊玩曲目。
註 : 所有程式碼均使用vibe coding

## ✨ 核心特色
- **🤖 AI 驅動的推薦系統**：使用 Gemini 模型深度分析網路攻略，自動萃取譜面標籤（高BPM、體力向、三連音等）
- **🔍 語意向量搜尋**：ChromaDB 向量搜尋實現自然語言查詢
- **🎮 個人畫像記憶**：存取代碼登入，記住玩家的「太鼓履歷」（段位、愛好星級、打法風格）
- **💬 聊天與對話管理**：最多三組歷史對話紀錄，串流式動態回覆

## 📁 專案結構

### 核心文件
- `server.py`: FastAPI 應用程式入口點，包含中間件與路由註冊
- `config.py`: 集中配置文件（API Key、資料庫路徑、安全設定等）
- `scraper.py`: 從 wikiwiki 爬取並過濾歌曲清單
- `generate_tags.py`: AI 特徵精煉器，抓取最大連擊數與譜面標籤
- `init_chroma.py`: 將歌曲轉換成 ChromaDB 向量庫

### 模塊化架構 (`lib/` 目錄)
```
lib/
├── auth/
│   ├── token_manager.py      # 令牌生命週期管理（過期驗證、登出）
│   └── validators.py          # 輸入驗證與清理
├── services/
│   ├── user_service.py        # 用戶數據操作（CRUD）
│   └── chat_service.py        # 聊天上下文構建與提示詞生成
├── utils/                     # 實用函數工具
└── dependencies.py            # FastAPI 依賴注入系統
```

### API 路由 (`api/` 目錄)
```
api/
├── login/route.py             # POST /api/login - 用戶認證
├── profile/route.py           # GET/POST /api/profile - 個人資料管理
├── sessions/route.py          # GET/POST/DELETE /api/sessions - 對話歷史
└── chat/route.py              # POST /api/chat, /api/logout - 聊天與登出
```

### 前端與資料
- `static/`: HTML / CSS / JS 前端介面
- `data/`: 歌曲庫 (`songs.json`) 與使用者帳戶 (`users.json`)

## 🚀 快速開始

### 基本需求
- Python 3.10+
- Gemini API Key
- Git

### 快速安裝

```bash
# 1. 克隆專案
git clone https://github.com/NatsuYukiowob/Taiko-Advisor.git
cd Taiko-Advisor

# 2. 創建虛擬環境並安裝依賴
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

# 3. 設定 API Key
cp .env.example .env
# 編輯 .env 並填入 GEMINI_API_KEY

# 4. 初始化數據庫（首次部署必做）
python scraper.py
python generate_tags.py
python init_chroma.py

# 5. 創建 data/users.json（見部署指南）

# 6. 啟動伺服器
python server.py
```

訪問 `http://127.0.0.1:8000` 開始使用！

### 📖 詳細文檔

**重要提示：** 本專案的歌曲資料庫 (`data/songs.json`)、向量快取 (`chroma_db`) 以及使用者設定 (`data/users.json`) 不包含在版本控制中，需要自行建立。

完整的部署說明、Docker 配置、生產環境設定等詳見：
- **[部署指南 (DEPLOYMENT_GUIDE.md)](DEPLOYMENT_GUIDE.md)** - 完整的安裝與配置步驟
- **本地開發環境** - 詳細的開發環境設置
- **Docker 部署** - 容器化部署方案
- **生產環境配置** - Nginx、SSL、Systemd 等配置
- **性能優化與監控** - 最佳實踐與故障排除

## 👨‍💻 技術堆疊
* **Backend:** FastAPI, Python
* **AI & NLP:** Google Gemini 2.5 Flash, Sentence-Transformers
* **Vector DB:** ChromaDB
* **Frontend:** HTML5, Vanilla JS, CSS (Glassmorphism UI), Marked.js

## 📄 License
MIT License.
