import { render, screen } from '@testing-library/react';
import App from '../App';

// Mock all the hooks to prevent API calls during testing
vi.mock('../hooks/useSystemStatus', () => ({
  useSystemStatus: () => ({
    data: {
      automationEnabled: true,
      isPaused: false,
      queuedJobs: 0,
      systemHealth: 'healthy',
    },
    toggleAutomation: vi.fn(),
    pauseSystem: vi.fn(),
    resumeSystem: vi.fn(),
    emergencyStop: vi.fn(),
  }),
}));

vi.mock('../hooks/useJobQueue', () => ({
  useJobQueue: () => ({
    data: {
      totalJobs: 0,
      queuedJobs: 0,
      processingJobs: 0,
      completedJobs: 0,
      failedJobs: 0,
      recentActivity: [],
    },
  }),
}));

vi.mock('../hooks/useMetrics', () => ({
  useMetrics: () => ({
    data: {
      dailyApplications: [],
      successRates: [],
      systemMetrics: {
        cpuUsage: 0,
        memoryUsage: 0,
        queueHealth: 100,
      },
      totalStats: {
        totalApplications: 0,
        totalResponses: 0,
        totalHires: 0,
        averageResponseTime: 0,
      },
    },
  }),
}));

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    connectionStatus: 'Connected',
    lastMessage: null,
    sendMessage: vi.fn(),
  }),
}));

vi.mock('../hooks/useJobs', () => ({
  useJobs: () => ({
    data: {
      jobs: [],
      total: 0,
    },
    refetch: vi.fn(),
  }),
}));

vi.mock('../hooks/useProposals', () => ({
  useProposals: () => ({
    data: [],
    generateProposal: vi.fn(),
    updateProposal: vi.fn(),
    submitProposal: vi.fn(),
  }),
}));

vi.mock('../hooks/useApplications', () => ({
  useApplications: () => ({
    data: {
      applications: [],
      total: 0,
      stats: {
        totalApplications: 0,
        responseRate: 0,
        hireRate: 0,
        averageResponseTime: 0,
      },
    },
    refetch: vi.fn(),
  }),
}));

vi.mock('../hooks/useSettings', () => ({
  useSettings: () => ({
    data: {
      daily_application_limit: 30,
      min_hourly_rate: 50,
      target_hourly_rate: 75,
      min_client_rating: 4.0,
      min_hire_rate: 0.5,
      keywords_include: ['Salesforce', 'Agentforce'],
      keywords_exclude: ['WordPress'],
      automation_enabled: true,
      notification_channels: ['slack'],
    },
    updateSettings: vi.fn(),
    isLoading: false,
  }),
}));

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    // Just check that the app renders without throwing an error
    expect(document.body).toBeInTheDocument();
  });

  it('renders the main navigation', () => {
    render(<App />);
    // Check for navigation elements that should be present
    expect(screen.getAllByText('Upwork Automation')).toHaveLength(2); // One in drawer, one in header
  });

  it('displays the dashboard by default', () => {
    render(<App />);
    // Check that we're on the dashboard page by looking for the h4 heading
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
  });
});