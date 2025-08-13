import { useQuery } from 'react-query';
import { api } from '../services/api';

export interface JobQueueStatus {
  totalJobs: number;
  queuedJobs: number;
  processingJobs: number;
  completedJobs: number;
  failedJobs: number;
  recentActivity: Array<{
    id: string;
    type: 'success' | 'error' | 'info';
    message: string;
    timestamp: string;
  }>;
}

export const useJobQueue = () => {
  return useQuery<JobQueueStatus>(
    'jobQueue',
    () => api.get('/queue/status').then(res => res.data),
    {
      refetchInterval: 3000, // Refresh every 3 seconds
    }
  );
};