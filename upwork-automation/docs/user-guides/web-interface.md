# Web Interface User Guide

## Overview

The Upwork Automation System web interface provides a comprehensive dashboard for monitoring, controlling, and configuring the automation system. This guide covers all features and functionality available through the web interface.

## Accessing the Web Interface

1. **URL**: Open your web browser and navigate to `http://localhost:3000`
2. **Login**: Use your system credentials to log in
3. **Dashboard**: You'll be redirected to the main dashboard upon successful login

## Dashboard Overview

The main dashboard provides a real-time overview of system status and performance.

### Key Metrics Cards

**Jobs Discovered Today**
- Shows the number of jobs found in the last 24 hours
- Color-coded: Green (>10), Yellow (5-10), Red (<5)
- Click to view detailed job list

**Applications Submitted**
- Displays applications sent today vs. daily limit
- Progress bar shows percentage of daily limit used
- Click to view application history

**Success Rate (7 days)**
- Shows the percentage of applications that led to interviews/hires
- Trend indicator shows improvement/decline
- Click for detailed analytics

**Active Browser Sessions**
- Number of currently active browser automation sessions
- Status indicators: Active (green), Idle (yellow), Error (red)
- Click to manage sessions

### Real-time Activity Feed

The activity feed shows live updates of system operations:

- **Job Discovery**: New jobs found with match scores
- **Proposal Generation**: Proposals created and stored
- **Application Submission**: Applications sent with status
- **System Events**: Configuration changes, errors, alerts

### Quick Actions Panel

**Emergency Controls**
- **Pause All**: Immediately stops all automation
- **Resume**: Restarts paused automation
- **Emergency Stop**: Complete system shutdown

**Manual Triggers**
- **Discover Jobs**: Manually trigger job discovery
- **Generate Proposals**: Create proposals for queued jobs
- **Submit Applications**: Process pending applications

## Jobs Management

### Jobs List View

Navigate to **Jobs** from the main menu to access the jobs management interface.

#### Filtering and Search

**Status Filters**
- **All**: Show all jobs regardless of status
- **Discovered**: Newly found jobs awaiting review
- **Filtered**: Jobs that passed initial filtering
- **Queued**: Jobs approved for application
- **Applied**: Jobs with submitted applications
- **Rejected**: Jobs marked as not suitable

**Search Options**
- **Title Search**: Search by job title keywords
- **Client Search**: Find jobs by client name
- **Skill Search**: Filter by required skills
- **Rate Range**: Filter by hourly rate range

**Sorting Options**
- **Match Score**: Sort by AI-calculated relevance
- **Posted Date**: Sort by when job was posted
- **Hourly Rate**: Sort by compensation
- **Client Rating**: Sort by client reputation

#### Job Details View

Click on any job to view detailed information:

**Job Information**
- Complete job description
- Budget and rate information
- Client details and history
- Required skills and qualifications
- Application deadline
- Number of existing proposals

**Match Analysis**
- AI-calculated match score (0-100%)
- Reasons for match score
- Recommended bid amount
- Success probability estimate

**Actions Available**
- **Apply Now**: Immediately queue for application
- **Generate Proposal**: Create proposal draft
- **Mark as Not Interested**: Remove from consideration
- **Add Notes**: Add personal notes about the job

### Proposal Preview and Editing

When viewing a job with a generated proposal:

**Proposal Content**
- Three-paragraph structure display
- Bid amount and reasoning
- Selected attachments
- Google Docs link for editing

**Editing Options**
- **Edit in Google Docs**: Opens proposal in Google Docs
- **Modify Bid**: Adjust bid amount
- **Change Attachments**: Select different files
- **Add Custom Notes**: Include additional information

**Approval Process**
- **Approve for Submission**: Queue proposal for automated submission
- **Request Changes**: Send back for revision
- **Manual Submission**: Handle submission manually

## Applications Tracking

### Applications Dashboard

Navigate to **Applications** to monitor submitted applications.

#### Application Status Tracking

**Status Categories**
- **Submitted**: Application sent, awaiting client response
- **Viewed**: Client has viewed the application
- **Interview Requested**: Client wants to schedule interview
- **Hired**: Successfully hired for the project
- **Declined**: Application was not selected

**Timeline View**
- Application submission timestamp
- Client response timeline
- Interview scheduling details
- Project start date (if hired)

#### Performance Analytics

**Success Metrics**
- Response rate: Percentage of applications receiving responses
- Interview rate: Percentage leading to interviews
- Hire rate: Percentage resulting in projects
- Average response time: How quickly clients respond

**Trend Analysis**
- Weekly/monthly performance trends
- Success rate by job category
- Optimal application timing
- Client rating correlation

## System Configuration

### General Settings

Navigate to **Settings** to configure system behavior.

#### Application Limits
- **Daily Application Limit**: Maximum applications per day (default: 30)
- **Hourly Rate Minimum**: Lowest acceptable hourly rate (default: $50)
- **Target Hourly Rate**: Preferred hourly rate (default: $75)
- **Client Rating Minimum**: Minimum client rating (default: 4.0)

#### Job Filtering Criteria
- **Keywords to Include**: Required keywords in job descriptions
- **Keywords to Exclude**: Keywords that disqualify jobs
- **Budget Requirements**: Minimum and maximum budget ranges
- **Client Requirements**: Payment verification, hire rate thresholds

#### Automation Settings
- **Auto-Discovery**: Enable/disable automatic job discovery
- **Auto-Proposal**: Enable/disable automatic proposal generation
- **Auto-Submission**: Enable/disable automatic application submission
- **Safety Delays**: Configure delays between applications

### Notification Preferences

**Slack Integration**
- **Channel Selection**: Choose Slack channels for notifications
- **Notification Types**: Select which events trigger notifications
- **Quiet Hours**: Set times when notifications are suppressed
- **Alert Thresholds**: Configure when to send urgent alerts

**Email Notifications**
- **Email Recipients**: Add team members for email alerts
- **Digest Frequency**: Daily/weekly summary emails
- **Critical Alerts**: Immediate email for system errors

### Browser Automation Settings

**Session Management**
- **Session Pool Size**: Number of concurrent browser sessions
- **Session Timeout**: How long to keep sessions active
- **Stealth Mode**: Enable advanced anti-detection features
- **Proxy Settings**: Configure proxy rotation

**Safety Controls**
- **Rate Limiting**: Applications per hour/day limits
- **Human Patterns**: Randomize timing and behavior
- **Error Handling**: How to respond to automation errors
- **Compliance Monitoring**: Platform change detection

## Real-time Monitoring

### Live System Status

The web interface provides real-time monitoring of all system components:

**Service Health**
- **API Server**: Response time and error rate
- **Database**: Connection status and performance
- **Browser Sessions**: Active sessions and health
- **External Services**: Google, Slack, n8n connectivity

**Performance Metrics**
- **Job Discovery Rate**: Jobs found per hour
- **Processing Speed**: Time from discovery to application
- **Success Rates**: Application to interview conversion
- **Error Rates**: System and automation errors

### WebSocket Updates

The interface uses WebSocket connections for real-time updates:

- **Live Job Discovery**: New jobs appear immediately
- **Application Status**: Real-time submission confirmations
- **System Alerts**: Instant error and warning notifications
- **Performance Updates**: Live metric updates

## Manual Override Procedures

### Emergency Controls

**Immediate Actions**
1. **Pause All Automation**: Click the red "Pause" button in the header
2. **Emergency Stop**: Use "Emergency Stop" for complete shutdown
3. **Cancel Pending Tasks**: Clear the application queue

**Verification Steps**
1. Check that all browser sessions are paused
2. Verify no applications are being processed
3. Confirm queue is empty or paused

### Manual Application Process

When automation is paused or for special cases:

**Manual Job Application**
1. Navigate to the job in the Jobs list
2. Click "Manual Application"
3. Review and edit the proposal
4. Set custom bid amount if needed
5. Select attachments
6. Click "Submit Manually"

**Tracking Manual Applications**
- Manual applications are marked with a special indicator
- They appear in the normal applications tracking
- Success metrics include both automated and manual applications

### System Recovery

**After Emergency Stop**
1. Check system logs for error details
2. Resolve any underlying issues
3. Restart services if needed
4. Resume automation gradually
5. Monitor for continued issues

**Gradual Resume Process**
1. Start with job discovery only
2. Enable proposal generation after verification
3. Enable application submission last
4. Monitor each stage for stability

## Troubleshooting Common Issues

### Interface Not Loading

**Symptoms**: Web page won't load or shows errors

**Solutions**:
1. Check that the web server is running: `docker-compose ps`
2. Verify the URL is correct: `http://localhost:3000`
3. Clear browser cache and cookies
4. Try a different browser or incognito mode
5. Check browser console for JavaScript errors

### Real-time Updates Not Working

**Symptoms**: Dashboard doesn't show live updates

**Solutions**:
1. Check WebSocket connection in browser developer tools
2. Verify API server is running and accessible
3. Check firewall settings for WebSocket connections
4. Refresh the page to re-establish connection
5. Check system logs for WebSocket errors

### Authentication Issues

**Symptoms**: Can't log in or getting unauthorized errors

**Solutions**:
1. Verify username and password are correct
2. Check if JWT token has expired (refresh page)
3. Clear browser storage and cookies
4. Verify API server authentication is working
5. Check system configuration for auth settings

### Performance Issues

**Symptoms**: Interface is slow or unresponsive

**Solutions**:
1. Check system resource usage (CPU, memory)
2. Verify database performance
3. Clear browser cache
4. Reduce the number of items displayed in lists
5. Check network connectivity to API server

### Data Not Updating

**Symptoms**: Old data showing, changes not reflected

**Solutions**:
1. Refresh the page manually
2. Check API server logs for errors
3. Verify database connectivity
4. Check if background workers are running
5. Clear browser cache and reload

## Best Practices

### Daily Monitoring Routine

**Morning Check** (5 minutes)
1. Review overnight job discoveries
2. Check application success from previous day
3. Verify system health indicators
4. Review any error alerts

**Midday Review** (10 minutes)
1. Monitor application progress toward daily limit
2. Review proposal quality for recent applications
3. Check for any client responses or interviews
4. Adjust settings if needed

**Evening Summary** (5 minutes)
1. Review daily performance metrics
2. Check for any system alerts or errors
3. Plan any needed configuration changes
4. Review upcoming job opportunities

### Configuration Management

**Regular Reviews**
- Weekly review of filtering criteria effectiveness
- Monthly analysis of success patterns
- Quarterly review of rate and budget settings
- Adjust based on market conditions and performance

**A/B Testing**
- Test different proposal templates
- Experiment with bid amounts
- Try different application timing
- Compare success rates across strategies

### Security Practices

**Access Control**
- Use strong passwords for system access
- Regularly rotate authentication tokens
- Limit access to authorized team members only
- Monitor login activity and access logs

**Data Protection**
- Regularly backup system configuration
- Protect sensitive client and job data
- Use secure connections (HTTPS) when available
- Follow data retention policies

## Advanced Features

### Custom Dashboards

Create personalized dashboards for different roles:

**Manager Dashboard**
- High-level performance metrics
- Success rate trends
- Resource utilization
- Team productivity indicators

**Operator Dashboard**
- Real-time job queue status
- Browser session health
- Error alerts and resolution
- Manual override controls

### Reporting and Analytics

**Performance Reports**
- Generate weekly/monthly performance summaries
- Export data for external analysis
- Create custom metric combinations
- Schedule automated report delivery

**Success Analysis**
- Identify patterns in successful applications
- Analyze client response behaviors
- Optimize proposal templates based on data
- Track ROI and efficiency metrics

### Integration Management

**External Service Status**
- Monitor Google Services connectivity
- Check Slack integration health
- Verify n8n workflow status
- Track API usage and limits

**Webhook Management**
- Configure custom webhooks for events
- Monitor webhook delivery status
- Debug webhook failures
- Set up custom integrations

This comprehensive guide covers all aspects of using the web interface effectively. For additional support or advanced configuration, refer to the [System Administration Guide](../operations/system-admin.md) or contact your system administrator.