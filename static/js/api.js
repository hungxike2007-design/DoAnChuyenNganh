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
  window.location.href = '/static/login.html';
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
    window.location.href = '/static/login.html';
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
  if (allowedRoles.length > 0 && !allowedRoles.includes(userRole)) {
    console.warn(`[RBAC] Access denied for role: ${userRole}. Allowed: [${allowedRoles.join(', ')}]`);
    if (userRole === 'sales' || userRole === 'user') {
      showToast('Tài khoản của bạn là USER/SALES. Bạn không có quyền truy cập Thống kê của Admin!', 'warning');
      window.location.replace('/static/orders.html');
    } else {
      showToast('Trang này yêu cầu quyền Quản Trị Viên (Admin)!', 'warning');
      window.location.replace('/static/dashboard.html');
    }
    return false;
  }
  return true;
}

// Cập nhật thông tin tài khoản và điều chỉnh Sidebar linh hoạt theo Role
function renderSidebarUser() {
  const user = getUser();
  const nameEl = document.getElementById('sidebar-user-name');
  const roleEl = document.getElementById('sidebar-user-role');
  const avatarEl = document.getElementById('sidebar-user-avatar');
  const navContainer = document.querySelector('.sidebar-nav');

  if (!user) return;

  const role = (user.role || 'user').toLowerCase();
  const isStaff = (role === 'sales' || role === 'user');

  if (nameEl) nameEl.textContent = user.fullName || user.name || (isStaff ? 'Nhân Viên Bán Hàng' : 'Quản Lý');
  if (roleEl) {
    if (role === 'admin') roleEl.textContent = 'ADMIN (QUẢN TRỊ)';
    else if (role === 'manager') roleEl.textContent = 'MANAGER (QUẢN LÝ)';
    else roleEl.textContent = 'USER (BÁN HÀNG)';
  }
  if (avatarEl) avatarEl.textContent = (user.fullName || user.name || (isStaff ? 'S' : 'A')).charAt(0).toUpperCase();

  // Đổi màu avatar theo Role
  if (avatarEl) {
    if (role === 'admin') avatarEl.style.background = 'linear-gradient(135deg, #8b5cf6, #ec4899)';
    else if (role === 'manager') avatarEl.style.background = 'linear-gradient(135deg, #06b6d4, #3b82f6)';
    else avatarEl.style.background = 'linear-gradient(135deg, #10b981, #06b6d4)';
  }

  // PHÂN QUYỀN HIỂN THỊ MENU SIDEBAR THEO ROLE
  if (navContainer) {
    // 1. Nếu là SALES hoặc USER: ẨN hoàn toàn Thống kê doanh thu, Phân khúc RFM, Chiến lược AI và Quản trị người dùng
    if (isStaff) {
      const sensitiveLinks = [
        '/static/dashboard.html',
        '/static/customer-rfm.html',
        '/static/ai-strategy.html',
        '/static/users.html'
      ];
      navContainer.querySelectorAll('.nav-link').forEach(link => {
        const href = link.getAttribute('href');
        if (sensitiveLinks.some(s => href && href.includes(s))) {
          link.style.display = 'none';
        }
      });

      const titles = navContainer.querySelectorAll('.nav-section-title');
      if (titles.length > 0) titles[0].textContent = 'Nghiệp Vụ Bán Hàng';
      if (titles.length > 1) titles[1].textContent = 'Trợ Lý Tư Vấn Bán Hàng';
    }

    // 2. Nếu là ADMIN: Bổ sung thêm menu "Quản Trị Người Dùng & Phân Quyền"
    if (role === 'admin') {
      if (!navContainer.querySelector('a[href*="users.html"]')) {
        const adminSection = document.createElement('div');
        adminSection.className = 'nav-section-title';
        adminSection.textContent = 'Quản Trị Hệ Thống';
        adminSection.style.color = 'var(--accent-secondary)';

        const usersLink = document.createElement('a');
        usersLink.href = '/static/users.html';
        usersLink.className = `nav-link ${window.location.pathname.includes('users.html') ? 'active' : ''}`;
        usersLink.innerHTML = `
          <i class="fa-solid fa-users-gear" style="color:var(--accent-secondary);"></i>
          <span>Quản Trị Người Dùng</span>
          <span class="badge-tag badge-warning" style="margin-left:auto; font-size:10px;">ADMIN</span>
        `;

        navContainer.appendChild(adminSection);
        navContainer.appendChild(usersLink);
      }
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  renderSidebarUser();
});
