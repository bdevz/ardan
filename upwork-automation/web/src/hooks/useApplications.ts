import { useQuery } from 'react-query';
import { api } from '../services/api';
import { Application, ApplicationStatus } from '../types/Application';

interface ApplicationsParams {
  page?: number;
  limit?: number;
  status?: ApplicationStatus;
  days?: number;
}

interface ApplicationsResponse {
  applications: Application[];
  total: number;
  page: number;
  limit: number;
  stats: {
    totalApplications: number;
    responseRate: number;
    hireRate: number;
    averageResponseTime: number;
  };
}

export const useApplications = (params: ApplicationsParams = {}) => {
  return useQuery<ApplicationsResponse>(
    ['applications', params],
    () => api.get('/applications', { params }).then(res => res.data),
    {
      keepPreviousData: true,
    }
  );
};

export const useApplication = (applicationId: string) => {
  return useQuery<Application>(
    ['application', applicationId],
    () => api.get(`/applications/${applicationId}`).then(res => res.data),
    {
      enabled: !!applicationId,
    }
  );
};