"""
Task Scheduler for cron-like functionality
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from croniter import croniter

from services.task_queue_service import task_queue_service

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """Represents a scheduled task"""
    name: str
    cron_expression: str
    task_type: str
    task_data: Dict[str, Any]
    priority: int = 0
    max_retries: int = 3
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class TaskScheduler:
    """Cron-like task scheduler"""
    
    def __init__(self):
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
    def add_scheduled_task(
        self,
        name: str,
        cron_expression: str,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 0,
        max_retries: int = 3,
        enabled: bool = True
    ):
        """Add a scheduled task"""
        # Validate cron expression
        try:
            cron = croniter(cron_expression, datetime.utcnow())
            next_run = cron.get_next(datetime)
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{cron_expression}': {str(e)}")
        
        scheduled_task = ScheduledTask(
            name=name,
            cron_expression=cron_expression,
            task_type=task_type,
            task_data=task_data,
            priority=priority,
            max_retries=max_retries,
            enabled=enabled,
            next_run=next_run
        )
        
        self.scheduled_tasks[name] = scheduled_task
        logger.info(f"Added scheduled task '{name}' with cron '{cron_expression}', next run: {next_run}")
    
    def remove_scheduled_task(self, name: str) -> bool:
        """Remove a scheduled task"""
        if name in self.scheduled_tasks:
            del self.scheduled_tasks[name]
            logger.info(f"Removed scheduled task '{name}'")
            return True
        return False
    
    def enable_task(self, name: str) -> bool:
        """Enable a scheduled task"""
        if name in self.scheduled_tasks:
            self.scheduled_tasks[name].enabled = True
            self._update_next_run(name)
            logger.info(f"Enabled scheduled task '{name}'")
            return True
        return False
    
    def disable_task(self, name: str) -> bool:
        """Disable a scheduled task"""
        if name in self.scheduled_tasks:
            self.scheduled_tasks[name].enabled = False
            logger.info(f"Disabled scheduled task '{name}'")
            return True
        return False
    
    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Get all scheduled tasks"""
        return [
            {
                "name": task.name,
                "cron_expression": task.cron_expression,
                "task_type": task.task_type,
                "priority": task.priority,
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat() if task.next_run else None
            }
            for task in self.scheduled_tasks.values()
        ]
    
    def _update_next_run(self, name: str):
        """Update next run time for a task"""
        if name not in self.scheduled_tasks:
            return
        
        task = self.scheduled_tasks[name]
        if not task.enabled:
            task.next_run = None
            return
        
        try:
            cron = croniter(task.cron_expression, datetime.utcnow())
            task.next_run = cron.get_next(datetime)
        except Exception as e:
            logger.error(f"Failed to calculate next run for task '{name}': {str(e)}")
            task.next_run = None
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting task scheduler")
        
        # Initialize task queue service
        await task_queue_service.initialize()
        
        # Start scheduler loop
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        try:
            await self.scheduler_task
        except asyncio.CancelledError:
            logger.info("Task scheduler cancelled")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
        
        logger.info("Stopping task scheduler")
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        await task_queue_service.close()
        logger.info("Task scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                # Check each scheduled task
                for name, task in self.scheduled_tasks.items():
                    if not task.enabled or not task.next_run:
                        continue
                    
                    # Check if task should run
                    if current_time >= task.next_run:
                        await self._execute_scheduled_task(name, task)
                
                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _execute_scheduled_task(self, name: str, task: ScheduledTask):
        """Execute a scheduled task"""
        try:
            logger.info(f"Executing scheduled task '{name}'")
            
            # Enqueue the task
            task_id = await task_queue_service.enqueue_task(
                task_type=task.task_type,
                task_data=task.task_data,
                priority=task.priority,
                max_retries=task.max_retries
            )
            
            # Update task execution info
            task.last_run = datetime.utcnow()
            self._update_next_run(name)
            
            logger.info(f"Scheduled task '{name}' enqueued with ID {task_id}, next run: {task.next_run}")
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled task '{name}': {str(e)}")
            # Still update next run time to avoid getting stuck
            self._update_next_run(name)


class DefaultScheduledTasks:
    """Default scheduled tasks for the system"""
    
    @staticmethod
    def setup_default_tasks(scheduler: TaskScheduler):
        """Set up default scheduled tasks"""
        
        # Job discovery every 30 minutes
        scheduler.add_scheduled_task(
            name="job_discovery_regular",
            cron_expression="*/30 * * * *",  # Every 30 minutes
            task_type="job_discovery",
            task_data={
                "search_params": {
                    "keywords": ["Salesforce Agentforce", "Salesforce AI", "Einstein"],
                    "min_hourly_rate": 50,
                    "min_client_rating": 4.0,
                    "payment_verified_only": True
                },
                "session_pool_size": 3
            },
            priority=5
        )
        
        # Intensive job discovery every 2 hours during business hours
        scheduler.add_scheduled_task(
            name="job_discovery_intensive",
            cron_expression="0 9-17/2 * * 1-5",  # Every 2 hours, 9-5 PM, Mon-Fri
            task_type="job_discovery",
            task_data={
                "search_params": {
                    "keywords": ["Salesforce", "Agentforce", "Einstein", "Salesforce Developer"],
                    "min_hourly_rate": 40,
                    "min_client_rating": 3.5,
                    "payment_verified_only": True
                },
                "session_pool_size": 5
            },
            priority=8
        )
        
        # Proposal generation for queued jobs every hour
        scheduler.add_scheduled_task(
            name="proposal_generation_batch",
            cron_expression="0 * * * *",  # Every hour
            task_type="batch_generate_proposals",
            task_data={
                "max_proposals": 10,
                "include_attachments": True,
                "filter_criteria": {
                    "status": "filtered",
                    "match_score_min": 0.7
                }
            },
            priority=7
        )
        
        # Application submission batch every 2 hours during business hours
        scheduler.add_scheduled_task(
            name="application_submission_batch",
            cron_expression="30 9-17/2 * * 1-5",  # Every 2 hours at :30, 9-5 PM, Mon-Fri
            task_type="batch_submit_applications",
            task_data={
                "max_applications": 5,
                "confirm_submission": True,
                "max_daily_limit": 30
            },
            priority=9
        )
        
        # Daily cleanup of old tasks
        scheduler.add_scheduled_task(
            name="cleanup_old_tasks",
            cron_expression="0 2 * * *",  # Daily at 2 AM
            task_type="cleanup_tasks",
            task_data={
                "days_old": 30
            },
            priority=1
        )
        
        # Weekly performance metrics calculation
        scheduler.add_scheduled_task(
            name="calculate_weekly_metrics",
            cron_expression="0 6 * * 1",  # Monday at 6 AM
            task_type="calculate_metrics",
            task_data={
                "metric_types": ["application_success", "response_rate", "hire_rate"],
                "time_period": "weekly"
            },
            priority=3
        )
        
        # Browser session cleanup every 4 hours
        scheduler.add_scheduled_task(
            name="browser_session_cleanup",
            cron_expression="0 */4 * * *",  # Every 4 hours
            task_type="cleanup_browser_sessions",
            task_data={
                "max_idle_hours": 2,
                "max_session_age_hours": 24
            },
            priority=2
        )
        
        logger.info("Default scheduled tasks configured")


# Global task scheduler instance
task_scheduler = TaskScheduler()

# Set up default tasks
DefaultScheduledTasks.setup_default_tasks(task_scheduler)