/**
 * ==============================================================================
 * LOGIC BẢNG ĐIỀU KHIỂN DOANH THU & BIỂU ĐỒ (DASHBOARD JS)
 * ==============================================================================
 */

let timelineChart = null;
let channelChart = null;
let currentDays = 180;

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;

  await loadDashboardData(currentDays);

  // Lắng nghe sự kiện đổi bộ lọc thời gian
  const filterBtns = document.querySelectorAll('.btn-timeframe');
  filterBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentDays = parseInt(btn.getAttribute('data-days'));
      await loadDashboardData(currentDays);
    });
  });
});

async function loadDashboardData(days) {
  try {
    // 1. Load KPIs
    const kpiRes = await apiRequest(`/api/revenue/kpis?days=${days}`);
    if (kpiRes.success && kpiRes.data) {
      updateKpis(kpiRes.data);
    }

    // 2. Load Timeline Chart
    const timelineRes = await apiRequest(`/api/revenue/timeline?days=${days > 30 ? 30 : days}`);
    if (timelineRes.success && timelineRes.data) {
      renderTimelineChart(timelineRes.data);
    }

    // 3. Load Channel Breakdown Chart
    const channelRes = await apiRequest(`/api/revenue/channels?days=${days}`);
    if (channelRes.success && channelRes.data) {
      renderChannelChart(channelRes.data);
    }

    // 4. Load Top Products
    const topProdRes = await apiRequest('/api/revenue/top-products?limit=6');
    if (topProdRes.success && topProdRes.data) {
      renderTopProductsTable(topProdRes.data);
    }

    // 5. Load Inventory Alerts
    const alertRes = await apiRequest('/api/revenue/inventory-alerts?threshold=45');
    if (alertRes.success && alertRes.data) {
      renderInventoryAlerts(alertRes.data);
    }
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

  if (timelineChart) {
    timelineChart.destroy();
  }

  timelineChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Doanh thu (VNĐ)',
        data: revenues,
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99, 102, 241, 0.12)',
        borderWidth: 3,
        fill: true,
        tension: 0.38,
        pointBackgroundColor: '#8b5cf6',
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
          backgroundColor: '#1e293b',
          titleColor: '#fff',
          bodyColor: '#38bdf8',
          padding: 12,
          callbacks: {
            label: (item) => ' Doanh thu: ' + formatVND(item.raw)
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#94a3b8', font: { size: 11 } }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: {
            color: '#94a3b8',
            font: { size: 11 },
            callback: (val) => val >= 1000000 ? (val / 1000000).toFixed(0) + ' Tr' : val
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
  const values = data.map(d => d.total_revenue);

  if (channelChart) {
    channelChart.destroy();
  }

  const colors = ['#6366f1', '#ec4899', '#06b6d4', '#10b981', '#f59e0b'];

  channelChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors.slice(0, labels.length),
        borderWidth: 0,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#cbd5e1', padding: 14, font: { size: 12 } }
        },
        tooltip: {
          backgroundColor: '#1e293b',
          padding: 12,
          callbacks: {
            label: (item) => ` ${item.label}: ${formatVND(item.raw)}`
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

  tbody.innerHTML = products.map((p, idx) => `
    <tr>
      <td style="font-weight:700; color:var(--accent-cyan);">#${idx + 1}</td>
      <td>
        <div style="font-weight:600; color:#fff;">${p.name}</div>
        <small style="color:var(--text-muted);">${p.sku} • ${p.category_name || 'Khác'}</small>
      </td>
      <td style="font-weight:700; text-align:center;">${p.total_sold}</td>
      <td style="font-weight:600; color:var(--accent-emerald);">${formatVND(p.total_revenue)}</td>
      <td>
        <span class="badge-tag badge-success">${formatVND(p.total_profit)}</span>
      </td>
    </tr>
  `).join('');
}

function renderInventoryAlerts(alerts) {
  const tbody = document.getElementById('alerts-tbody');
  if (!tbody) return;

  if (alerts.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px; color:var(--text-muted);">Tất cả sản phẩm đều đủ tồn kho an toàn!</td></tr>';
    return;
  }

  tbody.innerHTML = alerts.map(a => `
    <tr>
      <td>
        <div style="font-weight:600; color:#fff;">${a.name}</div>
        <small style="color:var(--text-muted);">${a.sku}</small>
      </td>
      <td>
        <span class="badge-tag ${a.stock_quantity < 25 ? 'badge-danger' : 'badge-warning'}">
          ${a.stock_quantity} cái tồn
        </span>
      </td>
      <td>${formatVND(a.selling_price)}</td>
      <td>
        <a href="/static/ai-strategy.html" class="link-highlight" style="font-size:12px;">
          Gợi ý xả hàng <i class="fa-solid fa-sparkles"></i>
        </a>
      </td>
    </tr>
  `).join('');
}
