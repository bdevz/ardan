"""
Unit tests for the Automated Proposal Generation System
"""
import asyncio
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from shared.models import Job, JobType, JobStatus, ProposalGenerationRequest
from services.llm_proposal_service import LLMProposalService
from services.google_services import GoogleDocsService, GoogleDriveService
from services.proposal_service import ProposalService
from services.workflow_service import WorkflowService


class TestLLMProposalService:
    """Test suite for LLM-based proposal generation"""
    
    @pytest.fixture
    def sample_job(self):
        """Sample job for testing"""
        return Job(
            id=uuid4(),
            upwork_job_id="upwork-123456",
            title="Salesforce Agentforce Developer Needed",
            description="We need an experienced Salesforce developer to implement Agentforce AI solutions for our customer service team. The project involves building automated chat responses and integrating with our existing CRM system.",
            hourly_rate=Decimal("75.00"),
            client_name="TechCorp Inc",
            client_rating=Decimal("4.8"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.85"),
            skills_required=["Salesforce", "Agentforce", "AI", "Customer Service"],
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def llm_service(self):
        """LLM proposal service instance"""
        return LLMProposalService()
    
    @pytest.mark.asyncio
    async def test_job_analysis(self, llm_service, sample_job):
        """Test job requirement analysis"""
        with patch.object(llm_service.client.chat.completions, 'create') as mock_create:
            # Mock LLM response
            mock_response = MagicMock()
            mock_response.choices[0].message.content = '''
            {
                "key_requirements": ["Salesforce Agentforce", "AI integration", "Customer service automation"],
                "project_complexity": "moderate",
                "estimated_timeline": "3-4 weeks",
                "relevant_skills": ["Salesforce", "Agentforce", "AI"],
                "project_goals": "Automate customer service responses",
                "pain_points": ["Manual response handling", "Slow customer service"],
                "value_proposition": "Automated AI-powered customer service",
                "risk_factors": []
            }
            '''
            mock_create.return_value = mock_response
            
            # Execute analysis
            analysis = await llm_service._analyze_job_requirements(sample_job)
            
            # Verify results
            assert "key_requirements" in analysis
            assert "project_complexity" in analysis
            assert analysis["project_complexity"] == "moderate"
            assert "Salesforce Agentforce" in analysis["key_requirements"]
    
    @pytest.mark.asyncio
    async def test_proposal_generation(self, llm_service, sample_job):
        """Test LLM proposal generation"""
        with patch.object(llm_service.client.chat.completions, 'create') as mock_create:
            # Mock job analysis
            mock_analysis_response = MagicMock()
            mock_analysis_response.choices[0].message.content = '''
            {
                "key_requirements": ["Salesforce Agentforce", "AI integration"],
                "project_complexity": "moderate",
                "estimated_timeline": "3-4 weeks",
                "relevant_skills": ["Salesforce", "Agentforce"],
                "project_goals": "Automate customer service",
                "pain_points": ["Manual processes"],
                "value_proposition": "AI automation",
                "risk_factors": []
            }
            '''
            
            # Mock proposal generation
            mock_proposal_response = MagicMock()
            mock_proposal_response.choices[0].message.content = """Dear TechCorp Inc,

I am excited to apply for your Salesforce Agentforce Developer position. As a seasoned developer with 5+ years of experience, I specialize in AI-powered customer service solutions that drive measurable results.

In my recent projects, I have successfully implemented Agentforce solutions that reduced response times by 50% and increased customer satisfaction by 30%. I've automated 80% of routine inquiries, saving 25 hours per week for client teams.

I am available to start immediately and can deliver your project within 3-4 weeks. Let's schedule a call to discuss how I can help automate your customer service processes.

Best regards,
Salesforce Agentforce Developer"""
            
            # Mock quality assessment
            mock_quality_response = MagicMock()
            mock_quality_response.choices[0].message.content = "0.85"
            
            mock_create.side_effect = [
                mock_analysis_response,
                mock_proposal_response,
                mock_quality_response
            ]
            
            # Execute proposal generation
            result = await llm_service.generate_proposal(sample_job)
            
            # Verify results
            assert result["content"] is not None
            assert "TechCorp Inc" in result["content"]
            assert result["bid_amount"] > 0
            assert result["quality_score"] > 0
            assert "attachments" in result
    
    @pytest.mark.asyncio
    async def test_bid_calculation(self, llm_service, sample_job):
        """Test optimal bid calculation"""
        job_analysis = {
            "project_complexity": "moderate",
            "estimated_timeline": "3-4 weeks"
        }
        
        bid_amount = await llm_service._calculate_optimal_bid(sample_job, job_analysis)
        
        # Verify bid is reasonable
        assert bid_amount >= Decimal("50.0")  # Above minimum
        assert bid_amount <= Decimal("150.0")  # Below maximum
        assert bid_amount <= sample_job.hourly_rate * Decimal("1.1")  # Not too much above posted rate
    
    @pytest.mark.asyncio
    async def test_fallback_analysis(self, llm_service, sample_job):
        """Test fallback job analysis when LLM fails"""
        analysis = llm_service._fallback_job_analysis(sample_job)
        
        # Verify fallback provides reasonable defaults
        assert "key_requirements" in analysis
        assert "project_complexity" in analysis
        assert analysis["project_complexity"] in ["simple", "moderate", "complex"]
        assert len(analysis["key_requirements"]) > 0
    
    @pytest.mark.asyncio
    async def test_quality_assessment_heuristic(self, llm_service, sample_job):
        """Test heuristic quality assessment"""
        # Good proposal
        good_proposal = """Dear TechCorp Inc,

I am excited to apply for your Salesforce Agentforce Developer position. With 5+ years of experience, I have delivered 20+ successful projects with 95% client satisfaction.

In my recent work, I implemented solutions that improved response times by 40% and reduced costs by $50,000 annually. I specialize in Agentforce and Einstein AI integration.

I would love to schedule a call to discuss your specific requirements and how I can help achieve your automation goals.

Best regards,
Developer"""
        
        quality_score = llm_service._heuristic_quality_score(good_proposal, sample_job)
        
        # Should score well due to client name, metrics, and call to action
        assert quality_score >= Decimal("0.7")
        
        # Poor proposal
        poor_proposal = "I can do this job. Please hire me."
        
        poor_quality_score = llm_service._heuristic_quality_score(poor_proposal, sample_job)
        
        # Should score poorly
        assert poor_quality_score <= Decimal("0.5")


class TestGoogleServicesIntegration:
    """Test suite for Google Services integration"""
    
    @pytest.fixture
    def google_docs_service(self):
        """Google Docs service instance"""
        return GoogleDocsService()
    
    @pytest.fixture
    def google_drive_service(self):
        """Google Drive service instance"""
        return GoogleDriveService()
    
    @pytest.mark.asyncio
    async def test_document_creation(self, google_docs_service):
        """Test Google Doc creation"""
        title = "Test Proposal"
        content = "This is a test proposal content."
        job_id = uuid4()
        
        # This will use mock service since credentials aren't configured
        result = await google_docs_service.create_proposal_document(
            title=title,
            content=content,
            job_id=job_id
        )
        
        # Verify mock response
        assert "document_id" in result
        assert "document_url" in result
        assert "title" in result
        assert str(job_id) in result["document_id"]
    
    @pytest.mark.asyncio
    async def test_document_update(self, google_docs_service):
        """Test Google Doc update"""
        document_id = "test_doc_123"
        new_content = "Updated proposal content."
        
        # This will use mock service
        success = await google_docs_service.update_proposal_document(
            document_id=document_id,
            content=new_content
        )
        
        # Mock service should return True
        assert success is True
    
    @pytest.mark.asyncio
    async def test_portfolio_file_listing(self, google_drive_service):
        """Test portfolio file listing"""
        files = await google_drive_service.list_portfolio_files()
        
        # Should return mock files
        assert len(files) > 0
        assert all("id" in file for file in files)
        assert all("name" in file for file in files)
        assert any("Salesforce" in file["name"] for file in files)
    
    @pytest.mark.asyncio
    async def test_relevant_attachment_selection(self, google_drive_service):
        """Test relevant attachment selection"""
        job_requirements = ["Salesforce", "Agentforce", "Einstein AI"]
        
        selected_files = await google_drive_service.select_relevant_attachments(
            job_requirements=job_requirements,
            max_attachments=2
        )
        
        # Should select relevant files
        assert len(selected_files) <= 2
        assert len(selected_files) > 0
        
        # Should prioritize relevant files
        file_names = [file["name"].lower() for file in selected_files]
        assert any("salesforce" in name for name in file_names)
    
    def test_relevance_scoring(self, google_drive_service):
        """Test file relevance scoring"""
        # High relevance file
        high_score = google_drive_service._calculate_relevance_score(
            "Salesforce_Agentforce_Portfolio.pdf",
            ["Salesforce", "Agentforce"]
        )
        
        # Low relevance file
        low_score = google_drive_service._calculate_relevance_score(
            "Random_Document.pdf",
            ["Salesforce", "Agentforce"]
        )
        
        assert high_score > low_score
        assert high_score >= 2.0  # Should match both keywords


class TestProposalService:
    """Test suite for enhanced proposal service"""
    
    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def proposal_service(self):
        """Proposal service instance"""
        return ProposalService()
    
    @pytest.fixture
    def sample_request(self):
        """Sample proposal generation request"""
        return ProposalGenerationRequest(
            job_id=uuid4(),
            custom_instructions="Focus on AI automation benefits",
            include_attachments=True
        )
    
    @pytest.mark.asyncio
    async def test_proposal_optimization_analysis(self, proposal_service):
        """Test proposal optimization analysis"""
        # Poor quality proposal
        poor_content = "I can do this job."
        
        # Mock job model
        mock_job = MagicMock()
        mock_job.client_name = "TestClient"
        mock_job.title = "Test Job"
        
        suggestions = await proposal_service._analyze_proposal_for_optimization(
            poor_content, mock_job
        )
        
        # Should identify multiple issues
        assert len(suggestions) > 0
        
        # Should identify length issue
        length_issues = [s for s in suggestions if s["type"] == "length"]
        assert len(length_issues) > 0
        
        # Should identify missing metrics
        metrics_issues = [s for s in suggestions if s["type"] == "metrics"]
        assert len(metrics_issues) > 0
    
    def test_improvement_estimation(self, proposal_service):
        """Test improvement potential estimation"""
        # High priority suggestions
        high_priority_suggestions = [
            {"type": "length", "priority": "high"},
            {"type": "metrics", "priority": "high"},
            {"type": "personalization", "priority": "medium"}
        ]
        
        improvement = proposal_service._estimate_improvement_potential(high_priority_suggestions)
        
        # Should estimate significant improvement
        assert improvement > 0.2
        assert improvement <= 0.3  # Capped at 30%
    
    def test_suggestions_to_instructions_conversion(self, proposal_service):
        """Test converting suggestions to instructions"""
        suggestions = [
            {
                "type": "length",
                "priority": "high",
                "suggestion": "Add more specific details"
            },
            {
                "type": "metrics",
                "priority": "medium", 
                "suggestion": "Include quantifiable results"
            }
        ]
        
        instructions = proposal_service._convert_suggestions_to_instructions(suggestions)
        
        assert "Important: Add more specific details" in instructions
        assert "Include quantifiable results" in instructions


class TestWorkflowService:
    """Test suite for workflow orchestration"""
    
    @pytest.fixture
    def workflow_service(self):
        """Workflow service instance"""
        return WorkflowService()
    
    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session"""
        return AsyncMock()
    
    def test_default_search_params(self, workflow_service):
        """Test default search parameters"""
        params = workflow_service._get_default_search_params()
        
        assert len(params.keywords) > 0
        assert "Salesforce Agentforce" in params.keywords
        assert params.min_hourly_rate == 50.0
        assert params.min_client_rating == 4.0
        assert params.payment_verified_only is True
    
    def test_quality_calculation(self, workflow_service):
        """Test average quality calculation"""
        # Mock proposals with quality scores
        mock_proposals = [
            MagicMock(quality_score=Decimal("0.8")),
            MagicMock(quality_score=Decimal("0.9")),
            MagicMock(quality_score=Decimal("0.7"))
        ]
        
        average = workflow_service._calculate_average_quality(mock_proposals)
        
        assert average == 0.8  # (0.8 + 0.9 + 0.7) / 3
    
    def test_next_steps_recommendations(self, workflow_service):
        """Test next steps recommendations"""
        # No qualifying jobs
        recommendations = workflow_service._generate_next_steps_recommendations([], [])
        assert any("No qualifying jobs" in rec for rec in recommendations)
        
        # Jobs but no proposals
        mock_jobs = [MagicMock(), MagicMock()]
        recommendations = workflow_service._generate_next_steps_recommendations(mock_jobs, [])
        assert any("no proposals generated" in rec for rec in recommendations)
        
        # High quality proposals
        mock_proposals = [MagicMock(quality_score=Decimal("0.9"))]
        recommendations = workflow_service._generate_next_steps_recommendations(mock_jobs, mock_proposals)
        assert any("high-quality proposals ready" in rec for rec in recommendations)


class TestIntegrationWorkflow:
    """Integration tests for the complete proposal generation workflow"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_proposal_generation(self):
        """Test complete proposal generation workflow"""
        # This would test the full integration
        # For now, verify that all components can be instantiated
        
        llm_service = LLMProposalService()
        google_docs = GoogleDocsService()
        google_drive = GoogleDriveService()
        proposal_service = ProposalService()
        workflow_service = WorkflowService()
        
        # Verify services are properly initialized
        assert llm_service is not None
        assert google_docs is not None
        assert google_drive is not None
        assert proposal_service is not None
        assert workflow_service is not None
    
    @pytest.mark.asyncio
    async def test_proposal_quality_pipeline(self):
        """Test proposal quality assessment pipeline"""
        llm_service = LLMProposalService()
        
        # Test with different quality proposals
        high_quality_job = Job(
            id=uuid4(),
            title="Senior Salesforce Agentforce Developer",
            description="Complex AI integration project requiring advanced Salesforce skills",
            client_name="Enterprise Client",
            client_rating=Decimal("4.9"),
            hourly_rate=Decimal("100.00"),
            skills_required=["Salesforce", "Agentforce", "AI"],
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            client_payment_verified=True,
            client_hire_rate=Decimal("0.9"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Test heuristic quality assessment
        good_proposal = """Dear Enterprise Client,

I am excited to apply for your Senior Salesforce Agentforce Developer position. With 5+ years of experience in AI integration, I have successfully delivered 15+ complex Salesforce projects with 98% client satisfaction.

In my recent work, I implemented Agentforce solutions that reduced customer response times by 60% and increased automation rates to 85%. My Einstein AI integrations have saved clients over $200,000 annually in operational costs.

I would love to schedule a call to discuss your specific AI integration requirements and demonstrate how my expertise can drive your project success.

Best regards,
Senior Salesforce Developer"""
        
        quality_score = llm_service._heuristic_quality_score(good_proposal, high_quality_job)
        
        # Should score highly
        assert quality_score >= Decimal("0.8")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])