"""
Database integration tests for the Upwork Automation System
"""
import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db, init_db, check_db_health, get_pool_stats
from api.database.models import (
    JobModel, ProposalModel, ApplicationModel, BrowserSessionModel,
    PerformanceMetricModel, TaskQueueModel, SystemConfigModel
)
from api.database.indexes import DatabaseIndexManager, optimize_database
from api.database.backup import DatabaseBackupManager
from shared.models import JobStatus, JobType, ProposalStatus, ApplicationStatus


class TestDatabaseConnection:
    """Test database connection and health checks"""
    
    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test basic database connectivity"""
        await init_db()
        
        async with get_db() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database health check functionality"""
        health = await check_db_health()
        
        assert isinstance(health, dict)
        assert "healthy" in health
        assert "timestamp" in health
        assert "response_time_ms" in health
        assert "pool_stats" in health
        
        if health["healthy"]:
            assert health["response_time_ms"] is not None
            assert health["response_time_ms"] > 0
            assert "database_info" in health
    
    @pytest.mark.asyncio
    async def test_connection_pool_stats(self):
        """Test connection pool statistics"""
        stats = await get_pool_stats()
        
        assert isinstance(stats, dict)
        assert "total_connections" in stats
        assert "checked_out_connections" in stats
        assert "pool_size_limit" in stats
        assert "max_overflow" in stats


class TestDatabaseModels:
    """Test database models and CRUD operations"""
    
    @pytest.fixture
    async def session(self):
        """Provide a database session for tests"""
        async with get_db() as session:
            yield session
    
    @pytest.mark.asyncio
    async def test_job_model_crud(self, session: AsyncSession):
        """Test Job model CRUD operations"""
        # Create
        job = JobModel(
            upwork_job_id="test_job_123",
            title="Test Salesforce Developer Job",
            description="Test job description for Salesforce development",
            hourly_rate=Decimal("75.00"),
            client_rating=Decimal("4.5"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.8"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            match_score=Decimal("0.9"),
            skills_required=["Salesforce", "Apex", "Lightning"]
        )
        
        session.add(job)
        await session.commit()
        await session.refresh(job)
        
        assert job.id is not None
        assert job.title == "Test Salesforce Developer Job"
        assert job.hourly_rate == Decimal("75.00")
        assert job.skills_required == ["Salesforce", "Apex", "Lightning"]
        
        # Read
        from sqlalchemy import select
        result = await session.execute(
            select(JobModel).where(JobModel.upwork_job_id == "test_job_123")
        )
        retrieved_job = result.scalar_one()
        
        assert retrieved_job.id == job.id
        assert retrieved_job.title == job.title
        
        # Update
        retrieved_job.status = JobStatus.QUEUED
        retrieved_job.match_score = Decimal("0.95")
        await session.commit()
        
        await session.refresh(retrieved_job)
        assert retrieved_job.status == JobStatus.QUEUED
        assert retrieved_job.match_score == Decimal("0.95")
        
        # Delete
        await session.delete(retrieved_job)
        await session.commit()
        
        result = await session.execute(
            select(JobModel).where(JobModel.upwork_job_id == "test_job_123")
        )
        assert result.scalar_one_or_none() is None
    
    @pytest.mark.asyncio
    async def test_proposal_model_crud(self, session: AsyncSession):
        """Test Proposal model CRUD operations"""
        # First create a job
        job = JobModel(
            upwork_job_id="test_job_for_proposal",
            title="Test Job for Proposal",
            description="Test job description",
            job_type=JobType.HOURLY,
            client_rating=Decimal("4.0"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.5")
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        
        # Create proposal
        proposal = ProposalModel(
            job_id=job.id,
            content="This is a test proposal for Salesforce development work.",
            bid_amount=Decimal("70.00"),
            attachments=["file1.pdf", "file2.docx"],
            status=ProposalStatus.DRAFT,
            quality_score=Decimal("0.85")
        )
        
        session.add(proposal)
        await session.commit()
        await session.refresh(proposal)
        
        assert proposal.id is not None
        assert proposal.job_id == job.id
        assert proposal.bid_amount == Decimal("70.00")
        assert proposal.attachments == ["file1.pdf", "file2.docx"]
        
        # Test relationship
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        
        result = await session.execute(
            select(ProposalModel)
            .options(selectinload(ProposalModel.job))
            .where(ProposalModel.id == proposal.id)
        )
        proposal_with_job = result.scalar_one()
        
        assert proposal_with_job.job.title == "Test Job for Proposal"
        
        # Cleanup
        await session.delete(proposal)
        await session.delete(job)
        await session.commit()
    
    @pytest.mark.asyncio
    async def test_application_model_crud(self, session: AsyncSession):
        """Test Application model CRUD operations"""
        # Create job and proposal first
        job = JobModel(
            upwork_job_id="test_job_for_app",
            title="Test Job for Application",
            description="Test job description",
            job_type=JobType.HOURLY,
            client_rating=Decimal("4.0"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.5")
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        
        proposal = ProposalModel(
            job_id=job.id,
            content="Test proposal content",
            bid_amount=Decimal("65.00"),
            status=ProposalStatus.SUBMITTED
        )
        session.add(proposal)
        await session.commit()
        await session.refresh(proposal)
        
        # Create application
        application = ApplicationModel(
            job_id=job.id,
            proposal_id=proposal.id,
            upwork_application_id="upwork_app_123",
            status=ApplicationStatus.SUBMITTED,
            submitted_at=datetime.utcnow()
        )
        
        session.add(application)
        await session.commit()
        await session.refresh(application)
        
        assert application.id is not None
        assert application.job_id == job.id
        assert application.proposal_id == proposal.id
        assert application.upwork_application_id == "upwork_app_123"
        
        # Test relationships
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        
        result = await session.execute(
            select(ApplicationModel)
            .options(
                selectinload(ApplicationModel.job),
                selectinload(ApplicationModel.proposal)
            )
            .where(ApplicationModel.id == application.id)
        )
        app_with_relations = result.scalar_one()
        
        assert app_with_relations.job.title == "Test Job for Application"
        assert app_with_relations.proposal.bid_amount == Decimal("65.00")
        
        # Cleanup
        await session.delete(application)
        await session.delete(proposal)
        await session.delete(job)
        await session.commit()
    
    @pytest.mark.asyncio
    async def test_system_config_model(self, session: AsyncSession):
        """Test SystemConfig model operations"""
        # Get or create config
        config = await SystemConfigModel.get_config(session)
        
        assert config is not None
        assert config.daily_application_limit == 30
        assert config.min_hourly_rate == Decimal("50.0")
        assert config.automation_enabled is True
        assert "Salesforce" in config.keywords_include
        
        # Update config
        config.daily_application_limit = 25
        config.min_hourly_rate = Decimal("55.0")
        await session.commit()
        
        # Verify update
        updated_config = await SystemConfigModel.get_config(session)
        assert updated_config.daily_application_limit == 25
        assert updated_config.min_hourly_rate == Decimal("55.0")
        
        # Reset to defaults
        config.daily_application_limit = 30
        config.min_hourly_rate = Decimal("50.0")
        await session.commit()
    
    @pytest.mark.asyncio
    async def test_browser_session_model(self, session: AsyncSession):
        """Test BrowserSession model operations"""
        browser_session = BrowserSessionModel(
            browserbase_session_id="bb_session_123",
            session_type="job_discovery",
            status="active",
            context={"user_agent": "test", "cookies": []},
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        session.add(browser_session)
        await session.commit()
        await session.refresh(browser_session)
        
        assert browser_session.id is not None
        assert browser_session.browserbase_session_id == "bb_session_123"
        assert browser_session.context["user_agent"] == "test"
        
        # Cleanup
        await session.delete(browser_session)
        await session.commit()
    
    @pytest.mark.asyncio
    async def test_task_queue_model(self, session: AsyncSession):
        """Test TaskQueue model operations"""
        task = TaskQueueModel(
            task_type="job_discovery",
            task_data={"keywords": ["Salesforce"], "limit": 10},
            status="pending",
            priority=1,
            scheduled_at=datetime.utcnow()
        )
        
        session.add(task)
        await session.commit()
        await session.refresh(task)
        
        assert task.id is not None
        assert task.task_type == "job_discovery"
        assert task.task_data["keywords"] == ["Salesforce"]
        assert task.priority == 1
        
        # Update task status
        task.status = "processing"
        task.started_at = datetime.utcnow()
        await session.commit()
        
        await session.refresh(task)
        assert task.status == "processing"
        assert task.started_at is not None
        
        # Cleanup
        await session.delete(task)
        await session.commit()
    
    @pytest.mark.asyncio
    async def test_performance_metric_model(self, session: AsyncSession):
        """Test PerformanceMetric model operations"""
        metric = PerformanceMetricModel(
            metric_type="application_success",
            metric_value=Decimal("0.75"),
            time_period="daily",
            date_recorded=datetime.utcnow(),
            metadata={"total_applications": 20, "successful": 15}
        )
        
        session.add(metric)
        await session.commit()
        await session.refresh(metric)
        
        assert metric.id is not None
        assert metric.metric_type == "application_success"
        assert metric.metric_value == Decimal("0.75")
        assert metric.metadata["total_applications"] == 20
        
        # Cleanup
        await session.delete(metric)
        await session.commit()


class TestDatabaseIndexes:
    """Test database indexes and performance optimization"""
    
    @pytest.mark.asyncio
    async def test_create_performance_indexes(self):
        """Test creating performance indexes"""
        async with get_db() as session:
            # This should not raise an error
            await DatabaseIndexManager.create_performance_indexes(session)
    
    @pytest.mark.asyncio
    async def test_analyze_table_stats(self):
        """Test table statistics analysis"""
        async with get_db() as session:
            # Analyze all tables
            stats = await DatabaseIndexManager.analyze_table_stats(session)
            
            assert "tables" in stats
            assert isinstance(stats["tables"], list)
            
            # Analyze specific table
            job_stats = await DatabaseIndexManager.analyze_table_stats(session, "jobs")
            
            assert "table" in job_stats
            assert job_stats["table"] == "jobs"
            assert "columns" in job_stats
    
    @pytest.mark.asyncio
    async def test_database_optimization(self):
        """Test full database optimization"""
        async with get_db() as session:
            stats = await optimize_database(session)
            
            assert isinstance(stats, dict)
            # Should complete without errors


class TestDatabaseBackup:
    """Test database backup and recovery functionality"""
    
    @pytest.fixture
    def backup_manager(self):
        """Provide a backup manager for tests"""
        return DatabaseBackupManager("test_backups")
    
    @pytest.mark.asyncio
    async def test_create_schema_backup(self, backup_manager):
        """Test creating a schema backup"""
        try:
            metadata = await backup_manager.create_backup("schema", compress=False)
            
            assert metadata["backup_type"] == "schema"
            assert "file_path" in metadata
            assert "file_size" in metadata
            assert metadata["file_size"] > 0
            
            # Verify backup file exists
            from pathlib import Path
            backup_file = Path(metadata["file_path"])
            assert backup_file.exists()
            
            # Cleanup
            backup_file.unlink()
            metadata_file = backup_file.with_suffix('.json')
            if metadata_file.exists():
                metadata_file.unlink()
                
        except Exception as e:
            # Skip test if pg_dump is not available
            if "pg_dump" in str(e):
                pytest.skip("pg_dump not available in test environment")
            else:
                raise
    
    def test_list_backups(self, backup_manager):
        """Test listing available backups"""
        backups = backup_manager.list_backups()
        assert isinstance(backups, list)
    
    @pytest.mark.asyncio
    async def test_verify_backup_nonexistent(self, backup_manager):
        """Test verifying a non-existent backup"""
        result = await backup_manager.verify_backup("nonexistent_backup.sql")
        
        assert result["valid"] is False
        assert "not found" in result["error"].lower()


class TestDatabaseTransactions:
    """Test database transaction handling"""
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self):
        """Test transaction rollback on error"""
        async with get_db() as session:
            # Create a job
            job = JobModel(
                upwork_job_id="test_rollback_job",
                title="Test Rollback Job",
                description="Test job for rollback",
                job_type=JobType.HOURLY,
                client_rating=Decimal("4.0"),
                client_payment_verified=True,
                client_hire_rate=Decimal("0.5")
            )
            
            session.add(job)
            await session.flush()  # Flush but don't commit
            
            job_id = job.id
            assert job_id is not None
            
            # Simulate an error that causes rollback
            try:
                # This should cause a constraint violation
                duplicate_job = JobModel(
                    upwork_job_id="test_rollback_job",  # Same ID
                    title="Duplicate Job",
                    description="This should fail",
                    job_type=JobType.HOURLY,
                    client_rating=Decimal("4.0"),
                    client_payment_verified=True,
                    client_hire_rate=Decimal("0.5")
                )
                session.add(duplicate_job)
                await session.commit()
                
                # Should not reach here
                assert False, "Expected constraint violation"
                
            except Exception:
                # Transaction should be rolled back
                await session.rollback()
        
        # Verify the job was not saved due to rollback
        async with get_db() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(JobModel).where(JobModel.upwork_job_id == "test_rollback_job")
            )
            assert result.scalar_one_or_none() is None
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent database access"""
        async def create_job(job_id: str):
            async with get_db() as session:
                job = JobModel(
                    upwork_job_id=f"concurrent_job_{job_id}",
                    title=f"Concurrent Job {job_id}",
                    description="Test concurrent access",
                    job_type=JobType.HOURLY,
                    client_rating=Decimal("4.0"),
                    client_payment_verified=True,
                    client_hire_rate=Decimal("0.5")
                )
                session.add(job)
                await session.commit()
                return job.id
        
        # Create multiple jobs concurrently
        tasks = [create_job(str(i)) for i in range(5)]
        job_ids = await asyncio.gather(*tasks)
        
        assert len(job_ids) == 5
        assert all(job_id is not None for job_id in job_ids)
        
        # Cleanup
        async with get_db() as session:
            from sqlalchemy import select
            for i in range(5):
                result = await session.execute(
                    select(JobModel).where(JobModel.upwork_job_id == f"concurrent_job_{i}")
                )
                job = result.scalar_one_or_none()
                if job:
                    await session.delete(job)
            await session.commit()


@pytest.mark.asyncio
async def test_database_initialization():
    """Test database initialization"""
    # This should not raise an error
    await init_db()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])