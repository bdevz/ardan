import { useQuery } from 'react-query';
import { api } from '../services/api';

export interface Metrics {
  dailyApplications: Array<{
    date: string;
    applications: number;
  }>;
  successRates: Array<{
    date: string;
    successRate: number;
    responseRate: number;
  }>;
  systemMetrics: {
    cpuUsage: number;
    memoryUsage: number;
    queueHealth: number;
  };
  totalStats: {
    totalApplications: number;
    totalResponses: number;
    totalHires: number;
    averageResponseTime: number;
  };
}

export const useMetrics = () => {
  return useQuery<Metrics>(
    'metrics',
    () => api.get('/metrics').then(res => res.data),
    {
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  );
};