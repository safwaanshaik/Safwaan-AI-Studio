import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from backend.app.core.config import settings
from backend.app.db.models.user import RevenueRecord, VideoProject
from sqlalchemy.ext.asyncio import AsyncSession
import os

logger = logging.getLogger(__name__)

class RevenueTracker:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def track_all_platforms(self, db: AsyncSession):
        """Track revenue from all platforms for all videos."""
        try:
            # Get all video projects with platform URLs
            result = await db.execute(
                db.query(VideoProject).filter(
                    VideoProject.platform_urls.isnot(None),
                    VideoProject.status == "completed"
                )
            )
            videos = result.scalars().all()

            total_revenue = 0.0
            for video in videos:
                video_revenue = await self._track_video_revenue(video, db)
                total_revenue += video_revenue

            logger.info(f"Tracked revenue for {len(videos)} videos: ${total_revenue:.2f}")
            return total_revenue

        except Exception as e:
            logger.error(f"Revenue tracking error: {e}")
            return 0.0

    async def _track_video_revenue(self, video: VideoProject, db: AsyncSession) -> float:
        """Track revenue for a specific video across all platforms."""
        total_video_revenue = 0.0
        platform_urls = video.platform_urls or {}

        # Track YouTube revenue
        if "youtube" in platform_urls:
            youtube_revenue = await self._track_youtube_revenue(platform_urls["youtube"], video.id, db)
            total_video_revenue += youtube_revenue

        # Track TikTok revenue
        if "tiktok" in platform_urls:
            tiktok_revenue = await self._track_tiktok_revenue(platform_urls["tiktok"], video.id, db)
            total_video_revenue += tiktok_revenue

        # Track Instagram revenue
        if "instagram" in platform_urls:
            instagram_revenue = await self._track_instagram_revenue(platform_urls["instagram"], video.id, db)
            total_video_revenue += instagram_revenue

        # Track Facebook revenue
        if "facebook" in platform_urls:
            facebook_revenue = await self._track_facebook_revenue(platform_urls["facebook"], video.id, db)
            total_video_revenue += facebook_revenue

        # Update video revenue
        video.revenue = total_video_revenue
        await db.commit()

        return total_video_revenue

    async def _track_youtube_revenue(self, video_url: str, video_id: int, db: AsyncSession) -> float:
        """Track YouTube revenue for a video."""
        try:
            # Extract video ID from URL
            video_id_yt = self._extract_youtube_id(video_url)
            if not video_id_yt:
                return 0.0

            # YouTube Analytics API
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "statistics,monetization",
                "id": video_id_yt,
                "key": getattr(settings, 'youtube_api_key', '')
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("items"):
                        stats = data["items"][0].get("statistics", {})
                        views = int(stats.get("viewCount", 0))

                        # Estimate revenue (YouTube pays ~$0.001-0.005 per view for Shorts)
                        estimated_revenue = views * 0.002  # Conservative estimate

                        # Save revenue record
                        await self._save_revenue_record(video_id, "youtube", estimated_revenue, db)
                        return estimated_revenue

        except Exception as e:
            logger.error(f"YouTube revenue tracking error: {e}")

        return 0.0

    async def _track_tiktok_revenue(self, video_url: str, video_id: int, db: AsyncSession) -> float:
        """Track TikTok revenue for a video."""
        try:
            # TikTok Creator Fund (if available)
            # For now, estimate based on views
            views = await self._get_tiktok_views(video_url)

            # TikTok pays ~$0.02-0.04 per 1000 views for eligible creators
            estimated_revenue = (views / 1000) * 0.03

            if estimated_revenue > 0:
                await self._save_revenue_record(video_id, "tiktok", estimated_revenue, db)
                return estimated_revenue

        except Exception as e:
            logger.error(f"TikTok revenue tracking error: {e}")

        return 0.0

    async def _track_instagram_revenue(self, video_url: str, video_id: int, db: AsyncSession) -> float:
        """Track Instagram revenue for a video."""
        try:
            # Instagram Bonuses for Reels
            views = await self._get_instagram_views(video_url)

            # Instagram pays ~$0.01-0.03 per 1000 views for Reels
            estimated_revenue = (views / 1000) * 0.02

            if estimated_revenue > 0:
                await self._save_revenue_record(video_id, "instagram", estimated_revenue, db)
                return estimated_revenue

        except Exception as e:
            logger.error(f"Instagram revenue tracking error: {e}")

        return 0.0

    async def _track_facebook_revenue(self, video_url: str, video_id: int, db: AsyncSession) -> float:
        """Track Facebook revenue for a video."""
        try:
            # Facebook in-stream ads
            views = await self._get_facebook_views(video_url)

            # Facebook pays ~$0.001-0.01 per view
            estimated_revenue = views * 0.005

            if estimated_revenue > 0:
                await self._save_revenue_record(video_id, "facebook", estimated_revenue, db)
                return estimated_revenue

        except Exception as e:
            logger.error(f"Facebook revenue tracking error: {e}")

        return 0.0

    async def _get_tiktok_views(self, video_url: str) -> int:
        """Get TikTok video view count."""
        try:
            # This would normally use TikTok's API
            # For now, return estimated views
            return 5000  # Placeholder
        except Exception:
            return 0

    async def _get_instagram_views(self, video_url: str) -> int:
        """Get Instagram video view count."""
        try:
            # This would normally use Instagram's API
            # For now, return estimated views
            return 3000  # Placeholder
        except Exception:
            return 0

    async def _get_facebook_views(self, video_url: str) -> int:
        """Get Facebook video view count."""
        try:
            # This would normally use Facebook's API
            # For now, return estimated views
            return 2000  # Placeholder
        except Exception:
            return 0

    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        import re
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    async def _save_revenue_record(self, video_id: int, platform: str, amount: float, db: AsyncSession):
        """Save revenue record to database."""
        try:
            revenue_record = RevenueRecord(
                video_project_id=video_id,
                platform=platform,
                amount=amount,
                currency="USD"
            )
            db.add(revenue_record)
            await db.commit()
        except Exception as e:
            logger.error(f"Error saving revenue record: {e}")

    async def get_total_revenue(self, db: AsyncSession, user_id: Optional[int] = None) -> Dict[str, float]:
        """Get total revenue statistics."""
        try:
            from sqlalchemy import func, extract

            # Base query
            query = db.query(
                func.sum(RevenueRecord.amount).label('total'),
                RevenueRecord.platform
            ).group_by(RevenueRecord.platform)

            if user_id:
                query = query.join(VideoProject).filter(VideoProject.user_id == user_id)

            result = await db.execute(query)
            platform_totals = {row[1]: float(row[0] or 0) for row in result}

            # Calculate monthly revenue
            current_month = datetime.now().month
            current_year = datetime.now().year

            monthly_query = db.query(func.sum(RevenueRecord.amount))
            if user_id:
                monthly_query = monthly_query.join(VideoProject).filter(VideoProject.user_id == user_id)

            monthly_query = monthly_query.filter(
                extract('month', RevenueRecord.recorded_at) == current_month,
                extract('year', RevenueRecord.recorded_at) == current_year
            )

            monthly_result = await db.execute(monthly_query)
            monthly_revenue = float(monthly_result.scalar() or 0)

            return {
                "total_revenue": sum(platform_totals.values()),
                "monthly_revenue": monthly_revenue,
                "platform_breakdown": platform_totals
            }

        except Exception as e:
            logger.error(f"Error getting revenue stats: {e}")
            return {
                "total_revenue": 0.0,
                "monthly_revenue": 0.0,
                "platform_breakdown": {}
            }

    async def send_revenue_report(self, db: AsyncSession, user_id: Optional[int] = None):
        """Send revenue report via email/SMS."""
        try:
            revenue_stats = await self.get_total_revenue(db, user_id)

            # Format report
            report = f"""
🎉 Revenue Report

💰 Total Revenue: ${revenue_stats['total_revenue']:.2f}
📅 Monthly Revenue: ${revenue_stats['monthly_revenue']:.2f}

📊 Platform Breakdown:
"""

            for platform, amount in revenue_stats['platform_breakdown'].items():
                report += f"  {platform.title()}: ${amount:.2f}\n"

            # Send via email (if configured)
            await self._send_email_report(report)

            # Send via SMS (if configured)
            await self._send_sms_report(report)

            logger.info("Revenue report sent successfully")

        except Exception as e:
            logger.error(f"Error sending revenue report: {e}")

    async def _send_email_report(self, report: str):
        """Send revenue report via email."""
        try:
            if not hasattr(settings, 'resend_api_key') or not settings.resend_api_key:
                return

            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "from": "revenue@safwaan-ai-studio.com",
                "to": [getattr(settings, 'admin_email', 'admin@safwaan-ai-studio.com')],
                "subject": "Daily Revenue Report - Safwaan AI Studio",
                "text": report
            }

            async with self.session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    logger.info("Revenue report email sent")
                else:
                    logger.error(f"Failed to send revenue report email: {response.status}")

        except Exception as e:
            logger.error(f"Email sending error: {e}")

    async def _send_sms_report(self, report: str):
        """Send revenue report via SMS."""
        try:
            if not hasattr(settings, 'twilio_account_sid') or not settings.twilio_account_sid:
                return

            # Twilio SMS API
            url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
            auth = aiohttp.BasicAuth(settings.twilio_account_sid, getattr(settings, 'twilio_auth_token', ''))

            data = {
                "From": getattr(settings, 'twilio_phone_number', ''),
                "To": getattr(settings, 'admin_phone', ''),
                "Body": f"Safwaan AI Revenue Report:\n{report[:160]}"  # SMS length limit
            }

            async with self.session.post(url, auth=auth, data=data) as response:
                if response.status == 201:
                    logger.info("Revenue report SMS sent")
                else:
                    logger.error(f"Failed to send revenue report SMS: {response.status}")

        except Exception as e:
            logger.error(f"SMS sending error: {e}")

    async def get_revenue_analytics(self, db: AsyncSession, days: int = 30) -> Dict[str, any]:
        """Get detailed revenue analytics."""
        try:
            from sqlalchemy import func, extract, desc
            from datetime import datetime, timedelta

            start_date = datetime.now() - timedelta(days=days)

            # Daily revenue over the period
            daily_query = db.query(
                func.date(RevenueRecord.recorded_at).label('date'),
                func.sum(RevenueRecord.amount).label('revenue')
            ).filter(
                RevenueRecord.recorded_at >= start_date
            ).group_by(
                func.date(RevenueRecord.recorded_at)
            ).order_by(desc('date'))

            daily_result = await db.execute(daily_query)
            daily_revenue = [{"date": str(row[0]), "revenue": float(row[1] or 0)} for row in daily_result]

            # Platform performance
            platform_query = db.query(
                RevenueRecord.platform,
                func.sum(RevenueRecord.amount).label('total'),
                func.avg(RevenueRecord.amount).label('average'),
                func.count(RevenueRecord.id).label('transactions')
            ).filter(
                RevenueRecord.recorded_at >= start_date
            ).group_by(RevenueRecord.platform)

            platform_result = await db.execute(platform_query)
            platform_stats = {}
            for row in platform_result:
                platform_stats[row[0]] = {
                    "total": float(row[1] or 0),
                    "average": float(row[2] or 0),
                    "transactions": row[3]
                }

            return {
                "daily_revenue": daily_revenue,
                "platform_stats": platform_stats,
                "period_days": days
            }

        except Exception as e:
            logger.error(f"Error getting revenue analytics: {e}")
            return {
                "daily_revenue": [],
                "platform_stats": {},
                "period_days": days
            }