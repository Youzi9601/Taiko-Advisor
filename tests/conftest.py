"""
pytest 配置和共享 fixtures

此文件定義了所有測試可以使用的公共 fixtures。
"""
import pytest
import tempfile
import os



@pytest.fixture
def temp_db_path():
    """為測試創建臨時數據庫路徑"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "test_users.json")


@pytest.fixture
def sample_users_data():
    """提供範例用戶數據"""
    return {
        "test_code_123": {
            "created_at": 1700000000,
            "profile": {
                "name": "測試玩家",
                "level": "十段",
                "star_pref": "9星",
                "style": "綜合"
            },
            "chat_sessions": []
        },
        "test_code_456": {
            "created_at": 1700000000,
            "profile": None,
            "chat_sessions": []
        }
    }


@pytest.fixture
def sample_song_data():
    """提供範例歌曲數據"""
    return {
        "id": 100001,
        "title": "Test Song",
        "subtitle": "Test Artist",
        "genre": "ポップス",
        "difficulty": {"oni": 8},
        "bpm": "150-200",
        "detail_url": "https://example.com/song/1",
        "features": ["高BPM", "變速"],
        "description": "This is a test song for unit testing.",
        "max_combo": 750
    }


@pytest.fixture
def sample_chat_request():
    """提供範例聊天請求"""
    return {
        "message": "推薦一首鬼級 8 星的歌",
        "code": "test_code_123",
        "history": [
            {"role": "user", "content": "你好"},
            {"role": "model", "content": "你好！有什麼我可以幫忙的嗎？"}
        ]
    }


# 在測試前後的 hooks
def pytest_configure(config):
    """pytest 啟動時的配置"""
    # 設置 DEBUG 模式以停用 TrustedHostMiddleware（避免 TestClient 的 Host header 問題）
    os.environ["DEBUG"] = "True"
    # 創建測試日誌目錄
    os.makedirs("tests/logs", exist_ok=True)


def pytest_unconfigure(config):
    """pytest 結束時的清理"""
    # 可以在這裡做清理工作
    pass
