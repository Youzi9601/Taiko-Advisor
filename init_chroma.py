import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

db_path = "e:/workplace/taiko_ai/data/songs.json"
chroma_path = "e:/workplace/taiko_ai/data/chroma_db"

def init_chromadb():
    print("載入嵌入模型 (這可能需要一點時間)...")
    # 使用輕量的多國語言模型，對中文和日文支援較好
    encoder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    
    print(f"連接或建立 ChromaDB (路徑: {chroma_path})...")
    client = chromadb.PersistentClient(path=chroma_path)
    
    print("取得或建立集合 'taiko_songs'...")
    collection = client.get_or_create_collection(name="taiko_songs")
    
    print("讀取現有的 songs.json...")
    with open(db_path, "r", encoding="utf-8") as f:
        songs = json.load(f)
        
    ids = []
    documents = []
    metadatas = []
    
    print(f"準備寫入 {len(songs)} 首歌的資料...")
    for song in songs:
        # 轉換為字串 ID
        ids.append(str(song["id"]))
        
        # 建立這首歌的文字描述，這個將用來轉換成向量並比對
        genre = song.get("genre", "")
        title = song.get("title", "")
        subtitle = song.get("subtitle", "")
        features = ", ".join(song.get("features", []))
        desc = song.get("description", "")
        bpm = song.get("bpm", 0)
        oni_star = song.get("difficulty", {}).get("oni", 0)
        max_combo = song.get("max_combo", 0)
        
        doc_text = f"曲名: {title}\n副標題/作者: {subtitle}\n類別: {genre}\n難度: 鬼級 {oni_star} 星\nBPM: {bpm}\n特色: {features}\n描述: {desc}"
        if max_combo:
            doc_text += f"\n最大連擊數 (Max Combo): {max_combo}"
            
        documents.append(doc_text)
        
        # 儲存 metadata，方便後續直接取用原始 JSON 物件
        song_json = json.dumps(song, ensure_ascii=False)
        metadatas.append({"json": song_json, "title": title, "subtitle": subtitle, "genre": genre})
    
    # 批次把資料丟進 Embedding 模型產生向量
    print("開始計算向量 (Embedding)...")
    embeddings = encoder.encode(documents).tolist()
    
    # 批次存入 ChromaDB
    # 為避免一次塞太多，我們切分批次
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        end_idx = min(i + batch_size, len(ids))
        print(f"正在存入索引 {i} 到 {end_idx - 1}...")
        collection.upsert(
            ids=ids[i:end_idx],
            embeddings=embeddings[i:end_idx],
            documents=documents[i:end_idx],
            metadatas=metadatas[i:end_idx]
        )
        
    print("ChromaDB 初始化完成！")

if __name__ == "__main__":
    init_chromadb()
