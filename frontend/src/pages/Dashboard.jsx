import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  LinearProgress,
  Avatar,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  PlayArrow,
  TrendingUp,
  VideoLibrary,
  Timeline,
  Settings,
  Add,
  Refresh,
} from '@mui/icons-material';
import { motion } from 'framer-motion';

const Dashboard = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    videosCreated: 347,
    totalViews: 2400000,
    engagementRate: 18.7,
    revenue: 12800,
  });

  const [recentWorkflows, setRecentWorkflows] = useState([
    {
      id: 1,
      name: 'Viral Video Pipeline',
      status: 'completed',
      lastRun: '2 hours ago',
      progress: 100,
    },
    {
      id: 2,
      name: 'Content Optimization',
      status: 'running',
      lastRun: '30 minutes ago',
      progress: 65,
    },
    {
      id: 3,
      name: 'Multi-Platform Publishing',
      status: 'idle',
      lastRun: '1 day ago',
      progress: 0,
    },
  ]);

  const quickActions = [
    {
      title: 'Create Workflow',
      description: 'Build automated video creation pipelines',
      icon: <Timeline />,
      action: () => navigate('/workflow/builder'),
      color: '#06b6d4',
    },
    {
      title: 'Content Studio',
      description: 'Create videos with AI assistance',
      icon: <VideoLibrary />,
      action: () => navigate('/studio'),
      color: '#a855f7',
    },
    {
      title: 'View Analytics',
      description: 'Monitor performance and trends',
      icon: <TrendingUp />,
      action: () => navigate('/analytics'),
      color: '#10b981',
    },
    {
      title: 'Settings',
      description: 'Configure your preferences',
      icon: <Settings />,
      action: () => navigate('/settings'),
      color: '#f59e0b',
    },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'running': return '#06b6d4';
      case 'idle': return '#64748b';
      case 'error': return '#ef4444';
      default: return '#64748b';
    }
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
  };

  return (
    <Box sx={{ p: 3, maxWidth: '1400px', mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 700, mb: 1 }}>
            CINEMATRIX Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Welcome back! Here's your AI video creation overview.
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<Refresh />}
          onClick={() => window.location.reload()}
          sx={{ borderRadius: 2 }}
        >
          Refresh
        </Button>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {[
          {
            title: 'Videos Created',
            value: stats.videosCreated,
            change: '+23%',
            color: '#06b6d4',
            icon: <VideoLibrary />,
          },
          {
            title: 'Total Views',
            value: formatNumber(stats.totalViews),
            change: '+15%',
            color: '#a855f7',
            icon: <PlayArrow />,
          },
          {
            title: 'Engagement Rate',
            value: `${stats.engagementRate}%`,
            change: '+5.2%',
            color: '#10b981',
            icon: <TrendingUp />,
          },
          {
            title: 'Revenue',
            value: `$${formatNumber(stats.revenue)}`,
            change: '+12%',
            color: '#f59e0b',
            icon: <Timeline />,
          },
        ].map((stat, index) => (
          <Grid item xs={12} sm={6} lg={3} key={index}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card
                sx={{
                  background: 'rgba(15, 23, 42, 0.6)',
                  backdropFilter: 'blur(16px)',
                  border: '1px solid rgba(148, 163, 184, 0.2)',
                  borderRadius: 3,
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 24px rgba(0, 0, 0, 0.3)',
                  },
                }}
              >
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Avatar
                      sx={{
                        bgcolor: stat.color + '20',
                        color: stat.color,
                        mr: 2,
                      }}
                    >
                      {stat.icon}
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        {stat.value}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {stat.title}
                      </Typography>
                    </Box>
                  </Box>
                  <Chip
                    label={stat.change}
                    size="small"
                    sx={{
                      bgcolor: stat.color + '20',
                      color: stat.color,
                      fontWeight: 600,
                    }}
                  />
                </CardContent>
              </Card>
            </motion.div>
          </Grid>
        ))}
      </Grid>

      {/* Quick Actions */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" sx={{ mb: 3, fontWeight: 600 }}>
          Quick Actions
        </Typography>
        <Grid container spacing={3}>
          {quickActions.map((action, index) => (
            <Grid item xs={12} sm={6} lg={3} key={index}>
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.1 + 0.4 }}
              >
                <Card
                  sx={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    backdropFilter: 'blur(16px)',
                    border: '1px solid rgba(148, 163, 184, 0.2)',
                    borderRadius: 3,
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: '0 12px 24px rgba(0, 0, 0, 0.3)',
                      borderColor: action.color + '40',
                    },
                  }}
                  onClick={action.action}
                >
                  <CardContent sx={{ p: 3, textAlign: 'center' }}>
                    <Avatar
                      sx={{
                        bgcolor: action.color + '20',
                        color: action.color,
                        width: 56,
                        height: 56,
                        mx: 'auto',
                        mb: 2,
                      }}
                    >
                      {action.icon}
                    </Avatar>
                    <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
                      {action.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {action.description}
                    </Typography>
                  </CardContent>
                </Card>
              </motion.div>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Recent Workflows */}
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            Recent Workflows
          </Typography>
          <Button
            variant="outlined"
            startIcon={<Add />}
            onClick={() => navigate('/workflow/builder')}
            sx={{ borderRadius: 2 }}
          >
            New Workflow
          </Button>
        </Box>

        <Grid container spacing={3}>
          {recentWorkflows.map((workflow, index) => (
            <Grid item xs={12} md={6} lg={4} key={workflow.id}>
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 + 0.6 }}
              >
                <Card
                  sx={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    backdropFilter: 'blur(16px)',
                    border: '1px solid rgba(148, 163, 184, 0.2)',
                    borderRadius: 3,
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: '0 8px 16px rgba(0, 0, 0, 0.3)',
                    },
                  }}
                >
                  <CardContent sx={{ p: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Box>
                        <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                          {workflow.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Last run: {workflow.lastRun}
                        </Typography>
                      </Box>
                      <Chip
                        label={workflow.status}
                        size="small"
                        sx={{
                          bgcolor: getStatusColor(workflow.status) + '20',
                          color: getStatusColor(workflow.status),
                          textTransform: 'capitalize',
                        }}
                      />
                    </Box>

                    {workflow.status === 'running' && (
                      <Box sx={{ mb: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                          <Typography variant="body2" color="text.secondary">
                            Progress
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {workflow.progress}%
                          </Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={workflow.progress}
                          sx={{
                            height: 6,
                            borderRadius: 3,
                            bgcolor: 'rgba(148, 163, 184, 0.2)',
                            '& .MuiLinearProgress-bar': {
                              bgcolor: getStatusColor(workflow.status),
                              borderRadius: 3,
                            },
                          }}
                        />
                      </Box>
                    )}

                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button
                        variant="outlined"
                        size="small"
                        onClick={() => navigate(`/workflow/${workflow.id}`)}
                        sx={{ flex: 1, borderRadius: 2 }}
                      >
                        View
                      </Button>
                      <Tooltip title="Run Workflow">
                        <IconButton
                          size="small"
                          sx={{
                            bgcolor: getStatusColor(workflow.status) + '20',
                            color: getStatusColor(workflow.status),
                            '&:hover': {
                              bgcolor: getStatusColor(workflow.status) + '30',
                            },
                          }}
                        >
                          <PlayArrow fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </CardContent>
                </Card>
              </motion.div>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  );
};

export default Dashboard;