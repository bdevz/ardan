"""
Recommendation System - Profile optimization and improvement recommendations
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import json
import statistics
from collections import defaultdict, Counter

from sqlalchemy import select, func, and_, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    JobModel, ApplicationModel, ProposalModel, 
    PerformanceMetricModel, SystemConfigModel
)
from shared.utils import setup_logging
from .analytics_engine import analytics_engine
from .performance_tracking_service import performance_tracking_service

logger = setup_logging("recommendation-system")


class Recommendation:
    """Represents a recommendation for improvement"""
    
    def __init__(
        self,
        category: str,
        title: str,
        description: str,
        priority: str,
        impact_score: float,
        effort_score: float,
        confidence: float,
        actionable_steps: List[str],
        supporting_data: Dict[str, Any] = None
    ):
        self.category = category
        self.title = title
        self.description = description
        self.priority = priority  # "high", "medium", "low"
        self.impact_score = impact_score  # 0-1 scale
        self.effort_score = effort_score  # 0-1 scale (lower = less effort)
        self.confidence = confidence  # 0-1 scale
        self.actionable_steps = actionable_steps
        self.supporting_data = supporting_data or {}
        self.created_at = datetime.utcnow()
        
        # Calculate priority score for ranking
        self.priority_score = (impact_score * confidence) / (effort_score + 0.1)


class RecommendationSystem:
    """System for generating profile optimization and improvement recommendations"""
    
    async def generate_comprehensive_recommendations(
        self, 
        db: AsyncSession,
        analysis_days: int = 60
    ) -> Dict[str, Any]:
        """Generate comprehensive recommendations across all categories"""
        try:
            logger.info("Generating comprehensive recommendations")
            
            # Get performance data for analysis
            performance_data = await self._gather_performance_data(db, analysis_days)
            
            # Generate recommendations by category
            profile_recommendations = await self._generate_profile_recommendations(db, performance_data)
            proposal_recommendations = await self._generate_proposal_recommendations(db, performance_data)
            strategy_recommendations = await self._generate_strategy_recommendations(db, performance_data)
            timing_recommendations = await self._generate_timing_recommendations(db, performance_data)
            technical_recommendations = await self._generate_technical_recommendations(db, performance_data)
            
            # Combine all recommendations
            all_recommendations = (
                profile_recommendations + 
                proposal_recommendations + 
                strategy_recommendations + 
                timing_recommendations + 
                technical_recommendations
            )
            
            # Rank recommendations by priority score
            ranked_recommendations = sorted(
                all_recommendations, 
                key=lambda x: x.priority_score, 
                reverse=True
            )
            
            # Categorize by priority
            high_priority = [r for r in ranked_recommendations if r.priority == "high"]
            medium_priority = [r for r in ranked_recommendations if r.priority == "medium"]
            low_priority = [r for r in ranked_recommendations if r.priority == "low"]
            
            return {
                "analysis_date": datetime.utcnow().isoformat(),
                "analysis_period_days": analysis_days,
                "total_recommendations": len(all_recommendations),
                "recommendations": {
                    "high_priority": [self._recommendation_to_dict(r) for r in high_priority],
                    "medium_priority": [self._recommendation_to_dict(r) for r in medium_priority],
                    "low_priority": [self._recommendation_to_dict(r) for r in low_priority]
                },
                "summary": {
                    "top_recommendation": self._recommendation_to_dict(ranked_recommendations[0]) if ranked_recommendations else None,
                    "categories": {
                        "profile": len(profile_recommendations),
                        "proposal": len(proposal_recommendations),
                        "strategy": len(strategy_recommendations),
                        "timing": len(timing_recommendations),
                        "technical": len(technical_recommendations)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating comprehensive recommendations: {e}")
            raise
    
    async def generate_profile_optimization_plan(
        self, 
        db: AsyncSession,
        target_improvement: float = 0.2  # 20% improvement target
    ) -> Dict[str, Any]:
        """Generate a specific optimization plan for profile improvement"""
        try:
            # Get current profile performance
            current_performance = await self._analyze_current_profile_performance(db)
            
            # Identify improvement opportunities
            opportunities = await self._identify_profile_improvement_opportunities(db, current_performance)
            
            # Create optimization plan
            optimization_plan = await self._create_optimization_plan(
                opportunities, target_improvement
            )
            
            # Estimate timeline and resources
            timeline = await self._estimate_optimization_timeline(optimization_plan)
            
            return {
                "plan_date": datetime.utcnow().isoformat(),
                "current_performance": current_performance,
                "target_improvement": target_improvement,
                "optimization_plan": optimization_plan,
                "timeline": timeline,
                "expected_outcomes": await self._calculate_expected_outcomes(optimization_plan)
            }
            
        except Exception as e:
            logger.error(f"Error generating profile optimization plan: {e}")
            raise
    
    async def get_personalized_recommendations(
        self, 
        db: AsyncSession,
        focus_areas: List[str] = None,
        max_recommendations: int = 10
    ) -> List[Dict[str, Any]]:
        """Get personalized recommendations based on specific focus areas"""
        try:
            # Get all recommendations
            all_recommendations = await self.generate_comprehensive_recommendations(db)
            
            # Filter by focus areas if specified
            if focus_areas:
                filtered_recommendations = []
                for priority_level in ["high_priority", "medium_priority", "low_priority"]:
                    for rec in all_recommendations["recommendations"][priority_level]:
                        if rec["category"] in focus_areas:
                            filtered_recommendations.append(rec)
            else:
                # Flatten all recommendations
                filtered_recommendations = []
                for priority_level in ["high_priority", "medium_priority", "low_priority"]:
                    filtered_recommendations.extend(all_recommendations["recommendations"][priority_level])
            
            # Sort by priority score and limit
            sorted_recommendations = sorted(
                filtered_recommendations,
                key=lambda x: x["priority_score"],
                reverse=True
            )[:max_recommendations]
            
            return sorted_recommendations
            
        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {e}")
            raise
    
    async def track_recommendation_implementation(
        self, 
        db: AsyncSession,
        recommendation_id: str,
        implementation_status: str,
        notes: str = None
    ) -> Dict[str, Any]:
        """Track the implementation of a recommendation"""
        try:
            # Record implementation tracking
            tracking_data = {
                "recommendation_id": recommendation_id,
                "implementation_status": implementation_status,
                "implementation_date": datetime.utcnow().isoformat(),
                "notes": notes
            }
            
            # Store in performance metrics
            metric = PerformanceMetricModel(
                metric_type="recommendation_implementation",
                metric_value=Decimal("1"),
                time_period="event",
                date_recorded=datetime.utcnow(),
                metadata=tracking_data
            )
            
            db.add(metric)
            await db.commit()
            
            return {
                "status": "tracked",
                "recommendation_id": recommendation_id,
                "implementation_status": implementation_status,
                "tracking_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error tracking recommendation implementation: {e}")
            raise
    
    # Private helper methods
    
    async def _gather_performance_data(
        self, 
        db: AsyncSession, 
        days: int
    ) -> Dict[str, Any]:
        """Gather comprehensive performance data for analysis"""
        # Get pipeline analytics
        pipeline_analytics = await performance_tracking_service.get_pipeline_analytics(db, days)
        
        # Get success patterns
        success_patterns = await analytics_engine.analyze_success_patterns(db)
        
        # Get current system configuration
        current_config = await SystemConfigModel.get_config(db)
        
        return {
            "pipeline_analytics": pipeline_analytics,
            "success_patterns": success_patterns,
            "current_config": {
                "daily_application_limit": current_config.daily_application_limit,
                "min_hourly_rate": float(current_config.min_hourly_rate),
                "target_hourly_rate": float(current_config.target_hourly_rate),
                "min_client_rating": float(current_config.min_client_rating),
                "keywords_include": current_config.keywords_include,
                "keywords_exclude": current_config.keywords_exclude
            }
        }
    
    async def _generate_profile_recommendations(
        self, 
        db: AsyncSession, 
        performance_data: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate profile-specific recommendations"""
        recommendations = []
        
        # Analyze success patterns for profile insights
        success_patterns = performance_data.get("success_patterns", {})
        
        if "error" not in success_patterns:
            patterns = success_patterns.get("patterns", {})
            
            # Hourly rate recommendations
            job_patterns = patterns.get("job_characteristics", {})
            if "hourly_rate" in job_patterns:
                rate_data = job_patterns["hourly_rate"]
                if rate_data.get("statistical_significance", False):
                    current_min = performance_data["current_config"]["min_hourly_rate"]
                    successful_avg = rate_data["successful_avg"]
                    
                    if successful_avg > current_min * 1.1:
                        recommendations.append(Recommendation(
                            category="profile",
                            title="Optimize Hourly Rate Targeting",
                            description=f"Successful applications average ${successful_avg:.2f}/hr, "
                                      f"significantly higher than your current minimum of ${current_min:.2f}/hr",
                            priority="high",
                            impact_score=0.8,
                            effort_score=0.2,
                            confidence=0.9,
                            actionable_steps=[
                                f"Increase minimum hourly rate to ${successful_avg * 0.9:.2f}/hr",
                                "Update profile to reflect premium positioning",
                                "Highlight high-value skills and certifications",
                                "Add case studies demonstrating ROI"
                            ],
                            supporting_data=rate_data
                        ))
            
            # Skills and expertise recommendations
            recommendations.append(Recommendation(
                category="profile",
                title="Enhance Salesforce Agentforce Specialization",
                description="Position yourself as a specialized Salesforce Agentforce expert to command higher rates",
                priority="high",
                impact_score=0.9,
                effort_score=0.6,
                confidence=0.8,
                actionable_steps=[
                    "Add Salesforce Agentforce certification to profile",
                    "Create portfolio showcasing Agentforce implementations",
                    "Write case studies demonstrating AI automation results",
                    "Update profile headline to emphasize Agentforce expertise",
                    "Add relevant keywords: 'Einstein AI', 'Salesforce AI', 'Agent Builder'"
                ]
            ))
            
            # Portfolio recommendations
            recommendations.append(Recommendation(
                category="profile",
                title="Strengthen Portfolio with Quantified Results",
                description="Add specific metrics and outcomes to portfolio pieces to increase credibility",
                priority="medium",
                impact_score=0.7,
                effort_score=0.5,
                confidence=0.7,
                actionable_steps=[
                    "Add ROI metrics to existing portfolio pieces",
                    "Include before/after screenshots of implementations",
                    "Quantify time savings and efficiency gains",
                    "Add client testimonials with specific results",
                    "Create video demos of complex implementations"
                ]
            ))
        
        return recommendations
    
    async def _generate_proposal_recommendations(
        self, 
        db: AsyncSession, 
        performance_data: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate proposal-specific recommendations"""
        recommendations = []
        
        success_patterns = performance_data.get("success_patterns", {})
        
        if "error" not in success_patterns:
            patterns = success_patterns.get("patterns", {})
            proposal_patterns = patterns.get("proposal_characteristics", {})
            
            # Proposal length recommendations
            if "proposal_length" in proposal_patterns:
                length_data = proposal_patterns["proposal_length"]
                if length_data.get("statistical_significance", False):
                    successful_avg = length_data["successful_avg_chars"]
                    
                    recommendations.append(Recommendation(
                        category="proposal",
                        title="Optimize Proposal Length",
                        description=f"Successful proposals average {successful_avg:.0f} characters. "
                                  f"Adjust your proposals to this optimal length.",
                        priority="medium",
                        impact_score=0.6,
                        effort_score=0.3,
                        confidence=0.7,
                        actionable_steps=[
                            f"Target proposal length of {successful_avg:.0f} characters",
                            "Use concise, impactful language",
                            "Focus on client benefits rather than features",
                            "Include specific examples without excessive detail"
                        ],
                        supporting_data=length_data
                    ))
            
            # Bid amount recommendations
            if "bid_amount" in proposal_patterns:
                bid_data = proposal_patterns["bid_amount"]
                if bid_data.get("statistical_significance", False):
                    successful_avg = bid_data["successful_avg"]
                    
                    recommendations.append(Recommendation(
                        category="proposal",
                        title="Optimize Bid Strategy",
                        description=f"Successful bids average ${successful_avg:.2f}/hr. "
                                  f"Consider adjusting your bidding strategy.",
                        priority="high",
                        impact_score=0.8,
                        effort_score=0.2,
                        confidence=0.8,
                        actionable_steps=[
                            f"Target bids around ${successful_avg:.2f}/hr for similar projects",
                            "Justify higher rates with specific value propositions",
                            "Consider project complexity when setting rates",
                            "Use tiered pricing for different service levels"
                        ],
                        supporting_data=bid_data
                    ))
        
        # General proposal quality recommendations
        recommendations.append(Recommendation(
            category="proposal",
            title="Implement Proposal Template Optimization",
            description="Standardize and optimize proposal templates based on successful patterns",
            priority="medium",
            impact_score=0.7,
            effort_score=0.4,
            confidence=0.8,
            actionable_steps=[
                "Create templates for different project types",
                "Include client-specific customization sections",
                "Add social proof and relevant case studies",
                "Use clear project timeline and deliverables",
                "Include risk mitigation strategies"
            ]
        ))
        
        return recommendations
    
    async def _generate_strategy_recommendations(
        self, 
        db: AsyncSession, 
        performance_data: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate strategy-specific recommendations"""
        recommendations = []
        
        pipeline_analytics = performance_data.get("pipeline_analytics", {})
        conversion_rates = pipeline_analytics.get("conversion_rates", {})
        
        # Application volume strategy
        response_rate = conversion_rates.get("application_to_response", 0)
        if response_rate < 10:  # Less than 10% response rate
            recommendations.append(Recommendation(
                category="strategy",
                title="Improve Job Selection Criteria",
                description=f"Low response rate ({response_rate:.1f}%) suggests need for better job targeting",
                priority="high",
                impact_score=0.9,
                effort_score=0.3,
                confidence=0.8,
                actionable_steps=[
                    "Increase minimum client rating threshold",
                    "Focus on payment-verified clients only",
                    "Target jobs with fewer competing proposals",
                    "Prioritize repeat clients and referrals",
                    "Avoid jobs with unrealistic budgets"
                ]
            ))
        
        # Keyword strategy
        current_keywords = performance_data["current_config"]["keywords_include"]
        recommendations.append(Recommendation(
            category="strategy",
            title="Expand Keyword Strategy",
            description="Broaden keyword targeting to capture more relevant opportunities",
            priority="medium",
            impact_score=0.6,
            effort_score=0.2,
            confidence=0.7,
            actionable_steps=[
                "Add emerging Salesforce technologies (MuleSoft, Tableau)",
                "Include industry-specific terms (Healthcare, Finance)",
                "Target integration-focused keywords",
                "Monitor competitor keywords and trends",
                "Use long-tail keywords for niche specializations"
            ]
        ))
        
        return recommendations
    
    async def _generate_timing_recommendations(
        self, 
        db: AsyncSession, 
        performance_data: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate timing-specific recommendations"""
        recommendations = []
        
        success_patterns = performance_data.get("success_patterns", {})
        
        if "error" not in success_patterns:
            patterns = success_patterns.get("patterns", {})
            timing_patterns = patterns.get("timing_patterns", {})
            
            optimal_hours = timing_patterns.get("optimal_hours", [])
            optimal_days = timing_patterns.get("optimal_days", [])
            
            if optimal_hours or optimal_days:
                recommendations.append(Recommendation(
                    category="timing",
                    title="Optimize Application Timing",
                    description="Apply during optimal hours and days for higher success rates",
                    priority="medium",
                    impact_score=0.5,
                    effort_score=0.1,
                    confidence=0.6,
                    actionable_steps=[
                        f"Schedule applications during optimal hours: {optimal_hours}",
                        f"Focus on optimal days: {optimal_days}",
                        "Avoid late night and weekend applications",
                        "Consider client time zones for international projects",
                        "Set up automated scheduling for optimal timing"
                    ],
                    supporting_data=timing_patterns
                ))
        
        # General timing recommendations
        recommendations.append(Recommendation(
            category="timing",
            title="Implement Quick Response Strategy",
            description="Apply to jobs quickly after posting to increase visibility",
            priority="medium",
            impact_score=0.6,
            effort_score=0.3,
            confidence=0.7,
            actionable_steps=[
                "Set up job alerts for immediate notifications",
                "Prepare template responses for quick customization",
                "Target jobs posted within the last 2 hours",
                "Use automation for faster application processing",
                "Monitor job boards multiple times per day"
            ]
        ))
        
        return recommendations
    
    async def _generate_technical_recommendations(
        self, 
        db: AsyncSession, 
        performance_data: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate technical system recommendations"""
        recommendations = []
        
        # System performance recommendations
        recommendations.append(Recommendation(
            category="technical",
            title="Enhance Automation Monitoring",
            description="Improve system monitoring and alerting for better performance tracking",
            priority="low",
            impact_score=0.4,
            effort_score=0.6,
            confidence=0.8,
            actionable_steps=[
                "Set up performance dashboards",
                "Implement real-time alerting for system issues",
                "Add detailed logging for all automation steps",
                "Create automated performance reports",
                "Set up backup systems for critical processes"
            ]
        ))
        
        return recommendations
    
    def _recommendation_to_dict(self, recommendation: Recommendation) -> Dict[str, Any]:
        """Convert recommendation object to dictionary"""
        return {
            "category": recommendation.category,
            "title": recommendation.title,
            "description": recommendation.description,
            "priority": recommendation.priority,
            "impact_score": recommendation.impact_score,
            "effort_score": recommendation.effort_score,
            "confidence": recommendation.confidence,
            "priority_score": recommendation.priority_score,
            "actionable_steps": recommendation.actionable_steps,
            "supporting_data": recommendation.supporting_data,
            "created_at": recommendation.created_at.isoformat()
        }
    
    async def _analyze_current_profile_performance(self, db: AsyncSession) -> Dict[str, Any]:
        """Analyze current profile performance metrics"""
        # This would analyze profile-specific metrics
        return {
            "profile_views": 0,
            "proposal_acceptance_rate": 0.0,
            "average_project_value": 0.0,
            "client_satisfaction": 0.0,
            "repeat_client_rate": 0.0
        }
    
    async def _identify_profile_improvement_opportunities(
        self, 
        db: AsyncSession, 
        current_performance: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify specific profile improvement opportunities"""
        return []
    
    async def _create_optimization_plan(
        self, 
        opportunities: List[Dict[str, Any]], 
        target_improvement: float
    ) -> Dict[str, Any]:
        """Create a structured optimization plan"""
        return {
            "phases": [],
            "timeline": "3 months",
            "resources_required": [],
            "success_metrics": []
        }
    
    async def _estimate_optimization_timeline(self, optimization_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate timeline for optimization plan implementation"""
        return {
            "total_duration": "3 months",
            "phases": [],
            "milestones": []
        }
    
    async def _calculate_expected_outcomes(self, optimization_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate expected outcomes from optimization plan"""
        return {
            "expected_improvement": 0.2,
            "confidence_interval": [0.1, 0.3],
            "key_metrics": []
        }


# Global service instance
recommendation_system = RecommendationSystem()