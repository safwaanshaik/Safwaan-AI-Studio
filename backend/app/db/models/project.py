"""
SAFWAAN AI STUDIO - Project Database Models
SQLAlchemy models for project management and video generation workflows.

This module defines database models for managing user projects, video generation
workflows, and project-related metadata.

Author: Safwaan AI Studio Team
Version: 1.0.0
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..core.database import Base

# Additional imports for enhanced functionality (keeping existing for now, can be refactored later if not used)
import asyncio
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import aiohttp
import numpy as np
from PIL import Image
import cv2
import torch
import requests
import time
import random
import os


class Project(Base):
    """
    Project model for organizing video generation work.

    Represents a user's project containing multiple videos and workflows.
    """

    __tablename__ = "projects"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Project details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), default="general")  # marketing, education, entertainment, etc.

    # Project settings
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_collaboration: Mapped[bool] = mapped_column(Boolean, default=False)

    # Project status
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, archived, deleted

    # Usage tracking
    total_videos: Mapped[int] = mapped_column(Integer, default=0)
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    total_likes: Mapped[int] = mapped_column(Integer, default=0)
    total_shares: Mapped[int] = mapped_column(Integer, default=0)

    # Storage and limits
    storage_used_mb: Mapped[float] = mapped_column(Float, default=0.0)
    storage_limit_mb: Mapped[float] = mapped_column(Float, default=1024.0)  # 1GB default

    # Metadata
    tags: Mapped[Optional[list]] = mapped_column(JSON)  # List of tags
    settings: Mapped[Optional[dict]] = mapped_column(JSON)  # Project-specific settings

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="projects")
    videos: Mapped[List["Video"]] = relationship("Video", back_populates="project", cascade="all, delete-orphan")
    workflows: Mapped[List["Workflow"]] = relationship("Workflow", back_populates="project", cascade="all, delete-orphan")
    collaborators: Mapped[List["ProjectCollaborator"]] = relationship("ProjectCollaborator", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, user_id={self.user_id})>"

    @property
    def storage_used_gb(self) -> float:
        """Get storage used in GB."""
        return self.storage_used_mb / 1024.0

    @property
    def storage_limit_gb(self) -> float:
        """Get storage limit in GB."""
        return self.storage_limit_mb / 1024.0

    @property
    def storage_usage_percentage(self) -> float:
        """Calculate storage usage percentage."""
        if self.storage_limit_mb > 0:
            return (self.storage_used_mb / self.storage_limit_mb) * 100
        return 0.0

    @property
    def is_storage_limit_exceeded(self) -> bool:
        """Check if storage limit is exceeded."""
        return self.storage_used_mb >= self.storage_limit_mb


class ProjectCollaborator(Base):
    """
    Project collaborator model for managing project access permissions.

    Allows multiple users to collaborate on projects with different permission levels.
    """

    __tablename__ = "project_collaborators"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Permissions
    permission_level: Mapped[str] = mapped_column(String(50), default="viewer")  # viewer, editor, admin

    # Collaboration status
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, invited, removed

    # Invitation details
    invitation_token: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    invited_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Activity tracking
    last_access_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="collaborators")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    inviter: Mapped[Optional["User"]] = relationship("User", foreign_keys=[invited_by])

    def __repr__(self) -> str:
        return f"<ProjectCollaborator(project_id={self.project_id}, user_id={self.user_id}, permission={self.permission_level})>"

    @property
    def can_edit(self) -> bool:
        """Check if collaborator can edit the project."""
        return self.permission_level in ["editor", "admin"]

    @property
    def can_delete(self) -> bool:
        """Check if collaborator can delete the project."""
        return self.permission_level == "admin"

    @property
    def is_invitation_pending(self) -> bool:
        """Check if invitation is still pending."""
        return self.status == "invited"


class Workflow(Base):
    """
    Workflow model for managing video generation workflows.

    Represents a sequence of steps for video generation, including AI model selection,
    post-processing, and social media distribution.
    """

    __tablename__ = "workflows"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Workflow details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Workflow configuration
    workflow_type: Mapped[str] = mapped_column(String(100), default="video_generation")  # video_generation, social_upload, etc.
    config: Mapped[dict] = mapped_column(JSON, nullable=False)  # Workflow configuration

    # Workflow status
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, active, archived, deleted

    # Execution tracking
    total_executions: Mapped[int] = mapped_column(Integer, default=0)
    successful_executions: Mapped[int] = mapped_column(Integer, default=0)
    failed_executions: Mapped[int] = mapped_column(Integer, default=0)

    # Performance metrics
    average_execution_time: Mapped[Optional[float]] = mapped_column(Float)  # seconds
    last_execution_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Scheduling
    is_scheduled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_config: Mapped[Optional[dict]] = mapped_column(JSON)  # Cron-like scheduling

    # Metadata
    tags: Mapped[Optional[list]] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="workflows")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    executions: Mapped[List["WorkflowExecution"]] = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name={self.name}, type={self.workflow_type})>"

    @property
    def success_rate(self) -> float:
        """Calculate workflow success rate."""
        total = self.total_executions
        if total == 0:
            return 0.0
        return (self.successful_executions / total) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate workflow failure rate."""
        total = self.total_executions
        if total == 0:
            return 0.0
        return (self.failed_executions / total) * 100


class WorkflowExecution(Base):
    """
    Workflow execution model for tracking workflow runs.

    Records each execution of a workflow, including inputs, outputs, and performance metrics.
    """

    __tablename__ = "workflow_executions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys
    workflow_id: Mapped[int] = mapped_column(Integer, ForeignKey("workflows.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Execution details
    execution_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Execution status
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # pending, running, completed, failed, cancelled

    # Execution data
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Performance metrics
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)

    # Resource usage
    cpu_usage_percent: Mapped[Optional[float]] = mapped_column(Float)
    memory_usage_mb: Mapped[Optional[float]] = mapped_column(Float)
    gpu_usage_percent: Mapped[Optional[float]] = mapped_column(Float)

    # Execution metadata
    execution_context: Mapped[Optional[dict]] = mapped_column(JSON)  # Environment, versions, etc.
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="executions")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<WorkflowExecution(id={self.id}, workflow_id={self.workflow_id}, status={self.status})>"

    @property
    def is_completed(self) -> bool:
        """Check if execution is completed."""
        return self.status in ["completed", "failed", "cancelled"]

    @property
    def is_successful(self) -> bool:
        """Check if execution was successful."""
        return self.status == "completed"

    @property
    def duration_minutes(self) -> Optional[float]:
        """Get duration in minutes."""
        if self.duration_seconds:
            return self.duration_seconds / 60
        return None


# Import other models to establish relationships
from .user import User  # noqa: E402
from .video import Video  # noqa: E402