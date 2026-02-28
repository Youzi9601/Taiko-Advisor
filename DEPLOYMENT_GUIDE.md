# 部署指南 - Taiko AI Advisor

此指南涵蓋在不同環境中部署 Taiko AI Advisor 的完整步驟。

## 📋 目錄

1. [本地開發環境](#本地開發環境)
2. [Docker 容器化部署](#docker-容器化部署)
3. [生產環境配置](#生產環境配置)
4. [性能優化](#性能優化)
5. [監控和日誌](#監控和日誌)
6. [故障排除](#故障排除)

---

## 本地開發環境

### 前置需求

- Python 3.10+
- Git
- 虛擬環境工具（venv 或 conda）

### 安裝步驟

```bash
# 1. 克隆倉庫
git clone https://github.com/NatsuYukiowob/Taiko-Advisor.git
cd Taiko-Advisor

# 2. 創建虛擬環境
python -m venv .venv

# 3. 激活虛擬環境
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# 4. 安裝依賴
pip install -r requirements.txt

# 5. 配置環境變數
cp .env.example .env
# 編輯 .env，填入 GEMINI_API_KEY

# 6. 初始化數據庫
python scraper.py          # 爬取歌曲
python generate_tags.py    # 生成標籤
python init_chroma.py      # 初始化向量庫

# 7. 設定使用者帳號
# 創建 data/users.json 並設置訪問代碼（見下方說明）

# 8. 啟動開發伺服器
python server.py
# 訪問 http://localhost:8000
```

### 設定使用者存取代碼

為了控制誰可以使用你的 AI，系統採用白名單存取代碼機制。請手動在 `data/` 資料夾中建立一份 `users.json`，格式如下：

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

**重要說明：**
- 將 `YOUR_SECRET_ACCESS_CODE` 替換成你要分發給使用者的密碼
- 當使用者初次登入時，profile 會自動建立
- 建議使用隨機字串作為存取代碼以提高安全性
- 歌曲資料庫 (`data/songs.json`)、向量快取 (`chroma_db`) 以及使用者設定 (`data/users.json`) 不包含在版本控制中，需要自行建立

### 開發命令

```bash
# 運行測試
pytest                    # 運行所有測試
pytest -v               # 詳細輸出
pytest --cov           # 生成覆蓋率報告
pytest tests/test_validators.py  # 運行特定測試

# 代碼檢查
# (可選) 使用 pylance/mypy/black 等工具
```

---

## Docker 容器化部署

### Dockerfile

創建 `Dockerfile`:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY . .

# 創建日誌目錄
RUN mkdir -p logs data

# 初始化數據庫（可選，取決於 data/ 是否上傳）
# RUN python scraper.py && python generate_tags.py && python init_chroma.py

# 暴露端口
EXPOSE 8000

# 啟動應用
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

創建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  taiko-advisor:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - LOG_LEVEL=INFO
      - VALIDATE_CONFIG=true
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 使用 Docker 部署

```bash
# 構建 Docker 鏡像
docker build -t taiko-advisor:latest .

# 使用 Docker Compose 啟動
docker-compose up -d

# 檢查日誌
docker-compose logs -f taiko-advisor

# 停止服務
docker-compose down
```

---

## 生產環境配置

### 1. 環境變數設置

```bash
# .env (生產環境)
GEMINI_API_KEY=your_production_key
LOG_LEVEL=INFO
DEBUG=false
VALIDATE_CONFIG=true
TOKEN_EXPIRY_DAYS=30
MAX_SESSIONS_PER_USER=5
```

### 2. 使用反向代理（Nginx）

`nginx.conf` 示例:

```nginx
upstream taiko_app {
    server localhost:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 配置
    ssl_certificate /etc/letsencrypt/live/your-domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 代理設置
    location / {
        proxy_pass http://taiko_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支援（如需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 靜態文件緩存
    location /static/ {
        expires 1h;
        proxy_pass http://taiko_app;
    }
}
```

### 3. Systemd 服務（Linux）

創建 `/etc/systemd/system/taiko-advisor.service`:

```ini
[Unit]
Description=Taiko AI Advisor
After=network.target

[Service]
Type=notify
User=taiko
WorkingDirectory=/opt/taiko-advisor
Environment="PATH=/opt/taiko-advisor/.venv/bin"
ExecStart=/opt/taiko-advisor/.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

啟動服務：

```bash
sudo systemctl start taiko-advisor
sudo systemctl enable taiko-advisor
```

---

## 性能優化

### 1. Uvicorn 多 Worker 配置

```bash
# 生產環境運行
uvicorn server:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker
```

### 2. 數據庫優化

- 定期備份 `data/users.json`
- 定期清理過期用戶（cron job）
- 考慮遷移到 PostgreSQL/MongoDB（未來版本）

### 3. 緩存策略

```python
# 在 config.py 添加
CACHE_TTL = 3600  # 1 小時
STATIC_FILE_CACHE_MAX_AGE = 86400  # 1 天
```

---

## 監控和日誌

### 日誌管理

日誌自動存儲在 `logs/taiko_advisor.log`

```bash
# 實時日誌監控
tail -f logs/taiko_advisor.log

# 按日期歸檔日誌
gzip logs/taiko_advisor.log $(date +%Y%m%d)
```

### 健康檢查

```bash
# 檢查應用健康狀態
curl http://localhost:8000/health

# 響應示例
{
    "status": "healthy",
    "version": "2.0",
    "python_version": "3.13.0",
    "checks": {
        "gemini": true,
        "chromadb": true,
        "songs_loaded": true,
        "user_db_writable": true
    },
    "songs_count": 1234
}
```

### 監控指標

建議監控以下指標：

- **API 響應時間** - 目標 < 2s
- **內存使用** - 目標 < 500MB
- **CPU 使用** - 目標 < 50%
- **錯誤率** - 目標 < 0.1%
- **並發連接數** - 取決於硬件

---

## 故障排除

### 常見問題

#### 1. GEMINI_API_KEY 未設置

**症狀：** 聊天功能返回 500 錯誤

**解決方案：**
```bash
# 檢查環境變數
echo $GEMINI_API_KEY

# 確認 .env 文件存在且正確
cat .env

# 重新啟動應用
python server.py
```

#### 2. ChromaDB 連接失敗

**症狀：** 聊天功能無法查詢歌曲

**解決方案：**
```bash
# 重新初始化 ChromaDB
python init_chroma.py

# 檢查 data/chroma_db 目錄是否存在
ls -la data/chroma_db/
```

#### 3. users.json 文件鎖定

**症狀：** 多個請求同時失敗

**解決方案：**
```bash
# 檢查文件鎖
ls -la data/users.json*

# 刪除舊鎖文件
rm data/users.json.lock

# 重新啟動應用
```

#### 4. 高記憶體使用

**症狀：** OOM killer 終止進程

**解決方案：**
- 減少歌曲庫大小
- 使用多進程架構
- 考慮遷移到數據庫

---

## 安全檢查清單

在生產部署前確保：

- [ ] HTTPS/SSL 已啟用
- [ ] GEMINI_API_KEY 未洩露
- [ ] DEBUG=false
- [ ] VALIDATE_CONFIG=true
- [ ] 防火牆已配置
- [ ] 日誌已正確重定向
- [ ] 備份策略已就位
- [ ] 監控已配置

---

## 支援和反饋

如果遇到部署問題，請：

1. 查看 `logs/taiko_advisor.log`
2. 在 GitHub 提交 Issue
3. 檢查本指南的故障排除部分

祝部署順利！🚀
