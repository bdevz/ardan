"""
LLM-based Proposal Generation Service using OpenAI API
"""
import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID

import openai
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import JobModel, ProposalModel
from shared.models import Job, Proposal, ProposalStatus
from shared.config import settings
from shared.utils import setup_logging

logger = setup_logging("llm-proposal-service")


class ProposalTemplate:
    """Proposal template structure"""
    
    def __init__(self):
        self.introduction_template = """
        Dear {client_name},

        I am excited to apply for your {job_title} position. As a seasoned Salesforce Agentforce Developer with {experience_years}+ years of experience, I specialize in building AI-powered customer service solutions that drive measurable business results. Your project requiring {key_requirements} aligns perfectly with my expertise in {relevant_skills}.
        """
        
        self.experience_template = """
        In my recent projects, I have successfully:
        • Implemented Agentforce solutions that reduced customer response time by {response_improvement}% and increased satisfaction scores by {satisfaction_improvement}%
        • Developed Einstein AI integrations that automated {automation_percentage}% of routine customer inquiries, saving {time_savings} hours per week
        • Built custom Salesforce applications serving {user_count}+ users with {uptime_percentage}% uptime and {performance_metric} average response time
        
        My technical expertise includes {technical_skills}, and I have a proven track record of delivering projects {delivery_metric} and {budget_metric}.
        """
        
        self.call_to_action_template = """
        I am available to start immediately and can deliver your project within {estimated_timeline}. I would love to discuss how my experience with {specific_experience} can help you achieve {project_goals}. 
        
        Let's schedule a brief call to discuss your requirements in detail and how I can contribute to your success.

        Best regards,
        {developer_name}
        """


class LLMProposalService:
    """Advanced proposal generation service using OpenAI LLM"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.template = ProposalTemplate()
        
        # Developer profile data
        self.developer_profile = {
            "name": "Salesforce Agentforce Developer",
            "experience_years": 5,
            "specializations": [
                "Salesforce Agentforce Development",
                "Einstein AI Integration", 
                "Customer Service Automation",
                "Apex Development",
                "Lightning Components",
                "Service Cloud Implementation"
            ],
            "metrics": {
                "response_improvement": "40-60",
                "satisfaction_improvement": "25-35", 
                "automation_percentage": "70-85",
                "time_savings": "20-30",
                "user_count": "500-2000",
                "uptime_percentage": "99.9",
                "performance_metric": "< 200ms",
                "delivery_metric": "on-time and within budget",
                "budget_metric": "under budget"
            },
            "technical_skills": [
                "Salesforce Agentforce", "Einstein AI", "Apex", "Lightning Web Components",
                "Service Cloud", "Integration APIs", "Workflow Automation", "Data Migration"
            ]
        }
    
    async def generate_proposal(
        self,
        job: Job,
        custom_instructions: Optional[str] = None,
        template_style: str = "professional"
    ) -> Dict[str, Any]:
        """Generate a comprehensive proposal using LLM"""
        try:
            # Analyze job requirements
            job_analysis = await self._analyze_job_requirements(job)
            
            # Generate proposal content using LLM
            proposal_content = await self._generate_llm_proposal(job, job_analysis, custom_instructions)
            
            # Calculate optimal bid amount
            bid_amount = await self._calculate_optimal_bid(job, job_analysis)
            
            # Generate quality score
            quality_score = await self._assess_proposal_quality(proposal_content, job)
            
            # Select relevant attachments
            attachments = await self._select_relevant_attachments(job, job_analysis)
            
            return {
                "content": proposal_content,
                "bid_amount": bid_amount,
                "quality_score": quality_score,
                "attachments": attachments,
                "job_analysis": job_analysis,
                "generated_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error generating LLM proposal: {e}")
            raise
    
    async def _analyze_job_requirements(self, job: Job) -> Dict[str, Any]:
        """Analyze job requirements using LLM"""
        try:
            analysis_prompt = f"""
            Analyze this Upwork job posting for a Salesforce Agentforce Developer and extract key information:

            Job Title: {job.title}
            Job Description: {job.description}
            Skills Required: {', '.join(job.skills_required) if job.skills_required else 'Not specified'}
            Budget: ${job.hourly_rate}/hr if job.hourly_rate else f"${job.budget_min}-${job.budget_max}" if job.budget_min else "Not specified"}
            Client Rating: {job.client_rating}

            Please provide a JSON response with:
            1. key_requirements: List of main technical requirements
            2. project_complexity: "simple", "moderate", or "complex"
            3. estimated_timeline: Estimated project duration
            4. relevant_skills: Skills from my profile that match this job
            5. project_goals: What the client wants to achieve
            6. pain_points: Problems the client is trying to solve
            7. value_proposition: How I can provide unique value
            8. risk_factors: Potential challenges or red flags
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert Salesforce consultant analyzing job requirements. Respond only with valid JSON."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            analysis = json.loads(response.choices[0].message.content)
            return analysis
            
        except Exception as e:
            logger.warning(f"LLM job analysis failed, using fallback: {e}")
            return self._fallback_job_analysis(job)
    
    async def _generate_llm_proposal(
        self,
        job: Job,
        job_analysis: Dict[str, Any],
        custom_instructions: Optional[str]
    ) -> str:
        """Generate proposal content using LLM"""
        try:
            # Prepare context for LLM
            context = {
                "job": {
                    "title": job.title,
                    "description": job.description[:500],  # Truncate for token limits
                    "client_name": job.client_name or "Hiring Manager",
                    "skills": job.skills_required or [],
                    "budget": f"${job.hourly_rate}/hr" if job.hourly_rate else "Budget not specified"
                },
                "analysis": job_analysis,
                "profile": self.developer_profile,
                "custom_instructions": custom_instructions
            }
            
            proposal_prompt = f"""
            Generate a professional, personalized proposal for this Upwork job. The proposal should be exactly 3 paragraphs:

            Job Context:
            - Title: {context['job']['title']}
            - Client: {context['job']['client_name']}
            - Key Requirements: {', '.join(job_analysis.get('key_requirements', []))}
            - Project Goals: {job_analysis.get('project_goals', 'Not specified')}
            - Complexity: {job_analysis.get('project_complexity', 'moderate')}

            Developer Profile:
            - Experience: {self.developer_profile['experience_years']}+ years in Salesforce Agentforce
            - Specializations: {', '.join(self.developer_profile['specializations'])}
            - Key Metrics: Improved response times by 40-60%, increased satisfaction by 25-35%

            Custom Instructions: {custom_instructions or 'None'}

            Requirements for the proposal:
            1. Paragraph 1: Goal-focused introduction that addresses the client's specific needs
            2. Paragraph 2: Relevant experience with specific metrics and achievements
            3. Paragraph 3: Clear call-to-action with timeline and next steps

            The proposal should be:
            - Professional but conversational
            - Specific to this job (not generic)
            - Include relevant metrics and achievements
            - Show understanding of client's pain points
            - Demonstrate unique value proposition
            - Be confident but not overselling
            - End with a clear call-to-action

            Generate only the proposal text, no additional formatting or explanations.
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert Salesforce Agentforce Developer writing winning Upwork proposals. Write in first person, be specific and results-focused."},
                    {"role": "user", "content": proposal_prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.warning(f"LLM proposal generation failed, using template: {e}")
            return self._generate_template_proposal(job, job_analysis, custom_instructions)
    
    async def _calculate_optimal_bid(self, job: Job, job_analysis: Dict[str, Any]) -> Decimal:
        """Calculate optimal bid amount using LLM analysis"""
        try:
            # Base bid calculation
            if job.hourly_rate:
                base_rate = job.hourly_rate
            elif job.budget_min and job.budget_max:
                # For fixed price, estimate hourly equivalent
                avg_budget = (job.budget_min + job.budget_max) / 2
                estimated_hours = self._estimate_project_hours(job_analysis.get('project_complexity', 'moderate'))
                base_rate = avg_budget / estimated_hours
            else:
                base_rate = Decimal("75.0")  # Default rate
            
            # Adjust based on complexity and competition
            complexity_multiplier = {
                'simple': Decimal("0.95"),
                'moderate': Decimal("1.0"),
                'complex': Decimal("1.1")
            }
            
            complexity = job_analysis.get('project_complexity', 'moderate')
            adjusted_rate = base_rate * complexity_multiplier.get(complexity, Decimal("1.0"))
            
            # Ensure minimum rate
            min_rate = Decimal("50.0")
            optimal_rate = max(adjusted_rate, min_rate)
            
            # Cap at reasonable maximum
            max_rate = Decimal("150.0")
            optimal_rate = min(optimal_rate, max_rate)
            
            return optimal_rate
            
        except Exception as e:
            logger.warning(f"Bid calculation failed, using default: {e}")
            return Decimal("75.0")
    
    async def _assess_proposal_quality(self, proposal_content: str, job: Job) -> Decimal:
        """Assess proposal quality using LLM"""
        try:
            quality_prompt = f"""
            Assess the quality of this Upwork proposal on a scale of 0.0 to 1.0:

            Job Title: {job.title}
            Proposal:
            {proposal_content}

            Evaluate based on:
            1. Relevance to job requirements (0-0.3)
            2. Specific experience and metrics (0-0.2)
            3. Professional tone and clarity (0-0.2)
            4. Personalization and client focus (0-0.2)
            5. Clear call-to-action (0-0.1)

            Respond with only a decimal number between 0.0 and 1.0.
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a proposal quality assessor. Respond only with a decimal number."},
                    {"role": "user", "content": quality_prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            quality_score = float(response.choices[0].message.content.strip())
            return Decimal(str(min(max(quality_score, 0.0), 1.0)))
            
        except Exception as e:
            logger.warning(f"Quality assessment failed, using heuristic: {e}")
            return self._heuristic_quality_score(proposal_content, job)
    
    async def _select_relevant_attachments(self, job: Job, job_analysis: Dict[str, Any]) -> List[str]:
        """Select relevant attachments based on job requirements"""
        # This would integrate with Google Drive to select relevant portfolio items
        # For now, return default attachments based on job analysis
        
        default_attachments = [
            "salesforce_portfolio.pdf",
            "agentforce_case_studies.pdf"
        ]
        
        # Add specific attachments based on job requirements
        key_requirements = job_analysis.get('key_requirements', [])
        
        if any('einstein' in req.lower() for req in key_requirements):
            default_attachments.append("einstein_ai_projects.pdf")
        
        if any('integration' in req.lower() for req in key_requirements):
            default_attachments.append("integration_examples.pdf")
        
        if any('lightning' in req.lower() for req in key_requirements):
            default_attachments.append("lightning_components_showcase.pdf")
        
        return default_attachments[:3]  # Limit to 3 attachments
    
    def _fallback_job_analysis(self, job: Job) -> Dict[str, Any]:
        """Fallback job analysis when LLM fails"""
        return {
            "key_requirements": job.skills_required or ["Salesforce Development"],
            "project_complexity": "moderate",
            "estimated_timeline": "2-4 weeks",
            "relevant_skills": ["Salesforce", "Agentforce", "Apex"],
            "project_goals": "Improve customer service efficiency",
            "pain_points": ["Manual processes", "Slow response times"],
            "value_proposition": "Automated solutions with proven results",
            "risk_factors": []
        }
    
    def _generate_template_proposal(
        self,
        job: Job,
        job_analysis: Dict[str, Any],
        custom_instructions: Optional[str]
    ) -> str:
        """Generate proposal using templates when LLM fails"""
        client_name = job.client_name or "Hiring Manager"
        
        # Introduction paragraph
        introduction = f"""Dear {client_name},

I am excited to apply for your {job.title} position. As a seasoned Salesforce Agentforce Developer with {self.developer_profile['experience_years']}+ years of experience, I specialize in building AI-powered customer service solutions that drive measurable business results. Your project requiring {', '.join(job_analysis.get('key_requirements', ['Salesforce development']))} aligns perfectly with my expertise in {', '.join(self.developer_profile['specializations'][:3])}."""
        
        # Experience paragraph
        experience = f"""In my recent projects, I have successfully implemented Agentforce solutions that reduced customer response time by 40-60% and increased satisfaction scores by 25-35%. I've developed Einstein AI integrations that automated 70-85% of routine customer inquiries, saving 20-30 hours per week for client teams. My custom Salesforce applications serve 500+ users with 99.9% uptime and sub-200ms response times. I consistently deliver projects on-time and within budget."""
        
        # Call to action paragraph
        timeline = job_analysis.get('estimated_timeline', '2-4 weeks')
        call_to_action = f"""I am available to start immediately and can deliver your project within {timeline}. I would love to discuss how my experience with {', '.join(job_analysis.get('relevant_skills', ['Salesforce', 'Agentforce']))} can help you achieve {job_analysis.get('project_goals', 'your business objectives')}.

Let's schedule a brief call to discuss your requirements in detail and how I can contribute to your success.

Best regards,
{self.developer_profile['name']}"""
        
        # Add custom instructions if provided
        if custom_instructions:
            call_to_action = f"{call_to_action}\n\nAdditional note: {custom_instructions}"
        
        return f"{introduction}\n\n{experience}\n\n{call_to_action}"
    
    def _estimate_project_hours(self, complexity: str) -> int:
        """Estimate project hours based on complexity"""
        hours_map = {
            'simple': 20,
            'moderate': 40,
            'complex': 80
        }
        return hours_map.get(complexity, 40)
    
    def _heuristic_quality_score(self, proposal_content: str, job: Job) -> Decimal:
        """Calculate quality score using heuristics"""
        score = Decimal("0.5")  # Base score
        
        # Check length (should be substantial but not too long)
        word_count = len(proposal_content.split())
        if 150 <= word_count <= 400:
            score += Decimal("0.1")
        
        # Check for specific mentions
        content_lower = proposal_content.lower()
        if job.client_name and job.client_name.lower() in content_lower:
            score += Decimal("0.1")
        
        # Check for metrics/numbers
        import re
        if re.search(r'\d+%|\d+\+|\d+ years', proposal_content):
            score += Decimal("0.1")
        
        # Check for call to action
        if any(phrase in content_lower for phrase in ['call', 'discuss', 'schedule', 'contact']):
            score += Decimal("0.1")
        
        return min(score, Decimal("1.0"))


# Global service instance
llm_proposal_service = LLMProposalService()