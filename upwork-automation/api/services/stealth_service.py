"""
Stealth Enhancement Service for Browser Automation

This service provides advanced stealth capabilities including:
- Dynamic browser fingerprinting
- Human-like interaction patterns
- Anti-detection measures
- Proxy rotation and management
"""
import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import hashlib
import base64

from shared.utils import setup_logging

logger = setup_logging("stealth-service")


class StealthLevel(Enum):
    """Stealth operation levels"""
    MINIMAL = "minimal"      # Basic stealth measures
    STANDARD = "standard"    # Standard stealth configuration
    MAXIMUM = "maximum"      # Maximum stealth with all measures


@dataclass
class MouseMovement:
    """Human-like mouse movement pattern"""
    x: int
    y: int
    duration: float
    curve_points: List[Tuple[int, int]]


@dataclass
class TypingPattern:
    """Human-like typing pattern"""
    text: str
    char_delays: List[float]
    total_duration: float
    mistakes: List[Tuple[int, str]]  # (position, correction)


@dataclass
class BrowserFingerprint:
    """Complete browser fingerprint configuration"""
    user_agent: str
    viewport: Dict[str, int]
    screen: Dict[str, int]
    timezone: str
    locale: str
    platform: str
    webgl_vendor: str
    webgl_renderer: str
    canvas_fingerprint: str
    audio_fingerprint: str
    fonts: List[str]
    plugins: List[Dict[str, str]]
    headers: Dict[str, str]
    webrtc_ips: List[str]
    battery_level: Optional[float]
    connection_type: str
    hardware_concurrency: int
    device_memory: int


class StealthService:
    """Advanced stealth enhancement service"""
    
    def __init__(self):
        self.current_fingerprints: Dict[str, BrowserFingerprint] = {}
        self.proxy_pool: List[Dict[str, str]] = []
        self.user_agent_pool: List[str] = []
        self.stealth_level = StealthLevel.STANDARD
        
        # Initialize stealth components
        self._initialize_user_agents()
        self._initialize_proxy_pool()
    
    def _initialize_user_agents(self):
        """Initialize pool of realistic user agents"""
        self.user_agent_pool = [
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            
            # Firefox
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            
            # Edge
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ]
    
    def _initialize_proxy_pool(self):
        """Initialize proxy pool (would be loaded from configuration)"""
        # In production, this would load from a proxy service
        self.proxy_pool = [
            {"type": "http", "host": "proxy1.example.com", "port": "8080"},
            {"type": "http", "host": "proxy2.example.com", "port": "8080"},
            {"type": "socks5", "host": "proxy3.example.com", "port": "1080"}
        ]
    
    async def generate_browser_fingerprint(
        self, 
        session_id: str,
        stealth_level: Optional[StealthLevel] = None
    ) -> BrowserFingerprint:
        """
        Generate comprehensive browser fingerprint for session
        """
        try:
            level = stealth_level or self.stealth_level
            
            # Select base configuration
            user_agent = random.choice(self.user_agent_pool)
            
            # Determine platform from user agent
            if "Macintosh" in user_agent:
                platform = "MacIntel"
                os_family = "macOS"
            elif "Windows" in user_agent:
                platform = "Win32"
                os_family = "Windows"
            else:
                platform = "Linux x86_64"
                os_family = "Linux"
            
            # Generate viewport and screen resolution
            common_resolutions = [
                {"width": 1920, "height": 1080},
                {"width": 1366, "height": 768},
                {"width": 1440, "height": 900},
                {"width": 1536, "height": 864},
                {"width": 1280, "height": 720},
                {"width": 1600, "height": 900}
            ]
            
            screen_res = random.choice(common_resolutions)
            viewport = {
                "width": screen_res["width"] - random.randint(0, 100),
                "height": screen_res["height"] - random.randint(100, 200)
            }
            
            # Generate WebGL fingerprint
            webgl_vendors = ["Intel Inc.", "NVIDIA Corporation", "AMD", "Apple Inc."]
            webgl_renderers = [
                "Intel Iris Pro OpenGL Engine",
                "NVIDIA GeForce GTX 1060",
                "AMD Radeon Pro 560X OpenGL Engine",
                "Apple M1 Pro"
            ]
            
            # Generate canvas fingerprint
            canvas_fingerprint = self._generate_canvas_fingerprint(session_id)
            
            # Generate audio fingerprint
            audio_fingerprint = self._generate_audio_fingerprint(session_id)
            
            # Generate font list
            fonts = self._generate_font_list(os_family)
            
            # Generate plugin list
            plugins = self._generate_plugin_list(user_agent)
            
            # Generate WebRTC IPs
            webrtc_ips = self._generate_webrtc_ips()
            
            # Generate headers
            headers = self._generate_headers(user_agent, level)
            
            fingerprint = BrowserFingerprint(
                user_agent=user_agent,
                viewport=viewport,
                screen=screen_res,
                timezone=random.choice([
                    "America/New_York", "America/Chicago", "America/Denver",
                    "America/Los_Angeles", "America/Toronto", "America/Vancouver"
                ]),
                locale=random.choice(["en-US", "en-CA", "en-GB"]),
                platform=platform,
                webgl_vendor=random.choice(webgl_vendors),
                webgl_renderer=random.choice(webgl_renderers),
                canvas_fingerprint=canvas_fingerprint,
                audio_fingerprint=audio_fingerprint,
                fonts=fonts,
                plugins=plugins,
                headers=headers,
                webrtc_ips=webrtc_ips,
                battery_level=random.uniform(0.2, 0.95) if random.random() > 0.3 else None,
                connection_type=random.choice(["wifi", "ethernet", "cellular"]),
                hardware_concurrency=random.choice([4, 8, 12, 16]),
                device_memory=random.choice([4, 8, 16, 32])
            )
            
            # Store fingerprint for session
            self.current_fingerprints[session_id] = fingerprint
            
            logger.info(f"Generated browser fingerprint for session {session_id}")
            return fingerprint
            
        except Exception as e:
            logger.error(f"Error generating browser fingerprint: {e}")
            raise
    
    def _generate_canvas_fingerprint(self, session_id: str) -> str:
        """Generate unique but consistent canvas fingerprint"""
        # Create deterministic but unique fingerprint based on session
        seed = hashlib.md5(session_id.encode()).hexdigest()
        random.seed(seed)
        
        # Generate canvas data points
        canvas_data = []
        for i in range(50):
            canvas_data.append(random.randint(0, 255))
        
        # Reset random seed
        random.seed()
        
        return base64.b64encode(bytes(canvas_data)).decode()[:32]
    
    def _generate_audio_fingerprint(self, session_id: str) -> str:
        """Generate unique but consistent audio fingerprint"""
        seed = hashlib.md5(f"audio_{session_id}".encode()).hexdigest()
        random.seed(seed)
        
        # Generate audio context fingerprint
        audio_data = [random.uniform(-1.0, 1.0) for _ in range(20)]
        
        # Reset random seed
        random.seed()
        
        return hashlib.md5(str(audio_data).encode()).hexdigest()[:16]
    
    def _generate_font_list(self, os_family: str) -> List[str]:
        """Generate realistic font list based on OS"""
        base_fonts = [
            "Arial", "Arial Black", "Comic Sans MS", "Courier New",
            "Georgia", "Helvetica", "Impact", "Times New Roman",
            "Trebuchet MS", "Verdana"
        ]
        
        os_fonts = {
            "macOS": [
                "SF Pro Display", "SF Pro Text", "Helvetica Neue",
                "Lucida Grande", "Menlo", "Monaco", "Optima",
                "Palatino", "Times", "Zapfino"
            ],
            "Windows": [
                "Segoe UI", "Segoe UI Black", "Segoe UI Light",
                "Tahoma", "Microsoft Sans Serif", "Calibri",
                "Cambria", "Consolas", "Corbel"
            ],
            "Linux": [
                "Ubuntu", "Ubuntu Mono", "DejaVu Sans",
                "DejaVu Sans Mono", "Liberation Sans",
                "Liberation Serif", "Noto Sans", "Roboto"
            ]
        }
        
        # Combine base fonts with OS-specific fonts
        all_fonts = base_fonts + os_fonts.get(os_family, [])
        
        # Add some random web fonts
        web_fonts = [
            "Open Sans", "Roboto", "Lato", "Montserrat",
            "Source Sans Pro", "Raleway", "PT Sans"
        ]
        
        # Randomly include some web fonts
        for font in web_fonts:
            if random.random() > 0.7:
                all_fonts.append(font)
        
        return sorted(list(set(all_fonts)))
    
    def _generate_plugin_list(self, user_agent: str) -> List[Dict[str, str]]:
        """Generate realistic plugin list based on browser"""
        plugins = []
        
        if "Chrome" in user_agent:
            plugins.extend([
                {"name": "Chrome PDF Plugin", "filename": "internal-pdf-viewer"},
                {"name": "Chrome PDF Viewer", "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai"},
                {"name": "Native Client", "filename": "internal-nacl-plugin"}
            ])
        
        elif "Firefox" in user_agent:
            plugins.extend([
                {"name": "PDF.js", "filename": "pdf.js"},
                {"name": "OpenH264 Video Codec", "filename": "gmpopenh264"}
            ])
        
        elif "Safari" in user_agent:
            plugins.extend([
                {"name": "WebKit built-in PDF", "filename": "WebKit built-in PDF"}
            ])
        
        # Add some common plugins randomly
        common_plugins = [
            {"name": "Widevine Content Decryption Module", "filename": "widevinecdmadapter"},
            {"name": "Shockwave Flash", "filename": "pepflashplayer"}
        ]
        
        for plugin in common_plugins:
            if random.random() > 0.5:
                plugins.append(plugin)
        
        return plugins
    
    def _generate_webrtc_ips(self) -> List[str]:
        """Generate realistic WebRTC IP addresses"""
        # Generate local network IPs
        local_ips = []
        
        # Common local network ranges
        ranges = [
            "192.168.1", "192.168.0", "10.0.0", "172.16.0"
        ]
        
        for range_prefix in ranges[:random.randint(1, 2)]:
            ip = f"{range_prefix}.{random.randint(1, 254)}"
            local_ips.append(ip)
        
        return local_ips
    
    def _generate_headers(self, user_agent: str, stealth_level: StealthLevel) -> Dict[str, str]:
        """Generate HTTP headers for stealth"""
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        if stealth_level == StealthLevel.MAXIMUM:
            # Add additional stealth headers
            headers.update({
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0"
            })
        
        return headers
    
    async def generate_human_mouse_movement(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: Optional[float] = None
    ) -> MouseMovement:
        """
        Generate human-like mouse movement pattern
        """
        try:
            # Calculate duration if not provided
            if duration is None:
                distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
                duration = max(0.5, min(2.0, distance / 500))  # Scale with distance
            
            # Generate curve points for natural movement
            curve_points = []
            num_points = max(5, int(duration * 10))
            
            for i in range(num_points):
                t = i / (num_points - 1)
                
                # Add some randomness to create natural curve
                noise_x = random.uniform(-10, 10) * (1 - abs(t - 0.5) * 2)
                noise_y = random.uniform(-10, 10) * (1 - abs(t - 0.5) * 2)
                
                # Bezier curve interpolation
                x = int(start_x + (end_x - start_x) * t + noise_x)
                y = int(start_y + (end_y - start_y) * t + noise_y)
                
                curve_points.append((x, y))
            
            return MouseMovement(
                x=end_x,
                y=end_y,
                duration=duration,
                curve_points=curve_points
            )
            
        except Exception as e:
            logger.error(f"Error generating mouse movement: {e}")
            raise
    
    async def generate_human_typing_pattern(self, text: str) -> TypingPattern:
        """
        Generate human-like typing pattern with realistic delays and mistakes
        """
        try:
            char_delays = []
            mistakes = []
            
            # Base typing speed (characters per minute)
            base_cpm = random.uniform(180, 280)  # 3-4.7 chars per second
            base_delay = 60.0 / base_cpm
            
            for i, char in enumerate(text):
                # Vary delay based on character type
                if char == ' ':
                    delay = base_delay * random.uniform(0.8, 1.2)
                elif char in '.,!?;:':
                    delay = base_delay * random.uniform(1.2, 1.8)
                elif char.isupper():
                    delay = base_delay * random.uniform(1.1, 1.5)
                elif char.isdigit():
                    delay = base_delay * random.uniform(1.0, 1.3)
                else:
                    delay = base_delay * random.uniform(0.9, 1.1)
                
                # Add occasional longer pauses (thinking)
                if random.random() < 0.05:  # 5% chance
                    delay += random.uniform(0.5, 2.0)
                
                # Add occasional mistakes
                if random.random() < 0.02 and i > 0:  # 2% chance
                    wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                    mistakes.append((i, wrong_char))
                    # Add extra delay for correction
                    delay += random.uniform(0.3, 0.8)
                
                char_delays.append(delay)
            
            total_duration = sum(char_delays)
            
            return TypingPattern(
                text=text,
                char_delays=char_delays,
                total_duration=total_duration,
                mistakes=mistakes
            )
            
        except Exception as e:
            logger.error(f"Error generating typing pattern: {e}")
            raise
    
    async def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Get random proxy from pool"""
        if not self.proxy_pool:
            return None
        
        return random.choice(self.proxy_pool)
    
    async def rotate_fingerprint(self, session_id: str) -> BrowserFingerprint:
        """Rotate fingerprint for existing session"""
        logger.info(f"Rotating fingerprint for session {session_id}")
        return await self.generate_browser_fingerprint(session_id)
    
    async def apply_stealth_measures(
        self,
        session_id: str,
        page_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply comprehensive stealth measures to browser session
        """
        try:
            fingerprint = self.current_fingerprints.get(session_id)
            if not fingerprint:
                fingerprint = await self.generate_browser_fingerprint(session_id)
            
            stealth_config = {
                "fingerprint": {
                    "userAgent": fingerprint.user_agent,
                    "viewport": fingerprint.viewport,
                    "screen": fingerprint.screen,
                    "timezone": fingerprint.timezone,
                    "locale": fingerprint.locale,
                    "platform": fingerprint.platform,
                    "webgl": {
                        "vendor": fingerprint.webgl_vendor,
                        "renderer": fingerprint.webgl_renderer
                    },
                    "canvas": fingerprint.canvas_fingerprint,
                    "audio": fingerprint.audio_fingerprint,
                    "fonts": fingerprint.fonts,
                    "plugins": fingerprint.plugins,
                    "webrtc_ips": fingerprint.webrtc_ips,
                    "battery": fingerprint.battery_level,
                    "connection": fingerprint.connection_type,
                    "hardware_concurrency": fingerprint.hardware_concurrency,
                    "device_memory": fingerprint.device_memory
                },
                "headers": fingerprint.headers,
                "proxy": await self.get_random_proxy(),
                "stealth_level": self.stealth_level.value
            }
            
            logger.info(f"Applied stealth measures for session {session_id}")
            return stealth_config
            
        except Exception as e:
            logger.error(f"Error applying stealth measures: {e}")
            return {}
    
    async def detect_anti_bot_measures(
        self,
        page_content: str,
        response_headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Detect anti-bot measures on the page
        """
        try:
            detection_results = {
                "captcha_detected": False,
                "rate_limiting": False,
                "fingerprinting_scripts": False,
                "bot_detection_services": [],
                "suspicious_headers": [],
                "risk_level": "low"
            }
            
            content_lower = page_content.lower()
            
            # Check for CAPTCHA
            captcha_indicators = [
                'recaptcha', 'hcaptcha', 'captcha', 'verify you are human',
                'security check', 'prove you are not a robot'
            ]
            
            for indicator in captcha_indicators:
                if indicator in content_lower:
                    detection_results["captcha_detected"] = True
                    break
            
            # Check for rate limiting
            rate_limit_indicators = [
                'rate limit', 'too many requests', 'slow down',
                'temporarily blocked', 'suspicious activity'
            ]
            
            for indicator in rate_limit_indicators:
                if indicator in content_lower:
                    detection_results["rate_limiting"] = True
                    break
            
            # Check for fingerprinting scripts
            fingerprinting_indicators = [
                'canvas fingerprint', 'webgl fingerprint', 'audio fingerprint',
                'font detection', 'screen resolution', 'timezone detection'
            ]
            
            for indicator in fingerprinting_indicators:
                if indicator in content_lower:
                    detection_results["fingerprinting_scripts"] = True
                    break
            
            # Check for bot detection services
            bot_detection_services = [
                'cloudflare', 'distil', 'perimeterx', 'datadome',
                'imperva', 'akamai', 'shape security'
            ]
            
            for service in bot_detection_services:
                if service in content_lower or service in str(response_headers).lower():
                    detection_results["bot_detection_services"].append(service)
            
            # Check suspicious headers
            suspicious_headers = [
                'cf-ray', 'x-distil-cs', 'x-px-authorization',
                'x-datadome-cid', 'x-akamai-edgescape'
            ]
            
            for header in suspicious_headers:
                if header.lower() in [h.lower() for h in response_headers.keys()]:
                    detection_results["suspicious_headers"].append(header)
            
            # Calculate risk level
            risk_score = 0
            if detection_results["captcha_detected"]:
                risk_score += 3
            if detection_results["rate_limiting"]:
                risk_score += 2
            if detection_results["fingerprinting_scripts"]:
                risk_score += 1
            risk_score += len(detection_results["bot_detection_services"])
            risk_score += len(detection_results["suspicious_headers"])
            
            if risk_score >= 5:
                detection_results["risk_level"] = "high"
            elif risk_score >= 2:
                detection_results["risk_level"] = "medium"
            else:
                detection_results["risk_level"] = "low"
            
            return detection_results
            
        except Exception as e:
            logger.error(f"Error detecting anti-bot measures: {e}")
            return {"risk_level": "unknown", "error": str(e)}
    
    def set_stealth_level(self, level: StealthLevel):
        """Set global stealth level"""
        self.stealth_level = level
        logger.info(f"Stealth level set to: {level.value}")
    
    def get_session_fingerprint(self, session_id: str) -> Optional[BrowserFingerprint]:
        """Get fingerprint for specific session"""
        return self.current_fingerprints.get(session_id)
    
    def clear_session_fingerprint(self, session_id: str):
        """Clear fingerprint for session"""
        if session_id in self.current_fingerprints:
            del self.current_fingerprints[session_id]
            logger.info(f"Cleared fingerprint for session {session_id}")


# Global service instance
stealth_service = StealthService()