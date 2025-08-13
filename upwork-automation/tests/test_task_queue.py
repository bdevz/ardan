"""
Tests for task queue functionality
"""
import asyncio
import pytest
import sys
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

# Add the api directory to the path
sys.path.append(str(Path(__file__).parent.parent / "api"))

from services.task_queue_service import TaskQueueService, task_queue_service
from services.task_scheduler import TaskScheduler, ScheduledTask
from services.queue_metrics_service import QueueMetricsService
from workers.base_worker import BaseWorker
from shared.models import TaskQueue


class TestTaskQueueService:
    """Test cases for TaskQueueService"""
    
    @pytest.fixture
    async def queue_service(self):
        """Create a test task queue service"""
        service = TaskQueueService("redis://localhost:6379/1")  # Use test database
        await service.initialize()
        yield service
        await service.close()
    
    @pytest.mark.asyncio
    async def test_enqueue_task(self, queue_service):
        """Test enqueuing a task"""
        task_data = {"test": "data", "value": 123}
        
        with patch('services.task_queue_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            task_id = await queue_service.enqueue_task(
                task_type="test_task",
                task_data=task_data,
                priority=5
            )
            
            assert task_id is not None
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_enqueue_scheduled_task(self, queue_service):
        """Test enqueuing a scheduled task"""
        task_data = {"test": "scheduled"}
        scheduled_at = datetime.utcnow() + timedelta(hours=1)
        
        with patch('services.task_queue_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            task_id = await queue_service.enqueue_task(
                task_type="scheduled_task",
                task_data=task_data,
                scheduled_at=scheduled_at
            )
            
            assert task_id is not None
            mock_session.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dequeue_task(self, queue_service):
        """Test dequeuing a task"""
        # Mock Redis operations
        with patch.object(queue_service.redis_client, 'zpopmin') as mock_zpopmin:
            mock_zpopmin.return_value = [('{"task_id": "test-id", "task_type": "test", "priority": 5}', -5)]
            
            with patch('services.task_queue_service.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                task_info = await queue_service.dequeue_task(["test"])
                
                assert task_info is not None
                assert task_info["task_type"] == "test"
                assert task_info["priority"] == 5
    
    @pytest.mark.asyncio
    async def test_complete_task(self, queue_service):
        """Test completing a task"""
        task_id = uuid4()
        result = {"status": "success", "data": "test"}
        
        with patch('services.task_queue_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            await queue_service.complete_task(task_id, result)
            
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fail_task_with_retry(self, queue_service):
        """Test failing a task with retry"""
        task_id = uuid4()
        error_message = "Test error"
        
        # Mock task with retry count < max_retries
        mock_task = MagicMock()
        mock_task.retry_count = 1
        mock_task.max_retries = 3
        
        with patch('services.task_queue_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_task
            mock_db.return_value.__aenter__.return_value = mock_session
            
            await queue_service.fail_task(task_id, error_message, retry=True)
            
            # Should update retry count and re-schedule
            assert mock_session.execute.call_count >= 1
            mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_fail_task_permanently(self, queue_service):
        """Test permanently failing a task"""
        task_id = uuid4()
        error_message = "Permanent failure"
        
        # Mock task with max retries reached
        mock_task = MagicMock()
        mock_task.retry_count = 3
        mock_task.max_retries = 3
        
        with patch('services.task_queue_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_task
            mock_db.return_value.__aenter__.return_value = mock_session
            
            await queue_service.fail_task(task_id, error_message, retry=True)
            
            mock_session.execute.assert_called()
            mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_queue_stats(self, queue_service):
        """Test getting queue statistics"""
        with patch.object(queue_service.redis_client, 'keys') as mock_keys, \
             patch.object(queue_service.redis_client, 'zcard') as mock_zcard, \
             patch('services.task_queue_service.get_db_session') as mock_db:
            
            mock_keys.return_value = ["queue:test1", "queue:test2"]
            mock_zcard.return_value = 5
            
            mock_session = AsyncMock()
            mock_session.execute.return_value.all.return_value = [MagicMock() for _ in range(3)]
            mock_db.return_value.__aenter__.return_value = mock_session
            
            stats = await queue_service.get_queue_stats()
            
            assert "queues" in stats
            assert "total_pending" in stats
            assert stats["queues"]["test1"] == 5
            assert stats["queues"]["test2"] == 5
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, queue_service):
        """Test cancelling a task"""
        task_id = uuid4()
        
        # Mock pending task
        mock_task = MagicMock()
        mock_task.status = "pending"
        mock_task.task_type = "test"
        
        with patch('services.task_queue_service.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_task
            mock_db.return_value.__aenter__.return_value = mock_session
            
            result = await queue_service.cancel_task(task_id)
            
            assert result is True
            mock_session.execute.assert_called()
            mock_session.commit.assert_called()


class TestTaskScheduler:
    """Test cases for TaskScheduler"""
    
    @pytest.fixture
    def scheduler(self):
        """Create a test task scheduler"""
        return TaskScheduler()
    
    def test_add_scheduled_task(self, scheduler):
        """Test adding a scheduled task"""
        scheduler.add_scheduled_task(
            name="test_task",
            cron_expression="0 * * * *",  # Every hour
            task_type="test",
            task_data={"test": "data"}
        )
        
        assert "test_task" in scheduler.scheduled_tasks
        task = scheduler.scheduled_tasks["test_task"]
        assert task.name == "test_task"
        assert task.cron_expression == "0 * * * *"
        assert task.enabled is True
        assert task.next_run is not None
    
    def test_add_invalid_cron_expression(self, scheduler):
        """Test adding task with invalid cron expression"""
        with pytest.raises(ValueError):
            scheduler.add_scheduled_task(
                name="invalid_task",
                cron_expression="invalid cron",
                task_type="test",
                task_data={}
            )
    
    def test_remove_scheduled_task(self, scheduler):
        """Test removing a scheduled task"""
        scheduler.add_scheduled_task(
            name="test_task",
            cron_expression="0 * * * *",
            task_type="test",
            task_data={}
        )
        
        result = scheduler.remove_scheduled_task("test_task")
        assert result is True
        assert "test_task" not in scheduler.scheduled_tasks
        
        # Try removing non-existent task
        result = scheduler.remove_scheduled_task("non_existent")
        assert result is False
    
    def test_enable_disable_task(self, scheduler):
        """Test enabling and disabling tasks"""
        scheduler.add_scheduled_task(
            name="test_task",
            cron_expression="0 * * * *",
            task_type="test",
            task_data={}
        )
        
        # Disable task
        result = scheduler.disable_task("test_task")
        assert result is True
        assert scheduler.scheduled_tasks["test_task"].enabled is False
        
        # Enable task
        result = scheduler.enable_task("test_task")
        assert result is True
        assert scheduler.scheduled_tasks["test_task"].enabled is True
    
    def test_get_scheduled_tasks(self, scheduler):
        """Test getting scheduled tasks list"""
        scheduler.add_scheduled_task(
            name="test_task1",
            cron_expression="0 * * * *",
            task_type="test1",
            task_data={}
        )
        scheduler.add_scheduled_task(
            name="test_task2",
            cron_expression="0 0 * * *",
            task_type="test2",
            task_data={}
        )
        
        tasks = scheduler.get_scheduled_tasks()
        assert len(tasks) == 2
        assert all("name" in task for task in tasks)
        assert all("cron_expression" in task for task in tasks)


class TestWorker:
    """Test cases for BaseWorker"""
    
    class TestWorkerImpl(BaseWorker):
        """Test implementation of BaseWorker"""
        
        def __init__(self):
            super().__init__("test_worker", ["test_task"], concurrency=1)
            self.processed_tasks = []
        
        async def process_task(self, task_id: str, task_type: str, task_data: dict):
            self.processed_tasks.append({
                "task_id": task_id,
                "task_type": task_type,
                "task_data": task_data
            })
            return {"status": "success"}
    
    @pytest.fixture
    def test_worker(self):
        """Create a test worker"""
        return self.TestWorkerImpl()
    
    @pytest.mark.asyncio
    async def test_worker_initialization(self, test_worker):
        """Test worker initialization"""
        assert test_worker.worker_name == "test_worker"
        assert test_worker.task_types == ["test_task"]
        assert test_worker.concurrency == 1
        assert test_worker.running is False
    
    @pytest.mark.asyncio
    async def test_process_task(self, test_worker):
        """Test task processing"""
        task_id = str(uuid4())
        task_type = "test_task"
        task_data = {"test": "data"}
        
        result = await test_worker.process_task(task_id, task_type, task_data)
        
        assert result["status"] == "success"
        assert len(test_worker.processed_tasks) == 1
        assert test_worker.processed_tasks[0]["task_id"] == task_id


class TestQueueMetricsService:
    """Test cases for QueueMetricsService"""
    
    @pytest.fixture
    def metrics_service(self):
        """Create a test metrics service"""
        return QueueMetricsService()
    
    @pytest.mark.asyncio
    async def test_get_queue_health_metrics(self, metrics_service):
        """Test getting queue health metrics"""
        with patch('services.queue_metrics_service.task_queue_service') as mock_queue_service, \
             patch('services.queue_metrics_service.get_db_session') as mock_db:
            
            # Mock basic stats
            mock_queue_service.get_queue_stats.return_value = {
                "total_pending": 10,
                "total_processing": 2,
                "total_completed": 100,
                "total_failed": 5,
                "queues": {"test": 5, "other": 5}
            }
            
            # Mock database session
            mock_session = AsyncMock()
            mock_session.execute.return_value = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            metrics = await metrics_service.get_queue_health_metrics()
            
            assert "basic_stats" in metrics
            assert "health_score" in metrics
            assert "timestamp" in metrics
            assert isinstance(metrics["health_score"], float)
    
    def test_calculate_health_score(self, metrics_service):
        """Test health score calculation"""
        basic_stats = {"total_pending": 50}
        failure_rates = {"test_task": {"failure_rate": 0.05}}
        processing_times = {"test_task": {"avg_seconds": 120}}
        
        score = metrics_service._calculate_health_score(
            basic_stats, failure_rates, processing_times
        )
        
        assert 0 <= score <= 100
        assert isinstance(score, float)
    
    def test_cache_functionality(self, metrics_service):
        """Test metrics caching"""
        cache_key = "test_cache"
        test_data = {"test": "data"}
        
        # Cache data
        metrics_service._cache_metrics(cache_key, test_data)
        
        # Check if cache is valid
        assert metrics_service._is_cache_valid(cache_key) is True
        
        # Check cached data
        cached_data = metrics_service.metrics_cache[cache_key]["data"]
        assert cached_data == test_data


class TestIntegration:
    """Integration tests for task queue system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_task_processing(self):
        """Test complete task processing workflow"""
        # This would be a more complex integration test
        # that tests the entire flow from enqueue to completion
        pass
    
    @pytest.mark.asyncio
    async def test_scheduler_integration(self):
        """Test scheduler integration with task queue"""
        # Test that scheduled tasks are properly enqueued
        pass
    
    @pytest.mark.asyncio
    async def test_worker_integration(self):
        """Test worker integration with task queue"""
        # Test that workers properly process tasks from the queue
        pass


# Fixtures for database testing
@pytest.fixture
async def test_db_session():
    """Create a test database session"""
    # This would set up a test database session
    # In a real implementation, you'd use a test database
    pass


@pytest.fixture
async def test_redis():
    """Create a test Redis connection"""
    # This would set up a test Redis instance
    # In a real implementation, you'd use a test Redis database
    pass


# Performance tests
class TestPerformance:
    """Performance tests for task queue"""
    
    @pytest.mark.asyncio
    async def test_high_volume_enqueue(self):
        """Test enqueuing many tasks quickly"""
        # Test performance with high volume of tasks
        pass
    
    @pytest.mark.asyncio
    async def test_concurrent_workers(self):
        """Test multiple workers processing tasks concurrently"""
        # Test performance with multiple concurrent workers
        pass
    
    @pytest.mark.asyncio
    async def test_queue_depth_performance(self):
        """Test performance with deep queues"""
        # Test how system performs with many queued tasks
        pass