import React, { useState, useCallback, useRef } from 'react';
import WorkflowCanvas from './WorkflowCanvas';
import NodePalette from './NodePalette';
import WorkflowToolbar from './WorkflowToolbar';
import WorkflowTemplates from './WorkflowTemplates';
import './WorkflowBuilder.css';

const WorkflowBuilder = () => {
  const [nodes, setNodes] = useState([]);
  const [connections, setConnections] = useState([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionLogs, setExecutionLogs] = useState([]);
  const canvasRef = useRef(null);

  // Workflow Templates
  const workflowTemplates = [
    {
      id: 'viral-video-pipeline',
      name: 'Viral Video Pipeline',
      description: 'Complete automated video creation from trend detection to multi-platform publishing',
      icon: 'fa-rocket',
      nodes: [
        {
          id: 'trend_trigger',
          type: 'trigger',
          title: 'Trend Detection',
          position: { x: 100, y: 100 },
          icon: 'fa-fire',
          outputs: [{ id: 'trend_out', label: 'Trend Data' }],
          config: { 'Min Score': '75', 'Frequency': '3 hours' }
        },
        {
          id: 'director_agent',
          type: 'ai-model',
          title: 'Director Agent',
          position: { x: 400, y: 100 },
          icon: 'fa-user-tie',
          inputs: [{ id: 'trend_in', label: 'Trend Data' }],
          outputs: [{ id: 'storyboard_out', label: 'Storyboard' }],
          config: { 'Style': 'Viral', 'Duration': '30-45s' }
        },
        {
          id: 'sora_generator',
          type: 'ai-model',
          title: 'Sora Video Gen',
          position: { x: 700, y: 100 },
          icon: 'fa-video',
          inputs: [{ id: 'prompt_in', label: 'Prompt' }],
          outputs: [{ id: 'video_out', label: 'Video URL' }],
          config: { 'Quality': 'HD', 'Duration': '30s' }
        },
        {
          id: 'editor_agent',
          type: 'ai-model',
          title: 'Editor Agent',
          position: { x: 1000, y: 100 },
          icon: 'fa-cut',
          inputs: [{ id: 'video_in', label: 'Video URL' }],
          outputs: [{ id: 'edited_out', label: 'Edited Video' }],
          config: { 'Enhancements': 'Color,Audio,Stabilize' }
        },
        {
          id: 'quality_check',
          type: 'action',
          title: 'Quality Check',
          position: { x: 1300, y: 100 },
          icon: 'fa-shield-alt',
          inputs: [{ id: 'video_check', label: 'Video URL' }],
          outputs: [{ id: 'approved', label: 'Approved' }, { id: 'rejected', label: 'Rejected' }],
          config: { 'Threshold': '85%' }
        },
        {
          id: 'youtube_upload',
          type: 'action',
          title: 'YouTube Upload',
          position: { x: 1000, y: 300 },
          icon: 'fa-youtube',
          inputs: [{ id: 'yt_video', label: 'Video URL' }],
          outputs: [{ id: 'yt_result', label: 'Upload Result' }],
          config: { 'Privacy': 'Public', 'Tags': 'AI,Viral,Trending' }
        },
        {
          id: 'tiktok_upload',
          type: 'action',
          title: 'TikTok Upload',
          position: { x: 1300, y: 300 },
          icon: 'fa-tiktok',
          inputs: [{ id: 'tt_video', label: 'Video URL' }],
          outputs: [{ id: 'tt_result', label: 'Upload Result' }],
          config: { 'Sound': 'Trending', 'Hashtags': '#AI #Viral' }
        }
      ],
      connections: [
        { id: 'conn1', fromNode: 'trend_trigger', fromPort: 'trend_out', toNode: 'director_agent', toPort: 'trend_in' },
        { id: 'conn2', fromNode: 'director_agent', fromPort: 'storyboard_out', toNode: 'sora_generator', toPort: 'prompt_in' },
        { id: 'conn3', fromNode: 'sora_generator', fromPort: 'video_out', toNode: 'editor_agent', toPort: 'video_in' },
        { id: 'conn4', fromNode: 'editor_agent', fromPort: 'edited_out', toNode: 'quality_check', toPort: 'video_check' },
        { id: 'conn5', fromNode: 'quality_check', fromPort: 'approved', toNode: 'youtube_upload', toPort: 'yt_video' },
        { id: 'conn6', fromNode: 'quality_check', fromPort: 'approved', toNode: 'tiktok_upload', toPort: 'tt_video' }
      ]
    },
    {
      id: 'content-optimization',
      name: 'Content Optimization',
      description: 'Analyze and optimize existing content for better performance',
      icon: 'fa-chart-line',
      nodes: [
        {
          id: 'content_input',
          type: 'trigger',
          title: 'Content Input',
          position: { x: 100, y: 100 },
          icon: 'fa-upload',
          outputs: [{ id: 'content_out', label: 'Content Data' }]
        },
        {
          id: 'performance_analyzer',
          type: 'ai-model',
          title: 'Performance Analyzer',
          position: { x: 400, y: 100 },
          icon: 'fa-chart-bar',
          inputs: [{ id: 'content_in', label: 'Content Data' }],
          outputs: [{ id: 'analysis_out', label: 'Analysis' }]
        },
        {
          id: 'optimizer_agent',
          type: 'ai-model',
          title: 'Optimizer Agent',
          position: { x: 700, y: 100 },
          icon: 'fa-magic',
          inputs: [{ id: 'analysis_in', label: 'Analysis' }],
          outputs: [{ id: 'optimized_out', label: 'Optimized Content' }]
        }
      ],
      connections: [
        { id: 'conn1', fromNode: 'content_input', fromPort: 'content_out', toNode: 'performance_analyzer', toPort: 'content_in' },
        { id: 'conn2', fromNode: 'performance_analyzer', fromPort: 'analysis_out', toNode: 'optimizer_agent', toPort: 'analysis_in' }
      ]
    }
  ];

  const handleAddNode = useCallback((nodeTemplate) => {
    const newNode = {
      ...nodeTemplate,
      id: `${nodeTemplate.id}_${Date.now()}`,
      position: {
        x: Math.random() * 400 + 200,
        y: Math.random() * 300 + 150
      }
    };
    setNodes(prev => [...prev, newNode]);
  }, []);

  const handleDropNode = useCallback((e) => {
    e.preventDefault();
    try {
      const nodeData = JSON.parse(e.dataTransfer.getData('application/json'));
      const rect = canvasRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const newNode = {
        ...nodeData,
        id: `${nodeData.id}_${Date.now()}`,
        position: { x, y }
      };

      setNodes(prev => [...prev, newNode]);
    } catch (error) {
      console.error('Error dropping node:', error);
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
  }, []);

  const handleLoadTemplate = useCallback((template) => {
    setNodes(template.nodes);
    setConnections(template.connections);
    setSelectedWorkflow(template);
    addLog(`Loaded workflow template: ${template.name}`);
  }, []);

  const handleExecuteWorkflow = useCallback(async () => {
    if (nodes.length === 0) {
      addLog('Error: No nodes in workflow');
      return;
    }

    setIsExecuting(true);
    addLog('Starting workflow execution...');

    try {
      // Simulate workflow execution
      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];
        setNodes(prev => prev.map(n =>
          n.id === node.id ? { ...n, status: 'running', executionProgress: 0 } : n
        ));

        // Simulate processing time
        await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));

        // Update progress
        for (let progress = 0; progress <= 100; progress += 20) {
          setNodes(prev => prev.map(n =>
            n.id === node.id ? { ...n, executionProgress: progress } : n
          ));
          await new Promise(resolve => setTimeout(resolve, 200));
        }

        setNodes(prev => prev.map(n =>
          n.id === node.id ? { ...n, status: 'success', executionProgress: 100 } : n
        ));

        addLog(`Completed: ${node.title}`);
      }

      addLog('Workflow execution completed successfully!');
    } catch (error) {
      addLog(`Error: ${error.message}`);
      setNodes(prev => prev.map(n => ({ ...n, status: 'error' })));
    } finally {
      setIsExecuting(false);
    }
  }, [nodes]);

  const addLog = useCallback((message) => {
    const timestamp = new Date().toLocaleTimeString();
    setExecutionLogs(prev => [...prev, { timestamp, message }]);
  }, []);

  const handleSaveWorkflow = useCallback(() => {
    const workflowData = {
      nodes,
      connections,
      name: selectedWorkflow?.name || 'Untitled Workflow',
      timestamp: new Date().toISOString()
    };

    // In a real app, this would save to backend
    localStorage.setItem('savedWorkflow', JSON.stringify(workflowData));
    addLog('Workflow saved successfully');
  }, [nodes, connections, selectedWorkflow]);

  const handleClearCanvas = useCallback(() => {
    setNodes([]);
    setConnections([]);
    setSelectedWorkflow(null);
    setExecutionLogs([]);
    addLog('Canvas cleared');
  }, []);

  return (
    <div className="workflow-builder">
      <WorkflowToolbar
        onExecute={handleExecuteWorkflow}
        onSave={handleSaveWorkflow}
        onClear={handleClearCanvas}
        isExecuting={isExecuting}
        nodeCount={nodes.length}
        connectionCount={connections.length}
      />

      <div className="workflow-main">
        <NodePalette onAddNode={handleAddNode} />

        <div className="workflow-canvas-area">
          <WorkflowTemplates
            templates={workflowTemplates}
            onLoadTemplate={handleLoadTemplate}
          />

          <div
            className="canvas-drop-zone"
            onDrop={handleDropNode}
            onDragOver={handleDragOver}
          >
            <WorkflowCanvas
              ref={canvasRef}
              nodes={nodes}
              connections={connections}
              onNodesChange={setNodes}
              onConnectionsChange={setConnections}
            />
          </div>
        </div>

        <div className="workflow-sidebar">
          <div className="execution-panel">
            <h3>Execution Logs</h3>
            <div className="logs-container">
              {executionLogs.map((log, index) => (
                <div key={index} className="log-entry">
                  <span className="log-timestamp">{log.timestamp}</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="workflow-info">
            <h3>Workflow Info</h3>
            <div className="info-stats">
              <div className="stat">
                <span className="stat-label">Nodes:</span>
                <span className="stat-value">{nodes.length}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Connections:</span>
                <span className="stat-value">{connections.length}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Status:</span>
                <span className={`stat-value ${isExecuting ? 'executing' : 'idle'}`}>
                  {isExecuting ? 'Running' : 'Ready'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkflowBuilder;