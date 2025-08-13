# Manual Override Procedures

## Overview

The Upwork Automation System includes comprehensive manual override capabilities to ensure you maintain full control over the automation process. This guide covers all manual override procedures, emergency controls, and manual operation modes.

## Emergency Controls

### Immediate Stop Procedures

#### Emergency Stop Button
**Location**: Red "Emergency Stop" button in the web interface header

**What it does**:
- Immediately halts all browser automation
- Stops job discovery processes
- Cancels pending applications
- Pauses all background workers
- Maintains data integrity

**When to use**:
- Suspected platform detection
- Unusual system behavior
- Client complaints or issues
- System errors or instability
- Compliance concerns

**Steps**:
1. Click the red "Emergency Stop" button
2. Confirm the action in the popup dialog
3. Wait for confirmation message
4. Verify all processes have stopped
5. Check system logs for any errors

#### Pause All Automation
**Location**: Yellow "Pause" button in the web interface header

**What it does**:
- Temporarily stops automation processes
- Preserves current session states
- Allows for quick resume
- Maintains queue positions

**When to use**:
- Temporary system maintenance
- Configuration changes
- Manual review of pending applications
- Testing new settings

**Steps**:
1. Click the "Pause" button
2. System shows "Paused" status
3. All automation stops but sessions remain active
4. Click "Resume" to continue operations

### Command Line Emergency Controls

If the web interface is unavailable, use these command line controls:

#### Stop All Services
```bash
# Navigate to project directory
cd upwork-automation

# Stop all Docker containers
docker-compose down

# Verify all services are stopped
docker-compose ps
```

#### Stop Specific Services
```bash
# Stop only the worker processes
docker-compose stop worker

# Stop browser automation
docker-compose stop api-server

# Stop web interface
docker-compose stop web-interface
```

#### Emergency Database Backup
```bash
# Create immediate backup before stopping
docker-compose exec db pg_dump -U user upwork_automation > emergency_backup_$(date +%Y%m%d_%H%M%S).sql
```

## Manual Application Process

### When to Use Manual Mode

**Recommended scenarios**:
- High-value opportunities requiring custom approach
- Complex job requirements needing human review
- Testing new proposal strategies
- Client-specific customization needs
- Recovery from automation errors

### Step-by-Step Manual Application

#### 1. Job Selection and Review
```bash
# Access the web interface
http://localhost:3000

# Navigate to Jobs > Discovered
# Filter for jobs requiring manual attention
```

**Review checklist**:
- [ ] Job matches your expertise
- [ ] Client rating meets requirements (≥4.0)
- [ ] Hourly rate is acceptable (≥$50)
- [ ] Payment verification status
- [ ] Competition level (number of proposals)
- [ ] Job posting quality and detail

#### 2. Proposal Creation

**Option A: Use Generated Proposal**
1. Click on the job in the jobs list
2. Review the AI-generated proposal
3. Click "Edit in Google Docs"
4. Customize the proposal content
5. Save changes in Google Docs

**Option B: Create Custom Proposal**
1. Click "Create Custom Proposal"
2. Use the proposal template:
   ```
   Paragraph 1: Goal-focused introduction
   - Address the specific need
   - Mention Salesforce Agentforce expertise
   - Show understanding of requirements
   
   Paragraph 2: Relevant experience
   - Specific similar projects
   - Quantifiable results
   - Technical skills demonstration
   
   Paragraph 3: Clear call-to-action
   - Next steps proposal
   - Timeline estimate
   - Availability confirmation
   ```

#### 3. Bid Amount Calculation

**Factors to consider**:
- Job complexity and scope
- Client budget range
- Your experience level
- Market rates for similar work
- Competition level

**Recommended approach**:
```
Base Rate: $65/hour (your standard rate)
Adjustments:
+ $10/hour for complex requirements
+ $5/hour for tight deadlines
- $5/hour for long-term projects
- $10/hour for high competition

Final bid = Base Rate + Adjustments
```

#### 4. Attachment Selection

**Standard attachments**:
- Salesforce certification documents
- Relevant case studies
- Portfolio samples
- Client testimonials

**Job-specific attachments**:
- Similar project examples
- Technical documentation
- Proof of concept materials

#### 5. Manual Submission Process

**Through Web Interface**:
1. Review all proposal details
2. Click "Submit Manually"
3. Confirm submission details
4. Monitor submission status
5. Capture confirmation screenshot

**Direct Browser Submission** (if needed):
1. Open browser session manually
2. Navigate to Upwork job page
3. Click "Submit a Proposal"
4. Fill form with prepared content
5. Upload attachments
6. Review and submit
7. Record submission in system

## System Recovery Procedures

### After Emergency Stop

#### 1. Assess System State
```bash
# Check service status
docker-compose ps

# Review recent logs
docker-compose logs --tail=100 api-server
docker-compose logs --tail=100 worker

# Check database connectivity
docker-compose exec db psql -U user -d upwork_automation -c "SELECT COUNT(*) FROM jobs;"
```

#### 2. Identify Issues
**Common issues to check**:
- Browser session errors
- API rate limiting
- Database connection problems
- External service failures
- Configuration errors

#### 3. Gradual System Restart

**Phase 1: Core Services**
```bash
# Start database and Redis first
docker-compose up -d db redis

# Wait for services to be ready
sleep 30

# Start API server
docker-compose up -d api-server

# Verify API is responding
curl http://localhost:8000/api/system/status
```

**Phase 2: Web Interface**
```bash
# Start web interface
docker-compose up -d web-interface

# Verify web interface loads
curl http://localhost:3000
```

**Phase 3: Background Workers**
```bash
# Start worker processes
docker-compose up -d worker

# Start scheduler
docker-compose up -d scheduler

# Monitor worker logs
docker-compose logs -f worker
```

#### 4. Resume Automation Gradually

**Step 1: Enable Job Discovery Only**
1. Access web interface
2. Go to Settings > Automation
3. Enable only "Auto-Discovery"
4. Disable "Auto-Proposal" and "Auto-Submission"
5. Monitor for 30 minutes

**Step 2: Enable Proposal Generation**
1. If discovery is stable, enable "Auto-Proposal"
2. Monitor proposal quality
3. Check Google Docs integration
4. Verify for 30 minutes

**Step 3: Enable Application Submission**
1. If proposals are generating correctly, enable "Auto-Submission"
2. Start with low rate (1 application per hour)
3. Monitor browser sessions
4. Gradually increase to normal rate

### Browser Session Recovery

#### Session Timeout Recovery
```bash
# Check active sessions
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/browser/sessions

# Create new session pool
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_pool_size": 3, "stealth_mode": true}' \
  http://localhost:8000/api/browser/sessions
```

#### CAPTCHA Handling
**When CAPTCHA is detected**:
1. System automatically pauses automation
2. Slack alert is sent to team
3. Manual intervention required:
   ```bash
   # Access browser session directly
   # Navigate to Browserbase dashboard
   # Solve CAPTCHA manually
   # Resume automation
   ```

#### Login Session Recovery
```bash
# Trigger manual login process
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "manual_login", "session_id": "session_123"}' \
  http://localhost:8000/api/browser/sessions/session_123/action
```

## Manual Queue Management

### Queue Inspection and Control

#### View Current Queue Status
```bash
# Check queue status via API
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/queue/status

# Or use web interface: Settings > Queue Management
```

#### Clear Pending Tasks
```bash
# Clear all pending tasks
curl -X DELETE -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/queue/clear

# Clear specific task type
curl -X DELETE -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/queue/clear?task_type=application_submission
```

#### Manual Task Processing
```bash
# Process specific job manually
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "job_123", "priority": "high"}' \
  http://localhost:8000/api/jobs/job_123/apply
```

### Priority Management

#### High Priority Applications
**When to use**:
- Exceptional job opportunities
- Client-requested quick response
- Time-sensitive applications

**Process**:
1. Mark job as high priority in web interface
2. Job moves to front of queue
3. Processed within 15 minutes
4. Extra monitoring and verification

#### Batch Processing Control
```bash
# Process jobs in batches
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 5, "delay_between": 300}' \
  http://localhost:8000/api/queue/process-batch
```

## Configuration Override

### Temporary Setting Changes

#### Rate Limiting Override
**Emergency rate reduction**:
1. Access Settings > Automation
2. Reduce "Applications per Hour" to 1
3. Increase "Delay Between Applications" to 3600 seconds
4. Enable "Extra Safety Mode"

#### Filter Override
**Bypass normal filters for specific jobs**:
```bash
# Apply to job regardless of filters
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"override_filters": true, "reason": "High value opportunity"}' \
  http://localhost:8000/api/jobs/job_123/apply
```

### Environment Variable Overrides

#### Temporary Configuration Changes
```bash
# Create override environment file
cat > .env.override << EOF
DAILY_APPLICATION_LIMIT=10
MIN_HOURLY_RATE=60
AUTOMATION_ENABLED=false
SAFETY_MODE=true
EOF

# Restart with overrides
docker-compose --env-file .env.override up -d
```

## Monitoring During Manual Operations

### Real-time Monitoring

#### Web Interface Monitoring
1. Keep dashboard open during manual operations
2. Monitor system health indicators
3. Watch for error alerts
4. Track application success rates

#### Log Monitoring
```bash
# Monitor all logs in real-time
docker-compose logs -f

# Monitor specific service
docker-compose logs -f api-server

# Monitor with filtering
docker-compose logs -f | grep ERROR
```

### Performance Tracking

#### Manual vs Automated Comparison
- Track success rates for manual applications
- Compare response times
- Monitor client feedback quality
- Analyze cost-effectiveness

#### Success Metrics
```bash
# Get manual application statistics
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/metrics?manual_only=true&period=7d"
```

## Communication Protocols

### Team Notification

#### Slack Alerts for Manual Operations
**Automatic notifications sent for**:
- Emergency stops activated
- Manual mode enabled
- High-priority applications
- System recovery completion

#### Manual Notification Commands
```bash
# Send custom Slack alert
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Manual override activated", "channel": "#upwork-automation", "priority": "high"}' \
  http://localhost:8000/api/notifications/slack
```

### Documentation Requirements

#### Manual Operation Log
**Required documentation for each manual override**:
- Timestamp and duration
- Reason for manual intervention
- Actions taken
- Results achieved
- Lessons learned

#### Incident Reporting
**For emergency stops**:
- Root cause analysis
- Impact assessment
- Recovery steps taken
- Prevention measures implemented

## Best Practices for Manual Operations

### When to Use Manual Override

**Recommended scenarios**:
- System errors or instability
- Platform policy changes
- High-value opportunities
- Testing new strategies
- Training new team members

**Avoid manual override for**:
- Routine operations
- Minor configuration changes
- Temporary network issues
- Normal queue processing

### Manual Operation Checklist

**Before Manual Override**:
- [ ] Document reason for manual intervention
- [ ] Notify team members
- [ ] Backup current system state
- [ ] Review recent system logs
- [ ] Prepare rollback plan

**During Manual Operation**:
- [ ] Monitor system performance
- [ ] Document all actions taken
- [ ] Track success metrics
- [ ] Maintain communication with team
- [ ] Follow security protocols

**After Manual Operation**:
- [ ] Verify system stability
- [ ] Update documentation
- [ ] Analyze results and lessons learned
- [ ] Plan improvements to automation
- [ ] Resume normal operations gradually

### Safety Guidelines

#### Data Protection
- Always backup before major changes
- Verify data integrity after operations
- Protect sensitive client information
- Follow data retention policies

#### Platform Compliance
- Maintain human-like behavior patterns
- Respect rate limits and delays
- Monitor for platform changes
- Document compliance measures

#### Security Measures
- Use secure connections
- Protect authentication credentials
- Monitor access logs
- Follow least privilege principles

This comprehensive guide ensures you can effectively manage the system manually when needed while maintaining safety, compliance, and data integrity. For additional support, refer to the [Troubleshooting Guide](../operations/troubleshooting.md) or contact your system administrator.