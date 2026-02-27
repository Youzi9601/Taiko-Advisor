from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import json
import random
from google import genai
import chromadb
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 初始化 FastAPI
app = FastAPI(title="Taiko AI Advisor API")

# 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載靜態檔案 (前端)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 初始化 Gemini 與資料庫位置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
db_path = os.getenv("SONGS_DB_PATH", "data/songs.json")
chroma_path = os.path.join(os.path.dirname(db_path), "chroma_db")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# 初始化 ChromaDB
try:
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    collection = chroma_client.get_collection(name="taiko_songs")
except Exception as e:
    print(f"ChromaDB 初始化失敗: {e}")
    collection = None

# 讀取全部歌曲做為 Fallback
with open(db_path, 'r', encoding='utf-8') as f:
    all_songs = json.load(f)

users_path = os.getenv("USERS_DB_PATH", "data/users.json")

def load_users():
    if not os.path.exists(users_path):
        return {}
    with open(users_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users_data):
    with open(users_path, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, indent=2, ensure_ascii=False)

class MessageItem(BaseModel):
    role: str
    content: str
    
class ChatRequest(BaseModel):
    message: str
    code: str
    history: list[MessageItem] = []

class LoginRequest(BaseModel):
    code: str

class ProfileRequest(BaseModel):
    code: str
    name: str   # 玩家名稱
    level: str  # 最高段位
    star_pref: str  # 偏好星星數
    style: str  # 打法偏好

class SaveSessionRequest(BaseModel):
    code: str
    title: str
    messages: list[MessageItem]

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/login")
async def login_endpoint(req: LoginRequest):
    users = load_users()
    if req.code in users:
        user_data = users[req.code]
        # 回傳是否需要填寫 profile
        needs_profile = user_data.get("profile") is None
        return {"success": True, "needs_profile": needs_profile, "profile": user_data.get("profile")}
    return JSONResponse(status_code=401, content={"error": "無效的存取代碼。"})

@app.post("/api/profile")
async def profile_endpoint(req: ProfileRequest):
    users = load_users()
    if req.code not in users:
        return JSONResponse(status_code=401, content={"error": "無效的存取代碼。"})
        
    users[req.code]["profile"] = {
        "name": req.name,
        "level": req.level,
        "star_pref": req.star_pref,
        "style": req.style
    }
    save_users(users)
    return {"success": True, "message": "個人資料已儲存！"}

@app.get("/api/profile")
async def get_profile(code: str):
    users = load_users()
    if code not in users:
        return JSONResponse(status_code=401, content={"error": "無效的存取代碼。"})
    
    profile = users[code].get("profile")
    return {"profile": profile}

@app.get("/api/sessions")
async def get_sessions(code: str):
    users = load_users()
    if code not in users:
        return JSONResponse(status_code=401, content={"error": "無效的存取代碼。"})
    
    sessions = users[code].get("chat_sessions", [])
    return {"sessions": sessions}

@app.post("/api/sessions")
async def save_session(req: SaveSessionRequest):
    users = load_users()
    if req.code not in users:
        return JSONResponse(status_code=401, content={"error": "無效的存取代碼。"})
    
    user_data = users[req.code]
    sessions = user_data.get("chat_sessions", [])
    
    if len(sessions) >= 3:
        return JSONResponse(status_code=400, content={"error": "已達到儲存對話數量上限 (3個)，請先刪除舊的對話。"})
        
    import uuid
    new_session = {
        "id": str(uuid.uuid4()),
        "title": req.title,
        "messages": [{"role": m.role, "content": m.content} for m in req.messages]
    }
    
    sessions.append(new_session)
    user_data["chat_sessions"] = sessions
    save_users(users)
    
    return {"success": True, "session_id": new_session["id"]}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, code: str):
    users = load_users()
    if code not in users:
        return JSONResponse(status_code=401, content={"error": "無效的存取代碼。"})
        
    user_data = users[code]
    sessions = user_data.get("chat_sessions", [])
    
    new_sessions = [s for s in sessions if s["id"] != session_id]
    user_data["chat_sessions"] = new_sessions
    save_users(users)
    
    return {"success": True}

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    message = req.message
    code = req.code
    
    users = load_users()
    if code not in users:
        return JSONResponse(status_code=401, content={"error": "無效的存取代碼。"})
    
    user_data = users[code]
    profile = user_data.get("profile")
    profile_text = ""
    if profile:
        profile_text = f'''【玩家實力與偏好設定】
玩家名稱: {profile.get("name", "玩家")}
最高段位: {profile.get("level", "未知")}
偏好星級: {profile.get("star_pref", "未知")}
打法偏好: {profile.get("style", "未知")}
'''
    
    if not client:
        return JSONResponse(status_code=500, content={"error": "找不到 Gemini API Key"})

    candidate_songs = []
    
    if collection:
        try:
            # 進行語意查詢，取出前30筆
            results = collection.query(
                query_texts=[message],
                n_results=30
            )
            if results and results['metadatas'] and len(results['metadatas'][0]) > 0:
                for meta in results['metadatas'][0]:
                    song_obj = json.loads(meta['json'])
                    candidate_songs.append(song_obj)
        except Exception as e:
            print(f"ChromaDB 查詢發生錯誤: {e}")
    
    # Fallback 機制
    if not candidate_songs:
        candidate_songs = random.sample(all_songs, min(15, len(all_songs)))

    songs_context = json.dumps(candidate_songs, ensure_ascii=False)
    
    history_text = ""
    if req.history:
        history_text = "【之前的對話紀錄】\n"
        for msg in req.history:
            role_name = "玩家: " if msg.role == "user" else "顧問: "
            history_text += f"{role_name}{msg.content}\n"
        history_text += "\n"

    prompt = f"""你是一個專業、有耐心的「太鼓之達人」遊玩顧問。
請根據玩家的需求，從以下的【候選歌曲資料庫】中挑選出最適合的歌曲來推薦。
{profile_text}
{history_text}
- 如果玩家只是閒聊，請普通地回應他。
- 如果推薦的要求帶有難度要求，輸出時請直接輸出該難度的資訊，不要輸出其他難度的資訊。
- 若【玩家實力與偏好設定】有資料，請在推薦歌曲時，務必將這些偏好納入考量，挑選符合他實力與打法的歌曲。
- 請記得參考【之前的對話紀錄】(如果有)，接續之前的脈絡進行回覆。
- 推薦的歌曲以3首為上限。
- 如果是要求推薦，請將推薦出來的歌曲以漂亮地排版，包含曲名(使用橙色標記)、歌曲類別、難度&星級()、BPM。不要使用任何表情符號。
- 務必只能推薦存在於資料庫中的歌曲，如果資料庫中沒有完全匹配的，可以推薦最相近的歌曲，並委婉說明。
- 務必使用繁體中文回應。

【候選歌曲資料庫】：
{songs_context}

【玩家需求】：
{message}
"""
    try:
        def stream_generator():
            responseStream = client.models.generate_content_stream(
                model='gemini-2.5-flash-lite',
                contents=prompt,            
            )
            for chunk in responseStream:
                if chunk.text:
                    yield chunk.text

        return StreamingResponse(stream_generator(), media_type="text/plain")
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"LLM 發生錯誤: {str(e)}"})

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
