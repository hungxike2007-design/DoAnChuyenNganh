/**
 * ==============================================================================
 * LOGIC KHUNG CHAT TRỢ LÝ AI COPILOT (COPILOT CHAT JS)
 * ==============================================================================
 */

let chatHistory = [];

function getStorageKey() {
  const user = getUser();
  const id = user ? (user.id || user.sub || user.email) : 'default';
  return `dacn_chat_history_${id}`;
}

function saveChatLocally() {
  try {
    localStorage.setItem(getStorageKey(), JSON.stringify(chatHistory));
  } catch (e) {
    console.warn('Không thể lưu localStorage:', e);
  }
}

function renderAllHistory(messages) {
  const messagesArea = document.getElementById('chat-messages');
  if (!messagesArea) return;

  const defaultGreeting = `
    <div class="chat-bubble assistant">
      <div class="chat-avatar"><i class="fa-solid fa-brain"></i></div>
      <div class="chat-content">
        Xin chào! Tôi là <strong>AI Business Copilot</strong> được kết nối trực tiếp với cơ sở dữ liệu bán hàng của bạn. 
        Bạn có thể hỏi tôi bất cứ điều gì về doanh thu, kênh bán, hàng tồn kho hoặc nhờ tôi gợi ý chiến lược tăng trưởng!
      </div>
    </div>
  `;
  messagesArea.innerHTML = defaultGreeting;

  chatHistory = [];
  if (Array.isArray(messages)) {
    messages.forEach(item => {
      appendMessage(item.sender, item.message);
      chatHistory.push({ sender: item.sender, message: item.message });
    });
  }
  messagesArea.scrollTop = messagesArea.scrollHeight;
}

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;

  // 1. Phục hồi ngay lịch sử từ LocalStorage để không bị trễ khi chuyển tab
  try {
    const cached = localStorage.getItem(getStorageKey());
    if (cached) {
      const parsed = JSON.parse(cached);
      if (Array.isArray(parsed) && parsed.length > 0) {
        renderAllHistory(parsed);
      }
    }
  } catch (e) {
    console.warn('Lỗi đọc cache chat:', e);
  }

  // 2. Đồng bộ dữ liệu lịch sử chuẩn xác từ CSDL SQL Server theo tài khoản
  try {
    const res = await apiRequest('/api/ai/copilot/history');
    if (res.success && Array.isArray(res.data) && res.data.length > 0) {
      renderAllHistory(res.data);
      saveChatLocally();
    }
  } catch (e) {
    console.warn('Chưa nạp được lịch sử từ máy chủ:', e);
  }

  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('btn-send-message');
  const clearBtn = document.getElementById('btn-clear-chat');
  const suggestionPills = document.querySelectorAll('.suggestion-pill');

  if (sendBtn && chatInput) {
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        sendMessage();
      }
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', async () => {
      if (!confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử trò chuyện của tài khoản này không?')) return;
      chatHistory = [];
      localStorage.removeItem(getStorageKey());
      renderAllHistory([]);
      try {
        await apiRequest('/api/ai/copilot/history', { method: 'DELETE' });
      } catch (err) {
        console.warn('Lỗi xóa trên server:', err);
      }
      showToast('Đã xóa sạch lịch sử trò chuyện!', 'info');
    });
  }

  suggestionPills.forEach(pill => {
    pill.addEventListener('click', () => {
      if (chatInput) {
        chatInput.value = pill.textContent.trim();
        sendMessage();
      }
    });
  });

  // Tự động nhận câu hỏi từ tham số URL ?q=
  const urlParams = new URLSearchParams(window.location.search);
  const initialQ = urlParams.get('q');
  if (initialQ && chatInput) {
    chatInput.value = initialQ;
    setTimeout(() => {
      sendMessage();
    }, 350);
  }
});

async function sendMessage() {
  const chatInput = document.getElementById('chat-input');
  const messagesArea = document.getElementById('chat-messages');
  const query = chatInput.value.trim();

  if (!query) return;

  // 1. Thêm tin nhắn của User
  appendMessage('user', query);
  chatInput.value = '';

  // 2. Thêm bong bóng loading của AI
  const loadingBubble = appendLoadingBubble();
  messagesArea.scrollTop = messagesArea.scrollHeight;

  try {
    const res = await apiRequest('/api/ai/copilot', {
      method: 'POST',
      body: JSON.stringify({
        message: query,
        history: chatHistory
      })
    });

    loadingBubble.remove();

    if (res.success && res.data) {
      appendMessage('assistant', res.data.reply);
      chatHistory.push({ sender: 'user', message: query });
      chatHistory.push({ sender: 'assistant', message: res.data.reply });
      saveChatLocally();
    }
  } catch (err) {
    loadingBubble.remove();
    appendMessage('assistant', '⚠️ Xin lỗi, đã xảy ra lỗi khi kết nối với AI: ' + err.message);
  }

  messagesArea.scrollTop = messagesArea.scrollHeight;
}

function appendMessage(sender, text) {
  const messagesArea = document.getElementById('chat-messages');
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${sender}`;

  const avatar = sender === 'user' ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-brain"></i>';

  bubble.innerHTML = `
    <div class="chat-avatar">${avatar}</div>
    <div class="chat-content">${formatChatContent(text)}</div>
  `;

  messagesArea.appendChild(bubble);
  messagesArea.scrollTop = messagesArea.scrollHeight;
  return bubble;
}

function appendLoadingBubble() {
  const messagesArea = document.getElementById('chat-messages');
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble assistant';
  bubble.innerHTML = `
    <div class="chat-avatar"><i class="fa-solid fa-brain"></i></div>
    <div class="chat-content" style="display:flex; align-items:center; gap:8px;">
      <i class="fa-solid fa-spinner fa-spin"></i>
      <span>Gemini AI đang tra cứu dữ liệu & suy luận...</span>
    </div>
  `;
  messagesArea.appendChild(bubble);
  return bubble;
}

function formatChatContent(text) {
  if (!text) return '';
  return text
    .replace(/#{1,6}\s*/g, '')
    .replace(/^---\s*$/gm, '')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}
