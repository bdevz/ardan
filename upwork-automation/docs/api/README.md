# API Documentation

## Overview

The Upwork Automation System provides a comprehensive REST API for all system operations. The API is built with FastAPI and includes automatic OpenAPI documentation, request/response validation, and WebSocket support for real-time updates.

## Base URL

```
http://localhost:8000/api
```

## Authentication

The API uses JWT-based authentication for secure access:

```bash
# Login to get access token
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'

# Use token in subsequent requests
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/jobs"
```

## API Endpoints

### Jobs API

#### List Jobs
```http
GET /api/jobs
```

**Query Parameters:**
- `status` (optional): Filter by job status (discovered, filtered, queued, applied, rejected)
- `limit` (optional): Number of jobs to return (default: 50)
- `offset` (optional): Pagination offset (default: 0)
- `sort` (optional): Sort field (created_at, match_score, hourly_rate)
- `order` (optional): Sort order (asc, desc)

**Response:**
```json
{
  "jobs": [
    {
      "id": "job_123",
      "title": "Salesforce Agentforce Developer",
      "description": "Looking for experienced developer...",
      "budget_min": 50.0,
      "budget_max": 75.0,
      "hourly_rate": 65.0,
      "client_rating": 4.8,
      "client_payment_verified": true,
      "posted_date": "2024-12-10T10:00:00Z",
      "skills_required": ["Salesforce", "Agentforce", "Python"],
      "status": "discovered",
      "match_score": 0.85,
      "created_at": "2024-12-10T10:05:00Z"
    }
  ],
  "total": 25,
  "limit": 50,
  "offset": 0
}
```

#### Get Job Details
```http
GET /api/jobs/{job_id}
```

**Response:**
```json
{
  "id": "job_123",
  "title": "Salesforce Agentforce Developer",
  "description": "Full job description...",
  "budget_min": 50.0,
  "budget_max": 75.0,
  "hourly_rate": 65.0,
  "client_rating": 4.8,
  "client_payment_verified": true,
  "client_hire_rate": 0.75,
  "posted_date": "2024-12-10T10:00:00Z",
  "deadline": "2024-12-20T23:59:59Z",
  "skills_required": ["Salesforce", "Agentforce", "Python"],
  "job_type": "hourly",
  "location": "Remote",
  "status": "discovered",
  "match_score": 0.85,
  "match_reasons": ["High client rating", "Good hourly rate", "Relevant skills"],
  "created_at": "2024-12-10T10:05:00Z",
  "updated_at": "2024-12-10T10:05:00Z"
}
```

#### Update Job Status
```http
PUT /api/jobs/{job_id}
```

**Request Body:**
```json
{
  "status": "queued",
  "notes": "Approved for application"
}
```

#### Manually Trigger Application
```http
POST /api/jobs/{job_id}/apply
```

**Request Body:**
```json
{
  "priority": "high",
  "custom_proposal": "Optional custom proposal content",
  "bid_amount": 70.0
}
```

### Proposals API

#### List Proposals
```http
GET /api/proposals
```

**Query Parameters:**
- `job_id` (optional): Filter by job ID
- `status` (optional): Filter by status (draft, submitted, accepted, rejected)
- `limit` (optional): Number of proposals to return
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "proposals": [
    {
      "id": "prop_456",
      "job_id": "job_123",
      "content": "Dear Client, I am excited to help...",
      "bid_amount": 65.0,
      "attachments": ["file_1", "file_2"],
      "google_doc_url": "https://docs.google.com/document/d/...",
      "generated_at": "2024-12-10T11:00:00Z",
      "submitted_at": "2024-12-10T11:30:00Z",
      "status": "submitted"
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

#### Generate Proposal
```http
POST /api/proposals/generate
```

**Request Body:**
```json
{
  "job_id": "job_123",
  "template_type": "standard",
  "custom_instructions": "Emphasize AI experience"
}
```

#### Get Proposal Details
```http
GET /api/proposals/{proposal_id}
```

#### Update Proposal
```http
PUT /api/proposals/{proposal_id}
```

**Request Body:**
```json
{
  "content": "Updated proposal content",
  "bid_amount": 70.0,
  "attachments": ["file_1", "file_3"]
}
```

### Applications API

#### List Applications
```http
GET /api/applications
```

**Response:**
```json
{
  "applications": [
    {
      "id": "app_789",
      "job_id": "job_123",
      "proposal_id": "prop_456",
      "submitted_at": "2024-12-10T12:00:00Z",
      "upwork_application_id": "upwork_987",
      "status": "submitted",
      "client_response": null,
      "client_response_date": null,
      "interview_scheduled": false,
      "hired": false
    }
  ],
  "total": 5,
  "limit": 50,
  "offset": 0
}
```

#### Get Application Details
```http
GET /api/applications/{application_id}
```

#### Update Application Status
```http
PUT /api/applications/{application_id}
```

**Request Body:**
```json
{
  "status": "interview_scheduled",
  "client_response": "We'd like to schedule an interview",
  "client_response_date": "2024-12-11T09:00:00Z",
  "interview_scheduled": true
}
```

### Browser Automation API

#### Get Browser Sessions
```http
GET /api/browser/sessions
```

**Response:**
```json
{
  "sessions": [
    {
      "id": "session_123",
      "status": "active",
      "created_at": "2024-12-10T10:00:00Z",
      "last_activity": "2024-12-10T12:00:00Z",
      "session_type": "job_discovery",
      "browserbase_session_id": "bb_session_456"
    }
  ]
}
```

#### Create Browser Session
```http
POST /api/browser/sessions
```

**Request Body:**
```json
{
  "session_type": "proposal_submission",
  "stealth_mode": true,
  "proxy_enabled": true
}
```

#### Execute Browser Action
```http
POST /api/browser/sessions/{session_id}/action
```

**Request Body:**
```json
{
  "action_type": "navigate",
  "parameters": {
    "url": "https://www.upwork.com/jobs/...",
    "wait_for": "page_load"
  }
}
```

#### Search Jobs via Browser
```http
POST /api/browser/search-jobs
```

**Request Body:**
```json
{
  "keywords": ["Salesforce Agentforce", "Salesforce AI"],
  "filters": {
    "min_hourly_rate": 50,
    "min_client_rating": 4.0,
    "payment_verified": true
  },
  "session_pool_size": 3
}
```

### System Configuration API

#### Get System Configuration
```http
GET /api/system/config
```

**Response:**
```json
{
  "daily_application_limit": 30,
  "min_hourly_rate": 50.0,
  "target_hourly_rate": 75.0,
  "min_client_rating": 4.0,
  "min_hire_rate": 0.5,
  "keywords_include": ["Salesforce Agentforce", "Salesforce AI", "Einstein"],
  "keywords_exclude": ["WordPress", "PHP"],
  "automation_enabled": true,
  "notification_channels": ["slack", "email"]
}
```

#### Update System Configuration
```http
PUT /api/system/config
```

**Request Body:**
```json
{
  "daily_application_limit": 25,
  "min_hourly_rate": 55.0,
  "automation_enabled": false
}
```

#### Get System Status
```http
GET /api/system/status
```

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "browserbase": "healthy",
    "n8n": "healthy"
  },
  "metrics": {
    "jobs_discovered_today": 15,
    "applications_submitted_today": 8,
    "success_rate_7d": 0.25,
    "active_browser_sessions": 3
  },
  "last_updated": "2024-12-10T12:00:00Z"
}
```

### Queue Management API

#### Get Queue Status
```http
GET /api/queue/status
```

**Response:**
```json
{
  "queues": {
    "job_discovery": {
      "pending": 2,
      "processing": 1,
      "completed": 45,
      "failed": 1
    },
    "proposal_generation": {
      "pending": 5,
      "processing": 2,
      "completed": 23,
      "failed": 0
    },
    "application_submission": {
      "pending": 3,
      "processing": 1,
      "completed": 18,
      "failed": 2
    }
  }
}
```

#### Add Task to Queue
```http
POST /api/queue/add
```

**Request Body:**
```json
{
  "task_type": "submit_proposal",
  "job_id": "job_123",
  "proposal_id": "prop_456",
  "priority": "normal",
  "scheduled_at": "2024-12-10T15:00:00Z"
}
```

#### Get Task Status
```http
GET /api/queue/tasks/{task_id}
```

#### Cancel Task
```http
DELETE /api/queue/tasks/{task_id}
```

### Metrics and Analytics API

#### Get Performance Metrics
```http
GET /api/metrics
```

**Query Parameters:**
- `period` (optional): Time period (1d, 7d, 30d, 90d)
- `metric_type` (optional): Specific metric type

**Response:**
```json
{
  "period": "7d",
  "metrics": {
    "jobs_discovered": 105,
    "applications_submitted": 42,
    "interviews_scheduled": 8,
    "hires": 2,
    "success_rate": 0.19,
    "average_response_time": 2.3,
    "client_rating_average": 4.6
  },
  "daily_breakdown": [
    {
      "date": "2024-12-10",
      "jobs_discovered": 15,
      "applications_submitted": 6,
      "interviews": 1,
      "hires": 0
    }
  ]
}
```

#### Get Success Analytics
```http
GET /api/metrics/success-analysis
```

**Response:**
```json
{
  "success_patterns": {
    "best_hourly_rate_range": [60, 80],
    "best_client_rating_threshold": 4.5,
    "most_successful_keywords": ["Agentforce", "Einstein", "AI"],
    "optimal_application_time": "09:00-11:00 EST"
  },
  "recommendations": [
    "Focus on jobs with hourly rates between $60-80",
    "Prioritize clients with 4.5+ rating",
    "Apply during morning hours for better response rates"
  ]
}
```

## WebSocket API

### Real-time Updates

Connect to WebSocket for real-time system updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

**Message Types:**
- `job_discovered`: New job found
- `proposal_generated`: Proposal created
- `application_submitted`: Application sent
- `system_status`: System status change
- `error_alert`: Error notification

**Example Message:**
```json
{
  "type": "job_discovered",
  "timestamp": "2024-12-10T12:00:00Z",
  "data": {
    "job_id": "job_123",
    "title": "Salesforce Agentforce Developer",
    "match_score": 0.85,
    "hourly_rate": 65.0
  }
}
```

## Error Handling

### HTTP Status Codes

- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "hourly_rate",
      "issue": "Must be greater than 0"
    }
  },
  "timestamp": "2024-12-10T12:00:00Z",
  "request_id": "req_123456"
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **General endpoints**: 100 requests per minute
- **Browser automation**: 10 requests per minute
- **Queue operations**: 50 requests per minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1702209600
```

## SDK and Integration Examples

### Python SDK Example

```python
import requests
from typing import List, Dict

class UpworkAutomationClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def get_jobs(self, status: str = None, limit: int = 50) -> List[Dict]:
        params = {"limit": limit}
        if status:
            params["status"] = status
        
        response = requests.get(
            f"{self.base_url}/jobs",
            headers=self.headers,
            params=params
        )
        return response.json()["jobs"]
    
    def apply_to_job(self, job_id: str, priority: str = "normal") -> Dict:
        response = requests.post(
            f"{self.base_url}/jobs/{job_id}/apply",
            headers=self.headers,
            json={"priority": priority}
        )
        return response.json()
    
    def get_system_status(self) -> Dict:
        response = requests.get(
            f"{self.base_url}/system/status",
            headers=self.headers
        )
        return response.json()

# Usage
client = UpworkAutomationClient("http://localhost:8000/api", "your_token")
jobs = client.get_jobs(status="discovered")
status = client.get_system_status()
```

### JavaScript/Node.js Example

```javascript
class UpworkAutomationClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  async getJobs(status = null, limit = 50) {
    const params = new URLSearchParams({ limit });
    if (status) params.append('status', status);
    
    const response = await fetch(`${this.baseUrl}/jobs?${params}`, {
      headers: this.headers
    });
    const data = await response.json();
    return data.jobs;
  }

  async applyToJob(jobId, priority = 'normal') {
    const response = await fetch(`${this.baseUrl}/jobs/${jobId}/apply`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ priority })
    });
    return await response.json();
  }

  async getSystemStatus() {
    const response = await fetch(`${this.baseUrl}/system/status`, {
      headers: this.headers
    });
    return await response.json();
  }
}

// Usage
const client = new UpworkAutomationClient('http://localhost:8000/api', 'your_token');
const jobs = await client.getJobs('discovered');
const status = await client.getSystemStatus();
```

## OpenAPI Documentation

The complete OpenAPI specification is available at:
```
http://localhost:8000/docs
```

Interactive API documentation (Swagger UI) is available at:
```
http://localhost:8000/docs
```

Alternative documentation (ReDoc) is available at:
```
http://localhost:8000/redoc
```

## Testing the API

### Using curl

```bash
# Get system status
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/system/status"

# List recent jobs
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/jobs?limit=10&sort=created_at&order=desc"

# Trigger job discovery
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["Salesforce Agentforce"]}' \
  "http://localhost:8000/api/browser/search-jobs"
```

### Using Postman

Import the OpenAPI specification from `/docs` into Postman for a complete collection of API endpoints with examples and documentation.

## API Versioning

The API uses URL versioning:
- Current version: `v1` (default)
- Future versions: `v2`, `v3`, etc.

Example:
```
http://localhost:8000/api/v1/jobs
http://localhost:8000/api/v2/jobs  # Future version
```

## Support and Troubleshooting

For API-related issues:
1. Check the [Troubleshooting Guide](../operations/troubleshooting.md)
2. Review API logs in the system dashboard
3. Verify authentication tokens are valid
4. Check rate limiting headers
5. Validate request format against OpenAPI spec