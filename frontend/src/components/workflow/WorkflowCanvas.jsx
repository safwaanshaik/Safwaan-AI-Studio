import React, { useState, useRef, useCallback, useEffect } from 'react';
import './WorkflowCanvas.css';

const WorkflowCanvas = ({ nodes = [], connections = [], onNodesChange, onConnectionsChange }) => {
  const canvasRef = useRef(null);
  const [draggedNode, setDraggedNode] = useState(null);
  const [connecting, setConnecting] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState(null);
  const [canvasOffset, setCanvasOffset] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);

  // Handle mouse move for connections and dragging
  const handleMouseMove = useCallback((e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left - canvasOffset.x) / zoom;
    const y = (e.clientY - rect.top - canvasOffset.y) / zoom;

    setMousePos({ x, y });

    if (draggedNode) {
      const updatedNodes = nodes.map(node =>
        node.id === draggedNode.id
          ? { ...node, position: { x, y } }
          : node
      );
      onNodesChange(updatedNodes);
    }
  }, [draggedNode, nodes, onNodesChange, canvasOffset, zoom]);

  // Handle mouse down for starting connections or selecting nodes
  const handleMouseDown = useCallback((e, nodeId, portId, portType) => {
    e.stopPropagation();

    if (portType === 'output') {
      setConnecting({ fromNode: nodeId, fromPort: portId, startPos: mousePos });
    } else if (portType === 'input') {
      // Handle input port connections
      const existingConnection = connections.find(conn =>
        conn.toNode === nodeId && conn.toPort === portId
      );
      if (existingConnection) {
        // Remove existing connection
        onConnectionsChange(connections.filter(conn =>
          !(conn.toNode === nodeId && conn.toPort === portId)
        ));
      }
    }
  }, [mousePos, connections, onConnectionsChange]);

  // Handle mouse up for completing connections
  const handleMouseUp = useCallback((e, nodeId, portId, portType) => {
    if (connecting && portType === 'input' && connecting.fromNode !== nodeId) {
      const newConnection = {
        id: `conn_${Date.now()}`,
        fromNode: connecting.fromNode,
        fromPort: connecting.fromPort,
        toNode: nodeId,
        toPort: portId
      };
      onConnectionsChange([...connections, newConnection]);
    }
    setConnecting(null);
  }, [connecting, connections, onConnectionsChange]);

  // Handle canvas click for deselection
  const handleCanvasClick = useCallback(() => {
    setSelectedNode(null);
    setConnecting(null);
  }, []);

  // Handle zoom
  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(prevZoom => Math.max(0.1, Math.min(3, prevZoom * zoomFactor)));
  }, []);

  // Handle canvas panning
  const handleCanvasMouseDown = useCallback((e) => {
    if (e.target === canvasRef.current) {
      const startX = e.clientX - canvasOffset.x;
      const startY = e.clientY - canvasOffset.y;

      const handleMouseMove = (e) => {
        setCanvasOffset({
          x: e.clientX - startX,
          y: e.clientY - startY
        });
      };

      const handleMouseUp = () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
  }, [canvasOffset]);

  return (
    <div className="workflow-canvas-container">
      <div className="workflow-toolbar">
        <div className="zoom-controls">
          <button onClick={() => setZoom(Math.max(0.1, zoom - 0.1))}>-</button>
          <span>{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom(Math.min(3, zoom + 0.1))}>+</button>
        </div>
        <div className="canvas-info">
          Nodes: {nodes.length} | Connections: {connections.length}
        </div>
      </div>

      <div
        ref={canvasRef}
        className="workflow-canvas"
        onMouseMove={handleMouseMove}
        onMouseDown={handleCanvasMouseDown}
        onWheel={handleWheel}
        onClick={handleCanvasClick}
        style={{
          transform: `translate(${canvasOffset.x}px, ${canvasOffset.y}px) scale(${zoom})`,
          transformOrigin: '0 0'
        }}
      >
        {/* Grid Background */}
        <div className="canvas-grid" />

        {/* Render Connections */}
        <svg className="connections-layer">
          {connections.map(connection => {
            const fromNode = nodes.find(n => n.id === connection.fromNode);
            const toNode = nodes.find(n => n.id === connection.toNode);

            if (!fromNode || !toNode) return null;

            const fromPos = {
              x: fromNode.position.x + 150, // Node width / 2
              y: fromNode.position.y + 30   // Port position
            };
            const toPos = {
              x: toNode.position.x + 150,
              y: toNode.position.y + 30
            };

            // Create curved path
            const dx = toPos.x - fromPos.x;
            const dy = toPos.y - fromPos.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            const curvature = Math.min(distance * 0.3, 100);

            const pathData = `M ${fromPos.x} ${fromPos.y} C ${fromPos.x + curvature} ${fromPos.y} ${toPos.x - curvature} ${toPos.y} ${toPos.x} ${toPos.y}`;

            return (
              <g key={connection.id}>
                <path
                  d={pathData}
                  className="connection-path"
                  stroke="#06b6d4"
                  strokeWidth="2"
                  fill="none"
                  markerEnd="url(#arrowhead)"
                />
                <circle
                  cx={fromPos.x}
                  cy={fromPos.y}
                  r="4"
                  className="connection-handle from-handle"
                  onClick={() => onConnectionsChange(connections.filter(c => c.id !== connection.id))}
                />
                <circle
                  cx={toPos.x}
                  cy={toPos.y}
                  r="4"
                  className="connection-handle to-handle"
                  onClick={() => onConnectionsChange(connections.filter(c => c.id !== connection.id))}
                />
              </g>
            );
          })}

          {/* Temporary connection line while connecting */}
          {connecting && (
            <path
              d={`M ${connecting.startPos.x} ${connecting.startPos.y} L ${mousePos.x} ${mousePos.y}`}
              className="temp-connection"
              stroke="#06b6d4"
              strokeWidth="2"
              strokeDasharray="5,5"
              fill="none"
            />
          )}

          {/* Arrow marker definition */}
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3.5, 0 7"
                fill="#06b6d4"
              />
            </marker>
          </defs>
        </svg>

        {/* Render Nodes */}
        {nodes.map(node => (
          <WorkflowNode
            key={node.id}
            node={node}
            isSelected={selectedNode === node.id}
            onMouseDown={(e, portId, portType) => handleMouseDown(e, node.id, portId, portType)}
            onMouseUp={(e, portId, portType) => handleMouseUp(e, node.id, portId, portType)}
            onDragStart={() => setDraggedNode(node)}
            onDragEnd={() => setDraggedNode(null)}
            onSelect={() => setSelectedNode(node.id)}
          />
        ))}
      </div>

      {/* Mini Map */}
      <div className="canvas-minimap">
        <div className="minimap-viewport" style={{
          transform: `translate(${-canvasOffset.x * 0.1}px, ${-canvasOffset.y * 0.1}px) scale(${zoom * 0.1})`
        }}>
          {nodes.map(node => (
            <div
              key={node.id}
              className="minimap-node"
              style={{
                left: node.position.x * 0.1,
                top: node.position.y * 0.1
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

const WorkflowNode = ({ node, isSelected, onMouseDown, onMouseUp, onDragStart, onDragEnd, onSelect }) => {
  const nodeRef = useRef(null);

  const handleMouseDown = (e) => {
    if (e.target.classList.contains('node-port')) return;
    onDragStart();
    onSelect();
  };

  return (
    <div
      ref={nodeRef}
      className={`workflow-node ${isSelected ? 'selected' : ''} ${node.type}`}
      style={{
        left: node.position.x,
        top: node.position.y
      }}
      onMouseDown={handleMouseDown}
      onMouseUp={onDragEnd}
    >
      <div className="node-header">
        <div className="node-icon">
          <i className={`fas ${node.icon || 'fa-cog'}`}></i>
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

        {node.config && (
          <div className="node-config">
            {Object.entries(node.config).map(([key, value]) => (
              <div key={key} className="config-item">
                <label>{key}:</label>
                <span>{value}</span>
              </div>
            ))}
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
            >
              <div className="port-connector"></div>
              <div className="port-label">{port.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default WorkflowCanvas;