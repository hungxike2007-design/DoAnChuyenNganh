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

import os
from fastapi import APIRouter, HTTPException, Depends, Header, Request, Response
from pydantic import BaseModel
from typing import Optional
from backend.modules.auth.auth_service import AuthService, decode_access_token

from backend.config.db import get_db_connection

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
def get_current_user(request: Request, authorization: Optional[str] = Header(None)) -> dict:
    token = request.cookies.get("dacn_token")
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để tiếp tục.")
    try:
        payload = decode_access_token(token)
        return payload
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


def require_roles(*allowed_roles):
    """Kiểm tra quyền hạn người dùng theo danh sách vai trò cho phép."""
    if len(allowed_roles) == 1 and isinstance(allowed_roles[0], (list, tuple, set)):
        roles_set = set(allowed_roles[0])
    else:
        roles_set = set(allowed_roles)

    def role_checker(user: dict = Depends(get_current_user)):
        user_role = (user.get("role") or "sales").lower()
        if user_role not in roles_set:
            roles_str = ", ".join(sorted(roles_set))
            raise HTTPException(
                status_code=403,
                detail=f"Quyền truy cập bị từ chối! Chức năng này yêu cầu vai trò: [{roles_str}]. Vai trò của bạn: '{user_role}'."
            )
        return user
    return role_checker


def _auth_cookie_settings():
    return {
        "key": "dacn_token", "httponly": True,
        "secure": os.getenv("COOKIE_SECURE", "false").lower() == "true",
        "samesite": "lax", "path": "/",
        "max_age": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080")) * 60,
    }


@router.post("/register")
def register(req: RegisterRequest, response: Response):
    try:
        result = AuthService.register_user(req.fullName, req.email, req.password, req.role)
        response.set_cookie(value=result["token"], **_auth_cookie_settings())
        return {
            "success": True,
            "message": "Đăng ký tài khoản thành công!",
            "data": {"user": result["user"]}
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")


@router.post("/login")
def login(req: LoginRequest, response: Response):
    try:
        result = AuthService.login_user(req.email, req.password)
        response.set_cookie(value=result["token"], **_auth_cookie_settings())
        return {
            "success": True,
            "message": "Đăng nhập thành công!",
            "data": {"user": result["user"]}
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("dacn_token", path="/", httponly=True,
                           secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
                           samesite="lax")
    return {"success": True, "message": "Đã đăng xuất."}


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    try:
        result = AuthService.request_forgot_password(req.email)
        debug_mode = os.getenv("DEBUG_MODE", "false").lower() in {"1", "true", "yes", "on"}
        data = {"email": result["email"], "expires_in_minutes": result["expires_in_minutes"]}
        message = "Yêu cầu khôi phục đã được ghi nhận. Vui lòng kiểm tra kênh nhận OTP do quản trị cấu hình."
        if debug_mode:
            data["demo_otp"] = result["demo_otp"]
            message = f"Mã OTP demo đồ án: {result['demo_otp']}"
        return {
            "success": True,
            "message": message,
            "data": data
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
    from backend.config.db import DB_TYPE, get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    created_at_expr = "strftime('%Y-%m-%d', u.created_at) as created_at" if DB_TYPE != "mssql" else "CONVERT(VARCHAR(10), u.created_at, 120) as created_at"
    group_by_expr = "strftime('%Y-%m-%d', u.created_at)" if DB_TYPE != "mssql" else "CONVERT(VARCHAR(10), u.created_at, 120)"
    cursor.execute(f"""
        SELECT u.id, u.full_name, u.email, u.role, u.avatar_url,
               {created_at_expr},
               COUNT(o.id) as total_orders,
               COALESCE(SUM(o.net_amount), 0) as total_revenue
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id AND o.status = 'completed'
        GROUP BY u.id, u.full_name, u.email, u.role, u.avatar_url, {group_by_expr}
        ORDER BY total_revenue DESC, u.id ASC
    """)
    users = cursor.fetchall()
    conn.close()
    for u in users:
        u["total_revenue"] = float(u.get("total_revenue", 0.0) or 0.0)
        u["total_orders"] = int(u.get("total_orders", 0) or 0)
    return {"success": True, "data": users}


@router.put("/users/{user_id}/role")
def update_user_role(user_id: int, req: UpdateRoleRequest, request: Request, admin: dict = Depends(require_roles("admin"))):
    """Admin thay đổi phân quyền của một tài khoản."""
    if req.role not in ["admin", "manager", "sales", "user"]:
        raise HTTPException(status_code=400, detail="Vai trò không hợp lệ! Chỉ cho phép: admin, manager, sales, user.")

    from backend.config.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role, email FROM users WHERE id = ?", (user_id,))
    target = cursor.fetchone()
    if not target:
        conn.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (req.role, user_id))
    conn.commit()
    conn.close()
    from backend.modules.audit.audit_service import AuditService
    AuditService.record_audit("CHANGE_ROLE", "users", str(user_id), int(admin["sub"]), admin.get("email"), admin.get("role"),
        {"role": target["role"]}, {"role": req.role}, request.client.host if request.client else "", request.headers.get("user-agent", ""))
    return {"success": True, "message": f"Đã cập nhật vai trò của tài khoản thành '{req.role}'!"}

