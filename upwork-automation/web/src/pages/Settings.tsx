import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Card,
  CardContent,
  CardHeader,
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Save,
  Add,
  Delete,
  Security,
  Speed,
  FilterList,
  Notifications,
} from '@mui/icons-material';
import { useSettings } from '../hooks/useSettings';
import { SystemConfig } from '../types/SystemConfig';

const Settings: React.FC = () => {
  const { data: settings, updateSettings, isLoading } = useSettings();
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [keywordDialogOpen, setKeywordDialogOpen] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');
  const [keywordType, setKeywordType] = useState<'include' | 'exclude'>('include');
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (settings) {
      setConfig(settings);
    }
  }, [settings]);

  const handleSave = async () => {
    if (config) {
      try {
        await updateSettings(config);
        setSaveSuccess(true);
      } catch (error) {
        console.error('Failed to save settings:', error);
      }
    }
  };

  const handleConfigChange = (field: keyof SystemConfig, value: any) => {
    if (config) {
      setConfig({ ...config, [field]: value });
    }
  };

  const handleAddKeyword = () => {
    if (config && newKeyword.trim()) {
      const field = keywordType === 'include' ? 'keywords_include' : 'keywords_exclude';
      const updatedKeywords = [...config[field], newKeyword.trim()];
      setConfig({ ...config, [field]: updatedKeywords });
      setNewKeyword('');
      setKeywordDialogOpen(false);
    }
  };

  const handleRemoveKeyword = (keyword: string, type: 'include' | 'exclude') => {
    if (config) {
      const field = type === 'include' ? 'keywords_include' : 'keywords_exclude';
      const updatedKeywords = config[field].filter(k => k !== keyword);
      setConfig({ ...config, [field]: updatedKeywords });
    }
  };

  if (isLoading || !config) {
    return <Typography>Loading settings...</Typography>;
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Settings
        </Typography>
        <Button
          variant="contained"
          startIcon={<Save />}
          onClick={handleSave}
        >
          Save Changes
        </Button>
      </Box>

      <Grid container spacing={3}>
        {/* Automation Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader
              avatar={<Speed />}
              title="Automation Settings"
              subheader="Configure automation behavior and limits"
            />
            <CardContent>
              <Box mb={3}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={config.automation_enabled}
                      onChange={(e) => handleConfigChange('automation_enabled', e.target.checked)}
                    />
                  }
                  label="Enable Automation"
                />
              </Box>

              <TextField
                fullWidth
                label="Daily Application Limit"
                type="number"
                value={config.daily_application_limit}
                onChange={(e) => handleConfigChange('daily_application_limit', parseInt(e.target.value))}
                margin="normal"
                helperText="Maximum number of applications per day"
              />

              <TextField
                fullWidth
                label="Minimum Hourly Rate ($)"
                type="number"
                value={config.min_hourly_rate}
                onChange={(e) => handleConfigChange('min_hourly_rate', parseFloat(e.target.value))}
                margin="normal"
                helperText="Minimum acceptable hourly rate"
              />

              <TextField
                fullWidth
                label="Target Hourly Rate ($)"
                type="number"
                value={config.target_hourly_rate}
                onChange={(e) => handleConfigChange('target_hourly_rate', parseFloat(e.target.value))}
                margin="normal"
                helperText="Preferred hourly rate for bidding"
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Client Filters */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader
              avatar={<FilterList />}
              title="Client Filters"
              subheader="Set minimum client requirements"
            />
            <CardContent>
              <TextField
                fullWidth
                label="Minimum Client Rating"
                type="number"
                inputProps={{ min: 0, max: 5, step: 0.1 }}
                value={config.min_client_rating}
                onChange={(e) => handleConfigChange('min_client_rating', parseFloat(e.target.value))}
                margin="normal"
                helperText="Minimum client rating (0-5)"
              />

              <TextField
                fullWidth
                label="Minimum Hire Rate"
                type="number"
                inputProps={{ min: 0, max: 1, step: 0.1 }}
                value={config.min_hire_rate}
                onChange={(e) => handleConfigChange('min_hire_rate', parseFloat(e.target.value))}
                margin="normal"
                helperText="Minimum client hire rate (0-1)"
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Keywords Management */}
        <Grid item xs={12}>
          <Card>
            <CardHeader
              avatar={<FilterList />}
              title="Keywords Management"
              subheader="Manage job search keywords"
              action={
                <Button
                  startIcon={<Add />}
                  onClick={() => setKeywordDialogOpen(true)}
                >
                  Add Keyword
                </Button>
              }
            />
            <CardContent>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom color="success.main">
                    Include Keywords
                  </Typography>
                  <Box display="flex" flexWrap="wrap" gap={1} mb={2}>
                    {config.keywords_include.map((keyword, index) => (
                      <Chip
                        key={index}
                        label={keyword}
                        color="success"
                        variant="outlined"
                        onDelete={() => handleRemoveKeyword(keyword, 'include')}
                      />
                    ))}
                  </Box>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom color="error.main">
                    Exclude Keywords
                  </Typography>
                  <Box display="flex" flexWrap="wrap" gap={1} mb={2}>
                    {config.keywords_exclude.map((keyword, index) => (
                      <Chip
                        key={index}
                        label={keyword}
                        color="error"
                        variant="outlined"
                        onDelete={() => handleRemoveKeyword(keyword, 'exclude')}
                      />
                    ))}
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Notification Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader
              avatar={<Notifications />}
              title="Notification Settings"
              subheader="Configure notification channels"
            />
            <CardContent>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                Active Notification Channels
              </Typography>
              <List dense>
                {config.notification_channels.map((channel, index) => (
                  <ListItem key={index}>
                    <ListItemText primary={channel} />
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        onClick={() => {
                          const updatedChannels = config.notification_channels.filter((_, i) => i !== index);
                          handleConfigChange('notification_channels', updatedChannels);
                        }}
                      >
                        <Delete />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Safety Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader
              avatar={<Security />}
              title="Safety Settings"
              subheader="Platform compliance and safety controls"
            />
            <CardContent>
              <Typography variant="body2" paragraph>
                These settings help maintain compliance with Upwork's terms of service and prevent account issues.
              </Typography>
              
              <Box mb={2}>
                <Typography variant="body2" color="textSecondary">
                  Rate Limiting: Enabled
                </Typography>
                <Typography variant="caption">
                  Applications are spaced to mimic human behavior
                </Typography>
              </Box>

              <Box mb={2}>
                <Typography variant="body2" color="textSecondary">
                  Stealth Mode: Active
                </Typography>
                <Typography variant="caption">
                  Browser fingerprinting and detection avoidance
                </Typography>
              </Box>

              <Box mb={2}>
                <Typography variant="body2" color="textSecondary">
                  Gradual Scaling: Enabled
                </Typography>
                <Typography variant="caption">
                  Application volume increases gradually over time
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* System Status */}
        <Grid item xs={12}>
          <Card>
            <CardHeader
              title="System Status"
              subheader="Current system configuration and health"
            />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12} md={3}>
                  <Typography variant="body2" color="textSecondary">
                    Configuration Status
                  </Typography>
                  <Typography variant="body1" color="success.main">
                    Valid
                  </Typography>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Typography variant="body2" color="textSecondary">
                    Last Updated
                  </Typography>
                  <Typography variant="body1">
                    {new Date().toLocaleString()}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Typography variant="body2" color="textSecondary">
                    Active Filters
                  </Typography>
                  <Typography variant="body1">
                    {config.keywords_include.length + config.keywords_exclude.length}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={3}>
                  <Typography variant="body2" color="textSecondary">
                    Automation Status
                  </Typography>
                  <Typography variant="body1" color={config.automation_enabled ? 'success.main' : 'error.main'}>
                    {config.automation_enabled ? 'Enabled' : 'Disabled'}
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Add Keyword Dialog */}
      <Dialog open={keywordDialogOpen} onClose={() => setKeywordDialogOpen(false)}>
        <DialogTitle>Add Keyword</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Keyword"
            fullWidth
            variant="outlined"
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
          />
          <Box mt={2}>
            <FormControlLabel
              control={
                <Switch
                  checked={keywordType === 'include'}
                  onChange={(e) => setKeywordType(e.target.checked ? 'include' : 'exclude')}
                />
              }
              label={keywordType === 'include' ? 'Include Keyword' : 'Exclude Keyword'}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setKeywordDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleAddKeyword} variant="contained">Add</Button>
        </DialogActions>
      </Dialog>

      {/* Success Snackbar */}
      <Snackbar
        open={saveSuccess}
        autoHideDuration={3000}
        onClose={() => setSaveSuccess(false)}
      >
        <Alert onClose={() => setSaveSuccess(false)} severity="success">
          Settings saved successfully!
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Settings;