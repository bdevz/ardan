"""
Unit tests for job filtering and ranking logic in the Job Discovery Service
"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'browser-automation'))

from shared.models import Job, JobStatus, JobType
from job_discovery_service import JobDiscoveryService, FilterCriteria


class TestJobFilteringAndRanking:
    """Test suite for job filtering and ranking functionality"""
    
    @pytest.fixture
    async def job_discovery_service(self):
        """Create JobDiscoveryService instance with mocked dependencies"""
        browserbase_client = AsyncMock()
        stagehand_controller = AsyncMock()
        mcp_client = AsyncMock()
        director = AsyncMock()
        
        # Mock MCP client initialization
        mcp_client.initialize.return_value = None
        
        service = JobDiscoveryService(
            browserbase_client=browserbase_client,
            stagehand_controller=stagehand_controller,
            mcp_client=mcp_client,
            director=director
        )
        await service.initialize()
        return service
    
    @pytest.fixture
    def create_test_job(self):
        """Factory function to create test jobs with different characteristics"""
        def _create_job(
            title="Test Job",
            description="Test description",
            hourly_rate=75.0,
            client_rating=4.5,
            client_hire_rate=0.8,
            payment_verified=True,
            skills=None,
            client_name="Test Client"
        ):
            if skills is None:
                skills = ["Salesforce"]
            
            return Job(
                id=uuid4(),
                ardan_job_id=f"job-{uuid4().hex[:8]}",
                title=title,
                description=description,
                hourly_rate=Decimal(str(hourly_rate)),
                client_name=client_name,
                client_rating=Decimal(str(client_rating)),
                client_payment_verified=payment_verified,
                client_hire_rate=Decimal(str(client_hire_rate)),
                skills_required=skills,
                job_type=JobType.HOURLY,
                status=JobStatus.DISCOVERED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        return _create_job

    class TestBasicCriteriaFiltering:
        """Test basic filtering criteria"""
        
        async def test_hourly_rate_filtering(self, job_discovery_service, create_test_job):
            """Test filtering by hourly rate"""
            # Job above minimum rate
            high_rate_job = create_test_job(hourly_rate=75.0)
            assert job_discovery_service._meets_basic_criteria(high_rate_job) is True
            
            # Job at minimum rate
            min_rate_job = create_test_job(hourly_rate=50.0)
            assert job_discovery_service._meets_basic_criteria(min_rate_job) is True
            
            # Job below minimum rate
            low_rate_job = create_test_job(hourly_rate=25.0)
            assert job_discovery_service._meets_basic_criteria(low_rate_job) is False
        
        async def test_client_rating_filtering(self, job_discovery_service, create_test_job):
            """Test filtering by client rating"""
            # High rating client
            high_rating_job = create_test_job(client_rating=4.8)
            assert job_discovery_service._meets_basic_criteria(high_rating_job) is True
            
            # Minimum rating client
            min_rating_job = create_test_job(client_rating=4.0)
            assert job_discovery_service._meets_basic_criteria(min_rating_job) is True
            
            # Low rating client
            low_rating_job = create_test_job(client_rating=3.5)
            assert job_discovery_service._meets_basic_criteria(low_rating_job) is False
        
        async def test_hire_rate_filtering(self, job_discovery_service, create_test_job):
            """Test filtering by client hire rate"""
            # High hire rate
            high_hire_job = create_test_job(client_hire_rate=0.8)
            assert job_discovery_service._meets_basic_criteria(high_hire_job) is True
            
            # Minimum hire rate
            min_hire_job = create_test_job(client_hire_rate=0.5)
            assert job_discovery_service._meets_basic_criteria(min_hire_job) is True
            
            # Low hire rate
            low_hire_job = create_test_job(client_hire_rate=0.3)
            assert job_discovery_service._meets_basic_criteria(low_hire_job) is False
        
        async def test_payment_verification_filtering(self, job_discovery_service, create_test_job):
            """Test filtering by payment verification"""
            # Verified client
            verified_job = create_test_job(payment_verified=True)
            assert job_discovery_service._meets_basic_criteria(verified_job) is True
            
            # Unverified client
            unverified_job = create_test_job(payment_verified=False)
            assert job_discovery_service._meets_basic_criteria(unverified_job) is False
        
        async def test_keyword_relevance_filtering(self, job_discovery_service, create_test_job):
            """Test filtering by Salesforce keyword relevance"""
            # Jobs with Salesforce keywords in title
            salesforce_title_job = create_test_job(title="Salesforce Developer Needed")
            assert job_discovery_service._meets_basic_criteria(salesforce_title_job) is True
            
            agentforce_title_job = create_test_job(title="Agentforce Implementation Expert")
            assert job_discovery_service._meets_basic_criteria(agentforce_title_job) is True
            
            # Jobs with Salesforce keywords in description
            salesforce_desc_job = create_test_job(
                title="CRM Developer",
                description="We need someone experienced with Salesforce CRM implementation"
            )
            assert job_discovery_service._meets_basic_criteria(salesforce_desc_job) is True
            
            # Jobs without Salesforce keywords
            irrelevant_job = create_test_job(
                title="WordPress Developer",
                description="Build WordPress websites with PHP and MySQL"
            )
            assert job_discovery_service._meets_basic_criteria(irrelevant_job) is False
        
        async def test_combined_criteria_filtering(self, job_discovery_service, create_test_job):
            """Test filtering with multiple criteria combined"""
            # Job that meets all criteria
            perfect_job = create_test_job(
                title="Salesforce Agentforce Developer",
                hourly_rate=85.0,
                client_rating=4.9,
                client_hire_rate=0.9,
                payment_verified=True
            )
            assert job_discovery_service._meets_basic_criteria(perfect_job) is True
            
            # Job that fails multiple criteria
            poor_job = create_test_job(
                title="WordPress Developer",  # No Salesforce keywords
                hourly_rate=20.0,  # Low rate
                client_rating=3.0,  # Low rating
                client_hire_rate=0.2,  # Low hire rate
                payment_verified=False  # Not verified
            )
            assert job_discovery_service._meets_basic_criteria(poor_job) is False

    class TestFallbackRelevanceAnalysis:
        """Test fallback relevance analysis logic"""
        
        async def test_salesforce_keyword_scoring(self, job_discovery_service, create_test_job):
            """Test scoring based on Salesforce keywords"""
            # High-value keywords in title
            agentforce_job = create_test_job(title="Salesforce Agentforce Developer")
            analysis = await job_discovery_service._fallback_relevance_analysis(agentforce_job)
            assert analysis["confidence"] > 0.8
            assert analysis["relevant"] is True
            assert any("Agentforce" in reason for reason in analysis["reasons"])
            
            # High-value keywords in description
            einstein_job = create_test_job(
                title="AI Developer",
                description="Implement Einstein AI solutions for customer service automation"
            )
            analysis = await job_discovery_service._fallback_relevance_analysis(einstein_job)
            assert analysis["confidence"] > 0.6
            assert analysis["relevant"] is True
        
        async def test_ai_automation_keyword_scoring(self, job_discovery_service, create_test_job):
            """Test scoring based on AI/automation keywords"""
            ai_job = create_test_job(
                title="AI Integration Specialist",
                description="Integrate artificial intelligence and automation solutions"
            )
            analysis = await job_discovery_service._fallback_relevance_analysis(ai_job)
            assert analysis["confidence"] > 0.5
            assert "AI/automation keyword" in str(analysis["reasons"])
        
        async def test_technical_skills_scoring(self, job_discovery_service, create_test_job):
            """Test scoring based on technical skills alignment"""
            skilled_job = create_test_job(
                title="Salesforce Developer",
                skills=["Apex", "Lightning", "SOQL", "REST API", "Integration"]
            )
            analysis = await job_discovery_service._fallback_relevance_analysis(skilled_job)
            assert analysis["confidence"] > 0.7
            assert "Relevant skills" in str(analysis["reasons"])
        
        async def test_client_quality_bonus(self, job_discovery_service, create_test_job):
            """Test client quality bonus scoring"""
            high_quality_client_job = create_test_job(
                title="Salesforce Developer",
                client_rating=4.9,
                client_hire_rate=0.95
            )
            analysis = await job_discovery_service._fallback_relevance_analysis(high_quality_client_job)
            
            reasons_str = str(analysis["reasons"])
            assert "High client rating" in reasons_str or "High client hire rate" in reasons_str
        
        async def test_hourly_rate_bonus(self, job_discovery_service, create_test_job):
            """Test hourly rate bonus scoring"""
            high_rate_job = create_test_job(
                title="Salesforce Developer",
                hourly_rate=100.0
            )
            analysis = await job_discovery_service._fallback_relevance_analysis(high_rate_job)
            assert "High hourly rate" in str(analysis["reasons"])
        
        async def test_confidence_score_capping(self, job_discovery_service, create_test_job):
            """Test that confidence scores are properly capped at 1.0"""
            super_job = create_test_job(
                title="Salesforce Agentforce Einstein AI Developer",
                description="Expert in Salesforce, Agentforce, Einstein AI, automation, machine learning",
                hourly_rate=150.0,
                client_rating=5.0,
                client_hire_rate=1.0,
                skills=["Apex", "Lightning", "SOQL", "REST API", "Integration", "AI", "ML"]
            )
            analysis = await job_discovery_service._fallback_relevance_analysis(super_job)
            assert analysis["confidence"] <= 1.0
        
        async def test_low_relevance_jobs(self, job_discovery_service, create_test_job):
            """Test analysis of low relevance jobs"""
            irrelevant_job = create_test_job(
                title="Data Entry Clerk",
                description="Simple data entry work in Excel spreadsheets",
                hourly_rate=15.0,
                client_rating=3.0,
                client_hire_rate=0.2,
                payment_verified=False,
                skills=["Excel", "Data Entry"]
            )
            analysis = await job_discovery_service._fallback_relevance_analysis(irrelevant_job)
            assert analysis["relevant"] is False
            assert analysis["confidence"] < 0.6
            assert analysis["match_quality"] == "low"

    class TestJobRankingAndScoring:
        """Test job ranking and scoring functionality"""
        
        async def test_basic_ranking_by_match_score(self, job_discovery_service, create_test_job):
            """Test basic ranking by match score"""
            jobs = [
                create_test_job(title="Job A"),
                create_test_job(title="Job B"),
                create_test_job(title="Job C")
            ]
            
            # Set different match scores
            jobs[0].match_score = Decimal("0.6")
            jobs[1].match_score = Decimal("0.9")
            jobs[2].match_score = Decimal("0.7")
            
            # Mock historical bonus to return 0
            with patch.object(job_discovery_service, '_get_historical_success_bonus', return_value=0.0):
                ranked_jobs = await job_discovery_service._rank_and_score_jobs(jobs)
            
            # Verify ranking (highest score first)
            assert ranked_jobs[0].match_score == Decimal("0.9")  # Job B
            assert ranked_jobs[1].match_score == Decimal("0.7")  # Job C
            assert ranked_jobs[2].match_score == Decimal("0.6")  # Job A
        
        async def test_default_match_score_assignment(self, job_discovery_service, create_test_job):
            """Test default match score assignment for jobs without scores"""
            jobs = [create_test_job(title="Job without score")]
            
            # Don't set match_score (should be None)
            assert jobs[0].match_score is None
            
            with patch.object(job_discovery_service, '_get_historical_success_bonus', return_value=0.0):
                ranked_jobs = await job_discovery_service._rank_and_score_jobs(jobs)
            
            # Should get default score
            assert ranked_jobs[0].match_score == Decimal("0.5")
        
        async def test_historical_bonus_application(self, job_discovery_service, create_test_job):
            """Test application of historical success bonus"""
            jobs = [create_test_job(title="Job with bonus")]
            jobs[0].match_score = Decimal("0.7")
            
            # Mock historical bonus
            with patch.object(job_discovery_service, '_get_historical_success_bonus', return_value=0.2):
                ranked_jobs = await job_discovery_service._rank_and_score_jobs(jobs)
            
            # Score should be increased by bonus
            assert ranked_jobs[0].match_score == Decimal("0.9")  # 0.7 + 0.2
        
        async def test_score_capping_at_one(self, job_discovery_service, create_test_job):
            """Test that scores are capped at 1.0"""
            jobs = [create_test_job(title="High score job")]
            jobs[0].match_score = Decimal("0.9")
            
            # Mock large historical bonus
            with patch.object(job_discovery_service, '_get_historical_success_bonus', return_value=0.5):
                ranked_jobs = await job_discovery_service._rank_and_score_jobs(jobs)
            
            # Score should be capped at 1.0
            assert ranked_jobs[0].match_score == Decimal("1.0")

    class TestHistoricalSuccessBonus:
        """Test historical success bonus calculation"""
        
        async def test_client_success_bonus(self, job_discovery_service, create_test_job):
            """Test bonus based on client success history"""
            # Set up success patterns
            job_discovery_service.success_patterns = {
                "client:Successful Client": 0.8
            }
            
            job = create_test_job(client_name="Successful Client")
            bonus = await job_discovery_service._get_historical_success_bonus(job)
            
            # Should get client bonus: 0.8 * 0.1 = 0.08
            assert bonus >= 0.08
        
        async def test_keyword_success_bonus(self, job_discovery_service, create_test_job):
            """Test bonus based on keyword success history"""
            # Set up success patterns
            job_discovery_service.success_patterns = {
                "keyword:Salesforce Agentforce": 0.9
            }
            
            job = create_test_job(title="Salesforce Agentforce Developer")
            bonus = await job_discovery_service._get_historical_success_bonus(job)
            
            # Should get keyword bonus: 0.9 * 0.05 = 0.045
            assert bonus >= 0.045
        
        async def test_hourly_rate_range_bonus(self, job_discovery_service, create_test_job):
            """Test bonus based on hourly rate range success"""
            # Set up success patterns for $75-$99 range
            job_discovery_service.success_patterns = {
                "rate:75": 0.7
            }
            
            job = create_test_job(hourly_rate=85.0)  # Falls in $75-$99 range
            bonus = await job_discovery_service._get_historical_success_bonus(job)
            
            # Should get rate bonus: 0.7 * 0.05 = 0.035
            assert bonus >= 0.035
        
        async def test_combined_bonuses(self, job_discovery_service, create_test_job):
            """Test combination of multiple bonuses"""
            # Set up multiple success patterns
            job_discovery_service.success_patterns = {
                "client:Great Client": 0.8,
                "keyword:Salesforce Agentforce": 0.9,
                "rate:75": 0.7
            }
            
            job = create_test_job(
                title="Salesforce Agentforce Implementation",
                client_name="Great Client",
                hourly_rate=80.0
            )
            bonus = await job_discovery_service._get_historical_success_bonus(job)
            
            # Should get combined bonuses but capped at 0.3
            expected_bonus = min(0.8 * 0.1 + 0.9 * 0.05 + 0.7 * 0.05, 0.3)
            assert abs(bonus - expected_bonus) < 0.01
        
        async def test_bonus_capping(self, job_discovery_service, create_test_job):
            """Test that bonus is capped at 0.3"""
            # Set up very high success patterns
            job_discovery_service.success_patterns = {
                "client:Amazing Client": 1.0,
                "keyword:Salesforce Agentforce": 1.0,
                "keyword:Einstein": 1.0,
                "rate:100": 1.0
            }
            
            job = create_test_job(
                title="Salesforce Agentforce Einstein Developer",
                client_name="Amazing Client",
                hourly_rate=100.0
            )
            bonus = await job_discovery_service._get_historical_success_bonus(job)
            
            # Should be capped at 0.3
            assert bonus == 0.3
        
        async def test_no_matching_patterns(self, job_discovery_service, create_test_job):
            """Test bonus calculation with no matching patterns"""
            # Empty success patterns
            job_discovery_service.success_patterns = {}
            
            job = create_test_job(title="Random Job")
            bonus = await job_discovery_service._get_historical_success_bonus(job)
            
            # Should get no bonus
            assert bonus == 0.0

    class TestAIPoweredFiltering:
        """Test AI-powered filtering functionality"""
        
        async def test_successful_ai_filtering(self, job_discovery_service, create_test_job):
            """Test successful AI-powered filtering"""
            jobs = [
                create_test_job(title="Relevant Job"),
                create_test_job(title="Irrelevant Job")
            ]
            
            # Mock AI analysis
            with patch.object(job_discovery_service, '_analyze_job_relevance') as mock_analyze:
                mock_analyze.side_effect = [
                    {"relevant": True, "confidence": 0.8, "reasons": ["High relevance"]},
                    {"relevant": False, "confidence": 0.3, "reasons": ["Low relevance"]}
                ]
                
                filtered_jobs = await job_discovery_service._ai_powered_filtering(jobs)
            
            # Should only keep relevant job
            assert len(filtered_jobs) == 1
            assert filtered_jobs[0].title == "Relevant Job"
            assert filtered_jobs[0].match_score == Decimal("0.8")
        
        async def test_ai_filtering_fallback(self, job_discovery_service, create_test_job):
            """Test fallback to basic filtering when AI fails"""
            jobs = [create_test_job(title="Salesforce Developer")]
            
            # Mock AI analysis failure
            with patch.object(job_discovery_service, '_analyze_job_relevance') as mock_analyze:
                mock_analyze.side_effect = Exception("AI analysis failed")
                
                filtered_jobs = await job_discovery_service._ai_powered_filtering(jobs)
            
            # Should fall back to basic filtering
            assert len(filtered_jobs) == 1
            assert filtered_jobs[0].match_score == Decimal("0.5")  # Default score
        
        async def test_confidence_threshold_filtering(self, job_discovery_service, create_test_job):
            """Test filtering based on confidence threshold"""
            jobs = [
                create_test_job(title="High Confidence Job"),
                create_test_job(title="Low Confidence Job")
            ]
            
            # Mock AI analysis with different confidence levels
            with patch.object(job_discovery_service, '_analyze_job_relevance') as mock_analyze:
                mock_analyze.side_effect = [
                    {"relevant": True, "confidence": 0.8, "reasons": ["High confidence"]},
                    {"relevant": True, "confidence": 0.5, "reasons": ["Low confidence"]}  # Below 0.6 threshold
                ]
                
                filtered_jobs = await job_discovery_service._ai_powered_filtering(jobs)
            
            # Should only keep high confidence job
            assert len(filtered_jobs) == 1
            assert filtered_jobs[0].title == "High Confidence Job"

    class TestFilteringIntegration:
        """Test integration of filtering components"""
        
        async def test_complete_filtering_pipeline(self, job_discovery_service, create_test_job):
            """Test complete filtering pipeline from basic to AI filtering"""
            jobs = [
                # Good job that should pass all filters
                create_test_job(
                    title="Salesforce Agentforce Developer",
                    hourly_rate=85.0,
                    client_rating=4.8,
                    client_hire_rate=0.9,
                    payment_verified=True
                ),
                # Job that fails basic criteria (low rate)
                create_test_job(
                    title="Salesforce Developer",
                    hourly_rate=25.0,  # Below minimum
                    client_rating=4.8,
                    client_hire_rate=0.9,
                    payment_verified=True
                ),
                # Job that passes basic but fails AI filtering
                create_test_job(
                    title="Salesforce Admin",
                    hourly_rate=60.0,
                    client_rating=4.5,
                    client_hire_rate=0.8,
                    payment_verified=True
                )
            ]
            
            # Mock AI analysis
            with patch.object(job_discovery_service, '_analyze_job_relevance') as mock_analyze:
                # Only called for jobs that pass basic filtering
                mock_analyze.side_effect = [
                    {"relevant": True, "confidence": 0.9, "reasons": ["Excellent match"]},
                    {"relevant": False, "confidence": 0.4, "reasons": ["Poor match"]}
                ]
                
                filtered_jobs = await job_discovery_service._ai_powered_filtering(jobs)
            
            # Should only keep the first job
            assert len(filtered_jobs) == 1
            assert filtered_jobs[0].title == "Salesforce Agentforce Developer"
            assert mock_analyze.call_count == 2  # Only called for jobs passing basic criteria


if __name__ == "__main__":
    pytest.main([__file__, "-v"])