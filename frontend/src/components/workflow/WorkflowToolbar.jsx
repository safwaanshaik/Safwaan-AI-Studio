import React from 'react';

const WorkflowToolbar = ({
  onExecute,
  onSave,
  onClear,
  isExecuting,
  nodeCount,
  connectionCount
}) => {
  return (
    <div className="workflow-toolbar">
      <div className="toolbar-left">
        <div className="workflow-title">
          <h2>CINEMATRIX Workflow Builder</h2>
          <div className="workflow-stats">
            <span className="stat-item">
              <i className="fas fa-project-diagram"></i>
              {nodeCount} nodes
            </span>
            <span className="stat-item">
              <i className="fas fa-link"></i>
              {connectionCount} connections
            </span>
          </div>
        </div>
      </div>

      <div className="toolbar-center">
        <div className="workflow-status">
          {isExecuting ? (
            <div className="status-executing">
              <div className="status-spinner"></div>
              <span>Executing Workflow...</span>
            </div>
          ) : (
            <div className="status-ready">
              <i className="fas fa-check-circle"></i>
              <span>Ready to Execute</span>
            </div>
          )}
        </div>
      </div>

      <div className="toolbar-right">
        <div className="toolbar-actions">
          <button
            className="toolbar-btn secondary"
            onClick={onClear}
            disabled={isExecuting}
            title="Clear Canvas"
          >
            <i className="fas fa-trash-alt"></i>
            <span>Clear</span>
          </button>

          <button
            className="toolbar-btn secondary"
            onClick={onSave}
            disabled={isExecuting}
            title="Save Workflow"
          >
            <i className="fas fa-save"></i>
            <span>Save</span>
          </button>

          <button
            className="toolbar-btn primary"
            onClick={onExecute}
            disabled={isExecuting || nodeCount === 0}
            title="Execute Workflow"
          >
            {isExecuting ? (
              <>
                <div className="btn-spinner"></div>
                <span>Running...</span>
              </>
            ) : (
              <>
                <i className="fas fa-play"></i>
                <span>Execute</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default WorkflowToolbar;