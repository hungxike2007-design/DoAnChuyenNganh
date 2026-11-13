/**
 * ==============================================================================
 * LOGIC GIAO DIỆN PHÂN HỆ PHÂN TÍCH ĐA CHIỀU (PIVOT TABLE JS)
 * ==============================================================================
 */

let currentPivotData = null;
let pivotChartInstance = null;

document.addEventListener('DOMContentLoaded', async () => {
  if (!checkPageRole(['admin', 'manager', 'sales', 'user'])) return;

  setupUserNavbar();
  setupEventListeners();
  await loadPivotMatrix();
});

function setupUserNavbar() {
  const user = getUser();
  if (!user) return;
  const nameEl = document.getElementById('user-name');
  const roleEl = document.getElementById('user-role');
  const avatarEl = document.getElementById('user-avatar-initials');
  const adminGroup = document.getElementById('nav-group-admin');

  if (nameEl) nameEl.textContent = user.fullName || user.email || 'Người dùng';
  if (roleEl) roleEl.textContent = (user.role || 'user').toUpperCase();
  if (avatarEl) {
    const initial = (user.fullName || user.email || 'U').charAt(0).toUpperCase();
    avatarEl.textContent = initial;
  }
  if (adminGroup && (user.role === 'admin')) {
    adminGroup.style.display = 'block';
  }
}

function setupEventListeners() {
  document.getElementById('btn-generate-pivot')?.addEventListener('click', loadPivotMatrix);
  document.getElementById('btn-ai-insight')?.addEventListener('click', loadAiInsight);
  document.getElementById('btn-export-csv')?.addEventListener('click', exportMatrixCsv);
  document.getElementById('btn-logout')?.addEventListener('click', () => {
    localStorage.removeItem('dacn_token');
    localStorage.removeItem('dacn_user');
    window.location.replace('/frontend/auth/login.html');
  });

  // Tự động load lại khi đổi chỉ số hoặc thời gian
  document.getElementById('select-metric')?.addEventListener('change', loadPivotMatrix);
  document.getElementById('select-days')?.addEventListener('change', loadPivotMatrix);
  document.getElementById('select-status')?.addEventListener('change', loadPivotMatrix);

  // Tự động ngăn trùng lặp giữa Trục Dòng và Trục Cột
  const rowSelect = document.getElementById('select-row-dim');
  const colSelect = document.getElementById('select-col-dim');

  rowSelect?.addEventListener('change', () => {
    if (rowSelect.value === colSelect.value) {
      for (let opt of colSelect.options) {
        if (opt.value !== rowSelect.value) {
          colSelect.value = opt.value;
          break;
        }
      }
      showToast('Đã tự động chuyển trục cột sang chiều khác để tránh trùng lặp ma trận!', 'info');
    }
    loadPivotMatrix();
  });

  colSelect?.addEventListener('change', () => {
    if (colSelect.value === rowSelect.value) {
      for (let opt of rowSelect.options) {
        if (opt.value !== colSelect.value) {
          rowSelect.value = opt.value;
          break;
        }
      }
      showToast('Đã tự động chuyển trục dòng sang chiều khác để tránh trùng lặp ma trận!', 'info');
    }
    loadPivotMatrix();
  });
}

/**
 * 1. Gọi API nạp dữ liệu ma trận Pivot 2 chiều
 */
async function loadPivotMatrix() {
  const rowDim = document.getElementById('select-row-dim')?.value || 'channel';
  const colDim = document.getElementById('select-col-dim')?.value || 'category';
  const metric = document.getElementById('select-metric')?.value || 'total_revenue';
  const days = parseInt(document.getElementById('select-days')?.value || '90', 10);
  const statusFilter = document.getElementById('select-status')?.value || 'completed';

  if (rowDim === colDim) {
    showToast('Trục dòng và trục cột không được trùng nhau!', 'warning');
    return;
  }

  const container = document.getElementById('pivot-table-container');
  if (container) {
    container.innerHTML = `
      <div style="padding:40px; text-align:center; color:#64748b;">
        <i class="fa-solid fa-spinner fa-spin fa-2x" style="margin-bottom:12px; color:#0284c7;"></i>
        <p>Đang tính toán ma trận xoay đa chiều...</p>
      </div>
    `;
  }

  try {
    const res = await apiRequest('/api/analytics/pivot/matrix', {
      method: 'POST',
      body: JSON.stringify({
        row_dimension: rowDim,
        col_dimension: colDim,
        metric: metric,
        days: days,
        status_filter: statusFilter
      })
    });

    if (res.success && res.data) {
      currentPivotData = res.data;
      renderPivotTable(currentPivotData);
      renderPivotChart(currentPivotData);
    } else {
      if (container) {
        container.innerHTML = `<div style="padding:30px; text-align:center; color:#ef4444;">Không thể tạo ma trận: ${res.message || 'Lỗi không xác định'}</div>`;
      }
    }
  } catch (err) {
    console.error('Lỗi khi nạp ma trận Pivot:', err);
    if (container) {
      container.innerHTML = `<div style="padding:30px; text-align:center; color:#ef4444;">Lỗi kết nối máy chủ: ${err.message}</div>`;
    }
  }
}

/**
 * 2. Render bảng ma trận nhiệt (Heatmap Table)
 */
function renderPivotTable(data) {
  const container = document.getElementById('pivot-table-container');
  if (!container) return;

  const rowHeaders = data.row_headers || [];
  const colHeaders = data.col_headers || [];
  const matrix = data.matrix || [];
  const rowTotals = data.row_totals || [];
  const colTotals = data.col_totals || [];
  const grandTotal = data.grand_total || 0;
  const maxVal = data.max_val || 1;
  const metricUnit = data.metric_unit || '';
  const isCurrency = metricUnit === '₫';

  if (rowHeaders.length === 0 || colHeaders.length === 0) {
    container.innerHTML = `
      <div style="padding:40px; text-align:center; color:#64748b;">
        <i class="fa-solid fa-circle-exclamation fa-2x" style="margin-bottom:12px; color:#f59e0b;"></i>
        <p>Không có dữ liệu giao thoa phù hợp cho 2 chiều phân tích này trong kỳ đã chọn.</p>
      </div>
    `;
    return;
  }

  let html = `<table class="pivot-table"><thead><tr>`;
  html += `<th class="pivot-th-corner">${escapeHtml(data.row_dimension_label)} \\ ${escapeHtml(data.col_dimension_label)}</th>`;

  colHeaders.forEach(col => {
    html += `<th>${escapeHtml(col)}</th>`;
  });
  html += `<th class="pivot-th-total">TỔNG HÀNG (${escapeHtml(metricUnit)})</th></tr></thead><tbody>`;

  matrix.forEach((row, rIdx) => {
    const rowName = rowHeaders[rIdx] || `Hàng ${rIdx + 1}`;
    html += `<tr><td class="pivot-td-header">${escapeHtml(rowName)}</td>`;

    row.forEach(val => {
      const ratio = maxVal > 0 ? (val / maxVal) : 0;
      // Dải màu nhiệt: từ trắng nhạt (#ffffff) đến xanh đậm rực (#0284c7)
      const bgColor = val > 0 
        ? `rgba(2, 132, 199, ${Math.max(0.08, ratio.toFixed(2))})` 
        : '#ffffff';
      const textColor = ratio > 0.65 ? '#ffffff' : '#0f172a';
      const formattedVal = isCurrency ? formatCurrencyVND(val) : formatNumber(val);

      html += `<td style="background-color: ${bgColor}; color: ${textColor};" title="${escapeHtml(rowName)} - ${formattedVal} ${metricUnit}">${formattedVal}</td>`;
    });

    const rTotalFormatted = isCurrency ? formatCurrencyVND(rowTotals[rIdx] || 0) : formatNumber(rowTotals[rIdx] || 0);
    html += `<td class="pivot-td-total">${rTotalFormatted}</td></tr>`;
  });

  // Hàng tổng cột (Grand Total Row)
  html += `<tr class="pivot-tr-grand-total"><td class="pivot-td-header" style="background:#e0f2fe; color:#0369a1;">TỔNG CỘT</td>`;
  colTotals.forEach(cTotal => {
    const cTotalFormatted = isCurrency ? formatCurrencyVND(cTotal) : formatNumber(cTotal);
    html += `<td>${cTotalFormatted}</td>`;
  });
  const grandFormatted = isCurrency ? formatCurrencyVND(grandTotal) : formatNumber(grandTotal);
  html += `<td>${grandFormatted}</td></tr>`;

  html += `</tbody></table>`;
  container.innerHTML = html;
}

/**
 * 3. Trực quan hóa tương quan bằng Chart.js
 */
function renderPivotChart(data) {
  const ctx = document.getElementById('pivotBarChart');
  if (!ctx) return;

  if (pivotChartInstance) {
    pivotChartInstance.destroy();
  }

  const rowHeaders = data.row_headers || [];
  const colHeaders = data.col_headers || [];
  const matrix = data.matrix || [];

  // Giới hạn tối đa 6 cột để biểu đồ không bị rối
  const displayCols = colHeaders.slice(0, 6);
  const colorPalette = [
    '#0284c7', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b'
  ];

  const datasets = displayCols.map((colName, cIdx) => {
    const dataPoints = rowHeaders.map((_, rIdx) => matrix[rIdx] ? matrix[rIdx][cIdx] || 0 : 0);
    return {
      label: colName,
      data: dataPoints,
      backgroundColor: colorPalette[cIdx % colorPalette.length],
      borderRadius: 4
    };
  });

  pivotChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: rowHeaders,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: { font: { family: 'inherit', size: 12, weight: 600 } }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const val = context.raw || 0;
              const unit = data.metric_unit || '';
              return ` ${context.dataset.label}: ${val.toLocaleString('vi-VN')} ${unit}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { family: 'inherit', size: 12 } }
        },
        y: {
          beginAtZero: true,
          grid: { color: '#f1f5f9' },
          ticks: {
            font: { family: 'inherit', size: 11 },
            callback: function(value) {
              if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
              if (value >= 1000) return (value / 1000).toFixed(0) + 'k';
              return value;
            }
          }
        }
      }
    }
  });
}

/**
 * 4. Gọi Gemini AI phân tích ma trận
 */
async function loadAiInsight() {
  if (!currentPivotData) {
    showToast('Vui lòng tạo ma trận trước khi yêu cầu AI phân tích!', 'warning');
    return;
  }

  const aiWrapper = document.getElementById('ai-insight-wrapper');
  const aiContent = document.getElementById('ai-insight-content');
  const aiBadge = document.getElementById('ai-model-badge');

  if (aiWrapper) aiWrapper.style.display = 'block';
  if (aiContent) {
    aiContent.innerHTML = `
      <div style="padding:16px 0; display:flex; align-items:center; gap:10px; color:#15803d;">
        <i class="fa-solid fa-spinner fa-spin fa-lg"></i>
        <span>Gemini AI đang phân tích toàn bộ ma trận số liệu và giải mã các điểm vàng doanh thu...</span>
      </div>
    `;
  }

  try {
    const res = await apiRequest('/api/analytics/pivot/ai-insight', {
      method: 'POST',
      body: JSON.stringify({ pivot_data: currentPivotData })
    });

    if (res.success && res.data) {
      if (aiBadge) aiBadge.textContent = res.data.model || 'Gemini 3.5 Flash';
      if (aiContent) {
        aiContent.innerHTML = formatMarkdownToHtml(res.data.insight_text || '');
      }
    } else {
      if (aiContent) aiContent.innerHTML = `<p style="color:#ef4444;">Lỗi khi gọi AI: ${res.message || 'Không có phản hồi'}</p>`;
    }
  } catch (err) {
    console.error('Lỗi Gemini AI Insight:', err);
    if (aiContent) aiContent.innerHTML = `<p style="color:#ef4444;">Không thể kết nối dịch vụ AI: ${err.message}</p>`;
  }
}

/**
 * 5. Xuất bảng ma trận ra file CSV
 */
function exportMatrixCsv() {
  if (!currentPivotData) {
    showToast('Chưa có dữ liệu ma trận để xuất file!', 'warning');
    return;
  }

  const rowLabel = currentPivotData.row_dimension_label || 'Hàng';
  const colLabel = currentPivotData.col_dimension_label || 'Cột';
  const rowHeaders = currentPivotData.row_headers || [];
  const colHeaders = currentPivotData.col_headers || [];
  const matrix = currentPivotData.matrix || [];
  const rowTotals = currentPivotData.row_totals || [];
  const colTotals = currentPivotData.col_totals || [];
  const grandTotal = currentPivotData.grand_total || 0;

  let csvContent = '\uFEFF'; // BOM UTF-8 chống lỗi font tiếng Việt trong Excel
  // Dòng tiêu đề
  csvContent += `"${rowLabel} \\ ${colLabel}",` + colHeaders.map(c => `"${c}"`).join(',') + ',"TỔNG HÀNG"\n';

  // Các dòng dữ liệu
  matrix.forEach((row, rIdx) => {
    const rName = rowHeaders[rIdx] || '';
    const rowCells = row.map(v => v.toString()).join(',');
    const rTot = rowTotals[rIdx] || 0;
    csvContent += `"${rName}",${rowCells},${rTot}\n`;
  });

  // Dòng tổng cộng
  csvContent += `"TỔNG CỘT",` + colTotals.map(c => c.toString()).join(',') + `,${grandTotal}\n`;

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `ma_tran_pivot_${currentPivotData.row_dimension}_${currentPivotData.col_dimension}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast('Đã xuất file CSV thành công!', 'success');
}

// Helper formats
function formatCurrencyVND(val) {
  return Math.round(val).toLocaleString('vi-VN') + ' ₫';
}

function formatNumber(val) {
  return (val % 1 === 0 ? val : val.toFixed(1)).toLocaleString('vi-VN');
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatMarkdownToHtml(md) {
  if (!md) return '';
  // Convert headers
  let html = md.replace(/^### (.*$)/gim, '<h4 style="margin:16px 0 6px 0; color:#0f172a; font-size:15px; font-weight:700;">$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3 style="margin:18px 0 8px 0; color:#0f172a; font-size:16px; font-weight:800;">$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2 style="margin:20px 0 10px 0; color:#0f172a; font-size:18px; font-weight:800;">$1</h2>');
  
  // Bold & Italic
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong style="color:#0f172a;">$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em style="color:#334155;">$1</em>');
  
  // Bullet lists
  html = html.replace(/^\s*-\s+(.*$)/gim, '<li style="margin-left:20px; margin-bottom:6px; color:#334155;">$1</li>');
  html = html.replace(/^\s*\*\s+(.*$)/gim, '<li style="margin-left:20px; margin-bottom:6px; color:#334155;">$1</li>');
  html = html.replace(/^\s*(\d+)\.\s+(.*$)/gim, '<div style="margin-top:14px; margin-bottom:6px; font-weight:700; color:#0f172a; font-size:14px;">$1. $2</div>');
  
  // Line breaks
  html = html.replace(/\n\n/g, '<div style="height:6px;"></div>');
  html = html.replace(/\n/g, '<br/>');
  return html;
}

