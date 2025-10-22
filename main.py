from fastapi import FastAPI, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import os
from contextlib import asynccontextmanager

# Import services (with error handling)
try:
    from backend.app.core.config import settings
    from backend.app.core.database import init_database, close_database, get_db_session
    from backend.app.api.v1.videos import router as videos_router
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
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers if available
if FULL_FEATURES:
    try:
        app.include_router(videos_router, prefix="/api/v1/videos", tags=["videos"])
        logger.info("Video routes loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load video routes: {e}")

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
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Simple health check that always returns healthy for Railway
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development"),
        "message": "Safwaan AI Studio is running"
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify app is working."""
    return {
        "message": "Safwaan AI Studio Test Endpoint",
        "env_vars": {
            "port": os.getenv("PORT", "8000"),
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "railway_env": os.getenv("RAILWAY_ENVIRONMENT", "not_set"),
            "full_features": FULL_FEATURES
        },
        "features_available": [
            "FastAPI" if 'fastapi' in str(type(app)).lower() else "Basic",
            "Database" if FULL_FEATURES else "Not Available",
            "AI Services" if FULL_FEATURES else "Not Available",
            "Social Media" if FULL_FEATURES else "Not Available"
        ]
    }

@app.post("/admin/generate-from-trends")
async def generate_from_trends(
    background_tasks: BackgroundTasks
):
    """Admin endpoint to manually trigger trend-based video generation."""
    if not FULL_FEATURES:
        return {"error": "Full features not loaded yet"}

    background_tasks.add_task(process_trends_and_generate)
    return {"message": "Trend-based video generation started"}

@app.get("/stats")
async def get_system_stats():
    """Get system statistics."""
    if not FULL_FEATURES:
        return {
            "message": "Full features not loaded yet",
            "status": "basic_mode",
            "uptime": asyncio.get_event_loop().time()
        }

    try:
        from backend.app.db.models.user import VideoProject, RevenueRecord, User
        from sqlalchemy import func

        # Get database session
        from backend.app.core.database import async_session_maker
        async with async_session_maker() as db:
            # Total videos generated
            video_count = await db.execute(func.count(VideoProject.id))
            total_videos = video_count.scalar() or 0

            # Total revenue
            revenue_result = await db.execute(func.sum(RevenueRecord.amount))
            total_revenue = revenue_result.scalar() or 0.0

            # Active users
            user_count = await db.execute(func.count(User.id).filter(User.is_active == True))
            active_users = user_count.scalar() or 0

            # Platform distribution
            platform_result = await db.execute(
                db.query(RevenueRecord.platform, func.sum(RevenueRecord.amount))
                .group_by(RevenueRecord.platform)
            )
            platform_revenue = {row[0]: row[1] for row in platform_result}

            return {
                "total_videos": total_videos,
                "total_revenue": total_revenue,
                "active_users": active_users,
                "platform_revenue": platform_revenue,
                "system_status": "running"
            }
    except Exception as e:
        return {
            "error": f"Database error: {str(e)}",
            "status": "error",
            "full_features_loaded": FULL_FEATURES
        }

async def run_trend_finder():
    """Background task to continuously find trends and generate videos."""
    if not FULL_FEATURES:
        logger.info("Full features not loaded, skipping trend finder")
        return

    while True:
        try:
            logger.info("Starting trend discovery cycle...")
            async with ViralTrendFinder() as trend_finder:
                # Get database session
                from backend.app.core.database import async_session_maker
                async with async_session_maker() as db:
                    # Find trending topics
                    trends = await trend_finder.find_trending_topics(db)
                    logger.info(f"Found {len(trends)} trending topics")

                    # Process top trends
                    top_trends = await trend_finder.get_top_trends(db, limit=5)
                    for trend in top_trends:
                        if trend["virality_score"] > 50:  # Only process highly viral trends
                            await generate_video_from_trend(trend, db)

            # Wait for next cycle (6 hours)
            await asyncio.sleep(getattr(settings, 'trend_check_interval', 21600))

        except Exception as e:
            logger.error(f"Error in trend finder cycle: {e}")
            await asyncio.sleep(3600)  # Wait 1 hour before retrying

async def generate_video_from_trend(trend: dict, db: AsyncSession):
    """Generate video from a trending topic."""
    if not FULL_FEATURES:
        return

    try:
        # Create AI prompt from trend
        prompt = f"Create a viral video about: {trend['trend_name']}. {trend['description']} Make it engaging and shareable."

        # Generate video using AI service
        async with AIService() as ai_service:
            video_url = await ai_service.generate_video(prompt)

            # Create video project record
            from backend.app.db.models.user import VideoProject
            video_project = VideoProject(
                user_id=1,  # System user
                prompt=prompt,
                status="completed",
                video_url=video_url,
                ai_model_used="auto",
                hashtags=trend.get("hashtags", [])
            )
            db.add(video_project)
            await db.commit()
            await db.refresh(video_project)

            # Auto-post to platforms
            async with SocialPosterService() as poster:
                platform_urls = await poster.post_to_all_platforms(
                    video_url, prompt, video_project.id, db
                )
                video_project.platform_urls = platform_urls
                await db.commit()

        logger.info(f"Successfully generated and posted video for trend: {trend['trend_name']}")

    except Exception as e:
        logger.error(f"Failed to generate video from trend {trend['trend_name']}: {e}")

async def process_trends_and_generate():
    """Process current trends and generate videos."""
    if not FULL_FEATURES:
        return {"error": "Full features not loaded"}

    try:
        async with ViralTrendFinder() as trend_finder:
            from backend.app.core.database import async_session_maker
            async with async_session_maker() as db:
                trends = await trend_finder.find_trending_topics(db)
                top_trends = await trend_finder.get_top_trends(db, limit=10)

                for trend in top_trends:
                    if trend["virality_score"] > 30:  # Lower threshold for manual trigger
                        await generate_video_from_trend(trend, db)

        logger.info("Completed trend-based video generation")
        return {"message": "Trend processing completed"}

    except Exception as e:
        logger.error(f"Error in trend processing: {e}")
        return {"error": f"Trend processing failed: {str(e)}"}

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