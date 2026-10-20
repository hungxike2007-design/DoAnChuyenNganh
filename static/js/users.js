/**
 * ==============================================================================
 * LOGIC QUẢN TRỊ NGƯỜI DÙNG & PHÂN QUYỀN (CHỈ DÀNH CHO ADMIN)
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', async () => {
  // Chỉ tài khoản có Role = admin mới được truy cập!
  if (!checkPageRole(['admin'])) return;

  await loadUsersList();
});

async function loadUsersList() {
  const tbody = document.getElementById('users-tbody');
  const countBadge = document.getElementById('users-count-badge');

  if (tbody) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:24px; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải danh sách người dùng từ SQL Server TOM...</td></tr>';
  }

  try {
    const res = await apiRequest('/api/auth/users');
    if (res.success && res.data) {
      if (countBadge) countBadge.textContent = `${res.data.length} Tài Khoản`;
      renderUsersTable(res.data);
    }
  } catch (err) {
    showToast('Lỗi khi tải danh sách người dùng: ' + err.message, 'error');
  }
}

function renderUsersTable(users) {
  const tbody = document.getElementById('users-tbody');
  if (!tbody) return;

  tbody.innerHTML = users.map((u, idx) => {
    const roleColors = {
      'admin': { bg: 'rgba(139, 92, 246, 0.2)', color: '#c084fc', border: 'rgba(139, 92, 246, 0.4)' },
      'manager': { bg: 'rgba(6, 182, 212, 0.2)', color: '#22d3ee', border: 'rgba(6, 182, 212, 0.4)' },
      'sales': { bg: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: 'rgba(16, 185, 129, 0.4)' },
      'user': { bg: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: 'rgba(16, 185, 129, 0.4)' }
    };
    const rc = roleColors[u.role] || roleColors['user'];

    return `
      <tr>
        <td style="font-weight:700; color:var(--accent-cyan);">#${idx + 1}</td>
        <td>
          <div style="display:flex; align-items:center; gap:10px;">
            <div style="width:34px; height:34px; border-radius:50%; background:${rc.bg}; color:${rc.color}; display:flex; align-items:center; justify-content:center; font-weight:700; border:1px solid ${rc.border};">
              ${(u.full_name || 'U').charAt(0).toUpperCase()}
            </div>
            <div>
              <div style="font-weight:600; color:#fff;">${u.full_name}</div>
              <small style="color:var(--text-muted);">${u.email}</small>
            </div>
          </div>
        </td>
        <td>
          <span style="display:inline-block; padding:4px 10px; border-radius:20px; font-size:12px; font-weight:700; background:${rc.bg}; color:${rc.color}; border:1px solid ${rc.border};">
            ${u.role.toUpperCase()}
          </span>
        </td>
        <td style="color:var(--text-secondary); font-size:13px;">
          ${u.created_at || 'N/A'}
        </td>
        <td>
          <div style="display:flex; align-items:center; gap:8px;">
            <select onchange="updateUserRole(${u.id}, this.value)" style="background:#1e293b; color:#fff; border:1px solid var(--border-subtle); padding:6px 10px; border-radius:6px; font-size:12px; cursor:pointer;">
              <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Quản Trị Viên (Admin)</option>
              <option value="manager" ${u.role === 'manager' ? 'selected' : ''}>Quản Lý (Manager)</option>
              <option value="user" ${u.role === 'user' || u.role === 'sales' ? 'selected' : ''}>Nhân Viên Bán Hàng (User / Sales)</option>
            </select>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function updateUserRole(userId, newRole) {
  try {
    const res = await apiRequest(`/api/auth/users/${userId}/role`, {
      method: 'PUT',
      body: JSON.stringify({ role: newRole })
    });

    if (res.success) {
      showToast(res.message, 'success');
      await loadUsersList();
    }
  } catch (err) {
    showToast('Lỗi cập nhật vai trò: ' + err.message, 'error');
  }
}
