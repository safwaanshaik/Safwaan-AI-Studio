import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Typography,
  Button,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  InputAdornment,
} from '@mui/material';
import {
  PlayArrow,
  MoreVert,
  Share,
  Download,
  Edit,
  Delete,
  Search,
  FilterList,
  Sort,
} from '@mui/icons-material';
import { motion } from 'framer-motion';

const VideoGalleryPage = () => {
  const [videos, setVideos] = useState([]);
  const [filteredVideos, setFilteredVideos] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, video: null });

  // Mock video data
  useEffect(() => {
    const mockVideos = [
      {
        id: 1,
        title: 'Quantum Computing Breakthrough',
        thumbnail: '/api/placeholder/320/180',
        duration: '2:34',
        views: 125000,
        likes: 8500,
        createdAt: '2024-01-15',
        category: 'Technology',
        status: 'published',
        platforms: ['YouTube', 'TikTok'],
        tags: ['AI', 'Quantum', 'Tech'],
      },
      {
        id: 2,
        title: 'Sustainable Energy Revolution',
        thumbnail: '/api/placeholder/320/180',
        duration: '3:12',
        views: 98000,
        likes: 6200,
        createdAt: '2024-01-14',
        category: 'Environment',
        status: 'published',
        platforms: ['YouTube', 'Instagram'],
        tags: ['Green', 'Energy', 'Future'],
      },
      {
        id: 3,
        title: 'AI Art Gallery Showcase',
        thumbnail: '/api/placeholder/320/180',
        duration: '4:56',
        views: 156000,
        likes: 12400,
        createdAt: '2024-01-13',
        category: 'Art',
        status: 'processing',
        platforms: ['YouTube'],
        tags: ['AI', 'Art', 'Creativity'],
      },
      {
        id: 4,
        title: 'Space Exploration Updates',
        thumbnail: '/api/placeholder/320/180',
        duration: '2:48',
        views: 89000,
        likes: 5800,
        createdAt: '2024-01-12',
        category: 'Science',
        status: 'published',
        platforms: ['YouTube', 'Twitter'],
        tags: ['Space', 'NASA', 'Exploration'],
      },
      {
        id: 5,
        title: 'Future of Transportation',
        thumbnail: '/api/placeholder/320/180',
        duration: '3:28',
        views: 134000,
        likes: 9200,
        createdAt: '2024-01-11',
        category: 'Technology',
        status: 'published',
        platforms: ['YouTube', 'TikTok', 'Instagram'],
        tags: ['Transport', 'Future', 'Innovation'],
      },
      {
        id: 6,
        title: 'Ocean Mysteries Revealed',
        thumbnail: '/api/placeholder/320/180',
        duration: '3:55',
        views: 112000,
        likes: 7800,
        createdAt: '2024-01-10',
        category: 'Science',
        status: 'published',
        platforms: ['YouTube'],
        tags: ['Ocean', 'Discovery', 'Nature'],
      },
    ];

    setVideos(mockVideos);
    setFilteredVideos(mockVideos);
  }, []);

  // Filter and sort videos
  useEffect(() => {
    let filtered = videos.filter(video => {
      const matchesSearch = video.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           video.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()));
      const matchesCategory = selectedCategory === 'all' || video.category === selectedCategory;
      return matchesSearch && matchesCategory;
    });

    // Sort videos
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'newest':
          return new Date(b.createdAt) - new Date(a.createdAt);
        case 'oldest':
          return new Date(a.createdAt) - new Date(b.createdAt);
        case 'most-viewed':
          return b.views - a.views;
        case 'most-liked':
          return b.likes - a.likes;
        default:
          return 0;
      }
    });

    setFilteredVideos(filtered);
  }, [videos, searchTerm, selectedCategory, sortBy]);

  const categories = [
    { value: 'all', label: 'All Categories' },
    { value: 'Technology', label: 'Technology' },
    { value: 'Science', label: 'Science' },
    { value: 'Art', label: 'Art' },
    { value: 'Environment', label: 'Environment' },
  ];

  const sortOptions = [
    { value: 'newest', label: 'Newest First' },
    { value: 'oldest', label: 'Oldest First' },
    { value: 'most-viewed', label: 'Most Viewed' },
    { value: 'most-liked', label: 'Most Liked' },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'published': return '#10b981';
      case 'processing': return '#f59e0b';
      case 'failed': return '#ef4444';
      default: return '#64748b';
    }
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
  };

  const handleMenuOpen = (event, video) => {
    setMenuAnchor(event.currentTarget);
    setSelectedVideo(video);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
    setSelectedVideo(null);
  };

  const handleDelete = (video) => {
    setDeleteDialog({ open: true, video });
    handleMenuClose();
  };

  const confirmDelete = () => {
    setVideos(videos.filter(v => v.id !== deleteDialog.video.id));
    setDeleteDialog({ open: false, video: null });
  };

  return (
    <Box sx={{ p: 3, maxWidth: '1400px', mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 700, mb: 2 }}>
          Video Gallery
        </Typography>

        {/* Filters and Search */}
        <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap', alignItems: 'center' }}>
          <TextField
            placeholder="Search videos..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
            sx={{
              minWidth: 300,
              '& .MuiOutlinedInput-root': {
                background: 'rgba(15, 23, 42, 0.6)',
                backdropFilter: 'blur(16px)',
                border: '1px solid rgba(148, 163, 184, 0.2)',
              },
            }}
          />

          <TextField
            select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <FilterList />
                </InputAdornment>
              ),
            }}
            sx={{
              minWidth: 200,
              '& .MuiOutlinedInput-root': {
                background: 'rgba(15, 23, 42, 0.6)',
                backdropFilter: 'blur(16px)',
                border: '1px solid rgba(148, 163, 184, 0.2)',
              },
            }}
          >
            {categories.map((category) => (
              <MenuItem key={category.value} value={category.value}>
                {category.label}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Sort />
                </InputAdornment>
              ),
            }}
            sx={{
              minWidth: 180,
              '& .MuiOutlinedInput-root': {
                background: 'rgba(15, 23, 42, 0.6)',
                backdropFilter: 'blur(16px)',
                border: '1px solid rgba(148, 163, 184, 0.2)',
              },
            }}
          >
            {sortOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
        </Box>

        <Typography variant="body1" color="text.secondary">
          Showing {filteredVideos.length} of {videos.length} videos
        </Typography>
      </Box>

      {/* Video Grid */}
      <Grid container spacing={3}>
        {filteredVideos.map((video, index) => (
          <Grid item xs={12} sm={6} lg={4} xl={3} key={video.id}>
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
                  overflow: 'hidden',
                  transition: 'all 0.3s ease',
                  cursor: 'pointer',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 12px 24px rgba(0, 0, 0, 0.3)',
                    borderColor: 'rgba(6, 182, 212, 0.4)',
                  },
                }}
              >
                {/* Video Thumbnail */}
                <Box sx={{ position: 'relative' }}>
                  <CardMedia
                    component="img"
                    height="180"
                    image={video.thumbnail}
                    alt={video.title}
                    sx={{ objectFit: 'cover' }}
                  />

                  {/* Play Button Overlay */}
                  <Box
                    sx={{
                      position: 'absolute',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)',
                      width: 60,
                      height: 60,
                      borderRadius: '50%',
                      background: 'rgba(0, 0, 0, 0.7)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.3s ease',
                      '&:hover': {
                        background: 'rgba(6, 182, 212, 0.8)',
                        transform: 'translate(-50%, -50%) scale(1.1)',
                      },
                    }}
                  >
                    <PlayArrow sx={{ fontSize: 30, color: 'white' }} />
                  </Box>

                  {/* Duration Badge */}
                  <Chip
                    label={video.duration}
                    size="small"
                    sx={{
                      position: 'absolute',
                      bottom: 8,
                      right: 8,
                      bgcolor: 'rgba(0, 0, 0, 0.7)',
                      color: 'white',
                      fontSize: '0.75rem',
                    }}
                  />

                  {/* Status Badge */}
                  <Chip
                    label={video.status}
                    size="small"
                    sx={{
                      position: 'absolute',
                      top: 8,
                      left: 8,
                      bgcolor: getStatusColor(video.status) + '20',
                      color: getStatusColor(video.status),
                      fontSize: '0.7rem',
                      textTransform: 'capitalize',
                    }}
                  />
                </Box>

                <CardContent sx={{ p: 2 }}>
                  <Typography
                    variant="h6"
                    sx={{
                      fontWeight: 600,
                      mb: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      lineHeight: 1.3,
                    }}
                  >
                    {video.title}
                  </Typography>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {formatNumber(video.views)} views
                    </Typography>
                    <Typography variant="body2" color="text.secondary">•</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {video.likes} likes
                    </Typography>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Chip
                      label={video.category}
                      size="small"
                      sx={{
                        bgcolor: 'rgba(6, 182, 212, 0.2)',
                        color: '#06b6d4',
                        fontSize: '0.7rem',
                      }}
                    />

                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      {video.platforms.slice(0, 3).map((platform) => (
                        <Chip
                          key={platform}
                          label={platform}
                          size="small"
                          variant="outlined"
                          sx={{
                            fontSize: '0.6rem',
                            height: 20,
                            borderColor: 'rgba(148, 163, 184, 0.3)',
                            color: 'text.secondary',
                          }}
                        />
                      ))}
                    </Box>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <IconButton size="small" sx={{ color: 'text.secondary' }}>
                        <Share fontSize="small" />
                      </IconButton>
                      <IconButton size="small" sx={{ color: 'text.secondary' }}>
                        <Download fontSize="small" />
                      </IconButton>
                    </Box>

                    <IconButton
                      size="small"
                      onClick={(e) => handleMenuOpen(e, video)}
                      sx={{ color: 'text.secondary' }}
                    >
                      <MoreVert fontSize="small" />
                    </IconButton>
                  </Box>
                </CardContent>
              </Card>
            </motion.div>
          </Grid>
        ))}
      </Grid>

      {/* Context Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleMenuClose}>
          <Edit sx={{ mr: 1 }} fontSize="small" />
          Edit
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <Share sx={{ mr: 1 }} fontSize="small" />
          Share
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <Download sx={{ mr: 1 }} fontSize="small" />
          Download
        </MenuItem>
        <MenuItem onClick={() => handleDelete(selectedVideo)}>
          <Delete sx={{ mr: 1 }} fontSize="small" />
          Delete
        </MenuItem>
      </Menu>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, video: null })}
        PaperProps={{
          sx: {
            background: 'rgba(15, 23, 42, 0.9)',
            backdropFilter: 'blur(16px)',
            border: '1px solid rgba(148, 163, 184, 0.2)',
          },
        }}
      >
        <DialogTitle>Delete Video</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{deleteDialog.video?.title}"?
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, video: null })}>
            Cancel
          </Button>
          <Button onClick={confirmDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Empty State */}
      {filteredVideos.length === 0 && (
        <Box
          sx={{
            textAlign: 'center',
            py: 8,
            color: 'text.secondary',
          }}
        >
          <Typography variant="h6" sx={{ mb: 2 }}>
            No videos found
          </Typography>
          <Typography variant="body2">
            Try adjusting your search or filter criteria
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default VideoGalleryPage;