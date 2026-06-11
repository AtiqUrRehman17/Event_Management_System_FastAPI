from fastapi import APIRouter, Depends, Request, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.dependencies import get_db, get_current_admin
from app.models.user import User
from app.schemas.audit import (
    AuditLogFilterParams, AuditLogListResponse, 
    AuditSummaryResponse, AuditActionCategoryEnum
)
from app.services.audit_service import AuditService
from app.utils.response import success_response

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs", response_model=dict)
async def get_audit_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    category: Optional[AuditActionCategoryEnum] = Query(None, description="Filter by category"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (event, booking, user)"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    start_date: Optional[datetime] = Query(None, description="Start date for filter"),
    end_date: Optional[datetime] = Query(None, description="End date for filter"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get audit logs with filters (Admin only).
    """
    filters = AuditLogFilterParams(
        user_id=user_id,
        action=action,
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit
    )
    
    logs, total, total_pages = AuditService.get_audit_logs(db, filters)
    
    return success_response(
        data={
            "logs": logs,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "filters_applied": {
                "user_id": user_id,
                "action": action,
                "category": category.value if category else None,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        },
        message="Audit logs retrieved successfully"
    )


@router.get("/summary", response_model=dict)
async def get_audit_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get audit log summary statistics (Admin only).
    """
    summary = AuditService.get_audit_summary(db)
    
    return success_response(
        data=summary,
        message="Audit summary retrieved successfully"
    )


@router.get("/user/{user_id}", response_model=dict)
async def get_user_audit_trail(
    user_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get audit trail for a specific user (Admin only).
    """
    audit_trail = AuditService.get_user_audit_trail(db, user_id, limit)
    
    return success_response(
        data={
            "user_id": user_id,
            "audit_trail": audit_trail,
            "total": len(audit_trail)
        },
        message="User audit trail retrieved successfully"
    )


@router.get("/entity/{entity_type}/{entity_id}", response_model=dict)
async def get_entity_audit_trail(
    entity_type: str,
    entity_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get audit trail for a specific entity (event, booking, user) (Admin only).
    """
    audit_trail = AuditService.get_entity_audit_trail(db, entity_type, entity_id, limit)
    
    return success_response(
        data={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "audit_trail": audit_trail,
            "total": len(audit_trail)
        },
        message="Entity audit trail retrieved successfully"
    )