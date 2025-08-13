"""
Alerting System - Performance decline detection and corrective action alerts
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4
import json
import statistics
from enum import Enum

from sqlalchemy import select, func, and_, desc, asc, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    JobModel, ApplicationModel, ProposalModel, 
    PerformanceMetricModel, SystemConfigModel
)
from shared.utils import setup_logging
from .notification_service import notification_service
from .performance_tracking_service import performance_tracking_service

logger = setup_logging("alerting-system")


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    PERFORMANCE_DECLINE = "performance_decline"
    CONVERSION_DROP = "conversion_drop"
    VOLUME_ANOMALY = "volume_anomaly"
    QUALITY_DEGRADATION = "quality_degradation"
    SYSTEM_ERROR = "system_error"
    THRESHOLD_BREACH = "threshold_breach"
    TREND_REVERSAL = "trend_reversal"


class Alert:
    """Represents a performance alert"""
    
    def __init__(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        description: str,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        trend_data: Dict[str, Any] = None,
        corrective_actions: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        self.id = uuid4()
        self.alert_type = alert_type
        self.severity = severity
        self.title = title
        self.description = description
        self.metric_name = metric_name
        self.current_value = current_value
        self.threshold_value = threshold_value
        self.trend_data = trend_data or {}
        self.corrective_actions = corrective_actions or []
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.acknowledged = False
        self.acknowledged_at = None
        self.resolved = False
        self.resolved_at = None


class AlertingSystem:
    """System for monitoring performance and generating alerts"""
    
    def __init__(self):
        self.active_alerts = {}
        self.alert_history = []
        self.thresholds = self._initialize_default_thresholds()
        self.monitoring_enabled = True
    
    def _initialize_default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Initialize default alert thresholds"""
        return {
            "response_rate": {
                "critical": 5.0,    # Below 5% response rate
                "high": 10.0,       # Below 10% response rate
                "medium": 15.0,     # Below 15% response rate
                "low": 20.0         # Below 20% response rate
            },
            "hire_rate": {
                "critical": 2.0,    # Below 2% hire rate
                "high": 5.0,        # Below 5% hire rate
                "medium": 8.0,      # Below 8% hire rate
                "low": 12.0         # Below 12% hire rate
            },
            "application_volume": {
                "critical": 5,      # Less than 5 applications per day
                "high": 10,         # Less than 10 applications per day
                "medium": 15,       # Less than 15 applications per day
                "low": 20           # Less than 20 applications per day
            },
            "success_rate": {
                "critical": 3.0,    # Below 3% overall success rate
                "high": 6.0,        # Below 6% overall success rate
                "medium": 10.0,     # Below 10% overall success rate
                "low": 15.0         # Below 15% overall success rate
            },
            "proposal_quality": {
                "critical": 0.3,    # Below 30% quality score
                "high": 0.5,        # Below 50% quality score
                "medium": 0.7,      # Below 70% quality score
                "low": 0.8          # Below 80% quality score
            }
        }
    
    async def monitor_performance(self, db: AsyncSession) -> Dict[str, Any]:
        """Monitor system performance and generate alerts"""
        try:
            if not self.monitoring_enabled:
                return {"status": "monitoring_disabled"}
            
            logger.info("Starting performance monitoring cycle")
            
            # Get current performance metrics
            current_metrics = await self._get_current_performance_metrics(db)
            
            # Check for performance declines
            decline_alerts = await self._check_performance_declines(db, current_metrics)
            
            # Check for threshold breaches
            threshold_alerts = await self._check_threshold_breaches(current_metrics)
            
            # Check for trend reversals
            trend_alerts = await self._check_trend_reversals(db)
            
            # Check for volume anomalies
            volume_alerts = await self._check_volume_anomalies(db)
            
            # Check for quality degradation
            quality_alerts = await self._check_quality_degradation(db)
            
            # Combine all alerts
            new_alerts = decline_alerts + threshold_alerts + trend_alerts + volume_alerts + quality_alerts
            
            # Process new alerts
            processed_alerts = await self._process_new_alerts(db, new_alerts)
            
            # Send notifications for critical alerts
            await self._send_alert_notifications(processed_alerts)
            
            # Update alert status
            monitoring_summary = {
                "monitoring_date": datetime.utcnow().isoformat(),
                "new_alerts": len(new_alerts),
                "critical_alerts": len([a for a in new_alerts if a.severity == AlertSeverity.CRITICAL]),
                "active_alerts": len(self.active_alerts),
                "alerts_by_type": self._categorize_alerts_by_type(new_alerts),
                "current_metrics": current_metrics
            }
            
            logger.info(f"Performance monitoring completed: {len(new_alerts)} new alerts")
            return monitoring_summary
            
        except Exception as e:
            logger.error(f"Error in performance monitoring: {e}")
            raise
    
    async def get_active_alerts(self, severity_filter: Optional[AlertSeverity] = None) -> List[Dict[str, Any]]:
        """Get currently active alerts"""
        try:
            active_alerts = list(self.active_alerts.values())
            
            if severity_filter:
                active_alerts = [a for a in active_alerts if a.severity == severity_filter]
            
            return [self._alert_to_dict(alert) for alert in active_alerts]
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            raise
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> Dict[str, Any]:
        """Acknowledge an alert"""
        try:
            if alert_id not in self.active_alerts:
                return {"error": "Alert not found"}
            
            alert = self.active_alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_at = datetime.utcnow()
            alert.metadata["acknowledged_by"] = acknowledged_by
            
            logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
            
            return {
                "status": "acknowledged",
                "alert_id": alert_id,
                "acknowledged_at": alert.acknowledged_at.isoformat(),
                "acknowledged_by": acknowledged_by
            }
            
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            raise
    
    async def resolve_alert(self, alert_id: str, resolution_notes: str = None) -> Dict[str, Any]:
        """Resolve an alert"""
        try:
            if alert_id not in self.active_alerts:
                return {"error": "Alert not found"}
            
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            if resolution_notes:
                alert.metadata["resolution_notes"] = resolution_notes
            
            # Move to history
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert resolved: {alert_id}")
            
            return {
                "status": "resolved",
                "alert_id": alert_id,
                "resolved_at": alert.resolved_at.isoformat(),
                "resolution_notes": resolution_notes
            }
            
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            raise
    
    async def get_alert_history(
        self, 
        days: int = 30,
        alert_type: Optional[AlertType] = None
    ) -> List[Dict[str, Any]]:
        """Get alert history"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            filtered_history = [
                alert for alert in self.alert_history
                if alert.created_at >= cutoff_date
            ]
            
            if alert_type:
                filtered_history = [
                    alert for alert in filtered_history
                    if alert.alert_type == alert_type
                ]
            
            return [self._alert_to_dict(alert) for alert in filtered_history]
            
        except Exception as e:
            logger.error(f"Error getting alert history: {e}")
            raise
    
    async def update_alert_thresholds(self, new_thresholds: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Update alert thresholds"""
        try:
            # Validate thresholds
            for metric, thresholds in new_thresholds.items():
                if not all(severity in thresholds for severity in ["critical", "high", "medium", "low"]):
                    return {"error": f"Missing severity levels for metric: {metric}"}
                
                # Ensure thresholds are in correct order
                if not (thresholds["critical"] <= thresholds["high"] <= thresholds["medium"] <= thresholds["low"]):
                    return {"error": f"Invalid threshold order for metric: {metric}"}
            
            # Update thresholds
            self.thresholds.update(new_thresholds)
            
            logger.info(f"Updated alert thresholds for {len(new_thresholds)} metrics")
            
            return {
                "status": "updated",
                "updated_metrics": list(new_thresholds.keys()),
                "update_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating alert thresholds: {e}")
            raise
    
    async def generate_corrective_action_plan(
        self, 
        db: AsyncSession,
        alert_id: str
    ) -> Dict[str, Any]:
        """Generate a corrective action plan for an alert"""
        try:
            if alert_id not in self.active_alerts:
                return {"error": "Alert not found"}
            
            alert = self.active_alerts[alert_id]
            
            # Generate specific corrective actions based on alert type
            action_plan = await self._generate_action_plan(db, alert)
            
            return {
                "alert_id": alert_id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "action_plan": action_plan,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating corrective action plan: {e}")
            raise
    
    # Private helper methods
    
    async def _get_current_performance_metrics(self, db: AsyncSession) -> Dict[str, float]:
        """Get current performance metrics"""
        try:
            # Get recent performance data
            pipeline_analytics = await performance_tracking_service.get_pipeline_analytics(db, days=7)
            
            conversion_rates = pipeline_analytics.get("conversion_rates", {})
            pipeline_metrics = pipeline_analytics.get("pipeline_metrics", {})
            
            # Calculate key metrics
            response_rate = conversion_rates.get("application_to_response", 0)
            hire_rate = conversion_rates.get("interview_to_hire", 0)
            
            # Calculate overall success rate
            success_rate = (
                conversion_rates.get("application_to_response", 0) / 100 *
                conversion_rates.get("response_to_interview", 0) / 100 *
                conversion_rates.get("interview_to_hire", 0) / 100 * 100
            )
            
            # Calculate daily application volume
            application_volume = pipeline_metrics.get("applied", 0) / 7  # Average per day
            
            return {
                "response_rate": response_rate,
                "hire_rate": hire_rate,
                "success_rate": success_rate,
                "application_volume": application_volume,
                "proposal_quality": 0.75  # Placeholder - would be calculated from actual quality metrics
            }
            
        except Exception as e:
            logger.error(f"Error getting current performance metrics: {e}")
            return {}
    
    async def _check_performance_declines(
        self, 
        db: AsyncSession, 
        current_metrics: Dict[str, float]
    ) -> List[Alert]:
        """Check for performance declines compared to historical data"""
        alerts = []
        
        try:
            # Get historical performance for comparison
            historical_metrics = await self._get_historical_performance_metrics(db, days=30)
            
            for metric_name, current_value in current_metrics.items():
                historical_value = historical_metrics.get(metric_name, 0)
                
                if historical_value > 0:
                    decline_percentage = ((historical_value - current_value) / historical_value) * 100
                    
                    # Check for significant declines
                    if decline_percentage > 50:  # 50% decline
                        severity = AlertSeverity.CRITICAL
                    elif decline_percentage > 30:  # 30% decline
                        severity = AlertSeverity.HIGH
                    elif decline_percentage > 20:  # 20% decline
                        severity = AlertSeverity.MEDIUM
                    elif decline_percentage > 10:  # 10% decline
                        severity = AlertSeverity.LOW
                    else:
                        continue
                    
                    alert = Alert(
                        alert_type=AlertType.PERFORMANCE_DECLINE,
                        severity=severity,
                        title=f"{metric_name.replace('_', ' ').title()} Performance Decline",
                        description=f"{metric_name} has declined by {decline_percentage:.1f}% "
                                  f"from {historical_value:.2f} to {current_value:.2f}",
                        metric_name=metric_name,
                        current_value=current_value,
                        threshold_value=historical_value,
                        trend_data={
                            "historical_value": historical_value,
                            "decline_percentage": decline_percentage
                        },
                        corrective_actions=self._get_decline_corrective_actions(metric_name, decline_percentage)
                    )
                    
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking performance declines: {e}")
            return []
    
    async def _check_threshold_breaches(self, current_metrics: Dict[str, float]) -> List[Alert]:
        """Check for threshold breaches"""
        alerts = []
        
        try:
            for metric_name, current_value in current_metrics.items():
                if metric_name not in self.thresholds:
                    continue
                
                thresholds = self.thresholds[metric_name]
                
                # Determine severity based on threshold breach
                severity = None
                threshold_value = None
                
                if current_value <= thresholds["critical"]:
                    severity = AlertSeverity.CRITICAL
                    threshold_value = thresholds["critical"]
                elif current_value <= thresholds["high"]:
                    severity = AlertSeverity.HIGH
                    threshold_value = thresholds["high"]
                elif current_value <= thresholds["medium"]:
                    severity = AlertSeverity.MEDIUM
                    threshold_value = thresholds["medium"]
                elif current_value <= thresholds["low"]:
                    severity = AlertSeverity.LOW
                    threshold_value = thresholds["low"]
                
                if severity:
                    alert = Alert(
                        alert_type=AlertType.THRESHOLD_BREACH,
                        severity=severity,
                        title=f"{metric_name.replace('_', ' ').title()} Below Threshold",
                        description=f"{metric_name} ({current_value:.2f}) is below the {severity.value} "
                                  f"threshold ({threshold_value:.2f})",
                        metric_name=metric_name,
                        current_value=current_value,
                        threshold_value=threshold_value,
                        corrective_actions=self._get_threshold_corrective_actions(metric_name, severity)
                    )
                    
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking threshold breaches: {e}")
            return []
    
    async def _check_trend_reversals(self, db: AsyncSession) -> List[Alert]:
        """Check for negative trend reversals"""
        alerts = []
        
        try:
            # Get trend data for key metrics
            trend_data = await self._get_trend_analysis(db)
            
            for metric_name, trend_info in trend_data.items():
                if trend_info.get("trend") == "decreasing" and trend_info.get("significant", False):
                    slope = trend_info.get("slope", 0)
                    
                    # Determine severity based on trend slope
                    if slope < -0.5:
                        severity = AlertSeverity.HIGH
                    elif slope < -0.3:
                        severity = AlertSeverity.MEDIUM
                    else:
                        severity = AlertSeverity.LOW
                    
                    alert = Alert(
                        alert_type=AlertType.TREND_REVERSAL,
                        severity=severity,
                        title=f"{metric_name.replace('_', ' ').title()} Negative Trend",
                        description=f"{metric_name} shows a significant decreasing trend "
                                  f"(slope: {slope:.3f})",
                        metric_name=metric_name,
                        current_value=trend_info.get("latest_value", 0),
                        threshold_value=0,  # Trend threshold
                        trend_data=trend_info,
                        corrective_actions=self._get_trend_corrective_actions(metric_name)
                    )
                    
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking trend reversals: {e}")
            return []
    
    async def _check_volume_anomalies(self, db: AsyncSession) -> List[Alert]:
        """Check for volume anomalies"""
        alerts = []
        
        try:
            # Get recent application volumes
            recent_volumes = await self._get_recent_application_volumes(db, days=7)
            
            if len(recent_volumes) >= 3:
                avg_volume = statistics.mean(recent_volumes)
                latest_volume = recent_volumes[-1]
                
                # Check for significant volume drops
                if latest_volume < avg_volume * 0.5:  # 50% drop
                    severity = AlertSeverity.HIGH
                elif latest_volume < avg_volume * 0.7:  # 30% drop
                    severity = AlertSeverity.MEDIUM
                else:
                    return alerts
                
                alert = Alert(
                    alert_type=AlertType.VOLUME_ANOMALY,
                    severity=severity,
                    title="Application Volume Drop",
                    description=f"Daily application volume ({latest_volume:.1f}) is significantly "
                              f"below recent average ({avg_volume:.1f})",
                    metric_name="application_volume",
                    current_value=latest_volume,
                    threshold_value=avg_volume * 0.7,
                    corrective_actions=self._get_volume_corrective_actions()
                )
                
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking volume anomalies: {e}")
            return []
    
    async def _check_quality_degradation(self, db: AsyncSession) -> List[Alert]:
        """Check for quality degradation"""
        alerts = []
        
        try:
            # Get recent quality metrics
            quality_trend = await self._get_quality_trend(db)
            
            if quality_trend.get("declining", False):
                current_quality = quality_trend.get("current_score", 0)
                decline_rate = quality_trend.get("decline_rate", 0)
                
                if decline_rate > 0.2:  # 20% decline
                    severity = AlertSeverity.HIGH
                elif decline_rate > 0.1:  # 10% decline
                    severity = AlertSeverity.MEDIUM
                else:
                    severity = AlertSeverity.LOW
                
                alert = Alert(
                    alert_type=AlertType.QUALITY_DEGRADATION,
                    severity=severity,
                    title="Proposal Quality Degradation",
                    description=f"Proposal quality has declined by {decline_rate*100:.1f}% "
                              f"to {current_quality:.2f}",
                    metric_name="proposal_quality",
                    current_value=current_quality,
                    threshold_value=current_quality * (1 + decline_rate),
                    corrective_actions=self._get_quality_corrective_actions()
                )
                
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking quality degradation: {e}")
            return []
    
    async def _process_new_alerts(self, db: AsyncSession, new_alerts: List[Alert]) -> List[Alert]:
        """Process new alerts and add to active alerts"""
        processed_alerts = []
        
        for alert in new_alerts:
            # Check if similar alert already exists
            existing_alert = self._find_similar_alert(alert)
            
            if existing_alert:
                # Update existing alert if new one is more severe
                if alert.severity.value > existing_alert.severity.value:
                    existing_alert.severity = alert.severity
                    existing_alert.description = alert.description
                    existing_alert.current_value = alert.current_value
                    processed_alerts.append(existing_alert)
            else:
                # Add new alert
                self.active_alerts[str(alert.id)] = alert
                processed_alerts.append(alert)
                
                # Record alert in database
                await self._record_alert_in_database(db, alert)
        
        return processed_alerts
    
    async def _send_alert_notifications(self, alerts: List[Alert]):
        """Send notifications for alerts"""
        try:
            for alert in alerts:
                if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                    # Send immediate notification
                    await notification_service.send_alert_notification(
                        title=alert.title,
                        message=alert.description,
                        severity=alert.severity.value,
                        corrective_actions=alert.corrective_actions
                    )
                    
        except Exception as e:
            logger.error(f"Error sending alert notifications: {e}")
    
    def _find_similar_alert(self, new_alert: Alert) -> Optional[Alert]:
        """Find similar existing alert"""
        for alert in self.active_alerts.values():
            if (alert.alert_type == new_alert.alert_type and 
                alert.metric_name == new_alert.metric_name and
                not alert.resolved):
                return alert
        return None
    
    async def _record_alert_in_database(self, db: AsyncSession, alert: Alert):
        """Record alert in database for historical tracking"""
        try:
            metric = PerformanceMetricModel(
                metric_type="alert_generated",
                metric_value=Decimal("1"),
                time_period="event",
                date_recorded=alert.created_at,
                metadata={
                    "alert_id": str(alert.id),
                    "alert_type": alert.alert_type.value,
                    "severity": alert.severity.value,
                    "metric_name": alert.metric_name,
                    "current_value": alert.current_value,
                    "threshold_value": alert.threshold_value,
                    "title": alert.title,
                    "description": alert.description
                }
            )
            
            db.add(metric)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error recording alert in database: {e}")
    
    def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]:
        """Convert alert object to dictionary"""
        return {
            "id": str(alert.id),
            "alert_type": alert.alert_type.value,
            "severity": alert.severity.value,
            "title": alert.title,
            "description": alert.description,
            "metric_name": alert.metric_name,
            "current_value": alert.current_value,
            "threshold_value": alert.threshold_value,
            "trend_data": alert.trend_data,
            "corrective_actions": alert.corrective_actions,
            "metadata": alert.metadata,
            "created_at": alert.created_at.isoformat(),
            "acknowledged": alert.acknowledged,
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            "resolved": alert.resolved,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
        }
    
    def _categorize_alerts_by_type(self, alerts: List[Alert]) -> Dict[str, int]:
        """Categorize alerts by type"""
        categories = {}
        for alert in alerts:
            alert_type = alert.alert_type.value
            categories[alert_type] = categories.get(alert_type, 0) + 1
        return categories
    
    # Corrective action generators
    
    def _get_decline_corrective_actions(self, metric_name: str, decline_percentage: float) -> List[str]:
        """Get corrective actions for performance declines"""
        base_actions = [
            "Review recent changes to automation settings",
            "Analyze job selection criteria for effectiveness",
            "Check for external factors affecting performance"
        ]
        
        if metric_name == "response_rate":
            return base_actions + [
                "Improve proposal quality and personalization",
                "Adjust bid amounts to be more competitive",
                "Target jobs with better client ratings",
                "Review and update proposal templates"
            ]
        elif metric_name == "hire_rate":
            return base_actions + [
                "Enhance interview preparation materials",
                "Follow up more promptly with interested clients",
                "Improve portfolio and case study presentations",
                "Adjust pricing strategy for better conversion"
            ]
        elif metric_name == "application_volume":
            return base_actions + [
                "Check job discovery automation for issues",
                "Expand keyword targeting criteria",
                "Review and adjust job filtering rules",
                "Increase daily application limits if appropriate"
            ]
        
        return base_actions
    
    def _get_threshold_corrective_actions(self, metric_name: str, severity: AlertSeverity) -> List[str]:
        """Get corrective actions for threshold breaches"""
        if severity == AlertSeverity.CRITICAL:
            return [
                "Immediately pause automation to prevent further issues",
                "Conduct emergency review of system settings",
                "Contact support team for assistance",
                "Implement manual oversight until issue is resolved"
            ]
        
        return [
            "Review and adjust automation parameters",
            "Analyze recent performance data for patterns",
            "Consider temporary reduction in application volume",
            "Monitor closely for continued degradation"
        ]
    
    def _get_trend_corrective_actions(self, metric_name: str) -> List[str]:
        """Get corrective actions for negative trends"""
        return [
            "Analyze trend data to identify root causes",
            "Review recent system changes and their impact",
            "Consider strategy adjustments based on market conditions",
            "Implement A/B testing for different approaches"
        ]
    
    def _get_volume_corrective_actions(self) -> List[str]:
        """Get corrective actions for volume anomalies"""
        return [
            "Check job discovery automation for technical issues",
            "Review job filtering criteria for over-restrictive rules",
            "Verify external job sources are functioning properly",
            "Consider expanding search parameters temporarily"
        ]
    
    def _get_quality_corrective_actions(self) -> List[str]:
        """Get corrective actions for quality degradation"""
        return [
            "Review and update proposal templates",
            "Implement additional quality checks in automation",
            "Analyze successful proposals for improvement patterns",
            "Consider manual review of generated proposals"
        ]
    
    # Placeholder methods for data retrieval
    
    async def _get_historical_performance_metrics(self, db: AsyncSession, days: int) -> Dict[str, float]:
        """Get historical performance metrics for comparison"""
        return {}
    
    async def _get_trend_analysis(self, db: AsyncSession) -> Dict[str, Any]:
        """Get trend analysis for key metrics"""
        return {}
    
    async def _get_recent_application_volumes(self, db: AsyncSession, days: int) -> List[float]:
        """Get recent application volumes"""
        return []
    
    async def _get_quality_trend(self, db: AsyncSession) -> Dict[str, Any]:
        """Get quality trend analysis"""
        return {}
    
    async def _generate_action_plan(self, db: AsyncSession, alert: Alert) -> Dict[str, Any]:
        """Generate detailed corrective action plan"""
        return {
            "immediate_actions": alert.corrective_actions[:2],
            "short_term_actions": alert.corrective_actions[2:4],
            "long_term_actions": alert.corrective_actions[4:],
            "monitoring_plan": [
                "Monitor metric daily for improvement",
                "Set up additional alerts for early warning",
                "Review effectiveness of actions weekly"
            ]
        }


# Global service instance
alerting_system = AlertingSystem()