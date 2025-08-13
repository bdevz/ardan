"""
Shared data models for the Ardan Automation System
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    DISCOVERED = "discovered"
    FILTERED = "filtered"
    QUEUED = "queued"
    APPLIED = "applied"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class JobType(str, Enum):
    FIXED = "fixed"
    HOURLY = "hourly"


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    VIEWED = "viewed"
    INTERVIEW = "interview"
    HIRED = "hired"
    DECLINED = "declined"


class Job(BaseModel):
    id: Optional[UUID] = None
    upwork_job_id: Optional[str] = None
    title: str
    description: str
    budget_min: Optional[Decimal] = None
    budget_max: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None
    client_name: Optional[str] = None
    client_rating: Decimal
    client_payment_verified: bool = False
    client_hire_rate: Decimal
    posted_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    skills_required: List[str] = Field(default_factory=list)
    job_type: JobType
    location: Optional[str] = None
    status: JobStatus = JobStatus.DISCOVERED
    match_score: Optional[Decimal] = None
    match_reasons: List[str] = Field(default_factory=list)
    content_hash: Optional[str] = None
    job_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class Proposal(BaseModel):
    id: Optional[UUID] = None
    job_id: UUID
    content: str
    bid_amount: Decimal
    attachments: List[str] = Field(default_factory=list)  # Google Drive file IDs
    google_doc_url: Optional[str] = None
    google_doc_id: Optional[str] = None
    generated_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    status: ProposalStatus = ProposalStatus.DRAFT
    quality_score: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class Application(BaseModel):
    id: Optional[UUID] = None
    job_id: UUID
    proposal_id: UUID
    upwork_application_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    status: ApplicationStatus = ApplicationStatus.PENDING
    client_response: Optional[str] = None
    client_response_date: Optional[datetime] = None
    interview_scheduled: bool = False
    interview_date: Optional[datetime] = None
    hired: bool = False
    hire_date: Optional[datetime] = None
    session_recording_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class SystemConfig(BaseModel):
    daily_application_limit: int = 30
    min_hourly_rate: Decimal = Decimal("50.0")
    target_hourly_rate: Decimal = Decimal("75.0")
    min_client_rating: Decimal = Decimal("4.0")
    min_hire_rate: Decimal = Decimal("0.5")
    keywords_include: List[str] = Field(default_factory=lambda: [
        "Salesforce", "Agentforce", "Salesforce AI", "Einstein", "Salesforce Developer"
    ])
    keywords_exclude: List[str] = Field(default_factory=lambda: [
        "WordPress", "Shopify", "PHP", "Junior", "Intern"
    ])
    automation_enabled: bool = True
    notification_channels: List[str] = Field(default_factory=lambda: ["slack"])
    profile_name: str = "Salesforce Agentforce Developer"


class BrowserSession(BaseModel):
    id: Optional[UUID] = None
    browserbase_session_id: str
    session_type: str  # 'job_discovery', 'proposal_submission', 'profile_management'
    status: str = "active"  # 'active', 'expired', 'terminated'
    context: Optional[dict] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None


class PerformanceMetric(BaseModel):
    id: Optional[UUID] = None
    metric_type: str  # 'application_success', 'response_rate', 'hire_rate'
    metric_value: Decimal
    time_period: str  # 'daily', 'weekly', 'monthly'
    date_recorded: datetime
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None


class TaskQueue(BaseModel):
    id: Optional[UUID] = None
    task_type: str
    task_data: dict
    status: str = "pending"  # 'pending', 'processing', 'completed', 'failed'
    priority: int = 0
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: Optional[datetime] = None


# Request/Response models for API
class JobSearchParams(BaseModel):
    keywords: List[str]
    min_hourly_rate: Optional[Decimal] = None
    max_hourly_rate: Optional[Decimal] = None
    min_client_rating: Optional[Decimal] = None
    job_type: Optional[JobType] = None
    location: Optional[str] = None
    payment_verified_only: bool = True


class ProposalGenerationRequest(BaseModel):
    job_id: UUID
    custom_instructions: Optional[str] = None
    include_attachments: bool = True


class ApplicationSubmissionRequest(BaseModel):
    job_id: UUID
    proposal_id: UUID
    confirm_submission: bool = False


class SystemStatusResponse(BaseModel):
    automation_enabled: bool
    jobs_in_queue: int
    applications_today: int
    daily_limit: int
    success_rate: Optional[Decimal] = None
    last_application: Optional[datetime] = None


class JobListResponse(BaseModel):
    jobs: List[Job]
    total: int
    page: int
    per_page: int


class DashboardMetrics(BaseModel):
    total_jobs_discovered: int
    total_applications_submitted: int
    applications_today: int
    success_rate: Decimal
    average_response_time: Optional[Decimal] = None
    top_keywords: List[str]
    recent_applications: List[Application]