from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import List, Optional
from pydantic import BaseModel

# Database and services
try:
    from backend.app.core.config import settings
    from backend.app.core.database import init_database, close_database, get_db_session
    from backend.app.db.models.user import VideoProject, Trend
    from backend.app.services.ai_service import AIService
    from backend.app.services.social_poster import SocialPosterService
    from trend_engine.viral_trend_finder import ViralTrendFinder
    from sqlalchemy.ext.asyncio import AsyncSession
    FULL_FEATURES = True
except ImportError as e:
    logging.warning(f"Some features not available: {e}")
    FULL_FEATURES = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Safwaan AI Studio - Viral Video Money Printing Machine")
    if FULL_FEATURES:
        try:
            await init_database()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

        # Start background tasks
        asyncio.create_task(run_trend_finder())

    yield

    # Shutdown
    logger.info("Shutting down Safwaan AI Studio")
    if FULL_FEATURES:
        try:
            await close_database()
        except Exception as e:
            logger.error(f"Database close failed: {e}")

app = FastAPI(
    title="Safwaan AI Studio - Viral Video Money Printing Machine",
    description="AI-powered viral video generation and automated social media posting for maximum revenue",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class VideoGenerationRequest(BaseModel):
    prompt: str
    duration: Optional[int] = 30
    auto_post: bool = True

class VideoResponse(BaseModel):
    id: int
    prompt: str
    status: str
    video_url: Optional[str]
    platform_urls: Optional[dict]
    created_at: str

class TrendResponse(BaseModel):
    id: int
    platform: str
    trend_name: str
    virality_score: float
    view_count: int
    description: str

@app.get("/")
async def root():
    """Root endpoint with system status."""
    features_status = []
    if FULL_FEATURES:
        features_status = [
            "AI Video Generation",
            "Automated Social Media Posting",
            "Trend Detection",
            "Revenue Tracking",
            "24/7 Money Making"
        ]
    else:
        features_status = ["Basic API (Full features loading...)"]

    return {
        "message": "Safwaan AI Studio - Viral Video Money Printing Machine is running!",
        "version": "1.0.0",
        "status": "active",
        "features": features_status,
        "full_features_loaded": FULL_FEATURES,
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development"),
        "endpoints": {
            "health": "/health",
            "generate_video": "POST /generate-video",
            "get_video": "GET /video/{id}",
            "trending_topics": "GET /trending-topics",
            "discover_trends": "POST /discover-trends"
        },
        "ready_for_use": True
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development"),
        "full_features_loaded": FULL_FEATURES
    }

    if FULL_FEATURES:
        try:
            # Test database connection
            from backend.app.core.database import check_database_health
            db_healthy = await check_database_health()
            health_status["database"] = "healthy" if db_healthy else "unhealthy"
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"

    return health_status

@app.post("/generate-video", response_model=VideoResponse)
async def generate_video(
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks
):
    """Generate a video from prompt and optionally auto-post."""
    if not FULL_FEATURES:
        raise HTTPException(status_code=503, detail="Full features not available yet")

    try:
        # Create video project
        from backend.app.core.database import async_session_maker
        async with async_session_maker() as db:
            video_project = VideoProject(
                user_id=1,  # System user
                prompt=request.prompt,
                status="generating"
            )
            db.add(video_project)
            await db.commit()
            await db.refresh(video_project)

        # Start background generation
        background_tasks.add_task(
            process_video_generation,
            video_project.id,
            request.prompt,
            request.duration,
            request.auto_post
        )

        return VideoResponse(
            id=video_project.id,
            prompt=video_project.prompt,
            status=video_project.status,
            video_url=video_project.video_url,
            platform_urls=video_project.platform_urls,
            created_at=video_project.created_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Error generating video: {e}")
        raise HTTPException(status_code=500, detail="Video generation failed")

@app.get("/video/{video_id}", response_model=VideoResponse)
async def get_video_status(video_id: int):
    """Get video generation status."""
    if not FULL_FEATURES:
        raise HTTPException(status_code=503, detail="Full features not available yet")

    try:
        from backend.app.core.database import async_session_maker
        async with async_session_maker() as db:
            video_project = await db.get(VideoProject, video_id)
            if not video_project:
                raise HTTPException(status_code=404, detail="Video not found")

            return VideoResponse(
                id=video_project.id,
                prompt=video_project.prompt,
                status=video_project.status,
                video_url=video_project.video_url,
                platform_urls=video_project.platform_urls,
                created_at=video_project.created_at.isoformat()
            )
    except Exception as e:
        logger.error(f"Error getting video status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get video status")

@app.get("/trending-topics", response_model=List[TrendResponse])
async def get_trending_topics(limit: int = 10):
    """Get current trending topics."""
    if not FULL_FEATURES:
        return []

    try:
        from backend.app.core.database import async_session_maker
        async with async_session_maker() as db:
            from sqlalchemy import desc
            result = await db.execute(
                db.query(Trend).filter(Trend.is_active == True).order_by(desc(Trend.virality_score)).limit(limit)
            )
            trends = result.scalars().all()

            return [
                TrendResponse(
                    id=trend.id,
                    platform=trend.platform,
                    trend_name=trend.trend_name,
                    virality_score=trend.virality_score,
                    view_count=trend.view_count,
                    description=trend.description
                )
                for trend in trends
            ]
    except Exception as e:
        logger.error(f"Error getting trending topics: {e}")
        return []

@app.post("/discover-trends")
async def discover_trends():
    """Manually trigger trend discovery."""
    if not FULL_FEATURES:
        return {"error": "Full features not available yet"}

    try:
        from backend.app.core.database import async_session_maker
        async with async_session_maker() as db:
            trend_finder = ViralTrendFinder()
            trends = await trend_finder.find_trending_topics(db)
            return {"message": f"Discovered {len(trends)} trending topics"}
    except Exception as e:
        logger.error(f"Error discovering trends: {e}")
        return {"error": f"Trend discovery failed: {str(e)}"}

async def process_video_generation(video_id: int, prompt: str, duration: int, auto_post: bool):
    """Background task to process video generation."""
    if not FULL_FEATURES:
        return

    try:
        # Generate video using AI service
        ai_service = AIService()
        video_url = await ai_service.generate_video(prompt, duration)

        # Update video project
        from backend.app.core.database import async_session_maker
        async with async_session_maker() as db:
            video_project = await db.get(VideoProject, video_id)
            if video_project:
                video_project.video_url = video_url
                video_project.status = "completed"
                await db.commit()

                # Auto-post to platforms if requested
                if auto_post:
                    social_poster = SocialPosterService()
                    platform_urls = await social_poster.post_to_all_platforms(
                        video_url, prompt, video_project.id, db
                    )
                    video_project.platform_urls = platform_urls
                    await db.commit()

        logger.info(f"Successfully generated and posted video: {video_id}")

    except Exception as e:
        logger.error(f"Error in video generation background task: {e}")
        # Update status to failed
        try:
            from backend.app.core.database import async_session_maker
            async with async_session_maker() as db:
                video_project = await db.get(VideoProject, video_id)
                if video_project:
                    video_project.status = "failed"
                    await db.commit()
        except Exception as db_error:
            logger.error(f"Error updating video status to failed: {db_error}")

async def run_trend_finder():
    """Background task to continuously find trends and generate videos."""
    if not FULL_FEATURES:
        logger.info("Full features not loaded, skipping trend finder")
        return

    while True:
        try:
            logger.info("Starting trend discovery cycle...")
            from backend.app.core.database import async_session_maker
            async with async_session_maker() as db:
                trend_finder = ViralTrendFinder()
                trends = await trend_finder.find_trending_topics(db)
                logger.info(f"Found {len(trends)} trending topics")

                # Auto-generate videos for top trends
                top_trends = await trend_finder.get_top_trends(db, limit=3)
                for trend in top_trends:
                    if trend["virality_score"] > 70:  # Only very viral trends
                        await generate_video_from_trend(trend)

            # Wait for next cycle (6 hours)
            await asyncio.sleep(21600)

        except Exception as e:
            logger.error(f"Error in trend finder cycle: {e}")
            await asyncio.sleep(3600)  # Wait 1 hour before retrying

async def generate_video_from_trend(trend: dict):
    """Generate video from a trending topic."""
    if not FULL_FEATURES:
        return

    try:
        # Create AI prompt from trend
        prompt = f"Create a viral video about: {trend['trend_name']}. {trend['description']} Make it engaging and shareable."

        # Generate video using AI service
        ai_service = AIService()
        video_url = await ai_service.generate_video(prompt)

        # Create video project record
        from backend.app.core.database import async_session_maker
        async with async_session_maker() as db:
            video_project = VideoProject(
                user_id=1,  # System user
                prompt=prompt,
                status="completed",
                video_url=video_url,
                ai_model_used="auto"
            )
            db.add(video_project)
            await db.commit()
            await db.refresh(video_project)

            # Auto-post to platforms
            social_poster = SocialPosterService()
            platform_urls = await social_poster.post_to_all_platforms(
                video_url, prompt, video_project.id, db
            )
            video_project.platform_urls = platform_urls
            await db.commit()

        logger.info(f"Auto-generated viral video for trend: {trend['trend_name']}")

    except Exception as e:
        logger.error(f"Failed to auto-generate video from trend {trend['trend_name']}: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )