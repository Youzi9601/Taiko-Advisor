import json
import os
import re
import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from google import genai
from google.genai import types
import config

# 配置日誌
logger = logging.getLogger(__name__)

if not config.GEMINI_API_KEY:
    logger.error("❌ GEMINI_API_KEY 未設置，程式終止")
    exit(1)

try:
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    logger.info("✅ Gemini 客戶端初始化成功")
except Exception as e:
    logger.error(f"❌ Gemini 客戶端初始化失敗: {e}")
    exit(1)


def load_songs():
    if os.path.exists(config.SONGS_DB_PATH):
        with open(config.SONGS_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_songs(songs):
    with open(config.SONGS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(songs, f, indent=2, ensure_ascii=False)


def fetch_details(url):
    try:
        r = requests.get(url, headers=config.HTTP_HEADERS, timeout=config.HTTP_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        max_combo = 0
        strategy_text = ""

        # 1. 抓取最大連段 (Max Combo)
        for t in soup.find_all("table"):
            if "最大コンボ数" in t.text or "最大コンボ" in t.text:
                for tr in t.find_all("tr"):
                    tds = tr.find_all(["th", "td"])
                    for i, td in enumerate(tds):
                        txt = td.text.replace("\n", "").strip(" \t\r*xX×★")
                        if "★" in td.text and txt.isdigit():
                            if i + 1 < len(tds):
                                val_str = (
                                    tds[i + 1]
                                    .get_text(separator=" ")
                                    .strip()
                                    .replace(",", "")
                                )
                                m = re.search(r"\d+", val_str)
                                if m:
                                    max_combo = int(m.group())
                                    break
                    if max_combo > 0:
                        break
                if max_combo > 0:
                    break

        # 2. 抓取攻略內文
        headings = soup.find_all(["h2", "h3", "h4"])
        for h in headings:
            if "譜面構成" in h.text or "攻略" in h.text:
                ul = h.find_next_sibling("ul")
                if ul:
                    strategy_text = ul.get_text(separator="\n", strip=True)
                break

        logger.debug(f"成功抓取詳細頁: max_combo={max_combo}, strategy_length={len(strategy_text)}")
        return max_combo, strategy_text
    except Exception as e:
        logger.error(f"❌ 詳細頁抓取失敗 ({url}): {e}")
        return 0, ""


def generate_ai_tags(strategy_text):
    prompt = config.TAG_GENERATION_PROMPT_TEMPLATE.format(strategy_text=strategy_text)
    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="你是一個嚴謹的自動萃取關鍵字系統。你只能輸出用逗號分隔的標籤，嚴禁任何多餘對話或自行想像的非客觀詞彙。",
            ),
        )
        out = f"{response.text}"
        tags_str = out.replace("，", ",").strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        logger.debug(f"AI 萃取標籤: {tags[:4]}")
        return tags[:4]
    except Exception as e:
        logger.error(f"❌ Gemini API 調用失敗: {e}")
        return ["API錯誤"]


def get_bpm_tag(bpm_val):
    """
    根據 BPM 值返回對應的速度標籤
    
    返回值:
    - 低BPM: 低於 160
    - 一般速度: 160-220
    - 高BPM: 220-260
    - 超高BPM: 260 及以上
    - None: 無法解析
    """
    try:
        nums = re.findall(r"\d+(?:\.\d+)?", str(bpm_val))
        if not nums:
            logger.debug(f"BPM 無法解析: {bpm_val}")
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
    except (ValueError, TypeError) as e:
        logger.debug(f"BPM 解析例外 (值: {bpm_val}): {e}")
        return None
    return None


def main():
    songs = load_songs()
    if not songs:
        logger.error("❌ 沒有找到歌曲資料！")
        return

    logger.info(f"開始處理 {len(songs)} 首歌曲...")
    updated_count = 0

    for i, song in enumerate(songs):
        changed = False

        # err_tags = ["API錯誤", "運算錯誤", "API額度耗盡"]

        # 為了強制套用新的嚴格 AI 規則與 BPM 標籤，我們在此次執行中無視舊的 AI 標籤
        curr_features = song.get("features", [])
        # has_error = any(tag in curr_features for tag in err_tags)

        # 只保留 Inner Oni 與 人工處理，其他 AI 標籤全部洗掉重算
        curr_features = [f for f in curr_features if f in ["Inner Oni", "人工處理"]]
        song["features"] = curr_features

        needs_fetch = "strategy_text" not in song or (song.get("max_combo", 0) == 0)

        # 如果有詳細頁網址且尚未抓取攻略內文 或 combo為0
        if song.get("detail_url") and needs_fetch:
            logger.info(f"[{i+1}/{len(songs)}] 正在重新抓取詳細頁: {song['title']}")
            combo, strategy = fetch_details(song["detail_url"])
            if combo > 0:
                song["max_combo"] = combo
                logger.debug(f"  ✓ 抓取 max_combo: {combo}")
            if strategy:
                song["strategy_text"] = strategy
                logger.debug(f"  ✓ 抓取攻略內文: {len(strategy)} 字元")
            changed = True
            time.sleep(random.uniform(0.5, 1.5))  # 禮貌性爬蟲延遲

        # needs_tagging = "strategy_text" in song and len(song["strategy_text"]) >= 50

        # 準備打標籤
        if "strategy_text" in song:
            strategy_text = song["strategy_text"]

            # [USER RULE] 若文本過短，不呼叫 API，直接標註人工處理
            if len(strategy_text) < 50:
                logger.info(
                    f"[{i+1}/{len(songs)}] 文本過短 ({len(strategy_text)} 字)，標註 [人工處理]: {song['title']}"
                )
                if "人工處理" not in curr_features:
                    curr_features.append("人工處理")
                song["features"] = curr_features
                changed = True
            else:
                logger.info(f"[{i+1}/{len(songs)}] 送出予 Gemini 萃取標籤: {song['title']}")
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
                logger.debug(f"  ✓ 新增標籤: {new_features}")
                changed = True

        if changed:
            updated_count += 1
            # 每處理 10 首就存檔一次，確保斷點續傳機制
            if updated_count % 10 == 0:
                logger.info(f"✅ 已處理 {updated_count} 首，自動存檔中...")
                save_songs(songs)

    # 最終存檔
    if updated_count > 0:
        save_songs(songs)
        logger.info(f"✅ 處理完成！共更新了 {updated_count} 首歌曲。")
    else:
        logger.info("ℹ️ 所有歌曲皆已處理完畢，無需更新。")


if __name__ == "__main__":
    main()
