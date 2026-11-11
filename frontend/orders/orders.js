/**
 * ==============================================================================
 * LOGIC QUẢN LÝ ĐƠN HÀNG ĐA KÊNH (ORDERS JS)
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;

  const user = getUser();
  const role = (user && user.role ? user.role : 'user').toLowerCase();
  if (role === 'user') {
    const pageTitle = document.querySelector('.page-title h1');
    if (pageTitle) pageTitle.textContent = 'Lịch Sử & Danh Sách Đơn Hàng';
    const pageSub = document.querySelector('.page-title p');
    if (pageSub) pageSub.textContent = 'Danh sách đơn hàng và trạng thái giao dịch cá nhân của bạn';
    const aiBtn = document.getElementById('btn-orders-ai');
    if (aiBtn) aiBtn.innerHTML = '<i class="fa-solid fa-comments"></i> AI Tư Vấn Mua Hàng';
  }

  await loadOrders();

  if (['admin', 'manager'].includes(role)) {
    document.getElementById('order-profit-section').style.display = 'block';
    document.getElementById('profit-cost-form').addEventListener('submit', saveProfitCost);
    await loadOrderProfit(true);
  }

  const channelFilter = document.getElementById('filter-channel');
  const statusFilter = document.getElementById('filter-status');

  if (channelFilter) {
    channelFilter.addEventListener('change', () => { loadOrders(); if (['admin', 'manager'].includes(role)) loadOrderProfit(true); });
  }
  if (statusFilter) {
    statusFilter.addEventListener('change', () => { loadOrders(); if (['admin', 'manager'].includes(role)) loadOrderProfit(true); });
  }

  // Bắt sự kiện submit form tạo đơn hàng
  const form = document.getElementById('create-order-form');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      await handleCreateOrderSubmit();
    });
  }
});

async function loadOrders() {
  const channel = document.getElementById('filter-channel') ? document.getElementById('filter-channel').value : 'All';
  const status = document.getElementById('filter-status') ? document.getElementById('filter-status').value : 'All';
  const tbody = document.getElementById('orders-tbody');
  const countBadge = document.getElementById('orders-count-badge');

  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:24px; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải dữ liệu đơn hàng từ SQL Server...</td></tr>';
  }

  try {
    const res = await apiRequest(`/api/revenue/orders?limit=100&channel=${encodeURIComponent(channel)}&status=${encodeURIComponent(status)}`);
    if (res.success && res.data) {
      if (countBadge) countBadge.textContent = `${res.data.length} Đơn Hàng`;
      renderOrdersTable(res.data);
    }
  } catch (err) {
    showToast('Lỗi khi tải danh sách đơn hàng: ' + err.message, 'error');
  }
}

function renderOrdersTable(orders) {
  const tbody = document.getElementById('orders-tbody');
  if (!tbody) return;

  if (orders.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:30px; color:var(--text-muted);">Không tìm thấy đơn hàng nào phù hợp với bộ lọc.</td></tr>';
    return;
  }

  const statusMap = {
    'completed': { label: 'Hoàn thành', class: 'badge-success' },
    'shipping': { label: 'Đang giao', class: 'badge-warning' },
    'processing': { label: 'Đang xử lý', class: 'badge-tag' },
    'cancelled': { label: 'Đã hủy', class: 'badge-danger' },
    'refunded': { label: 'Hoàn tiền', class: 'badge-danger' }
  };

  const channelMap = {
    'Shopee': { color: '#ee4d2d', icon: 'fa-bag-shopping' },
    'TikTok Shop': { color: '#fe2c55', icon: 'fa-video' },
    'Cửa hàng trực tiếp': { color: '#10b981', icon: 'fa-store' },
    'Website': { color: '#3b82f6', icon: 'fa-globe' }
  };

  tbody.innerHTML = orders.map(o => {
    const st = statusMap[o.status] || { label: o.status, class: 'badge-tag' };
    const ch = channelMap[o.channel] || { color: '#2563eb', icon: 'fa-cart-shopping' };
    const prodDesc = o.product_summary || 'Sản phẩm đặt hàng';

    return `
      <tr>
        <td style="font-weight:700; color:var(--accent-primary); font-family:monospace; font-size:13.5px; white-space:nowrap;">
          ${o.order_code}
        </td>
        <td style="max-width:280px;">
          <div style="font-weight:600; color:#0f172a; font-size:13px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;" title="${prodDesc}">
            <i class="fa-solid fa-box-open" style="color:#2563eb; margin-right:6px; font-size:12px;"></i>
            <span>${prodDesc}</span>
          </div>
        </td>
        <td>
          <div style="font-weight:600; color:var(--text-primary); font-size:13px;">${o.customer_name || 'Khách vãng lai'}</div>
          <small style="color:var(--text-muted); font-size:11px;">${o.customer_phone || ''}</small>
        </td>
        <td>
          <span style="display:inline-flex; align-items:center; gap:6px; color:${ch.color}; font-weight:600; font-size:12.5px;">
            <i class="fa-solid ${ch.icon}"></i> ${o.channel}
          </span>
        </td>
        <td style="color:var(--text-muted); font-size:12px;">
          ${o.payment_method || 'COD'}
        </td>
        <td style="color:var(--text-secondary); font-size:12px; white-space:nowrap;">
          ${o.order_date || 'N/A'}
        </td>
        <td>
          <span class="badge-tag ${st.class}">${st.label}</span>
        </td>
        <td style="font-weight:700; color:#16a34a; text-align:right; font-family:var(--font-mono); font-size:14px; white-space:nowrap;">
          ${formatVND(o.net_amount)}
        </td>
      </tr>
    `;
  }).join('');
}

let orderProfitOffset = 0;
let currentProfitOrderId = null;
let editingProfitCostId = null;
let currentProfitCosts = [];

function escapeProfitText(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}

async function loadOrderProfit(reset = false) {
  if (reset) orderProfitOffset = 0;
  const params = new URLSearchParams({
    limit: '50', offset: String(orderProfitOffset),
    channel: document.getElementById('filter-channel')?.value || 'All',
    order_status: document.getElementById('filter-status')?.value || 'All',
    fee_status: document.getElementById('profit-fee-status').value,
    profit_filter: document.getElementById('profit-margin-filter').value
  });
  const fromDate = document.getElementById('profit-from-date').value;
  const toDate = document.getElementById('profit-to-date').value;
  if (fromDate) params.set('from_date', fromDate);
  if (toDate) params.set('to_date', toDate);
  try {
    const res = await apiRequest(`/api/financial/order-profit?${params}`);
    const tbody = document.getElementById('order-profit-tbody');
    if (reset) tbody.innerHTML = '';
    const feeLabels = {unverified:'Chưa đối soát', entered:'Đã nhập phí', reconciled:'Đã đối soát'};
    const rows = res.data.map(order => `<tr>
      <td>${escapeProfitText(order.order_code)}</td><td>${escapeProfitText(order.channel)}</td><td>${escapeProfitText(order.order_date)}</td>
      <td>${feeLabels[order.fee_status] || 'Chưa đối soát'}</td>
      <td style="text-align:right;">${formatVND(order.revenue)}</td><td style="text-align:right;">${formatVND(order.cogs)}</td><td style="text-align:right;">${formatVND(order.direct_costs)}</td>
      <td style="text-align:right;font-weight:700;color:${order.contribution_profit < 0 ? '#dc2626' : '#15803d'}">${order.contribution_profit === null ? '—' : `${formatVND(order.contribution_profit)} (${order.margin_pct}%)`}</td>
      <td><button type="button" onclick="openProfitDetail(${order.id})">Chi tiết</button></td></tr>`).join('');
    if (reset) tbody.innerHTML = rows || '<tr><td colspan="9" style="text-align:center;padding:20px;">Không có đơn phù hợp.</td></tr>';
    else tbody.insertAdjacentHTML('beforeend', rows);
    orderProfitOffset += res.data.length;
    document.getElementById('order-profit-more').style.display = res.data.length === 50 ? 'inline-flex' : 'none';
  } catch (err) {
    showToast('Không tải được phân tích lợi nhuận đơn: ' + err.message, 'error');
  }
}

async function openProfitDetail(orderId) {
  try {
    const res = await apiRequest(`/api/financial/orders/${orderId}/profit`);
    const order = res.data;
    currentProfitOrderId = orderId;
    currentProfitCosts = order.costs || [];
    const costTypeLabels = {marketplace_fee:'Phí sàn', payment_fee:'Phí thanh toán', shipping_cost:'Vận chuyển shop chịu', packaging:'Đóng gói', order_ads:'Quảng cáo theo đơn', other:'Chi phí khác'};
    const costs = currentProfitCosts.map(cost => `<tr><td>${costTypeLabels[cost.cost_type] || escapeProfitText(cost.cost_type)}</td><td>${formatVND(cost.amount)}</td><td>${escapeProfitText(cost.note)}</td><td><button type="button" onclick="editProfitCost(${cost.id})">Sửa</button></td></tr>`).join('');
    const items = order.items.map(item => `<tr><td>${escapeProfitText(item.product_name || 'Sản phẩm')}</td><td>${item.quantity}</td><td>${formatVND(item.unit_price)}</td><td>${formatVND(item.cost_price * item.quantity)}</td></tr>`).join('');
    document.getElementById('profit-detail-content').innerHTML = `
      <h3>${escapeProfitText(order.order_code)} · ${escapeProfitText(order.channel)}</h3>
      <div style="overflow-x:auto"><table class="custom-table"><thead><tr><th>Sản phẩm</th><th>SL</th><th>Giá bán</th><th>Giá vốn</th></tr></thead><tbody>${items || '<tr><td colspan="4">Không có dòng hàng</td></tr>'}</tbody></table></div>
      <div style="overflow-x:auto;margin-top:12px"><table class="custom-table"><thead><tr><th>Khoản phí</th><th>Số tiền</th><th>Ghi chú</th><th></th></tr></thead><tbody>${costs || '<tr><td colspan="4">Chưa nhập khoản phí nào.</td></tr>'}</tbody></table></div>
      <p><strong>Doanh thu thuần:</strong> ${formatVND(order.revenue)} · <strong>Giá vốn:</strong> ${formatVND(order.cogs)} · <strong>Phí trực tiếp:</strong> ${formatVND(order.direct_costs)}</p>
      <p><strong>Lợi nhuận đóng góp:</strong> ${order.contribution_profit === null ? 'Chỉ tính cho đơn hoàn thành' : formatVND(order.contribution_profit)} ${order.margin_pct === null ? '' : `(${order.margin_pct}%)`}</p>`;
    document.getElementById('profit-fee-status-edit').value = order.fee_status;
    resetProfitCostForm();
    document.getElementById('order-profit-modal').showModal();
  } catch (err) { showToast('Không tải được chi tiết lợi nhuận: ' + err.message, 'error'); }
}

function closeProfitDetail() {
  document.getElementById('order-profit-modal').close();
  currentProfitOrderId = null;
  resetProfitCostForm();
}

function editProfitCost(costId) {
  const cost = currentProfitCosts.find(item => item.id === costId);
  if (!cost) return;
  editingProfitCostId = costId;
  document.getElementById('profit-cost-type').value = cost.cost_type;
  document.getElementById('profit-cost-amount').value = cost.amount;
  document.getElementById('profit-cost-note').value = cost.note || '';
  document.getElementById('profit-cost-submit').textContent = 'Lưu khoản phí';
  document.getElementById('profit-cost-cancel-edit').style.display = 'inline-flex';
}

function resetProfitCostForm() {
  editingProfitCostId = null;
  document.getElementById('profit-cost-form')?.reset();
  const button = document.getElementById('profit-cost-submit');
  if (button) button.textContent = 'Thêm khoản phí';
  const cancel = document.getElementById('profit-cost-cancel-edit');
  if (cancel) cancel.style.display = 'none';
}

async function saveProfitCost(event) {
  event.preventDefault();
  const payload = {cost_type:document.getElementById('profit-cost-type').value, amount:Number(document.getElementById('profit-cost-amount').value), note:document.getElementById('profit-cost-note').value};
  const endpoint = editingProfitCostId ? `/api/financial/order-costs/${editingProfitCostId}` : `/api/financial/orders/${currentProfitOrderId}/costs`;
  try {
    await apiRequest(endpoint, {method:editingProfitCostId ? 'PUT' : 'POST', body:JSON.stringify(payload)});
    showToast(editingProfitCostId ? 'Đã cập nhật khoản phí.' : 'Đã thêm khoản phí.', 'success');
    resetProfitCostForm();
    await openProfitDetail(currentProfitOrderId);
    await loadOrderProfit(true);
  } catch (err) { showToast('Không lưu được khoản phí: ' + err.message, 'error'); }
}

async function saveProfitFeeStatus() {
  if (!currentProfitOrderId) return;
  try {
    await apiRequest(`/api/financial/orders/${currentProfitOrderId}/fee-status`, {method:'PUT', body:JSON.stringify({status:document.getElementById('profit-fee-status-edit').value})});
    showToast('Đã cập nhật trạng thái đối soát.', 'success');
    await openProfitDetail(currentProfitOrderId);
    await loadOrderProfit(true);
  } catch (err) { showToast('Không cập nhật được trạng thái: ' + err.message, 'error'); }
}

/* ==============================================================================
   MODAL TẠO ĐƠN HÀNG MỚI (TỰ NHẬP TINH GỌN, TRỰC TIẾP)
   ============================================================================== */

function openCreateOrderModal() {
  const modal = document.getElementById('create-order-modal');
  const nameInput = document.getElementById('modal-order-product-name');
  const priceInput = document.getElementById('modal-order-price');
  const qtyInput = document.getElementById('modal-order-qty');
  const totalPreview = document.getElementById('modal-order-total-preview');

  if (!modal) return;

  // Reset form sạch sẽ để user tự nhập
  if (nameInput) nameInput.value = '';
  if (priceInput) priceInput.value = '';
  if (qtyInput) qtyInput.value = '1';
  if (totalPreview) totalPreview.textContent = '0 ₫';

  modal.style.display = 'flex';
  if (nameInput) nameInput.focus();
}

function closeCreateOrderModal() {
  const modal = document.getElementById('create-order-modal');
  if (modal) modal.style.display = 'none';
}

function updateModalProductPrice() {
  const priceInput = document.getElementById('modal-order-price');
  const qtyInput = document.getElementById('modal-order-qty');
  const totalPreview = document.getElementById('modal-order-total-preview');
  if (!priceInput || !qtyInput || !totalPreview) return;

  const price = parseFloat(priceInput.value) || 0;
  const qty = parseInt(qtyInput.value) || 1;
  totalPreview.textContent = formatVND(price * qty);
}

async function handleCreateOrderSubmit() {
  const channel = document.getElementById('modal-order-channel').value;
  const productName = (document.getElementById('modal-order-product-name').value || '').trim();
  const unitPrice = parseFloat(document.getElementById('modal-order-price').value) || 0;
  const quantity = parseInt(document.getElementById('modal-order-qty').value) || 1;
  const paymentMethod = document.getElementById('modal-order-payment').value;

  if (!productName) {
    showToast('Vui lòng nhập tên sản phẩm / món hàng!', 'error');
    return;
  }

  if (unitPrice <= 0) {
    showToast('Vui lòng nhập đơn giá bán hợp lệ (> 0 VNĐ)!', 'error');
    return;
  }

  try {
    const payload = {
      channel,
      customerId: 1,
      paymentMethod,
      items: [{
        productName: productName,
        unitPrice: unitPrice,
        quantity: quantity
      }]
    };

    const res = await apiRequest('/api/revenue/orders', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res.success) {
      showToast(res.message, 'success');
      closeCreateOrderModal();
      await loadOrders();
    }
  } catch (err) {
    showToast('Lỗi khi tạo đơn hàng: ' + err.message, 'error');
  }
}
