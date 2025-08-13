import { useQuery, useMutation, useQueryClient } from 'react-query';
import { api } from '../services/api';
import { Proposal } from '../types/Proposal';

export const useProposals = () => {
  const queryClient = useQueryClient();

  const query = useQuery<Proposal[]>(
    'proposals',
    () => api.get('/proposals').then(res => res.data)
  );

  const generateProposal = useMutation(
    (jobId: string) => api.post(`/proposals/generate`, { job_id: jobId }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('proposals');
        queryClient.invalidateQueries('jobs');
      },
    }
  );

  const updateProposal = useMutation(
    ({ proposalId, data }: { proposalId: string; data: Partial<Proposal> }) =>
      api.put(`/proposals/${proposalId}`, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('proposals');
      },
    }
  );

  const submitProposal = useMutation(
    (jobId: string) => api.post(`/proposals/submit`, { job_id: jobId }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('proposals');
        queryClient.invalidateQueries('jobs');
        queryClient.invalidateQueries('applications');
      },
    }
  );

  return {
    ...query,
    generateProposal: generateProposal.mutate,
    updateProposal: (proposalId: string, data: Partial<Proposal>) =>
      updateProposal.mutate({ proposalId, data }),
    submitProposal: submitProposal.mutate,
  };
};