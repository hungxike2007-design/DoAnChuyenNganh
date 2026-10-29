/**
 * ==============================================================================
 * LOGIC GIAO DIỆN PHÂN HỆ LẬP KẾ HOẠCH DOANH THU (PLANNER JS)
 * Tách riêng file JS để đảm bảo tính module hóa và dễ bảo trì
 * ==============================================================================
 */

let plannerBaseline = {
  baselineRevenue: 0,
  baselineAov: 0,
  baselineOrders: 0,
  channels: []
};

document.addEventListener('DOMContentLoaded', async () => {
  if (!checkPageRole(['admin', 'manager', 'sales', 'user'])) return;

  await loadBaselineData();
  setupPresetChips();
  setupInputFormatting();
  setupRunButton();
  loadPlanHistory();
});

/**
 * 1. Nạp số liệu năng lực cơ sở thực tế từ Backend SQL
 */
async function loadBaselineData() {
  const revEl = document.getElementById('stat-baseline-rev');
  const aovEl = document.getElementById('stat-baseline-aov');
  const ordersEl = document.getElementById('stat-baseline-orders');
  const targetInput = document.getElementById('target-revenue-input');

  try {
    const res = await apiRequest('/api/planner/baseline?days=30');
    if (res.success && res.data) {
      plannerBaseline = res.data;
      const bRev = plannerBaseline.baselineRevenue || 0;
      const bAov = plannerBaseline.baselineAov || 0;
      const bOrders = plannerBaseline.baselineOrders || 0;

      if (revEl) revEl.textContent = formatVND(bRev);
      if (aovEl) aovEl.textContent = formatVND(bAov);
      if (ordersEl) ordersEl.textContent = `${bOrders} đơn`;

      // Mặc định gợi ý mức tăng trưởng +20% làm tròn đẹp theo triệu đồng
      const defaultTarget = bRev > 0 
        ? Math.round((bRev * 1.2) / 1000000) * 1000000 
        : 250000000;

      if (targetInput) {
        targetInput.value = formatNumber(defaultTarget);
      }
    }
  } catch (err) {
    console.warn('Không thể tải baseline doanh thu:', err);
    if (revEl) revEl.textContent = '25.000.000 ₫ (Dự phòng)';
    if (aovEl) aovEl.textContent = '1.350.000 ₫ (Dự phòng)';
    if (targetInput) targetInput.value = '30.000.000';
  }
}

/**
 * 2. Bắt sự kiện chọn các nút Preset tăng trưởng (+10%, +20%, +30%, +50%)
 */
function setupPresetChips() {
  const chips = document.querySelectorAll('.growth-chip');
  const targetInput = document.getElementById('target-revenue-input');

  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');

      const pct = parseFloat(chip.dataset.growth) || 20;
      const base = plannerBaseline.baselineRevenue > 0 ? plannerBaseline.baselineRevenue : 25000000;
      const target = Math.round((base * (1 + pct / 100)) / 500000) * 500000;

      if (targetInput) {
        targetInput.value = formatNumber(target);
      }
    });
  });
}

/**
 * 3. Tự động định dạng dấu chấm phân cách hàng nghìn khi người dùng gõ
 */
function setupInputFormatting() {
  const targetInput = document.getElementById('target-revenue-input');
  const chips = document.querySelectorAll('.growth-chip');

  if (!targetInput) return;

  targetInput.addEventListener('input', (e) => {
    const rawDigits = e.target.value.replace(/\D/g, '');
    if (!rawDigits) {
      e.target.value = '';
      return;
    }
    e.target.value = formatNumber(parseInt(rawDigits, 10));
    // Hủy trạng thái active của preset nếu người dùng nhập số tùy biến
    chips.forEach(c => c.classList.remove('active'));
  });
}

/**
 * 4. Bắt sự kiện nút bấm thực thi phân rã mục tiêu bằng Gemini AI
 */
function setupRunButton() {
  const btnRun = document.getElementById('btn-run-planner');
  if (!btnRun) return;

  btnRun.addEventListener('click', async () => {
    await executeGoalPlanning();
  });
}

async function executeGoalPlanning() {
  const targetInput = document.getElementById('target-revenue-input');
  const periodSelect = document.getElementById('target-period-select');
  const loadingEl = document.getElementById('planner-loading');
  const resultsWrapper = document.getElementById('plan-results-wrapper');

  const rawDigits = targetInput.value.replace(/\D/g, '');
  const targetRevenue = parseFloat(rawDigits);
  const days = parseInt(periodSelect.value, 10) || 30;

  if (!targetRevenue || targetRevenue <= 0) {
    showToast('Vui lòng nhập mục tiêu doanh thu hợp lệ (> 0 VNĐ)', 'error');
    return;
  }

  try {
    if (resultsWrapper) resultsWrapper.style.display = 'none';
    if (loadingEl) loadingEl.style.display = 'block';

    const res = await apiRequest('/api/planner/generate', {
      method: 'POST',
      body: JSON.stringify({
        target_revenue: targetRevenue,
        days: days
      })
    });

    if (loadingEl) loadingEl.style.display = 'none';

    if (res.success && res.data) {
      renderPlannerResults(res.data);
      if (resultsWrapper) {
        resultsWrapper.style.display = 'block';
        resultsWrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      showToast('Gemini AI đã hoàn tất phân rã mục tiêu và lập lộ trình!', 'success');
      loadPlanHistory();
    }
  } catch (err) {
    if (loadingEl) loadingEl.style.display = 'none';
    showToast('Lỗi lập kế hoạch AI: ' + err.message, 'error');
  }
}

/**
 * 5. Hiển thị trực quan toàn bộ kết quả phân rã mục tiêu
 */
function renderPlannerResults(plan) {
  // A. Thanh Headline & Growth Pill
  const headline = document.getElementById('plan-headline-text');
  const growthPill = document.getElementById('plan-growth-pill');

  if (headline) headline.textContent = `Kế Hoạch Doanh Thu: ${formatVND(plan.targetRevenue)}`;
  if (growthPill) {
    growthPill.textContent = `${plan.growthRate >= 0 ? '+' : ''}${plan.growthRate}% TĂNG TRƯỞNG`;
    growthPill.style.background = plan.growthRate >= 0 
      ? 'linear-gradient(135deg, #10b981, #059669)' 
      : 'linear-gradient(135deg, #f59e0b, #d97706)';
  }

  // B. 4 Thẻ KPI định lượng
  const valRev = document.getElementById('plan-val-revenue');
  const noteRev = document.getElementById('plan-note-revenue');
  const valOrders = document.getElementById('plan-val-orders');
  const valAov = document.getElementById('plan-val-aov');
  const valDaily = document.getElementById('plan-val-daily');

  if (valRev) valRev.textContent = formatVND(plan.targetRevenue);
  if (noteRev) noteRev.textContent = `Cơ sở: ${formatVND(plan.baselineRevenue)} (${plan.growthRate >= 0 ? '+' : ''}${plan.growthRate}%)`;
  if (valOrders) valOrders.textContent = `${plan.requiredOrders.toLocaleString('vi-VN')} đơn`;
  if (valAov) valAov.textContent = formatVND(plan.targetAov);
  if (valDaily) valDaily.textContent = formatVND(plan.dailyTarget);

  // C. Phân bổ Quota 4 Kênh bán lẻ
  renderChannelQuotas(plan.channelQuotas || []);

  // D. Lộ trình 4 tuần & Tư vấn chiến lược của Gemini AI
  const markdownBox = document.getElementById('plan-roadmap-markdown');
  if (markdownBox) {
    markdownBox.innerHTML = renderMarkdown(plan.content);
  }
}

/**
 * 6. Render lưới 4 Thẻ Quota Kênh bán lẻ
 */
function renderChannelQuotas(channels) {
  const container = document.getElementById('plan-channel-quotas-container');
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
      <div class="channel-quota-box" style="border-top: 3px solid ${meta.color};">
        <div class="channel-quota-top">
          <div style="display:flex; align-items:center; gap:8px; font-weight:700; color:#0f172a; font-size:15px;">
            <i class="${meta.icon}" style="color:${meta.color}; font-size:16px;"></i>
            <span>${ch.channel}</span>
          </div>
          <span class="channel-badge-pct" style="color:${meta.color}; background:${meta.bg};">
            ${pct}% Quota
          </span>
        </div>
        <div class="channel-stats-row">
          <div>
            <div style="font-size:11px; color:var(--text-muted); margin-bottom:2px;">Mục tiêu doanh thu:</div>
            <div style="font-size:16px; font-weight:700; color:#0f172a; font-family:var(--font-mono);">${formatVND(ch.targetRevenue)}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px; color:var(--text-muted); margin-bottom:2px;">Chỉ tiêu đơn hàng:</div>
            <div style="font-size:15px; font-weight:700; color:#34d399; font-family:var(--font-mono);">${ch.targetOrders} đơn</div>
          </div>
        </div>
        <div class="channel-quota-bar-bg">
          <div class="channel-quota-bar-fill" style="width: ${Math.min(pct, 100)}%; background: ${meta.color};"></div>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * 7. Tải và hiển thị lịch sử các kế hoạch đã tạo
 */
async function loadPlanHistory() {
  const historyList = document.getElementById('plan-history-list');
  if (!historyList) return;

  try {
    const res = await apiRequest('/api/planner/history?limit=6');
    if (res.success && res.data) {
      if (res.data.length === 0) {
        historyList.innerHTML = '<p style="color:var(--text-muted); font-size:13px;">Chưa có bản kế hoạch nào được lưu trong hệ thống.</p>';
        return;
      }

      historyList.innerHTML = res.data.map(item => `
        <div class="history-item-card" onclick="viewHistoryPlan(${item.id})">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div class="history-item-title">
              <i class="fa-solid fa-bullseye" style="color:var(--accent-primary);"></i>
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
  } catch (err) {
    console.error('Lỗi tải lịch sử kế hoạch:', err);
  }
}

async function viewHistoryPlan(id) {
  try {
    const res = await apiRequest('/api/planner/history?limit=20');
    if (res.success && res.data) {
      const item = res.data.find(x => x.id === id);
      if (!item) return;

      const resultsWrapper = document.getElementById('plan-results-wrapper');
      const headline = document.getElementById('plan-headline-text');
      const growthPill = document.getElementById('plan-growth-pill');
      const markdownBox = document.getElementById('plan-roadmap-markdown');

      if (item.metrics_context) {
        renderPlannerResults({
          targetRevenue: item.metrics_context.targetRevenue || 0,
          baselineRevenue: item.metrics_context.baselineRevenue || 0,
          growthRate: item.metrics_context.growthRate || 0,
          requiredOrders: item.metrics_context.requiredOrders || 0,
          targetAov: item.metrics_context.targetAov || 0,
          dailyTarget: item.metrics_context.dailyTarget || 0,
          channelQuotas: item.metrics_context.channelQuotas || [],
          content: item.ai_response || ''
        });
      } else {
        if (headline) headline.textContent = item.title;
        if (growthPill) growthPill.textContent = 'LỊCH SỬ';
        if (markdownBox) markdownBox.innerHTML = renderMarkdown(item.ai_response);
      }

      if (resultsWrapper) {
        resultsWrapper.style.display = 'block';
        resultsWrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  } catch (err) {
    console.error('Lỗi xem lại kế hoạch:', err);
  }
}

// Format số có dấu chấm hàng nghìn
function formatNumber(num) {
  if (isNaN(num) || num === null) return '0';
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

// Render Markdown sang HTML
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
