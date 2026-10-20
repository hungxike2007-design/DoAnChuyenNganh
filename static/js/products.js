/**
 * ==============================================================================
 * LOGIC QUẢN LÝ SẢN PHẨM & TỒN KHO (PRODUCTS JS)
 * ==============================================================================
 */

let allProducts = [];

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;

  const user = getUser();
  const role = (user && user.role ? user.role : 'user').toLowerCase();
  const isStaff = (role === 'sales' || role === 'user');

  // Nếu là Staff (User / Sales), ẩn hoàn toàn các quyền thêm sản phẩm và cột chi phí vốn
  if (isStaff) {
    const addBtn = document.getElementById('btn-add-product');
    if (addBtn) addBtn.style.display = 'none';

    const invCard = document.getElementById('kpi-inventory-value-card');
    if (invCard) invCard.style.display = 'none';

    document.querySelectorAll('.cost-col').forEach(el => el.style.display = 'none');
  }

  await loadCategories();
  await loadProducts();

  const searchInput = document.getElementById('search-product');
  const catFilter = document.getElementById('filter-category');

  if (searchInput) {
    searchInput.addEventListener('input', filterAndRenderProducts);
  }
  if (catFilter) {
    catFilter.addEventListener('change', filterAndRenderProducts);
  }

  // Xử lý Form Thêm sản phẩm mới
  const addForm = document.getElementById('add-product-form');
  if (addForm) {
    addForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      await handleAddProduct();
    });
  }
});

async function loadCategories() {
  const catSelect = document.getElementById('filter-category');
  const modalCatSelect = document.getElementById('modal-category');

  try {
    const res = await apiRequest('/api/products/categories');
    if (res.success && res.data) {
      const optionsHtml = res.data.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
      
      if (catSelect) {
        catSelect.innerHTML = '<option value="All">Tất cả danh mục</option>' + optionsHtml;
      }
      if (modalCatSelect) {
        modalCatSelect.innerHTML = optionsHtml;
      }
    }
  } catch (err) {
    console.error('Lỗi tải danh mục:', err);
  }
}

async function loadProducts() {
  const tbody = document.getElementById('products-tbody');
  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải dữ liệu sản phẩm từ SQL Server...</td></tr>';
  }

  try {
    const res = await apiRequest('/api/products/');
    if (res.success && res.data) {
      allProducts = res.data;
      updateProductSummaryCards(allProducts);
      filterAndRenderProducts();
    }
  } catch (err) {
    showToast('Lỗi khi tải sản phẩm: ' + err.message, 'error');
  }
}

function updateProductSummaryCards(products) {
  const totalCountEl = document.getElementById('summary-total-products');
  const totalStockEl = document.getElementById('summary-total-stock');
  const inventoryValueEl = document.getElementById('summary-inventory-value');

  if (totalCountEl) totalCountEl.textContent = `${products.length} Mặt Hàng`;
  
  const totalUnits = products.reduce((acc, p) => acc + (p.stock_quantity || 0), 0);
  if (totalStockEl) totalStockEl.textContent = `${totalUnits.toLocaleString('vi-VN')} Cái`;

  const totalValue = products.reduce((acc, p) => acc + ((p.cost_price || 0) * (p.stock_quantity || 0)), 0);
  if (inventoryValueEl) inventoryValueEl.textContent = formatVND(totalValue);
}

function filterAndRenderProducts() {
  const keyword = (document.getElementById('search-product')?.value || '').toLowerCase().trim();
  const catId = document.getElementById('filter-category')?.value || 'All';

  let filtered = allProducts.filter(p => {
    const matchName = p.name.toLowerCase().includes(keyword) || p.sku.toLowerCase().includes(keyword);
    const matchCat = catId === 'All' || p.category_id == catId;
    return matchName && matchCat;
  });

  renderProductsTable(filtered);
}

function renderProductsTable(products) {
  const tbody = document.getElementById('products-tbody');
  if (!tbody) return;

  const user = getUser();
  const role = (user && user.role ? user.role : 'user').toLowerCase();
  const isStaff = (role === 'sales' || role === 'user');

  if (products.length === 0) {
    tbody.innerHTML = `<tr><td colspan="${isStaff ? 5 : 7}" style="text-align:center; padding:30px; color:var(--text-muted);">Không tìm thấy sản phẩm nào phù hợp.</td></tr>`;
    return;
  }

  tbody.innerHTML = products.map(p => {
    const isLowStock = p.stock_quantity <= 40;

    if (isStaff) {
      // Giao diện Nhân Viên / User: CHỈ THẤY GIÁ BÁN NIÊM YẾT VÀ TỒN KHO (Giá vốn & Biên lãi được bảo mật)
      return `
        <tr>
          <td style="font-weight:700; color:var(--accent-cyan); font-family:monospace;">
            ${p.sku}
          </td>
          <td>
            <div style="font-weight:600; color:#fff;">${p.name}</div>
            <small style="color:var(--text-muted);">${p.category_name || 'Khác'}</small>
          </td>
          <td style="font-weight:600; color:#fff;">${formatVND(p.selling_price)}</td>
          <td>
            <span class="badge-tag ${isLowStock ? 'badge-warning' : 'badge-success'}">
              ${p.stock_quantity} tồn kho
            </span>
          </td>
          <td>
            <a href="/static/ai-copilot.html" class="link-highlight" style="font-size:12px;">
              <i class="fa-solid fa-comments" style="color:var(--accent-cyan); margin-right:4px;"></i> Tư vấn bán hàng
            </a>
          </td>
        </tr>
      `;
    }

    // Giao diện Admin / Manager: Thấy toàn bộ Giá vốn (COGS) & Biên lợi nhuận
    const margin = p.selling_price > 0 ? (((p.selling_price - p.cost_price) / p.selling_price) * 100).toFixed(1) : 0;
    return `
      <tr>
        <td style="font-weight:700; color:var(--accent-cyan); font-family:monospace;">
          ${p.sku}
        </td>
        <td>
          <div style="font-weight:600; color:#fff;">${p.name}</div>
          <small style="color:var(--text-muted);">${p.category_name || 'Khác'}</small>
        </td>
        <td class="cost-col">${formatVND(p.cost_price)}</td>
        <td style="font-weight:600; color:#fff;">${formatVND(p.selling_price)}</td>
        <td class="cost-col">
          <span class="badge-tag ${margin > 50 ? 'badge-success' : 'badge-tag'}" style="font-weight:700;">
            ${margin}%
          </span>
        </td>
        <td>
          <span class="badge-tag ${isLowStock ? 'badge-warning' : 'badge-success'}">
            ${p.stock_quantity} tồn kho
          </span>
        </td>
        <td>
          <a href="/static/ai-strategy.html" class="link-highlight" style="font-size:12px;">
            Chiến lược giá AI <i class="fa-solid fa-sparkles"></i>
          </a>
        </td>
      </tr>
    `;
  }).join('');
}

async function handleAddProduct() {
  const sku = document.getElementById('modal-sku').value.trim();
  const name = document.getElementById('modal-name').value.trim();
  const categoryId = parseInt(document.getElementById('modal-category').value);
  const costPrice = parseFloat(document.getElementById('modal-cost').value);
  const sellingPrice = parseFloat(document.getElementById('modal-price').value);
  const stockQuantity = parseInt(document.getElementById('modal-stock').value);

  if (!sku || !name || isNaN(costPrice) || isNaN(sellingPrice) || isNaN(stockQuantity)) {
    showToast('Vui lòng điền đầy đủ và chính xác các trường thông tin!', 'warning');
    return;
  }

  try {
    const res = await apiRequest('/api/products/', {
      method: 'POST',
      body: JSON.stringify({ sku, name, categoryId, costPrice, sellingPrice, stockQuantity })
    });

    if (res.success) {
      showToast('Đã thêm sản phẩm mới vào SQL Server thành công!', 'success');
      closeAddModal();
      await loadProducts();
    }
  } catch (err) {
    showToast('Lỗi khi thêm sản phẩm: ' + err.message, 'error');
  }
}

function openAddModal() {
  const modal = document.getElementById('add-product-modal');
  if (modal) modal.style.display = 'flex';
}

function closeAddModal() {
  const modal = document.getElementById('add-product-modal');
  if (modal) modal.style.display = 'none';
}
