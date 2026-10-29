/**
 * ==============================================================================
 * LOGIC BẢNG ĐIỀU KHIỂN DOANH THU & BẢNG XẾP HẠNG USER (DASHBOARD JS)
 * ==============================================================================
 */

let timelineChart = null;
let channelChart = null;
let currentDays = 180;
let inspectingUserId = null; // null if viewing own data or if Admin is in ranking mode
let allRankingUsers = [];

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;
  const user = getUser();
  const role = (user?.role || 'user').toLowerCase();

  // Thiết lập sự kiện đổi bộ lọc thời gian
  const filterBtns = document.querySelectorAll('.btn-timeframe');
  filterBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentDays = parseInt(btn.getAttribute('data-days'));
      await loadDashboardData(currentDays, inspectingUserId);
    });
  });

  if (role === 'admin' || role === 'manager') {
    // 1. DÀNH CHO ADMIN & MANAGER:
    // Mặc định hiện Bảng Xếp Hạng & Danh Sách User, KHÔNG HIỆN CONSOLIDATED VIEW
    setupAdminDashboard();
  } else {
    // 2. DÀNH CHO USER / SALES:
    // Mặc định hiện ngay Dashboard cá nhân của chính User đó
    setupUserDashboard();
  }
});

async function setupAdminDashboard() {
  const rankingSection = document.getElementById('admin-user-ranking-section');
  const detailSection = document.getElementById('user-revenue-detail-section');
  const pageTitle = document.getElementById('dashboard-page-title');
  const pageDesc = document.getElementById('dashboard-page-desc');

  if (pageTitle) pageTitle.textContent = 'Quản Trị Doanh Thu Người Dùng & Hiệu Suất Bán Hàng';
  if (pageDesc) pageDesc.textContent = 'Mỗi người dùng sở hữu dữ liệu kinh doanh độc lập. Bấm vào người dùng bất kỳ bên dưới để xem chi tiết báo cáo doanh thu của họ.';

  if (rankingSection) rankingSection.style.display = 'block';
  if (detailSection) detailSection.style.display = 'none';

  await loadUserRankings();
}

async function setupUserDashboard() {
  const rankingSection = document.getElementById('admin-user-ranking-section');
  const detailSection = document.getElementById('user-revenue-detail-section');
  const inspectingBanner = document.getElementById('inspecting-banner');
  const pageTitle = document.getElementById('dashboard-page-title');
  const pageDesc = document.getElementById('dashboard-page-desc');

  if (pageTitle) pageTitle.textContent = 'Bảng Điều Khiển Doanh Thu Cá Nhân';
  if (pageDesc) pageDesc.textContent = 'Theo dõi doanh số, số đơn đặt hàng và hiệu suất bán hàng của tài khoản bạn.';

  if (rankingSection) rankingSection.style.display = 'none';
  if (inspectingBanner) inspectingBanner.style.display = 'none';
  if (detailSection) detailSection.style.display = 'block';

  await loadDashboardData(currentDays, null);
}

async function loadUserRankings() {
  const tbody = document.getElementById('user-leaderboard-tbody');
  const countBadge = document.getElementById('ranking-users-count');

  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:24px; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải dữ liệu người dùng từ SQL Server...</td></tr>';
  }

  try {
    const res = await apiRequest('/api/revenue/user-rankings');
    if (res.success && res.data) {
      allRankingUsers = res.data;
      if (countBadge) countBadge.textContent = `${allRankingUsers.length} Tài Khoản`;
      renderUserLeaderboard(allRankingUsers);
    }
  } catch (err) {
    showToast('Lỗi khi tải bảng xếp hạng: ' + err.message, 'error');
  }
}

function renderUserLeaderboard(users) {
  const tbody = document.getElementById('user-leaderboard-tbody');
  if (!tbody) return;

  if (!users || users.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:24px; color:var(--text-muted);">Không tìm thấy người dùng nào phù hợp.</td></tr>';
    return;
  }

  tbody.innerHTML = users.map((u, idx) => {
    let rankBadge = `<span style="font-weight:700; color:var(--text-secondary);">#${idx + 1}</span>`;
    if (idx === 0) rankBadge = `<span style="font-size:16px;">🥇</span> <b style="color:#d97706;">#1</b>`;
    else if (idx === 1) rankBadge = `<span style="font-size:16px;">🥈</span> <b style="color:#64748b;">#2</b>`;
    else if (idx === 2) rankBadge = `<span style="font-size:16px;">🥉</span> <b style="color:#b45309;">#3</b>`;

    let roleBadge = '<span class="badge-tag badge-dss">USER</span>';
    if (u.role === 'admin') roleBadge = '<span class="badge-tag badge-admin">ADMIN</span>';
    else if (u.role === 'manager') roleBadge = '<span class="badge-tag badge-chat">MANAGER</span>';
    else if (u.role === 'sales') roleBadge = '<span class="badge-tag badge-pro">SALES</span>';

    const lastDate = u.last_order_date || 'Chưa phát sinh';

    return `
      <tr style="cursor: pointer;" onclick="inspectUser(${u.id}, '${u.full_name}', '${u.email}')">
        <td style="text-align:center;">${rankBadge}</td>
        <td>
          <div style="font-weight:700; color:var(--text-primary); font-size:13.5px;">${u.full_name || 'Người dùng #' + u.id}</div>
          <small style="color:var(--text-muted);"><i class="fa-solid fa-envelope" style="font-size:10px; margin-right:4px;"></i>${u.email}</small>
        </td>
        <td>${roleBadge}</td>
        <td style="font-weight:700; text-align:center; color:var(--text-primary); font-size:13px;">
          ${u.total_orders} đơn
        </td>
        <td style="font-weight:800; color:var(--accent-emerald); font-size:14px;">
          ${formatVND(u.total_revenue)}
        </td>
        <td style="font-weight:600; color:var(--text-primary); font-size:13px;">
          ${formatVND(u.avg_order_value)}
        </td>
        <td>
          <span style="font-size:12px; color:var(--text-secondary);"><i class="fa-regular fa-clock" style="font-size:11px; color:#94a3b8; margin-right:4px;"></i>${lastDate}</span>
        </td>
        <td style="text-align:center;" onclick="event.stopPropagation();">
          <button class="btn btn-secondary" onclick="inspectUser(${u.id}, '${u.full_name}', '${u.email}')" style="padding:4px 10px; font-size:11.5px; border-radius:6px; font-weight:600;">
            <i class="fa-solid fa-chart-line" style="color:var(--accent-primary);"></i> Xem Doanh Thu
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function filterUserRankings(query) {
  const q = (query || '').toLowerCase().trim();
  if (!q) {
    renderUserLeaderboard(allRankingUsers);
    return;
  }
  const filtered = allRankingUsers.filter(u => 
    (u.full_name || '').toLowerCase().includes(q) || 
    (u.email || '').toLowerCase().includes(q)
  );
  renderUserLeaderboard(filtered);
}

async function inspectUser(userId, userName, userEmail) {
  inspectingUserId = userId;
  const rankingSection = document.getElementById('admin-user-ranking-section');
  const detailSection = document.getElementById('user-revenue-detail-section');
  const inspectingBanner = document.getElementById('inspecting-banner');
  const nameEl = document.getElementById('inspecting-user-name');
  const emailEl = document.getElementById('inspecting-user-email');

  if (nameEl) nameEl.textContent = userName;
  if (emailEl) emailEl.textContent = userEmail;

  if (rankingSection) rankingSection.style.display = 'none';
  if (detailSection) detailSection.style.display = 'block';
  if (inspectingBanner) inspectingBanner.style.display = 'flex';

  await loadDashboardData(currentDays, userId);

  // Cuộn mượt lên trên
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function backToUserRanking() {
  inspectingUserId = null;
  const rankingSection = document.getElementById('admin-user-ranking-section');
  const detailSection = document.getElementById('user-revenue-detail-section');
  const inspectingBanner = document.getElementById('inspecting-banner');

  if (rankingSection) rankingSection.style.display = 'block';
  if (detailSection) detailSection.style.display = 'none';
  if (inspectingBanner) inspectingBanner.style.display = 'none';

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function loadDashboardData(days, targetUserId = null) {
  const queryParam = targetUserId ? `&view_user_id=${targetUserId}` : '';

  try {
    // 1. KPIs
    const kpiRes = await apiRequest(`/api/revenue/kpis?days=${days}${queryParam}`);
    if (kpiRes.success && kpiRes.data) updateKpis(kpiRes.data);

    // 2. Timeline
    const timelineRes = await apiRequest(`/api/revenue/timeline?days=${days > 30 ? 30 : days}${queryParam}`);
    if (timelineRes.success && timelineRes.data) renderTimelineChart(timelineRes.data);

    // 3. Channels
    const channelRes = await apiRequest(`/api/revenue/channels?days=${days}${queryParam}`);
    if (channelRes.success && channelRes.data) renderChannelChart(channelRes.data);

    // 4. Top Products
    const topProdRes = await apiRequest(`/api/revenue/top-products?limit=6${queryParam}`);
    if (topProdRes.success && topProdRes.data) renderTopProductsTable(topProdRes.data);

    // 5. Inventory Alerts
    const alertRes = await apiRequest(`/api/revenue/inventory-alerts?threshold=45${queryParam}`);
    if (alertRes.success && alertRes.data) renderInventoryAlerts(alertRes.data);
  } catch (err) {
    showToast('Lỗi khi tải dữ liệu thống kê: ' + err.message, 'error');
  }
}

function updateKpis(kpis) {
  document.getElementById('kpi-revenue').textContent = formatVND(kpis.totalRevenue);
  document.getElementById('kpi-profit').textContent = formatVND(kpis.grossProfit);
  document.getElementById('kpi-margin').textContent = `Tỷ suất lợi nhuận: ${kpis.profitMargin}%`;
  document.getElementById('kpi-orders').textContent = kpis.totalOrders.toLocaleString('vi-VN');
  document.getElementById('kpi-completed-rate').textContent = `${kpis.completedOrders} đơn thành công`;
  document.getElementById('kpi-aov').textContent = formatVND(kpis.aov);
  document.getElementById('kpi-cancel-rate').textContent = `Tỷ lệ hủy: ${kpis.cancelRate}%`;
}

function renderTimelineChart(data) {
  const ctx = document.getElementById('timelineChart');
  if (!ctx) return;

  const labels = data.map(d => d.date);
  const revenues = data.map(d => d.revenue);

  if (timelineChart) timelineChart.destroy();

  timelineChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Doanh thu (VNĐ)',
        data: revenues,
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.08)',
        borderWidth: 3,
        fill: true,
        tension: 0.38,
        pointBackgroundColor: '#2563eb',
        pointBorderColor: '#fff',
        pointRadius: 4,
        pointHoverRadius: 7
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          titleFont: { size: 13, weight: 'bold' },
          bodyFont: { size: 12 },
          padding: 10,
          callbacks: {
            label: (ctx) => `Doanh thu: ${formatVND(ctx.parsed.y)}`
          }
        }
      },
      scales: {
        x: { grid: { color: '#f1f5f9' }, ticks: { color: '#64748b', font: { size: 11 } } },
        y: {
          grid: { color: '#f1f5f9' },
          ticks: {
            color: '#64748b',
            font: { size: 11 },
            callback: (val) => val >= 1000000 ? `${(val / 1000000).toFixed(1)} tr` : val
          }
        }
      }
    }
  });
}

function renderChannelChart(data) {
  const ctx = document.getElementById('channelChart');
  if (!ctx) return;

  const labels = data.map(d => d.channel);
  const revenues = data.map(d => d.revenue);

  if (channelChart) channelChart.destroy();

  channelChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: revenues,
        backgroundColor: ['#2563eb', '#06b6d4', '#10b981', '#f59e0b', '#dc2626'],
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#475569', font: { size: 12 }, padding: 14 }
        },
        tooltip: {
          backgroundColor: '#0f172a',
          callbacks: {
            label: (ctx) => `${ctx.label}: ${formatVND(ctx.parsed)}`
          }
        }
      },
      cutout: '68%'
    }
  });
}

function renderTopProductsTable(products) {
  const tbody = document.getElementById('top-products-tbody');
  if (!tbody) return;

  if (!products || products.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:24px; color:var(--text-muted);"><i class="fa-solid fa-box-open" style="font-size:20px; display:block; margin-bottom:8px;"></i>Chưa có sản phẩm nào phát sinh doanh thu.</td></tr>';
    return;
  }

  tbody.innerHTML = products.map((p, idx) => `
    <tr>
      <td style="font-weight:700; color:var(--accent-cyan);">#${idx + 1}</td>
      <td>
        <div style="font-weight:700; color:var(--text-primary);">${p.name}</div>
        <small style="color:var(--text-muted);">${p.sku} • ${p.category_name || 'Khác'}</small>
      </td>
      <td style="font-weight:700; text-align:center;">${p.total_sold}</td>
      <td style="font-weight:700; color:var(--accent-emerald);">${formatVND(p.total_revenue)}</td>
      <td>
        <span class="badge-tag badge-success">${formatVND(p.total_profit || 0)}</span>
      </td>
    </tr>
  `).join('');
}

function renderInventoryAlerts(alerts) {
  const tbody = document.getElementById('alerts-tbody');
  if (!tbody) return;

  if (!alerts || alerts.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:20px; color:var(--text-muted);">Tất cả sản phẩm đều đủ tồn kho an toàn!</td></tr>';
    return;
  }

  tbody.innerHTML = alerts.map(a => `
    <tr>
      <td>
        <div style="font-weight:700; color:var(--text-primary);">${a.name}</div>
        <small style="color:var(--text-muted);">${a.sku}</small>
      </td>
      <td>
        <span class="badge-tag ${a.stock_quantity < 25 ? 'badge-danger' : 'badge-warning'}">
          ${a.stock_quantity} cái tồn
        </span>
      </td>
      <td style="font-weight:700; color:var(--accent-emerald);">${formatVND(a.selling_price)}</td>
    </tr>
  `).join('');
}
