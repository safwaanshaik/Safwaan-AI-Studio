"""
SAFWAAN AI STUDIO - Video Service
Business logic for video generation and management operations.

This module provides:
- Video generation request handling
- Video processing status tracking
- Video storage and retrieval
- Video analytics and insights
- Access control and permissions
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload

from app.db.models.video import Video, VideoGenerationRequest
from app.db.models.user import User
from app.schemas.video import (
    VideoCreate,
    VideoUpdate,
    VideoGenerationRequest as VideoGenerationRequestSchema,
    VideoProcessingStatus
)
from app.utils.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.core.monitoring import record_error


class VideoService:
    """Service class for video-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_video_request(
        self,
        user_id: str,
        generation_request: VideoGenerationRequestSchema
    ) -> Video:
        """Create a new video generation request."""
        try:
            # Create video record
            video = Video(
                title=generation_request.title,
                description=generation_request.description,
                user_id=user_id,
                project_id=generation_request.project_id,
                status="pending",
                generation_params=generation_request.dict(),
                settings=generation_request.settings or {},
                tags=generation_request.tags or [],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            self.db.add(video)
            await self.db.commit()
            await self.db.refresh(video)

            return video

        except Exception as e:
            await self.db.rollback()
            record_error("create_video_request_error", "video_service")
            raise

    async def get_video_by_id(self, video_id: str) -> Optional[Video]:
        """Get video by ID."""
        try:
            query = select(Video).where(Video.id == video_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            record_error("get_video_by_id_error", "video_service")
            raise

    async def get_user_videos(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[Video]:
        """Get videos for a user with filtering and pagination."""
        try:
            query = select(Video).where(
                and_(Video.user_id == user_id, Video.is_deleted == False)
            )

            # Apply filters
            if project_id:
                query = query.where(Video.project_id == project_id)

            if status:
                query = query.where(Video.status == status)

            if search:
                search_filter = f"%{search}%"
                query = query.where(
                    or_(
                        Video.title.ilike(search_filter),
                        Video.description.ilike(search_filter)
                    )
                )

            # Apply sorting
            sort_column = getattr(Video, sort_by, Video.created_at)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

            # Apply pagination
            query = query.offset(skip).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            record_error("get_user_videos_error", "video_service")
            raise

    async def update_video(self, video_id: str, video_update: VideoUpdate) -> Optional[Video]:
        """Update video metadata."""
        try:
            # Check if video exists
            video = await self.get_video_by_id(video_id)
            if not video:
                return None

            # Prepare update data
            update_data = video_update.dict(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow()

            # Update video
            query = (
                update(Video)
                .where(Video.id == video_id)
                .values(**update_data)
            )
            await self.db.execute(query)
            await self.db.commit()

            # Return updated video
            return await self.get_video_by_id(video_id)

        except Exception as e:
            await self.db.rollback()
            record_error("update_video_error", "video_service")
            raise

    async def delete_video(self, video_id: str) -> None:
        """Soft delete a video."""
        try:
            query = (
                update(Video)
                .where(Video.id == video_id)
                .values(
                    is_deleted=True,
                    deleted_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.execute(query)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            record_error("delete_video_error", "video_service")
            raise

    async def check_video_access(self, video_id: str, user_id: str) -> bool:
        """Check if user has access to video."""
        try:
            query = select(Video).where(
                and_(
                    Video.id == video_id,
                    Video.user_id == user_id,
                    Video.is_deleted == False
                )
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none() is not None

        except Exception as e:
            record_error("check_video_access_error", "video_service")
            return False

    async def check_video_write_access(self, video_id: str, user_id: str) -> bool:
        """Check if user has write access to video."""
        try:
            # For now, only owner has write access
            # TODO: Implement project-based permissions
            return await self.check_video_access(video_id, user_id)

        except Exception as e:
            record_error("check_video_write_access_error", "video_service")
            return False

    async def update_video_generation_result(
        self,
        video_id: str,
        result: Dict[str, Any]
    ) -> None:
        """Update video with generation results."""
        try:
            update_data = {
                "status": result.get("status", "completed"),
                "file_url": result.get("file_url"),
                "thumbnail_url": result.get("thumbnail_url"),
                "duration": result.get("duration"),
                "file_size": result.get("file_size"),
                "resolution": result.get("resolution"),
                "format": result.get("format"),
                "processing_time": result.get("processing_time"),
                "error_message": result.get("error_message"),
                "completed_at": datetime.utcnow() if result.get("status") == "completed" else None,
                "updated_at": datetime.utcnow()
            }

            query = (
                update(Video)
                .where(Video.id == video_id)
                .values(**update_data)
            )
            await self.db.execute(query)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            record_error("update_generation_result_error", "video_service")
            raise

    async def update_video_generation_error(
        self,
        video_id: str,
        error_message: str
    ) -> None:
        """Update video with generation error."""
        try:
            query = (
                update(Video)
                .where(Video.id == video_id)
                .values(
                    status="failed",
                    error_message=error_message,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.execute(query)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            record_error("update_generation_error_error", "video_service")
            raise

    async def get_video_processing_status(self, video_id: str) -> VideoProcessingStatus:
        """Get video processing status and progress."""
        try:
            video = await self.get_video_by_id(video_id)
            if not video:
                raise NotFoundError("Video not found")

            return VideoProcessingStatus(
                video_id=video.id,
                status=video.status,
                progress=video.progress or 0,
                estimated_time_remaining=video.estimated_completion_time,
                current_step=video.current_processing_step,
                error_message=video.error_message,
                created_at=video.created_at,
                updated_at=video.updated_at
            )

        except NotFoundError:
            raise
        except Exception as e:
            record_error("get_processing_status_error", "video_service")
            raise

    async def get_video_download_stream(self, video_id: str):
        """Get video file download stream."""
        try:
            video = await self.get_video_by_id(video_id)
            if not video or not video.file_url:
                raise NotFoundError("Video file not found")

            # TODO: Implement actual file streaming from storage
            # For now, return placeholder
            raise NotImplementedError("File streaming not yet implemented")

        except NotFoundError:
            raise
        except Exception as e:
            record_error("get_download_stream_error", "video_service")
            raise

    async def check_generation_permissions(self, user_id: str, request: VideoGenerationRequestSchema) -> None:
        """Check if user has permissions to generate video."""
        try:
            # TODO: Implement credit checking, rate limiting, etc.
            # For now, just basic validation
            if not request.title or len(request.title.strip()) == 0:
                raise ValidationError("Video title is required")

            if not request.prompt or len(request.prompt.strip()) == 0:
                raise ValidationError("Video prompt is required")

        except ValidationError:
            raise
        except Exception as e:
            record_error("check_generation_permissions_error", "video_service")
            raise

    async def check_regeneration_permissions(self, user_id: str, video: Video) -> None:
        """Check if user can regenerate video."""
        try:
            # Check if video belongs to user
            if video.user_id != user_id:
                raise AuthorizationError("Cannot regenerate this video")

            # Check if video is in a regenerable state
            if video.status not in ["completed", "failed"]:
                raise ValidationError("Video is not in a regenerable state")

            # TODO: Check credits, rate limits, etc.

        except (AuthorizationError, ValidationError):
            raise
        except Exception as e:
            record_error("check_regeneration_permissions_error", "video_service")
            raise

    async def create_video_share_link(
        self,
        video_id: str,
        share_settings: Dict[str, Any]
    ) -> str:
        """Create a shareable link for video."""
        try:
            # TODO: Implement share link generation with expiration, permissions, etc.
            # For now, return placeholder
            share_token = f"share_{video_id}_{datetime.utcnow().timestamp()}"
            return f"https://safwaan.ai/shared/{share_token}"

        except Exception as e:
            record_error("create_share_link_error", "video_service")
            raise

    async def get_video_analytics(self, video_id: str, days: int = 30) -> Dict[str, Any]:
        """Get video analytics and performance metrics."""
        try:
            video = await self.get_video_by_id(video_id)
            if not video:
                raise NotFoundError("Video not found")

            # TODO: Implement actual analytics from analytics service
            # For now, return basic video stats
            return {
                "video_id": video_id,
                "views": 0,  # Placeholder
                "shares": 0,  # Placeholder
                "downloads": 0,  # Placeholder
                "processing_time": video.processing_time,
                "file_size": video.file_size,
                "status": video.status,
                "created_at": video.created_at,
                "completed_at": video.completed_at
            }

        except NotFoundError:
            raise
        except Exception as e:
            record_error("get_video_analytics_error", "video_service")
            raise

    async def check_batch_generation_permissions(
        self,
        user_id: str,
        batch_request: Dict[str, Any]
    ) -> None:
        """Check permissions for batch video generation."""
        try:
            videos = batch_request.get("videos", [])
            if not videos or len(videos) == 0:
                raise ValidationError("No videos specified for batch generation")

            if len(videos) > 10:  # Max batch size
                raise ValidationError("Maximum 10 videos allowed per batch")

            # TODO: Check credits, rate limits, etc.

        except ValidationError:
            raise
        except Exception as e:
            record_error("check_batch_permissions_error", "video_service")
            raise

    async def create_batch_generation_job(
        self,
        user_id: str,
        batch_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a batch generation job."""
        try:
            # TODO: Implement batch job creation
            # For now, return placeholder
            batch_id = f"batch_{user_id}_{datetime.utcnow().timestamp()}"
            return {
                "id": batch_id,
                "user_id": user_id,
                "status": "pending",
                "video_count": len(batch_request.get("videos", [])),
                "created_at": datetime.utcnow()
            }

        except Exception as e:
            record_error("create_batch_job_error", "video_service")
            raise