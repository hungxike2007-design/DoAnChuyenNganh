/**
 * ==============================================================================
 * LOGIC TỐI ƯU CHIẾN LƯỢC BÁN HÀNG TÍCH HỢP GEMINI AI (STRATEGY JS)
 * ==============================================================================
 */

let currentBaseline = {
  baselineRevenue: 0,
  baselineAov: 0,
  baselineOrders: 0,
  channels: []
};

document.addEventListener('DOMContentLoaded', async () => {
  if (!checkPageRole(['admin', 'manager'])) return;

  loadStrategyHistory();
  await initGoalPlanner();

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

/* ==============================================================================
   PHÂN HỆ LẬP KẾ HOẠCH PHÂN BỔ MỤC TIÊU DOANH THU (GOAL PLANNER)
   ============================================================================== */
async function initGoalPlanner() {
  const baselineRevEl = document.getElementById('plan-baseline-rev');
  const baselineAovEl = document.getElementById('plan-baseline-aov');
  const targetInput = document.getElementById('target-revenue-input');
  const periodSelect = document.getElementById('target-period-select');
  const btnRunPlan = document.getElementById('btn-run-goal-plan');
  const presetButtons = document.querySelectorAll('.btn-preset');

  try {
    const res = await apiRequest('/api/ai/planning-baseline?days=30');
    if (res.success && res.data) {
      currentBaseline = res.data;
      const bRev = currentBaseline.baselineRevenue || 0;
      const bAov = currentBaseline.baselineAov || 0;

      if (baselineRevEl) baselineRevEl.textContent = formatVND(bRev);
      if (baselineAovEl) baselineAovEl.textContent = formatVND(bAov);

      // Mặc định đề xuất mức +20% tăng trưởng làm tròn đẹp
      const defaultGrowth = 20;
      const defaultTarget = bRev > 0 
        ? Math.round((bRev * 1.2) / 1000000) * 1000000 
        : 250000000;
      
      if (targetInput) {
        targetInput.value = formatNumberDisplay(defaultTarget);
      }
    }
  } catch (err) {
    console.warn('Không thể tải baseline doanh thu:', err);
    if (baselineRevEl) baselineRevEl.textContent = '180.000.000 ₫ (Mẫu)';
    if (baselineAovEl) baselineAovEl.textContent = '350.000 ₫ (Mẫu)';
    if (targetInput) targetInput.value = '220.000.000';
  }

  // Bắt sự kiện chọn nút Preset tăng trưởng (+10%, +20%, +30%, +50%)
  presetButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      presetButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const growthPct = parseFloat(btn.dataset.growth) || 20;
      const base = currentBaseline.baselineRevenue > 0 ? currentBaseline.baselineRevenue : 180000000;
      const calculated = Math.round((base * (1 + growthPct / 100)) / 500000) * 500000;

      if (targetInput) {
        targetInput.value = formatNumberDisplay(calculated);
      }
    });
  });

  // Tự động định dạng dấu chấm phân cách hàng nghìn khi người dùng gõ
  if (targetInput) {
    targetInput.addEventListener('input', (e) => {
      const raw = e.target.value.replace(/\D/g, '');
      if (!raw) {
        e.target.value = '';
        return;
      }
      e.target.value = formatNumberDisplay(parseInt(raw, 10));
      // Bỏ active của các preset nếu người dùng nhập số tùy ý
      presetButtons.forEach(b => b.classList.remove('active'));
    });
  }

  // Nút chạy Gemini AI phân rã mục tiêu
  if (btnRunPlan) {
    btnRunPlan.addEventListener('click', async () => {
      await executeRevenuePlan();
    });
  }
}

async function executeRevenuePlan() {
  const targetInput = document.getElementById('target-revenue-input');
  const periodSelect = document.getElementById('target-period-select');
  const loadingEl = document.getElementById('ai-loading');
  const resultContainer = document.getElementById('plan-result-container');
  const resultBox = document.getElementById('ai-result-box');

  const rawTarget = targetInput.value.replace(/\D/g, '');
  const targetRevenue = parseFloat(rawTarget);
  const days = parseInt(periodSelect.value, 10) || 30;

  if (!targetRevenue || targetRevenue <= 0) {
    showToast('Vui lòng nhập mục tiêu doanh thu hợp lệ (> 0 VNĐ)', 'error');
    return;
  }

  try {
    if (resultBox) resultBox.style.display = 'none';
    if (resultContainer) resultContainer.style.display = 'none';

    // Đổi thông điệp loading chuyên nghiệp
    const loadingTitle = loadingEl.querySelector('h3');
    const loadingDesc = loadingEl.querySelector('p');
    if (loadingTitle) loadingTitle.textContent = 'Gemini AI Đang Phân Rã Mục Tiêu Doanh Thu...';
    if (loadingDesc) loadingDesc.textContent = 'Đang tính toán hạn mức cho 4 kênh bán lẻ, giỏ hàng AOV và lập lộ trình 4 tuần.';
    loadingEl.style.display = 'block';

    const res = await apiRequest('/api/ai/revenue-plan', {
      method: 'POST',
      body: JSON.stringify({
        target_revenue: targetRevenue,
        days: days
      })
    });

    loadingEl.style.display = 'none';

    if (res.success && res.data) {
      renderGoalPlanResults(res.data);
      if (resultContainer) {
        resultContainer.style.display = 'block';
        resultContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      showToast('Đã lập kế hoạch phân bổ mục tiêu doanh thu thành công!', 'success');
      loadStrategyHistory();
    }
  } catch (err) {
    loadingEl.style.display = 'none';
    showToast('Lỗi lập kế hoạch AI: ' + err.message, 'error');
  }
}

function renderGoalPlanResults(plan) {
  // 1. Tiêu đề và Growth Pill
  const headline = document.getElementById('plan-result-headline');
  const growthBadge = document.getElementById('plan-growth-badge');
  if (headline) headline.textContent = `Kế Hoạch Doanh Thu: ${formatVND(plan.targetRevenue)}`;
  if (growthBadge) {
    growthBadge.textContent = `${plan.growthRate >= 0 ? '+' : ''}${plan.growthRate}% TĂNG TRƯỞNG`;
    growthBadge.style.background = plan.growthRate >= 0 
      ? 'linear-gradient(135deg, #10b981, #059669)' 
      : 'linear-gradient(135deg, #f59e0b, #d97706)';
  }

  // 2. 4 Thẻ KPI định lượng
  const kpiRev = document.getElementById('plan-kpi-revenue');
  const kpiGrowth = document.getElementById('plan-kpi-growth');
  const kpiOrders = document.getElementById('plan-kpi-orders');
  const kpiAov = document.getElementById('plan-kpi-aov');
  const kpiDaily = document.getElementById('plan-kpi-daily');

  if (kpiRev) kpiRev.textContent = formatVND(plan.targetRevenue);
  if (kpiGrowth) kpiGrowth.textContent = `So với cơ sở: ${formatVND(plan.baselineRevenue)} (${plan.growthRate >= 0 ? '+' : ''}${plan.growthRate}%)`;
  if (kpiOrders) kpiOrders.textContent = `${plan.requiredOrders.toLocaleString('vi-VN')} đơn`;
  if (kpiAov) kpiAov.textContent = formatVND(plan.targetAov);
  if (kpiDaily) kpiDaily.textContent = formatVND(plan.dailyTarget);

  // 3. Phân bổ Quota 4 Kênh bán lẻ
  renderChannelQuotaCards(plan.channelQuotas || []);

  // 4. Lộ trình 4 tuần & Nhận xét chiến lược từ Gemini AI
  const markdownEl = document.getElementById('plan-ai-markdown');
  if (markdownEl) {
    markdownEl.innerHTML = renderMarkdown(plan.content);
  }
}

function renderChannelQuotaCards(channels) {
  const container = document.getElementById('plan-channel-cards');
  if (!container) return;

  const channelMeta = {
    'Shopee': { icon: 'fa-solid fa-bag-shopping', color: '#f97316', bg: 'rgba(249, 115, 22, 0.15)' },
    'TikTok Shop': { icon: 'fa-brands fa-tiktok', color: '#ec4899', bg: 'rgba(236, 72, 153, 0.15)' },
    'Cửa hàng trực tiếp': { icon: 'fa-solid fa-store', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)' },
    'Website': { icon: 'fa-solid fa-globe', color: '#6366f1', bg: 'rgba(99, 102, 241, 0.15)' }
  };

  container.innerHTML = channels.map(ch => {
    const meta = channelMeta[ch.channel] || { icon: 'fa-solid fa-network-wired', color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.15)' };
    const pct = ch.sharePercent || 0;

    return `
      <div class="channel-quota-card" style="border-top: 3px solid ${meta.color};">
        <div class="channel-top-row">
          <div class="channel-name">
            <i class="${meta.icon}" style="color:${meta.color};"></i>
            <span>${ch.channel}</span>
          </div>
          <span class="channel-share-badge" style="color:${meta.color}; background:${meta.bg};">
            ${pct}% Quota
          </span>
        </div>
        <div class="channel-numbers">
          <div>
            <div style="font-size:11px; color:var(--text-muted); margin-bottom:2px;">Mục tiêu doanh thu:</div>
            <div class="channel-target-rev">${formatVND(ch.targetRevenue)}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px; color:var(--text-muted); margin-bottom:2px;">Chỉ tiêu đơn hàng:</div>
            <div style="font-size:14px; font-weight:700; color:#34d399; font-family:var(--font-mono);">${ch.targetOrders} đơn</div>
          </div>
        </div>
        <div class="quota-progress-bar">
          <div class="quota-fill" style="width: ${Math.min(pct, 100)}%; background: ${meta.color};"></div>
        </div>
      </div>
    `;
  }).join('');
}

function formatNumberDisplay(num) {
  if (isNaN(num) || num === null) return '0';
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

/* ==============================================================================
   CHIẾN LƯỢC TỔNG THỂ & LỊCH SỬ BÁO CÁO
   ============================================================================== */
async function generateStrategy(endpoint, title) {
  const loadingEl = document.getElementById('ai-loading');
  const resultBox = document.getElementById('ai-result-box');
  const resultTitle = document.getElementById('ai-result-title');
  const resultContent = document.getElementById('ai-result-content');
  const modelBadge = document.getElementById('ai-model-badge');
  const planContainer = document.getElementById('plan-result-container');

  try {
    if (planContainer) planContainer.style.display = 'none';
    resultBox.style.display = 'none';

    const loadingTitle = loadingEl.querySelector('h3');
    const loadingDesc = loadingEl.querySelector('p');
    if (loadingTitle) loadingTitle.textContent = 'Gemini AI Đang Phân Tích Dữ Liệu SQL...';
    if (loadingDesc) loadingDesc.textContent = 'Đang tính toán ma trận tương quan doanh số, chu kỳ tồn kho và xây dựng kịch bản tối ưu.';
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
      resultBox.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    const res = await apiRequest('/api/ai/history?limit=6');
    if (res.success && res.data) {
      if (res.data.length === 0) {
        historyList.innerHTML = '<p style="color:var(--text-muted); font-size:13px;">Chưa có báo cáo nào được lưu.</p>';
        return;
      }

      historyList.innerHTML = res.data.map(item => `
        <div class="history-item-card" onclick="viewHistoryItem(${item.id})">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div class="history-item-title">
              <i class="fa-solid ${item.strategy_type === 'goal_plan' ? 'fa-bullseye' : item.strategy_type === 'pricing' ? 'fa-tags' : 'fa-file-invoice-dollar'}" style="color:var(--accent-primary);"></i>
              <span>${item.title}</span>
            </div>
            <span class="history-item-date">${item.created_at || ''}</span>
          </div>
          <div class="history-item-desc" style="display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">
            ${(item.ai_response || '').replace(/[#*`]/g, '')}
          </div>
        </div>
      `).join('');
    }
  } catch (e) {
    console.error('Lỗi tải lịch sử:', e);
  }
}

async function viewHistoryItem(id) {
  try {
    const res = await apiRequest('/api/ai/history?limit=20');
    if (res.success && res.data) {
      const item = res.data.find(x => x.id === id);
      if (!item) return;

      const resultBox = document.getElementById('ai-result-box');
      const resultTitle = document.getElementById('ai-result-title');
      const resultContent = document.getElementById('ai-result-content');
      const planContainer = document.getElementById('plan-result-container');

      if (planContainer) planContainer.style.display = 'none';
      resultTitle.innerHTML = `<i class="fa-solid ${item.strategy_type === 'goal_plan' ? 'fa-bullseye text-cyan' : item.strategy_type === 'pricing' ? 'fa-tags text-purple' : 'fa-file-invoice-dollar text-emerald'}"></i> ${item.title}`;
      resultContent.innerHTML = renderMarkdown(item.ai_response);
      resultBox.style.display = 'block';
      resultBox.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  } catch (e) {
    console.error('Lỗi xem lại báo cáo:', e);
  }
}


// Chuyển đổi Markdown cơ bản sang HTML đẹp mắt
function renderMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/^#### (.*$)/gim, '<h4>$1</h4>')
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/#{1,6}\s*/g, '')
    .replace(/^---\s*$/gm, '<hr style="border:none; border-top:1px solid rgba(148,163,184,0.15); margin:18px 0;">')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/^\> (.*$)/gim, '<blockquote style="border-left:3px solid var(--accent-cyan); padding-left:12px; margin:10px 0; color:#cbd5e1;">$1</blockquote>')
    .replace(/^- (.*$)/gim, '<li style="margin-bottom:4px; margin-left:18px;">$1</li>')
    .replace(/\n\n/gim, '<br><br>')
    .replace(/\n/gim, '<br>');
}

