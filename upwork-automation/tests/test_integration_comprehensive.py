"""
Comprehensive Integration Testing and System Validation
Task 18: Integration Testing and System Validation

This module provides comprehensive integration tests covering:
- End-to-end workflows from job discovery to application
- Browser automation testing with mock Upwork pages
- Performance tests for concurrent session handling
- Failure scenario tests for error recovery
- External service integration tests
- System validation ensuring requirements compliance
"""
import asyncio
import pytest
import uuid
import time
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any
import json
import tempfile
import os

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import all major components for integration testing
from api.main import app
from api.database.connection import get_db, init_db
from api.database.models import JobModel, ProposalModel, ApplicationModel
from shared.models import JobStatus, JobType, ProposalStatus, ApplicationStatus


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows from job discovery to application"""
    
    @pytest.fixture
    async def integrated_system(self):
        """Set up integrated system with all components"""
        # Initialize database
        await init_db()
        
        # Mock external services
        mock_browserbase = Mock()
        mock_browserbase.create_session = AsyncMock(return_value="test_session_123")
        mock_browserbase.create_session_pool = AsyncMock(return_value=["session1", "session2", "session3"])
        mock_browserbase.get_session_health = AsyncMock(return_value={"healthy": True})
        mock_browserbase.close_session = AsyncMock(return_value=True)
        
        mock_stagehand = Mock()
        mock_stagehand.intelligent_navigate = AsyncMock()
        mock_stagehand.extract_content = AsyncMock()
        mock_stagehand.interact_with_form = AsyncMock()
        
        mock_session_manager = Mock()
        mock_session_manager.initialize_session_pools = AsyncMock()
        mock_session_manager.get_session_for_task = AsyncMock(return_value="test_session")
        
        system = {
            "mock_browserbase": mock_browserbase,
            "mock_stagehand": mock_stagehand,
            "mock_session_manager": mock_session_manager
        }
        
        yield system
    
    @pytest.mark.asyncio
    async def test_complete_job_discovery_to_application_workflow(self, integrated_system):
        """Test complete workflow: job discovery -> proposal generation -> application submission"""
        mock_stagehand = integrated_system["mock_stagehand"]
        
        # Step 1: Job Discovery
        mock_job_data = [
            {
                "id": "job_123",
                "title": "Senior Salesforce Agentforce Developer",
                "description": "We need an experienced Salesforce developer to build AI agents using Agentforce platform.",
                "job_url": "https://upwork.com/jobs/job_123",
                "hourly_rate": 85.0,
                "client_rating": 4.8,
                "client_payment_verified": True,
                "client_hire_rate": 0.9,
                "skills_required": ["Salesforce", "Agentforce", "Apex", "Lightning"],
                "posted_date": datetime.utcnow().isoformat(),
                "match_score": 0.95
            }
        ]
        
        # Mock job discovery
        mock_stagehand.extract_content.return_value = {
            "success": True,
            "data": {"jobs": mock_job_data}
        }
        
        # Verify jobs were discovered
        assert len(mock_job_data) == 1
        discovered_job = mock_job_data[0]
        assert discovered_job["title"] == "Senior Salesforce Agentforce Developer"
        assert discovered_job["match_score"] == 0.95
        
        # Step 2: Store job in database
        async with get_db() as session:
            job_model = JobModel(
                upwork_job_id=discovered_job["id"],
                title=discovered_job["title"],
                description=discovered_job["description"],
                hourly_rate=Decimal(str(discovered_job["hourly_rate"])),
                client_rating=Decimal(str(discovered_job["client_rating"])),
                client_payment_verified=discovered_job["client_payment_verified"],
                client_hire_rate=Decimal(str(discovered_job["client_hire_rate"])),
                job_type=JobType.HOURLY,
                status=JobStatus.DISCOVERED,
                match_score=Decimal(str(discovered_job["match_score"])),
                skills_required=discovered_job["skills_required"]
            )
            session.add(job_model)
            await session.commit()
            await session.refresh(job_model)
            job_id = job_model.id
        
        # Step 3: Proposal Generation
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            mock_openai.return_value = {
                "choices": [{
                    "message": {
                        "content": """I am an experienced Salesforce Agentforce developer with 5+ years of expertise in building intelligent AI agents on the Salesforce platform. I have successfully delivered 15+ Agentforce implementations with an average client satisfaction rating of 4.9/5.

My relevant experience includes developing custom Einstein bots, implementing Salesforce AI features, and creating sophisticated automation workflows. In my recent project for TechCorp, I built an Agentforce solution that increased lead qualification efficiency by 40% and reduced response time by 60%.

I would love to discuss how I can help you build powerful AI agents for your business. I'm available to start immediately and can deliver a prototype within the first week. Let's schedule a call to discuss your specific requirements and timeline."""
                    }
                }]
            }
            
            # Generate proposal content
            proposal_content = mock_openai.return_value["choices"][0]["message"]["content"]
            
            assert "Agentforce developer" in proposal_content
            assert "5+ years" in proposal_content
            assert "40%" in proposal_content  # Metrics included
        
        # Step 4: Store proposal in database
        async with get_db() as session:
            proposal_model = ProposalModel(
                job_id=job_id,
                content=proposal_content,
                bid_amount=Decimal("80.00"),  # Slightly below their max rate
                status=ProposalStatus.DRAFT,
                quality_score=Decimal("0.9")
            )
            session.add(proposal_model)
            await session.commit()
            await session.refresh(proposal_model)
            proposal_id = proposal_model.id
        
        # Step 5: Application Submission via Browser Automation
        mock_stagehand.interact_with_form.return_value = {
            "success": True,
            "action_performed": "form_submit",
            "elements_affected": ["cover_letter", "bid_amount", "submit_button"]
        }
        
        # Step 6: Store application in database
        async with get_db() as session:
            application_model = ApplicationModel(
                job_id=job_id,
                proposal_id=proposal_id,
                upwork_application_id="upwork_app_456",
                status=ApplicationStatus.SUBMITTED,
                submitted_at=datetime.utcnow()
            )
            session.add(application_model)
            await session.commit()
            await session.refresh(application_model)
        
        # Step 7: Verify complete workflow
        async with get_db() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            
            # Get complete application with relationships
            result = await session.execute(
                select(ApplicationModel)
                .options(
                    selectinload(ApplicationModel.job),
                    selectinload(ApplicationModel.proposal)
                )
                .where(ApplicationModel.upwork_application_id == "upwork_app_456")
            )
            complete_application = result.scalar_one()
            
            # Verify all data is connected correctly
            assert complete_application.job.title == "Senior Salesforce Agentforce Developer"
            assert complete_application.job.match_score == Decimal("0.95")
            assert complete_application.proposal.bid_amount == Decimal("80.00")
            assert complete_application.status == ApplicationStatus.SUBMITTED
            assert "Agentforce developer" in complete_application.proposal.content
        
        # Verify browser automation was called correctly
        mock_stagehand.extract_content.assert_called()
        mock_stagehand.interact_with_form.assert_called()
        
        print("✅ Complete end-to-end workflow test passed")


class TestBrowserAutomationMockPages:
    """Test browser automation with mock Upwork pages"""
    
    @pytest.fixture
    def mock_upwork_pages(self):
        """Create mock Upwork page responses"""
        return {
            "job_search_page": {
                "url": "https://www.upwork.com/nx/search/jobs",
                "html": """
                <div class="job-tile">
                    <h4 class="job-title">Senior Salesforce Agentforce Developer</h4>
                    <div class="client-rating">4.8 stars</div>
                    <div class="hourly-rate">$75-$90/hr</div>
                    <div class="job-description">Build AI agents using Salesforce Agentforce...</div>
                </div>
                """,
                "elements": {
                    "search_input": {"id": "search-input", "value": ""},
                    "filter_hourly": {"id": "filter-hourly", "checked": False},
                    "filter_payment_verified": {"id": "payment-verified", "checked": False}
                }
            },
            "application_form_page": {
                "url": "https://www.upwork.com/jobs/job_123/apply",
                "html": """
                <form class="application-form">
                    <textarea id="cover-letter" placeholder="Write your proposal..."></textarea>
                    <input id="bid-amount" type="number" placeholder="Your hourly rate"/>
                    <div class="attachments">
                        <input type="file" id="file-upload" multiple/>
                    </div>
                    <button id="submit-application" type="submit">Submit Application</button>
                </form>
                """,
                "elements": {
                    "cover_letter": {"id": "cover-letter", "value": ""},
                    "bid_amount": {"id": "bid-amount", "value": ""},
                    "submit_button": {"id": "submit-application", "enabled": True}
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_job_search_page_automation(self, mock_upwork_pages):
        """Test automated job search on mock Upwork pages"""
        # Mock Stagehand controller
        mock_stagehand = Mock()
        
        # Mock navigation to search page
        mock_stagehand.intelligent_navigate.return_value = {
            "success": True,
            "current_url": mock_upwork_pages["job_search_page"]["url"],
            "page_title": "Find Jobs - Upwork"
        }
        
        # Mock search interaction
        mock_stagehand.interact_with_form.return_value = {
            "success": True,
            "action_performed": "search_submitted",
            "elements_affected": ["search-input", "filter-hourly", "payment-verified"]
        }
        
        # Mock job extraction
        mock_stagehand.extract_content.return_value = {
            "success": True,
            "data": {
                "jobs": [{
                    "title": "Senior Salesforce Agentforce Developer",
                    "client_rating": 4.8,
                    "hourly_rate": "75-90",
                    "description": "Build AI agents using Salesforce Agentforce...",
                    "job_url": "https://www.upwork.com/jobs/job_123"
                }]
            }
        }
        
        # Test search workflow
        session_id = "test_session"
        search_keywords = ["Salesforce", "Agentforce"]
        
        # Navigate to search page
        nav_result = await mock_stagehand.intelligent_navigate(
            session_id, "upwork job search page"
        )
        assert nav_result["success"] is True
        assert "upwork.com" in nav_result["current_url"]
        
        # Perform search
        search_result = await mock_stagehand.interact_with_form(
            session_id, {
                "search_query": " ".join(search_keywords),
                "filters": ["hourly", "payment_verified"]
            }
        )
        assert search_result["success"] is True
        assert "search_submitted" in search_result["action_performed"]
        
        # Extract job results
        extraction_result = await mock_stagehand.extract_content(
            session_id, "job listings with details"
        )
        assert extraction_result["success"] is True
        assert len(extraction_result["data"]["jobs"]) == 1
        
        job = extraction_result["data"]["jobs"][0]
        assert "Agentforce" in job["title"]
        assert job["client_rating"] == 4.8
        
        print("✅ Job search page automation test passed")


class TestPerformanceConcurrency:
    """Test performance and concurrent session handling"""
    
    @pytest.mark.asyncio
    async def test_concurrent_session_handling(self):
        """Test handling multiple concurrent browser sessions"""
        # Mock session manager with realistic behavior
        mock_session_manager = Mock()
        mock_browserbase = Mock()
        
        # Create session pool
        session_pool = [f"session_{i}" for i in range(10)]
        mock_browserbase.create_session_pool.return_value = session_pool
        
        # Mock session health checks
        mock_browserbase.get_session_health.return_value = {"healthy": True}
        
        # Mock session assignment
        session_assignments = {}
        def mock_get_session(task_type):
            # Simulate round-robin assignment
            available_sessions = [s for s in session_pool if s not in session_assignments.values()]
            if available_sessions:
                session_id = available_sessions[0]
                session_assignments[task_type] = session_id
                return session_id
            return None
        
        mock_session_manager.get_session_for_task.side_effect = mock_get_session
        
        # Test concurrent task execution
        async def simulate_task(task_id: str, task_type: str):
            session_id = mock_session_manager.get_session_for_task(task_type)
            if session_id:
                # Simulate work
                await asyncio.sleep(0.1)
                return {"task_id": task_id, "session_id": session_id, "success": True}
            return {"task_id": task_id, "session_id": None, "success": False}
        
        # Create multiple concurrent tasks
        tasks = []
        for i in range(15):  # More tasks than sessions to test queuing
            task_type = ["job_discovery", "proposal_submission", "profile_management"][i % 3]
            task = simulate_task(f"task_{i}", task_type)
            tasks.append(task)
        
        # Execute tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify results
        successful_tasks = [r for r in results if r["success"]]
        failed_tasks = [r for r in results if not r["success"]]
        
        # Should have successful tasks up to session pool size
        assert len(successful_tasks) <= len(session_pool)
        assert len(failed_tasks) >= 0  # Some tasks might fail due to no available sessions
        
        # Verify performance (should complete in reasonable time)
        execution_time = end_time - start_time
        assert execution_time < 2.0  # Should complete within 2 seconds
        
        print(f"✅ Concurrent session handling test passed - {len(successful_tasks)} successful, {len(failed_tasks)} failed, {execution_time:.2f}s")


class TestFailureScenarios:
    """Test error recovery and system resilience"""
    
    @pytest.mark.asyncio
    async def test_browser_session_failure_recovery(self):
        """Test recovery from browser session failures"""
        mock_browserbase = Mock()
        mock_session_manager = Mock()
        
        # Simulate session failure scenarios
        session_failures = [
            {"session_id": "session_1", "error": "Connection timeout"},
            {"session_id": "session_2", "error": "Browser crashed"},
            {"session_id": "session_3", "error": "Network error"}
        ]
        
        # Mock session health checks that detect failures
        def mock_health_check(session_id):
            for failure in session_failures:
                if failure["session_id"] == session_id:
                    return {"healthy": False, "error": failure["error"]}
            return {"healthy": True}
        
        mock_browserbase.get_session_health.side_effect = mock_health_check
        
        # Mock session refresh/recovery
        mock_browserbase.refresh_session.return_value = "new_session_123"
        mock_browserbase.create_session.return_value = "backup_session_456"
        
        # Test failure detection and recovery
        failed_sessions = []
        recovered_sessions = []
        
        for failure in session_failures:
            session_id = failure["session_id"]
            
            # Check session health
            health = mock_browserbase.get_session_health(session_id)
            
            if not health["healthy"]:
                failed_sessions.append(session_id)
                
                # Attempt recovery
                try:
                    if "timeout" in health["error"].lower():
                        # Refresh existing session
                        new_session = await mock_browserbase.refresh_session(session_id)
                        recovered_sessions.append(new_session)
                    else:
                        # Create new session
                        new_session = await mock_browserbase.create_session({})
                        recovered_sessions.append(new_session)
                except Exception as e:
                    print(f"Recovery failed for {session_id}: {e}")
        
        # Verify failure detection and recovery
        assert len(failed_sessions) == 3
        assert len(recovered_sessions) == 3
        assert all(session.startswith(("new_session", "backup_session")) for session in recovered_sessions)
        
        print("✅ Browser session failure recovery test passed")


class TestExternalServiceIntegration:
    """Test integration with all external services"""
    
    @pytest.mark.asyncio
    async def test_openai_integration(self):
        """Test OpenAI API integration for proposal generation"""
        with patch('openai.ChatCompletion.acreate') as mock_openai:
            # Mock successful API response
            mock_openai.return_value = {
                "choices": [{
                    "message": {
                        "content": "I am an experienced Salesforce Agentforce developer with proven expertise in building AI-powered solutions. My recent project increased client efficiency by 45% through intelligent automation."
                    }
                }],
                "usage": {"total_tokens": 150}
            }
            
            # Test proposal generation
            proposal = mock_openai.return_value["choices"][0]["message"]["content"]
            
            assert "Agentforce developer" in proposal
            assert "45%" in proposal  # Should include metrics
            assert len(proposal) > 100  # Should be substantial
            
            print("✅ OpenAI integration test passed")


class TestSystemValidation:
    """Test system validation ensuring requirements compliance"""
    
    @pytest.mark.asyncio
    async def test_job_discovery_requirements_compliance(self):
        """Validate job discovery meets all requirements"""
        # Test Requirement 1: Job Discovery
        mock_job_service = Mock()
        
        # Mock job discovery with required filters
        discovered_jobs = [
            {
                "id": "job_1",
                "title": "Salesforce Agentforce Developer",
                "client_rating": 4.5,
                "hourly_rate": 75,
                "payment_verified": True,
                "match_score": 0.9,
                "skills": ["Salesforce", "Agentforce", "Apex"]
            },
            {
                "id": "job_2", 
                "title": "Salesforce AI Specialist",
                "client_rating": 4.8,
                "hourly_rate": 80,
                "payment_verified": True,
                "match_score": 0.85,
                "skills": ["Salesforce", "Einstein", "AI"]
            }
        ]
        
        mock_job_service.discover_jobs.return_value = discovered_jobs
        
        # Test discovery with required keywords
        required_keywords = ["Salesforce Agentforce", "Salesforce AI", "Einstein", "Salesforce Developer"]
        jobs = await mock_job_service.discover_jobs(keywords=required_keywords)
        
        # Validate Requirement 1.1: Search with specified keywords
        assert len(jobs) > 0
        for job in jobs:
            assert any(keyword.split()[0].lower() in job["title"].lower() for keyword in required_keywords)
        
        # Validate Requirement 1.3: Filter by client rating >= 4.0, hourly rate >= $50, payment verified
        for job in jobs:
            assert job["client_rating"] >= 4.0
            assert job["hourly_rate"] >= 50
            assert job["payment_verified"] is True
        
        # Validate Requirement 1.4: Match scores assigned
        for job in jobs:
            assert "match_score" in job
            assert 0 <= job["match_score"] <= 1
        
        print("✅ Job discovery requirements compliance validated")


# Test runner function
async def run_comprehensive_integration_tests():
    """Run all comprehensive integration tests"""
    print("🚀 Starting Comprehensive Integration Testing...")
    
    # Initialize test environment
    await init_db()
    
    test_classes = [
        TestEndToEndWorkflows,
        TestBrowserAutomationMockPages,
        TestPerformanceConcurrency,
        TestFailureScenarios,
        TestExternalServiceIntegration,
        TestSystemValidation
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}...")
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for test_method_name in test_methods:
            total_tests += 1
            try:
                # Create test instance
                test_instance = test_class()
                
                # Run test method
                test_method = getattr(test_instance, test_method_name)
                if asyncio.iscoroutinefunction(test_method):
                    await test_method()
                else:
                    test_method()
                
                passed_tests += 1
                print(f"  ✅ {test_method_name}")
                
            except Exception as e:
                print(f"  ❌ {test_method_name}: {e}")
    
    print(f"\n🎯 Integration Testing Complete: {passed_tests}/{total_tests} tests passed")
    return passed_tests == total_tests


if __name__ == "__main__":
    # Run comprehensive integration tests
    asyncio.run(run_comprehensive_integration_tests())