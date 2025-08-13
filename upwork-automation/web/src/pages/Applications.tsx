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
  Grid,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,

  Divider,
} from '@mui/material';
import {
  Visibility,
  Refresh,
  TrendingUp,
  Schedule,
  AttachMoney,
  Person,
  CheckCircle,
  Cancel,
  HourglassEmpty,
} from '@mui/icons-material';
import { useApplications } from '../hooks/useApplications';
import { Application, ApplicationStatus } from '../types/Application';

const Applications: React.FC = () => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [selectedApplication, setSelectedApplication] = useState<Application | null>(null);
  const [filterStatus, setFilterStatus] = useState<ApplicationStatus | 'all'>('all');
  const [dateRange, setDateRange] = useState('7'); // days

  const { data: applicationsData, refetch } = useApplications({
    page: page + 1,
    limit: rowsPerPage,
    status: filterStatus === 'all' ? undefined : filterStatus,
    days: parseInt(dateRange),
  });

  const applications = applicationsData?.applications || [];
  const totalApplications = applicationsData?.total || 0;
  const stats = applicationsData?.stats;

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleViewApplication = (application: Application) => {
    setSelectedApplication(application);
  };

  const getStatusColor = (status: ApplicationStatus) => {
    switch (status) {
      case 'SUBMITTED': return 'primary';
      case 'VIEWED': return 'info';
      case 'RESPONDED': return 'warning';
      case 'INTERVIEWED': return 'secondary';
      case 'HIRED': return 'success';
      case 'REJECTED': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: ApplicationStatus) => {
    switch (status) {
      case 'HIRED': return <CheckCircle color="success" />;
      case 'REJECTED': return <Cancel color="error" />;
      case 'INTERVIEWED': return <Person color="secondary" />;
      default: return <HourglassEmpty color="action" />;
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 24) {
      return `${diffInHours}h ago`;
    }
    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays}d ago`;
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Applications
        </Typography>
        <Box display="flex" gap={2}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={filterStatus}
              label="Status"
              onChange={(e) => setFilterStatus(e.target.value as ApplicationStatus | 'all')}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="SUBMITTED">Submitted</MenuItem>
              <MenuItem value="VIEWED">Viewed</MenuItem>
              <MenuItem value="RESPONDED">Responded</MenuItem>
              <MenuItem value="INTERVIEWED">Interviewed</MenuItem>
              <MenuItem value="HIRED">Hired</MenuItem>
              <MenuItem value="REJECTED">Rejected</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 100 }}>
            <InputLabel>Period</InputLabel>
            <Select
              value={dateRange}
              label="Period"
              onChange={(e) => setDateRange(e.target.value)}
            >
              <MenuItem value="7">7 days</MenuItem>
              <MenuItem value="30">30 days</MenuItem>
              <MenuItem value="90">90 days</MenuItem>
              <MenuItem value="365">1 year</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => refetch()}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Statistics Cards */}
      {stats && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      Total Applications
                    </Typography>
                    <Typography variant="h4">
                      {stats.totalApplications}
                    </Typography>
                  </Box>
                  <TrendingUp color="primary" />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      Response Rate
                    </Typography>
                    <Typography variant="h4">
                      {Math.round(stats.responseRate * 100)}%
                    </Typography>
                  </Box>
                  <Person color="info" />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      Hire Rate
                    </Typography>
                    <Typography variant="h4">
                      {Math.round(stats.hireRate * 100)}%
                    </Typography>
                  </Box>
                  <CheckCircle color="success" />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      Avg. Response Time
                    </Typography>
                    <Typography variant="h4">
                      {Math.round(stats.averageResponseTime)}h
                    </Typography>
                  </Box>
                  <Schedule color="warning" />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Job Title</TableCell>
              <TableCell>Bid Amount</TableCell>
              <TableCell>Submitted</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Client Response</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {applications.map((application) => (
              <TableRow key={application.id}>
                <TableCell>
                  <Typography variant="subtitle2" noWrap sx={{ maxWidth: 250 }}>
                    {application.job?.title || 'Unknown Job'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Box display="flex" alignItems="center">
                    <AttachMoney fontSize="small" />
                    ${application.proposal?.bid_amount || 0}/hr
                  </Box>
                </TableCell>
                <TableCell>
                  <Typography variant="caption">
                    {formatTimeAgo(application.submitted_at)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Box display="flex" alignItems="center" gap={1}>
                    {getStatusIcon(application.status)}
                    <Chip
                      label={application.status}
                      color={getStatusColor(application.status) as any}
                      size="small"
                    />
                  </Box>
                </TableCell>
                <TableCell>
                  {application.client_response_date ? (
                    <Typography variant="caption">
                      {formatTimeAgo(application.client_response_date)}
                    </Typography>
                  ) : (
                    <Typography variant="caption" color="textSecondary">
                      No response
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => handleViewApplication(application)}
                    title="View Details"
                  >
                    <Visibility />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={totalApplications}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </TableContainer>

      {/* Application Detail Dialog */}
      <Dialog
        open={!!selectedApplication}
        onClose={() => setSelectedApplication(null)}
        maxWidth="md"
        fullWidth
      >
        {selectedApplication && (
          <>
            <DialogTitle>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="h6">
                  Application Details
                </Typography>
                <Chip
                  label={selectedApplication.status}
                  color={getStatusColor(selectedApplication.status) as any}
                  size="small"
                />
              </Box>
            </DialogTitle>
            <DialogContent>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>
                    Job Information
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    <strong>Title:</strong> {selectedApplication.job?.title}
                  </Typography>
                  <Typography variant="body2" paragraph>
                    <strong>Description:</strong> {selectedApplication.job?.description}
                  </Typography>
                  
                  <Divider sx={{ my: 2 }} />
                  
                  <Typography variant="h6" gutterBottom>
                    Proposal
                  </Typography>
                  <Typography variant="body2" paragraph>
                    {selectedApplication.proposal?.content}
                  </Typography>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>
                    Application Timeline
                  </Typography>
                  
                  <Box mb={2}>
                    <Typography variant="body2" color="textSecondary">
                      Submitted
                    </Typography>
                    <Typography variant="body1">
                      {new Date(selectedApplication.submitted_at).toLocaleString()}
                    </Typography>
                  </Box>
                  
                  {selectedApplication.client_response_date && (
                    <Box mb={2}>
                      <Typography variant="body2" color="textSecondary">
                        Client Response
                      </Typography>
                      <Typography variant="body1">
                        {new Date(selectedApplication.client_response_date).toLocaleString()}
                      </Typography>
                    </Box>
                  )}
                  
                  {selectedApplication.client_response && (
                    <Box mb={2}>
                      <Typography variant="body2" color="textSecondary">
                        Client Message
                      </Typography>
                      <Typography variant="body1">
                        {selectedApplication.client_response}
                      </Typography>
                    </Box>
                  )}
                  
                  <Box mb={2}>
                    <Typography variant="body2" color="textSecondary">
                      Bid Amount
                    </Typography>
                    <Typography variant="body1">
                      ${selectedApplication.proposal?.bid_amount}/hr
                    </Typography>
                  </Box>
                  
                  {selectedApplication.upwork_application_id && (
                    <Box mb={2}>
                      <Typography variant="body2" color="textSecondary">
                        Upwork Application ID
                      </Typography>
                      <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
                        {selectedApplication.upwork_application_id}
                      </Typography>
                    </Box>
                  )}
                </Grid>
              </Grid>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedApplication(null)}>
                Close
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default Applications;