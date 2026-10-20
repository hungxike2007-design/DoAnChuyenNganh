/**
 * ==============================================================================
 * LOGIC KHUNG CHAT TRỢ LÝ AI COPILOT (COPILOT CHAT JS)
 * ==============================================================================
 */

const chatHistory = [];

document.addEventListener('DOMContentLoaded', () => {
  if (!requireAuth()) return;

  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('btn-send-message');
  const suggestionPills = document.querySelectorAll('.suggestion-pill');

  if (sendBtn && chatInput) {
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        sendMessage();
      }
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
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}
