/**
 * ==============================================================================
 * LOGIC TỐI ƯU CHIẾN LƯỢC BÁN HÀNG TÍCH HỢP GEMINI AI (STRATEGY JS)
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;

  loadStrategyHistory();

  const btnSummary = document.getElementById('btn-ai-summary');
  const btnPricing = document.getElementById('btn-ai-pricing');

  if (btnSummary) {
    btnSummary.addEventListener('click', async () => {
      await generateStrategy('/api/ai/executive-summary', 'Bản Tóm Tắt & Phân Tích Hiệu Suất Kinh Doanh');
    });
  }

  if (btnPricing) {
    btnPricing.addEventListener('click', async () => {
      await generateStrategy('/api/ai/strategy', 'Chiến Lược Giá Động (Dynamic Pricing) & Combo Xả Hàng');
    });
  }
});

async function generateStrategy(endpoint, title) {
  const loadingEl = document.getElementById('ai-loading');
  const resultBox = document.getElementById('ai-result-box');
  const resultTitle = document.getElementById('ai-result-title');
  const resultContent = document.getElementById('ai-result-content');
  const modelBadge = document.getElementById('ai-model-badge');

  try {
    resultBox.style.display = 'none';
    loadingEl.style.display = 'block';

    const res = await apiRequest(endpoint, { method: 'POST' });

    if (res.success && res.data) {
      resultTitle.textContent = title;
      resultContent.innerHTML = renderMarkdown(res.data.content);
      
      if (modelBadge) {
        modelBadge.textContent = res.data.isLiveAI 
          ? `Google Gemini (${res.data.model})` 
          : 'Chế độ Demo (Chưa gán key)';
        modelBadge.className = res.data.isLiveAI ? 'badge-tag badge-success' : 'badge-tag badge-warning';
      }

      loadingEl.style.display = 'none';
      resultBox.style.display = 'block';
      showToast('Gemini AI đã hoàn thành phân tích!', 'success');
      loadStrategyHistory();
    }
  } catch (err) {
    loadingEl.style.display = 'none';
    showToast('Lỗi khi phân tích AI: ' + err.message, 'error');
  }
}

async function loadStrategyHistory() {
  const historyList = document.getElementById('strategy-history-list');
  if (!historyList) return;

  try {
    const res = await apiRequest('/api/ai/history?limit=5');
    if (res.success && res.data) {
      if (res.data.length === 0) {
        historyList.innerHTML = '<p style="color:var(--text-muted); font-size:13px;">Chưa có báo cáo nào được lưu.</p>';
        return;
      }

      historyList.innerHTML = res.data.map(item => `
        <div class="glass-card" style="padding:16px; margin-bottom:12px; cursor:pointer;" onclick="viewHistoryItem(${item.id})">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <strong style="font-size:14px; color:#fff;">${item.title}</strong>
            <small style="color:var(--text-muted); font-size:11px;">${item.created_at}</small>
          </div>
          <div style="font-size:12px; color:var(--text-secondary); display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">
            ${item.ai_response.replace(/[#*`]/g, '')}
          </div>
        </div>
      `).join('');
    }
  } catch (e) {
    console.error('Lỗi tải lịch sử:', e);
  }
}

// Chuyển đổi Markdown cơ bản sang HTML đẹp mắt
function renderMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
    .replace(/^- (.*$)/gim, '<li>$1</li>')
    .replace(/\n\n/gim, '<br><br>')
    .replace(/\n/gim, '<br>');
}
