#!/usr/bin/env python3
"""
Simple test runner for performance tracking system
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

# Add API directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

from services.performance_tracking_service import performance_tracking_service
from services.analytics_engine import analytics_engine
from services.learning_system import learning_system, StrategyAdjustment
from services.recommendation_system import recommendation_system, Recommendation
from services.alerting_system import alerting_system, Alert, AlertSeverity, AlertType


class MockDBSession:
    """Mock database session for testing"""
    
    def __init__(self):
        self.added_objects = []
        self.committed = False
    
    def add(self, obj):
        self.added_objects.append(obj)
    
    async def commit(self):
        self.committed = True
    
    async def rollback(self):
        pass
    
    async def execute(self, query):
        # Mock query result
        class MockResult:
            def scalar(self):
                return 10
            
            def scalar_one_or_none(self):
                return None
            
            def scalars(self):
                class MockScalars:
                    def all(self):
                        return []
                return MockScalars()
            
            def fetchall(self):
                return []
        
        return MockResult()


async def test_performance_tracking():
    """Test performance tracking service"""
    print("Testing Performance Tracking Service...")
    
    mock_db = MockDBSession()
    application_id = uuid4()
    
    try:
        # Test pipeline tracking
        await performance_tracking_service.track_application_pipeline(
            mock_db, application_id, "submitted", {"test": "data"}
        )
        
        print("✓ Pipeline tracking works")
        
        # Test analytics retrieval
        analytics = await performance_tracking_service.get_pipeline_analytics(mock_db, days=30)
        print("✓ Pipeline analytics works")
        
        # Test insights generation
        insights = await performance_tracking_service.get_performance_insights(mock_db, days=30)
        print("✓ Performance insights works")
        
    except Exception as e:
        print(f"✗ Performance tracking failed: {e}")
        return False
    
    return True


async def test_analytics_engine():
    """Test analytics engine"""
    print("\nTesting Analytics Engine...")
    
    mock_db = MockDBSession()
    
    try:
        # Test success pattern analysis
        patterns = await analytics_engine.analyze_success_patterns(mock_db, min_sample_size=5)
        print("✓ Success pattern analysis works")
        
        # Test optimization opportunities
        current_performance = {"response_rate": 10.0, "hire_rate": 5.0}
        opportunities = await analytics_engine.identify_optimization_opportunities(
            mock_db, current_performance
        )
        print("✓ Optimization opportunities works")
        
        # Test predictive scoring
        job_data = {"hourly_rate": 75.0, "client_rating": 4.8}
        proposal_data = {"bid_amount": 70.0, "content_length": 250}
        
        scores = await analytics_engine.calculate_predictive_scores(
            mock_db, job_data, proposal_data
        )
        print("✓ Predictive scoring works")
        
    except Exception as e:
        print(f"✗ Analytics engine failed: {e}")
        return False
    
    return True


async def test_learning_system():
    """Test learning system"""
    print("\nTesting Learning System...")
    
    mock_db = MockDBSession()
    
    try:
        # Test strategy adjustment creation
        adjustment = StrategyAdjustment(
            strategy_type="min_hourly_rate",
            current_value=50.0,
            recommended_value=60.0,
            confidence=0.8,
            expected_impact=0.15,
            reasoning="Test adjustment"
        )
        
        print("✓ Strategy adjustment creation works")
        
        # Test learning insights
        insights = await learning_system.get_learning_insights(mock_db)
        print("✓ Learning insights works")
        
        # Test strategy prediction
        strategy_changes = {"min_hourly_rate": 65.0}
        prediction = await learning_system.predict_strategy_performance(
            mock_db, strategy_changes
        )
        print("✓ Strategy prediction works")
        
    except Exception as e:
        print(f"✗ Learning system failed: {e}")
        return False
    
    return True


async def test_recommendation_system():
    """Test recommendation system"""
    print("\nTesting Recommendation System...")
    
    mock_db = MockDBSession()
    
    try:
        # Test recommendation creation
        recommendation = Recommendation(
            category="profile",
            title="Test Recommendation",
            description="Test description",
            priority="high",
            impact_score=0.8,
            effort_score=0.2,
            confidence=0.9,
            actionable_steps=["Step 1", "Step 2"]
        )
        
        print("✓ Recommendation creation works")
        
        # Test personalized recommendations
        personalized = await recommendation_system.get_personalized_recommendations(
            mock_db, focus_areas=["profile"], max_recommendations=5
        )
        print("✓ Personalized recommendations works")
        
        # Test implementation tracking
        result = await recommendation_system.track_recommendation_implementation(
            mock_db, "test-id", "implemented", "Test notes"
        )
        print("✓ Implementation tracking works")
        
    except Exception as e:
        print(f"✗ Recommendation system failed: {e}")
        return False
    
    return True


async def test_alerting_system():
    """Test alerting system"""
    print("\nTesting Alerting System...")
    
    mock_db = MockDBSession()
    
    try:
        # Test alert creation
        alert = Alert(
            alert_type=AlertType.PERFORMANCE_DECLINE,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            description="Test description",
            metric_name="response_rate",
            current_value=8.0,
            threshold_value=12.0,
            corrective_actions=["Action 1", "Action 2"]
        )
        
        print("✓ Alert creation works")
        
        # Test alert acknowledgment
        alerting_system.active_alerts[str(alert.id)] = alert
        result = await alerting_system.acknowledge_alert(str(alert.id), "test_user")
        print("✓ Alert acknowledgment works")
        
        # Test alert resolution
        result = await alerting_system.resolve_alert(str(alert.id), "Test resolution")
        print("✓ Alert resolution works")
        
        # Test threshold updates
        new_thresholds = {
            "response_rate": {
                "critical": 3.0,
                "high": 8.0,
                "medium": 12.0,
                "low": 18.0
            }
        }
        result = await alerting_system.update_alert_thresholds(new_thresholds)
        print("✓ Threshold updates work")
        
    except Exception as e:
        print(f"✗ Alerting system failed: {e}")
        return False
    
    return True


async def main():
    """Run all tests"""
    print("Performance Tracking and Learning System Tests")
    print("=" * 50)
    
    tests = [
        test_performance_tracking,
        test_analytics_engine,
        test_learning_system,
        test_recommendation_system,
        test_alerting_system
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)