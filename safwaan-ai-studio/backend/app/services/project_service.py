"""
SAFWAAN AI STUDIO - Project Service
Business logic for project management operations.

This module provides:
- Project CRUD operations
- Project sharing and collaboration
- Project templates and workflows
- Project analytics and insights
- Access control and permissions
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, exists
from sqlalchemy.orm import selectinload

from app.db.models.project import Project, ProjectShare, ProjectTemplate
from app.db.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectShare as ProjectShareSchema,
    ProjectTemplate as ProjectTemplateSchema
)
from app.utils.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.core.monitoring import record_error


class ProjectService:
    """Service class for project-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_project(self, owner_id: str, project_data: ProjectCreate) -> Project:
        """Create a new project."""
        try:
            # Create project instance
            project = Project(
                name=project_data.name,
                description=project_data.description,
                owner_id=owner_id,
                status=project_data.status or "active",
                settings=project_data.settings or {},
                tags=project_data.tags or [],
                is_public=project_data.is_public or False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            self.db.add(project)
            await self.db.commit()
            await self.db.refresh(project)

            return project

        except Exception as e:
            await self.db.rollback()
            record_error("create_project_error", "project_service")
            raise

    async def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        try:
            query = select(Project).where(Project.id == project_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            record_error("get_project_by_id_error", "project_service")
            raise

    async def get_user_projects(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[Project]:
        """Get projects accessible by user."""
        try:
            # Base query for owned projects
            owned_query = select(Project).where(
                and_(Project.owner_id == user_id, Project.is_deleted == False)
            )

            # Query for shared projects
            shared_query = (
                select(Project)
                .join(ProjectShare, Project.id == ProjectShare.project_id)
                .where(
                    and_(
                        ProjectShare.user_id == user_id,
                        Project.is_deleted == False
                    )
                )
            )

            # Combine queries
            combined_query = owned_query.union(shared_query)

            # Apply filters
            if search:
                search_filter = f"%{search}%"
                combined_query = combined_query.where(
                    or_(
                        Project.name.ilike(search_filter),
                        Project.description.ilike(search_filter)
                    )
                )

            if status:
                combined_query = combined_query.where(Project.status == status)

            # Apply sorting
            sort_column = getattr(Project, sort_by, Project.created_at)
            if sort_order == "desc":
                combined_query = combined_query.order_by(sort_column.desc())
            else:
                combined_query = combined_query.order_by(sort_column.asc())

            # Apply pagination
            combined_query = combined_query.offset(skip).limit(limit)

            result = await self.db.execute(combined_query)
            return result.scalars().unique().all()

        except Exception as e:
            record_error("get_user_projects_error", "project_service")
            raise

    async def update_project(self, project_id: str, project_update: ProjectUpdate) -> Optional[Project]:
        """Update project information."""
        try:
            # Check if project exists
            project = await self.get_project_by_id(project_id)
            if not project:
                return None

            # Prepare update data
            update_data = project_update.dict(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow()

            # Update project
            query = (
                update(Project)
                .where(Project.id == project_id)
                .values(**update_data)
            )
            await self.db.execute(query)
            await self.db.commit()

            # Return updated project
            return await self.get_project_by_id(project_id)

        except Exception as e:
            await self.db.rollback()
            record_error("update_project_error", "project_service")
            raise

    async def delete_project(self, project_id: str) -> None:
        """Soft delete a project."""
        try:
            query = (
                update(Project)
                .where(Project.id == project_id)
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
            record_error("delete_project_error", "project_service")
            raise

    async def check_project_access(self, project_id: str, user_id: str) -> bool:
        """Check if user has access to project."""
        try:
            # Check if user owns the project
            owned_query = select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.owner_id == user_id,
                    Project.is_deleted == False
                )
            )
            owned_result = await self.db.execute(owned_query)
            if owned_result.scalar_one_or_none():
                return True

            # Check if project is shared with user
            shared_query = select(ProjectShare).where(
                and_(
                    ProjectShare.project_id == project_id,
                    ProjectShare.user_id == user_id
                )
            )
            shared_result = await self.db.execute(shared_query)
            if shared_result.scalar_one_or_none():
                return True

            # Check if project is public
            public_query = select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.is_public == True,
                    Project.is_deleted == False
                )
            )
            public_result = await self.db.execute(public_query)
            return public_result.scalar_one_or_none() is not None

        except Exception as e:
            record_error("check_access_error", "project_service")
            return False

    async def check_project_write_access(self, project_id: str, user_id: str) -> bool:
        """Check if user has write access to project."""
        try:
            # Check if user owns the project
            owned_query = select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.owner_id == user_id,
                    Project.is_deleted == False
                )
            )
            owned_result = await self.db.execute(owned_query)
            if owned_result.scalar_one_or_none():
                return True

            # Check if project is shared with write permissions
            shared_query = select(ProjectShare).where(
                and_(
                    ProjectShare.project_id == project_id,
                    ProjectShare.user_id == user_id,
                    ProjectShare.permissions.in_(["write", "admin"])
                )
            )
            shared_result = await self.db.execute(shared_query)
            return shared_result.scalar_one_or_none() is not None

        except Exception as e:
            record_error("check_write_access_error", "project_service")
            return False

    async def share_project(
        self,
        project_id: str,
        user_id: str,
        permissions: str = "read"
    ) -> Project:
        """Share project with another user."""
        try:
            # Validate permissions
            if permissions not in ["read", "write", "admin"]:
                raise ValidationError("Invalid permission level")

            # Check if share already exists
            existing_query = select(ProjectShare).where(
                and_(
                    ProjectShare.project_id == project_id,
                    ProjectShare.user_id == user_id
                )
            )
            existing = await self.db.execute(existing_query)
            existing_share = existing.scalar_one_or_none()

            if existing_share:
                # Update existing share
                query = (
                    update(ProjectShare)
                    .where(
                        and_(
                            ProjectShare.project_id == project_id,
                            ProjectShare.user_id == user_id
                        )
                    )
                    .values(
                        permissions=permissions,
                        updated_at=datetime.utcnow()
                    )
                )
            else:
                # Create new share
                share = ProjectShare(
                    project_id=project_id,
                    user_id=user_id,
                    permissions=permissions,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(share)

            await self.db.commit()
            return await self.get_project_by_id(project_id)

        except Exception as e:
            await self.db.rollback()
            record_error("share_project_error", "project_service")
            raise

    async def revoke_project_access(self, project_id: str, user_id: str) -> None:
        """Revoke user's access to project."""
        try:
            query = delete(ProjectShare).where(
                and_(
                    ProjectShare.project_id == project_id,
                    ProjectShare.user_id == user_id
                )
            )
            await self.db.execute(query)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            record_error("revoke_access_error", "project_service")
            raise

    async def get_project_templates(self, category: Optional[str] = None) -> List[ProjectTemplateSchema]:
        """Get available project templates."""
        try:
            query = select(ProjectTemplate).where(ProjectTemplate.is_active == True)

            if category:
                query = query.where(ProjectTemplate.category == category)

            query = query.order_by(ProjectTemplate.sort_order)

            result = await self.db.execute(query)
            templates = result.scalars().all()

            return [ProjectTemplateSchema.from_orm(template) for template in templates]

        except Exception as e:
            record_error("get_templates_error", "project_service")
            raise

    async def duplicate_project(
        self,
        project_id: str,
        user_id: str,
        new_name: Optional[str] = None
    ) -> Project:
        """Duplicate an existing project."""
        try:
            # Get original project
            original = await self.get_project_by_id(project_id)
            if not original:
                raise NotFoundError("Project not found")

            # Create duplicate
            duplicate_data = ProjectCreate(
                name=new_name or f"{original.name} (Copy)",
                description=original.description,
                status="active",
                settings=original.settings.copy(),
                tags=original.tags.copy(),
                is_public=False
            )

            return await self.create_project(user_id, duplicate_data)

        except Exception as e:
            await self.db.rollback()
            record_error("duplicate_project_error", "project_service")
            raise

    async def get_project_analytics(self, project_id: str, days: int = 30) -> Dict[str, Any]:
        """Get project analytics and insights."""
        try:
            # This would integrate with analytics service
            # For now, return basic project stats
            project = await self.get_project_by_id(project_id)
            if not project:
                raise NotFoundError("Project not found")

            # Get video count (placeholder - would query video table)
            video_count = 0  # TODO: Implement actual video counting

            # Get collaborator count
            collaborator_query = select(func.count(ProjectShare.id)).where(
                ProjectShare.project_id == project_id
            )
            collaborator_result = await self.db.execute(collaborator_query)
            collaborator_count = collaborator_result.scalar()

            return {
                "project_id": project_id,
                "total_videos": video_count,
                "collaborators": collaborator_count,
                "created_date": project.created_at,
                "last_updated": project.updated_at,
                "status": project.status
            }

        except Exception as e:
            record_error("get_project_analytics_error", "project_service")
            raise