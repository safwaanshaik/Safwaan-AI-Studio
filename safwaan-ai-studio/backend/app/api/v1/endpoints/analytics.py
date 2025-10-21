"""
SAFWAAN AI STUDIO - Analytics Endpoints
User and system analytics, insights, and reporting.

This module provides:
- User behavior analytics
- Video performance metrics
- System usage statistics
- Revenue and monetization analytics
- Real-time dashboards
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.services.analytics_service import AnalyticsService
from app.utils.exceptions import AuthorizationError
from app.core.monitoring import record_error

router = APIRouter()


@router.get("/dashboard")
async def get_user_dashboard_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get personalized dashboard analytics for current user.

    - **days**: Number of days to analyze
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        analytics_service = AnalyticsService(db)

        dashboard_data = await analytics_service.get_user_dashboard_analytics(
            current_user["id"], days
        )

        return dashboard_data

    except Exception as e:
        record_error("get_dashboard_analytics_error", "analytics")
        raise


@router.get("/videos/performance")
async def get_video_performance_analytics(
    video_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get video performance analytics.

    - **video_id**: Specific video ID (optional)
    - **days**: Number of days to analyze
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        analytics_service = AnalyticsService(db)

        if video_id:
            # Single video analytics
            analytics = await analytics_service.get_video_analytics(
                video_id, current_user["id"], days
            )
        else:
            # All user videos analytics
            analytics = await analytics_service.get_user_videos_analytics(
                current_user["id"], days
            )

        return analytics

    except Exception as e:
        record_error("get_video_analytics_error", "analytics")
        raise


@router.get("/usage")
async def get_usage_analytics(
    period: str = Query("month", regex="^(day|week|month|year)$"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user usage analytics and statistics.

    - **period**: Time period for analysis
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        analytics_service = AnalyticsService(db)

        usage_data = await analytics_service.get_user_usage_analytics(
            current_user["id"], period
        )

        return usage_data

    except Exception as e:
        record_error("get_usage_analytics_error", "analytics")
        raise


@router.get("/trends")
async def get_content_trends(
    category: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get content trends and insights.

    - **category**: Content category filter
    - **days**: Number of days to analyze
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        analytics_service = AnalyticsService(db)

        trends_data = await analytics_service.get_content_trends(
            current_user["id"], category, days
        )

        return trends_data

    except Exception as e:
        record_error("get_trends_error", "analytics")
        raise


# Admin-only analytics endpoints
@router.get("/admin/overview", response_model=Dict[str, Any])
async def get_system_overview_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get system-wide analytics overview (admin only).

    - **days**: Number of days to analyze
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        analytics_service = AnalyticsService(db)

        overview_data = await analytics_service.get_system_overview_analytics(days)

        return overview_data

    except Exception as e:
        record_error("get_system_overview_error", "analytics")
        raise


@router.get("/admin/users", response_model=Dict[str, Any])
async def get_user_analytics(
    days: int = Query(30, ge=1, le=365),
    segment: Optional[str] = Query(None, regex="^(free|basic|pro|enterprise)$"),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user analytics and segmentation (admin only).

    - **days**: Number of days to analyze
    - **segment**: User segment filter
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        analytics_service = AnalyticsService(db)

        user_analytics = await analytics_service.get_user_segmentation_analytics(
            days, segment
        )

        return user_analytics

    except Exception as e:
        record_error("get_user_analytics_error", "analytics")
        raise


@router.get("/admin/revenue", response_model=Dict[str, Any])
async def get_revenue_analytics(
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get revenue and monetization analytics (admin only).

    - **period**: Time period for analysis
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        analytics_service = AnalyticsService(db)

        revenue_data = await analytics_service.get_revenue_analytics(period)

        return revenue_data

    except Exception as e:
        record_error("get_revenue_analytics_error", "analytics")
        raise


@router.get("/admin/performance", response_model=Dict[str, Any])
async def get_system_performance_analytics(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get system performance analytics (admin only).

    - **hours**: Number of hours to analyze
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        analytics_service = AnalyticsService(db)

        performance_data = await analytics_service.get_system_performance_analytics(hours)

        return performance_data

    except Exception as e:
        record_error("get_performance_analytics_error", "analytics")
        raise


@router.get("/admin/content", response_model=Dict[str, Any])
async def get_content_analytics(
    days: int = Query(30, ge=1, le=365),
    content_type: Optional[str] = Query(None, regex="^(video|image|text)$"),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get content generation analytics (admin only).

    - **days**: Number of days to analyze
    - **content_type**: Content type filter
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        analytics_service = AnalyticsService(db)

        content_analytics = await analytics_service.get_content_generation_analytics(
            days, content_type
        )

        return content_analytics

    except Exception as e:
        record_error("get_content_analytics_error", "analytics")
        raise


@router.get("/admin/export")
async def export_analytics_data(
    report_type: str = Query(..., regex="^(users|revenue|performance|content)$"),
    start_date: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$"),
    format: str = Query("json", regex="^(json|csv|excel)$"),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Export analytics data for reporting (admin only).

    - **report_type**: Type of report to export
    - **start_date**: Start date (YYYY-MM-DD)
    - **end_date**: End date (YYYY-MM-DD)
    - **format**: Export format
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        analytics_service = AnalyticsService(db)

        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if end < start:
            raise ValueError("End date must be after start date")

        export_data = await analytics_service.export_analytics_data(
            report_type, start, end, format
        )

        return export_data

    except ValueError as e:
        from app.utils.exceptions import ValidationError
        raise ValidationError(str(e))
    except Exception as e:
        record_error("export_analytics_error", "analytics")
        raise


@router.post("/events/track")
async def track_user_event(
    event_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Track user interaction events for analytics.

    - **event_data**: Event data to track
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        analytics_service = AnalyticsService(db)

        # Add user context to event
        event_data["user_id"] = current_user["id"]
        event_data["timestamp"] = datetime.utcnow()

        await analytics_service.track_event(event_data)

        return {"message": "Event tracked successfully"}

    except Exception as e:
        record_error("track_event_error", "analytics")
        raise


@router.get("/insights/recommendations")
async def get_personalized_recommendations(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get personalized recommendations based on user behavior.

    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        analytics_service = AnalyticsService(db)

        recommendations = await analytics_service.get_personalized_recommendations(
            current_user["id"]
        )

        return recommendations

    except Exception as e:
        record_error("get_recommendations_error", "analytics")
        raise