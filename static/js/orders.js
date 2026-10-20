/**
 * ==============================================================================
 * LOGIC QUẢN LÝ ĐƠN HÀNG ĐA KÊNH (ORDERS JS)
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;

  await loadOrders();

  const channelFilter = document.getElementById('filter-channel');
  const statusFilter = document.getElementById('filter-status');

  if (channelFilter) {
    channelFilter.addEventListener('change', loadOrders);
  }
  if (statusFilter) {
    statusFilter.addEventListener('change', loadOrders);
  }
});

async function loadOrders() {
  const channel = document.getElementById('filter-channel') ? document.getElementById('filter-channel').value : 'All';
  const status = document.getElementById('filter-status') ? document.getElementById('filter-status').value : 'All';
  const tbody = document.getElementById('orders-tbody');
  const countBadge = document.getElementById('orders-count-badge');

  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải dữ liệu đơn hàng từ SQL Server...</td></tr>';
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
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">Không tìm thấy đơn hàng nào phù hợp với bộ lọc.</td></tr>';
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
    const ch = channelMap[o.channel] || { color: '#6366f1', icon: 'fa-cart-shopping' };

    return `
      <tr>
        <td style="font-weight:700; color:var(--accent-cyan); font-family:monospace; font-size:14px;">
          ${o.order_code}
        </td>
        <td>
          <div style="font-weight:600; color:#fff;">${o.customer_name || 'Khách vãng lai'}</div>
          <small style="color:var(--text-muted);">${o.customer_phone || ''}</small>
        </td>
        <td>
          <span style="display:inline-flex; align-items:center; gap:6px; color:${ch.color}; font-weight:600; font-size:13px;">
            <i class="fa-solid ${ch.icon}"></i> ${o.channel}
          </span>
        </td>
        <td style="color:var(--text-muted); font-size:12px;">
          ${o.payment_method || 'COD'}
        </td>
        <td style="color:var(--text-secondary); font-size:12px;">
          ${o.order_date || 'N/A'}
        </td>
        <td>
          <span class="badge-tag ${st.class}">${st.label}</span>
        </td>
        <td style="font-weight:700; color:var(--accent-emerald); text-align:right;">
          ${formatVND(o.net_amount)}
        </td>
      </tr>
    `;
  }).join('');
}

let availableProducts = [];

async function openCreateOrderModal() {
  const modal = document.getElementById('create-order-modal');
  const prodSelect = document.getElementById('modal-order-product');
  if (!modal) return;

  try {
    if (availableProducts.length === 0) {
      const res = await apiRequest('/api/products/');
      if (res.success && res.data) {
        availableProducts = res.data;
      }
    }

    if (prodSelect) {
      prodSelect.innerHTML = availableProducts.map(p => `
        <option value="${p.id}" data-price="${p.selling_price}">
          ${p.name} - ${formatVND(p.selling_price)} (Còn: ${p.stock_quantity})
        </option>
      `).join('');
    }

    modal.style.display = 'flex';
    updateModalProductPrice();
  } catch (err) {
    showToast('Lỗi khi tải danh sách sản phẩm: ' + err.message, 'error');
  }
}

function closeCreateOrderModal() {
  const modal = document.getElementById('create-order-modal');
  if (modal) modal.style.display = 'none';
}

function updateModalProductPrice() {
  const prodSelect = document.getElementById('modal-order-product');
  const qtyInput = document.getElementById('modal-order-qty');
  const totalPreview = document.getElementById('modal-order-total-preview');
  if (!prodSelect || !qtyInput || !totalPreview) return;

  const selectedOpt = prodSelect.options[prodSelect.selectedIndex];
  if (!selectedOpt) return;

  const price = parseFloat(selectedOpt.getAttribute('data-price') || 0);
  const qty = parseInt(qtyInput.value) || 1;
  totalPreview.textContent = formatVND(price * qty);
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('create-order-form');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const channel = document.getElementById('modal-order-channel').value;
      const productId = parseInt(document.getElementById('modal-order-product').value);
      const quantity = parseInt(document.getElementById('modal-order-qty').value) || 1;
      const paymentMethod = document.getElementById('modal-order-payment').value;

      try {
        const res = await apiRequest('/api/revenue/orders', {
          method: 'POST',
          body: JSON.stringify({
            channel,
            customerId: 1,
            paymentMethod,
            items: [{ productId, quantity }]
          })
        });

        if (res.success) {
          showToast(res.message, 'success');
          closeCreateOrderModal();
          await loadOrders();
        }
      } catch (err) {
        showToast('Lỗi khi tạo đơn hàng: ' + err.message, 'error');
      }
    });
  }
});
