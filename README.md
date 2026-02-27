# Taiko AI Advisor (太鼓之達人 AI 遊玩顧問)

這是一個基於 Python 與 FastAPI 的太鼓之達人 AI 遊玩顧問系統。利用最新的網頁爬蟲與 Gemini 大語言模型，系統會學習海量的譜面特徵，並透過向量搜尋 (ChromaDB) 幫助玩家根據難度段位、打法偏好、BPM等自定義需求推薦合適的遊玩曲目。

## ✨ 核心特色
- **🤖 AI 驅動的推薦系統**：使用 Gemini 模型爬取並深度分析網路攻略文字，自動萃取出客觀的譜面標籤（如：高BPM、體力向、三連音為主）。
- **🔍 語意向量搜尋**：將包含 Max Combo 與 AI 標籤的歌曲資料嵌入為 ChromaDB 向量，實現自然語言查詢。
- **🎮 個人畫像記憶**：支援存取代碼登入，並能記住個人的「太鼓履歷」（最高段位、愛好星級、打法）。
- **💬 聊天室記憶與串流回覆**：儲存最多三組歷史對話紀錄，並且以打字機風格動態串流輸出。

## 專案結構
- `scraper.py`: 從 wikiwiki 爬取並過濾出純淨的歌曲清單。
- `generate_tags.py`: 深度爬蟲與 AI 特徵精煉器，抓取最大連擊數與特徵標籤。
- `init_chroma.py`: 將 `songs.json` 的歌曲轉換成 ChromaDB 語意向量庫。
- `server.py`: FastAPI 核心伺服器，負責與前端介接、Gemini 串流對答、與帳號驗證。
- `static/`: 前端 HTML / CSS / JS 介面代碼。
- `data/`: 存放 `songs.json` 歌曲庫與 `users.json` 帳號資料。

## 🚀 佈署與啟動指南

為了保護使用者隱私與資料庫運作效能，本專案的歌曲來源資料庫 (`data/songs.json`)、向量快取 (`chroma_db`) 以及使用者設定 (`data/users.json`) **不會包含在開源版本庫中**，你必須自己抓取與建立。

### 步驟 1：安裝套件與環境
```bash
git clone <本專案網址>
cd taiko_ai

# 建議使用虛擬環境
python -m venv venv
source venv/bin/activate  # Windows 輸入: venv\Scripts\activate

pip install -r requirements.txt
```

### 步驟 2：設定 API 授權金鑰
複製環境變數範例檔，並填入你的 Gemini API Key：
```bash
cp .env.example .env
```
*(請將你的 `GEMINI_API_KEY` 填入 `.env` 檔案中)*

### 步驟 3：[第一次佈署必做] 初始化資料庫
請確保留定足夠的時間讓程式透過網路抓取與分析資料：
```bash
# 1. 爬取原始歌曲與最大連擊數: (需時約幾分鐘)
python scraper.py

# 2. 呼叫 Gemini AI 精煉歌曲特色標籤 (有中斷接續機制):
python generate_tags.py

# 3. 嵌入 ChromaDB 語意向量庫:
python init_chroma.py
```

### 步驟 4：設定管理員與使用者帳號
為了控制誰可以使用你的 AI，系統採用白名單存取代碼機制。
請手動在 `data/` 資料夾中建立一份 `users.json`，格式如下：
```json
{
  "YOUR_SECRET_ACCESS_CODE_1": {
    "profile": null,
    "chat_sessions": []
  },
  "YOUR_SECRET_ACCESS_CODE_2": {
    "profile": null,
    "chat_sessions": []
  }
}
```
*把 `YOUR_SECRET_ACCESS_CODE` 替換成你要分發給朋友的密碼。當他們初次登入時，profile 就會自動建立。*

### 步驟 5：啟動伺服器
```bash
python server.py
# 或使用 uvicorn 正式運行：uvicorn server:app --host 0.0.0.0 --port 8000
```
現在打開瀏覽器前往 `http://127.0.0.1:8000` 即可開始玩囉！

## 👨‍💻 技術堆疊
* **Backend:** FastAPI, Python
* **AI & NLP:** Google Gemini 2.5 Flash, Sentence-Transformers
* **Vector DB:** ChromaDB
* **Frontend:** HTML5, Vanilla JS, CSS (Glassmorphism UI), Marked.js

## 📄 License
MIT License.
