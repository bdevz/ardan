"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    job_status_enum = postgresql.ENUM('discovered', 'filtered', 'queued', 'applied', 'rejected', 'archived', name='jobstatus')
    job_type_enum = postgresql.ENUM('fixed', 'hourly', name='jobtype')
    proposal_status_enum = postgresql.ENUM('draft', 'submitted', 'accepted', 'rejected', name='proposalstatus')
    application_status_enum = postgresql.ENUM('pending', 'submitted', 'viewed', 'interview', 'hired', 'declined', name='applicationstatus')
    
    job_status_enum.create(op.get_bind())
    job_type_enum.create(op.get_bind())
    proposal_status_enum.create(op.get_bind())
    application_status_enum.create(op.get_bind())
    
    # Create jobs table
    op.create_table('jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('upwork_job_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('budget_min', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('budget_max', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('hourly_rate', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('client_name', sa.String(length=255), nullable=True),
        sa.Column('client_rating', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('client_payment_verified', sa.Boolean(), nullable=True),
        sa.Column('client_hire_rate', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('posted_date', sa.DateTime(), nullable=True),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('skills_required', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('job_type', job_type_enum, nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('status', job_status_enum, nullable=True),
        sa.Column('match_score', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('match_reasons', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('content_hash', sa.String(length=32), nullable=True),
        sa.Column('job_url', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_jobs_client_rating', 'jobs', ['client_rating'], unique=False)
    op.create_index('idx_jobs_hourly_rate', 'jobs', ['hourly_rate'], unique=False)
    op.create_index('idx_jobs_match_score', 'jobs', ['match_score'], unique=False)
    op.create_index('idx_jobs_status_created', 'jobs', ['status', 'created_at'], unique=False)
    op.create_index(op.f('ix_jobs_content_hash'), 'jobs', ['content_hash'], unique=False)
    op.create_index(op.f('ix_jobs_upwork_job_id'), 'jobs', ['upwork_job_id'], unique=True)

    # Create proposals table
    op.create_table('proposals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('bid_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('attachments', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('google_doc_url', sa.String(length=1000), nullable=True),
        sa.Column('google_doc_id', sa.String(length=255), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('status', proposal_status_enum, nullable=True),
        sa.Column('quality_score', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_proposals_job_status', 'proposals', ['job_id', 'status'], unique=False)
    op.create_index('idx_proposals_quality_score', 'proposals', ['quality_score'], unique=False)

    # Create applications table
    op.create_table('applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('proposal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('upwork_application_id', sa.String(length=255), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('status', application_status_enum, nullable=True),
        sa.Column('client_response', sa.Text(), nullable=True),
        sa.Column('client_response_date', sa.DateTime(), nullable=True),
        sa.Column('interview_scheduled', sa.Boolean(), nullable=True),
        sa.Column('interview_date', sa.DateTime(), nullable=True),
        sa.Column('hired', sa.Boolean(), nullable=True),
        sa.Column('hire_date', sa.DateTime(), nullable=True),
        sa.Column('session_recording_url', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_applications_job_id', 'applications', ['job_id'], unique=False)
    op.create_index('idx_applications_status_submitted', 'applications', ['status', 'submitted_at'], unique=False)
    op.create_index(op.f('ix_applications_upwork_application_id'), 'applications', ['upwork_application_id'], unique=True)

    # Create browser_sessions table
    op.create_table('browser_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('browserbase_session_id', sa.String(length=255), nullable=False),
        sa.Column('session_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_browser_sessions_status', 'browser_sessions', ['status'], unique=False)
    op.create_index('idx_browser_sessions_type', 'browser_sessions', ['session_type'], unique=False)
    op.create_index(op.f('ix_browser_sessions_browserbase_session_id'), 'browser_sessions', ['browserbase_session_id'], unique=True)

    # Create performance_metrics table
    op.create_table('performance_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_type', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('time_period', sa.String(length=50), nullable=False),
        sa.Column('date_recorded', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_performance_metrics_period', 'performance_metrics', ['time_period'], unique=False)
    op.create_index('idx_performance_metrics_type_date', 'performance_metrics', ['metric_type', 'date_recorded'], unique=False)

    # Create task_queue table
    op.create_table('task_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_type', sa.String(length=100), nullable=False),
        sa.Column('task_data', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_task_queue_scheduled', 'task_queue', ['scheduled_at'], unique=False)
    op.create_index('idx_task_queue_status_priority', 'task_queue', ['status', 'priority'], unique=False)

    # Create system_config table
    op.create_table('system_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('daily_application_limit', sa.Integer(), nullable=True),
        sa.Column('min_hourly_rate', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('target_hourly_rate', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('min_client_rating', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('min_hire_rate', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('keywords_include', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('keywords_exclude', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('automation_enabled', sa.Boolean(), nullable=True),
        sa.Column('notification_channels', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('profile_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Insert default system configuration
    op.execute("""
        INSERT INTO system_config (
            id,
            daily_application_limit,
            min_hourly_rate,
            target_hourly_rate,
            min_client_rating,
            min_hire_rate,
            keywords_include,
            keywords_exclude,
            automation_enabled,
            notification_channels,
            profile_name,
            created_at,
            updated_at
        ) VALUES (
            gen_random_uuid(),
            30,
            50.0,
            75.0,
            4.0,
            0.5,
            ARRAY['Salesforce', 'Agentforce', 'Salesforce AI', 'Einstein', 'Salesforce Developer'],
            ARRAY['WordPress', 'Shopify', 'PHP', 'Junior', 'Intern'],
            true,
            ARRAY['slack'],
            'Salesforce Agentforce Developer',
            NOW(),
            NOW()
        )
    """)


def downgrade() -> None:
    op.drop_table('system_config')
    op.drop_index('idx_task_queue_status_priority', table_name='task_queue')
    op.drop_index('idx_task_queue_scheduled', table_name='task_queue')
    op.drop_table('task_queue')
    op.drop_index('idx_performance_metrics_type_date', table_name='performance_metrics')
    op.drop_index('idx_performance_metrics_period', table_name='performance_metrics')
    op.drop_table('performance_metrics')
    op.drop_index(op.f('ix_browser_sessions_browserbase_session_id'), table_name='browser_sessions')
    op.drop_index('idx_browser_sessions_type', table_name='browser_sessions')
    op.drop_index('idx_browser_sessions_status', table_name='browser_sessions')
    op.drop_table('browser_sessions')
    op.drop_index(op.f('ix_applications_upwork_application_id'), table_name='applications')
    op.drop_index('idx_applications_status_submitted', table_name='applications')
    op.drop_index('idx_applications_job_id', table_name='applications')
    op.drop_table('applications')
    op.drop_index('idx_proposals_quality_score', table_name='proposals')
    op.drop_index('idx_proposals_job_status', table_name='proposals')
    op.drop_table('proposals')
    op.drop_index(op.f('ix_jobs_upwork_job_id'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_content_hash'), table_name='jobs')
    op.drop_index('idx_jobs_status_created', table_name='jobs')
    op.drop_index('idx_jobs_match_score', table_name='jobs')
    op.drop_index('idx_jobs_hourly_rate', table_name='jobs')
    op.drop_index('idx_jobs_client_rating', table_name='jobs')
    op.drop_table('jobs')
    
    # Drop enums
    postgresql.ENUM(name='applicationstatus').drop(op.get_bind())
    postgresql.ENUM(name='proposalstatus').drop(op.get_bind())
    postgresql.ENUM(name='jobtype').drop(op.get_bind())
    postgresql.ENUM(name='jobstatus').drop(op.get_bind())