/**
 * ==============================================================================
 * LOGIC BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH (PNL REPORT JS)
 * ==============================================================================
 */

let currentPnlData = null;
let waterfallChartInstance = null;
let costDonutChartInstance = null;

document.addEventListener('DOMContentLoaded', async () => {
  if (!checkPageRole(['admin', 'manager', 'sales', 'user'])) return;

  const user = getUser();
  const role = (user && user.role ? user.role : 'user').toLowerCase();

  // Chỉ Admin và Manager mới có quyền cập nhật chi phí OPEX
  if (role === 'sales' || role === 'user') {
    const editOpexBtn = document.getElementById('btn-edit-opex');
    if (editOpexBtn) editOpexBtn.style.display = 'none';
  }

  // Khởi tạo các bộ lọc với giá trị hiện tại (mặc định Tháng 10/2026 là kỳ có dữ liệu đơn hàng)
  const monthSelect = document.getElementById('filter-month');
  const yearSelect = document.getElementById('filter-year');
  const channelSelect = document.getElementById('filter-channel');
  const userSelect = document.getElementById('filter-user');

  if (monthSelect) monthSelect.value = '10';
  if (yearSelect) yearSelect.value = '2026';

  monthSelect?.addEventListener('change', loadPnlReport);
  yearSelect?.addEventListener('change', loadPnlReport);
  channelSelect?.addEventListener('change', loadPnlReport);
  if (['admin', 'manager'].includes(role) && userSelect) {
    userSelect.style.display = '';
    try {
      const usersRes = await apiRequest('/api/financial/pnl-users');
      if (usersRes.success) {
        usersRes.data.forEach(u => {
          const option = document.createElement('option');
          option.value = u.id;
          option.textContent = `${u.full_name || u.email} (${u.email})`;
          userSelect.appendChild(option);
        });
      }
    } catch (err) {
      showToast('Không thể tải danh sách người dùng: ' + err.message, 'error');
    }
    userSelect.addEventListener('change', loadPnlReport);
  }

  // Lắng nghe thay đổi input trong Modal OPEX để tính tổng realtime
  ['input-rent', 'input-salary', 'input-marketing', 'input-utilities', 'input-other'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', updateModalOpexTotal);
  });

  await loadPnlReport();
});

async function loadPnlReport() {
  const month = document.getElementById('filter-month')?.value || 10;
  const year = document.getElementById('filter-year')?.value || 2026;
  const channel = document.getElementById('filter-channel')?.value || 'All';
  const viewUserId = document.getElementById('filter-user')?.value || '';

  // Cập nhật tiêu đề in ấn
  const printTitle = document.getElementById('print-period-title');
  if (printTitle) {
    const selectedUser = document.getElementById('filter-user')?.selectedOptions[0]?.textContent;
    printTitle.textContent = `Kỳ kế toán: Tháng ${month} Năm ${year}${channel !== 'All' ? ' (Kênh ' + channel + ')' : ''}${viewUserId ? ' (' + selectedUser + ')' : ''}`;
  }

  const statementSubtitle = document.getElementById('statement-period-subtitle');
  if (statementSubtitle) {
    const prevMonth = month == 1 ? 12 : month - 1;
    const prevYear = month == 1 ? year - 1 : year;
    statementSubtitle.textContent = `Tháng ${month}/${year} so sánh cùng kỳ Tháng ${prevMonth}/${prevYear}`;
  }

  const tbody = document.getElementById('pnl-statement-tbody');
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align:center; padding:32px; color:#64748b;">
          <i class="fa-solid fa-spinner fa-spin" style="margin-right:6px;"></i> Đang kết xuất báo cáo tài chính P&L từ SQL Server...
        </td>
      </tr>
    `;
  }

  try {
    const res = await apiRequest(`/api/financial/pnl-report?month=${month}&year=${year}&channel=${encodeURIComponent(channel)}${viewUserId ? '&view_user_id=' + encodeURIComponent(viewUserId) : ''}`);
    if (res.success && res.data) {
      currentPnlData = res.data;
      renderPnlSummary(currentPnlData.summary);
      renderPnlStatementTable(currentPnlData.statement);
      renderWaterfallChart(currentPnlData.waterfall);
      renderCostDonutChart(currentPnlData.cost_distribution);
    } else {
      showToast(res.detail || 'Không thể tải báo cáo tài chính!', 'error');
    }
  } catch (err) {
    showToast('Lỗi khi tải báo cáo P&L: ' + err.message, 'error');
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:24px; color:#ef4444;">Lỗi: ${err.message}</td></tr>`;
    }
  }
}

function renderPnlSummary(summary) {
  if (!summary) return;

  // 1. Doanh thu thuần
  const netRevEl = document.getElementById('card-net-revenue');
  if (netRevEl) netRevEl.textContent = formatVND(summary.net_revenue);
  renderTrendPill('pill-net-revenue-mom', summary.net_revenue_mom);

  // 2. Lợi nhuận gộp
  const grossProfitEl = document.getElementById('card-gross-profit');
  if (grossProfitEl) grossProfitEl.textContent = formatVND(summary.gross_profit);
  const grossMarginEl = document.getElementById('badge-gross-margin');
  if (grossMarginEl) grossMarginEl.textContent = `Biên lãi: ${summary.gross_margin}%`;
  renderTrendPill('pill-gross-profit-mom', summary.gross_profit_mom);

  // 3. Chi phí OPEX
  const opexEl = document.getElementById('card-total-opex');
  if (opexEl) opexEl.textContent = formatVND(summary.total_opex);
  const opexShareEl = document.getElementById('text-opex-share');
  if (opexShareEl) {
    const share = summary.net_revenue > 0 ? ((summary.total_opex / summary.net_revenue) * 100).toFixed(1) : 0;
    opexShareEl.textContent = `${share}%`;
  }
  renderTrendPill('pill-total-opex-mom', summary.total_opex_mom, true); // Chi phí tăng là cảnh báo

  // 4. Lợi nhuận ròng (EBITDA)
  const ebitdaEl = document.getElementById('card-ebitda');
  const ebitdaIconBox = document.getElementById('icon-ebitda-box');
  const netMarginEl = document.getElementById('badge-net-margin');

  if (ebitdaEl) {
    ebitdaEl.textContent = formatVND(summary.ebitda);
    if (summary.ebitda >= 0) {
      ebitdaEl.style.color = '#15803d';
      if (ebitdaIconBox) {
        ebitdaIconBox.style.background = '#f0fdf4';
        ebitdaIconBox.style.color = '#16a34a';
      }
    } else {
      ebitdaEl.style.color = '#dc2626';
      if (ebitdaIconBox) {
        ebitdaIconBox.style.background = '#fef2f2';
        ebitdaIconBox.style.color = '#dc2626';
      }
    }
  }

  if (netMarginEl) {
    netMarginEl.textContent = `Biên ròng: ${summary.net_margin}%`;
    netMarginEl.style.background = summary.ebitda >= 0 ? '#dcfce7' : '#fee2e2';
    netMarginEl.style.color = summary.ebitda >= 0 ? '#166534' : '#991b1b';
  }
  renderTrendPill('pill-ebitda-mom', summary.ebitda_mom);
}

function renderTrendPill(elementId, value, reverse = false) {
  const el = document.getElementById(elementId);
  if (!el) return;

  const val = parseFloat(value) || 0;
  let isPositive = val > 0;
  if (reverse) isPositive = !isPositive;

  el.className = 'trend-pill ' + (val === 0 ? 'trend-neutral' : (isPositive ? 'trend-up' : 'trend-down'));
  const icon = val > 0 ? '<i class="fa-solid fa-arrow-trend-up"></i>' : (val < 0 ? '<i class="fa-solid fa-arrow-trend-down"></i>' : '');
  const prefix = val > 0 ? '+' : '';
  el.innerHTML = `${icon} ${prefix}${val}% MoM`;
}

function renderPnlStatementTable(items) {
  const tbody = document.getElementById('pnl-statement-tbody');
  if (!tbody || !items) return;

  tbody.innerHTML = items.map(item => {
    let rowClass = '';
    if (item.is_final) {
      rowClass = 'pnl-row-final' + (item.current < 0 ? ' is-loss' : '');
    } else if (item.is_highlight) {
      rowClass = 'pnl-row-highlight';
    } else if (item.is_header) {
      rowClass = 'pnl-row-header';
    } else if (item.is_sub) {
      rowClass = 'pnl-row-sub';
    }

    const valStr = formatVND(item.current);
    const prevStr = formatVND(item.previous);
    const mom = item.mom_growth;
    const momClass = mom > 0 ? 'trend-up' : (mom < 0 ? 'trend-down' : 'trend-neutral');
    const momIcon = mom > 0 ? '↑' : (mom < 0 ? '↓' : '');
    const momPrefix = mom > 0 ? '+' : '';

    return `
      <tr class="${rowClass}">
        <td style="font-family:monospace; font-weight:700; color:#64748b;">${item.code}</td>
        <td>${item.label}</td>
        <td style="text-align:right; font-weight:700;">${valStr}</td>
        <td style="text-align:right; font-weight:600; color:#475569;">${item.share_pct}%</td>
        <td style="text-align:right; color:#64748b;">${prevStr}</td>
        <td style="text-align:center;">
          <span class="trend-pill ${momClass}">${momIcon} ${momPrefix}${mom}%</span>
        </td>
      </tr>
    `;
  }).join('');
}

function renderWaterfallChart(waterfall) {
  const ctx = document.getElementById('pnl-waterfall-chart');
  if (!ctx || !waterfall) return;

  if (waterfallChartInstance) {
    waterfallChartInstance.destroy();
  }

  const labels = waterfall.map(w => w.label);
  const values = waterfall.map(w => w.value);
  const colors = waterfall.map(w => {
    if (w.type === 'total') return '#3b82f6';
    if (w.type === 'subtraction') return '#f97316';
    if (w.type === 'subtotal') return '#10b981';
    return w.value >= 0 ? '#16a34a' : '#ef4444';
  });

  waterfallChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Giá trị dòng tiền (VNĐ)',
        data: values,
        backgroundColor: colors,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ' ' + formatVND(ctx.raw)
          }
        }
      },
      scales: {
        y: {
          ticks: {
            callback: (v) => (v / 1e6).toFixed(0) + ' Tr'
          },
          grid: { color: '#f1f5f9' }
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 11, weight: '600' } }
        }
      }
    }
  });
}

function renderCostDonutChart(distribution) {
  const ctx = document.getElementById('pnl-cost-donut-chart');
  if (!ctx || !distribution) return;

  if (costDonutChartInstance) {
    costDonutChartInstance.destroy();
  }

  const validItems = distribution.filter(d => d.value > 0);
  const labels = validItems.map(d => d.label);
  const data = validItems.map(d => d.value);
  const colors = validItems.map(d => d.color);

  costDonutChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            boxWidth: 12,
            font: { size: 11, weight: '600' },
            padding: 12
          }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${formatVND(ctx.raw)}`
          }
        }
      },
      cutout: '62%'
    }
  });
}

// ==========================================
// MODAL QUẢN LÝ CHI PHÍ VẬN HÀNH (OPEX)
// ==========================================

function openOpexModal() {
  const modal = document.getElementById('modal-opex');
  if (!modal) return;

  const month = document.getElementById('filter-month')?.value || 10;
  const year = document.getElementById('filter-year')?.value || 2026;
  
  const periodEl = document.getElementById('modal-opex-period');
  const selectedUser = document.getElementById('filter-user')?.selectedOptions[0]?.textContent;
  if (periodEl) periodEl.textContent = `Tháng ${month}/${year}${document.getElementById('filter-user')?.value ? ` · ${selectedUser}` : ' · Toàn hệ thống'}`;

  const raw = currentPnlData?.opex_raw || {};
  document.getElementById('input-rent').value = raw.rent || 0;
  document.getElementById('input-salary').value = raw.salary || 0;
  document.getElementById('input-marketing').value = raw.marketing || 0;
  document.getElementById('input-utilities').value = raw.utilities || 0;
  document.getElementById('input-other').value = raw.other || 0;

  updateModalOpexTotal();
  modal.style.display = 'flex';
}

function closeOpexModal() {
  const modal = document.getElementById('modal-opex');
  if (modal) modal.style.display = 'none';
}

function updateModalOpexTotal() {
  const rent = parseFloat(document.getElementById('input-rent')?.value) || 0;
  const salary = parseFloat(document.getElementById('input-salary')?.value) || 0;
  const marketing = parseFloat(document.getElementById('input-marketing')?.value) || 0;
  const utilities = parseFloat(document.getElementById('input-utilities')?.value) || 0;
  const other = parseFloat(document.getElementById('input-other')?.value) || 0;

  const total = rent + salary + marketing + utilities + other;
  const totalEl = document.getElementById('modal-calculated-total');
  if (totalEl) totalEl.textContent = formatVND(total);
}

async function handleSaveOpex(e) {
  e.preventDefault();

  const month = document.getElementById('filter-month')?.value || 10;
  const year = document.getElementById('filter-year')?.value || 2026;
  const month_year = `${year}-${String(month).padStart(2, '0')}`;
  const channel = document.getElementById('filter-channel')?.value || 'All';

  const rent = parseFloat(document.getElementById('input-rent')?.value) || 0;
  const salary = parseFloat(document.getElementById('input-salary')?.value) || 0;
  const marketing = parseFloat(document.getElementById('input-marketing')?.value) || 0;
  const utilities = parseFloat(document.getElementById('input-utilities')?.value) || 0;
  const other = parseFloat(document.getElementById('input-other')?.value) || 0;

  try {
    const res = await apiRequest('/api/financial/expenses', {
      method: 'POST',
      body: JSON.stringify({
        month_year,
        channel,
        rent_expense: rent,
        salary_expense: salary,
        marketing_expense: marketing,
        utilities_expense: utilities,
        other_expense: other,
        note: `Cập nhật chi phí vận hành tháng ${month}/${year}`,
        scope_user_id: document.getElementById('filter-user')?.value || null
      })
    });

    if (res.success) {
      showToast(res.message || 'Đã lưu chi phí vận hành thành công!', 'success');
      closeOpexModal();
      await loadPnlReport();
    } else {
      showToast(res.detail || 'Lỗi khi lưu chi phí', 'error');
    }
  } catch (err) {
    showToast('Lỗi khi lưu OPEX: ' + err.message, 'error');
  }
}

// ==========================================
// XUẤT BÁO CÁO CSV (UTF-8 BOM CHO EXCEL)
// ==========================================

function exportPnlCsv() {
  if (!currentPnlData || !currentPnlData.statement) {
    showToast('Chưa có dữ liệu báo cáo để xuất!', 'warning');
    return;
  }

  const p = currentPnlData.period;
  let csv = '\uFEFF'; // UTF-8 BOM
  csv += `BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH (P&L)\n`;
  csv += `Kỳ báo cáo: Tháng ${p.month}/${p.year} (Kênh: ${p.channel})\n`;
  csv += `Ngày xuất báo cáo: ${new Date().toLocaleDateString('vi-VN')}\n\n`;
  csv += `Mã số,Chỉ tiêu tài chính,Kỳ này (VNĐ),Tỷ trọng (%),Kỳ trước (VNĐ),Biến động MoM (%)\n`;

  currentPnlData.statement.forEach(item => {
    const label = `"${item.label.replace(/"/g, '""').trim()}"`;
    csv += `"${item.code}",${label},${item.current},${item.share_pct}%,${item.previous},${item.mom_growth}%\n`;
  });

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Bao_Cao_PnL_Thang_${p.month}_${p.year}${document.getElementById('filter-user')?.value ? '_user_' + document.getElementById('filter-user').value : ''}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast('Đã xuất file CSV thành công!', 'success');
}
