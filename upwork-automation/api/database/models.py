"""
SQLAlchemy database models for the Upwork Automation System
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Integer, 
    Numeric, ForeignKey, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.sql import func

from .connection import Base
from shared.models import (
    JobStatus, JobType, ProposalStatus, ApplicationStatus
)


class JobModel(Base):
    """Job database model"""
    __tablename__ = "jobs"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    upwork_job_id = Column(String(255), unique=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    budget_min = Column(Numeric(10, 2))
    budget_max = Column(Numeric(10, 2))
    hourly_rate = Column(Numeric(10, 2))
    client_name = Column(String(255))
    client_rating = Column(Numeric(3, 2), default=0)
    client_payment_verified = Column(Boolean, default=False)
    client_hire_rate = Column(Numeric(3, 2), default=0)
    posted_date = Column(DateTime)
    deadline = Column(DateTime)
    skills_required = Column(ARRAY(String))
    job_type = Column(SQLEnum(JobType), nullable=False)
    location = Column(String(255))
    status = Column(SQLEnum(JobStatus), default=JobStatus.DISCOVERED)
    match_score = Column(Numeric(3, 2))
    match_reasons = Column(ARRAY(String))
    content_hash = Column(String(32), index=True)
    job_url = Column(String(1000))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    proposals = relationship("ProposalModel", back_populates="job")
    applications = relationship("ApplicationModel", back_populates="job")
    
    # Indexes
    __table_args__ = (
        Index('idx_jobs_status_created', 'status', 'created_at'),
        Index('idx_jobs_match_score', 'match_score'),
        Index('idx_jobs_hourly_rate', 'hourly_rate'),
        Index('idx_jobs_client_rating', 'client_rating'),
    )


class ProposalModel(Base):
    """Proposal database model"""
    __tablename__ = "proposals"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(PGUUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    content = Column(Text, nullable=False)
    bid_amount = Column(Numeric(10, 2), nullable=False)
    attachments = Column(ARRAY(String))  # Google Drive file IDs
    google_doc_url = Column(String(1000))
    google_doc_id = Column(String(255))
    generated_at = Column(DateTime)
    submitted_at = Column(DateTime)
    status = Column(SQLEnum(ProposalStatus), default=ProposalStatus.DRAFT)
    quality_score = Column(Numeric(3, 2))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    job = relationship("JobModel", back_populates="proposals")
    applications = relationship("ApplicationModel", back_populates="proposal")
    
    # Indexes
    __table_args__ = (
        Index('idx_proposals_job_status', 'job_id', 'status'),
        Index('idx_proposals_quality_score', 'quality_score'),
    )


class ApplicationModel(Base):
    """Application database model"""
    __tablename__ = "applications"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(PGUUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    proposal_id = Column(PGUUID(as_uuid=True), ForeignKey("proposals.id"), nullable=False)
    upwork_application_id = Column(String(255), unique=True)
    submitted_at = Column(DateTime)
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.PENDING)
    client_response = Column(Text)
    client_response_date = Column(DateTime)
    interview_scheduled = Column(Boolean, default=False)
    interview_date = Column(DateTime)
    hired = Column(Boolean, default=False)
    hire_date = Column(DateTime)
    session_recording_url = Column(String(1000))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    job = relationship("JobModel", back_populates="applications")
    proposal = relationship("ProposalModel", back_populates="applications")
    
    # Indexes
    __table_args__ = (
        Index('idx_applications_status_submitted', 'status', 'submitted_at'),
        Index('idx_applications_job_id', 'job_id'),
    )


class BrowserSessionModel(Base):
    """Browser session database model"""
    __tablename__ = "browser_sessions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    browserbase_session_id = Column(String(255), unique=True, nullable=False)
    session_type = Column(String(100), nullable=False)  # 'job_discovery', 'proposal_submission', etc.
    status = Column(String(50), default="active")  # 'active', 'expired', 'terminated'
    context = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_browser_sessions_status', 'status'),
        Index('idx_browser_sessions_type', 'session_type'),
    )


class PerformanceMetricModel(Base):
    """Performance metrics database model"""
    __tablename__ = "performance_metrics"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    metric_type = Column(String(100), nullable=False)  # 'application_success', 'response_rate', etc.
    metric_value = Column(Numeric(10, 4), nullable=False)
    time_period = Column(String(50), nullable=False)  # 'daily', 'weekly', 'monthly'
    date_recorded = Column(DateTime, nullable=False)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_performance_metrics_type_date', 'metric_type', 'date_recorded'),
        Index('idx_performance_metrics_period', 'time_period'),
    )


class TaskQueueModel(Base):
    """Task queue database model"""
    __tablename__ = "task_queue"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    task_type = Column(String(100), nullable=False)
    task_data = Column(JSON, nullable=False)
    status = Column(String(50), default="pending")  # 'pending', 'processing', 'completed', 'failed'
    priority = Column(Integer, default=0)
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_task_queue_status_priority', 'status', 'priority'),
        Index('idx_task_queue_scheduled', 'scheduled_at'),
    )


class SystemConfigModel(Base):
    """System configuration database model"""
    __tablename__ = "system_config"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    daily_application_limit = Column(Integer, default=30)
    min_hourly_rate = Column(Numeric(10, 2), default=50.0)
    target_hourly_rate = Column(Numeric(10, 2), default=75.0)
    min_client_rating = Column(Numeric(3, 2), default=4.0)
    min_hire_rate = Column(Numeric(3, 2), default=0.5)
    keywords_include = Column(ARRAY(String))
    keywords_exclude = Column(ARRAY(String))
    automation_enabled = Column(Boolean, default=True)
    notification_channels = Column(ARRAY(String))
    profile_name = Column(String(255), default="Salesforce Agentforce Developer")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    @classmethod
    async def get_config(cls, session: AsyncSession):
        """Get the single system configuration record"""
        from sqlalchemy import select
        result = await session.execute(select(cls))
        config = result.scalar_one_or_none()
        if not config:
            # Create default config if none exists
            config = cls()
            session.add(config)
            await session.commit()
            await session.refresh(config)
        return config