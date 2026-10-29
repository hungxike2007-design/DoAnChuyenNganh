/**
 * ==============================================================================
 * MODULE API CLIENT TOÀN CỤC (GLOBAL API & AUTH HELPER)
 * ==============================================================================
 */

const API_BASE = ''; // Dùng relative path để tự động theo host và port của server

// Quản lý Token & Người dùng trong LocalStorage
function getToken() {
  return localStorage.getItem('dacn_token');
}

function setToken(token) {
  localStorage.setItem('dacn_token', token);
}

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

function logout() {
  localStorage.removeItem('dacn_token');
  localStorage.removeItem('dacn_user');
  const isFrontend = window.location.pathname.startsWith('/frontend/');
  window.location.href = isFrontend ? '/frontend/auth/login.html' : '/frontend/auth/login.html';
}

// Wrapper Fetch tự động gán Bearer Token và xử lý lỗi
async function apiRequest(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
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
  toast.innerHTML = `
    <div style="display:flex; align-items:center; gap:8px;">
      <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info'}"></i>
      <span>${message}</span>
    </div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Định dạng tiền tệ VND
function formatVND(number) {
  if (isNaN(number) || number === null) return '0 ₫';
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(number);
}

// Kiểm tra phiên đăng nhập và bảo vệ trang
function requireAuth() {
  const token = getToken();
  if (!token) {
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
