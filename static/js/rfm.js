/**
 * ==============================================================================
 * LOGIC PHÂN KHÚC KHÁCH HÀNG RFM (CUSTOMER RFM JS)
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!checkPageRole(['admin', 'manager'])) return;

  try {
    const res = await apiRequest('/api/revenue/rfm');
    if (res.success && res.data) {
      renderSegmentCards(res.data.segments);
      renderTopCustomersTable(res.data.topCustomers);
    }
  } catch (err) {
    showToast('Lỗi khi tải dữ liệu phân khúc: ' + err.message, 'error');
  }
});

function renderSegmentCards(segments) {
  const container = document.getElementById('rfm-cards-grid');
  if (!container) return;

  const segmentConfig = {
    'VIP': { color: 'var(--accent-amber)', icon: 'fa-crown', desc: 'Khách hàng chi tiêu cao nhất, tần suất mua đều đặn' },
    'Loyal': { color: 'var(--accent-emerald)', icon: 'fa-heart', desc: 'Khách hàng trung thành, gắn bó lâu năm' },
    'Potential': { color: 'var(--accent-cyan)', icon: 'fa-arrow-trend-up', desc: 'Khách hàng tiềm năng, cần tiếp thị thêm' },
    'At-Risk': { color: 'var(--accent-rose)', icon: 'fa-triangle-exclamation', desc: 'Đã lâu chưa quay lại, nguy cơ rời bỏ cao' },
    'New': { color: 'var(--accent-primary)', icon: 'fa-sparkles', desc: 'Khách hàng mới phát sinh đơn đầu tiên' }
  };

  container.innerHTML = segments.map(s => {
    const cfg = segmentConfig[s.segment] || { color: 'var(--accent-primary)', icon: 'fa-user', desc: 'Phân khúc khách hàng' };
    return `
      <div class="glass-card" style="padding:22px; position:relative; overflow:hidden;">
        <div style="position:absolute; top:0; left:0; right:0; height:3px; background:${cfg.color};"></div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <h3 style="font-size:16px; font-weight:700; color:#fff; display:flex; align-items:center; gap:8px;">
            <i class="fa-solid ${cfg.icon}" style="color:${cfg.color};"></i>
            Phân khúc ${s.segment}
          </h3>
          <span class="badge-tag" style="background:rgba(255,255,255,0.08); color:#fff;">${s.customer_count} khách</span>
        </div>
        <p style="font-size:12px; color:var(--text-muted); margin-bottom:16px;">${cfg.desc}</p>
        <div style="font-size:22px; font-weight:700; color:${cfg.color}; margin-bottom:4px;">
          ${formatVND(s.total_revenue)}
        </div>
        <small style="font-size:11px; color:var(--text-secondary);">Trung bình: ${formatVND(s.avg_spent)} / khách</small>
      </div>
    `;
  }).join('');
}

function renderTopCustomersTable(customers) {
  const tbody = document.getElementById('top-customers-tbody');
  if (!tbody) return;

  tbody.innerHTML = customers.map((c, idx) => `
    <tr>
      <td style="font-weight:700; color:var(--accent-cyan);">#${idx + 1}</td>
      <td>
        <div style="font-weight:600; color:#fff;">${c.name}</div>
        <small style="color:var(--text-muted);">${c.email} • ${c.phone || 'N/A'}</small>
      </td>
      <td>${c.city || 'Việt Nam'}</td>
      <td>
        <span class="badge-tag ${c.segment === 'VIP' ? 'badge-warning' : c.segment === 'At-Risk' ? 'badge-danger' : 'badge-success'}">
          ${c.segment}
        </span>
      </td>
      <td style="font-weight:700; text-align:center;">${c.orders_count} đơn</td>
      <td style="font-weight:700; color:var(--accent-emerald);">${formatVND(c.total_spent)}</td>
    </tr>
  `).join('');
}
