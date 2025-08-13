"""
Task Scheduler Runner - Main entry point for running the task scheduler
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add the current directory to the path so we can import from api modules
sys.path.append(str(Path(__file__).parent))

from services.task_scheduler import task_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scheduler.log')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main function to start the task scheduler"""
    logger.info("Starting Upwork Automation Task Scheduler")
    
    try:
        # Start the scheduler
        await task_scheduler.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        logger.info("Task scheduler shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())