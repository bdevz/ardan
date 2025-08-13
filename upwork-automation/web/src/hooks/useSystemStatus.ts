import { useQuery, useMutation, useQueryClient } from 'react-query';
import { api } from '../services/api';

export interface SystemStatus {
  automationEnabled: boolean;
  isPaused: boolean;
  queuedJobs: number;
  activeWorkers: number;
  lastJobDiscovery: string;
  systemHealth: 'healthy' | 'warning' | 'error';
  uptime: number;
}

export const useSystemStatus = () => {
  const queryClient = useQueryClient();

  const query = useQuery<SystemStatus>(
    'systemStatus',
    () => api.get('/system/status').then(res => res.data),
    {
      refetchInterval: 5000, // Refresh every 5 seconds
    }
  );

  const toggleAutomationMutation = useMutation(
    () => api.post('/system/toggle-automation'),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('systemStatus');
      },
    }
  );

  const pauseSystemMutation = useMutation(
    () => api.post('/system/pause'),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('systemStatus');
      },
    }
  );

  const resumeSystemMutation = useMutation(
    () => api.post('/system/resume'),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('systemStatus');
      },
    }
  );

  const emergencyStopMutation = useMutation(
    () => api.post('/system/emergency-stop'),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('systemStatus');
      },
    }
  );

  return {
    ...query,
    toggleAutomation: toggleAutomationMutation.mutate,
    pauseSystem: pauseSystemMutation.mutate,
    resumeSystem: resumeSystemMutation.mutate,
    emergencyStop: emergencyStopMutation.mutate,
  };
};