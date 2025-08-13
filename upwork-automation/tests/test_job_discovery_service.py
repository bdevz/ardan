"""
Unit tests for the Core Job Discovery Service
"""
import asyncio
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'browser-automation'))

from shared.models import Job, JobStatus, JobType, JobSearchParams
from job_discovery_service import (
    JobDiscoveryService,
    SearchStrategy,
    JobDiscoveryResult,
    DeduplicationResult
)
from stagehand_controller import ExtractionResult, ExtractionType


class TestJobDiscoveryService:
    """Test suite for JobDiscoveryService"""
    
    @pytest.fixture
    async def mock_dependencies(self):
        """Create mock dependencies for JobDiscoveryService"""
        browserbase_client = AsyncMock()
        stagehand_controller = AsyncMock()
        mcp_client = AsyncMock()
        director = AsyncMock()
        
        # Mock session creation
        browserbase_client.create_session.return_value = MagicMock(id="test-session-123")
        browserbase_client.end_session.return_value = True
        
        # Mock MCP client initialization
        mcp_client.initialize.return_value = None
        
        return {
            "browserbase_client": browserbase_client,
            "stagehand_controller": stagehand_controller,
            "mcp_client": mcp_client,
            "director": director
        }
    
    @pytest.fixture
    async def job_discovery_service(self, mock_dependencies):
        """Create JobDiscoveryService instance with mocked dependencies"""
        service = JobDiscoveryService(
            browserbase_client=mock_dependencies["browserbase_client"],
            stagehand_controller=mock_dependencies["stagehand_controller"],
            mcp_client=mock_dependencies["mcp_client"],
            director=mock_dependencies["director"]
        )
        await service.initialize()
        return service
    
    @pytest.fixture
    def sample_job_data(self):
        """Sample job data for testing"""
        return {
            "title": "Salesforce Agentforce Developer Needed",
            "description": "We need an experienced Salesforce developer to implement Agentforce AI solutions for our customer service team.",
            "client_name": "TechCorp Inc",
            "budget": "$75/hr",
            "client_rating": "4.8",
            "payment_verified": True,
            "hire_rate": "0.85",
            "skills": ["Salesforce", "Apex", "Lightning", "AI"],
            "posted_time": "2024-01-15T10:00:00Z",
            "job_id": "upwork-123456",
            "job_url": "https://www.upwork.com/jobs/123456"
        }
    
    @pytest.fixture
    def sample_jobs_list(self):
        """Sample list of jobs for testing"""
        return [
            Job(
                id=uuid4(),
                upwork_job_id="job-001",
                title="Salesforce Agentforce Implementation",
                description="Implement Agentforce for customer service automation",
                hourly_rate=Decimal("75.00"),
                client_name="Client A",
                client_rating=Decimal("4.8"),
                client_payment_verified=True,
                client_hire_rate=Decimal("0.85"),
                job_type=JobType.HOURLY,
                skills_required=["Salesforce", "Agentforce", "AI"],
                status=JobStatus.DISCOVERED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Job(
                id=uuid4(),
                upwork_job_id="job-002",
                title="Einstein AI Integration",
                description="Integrate Einstein AI with existing Salesforce org",
                hourly_rate=Decimal("80.00"),
                client_name="Client B",
                client_rating=Decimal("4.9"),
                client_payment_verified=True,
                client_hire_rate=Decimal("0.90"),
                job_type=JobType.HOURLY,
                skills_required=["Salesforce", "Einstein", "Integration"],
                status=JobStatus.DISCOVERED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]

    async def test_service_initialization(self, mock_dependencies):
        """Test service initialization"""
        service = JobDiscoveryService(**mock_dependencies)
        
        # Test initialization
        await service.initialize()
        
        # Verify MCP client was initialized
        mock_dependencies["mcp_client"].initialize.assert_called_once()
        
        # Verify default configuration
        assert service.min_hourly_rate == Decimal("50.0")
        assert service.min_client_rating == Decimal("4.0")
        assert "Salesforce Agentforce" in service.default_keywords

    async def test_discover_jobs_success(self, job_discovery_service, mock_dependencies, sample_job_data):
        """Test successful job discovery"""
        # Mock session pool creation
        mock_dependencies["browserbase_client"].create_session.return_value = MagicMock(id="session-1")
        
        # Mock navigation success
        mock_dependencies["stagehand_controller"].intelligent_navigate.return_value = MagicMock(success=True)
        
        # Mock job search results
        search_result = ExtractionResult(
            success=True,
            data={"jobs": [sample_job_data]},
            extraction_type=ExtractionType.JOB_LISTINGS,
            confidence_score=0.9
        )
        mock_dependencies["stagehand_controller"].search_jobs.return_value = search_result
        
        # Mock Stagehand initialization
        mock_dependencies["stagehand_controller"].initialize_stagehand.return_value = True
        mock_dependencies["stagehand_controller"].cleanup_session.return_value = None
        
        # Execute job discovery
        search_params = JobSearchParams(
            keywords=["Salesforce Agentforce"],
            min_hourly_rate=Decimal("50.0")
        )
        
        result = await job_discovery_service.discover_jobs(
            search_params=search_params,
            max_jobs=10,
            search_strategy=SearchStrategy.KEYWORD_BASED
        )
        
        # Verify results
        assert result.success is True
        assert len(result.jobs_found) > 0
        assert result.search_strategy == SearchStrategy.KEYWORD_BASED.value
        assert result.search_duration > 0
        
        # Verify job properties
        job = result.jobs_found[0]
        assert job.title == sample_job_data["title"]
        assert job.client_name == sample_job_data["client_name"]
        assert job.hourly_rate == Decimal("75.00")
        assert job.status == JobStatus.DISCOVERED

    async def test_discover_jobs_failure(self, job_discovery_service, mock_dependencies):
        """Test job discovery failure handling"""
        # Mock session creation failure
        mock_dependencies["browserbase_client"].create_session.side_effect = Exception("Session creation failed")
        
        # Execute job discovery
        result = await job_discovery_service.discover_jobs(max_jobs=10)
        
        # Verify failure handling
        assert result.success is False
        assert result.error_message is not None
        assert len(result.jobs_found) == 0

    async def test_extract_job_details_success(self, job_discovery_service, mock_dependencies, sample_job_data):
        """Test successful job detail extraction"""
        job_url = "https://www.upwork.com/jobs/123456"
        
        # Mock session creation
        mock_dependencies["browserbase_client"].create_session.return_value = MagicMock(id="session-123")
        
        # Mock job detail extraction
        extraction_result = ExtractionResult(
            success=True,
            data=sample_job_data,
            extraction_type=ExtractionType.JOB_DETAILS,
            confidence_score=0.95
        )
        mock_dependencies["stagehand_controller"].extract_job_details.return_value = extraction_result
        
        # Execute job detail extraction
        job = await job_discovery_service.extract_job_details(job_url)
        
        # Verify results
        assert job is not None
        assert job.title == sample_job_data["title"]
        assert job.job_url == job_url
        assert job.content_hash is not None
        
        # Verify session cleanup
        mock_dependencies["browserbase_client"].end_session.assert_called_once()

    async def test_extract_job_details_failure(self, job_discovery_service, mock_dependencies):
        """Test job detail extraction failure"""
        job_url = "https://www.upwork.com/jobs/invalid"
        
        # Mock session creation
        mock_dependencies["browserbase_client"].create_session.return_value = MagicMock(id="session-123")
        
        # Mock extraction failure
        extraction_result = ExtractionResult(
            success=False,
            data={},
            extraction_type=ExtractionType.JOB_DETAILS,
            error_message="Page not found"
        )
        mock_dependencies["stagehand_controller"].extract_job_details.return_value = extraction_result
        
        # Execute job detail extraction
        job = await job_discovery_service.extract_job_details(job_url)
        
        # Verify failure handling
        assert job is None

    async def test_job_deduplication(self, job_discovery_service):
        """Test job deduplication functionality"""
        # Create jobs with duplicates
        job1 = Job(
            id=uuid4(),
            upwork_job_id="job-001",
            title="Salesforce Developer",
            description="Salesforce development work",
            client_name="Client A",
            client_rating=Decimal("4.5"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.8"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Duplicate by Upwork ID
        job2 = Job(
            id=uuid4(),
            upwork_job_id="job-001",  # Same Upwork ID
            title="Different Title",
            description="Different description",
            client_name="Client B",
            client_rating=Decimal("4.0"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.7"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Generate content hashes
        job1.content_hash = job_discovery_service._generate_content_hash(job1)
        job2.content_hash = job_discovery_service._generate_content_hash(job2)
        
        # Create duplicate by content hash
        job3 = Job(
            id=uuid4(),
            upwork_job_id="job-003",
            title="Salesforce Developer",  # Same title
            description="Salesforce development work",  # Same description
            client_name="Client A",  # Same client
            client_rating=Decimal("4.5"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.8"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        job3.content_hash = job_discovery_service._generate_content_hash(job3)
        
        jobs = [job1, job2, job3]
        
        # Execute deduplication
        result = await job_discovery_service._deduplicate_jobs(jobs)
        
        # Verify deduplication results
        assert result.original_count == 3
        assert result.duplicates_found == 2  # job2 (duplicate ID) and job3 (duplicate content)
        assert result.deduplicated_count == 1
        assert len(result.duplicate_pairs) == 2

    async def test_basic_criteria_filtering(self, job_discovery_service):
        """Test basic job filtering criteria"""
        # Job that meets criteria
        good_job = Job(
            id=uuid4(),
            title="Salesforce Agentforce Developer",
            description="Implement Salesforce Agentforce solutions",
            hourly_rate=Decimal("75.00"),
            client_rating=Decimal("4.8"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.85"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Job that doesn't meet criteria (low rate)
        low_rate_job = Job(
            id=uuid4(),
            title="Salesforce Developer",
            description="Basic Salesforce work",
            hourly_rate=Decimal("25.00"),  # Below minimum
            client_rating=Decimal("4.8"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.85"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Job that doesn't meet criteria (no Salesforce keywords)
        irrelevant_job = Job(
            id=uuid4(),
            title="WordPress Developer",
            description="WordPress website development",
            hourly_rate=Decimal("75.00"),
            client_rating=Decimal("4.8"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.85"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Test filtering
        assert job_discovery_service._meets_basic_criteria(good_job) is True
        assert job_discovery_service._meets_basic_criteria(low_rate_job) is False
        assert job_discovery_service._meets_basic_criteria(irrelevant_job) is False

    async def test_ai_powered_filtering(self, job_discovery_service, sample_jobs_list):
        """Test AI-powered job filtering"""
        # Mock the AI relevance analysis
        with patch.object(job_discovery_service, '_analyze_job_relevance') as mock_analyze:
            # Mock high relevance for first job
            mock_analyze.side_effect = [
                {"relevant": True, "confidence": 0.85, "reasons": ["Contains Agentforce"]},
                {"relevant": True, "confidence": 0.75, "reasons": ["Contains Einstein AI"]}
            ]
            
            # Execute AI filtering
            filtered_jobs = await job_discovery_service._ai_powered_filtering(sample_jobs_list)
            
            # Verify results
            assert len(filtered_jobs) == 2
            assert all(job.match_score is not None for job in filtered_jobs)
            assert filtered_jobs[0].match_score == Decimal("0.85")
            assert filtered_jobs[1].match_score == Decimal("0.75")

    async def test_fallback_relevance_analysis(self, job_discovery_service):
        """Test fallback relevance analysis"""
        # High relevance job
        high_relevance_job = Job(
            id=uuid4(),
            title="Salesforce Agentforce AI Developer",
            description="Implement Agentforce AI solutions with Einstein integration",
            hourly_rate=Decimal("85.00"),
            client_rating=Decimal("4.9"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.90"),
            skills_required=["Salesforce", "Apex", "Einstein", "AI"],
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Low relevance job
        low_relevance_job = Job(
            id=uuid4(),
            title="Basic Data Entry",
            description="Simple data entry work",
            hourly_rate=Decimal("15.00"),
            client_rating=Decimal("3.5"),
            client_payment_verified=False,
            client_hire_rate=Decimal("0.3"),
            skills_required=["Excel"],
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Test high relevance analysis
        high_analysis = await job_discovery_service._fallback_relevance_analysis(high_relevance_job)
        assert high_analysis["relevant"] is True
        assert high_analysis["confidence"] > 0.8
        assert len(high_analysis["reasons"]) > 0
        
        # Test low relevance analysis
        low_analysis = await job_discovery_service._fallback_relevance_analysis(low_relevance_job)
        assert low_analysis["relevant"] is False
        assert low_analysis["confidence"] < 0.6

    async def test_job_ranking_and_scoring(self, job_discovery_service, sample_jobs_list):
        """Test job ranking and scoring"""
        # Set initial match scores
        sample_jobs_list[0].match_score = Decimal("0.7")
        sample_jobs_list[1].match_score = Decimal("0.9")
        
        # Mock historical success bonus
        with patch.object(job_discovery_service, '_get_historical_success_bonus') as mock_bonus:
            mock_bonus.side_effect = [0.1, 0.05]  # Different bonuses for each job
            
            # Execute ranking
            ranked_jobs = await job_discovery_service._rank_and_score_jobs(sample_jobs_list)
            
            # Verify ranking (higher scores first)
            assert len(ranked_jobs) == 2
            assert ranked_jobs[0].match_score >= ranked_jobs[1].match_score
            assert ranked_jobs[0].match_score == Decimal("0.95")  # 0.9 + 0.05
            assert ranked_jobs[1].match_score == Decimal("0.8")   # 0.7 + 0.1

    async def test_historical_success_bonus(self, job_discovery_service):
        """Test historical success bonus calculation"""
        # Set up success patterns
        job_discovery_service.success_patterns = {
            "client:TechCorp Inc": 0.8,
            "keyword:Salesforce Agentforce": 0.9,
            "rate:75": 0.7
        }
        
        job = Job(
            id=uuid4(),
            title="Salesforce Agentforce Implementation",
            description="Implement Agentforce solutions",
            hourly_rate=Decimal("75.00"),
            client_name="TechCorp Inc",
            client_rating=Decimal("4.8"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.85"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Calculate bonus
        bonus = await job_discovery_service._get_historical_success_bonus(job)
        
        # Verify bonus calculation
        assert bonus > 0
        assert bonus <= 0.3  # Should be capped at 0.3

    async def test_content_hash_generation(self, job_discovery_service):
        """Test content hash generation for deduplication"""
        job1 = Job(
            id=uuid4(),
            title="Salesforce Developer",
            description="Salesforce development work",
            client_name="Client A",
            client_rating=Decimal("4.5"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.8"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        job2 = Job(
            id=uuid4(),
            title="Salesforce Developer",  # Same title
            description="Salesforce development work",  # Same description
            client_name="Client A",  # Same client
            client_rating=Decimal("4.5"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.8"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        job3 = Job(
            id=uuid4(),
            title="Different Title",  # Different title
            description="Different description",  # Different description
            client_name="Client B",  # Different client
            client_rating=Decimal("4.0"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.7"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Generate hashes
        hash1 = job_discovery_service._generate_content_hash(job1)
        hash2 = job_discovery_service._generate_content_hash(job2)
        hash3 = job_discovery_service._generate_content_hash(job3)
        
        # Verify hash properties
        assert hash1 == hash2  # Same content should produce same hash
        assert hash1 != hash3  # Different content should produce different hash
        assert len(hash1) == 32  # MD5 hash length

    async def test_job_model_conversion(self, job_discovery_service, sample_job_data):
        """Test conversion of raw job data to Job model"""
        job = await job_discovery_service._convert_to_job_model(sample_job_data)
        
        # Verify conversion
        assert job is not None
        assert job.title == sample_job_data["title"]
        assert job.description == sample_job_data["description"]
        assert job.client_name == sample_job_data["client_name"]
        assert job.hourly_rate == Decimal("75.00")
        assert job.client_rating == Decimal("4.8")
        assert job.client_payment_verified is True
        assert job.client_hire_rate == Decimal("0.85")
        assert job.job_type == JobType.HOURLY
        assert job.upwork_job_id == sample_job_data["job_id"]
        assert job.skills_required == sample_job_data["skills"]
        assert job.status == JobStatus.DISCOVERED
        assert job.content_hash is not None

    async def test_invalid_job_data_conversion(self, job_discovery_service):
        """Test handling of invalid job data during conversion"""
        # Missing required fields
        invalid_data = {
            "description": "Some description",
            # Missing title
        }
        
        job = await job_discovery_service._convert_to_job_model(invalid_data)
        assert job is None
        
        # Empty title
        invalid_data2 = {
            "title": "",
            "description": "Some description"
        }
        
        job2 = await job_discovery_service._convert_to_job_model(invalid_data2)
        assert job2 is None

    async def test_search_strategy_execution(self, job_discovery_service, mock_dependencies):
        """Test different search strategy execution"""
        # Mock session pool creation
        mock_dependencies["browserbase_client"].create_session.return_value = MagicMock(id="session-1")
        mock_dependencies["stagehand_controller"].initialize_stagehand.return_value = True
        mock_dependencies["stagehand_controller"].cleanup_session.return_value = None
        
        # Mock navigation and search
        mock_dependencies["stagehand_controller"].intelligent_navigate.return_value = MagicMock(success=True)
        mock_dependencies["stagehand_controller"].search_jobs.return_value = ExtractionResult(
            success=True,
            data={"jobs": []},
            extraction_type=ExtractionType.JOB_LISTINGS,
            confidence_score=0.8
        )
        
        search_params = JobSearchParams(keywords=["Salesforce"])
        
        # Test keyword-based strategy
        result = await job_discovery_service.discover_jobs(
            search_params=search_params,
            search_strategy=SearchStrategy.KEYWORD_BASED
        )
        assert result.search_strategy == SearchStrategy.KEYWORD_BASED.value
        
        # Test hybrid strategy
        result = await job_discovery_service.discover_jobs(
            search_params=search_params,
            search_strategy=SearchStrategy.HYBRID
        )
        assert result.search_strategy == SearchStrategy.HYBRID.value

    async def test_service_statistics(self, job_discovery_service):
        """Test service statistics retrieval"""
        # Add some test data
        job_discovery_service.discovered_jobs["job1"] = MagicMock()
        job_discovery_service.job_content_hashes.add("hash1")
        job_discovery_service.upwork_job_ids.add("upwork1")
        
        # Get initial pattern count (service loads default patterns)
        initial_stats = await job_discovery_service.get_discovery_stats()
        initial_pattern_count = initial_stats["success_patterns_count"]
        
        # Add a new pattern
        job_discovery_service.success_patterns["pattern1"] = 0.8
        
        # Get statistics
        stats = await job_discovery_service.get_discovery_stats()
        
        # Verify statistics
        assert stats["total_jobs_discovered"] == 1
        assert stats["unique_content_hashes"] == 1
        assert stats["unique_upwork_ids"] == 1
        assert stats["success_patterns_count"] == initial_pattern_count + 1
        assert "last_discovery" in stats

    async def test_service_shutdown(self, job_discovery_service, mock_dependencies):
        """Test service shutdown"""
        # Mock shutdown methods
        mock_dependencies["stagehand_controller"].shutdown.return_value = None
        
        # Execute shutdown
        await job_discovery_service.shutdown()
        
        # Verify shutdown was called
        mock_dependencies["stagehand_controller"].shutdown.assert_called_once()

    async def test_success_pattern_update(self, job_discovery_service):
        """Test success pattern updates"""
        pattern_key = "test_pattern"
        success_rate = 0.75
        
        # Update pattern
        await job_discovery_service.update_success_pattern(pattern_key, success_rate)
        
        # Verify update
        assert job_discovery_service.success_patterns[pattern_key] == success_rate

    async def test_session_pool_management(self, job_discovery_service, mock_dependencies):
        """Test browser session pool creation and cleanup"""
        # Mock session creation
        mock_dependencies["browserbase_client"].create_session.side_effect = [
            MagicMock(id="session-1"),
            MagicMock(id="session-2"),
            MagicMock(id="session-3")
        ]
        mock_dependencies["stagehand_controller"].initialize_stagehand.return_value = True
        
        # Create session pool
        sessions = await job_discovery_service._create_search_session_pool(size=3)
        
        # Verify session creation
        assert len(sessions) == 3
        assert mock_dependencies["browserbase_client"].create_session.call_count == 3
        assert mock_dependencies["stagehand_controller"].initialize_stagehand.call_count == 3
        
        # Test cleanup
        mock_dependencies["stagehand_controller"].cleanup_session.return_value = None
        mock_dependencies["browserbase_client"].end_session.return_value = True
        
        await job_discovery_service._cleanup_session_pool(sessions)
        
        # Verify cleanup
        assert mock_dependencies["stagehand_controller"].cleanup_session.call_count == 3
        assert mock_dependencies["browserbase_client"].end_session.call_count == 3


# Integration tests
class TestJobDiscoveryIntegration:
    """Integration tests for job discovery service"""
    
    @pytest.mark.integration
    async def test_end_to_end_job_discovery(self):
        """Test end-to-end job discovery flow"""
        # This would test the full flow with real browser automation
        # Skipped in unit tests but would be valuable for integration testing
        pass
    
    @pytest.mark.integration
    async def test_real_upwork_search(self):
        """Test real Upwork job search"""
        # This would test against real Upwork pages
        # Requires careful setup to avoid rate limiting
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])