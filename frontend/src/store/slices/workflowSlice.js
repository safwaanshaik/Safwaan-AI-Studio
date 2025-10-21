import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  currentWorkflow: null,
  workflows: [],
  nodes: [],
  connections: [],
  executionState: 'idle', // idle, running, paused, completed, error
  executionLogs: [],
  selectedNode: null,
  canvasOffset: { x: 0, y: 0 },
  zoom: 1,
  templates: [],
  isLoading: false,
  error: null,
};

const workflowSlice = createSlice({
  name: 'workflow',
  initialState,
  reducers: {
    setCurrentWorkflow: (state, action) => {
      state.currentWorkflow = action.payload;
    },
    setNodes: (state, action) => {
      state.nodes = action.payload;
    },
    setConnections: (state, action) => {
      state.connections = action.payload;
    },
    addNode: (state, action) => {
      state.nodes.push(action.payload);
    },
    updateNode: (state, action) => {
      const { id, updates } = action.payload;
      const nodeIndex = state.nodes.findIndex(node => node.id === id);
      if (nodeIndex !== -1) {
        state.nodes[nodeIndex] = { ...state.nodes[nodeIndex], ...updates };
      }
    },
    removeNode: (state, action) => {
      const nodeId = action.payload;
      state.nodes = state.nodes.filter(node => node.id !== nodeId);
      state.connections = state.connections.filter(
        conn => conn.fromNode !== nodeId && conn.toNode !== nodeId
      );
    },
    addConnection: (state, action) => {
      state.connections.push(action.payload);
    },
    removeConnection: (state, action) => {
      const connectionId = action.payload;
      state.connections = state.connections.filter(conn => conn.id !== connectionId);
    },
    setExecutionState: (state, action) => {
      state.executionState = action.payload;
    },
    addExecutionLog: (state, action) => {
      state.executionLogs.push({
        id: Date.now(),
        timestamp: new Date().toISOString(),
        ...action.payload,
      });
    },
    clearExecutionLogs: (state) => {
      state.executionLogs = [];
    },
    setSelectedNode: (state, action) => {
      state.selectedNode = action.payload;
    },
    setCanvasOffset: (state, action) => {
      state.canvasOffset = action.payload;
    },
    setZoom: (state, action) => {
      state.zoom = Math.max(0.1, Math.min(3, action.payload));
    },
    setTemplates: (state, action) => {
      state.templates = action.payload;
    },
    setLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    setError: (state, action) => {
      state.error = action.payload;
    },
    resetWorkflow: (state) => {
      state.nodes = [];
      state.connections = [];
      state.executionState = 'idle';
      state.executionLogs = [];
      state.selectedNode = null;
      state.currentWorkflow = null;
    },
    loadWorkflow: (state, action) => {
      const { nodes, connections, ...workflowData } = action.payload;
      state.nodes = nodes || [];
      state.connections = connections || [];
      state.currentWorkflow = workflowData;
      state.executionState = 'idle';
      state.executionLogs = [];
      state.selectedNode = null;
    },
    saveWorkflow: (state) => {
      // This would typically trigger an API call
      // For now, we'll just mark it as saved
      if (state.currentWorkflow) {
        state.currentWorkflow.lastSaved = new Date().toISOString();
      }
    },
  },
});

export const {
  setCurrentWorkflow,
  setNodes,
  setConnections,
  addNode,
  updateNode,
  removeNode,
  addConnection,
  removeConnection,
  setExecutionState,
  addExecutionLog,
  clearExecutionLogs,
  setSelectedNode,
  setCanvasOffset,
  setZoom,
  setTemplates,
  setLoading,
  setError,
  resetWorkflow,
  loadWorkflow,
  saveWorkflow,
} = workflowSlice.actions;

export default workflowSlice.reducer;