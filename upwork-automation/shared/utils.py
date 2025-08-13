"""
Shared utility functions for the Ardan Automation System
"""
import hashlib
import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

import asyncio
from functools import wraps


def setup_logging(name: str, level: str = "INFO") -> logging.Logger:
    """Set up structured logging for a service"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def generate_content_hash(content: str) -> str:
    """Generate SHA-256 hash of content for deduplication"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """Extract keywords from text for matching and analysis"""
    # Remove special characters and convert to lowercase
    cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
    
    # Split into words and filter by length
    words = [word for word in cleaned_text.split() if len(word) >= min_length]
    
    # Remove common stop words
    stop_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'between', 'among', 'this', 'that', 'these',
        'those', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
        'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his',
        'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself',
        'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which',
        'who', 'whom', 'whose', 'this', 'that', 'these', 'those', 'am', 'is',
        'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'having', 'do', 'does', 'did', 'doing', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'can', 'shall'
    }
    
    keywords = [word for word in words if word not in stop_words]
    
    # Return unique keywords
    return list(set(keywords))


def calculate_match_score(
    job_keywords: List[str],
    target_keywords: List[str],
    job_description: str,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """Calculate job match score based on keywords and other factors"""
    if weights is None:
        weights = {
            'keyword_match': 0.4,
            'title_match': 0.3,
            'description_relevance': 0.2,
            'urgency': 0.1
        }
    
    score = 0.0
    
    # Keyword matching
    job_keywords_lower = [k.lower() for k in job_keywords]
    target_keywords_lower = [k.lower() for k in target_keywords]
    
    matches = sum(1 for keyword in target_keywords_lower if keyword in job_keywords_lower)
    keyword_score = matches / len(target_keywords_lower) if target_keywords_lower else 0
    score += keyword_score * weights['keyword_match']
    
    # Title relevance (check if target keywords appear in job title)
    title_matches = sum(1 for keyword in target_keywords_lower 
                       if keyword in job_description.lower()[:100])  # First 100 chars as title proxy
    title_score = min(title_matches / len(target_keywords_lower), 1.0) if target_keywords_lower else 0
    score += title_score * weights['title_match']
    
    # Description relevance
    description_keywords = extract_keywords(job_description)
    desc_matches = sum(1 for keyword in target_keywords_lower 
                      if keyword in description_keywords)
    desc_score = min(desc_matches / len(target_keywords_lower), 1.0) if target_keywords_lower else 0
    score += desc_score * weights['description_relevance']
    
    # Urgency indicators
    urgency_keywords = ['urgent', 'asap', 'immediately', 'rush', 'quick', 'fast']
    urgency_score = 1.0 if any(keyword in job_description.lower() for keyword in urgency_keywords) else 0.5
    score += urgency_score * weights['urgency']
    
    return min(score, 1.0)  # Cap at 1.0


def format_currency(amount: Decimal, currency: str = "USD") -> str:
    """Format currency amount for display"""
    if currency == "USD":
        return f"${amount:,.2f}"
    return f"{amount:,.2f} {currency}"


def format_rate(hourly_rate: Decimal) -> str:
    """Format hourly rate for display"""
    return f"${hourly_rate}/hr"


def calculate_bid_amount(
    job_budget_min: Optional[Decimal],
    job_budget_max: Optional[Decimal],
    target_rate: Decimal,
    min_rate: Decimal,
    competition_factor: float = 1.0
) -> Decimal:
    """Calculate optimal bid amount based on job budget and competition"""
    
    # If no budget range provided, use target rate
    if not job_budget_min and not job_budget_max:
        return target_rate
    
    # Use budget range to determine bid
    if job_budget_min and job_budget_max:
        # Bid slightly below the maximum but above our minimum
        max_bid = min(job_budget_max * Decimal('0.95'), target_rate * Decimal('1.1'))
        min_bid = max(job_budget_min, min_rate)
        
        # Adjust for competition
        if competition_factor > 1.0:  # High competition, bid lower
            bid = min_bid + (max_bid - min_bid) * Decimal('0.3')
        else:  # Low competition, bid higher
            bid = min_bid + (max_bid - min_bid) * Decimal('0.7')
        
        return max(min(bid, max_bid), min_bid)
    
    # Single budget value
    budget = job_budget_min or job_budget_max
    return max(min(budget * Decimal('0.95'), target_rate), min_rate)


def is_within_rate_limits(
    applications_today: int,
    last_application_time: Optional[datetime],
    daily_limit: int = 30,
    min_interval_minutes: int = 5
) -> tuple[bool, Optional[str]]:
    """Check if we can submit another application within rate limits"""
    
    # Check daily limit
    if applications_today >= daily_limit:
        return False, f"Daily limit of {daily_limit} applications reached"
    
    # Check time interval
    if last_application_time:
        time_since_last = datetime.utcnow() - last_application_time
        min_interval = timedelta(minutes=min_interval_minutes)
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            return False, f"Must wait {wait_time.seconds // 60} more minutes between applications"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system operations"""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(' .')
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized


def retry_async(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for async functions with exponential backoff retry logic"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        break
                    
                    wait_time = delay * (backoff ** attempt)
                    await asyncio.sleep(wait_time)
            
            raise last_exception
        
        return wrapper
    return decorator


def validate_uuid(uuid_string: str) -> bool:
    """Validate UUID string format"""
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length with suffix"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def extract_ardan_job_id(job_url: str) -> Optional[str]:
    """Extract Ardan job ID from job URL"""
    # Pattern for Ardan job URLs
    pattern = r'/jobs/([a-zA-Z0-9_-]+)'
    match = re.search(pattern, job_url)
    
    if match:
        return match.group(1)
    
    return None


def calculate_success_rate(
    total_applications: int,
    successful_applications: int
) -> Decimal:
    """Calculate success rate as a decimal"""
    if total_applications == 0:
        return Decimal('0.0')
    
    return Decimal(successful_applications) / Decimal(total_applications)


def get_time_until_next_day() -> timedelta:
    """Get time remaining until next day (for daily limit resets)"""
    now = datetime.utcnow()
    next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return next_day - now


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def can_make_call(self) -> bool:
        """Check if a call can be made within rate limits"""
        now = datetime.utcnow()
        
        # Remove old calls outside the time window
        cutoff = now - timedelta(seconds=self.time_window)
        self.calls = [call_time for call_time in self.calls if call_time > cutoff]
        
        return len(self.calls) < self.max_calls
    
    def make_call(self) -> bool:
        """Record a call if within rate limits"""
        if self.can_make_call():
            self.calls.append(datetime.utcnow())
            return True
        return False
    
    def time_until_next_call(self) -> Optional[timedelta]:
        """Get time until next call can be made"""
        if self.can_make_call():
            return None
        
        if not self.calls:
            return None
        
        oldest_call = min(self.calls)
        next_available = oldest_call + timedelta(seconds=self.time_window)
        return next_available - datetime.utcnow()