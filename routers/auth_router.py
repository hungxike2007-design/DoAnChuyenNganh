"""
==============================================================================
ROUTER XÁC THỰC NGƯỜI DÙNG (AUTH ROUTER - FASTAPI)
==============================================================================
Các Endpoint:
- POST /api/auth/register: Đăng ký tài khoản mới
- POST /api/auth/login: Đăng nhập & trả về JWT Token
- POST /api/auth/forgot-password: Quên mật khẩu & cấp mã OTP
- POST /api/auth/reset-password: Xác thực OTP và đặt lại mật khẩu mới
- GET  /api/auth/me: Lấy thông tin tài khoản hiện tại
==============================================================================
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from services.auth_service import AuthService, decode_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# Pydantic Schemas cho Request Body
class RegisterRequest(BaseModel):
    fullName: str
    email: str
    password: str
    role: Optional[str] = "user"


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    otpCode: str
    newPassword: str


# Dependency để bảo vệ endpoint cần đăng nhập
def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để tiếp tục.")
    token = authorization.split(" ")[1]
    try:
        payload = decode_access_token(token)
        return payload
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


def require_roles(*allowed_roles):
    """Kiểm tra quyền hạn người dùng theo danh sách vai trò cho phép."""
    def role_checker(user: dict = Depends(get_current_user)):
        user_role = user.get("role", "sales")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Quyền truy cập bị từ chối! Chức năng này yêu cầu vai trò: [{', '.join(allowed_roles)}]. Vai trò của bạn: '{user_role}'."
            )
        return user
    return role_checker


@router.post("/register")
def register(req: RegisterRequest):
    try:
        result = AuthService.register_user(req.fullName, req.email, req.password, req.role)
        return {
            "success": True,
            "message": "Đăng ký tài khoản thành công!",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")


@router.post("/login")
def login(req: LoginRequest):
    try:
        result = AuthService.login_user(req.email, req.password)
        return {
            "success": True,
            "message": "Đăng nhập thành công!",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    try:
        result = AuthService.request_forgot_password(req.email)
        return {
            "success": True,
            "message": f"Mã xác thực OTP đã được gửi! (Mã OTP demo đồ án là: {result['demo_otp']})",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest):
    try:
        AuthService.reset_password(req.email, req.otpCode, req.newPassword)
        return {
            "success": True,
            "message": "Đặt lại mật khẩu thành công! Bạn có thể đăng nhập ngay với mật khẩu mới."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    user_id = int(user["sub"])
    profile = AuthService.get_user_by_id(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")
    return {
        "success": True,
        "data": profile
    }


# ==============================================================================
# CÁC ENDPOINT QUẢN TRỊ TÀI KHOẢN (CHỈ DÀNH CHO ADMIN)
# ==============================================================================

class UpdateRoleRequest(BaseModel):
    role: str


@router.get("/users")
def get_all_users(admin: dict = Depends(require_roles("admin"))):
    """Admin lấy danh sách toàn bộ người dùng và vai trò."""
    from config.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.full_name, u.email, u.role, u.avatar_url, 
               CONVERT(VARCHAR(10), u.created_at, 120) as created_at,
               COUNT(o.id) as total_orders,
               COALESCE(SUM(o.net_amount), 0) as total_revenue
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id AND o.status = 'completed'
        GROUP BY u.id, u.full_name, u.email, u.role, u.avatar_url, CONVERT(VARCHAR(10), u.created_at, 120)
        ORDER BY total_revenue DESC, u.id ASC
    """)
    users = cursor.fetchall()
    conn.close()
    for u in users:
        u["total_revenue"] = float(u.get("total_revenue", 0.0) or 0.0)
        u["total_orders"] = int(u.get("total_orders", 0) or 0)
    return {"success": True, "data": users}


@router.put("/users/{user_id}/role")
def update_user_role(user_id: int, req: UpdateRoleRequest, admin: dict = Depends(require_roles("admin"))):
    """Admin thay đổi phân quyền của một tài khoản."""
    if req.role not in ["admin", "manager", "sales", "user"]:
        raise HTTPException(status_code=400, detail="Vai trò không hợp lệ! Chỉ cho phép: admin, manager, sales, user.")

    from config.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (req.role, user_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Đã cập nhật vai trò của tài khoản thành '{req.role}'!"}

