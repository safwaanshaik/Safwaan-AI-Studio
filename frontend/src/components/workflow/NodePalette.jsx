import React, { useState } from 'react';

const NodePalette = ({ onAddNode }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const nodeTemplates = [
    // Triggers
    {
      id: 'trend-trigger',
      type: 'trigger',
      title: 'Trend Detected',
      description: 'Triggers when trending topics are found',
      icon: 'fa-fire',
      category: 'triggers',
      inputs: [],
      outputs: [{ id: 'trend_data', label: 'Trend Data' }],
      config: {
        'Min Score': '70',
        'Frequency': '6 hours',
        'Categories': 'Technology,Entertainment'
      }
    },
    {
      id: 'schedule-trigger',
      type: 'trigger',
      title: 'Schedule',
      description: 'Runs on a scheduled interval',
      icon: 'fa-clock',
      category: 'triggers',
      inputs: [],
      outputs: [{ id: 'timestamp', label: 'Timestamp' }],
      config: {
        'Interval': 'daily',
        'Time': '09:00'
      }
    },
    {
      id: 'webhook-trigger',
      type: 'trigger',
      title: 'Webhook',
      description: 'Triggers on webhook events',
      icon: 'fa-globe',
      category: 'triggers',
      inputs: [],
      outputs: [{ id: 'webhook_data', label: 'Webhook Data' }],
      config: {
        'URL': '/api/webhook',
        'Method': 'POST'
      }
    },

    // AI Models
    {
      id: 'sora-model',
      type: 'ai-model',
      title: 'Sora Video Gen',
      description: 'Generate videos with OpenAI Sora',
      icon: 'fa-video',
      category: 'ai-models',
      inputs: [{ id: 'prompt', label: 'Prompt' }],
      outputs: [{ id: 'video_url', label: 'Video URL' }],
      config: {
        'Model': 'Sora v1',
        'Duration': '5-10 seconds',
        'Quality': 'HD'
      }
    },
    {
      id: 'runway-model',
      type: 'ai-model',
      title: 'Runway Gen-3',
      description: 'Advanced video generation with Runway',
      icon: 'fa-film',
      category: 'ai-models',
      inputs: [{ id: 'prompt', label: 'Prompt' }],
      outputs: [{ id: 'video_url', label: 'Video URL' }],
      config: {
        'Model': 'Gen-3 Alpha',
        'Style': 'Cinematic',
        'Resolution': '1080p'
      }
    },
    {
      id: 'stable-diffusion',
      type: 'ai-model',
      title: 'Stable Video Diff',
      description: 'Open-source video generation',
      icon: 'fa-magic',
      category: 'ai-models',
      inputs: [{ id: 'prompt', label: 'Prompt' }],
      outputs: [{ id: 'video_url', label: 'Video URL' }],
      config: {
        'Model': 'SD Video',
        'Steps': '25',
        'Guidance': '7.5'
      }
    },
    {
      id: 'director-agent',
      type: 'ai-model',
      title: 'Director Agent',
      description: 'AI director for storyboarding',
      icon: 'fa-user-tie',
      category: 'ai-models',
      inputs: [{ id: 'trend_data', label: 'Trend Data' }],
      outputs: [{ id: 'storyboard', label: 'Storyboard' }],
      config: {
        'Style': 'Cinematic',
        'Genre': 'Auto-detect',
        'Length': '30-60 seconds'
      }
    },
    {
      id: 'editor-agent',
      type: 'ai-model',
      title: 'Editor Agent',
      description: 'AI editor for post-production',
      icon: 'fa-cut',
      category: 'ai-models',
      inputs: [{ id: 'video_url', label: 'Video URL' }],
      outputs: [{ id: 'edited_video', label: 'Edited Video' }],
      config: {
        'Enhancements': 'Color,Audio,Stabilize',
        'Format': 'MP4',
        'Quality': 'HD'
      }
    },

    // Actions
    {
      id: 'video-processor',
      type: 'action',
      title: 'Video Processor',
      description: 'Process and enhance videos',
      icon: 'fa-cogs',
      category: 'actions',
      inputs: [{ id: 'video_input', label: 'Video Input' }],
      outputs: [{ id: 'processed_video', label: 'Processed Video' }],
      config: {
        'Upscale': '2x',
        'Stabilize': 'true',
        'Color Grade': 'Cinematic'
      }
    },
    {
      id: 'quality-check',
      type: 'action',
      title: 'Quality Check',
      description: 'Automated quality assessment',
      icon: 'fa-shield-alt',
      category: 'actions',
      inputs: [{ id: 'video_url', label: 'Video URL' }],
      outputs: [{ id: 'quality_score', label: 'Quality Score' }],
      config: {
        'Checks': 'Technical,Content,Safety',
        'Threshold': '85%'
      }
    },
    {
      id: 'youtube-upload',
      type: 'action',
      title: 'YouTube Upload',
      description: 'Upload to YouTube automatically',
      icon: 'fa-youtube',
      category: 'actions',
      inputs: [{ id: 'video_url', label: 'Video URL' }],
      outputs: [{ id: 'upload_result', label: 'Upload Result' }],
      config: {
        'Privacy': 'Public',
        'Tags': 'AI,Trending,Viral',
        'Thumbnail': 'Auto-generate'
      }
    },
    {
      id: 'tiktok-upload',
      type: 'action',
      title: 'TikTok Upload',
      description: 'Upload to TikTok with optimization',
      icon: 'fa-tiktok',
      category: 'actions',
      inputs: [{ id: 'video_url', label: 'Video URL' }],
      outputs: [{ id: 'upload_result', label: 'Upload Result' }],
      config: {
        'Sound': 'Trending',
        'Caption': 'Auto-generate',
        'Hashtags': 'AI,Viral,Trending'
      }
    },
    {
      id: 'instagram-upload',
      type: 'action',
      title: 'Instagram Upload',
      description: 'Upload to Instagram Reels',
      icon: 'fa-instagram',
      category: 'actions',
      inputs: [{ id: 'video_url', label: 'Video URL' }],
      outputs: [{ id: 'upload_result', label: 'Upload Result' }],
      config: {
        'Format': 'Reels',
        'Caption': 'Auto-generate',
        'Music': 'Trending'
      }
    },

    // Conditions
    {
      id: 'quality-gate',
      type: 'condition',
      title: 'Quality Gate',
      description: 'Check if video meets quality standards',
      icon: 'fa-filter',
      category: 'conditions',
      inputs: [{ id: 'quality_score', label: 'Quality Score' }],
      outputs: [
        { id: 'approved', label: 'Approved' },
        { id: 'rejected', label: 'Rejected' }
      ],
      config: {
        'Min Score': '80',
        'Auto Reject': 'false'
      }
    },
    {
      id: 'trend-filter',
      type: 'condition',
      title: 'Trend Filter',
      description: 'Filter trends by criteria',
      icon: 'fa-sliders-h',
      category: 'conditions',
      inputs: [{ id: 'trend_data', label: 'Trend Data' }],
      outputs: [
        { id: 'filtered', label: 'Filtered' },
        { id: 'discarded', label: 'Discarded' }
      ],
      config: {
        'Min Score': '70',
        'Categories': 'Technology,Science',
        'Exclude': 'Politics'
      }
    },

    // Outputs
    {
      id: 'analytics-logger',
      type: 'output',
      title: 'Analytics Logger',
      description: 'Log performance analytics',
      icon: 'fa-chart-bar',
      category: 'outputs',
      inputs: [{ id: 'performance_data', label: 'Performance Data' }],
      outputs: [],
      config: {
        'Metrics': 'Views,Engagement,Revenue',
        'Storage': 'Database'
      }
    },
    {
      id: 'notification',
      type: 'output',
      title: 'Notification',
      description: 'Send notifications',
      icon: 'fa-bell',
      category: 'outputs',
      inputs: [{ id: 'message', label: 'Message' }],
      outputs: [],
      config: {
        'Type': 'Email,Slack',
        'Recipients': 'admin@example.com',
        'Template': 'Workflow Complete'
      }
    }
  ];

  const categories = [
    { id: 'all', label: 'All', icon: 'fa-th' },
    { id: 'triggers', label: 'Triggers', icon: 'fa-bolt' },
    { id: 'ai-models', label: 'AI Models', icon: 'fa-brain' },
    { id: 'actions', label: 'Actions', icon: 'fa-play' },
    { id: 'conditions', label: 'Conditions', icon: 'fa-code-branch' },
    { id: 'outputs', label: 'Outputs', icon: 'fa-upload' }
  ];

  const filteredNodes = nodeTemplates.filter(node => {
    const matchesSearch = node.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         node.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || node.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleDragStart = (e, nodeTemplate) => {
    e.dataTransfer.setData('application/json', JSON.stringify(nodeTemplate));
    e.dataTransfer.effectAllowed = 'copy';
  };

  return (
    <div className="node-palette">
      <div className="palette-header">
        <h3>Node Library</h3>
        <div className="search-box">
          <i className="fas fa-search"></i>
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="category-tabs">
        {categories.map(category => (
          <button
            key={category.id}
            className={`category-tab ${selectedCategory === category.id ? 'active' : ''}`}
            onClick={() => setSelectedCategory(category.id)}
          >
            <i className={`fas ${category.icon}`}></i>
            <span>{category.label}</span>
          </button>
        ))}
      </div>

      <div className="nodes-list">
        {filteredNodes.map(node => (
          <div
            key={node.id}
            className="palette-node"
            draggable
            onDragStart={(e) => handleDragStart(e, node)}
            onClick={() => onAddNode(node)}
          >
            <div className="node-icon">
              <i className={`fas ${node.icon}`}></i>
            </div>
            <div className="node-info">
              <div className="node-title">{node.title}</div>
              <div className="node-description">{node.description}</div>
            </div>
            <div className="drag-handle">
              <i className="fas fa-grip-vertical"></i>
            </div>
          </div>
        ))}
      </div>

      {filteredNodes.length === 0 && (
        <div className="no-results">
          <i className="fas fa-search"></i>
          <p>No nodes found matching your search.</p>
        </div>
      )}
    </div>
  );
};

export default NodePalette;