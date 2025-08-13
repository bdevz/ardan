"""
Browser service - business logic for browser automation and session management
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Add browser-automation to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'browser-automation'))

from database.models import BrowserSessionModel
from shared.models import BrowserSession
from shared.utils import setup_logging
from shared.error_handling import resilient_service, RetryConfig, CircuitBreakerConfig
from shared.circuit_breaker import CircuitBreakerConfig as CBConfig
from browserbase_client import BrowserbaseClient
from stagehand_controller import StagehandController
from job_discovery_service import JobDiscoveryService

logger = setup_logging("browser-service")


@resilient_service(
    "browser_service",
    retry_config=RetryConfig(
        max_retries=3,
        base_delay=2.0,
        max_delay=30.0,
        retryable_exceptions=(ConnectionError, TimeoutError, Exception),
        non_retryable_exceptions=(ValueError, TypeError)
    ),
    circuit_breaker_config=CBConfig(
        failure_threshold=5,
        recovery_timeout=120,
        timeout=60.0
    )
)
class BrowserService:
    """Service for browser automation operations"""
    
    def __init__(self):
        self.browserbase_client = BrowserbaseClient()
        self.stagehand_controller = StagehandController()
        self.job_discovery_service = None
    
    async def get_job_discovery_service(self) -> JobDiscoveryService:
        """Get or create job discovery service instance"""
        if self.job_discovery_service is None:
            self.job_discovery_service = JobDiscoveryService()
            await self.job_discovery_service.initialize()
        return self.job_discovery_service
    
    async def create_browser_session(
        self,
        db: AsyncSession,
        session_type: str = "job_discovery",
        context: Optional[Dict[str, Any]] = None
    ) -> BrowserSession:
        """Create new browser session"""
        try:
            # Create session with Browserbase
            session_config = {
                "projectId": "upwork-automation",
                "stealth": True,
                "keepAlive": True,
                "proxies": True
            }
            
            browserbase_session = await self.browserbase_client.create_session(session_config)
            
            # Calculate expiration (24 hours from now)
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            # Save session to database
            session_model = BrowserSessionModel(
                browserbase_session_id=browserbase_session.id,
                session_type=session_type,
                status="active",
                context=context or {},
                expires_at=expires_at
            )
            
            db.add(session_model)
            await db.commit()
            
            # Initialize Stagehand for the session
            await self.stagehand_controller.initialize_stagehand(browserbase_session.id)
            
            logger.info(f"Created browser session: {session_model.id}")
            
            return BrowserSession(
                id=session_model.id,
                browserbase_session_id=session_model.browserbase_session_id,
                session_type=session_model.session_type,
                status=session_model.status,
                context=session_model.context,
                created_at=session_model.created_at,
                expires_at=session_model.expires_at,
                last_used_at=session_model.last_used_at
            )
            
        except Exception as e:
            logger.error(f"Error creating browser session: {e}")
            await db.rollback()
            raise
    
    async def get_browser_session(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> Optional[BrowserSession]:
        """Get browser session details"""
        try:
            query = select(BrowserSessionModel).where(BrowserSessionModel.id == session_id)
            result = await db.execute(query)
            session_model = result.scalar_one_or_none()
            
            if not session_model:
                return None
            
            # Update last used timestamp
            session_model.last_used_at = datetime.utcnow()
            await db.commit()
            
            return BrowserSession(
                id=session_model.id,
                browserbase_session_id=session_model.browserbase_session_id,
                session_type=session_model.session_type,
                status=session_model.status,
                context=session_model.context,
                created_at=session_model.created_at,
                expires_at=session_model.expires_at,
                last_used_at=session_model.last_used_at
            )
            
        except Exception as e:
            logger.error(f"Error getting browser session: {e}")
            raise
    
    async def list_browser_sessions(
        self,
        db: AsyncSession,
        session_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[BrowserSession]:
        """List browser sessions with optional filtering"""
        try:
            query = select(BrowserSessionModel)
            
            # Apply filters
            filters = []
            if session_type:
                filters.append(BrowserSessionModel.session_type == session_type)
            if status:
                filters.append(BrowserSessionModel.status == status)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Order by created_at desc
            query = query.order_by(BrowserSessionModel.created_at.desc())
            
            result = await db.execute(query)
            session_models = result.scalars().all()
            
            sessions = []
            for session_model in session_models:
                sessions.append(BrowserSession(
                    id=session_model.id,
                    browserbase_session_id=session_model.browserbase_session_id,
                    session_type=session_model.session_type,
                    status=session_model.status,
                    context=session_model.context,
                    created_at=session_model.created_at,
                    expires_at=session_model.expires_at,
                    last_used_at=session_model.last_used_at
                ))
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error listing browser sessions: {e}")
            raise
    
    async def terminate_browser_session(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> bool:
        """Terminate browser session"""
        try:
            # Get session from database
            query = select(BrowserSessionModel).where(BrowserSessionModel.id == session_id)
            result = await db.execute(query)
            session_model = result.scalar_one_or_none()
            
            if not session_model:
                return False
            
            # Terminate Browserbase session
            try:
                await self.browserbase_client.end_session(session_model.browserbase_session_id)
            except Exception as e:
                logger.warning(f"Failed to terminate Browserbase session: {e}")
            
            # Cleanup Stagehand
            try:
                await self.stagehand_controller.cleanup_session(session_model.browserbase_session_id)
            except Exception as e:
                logger.warning(f"Failed to cleanup Stagehand session: {e}")
            
            # Update session status
            session_model.status = "terminated"
            await db.commit()
            
            logger.info(f"Terminated browser session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error terminating browser session: {e}")
            await db.rollback()
            raise
    
    async def browser_search_jobs(
        self,
        db: AsyncSession,
        keywords: List[str],
        session_pool_size: int = 3,
        max_jobs: int = 50
    ) -> Dict[str, Any]:
        """Search for jobs using browser automation"""
        try:
            # Get job discovery service
            discovery_service = await self.get_job_discovery_service()
            
            # Create search parameters
            from shared.models import JobSearchParams
            search_params = JobSearchParams(
                keywords=keywords,
                payment_verified_only=True
            )
            
            # Execute job discovery
            result = await discovery_service.discover_jobs(
                search_params=search_params,
                max_jobs=max_jobs
            )
            
            if result.success:
                # Save discovered jobs to database (this would be handled by job service)
                return {
                    "success": True,
                    "jobs_found": len(result.jobs_found),
                    "total_processed": result.total_processed,
                    "duplicates_removed": result.duplicates_removed,
                    "filtered_out": result.filtered_out,
                    "search_duration": result.search_duration,
                    "search_strategy": result.search_strategy,
                    "keywords": keywords
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "search_duration": result.search_duration,
                    "keywords": keywords
                }
                
        except Exception as e:
            logger.error(f"Error in browser job search: {e}")
            raise
    
    async def cleanup_expired_sessions(self, db: AsyncSession) -> int:
        """Cleanup expired browser sessions"""
        try:
            # Find expired sessions
            now = datetime.utcnow()
            query = select(BrowserSessionModel).where(
                and_(
                    BrowserSessionModel.expires_at < now,
                    BrowserSessionModel.status == "active"
                )
            )
            
            result = await db.execute(query)
            expired_sessions = result.scalars().all()
            
            cleanup_count = 0
            for session in expired_sessions:
                try:
                    # Terminate Browserbase session
                    await self.browserbase_client.end_session(session.browserbase_session_id)
                    
                    # Cleanup Stagehand
                    await self.stagehand_controller.cleanup_session(session.browserbase_session_id)
                    
                    # Update status
                    session.status = "expired"
                    cleanup_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to cleanup session {session.id}: {e}")
            
            await db.commit()
            
            if cleanup_count > 0:
                logger.info(f"Cleaned up {cleanup_count} expired browser sessions")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            await db.rollback()
            raise


# Global service instance
browser_service = BrowserService()