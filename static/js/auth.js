/**
 * ==============================================================================
 * LOGIC XÁC THỰC: ĐĂNG NHẬP, ĐĂNG KÝ, QUÊN MẬT KHẨU
 * ==============================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. XỬ LÝ ĐĂNG NHẬP (LOGIN)
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;
      const submitBtn = loginForm.querySelector('button[type="submit"]');

      try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang đăng nhập...';

        const res = await apiRequest('/api/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email, password })
        });

        if (res.success && res.data) {
          setToken(res.data.token);
          setUser(res.data.user);
          showToast('Đăng nhập thành công! Đang chuyển hướng...', 'success');
          setTimeout(() => {
            const role = (res.data.user && res.data.user.role ? res.data.user.role : 'user').toLowerCase();
            if (role === 'admin' || role === 'manager') {
              window.location.href = '/static/dashboard.html';
            } else {
              window.location.href = '/static/orders.html';
            }
          }, 700);
        }
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Đăng Nhập <i class="fa-solid fa-arrow-right"></i>';
      }
    });
  }

  // 2. XỬ LÝ ĐĂNG KÝ (REGISTER)
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fullName = document.getElementById('fullName').value.trim();
      const email = document.getElementById('email').value.trim();
      const role = document.getElementById('role').value;
      const password = document.getElementById('password').value;
      const confirmPassword = document.getElementById('confirmPassword').value;
      const submitBtn = registerForm.querySelector('button[type="submit"]');

      if (password !== confirmPassword) {
        showToast('Mật khẩu xác nhận không trùng khớp!', 'warning');
        return;
      }

      try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tạo tài khoản...';

        const res = await apiRequest('/api/auth/register', {
          method: 'POST',
          body: JSON.stringify({ fullName, email, password, role })
        });

        if (res.success && res.data) {
          setToken(res.data.token);
          setUser(res.data.user);
          showToast('Đăng ký tài khoản thành công! Đang chuyển hướng...', 'success');
          setTimeout(() => {
            const role = (res.data.user && res.data.user.role ? res.data.user.role : 'user').toLowerCase();
            if (role === 'admin' || role === 'manager') {
              window.location.href = '/static/dashboard.html';
            } else {
              window.location.href = '/static/orders.html';
            }
          }, 700);
        }
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Tạo Tài Khoản <i class="fa-solid fa-arrow-right"></i>';
      }
    });
  }

  // 3. XỬ LÝ QUÊN MẬT KHẨU (FORGOT PASSWORD)
  const forgotForm = document.getElementById('forgot-form');
  const resetForm = document.getElementById('reset-form');

  if (forgotForm) {
    forgotForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('forgot-email').value.trim();
      const submitBtn = forgotForm.querySelector('button[type="submit"]');

      try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tạo mã OTP...';

        const res = await apiRequest('/api/auth/forgot-password', {
          method: 'POST',
          body: JSON.stringify({ email })
        });

        if (res.success) {
          showToast(res.message, 'success');
          // Chuyển sang bước 2 (Đặt lại mật khẩu)
          document.getElementById('step-1').classList.remove('active');
          document.getElementById('step-2').classList.add('active');
          document.getElementById('reset-email').value = email;
          if (res.data && res.data.demo_otp) {
            document.getElementById('otp-code').value = res.data.demo_otp;
          }
        }
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Gửi Mã Xác Thực OTP <i class="fa-solid fa-paper-plane"></i>';
      }
    });
  }

  if (resetForm) {
    resetForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('reset-email').value.trim();
      const otpCode = document.getElementById('otp-code').value.trim();
      const newPassword = document.getElementById('new-password').value;
      const confirmNewPassword = document.getElementById('confirm-new-password').value;
      const submitBtn = resetForm.querySelector('button[type="submit"]');

      if (newPassword !== confirmNewPassword) {
        showToast('Mật khẩu mới xác nhận không khớp!', 'warning');
        return;
      }

      try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang cập nhật...';

        const res = await apiRequest('/api/auth/reset-password', {
          method: 'POST',
          body: JSON.stringify({ email, otpCode, newPassword })
        });

        if (res.success) {
          showToast(res.message, 'success');
          setTimeout(() => {
            window.location.href = '/static/login.html';
          }, 1500);
        }
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Xác Nhận Đổi Mật Khẩu <i class="fa-solid fa-check"></i>';
      }
    });
  }
});

// Nút điền nhanh tài khoản mẫu để chấm đồ án
function fillDemoAccount(role) {
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  if (!emailInput || !passwordInput) return;

  if (role === 'admin') {
    emailInput.value = 'admin@dacn.vn';
    showToast('Tài khoản ADMIN: Toàn quyền Thống kê Doanh thu & Quản trị người dùng', 'info');
  } else if (role === 'manager') {
    emailInput.value = 'manager@dacn.vn';
    showToast('Tài khoản MANAGER: Thống kê Doanh thu, RFM & AI Strategy (Không quản trị user)', 'info');
  } else {
    emailInput.value = 'user@dacn.vn';
    showToast('Tài khoản USER / SALES: Chỉ có chức năng Quản lý Đơn Hàng & Kho Hàng', 'info');
  }
  passwordInput.value = '123456';
}

// Hàm toggle hiển thị mật khẩu
function togglePasswordVisibility(fieldId) {
  const field = document.getElementById(fieldId);
  if (!field) return;
  if (field.type === 'password') {
    field.type = 'text';
  } else {
    field.type = 'password';
  }
}
