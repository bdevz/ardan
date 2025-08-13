import { useQuery, useMutation, useQueryClient } from 'react-query';
import { api } from '../services/api';
import { SystemConfig } from '../types/SystemConfig';

export const useSettings = () => {
  const queryClient = useQueryClient();

  const query = useQuery<SystemConfig>(
    'settings',
    () => api.get('/settings').then(res => res.data)
  );

  const updateSettingsMutation = useMutation(
    (config: SystemConfig) => api.post('/settings', config),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('settings');
        queryClient.invalidateQueries('systemStatus');
      },
    }
  );

  return {
    ...query,
    updateSettings: updateSettingsMutation.mutateAsync,
    isUpdating: updateSettingsMutation.isLoading,
  };
};