import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  Card,
  CardContent,
  Rating,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Visibility,
  Edit,
  Send,
  Refresh,
  AttachMoney,
  Schedule,
  Person,
  Star,
} from '@mui/icons-material';
import { useJobs } from '../hooks/useJobs';
import { useProposals } from '../hooks/useProposals';
import { useJobsWebSocket } from '../hooks/useWebSocketChannels';
import { Job, JobStatus } from '../types/Job';
import { Proposal } from '../types/Proposal';

const Jobs: React.FC = () => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [proposalDialogOpen, setProposalDialogOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState<JobStatus | 'all'>('all');

  // WebSocket connection for real-time job updates
  const {
    connectionStatus,
    isConnected,
    jobUpdates,
    proposalUpdates,
    applicationUpdates,
  } = useJobsWebSocket();
  
  const { data: jobsData, refetch: refetchJobs } = useJobs({
    page: page + 1,
    limit: rowsPerPage,
    status: filterStatus === 'all' ? undefined : filterStatus,
  });

  const { 
    generateProposal, 
    updateProposal, 
    submitProposal,
    data: proposalData 
  } = useProposals();

  const jobs = jobsData?.jobs || [];
  const totalJobs = jobsData?.total || 0;

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleViewJob = (job: Job) => {
    setSelectedJob(job);
  };

  const handleEditProposal = (job: Job) => {
    setSelectedJob(job);
    setProposalDialogOpen(true);
  };

  const handleGenerateProposal = async (jobId: string) => {
    try {
      await generateProposal(jobId);
      refetchJobs();
    } catch (error) {
      console.error('Failed to generate proposal:', error);
    }
  };

  const handleSubmitProposal = async (jobId: string) => {
    try {
      await submitProposal(jobId);
      refetchJobs();
    } catch (error) {
      console.error('Failed to submit proposal:', error);
    }
  };

  const getStatusColor = (status: JobStatus) => {
    switch (status) {
      case 'DISCOVERED': return 'info';
      case 'FILTERED': return 'warning';
      case 'QUEUED': return 'primary';
      case 'APPLIED': return 'success';
      case 'REJECTED': return 'error';
      default: return 'default';
    }
  };

  const formatBudget = (job: Job) => {
    if (job.hourly_rate) {
      return `$${job.hourly_rate}/hr`;
    }
    if (job.budget_min && job.budget_max) {
      return `$${job.budget_min} - $${job.budget_max}`;
    }
    return 'Not specified';
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Jobs
        </Typography>
        <Box display="flex" gap={2}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={filterStatus}
              label="Status"
              onChange={(e) => setFilterStatus(e.target.value as JobStatus | 'all')}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="DISCOVERED">Discovered</MenuItem>
              <MenuItem value="FILTERED">Filtered</MenuItem>
              <MenuItem value="QUEUED">Queued</MenuItem>
              <MenuItem value="APPLIED">Applied</MenuItem>
              <MenuItem value="REJECTED">Rejected</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => refetchJobs()}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Title</TableCell>
              <TableCell>Budget</TableCell>
              <TableCell>Client</TableCell>
              <TableCell>Posted</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Match Score</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {jobs.map((job) => (
              <TableRow key={job.id}>
                <TableCell>
                  <Typography variant="subtitle2" noWrap sx={{ maxWidth: 200 }}>
                    {job.title}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Box display="flex" alignItems="center">
                    <AttachMoney fontSize="small" />
                    {formatBudget(job)}
                  </Box>
                </TableCell>
                <TableCell>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Rating value={job.client_rating} readOnly size="small" />
                    <Typography variant="caption">
                      ({job.client_rating})
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  <Typography variant="caption">
                    {new Date(job.posted_date).toLocaleDateString()}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={job.status}
                    color={getStatusColor(job.status) as any}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="primary">
                    {Math.round(job.match_score * 100)}%
                  </Typography>
                </TableCell>
                <TableCell>
                  <Box display="flex" gap={1}>
                    <IconButton
                      size="small"
                      onClick={() => handleViewJob(job)}
                      title="View Details"
                    >
                      <Visibility />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleEditProposal(job)}
                      title="Edit Proposal"
                    >
                      <Edit />
                    </IconButton>
                    {job.status === 'QUEUED' && (
                      <IconButton
                        size="small"
                        onClick={() => handleSubmitProposal(job.id)}
                        title="Submit Application"
                        color="primary"
                      >
                        <Send />
                      </IconButton>
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={totalJobs}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </TableContainer>

      {/* Job Detail Dialog */}
      <Dialog
        open={!!selectedJob && !proposalDialogOpen}
        onClose={() => setSelectedJob(null)}
        maxWidth="md"
        fullWidth
      >
        {selectedJob && (
          <>
            <DialogTitle>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="h6">{selectedJob.title}</Typography>
                <Chip
                  label={selectedJob.status}
                  color={getStatusColor(selectedJob.status) as any}
                  size="small"
                />
              </Box>
            </DialogTitle>
            <DialogContent>
              <Grid container spacing={3}>
                <Grid item xs={12} md={8}>
                  <Typography variant="h6" gutterBottom>
                    Job Description
                  </Typography>
                  <Typography variant="body2" paragraph>
                    {selectedJob.description}
                  </Typography>
                  
                  <Typography variant="h6" gutterBottom>
                    Required Skills
                  </Typography>
                  <Box display="flex" flexWrap="wrap" gap={1} mb={2}>
                    {selectedJob.skills_required.map((skill, index) => (
                      <Chip key={index} label={skill} size="small" variant="outlined" />
                    ))}
                  </Box>
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        Job Details
                      </Typography>
                      
                      <Box display="flex" alignItems="center" mb={2}>
                        <AttachMoney />
                        <Box ml={1}>
                          <Typography variant="body2" color="textSecondary">
                            Budget
                          </Typography>
                          <Typography variant="body1">
                            {formatBudget(selectedJob)}
                          </Typography>
                        </Box>
                      </Box>
                      
                      <Box display="flex" alignItems="center" mb={2}>
                        <Person />
                        <Box ml={1}>
                          <Typography variant="body2" color="textSecondary">
                            Client Rating
                          </Typography>
                          <Box display="flex" alignItems="center">
                            <Rating value={selectedJob.client_rating} readOnly size="small" />
                            <Typography variant="body2" ml={1}>
                              ({selectedJob.client_rating})
                            </Typography>
                          </Box>
                        </Box>
                      </Box>
                      
                      <Box display="flex" alignItems="center" mb={2}>
                        <Schedule />
                        <Box ml={1}>
                          <Typography variant="body2" color="textSecondary">
                            Posted
                          </Typography>
                          <Typography variant="body1">
                            {new Date(selectedJob.posted_date).toLocaleDateString()}
                          </Typography>
                        </Box>
                      </Box>
                      
                      <Box display="flex" alignItems="center">
                        <Star />
                        <Box ml={1}>
                          <Typography variant="body2" color="textSecondary">
                            Match Score
                          </Typography>
                          <Typography variant="body1" color="primary">
                            {Math.round(selectedJob.match_score * 100)}%
                          </Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedJob(null)}>
                Close
              </Button>
              <Button
                variant="contained"
                onClick={() => handleEditProposal(selectedJob)}
              >
                Edit Proposal
              </Button>
              {selectedJob.status === 'FILTERED' && (
                <Button
                  variant="contained"
                  color="primary"
                  onClick={() => handleGenerateProposal(selectedJob.id)}
                >
                  Generate Proposal
                </Button>
              )}
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Proposal Edit Dialog */}
      <ProposalEditDialog
        open={proposalDialogOpen}
        onClose={() => setProposalDialogOpen(false)}
        job={selectedJob}
        proposal={proposalData?.find(p => p.job_id === selectedJob?.id)}
        onSave={async (proposalId: string, data: Partial<Proposal>) => {
          await updateProposal(proposalId, data);
        }}
        onSubmit={handleSubmitProposal}
      />
    </Box>
  );
};

// Proposal Edit Dialog Component
interface ProposalEditDialogProps {
  open: boolean;
  onClose: () => void;
  job: Job | null;
  proposal?: Proposal;
  onSave: (proposalId: string, data: Partial<Proposal>) => Promise<void>;
  onSubmit: (jobId: string) => Promise<void>;
}

const ProposalEditDialog: React.FC<ProposalEditDialogProps> = ({
  open,
  onClose,
  job,
  proposal,
  onSave,
  onSubmit,
}) => {
  const [content, setContent] = useState(proposal?.content || '');
  const [bidAmount, setBidAmount] = useState(proposal?.bid_amount || 0);

  React.useEffect(() => {
    if (proposal) {
      setContent(proposal.content);
      setBidAmount(proposal.bid_amount);
    }
  }, [proposal]);

  const handleSave = async () => {
    if (proposal) {
      await onSave(proposal.id, { content, bid_amount: bidAmount });
      onClose();
    }
  };

  const handleSubmit = async () => {
    if (job) {
      await onSubmit(job.id);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Edit Proposal - {job?.title}
      </DialogTitle>
      <DialogContent>
        <Box mb={3}>
          <TextField
            fullWidth
            label="Bid Amount ($)"
            type="number"
            value={bidAmount}
            onChange={(e) => setBidAmount(Number(e.target.value))}
            margin="normal"
          />
        </Box>
        <TextField
          fullWidth
          multiline
          rows={12}
          label="Proposal Content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          variant="outlined"
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleSave} variant="outlined">
          Save Draft
        </Button>
        <Button onClick={handleSubmit} variant="contained" color="primary">
          Submit Application
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default Jobs;