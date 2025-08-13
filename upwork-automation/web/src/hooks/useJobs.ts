import { useQuery, useMutation, useQueryClient } from 'react-query';
import { api } from '../services/api';
import { Job, JobStatus } from '../types/Job';

interface JobsParams {
  page?: number;
  limit?: number;
  status?: JobStatus;
  search?: string;
}

interface JobsResponse {
  jobs: Job[];
  total: number;
  page: number;
  limit: number;
}

export const useJobs = (params: JobsParams = {}) => {
  return useQuery<JobsResponse>(
    ['jobs', params],
    () => api.get('/jobs', { params }).then(res => res.data),
    {
      keepPreviousData: true,
    }
  );
};

export const useJob = (jobId: string) => {
  return useQuery<Job>(
    ['job', jobId],
    () => api.get(`/jobs/${jobId}`).then(res => res.data),
    {
      enabled: !!jobId,
    }
  );
};

export const useJobMutations = () => {
  const queryClient = useQueryClient();

  const updateJobStatus = useMutation(
    ({ jobId, status }: { jobId: string; status: JobStatus }) =>
      api.put(`/jobs/${jobId}`, { status }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('jobs');
      },
    }
  );

  const applyToJob = useMutation(
    (jobId: string) => api.post(`/jobs/${jobId}/apply`),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('jobs');
      },
    }
  );

  return {
    updateJobStatus: updateJobStatus.mutate,
    applyToJob: applyToJob.mutate,
  };
};