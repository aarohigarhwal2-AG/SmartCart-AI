from fastapi import APIRouter, Query
from typing import List
from ..models.schemas import MerchantAnalytics, AuditLogItem
from ..services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Merchant Analytics & Safety Audit"])

@router.get("", response_model=MerchantAnalytics)
async def get_merchant_analytics():
    """Returns merchant growth metrics and conversion funnel data."""
    return AnalyticsService.get_metrics()

@router.get("/audit-logs", response_model=List[AuditLogItem])
async def get_audit_trail(limit: int = Query(50, le=200)):
    """Returns recent safety audit log entries."""
    return AnalyticsService.get_audit_logs(limit=limit)
