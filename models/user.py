"""
Flask-Login User Model (models/user.py)
"""
from typing import Optional, Dict, Any
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, data: Dict[str, Any]):
        self.id = data["id"]
        self.username = data["username"]
        self.email = data["email"]
        self.full_name = data["full_name"]
        self.role = data["role"]
        self.status = data["status"]
        self.is_demo = bool(data.get("is_demo", False))
        self.failed_login_attempts = data.get("failed_login_attempts", 0)
        self.locked_until = data.get("locked_until")
        self.last_login_at = data.get("last_login_at")

    @property
    def is_active(self) -> bool:
        """Deactivated users cannot log in or maintain active sessions."""
        return self.status == 'ACTIVE'

    @property
    def is_admin(self) -> bool:
        return self.role == 'ADMIN'

    @property
    def is_broker(self) -> bool:
        return self.role == 'BROKER'

    @property
    def is_investor(self) -> bool:
        return self.role == 'INVESTOR'

    def get_id(self) -> str:
        return str(self.id)
