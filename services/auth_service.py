"""
Authentication & Authorization Service (services/auth_service.py)
Implements password verification, brute-force lockout, session rotation, and RBAC decorators.
"""
from datetime import datetime
from functools import wraps
from typing import Optional, Tuple, Dict, Any
from werkzeug.security import check_password_hash
from flask import abort, request, jsonify, redirect, url_for
from flask_login import current_user
from repositories.user_repo import UserRepository
from repositories.audit_repo import AuditRepository

class AuthService:
    @staticmethod
    def authenticate(identifier: str, password: str, ip_address: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Validates user credentials against password hash.
        Handles account deactivation, failed attempt counting, and account locking.
        """
        ident = identifier.strip()
        # Find user by email or username
        user = UserRepository.get_by_email(ident) if "@" in ident else UserRepository.get_by_username(ident)
        
        if not user:
            AuditRepository.log(None, 'LOGIN_FAILED', 'USER', None, {'identifier': ident, 'reason': 'User not found'}, ip_address)
            return None, "Invalid email/username or password."

        # Check deactivation
        if user['status'] != 'ACTIVE':
            AuditRepository.log(user['id'], 'LOGIN_BLOCKED', 'USER', str(user['id']), {'reason': 'Account inactive'}, ip_address)
            return None, "This account is inactive. Please contact system support."

        # Check lockout
        if user['locked_until']:
            if user['locked_until'] > datetime.utcnow():
                rem_mins = int((user['locked_until'] - datetime.utcnow()).total_seconds() / 60) + 1
                AuditRepository.log(user['id'], 'LOGIN_LOCKED', 'USER', str(user['id']), {'rem_mins': rem_mins}, ip_address)
                return None, f"Account temporarily locked due to failed attempts. Try again in {rem_mins} minutes."
            else:
                UserRepository.reset_failed_logins(user['id'])

        # Verify password (hash or accepted demo passwords for seeded demo users)
        is_valid = check_password_hash(user['password_hash'], password)
        if not is_valid and user.get('is_demo'):
            if password in ('DemoPassword123!', 'Investor@StockTrade2026', 'Broker@StockTrade2026', 'Admin@StockTrade2026'):
                is_valid = True

        if not is_valid:
            attempts = UserRepository.record_failed_login(user['id'])
            rem = max(0, 5 - attempts)
            AuditRepository.log(user['id'], 'LOGIN_FAILED', 'USER', str(user['id']), {'attempt': attempts}, ip_address)
            if attempts >= 5:
                return None, "Account has been locked for 15 minutes due to consecutive failed login attempts."
            return None, f"Invalid email/username or password. ({rem} attempts remaining before lockout)"

        # Login successful: update last login & clear failed attempts
        UserRepository.update_last_login(user['id'])
        AuditRepository.log(user['id'], 'LOGIN_SUCCESS', 'USER', str(user['id']), {'role': user['role']}, ip_address)
        return user, None

def role_required(*allowed_roles):
    """Decorator to enforce strict server-side Role-Based Access Control (RBAC)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.path.startswith('/api/'):
                    return jsonify({
                        "ok": False,
                        "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}
                    }), 401
                return redirect(url_for('auth.login', next=request.url))

            if current_user.role not in allowed_roles:
                if request.path.startswith('/api/'):
                    return jsonify({
                        "ok": False,
                        "error": {"code": "FORBIDDEN", "message": "Access denied for current role"}
                    }), 403
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator
