/**
 * ==============================================================================
 * LOGIC PHÂN KHÚC KHÁCH HÀNG RFM (CUSTOMER RFM JS)
 * CỤ THỂ HÓA TỪNG KHÁCH HÀNG THEO PHÂN KHÚC & CHIẾN LƯỢC HÀNH ĐỘNG
 * ==============================================================================
 */
let allCustomers = [];
let allSegments = [];
let activeSegment = 'All';
const segmentConfig = {
  'VIP': {
    color: '#d97706', // amber
    border: '#d97706',
    bg: '#fffbeb',
    badgeClass: 'badge-admin',
    icon: 'fa-crown',
    title: 'Phân Khúc VIP (Khách Hàng Đặc Quyền)',
    desc: 'Khách hàng chi tiêu cao nhất, tần suất mua đều đặn',
    goal: 'Mục tiêu: Duy trì sự hài lòng tuyệt đối và chăm sóc đặc quyền 1-1',
    strategy: '👑 <b>Chiến lược VIP:</b> Nhóm khách này đóng góp tới 30-50% tổng doanh thu của doanh nghiệp. Cần cử nhân viên chăm sóc riêng, gọi điện chúc mừng ngày sinh nhật/dịp lễ, gửi quà tri ân đặc quyền và ưu tiên xử lý mọi thắc mắc ngay lập tức để không bao giờ để mất họ sang đối thủ!',
    actionText: 'Tặng Quà VIP',
    actionToast: 'Đã tạo mã quà tặng đặc quyền VIP gửi tới'
  },
  'Loyal': {
    color: '#16a34a', // emerald
    border: '#16a34a',
    bg: '#f0fdf4',
    badgeClass: 'badge-chat',
    icon: 'fa-heart',
    title: 'Phân Khúc Trung Thành (Loyal)',
    desc: 'Khách hàng trung thành, gắn bó lâu năm',
    goal: 'Mục tiêu: Tối ưu giá trị trọn đời (LTV) và bán thêm sản phẩm mới (Cross-sell)',
    strategy: '💚 <b>Chiến lược Trung Thành:</b> Khách hàng có độ tin tưởng thương hiệu rất cao. Hãy áp dụng cơ chế tích điểm nâng hạng hội viên, gửi trải nghiệm trước các sản phẩm mới và tặng voucher độc quyền khi họ giới thiệu thêm khách hàng mới.',
    actionText: 'Tặng Điểm Thưởng',
    actionToast: 'Đã cộng điểm thưởng hội viên thân thiết cho'
  },
  'Potential': {
    color: '#0284c7', // cyan
    border: '#0284c7',
    bg: '#f0f9ff',
    badgeClass: 'badge-dss',
    icon: 'fa-arrow-trend-up',
    title: 'Phân Khúc Tiềm Năng (Potential)',
    desc: 'Khách hàng tiềm năng, cần tiếp thị thêm',
    goal: 'Mục tiêu: Thúc đẩy tần suất mua hàng để chuyển hóa thành khách Trung Thành',
    strategy: '📈 <b>Chiến lược Tiềm Năng:</b> Khách hàng có năng lực tài chính tốt nhưng chu kỳ mua hàng còn ngắt quãng. Hãy gửi các gợi ý Combo tiết kiệm, gợi ý sản phẩm phù hợp sở thích kèm thông báo Flash Sale có giới hạn thời gian để kích cầu mua sắm.',
    actionText: 'Gợi Ý Combo',
    actionToast: 'Đã gửi danh mục Combo ưu đãi tới'
  },
  'At-Risk': {
    color: '#dc2626', // rose
    border: '#dc2626',
    bg: '#fef2f2',
    badgeClass: 'badge-status cancelled',
    icon: 'fa-triangle-exclamation',
    title: 'Phân Khúc Nguy Cơ Rời Bỏ (At-Risk)',
    desc: 'Đã rất lâu chưa quay lại, nguy cơ rời bỏ cao',
    goal: 'Mục tiêu: CỨU VỚT KHÁCH HÀNG NGAY TRƯỚC KHI MẤT HẲN VÀO TAY ĐỐI THỦ',
    strategy: '🚨 <b>Chiến lược Cứu Vớt Khách Hàng (Win-back Strategy):</b> Đây là nhóm khách hàng đã từng chi tiêu rất nhiều tiền nhưng đã rất lâu (hơn 60-90 ngày) không phát sinh đơn mới. CẦN GỌI ĐIỆN HỎI THĂM TRỰC TIẾP xem họ có gặp vấn đề gì về dịch vụ không, sau đó tặng ngay voucher "Tri Ân Khách Hàng Cũ" giảm 15-20% để kéo họ quay trở lại mua sắm ngay hôm nay!',
    actionText: 'Cứu Vớt / Tặng Mã',
    actionToast: 'Đã kích hoạt chiến dịch giải cứu khách hàng & gửi Voucher 20% cho'
  },
  'New': {
    color: '#2563eb', // blue
    border: '#2563eb',
    bg: '#eff6ff',
    badgeClass: 'badge-dss',
    icon: 'fa-sparkles',
    title: 'Phân Khúc Khách Hàng Mới (New)',
    desc: 'Khách hàng mới phát sinh đơn đầu tiên',
    goal: 'Mục tiêu: Tạo thiện cảm dịch vụ và thúc đẩy phát sinh đơn hàng thứ 2',
    strategy: '✨ <b>Chiến lược Khách Mới:</b> Khách hàng mới có lần trải nghiệm đầu tiên. Hãy gọi điện hoặc nhắn tin hỏi thăm xem họ đã nhận được hàng chưa, hướng dẫn sử dụng chi tiết và tặng mã giảm giá 10% có thời hạn 7 ngày cho đơn hàng kế tiếp để hình thành thói quen mua sắm.',
    actionText: 'Tặng Mã Đơn 2',
    actionToast: 'Đã gửi mã giảm giá 10% cho đơn hàng tiếp theo tới'
  }
};
document.addEventListener('DOMContentLoaded', async () => {
  if (!checkPageRole(['admin', 'manager'])) return;
  try {
    const res = await apiRequest('/api/revenue/rfm');
    if (res.success && res.data) {
      allSegments = res.data.segments || [];
      allCustomers = res.data.customers || res.data.topCustomers || [];
      renderSegmentCards(allSegments);
      applyCustomerFilter();
    }
  } catch (err) {
    showToast('Lỗi khi tải dữ liệu phân khúc: ' + err.message, 'error');
  }
});
function renderSegmentCards(segments) {
  const container = document.getElementById('rfm-cards-grid');
  if (!container) return;
  if (!segments || segments.length === 0) {
    container.innerHTML = `
      <div class="glass-card" style="grid-column: 1 / -1; padding: 28px; text-align: center; color: var(--text-muted); background:#fff; border:1px solid var(--border-card);">
        <i class="fa-solid fa-users" style="font-size: 32px; margin-bottom: 12px; color: var(--accent-primary);"></i>
        <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">Chưa có dữ liệu phân khúc khách hàng</div>
        <div style="font-size: 13px; margin-top: 4px;">Dữ liệu sẽ tự động tính toán khi cửa hàng của bạn phát sinh giao dịch.</div>
      </div>
    `;
    return;
  }
  container.innerHTML = segments.map(s => {
    const cfg = segmentConfig[s.segment] || {
      color: '#2563eb',
      border: '#cbd5e1',
      bg: '#ffffff',
      icon: 'fa-user',
      title: s.segment,
      desc: 'Phân khúc khách hàng'
    };
    const isActive = activeSegment === s.segment;
    const cardBorder = isActive ? `2px solid ${cfg.color}` : '1px solid var(--border-card)';
    const cardShadow = isActive ? `0 4px 14px rgba(0, 0, 0, 0.08), 0 0 0 2px ${cfg.color}33` : 'var(--shadow-sm)';
    const activeBadge = isActive 
      ? `<span style="font-size:10px; background:${cfg.color}; color:#fff; padding:2px 8px; border-radius:10px; font-weight:700;"><i class="fa-solid fa-check"></i> Đang Lọc</span>` 
      : `<span style="font-size:11px; background:#f1f5f9; color:var(--text-secondary); padding:2px 8px; border-radius:10px; font-weight:600;">${s.customer_count} khách</span>`;
    return `
      <div class="kpi-card rfm-segment-card" 
           onclick="toggleSegmentFilter('${s.segment}')"
           style="cursor: pointer; border: ${cardBorder}; box-shadow: ${cardShadow}; transition: all 0.2s ease; position: relative; background: ${isActive ? cfg.bg : '#ffffff'}; padding: 18px 20px;">
        <div style="position: absolute; top:0; left:0; right:0; height:3px; background:${cfg.color}; border-top-left-radius:var(--radius-md); border-top-right-radius:var(--radius-md);"></div>
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <div style="width:32px; height:32px; border-radius:6px; background:${cfg.color}15; display:flex; align-items:center; justify-content:center; color:${cfg.color}; font-size:14px;">
              <i class="fa-solid ${cfg.icon}"></i>
            </div>
            <div>
              <div style="font-size:14px; font-weight:700; color:var(--text-primary);">
                ${s.segment}
              </div>
              <div style="font-size:11px; color:var(--text-muted);">${s.customer_count} khách hàng</div>
            </div>
          </div>
          <div>${activeBadge}</div>
        </div>
        <p style="font-size:12px; color:var(--text-secondary); line-height:1.4; margin-bottom:12px; min-height:34px;">
          ${cfg.desc}
        </p>
        <div style="font-size:20px; font-weight:800; color:${cfg.color}; margin-bottom:2px; letter-spacing:-0.02em;">
          ${formatVND(s.total_revenue)}
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px; color:var(--text-muted); padding-top:6px; border-top:1px dashed var(--border-card);">
          <span>TB/khách: <b>${formatVND(s.avg_spent)}</b></span>
          <span style="color:${cfg.color}; font-weight:600;"><i class="fa-solid fa-arrow-pointer"></i> ${isActive ? 'Hủy chọn' : 'Bấm để lọc'}</span>
        </div>
      </div>
    `;
  }).join('');
}
function toggleSegmentFilter(segmentName) {
  if (activeSegment === segmentName) {
    activeSegment = 'All';
  } else {
    activeSegment = segmentName;
  }
  renderSegmentCards(allSegments);
  applyCustomerFilter();
}
function applyCustomerFilter() {
  const filteredCustomers = (activeSegment === 'All') 
    ? allCustomers 
    : allCustomers.filter(c => c.segment === activeSegment);
  const headline = document.getElementById('table-headline');
  const subline = document.getElementById('table-subline');
  const countBadge = document.getElementById('table-count-badge');
  const strategyBanner = document.getElementById('segment-strategy-banner');
  const btnShowAll = document.getElementById('btn-show-all');
  if (activeSegment === 'All') {
    if (headline) headline.innerHTML = `<i class="fa-solid fa-users" style="color:var(--accent-primary);"></i> Danh Sách Toàn Bộ Khách Hàng (Tất Cả Phân Khúc)`;
    if (subline) subline.textContent = `Hiển thị danh sách ${allCustomers.length} khách hàng trong hệ thống. Bấm vào bất kỳ thẻ phân khúc bên trên để lọc và hành động cụ thể.`;
    if (countBadge) {
      countBadge.className = 'badge-tag badge-dss';
      countBadge.style.background = '';
      countBadge.style.color = '';
      countBadge.style.border = '';
      countBadge.textContent = `${filteredCustomers.length} Khách Hàng`;
    }
    if (strategyBanner) strategyBanner.style.display = 'none';
    if (btnShowAll) btnShowAll.style.display = 'none';
  } else {
    const cfg = segmentConfig[activeSegment] || {};
    if (headline) headline.innerHTML = `<i class="fa-solid ${cfg.icon || 'fa-users'}" style="color:${cfg.color || 'var(--accent-primary)'};"></i> ${cfg.title || 'Phân khúc ' + activeSegment}`;
    if (subline) subline.textContent = `Danh sách ${filteredCustomers.length} khách hàng cụ thể thuộc nhóm ${activeSegment}. Hãy sử dụng thông tin liên hệ và hành động CSKH bên dưới để gia tăng doanh thu.`;
    if (countBadge) {
      countBadge.className = `badge-tag`;
      countBadge.style.background = cfg.bg;
      countBadge.style.color = cfg.color;
      countBadge.style.border = `1px solid ${cfg.color}40`;
      countBadge.textContent = `${filteredCustomers.length} Khách Thuộc Nhóm ${activeSegment}`;
    }
    if (btnShowAll) {
      btnShowAll.style.display = 'inline-flex';
      btnShowAll.innerHTML = `<i class="fa-solid fa-rotate-left"></i> Xem Tất Cả (${allCustomers.length} khách)`;
    }
    if (strategyBanner) {
      strategyBanner.style.display = 'block';
      strategyBanner.style.borderLeftColor = cfg.color;
      strategyBanner.innerHTML = `
        <div style="display:flex; align-items:flex-start; gap:14px;">
          <div style="font-size:24px; color:${cfg.color}; line-height:1; margin-top:2px;">
            <i class="fa-solid ${cfg.icon}"></i>
          </div>
          <div style="flex:1;">
            <div style="font-size:14.5px; font-weight:700; color:var(--text-primary); margin-bottom:4px;">
              ${cfg.goal}
            </div>
            <div style="font-size:13px; color:var(--text-secondary); line-height:1.5;">
              ${cfg.strategy}
            </div>
          </div>
        </div>
      `;
    }
  }
  renderCustomersTable(filteredCustomers);
}
function renderCustomersTable(customers) {
  const tbody = document.getElementById('top-customers-tbody');
  if (!tbody) return;
  if (!customers || customers.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align:center; padding:36px; color:var(--text-muted);">
          <i class="fa-solid fa-user-slash" style="font-size:28px; display:block; margin-bottom:10px; color:#cbd5e1;"></i>
          Không tìm thấy khách hàng nào trong phân khúc này.
        </td>
      </tr>
    `;
    return;
  }
  tbody.innerHTML = customers.map((c, idx) => {
    const cfg = segmentConfig[c.segment] || { color: '#2563eb', badgeClass: 'badge-dss', actionText: 'Chăm Sóc' };
    const lastDate = c.last_order_date || 'Chưa có đơn';
    return `
      <tr>
        <td style="font-weight:700; color:var(--text-secondary); text-align:center;">#${idx + 1}</td>
        <td>
          <div style="font-weight:700; color:var(--text-primary); font-size:13.5px;">${c.name}</div>
          <div style="font-size:12px; color:var(--text-muted); margin-top:2px; display:flex; align-items:center; gap:8px;">
            <span><i class="fa-solid fa-phone" style="font-size:10px; color:var(--accent-primary);"></i> ${c.phone || 'N/A'}</span>
            <span>•</span>
            <span><i class="fa-solid fa-envelope" style="font-size:10px;"></i> ${c.email || 'N/A'}</span>
          </div>
        </td>
        <td>
          <span style="font-weight:500; color:var(--text-secondary);"><i class="fa-solid fa-location-dot" style="font-size:11px; color:#94a3b8; margin-right:4px;"></i>${c.city || 'Toàn quốc'}</span>
        </td>
        <td>
          <span class="badge-tag" style="background:${cfg.color}15; color:${cfg.color}; border:1px solid ${cfg.color}40; font-weight:700; font-size:11px; padding:3px 9px;">
            <i class="fa-solid ${cfg.icon}" style="margin-right:4px;"></i>${c.segment}
          </span>
        </td>
        <td>
          <div style="font-weight:600; color:var(--text-primary); font-size:12.5px;">
            <i class="fa-regular fa-calendar-days" style="color:#94a3b8; margin-right:4px;"></i>${lastDate}
          </div>
        </td>
        <td style="font-weight:700; text-align:center; color:var(--text-primary); font-size:13px;">
          ${c.orders_count} đơn
        </td>
        <td style="font-weight:800; color:var(--accent-emerald); font-size:14px;">
          ${formatVND(c.total_spent)}
        </td>
        <td style="text-align:center;">
          <div style="display:inline-flex; gap:6px;">
            <button class="btn btn-secondary" style="padding:4px 9px; font-size:11.5px; border-radius:6px;" 
                    onclick="actionCallCustomer('${c.name}', '${c.phone}')" title="Sao chép SĐT gọi CSKH">
              <i class="fa-solid fa-phone" style="color:var(--accent-primary);"></i> Gọi
            </button>
            <button class="btn btn-secondary" style="padding:4px 9px; font-size:11.5px; border-radius:6px;" 
                    onclick="actionSendOffer('${c.name}', '${c.segment}')" title="Gửi mã ưu đãi / voucher">
              <i class="fa-solid fa-gift" style="color:${cfg.color};"></i> ${cfg.actionText}
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}
function actionCallCustomer(name, phone) {
  if (!phone || phone === 'N/A') {
    showToast(`Khách hàng ${name} chưa có số điện thoại!`, 'warning');
    return;
  }
  if (navigator.clipboard) {
    navigator.clipboard.writeText(phone);
  }
  showToast(`Đã sao chép SĐT ${phone} (${name}) để CSKH gọi điện hỗ trợ!`, 'success');
}
function actionSendOffer(name, segment) {
  const cfg = segmentConfig[segment] || {};
  const msg = cfg.actionToast || 'Đã gửi ưu đãi thành công cho';
  showToast(`${msg} ${name} (${segment})!`, 'success');
}
