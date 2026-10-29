/**
 * ==============================================================================
 * MODULE HỖ TRỢ NHẬP DỮ LIỆU TỪ FILE EXCEL / CSV (IMPORT HELPER JS)
 * ==============================================================================
 * Tách riêng file JS xử lý giao diện Kéo thả, Tải file mẫu, Xem trước & Gửi API
 * ==============================================================================
 */

// Quản lý trạng thái file đang chọn
let selectedOrderFile = null;
let selectedProductFile = null;

// ==============================================================================
// 1. IMPORT ĐƠN HÀNG (ORDERS IMPORT)
// ==============================================================================

function openImportOrderModal() {
  const modal = document.getElementById('import-orders-modal');
  if (modal) {
    modal.style.display = 'flex';
    resetOrderImportState();
  }
}

function closeImportOrderModal() {
  const modal = document.getElementById('import-orders-modal');
  if (modal) {
    modal.style.display = 'none';
  }
}

function resetOrderImportState() {
  selectedOrderFile = null;
  const fileInput = document.getElementById('order-file-input');
  if (fileInput) fileInput.value = '';

  const dropZone = document.getElementById('order-drop-zone');
  const fileInfo = document.getElementById('order-file-info');
  const btnSubmit = document.getElementById('btn-submit-import-orders');
  const progressBox = document.getElementById('order-import-progress');

  if (dropZone) dropZone.style.display = 'block';
  if (fileInfo) fileInfo.style.display = 'none';
  if (btnSubmit) btnSubmit.disabled = true;
  if (progressBox) progressBox.style.display = 'none';
}

function handleOrderFileSelected(file) {
  if (!file) return;

  const validExts = ['.csv', '.xlsx', '.xls'];
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
  if (!validExts.includes(ext)) {
    showToast('Vui lòng chọn định dạng file hợp lệ (.csv, .xlsx, .xls)!', 'warning');
    return;
  }

  selectedOrderFile = file;

  const dropZone = document.getElementById('order-drop-zone');
  const fileInfo = document.getElementById('order-file-info');
  const fileNameEl = document.getElementById('order-file-name');
  const fileSizeEl = document.getElementById('order-file-size');
  const btnSubmit = document.getElementById('btn-submit-import-orders');

  if (fileNameEl) fileNameEl.textContent = file.name;
  if (fileSizeEl) fileSizeEl.textContent = `${(file.size / 1024).toFixed(1)} KB`;

  if (dropZone) dropZone.style.display = 'none';
  if (fileInfo) fileInfo.style.display = 'flex';
  if (btnSubmit) btnSubmit.disabled = false;
}

async function submitImportOrders() {
  if (!selectedOrderFile) {
    showToast('Vui lòng chọn file dữ liệu trước khi nạp!', 'warning');
    return;
  }

  const btnSubmit = document.getElementById('btn-submit-import-orders');
  const progressBox = document.getElementById('order-import-progress');
  const token = getToken();

  try {
    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang nạp vào SQL Server...';
    }
    if (progressBox) progressBox.style.display = 'block';

    const formData = new FormData();
    formData.append('file', selectedOrderFile);

    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch('/api/import/orders', {
      method: 'POST',
      headers,
      body: formData
    });

    const res = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(res.detail || 'Lỗi khi nạp dữ liệu từ máy chủ');
    }

    if (res.success) {
      showToast(res.message || 'Nạp dữ liệu đơn hàng thành công!', 'success');
      if (res.warnings && res.warnings.length > 0) {
        setTimeout(() => {
          showToast(`💡 Hệ thống tự động bù cột: ${res.warnings.slice(0, 2).join(' • ')}`, 'info');
        }, 1200);
      }
      closeImportOrderModal();

      // Nếu đang ở trang Đơn Hàng thì tự động nạp lại bảng
      if (typeof loadOrders === 'function') {
        await loadOrders();
      }
    }
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> Bắt Đầu Nạp Dữ Liệu';
    }
    if (progressBox) progressBox.style.display = 'none';
  }
}

function downloadOrderTemplate() {
  window.location.href = '/api/import/template/orders';
  showToast('Đang tải file mẫu đơn hàng Excel / CSV...', 'info');
}

// ==============================================================================
// 2. IMPORT SẢN PHẨM (PRODUCTS IMPORT)
// ==============================================================================

function openImportProductModal() {
  const modal = document.getElementById('import-products-modal');
  if (modal) {
    modal.style.display = 'flex';
    resetProductImportState();
  }
}

function closeImportProductModal() {
  const modal = document.getElementById('import-products-modal');
  if (modal) {
    modal.style.display = 'none';
  }
}

function resetProductImportState() {
  selectedProductFile = null;
  const fileInput = document.getElementById('product-file-input');
  if (fileInput) fileInput.value = '';

  const dropZone = document.getElementById('product-drop-zone');
  const fileInfo = document.getElementById('product-file-info');
  const btnSubmit = document.getElementById('btn-submit-import-products');
  const progressBox = document.getElementById('product-import-progress');

  if (dropZone) dropZone.style.display = 'block';
  if (fileInfo) fileInfo.style.display = 'none';
  if (btnSubmit) btnSubmit.disabled = true;
  if (progressBox) progressBox.style.display = 'none';
}

function handleProductFileSelected(file) {
  if (!file) return;

  const validExts = ['.csv', '.xlsx', '.xls'];
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
  if (!validExts.includes(ext)) {
    showToast('Vui lòng chọn định dạng file hợp lệ (.csv, .xlsx, .xls)!', 'warning');
    return;
  }

  selectedProductFile = file;

  const dropZone = document.getElementById('product-drop-zone');
  const fileInfo = document.getElementById('product-file-info');
  const fileNameEl = document.getElementById('product-file-name');
  const fileSizeEl = document.getElementById('product-file-size');
  const btnSubmit = document.getElementById('btn-submit-import-products');

  if (fileNameEl) fileNameEl.textContent = file.name;
  if (fileSizeEl) fileSizeEl.textContent = `${(file.size / 1024).toFixed(1)} KB`;

  if (dropZone) dropZone.style.display = 'none';
  if (fileInfo) fileInfo.style.display = 'flex';
  if (btnSubmit) btnSubmit.disabled = false;
}

async function submitImportProducts() {
  if (!selectedProductFile) {
    showToast('Vui lòng chọn file sản phẩm trước khi nạp!', 'warning');
    return;
  }

  const btnSubmit = document.getElementById('btn-submit-import-products');
  const progressBox = document.getElementById('product-import-progress');
  const token = getToken();

  try {
    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang nạp sản phẩm...';
    }
    if (progressBox) progressBox.style.display = 'block';

    const formData = new FormData();
    formData.append('file', selectedProductFile);

    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch('/api/import/products', {
      method: 'POST',
      headers,
      body: formData
    });

    const res = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(res.detail || 'Lỗi khi nạp dữ liệu từ máy chủ');
    }

    if (res.success) {
      showToast(res.message || 'Nạp danh mục sản phẩm thành công!', 'success');
      if (res.warnings && res.warnings.length > 0) {
        setTimeout(() => {
          showToast(`💡 Hệ thống tự động bù cột: ${res.warnings.slice(0, 2).join(' • ')}`, 'info');
        }, 1200);
      }
      closeImportProductModal();

      // Nếu đang ở trang Sản Phẩm thì tự động nạp lại
      if (typeof loadProducts === 'function') {
        await loadProducts();
      }
    }
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> Bắt Đầu Nạp Sản Phẩm';
    }
    if (progressBox) progressBox.style.display = 'none';
  }
}

function downloadProductTemplate() {
  window.location.href = '/api/import/template/products';
  showToast('Đang tải file mẫu sản phẩm Excel / CSV...', 'info');
}

// Khởi tạo sự kiện Drag & Drop khi DOM đã tải xong
document.addEventListener('DOMContentLoaded', () => {
  // 1. Drag & drop cho Đơn Hàng
  const orderDropZone = document.getElementById('order-drop-zone');
  const orderFileInput = document.getElementById('order-file-input');

  if (orderDropZone && orderFileInput) {
    orderDropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      orderDropZone.style.borderColor = 'var(--accent-primary)';
      orderDropZone.style.background = 'rgba(99, 102, 241, 0.12)';
    });

    orderDropZone.addEventListener('dragleave', () => {
      orderDropZone.style.borderColor = 'var(--border-subtle)';
      orderDropZone.style.background = 'rgba(255, 255, 255, 0.02)';
    });

    orderDropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      orderDropZone.style.borderColor = 'var(--border-subtle)';
      orderDropZone.style.background = 'rgba(255, 255, 255, 0.02)';
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleOrderFileSelected(e.dataTransfer.files[0]);
      }
    });

    orderFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleOrderFileSelected(e.target.files[0]);
      }
    });
  }

  // 2. Drag & drop cho Sản Phẩm
  const prodDropZone = document.getElementById('product-drop-zone');
  const prodFileInput = document.getElementById('product-file-input');

  if (prodDropZone && prodFileInput) {
    prodDropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      prodDropZone.style.borderColor = 'var(--accent-primary)';
      prodDropZone.style.background = 'rgba(99, 102, 241, 0.12)';
    });

    prodDropZone.addEventListener('dragleave', () => {
      prodDropZone.style.borderColor = 'var(--border-subtle)';
      prodDropZone.style.background = 'rgba(255, 255, 255, 0.02)';
    });

    prodDropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      prodDropZone.style.borderColor = 'var(--border-subtle)';
      prodDropZone.style.background = 'rgba(255, 255, 255, 0.02)';
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleProductFileSelected(e.dataTransfer.files[0]);
      }
    });

    prodFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleProductFileSelected(e.target.files[0]);
      }
    });
  }
});
