import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import Layout from '../components/Layout';

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

// Mock the system status hook
vi.mock('../hooks/useSystemStatus', () => ({
  useSystemStatus: () => ({
    data: {
      automationEnabled: true,
      isPaused: false,
      queuedJobs: 3,
      systemHealth: 'healthy',
    },
    toggleAutomation: vi.fn(),
    pauseSystem: vi.fn(),
    resumeSystem: vi.fn(),
    emergencyStop: vi.fn(),
  }),
}));

describe('Layout', () => {
  it('renders application title', () => {
    renderWithProviders(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );
    expect(screen.getByText('Upwork Automation')).toBeInTheDocument();
  });

  it('renders navigation menu items', () => {
    renderWithProviders(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Jobs')).toBeInTheDocument();
    expect(screen.getByText('Applications')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('displays system controls in header', () => {
    renderWithProviders(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );
    expect(screen.getByLabelText(/Auto/)).toBeInTheDocument();
    expect(screen.getByTitle('Pause System')).toBeInTheDocument();
    expect(screen.getByTitle('Emergency Stop')).toBeInTheDocument();
  });

  it('shows job queue badge', () => {
    renderWithProviders(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );
    // The badge should show the number of queued jobs (3 from mock)
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders child content', () => {
    renderWithProviders(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('handles automation toggle', () => {
    const mockToggle = vi.fn();
    vi.mocked(require('../hooks/useSystemStatus').useSystemStatus).mockReturnValue({
      data: {
        automationEnabled: false,
        isPaused: false,
        queuedJobs: 0,
        systemHealth: 'healthy',
      },
      toggleAutomation: mockToggle,
      pauseSystem: vi.fn(),
      resumeSystem: vi.fn(),
      emergencyStop: vi.fn(),
    });

    renderWithProviders(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    const autoSwitch = screen.getByRole('checkbox');
    fireEvent.click(autoSwitch);
    expect(mockToggle).toHaveBeenCalled();
  });
});