import React, { useEffect, useState } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,

} from '@mui/material';
import {
  TrendingUp,
  Work,
  Assignment,
  CheckCircle,
  Error,

  PlayArrow,
  Pause,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { useSystemStatus } from '../hooks/useSystemStatus';
import { useJobQueue } from '../hooks/useJobQueue';
import { useMetrics } from '../hooks/useMetrics';
import { useDashboardWebSocket } from '../hooks/useWebSocketChannels';

const Dashboard: React.FC = () => {
  const { data: systemStatus } = useSystemStatus();
  const { data: jobQueue } = useJobQueue();
  const { data: metrics } = useMetrics();

  // WebSocket connection for real-time updates
  const {
    connectionStatus,
    isConnected,
    dashboardData,
    jobUpdates,
    systemAlerts,
  } = useDashboardWebSocket();

  // Combine real-time data with static data
  const currentMetrics = dashboardData || metrics?.systemMetrics || {};
  const recentActivity = jobUpdates.slice(0, 10); // Show last 10 updates

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'success';
      case 'warning': return 'warning';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      {/* System Status Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    System Status
                  </Typography>
                  <Chip
                    label={systemStatus?.systemHealth || 'Unknown'}
                    color={getStatusColor(systemStatus?.systemHealth || 'default') as any}
                    size="small"
                  />
                </Box>
                <Box display="flex" alignItems="center">
                  {systemStatus?.automationEnabled ? (
                    <PlayArrow color="success" />
                  ) : (
                    <Pause color="warning" />
                  )}
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Queued Jobs
                  </Typography>
                  <Typography variant="h4">
                    {currentMetrics?.pending_jobs || systemStatus?.queuedJobs || 0}
                  </Typography>
                </Box>
                <Work color="primary" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Active Sessions
                  </Typography>
                  <Typography variant="h4">
                    {currentMetrics?.active_sessions || systemStatus?.activeWorkers || 0}
                  </Typography>
                </Box>
                <Assignment color="secondary" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Uptime
                  </Typography>
                  <Typography variant="h6">
                    {formatUptime(systemStatus?.uptime || 0)}
                  </Typography>
                </Box>
                <TrendingUp color="success" />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Real-time Job Queue Monitoring */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
              <Typography variant="h6">
                Real-time System Metrics
              </Typography>
              <Chip
                label={isConnected ? 'Live' : 'Disconnected'}
                color={isConnected ? 'success' : 'error'}
                size="small"
              />
            </Box>
            {systemAlerts.length > 0 && (
              <Box mb={2}>
                {systemAlerts.slice(0, 3).map((alert, index) => (
                  <Chip
                    key={index}
                    label={alert.message || alert.error_type}
                    color={alert.severity === 'high' ? 'error' : 'warning'}
                    size="small"
                    sx={{ mr: 1, mb: 1 }}
                  />
                ))}
              </Box>
            )}
            <Grid container spacing={2}>
              <Grid item xs={6} md={3}>
                <Typography variant="body2" gutterBottom>
                  Applications Today
                </Typography>
                <Typography variant="h5" color="primary">
                  {currentMetrics?.applications_today || 0}
                </Typography>
              </Grid>
              <Grid item xs={6} md={3}>
                <Typography variant="body2" gutterBottom>
                  Success Rate
                </Typography>
                <Typography variant="h5" color="success.main">
                  {currentMetrics?.success_rate ? `${(currentMetrics.success_rate * 100).toFixed(1)}%` : '0%'}
                </Typography>
              </Grid>
              <Grid item xs={6} md={3}>
                <Typography variant="body2" gutterBottom>
                  Avg Response Time
                </Typography>
                <Typography variant="h5">
                  {currentMetrics?.avg_response_time ? `${currentMetrics.avg_response_time}ms` : '0ms'}
                </Typography>
              </Grid>
              <Grid item xs={6} md={3}>
                <Typography variant="body2" gutterBottom>
                  System Health
                </Typography>
                <Chip
                  label={currentMetrics?.system_health || 'Unknown'}
                  color={getStatusColor(currentMetrics?.system_health || 'default') as any}
                  size="small"
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Recent Activity
            </Typography>
            <List dense>
              {recentActivity.length > 0 ? recentActivity.map((activity: any, index: number) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    {activity.status === 'APPLIED' || activity.status === 'SUBMITTED' ? (
                      <CheckCircle color="success" />
                    ) : activity.status === 'FAILED' ? (
                      <Error color="error" />
                    ) : (
                      <Work color="primary" />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      activity.job_title || 
                      activity.title || 
                      `${activity.status || 'Update'}: Job ${activity.job_id || 'Unknown'}`
                    }
                    secondary={
                      activity.timestamp ? 
                        new Date(activity.timestamp).toLocaleTimeString() :
                        'Just now'
                    }
                  />
                </ListItem>
              )) : (
                <ListItem>
                  <ListItemText
                    primary="No recent activity"
                    secondary="Waiting for updates..."
                  />
                </ListItem>
              )}
            </List>
          </Paper>
        </Grid>

        {/* Performance Metrics */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Daily Applications
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={metrics?.dailyApplications || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="applications" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Success Rate Trends */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Success Rate Trends
            </Typography>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={metrics?.successRates || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="successRate" stroke="#82ca9d" strokeWidth={2} />
                <Line type="monotone" dataKey="responseRate" stroke="#ffc658" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* System Performance */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              System Performance
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <Typography variant="body2" gutterBottom>
                  CPU Usage
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={currentMetrics?.cpu_usage || 0}
                  sx={{ mb: 1 }}
                />
                <Typography variant="caption">
                  {currentMetrics?.cpu_usage || 0}%
                </Typography>
              </Grid>
              <Grid item xs={12} md={4}>
                <Typography variant="body2" gutterBottom>
                  Memory Usage
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={currentMetrics?.memory_usage || 0}
                  sx={{ mb: 1 }}
                />
                <Typography variant="caption">
                  {currentMetrics?.memory_usage || 0}%
                </Typography>
              </Grid>
              <Grid item xs={12} md={4}>
                <Typography variant="body2" gutterBottom>
                  Queue Health
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={currentMetrics?.queue_health === 'healthy' ? 100 : currentMetrics?.queue_health === 'warning' ? 50 : 0}
                  color="success"
                  sx={{ mb: 1 }}
                />
                <Typography variant="caption">
                  {currentMetrics?.queue_health || 'Unknown'}
                </Typography>
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;