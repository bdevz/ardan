"""
Base worker class for background task processing
"""
import asyncio
import logging
import signal
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional

from services.task_queue_service import task_queue_service

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """Base class for background workers"""
    
    def __init__(self, worker_name: str, task_types: List[str], concurrency: int = 1):
        self.worker_name = worker_name
        self.task_types = task_types
        self.concurrency = concurrency
        self.running = False
        self.tasks = []
        
    @abstractmethod
    async def process_task(self, task_id: str, task_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single task - must be implemented by subclasses"""
        pass
    
    async def start(self):
        """Start the worker"""
        self.running = True
        logger.info(f"Starting worker {self.worker_name} with {self.concurrency} concurrent tasks")
        
        # Initialize task queue service
        await task_queue_service.initialize()
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start worker tasks
        self.tasks = [
            asyncio.create_task(self._worker_loop(i))
            for i in range(self.concurrency)
        ]
        
        # Start scheduled task processor
        self.tasks.append(asyncio.create_task(self._scheduled_task_processor()))
        
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info(f"Worker {self.worker_name} cancelled")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the worker gracefully"""
        if not self.running:
            return
            
        logger.info(f"Stopping worker {self.worker_name}")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Close task queue service
        await task_queue_service.close()
        
        logger.info(f"Worker {self.worker_name} stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down worker {self.worker_name}")
        self.running = False
    
    async def _worker_loop(self, worker_id: int):
        """Main worker loop for processing tasks"""
        logger.info(f"Worker {self.worker_name}-{worker_id} started")
        
        while self.running:
            try:
                # Dequeue next task
                task_info = await task_queue_service.dequeue_task(self.task_types, timeout=5)
                
                if not task_info:
                    # No tasks available, wait a bit
                    await asyncio.sleep(1)
                    continue
                
                task_id = task_info["task_id"]
                task_type = task_info["task_type"]
                
                logger.info(f"Worker {self.worker_name}-{worker_id} processing task {task_id}")
                
                # Get task data from database
                task_status = await task_queue_service.get_task_status(task_id)
                if not task_status:
                    logger.error(f"Task {task_id} not found in database")
                    continue
                
                try:
                    # Process the task
                    start_time = datetime.utcnow()
                    result = await self.process_task(str(task_id), task_type, task_status.task_data)
                    end_time = datetime.utcnow()
                    
                    # Mark task as completed
                    completion_result = {
                        "result": result,
                        "processing_time": (end_time - start_time).total_seconds(),
                        "worker_id": f"{self.worker_name}-{worker_id}"
                    }
                    await task_queue_service.complete_task(task_id, completion_result)
                    
                    logger.info(f"Worker {self.worker_name}-{worker_id} completed task {task_id}")
                    
                except Exception as e:
                    logger.error(f"Worker {self.worker_name}-{worker_id} failed to process task {task_id}: {str(e)}")
                    await task_queue_service.fail_task(task_id, str(e))
                
            except asyncio.CancelledError:
                logger.info(f"Worker {self.worker_name}-{worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker {self.worker_name}-{worker_id}: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
        
        logger.info(f"Worker {self.worker_name}-{worker_id} stopped")
    
    async def _scheduled_task_processor(self):
        """Process scheduled tasks"""
        logger.info(f"Scheduled task processor for {self.worker_name} started")
        
        while self.running:
            try:
                await task_queue_service.process_scheduled_tasks()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduled task processor: {str(e)}")
                await asyncio.sleep(60)
        
        logger.info(f"Scheduled task processor for {self.worker_name} stopped")


class WorkerManager:
    """Manager for multiple workers"""
    
    def __init__(self):
        self.workers: List[BaseWorker] = []
        self.running = False
    
    def add_worker(self, worker: BaseWorker):
        """Add a worker to the manager"""
        self.workers.append(worker)
    
    async def start_all(self):
        """Start all workers"""
        self.running = True
        logger.info(f"Starting {len(self.workers)} workers")
        
        # Start all workers concurrently
        worker_tasks = [asyncio.create_task(worker.start()) for worker in self.workers]
        
        try:
            await asyncio.gather(*worker_tasks)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down workers")
        finally:
            await self.stop_all()
    
    async def stop_all(self):
        """Stop all workers"""
        if not self.running:
            return
            
        logger.info("Stopping all workers")
        self.running = False
        
        # Stop all workers
        stop_tasks = [asyncio.create_task(worker.stop()) for worker in self.workers]
        await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        logger.info("All workers stopped")


# Global worker manager instance
worker_manager = WorkerManager()