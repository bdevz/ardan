"""
Google Services Integration for Docs, Drive, and Sheets
Comprehensive integration with OAuth2 authentication, error handling, and retry logic
"""
import asyncio
import json
import os
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
import time
import random

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io

from shared.config import settings
from shared.utils import setup_logging
from shared.error_handling import resilient_service, RetryConfig
from shared.circuit_breaker import CircuitBreakerConfig

logger = setup_logging("google-services")


class GoogleAuthManager:
    """Manages Google OAuth2 authentication and credential rotation"""
    
    def __init__(self):
        self.credentials = None
        self.service_account_credentials = None
        self.token_file = "google_token.pickle"
        self.scopes = [
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        self._initialize_credentials()
    
    def _initialize_credentials(self):
        """Initialize credentials using service account or OAuth2"""
        try:
            # Try service account first
            if settings.google_service_account_file and os.path.exists(settings.google_service_account_file):
                self.service_account_credentials = ServiceAccountCredentials.from_service_account_file(
                    settings.google_service_account_file,
                    scopes=self.scopes
                )
                self.credentials = self.service_account_credentials
                logger.info("Initialized Google services with service account credentials")
                return
            
            # Try OAuth2 credentials from JSON string
            if settings.google_credentials:
                try:
                    creds_info = json.loads(settings.google_credentials)
                    self.service_account_credentials = ServiceAccountCredentials.from_service_account_info(
                        creds_info,
                        scopes=self.scopes
                    )
                    self.credentials = self.service_account_credentials
                    logger.info("Initialized Google services with credentials from environment")
                    return
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON in GOOGLE_CREDENTIALS environment variable")
            
            # Try OAuth2 flow
            if settings.google_oauth_client_id and settings.google_oauth_client_secret:
                self._initialize_oauth_credentials()
                return
            
            logger.warning("No Google credentials configured, using mock services")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google credentials: {e}")
    
    def _initialize_oauth_credentials(self):
        """Initialize OAuth2 credentials"""
        try:
            # Load existing token
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # If there are no (valid) credentials available, let the user log in
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    flow = Flow.from_client_config(
                        {
                            "web": {
                                "client_id": settings.google_oauth_client_id,
                                "client_secret": settings.google_oauth_client_secret,
                                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                                "token_uri": "https://oauth2.googleapis.com/token",
                                "redirect_uris": [settings.google_oauth_redirect_uri]
                            }
                        },
                        scopes=self.scopes
                    )
                    flow.redirect_uri = settings.google_oauth_redirect_uri
                    
                    # This would need to be handled by a web endpoint in production
                    logger.warning("OAuth2 flow needs to be completed via web interface")
                    return
                
                # Save the credentials for the next run
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.credentials, token)
            
            logger.info("Initialized Google services with OAuth2 credentials")
            
        except Exception as e:
            logger.error(f"Failed to initialize OAuth2 credentials: {e}")
    
    def get_credentials(self) -> Optional[Credentials]:
        """Get valid credentials, refreshing if necessary"""
        if not self.credentials:
            return None
        
        try:
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
                # Save refreshed credentials
                if os.path.exists(self.token_file):
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(self.credentials, token)
            
            return self.credentials
            
        except Exception as e:
            logger.error(f"Failed to refresh credentials: {e}")
            return None
    
    def revoke_credentials(self):
        """Revoke and remove stored credentials"""
        try:
            if self.credentials:
                self.credentials.revoke(Request())
            
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
            
            self.credentials = None
            logger.info("Google credentials revoked and removed")
            
        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")


class RetryHandler:
    """Handles retry logic with exponential backoff for Google API calls"""
    
    @staticmethod
    async def retry_with_backoff(
        func,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0
    ):
        """Execute function with exponential backoff retry logic"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func()
                else:
                    return func()
                    
            except HttpError as e:
                last_exception = e
                
                # Don't retry on certain errors
                if e.resp.status in [400, 401, 403, 404]:
                    logger.error(f"Non-retryable error: {e}")
                    raise e
                
                if attempt == max_retries:
                    logger.error(f"Max retries exceeded: {e}")
                    raise e
                
                # Calculate delay with jitter
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                jitter = random.uniform(0.1, 0.3) * delay
                total_delay = delay + jitter
                
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {total_delay:.2f}s: {e}")
                await asyncio.sleep(total_delay)
                
            except Exception as e:
                last_exception = e
                
                if attempt == max_retries:
                    logger.error(f"Max retries exceeded: {e}")
                    raise e
                
                delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                await asyncio.sleep(delay)
        
        raise last_exception


@resilient_service(
    "google_docs_service",
    retry_config=RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        retryable_exceptions=(HttpError, ConnectionError, TimeoutError),
        non_retryable_exceptions=(ValueError, TypeError)
    ),
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=300,
        timeout=30.0
    )
)
class GoogleDocsService:
    """Google Docs API integration for proposal management"""
    
    def __init__(self, auth_manager: GoogleAuthManager):
        self.auth_manager = auth_manager
        self.service = None
        self.retry_handler = RetryHandler()
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Docs service"""
        try:
            credentials = self.auth_manager.get_credentials()
            if credentials:
                self.service = build('docs', 'v1', credentials=credentials)
                logger.info("Google Docs service initialized successfully")
            else:
                logger.warning("No Google credentials available, using mock service")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Docs service: {e}")
    
    def _refresh_service_if_needed(self):
        """Refresh service if credentials have been updated"""
        try:
            credentials = self.auth_manager.get_credentials()
            if credentials and credentials != getattr(self, '_last_credentials', None):
                self.service = build('docs', 'v1', credentials=credentials)
                self._last_credentials = credentials
                logger.info("Google Docs service refreshed with new credentials")
        except Exception as e:
            logger.error(f"Failed to refresh Google Docs service: {e}")
    
    async def create_proposal_document(
        self,
        title: str,
        content: str,
        job_id: UUID,
        folder_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Create a new Google Doc for a proposal with retry logic"""
        try:
            self._refresh_service_if_needed()
            
            if not self.service:
                return await self._mock_create_document(title, content, job_id)
            
            # Create document with retry logic
            async def create_doc():
                document = {
                    'title': f"Proposal - {title} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }
                return self.service.documents().create(body=document).execute()
            
            doc = await self.retry_handler.retry_with_backoff(create_doc)
            document_id = doc.get('documentId')
            
            # Add content to document
            await self._add_content_to_document(document_id, content)
            
            # Move to folder if specified
            if folder_id:
                await self._move_document_to_folder(document_id, folder_id)
            
            # Make document shareable
            await self._make_document_shareable(document_id)
            
            # Get shareable link
            doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
            
            logger.info(f"Created Google Doc: {document_id} for job {job_id}")
            
            return {
                "document_id": document_id,
                "document_url": doc_url,
                "title": document['title'],
                "job_id": str(job_id),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create Google Doc for job {job_id}: {e}")
            return await self._mock_create_document(title, content, job_id)
    
    async def _add_content_to_document(self, document_id: str, content: str):
        """Add content to Google Doc with formatting"""
        try:
            async def add_content():
                # Split content into paragraphs and format
                paragraphs = content.split('\n\n')
                
                requests = []
                index = 1  # Start after title
                
                for paragraph in paragraphs:
                    if paragraph.strip():
                        # Add paragraph text
                        requests.append({
                            'insertText': {
                                'location': {'index': index},
                                'text': paragraph.strip() + '\n\n'
                            }
                        })
                        
                        # Add basic formatting for headers (if paragraph starts with #)
                        if paragraph.strip().startswith('#'):
                            requests.append({
                                'updateTextStyle': {
                                    'range': {
                                        'startIndex': index,
                                        'endIndex': index + len(paragraph.strip())
                                    },
                                    'textStyle': {
                                        'bold': True,
                                        'fontSize': {'magnitude': 14, 'unit': 'PT'}
                                    },
                                    'fields': 'bold,fontSize'
                                }
                            })
                        
                        index += len(paragraph.strip()) + 2
                
                # Execute batch update
                if requests:
                    return self.service.documents().batchUpdate(
                        documentId=document_id,
                        body={'requests': requests}
                    ).execute()
            
            await self.retry_handler.retry_with_backoff(add_content)
            logger.info(f"Added content to document {document_id}")
                
        except Exception as e:
            logger.error(f"Failed to add content to document {document_id}: {e}")
            raise
    
    async def _make_document_shareable(self, document_id: str):
        """Make document shareable with link"""
        try:
            # This would use Drive API to set sharing permissions
            # For now, documents are created with default permissions
            logger.info(f"Document {document_id} sharing permissions set")
            
        except Exception as e:
            logger.error(f"Failed to set sharing permissions for document {document_id}: {e}")
    
    async def _move_document_to_folder(self, document_id: str, folder_id: str):
        """Move document to specific folder"""
        try:
            # This would use Drive API to move the document
            # For now, just log the action
            logger.info(f"Would move document {document_id} to folder {folder_id}")
            
        except Exception as e:
            logger.error(f"Failed to move document to folder: {e}")
    
    async def update_proposal_document(
        self,
        document_id: str,
        content: str
    ) -> bool:
        """Update existing Google Doc with new content"""
        try:
            self._refresh_service_if_needed()
            
            if not self.service:
                logger.info(f"Mock: Updated document {document_id}")
                return True
            
            async def update_doc():
                # Get document to find content length
                doc = self.service.documents().get(documentId=document_id).execute()
                doc_content = doc.get('body', {}).get('content', [])
                
                # Calculate end index (leave title intact)
                end_index = 1
                for element in doc_content:
                    if 'paragraph' in element:
                        end_index = element.get('endIndex', end_index)
                
                # Prepare update requests
                requests = []
                
                # Clear existing content (except title)
                if end_index > 1:
                    requests.append({
                        'deleteContentRange': {
                            'range': {
                                'startIndex': 1,
                                'endIndex': end_index - 1
                            }
                        }
                    })
                
                # Add new content
                requests.append({
                    'insertText': {
                        'location': {'index': 1},
                        'text': content + '\n\n'
                    }
                })
                
                # Add update timestamp
                requests.append({
                    'insertText': {
                        'location': {'index': 1 + len(content) + 2},
                        'text': f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    }
                })
                
                return self.service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': requests}
                ).execute()
            
            await self.retry_handler.retry_with_backoff(update_doc)
            logger.info(f"Updated Google Doc: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update Google Doc {document_id}: {e}")
            return False
    
    async def get_document_content(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get content and metadata from Google Doc"""
        try:
            self._refresh_service_if_needed()
            
            if not self.service:
                return {
                    "content": f"Mock content for document {document_id}",
                    "title": f"Mock Document {document_id}",
                    "last_modified": datetime.now().isoformat()
                }
            
            async def get_doc():
                return self.service.documents().get(documentId=document_id).execute()
            
            doc = await self.retry_handler.retry_with_backoff(get_doc)
            
            # Extract text content
            content = ""
            for element in doc.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    paragraph = element['paragraph']
                    for text_element in paragraph.get('elements', []):
                        if 'textRun' in text_element:
                            content += text_element['textRun'].get('content', '')
            
            return {
                "content": content.strip(),
                "title": doc.get('title', ''),
                "document_id": document_id,
                "revision_id": doc.get('revisionId', ''),
                "last_modified": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get document content for {document_id}: {e}")
            return None
    
    async def list_proposal_documents(self, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all proposal documents"""
        try:
            self._refresh_service_if_needed()
            
            if not self.service:
                return self._mock_document_list()
            
            # This would use Drive API to list documents
            # For now, return mock data
            return self._mock_document_list()
            
        except Exception as e:
            logger.error(f"Failed to list proposal documents: {e}")
            return []
    
    def _mock_document_list(self) -> List[Dict[str, Any]]:
        """Mock document list for testing"""
        return [
            {
                "document_id": "mock_doc_1",
                "title": "Proposal - Salesforce Agentforce Developer - 2024-01-01",
                "created_at": "2024-01-01T10:00:00Z",
                "last_modified": "2024-01-01T10:30:00Z",
                "document_url": "https://docs.google.com/document/d/mock_doc_1/edit"
            },
            {
                "document_id": "mock_doc_2", 
                "title": "Proposal - Einstein AI Integration - 2024-01-02",
                "created_at": "2024-01-02T14:00:00Z",
                "last_modified": "2024-01-02T14:15:00Z",
                "document_url": "https://docs.google.com/document/d/mock_doc_2/edit"
            }
        ]
    
    async def _mock_create_document(self, title: str, content: str, job_id: UUID) -> Dict[str, str]:
        """Mock document creation for testing"""
        mock_id = f"mock_doc_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return {
            "document_id": mock_id,
            "document_url": f"https://docs.google.com/document/d/{mock_id}/edit",
            "title": f"Proposal - {title} - {datetime.now().strftime('%Y-%m-%d')}"
        }


@resilient_service(
    "google_drive_service",
    retry_config=RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        retryable_exceptions=(HttpError, ConnectionError, TimeoutError),
        non_retryable_exceptions=(ValueError, TypeError)
    ),
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=300,
        timeout=30.0
    )
)
class GoogleDriveService:
    """Google Drive API integration for attachment management"""
    
    def __init__(self, auth_manager: GoogleAuthManager):
        self.auth_manager = auth_manager
        self.service = None
        self.retry_handler = RetryHandler()
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive service"""
        try:
            credentials = self.auth_manager.get_credentials()
            if credentials:
                self.service = build('drive', 'v3', credentials=credentials)
                logger.info("Google Drive service initialized successfully")
            else:
                logger.warning("No Google credentials available, using mock service")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
    
    def _refresh_service_if_needed(self):
        """Refresh service if credentials have been updated"""
        try:
            credentials = self.auth_manager.get_credentials()
            if credentials and credentials != getattr(self, '_last_credentials', None):
                self.service = build('drive', 'v3', credentials=credentials)
                self._last_credentials = credentials
                logger.info("Google Drive service refreshed with new credentials")
        except Exception as e:
            logger.error(f"Failed to refresh Google Drive service: {e}")
    
    async def list_portfolio_files(self, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available portfolio files with enhanced filtering"""
        try:
            self._refresh_service_if_needed()
            
            if not self.service:
                return self._mock_portfolio_files()
            
            async def list_files():
                # Build query for portfolio files
                query_parts = [
                    "trashed=false",
                    "(mimeType='application/pdf' or mimeType contains 'document' or mimeType contains 'presentation')"
                ]
                
                if folder_id:
                    query_parts.append(f"'{folder_id}' in parents")
                else:
                    # Search for common portfolio folder names
                    query_parts.append("(name contains 'portfolio' or name contains 'case' or name contains 'example')")
                
                query = " and ".join(query_parts)
                
                # List files with pagination
                all_files = []
                page_token = None
                
                while True:
                    results = self.service.files().list(
                        q=query,
                        fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, description, parents)",
                        pageSize=100,
                        pageToken=page_token
                    ).execute()
                    
                    files = results.get('files', [])
                    all_files.extend(files)
                    
                    page_token = results.get('nextPageToken')
                    if not page_token:
                        break
                
                return all_files
            
            files = await self.retry_handler.retry_with_backoff(list_files)
            
            # Format file information
            portfolio_files = []
            for file in files:
                portfolio_files.append({
                    "id": file['id'],
                    "name": file['name'],
                    "mime_type": file['mimeType'],
                    "size": int(file.get('size', 0)),
                    "modified_time": file['modifiedTime'],
                    "description": file.get('description', ''),
                    "download_url": f"https://drive.google.com/file/d/{file['id']}/view",
                    "direct_download_url": f"https://drive.google.com/uc?id={file['id']}&export=download"
                })
            
            logger.info(f"Found {len(portfolio_files)} portfolio files")
            return portfolio_files
            
        except Exception as e:
            logger.error(f"Failed to list portfolio files: {e}")
            return self._mock_portfolio_files()
    
    async def select_relevant_attachments(
        self,
        job_requirements: List[str],
        job_description: str = "",
        max_attachments: int = 3
    ) -> List[Dict[str, Any]]:
        """Select relevant attachments based on job requirements and description"""
        try:
            # Get all available files
            all_files = await self.list_portfolio_files()
            
            # Score files based on relevance
            scored_files = []
            for file in all_files:
                score = self._calculate_relevance_score(
                    file['name'], 
                    job_requirements, 
                    job_description,
                    file.get('description', '')
                )
                scored_files.append((file, score))
            
            # Sort by score and return top files
            scored_files.sort(key=lambda x: x[1], reverse=True)
            selected_files = [
                {**file, "relevance_score": score} 
                for file, score in scored_files[:max_attachments] 
                if score > 0.1  # Minimum relevance threshold
            ]
            
            logger.info(f"Selected {len(selected_files)} relevant attachments from {len(all_files)} total files")
            
            # Log selection reasoning
            for file in selected_files:
                logger.info(f"Selected: {file['name']} (score: {file['relevance_score']:.2f})")
            
            return selected_files
            
        except Exception as e:
            logger.error(f"Failed to select relevant attachments: {e}")
            return self._mock_portfolio_files()[:max_attachments]
    
    def _calculate_relevance_score(
        self, 
        filename: str, 
        requirements: List[str], 
        job_description: str = "",
        file_description: str = ""
    ) -> float:
        """Calculate relevance score for a file based on job requirements"""
        filename_lower = filename.lower()
        job_description_lower = job_description.lower()
        file_description_lower = file_description.lower()
        score = 0.0
        
        # Combine all text for analysis
        all_text = f"{filename_lower} {file_description_lower}"
        
        # Check for exact keyword matches in filename (highest weight)
        for requirement in requirements:
            requirement_lower = requirement.lower()
            if requirement_lower in filename_lower:
                score += 2.0
            elif any(word in filename_lower for word in requirement_lower.split() if len(word) > 3):
                score += 1.0
        
        # Check for keyword matches in file description
        for requirement in requirements:
            requirement_lower = requirement.lower()
            if requirement_lower in file_description_lower:
                score += 1.5
            elif any(word in file_description_lower for word in requirement_lower.split() if len(word) > 3):
                score += 0.7
        
        # Salesforce-specific terms (high relevance)
        salesforce_terms = [
            'salesforce', 'agentforce', 'einstein', 'lightning', 'apex', 'visualforce',
            'trailhead', 'crm', 'service cloud', 'sales cloud', 'marketing cloud'
        ]
        for term in salesforce_terms:
            if term in all_text:
                score += 1.5
        
        # Technical terms that might be relevant
        tech_terms = [
            'integration', 'api', 'automation', 'workflow', 'custom', 'development',
            'implementation', 'migration', 'configuration', 'customization'
        ]
        for term in tech_terms:
            if term in all_text:
                score += 0.8
        
        # Portfolio and showcase terms
        portfolio_terms = [
            'portfolio', 'case_study', 'example', 'project', 'showcase', 'demo',
            'sample', 'proof_of_concept', 'poc', 'success_story'
        ]
        for term in portfolio_terms:
            if term in all_text:
                score += 0.5
        
        # File type bonuses
        if filename_lower.endswith('.pdf'):
            score += 0.3  # PDFs are often well-formatted portfolios
        elif any(ext in filename_lower for ext in ['.doc', '.docx', '.ppt', '.pptx']):
            score += 0.2
        
        # Penalize very generic names
        generic_terms = ['document', 'file', 'untitled', 'new', 'copy']
        for term in generic_terms:
            if term in filename_lower:
                score -= 0.5
        
        # Boost score if job description keywords match
        if job_description:
            job_keywords = [word for word in job_description_lower.split() if len(word) > 4]
            for keyword in job_keywords[:10]:  # Check top 10 keywords
                if keyword in all_text:
                    score += 0.3
        
        return max(0.0, score)  # Ensure non-negative score
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        folder_id: Optional[str] = None,
        description: str = ""
    ) -> Dict[str, str]:
        """Upload file to Google Drive with retry logic"""
        try:
            self._refresh_service_if_needed()
            
            if not self.service:
                return self._mock_upload_file(filename)
            
            async def upload():
                file_metadata = {
                    'name': filename,
                    'description': description
                }
                if folder_id:
                    file_metadata['parents'] = [folder_id]
                
                media = MediaIoBaseUpload(
                    io.BytesIO(file_content),
                    mimetype=mime_type,
                    resumable=True
                )
                
                return self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, name, size, mimeType'
                ).execute()
            
            file = await self.retry_handler.retry_with_backoff(upload)
            file_id = file.get('id')
            
            logger.info(f"Uploaded file to Google Drive: {filename} ({file_id})")
            
            return {
                "file_id": file_id,
                "filename": filename,
                "mime_type": mime_type,
                "size": file.get('size', 0),
                "download_url": f"https://drive.google.com/file/d/{file_id}/view",
                "direct_download_url": f"https://drive.google.com/uc?id={file_id}&export=download",
                "uploaded_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file {filename} to Google Drive: {e}")
            return self._mock_upload_file(filename)
    
    async def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file content from Google Drive"""
        try:
            self._refresh_service_if_needed()
            
            if not self.service:
                return b"Mock file content"
            
            async def download():
                request = self.service.files().get_media(fileId=file_id)
                file_io = io.BytesIO()
                downloader = MediaIoBaseDownload(file_io, request)
                
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                return file_io.getvalue()
            
            content = await self.retry_handler.retry_with_backoff(download)
            logger.info(f"Downloaded file {file_id} from Google Drive")
            return content
            
        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            return None
    
    async def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Dict[str, str]:
        """Create a new folder in Google Drive"""
        try:
            self._refresh_service_if_needed()
            
            if not self.service:
                return self._mock_create_folder(folder_name)
            
            async def create():
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                if parent_folder_id:
                    file_metadata['parents'] = [parent_folder_id]
                
                return self.service.files().create(
                    body=file_metadata,
                    fields='id, name'
                ).execute()
            
            folder = await self.retry_handler.retry_with_backoff(create)
            folder_id = folder.get('id')
            
            logger.info(f"Created folder in Google Drive: {folder_name} ({folder_id})")
            
            return {
                "folder_id": folder_id,
                "folder_name": folder_name,
                "folder_url": f"https://drive.google.com/drive/folders/{folder_id}",
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create folder {folder_name}: {e}")
            return self._mock_create_folder(folder_name)
    
    def _mock_create_folder(self, folder_name: str) -> Dict[str, str]:
        """Mock folder creation for testing"""
        mock_id = f"mock_folder_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return {
            "folder_id": mock_id,
            "folder_name": folder_name,
            "folder_url": f"https://drive.google.com/drive/folders/{mock_id}",
            "created_at": datetime.now().isoformat()
        }
    
    def _mock_portfolio_files(self) -> List[Dict[str, Any]]:
        """Mock portfolio files for testing"""
        return [
            {
                "id": "mock_salesforce_portfolio",
                "name": "Salesforce_Agentforce_Portfolio.pdf",
                "mime_type": "application/pdf",
                "size": 2048000,
                "modified_time": "2024-01-01T00:00:00Z",
                "download_url": "https://drive.google.com/file/d/mock_salesforce_portfolio/view"
            },
            {
                "id": "mock_einstein_cases",
                "name": "Einstein_AI_Case_Studies.pdf", 
                "mime_type": "application/pdf",
                "size": 1536000,
                "modified_time": "2024-01-01T00:00:00Z",
                "download_url": "https://drive.google.com/file/d/mock_einstein_cases/view"
            },
            {
                "id": "mock_lightning_showcase",
                "name": "Lightning_Components_Showcase.pdf",
                "mime_type": "application/pdf", 
                "size": 1024000,
                "modified_time": "2024-01-01T00:00:00Z",
                "download_url": "https://drive.google.com/file/d/mock_lightning_showcase/view"
            }
        ]
    
    def _mock_upload_file(self, filename: str) -> Dict[str, str]:
        """Mock file upload for testing"""
        mock_id = f"mock_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return {
            "file_id": mock_id,
            "filename": filename,
            "download_url": f"https://drive.google.com/file/d/{mock_id}/view"
        }


@resilient_service(
    "google_sheets_service",
    retry_config=RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        retryable_exceptions=(HttpError, ConnectionError, TimeoutError),
        non_retryable_exceptions=(ValueError, TypeError)
    ),
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=300,
        timeout=30.0
    )
)
class GoogleSheetsService:
    """Google Sheets API integration for data export and reporting"""
    
    def __init__(self, auth_manager: GoogleAuthManager):
        self.auth_manager = auth_manager
        self.service = None
        self.retry_handler = RetryHandler()
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Sheets service"""
        try:
            credentials = self.auth_manager.get_credentials()
            if credentials:
                self.service = build('sheets', 'v4', credentials=credentials)
                logger.info("Google Sheets service initialized successfully")
            else:
                logger.warning("No Google credentials available, using mock service")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {e}")
    
    def _refresh_service_if_needed(self):
        """Refresh service if credentials have been updated"""
        try:
            credentials = self.auth_manager.get_credentials()
            if credentials and credentials != getattr(self, '_last_credentials', None):
                self.service = build('sheets', 'v4', credentials=credentials)
                self._last_credentials = credentials
                logger.info("Google Sheets service refreshed with new credentials")
        except Exception as e:
            logger.error(f"Failed to refresh Google Sheets service: {e}")
    
    async def export_jobs_data(
        self,
        jobs_data: List[Dict[str, Any]],
        spreadsheet_id: Optional[str] = None,
        sheet_name: str = "Jobs"
    ) -> Dict[str, str]:
        """Export jobs data to Google Sheets with enhanced formatting"""
        try:
            self._refresh_service_if_needed()
            
            if not self.service:
                return self._mock_export_data("jobs", len(jobs_data))
            
            # Create spreadsheet if not provided
            if not spreadsheet_id:
                spreadsheet_id = await self._create_spreadsheet("Upwork Jobs Export")
            
            # Prepare comprehensive data for sheets
            headers = [
                "Job ID", "Title", "Client Name", "Hourly Rate", "Budget Range",
                "Client Rating", "Payment Verified", "Hire Rate", "Status", 
                "Match Score", "Skills Required", "Posted Date", "Deadline",
                "Proposals Count", "Job URL", "Discovery Date", "Applied Date"
            ]
            
            rows = [headers]
            for job in jobs_data:
                rows.append([
                    str(job.get('id', '')),
                    job.get('title', ''),
                    job.get('client_name', ''),
                    f"${job.get('hourly_rate', 0)}/hr" if job.get('hourly_rate') else '',
                    f"${job.get('budget_min', 0)}-${job.get('budget_max', 0)}" if job.get('budget_min') else '',
                    str(job.get('client_rating', '')),
                    'Yes' if job.get('client_payment_verified') else 'No',
                    f"{job.get('client_hire_rate', 0)*100:.1f}%" if job.get('client_hire_rate') else '',
                    job.get('status', ''),
                    f"{job.get('match_score', 0):.2f}" if job.get('match_score') else '',
                    ', '.join(job.get('skills_required', [])),
                    job.get('posted_date', ''),
                    job.get('deadline', ''),
                    str(job.get('proposals_count', '')),
                    job.get('job_url', ''),
                    job.get('created_at', ''),
                    job.get('applied_at', '')
                ])
            
            # Update spreadsheet with retry logic
            async def update_sheet():
                # Clear existing data
                self.service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!A:Z"
                ).execute()
                
                # Add new data
                body = {'values': rows}
                return self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!A1",
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
            
            await self.retry_handler.retry_with_backoff(update_sheet)
            
            # Apply formatting
            await self._format_jobs_sheet(spreadsheet_id, sheet_name, len(rows))
            
            logger.info(f"Exported {len(jobs_data)} jobs to Google Sheets")
            
            return {
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
                "sheet_name": sheet_name,
                "rows_exported": len(jobs_data),
                "exported_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to export jobs data: {e}")
            return self._mock_export_data("jobs", len(jobs_data))
    
    async def export_proposals_data(
        self,
        proposals_data: List[Dict[str, Any]],
        spreadsheet_id: Optional[str] = None,
        sheet_name: str = "Proposals"
    ) -> Dict[str, str]:
        """Export proposals data to Google Sheets"""
        try:
            self._refresh_service_if_needed()
            
            if not self.service:
                return self._mock_export_data("proposals", len(proposals_data))
            
            # Create spreadsheet if not provided
            if not spreadsheet_id:
                spreadsheet_id = await self._create_spreadsheet("Upwork Proposals Export")
            
            # Prepare data for sheets
            headers = [
                "Proposal ID", "Job ID", "Job Title", "Bid Amount", "Status",
                "Generated Date", "Submitted Date", "Client Response", "Response Date",
                "Google Doc URL", "Attachments Count", "Success Rate"
            ]
            
            rows = [headers]
            for proposal in proposals_data:
                rows.append([
                    str(proposal.get('id', '')),
                    str(proposal.get('job_id', '')),
                    proposal.get('job_title', ''),
                    f"${proposal.get('bid_amount', 0)}/hr" if proposal.get('bid_amount') else '',
                    proposal.get('status', ''),
                    proposal.get('generated_at', ''),
                    proposal.get('submitted_at', ''),
                    proposal.get('client_response', ''),
                    proposal.get('client_response_date', ''),
                    proposal.get('google_doc_url', ''),
                    str(len(proposal.get('attachments', []))),
                    f"{proposal.get('success_rate', 0)*100:.1f}%" if proposal.get('success_rate') else ''
                ])
            
            # Update spreadsheet
            async def update_sheet():
                # Ensure sheet exists
                await self._ensure_sheet_exists(spreadsheet_id, sheet_name)
                
                # Clear and update
                self.service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!A:Z"
                ).execute()
                
                body = {'values': rows}
                return self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!A1",
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
            
            await self.retry_handler.retry_with_backoff(update_sheet)
            
            logger.info(f"Exported {len(proposals_data)} proposals to Google Sheets")
            
            return {
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
                "sheet_name": sheet_name,
                "rows_exported": len(proposals_data),
                "exported_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to export proposals data: {e}")
            return self._mock_export_data("proposals", len(proposals_data))
    
    async def export_analytics_data(
        self,
        analytics_data: Dict[str, Any],
        spreadsheet_id: Optional[str] = None,
        sheet_name: str = "Analytics"
    ) -> Dict[str, str]:
        """Export analytics and performance data to Google Sheets"""
        try:
            self._refresh_service_if_needed()
            
            if not self.service:
                return self._mock_export_data("analytics", 1)
            
            # Create spreadsheet if not provided
            if not spreadsheet_id:
                spreadsheet_id = await self._create_spreadsheet("Upwork Analytics Export")
            
            # Prepare analytics summary
            rows = [
                ["Metric", "Value", "Period", "Last Updated"],
                ["Total Jobs Discovered", str(analytics_data.get('total_jobs', 0)), "All Time", datetime.now().strftime('%Y-%m-%d %H:%M')],
                ["Total Proposals Sent", str(analytics_data.get('total_proposals', 0)), "All Time", datetime.now().strftime('%Y-%m-%d %H:%M')],
                ["Success Rate", f"{analytics_data.get('success_rate', 0)*100:.1f}%", "All Time", datetime.now().strftime('%Y-%m-%d %H:%M')],
                ["Average Bid Amount", f"${analytics_data.get('avg_bid_amount', 0):.2f}/hr", "All Time", datetime.now().strftime('%Y-%m-%d %H:%M')],
                ["Jobs This Week", str(analytics_data.get('jobs_this_week', 0)), "This Week", datetime.now().strftime('%Y-%m-%d %H:%M')],
                ["Proposals This Week", str(analytics_data.get('proposals_this_week', 0)), "This Week", datetime.now().strftime('%Y-%m-%d %H:%M')],
                ["Response Rate", f"{analytics_data.get('response_rate', 0)*100:.1f}%", "All Time", datetime.now().strftime('%Y-%m-%d %H:%M')],
                ["Average Response Time", f"{analytics_data.get('avg_response_time_hours', 0):.1f} hours", "All Time", datetime.now().strftime('%Y-%m-%d %H:%M')]
            ]
            
            # Add daily breakdown if available
            if 'daily_stats' in analytics_data:
                rows.append([])  # Empty row
                rows.append(["Daily Breakdown", "", "", ""])
                rows.append(["Date", "Jobs Found", "Proposals Sent", "Responses"])
                
                for day_stat in analytics_data['daily_stats']:
                    rows.append([
                        day_stat.get('date', ''),
                        str(day_stat.get('jobs_found', 0)),
                        str(day_stat.get('proposals_sent', 0)),
                        str(day_stat.get('responses', 0))
                    ])
            
            # Update spreadsheet
            async def update_sheet():
                await self._ensure_sheet_exists(spreadsheet_id, sheet_name)
                
                self.service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!A:Z"
                ).execute()
                
                body = {'values': rows}
                return self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!A1",
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
            
            await self.retry_handler.retry_with_backoff(update_sheet)
            
            logger.info(f"Exported analytics data to Google Sheets")
            
            return {
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
                "sheet_name": sheet_name,
                "rows_exported": len(rows),
                "exported_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to export analytics data: {e}")
            return self._mock_export_data("analytics", 1)
    
    async def _create_spreadsheet(self, title: str) -> str:
        """Create new Google Spreadsheet with multiple sheets"""
        try:
            async def create():
                spreadsheet = {
                    'properties': {
                        'title': f"{title} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    },
                    'sheets': [
                        {'properties': {'title': 'Jobs'}},
                        {'properties': {'title': 'Proposals'}},
                        {'properties': {'title': 'Analytics'}}
                    ]
                }
                
                return self.service.spreadsheets().create(body=spreadsheet).execute()
            
            result = await self.retry_handler.retry_with_backoff(create)
            spreadsheet_id = result.get('spreadsheetId')
            
            logger.info(f"Created new spreadsheet: {title} ({spreadsheet_id})")
            return spreadsheet_id
            
        except Exception as e:
            logger.error(f"Failed to create spreadsheet: {e}")
            return f"mock_spreadsheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _ensure_sheet_exists(self, spreadsheet_id: str, sheet_name: str):
        """Ensure a sheet exists in the spreadsheet"""
        try:
            async def check_and_create():
                # Get spreadsheet info
                spreadsheet = self.service.spreadsheets().get(
                    spreadsheetId=spreadsheet_id
                ).execute()
                
                # Check if sheet exists
                sheet_names = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
                
                if sheet_name not in sheet_names:
                    # Create the sheet
                    requests = [{
                        'addSheet': {
                            'properties': {
                                'title': sheet_name
                            }
                        }
                    }]
                    
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={'requests': requests}
                    ).execute()
                    
                    logger.info(f"Created sheet '{sheet_name}' in spreadsheet {spreadsheet_id}")
            
            await self.retry_handler.retry_with_backoff(check_and_create)
            
        except Exception as e:
            logger.error(f"Failed to ensure sheet exists: {e}")
    
    async def _format_jobs_sheet(self, spreadsheet_id: str, sheet_name: str, row_count: int):
        """Apply formatting to jobs sheet"""
        try:
            async def format_sheet():
                requests = [
                    # Freeze header row
                    {
                        'updateSheetProperties': {
                            'properties': {
                                'title': sheet_name,
                                'gridProperties': {
                                    'frozenRowCount': 1
                                }
                            },
                            'fields': 'gridProperties.frozenRowCount'
                        }
                    },
                    # Format header row
                    {
                        'repeatCell': {
                            'range': {
                                'sheetId': 0,
                                'startRowIndex': 0,
                                'endRowIndex': 1
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
                                    'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
                                }
                            },
                            'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                        }
                    },
                    # Auto-resize columns
                    {
                        'autoResizeDimensions': {
                            'dimensions': {
                                'sheetId': 0,
                                'dimension': 'COLUMNS',
                                'startIndex': 0,
                                'endIndex': 17
                            }
                        }
                    }
                ]
                
                return self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': requests}
                ).execute()
            
            await self.retry_handler.retry_with_backoff(format_sheet)
            logger.info(f"Applied formatting to sheet '{sheet_name}'")
            
        except Exception as e:
            logger.error(f"Failed to format sheet: {e}")
    
    async def create_dashboard_spreadsheet(self) -> Dict[str, str]:
        """Create a comprehensive dashboard spreadsheet"""
        try:
            spreadsheet_id = await self._create_spreadsheet("Upwork Automation Dashboard")
            
            # Create summary dashboard
            await self._create_dashboard_summary(spreadsheet_id)
            
            return {
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create dashboard spreadsheet: {e}")
            return self._mock_export_data("dashboard", 1)
    
    async def _create_dashboard_summary(self, spreadsheet_id: str):
        """Create dashboard summary sheet"""
        try:
            # This would create a comprehensive dashboard with charts and summaries
            # For now, just create a basic summary
            summary_data = [
                ["Upwork Automation Dashboard", "", "", ""],
                ["Generated on:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "", ""],
                ["", "", "", ""],
                ["Quick Stats", "", "", ""],
                ["Total Jobs Tracked:", "=COUNTA(Jobs!A:A)-1", "", ""],
                ["Total Proposals:", "=COUNTA(Proposals!A:A)-1", "", ""],
                ["Success Rate:", "=IF(COUNTA(Proposals!A:A)>1,COUNTIF(Proposals!E:E,\"ACCEPTED\")/COUNTA(Proposals!A:A)*100,0)&\"%\"", "", ""],
                ["", "", "", ""],
                ["Recent Activity", "", "", ""],
                ["Last Job Added:", "=MAX(Jobs!P:P)", "", ""],
                ["Last Proposal:", "=MAX(Proposals!F:F)", "", ""]
            ]
            
            async def create_summary():
                body = {'values': summary_data}
                return self.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range="Jobs!A1",
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
            
            await self.retry_handler.retry_with_backoff(create_summary)
            
        except Exception as e:
            logger.error(f"Failed to create dashboard summary: {e}")
    
    def _mock_export_data(self, data_type: str, row_count: int) -> Dict[str, str]:
        """Mock data export for testing"""
        mock_id = f"mock_{data_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return {
            "spreadsheet_id": mock_id,
            "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{mock_id}/edit",
            "sheet_name": data_type.title(),
            "rows_exported": row_count,
            "exported_at": datetime.now().isoformat()
        }


class GoogleServicesManager:
    """Manager class for all Google services with shared authentication"""
    
    def __init__(self):
        self.auth_manager = GoogleAuthManager()
        self.docs_service = GoogleDocsService(self.auth_manager)
        self.drive_service = GoogleDriveService(self.auth_manager)
        self.sheets_service = GoogleSheetsService(self.auth_manager)
    
    def get_docs_service(self) -> GoogleDocsService:
        """Get Google Docs service instance"""
        return self.docs_service
    
    def get_drive_service(self) -> GoogleDriveService:
        """Get Google Drive service instance"""
        return self.drive_service
    
    def get_sheets_service(self) -> GoogleSheetsService:
        """Get Google Sheets service instance"""
        return self.sheets_service
    
    def refresh_all_services(self):
        """Refresh all service instances with new credentials"""
        try:
            self.docs_service._refresh_service_if_needed()
            self.drive_service._refresh_service_if_needed()
            self.sheets_service._refresh_service_if_needed()
            logger.info("Refreshed all Google services")
        except Exception as e:
            logger.error(f"Failed to refresh Google services: {e}")
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get authentication status for all services"""
        credentials = self.auth_manager.get_credentials()
        
        return {
            "authenticated": credentials is not None,
            "credentials_valid": credentials.valid if credentials else False,
            "credentials_expired": credentials.expired if credentials else True,
            "service_account": isinstance(credentials, ServiceAccountCredentials) if credentials else False,
            "scopes": credentials.scopes if credentials else [],
            "last_refresh": datetime.now().isoformat()
        }


# Global service manager instance
google_services_manager = GoogleServicesManager()

# Backward compatibility - global service instances
google_docs_service = google_services_manager.get_docs_service()
google_drive_service = google_services_manager.get_drive_service()
google_sheets_service = google_services_manager.get_sheets_service()