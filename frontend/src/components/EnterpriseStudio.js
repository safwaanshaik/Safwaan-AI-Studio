import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { 
  Box, 
  Grid, 
  Paper, 
  Typography, 
  TextField, 
  Button, 
  Select, 
  MenuItem, 
  FormControl, 
  InputLabel,
  Slider,
  Chip,
  Card,
  CardContent,
  CardMedia,
  CircularProgress,
  Divider,
  IconButton,
  Tabs,
  Tab,
  Alert,
  AlertTitle,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Switch,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  LinearProgress
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { 
  ExpandMore, 
  PlayArrow, 
  Pause, 
  Save, 
  CloudUpload, 
  Edit, 
  History, 
  Settings, 
  Info, 
  Warning, 
  CheckCircle,
  VideoLibrary,
  HelpOutline,
  Tune,
  CameraAlt,
  MovieCreation,
  YouTube,
  TikTok,
  Instagram,
  Twitter,
  CloudDownload,
  Delete,
  Star,
  StarBorder,
  FormatQuote,
  Speed
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { toast } from 'react-toastify';
import { debounce } from 'lodash';
import ReactPlayer from 'react-player';

// Import project services and context
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

// Import custom components
import ModelComparisonCard from './studio/ModelComparisonCard';
import GenerationHistoryPanel from './studio/GenerationHistoryPanel';
import AdvancedOptionsPanel from './studio/AdvancedOptionsPanel';
import PromptSuggestionsPanel from './studio/PromptSuggestionsPanel';
import LivePreview from './studio/LivePreview';
import StatusPanel from './studio/StatusPanel';
import ModelSelector from './studio/ModelSelector';
import CostEstimator from './studio/CostEstimator';
import ResolutionPicker from './studio/ResolutionPicker';

// Constants and configuration
const QUALITY_TIERS = {
  ECONOMY: { label: 'Economy', description: 'Basic quality, faster generation', color: '#4CAF50' },
  STANDARD: { label: 'Standard', description: 'Balanced quality and speed', color: '#2196F3' },
  PREMIUM: { label: 'Premium', description: 'High quality, slower generation', color: '#9C27B0' },
  ULTRA: { label: 'Ultra', description: 'Maximum quality, business tier only', color: '#F44336' }
};

const CONTENT_CATEGORIES = {
  GENERAL: { label: 'General', icon: <MovieCreation /> },
  CINEMATIC: { label: 'Cinematic', icon: <VideoLibrary /> },
  ANIMATED: { label: 'Animated', icon: <MovieCreation /> },
  PRODUCT: { label: 'Product', icon: <CameraAlt /> },
  TUTORIAL: { label: 'Tutorial', icon: <HelpOutline /> },
  STYLIZED: { label: 'Stylized', icon: <Tune /> }
};

const DEFAULT_RESOLUTIONS = [
  { width: 768, height: 768, label: 'Square (768×768)' },
  { width: 1024, height: 576, label: 'Landscape HD (1024×576)' },
  { width: 576, height: 1024, label: 'Portrait HD (576×1024)' },
  { width: 1920, height: 1080, label: 'Full HD (1920×1080)' },
  { width: 3840, height: 2160, label: '4K (3840×2160)' },
];

const DEFAULT_DURATIONS = [
  { value: 5, label: '5 seconds' },
  { value: 15, label: '15 seconds' },
  { value: 30, label: '30 seconds' },
  { value: 45, label: '45 seconds' },
  { value: 60, label: '60 seconds' },
  { value: 90, label: '90 seconds' },
];

// Styled components
const PromptField = styled(TextField)(({ theme }) => ({
  '& .MuiOutlinedInput-root': {
    borderRadius: theme.shape.borderRadius,
    backgroundColor: theme.palette.background.paper,
    transition: theme.transitions.create(['border-color', 'box-shadow']),
    '&:hover': {
      borderColor: theme.palette.primary.main,
    },
    '&.Mui-focused': {
      boxShadow: `0 0 0 2px ${theme.palette.primary.light}`,
    },
  },
  '& .MuiOutlinedInput-input': {
    padding: '16px',
    fontSize: '1.1rem',
    lineHeight: 1.5,
  },
}));

const StyledChip = styled(Chip)(({ theme, color }) => ({
  backgroundColor: color || theme.palette.primary.main,
  color: theme.palette.common.white,
  fontWeight: 'bold',
  '&:hover': {
    backgroundColor: color ? `${color}DD` : theme.palette.primary.dark,
  },
}));

const ThumbnailCard = styled(Card)(({ theme }) => ({
  position: 'relative',
  overflow: 'hidden',
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[2],
  cursor: 'pointer',
  transition: 'transform 0.3s ease, box-shadow 0.3s ease',
  '&:hover': {
    transform: 'translateY(-5px)',
    boxShadow: theme.shadows[4],
  },
}));

const StatusIndicator = styled('div')(({ theme, status }) => {
  const colors = {
    pending: theme.palette.grey[500],
    queued: theme.palette.info.light,
    processing: theme.palette.warning.main,
    completed: theme.palette.success.main,
    failed: theme.palette.error.main,
  };
  
  return {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    backgroundColor: colors[status] || colors.pending,
    display: 'inline-block',
    marginRight: theme.spacing(1),
  };
});

/**
 * EnterpriseStudio component provides an advanced interface for AI video generation 
 * with premium features like model selection, quality tiers, and advanced options.
 */
const EnterpriseStudio = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { projectId } = useParams();
  const queryClient = useQueryClient();
  const promptInputRef = useRef(null);
  
  // State for video generation form
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [selectedModel, setSelectedModel] = useState(null);
  const [qualityTier, setQualityTier] = useState('STANDARD');
  const [contentCategory, setContentCategory] = useState('GENERAL');
  const [resolution, setResolution] = useState({ width: 1024, height: 576 });
  const [duration, setDuration] = useState(15);
  const [fps, setFps] = useState(24);
  const [style, setStyle] = useState('cinematic');
  const [useCache, setUseCache] = useState(true);
  const [saveToGallery, setSaveToGallery] = useState(true);
  
  // Advanced options
  const [advancedOptions, setAdvancedOptions] = useState({
    seed: null,
    guidanceScale: 7.5,
    motionStrength: 0.8,
    customParameters: {},
  });
  
  // UI state
  const [activeTab, setActiveTab] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentGeneration, setCurrentGeneration] = useState(null);
  const [estimatedCost, setEstimatedCost] = useState(null);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [showModelComparison, setShowModelComparison] = useState(false);
  const [isPreviewExpanded, setIsPreviewExpanded] = useState(false);
  
  // Polling state for generation status
  const [statusPollingInterval, setStatusPollingInterval] = useState(null);
  
  // Load available models
  const { 
    data: models,
    isLoading: isLoadingModels,
    isError: isErrorModels,
    error: modelsError
  } = useQuery(
    ['models'], 
    () => api.get('/api/v1/ai-models/models').then(res => res.data),
    {
      onSuccess: (data) => {
        // Set the first available model as default if none is selected
        if (!selectedModel && data && data.length > 0) {
          // Find a default model based on quality tier
          const defaultModel = data.find(model => 
            model.status === 'available' && 
            model.supported_quality_tiers.includes(qualityTier)
          );
          
          setSelectedModel(defaultModel?.id || data[0].id);
        }
      },
      staleTime: 60000, // 1 minute
    }
  );
  
  // Load user's subscription tier and quota
  const {
    data: quotaData,
    isLoading: isLoadingQuota,
  } = useQuery(
    ['quota'], 
    () => api.get('/api/v1/ai-models/quota').then(res => res.data),
    {
      staleTime: 300000, // 5 minutes
    }
  );
  
  // Load recent generations for this project
  const {
    data: recentGenerations,
    isLoading: isLoadingRecent,
    refetch: refetchRecent,
  } = useQuery(
    ['recent-generations', projectId], 
    () => api.get(`/api/v1/projects/${projectId}/generations`).then(res => res.data),
    {
      enabled: !!projectId,
      staleTime: 30000, // 30 seconds
    }
  );
  
  // Mutation for cost estimation
  const estimateMutation = useMutation(
    (requestData) => api.post('/api/v1/ai-models/estimate', requestData),
    {
      onSuccess: (response) => {
        setEstimatedCost(response.data);
      },
      onError: (error) => {
        console.error('Estimation error:', error);
        toast.error('Failed to estimate generation cost');
      }
    }
  );
  
  // Mutation for video generation
  const generateMutation = useMutation(
    (requestData) => api.post('/api/v1/ai-models/generate', requestData),
    {
      onSuccess: (response) => {
        console.log('Generation started:', response.data);
        setCurrentGeneration(response.data);
        setIsGenerating(true);
        
        // Start polling for status updates
        startStatusPolling(response.data.request_id);
        
        // Refresh recent generations after a short delay
        setTimeout(() => refetchRecent(), 2000);
        
        toast.success('Video generation started successfully');
      },
      onError: (error) => {
        console.error('Generation error:', error);
        setIsGenerating(false);
        
        const errorMsg = error.response?.data?.detail || 'Failed to start video generation';
        toast.error(errorMsg);
      }
    }
  );
  
  // Mutation for fetching generation status
  const statusMutation = useMutation(
    (requestId) => api.get(`/api/v1/ai-models/status/${requestId}`),
    {
      onSuccess: (response) => {
        const statusData = response.data;
        setCurrentGeneration(statusData);
        
        // If generation is complete or failed, stop polling
        if (['completed', 'failed', 'cancelled'].includes(statusData.status)) {
          stopStatusPolling();
          setIsGenerating(false);
          
          if (statusData.status === 'completed') {
            toast.success('Video generation completed successfully');
            refetchRecent();
          } else if (statusData.status === 'failed') {
            toast.error(`Generation failed: ${statusData.error || 'Unknown error'}`);
          }
        }
      },
      onError: (error) => {
        console.error('Status fetch error:', error);
        // Don't stop polling on temporary errors
      }
    }
  );
  
  // Debounced cost estimation
  const debouncedEstimate = useCallback(
    debounce((requestData) => {
      if (requestData.prompt.trim().length > 3) {
        estimateMutation.mutate(requestData);
      }
    }, 500),
    []
  );
  
  // Update cost estimation whenever relevant parameters change
  useEffect(() => {
    if (prompt.trim().length > 3) {
      const requestData = {
        prompt,
        model_id: selectedModel,
        quality_tier: qualityTier,
        content_category: contentCategory,
        duration,
        width: resolution.width,
        height: resolution.height,
      };
      
      debouncedEstimate(requestData);
    }
  }, [prompt, selectedModel, qualityTier, contentCategory, duration, resolution, debouncedEstimate]);
  
  // Start polling for generation status
  const startStatusPolling = (requestId) => {
    // Clear any existing interval
    if (statusPollingInterval) {
      clearInterval(statusPollingInterval);
    }
    
    // Create new polling interval
    const interval = setInterval(() => {
      statusMutation.mutate(requestId);
    }, 2000); // Poll every 2 seconds
    
    setStatusPollingInterval(interval);
  };
  
  // Stop polling for generation status
  const stopStatusPolling = () => {
    if (statusPollingInterval) {
      clearInterval(statusPollingInterval);
      setStatusPollingInterval(null);
    }
  };
  
  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (statusPollingInterval) {
        clearInterval(statusPollingInterval);
      }
    };
  }, [statusPollingInterval]);
  
  // Handle prompt change
  const handlePromptChange = (event) => {
    setPrompt(event.target.value);
  };
  
  // Handle negative prompt change
  const handleNegativePromptChange = (event) => {
    setNegativePrompt(event.target.value);
  };
  
  // Handle quality tier change
  const handleQualityTierChange = (event) => {
    const newTier = event.target.value;
    setQualityTier(newTier);
    
    // If the current model doesn't support this tier, find one that does
    if (models) {
      const currentModel = models.find(model => model.id === selectedModel);
      if (currentModel && !currentModel.supported_quality_tiers.includes(newTier)) {
        // Find a model that supports this tier
        const compatibleModel = models.find(model => 
          model.status === 'available' && 
          model.supported_quality_tiers.includes(newTier)
        );
        
        if (compatibleModel) {
          setSelectedModel(compatibleModel.id);
          toast.info(`Model changed to ${compatibleModel.name} to support ${QUALITY_TIERS[newTier].label} quality`);
        }
      }
    }
  };
  
  // Handle content category change
  const handleCategoryChange = (event) => {
    const newCategory = event.target.value;
    setContentCategory(newCategory);
    
    // If the current model doesn't support this category, find one that does
    if (models) {
      const currentModel = models.find(model => model.id === selectedModel);
      if (currentModel && !currentModel.supported_content_categories.includes(newCategory)) {
        // Find a model that supports this category
        const compatibleModel = models.find(model => 
          model.status === 'available' && 
          model.supported_content_categories.includes(newCategory)
        );
        
        if (compatibleModel) {
          setSelectedModel(compatibleModel.id);
          toast.info(`Model changed to ${compatibleModel.name} to support ${CONTENT_CATEGORIES[newCategory].label} content`);
        }
      }
    }
  };
  
  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };
  
  // Handle advanced options change
  const handleAdvancedOptionChange = (option, value) => {
    setAdvancedOptions(prev => ({
      ...prev,
      [option]: value
    }));
  };
  
  // Handle resolution change
  const handleResolutionChange = (newResolution) => {
    setResolution(newResolution);
  };
  
  // Handle duration change
  const handleDurationChange = (event, newValue) => {
    setDuration(newValue);
  };
  
  // Handle model change
  const handleModelChange = (modelId) => {
    setSelectedModel(modelId);
  };
  
  // Submit generation request
  const handleGenerate = async () => {
    // Validate input
    if (prompt.trim().length < 3) {
      toast.error('Please enter a more detailed prompt (at least 3 characters)');
      promptInputRef.current?.focus();
      return;
    }
    
    // Check quota
    if (quotaData && quotaData.daily_quota.remaining <= 0) {
      toast.error('Daily generation quota exceeded. Please try again tomorrow or upgrade your plan.');
      return;
    }
    
    // Prepare request data
    const generationRequest = {
      prompt,
      model_id: selectedModel,
      quality_tier: qualityTier,
      content_category: contentCategory,
      duration,
      width: resolution.width,
      height: resolution.height,
      fps,
      style,
      use_cache: useCache,
      save_to_gallery: saveToGallery,
      project_id: projectId,
    };
    
    // Add advanced options if enabled
    if (showAdvancedOptions) {
      generationRequest.generation_options = {
        negative_prompt: negativePrompt,
        seed: advancedOptions.seed,
        guidance_scale: advancedOptions.guidanceScale,
        motion_strength: advancedOptions.motionStrength,
        custom_parameters: advancedOptions.customParameters,
      };
    }
    
    // Start generation
    try {
      setIsGenerating(true);
      generateMutation.mutate(generationRequest);
    } catch (error) {
      console.error('Error submitting generation:', error);
      setIsGenerating(false);
      toast.error('Failed to start generation');
    }
  };
  
  // Cancel current generation
  const handleCancelGeneration = async () => {
    if (currentGeneration && currentGeneration.request_id) {
      try {
        await api.delete(`/api/v1/ai-models/cancel/${currentGeneration.request_id}`);
        stopStatusPolling();
        setIsGenerating(false);
        setCurrentGeneration(null);
        toast.info('Generation cancelled');
      } catch (error) {
        console.error('Error cancelling generation:', error);
        toast.error('Failed to cancel generation');
      }
    }
  };
  
  // Load generation history for a specific video
  const handleViewGeneration = (generation) => {
    setCurrentGeneration(generation);
    setIsPreviewExpanded(true);
  };
  
  // Calculate generation progress percentage
  const calculateProgress = (generation) => {
    if (!generation) return 0;
    
    switch (generation.status) {
      case 'completed':
        return 100;
      case 'failed':
      case 'cancelled':
        return 0;
      case 'processing':
        return generation.metrics?.progress ? Math.round(generation.metrics.progress * 100) : 50;
      case 'pending':
        return 10;
      case 'queued':
        return 20;
      default:
        return 0;
    }
  };
  
  // Get remaining time estimate
  const getRemainingTimeText = (generation) => {
    if (!generation || !generation.estimated_completion_time) return 'Calculating...';
    
    const estimatedTime = new Date(generation.estimated_completion_time);
    const now = new Date();
    
    if (estimatedTime < now) return 'Finalizing...';
    
    const diffMs = estimatedTime - now;
    const diffSec = Math.round(diffMs / 1000);
    
    if (diffSec < 60) return `${diffSec} seconds remaining`;
    return `${Math.ceil(diffSec / 60)} minutes remaining`;
  };
  
  // Get status display text
  const getStatusText = (status) => {
    switch (status) {
      case 'pending': return 'Preparing';
      case 'queued': return 'In Queue';
      case 'processing': return 'Processing';
      case 'completed': return 'Completed';
      case 'failed': return 'Failed';
      case 'cancelled': return 'Cancelled';
      default: return status;
    }
  };
  
  // Determine if the current quality tier is available for the user's subscription
  const isQualityTierAvailable = (tier) => {
    if (!quotaData) return true; // Default to true if quota data not loaded yet
    return quotaData.limits.quality_tiers.includes(tier);
  };
  
  // Determine if a resolution is available for the user's subscription
  const isResolutionAvailable = (width, height) => {
    if (!quotaData) return true; // Default to true if quota data not loaded yet
    
    // Parse max resolution string (format: 1920x1080)
    const [maxWidth, maxHeight] = quotaData.limits.max_resolution.split('x').map(Number);
    return width <= maxWidth && height <= maxHeight;
  };
  
  // Determine if duration is available for user's subscription
  const isDurationAvailable = (durationValue) => {
    if (!quotaData) return true;
    return durationValue <= quotaData.limits.max_duration;
  };

  return (
    <Box sx={{ px: 3, py: 2, maxWidth: '100%', overflow: 'hidden' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        AI Video Studio
        {quotaData && (
          <Tooltip title={`${quotaData.daily_quota.remaining} generations remaining today`}>
            <Chip 
              label={`${quotaData.daily_quota.used}/${quotaData.daily_quota.total}`}
              color={quotaData.daily_quota.remaining > 0 ? 'primary' : 'error'}
              size="small"
              sx={{ ml: 2, verticalAlign: 'middle' }}
            />
          </Tooltip>
        )}
      </Typography>
      
      {quotaData && quotaData.subscription_tier && (
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          {quotaData.subscription_tier} Plan
        </Typography>
      )}
      
      <Grid container spacing={3}>
        {/* Left panel: Generation form */}
        <Grid item xs={12} md={7} lg={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            {/* Tabs for different aspects of generation */}
            <Tabs
              value={activeTab}
              onChange={handleTabChange}
              indicatorColor="primary"
              textColor="primary"
              sx={{ mb: 3 }}
            >
              <Tab icon={<Edit />} label="Create" />
              <Tab icon={<History />} label="History" disabled={!projectId} />
              <Tab icon={<Settings />} label="Advanced" />
            </Tabs>
            
            {/* Create tab */}
            {activeTab === 0 && (
              <>
                {/* Prompt input */}
                <FormControl fullWidth sx={{ mb: 3 }}>
                  <PromptField
                    inputRef={promptInputRef}
                    label="Prompt"
                    multiline
                    rows={4}
                    value={prompt}
                    onChange={handlePromptChange}
                    placeholder="Describe what you want to generate in detail. For example: A cinematic shot of a spaceship landing on Mars with astronauts watching from a distance"
                    variant="outlined"
                    fullWidth
                    required
                  />
                </FormControl>
                
                {/* Model selector with comparison button */}
                <Box sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
                  <FormControl sx={{ flexGrow: 1, mr: 1 }}>
                    <InputLabel id="model-select-label">AI Model</InputLabel>
                    <Select
                      labelId="model-select-label"
                      value={selectedModel || ''}
                      onChange={(e) => handleModelChange(e.target.value)}
                      label="AI Model"
                      disabled={isLoadingModels || isGenerating}
                    >
                      {isLoadingModels ? (
                        <MenuItem value="">Loading models...</MenuItem>
                      ) : (
                        models && models.map(model => (
                          <MenuItem 
                            key={model.id} 
                            value={model.id}
                            disabled={!model.status === 'available' || (model.business_tier && quotaData && !quotaData.limits.business_models)}
                          >
                            {model.name} 
                            {model.business_tier && (
                              <Chip 
                                size="small" 
                                label="Business" 
                                color="secondary" 
                                sx={{ ml: 1, height: 20 }} 
                              />
                            )}
                          </MenuItem>
                        ))
                      )}
                    </Select>
                  </FormControl>
                  
                  <Button 
                    variant="outlined"
                    onClick={() => setShowModelComparison(true)}
                    sx={{ flexShrink: 0 }}
                  >
                    Compare
                  </Button>
                </Box>
                
                {/* Quality tier selector */}
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    Quality Tier
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {Object.entries(QUALITY_TIERS).map(([key, { label, description, color }]) => (
                      <Tooltip title={description} key={key}>
                        <span>
                          <StyledChip 
                            label={label}
                            color={color}
                            onClick={() => isQualityTierAvailable(key) && setQualityTier(key)}
                            variant={qualityTier === key ? "filled" : "outlined"}
                            disabled={!isQualityTierAvailable(key) || isGenerating}
                          />
                        </span>
                      </Tooltip>
                    ))}
                  </Box>
                </Box>
                
                {/* Content category selector */}
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    Content Category
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {Object.entries(CONTENT_CATEGORIES).map(([key, { label, icon }]) => (
                      <Chip 
                        key={key}
                        label={label}
                        icon={icon}
                        onClick={() => setContentCategory(key)}
                        color={contentCategory === key ? "primary" : "default"}
                        variant={contentCategory === key ? "filled" : "outlined"}
                        disabled={isGenerating}
                      />
                    ))}
                  </Box>
                </Box>
                
                {/* Resolution and duration */}
                <Grid container spacing={3} sx={{ mb: 3 }}>
                  {/* Resolution picker */}
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle1" gutterBottom>
                      Resolution
                    </Typography>
                    <FormControl fullWidth>
                      <Select
                        value={`${resolution.width}x${resolution.height}`}
                        onChange={(e) => {
                          const [width, height] = e.target.value.split('x').map(Number);
                          handleResolutionChange({ width, height });
                        }}
                        disabled={isGenerating}
                      >
                        {DEFAULT_RESOLUTIONS.map(({ width, height, label }) => (
                          <MenuItem 
                            key={`${width}x${height}`} 
                            value={`${width}x${height}`}
                            disabled={!isResolutionAvailable(width, height)}
                          >
                            {label}
                            {!isResolutionAvailable(width, height) && (
                              <Chip 
                                size="small" 
                                label="Upgrade" 
                                color="secondary" 
                                sx={{ ml: 1, height: 20 }} 
                              />
                            )}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  
                  {/* Duration picker */}
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle1" gutterBottom>
                      Duration: {duration} seconds
                    </Typography>
                    <FormControl fullWidth>
                      <Select
                        value={duration}
                        onChange={(e) => setDuration(Number(e.target.value))}
                        disabled={isGenerating}
                      >
                        {DEFAULT_DURATIONS.map(({ value, label }) => (
                          <MenuItem 
                            key={value} 
                            value={value}
                            disabled={!isDurationAvailable(value)}
                          >
                            {label}
                            {!isDurationAvailable(value) && (
                              <Chip 
                                size="small" 
                                label="Upgrade" 
                                color="secondary" 
                                sx={{ ml: 1, height: 20 }} 
                              />
                            )}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
                
                {/* Advanced options accordion */}
                <Accordion 
                  expanded={showAdvancedOptions} 
                  onChange={() => setShowAdvancedOptions(!showAdvancedOptions)}
                  sx={{ mb: 3 }}
                >
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography>Advanced Options</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    {/* Negative prompt */}
                    <TextField
                      label="Negative Prompt"
                      multiline
                      rows={2}
                      value={negativePrompt}
                      onChange={handleNegativePromptChange}
                      placeholder="Describe what you want to exclude from the generation. For example: blurry, low quality, distorted faces"
                      variant="outlined"
                      fullWidth
                      sx={{ mb: 2 }}
                      disabled={isGenerating}
                    />
                    
                    {/* Seed */}
                    <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
                      <Grid item xs={8}>
                        <TextField
                          label="Seed (leave empty for random)"
                          type="number"
                          value={advancedOptions.seed || ''}
                          onChange={(e) => handleAdvancedOptionChange('seed', e.target.value === '' ? null : Number(e.target.value))}
                          variant="outlined"
                          fullWidth
                          disabled={isGenerating}
                        />
                      </Grid>
                      <Grid item xs={4}>
                        <Button 
                          variant="outlined" 
                          onClick={() => handleAdvancedOptionChange('seed', Math.floor(Math.random() * 1000000))}
                          disabled={isGenerating}
                          fullWidth
                        >
                          Random
                        </Button>
                      </Grid>
                    </Grid>
                    
                    {/* Guidance Scale */}
                    <Typography variant="subtitle2" gutterBottom>
                      Guidance Scale: {advancedOptions.guidanceScale}
                    </Typography>
                    <Slider
                      value={advancedOptions.guidanceScale}
                      onChange={(e, value) => handleAdvancedOptionChange('guidanceScale', value)}
                      min={1}
                      max={20}
                      step={0.1}
                      marks={[
                        { value: 1, label: 'Creative' },
                        { value: 7.5, label: 'Balanced' },
                        { value: 20, label: 'Precise' },
                      ]}
                      disabled={isGenerating}
                      sx={{ mb: 2 }}
                    />
                    
                    {/* Motion Strength */}
                    <Typography variant="subtitle2" gutterBottom>
                      Motion Strength: {advancedOptions.motionStrength}
                    </Typography>
                    <Slider
                      value={advancedOptions.motionStrength}
                      onChange={(e, value) => handleAdvancedOptionChange('motionStrength', value)}
                      min={0}
                      max={1}
                      step={0.05}
                      marks={[
                        { value: 0, label: 'Subtle' },
                        { value: 0.5, label: 'Medium' },
                        { value: 1, label: 'Strong' },
                      ]}
                      disabled={isGenerating}
                      sx={{ mb: 2 }}
                    />
                    
                    {/* Options */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={useCache}
                            onChange={(e) => setUseCache(e.target.checked)}
                            disabled={isGenerating}
                          />
                        }
                        label="Use Cache"
                      />
                      
                      <FormControlLabel
                        control={
                          <Switch
                            checked={saveToGallery}
                            onChange={(e) => setSaveToGallery(e.target.checked)}
                            disabled={isGenerating}
                          />
                        }
                        label="Save to Gallery"
                      />
                    </Box>
                  </AccordionDetails>
                </Accordion>
                
                {/* Generation button and cost */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    {estimatedCost && (
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Typography variant="body2" color="text.secondary" sx={{ mr: 1 }}>
                          Estimated cost: ${estimatedCost.estimated_cost_dollars?.toFixed(2) || '0.00'} 
                          ({estimatedCost.estimated_cost_credits || 0} credits)
                        </Typography>
                        
                        {estimatedCost.selected_model && (
                          <Tooltip title={`Using ${estimatedCost.model_name} from ${estimatedCost.provider}`}>
                            <Info fontSize="small" color="action" />
                          </Tooltip>
                        )}
                      </Box>
                    )}
                    
                    {estimatedCost && !estimatedCost.can_fulfill && (
                      <Typography variant="body2" color="error">
                        {estimatedCost.reason}
                      </Typography>
                    )}
                  </Box>
                  
                  <Box>
                    {isGenerating ? (
                      <Button
                        variant="outlined"
                        color="secondary"
                        onClick={handleCancelGeneration}
                        startIcon={<Pause />}
                      >
                        Cancel
                      </Button>
                    ) : (
                      <Button
                        variant="contained"
                        color="primary"
                        onClick={handleGenerate}
                        startIcon={<MovieCreation />}
                        disabled={
                          prompt.trim().length < 3 || 
                          !selectedModel || 
                          (estimatedCost && !estimatedCost.can_fulfill) ||
                          (quotaData && quotaData.daily_quota.remaining <= 0)
                        }
                      >
                        Generate Video
                      </Button>
                    )}
                  </Box>
                </Box>
                
                {/* Quota warning if low */}
                {quotaData && quotaData.daily_quota.remaining <= 3 && quotaData.daily_quota.remaining > 0 && (
                  <Alert severity="warning" sx={{ mt: 2 }}>
                    <AlertTitle>Low Quota</AlertTitle>
                    You have only {quotaData.daily_quota.remaining} generations remaining today.
                  </Alert>
                )}
                
                {/* Quota exceeded warning */}
                {quotaData && quotaData.daily_quota.remaining <= 0 && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    <AlertTitle>Quota Exceeded</AlertTitle>
                    You've reached your daily generation limit. Your quota will reset in {quotaData.quota_resets_in.formatted}.
                  </Alert>
                )}
              </>
            )}
            
            {/* History tab */}
            {activeTab === 1 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Recent Generations
                  <IconButton size="small" onClick={refetchRecent} sx={{ ml: 1 }}>
                    <RefreshIcon />
                  </IconButton>
                </Typography>
                
                {isLoadingRecent ? (
                  <CircularProgress />
                ) : (
                  <>
                    {recentGenerations && recentGenerations.length > 0 ? (
                      <Grid container spacing={2}>
                        {recentGenerations.map(generation => (
                          <Grid item xs={12} sm={6} md={4} key={generation.id}>
                            <ThumbnailCard onClick={() => handleViewGeneration(generation)}>
                              <CardMedia
                                component="img"
                                height="140"
                                image={generation.thumbnail_url || '/placeholder-thumbnail.jpg'}
                                alt={generation.prompt?.substring(0, 30) || 'Generated video'}
                              />
                              <Box 
                                sx={{ 
                                  position: 'absolute', 
                                  top: 8, 
                                  right: 8,
                                  bgcolor: 'rgba(0, 0, 0, 0.6)', 
                                  borderRadius: '4px',
                                  px: 1,
                                  py: 0.5
                                }}
                              >
                                <Typography variant="caption" sx={{ color: 'white' }}>
                                  {generation.resolution_str || `${generation.width}x${generation.height}`}
                                </Typography>
                              </Box>
                              <CardContent>
                                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                  <StatusIndicator status={generation.status} />
                                  <Typography variant="caption">
                                    {getStatusText(generation.status)}
                                  </Typography>
                                </Box>
                                <Typography variant="body2" noWrap title={generation.prompt}>
                                  {generation.prompt?.substring(0, 60) || 'No prompt available'}
                                  {generation.prompt?.length > 60 ? '...' : ''}
                                </Typography>
                              </CardContent>
                            </ThumbnailCard>
                          </Grid>
                        ))}
                      </Grid>
                    ) : (
                      <Typography variant="body1" color="text.secondary">
                        No generations found for this project.
                      </Typography>
                    )}
                  </>
                )}
              </Box>
            )}
            
            {/* Advanced settings tab */}
            {activeTab === 2 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Advanced Settings
                </Typography>
                
                {/* FPS selector */}
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Frames Per Second (FPS): {fps}
                  </Typography>
                  <Slider
                    value={fps}
                    onChange={(e, value) => setFps(value)}
                    min={15}
                    max={60}
                    step={1}
                    marks={[
                      { value: 15, label: '15' },
                      { value: 24, label: '24' },
                      { value: 30, label: '30' },
                      { value: 60, label: '60' },
                    ]}
                    disabled={isGenerating}
                  />
                </Box>
                
                {/* Style selector */}
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    Visual Style
                  </Typography>
                  <FormControl fullWidth>
                    <Select
                      value={style}
                      onChange={(e) => setStyle(e.target.value)}
                      disabled={isGenerating}
                    >
                      <MenuItem value="cinematic">Cinematic</MenuItem>
                      <MenuItem value="photorealistic">Photorealistic</MenuItem>
                      <MenuItem value="anime">Anime</MenuItem>
                      <MenuItem value="3d_animation">3D Animation</MenuItem>
                      <MenuItem value="cartoon">Cartoon</MenuItem>
                      <MenuItem value="digital_art">Digital Art</MenuItem>
                      <MenuItem value="pixel_art">Pixel Art</MenuItem>
                      <MenuItem value="oil_painting">Oil Painting</MenuItem>
                      <MenuItem value="watercolor">Watercolor</MenuItem>
                      <MenuItem value="sketch">Sketch</MenuItem>
                      <MenuItem value="minimalist">Minimalist</MenuItem>
                      <MenuItem value="vintage">Vintage</MenuItem>
                      <MenuItem value="sci_fi">Sci-Fi</MenuItem>
                      <MenuItem value="fantasy">Fantasy</MenuItem>
                      <MenuItem value="dystopian">Dystopian</MenuItem>
                      <MenuItem value="surrealist">Surrealist</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
              </Box>
            )}
          </Paper>
        </Grid>
        
        {/* Right panel: Preview and status */}
        <Grid item xs={12} md={5} lg={4}>
          {/* Current generation preview */}
          {currentGeneration ? (
            <Paper sx={{ p: 3, mb: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Preview
                </Typography>
                <Box>
                  <IconButton 
                    size="small" 
                    onClick={() => setIsPreviewExpanded(!isPreviewExpanded)}
                    color={isPreviewExpanded ? "primary" : "default"}
                  >
                    <Fullscreen />
                  </IconButton>
                </Box>
              </Box>
              
              <Box 
                sx={{ 
                  position: 'relative',
                  borderRadius: 1,
                  overflow: 'hidden',
                  mb: 2,
                  bgcolor: 'black',
                  aspectRatio: `${currentGeneration.width || 16}/${currentGeneration.height || 9}`
                }}
              >
                {currentGeneration.status === 'processing' && currentGeneration.preview_url && (
                  <img
                    src={currentGeneration.preview_url}
                    alt="Generation preview"
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                  />
                )}
                
                {currentGeneration.status === 'completed' && currentGeneration.video_url && (
                  <ReactPlayer
                    url={currentGeneration.video_url}
                    width="100%"
                    height="100%"
                    controls
                    playing={isPreviewExpanded}
                  />
                )}
                
                {(['pending', 'queued'].includes(currentGeneration.status) || 
                  (currentGeneration.status === 'processing' && !currentGeneration.preview_url)) && (
                  <Box 
                    sx={{ 
                      display: 'flex', 
                      flexDirection: 'column',
                      justifyContent: 'center', 
                      alignItems: 'center',
                      height: '100%',
                      p: 3
                    }}
                  >
                    <CircularProgress 
                      variant="determinate" 
                      value={calculateProgress(currentGeneration)}
                      sx={{ mb: 2 }}
                    />
                    <Typography variant="body2" color="white" align="center">
                      {currentGeneration.status === 'pending' && 'Preparing your video...'}
                      {currentGeneration.status === 'queued' && `Position in queue: ${currentGeneration.position_in_queue || 'Calculating...'}`}
                      {currentGeneration.status === 'processing' && getRemainingTimeText(currentGeneration)}
                    </Typography>
                  </Box>
                )}
                
                {currentGeneration.status === 'failed' && (
                  <Box 
                    sx={{ 
                      display: 'flex', 
                      flexDirection: 'column',
                      justifyContent: 'center', 
                      alignItems: 'center',
                      height: '100%',
                      p: 3
                    }}
                  >
                    <Error color="error" sx={{ fontSize: 48, mb: 2 }} />
                    <Typography variant="body2" color="error" align="center">
                      {currentGeneration.error || 'Generation failed'}
                    </Typography>
                  </Box>
                )}
              </Box>
              
              {/* Progress bar */}
              {['pending', 'queued', 'processing'].includes(currentGeneration.status) && (
                <Box sx={{ width: '100%', mb: 2 }}>
                  <LinearProgress 
                    variant={currentGeneration.status === 'processing' ? "determinate" : "indeterminate"} 
                    value={calculateProgress(currentGeneration)}
                  />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      {getStatusText(currentGeneration.status)}
                      {currentGeneration.status === 'processing' && ` (${calculateProgress(currentGeneration)}%)`}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {currentGeneration.status === 'processing' && getRemainingTimeText(currentGeneration)}
                    </Typography>
                  </Box>
                </Box>
              )}
              
              {/* Generation details */}
              <Divider sx={{ my: 2 }} />
              
              <Grid container spacing={1}>
                {/* Request ID */}
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    Request ID
                  </Typography>
                  <Typography variant="body2" noWrap>
                    {currentGeneration.request_id || 'N/A'}
                  </Typography>
                </Grid>
                
                {/* Model */}
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    Model
                  </Typography>
                  <Typography variant="body2" noWrap>
                    {currentGeneration.model_used || 'Automatic'}
                  </Typography>
                </Grid>
                
                {/* Resolution */}
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    Resolution
                  </Typography>
                  <Typography variant="body2">
                    {currentGeneration.width}×{currentGeneration.height}
                  </Typography>
                </Grid>
                
                {/* Duration */}
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    Duration
                  </Typography>
                  <Typography variant="body2">
                    {currentGeneration.duration || 'N/A'} seconds
                  </Typography>
                </Grid>
                
                {/* Cost */}
                {currentGeneration.cost !== undefined && (
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      Cost
                    </Typography>
                    <Typography variant="body2">
                      ${currentGeneration.cost.toFixed(2)} ({Math.round(currentGeneration.cost * 100)} credits)
                    </Typography>
                  </Grid>
                )}
                
                {/* Processing time */}
                {currentGeneration.metrics && currentGeneration.metrics.processing_time && (
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      Processing Time
                    </Typography>
                    <Typography variant="body2">
                      {currentGeneration.metrics.processing_time.toFixed(1)}s
                    </Typography>
                  </Grid>
                )}
              </Grid>
              
              {/* Action buttons for completed videos */}
              {currentGeneration.status === 'completed' && (
                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between' }}>
                  <Button 
                    startIcon={<CloudDownload />}
                    variant="outlined"
                    size="small"
                    href={currentGeneration.video_url}
                    download
                  >
                    Download
                  </Button>
                  
                  <Button 
                    startIcon={<CloudUpload />}
                    variant="contained"
                    size="small"
                    color="primary"
                  >
                    Share
                  </Button>
                </Box>
              )}
            </Paper>
          ) : (
            <Paper 
              sx={{ 
                p: 3, 
                mb: 3, 
                display: 'flex', 
                flexDirection: 'column', 
                justifyContent: 'center', 
                alignItems: 'center',
                height: '300px'
              }}
            >
              <MovieCreation sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
              <Typography variant="body1" color="text.secondary" align="center">
                Enter a prompt and click "Generate Video" to start creating.
              </Typography>
            </Paper>
          )}
          
          {/* Prompt suggestions */}
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Prompt Suggestions
            </Typography>
            
            <Box sx={{ mb: 2 }}>
              {[
                "A cinematic shot of a spaceship landing on Mars, dramatic lighting, dust particles",
                "A photorealistic forest with sunlight streaming through the trees, mist rising from the ground",
                "A bustling cyberpunk city at night with neon signs and flying cars",
                "A serene beach sunset with waves gently washing onto shore",
                "An aerial view of a mountain range covered in snow, clouds moving across peaks"
              ].map((suggestion, index) => (
                <Chip
                  key={index}
                  label={suggestion.substring(0, 40) + '...'}
                  onClick={() => setPrompt(suggestion)}
                  sx={{ m: 0.5 }}
                />
              ))}
            </Box>
            
            <Typography variant="subtitle2" gutterBottom>
              Tips for better results:
            </Typography>
            
            <Box component="ul" sx={{ pl: 2, m: 0 }}>
              <Typography component="li" variant="body2" color="text.secondary">
                Be specific and detailed in your descriptions
              </Typography>
              <Typography component="li" variant="body2" color="text.secondary">
                Include lighting, camera angles, and atmosphere
              </Typography>
              <Typography component="li" variant="body2" color="text.secondary">
                Use "cinematic" for film-like quality
              </Typography>
              <Typography component="li" variant="body2" color="text.secondary">
                Adjust advanced settings for more control
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>
      
      {/* Model comparison dialog */}
      <Dialog
        open={showModelComparison}
        onClose={() => setShowModelComparison(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>AI Model Comparison</DialogTitle>
        <DialogContent>
          <DialogContentText paragraph>
            Compare the capabilities and performance of different AI video generation models:
          </DialogContentText>
          
          {isLoadingModels ? (
            <CircularProgress />
          ) : (
            <Grid container spacing={2}>
              {models && models.map(model => (
                <Grid item xs={12} md={6} lg={4} key={model.id}>
                  <Card variant="outlined" sx={{ height: '100%' }}>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        {model.name}
                        {model.status !== 'available' && (
                          <Chip 
                            size="small" 
                            label={model.status} 
                            color={model.status === 'maintenance' ? 'warning' : 'error'} 
                            sx={{ ml: 1 }} 
                          />
                        )}
                      </Typography>
                      
                      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        {model.provider}
                      </Typography>
                      
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <Typography variant="body2">Quality:</Typography>
                        <Rating 
                          value={model.quality_score / 2}
                          precision={0.5}
                          readOnly 
                          size="small"
                          sx={{ ml: 1 }}
                        />
                      </Box>
                      
                      <Divider sx={{ my: 1.5 }} />
                      
                      <Typography variant="body2">
                        <strong>Cost:</strong> ${model.cost_per_second.toFixed(2)}/sec
                      </Typography>
                      
                      <Typography variant="body2">
                        <strong>Max Duration:</strong> {model.max_duration}s
                      </Typography>
                      
                      <Typography variant="body2">
                        <strong>Success Rate:</strong> {model.success_rate.toFixed(1)}%
                      </Typography>
                      
                      <Typography variant="body2">
                        <strong>Avg. Generation Time:</strong> {model.average_generation_time.toFixed(0)}s
                      </Typography>
                      
                      <Divider sx={{ my: 1.5 }} />
                      
                      <Typography variant="body2" gutterBottom>
                        <strong>Supported Quality Tiers:</strong>
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
                        {model.supported_quality_tiers.map(tier => (
                          <Chip 
                            key={tier} 
                            label={QUALITY_TIERS[tier]?.label || tier} 
                            size="small" 
                            color="primary"
                            variant="outlined"
                          />
                        ))}
                      </Box>
                      
                      <Typography variant="body2" gutterBottom>
                        <strong>Supported Categories:</strong>
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {model.supported_content_categories.map(category => (
                          <Chip 
                            key={category} 
                            label={CONTENT_CATEGORIES[category]?.label || category} 
                            size="small"
                            variant="outlined"
                          />
                        ))}
                      </Box>
                    </CardContent>
                    
                    <Box sx={{ p: 2, pt: 0 }}>
                      <Button 
                        variant={selectedModel === model.id ? "contained" : "outlined"}
                        fullWidth
                        onClick={() => {
                          handleModelChange(model.id);
                          setShowModelComparison(false);
                        }}
                        disabled={model.status !== 'available' || (model.business_tier && quotaData && !quotaData.limits.business_models)}
                      >
                        {selectedModel === model.id ? "Selected" : "Select Model"}
                      </Button>
                    </Box>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowModelComparison(false)}>Close</Button>
        </DialogActions>
      </Dialog>
      
      {/* Full-screen preview dialog */}
      <Dialog
        open={isPreviewExpanded && currentGeneration?.video_url}
        onClose={() => setIsPreviewExpanded(false)}
        maxWidth="xl"
        fullWidth
      >
        <DialogContent sx={{ p: 0, bgcolor: 'black' }}>
          {currentGeneration?.video_url && (
            <ReactPlayer
              url={currentGeneration.video_url}
              width="100%"
              height="calc(100vh - 100px)"
              controls
              playing
            />
          )}
        </DialogContent>
        <DialogActions sx={{ bgcolor: 'black', color: 'white' }}>
          <Typography variant="body2" sx={{ flexGrow: 1, color: 'white' }}>
            {currentGeneration?.prompt?.substring(0, 100)}
            {currentGeneration?.prompt?.length > 100 ? '...' : ''}
          </Typography>
          <Button onClick={() => setIsPreviewExpanded(false)} sx={{ color: 'white' }}>
            Close
          </Button>
          <Button 
            startIcon={<CloudDownload />}
            variant="contained"
            color="primary"
            href={currentGeneration?.video_url}
            download
          >
            Download
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EnterpriseStudio;