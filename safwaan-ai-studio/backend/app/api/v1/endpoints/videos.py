"""
SAFWAAN AI STUDIO - Video Management Endpoints
Video generation, processing, and management.

This module provides:
- Video generation requests
- Video processing status tracking
- Video download and streaming
- Video analytics and insights
- Video sharing and collaboration
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_active_user
from app.schemas.video import (
    Video,
    VideoCreate,
    VideoUpdate,
    VideoGenerationRequest,
    VideoProcessingStatus
)
from app.services.video_service import VideoService
from app.services.ai_service import AIService
from app.utils.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.core.monitoring import record_error, record_video_generated

router = APIRouter()


@router.post("/generate", response_model=Video)
async def generate_video(
    generation_request: VideoGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Generate a new video using AI models.

    - **generation_request**: Video generation parameters
    - **background_tasks**: Background task queue
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        video_service = VideoService(db)
        ai_service = AIService()

        # Check user credits/permissions
        await video_service.check_generation_permissions(current_user["id"], generation_request)

        # Create video record
        video = await video_service.create_video_request(
            current_user["id"],
            generation_request
        )

        # Start video generation (async)
        background_tasks.add_task(
            process_video_generation,
            video.id,
            generation_request,
            current_user["id"]
        )

        return video

    except (ValidationError, AuthorizationError):
        raise
    except Exception as e:
        record_error("generate_video_error", "videos")
        raise


@router.get("/", response_model=List[Video])
async def get_user_videos(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|title)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user's videos with filtering and pagination.

    - **skip**: Number of videos to skip
    - **limit**: Maximum number of videos to return
    - **project_id**: Filter by project ID
    - **status**: Filter by video status
    - **search**: Search query for video title or description
    - **sort_by**: Sort field
    - **sort_order**: Sort order (asc/desc)
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        video_service = VideoService(db)
        videos = await video_service.get_user_videos(
            user_id=current_user["id"],
            skip=skip,
            limit=limit,
            project_id=project_id,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return videos

    except Exception as e:
        record_error("get_videos_error", "videos")
        raise


@router.get("/{video_id}", response_model=Video)
async def get_video(
    video_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get video by ID.

    - **video_id**: Video ID
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        video_service = VideoService(db)
        video = await video_service.get_video_by_id(video_id)

        if not video:
            raise NotFoundError("Video not found")

        # Check if user has access to this video
        if not await video_service.check_video_access(video_id, current_user["id"]):
            raise AuthorizationError("Access denied to this video")

        return video

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        record_error("get_video_error", "videos")
        raise


@router.put("/{video_id}", response_model=Video)
async def update_video(
    video_id: str,
    video_update: VideoUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update video metadata.

    - **video_id**: Video ID
    - **video_update**: Video update data
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        video_service = VideoService(db)

        # Check if user has access and can modify
        if not await video_service.check_video_write_access(video_id, current_user["id"]):
            raise AuthorizationError("Cannot modify this video")

        updated_video = await video_service.update_video(video_id, video_update)
        if not updated_video:
            raise NotFoundError("Video not found")

        return updated_video

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        record_error("update_video_error", "videos")
        raise


@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Delete video (soft delete).

    - **video_id**: Video ID
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        video_service = VideoService(db)

        # Check if user owns this video
        video = await video_service.get_video_by_id(video_id)
        if not video or video.user_id != current_user["id"]:
            raise AuthorizationError("Cannot delete this video")

        await video_service.delete_video(video_id)
        return {"message": "Video deleted successfully"}

    except AuthorizationError:
        raise
    except Exception as e:
        record_error("delete_video_error", "videos")
        raise


@router.get("/{video_id}/status", response_model=VideoProcessingStatus)
async def get_video_processing_status(
    video_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get video processing status and progress.

    - **video_id**: Video ID
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        video_service = VideoService(db)

        # Check access
        if not await video_service.check_video_access(video_id, current_user["id"]):
            raise AuthorizationError("Access denied to this video")

        status = await video_service.get_video_processing_status(video_id)
        return status

    except AuthorizationError:
        raise
    except Exception as e:
        record_error("get_video_status_error", "videos")
        raise


@router.get("/{video_id}/download")
async def download_video(
    video_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """
    Download video file.

    - **video_id**: Video ID
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        video_service = VideoService(db)

        # Check access
        if not await video_service.check_video_access(video_id, current_user["id"]):
            raise AuthorizationError("Access denied to this video")

        # Get video file stream
        video_stream = await video_service.get_video_download_stream(video_id)

        return StreamingResponse(
            video_stream,
            media_type="video/mp4",
            headers={"Content-Disposition": f"attachment; filename=video_{video_id}.mp4"}
        )

    except AuthorizationError:
        raise
    except Exception as e:
        record_error("download_video_error", "videos")
        raise


@router.post("/{video_id}/regenerate")
async def regenerate_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Regenerate video with same parameters.

    - **video_id**: Video ID to regenerate
    - **background_tasks**: Background task queue
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        video_service = VideoService(db)

        # Check access and ownership
        video = await video_service.get_video_by_id(video_id)
        if not video or video.user_id != current_user["id"]:
            raise AuthorizationError("Cannot regenerate this video")

        # Check credits
        await video_service.check_regeneration_permissions(current_user["id"], video)

        # Start regeneration
        background_tasks.add_task(
            process_video_regeneration,
            video_id,
            current_user["id"]
        )

        return {"message": "Video regeneration started"}

    except AuthorizationError:
        raise
    except Exception as e:
        record_error("regenerate_video_error", "videos")
        raise


@router.post("/{video_id}/share")
async def share_video(
    video_id: str,
    share_settings: dict,  # TODO: Create proper schema
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Generate shareable link for video.

    - **video_id**: Video ID
    - **share_settings**: Sharing settings
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        video_service = VideoService(db)

        # Check ownership
        video = await video_service.get_video_by_id(video_id)
        if not video or video.user_id != current_user["id"]:
            raise AuthorizationError("Cannot share this video")

        share_link = await video_service.create_video_share_link(video_id, share_settings)
        return {"share_link": share_link}

    except AuthorizationError:
        raise
    except Exception as e:
        record_error("share_video_error", "videos")
        raise


@router.get("/{video_id}/analytics")
async def get_video_analytics(
    video_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get video analytics and performance metrics.

    - **video_id**: Video ID
    - **days**: Number of days to analyze
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        video_service = VideoService(db)

        # Check access
        if not await video_service.check_video_access(video_id, current_user["id"]):
            raise AuthorizationError("Access denied to this video")

        analytics = await video_service.get_video_analytics(video_id, days)
        return analytics

    except AuthorizationError:
        raise
    except Exception as e:
        record_error("get_video_analytics_error", "videos")
        raise


@router.post("/batch-generate")
async def batch_generate_videos(
    batch_request: dict,  # TODO: Create proper schema
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Generate multiple videos in batch.

    - **batch_request**: Batch generation parameters
    - **background_tasks**: Background task queue
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        video_service = VideoService(db)

        # Check batch permissions and credits
        await video_service.check_batch_generation_permissions(current_user["id"], batch_request)

        # Create batch job
        batch_job = await video_service.create_batch_generation_job(
            current_user["id"], batch_request
        )

        # Start batch processing
        background_tasks.add_task(
            process_batch_generation,
            batch_job["id"],
            current_user["id"]
        )

        return {
            "message": "Batch generation started",
            "batch_id": batch_job["id"],
            "estimated_videos": len(batch_request.get("videos", []))
        }

    except ValidationError:
        raise
    except Exception as e:
        record_error("batch_generate_error", "videos")
        raise


# Background task functions
async def process_video_generation(
    video_id: str,
    generation_request: VideoGenerationRequest,
    user_id: str
) -> None:
    """Process video generation in background."""
    try:
        ai_service = AIService()
        video_service = VideoService(None)  # TODO: Get proper DB session

        # Generate video using AI service
        result = await ai_service.generate_video(generation_request)

        # Update video record with result
        await video_service.update_video_generation_result(video_id, result)

        # Record metrics
        record_video_generated()

    except Exception as e:
        # Update video with error status
        await video_service.update_video_generation_error(video_id, str(e))
        record_error("video_generation_failed", "videos")


async def process_video_regeneration(video_id: str, user_id: str) -> None:
    """Process video regeneration in background."""
    # TODO: Implement regeneration logic
    pass


async def process_batch_generation(batch_id: str, user_id: str) -> None:
    """Process batch video generation in background."""
    # TODO: Implement batch processing logic
    pass