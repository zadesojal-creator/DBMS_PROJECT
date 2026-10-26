"""
Audit Repository (repositories/audit_repo.py)
System security audit logging and traceability.
"""
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import text, insert
from models.db import get_db_connection, get_db_transaction
from models.schema import audit_logs_table

class AuditRepository:
    @staticmethod
    def log(
        user_id: Optional[int], action: str, entity_type: str,
        entity_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        with get_db_transaction() as conn:
            stmt = insert(audit_logs_table).values(
                user_id=user_id,
                action=action.upper(),
                entity_type=entity_type.upper(),
                entity_id=str(entity_id) if entity_id else None,
                details=json.dumps(details) if details else None,
                ip_address=ip_address,
                created_at=datetime.utcnow()
            )
            conn.execute(stmt)

    @staticmethod
    def list_logs(limit: int = 100, action: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            query = """
                SELECT 
                    a.id, a.user_id, u.username, u.role, a.action,
                    a.entity_type, a.entity_id, a.details, a.ip_address, a.created_at
                FROM Audit_Logs a
                LEFT JOIN Users u ON a.user_id = u.id
                WHERE 1=1
            """
            params: Dict[str, Any] = {"limit": limit}
            if action:
                query += " AND a.action = :action"
                params["action"] = action.upper()
            query += " ORDER BY a.created_at DESC LIMIT :limit"
            
            rows = conn.execute(text(query), params).mappings().all()
            return [dict(r) for r in rows]
