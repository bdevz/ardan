"""
Browser automation module for Ardan automation system
"""
from .browserbase_client import BrowserbaseClient, SessionInfo, SessionConfig, SessionStatus, SessionPool
from .session_manager import SessionManager, SessionType
from .stagehand_controller import (
    StagehandController,
    ArdanJobSearchController,
    ArdanApplicationController,
    NavigationStrategy,
    ExtractionType,
    NavigationResult,
    ExtractionResult,
    InteractionResult
)
from .stagehand_error_handler import (
    StagehandErrorHandler,
    ErrorType,
    RecoveryStrategy,
    ErrorContext,
    RecoveryResult,
    with_error_handling
)
from .job_discovery_service import (
    JobDiscoveryService,
    SearchStrategy,
    FilterCriteria,
    JobDiscoveryResult,
    DeduplicationResult
)

__all__ = [
    # Browserbase components
    'BrowserbaseClient',
    'SessionInfo', 
    'SessionConfig',
    'SessionStatus',
    'SessionPool',
    
    # Session management
    'SessionManager',
    'SessionType',
    
    # Stagehand components
    'StagehandController',
    'ArdanJobSearchController', 
    'ArdanApplicationController',
    'NavigationStrategy',
    'ExtractionType',
    'NavigationResult',
    'ExtractionResult',
    'InteractionResult',
    
    # Error handling
    'StagehandErrorHandler',
    'ErrorType',
    'RecoveryStrategy', 
    'ErrorContext',
    'RecoveryResult',
    'with_error_handling',
    
    # Job discovery
    'JobDiscoveryService',
    'SearchStrategy',
    'FilterCriteria',
    'JobDiscoveryResult',
    'DeduplicationResult'
]