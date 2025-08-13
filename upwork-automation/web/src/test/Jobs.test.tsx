import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import Jobs from '../pages/Jobs';
import { Job } from '../types/Job';

const theme = createTheme();

const mockJobs: Job[] = [
  {
    id: '1',
    title: 'Salesforce Agentforce Developer',
    description: 'Looking for an experienced Salesforce developer...',
    hourly_rate: 75,
    client_rating: 4.8,
    client_payment_verified: true,
    client_hire_rate: 0.8,
    posted_date: '2024-01-15T10:00:00Z',
    skills_required: ['Salesforce', 'Apex', 'Lightning'],
    job_type: 'HOURLY',
    status: 'FILTERED',
    match_score: 0.95,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
];

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
vi.mock('../hooks/useJobs', () => ({
  useJobs: () => ({
    data: {
      jobs: mockJobs,
      total: 1,
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

describe('Jobs', () => {
  it('renders jobs page title', () => {
    renderWithProviders(<Jobs />);
    expect(screen.getByText('Jobs')).toBeInTheDocument();
  });

  it('displays job table with headers', () => {
    renderWithProviders(<Jobs />);
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Budget')).toBeInTheDocument();
    expect(screen.getByText('Client')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Match Score')).toBeInTheDocument();
  });

  it('displays job data in table', () => {
    renderWithProviders(<Jobs />);
    expect(screen.getByText('Salesforce Agentforce Developer')).toBeInTheDocument();
    expect(screen.getByText('$75/hr')).toBeInTheDocument();
    expect(screen.getByText('FILTERED')).toBeInTheDocument();
    expect(screen.getByText('95%')).toBeInTheDocument();
  });

  it('has filter controls', () => {
    renderWithProviders(<Jobs />);
    expect(screen.getByLabelText('Status')).toBeInTheDocument();
    expect(screen.getByText('Refresh')).toBeInTheDocument();
  });

  it('opens job detail dialog when view button is clicked', async () => {
    renderWithProviders(<Jobs />);
    
    const viewButton = screen.getByTitle('View Details');
    fireEvent.click(viewButton);

    await waitFor(() => {
      expect(screen.getByText('Job Description')).toBeInTheDocument();
      expect(screen.getByText('Required Skills')).toBeInTheDocument();
    });
  });

  it('shows action buttons for jobs', () => {
    renderWithProviders(<Jobs />);
    expect(screen.getByTitle('View Details')).toBeInTheDocument();
    expect(screen.getByTitle('Edit Proposal')).toBeInTheDocument();
  });
});