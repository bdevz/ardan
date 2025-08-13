# Google Services Integration

This document describes the comprehensive Google services integration for the Upwork Automation System, including Google Docs, Google Drive, and Google Sheets functionality.

## Overview

The Google services integration provides:

- **Google Docs**: Automated proposal document creation and management
- **Google Drive**: Portfolio file management and intelligent attachment selection
- **Google Sheets**: Data export, reporting, and analytics dashboards
- **OAuth2 Authentication**: Secure authentication with credential rotation
- **Error Handling**: Comprehensive retry logic and fallback mechanisms

## Features

### Google Docs Integration

- ✅ Create proposal documents with formatted content
- ✅ Update existing documents with new content
- ✅ Retrieve document content and metadata
- ✅ List all proposal documents
- ✅ Automatic document sharing and permissions

### Google Drive Integration

- ✅ List portfolio files with advanced filtering
- ✅ Intelligent attachment selection based on job requirements
- ✅ File upload with metadata and folder organization
- ✅ File download and content retrieval
- ✅ Folder creation and management
- ✅ Relevance scoring algorithm for attachment selection

### Google Sheets Integration

- ✅ Export jobs data with comprehensive formatting
- ✅ Export proposals data with status tracking
- ✅ Export analytics data with performance metrics
- ✅ Create dashboard spreadsheets with charts
- ✅ Multi-sheet workbooks with automatic formatting
- ✅ Real-time data updates and synchronization

### Authentication & Security

- ✅ Service account authentication
- ✅ OAuth2 flow support
- ✅ Automatic credential refresh
- ✅ Credential rotation and management
- ✅ Secure token storage

### Error Handling & Reliability

- ✅ Exponential backoff retry logic
- ✅ HTTP error classification and handling
- ✅ Fallback to mock services for development
- ✅ Comprehensive logging and monitoring
- ✅ Rate limiting and quota management

## Setup and Configuration

### 1. Service Account Setup (Recommended)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the required APIs:
   - Google Docs API
   - Google Drive API
   - Google Sheets API
4. Create a service account:
   - Go to IAM & Admin > Service Accounts
   - Click "Create Service Account"
   - Download the JSON key file
5. Share your Google Drive folder with the service account email

### 2. Environment Configuration

```bash
# Service Account (Recommended)
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service-account.json

# Or JSON credentials directly
GOOGLE_CREDENTIALS='{"type": "service_account", "project_id": "your-project"...}'

# OAuth2 (Alternative)
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Optional settings
GOOGLE_DRIVE_FOLDER_ID=your-portfolio-folder-id
GOOGLE_SHEETS_EXPORT_ENABLED=true
```

### 3. Required Scopes

The integration requires the following OAuth2 scopes:

- `https://www.googleapis.com/auth/documents` - Google Docs access
- `https://www.googleapis.com/auth/drive` - Google Drive access
- `https://www.googleapis.com/auth/spreadsheets` - Google Sheets access

## Usage Examples

### Basic Usage

```python
from api.services.google_services import google_services_manager

# Get service instances
docs_service = google_services_manager.get_docs_service()
drive_service = google_services_manager.get_drive_service()
sheets_service = google_services_manager.get_sheets_service()

# Create a proposal document
doc_result = await docs_service.create_proposal_document(
    title="Salesforce Agentforce Developer",
    content="Your proposal content here...",
    job_id=uuid4()
)

# Select relevant attachments
attachments = await drive_service.select_relevant_attachments(
    job_requirements=["Salesforce", "Agentforce"],
    job_description="Looking for Salesforce developer...",
    max_attachments=3
)

# Export data to sheets
export_result = await sheets_service.export_jobs_data(jobs_data)
```

### API Endpoints

The integration provides REST API endpoints:

```bash
# Authentication
GET /api/google/auth/status
POST /api/google/auth/refresh

# Google Docs
POST /api/google/docs/create
PUT /api/google/docs/{document_id}
GET /api/google/docs/{document_id}
GET /api/google/docs

# Google Drive
GET /api/google/drive/portfolio
POST /api/google/drive/select-attachments
POST /api/google/drive/upload
GET /api/google/drive/download/{file_id}
POST /api/google/drive/create-folder

# Google Sheets
POST /api/google/sheets/export/jobs
POST /api/google/sheets/export/proposals
POST /api/google/sheets/export/analytics
POST /api/google/sheets/create-dashboard

# Testing
POST /api/google/test-integration
```

### Complete Workflow Example

```python
async def complete_workflow_example():
    """Example of complete Google services workflow"""
    
    # 1. Create proposal document
    doc_result = await docs_service.create_proposal_document(
        title="Senior Salesforce Developer",
        content=generate_proposal_content(job_data),
        job_id=job_data['id']
    )
    
    # 2. Select relevant attachments
    attachments = await drive_service.select_relevant_attachments(
        job_requirements=job_data['skills_required'],
        job_description=job_data['description']
    )
    
    # 3. Export application data
    application_data = {
        'job_id': job_data['id'],
        'proposal_doc_id': doc_result['document_id'],
        'attachments': [a['name'] for a in attachments],
        'status': 'READY_FOR_SUBMISSION'
    }
    
    export_result = await sheets_service.export_jobs_data([application_data])
    
    return {
        'document': doc_result,
        'attachments': attachments,
        'export': export_result
    }
```

## Intelligent Attachment Selection

The system includes an advanced relevance scoring algorithm for selecting the most appropriate portfolio files:

### Scoring Factors

1. **Exact Keyword Matches** (Weight: 2.0)
   - Direct matches in filename get highest priority
   
2. **Partial Keyword Matches** (Weight: 1.0)
   - Word matches in filename or description
   
3. **Salesforce-Specific Terms** (Weight: 1.5)
   - Salesforce, Agentforce, Einstein, Lightning, etc.
   
4. **Technical Terms** (Weight: 0.8)
   - Integration, API, automation, workflow, etc.
   
5. **Portfolio Terms** (Weight: 0.5)
   - Portfolio, case study, example, showcase, etc.
   
6. **File Type Bonuses** (Weight: 0.3)
   - PDFs get preference for professional presentation
   
7. **Job Description Matching** (Weight: 0.3)
   - Keywords from job description boost relevance

### Example Scoring

```python
# High relevance file
"Salesforce_Agentforce_Portfolio.pdf" + "Agentforce case studies"
# Score: 2.0 (exact) + 1.5 (Salesforce) + 1.5 (Agentforce) + 0.5 (portfolio) + 0.3 (PDF) = 5.8

# Medium relevance file  
"Lightning_Components_Demo.pptx" + "Lightning development examples"
# Score: 1.5 (Lightning) + 0.8 (development) + 0.5 (demo) + 0.2 (pptx) = 3.0

# Low relevance file
"Generic_Document.pdf" + "General information"
# Score: 0.3 (PDF) - 0.5 (generic penalty) = -0.2 (filtered out)
```

## Data Export Formats

### Jobs Export Format

| Column | Description | Example |
|--------|-------------|---------|
| Job ID | Unique identifier | job_001 |
| Title | Job title | Salesforce Agentforce Developer |
| Client Name | Client company | Tech Startup Inc |
| Hourly Rate | Rate in $/hour | $75/hr |
| Budget Range | Budget range | $5000-$10000 |
| Client Rating | Client rating | 4.8 |
| Payment Verified | Verification status | Yes |
| Status | Application status | APPLIED |
| Match Score | Relevance score | 0.92 |
| Skills Required | Required skills | Salesforce, Agentforce |
| Posted Date | When posted | 2024-01-15 |
| Job URL | Upwork job URL | https://upwork.com/... |

### Proposals Export Format

| Column | Description | Example |
|--------|-------------|---------|
| Proposal ID | Unique identifier | prop_001 |
| Job ID | Related job ID | job_001 |
| Job Title | Job title | Salesforce Developer |
| Bid Amount | Bid amount | $75/hr |
| Status | Proposal status | SUBMITTED |
| Generated Date | When generated | 2024-01-15 11:00 |
| Submitted Date | When submitted | 2024-01-15 11:30 |
| Google Doc URL | Document link | https://docs.google.com/... |
| Attachments Count | Number of files | 3 |

### Analytics Export Format

| Metric | Value | Period |
|--------|-------|--------|
| Total Jobs Discovered | 150 | All Time |
| Total Proposals Sent | 75 | All Time |
| Success Rate | 16.0% | All Time |
| Average Bid Amount | $78.50/hr | All Time |
| Jobs This Week | 12 | This Week |
| Response Rate | 32.0% | All Time |

## Error Handling

The integration includes comprehensive error handling:

### Retry Logic

```python
# Exponential backoff with jitter
max_retries = 3
base_delay = 1.0
backoff_factor = 2.0
max_delay = 60.0

# Retryable errors: 500, 502, 503, 504
# Non-retryable errors: 400, 401, 403, 404
```

### Fallback Mechanisms

1. **Mock Services**: When credentials are unavailable
2. **Local Storage**: For document content backup
3. **Error Logging**: Comprehensive error tracking
4. **Graceful Degradation**: System continues without Google services

## Testing

### Unit Tests

```bash
# Run all Google services tests
pytest tests/test_google_services.py -v

# Run specific test categories
pytest tests/test_google_services.py::TestGoogleDocsService -v
pytest tests/test_google_services.py::TestGoogleDriveService -v
pytest tests/test_google_services.py::TestGoogleSheetsService -v
```

### Integration Tests

```bash
# Run integration tests (requires credentials)
pytest tests/test_google_services.py::TestGoogleServicesIntegration --integration -v
```

### Demo Script

```bash
# Run the comprehensive demo
python examples/google_services_demo.py
```

## Monitoring and Logging

### Log Levels

- **INFO**: Successful operations, service initialization
- **WARNING**: Fallback to mock services, credential issues
- **ERROR**: API failures, authentication errors
- **DEBUG**: Detailed operation traces

### Metrics Tracked

- Document creation/update success rates
- File selection accuracy
- Export operation performance
- Authentication refresh frequency
- API quota usage

## Security Considerations

### Credential Management

- Service account keys stored securely
- OAuth2 tokens encrypted at rest
- Automatic credential rotation
- Scope limitation to required permissions

### Data Privacy

- No sensitive data stored in Google services
- Document sharing limited to necessary parties
- Audit logging for all operations
- GDPR compliance for data export

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   ```
   Solution: Check service account file path and permissions
   ```

2. **Quota Exceeded**
   ```
   Solution: Implement rate limiting and retry with backoff
   ```

3. **Permission Denied**
   ```
   Solution: Verify service account has access to Drive folders
   ```

4. **Document Not Found**
   ```
   Solution: Check document ID and sharing permissions
   ```

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('google-services').setLevel(logging.DEBUG)
```

## Performance Optimization

### Best Practices

1. **Batch Operations**: Group multiple API calls
2. **Caching**: Cache frequently accessed data
3. **Pagination**: Handle large result sets efficiently
4. **Connection Pooling**: Reuse HTTP connections
5. **Async Operations**: Use async/await for concurrency

### Rate Limiting

- Google Docs API: 100 requests/100 seconds/user
- Google Drive API: 1000 requests/100 seconds/user  
- Google Sheets API: 300 requests/100 seconds/user

## Future Enhancements

### Planned Features

- [ ] Real-time document collaboration
- [ ] Advanced chart generation in Sheets
- [ ] Automated folder organization
- [ ] Template management system
- [ ] Bulk operations optimization
- [ ] Advanced analytics dashboards

### Integration Opportunities

- [ ] Gmail integration for notifications
- [ ] Google Calendar for scheduling
- [ ] Google Forms for client feedback
- [ ] Google Sites for portfolio hosting

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review the logs for error details
3. Run the integration test endpoint
4. Consult the Google API documentation
5. Contact the development team

## References

- [Google Docs API Documentation](https://developers.google.com/docs/api)
- [Google Drive API Documentation](https://developers.google.com/drive/api)
- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [Google Cloud Console](https://console.cloud.google.com/)
- [OAuth2 Setup Guide](https://developers.google.com/identity/protocols/oauth2)