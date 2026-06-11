from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import Request
from app.models.audit_log import AuditLog, AuditActionType, AuditActionCategory
from app.models.user import User
from app.schemas.audit import AuditLogFilterParams, AuditLogResponse
from app.utils.datetime_utils import get_current_utc
import json
import logging

logger = logging.getLogger(__name__)


class AuditService:
    
    @staticmethod
    def log_action(
        db: Session,
        user_id: Optional[int],
        action: AuditActionType,
        category: AuditActionCategory,
        request: Optional[Request] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        details: Optional[Dict] = None
    ) -> AuditLog:
        """
        Log an action to the audit log.
        """
        # Get IP address from request
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
        
        # Convert dict values to JSON strings
        old_value_str = json.dumps(old_value) if old_value else None
        new_value_str = json.dumps(new_value) if new_value else None
        
        audit_log = AuditLog(
            user_id=user_id,
            action=action.value,
            category=category.value,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value_str,
            new_value=new_value_str,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        logger.info(f"Audit log created: {action.value} by user {user_id}")
        
        return audit_log
    
    @staticmethod
    def get_audit_logs(
        db: Session,
        filters: AuditLogFilterParams
    ) -> tuple:
        """
        Get audit logs with filtering and pagination.
        """
        query = db.query(AuditLog)
        
        # Apply filters
        if filters.user_id:
            query = query.filter(AuditLog.user_id == filters.user_id)
        
        if filters.action:
            query = query.filter(AuditLog.action == filters.action)
        
        if filters.category:
            query = query.filter(AuditLog.category == filters.category.value)
        
        if filters.entity_type:
            query = query.filter(AuditLog.entity_type == filters.entity_type)
        
        if filters.entity_id:
            query = query.filter(AuditLog.entity_id == filters.entity_id)
        
        if filters.start_date:
            query = query.filter(AuditLog.created_at >= filters.start_date)
        
        if filters.end_date:
            query = query.filter(AuditLog.created_at <= filters.end_date)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (filters.page - 1) * filters.limit
        logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(filters.limit).all()
        
        total_pages = (total + filters.limit - 1) // filters.limit if total > 0 else 0
        
        # Enrich logs with user information
        enriched_logs = []
        for log in logs:
            user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
            enriched_logs.append({
                "id": log.id,
                "user_id": log.user_id,
                "username": user.username if user else None,
                "user_email": user.email if user else None,
                "action": log.action,
                "category": log.category,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "details": log.details,
                "created_at": log.created_at
            })
        
        return enriched_logs, total, total_pages
    
    @staticmethod
    def get_audit_summary(db: Session) -> Dict[str, Any]:
        """
        Get summary statistics for audit logs.
        """
        total_logs = db.query(AuditLog).count()
        
        # Logs by category
        logs_by_category = db.query(
            AuditLog.category, func.count(AuditLog.id)
        ).group_by(AuditLog.category).all()
        
        logs_by_category_dict = {cat: count for cat, count in logs_by_category}
        
        # Logs by action (top 10)
        logs_by_action = db.query(
            AuditLog.action, func.count(AuditLog.id)
        ).group_by(AuditLog.action).order_by(func.count(AuditLog.id).desc()).limit(10).all()
        
        logs_by_action_dict = {action: count for action, count in logs_by_action}
        
        # Recent activity (last 24 hours)
        day_ago = get_current_utc() - __import__('datetime').timedelta(hours=24)
        recent_logs = db.query(AuditLog).filter(
            AuditLog.created_at >= day_ago
        ).order_by(desc(AuditLog.created_at)).limit(20).all()
        
        recent_activity = []
        for log in recent_logs:
            user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
            recent_activity.append({
                "id": log.id,
                "user_id": log.user_id,
                "username": user.username if user else None,
                "action": log.action,
                "category": log.category,
                "created_at": log.created_at
            })
        
        # Top users by activity
        top_users = db.query(
            AuditLog.user_id, func.count(AuditLog.id).label("log_count")
        ).group_by(AuditLog.user_id).order_by(func.count(AuditLog.id).desc()).limit(10).all()
        
        top_users_data = []
        for user_id, count in top_users:
            user = db.query(User).filter(User.id == user_id).first() if user_id else None
            top_users_data.append({
                "user_id": user_id,
                "username": user.username if user else "System/Unknown",
                "log_count": count
            })
        
        return {
            "total_logs": total_logs,
            "logs_by_category": logs_by_category_dict,
            "logs_by_action": logs_by_action_dict,
            "recent_activity": recent_activity,
            "top_users": top_users_data
        }
    
    @staticmethod
    def get_user_audit_trail(db: Session, user_id: int, limit: int = 50) -> List[Dict]:
        """
        Get audit trail for a specific user.
        """
        logs = db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()
        
        result = []
        for log in logs:
            result.append({
                "id": log.id,
                "action": log.action,
                "category": log.category,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at
            })
        
        return result
    
    @staticmethod
    def get_entity_audit_trail(db: Session, entity_type: str, entity_id: int, limit: int = 50) -> List[Dict]:
        """
        Get audit trail for a specific entity (e.g., event, booking).
        """
        logs = db.query(AuditLog).filter(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()
        
        result = []
        for log in logs:
            user = db.query(User).filter(User.id == log.user_id).first() if log.user_id else None
            result.append({
                "id": log.id,
                "user_id": log.user_id,
                "username": user.username if user else None,
                "action": log.action,
                "category": log.category,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "details": log.details,
                "created_at": log.created_at
            })
        
        return result