import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random
import re

import urllib.parse

def scrape_taiko_wiki():
    categories = ['ポップス', 'キッズ', 'アニメ', 'ボーカロイド™曲', 'ゲームミュージック', 'バラエティ', 'クラシック', 'ナムコオリジナル', '段位道場課題曲']
    base_url = "https://wikiwiki.jp/taiko-fumen/%E4%BD%9C%E5%93%81/%E6%96%B0AC/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    songs = []

    category_prefixes = {
        'ポップス': 100000,
        'キッズ': 200000,
        'アニメ': 300000,
        'ボーカロイド™曲': 400000,
        'ゲームミュージック': 500000,
        'バラエティ': 600000,
        'クラシック': 700000,
        'ナムコオリジナル': 800000,
        '段位道場課題曲': 900000
    }
    
    # 用字典記錄每個類別目前的計數器
    category_counters = {k: 1 for k in categories}

    for category in categories:
        encoded_category = urllib.parse.quote(category)
        url = base_url + encoded_category
        print(f"正在請求與解析 wikiwiki.jp 歌曲列表 ({category})...")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 加上隨機延遲保護伺服器
            delay = random.uniform(3, 5)
            print(f"等待 {delay:.2f} 秒再進行後續動作...")
            time.sleep(delay)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 抓取包含歌曲資料的超大表格
            tables = soup.find_all('table')
            
            # 尋找行數最多的表格（通常是資料表本身）
            target_table = None
            max_rows = 0
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > max_rows:
                    max_rows = len(rows)
                    target_table = table
                    
            if not target_table or max_rows < 5:
                print(f"找不到 {category} 包含資料的表格！")
                continue
                
            rows = target_table.find_all('tr')
            
            # 第一、二列通常是 Header，我們嘗試解析後續資料列
            for row in rows[2:]:
                cols = row.find_all(['td', 'th'])
                # Namco 表格通常有 9 欄: [日期, 收錄標記, 曲名, BPM, 簡單, 普通, 困難, 鬼, 裡鬼(若有)]
                if len(cols) < 5:
                    continue
                    
                texts = [c.get_text(strip=True) for c in cols]
                
                # 使用更強健的解析
                title_cell_strings = list(cols[2].stripped_strings) if len(cols) > 2 else []
                title = str(title_cell_strings[0]) if len(title_cell_strings) > 0 else ""
                subtitle = " ".join([str(s) for s in title_cell_strings[1:]]) if len(title_cell_strings) > 1 else ""
                
                # 忽略表頭或標題行，並過濾掉限定曲
                if not title or title in ["曲名", category] or "【限定】" in title:
                    continue
                    
                # 解析 BPM，如實保留例如 "9.38?-150"
                bpm = texts[3].strip() if len(texts) > 3 else "0"
                    
                # 解析鬼級難度
                oni_star = 0
                detail_url = ""
                if len(cols) > 7:
                    oni_cell = cols[7]
                    oni_text = oni_cell.get_text(strip=True)
                    match_oni = re.search(r'(?:★[×x]?)?(\d+)', oni_text)
                    if match_oni:
                        oni_star = int(match_oni.group(1))
                    
                    oni_link = oni_cell.find('a')
                    if oni_link:
                        detail_url = urllib.parse.urljoin(url, oni_link.get('href'))
                        
                # 預設資料結構 - 表鬼
                song = {
                    "id": category_prefixes[category] + category_counters[category],
                    "title": title,
                    "subtitle": subtitle,
                    "genre": category,  # 動態對應當前分類
                    "difficulty": {
                        "oni": oni_star
                    },
                    "bpm": bpm,
                    "detail_url": detail_url,
                    "features": [],
                    "description": f"這是由系統自動爬取自 wikiwiki.jp 的 {category} 資料。"
                }
                songs.append(song)
                category_counters[category] += 1
                
                # 檢查裏譜面 (Ura) - 通常在 index 8
                ura_oni_star = 0
                ura_detail_url = ""
                if len(cols) > 8:
                    ura_cell = cols[8]
                    ura_text = ura_cell.get_text(strip=True)
                    
                    # 有些儲存格只有一個 "-"，過濾掉長度過短且沒有數字的狀況
                    if "★" in ura_text or any(c.isdigit() for c in ura_text):
                        match_ura = re.search(r'(?:★[×x]?)?(\d+)', ura_text)
                        if match_ura:
                            ura_oni_star = int(match_ura.group(1))
                            
                            ura_link = ura_cell.find('a')
                            if ura_link:
                                ura_detail_url = urllib.parse.urljoin(url, ura_link.get('href'))
                            
                            # 如果有裏譜面，新增一首獨立的條目
                            ura_song = {
                                "id": category_prefixes[category] + category_counters[category],
                                "title": title + " (Inner Oni)",
                                "subtitle": subtitle,
                                "genre": category,
                                "difficulty": {
                                    "oni": ura_oni_star
                                },
                                "bpm": bpm,
                                "detail_url": ura_detail_url,
                                "features": ["Inner Oni"],
                                "description": f"這是由系統自動爬取自 wikiwiki.jp 的 {category} (Inner Oni) 資料。"
                            }
                            songs.append(ura_song)
                            category_counters[category] += 1

            print(f"成功從 {category} 爬取資料！累計 {len(songs)} 首曲目。")

        except Exception as e:
            print(f"爬取 {category} 分類時發生錯誤: {e}")
            continue

    print(f"總共成功爬取到 {len(songs)} 首基礎曲目資料！")
    return songs

def merge_and_save(new_songs, db_path="data/songs.json"):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    existing_songs = []
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                existing_songs = json.load(f)
        except:
            pass
            
    # 去除舊資料中的限定曲
    existing_songs = [s for s in existing_songs if "【限定】" not in s.get("title", "")]
            
    # 建立以 title 為 key 的字典，方便 O(1) 尋找與更新
    existing_dict = {s['title']: s for s in existing_songs if s.get('title')}
    added_count = 0
    updated_count = 0
    
    for ns in new_songs:
        if not ns['title'] or "【限定】" in ns['title']: continue
        
        if ns['title'] in existing_dict:
            # 已經存在，只更新基礎屬性 (BPM, detail_url, difficulty)
            # 絕對不能覆蓋 max_combo, strategy_text, features
            ex = existing_dict[ns['title']]
            ex['bpm'] = ns['bpm']
            ex['difficulty'] = ns.get('difficulty', ex.get('difficulty'))
            # 若爬蟲抓到新的正確 url 也更新
            if ns.get('detail_url'):
                ex['detail_url'] = ns['detail_url']
            updated_count += 1
        else:
            # 新歌
            existing_dict[ns['title']] = ns
            added_count += 1
            
    # 轉回 list 並依照 id 排序 (可選)
    final_songs = list(existing_dict.values())
            
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(final_songs, f, indent=2, ensure_ascii=False)
        
    print(f"合併完成！新增 {added_count} 首，更新了 {updated_count} 首基礎資料 (BPM字串化)。")

if __name__ == "__main__":
    scraped = scrape_taiko_wiki()
    if scraped:
        merge_and_save(scraped)
