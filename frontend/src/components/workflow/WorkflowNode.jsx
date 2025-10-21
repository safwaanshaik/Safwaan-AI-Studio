import React, { useState } from 'react';

const WorkflowNode = ({
  node,
  isSelected,
  onMouseDown,
  onMouseUp,
  onDragStart,
  onDragEnd,
  onSelect,
  onConfigChange
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState('');

  const handleDoubleClick = () => {
    if (node.config && Object.keys(node.config).length > 0) {
      setIsEditing(true);
    }
  };

  const handleConfigSave = () => {
    if (editValue.trim()) {
      onConfigChange?.(node.id, { ...node.config, [editValue.split(':')[0]]: editValue.split(':')[1] });
    }
    setIsEditing(false);
    setEditValue('');
  };

  const getNodeTypeColor = (type) => {
    switch (type) {
      case 'trigger': return '#10b981';
      case 'action': return '#06b6d4';
      case 'condition': return '#f59e0b';
      case 'ai-model': return '#a855f7';
      case 'output': return '#ef4444';
      default: return '#64748b';
    }
  };

  const getNodeTypeIcon = (type) => {
    switch (type) {
      case 'trigger': return 'fa-bolt';
      case 'action': return 'fa-play';
      case 'condition': return 'fa-code-branch';
      case 'ai-model': return 'fa-brain';
      case 'output': return 'fa-upload';
      default: return 'fa-cog';
    }
  };

  return (
    <div
      className={`workflow-node ${isSelected ? 'selected' : ''} ${node.type || 'default'}`}
      style={{
        left: node.position.x,
        top: node.position.y,
        borderLeftColor: getNodeTypeColor(node.type)
      }}
      onDoubleClick={handleDoubleClick}
    >
      <div className="node-header">
        <div
          className="node-icon"
          style={{ background: `linear-gradient(135deg, ${getNodeTypeColor(node.type)}, ${getNodeTypeColor(node.type)}dd)` }}
        >
          <i className={`fas ${node.icon || getNodeTypeIcon(node.type)}`}></i>
        </div>
        <div className="node-title">{node.title}</div>
        <div className="node-status">
          <div className={`status-indicator ${node.status || 'idle'}`}></div>
        </div>
      </div>

      <div className="node-content">
        {node.description && (
          <div className="node-description">{node.description}</div>
        )}

        {node.config && Object.keys(node.config).length > 0 && (
          <div className="node-config">
            {Object.entries(node.config).map(([key, value]) => (
              <div key={key} className="config-item">
                <label>{key}:</label>
                <span>{value}</span>
              </div>
            ))}
          </div>
        )}

        {/* Execution Progress */}
        {node.executionProgress && (
          <div className="execution-progress">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${node.executionProgress}%` }}
              ></div>
            </div>
            <div className="progress-text">{node.executionProgress}%</div>
          </div>
        )}

        {/* Error Display */}
        {node.error && (
          <div className="node-error">
            <i className="fas fa-exclamation-triangle"></i>
            <span>{node.error}</span>
          </div>
        )}
      </div>

      <div className="node-ports">
        <div className="input-ports">
          {node.inputs?.map(port => (
            <div
              key={port.id}
              className="node-port input-port"
              onMouseDown={(e) => onMouseDown(e, port.id, 'input')}
              onMouseUp={(e) => onMouseUp(e, port.id, 'input')}
              title={port.description || port.label}
            >
              <div className="port-label">{port.label}</div>
              <div className="port-connector"></div>
            </div>
          ))}
        </div>

        <div className="output-ports">
          {node.outputs?.map(port => (
            <div
              key={port.id}
              className="node-port output-port"
              onMouseDown={(e) => onMouseDown(e, port.id, 'output')}
              onMouseUp={(e) => onMouseUp(e, port.id, 'output')}
              title={port.description || port.label}
            >
              <div className="port-connector"></div>
              <div className="port-label">{port.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Configuration Modal */}
      {isEditing && (
        <div className="node-config-modal">
          <div className="modal-header">
            <h3>Configure {node.title}</h3>
            <button onClick={() => setIsEditing(false)}>×</button>
          </div>
          <div className="modal-body">
            {node.config && Object.entries(node.config).map(([key, value]) => (
              <div key={key} className="config-field">
                <label>{key}</label>
                <input
                  type="text"
                  defaultValue={value}
                  onChange={(e) => {
                    const newConfig = { ...node.config, [key]: e.target.value };
                    onConfigChange?.(node.id, newConfig);
                  }}
                />
              </div>
            ))}
          </div>
          <div className="modal-footer">
            <button onClick={() => setIsEditing(false)}>Cancel</button>
            <button onClick={handleConfigSave}>Save</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkflowNode;