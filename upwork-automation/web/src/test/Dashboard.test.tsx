import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import Dashboard from '../pages/Dashboard';

const theme = createTheme();

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <BrowserRouter>
          {component}
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

// Mock the hooks
vi.mock('../hooks/useSystemStatus', () => ({
  useSystemStatus: () => ({
    data: {
      automationEnabled: true,
      isPaused: false,
      queuedJobs: 5,
      activeWorkers: 2,
      systemHealth: 'healthy',
      uptime: 3600,
    },
  }),
}));

vi.mock('../hooks/useJobQueue', () => ({
  useJobQueue: () => ({
    data: {
      totalJobs: 10,
      queuedJobs: 5,
      processingJobs: 2,
      completedJobs: 3,
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
        cpuUsage: 45,
        memoryUsage: 60,
        queueHealth: 95,
      },
      totalStats: {
        totalApplications: 100,
        totalResponses: 25,
        totalHires: 5,
        averageResponseTime: 24,
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

describe('Dashboard', () => {
  it('renders dashboard title', () => {
    renderWithProviders(<Dashboard />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('displays system status cards', () => {
    renderWithProviders(<Dashboard />);
    expect(screen.getByText('System Status')).toBeInTheDocument();
    expect(screen.getByText('Queued Jobs')).toBeInTheDocument();
    expect(screen.getByText('Active Workers')).toBeInTheDocument();
    expect(screen.getByText('Uptime')).toBeInTheDocument();
  });

  it('shows correct queue count', () => {
    renderWithProviders(<Dashboard />);
    expect(screen.getByText('5')).toBeInTheDocument(); // Queued jobs count
  });

  it('displays real-time monitoring section', () => {
    renderWithProviders(<Dashboard />);
    expect(screen.getByText('Real-time Queue Activity')).toBeInTheDocument();
    expect(screen.getByText('Live')).toBeInTheDocument();
  });

  it('shows performance metrics sections', () => {
    renderWithProviders(<Dashboard />);
    expect(screen.getByText('Daily Applications')).toBeInTheDocument();
    expect(screen.getByText('Success Rate Trends')).toBeInTheDocument();
    expect(screen.getByText('System Performance')).toBeInTheDocument();
  });
});