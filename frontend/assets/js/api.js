/**
 * ==============================================================================
 * MODULE API CLIENT TOÀN CỤC (GLOBAL API & AUTH HELPER)
 * ==============================================================================
 */

const API_BASE = ''; // Dùng relative path để tự động theo host và port của server
localStorage.removeItem('dacn_token'); // Xóa JWT cũ từng được lưu không an toàn.

// Quản lý Token & Người dùng trong LocalStorage
function getToken() { return null; }

function setToken(_token) { localStorage.removeItem('dacn_token'); }

function getUser() {
  const userStr = localStorage.getItem('dacn_user');
  try {
    return userStr ? JSON.parse(userStr) : null;
  } catch (e) {
    return null;
  }
}

function setUser(user) {
  localStorage.setItem('dacn_user', JSON.stringify(user));
}

async function logout() {
  localStorage.removeItem('dacn_token');
  localStorage.removeItem('dacn_user');
  try { await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' }); } catch (_) {}
  window.location.href = '/frontend/auth/login.html';
}

// Wrapper Fetch tự động gán Bearer Token và xử lý lỗi
async function apiRequest(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };


  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      credentials: 'same-origin',
      headers
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        // Token hết hạn hoặc không có quyền
        console.warn('Phiên đăng nhập hết hạn hoặc không hợp lệ.');
      }
      throw new Error(data.detail || data.message || `Lỗi HTTP ${response.status}`);
    }

    return data;
  } catch (error) {
    console.error(`[API Error ${endpoint}]:`, error);
    throw error;
  }
}

// Toast thông báo góc phải màn hình
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const row = document.createElement('div');
  row.style.cssText = 'display:flex; align-items:center; gap:8px;';
  const icon = document.createElement('i');
  icon.className = `fa-solid ${type === 'success' ? 'fa-circle-check' : type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info'}`;
  const text = document.createElement('span');
  text.textContent = String(message ?? '');
  row.append(icon, text);
  toast.appendChild(row);

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/**
 * Hộp thoại xác nhận tùy chỉnh (Custom Confirm Modal) - Thay thế hoàn toàn window.confirm()
 * @param {Object} options Cấu hình hộp thoại
 * @returns {Promise<boolean>}
 */
function showConfirmModal({
  title = 'Xác Nhận Hành Động',
  message = 'Bạn có chắc chắn muốn thực hiện hành động này?',
  confirmText = 'Xác Nhận',
  cancelText = 'Hủy Bỏ',
  type = 'danger',
  icon = null
} = {}) {
  return new Promise((resolve) => {
    const existing = document.getElementById('custom-confirm-modal-wrapper');
    if (existing) existing.remove();

    const isDanger = type === 'danger';
    const iconClass = icon || (isDanger ? 'fa-solid fa-triangle-exclamation' : 'fa-solid fa-circle-question');
    const iconColor = isDanger ? '#dc2626' : '#2563eb';
    const iconBg = isDanger ? '#fee2e2' : '#eff6ff';
    const confirmBtnBg = isDanger ? '#dc2626' : '#2563eb';

    const overlay = document.createElement('div');
    overlay.id = 'custom-confirm-modal-wrapper';
    overlay.style.cssText = `
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.55);
      backdrop-filter: blur(4px);
      z-index: 999999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      opacity: 0;
      transition: opacity 0.18s ease;
    `;

    overlay.innerHTML = `
      <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:12px; width:100%; max-width:420px; box-shadow:0 20px 25px -5px rgba(0,0,0,0.15), 0 8px 10px -6px rgba(0,0,0,0.1); padding:24px; transform:scale(0.96); transition:transform 0.18s cubic-bezier(0.16,1,0.3,1);">
        <div style="display:flex; align-items:flex-start; gap:14px; margin-bottom:16px;">
          <div style="width:42px; height:42px; border-radius:50%; background:${iconBg}; color:${iconColor}; display:flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0;">
            <i class="${iconClass}"></i>
          </div>
          <div style="flex:1;">
            <h3 style="margin:0 0 6px 0; font-size:16px; font-weight:700; color:#0f172a;">${title}</h3>
            <p style="margin:0; font-size:13px; color:#475569; line-height:1.5;">${message}</p>
          </div>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
          <button type="button" id="custom-modal-cancel-btn" style="padding:8px 16px; border-radius:6px; font-size:13px; font-weight:600; background:#f1f5f9; border:1px solid #cbd5e1; color:#475569; cursor:pointer; transition:all 0.15s ease;">
            ${cancelText}
          </button>
          <button type="button" id="custom-modal-confirm-btn" style="padding:8px 18px; border-radius:6px; font-size:13px; font-weight:700; background:${confirmBtnBg}; border:none; color:#ffffff; cursor:pointer; display:inline-flex; align-items:center; gap:6px; box-shadow:0 1px 2px rgba(0,0,0,0.1); transition:all 0.15s ease;">
            ${confirmText}
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    // Hiệu ứng mở mượt mà
    requestAnimationFrame(() => {
      overlay.style.opacity = '1';
      const box = overlay.querySelector('div');
      if (box) box.style.transform = 'scale(1)';
    });

    const cleanup = () => {
      overlay.style.opacity = '0';
      const box = overlay.querySelector('div');
      if (box) box.style.transform = 'scale(0.96)';
      setTimeout(() => overlay.remove(), 180);
    };

    const confirmBtn = overlay.querySelector('#custom-modal-confirm-btn');
    const cancelBtn = overlay.querySelector('#custom-modal-cancel-btn');

    if (confirmBtn) {
      confirmBtn.addEventListener('click', () => {
        cleanup();
        resolve(true);
      });
    }

    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => {
        cleanup();
        resolve(false);
      });
    }

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        cleanup();
        resolve(false);
      }
    });

    const handleKey = (e) => {
      if (e.key === 'Escape') {
        window.removeEventListener('keydown', handleKey);
        cleanup();
        resolve(false);
      }
    };
    window.addEventListener('keydown', handleKey);
  });
}

// Định dạng tiền tệ VND
function formatVND(number) {
  if (isNaN(number) || number === null) return '0 ₫';
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(number);
}

// Kiểm tra phiên đăng nhập và bảo vệ trang
function requireAuth() {
  const user = getUser();
  if (!user) {
    const isFrontend = window.location.pathname.startsWith('/frontend/');
    window.location.href = isFrontend ? '/frontend/auth/login.html' : '/frontend/auth/login.html';
    return false;
  }
  return true;
}

// Kiểm tra quyền truy cập theo vai trò (Role-Based Page Protection)
function checkPageRole(allowedRoles = []) {
  if (!requireAuth()) return false;
  const user = getUser();
  if (!user) return false;

  const userRole = (user.role || 'user').toLowerCase();
  const isFrontend = window.location.pathname.startsWith('/frontend/');
  const ordersPage = isFrontend ? '/frontend/orders/orders.html' : '/frontend/orders/orders.html';
  const dashboardPage = isFrontend ? '/frontend/dashboard/dashboard.html' : '/frontend/dashboard/dashboard.html';

  if (allowedRoles.length > 0 && !allowedRoles.includes(userRole)) {
    console.warn(`[RBAC] Access denied for role: ${userRole}. Allowed: [${allowedRoles.join(', ')}]`);
    if (userRole === 'sales') {
      showToast('Tài khoản SALES không có quyền xem Báo cáo Tài chính / Thống kê Doanh thu!', 'warning');
      window.location.replace(ordersPage);
    } else if (userRole === 'user') {
      showToast('Tài khoản USER không có quyền truy cập trang Quản lý / Báo cáo!', 'warning');
      window.location.replace(ordersPage);
    } else {
      showToast('Trang này yêu cầu quyền Quản Trị Viên (Admin)!', 'warning');
      window.location.replace(dashboardPage);
    }
    return false;
  }
  return true;
}

// Cập nhật thông tin tài khoản và điều chỉnh Sidebar linh hoạt theo Role
// Cập nhật thông tin tài khoản và điều chỉnh Sidebar linh hoạt theo Role
// Cập nhật thông tin tài khoản và điều chỉnh Sidebar linh hoạt theo Role
function renderSidebarUser() {
  const user = getUser();
  const nameEl = document.getElementById('sidebar-user-name');
  const roleEl = document.getElementById('sidebar-user-role');
  const avatarEl = document.getElementById('sidebar-user-avatar');

  if (!user) return;

  const role = (user.role || 'user').toLowerCase();
  const isStaff = (role === 'sales' || role === 'user');

  if (nameEl) nameEl.textContent = user.fullName || user.name || (role === 'sales' ? 'Nhân Viên Bán Hàng' : role === 'user' ? 'Khách Hàng' : 'Quản Lý');
  if (roleEl) {
    if (role === 'admin') roleEl.textContent = 'ADMIN';
    else if (role === 'manager') roleEl.textContent = 'MANAGER';
    else if (role === 'sales') roleEl.textContent = 'SALES';
    else roleEl.textContent = 'USER';
  }
  if (avatarEl) avatarEl.textContent = (user.fullName || user.name || (role === 'sales' ? 'S' : role === 'user' ? 'U' : 'A')).charAt(0).toUpperCase();

  // Đổi màu avatar theo Role (Màu đơn sắc dịu mắt)
  if (avatarEl) {
    if (role === 'admin') avatarEl.style.background = '#4f46e5';
    else if (role === 'manager') avatarEl.style.background = '#2563eb';
    else if (role === 'sales') avatarEl.style.background = '#059669';
    else avatarEl.style.background = '#0284c7';
  }

  // PHÂN QUYỀN HIỂN THỊ MENU SIDEBAR THEO 4 NHÓM CHỨC NĂNG
  const groupAnalytics = document.getElementById('nav-group-analytics');
  const groupOperations = document.getElementById('nav-group-operations');
  const groupAi = document.getElementById('nav-group-ai');
  const groupAdmin = document.getElementById('nav-group-admin');
  const titleOperations = document.getElementById('title-operations');
  const titleAi = document.getElementById('title-ai');

  if (role === 'user' || role === 'sales') {
    // 1. TÀI KHOẢN NGƯỜI KINH DOANH ĐỘC LẬP (USER / SALES MERCHANT):
    // Được sử dụng đầy đủ các tính năng chính: Dashboard cá nhân, Kho hàng, Đơn hàng, Kế hoạch AI, Copilot
    if (groupAnalytics) {
      groupAnalytics.style.display = 'block';
      // Chỉ ẩn RFM toàn hệ thống
      document.querySelectorAll('a[href*="customer-rfm.html"]').forEach(el => el.style.display = 'none');
    }

    if (titleOperations) {
      titleOperations.innerHTML = '<i class="fa-solid fa-cart-shopping"></i> Vận Hành & Bán Hàng';
    }

    // Mở kho hàng riêng của User
    document.querySelectorAll('a[href*="products.html"]').forEach(el => el.style.display = 'flex');

    // Mở Lập Kế Hoạch Doanh Thu AI (DSS) cho User, chỉ ẩn Chiến lược giá PRO (ai-strategy)
    document.querySelectorAll('a[href*="revenue-planner.html"]').forEach(el => el.style.display = 'flex');
    document.querySelectorAll('a[href*="ai-strategy.html"]').forEach(el => el.style.display = 'none');

    if (titleAi) {
      titleAi.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Trí Tuệ Nhân Tạo (AI)';
    }

    if (groupAdmin) groupAdmin.style.display = 'none';
  } else {
    // 2. ADMIN & MANAGER: Quản trị toàn bộ
    if (groupAnalytics) groupAnalytics.style.display = 'block';
    document.querySelectorAll('.nav-link').forEach(el => el.style.display = 'flex');

    if (groupAdmin) {
      groupAdmin.style.display = (role === 'admin') ? 'block' : 'none';
    }
  }

  // Fallback an toàn bằng duyệt URL
  const navContainer = document.querySelector('.sidebar-nav');
  if (navContainer) {
    if (role === 'user' || role === 'sales') {
      const userForbidden = ['customer-rfm.html', 'ai-strategy.html', 'users.html'];
      navContainer.querySelectorAll('.nav-link').forEach(link => {
        const href = link.getAttribute('href') || '';
        if (userForbidden.some(kw => href.includes(kw))) {
          link.style.display = 'none';
        }
      });
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  renderSidebarUser();
});
