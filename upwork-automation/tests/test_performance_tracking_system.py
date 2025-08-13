"""
Tests for Performance Tracking and Learning System
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))

from services.performance_tracking_service import performance_tracking_service
from services.analytics_engine import analytics_engine
from services.learning_system import learning_system, StrategyAdjustment
from services.recommendation_system import recommendation_system, Recommendation
from services.alerting_system import alerting_system, Alert, AlertSeverity, AlertType
from database.models import (
    JobModel, ApplicationModel, ProposalModel, 
    PerformanceMetricModel, SystemConfigModel
)
from shared.models import JobStatus, ApplicationStatus, ProposalStatus


class TestPerformanceTrackingService:
    """Test performance tracking service functionality"""
    
    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session"""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def sample_application_id(self):
        """Sample application ID"""
        return uuid4()
    
    @pytest.fixture
    def sample_applications(self):
        """Sample application models for testing"""
        job = JobModel(
            id=uuid4(),
            title="Salesforce Agentforce Developer",
            description="Build AI agents",
            hourly_rate=Decimal("75.00"),
            client_rating=Decimal("4.8"),
            client_payment_verified=True,
            job_type="hourly",
            status=JobStatus.APPLIED
        )
        
        proposal = ProposalModel(
            id=uuid4(),
            job_id=job.id,
            content="Excellent proposal content",
            bid_amount=Decimal("70.00"),
            status=ProposalStatus.SUBMITTED
        )
        
        application = ApplicationModel(
            id=uuid4(),
            job_id=job.id,
            proposal_id=proposal.id,
            status=ApplicationStatus.HIRED,
            submitted_at=datetime.utcnow() - timedelta(days=5),
            hire_date=datetime.utcnow()
        )
        
        application.job = job
        application.proposal = proposal
        
        return [application]
    
    async def test_track_application_pipeline(self, mock_db_session, sample_application_id):
        """Test application pipeline tracking"""
        # Test tracking a pipeline stage
        await performance_tracking_service.track_application_pipeline(
            mock_db_session,
            sample_application_id,
            "submitted",
            {"test_metadata": "value"}
        )
        
        # Verify database operations were called
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
    
    async def test_get_pipeline_analytics(self, mock_db_session):
        """Test pipeline analytics retrieval"""
        # Mock database query results
        mock_db_session.execute.return_value.scalar.return_value = 10
        
        analytics = await performance_tracking_service.get_pipeline_analytics(mock_db_session, days=30)
        
        assert "period" in analytics
        assert "pipeline_metrics" in analytics
        assert "conversion_rates" in analytics
        assert analytics["period"]["days"] == 30
    
    async def test_get_success_correlations(self, mock_db_session, sample_applications):
        """Test success correlation analysis"""
        # Mock successful applications query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_applications
        mock_db_session.execute.return_value = mock_result
        
        correlations = await performance_tracking_service.get_success_correlations(
            mock_db_session, min_applications=1
        )
        
        assert "analysis_period" in correlations
        assert "sample_size" in correlations
        assert "correlations" in correlations
        assert correlations["sample_size"] == 1
    
    async def test_get_performance_insights(self, mock_db_session):
        """Test performance insights generation"""
        insights = await performance_tracking_service.get_performance_insights(
            mock_db_session, days=30
        )
        
        assert "analysis_date" in insights
        assert "period_days" in insights
        assert "current_metrics" in insights
        assert "recommendations" in insights
    
    async def test_track_strategy_performance(self, mock_db_session):
        """Test strategy performance tracking"""
        strategy_params = {"min_hourly_rate": 60.0, "daily_limit": 25}
        performance_metrics = {"success_rate": 0.15, "response_rate": 0.25}
        
        await performance_tracking_service.track_strategy_performance(
            mock_db_session,
            "optimized_targeting",
            strategy_params,
            performance_metrics
        )
        
        # Verify tracking was recorded
        assert mock_db_session.add.called or mock_db_session.commit.called


class TestAnalyticsEngine:
    """Test analytics engine functionality"""
    
    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session"""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def sample_successful_apps(self):
        """Sample successful applications"""
        apps = []
        for i in range(25):  # Sufficient sample size
            job = JobModel(
                hourly_rate=Decimal(str(60 + i * 2)),
                client_rating=Decimal("4.5"),
                client_payment_verified=True,
                job_type="hourly"
            )
            
            proposal = ProposalModel(
                bid_amount=Decimal(str(55 + i * 2)),
                content="A" * (200 + i * 10)  # Varying lengths
            )
            
            app = ApplicationModel(
                status=ApplicationStatus.HIRED,
                submitted_at=datetime.utcnow() - timedelta(days=i)
            )
            
            app.job = job
            app.proposal = proposal
            apps.append(app)
        
        return apps
    
    async def test_analyze_success_patterns(self, mock_db_session, sample_successful_apps):
        """Test success pattern analysis"""
        # Mock database queries
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_successful_apps
        mock_db_session.execute.return_value = mock_result
        
        patterns = await analytics_engine.analyze_success_patterns(mock_db_session, min_sample_size=20)
        
        assert "analysis_date" in patterns
        assert "sample_sizes" in patterns
        assert "patterns" in patterns
        assert patterns["sample_sizes"]["successful"] == 25
        
        # Check pattern categories
        assert "job_characteristics" in patterns["patterns"]
        assert "proposal_characteristics" in patterns["patterns"]
        assert "timing_patterns" in patterns["patterns"]
    
    async def test_identify_optimization_opportunities(self, mock_db_session):
        """Test optimization opportunity identification"""
        current_performance = {
            "response_rate": 12.0,
            "hire_rate": 8.0,
            "application_volume": 20
        }
        
        opportunities = await analytics_engine.identify_optimization_opportunities(
            mock_db_session, current_performance
        )
        
        assert isinstance(opportunities, list)
        # Would contain specific optimization recommendations
    
    async def test_calculate_predictive_scores(self, mock_db_session):
        """Test predictive score calculation"""
        job_data = {
            "hourly_rate": 75.0,
            "client_rating": 4.8,
            "client_payment_verified": True,
            "job_type": "hourly"
        }
        
        proposal_data = {
            "bid_amount": 70.0,
            "content_length": 250,
            "quality_score": 0.85
        }
        
        # Mock success patterns
        with patch.object(analytics_engine, 'analyze_success_patterns') as mock_patterns:
            mock_patterns.return_value = {
                "patterns": {
                    "job_characteristics": {
                        "hourly_rate": {"successful_avg": 72.0}
                    }
                }
            }
            
            scores = await analytics_engine.calculate_predictive_scores(
                mock_db_session, job_data, proposal_data
            )
            
            assert "success_probability" in scores
            assert "confidence" in scores
            assert "component_scores" in scores
            assert 0 <= scores["success_probability"] <= 1
            assert 0 <= scores["confidence"] <= 1
    
    async def test_analyze_performance_trends(self, mock_db_session):
        """Test performance trend analysis"""
        trends = await analytics_engine.analyze_performance_trends(mock_db_session, days=90)
        
        assert "analysis_period" in trends
        assert "trends" in trends
        assert trends["analysis_period"]["days"] == 90
    
    async def test_generate_actionable_insights(self, mock_db_session):
        """Test actionable insight generation"""
        analysis_results = {
            "patterns": {
                "job_characteristics": {
                    "hourly_rate": {"successful_avg": 75.0, "statistical_significance": True}
                }
            },
            "trends": {
                "response_rate": {"trend": "decreasing", "significant": True}
            }
        }
        
        insights = await analytics_engine.generate_actionable_insights(
            mock_db_session, analysis_results
        )
        
        assert isinstance(insights, list)
        # Each insight should have required fields
        for insight in insights:
            assert "category" in insight
            assert "title" in insight
            assert "description" in insight


class TestLearningSystem:
    """Test learning system functionality"""
    
    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session"""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def mock_system_config(self):
        """Mock system configuration"""
        config = SystemConfigModel(
            daily_application_limit=30,
            min_hourly_rate=Decimal("50.0"),
            min_client_rating=Decimal("4.0")
        )
        return config
    
    async def test_analyze_and_adjust_strategies(self, mock_db_session, mock_system_config):
        """Test strategy analysis and adjustment"""
        # Mock system config retrieval
        with patch.object(SystemConfigModel, 'get_config', return_value=mock_system_config):
            # Mock performance analysis
            with patch.object(learning_system, '_analyze_current_performance') as mock_analysis:
                mock_analysis.return_value = {
                    "success_correlations": {
                        "patterns": {
                            "job_characteristics": {
                                "hourly_rate": {
                                    "successful_avg": 65.0,
                                    "p_value": 0.02
                                }
                            }
                        }
                    }
                }
                
                result = await learning_system.analyze_and_adjust_strategies(mock_db_session)
                
                assert "analysis_date" in result
                assert "total_adjustments_identified" in result
                assert "applied_adjustments" in result
                assert "adjustments" in result
    
    async def test_strategy_adjustment_creation(self):
        """Test strategy adjustment object creation"""
        adjustment = StrategyAdjustment(
            strategy_type="min_hourly_rate",
            current_value=50.0,
            recommended_value=60.0,
            confidence=0.8,
            expected_impact=0.15,
            reasoning="Successful applications average higher rates"
        )
        
        assert adjustment.strategy_type == "min_hourly_rate"
        assert adjustment.current_value == 50.0
        assert adjustment.recommended_value == 60.0
        assert adjustment.confidence == 0.8
        assert not adjustment.applied
        assert adjustment.created_at is not None
    
    async def test_evaluate_adjustment_results(self, mock_db_session):
        """Test adjustment result evaluation"""
        # Create a test adjustment
        adjustment = StrategyAdjustment(
            strategy_type="min_hourly_rate",
            current_value=50.0,
            recommended_value=60.0,
            confidence=0.8,
            expected_impact=0.15,
            reasoning="Test adjustment"
        )
        adjustment.applied = True
        adjustment.applied_at = datetime.utcnow() - timedelta(days=5)
        
        learning_system.adjustment_history = [adjustment]
        
        evaluation = await learning_system.evaluate_adjustment_results(mock_db_session, days_since_adjustment=7)
        
        assert "evaluation_date" in evaluation
        assert "adjustments_evaluated" in evaluation
        assert "overall_success_rate" in evaluation
    
    async def test_predict_strategy_performance(self, mock_db_session):
        """Test strategy performance prediction"""
        strategy_changes = {
            "min_hourly_rate": 65.0,
            "daily_application_limit": 25
        }
        
        prediction = await learning_system.predict_strategy_performance(
            mock_db_session, strategy_changes
        )
        
        assert "prediction_date" in prediction
        assert "strategy_changes" in prediction
        assert "predicted_impact" in prediction
        assert "confidence" in prediction
        assert "recommendation" in prediction


class TestRecommendationSystem:
    """Test recommendation system functionality"""
    
    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session"""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    async def test_generate_comprehensive_recommendations(self, mock_db_session):
        """Test comprehensive recommendation generation"""
        # Mock performance data gathering
        with patch.object(recommendation_system, '_gather_performance_data') as mock_gather:
            mock_gather.return_value = {
                "success_patterns": {
                    "patterns": {
                        "job_characteristics": {
                            "hourly_rate": {
                                "successful_avg": 75.0,
                                "statistical_significance": True
                            }
                        }
                    }
                },
                "current_config": {
                    "min_hourly_rate": 50.0
                }
            }
            
            recommendations = await recommendation_system.generate_comprehensive_recommendations(
                mock_db_session, analysis_days=60
            )
            
            assert "analysis_date" in recommendations
            assert "total_recommendations" in recommendations
            assert "recommendations" in recommendations
            assert "summary" in recommendations
            
            # Check recommendation categories
            rec_data = recommendations["recommendations"]
            assert "high_priority" in rec_data
            assert "medium_priority" in rec_data
            assert "low_priority" in rec_data
    
    async def test_recommendation_creation(self):
        """Test recommendation object creation"""
        recommendation = Recommendation(
            category="profile",
            title="Optimize Hourly Rate",
            description="Increase minimum hourly rate based on successful applications",
            priority="high",
            impact_score=0.8,
            effort_score=0.2,
            confidence=0.9,
            actionable_steps=[
                "Increase minimum rate to $65/hr",
                "Update profile positioning"
            ]
        )
        
        assert recommendation.category == "profile"
        assert recommendation.priority == "high"
        assert recommendation.priority_score > 0  # Should be calculated
        assert len(recommendation.actionable_steps) == 2
    
    async def test_get_personalized_recommendations(self, mock_db_session):
        """Test personalized recommendation retrieval"""
        # Mock comprehensive recommendations
        with patch.object(recommendation_system, 'generate_comprehensive_recommendations') as mock_gen:
            mock_gen.return_value = {
                "recommendations": {
                    "high_priority": [
                        {
                            "category": "profile",
                            "title": "Test Recommendation",
                            "priority_score": 0.8
                        }
                    ],
                    "medium_priority": [],
                    "low_priority": []
                }
            }
            
            personalized = await recommendation_system.get_personalized_recommendations(
                mock_db_session,
                focus_areas=["profile"],
                max_recommendations=5
            )
            
            assert isinstance(personalized, list)
            assert len(personalized) <= 5
            if personalized:
                assert personalized[0]["category"] == "profile"
    
    async def test_track_recommendation_implementation(self, mock_db_session):
        """Test recommendation implementation tracking"""
        result = await recommendation_system.track_recommendation_implementation(
            mock_db_session,
            "test-recommendation-id",
            "implemented",
            "Successfully implemented rate increase"
        )
        
        assert result["status"] == "tracked"
        assert result["recommendation_id"] == "test-recommendation-id"
        assert result["implementation_status"] == "implemented"
        assert mock_db_session.add.called
        assert mock_db_session.commit.called


class TestAlertingSystem:
    """Test alerting system functionality"""
    
    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session"""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    async def test_monitor_performance(self, mock_db_session):
        """Test performance monitoring"""
        # Mock performance metrics
        with patch.object(alerting_system, '_get_current_performance_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "response_rate": 8.0,  # Below threshold
                "hire_rate": 3.0,      # Below threshold
                "application_volume": 15
            }
            
            monitoring_result = await alerting_system.monitor_performance(mock_db_session)
            
            assert "monitoring_date" in monitoring_result
            assert "new_alerts" in monitoring_result
            assert "active_alerts" in monitoring_result
            assert "alerts_by_type" in monitoring_result
    
    async def test_alert_creation(self):
        """Test alert object creation"""
        alert = Alert(
            alert_type=AlertType.PERFORMANCE_DECLINE,
            severity=AlertSeverity.HIGH,
            title="Response Rate Decline",
            description="Response rate has declined by 30%",
            metric_name="response_rate",
            current_value=8.0,
            threshold_value=12.0,
            corrective_actions=["Review proposal quality", "Adjust targeting"]
        )
        
        assert alert.alert_type == AlertType.PERFORMANCE_DECLINE
        assert alert.severity == AlertSeverity.HIGH
        assert alert.current_value == 8.0
        assert len(alert.corrective_actions) == 2
        assert not alert.acknowledged
        assert not alert.resolved
    
    async def test_acknowledge_alert(self):
        """Test alert acknowledgment"""
        alert = Alert(
            alert_type=AlertType.THRESHOLD_BREACH,
            severity=AlertSeverity.MEDIUM,
            title="Test Alert",
            description="Test description",
            metric_name="test_metric",
            current_value=5.0,
            threshold_value=10.0
        )
        
        alerting_system.active_alerts[str(alert.id)] = alert
        
        result = await alerting_system.acknowledge_alert(str(alert.id), "test_user")
        
        assert result["status"] == "acknowledged"
        assert alert.acknowledged
        assert alert.acknowledged_at is not None
    
    async def test_resolve_alert(self):
        """Test alert resolution"""
        alert = Alert(
            alert_type=AlertType.THRESHOLD_BREACH,
            severity=AlertSeverity.MEDIUM,
            title="Test Alert",
            description="Test description",
            metric_name="test_metric",
            current_value=5.0,
            threshold_value=10.0
        )
        
        alerting_system.active_alerts[str(alert.id)] = alert
        
        result = await alerting_system.resolve_alert(str(alert.id), "Issue resolved")
        
        assert result["status"] == "resolved"
        assert alert.resolved
        assert alert.resolved_at is not None
        assert str(alert.id) not in alerting_system.active_alerts
        assert alert in alerting_system.alert_history
    
    async def test_update_alert_thresholds(self):
        """Test alert threshold updates"""
        new_thresholds = {
            "response_rate": {
                "critical": 3.0,
                "high": 8.0,
                "medium": 12.0,
                "low": 18.0
            }
        }
        
        result = await alerting_system.update_alert_thresholds(new_thresholds)
        
        assert result["status"] == "updated"
        assert "response_rate" in result["updated_metrics"]
        assert alerting_system.thresholds["response_rate"]["critical"] == 3.0
    
    async def test_generate_corrective_action_plan(self, mock_db_session):
        """Test corrective action plan generation"""
        alert = Alert(
            alert_type=AlertType.PERFORMANCE_DECLINE,
            severity=AlertSeverity.HIGH,
            title="Performance Issue",
            description="Performance has declined",
            metric_name="response_rate",
            current_value=5.0,
            threshold_value=10.0,
            corrective_actions=["Action 1", "Action 2", "Action 3", "Action 4"]
        )
        
        alerting_system.active_alerts[str(alert.id)] = alert
        
        action_plan = await alerting_system.generate_corrective_action_plan(
            mock_db_session, str(alert.id)
        )
        
        assert "alert_id" in action_plan
        assert "action_plan" in action_plan
        assert "immediate_actions" in action_plan["action_plan"]
        assert "short_term_actions" in action_plan["action_plan"]
        assert "monitoring_plan" in action_plan["action_plan"]


# Integration tests
class TestPerformanceSystemIntegration:
    """Test integration between performance tracking components"""
    
    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session"""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    async def test_end_to_end_performance_analysis(self, mock_db_session):
        """Test end-to-end performance analysis workflow"""
        # 1. Track application pipeline
        application_id = uuid4()
        await performance_tracking_service.track_application_pipeline(
            mock_db_session, application_id, "submitted"
        )
        
        # 2. Analyze patterns (mocked)
        with patch.object(analytics_engine, 'analyze_success_patterns') as mock_patterns:
            mock_patterns.return_value = {
                "patterns": {
                    "job_characteristics": {
                        "hourly_rate": {"successful_avg": 70.0}
                    }
                }
            }
            
            patterns = await analytics_engine.analyze_success_patterns(mock_db_session)
            assert "patterns" in patterns
        
        # 3. Generate recommendations
        with patch.object(recommendation_system, '_gather_performance_data') as mock_gather:
            mock_gather.return_value = {"success_patterns": patterns}
            
            recommendations = await recommendation_system.generate_comprehensive_recommendations(
                mock_db_session
            )
            assert "recommendations" in recommendations
        
        # 4. Monitor for alerts
        with patch.object(alerting_system, '_get_current_performance_metrics') as mock_metrics:
            mock_metrics.return_value = {"response_rate": 5.0}  # Low rate
            
            monitoring = await alerting_system.monitor_performance(mock_db_session)
            assert "new_alerts" in monitoring
    
    async def test_learning_system_feedback_loop(self, mock_db_session):
        """Test learning system feedback loop"""
        # Mock system configuration
        mock_config = SystemConfigModel(
            min_hourly_rate=Decimal("50.0"),
            daily_application_limit=30
        )
        
        with patch.object(SystemConfigModel, 'get_config', return_value=mock_config):
            # 1. Analyze and adjust strategies
            with patch.object(learning_system, '_analyze_current_performance') as mock_analysis:
                mock_analysis.return_value = {
                    "success_correlations": {
                        "patterns": {
                            "job_characteristics": {
                                "hourly_rate": {"successful_avg": 65.0, "p_value": 0.01}
                            }
                        }
                    }
                }
                
                adjustment_result = await learning_system.analyze_and_adjust_strategies(mock_db_session)
                assert "adjustments" in adjustment_result
            
            # 2. Evaluate results (after some time)
            evaluation = await learning_system.evaluate_adjustment_results(mock_db_session)
            assert "evaluation_date" in evaluation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])