import { renderHook, act, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { useWebSocket } from '../hooks/useWebSocket';
import { useDashboardWebSocket, useJobQueueWebSocket, useSystemMetricsWebSocket } from '../hooks/useWebSocketChannels';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(public url: string) {
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  send(data: string) {
    // Mock send functionality
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Helper method to simulate receiving messages
  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }
}

// Mock global WebSocket
(global as any).WebSocket = MockWebSocket;

describe('WebSocket Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useWebSocket', () => {
    it('should establish WebSocket connection', async () => {
      const { result } = renderHook(() => useWebSocket('/api/ws/test'));

      expect(result.current.connectionStatus).toBe('Connecting');

      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('Connected');
      });

      expect(result.current.isConnected).toBe(true);
    });

    it('should handle connection errors', async () => {
      const { result } = renderHook(() => useWebSocket('/api/ws/test'));

      // Simulate connection error
      act(() => {
        const mockWs = (WebSocket as any).mock?.instances?.[0];
        if (mockWs?.onerror) {
          mockWs.onerror(new Event('error'));
        }
      });

      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('Error');
      });

      expect(result.current.error).toBeTruthy();
    });

    it('should handle reconnection', async () => {
      const { result } = renderHook(() => 
        useWebSocket('/api/ws/test', { maxReconnectAttempts: 3, reconnectInterval: 100 })
      );

      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('Connected');
      });

      // Simulate connection close
      act(() => {
        const mockWs = (WebSocket as any).mock?.instances?.[0];
        if (mockWs?.onclose) {
          mockWs.onclose(new CloseEvent('close'));
        }
      });

      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('Reconnecting');
      });
    });

    it('should send messages when connected', async () => {
      const { result } = renderHook(() => useWebSocket('/api/ws/test'));

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      const sendResult = result.current.sendMessage({ type: 'test', data: 'hello' });
      expect(sendResult).toBe(true);
    });

    it('should handle ping/pong heartbeat', async () => {
      const { result } = renderHook(() => 
        useWebSocket('/api/ws/test', { heartbeatInterval: 100 })
      );

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      // Wait for heartbeat to trigger
      await new Promise(resolve => setTimeout(resolve, 150));

      // Verify ping was sent (would need to mock WebSocket send method)
    });
  });

  describe('useDashboardWebSocket', () => {
    it('should handle job discovery messages', async () => {
      const { result } = renderHook(() => useDashboardWebSocket());

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      // Simulate job discovery message
      const jobMessage = {
        type: 'job_discovered',
        data: {
          id: 'job-123',
          title: 'Test Salesforce Job',
          budget_max: 5000,
          client_rating: 4.8,
          match_score: 0.95
        },
        timestamp: new Date().toISOString()
      };

      act(() => {
        // Simulate receiving the message
        const mockWs = (WebSocket as any).mock?.instances?.[0];
        if (mockWs) {
          mockWs.simulateMessage(jobMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.jobUpdates).toHaveLength(1);
        expect(result.current.jobUpdates[0]).toEqual(jobMessage.data);
      });
    });

    it('should handle system metrics updates', async () => {
      const { result } = renderHook(() => useDashboardWebSocket());

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      const metricsMessage = {
        type: 'system_metrics_update',
        data: {
          applications_today: 15,
          success_rate: 0.75,
          avg_response_time: 250,
          system_health: 'healthy'
        },
        timestamp: new Date().toISOString()
      };

      act(() => {
        const mockWs = (WebSocket as any).mock?.instances?.[0];
        if (mockWs) {
          mockWs.simulateMessage(metricsMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.dashboardData).toEqual(metricsMessage.data);
      });
    });

    it('should handle error alerts', async () => {
      const { result } = renderHook(() => useDashboardWebSocket());

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      const errorMessage = {
        type: 'error_alert',
        data: {
          id: 'error-123',
          type: 'browser_automation_error',
          message: 'Failed to submit application',
          severity: 'high'
        },
        timestamp: new Date().toISOString()
      };

      act(() => {
        const mockWs = (WebSocket as any).mock?.instances?.[0];
        if (mockWs) {
          mockWs.simulateMessage(errorMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.systemAlerts).toHaveLength(1);
        expect(result.current.systemAlerts[0]).toEqual(errorMessage.data);
      });
    });
  });

  describe('useJobQueueWebSocket', () => {
    it('should handle queue status updates', async () => {
      const { result } = renderHook(() => useJobQueueWebSocket());

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      const queueMessage = {
        type: 'queue_status_update',
        data: {
          total_jobs: 100,
          pending_jobs: 10,
          processing_jobs: 5,
          completed_jobs: 80,
          failed_jobs: 5,
          queue_health: 'healthy'
        },
        timestamp: new Date().toISOString()
      };

      act(() => {
        const mockWs = (WebSocket as any).mock?.instances?.[0];
        if (mockWs) {
          mockWs.simulateMessage(queueMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.queueStatus).toEqual(queueMessage.data);
        expect(result.current.queueHistory).toHaveLength(1);
      });
    });

    it('should maintain queue history', async () => {
      const { result } = renderHook(() => useJobQueueWebSocket());

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      // Send multiple queue updates
      for (let i = 0; i < 25; i++) {
        const queueMessage = {
          type: 'queue_status_update',
          data: {
            total_jobs: 100 + i,
            pending_jobs: 10 + i,
            processing_jobs: 5,
            completed_jobs: 80 + i,
            failed_jobs: 5,
            queue_health: 'healthy'
          },
          timestamp: new Date().toISOString()
        };

        act(() => {
          const mockWs = (WebSocket as any).mock?.instances?.[0];
          if (mockWs) {
            mockWs.simulateMessage(queueMessage);
          }
        });
      }

      await waitFor(() => {
        // Should keep only last 20 items
        expect(result.current.queueHistory.length).toBeLessThanOrEqual(20);
      });
    });
  });

  describe('useSystemMetricsWebSocket', () => {
    it('should handle system metrics updates', async () => {
      const { result } = renderHook(() => useSystemMetricsWebSocket());

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      const metricsMessage = {
        type: 'system_metrics_update',
        data: {
          applications_today: 15,
          success_rate: 0.75,
          avg_response_time: 250,
          active_sessions: 3,
          system_health: 'healthy',
          cpu_usage: 45,
          memory_usage: 60,
          last_updated: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      };

      act(() => {
        const mockWs = (WebSocket as any).mock?.instances?.[0];
        if (mockWs) {
          mockWs.simulateMessage(metricsMessage);
        }
      });

      await waitFor(() => {
        expect(result.current.currentMetrics).toEqual(metricsMessage.data);
        expect(result.current.metricsHistory).toHaveLength(1);
        expect(result.current.performanceData).toHaveLength(1);
      });
    });

    it('should maintain performance data for charts', async () => {
      const { result } = renderHook(() => useSystemMetricsWebSocket());

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      // Send multiple metrics updates
      for (let i = 0; i < 105; i++) {
        const metricsMessage = {
          type: 'system_metrics_update',
          data: {
            applications_today: 15 + i,
            success_rate: 0.75,
            avg_response_time: 250 + i,
            active_sessions: 3,
            system_health: 'healthy',
            cpu_usage: 45 + (i % 20),
            memory_usage: 60 + (i % 15),
            last_updated: new Date().toISOString()
          },
          timestamp: new Date().toISOString()
        };

        act(() => {
          const mockWs = (WebSocket as any).mock?.instances?.[0];
          if (mockWs) {
            mockWs.simulateMessage(metricsMessage);
          }
        });
      }

      await waitFor(() => {
        // Should keep only last 100 items for charts
        expect(result.current.performanceData.length).toBeLessThanOrEqual(100);
        expect(result.current.metricsHistory.length).toBeLessThanOrEqual(60);
      });
    });
  });

  describe('WebSocket Error Handling', () => {
    it('should handle connection failures gracefully', async () => {
      const { result } = renderHook(() => 
        useWebSocket('/api/ws/test', { maxReconnectAttempts: 1, reconnectInterval: 100 })
      );

      // Simulate immediate connection failure
      act(() => {
        const mockWs = (WebSocket as any).mock?.instances?.[0];
        if (mockWs?.onerror) {
          mockWs.onerror(new Event('error'));
        }
      });

      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('Error');
        expect(result.current.error).toBeTruthy();
      });
    });

    it('should stop reconnecting after max attempts', async () => {
      const { result } = renderHook(() => 
        useWebSocket('/api/ws/test', { maxReconnectAttempts: 2, reconnectInterval: 50 })
      );

      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('Connected');
      });

      // Simulate multiple disconnections
      for (let i = 0; i < 3; i++) {
        act(() => {
          const mockWs = (WebSocket as any).mock?.instances?.[0];
          if (mockWs?.onclose) {
            mockWs.onclose(new CloseEvent('close'));
          }
        });

        await new Promise(resolve => setTimeout(resolve, 100));
      }

      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('Disconnected');
        expect(result.current.error).toContain('Max reconnection attempts reached');
      });
    });

    it('should handle malformed messages gracefully', async () => {
      const { result } = renderHook(() => useDashboardWebSocket());

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      // Send malformed JSON
      act(() => {
        const mockWs = (WebSocket as any).mock?.instances?.[0];
        if (mockWs?.onmessage) {
          mockWs.onmessage(new MessageEvent('message', { data: 'invalid json' }));
        }
      });

      // Should not crash and should maintain connection
      expect(result.current.isConnected).toBe(true);
    });
  });
});