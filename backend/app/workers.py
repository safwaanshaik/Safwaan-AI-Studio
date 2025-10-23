from celery import Celery
import os
import asyncio
from backend.app.services.ai_service import AIService
from backend.app.services.social_poster import SocialPosterService
from backend.app.core.database import async_session_maker
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models.user import VideoProject
import logging

logger = logging.getLogger(__name__)

# Initialize Celery
celery = Celery(
    "cinematrix",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0")
)

celery.conf.task_routes = {
    "workers.generate_video": {"queue": "gen"},
    "workers.post_to_social": {"queue": "social"},
    "workers.track_revenue": {"queue": "revenue"}
}

@celery.task(name="workers.generate_video")
def generate_video(job_id: str, payload: dict):
    """Generate video using AI services."""
    try:
        logger.info(f"Starting video generation for job {job_id}")

        # Run async function in sync context
        result = asyncio.run(_generate_video_async(job_id, payload))

        logger.info(f"Video generation completed for job {job_id}")
        return result

    except Exception as e:
        logger.error(f"Video generation failed for job {job_id}: {e}")
        # Update job status to failed
        asyncio.run(_update_job_status(job_id, "failed", error=str(e)))
        raise

@celery.task(name="workers.post_to_social")
def post_to_social(video_id: int, platform_urls: dict):
    """Post video to social media platforms."""
    try:
        logger.info(f"Starting social media posting for video {video_id}")

        # Run async function in sync context
        result = asyncio.run(_post_to_social_async(video_id, platform_urls))

        logger.info(f"Social media posting completed for video {video_id}")
        return result

    except Exception as e:
        logger.error(f"Social media posting failed for video {video_id}: {e}")
        raise

@celery.task(name="workers.track_revenue")
def track_revenue():
    """Track revenue from all platforms."""
    try:
        logger.info("Starting revenue tracking")

        # Run async function in sync context
        result = asyncio.run(_track_revenue_async())

        logger.info("Revenue tracking completed")
        return result

    except Exception as e:
        logger.error(f"Revenue tracking failed: {e}")
        raise

async def _generate_video_async(job_id: str, payload: dict):
    """Async video generation logic."""
    prompt = payload.get("prompt", "")
    duration = payload.get("duration", 30)

    # Update job status
    await _update_job_status(job_id, "running", stage="initializing")

    # Generate video using AI service
    async with AIService() as ai_service:
        await _update_job_status(job_id, "running", stage="generating_video", progress=25)

        video_url = await ai_service.generate_video(prompt, duration)

        await _update_job_status(job_id, "running", stage="enhancing_video", progress=75)

        # Enhance video quality
        enhanced_url = await ai_service.enhance_video(video_url)

        await _update_job_status(job_id, "running", stage="generating_captions", progress=90)

        # Generate captions and hashtags
        captions_data = await ai_service.generate_captions(prompt)

    # Update database with results
    async with async_session_maker() as db:
        # Find video project by job_id (assuming job_id is video_id for now)
        try:
            video_id = int(job_id)
            video_project = await db.get(VideoProject, video_id)
            if video_project:
                video_project.video_url = enhanced_url
                video_project.status = "completed"
                video_project.hashtags = captions_data.get("hashtags", [])
                await db.commit()
        except ValueError:
            # job_id might not be video_id, handle accordingly
            pass

    await _update_job_status(job_id, "completed", progress=100, output_url=enhanced_url)

    return {
        "job_id": job_id,
        "video_url": enhanced_url,
        "captions": captions_data
    }

async def _post_to_social_async(video_id: int, platform_urls: dict):
    """Async social media posting logic."""
    async with async_session_maker() as db:
        video_project = await db.get(VideoProject, video_id)
        if not video_project:
            raise Exception(f"Video project {video_id} not found")

        # Post to all platforms
        async with SocialPosterService() as poster:
            posted_urls = await poster.post_to_all_platforms(
                video_project.video_url,
                video_project.prompt,
                video_id,
                db
            )

        # Update video project with platform URLs
        video_project.platform_urls = posted_urls
        await db.commit()

        return posted_urls

async def _track_revenue_async():
    """Async revenue tracking logic."""
    from backend.app.services.revenue_tracker import RevenueTracker

    async with RevenueTracker() as tracker:
        total_revenue = await tracker.track_all_platforms(None)  # Track for all users

        # Send revenue report
        await tracker.send_revenue_report(None)  # Send for admin

        return {"total_revenue": total_revenue}

async def _update_job_status(job_id: str, status: str, stage: str = "", progress: int = 0,
                           output_url: str = "", error: str = ""):
    """Update job status in storage."""
    # This would integrate with your job storage system
    # For now, we'll use a simple approach
    try:
        # You can implement proper job storage here
        # For Railway deployment, consider using Redis or database
        logger.info(f"Job {job_id} status: {status}, stage: {stage}, progress: {progress}%")
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")

# Periodic tasks
@celery.task(name="workers.discover_trends")
def discover_trends():
    """Discover trending topics periodically."""
    try:
        logger.info("Starting trend discovery")

        # Run async function in sync context
        result = asyncio.run(_discover_trends_async())

        logger.info("Trend discovery completed")
        return result

    except Exception as e:
        logger.error(f"Trend discovery failed: {e}")
        raise

async def _discover_trends_async():
    """Async trend discovery logic."""
    from trend_engine.viral_trend_finder import ViralTrendFinder

    async with async_session_maker() as db:
        async with ViralTrendFinder() as trend_finder:
            trends = await trend_finder.find_trending_topics(db)

            return {"trends_found": len(trends)}

# Auto-generate videos from top trends
@celery.task(name="workers.auto_generate_from_trends")
def auto_generate_from_trends():
    """Automatically generate videos from top trending topics."""
    try:
        logger.info("Starting auto video generation from trends")

        # Run async function in sync context
        result = asyncio.run(_auto_generate_from_trends_async())

        logger.info("Auto video generation completed")
        return result

    except Exception as e:
        logger.error(f"Auto video generation failed: {e}")
        raise

async def _auto_generate_from_trends_async():
    """Async auto video generation logic."""
    from trend_engine.viral_trend_finder import ViralTrendFinder

    async with async_session_maker() as db:
        async with ViralTrendFinder() as trend_finder:
            # Get top 3 viral trends
            top_trends = await trend_finder.get_top_trends(db, limit=3)

            generated_count = 0
            for trend in top_trends:
                if trend["virality_score"] > 70:  # Only very viral trends
                    # Create video generation job
                    job_id = f"auto_{trend['id']}_{int(asyncio.get_event_loop().time())}"

                    payload = {
                        "prompt": f"Create a viral video about: {trend['trend_name']}. {trend['description']}",
                        "duration": 30,
                        "auto_post": True
                    }

                    # Queue video generation
                    from workers import generate_video
                    generate_video.delay(job_id, payload)
                    generated_count += 1

            return {"videos_generated": generated_count}