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

// Cập nhật thông tin tài khoản trên Sidebar
function renderSidebarUser() {
  const user = getUser();
  const nameEl = document.getElementById('sidebar-user-name');
  const roleEl = document.getElementById('sidebar-user-role');
  const avatarEl = document.getElementById('sidebar-user-avatar');

  if (user) {
    if (nameEl) nameEl.textContent = user.fullName || user.name || 'Người dùng';
    if (roleEl) roleEl.textContent = (user.role || 'manager').toUpperCase();
    if (avatarEl) avatarEl.textContent = (user.fullName || user.name || 'U').charAt(0).toUpperCase();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  renderSidebarUser();
});
