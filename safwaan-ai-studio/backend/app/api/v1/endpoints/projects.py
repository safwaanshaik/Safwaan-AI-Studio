"""
SAFWAAN AI STUDIO - Project Management Endpoints
Project CRUD operations and management.

This module provides:
- Project creation and management
- Project sharing and collaboration
- Project templates and workflows
- Project analytics and insights
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_active_user
from app.schemas.project import (
    Project,
    ProjectCreate,
    ProjectUpdate,
    ProjectShare,
    ProjectTemplate
)
from app.services.project_service import ProjectService
from app.utils.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.core.monitoring import record_error

router = APIRouter()


@router.post("/", response_model=Project)
async def create_project(
    project_data: ProjectCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new project.

    - **project_data**: Project creation data
    - **background_tasks**: Background task queue
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        project_service = ProjectService(db)
        project = await project_service.create_project(current_user["id"], project_data)

        # Initialize project analytics (async)
        background_tasks.add_task(
            initialize_project_analytics,
            project.id,
            current_user["id"]
        )

        return project

    except ValidationError:
        raise
    except Exception as e:
        record_error("create_project_error", "projects")
        raise


@router.get("/", response_model=List[Project])
async def get_user_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|name)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user's projects with filtering and pagination.

    - **skip**: Number of projects to skip
    - **limit**: Maximum number of projects to return
    - **search**: Search query for project name or description
    - **status**: Filter by project status
    - **sort_by**: Sort field
    - **sort_order**: Sort order (asc/desc)
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        project_service = ProjectService(db)
        projects = await project_service.get_user_projects(
            user_id=current_user["id"],
            skip=skip,
            limit=limit,
            search=search,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return projects

    except Exception as e:
        record_error("get_projects_error", "projects")
        raise


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get project by ID.

    - **project_id**: Project ID
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        project_service = ProjectService(db)
        project = await project_service.get_project_by_id(project_id)

        if not project:
            raise NotFoundError("Project not found")

        # Check if user has access to this project
        if not await project_service.check_project_access(project_id, current_user["id"]):
            raise AuthorizationError("Access denied to this project")

        return project

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        record_error("get_project_error", "projects")
        raise


@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update project by ID.

    - **project_id**: Project ID
    - **project_update**: Project update data
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        project_service = ProjectService(db)

        # Check if user has access and can modify
        if not await project_service.check_project_write_access(project_id, current_user["id"]):
            raise AuthorizationError("Cannot modify this project")

        updated_project = await project_service.update_project(project_id, project_update)
        if not updated_project:
            raise NotFoundError("Project not found")

        return updated_project

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        record_error("update_project_error", "projects")
        raise


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Delete project by ID (soft delete).

    - **project_id**: Project ID
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        project_service = ProjectService(db)

        # Check if user owns this project
        project = await project_service.get_project_by_id(project_id)
        if not project or project.owner_id != current_user["id"]:
            raise AuthorizationError("Cannot delete this project")

        await project_service.delete_project(project_id)
        return {"message": "Project deleted successfully"}

    except AuthorizationError:
        raise
    except Exception as e:
        record_error("delete_project_error", "projects")
        raise


@router.post("/{project_id}/share", response_model=Project)
async def share_project(
    project_id: str,
    share_data: ProjectShare,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Share project with another user.

    - **project_id**: Project ID
    - **share_data**: Sharing configuration
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        project_service = ProjectService(db)

        # Check if user owns this project
        project = await project_service.get_project_by_id(project_id)
        if not project or project.owner_id != current_user["id"]:
            raise AuthorizationError("Cannot share this project")

        updated_project = await project_service.share_project(
            project_id, share_data.user_id, share_data.permissions
        )
        return updated_project

    except AuthorizationError:
        raise
    except Exception as e:
        record_error("share_project_error", "projects")
        raise


@router.delete("/{project_id}/share/{user_id}")
async def revoke_project_access(
    project_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Revoke user's access to project.

    - **project_id**: Project ID
    - **user_id**: User ID to revoke access for
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        project_service = ProjectService(db)

        # Check if user owns this project
        project = await project_service.get_project_by_id(project_id)
        if not project or project.owner_id != current_user["id"]:
            raise AuthorizationError("Cannot manage access to this project")

        await project_service.revoke_project_access(project_id, user_id)
        return {"message": "Access revoked successfully"}

    except AuthorizationError:
        raise
    except Exception as e:
        record_error("revoke_access_error", "projects")
        raise


@router.get("/templates/", response_model=List[ProjectTemplate])
async def get_project_templates(
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get available project templates.

    - **category**: Filter templates by category
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        project_service = ProjectService(db)
        templates = await project_service.get_project_templates(category)
        return templates

    except Exception as e:
        record_error("get_templates_error", "projects")
        raise


@router.post("/{project_id}/duplicate", response_model=Project)
async def duplicate_project(
    project_id: str,
    new_name: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Duplicate an existing project.

    - **project_id**: Project ID to duplicate
    - **new_name**: New name for the duplicated project
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        project_service = ProjectService(db)

        # Check if user has access to the original project
        if not await project_service.check_project_access(project_id, current_user["id"]):
            raise AuthorizationError("Access denied to this project")

        duplicated_project = await project_service.duplicate_project(
            project_id, current_user["id"], new_name
        )
        return duplicated_project

    except AuthorizationError:
        raise
    except Exception as e:
        record_error("duplicate_project_error", "projects")
        raise


@router.get("/{project_id}/analytics")
async def get_project_analytics(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get project analytics and insights.

    - **project_id**: Project ID
    - **days**: Number of days to analyze
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        project_service = ProjectService(db)

        # Check if user has access to this project
        if not await project_service.check_project_access(project_id, current_user["id"]):
            raise AuthorizationError("Access denied to this project")

        analytics = await project_service.get_project_analytics(project_id, days)
        return analytics

    except AuthorizationError:
        raise
    except Exception as e:
        record_error("get_project_analytics_error", "projects")
        raise


# Helper functions
async def initialize_project_analytics(project_id: str, user_id: str) -> None:
    """Initialize analytics tracking for new project."""
    # TODO: Implement project analytics initialization
    pass