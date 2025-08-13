"""
Worker Manager - Main entry point for running background workers
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from api modules
sys.path.append(str(Path(__file__).parent.parent))

from workers.base_worker import worker_manager
from workers.job_discovery_worker import job_discovery_worker
from workers.proposal_worker import proposal_worker
from workers.application_worker import application_worker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('workers.log')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main function to start all workers"""
    logger.info("Starting Upwork Automation Workers")
    
    # Add all workers to the manager
    worker_manager.add_worker(job_discovery_worker)
    worker_manager.add_worker(proposal_worker)
    worker_manager.add_worker(application_worker)
    
    try:
        # Start all workers
        await worker_manager.start_all()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        logger.info("Workers shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())