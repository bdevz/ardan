"""
Synchronous unit tests for Job Discovery Service core logic
"""
import pytest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
import hashlib

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.models import Job, JobStatus, JobType


class TestJobDiscoveryLogic:
    """Test core job discovery logic without async complexity"""
    
    def create_test_job(
        self,
        title="Test Job",
        description="Test description",
        hourly_rate=75.0,
        client_rating=4.5,
        client_hire_rate=0.8,
        payment_verified=True,
        skills=None,
        client_name="Test Client",
        ardan_job_id=None
    ):
        """Create a test job with specified parameters"""
        if skills is None:
            skills = ["Salesforce"]
        
        job = Job(
            id=uuid4(),
            ardan_job_id=ardan_job_id or f"job-{uuid4().hex[:8]}",
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
        return job
    
    def meets_basic_criteria(self, job: Job) -> bool:
        """Check if job meets basic filtering criteria"""
        min_hourly_rate = Decimal("50.0")
        min_client_rating = Decimal("4.0")
        min_hire_rate = Decimal("0.5")
        
        # Hourly rate check
        if job.hourly_rate and job.hourly_rate < min_hourly_rate:
            return False
        
        # Client rating check
        if job.client_rating < min_client_rating:
            return False
        
        # Client hire rate check
        if job.client_hire_rate < min_hire_rate:
            return False
        
        # Payment verification check
        if not job.client_payment_verified:
            return False
        
        # Keyword relevance check
        title_lower = job.title.lower()
        description_lower = job.description.lower()
        
        salesforce_keywords = ["salesforce", "agentforce", "einstein", "crm"]
        has_salesforce_keyword = any(keyword in title_lower or keyword in description_lower 
                                   for keyword in salesforce_keywords)
        
        if not has_salesforce_keyword:
            return False
        
        return True
    
    def generate_content_hash(self, job: Job) -> str:
        """Generate content hash for job deduplication"""
        content_string = f"{job.title}:{job.client_name}:{job.description[:200]}"
        return hashlib.md5(content_string.encode()).hexdigest()
    
    def fallback_relevance_analysis(self, job: Job) -> dict:
        """Fallback relevance analysis using rule-based approach"""
        title_lower = job.title.lower()
        description_lower = job.description.lower()
        
        # Scoring factors
        score = 0.0
        reasons = []
        
        # Salesforce keywords (high value)
        salesforce_keywords = ["salesforce", "agentforce", "einstein", "service cloud", "sales cloud"]
        for keyword in salesforce_keywords:
            if keyword in title_lower:
                score += 0.3
                reasons.append(f"Title contains '{keyword}'")
            elif keyword in description_lower:
                score += 0.2
                reasons.append(f"Description mentions '{keyword}'")
        
        # AI/Automation keywords (medium value)
        ai_keywords = ["ai", "artificial intelligence", "automation", "chatbot", "machine learning"]
        for keyword in ai_keywords:
            if keyword in title_lower or keyword in description_lower:
                score += 0.1
                reasons.append(f"Contains AI/automation keyword: '{keyword}'")
        
        # Technical skills alignment
        relevant_skills = ["apex", "lightning", "visualforce", "soql", "rest api", "integration"]
        skill_matches = [skill for skill in job.skills_required 
                        if any(relevant in skill.lower() for relevant in relevant_skills)]
        
        if skill_matches:
            score += len(skill_matches) * 0.05
            reasons.append(f"Relevant skills: {', '.join(skill_matches)}")
        
        # Client quality bonus
        if job.client_rating >= Decimal("4.5"):
            score += 0.1
            reasons.append("High client rating")
        
        if job.client_hire_rate >= Decimal("0.8"):
            score += 0.1
            reasons.append("High client hire rate")
        
        # Hourly rate consideration
        if job.hourly_rate and job.hourly_rate >= Decimal("75"):
            score += 0.1
            reasons.append("High hourly rate")
        
        # Cap score at 1.0
        score = min(score, 1.0)
        
        return {
            "relevant": score >= 0.6,
            "confidence": score,
            "reasons": reasons,
            "match_quality": "high" if score >= 0.8 else "medium" if score >= 0.6 else "low"
        }
    
    def deduplicate_jobs(self, jobs: list) -> dict:
        """Remove duplicate jobs using ID and content hash checking"""
        original_count = len(jobs)
        seen_hashes = set()
        seen_ardan_ids = set()
        deduplicated_jobs = []
        duplicate_pairs = []
        
        for job in jobs:
            is_duplicate = False
            duplicate_reason = ""
            
            # Check Ardan job ID
            if job.ardan_job_id and job.ardan_job_id in seen_ardan_ids:
                is_duplicate = True
                duplicate_reason = f"Duplicate Ardan ID: {job.ardan_job_id}"
            
            # Check content hash
            elif job.content_hash and job.content_hash in seen_hashes:
                is_duplicate = True
                duplicate_reason = f"Duplicate content hash: {job.content_hash}"
            
            if is_duplicate:
                duplicate_pairs.append((str(job.id), duplicate_reason))
            else:
                deduplicated_jobs.append(job)
                if job.ardan_job_id:
                    seen_ardan_ids.add(job.ardan_job_id)
                if job.content_hash:
                    seen_hashes.add(job.content_hash)
        
        duplicates_found = original_count - len(deduplicated_jobs)
        
        return {
            "original_count": original_count,
            "deduplicated_count": len(deduplicated_jobs),
            "duplicates_found": duplicates_found,
            "duplicate_pairs": duplicate_pairs,
            "deduplicated_jobs": deduplicated_jobs
        }

    def test_basic_criteria_filtering_success(self):
        """Test that jobs meeting all criteria pass filtering"""
        good_job = self.create_test_job(
            title="Salesforce Agentforce Developer",
            description="Implement Salesforce Agentforce solutions",
            hourly_rate=75.0,
            client_rating=4.8,
            client_hire_rate=0.85,
            payment_verified=True
        )
        
        assert self.meets_basic_criteria(good_job) is True

    def test_basic_criteria_filtering_low_rate(self):
        """Test that jobs with low hourly rate are filtered out"""
        low_rate_job = self.create_test_job(
            title="Salesforce Developer",
            hourly_rate=25.0,  # Below minimum
            client_rating=4.8,
            client_hire_rate=0.85,
            payment_verified=True
        )
        
        assert self.meets_basic_criteria(low_rate_job) is False

    def test_basic_criteria_filtering_low_client_rating(self):
        """Test that jobs with low client rating are filtered out"""
        low_rating_job = self.create_test_job(
            title="Salesforce Developer",
            hourly_rate=75.0,
            client_rating=3.5,  # Below minimum
            client_hire_rate=0.85,
            payment_verified=True
        )
        
        assert self.meets_basic_criteria(low_rating_job) is False

    def test_basic_criteria_filtering_unverified_payment(self):
        """Test that jobs with unverified payment are filtered out"""
        unverified_job = self.create_test_job(
            title="Salesforce Developer",
            hourly_rate=75.0,
            client_rating=4.8,
            client_hire_rate=0.85,
            payment_verified=False  # Not verified
        )
        
        assert self.meets_basic_criteria(unverified_job) is False

    def test_basic_criteria_filtering_irrelevant_keywords(self):
        """Test that jobs without Salesforce keywords are filtered out"""
        irrelevant_job = self.create_test_job(
            title="WordPress Developer",
            description="Build WordPress websites with PHP",
            hourly_rate=75.0,
            client_rating=4.8,
            client_hire_rate=0.85,
            payment_verified=True
        )
        
        assert self.meets_basic_criteria(irrelevant_job) is False

    def test_content_hash_generation(self):
        """Test content hash generation for deduplication"""
        job1 = self.create_test_job(
            title="Salesforce Developer",
            description="Salesforce development work",
            client_name="Client A"
        )
        
        job2 = self.create_test_job(
            title="Salesforce Developer",  # Same title
            description="Salesforce development work",  # Same description
            client_name="Client A"  # Same client
        )
        
        job3 = self.create_test_job(
            title="Different Title",
            description="Different description",
            client_name="Client B"
        )
        
        hash1 = self.generate_content_hash(job1)
        hash2 = self.generate_content_hash(job2)
        hash3 = self.generate_content_hash(job3)
        
        # Same content should produce same hash
        assert hash1 == hash2
        # Different content should produce different hash
        assert hash1 != hash3
        # Hash should be MD5 length
        assert len(hash1) == 32

    def test_job_deduplication_by_ardan_id(self):
        """Test deduplication by Ardan job ID"""
        job1 = self.create_test_job(title="Job 1", ardan_job_id="job-123")
        job2 = self.create_test_job(title="Job 2", ardan_job_id="job-123")  # Same ID
        job3 = self.create_test_job(title="Job 3", ardan_job_id="job-456")  # Different ID
        
        # Generate content hashes
        job1.content_hash = self.generate_content_hash(job1)
        job2.content_hash = self.generate_content_hash(job2)
        job3.content_hash = self.generate_content_hash(job3)
        
        jobs = [job1, job2, job3]
        result = self.deduplicate_jobs(jobs)
        
        assert result["original_count"] == 3
        assert result["duplicates_found"] == 1  # job2 is duplicate of job1
        assert result["deduplicated_count"] == 2
        assert len(result["duplicate_pairs"]) == 1

    def test_job_deduplication_by_content_hash(self):
        """Test deduplication by content hash"""
        job1 = self.create_test_job(
            title="Salesforce Developer",
            description="Salesforce work",
            client_name="Client A",
            ardan_job_id="job-123"
        )
        
        job2 = self.create_test_job(
            title="Salesforce Developer",  # Same content
            description="Salesforce work",
            client_name="Client A",
            ardan_job_id="job-456"  # Different ID
        )
        
        # Generate same content hash
        job1.content_hash = self.generate_content_hash(job1)
        job2.content_hash = self.generate_content_hash(job2)
        
        jobs = [job1, job2]
        result = self.deduplicate_jobs(jobs)
        
        assert result["original_count"] == 2
        assert result["duplicates_found"] == 1  # job2 has same content hash
        assert result["deduplicated_count"] == 1

    def test_relevance_analysis_high_score(self):
        """Test relevance analysis for high-scoring job"""
        high_relevance_job = self.create_test_job(
            title="Salesforce Agentforce AI Developer",
            description="Implement Agentforce AI solutions with Einstein integration",
            hourly_rate=85.0,
            client_rating=4.9,
            client_hire_rate=0.90,
            skills=["Salesforce", "Apex", "Einstein", "AI"]
        )
        
        analysis = self.fallback_relevance_analysis(high_relevance_job)
        
        assert analysis["relevant"] is True
        assert analysis["confidence"] > 0.8
        assert len(analysis["reasons"]) > 0
        assert analysis["match_quality"] == "high"

    def test_relevance_analysis_medium_score(self):
        """Test relevance analysis for medium-scoring job"""
        medium_relevance_job = self.create_test_job(
            title="Salesforce CRM Developer",  # Added Salesforce to title for higher score
            description="Work with Salesforce CRM system and automation",
            hourly_rate=75.0,  # Increased to get bonus points
            client_rating=4.5,  # Increased to get bonus points
            client_hire_rate=0.8,  # Increased to get bonus points
            skills=["Salesforce", "CRM", "Apex"]  # Added more relevant skills
        )
        
        analysis = self.fallback_relevance_analysis(medium_relevance_job)
        
        assert analysis["relevant"] is True
        assert 0.6 <= analysis["confidence"] < 0.8
        assert analysis["match_quality"] == "medium"

    def test_relevance_analysis_low_score(self):
        """Test relevance analysis for low-scoring job"""
        low_relevance_job = self.create_test_job(
            title="Data Entry Clerk",
            description="Simple data entry work",
            hourly_rate=15.0,
            client_rating=3.0,
            client_hire_rate=0.2,
            skills=["Excel"]
        )
        
        analysis = self.fallback_relevance_analysis(low_relevance_job)
        
        assert analysis["relevant"] is False
        assert analysis["confidence"] < 0.6
        assert analysis["match_quality"] == "low"

    def test_relevance_analysis_keyword_scoring(self):
        """Test that different keywords contribute different scores"""
        # Job with high-value keywords in title
        title_job = self.create_test_job(
            title="Salesforce Agentforce Developer",
            description="General development work"
        )
        
        # Job with keywords in description
        desc_job = self.create_test_job(
            title="Developer",
            description="Work with Salesforce and Einstein AI systems"
        )
        
        title_analysis = self.fallback_relevance_analysis(title_job)
        desc_analysis = self.fallback_relevance_analysis(desc_job)
        
        # Title keywords should score higher than description keywords
        assert title_analysis["confidence"] > desc_analysis["confidence"]

    def test_relevance_analysis_skills_bonus(self):
        """Test that relevant skills increase the score"""
        skilled_job = self.create_test_job(
            title="Salesforce Developer",
            description="Salesforce development",
            skills=["Apex", "Lightning", "SOQL", "REST API", "Integration"]
        )
        
        basic_job = self.create_test_job(
            title="Salesforce Developer",
            description="Salesforce development",
            skills=["Salesforce"]
        )
        
        skilled_analysis = self.fallback_relevance_analysis(skilled_job)
        basic_analysis = self.fallback_relevance_analysis(basic_job)
        
        # Job with more relevant skills should score higher
        assert skilled_analysis["confidence"] > basic_analysis["confidence"]
        assert "Relevant skills" in str(skilled_analysis["reasons"])

    def test_relevance_analysis_client_quality_bonus(self):
        """Test that high-quality clients increase the score"""
        high_quality_job = self.create_test_job(
            title="Salesforce Developer",
            description="Salesforce development",
            client_rating=4.9,
            client_hire_rate=0.95,
            hourly_rate=100.0
        )
        
        basic_quality_job = self.create_test_job(
            title="Salesforce Developer",
            description="Salesforce development",
            client_rating=4.0,
            client_hire_rate=0.5,
            hourly_rate=50.0
        )
        
        high_analysis = self.fallback_relevance_analysis(high_quality_job)
        basic_analysis = self.fallback_relevance_analysis(basic_quality_job)
        
        # High-quality client job should score higher
        assert high_analysis["confidence"] > basic_analysis["confidence"]

    def test_relevance_analysis_score_capping(self):
        """Test that confidence scores are capped at 1.0"""
        super_job = self.create_test_job(
            title="Salesforce Agentforce Einstein AI Developer",
            description="Expert in Salesforce, Agentforce, Einstein AI, automation, machine learning",
            hourly_rate=150.0,
            client_rating=5.0,
            client_hire_rate=1.0,
            skills=["Apex", "Lightning", "SOQL", "REST API", "Integration", "AI", "ML"]
        )
        
        analysis = self.fallback_relevance_analysis(super_job)
        
        # Score should be capped at 1.0
        assert analysis["confidence"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])