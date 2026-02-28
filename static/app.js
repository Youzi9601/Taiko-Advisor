const chatHistory = document.getElementById('chat-history');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const typingIndicator = document.getElementById('typing-indicator');
const statusIndicator = document.querySelector('.status-indicator');
const toastContainer = document.getElementById('toast-container');

let accessCode = localStorage.getItem('access_code');
let chatContext = [];
let currentSessions = [];

function showToast(message, type = 'info', duration = 3200) {
    if (!toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-hide');
        setTimeout(() => {
            toast.remove();
        }, 220);
    }, duration);
}

function showErrorMessage(message) {
    showToast(`❌ ${message}`, 'error');
}

function showSuccessMessage(message) {
    showToast(`✅ ${message}`, 'success');
}

function showLoginModal() {
    document.getElementById('auth-overlay').style.display = 'flex';
    document.getElementById('login-modal').style.display = 'block';
    document.getElementById('profile-modal').style.display = 'none';
}

async function restoreFromLocalAccessCode() {
    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: accessCode })
        });

        const data = await res.json();
        if (!res.ok || !data.success) {
            localStorage.removeItem('access_code');
            accessCode = null;
            showLoginModal();
            showErrorMessage(data.error || '登入狀態已失效，請重新登入');
            return;
        }

        document.getElementById('login-error').style.display = 'none';
        document.getElementById('login-modal').style.display = 'none';

        if (data.needs_profile) {
            document.getElementById('auth-overlay').style.display = 'flex';
            document.getElementById('profile-modal').style.display = 'block';
            document.getElementById('close-profile-btn').style.display = 'none';
            return;
        }

        document.getElementById('auth-overlay').style.display = 'none';
        await loadSessions(true);
    } catch (e) {
        console.error('恢復登入狀態失敗:', e);
        showLoginModal();
        showErrorMessage('無法恢復登入狀態，請檢查網路連線');
    }
}

// 初始化驗證
window.onload = async () => {
    if (!accessCode) {
        showLoginModal();
    } else {
        await restoreFromLocalAccessCode();
    }
};

async function login() {
    const code = document.getElementById('access-code-input').value.trim();
    if (!code) {
        showErrorMessage('請輸入存取代碼');
        return;
    }

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });

        const data = await res.json();
        if (res.ok && data.success) {
            accessCode = code;
            localStorage.setItem('access_code', code);
            document.getElementById('login-error').style.display = 'none';
            document.getElementById('login-modal').style.display = 'none';

            if (data.needs_profile) {
                document.getElementById('profile-modal').style.display = 'block';
                document.getElementById('close-profile-btn').style.display = 'none';
            } else {
                document.getElementById('auth-overlay').style.display = 'none';
                loadSessions(true);
            }
        } else {
            showErrorMessage(data.error || '驗證失敗，請檢查存取代碼');
            document.getElementById('login-error').style.display = 'block';
            document.getElementById('login-error').textContent = data.error || '驗證失敗';
        }
    } catch (e) {
        console.error('登入錯誤:', e);
        showErrorMessage('連線失敗，請檢查網路連接');
    }
}

async function saveProfile() {
    const name = document.getElementById('profile-name').value.trim();
    const level = document.getElementById('profile-level').value.trim();
    const starPref = document.getElementById('profile-star').value;
    const style = document.getElementById('profile-style').value;

    if (!name) {
        showErrorMessage('請填寫玩家名稱！');
        return;
    }
    if (!level) {
        showErrorMessage('請填寫最高段位！');
        return;
    }

    try {
        const res = await fetch('/api/profile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessCode}`
            },
            body: JSON.stringify({ code: accessCode, name, level, star_pref: starPref, style })
        });

        if (res.ok) {
            document.getElementById('auth-overlay').style.display = 'none';
            document.getElementById('profile-modal').style.display = 'none';
            showSuccessMessage('您的玩家履歷已設定 / 更新成功！');
            loadSessions();
        } else {
            const data = await res.json();
            showErrorMessage(data.error || '儲存失敗');
        }
    } catch (e) {
        console.error('儲存失敗:', e);
        showErrorMessage('儲存失敗，請檢查網路連接');
    }
}

async function loadSessions(autoLoadLatest = false) {
    try {
        const res = await fetch('/api/sessions', {
            headers: {
                'Authorization': `Bearer ${accessCode}`
            }
        });
        if (res.ok) {
            const data = await res.json();
            currentSessions = data.sessions || [];
            renderSessions();

            if (autoLoadLatest && currentSessions.length > 0) {
                const latestSession = currentSessions[currentSessions.length - 1];
                loadChat(latestSession);
            }
        } else {
            console.error("無法載入歷史紀錄");
        }
    } catch (e) {
        console.error("無法載入歷史紀錄:", e);
    }
}

function renderSessions() {
    const list = document.getElementById('sessions-list');
    list.innerHTML = '';

    currentSessions.forEach(session => {
        const item = document.createElement('div');
        item.className = 'session-item';
        item.onclick = () => loadChat(session);

        const title = document.createElement('div');
        title.className = 'session-item-title';
        title.textContent = session.title;

        const delBtn = document.createElement('button');
        delBtn.className = 'delete-session-btn';
        delBtn.innerHTML = '🗑️';
        delBtn.onclick = (e) => {
            e.stopPropagation();
            deleteSession(session.id);
        };

        item.appendChild(title);
        item.appendChild(delBtn);
        list.appendChild(item);
    });
}

function startNewChat() {
    chatContext = [];
    chatHistory.innerHTML = `
        <div class="message-wrapper bot-message">
            <div class="message-bubble">
                你好！我是你的專屬「太鼓之達人」遊玩顧問，有什麼我可以幫忙推薦的嗎？（已開啟新對話）
            </div>
        </div>
    `;
}

function loadChat(session) {
    chatContext = session.messages || [];
    chatHistory.innerHTML = '';
    chatContext.forEach(msg => {
        appendMessage(msg.role, msg.content, false);
    });
}

async function deleteSession(id) {
    if (!confirm('確定要刪除這筆紀錄嗎？')) return;
    try {
        const res = await fetch(`/api/sessions/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${accessCode}`
            }
        });
        if (res.ok) {
            loadSessions();
        } else {
            const data = await res.json();
            showErrorMessage(data.error || '刪除失敗');
        }
    } catch (e) {
        console.error('刪除錯誤:', e);
        showErrorMessage('刪除失敗，請檢查網路連接');
    }
}

async function saveCurrentSession() {
    if (chatContext.length < 2) {
        showErrorMessage('對話內容太空，不需要儲存喔！');
        return;
    }
    if (currentSessions.length >= 3) {
        showErrorMessage('儲存空間已滿 (最多3筆)，請先刪除舊的對話。');
        return;
    }

    // 取第一句使用者的話當標題
    let title = "未命名對話";
    const firstUserMsg = chatContext.find(m => m.role === 'user');
    if (firstUserMsg) {
        title = firstUserMsg.content.substring(0, 15) + "...";
    }

    try {
        const res = await fetch('/api/sessions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessCode}`
            },
            body: JSON.stringify({ code: accessCode, title, messages: chatContext })
        });

        if (res.ok) {
            showSuccessMessage('對話已儲存！');
            loadSessions();
        } else {
            const err = await res.json();
            showErrorMessage(err.error || '儲存失敗');
        }
    } catch (e) {
        console.error('儲存錯誤:', e);
        showErrorMessage('連線異常，請稍後再試');
    }
}

// 當使用者點擊左側推薦按鈕時，自動帶入輸入框
function setInputValue(text) {
    chatInput.value = text;
    chatInput.focus();
}

// 監聽 Enter 送出
function handleEnter(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// 將對話泡泡加入畫面
function appendMessage(sender, text, saveToContext = true) {
    if (saveToContext) {
        chatContext.push({ role: sender, content: text });
    }

    const wrapper = document.createElement('div');
    wrapper.classList.add('message-wrapper', sender === 'user' ? 'user-message' : 'bot-message');

    const bubble = document.createElement('div');
    bubble.classList.add('message-bubble');

    // 解析 markdown 或是純文字
    if (sender === 'bot' || sender === 'model') {
        // 使用 DOMPurify 清理 HTML 防止 XSS 攻擊
        bubble.innerHTML = DOMPurify.sanitize(marked.parse(text));
    } else {
        bubble.textContent = text;
    }

    wrapper.appendChild(bubble);
    chatHistory.appendChild(wrapper);

    // 捲動到底部
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// 傳送訊息給 FastAPI 後端
async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    chatInput.value = '';
    chatInput.disabled = true;
    sendBtn.disabled = true;

    // 傳送出的歷史紀錄不應該包含「當下正在送出的這句話」
    const historyToSend = [...chatContext];

    // 顯示使用者的訊息並存入上下文
    appendMessage('user', message);

    // 顯示打字動畫
    typingIndicator.style.display = 'flex';
    chatHistory.scrollTop = chatHistory.scrollHeight;

    try {
        statusIndicator.style.backgroundColor = '#ff9e64'; // 黃色 Loading 狀態
        statusIndicator.style.boxShadow = '0 0 10px #ff9e64';

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message, code: accessCode, history: historyToSend })
        });

        typingIndicator.style.display = 'none';

        if (response.status === 401) {
            appendMessage('bot', '❌ 您的存取代碼已失效，請重新登入。');
            localStorage.removeItem('access_code');
        } else if (!response.ok) {
            appendMessage('bot', '❌ 伺服器發生錯誤，請稍後再試。');
        } else {
            // 建立一個空的泡泡來接收串流
            const wrapper = document.createElement('div');
            wrapper.classList.add('message-wrapper', 'bot-message');
            const bubble = document.createElement('div');
            bubble.classList.add('message-bubble');
            wrapper.appendChild(bubble);
            chatHistory.appendChild(wrapper);

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let fullText = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                fullText += chunk;
                bubble.innerHTML = DOMPurify.sanitize(marked.parse(fullText));
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }

            // 儲存進上下文
            chatContext.push({ role: 'model', content: fullText });
        }

        statusIndicator.style.backgroundColor = '#9ece6a'; // 綠色正常狀態
        statusIndicator.style.boxShadow = '0 0 10px #9ece6a';

    } catch (err) {
        typingIndicator.style.display = 'none';
        console.error('聊天錯誤:', err);
        appendMessage('bot', '❌ 連線異常，請檢查你的網路或伺服器狀態。');
        statusIndicator.style.backgroundColor = '#f7768e'; // 紅色錯誤狀態
        statusIndicator.style.boxShadow = '0 0 10px #f7768e';
    }

    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatInput.focus();
}

function logout() {
    if (!confirm('確定要登出並刪除嗎？')) return;
    
    try {
        // 調用後端 logout 端點使令牌失效
        fetch("/api/logout", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ code: accessCode }),
		}).catch((e) => console.error("登出並刪除請求失敗:", e));
    } catch (e) {
        console.error("登出並刪除錯誤:", e);
    }
    
    // 清除本地存儲
    localStorage.removeItem('access_code');
    location.reload();
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    sidebar.classList.toggle('collapsed');

    if (overlay) {
        if (sidebar.classList.contains('collapsed')) {
            overlay.classList.remove('active');
        } else {
            overlay.classList.add('active');
        }
    }
}

// 頁面載入時若螢幕寬度小於 768px，預設將選單收起
window.addEventListener('DOMContentLoaded', () => {
    if (window.innerWidth <= 768) {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        if (sidebar && !sidebar.classList.contains('collapsed')) {
            sidebar.classList.add('collapsed');
        }
        if (overlay) {
            overlay.classList.remove('active');
        }
    }
});

async function openProfileModal() {
    try {
        const res = await fetch('/api/profile', {
            headers: {
                'Authorization': `Bearer ${accessCode}`
            }
        });
        if (res.ok) {
            const data = await res.json();
            const p = data.profile || {};
            document.getElementById('profile-name').value = p.name || '';
            document.getElementById('profile-level').value = p.level || '';
            if (p.star_pref) document.getElementById('profile-star').value = p.star_pref;
            if (p.style) document.getElementById('profile-style').value = p.style;
        } else {
            const data = await res.json();
            showErrorMessage(data.error || '無法載入履歷');
        }
    } catch (e) {
        console.error("無法載入履歷", e);
        showErrorMessage('無法載入履歷，請檢查網路連接');
    }
    document.getElementById('auth-overlay').style.display = 'flex';
    document.getElementById('login-modal').style.display = 'none';
    document.getElementById('profile-modal').style.display = 'block';
    document.getElementById('close-profile-btn').style.display = 'block'; // 允許取消
}

function closeProfileModal() {
    document.getElementById('auth-overlay').style.display = 'none';
    document.getElementById('profile-modal').style.display = 'none';
}
