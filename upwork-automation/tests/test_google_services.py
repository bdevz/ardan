"""
Tests for Google Services Integration
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from uuid import uuid4

from api.services.google_services import (
    GoogleAuthManager,
    GoogleDocsService,
    GoogleDriveService,
    GoogleSheetsService,
    GoogleServicesManager,
    RetryHandler
)


class TestGoogleAuthManager:
    """Test Google authentication manager"""
    
    def test_init_with_service_account(self):
        """Test initialization with service account credentials"""
        with patch('api.services.google_services.settings') as mock_settings:
            mock_settings.google_service_account_file = "test_service_account.json"
            with patch('os.path.exists', return_value=True):
                with patch('api.services.google_services.ServiceAccountCredentials') as mock_creds:
                    auth_manager = GoogleAuthManager()
                    assert auth_manager.credentials is not None
    
    def test_init_with_json_credentials(self):
        """Test initialization with JSON credentials"""
        with patch('api.services.google_services.settings') as mock_settings:
            mock_settings.google_service_account_file = None
            mock_settings.google_credentials = '{"type": "service_account", "project_id": "test"}'
            
            with patch('api.services.google_services.ServiceAccountCredentials') as mock_creds:
                auth_manager = GoogleAuthManager()
                assert auth_manager.credentials is not None
    
    def test_get_credentials_refresh(self):
        """Test credential refresh functionality"""
        auth_manager = GoogleAuthManager()
        mock_creds = Mock()
        mock_creds.expired = True
        mock_creds.refresh_token = "test_token"
        auth_manager.credentials = mock_creds
        
        result = auth_manager.get_credentials()
        mock_creds.refresh.assert_called_once()
        assert result == mock_creds


class TestRetryHandler:
    """Test retry handler functionality"""
    
    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test successful execution on first attempt"""
        async def success_func():
            return "success"
        
        result = await RetryHandler.retry_with_backoff(success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_with_http_error(self):
        """Test retry with HTTP error"""
        from googleapiclient.errors import HttpError
        
        call_count = 0
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Mock HTTP error with retryable status
                mock_resp = Mock()
                mock_resp.status = 500
                raise HttpError(mock_resp, b"Server Error")
            return "success"
        
        result = await RetryHandler.retry_with_backoff(failing_func, max_retries=3)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_non_retryable_error(self):
        """Test non-retryable HTTP error"""
        from googleapiclient.errors import HttpError
        
        async def failing_func():
            mock_resp = Mock()
            mock_resp.status = 404
            raise HttpError(mock_resp, b"Not Found")
        
        with pytest.raises(HttpError):
            await RetryHandler.retry_with_backoff(failing_func, max_retries=3)


class TestGoogleDocsService:
    """Test Google Docs service functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_auth_manager = Mock()
        self.mock_auth_manager.get_credentials.return_value = Mock()
        self.docs_service = GoogleDocsService(self.mock_auth_manager)
    
    @pytest.mark.asyncio
    async def test_create_proposal_document_success(self):
        """Test successful proposal document creation"""
        mock_service = Mock()
        mock_doc = {'documentId': 'test_doc_id'}
        mock_service.documents().create().execute.return_value = mock_doc
        
        self.docs_service.service = mock_service
        
        result = await self.docs_service.create_proposal_document(
            title="Test Job",
            content="Test proposal content",
            job_id=uuid4()
        )
        
        assert result['document_id'] == 'test_doc_id'
        assert 'document_url' in result
        assert 'created_at' in result
    
    @pytest.mark.asyncio
    async def test_create_proposal_document_no_service(self):
        """Test proposal document creation without service"""
        self.docs_service.service = None
        
        result = await self.docs_service.create_proposal_document(
            title="Test Job",
            content="Test proposal content",
            job_id=uuid4()
        )
        
        assert result['document_id'].startswith('mock_doc_')
        assert 'document_url' in result
    
    @pytest.mark.asyncio
    async def test_update_proposal_document(self):
        """Test proposal document update"""
        mock_service = Mock()
        mock_doc = {
            'body': {
                'content': [
                    {'paragraph': {'endIndex': 100}}
                ]
            }
        }
        mock_service.documents().get().execute.return_value = mock_doc
        
        self.docs_service.service = mock_service
        
        result = await self.docs_service.update_proposal_document(
            document_id="test_doc_id",
            content="Updated content"
        )
        
        assert result is True
        mock_service.documents().batchUpdate.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_document_content(self):
        """Test getting document content"""
        mock_service = Mock()
        mock_doc = {
            'title': 'Test Document',
            'revisionId': 'rev123',
            'body': {
                'content': [
                    {
                        'paragraph': {
                            'elements': [
                                {
                                    'textRun': {
                                        'content': 'Test content'
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        mock_service.documents().get().execute.return_value = mock_doc
        
        self.docs_service.service = mock_service
        
        result = await self.docs_service.get_document_content("test_doc_id")
        
        assert result['content'] == 'Test content'
        assert result['title'] == 'Test Document'
        assert result['document_id'] == 'test_doc_id'


class TestGoogleDriveService:
    """Test Google Drive service functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_auth_manager = Mock()
        self.mock_auth_manager.get_credentials.return_value = Mock()
        self.drive_service = GoogleDriveService(self.mock_auth_manager)
    
    @pytest.mark.asyncio
    async def test_list_portfolio_files(self):
        """Test listing portfolio files"""
        mock_service = Mock()
        mock_files = {
            'files': [
                {
                    'id': 'file1',
                    'name': 'Salesforce Portfolio.pdf',
                    'mimeType': 'application/pdf',
                    'size': '1024000',
                    'modifiedTime': '2024-01-01T00:00:00Z'
                }
            ]
        }
        mock_service.files().list().execute.return_value = mock_files
        
        self.drive_service.service = mock_service
        
        result = await self.drive_service.list_portfolio_files()
        
        assert len(result) == 1
        assert result[0]['name'] == 'Salesforce Portfolio.pdf'
        assert result[0]['size'] == 1024000
    
    @pytest.mark.asyncio
    async def test_select_relevant_attachments(self):
        """Test selecting relevant attachments"""
        # Mock the list_portfolio_files method
        mock_files = [
            {
                'id': 'file1',
                'name': 'Salesforce_Agentforce_Portfolio.pdf',
                'mime_type': 'application/pdf',
                'size': 1024000,
                'description': 'Salesforce Agentforce case studies'
            },
            {
                'id': 'file2',
                'name': 'Generic_Document.pdf',
                'mime_type': 'application/pdf',
                'size': 512000,
                'description': 'Generic document'
            }
        ]
        
        self.drive_service.list_portfolio_files = AsyncMock(return_value=mock_files)
        
        result = await self.drive_service.select_relevant_attachments(
            job_requirements=['Salesforce', 'Agentforce'],
            job_description="Looking for Salesforce Agentforce developer"
        )
        
        assert len(result) == 1
        assert result[0]['name'] == 'Salesforce_Agentforce_Portfolio.pdf'
        assert result[0]['relevance_score'] > 0
    
    def test_calculate_relevance_score(self):
        """Test relevance score calculation"""
        score = self.drive_service._calculate_relevance_score(
            filename="Salesforce_Agentforce_Portfolio.pdf",
            requirements=["Salesforce", "Agentforce"],
            job_description="Need Salesforce Agentforce developer",
            file_description="Portfolio of Salesforce Agentforce projects"
        )
        
        assert score > 5.0  # Should have high relevance
        
        # Test low relevance
        low_score = self.drive_service._calculate_relevance_score(
            filename="Generic_Document.pdf",
            requirements=["Salesforce", "Agentforce"],
            job_description="Need Salesforce developer",
            file_description="Generic document"
        )
        
        assert low_score < score
    
    @pytest.mark.asyncio
    async def test_upload_file(self):
        """Test file upload"""
        mock_service = Mock()
        mock_file = {
            'id': 'uploaded_file_id',
            'name': 'test_file.pdf',
            'size': '1024'
        }
        mock_service.files().create().execute.return_value = mock_file
        
        self.drive_service.service = mock_service
        
        result = await self.drive_service.upload_file(
            file_content=b"test content",
            filename="test_file.pdf",
            mime_type="application/pdf"
        )
        
        assert result['file_id'] == 'uploaded_file_id'
        assert result['filename'] == 'test_file.pdf'
        assert 'uploaded_at' in result
    
    @pytest.mark.asyncio
    async def test_create_folder(self):
        """Test folder creation"""
        mock_service = Mock()
        mock_folder = {
            'id': 'folder_id',
            'name': 'Test Folder'
        }
        mock_service.files().create().execute.return_value = mock_folder
        
        self.drive_service.service = mock_service
        
        result = await self.drive_service.create_folder("Test Folder")
        
        assert result['folder_id'] == 'folder_id'
        assert result['folder_name'] == 'Test Folder'
        assert 'created_at' in result


class TestGoogleSheetsService:
    """Test Google Sheets service functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_auth_manager = Mock()
        self.mock_auth_manager.get_credentials.return_value = Mock()
        self.sheets_service = GoogleSheetsService(self.mock_auth_manager)
    
    @pytest.mark.asyncio
    async def test_export_jobs_data(self):
        """Test exporting jobs data"""
        mock_service = Mock()
        mock_service.spreadsheets().create().execute.return_value = {
            'spreadsheetId': 'test_sheet_id'
        }
        
        self.sheets_service.service = mock_service
        
        jobs_data = [
            {
                'id': 'job1',
                'title': 'Salesforce Developer',
                'client_name': 'Test Client',
                'hourly_rate': 75,
                'status': 'DISCOVERED'
            }
        ]
        
        result = await self.sheets_service.export_jobs_data(jobs_data)
        
        assert result['spreadsheet_id'] == 'test_sheet_id'
        assert result['rows_exported'] == 1
        assert 'exported_at' in result
    
    @pytest.mark.asyncio
    async def test_export_proposals_data(self):
        """Test exporting proposals data"""
        mock_service = Mock()
        mock_service.spreadsheets().create().execute.return_value = {
            'spreadsheetId': 'test_sheet_id'
        }
        
        self.sheets_service.service = mock_service
        
        proposals_data = [
            {
                'id': 'prop1',
                'job_id': 'job1',
                'job_title': 'Salesforce Developer',
                'bid_amount': 75,
                'status': 'SUBMITTED'
            }
        ]
        
        result = await self.sheets_service.export_proposals_data(proposals_data)
        
        assert result['spreadsheet_id'] == 'test_sheet_id'
        assert result['rows_exported'] == 1
    
    @pytest.mark.asyncio
    async def test_export_analytics_data(self):
        """Test exporting analytics data"""
        mock_service = Mock()
        mock_service.spreadsheets().create().execute.return_value = {
            'spreadsheetId': 'test_sheet_id'
        }
        
        self.sheets_service.service = mock_service
        
        analytics_data = {
            'total_jobs': 100,
            'total_proposals': 50,
            'success_rate': 0.15,
            'avg_bid_amount': 72.5,
            'jobs_this_week': 10,
            'proposals_this_week': 5
        }
        
        result = await self.sheets_service.export_analytics_data(analytics_data)
        
        assert result['spreadsheet_id'] == 'test_sheet_id'
        assert result['rows_exported'] > 0
    
    @pytest.mark.asyncio
    async def test_create_dashboard_spreadsheet(self):
        """Test creating dashboard spreadsheet"""
        mock_service = Mock()
        mock_service.spreadsheets().create().execute.return_value = {
            'spreadsheetId': 'dashboard_sheet_id'
        }
        
        self.sheets_service.service = mock_service
        
        result = await self.sheets_service.create_dashboard_spreadsheet()
        
        assert result['spreadsheet_id'] == 'dashboard_sheet_id'
        assert 'created_at' in result


class TestGoogleServicesManager:
    """Test Google services manager"""
    
    def test_init(self):
        """Test manager initialization"""
        manager = GoogleServicesManager()
        
        assert manager.auth_manager is not None
        assert manager.docs_service is not None
        assert manager.drive_service is not None
        assert manager.sheets_service is not None
    
    def test_get_services(self):
        """Test getting service instances"""
        manager = GoogleServicesManager()
        
        docs = manager.get_docs_service()
        drive = manager.get_drive_service()
        sheets = manager.get_sheets_service()
        
        assert isinstance(docs, GoogleDocsService)
        assert isinstance(drive, GoogleDriveService)
        assert isinstance(sheets, GoogleSheetsService)
    
    def test_get_auth_status(self):
        """Test getting authentication status"""
        manager = GoogleServicesManager()
        
        status = manager.get_auth_status()
        
        assert 'authenticated' in status
        assert 'credentials_valid' in status
        assert 'last_refresh' in status


@pytest.mark.integration
class TestGoogleServicesIntegration:
    """Integration tests for Google services (requires actual credentials)"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test full workflow: create doc, upload file, export data"""
        # This would test the full integration with real Google services
        # Only run when integration testing is enabled
        pytest.skip("Integration tests require actual Google credentials")


if __name__ == "__main__":
    pytest.main([__file__])