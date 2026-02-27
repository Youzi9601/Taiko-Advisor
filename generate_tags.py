import json
import os
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
DB_PATH = os.getenv("SONGS_DB_PATH", "data/songs.json")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("請先在 .env 設定 GEMINI_API_KEY")
    exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

def load_songs():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_songs(songs):
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(songs, f, indent=2, ensure_ascii=False)

import re

def fetch_details(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        
        max_combo = 0
        strategy_text = ""
        
        # 1. 抓取最大連段 (Max Combo)
        for t in soup.find_all('table'):
            if '最大コンボ数' in t.text or '最大コンボ' in t.text:
                for tr in t.find_all('tr'):
                    tds = tr.find_all(['th', 'td'])
                    for i, td in enumerate(tds):
                        txt = td.text.replace("\n", "").strip(' \t\r*xX×★')
                        if '★' in td.text and txt.isdigit():
                            if i + 1 < len(tds):
                                val_str = tds[i+1].get_text(separator=' ').strip().replace(',', '')
                                m = re.search(r'\d+', val_str)
                                if m:
                                    max_combo = int(m.group())
                                    break
                    if max_combo > 0:
                        break
                if max_combo > 0:
                    break
            
        # 2. 抓取攻略內文
        headings = soup.find_all(['h2', 'h3', 'h4'])
        for h in headings:
            if '譜面構成' in h.text or '攻略' in h.text:
                ul = h.find_next_sibling('ul')
                if ul:
                    strategy_text = ul.get_text(separator='\n', strip=True)
                break
                
        return max_combo, strategy_text
    except Exception as e:
        print(f"Fetch failed for {url}: {e}")
        return 0, ""

def generate_ai_tags(strategy_text):
    prompt = f"""請閱讀以下「太鼓之達人」的歌曲譜面攻略心得，並從中萃取出 1 到 4 個簡潔的遊戲特色標籤。
【重要規則】：
1. 嚴厲禁止自行想像或過度解讀，標籤必須是針對太鼓之達人常見的客觀譜面特徵，例如：三連音為主、長複合、節奏複雜、變速、體力向等。
2. 嚴禁出現與譜面客觀事實無關的主觀感受詞彙（例如「現場感」、「激昂」等）。
3. 嚴格使用繁體中文標記。
4. 只能輸出標籤，以逗號分隔，絕對不要輸出其它任何文字或解釋。

【攻略內容】：
{strategy_text}
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="你是一個嚴謹的自動萃取關鍵字系統。你只能輸出用逗號分隔的標籤，嚴禁任何多餘對話或自行想像的非客觀詞彙。",
            )
        )
        out = response.text
        tags_str = out.replace('，', ',').strip()
        tags = [t.strip() for t in tags_str.split(',') if t.strip()]
        return tags[:4]
    except Exception as e:
        print(f"Gemini API 發生錯誤: {e}")
        return ["API錯誤"]

def get_bpm_tag(bpm_val):
    try:
        nums = re.findall(r'\d+(?:\.\d+)?', str(bpm_val))
        if not nums:
            return None
        max_b = max(float(n) for n in nums)
        
        if max_b < 160:
            return "低BPM"
        elif 160 <= max_b <= 220:
            return "一般速度"
        elif 220 < max_b < 260:
            return "高BPM"
        elif max_b >= 260:
            return "超高BPM"
    except:
        pass
    return None

def main():
    songs = load_songs()
    if not songs:
        print("沒有找到歌曲資料！")
        return

    updated_count = 0

    for i, song in enumerate(songs):
        changed = False
        
        err_tags = ["API錯誤", "運算錯誤", "API額度耗盡"]
        
        # 為了強制套用新的嚴格 AI 規則與 BPM 標籤，我們在此次執行中無視舊的 AI 標籤
        curr_features = song.get("features", [])
        has_error = any(tag in curr_features for tag in err_tags)
        
        # 只保留 Inner Oni 與 人工處理，其他 AI 標籤全部洗掉重算
        curr_features = [f for f in curr_features if f in ["Inner Oni", "人工處理"]]
        song["features"] = curr_features
        
        needs_fetch = "strategy_text" not in song or (song.get("max_combo", 0) == 0)

        # 如果有詳細頁網址且尚未抓取攻略內文 或 combo為0
        if song.get("detail_url") and needs_fetch:
            print(f"[{i}/{len(songs)}] 正在重新抓取詳細頁: {song['title']}")
            combo, strategy = fetch_details(song["detail_url"])
            if combo > 0:
                song["max_combo"] = combo
            if strategy:
                song["strategy_text"] = strategy
            changed = True
            time.sleep(random.uniform(0.5, 1.5)) # 禮貌性爬蟲延遲
            
        needs_tagging = "strategy_text" in song and len(song["strategy_text"]) >= 50
        
        # 準備打標籤
        if "strategy_text" in song:
            strategy_text = song["strategy_text"]
            
            # [USER RULE] 若文本過短，不呼叫 API，直接標註人工處理
            if len(strategy_text) < 50:
                print(f"[{i}/{len(songs)}] 文本過短 ({len(strategy_text)} 字)，標註 [人工處理]: {song['title']}")
                if "人工處理" not in curr_features:
                    curr_features.append("人工處理")
                song["features"] = curr_features
                changed = True
            else:
                print(f"[{i}/{len(songs)}] 送出予 Qwen 萃取標籤: {song['title']}")
                tags = generate_ai_tags(strategy_text)
                
                new_features = list(curr_features)
                
                # 自動判讀 BPM 標籤
                bpm_tag = get_bpm_tag(song.get("bpm", 0))
                
                for t in tags:
                    if t not in new_features and t != bpm_tag:
                        new_features.append(t)
                        
                if bpm_tag and bpm_tag not in new_features:
                    new_features.append(bpm_tag)
                        
                song["features"] = new_features
                changed = True
                
        if changed:
            updated_count += 1
            # 每處理 10 首就存檔一次，確保斷點續傳機制
            if updated_count % 10 == 0:
                print(f"已處理 {updated_count} 首，自動存檔中...")
                save_songs(songs)
                
    # 最終存檔
    if updated_count > 0:
        save_songs(songs)
        print(f"處理完成！共更新了 {updated_count} 首歌曲。")
    else:
        print("所有歌曲皆已處理完畢，無需更新。")

if __name__ == "__main__":
    main()
