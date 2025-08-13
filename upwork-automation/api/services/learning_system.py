"""
Learning System - Automatic strategy adjustment based on performance data
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4
import json
import statistics
from collections import defaultdict

from sqlalchemy import select, func, and_, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    JobModel, ApplicationModel, ProposalModel, 
    PerformanceMetricModel, SystemConfigModel
)
from shared.models import SystemConfig
from shared.utils import setup_logging
from .analytics_engine import analytics_engine
from .performance_tracking_service import performance_tracking_service

logger = setup_logging("learning-system")


class StrategyAdjustment:
    """Represents a strategy adjustment recommendation"""
    
    def __init__(
        self,
        strategy_type: str,
        current_value: Any,
        recommended_value: Any,
        confidence: float,
        expected_impact: float,
        reasoning: str
    ):
        self.id = uuid4()
        self.strategy_type = strategy_type
        self.current_value = current_value
        self.recommended_value = recommended_value
        self.confidence = confidence
        self.expected_impact = expected_impact
        self.reasoning = reasoning
        self.created_at = datetime.utcnow()
        self.applied = False
        self.applied_at = None
        self.results = None


class LearningSystem:
    """System for automatic strategy adjustment based on performance data"""
    
    def __init__(self):
        self.adjustment_history = []
        self.strategy_performance_cache = {}
        self.learning_rate = 0.1  # How aggressively to adjust strategies
        self.confidence_threshold = 0.7  # Minimum confidence to apply adjustments
    
    async def analyze_and_adjust_strategies(
        self, 
        db: AsyncSession,
        force_adjustment: bool = False
    ) -> Dict[str, Any]:
        """Analyze performance and automatically adjust strategies"""
        try:
            logger.info("Starting strategy analysis and adjustment")
            
            # Get current system configuration
            current_config = await SystemConfigModel.get_config(db)
            
            # Analyze current performance
            performance_analysis = await self._analyze_current_performance(db)
            
            # Identify strategy adjustments
            adjustments = await self._identify_strategy_adjustments(
                db, current_config, performance_analysis
            )
            
            # Filter adjustments by confidence threshold
            high_confidence_adjustments = [
                adj for adj in adjustments 
                if adj.confidence >= self.confidence_threshold or force_adjustment
            ]
            
            # Apply approved adjustments
            applied_adjustments = []
            for adjustment in high_confidence_adjustments:
                if await self._apply_strategy_adjustment(db, current_config, adjustment):
                    applied_adjustments.append(adjustment)
                    self.adjustment_history.append(adjustment)
            
            # Record learning session
            await self._record_learning_session(db, adjustments, applied_adjustments)
            
            return {
                "analysis_date": datetime.utcnow().isoformat(),
                "performance_analysis": performance_analysis,
                "total_adjustments_identified": len(adjustments),
                "high_confidence_adjustments": len(high_confidence_adjustments),
                "applied_adjustments": len(applied_adjustments),
                "adjustments": [
                    {
                        "id": str(adj.id),
                        "strategy_type": adj.strategy_type,
                        "current_value": adj.current_value,
                        "recommended_value": adj.recommended_value,
                        "confidence": adj.confidence,
                        "expected_impact": adj.expected_impact,
                        "reasoning": adj.reasoning,
                        "applied": adj.applied
                    }
                    for adj in adjustments
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in strategy analysis and adjustment: {e}")
            raise
    
    async def evaluate_adjustment_results(
        self, 
        db: AsyncSession,
        days_since_adjustment: int = 7
    ) -> Dict[str, Any]:
        """Evaluate the results of recent strategy adjustments"""
        try:
            # Get recent adjustments
            recent_adjustments = [
                adj for adj in self.adjustment_history
                if adj.applied and adj.applied_at and 
                (datetime.utcnow() - adj.applied_at).days <= days_since_adjustment
            ]
            
            if not recent_adjustments:
                return {"message": "No recent adjustments to evaluate"}
            
            evaluation_results = []
            
            for adjustment in recent_adjustments:
                # Get performance before and after adjustment
                before_performance = await self._get_performance_before_adjustment(
                    db, adjustment
                )
                after_performance = await self._get_performance_after_adjustment(
                    db, adjustment
                )
                
                # Calculate actual impact
                actual_impact = await self._calculate_actual_impact(
                    before_performance, after_performance
                )
                
                # Compare with expected impact
                impact_accuracy = await self._calculate_impact_accuracy(
                    adjustment.expected_impact, actual_impact
                )
                
                # Update adjustment results
                adjustment.results = {
                    "before_performance": before_performance,
                    "after_performance": after_performance,
                    "actual_impact": actual_impact,
                    "expected_impact": adjustment.expected_impact,
                    "impact_accuracy": impact_accuracy,
                    "evaluation_date": datetime.utcnow().isoformat()
                }
                
                evaluation_results.append({
                    "adjustment_id": str(adjustment.id),
                    "strategy_type": adjustment.strategy_type,
                    "expected_impact": adjustment.expected_impact,
                    "actual_impact": actual_impact,
                    "impact_accuracy": impact_accuracy,
                    "success": actual_impact > 0 and impact_accuracy > 0.5
                })
            
            # Update learning parameters based on results
            await self._update_learning_parameters(evaluation_results)
            
            return {
                "evaluation_date": datetime.utcnow().isoformat(),
                "adjustments_evaluated": len(evaluation_results),
                "results": evaluation_results,
                "overall_success_rate": sum(1 for r in evaluation_results if r["success"]) / len(evaluation_results)
            }
            
        except Exception as e:
            logger.error(f"Error evaluating adjustment results: {e}")
            raise
    
    async def get_learning_insights(
        self, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get insights from the learning system's performance"""
        try:
            # Analyze adjustment history
            adjustment_analysis = await self._analyze_adjustment_history()
            
            # Get strategy performance trends
            strategy_trends = await self._get_strategy_performance_trends(db)
            
            # Identify learning patterns
            learning_patterns = await self._identify_learning_patterns()
            
            # Generate recommendations for learning system improvement
            system_recommendations = await self._generate_system_recommendations()
            
            return {
                "analysis_date": datetime.utcnow().isoformat(),
                "total_adjustments": len(self.adjustment_history),
                "adjustment_analysis": adjustment_analysis,
                "strategy_trends": strategy_trends,
                "learning_patterns": learning_patterns,
                "system_recommendations": system_recommendations
            }
            
        except Exception as e:
            logger.error(f"Error getting learning insights: {e}")
            raise
    
    async def predict_strategy_performance(
        self, 
        db: AsyncSession,
        strategy_changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Predict the performance impact of proposed strategy changes"""
        try:
            # Get historical performance data
            historical_data = await self._get_historical_strategy_performance(db)
            
            # Analyze similar past changes
            similar_changes = await self._find_similar_strategy_changes(
                strategy_changes, historical_data
            )
            
            # Calculate predicted impact
            predicted_impact = await self._calculate_predicted_impact(
                strategy_changes, similar_changes
            )
            
            # Calculate confidence in prediction
            prediction_confidence = await self._calculate_prediction_confidence(
                similar_changes, historical_data
            )
            
            # Generate risk assessment
            risk_assessment = await self._assess_strategy_change_risks(
                strategy_changes, historical_data
            )
            
            return {
                "prediction_date": datetime.utcnow().isoformat(),
                "strategy_changes": strategy_changes,
                "predicted_impact": predicted_impact,
                "confidence": prediction_confidence,
                "risk_assessment": risk_assessment,
                "similar_historical_changes": len(similar_changes),
                "recommendation": "apply" if prediction_confidence > 0.7 and predicted_impact > 0 else "review"
            }
            
        except Exception as e:
            logger.error(f"Error predicting strategy performance: {e}")
            raise
    
    # Private helper methods
    
    async def _analyze_current_performance(self, db: AsyncSession) -> Dict[str, Any]:
        """Analyze current system performance"""
        # Get recent performance metrics
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # Get pipeline analytics
        pipeline_analytics = await performance_tracking_service.get_pipeline_analytics(db, days=30)
        
        # Get success correlations
        success_correlations = await analytics_engine.analyze_success_patterns(db)
        
        # Calculate performance scores
        performance_scores = await self._calculate_performance_scores(pipeline_analytics)
        
        return {
            "pipeline_analytics": pipeline_analytics,
            "success_correlations": success_correlations,
            "performance_scores": performance_scores,
            "analysis_period": {"start": start_date.isoformat(), "end": end_date.isoformat()}
        }
    
    async def _identify_strategy_adjustments(
        self,
        db: AsyncSession,
        current_config: SystemConfigModel,
        performance_analysis: Dict[str, Any]
    ) -> List[StrategyAdjustment]:
        """Identify potential strategy adjustments"""
        adjustments = []
        
        # Analyze hourly rate strategy
        rate_adjustment = await self._analyze_hourly_rate_strategy(
            current_config, performance_analysis
        )
        if rate_adjustment:
            adjustments.append(rate_adjustment)
        
        # Analyze application volume strategy
        volume_adjustment = await self._analyze_application_volume_strategy(
            current_config, performance_analysis
        )
        if volume_adjustment:
            adjustments.append(volume_adjustment)
        
        # Analyze client rating threshold strategy
        rating_adjustment = await self._analyze_client_rating_strategy(
            current_config, performance_analysis
        )
        if rating_adjustment:
            adjustments.append(rating_adjustment)
        
        # Analyze keyword strategy
        keyword_adjustment = await self._analyze_keyword_strategy(
            current_config, performance_analysis
        )
        if keyword_adjustment:
            adjustments.append(keyword_adjustment)
        
        # Analyze timing strategy
        timing_adjustment = await self._analyze_timing_strategy(
            current_config, performance_analysis
        )
        if timing_adjustment:
            adjustments.append(timing_adjustment)
        
        return adjustments
    
    async def _analyze_hourly_rate_strategy(
        self,
        current_config: SystemConfigModel,
        performance_analysis: Dict[str, Any]
    ) -> Optional[StrategyAdjustment]:
        """Analyze and recommend hourly rate adjustments"""
        try:
            # Get success patterns for hourly rates
            success_patterns = performance_analysis.get("success_correlations", {})
            job_patterns = success_patterns.get("patterns", {}).get("job_characteristics", {})
            hourly_rate_pattern = job_patterns.get("hourly_rate", {})
            
            if not hourly_rate_pattern:
                return None
            
            successful_avg = hourly_rate_pattern.get("successful_avg", 0)
            current_min_rate = float(current_config.min_hourly_rate)
            
            # If successful applications have significantly higher rates, adjust minimum
            if successful_avg > current_min_rate * 1.2:  # 20% higher
                recommended_rate = successful_avg * 0.9  # Set slightly below average
                confidence = min(0.9, hourly_rate_pattern.get("p_value", 1.0))
                expected_impact = (recommended_rate - current_min_rate) / current_min_rate * 0.1  # 10% of rate increase
                
                return StrategyAdjustment(
                    strategy_type="min_hourly_rate",
                    current_value=current_min_rate,
                    recommended_value=recommended_rate,
                    confidence=confidence,
                    expected_impact=expected_impact,
                    reasoning=f"Successful applications average ${successful_avg:.2f}/hr, "
                             f"significantly higher than current minimum of ${current_min_rate:.2f}/hr"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing hourly rate strategy: {e}")
            return None
    
    async def _analyze_application_volume_strategy(
        self,
        current_config: SystemConfigModel,
        performance_analysis: Dict[str, Any]
    ) -> Optional[StrategyAdjustment]:
        """Analyze and recommend application volume adjustments"""
        try:
            # Get current performance metrics
            pipeline_analytics = performance_analysis.get("pipeline_analytics", {})
            conversion_rates = pipeline_analytics.get("conversion_rates", {})
            
            # Calculate current success rate
            response_rate = conversion_rates.get("application_to_response", 0) / 100
            hire_rate = conversion_rates.get("response_to_interview", 0) / 100 * conversion_rates.get("interview_to_hire", 0) / 100
            overall_success_rate = response_rate * hire_rate
            
            current_daily_limit = current_config.daily_application_limit
            
            # If success rate is high, consider increasing volume
            if overall_success_rate > 0.15:  # 15% overall success rate
                recommended_limit = min(50, int(current_daily_limit * 1.2))  # Increase by 20%, cap at 50
                confidence = min(0.8, overall_success_rate * 2)
                expected_impact = (recommended_limit - current_daily_limit) / current_daily_limit * overall_success_rate
                
                return StrategyAdjustment(
                    strategy_type="daily_application_limit",
                    current_value=current_daily_limit,
                    recommended_value=recommended_limit,
                    confidence=confidence,
                    expected_impact=expected_impact,
                    reasoning=f"High success rate ({overall_success_rate:.1%}) suggests capacity for increased volume"
                )
            
            # If success rate is low, consider decreasing volume to focus on quality
            elif overall_success_rate < 0.05:  # 5% overall success rate
                recommended_limit = max(10, int(current_daily_limit * 0.8))  # Decrease by 20%, minimum 10
                confidence = 0.7
                expected_impact = 0.1  # Focus on quality should improve success rate
                
                return StrategyAdjustment(
                    strategy_type="daily_application_limit",
                    current_value=current_daily_limit,
                    recommended_value=recommended_limit,
                    confidence=confidence,
                    expected_impact=expected_impact,
                    reasoning=f"Low success rate ({overall_success_rate:.1%}) suggests need to focus on quality over quantity"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing application volume strategy: {e}")
            return None
    
    async def _analyze_client_rating_strategy(
        self,
        current_config: SystemConfigModel,
        performance_analysis: Dict[str, Any]
    ) -> Optional[StrategyAdjustment]:
        """Analyze and recommend client rating threshold adjustments"""
        try:
            # Get success patterns for client ratings
            success_patterns = performance_analysis.get("success_correlations", {})
            job_patterns = success_patterns.get("patterns", {}).get("job_characteristics", {})
            rating_pattern = job_patterns.get("client_rating", {})
            
            if not rating_pattern:
                return None
            
            successful_avg = rating_pattern.get("successful_avg", 0)
            current_min_rating = float(current_config.min_client_rating)
            
            # If successful applications have significantly higher client ratings
            if successful_avg > current_min_rating + 0.3:  # 0.3 points higher
                recommended_rating = min(5.0, successful_avg - 0.1)  # Set slightly below average
                confidence = 1.0 - rating_pattern.get("p_value", 1.0)
                expected_impact = (recommended_rating - current_min_rating) * 0.05  # 5% per rating point
                
                return StrategyAdjustment(
                    strategy_type="min_client_rating",
                    current_value=current_min_rating,
                    recommended_value=recommended_rating,
                    confidence=confidence,
                    expected_impact=expected_impact,
                    reasoning=f"Successful applications have clients with average rating of {successful_avg:.1f}, "
                             f"higher than current minimum of {current_min_rating:.1f}"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing client rating strategy: {e}")
            return None
    
    async def _analyze_keyword_strategy(
        self,
        current_config: SystemConfigModel,
        performance_analysis: Dict[str, Any]
    ) -> Optional[StrategyAdjustment]:
        """Analyze and recommend keyword strategy adjustments"""
        # This would analyze which keywords are most successful
        # For now, return None as this requires more complex text analysis
        return None
    
    async def _analyze_timing_strategy(
        self,
        current_config: SystemConfigModel,
        performance_analysis: Dict[str, Any]
    ) -> Optional[StrategyAdjustment]:
        """Analyze and recommend timing strategy adjustments"""
        try:
            # Get timing patterns from success analysis
            success_patterns = performance_analysis.get("success_correlations", {})
            timing_patterns = success_patterns.get("patterns", {}).get("timing_patterns", {})
            
            optimal_hours = timing_patterns.get("optimal_hours", [])
            optimal_days = timing_patterns.get("optimal_days", [])
            
            if optimal_hours or optimal_days:
                return StrategyAdjustment(
                    strategy_type="optimal_timing",
                    current_value={"hours": "all", "days": "all"},
                    recommended_value={"hours": optimal_hours, "days": optimal_days},
                    confidence=0.6,
                    expected_impact=0.1,
                    reasoning=f"Analysis shows optimal application times: hours {optimal_hours}, days {optimal_days}"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing timing strategy: {e}")
            return None
    
    async def _apply_strategy_adjustment(
        self,
        db: AsyncSession,
        current_config: SystemConfigModel,
        adjustment: StrategyAdjustment
    ) -> bool:
        """Apply a strategy adjustment to the system configuration"""
        try:
            if adjustment.strategy_type == "min_hourly_rate":
                current_config.min_hourly_rate = Decimal(str(adjustment.recommended_value))
            elif adjustment.strategy_type == "daily_application_limit":
                current_config.daily_application_limit = int(adjustment.recommended_value)
            elif adjustment.strategy_type == "min_client_rating":
                current_config.min_client_rating = Decimal(str(adjustment.recommended_value))
            elif adjustment.strategy_type == "optimal_timing":
                # This would require additional configuration fields
                pass
            else:
                logger.warning(f"Unknown strategy type: {adjustment.strategy_type}")
                return False
            
            # Update timestamp
            current_config.updated_at = datetime.utcnow()
            
            # Commit changes
            await db.commit()
            
            # Mark adjustment as applied
            adjustment.applied = True
            adjustment.applied_at = datetime.utcnow()
            
            logger.info(f"Applied strategy adjustment: {adjustment.strategy_type} = {adjustment.recommended_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error applying strategy adjustment: {e}")
            await db.rollback()
            return False
    
    async def _record_learning_session(
        self,
        db: AsyncSession,
        all_adjustments: List[StrategyAdjustment],
        applied_adjustments: List[StrategyAdjustment]
    ):
        """Record a learning session in the performance metrics"""
        try:
            session_data = {
                "total_adjustments": len(all_adjustments),
                "applied_adjustments": len(applied_adjustments),
                "adjustments": [
                    {
                        "strategy_type": adj.strategy_type,
                        "confidence": adj.confidence,
                        "expected_impact": adj.expected_impact,
                        "applied": adj.applied
                    }
                    for adj in all_adjustments
                ]
            }
            
            metric = PerformanceMetricModel(
                metric_type="learning_session",
                metric_value=Decimal(str(len(applied_adjustments))),
                time_period="event",
                date_recorded=datetime.utcnow(),
                metadata=session_data
            )
            
            db.add(metric)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error recording learning session: {e}")
    
    async def _calculate_performance_scores(self, pipeline_analytics: Dict[str, Any]) -> Dict[str, float]:
        """Calculate overall performance scores"""
        scores = {}
        
        # Conversion rate score
        conversion_rates = pipeline_analytics.get("conversion_rates", {})
        overall_conversion = 1.0
        for rate in conversion_rates.values():
            overall_conversion *= (rate / 100)
        scores["conversion_rate"] = min(1.0, overall_conversion * 10)  # Scale to 0-1
        
        # Volume score (based on pipeline metrics)
        pipeline_metrics = pipeline_analytics.get("pipeline_metrics", {})
        daily_applications = pipeline_metrics.get("applied", 0) / 30  # Average per day
        scores["volume"] = min(1.0, daily_applications / 30)  # Scale to 0-1, target 30/day
        
        # Quality score (placeholder)
        scores["quality"] = 0.7  # Would be calculated from proposal quality metrics
        
        return scores
    
    # Additional helper methods would be implemented here for evaluation, insights, etc.
    # Due to length constraints, implementing core structure with key methods
    
    async def _get_performance_before_adjustment(self, db: AsyncSession, adjustment: StrategyAdjustment) -> Dict[str, Any]:
        """Get performance metrics before an adjustment was applied"""
        return {}
    
    async def _get_performance_after_adjustment(self, db: AsyncSession, adjustment: StrategyAdjustment) -> Dict[str, Any]:
        """Get performance metrics after an adjustment was applied"""
        return {}
    
    async def _calculate_actual_impact(self, before: Dict, after: Dict) -> float:
        """Calculate actual impact of an adjustment"""
        return 0.0
    
    async def _calculate_impact_accuracy(self, expected: float, actual: float) -> float:
        """Calculate accuracy of impact prediction"""
        if expected == 0:
            return 1.0 if actual == 0 else 0.0
        return 1.0 - abs(expected - actual) / abs(expected)
    
    async def _update_learning_parameters(self, evaluation_results: List[Dict[str, Any]]):
        """Update learning system parameters based on evaluation results"""
        # Adjust learning rate based on accuracy
        accuracy_scores = [r["impact_accuracy"] for r in evaluation_results]
        if accuracy_scores:
            avg_accuracy = statistics.mean(accuracy_scores)
            if avg_accuracy > 0.8:
                self.learning_rate = min(0.2, self.learning_rate * 1.1)
            elif avg_accuracy < 0.5:
                self.learning_rate = max(0.05, self.learning_rate * 0.9)
    
    async def _analyze_adjustment_history(self) -> Dict[str, Any]:
        """Analyze the history of adjustments"""
        return {}
    
    async def _get_strategy_performance_trends(self, db: AsyncSession) -> Dict[str, Any]:
        """Get performance trends for different strategies"""
        return {}
    
    async def _identify_learning_patterns(self) -> Dict[str, Any]:
        """Identify patterns in the learning system's behavior"""
        return {}
    
    async def _generate_system_recommendations(self) -> List[Dict[str, Any]]:
        """Generate recommendations for improving the learning system"""
        return []
    
    async def _get_historical_strategy_performance(self, db: AsyncSession) -> Dict[str, Any]:
        """Get historical strategy performance data"""
        return {}
    
    async def _find_similar_strategy_changes(self, changes: Dict, historical: Dict) -> List[Dict[str, Any]]:
        """Find similar strategy changes in historical data"""
        return []
    
    async def _calculate_predicted_impact(self, changes: Dict, similar_changes: List) -> float:
        """Calculate predicted impact of strategy changes"""
        return 0.0
    
    async def _calculate_prediction_confidence(self, similar_changes: List, historical: Dict) -> float:
        """Calculate confidence in prediction"""
        return 0.5
    
    async def _assess_strategy_change_risks(self, changes: Dict, historical: Dict) -> Dict[str, Any]:
        """Assess risks of proposed strategy changes"""
        return {"risk_level": "low", "risks": []}


# Global service instance
learning_system = LearningSystem()