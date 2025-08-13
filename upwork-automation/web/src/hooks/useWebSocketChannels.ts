import { useEffect, useState } from 'react';
import { useWebSocket, WebSocketMessage } from './useWebSocket';

// Dashboard WebSocket hook
export const useDashboardWebSocket = () => {
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [jobUpdates, setJobUpdates] = useState<any[]>([]);
  const [systemAlerts, setSystemAlerts] = useState<any[]>([]);
  
  const { connectionStatus, lastMessage, error, isConnected } = useWebSocket('/api/ws/dashboard');

  useEffect(() => {
    if (lastMessage) {
      switch (lastMessage.type) {
        case 'job_discovered':
          setJobUpdates(prev => [lastMessage.data, ...prev.slice(0, 9)]); // Keep last 10
          break;
        case 'job_status_update':
          setJobUpdates(prev => [lastMessage.data, ...prev.slice(0, 9)]);
          break;
        case 'application_submitted':
          setJobUpdates(prev => [lastMessage.data, ...prev.slice(0, 9)]);
          break;
        case 'system_metrics_update':
          setDashboardData(lastMessage.data);
          break;
        case 'error_alert':
          setSystemAlerts(prev => [lastMessage.data, ...prev.slice(0, 4)]); // Keep last 5
          break;
        case 'system_status_change':
          setSystemAlerts(prev => [lastMessage.data, ...prev.slice(0, 4)]);
          break;
      }
    }
  }, [lastMessage]);

  return {
    connectionStatus,
    error,
    isConnected,
    dashboardData,
    jobUpdates,
    systemAlerts,
  };
};

// Job Queue WebSocket hook
export const useJobQueueWebSocket = () => {
  const [queueStatus, setQueueStatus] = useState<any>(null);
  const [queueHistory, setQueueHistory] = useState<any[]>([]);
  
  const { connectionStatus, lastMessage, error, isConnected } = useWebSocket('/api/ws/queue');

  useEffect(() => {
    if (lastMessage) {
      switch (lastMessage.type) {
        case 'queue_status_update':
          setQueueStatus(lastMessage.data);
          setQueueHistory(prev => [lastMessage.data, ...prev.slice(0, 19)]); // Keep last 20
          break;
        case 'job_discovered':
        case 'job_status_update':
        case 'application_submitted':
          // Update queue history with job-related events
          setQueueHistory(prev => [
            { ...lastMessage.data, event_type: lastMessage.type, timestamp: lastMessage.timestamp },
            ...prev.slice(0, 19)
          ]);
          break;
      }
    }
  }, [lastMessage]);

  return {
    connectionStatus,
    error,
    isConnected,
    queueStatus,
    queueHistory,
  };
};

// System Metrics WebSocket hook
export const useSystemMetricsWebSocket = () => {
  const [currentMetrics, setCurrentMetrics] = useState<any>(null);
  const [metricsHistory, setMetricsHistory] = useState<any[]>([]);
  const [performanceData, setPerformanceData] = useState<any[]>([]);
  
  const { connectionStatus, lastMessage, error, isConnected } = useWebSocket('/api/ws/metrics');

  useEffect(() => {
    if (lastMessage) {
      switch (lastMessage.type) {
        case 'system_metrics_update':
          setCurrentMetrics(lastMessage.data);
          setMetricsHistory(prev => [lastMessage.data, ...prev.slice(0, 59)]); // Keep last 60 for charts
          
          // Extract performance data for charts
          const performancePoint = {
            timestamp: lastMessage.data.last_updated,
            applications_today: lastMessage.data.applications_today,
            success_rate: lastMessage.data.success_rate,
            avg_response_time: lastMessage.data.avg_response_time,
            cpu_usage: lastMessage.data.cpu_usage,
            memory_usage: lastMessage.data.memory_usage,
          };
          setPerformanceData(prev => [performancePoint, ...prev.slice(0, 99)]); // Keep last 100 for charts
          break;
      }
    }
  }, [lastMessage]);

  return {
    connectionStatus,
    error,
    isConnected,
    currentMetrics,
    metricsHistory,
    performanceData,
  };
};

// Jobs WebSocket hook
export const useJobsWebSocket = () => {
  const [jobUpdates, setJobUpdates] = useState<any[]>([]);
  const [proposalUpdates, setProposalUpdates] = useState<any[]>([]);
  const [applicationUpdates, setApplicationUpdates] = useState<any[]>([]);
  
  const { connectionStatus, lastMessage, error, isConnected } = useWebSocket('/api/ws/jobs');

  useEffect(() => {
    if (lastMessage) {
      switch (lastMessage.type) {
        case 'job_discovered':
          setJobUpdates(prev => [lastMessage.data, ...prev.slice(0, 49)]); // Keep last 50
          break;
        case 'job_status_update':
          setJobUpdates(prev => 
            prev.map(job => 
              job.job_id === lastMessage.data.job_id 
                ? { ...job, ...lastMessage.data }
                : job
            )
          );
          break;
        case 'proposal_generated':
          setProposalUpdates(prev => [lastMessage.data, ...prev.slice(0, 49)]);
          break;
        case 'application_submitted':
          setApplicationUpdates(prev => [lastMessage.data, ...prev.slice(0, 49)]);
          break;
      }
    }
  }, [lastMessage]);

  return {
    connectionStatus,
    error,
    isConnected,
    jobUpdates,
    proposalUpdates,
    applicationUpdates,
  };
};

// System Status WebSocket hook
export const useSystemStatusWebSocket = () => {
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [statusHistory, setStatusHistory] = useState<any[]>([]);
  const [automationStatus, setAutomationStatus] = useState<any>(null);
  
  const { connectionStatus, lastMessage, error, isConnected } = useWebSocket('/api/ws/system');

  useEffect(() => {
    if (lastMessage) {
      switch (lastMessage.type) {
        case 'system_status_change':
          setSystemStatus(lastMessage.data);
          setStatusHistory(prev => [lastMessage.data, ...prev.slice(0, 19)]); // Keep last 20
          break;
        case 'automation_control':
          setAutomationStatus(lastMessage.data);
          setStatusHistory(prev => [
            { ...lastMessage.data, type: 'automation_control' },
            ...prev.slice(0, 19)
          ]);
          break;
        case 'error_alert':
          setStatusHistory(prev => [
            { ...lastMessage.data, type: 'error_alert' },
            ...prev.slice(0, 19)
          ]);
          break;
      }
    }
  }, [lastMessage]);

  return {
    connectionStatus,
    error,
    isConnected,
    systemStatus,
    statusHistory,
    automationStatus,
  };
};

export default {
  useDashboardWebSocket,
  useJobQueueWebSocket,
  useSystemMetricsWebSocket,
  useJobsWebSocket,
  useSystemStatusWebSocket,
};