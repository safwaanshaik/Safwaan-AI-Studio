import logging
import asyncio
from typing import Dict, Any, List, Tuple, Set, Optional
import datetime
from sqlalchemy.orm import Session
from app.db.models.workflow import (
    Workflow, WorkflowNode, WorkflowConnection, 
    WorkflowExecution, WorkflowExecutionLog
)
from ai_engine.pipelines import VideoGenerationPipeline
from app.core.config import settings

logger = logging.getLogger(__name__)

class NodeExecutionError(Exception):
    """Exception raised when a node execution fails"""
    pass

class WorkflowEngine:
    """Engine for executing workflow graphs"""
    
    def __init__(self, db: Session, execution_id: int):
        self.db = db
        self.execution_id = execution_id
        self.execution = None
        self.nodes = {}
        self.connections = {}
        self.node_outputs = {}
        self.visited_nodes = set()
        self.pipeline = VideoGenerationPipeline()
        
    async def load_workflow(self) -> Workflow:
        """Load workflow data from database"""
        self.execution = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.id == self.execution_id
        ).first()
        
        if not self.execution:
            raise ValueError(f"Execution {self.execution_id} not found")
            
        workflow = self.db.query(Workflow).filter(
            Workflow.id == self.execution.workflow_id
        ).first()
        
        if not workflow:
            raise ValueError(f"Workflow {self.execution.workflow_id} not found")
            
        # Load nodes
        nodes = self.db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == workflow.id
        ).all()
        
        self.nodes = {node.id: node for node in nodes}
        
        # Load connections
        connections = self.db.query(WorkflowConnection).filter(
            WorkflowConnection.workflow_id == workflow.id
        ).all()
        
        # Group connections by target node
        self.connections = {}
        for conn in connections:
            if conn.target_node_id not in self.connections:
                self.connections[conn.target_node_id] = []
            self.connections[conn.target_node_id].append(conn)
            
        return workflow
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the workflow"""
        try:
            # Start execution
            workflow = await self.load_workflow()
            
            self.execution.status = "running"
            self.execution.started_at = datetime.datetime.utcnow()
            self.db.commit()
            
            await self.log("Workflow execution started", level="info")
            
            # Find source nodes (nodes without incoming connections)
            source_nodes = self._find_source_nodes()
            
            # Execute from each source node
            results = {}
            for node_id in source_nodes:
                node_result = await self._execute_node(node_id)
                results[node_id] = node_result
                
            # Update execution with success status
            self.execution.status = "completed"
            self.execution.progress = 100
            self.execution.completed_at = datetime.datetime.utcnow()
            self.execution.output_data = self._get_final_outputs(results)
            self.db.commit()
            
            await self.log("Workflow execution completed successfully", level="info")
            
            return {
                "success": True,
                "execution_id": self.execution_id,
                "output": self.execution.output_data
            }
            
        except Exception as e:
            # Handle any exceptions during execution
            logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
            
            self.execution.status = "failed"
            self.execution.error_message = str(e)
            self.execution.completed_at = datetime.datetime.utcnow()
            self.db.commit()
            
            await self.log(f"Workflow execution failed: {str(e)}", level="error")
            
            return {
                "success": False,
                "execution_id": self.execution_id,
                "error": str(e)
            }
    
    def _find_source_nodes(self) -> List[int]:
        """Find source nodes (nodes without incoming connections)"""
        # All nodes that are targets of connections
        target_nodes = set()
        for connections in self.connections.values():
            for conn in connections:
                target_nodes.add(conn.target_node_id)
                
        # Nodes that are not targets are source nodes
        source_nodes = [node_id for node_id in self.nodes.keys() if node_id not in target_nodes]
        
        if not source_nodes:
            # If no source nodes found, there might be a cycle
            # For simplicity, we'll use the first node as a source
            return [next(iter(self.nodes.keys()))] if self.nodes else []
            
        return source_nodes
    
    def _find_sink_nodes(self) -> List[int]:
        """Find sink nodes (nodes without outgoing connections)"""
        # All nodes that are sources of connections
        source_nodes = set()
        for connections in self.connections.values():
            for conn in connections:
                source_nodes.add(conn.source_node_id)
                
        # Nodes that are not sources are sink nodes
        sink_nodes = [node_id for node_id in self.nodes.keys() if node_id not in source_nodes]
        
        return sink_nodes
    
    def _get_final_outputs(self, results: Dict[int, Any]) -> Dict[str, Any]:
        """Get final outputs from sink nodes"""
        sink_nodes = self._find_sink_nodes()
        
        outputs = {}
        for node_id in sink_nodes:
            if node_id in self.node_outputs:
                node = self.nodes[node_id]
                outputs[node.name] = self.node_outputs[node_id]
                
        return outputs
    
    async def _execute_node(self, node_id: int) -> Any:
        """Execute a single node and its descendants"""
        # If node already visited, return its output
        if node_id in self.visited_nodes:
            return self.node_outputs.get(node_id)
            
        node = self.nodes[node_id]
        
        # Mark node as visited
        self.visited_nodes.add(node_id)
        
        try:
            # Log node execution start
            await self.log(f"Executing node: {node.name} ({node.node_type})", node_id=node_id)
            
            # Get input data from parent nodes
            input_data = await self._get_node_inputs(node_id)
            
            # Execute node based on its type
            node_output = await self._process_node(node, input_data)
            
            # Store node output
            self.node_outputs[node_id] = node_output
            
            # Log node execution success
            await self.log(
                f"Node executed successfully: {node.name}", 
                node_id=node_id,
                data={"output_summary": str(node_output)[:100]}
            )
            
            # Execute child nodes
            child_results = {}
            child_nodes = self._find_child_nodes(node_id)
            
            for child_id in child_nodes:
                child_result = await self._execute_node(child_id)
                child_results[child_id] = child_result
                
            # Update progress
            progress = int((len(self.visited_nodes) / len(self.nodes)) * 100)
            self.execution.progress = min(progress, 99)  # Keep at 99% until fully complete
            self.db.commit()
                
            return node_output
            
        except Exception as e:
            # Log node execution failure
            await self.log(
                f"Node execution failed: {str(e)}", 
                level="error",
                node_id=node_id
            )
            
            raise NodeExecutionError(f"Error executing node {node.name}: {str(e)}")
    
    async def _get_node_inputs(self, node_id: int) -> Dict[str, Any]:
        """Get input data for a node from its parent nodes"""
        # If node has no parent connections, use execution input data
        if node_id not in self.connections:
            return self.execution.input_data or {}
            
        input_data = {}
        
        # Process each incoming connection
        for conn in self.connections[node_id]:
            # Get source node
            source_node_id = conn.source_node_id
            source_node = self.nodes[source_node_id]
            
            # Execute source node if not already executed
            if source_node_id not in self.visited_nodes:
                await self._execute_node(source_node_id)
                
            # Get output from source node
            source_output = self.node_outputs.get(source_node_id)
            
            # Map to specific input based on handles
            if conn.target_handle:
                input_data[conn.target_handle] = source_output
            else:
                # If no specific handle, merge all data
                if isinstance(source_output, dict):
                    input_data.update(source_output)
                else:
                    input_data[source_node.name] = source_output
                    
        return input_data
    
    def _find_child_nodes(self, node_id: int) -> List[int]:
        """Find child nodes connected to the given node"""
        child_nodes = []
        
        # Check all connections for those where this node is the source
        for target_id, connections in self.connections.items():
            for conn in connections:
                if conn.source_node_id == node_id:
                    child_nodes.append(target_id)
                    
        return child_nodes
        
    async def _process_node(self, node: WorkflowNode, input_data: Dict[str, Any]) -> Any:
        """Process a node based on its type"""
        # This will be expanded with specific node type implementations
        node_type = node.node_type.lower()
        
        # Get node config
        config = node.config or {}
        
        # Default implementation with node type mapping
        if node_type == "input.text":
            # Text input node
            return config.get("text", "")
            
        elif node_type == "input.json":
            # JSON input node
            return config.get("json", {})
            
        elif node_type == "input.image":
            # Image input node (path to image)
            return config.get("image_path", "")
            
        elif node_type == "input.video":
            # Video input node (path to video)
            return config.get("video_path", "")
            
        elif node_type == "input.trend":
            # Trend data input node
            trend_keyword = config.get("trend_keyword", "")
            if not trend_keyword and input_data.get("keyword"):
                trend_keyword = input_data.get("keyword")
                
            # In a real implementation, this would fetch trend data
            return {
                "keyword": trend_keyword,
                "viral_score": config.get("viral_score", 75),
                "category": config.get("category", "general"),
                "volume": config.get("volume", 1000)
            }
            
        elif node_type == "output.video":
            # Video output node
            video_data = input_data.get("video_data") or input_data
            return video_data
            
        elif node_type == "output.metadata":
            # Metadata output node
            metadata = input_data.get("metadata") or input_data
            return metadata
            
        elif node_type == "ai.script":
            # Script generation node
            trend_data = input_data.get("trend_data") or input_data
            prompt_override = config.get("prompt")
            
            if prompt_override:
                # Use provided prompt
                script_prompt = prompt_override
            else:
                # Generate prompt from trend data
                keyword = trend_data.get("keyword", "")
                script_prompt = f"Create a script for a video about {keyword}"
                
            # In a full implementation, this would use a LLM or the script_writer_agent
            return {
                "title": f"Video about {trend_data.get('keyword', 'topic')}",
                "description": f"An engaging video about {trend_data.get('keyword', 'interesting topic')}",
                "script": f"[SCRIPT PLACEHOLDER] This would be a full script about {trend_data.get('keyword', 'the topic')}",
                "keywords": [trend_data.get("keyword", "topic"), "video", "content"]
            }
            
        elif node_type == "ai.storyboard":
            # Storyboard generation node
            script_data = input_data.get("script") or input_data
            
            # In a full implementation, this would use the director_agent
            return {
                "scenes": [
                    {"description": "Opening scene", "duration": 5},
                    {"description": "Main content", "duration": 15},
                    {"description": "Closing scene", "duration": 5}
                ],
                "style": config.get("style", "cinematic"),
                "aspect_ratio": config.get("aspect_ratio", "16:9")
            }
            
        elif node_type == "ai.video_generation":
            # Video generation node
            model = config.get("model", "auto")
            prompt = input_data.get("prompt", "")
            
            if not prompt:
                # Try to generate prompt from script or trend data
                script = input_data.get("script", {})
                if script:
                    prompt = f"Create a video about {script.get('title', 'the topic')}"
                else:
                    trend_data = input_data.get("trend_data", {})
                    prompt = f"Create a video about {trend_data.get('keyword', 'the topic')}"
            
            # In a full implementation, this would use the pipeline.generate_video method
            return {
                "video_url": f"/static/videos/generated_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
                "thumbnail_url": f"/static/thumbnails/thumb_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                "duration": config.get("duration", 30),
                "model_used": model
            }
            
        elif node_type == "ai.audio":
            # Audio processing node
            video_data = input_data.get("video_data") or input_data
            
            # In a full implementation, this would use the audio_agent
            return {
                **video_data,
                "audio_enhanced": True,
                "audio_type": config.get("audio_type", "background_music")
            }
            
        elif node_type == "transform.enhance":
            # Video enhancement node
            video_data = input_data.get("video_data") or input_data
            
            # In a full implementation, this would use video enhancement APIs
            return {
                **video_data,
                "enhanced": True,
                "quality": "improved"
            }
            
        elif node_type == "transform.text_overlay":
            # Text overlay node
            video_data = input_data.get("video_data") or input_data
            
            # In a full implementation, this would add text overlays to the video
            return {
                **video_data,
                "has_text_overlay": True,
                "text_content": config.get("text", "Sample Text")
            }
            
        elif node_type == "transform.concat":
            # Video concatenation node
            videos = []
            
            # Extract videos from input
            for key, value in input_data.items():
                if isinstance(value, dict) and "video_url" in value:
                    videos.append(value)
            
            # In a full implementation, this would concatenate the videos
            return {
                "video_url": f"/static/videos/concatenated_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
                "duration": sum(v.get("duration", 0) for v in videos),
                "source_videos": len(videos)
            }
            
        elif node_type == "control.branch":
            # Branching control node
            condition_field = config.get("condition_field", "")
            condition_value = config.get("condition_value", "")
            
            # Get the value to compare
            actual_value = input_data.get(condition_field)
            
            # Determine output path
            if str(actual_value) == str(condition_value):
                return {"result": "true", "data": input_data}
            else:
                return {"result": "false", "data": input_data}
            
        elif node_type == "control.merge":
            # Merge multiple inputs
            return input_data
            
        else:
            # Default pass-through for unknown node types
            logger.warning(f"Unknown node type: {node_type}, using pass-through behavior")
            return input_data
    
    async def log(self, message: str, level: str = "info", node_id: Optional[int] = None, data: Dict[str, Any] = None) -> None:
        """Add a log entry for the execution"""
        log_entry = WorkflowExecutionLog(
            execution_id=self.execution_id,
            node_id=node_id,
            level=level,
            message=message,
            data=data or {}
        )
        
        self.db.add(log_entry)
        self.db.commit()
        
        logger.log(
            getattr(logging, level.upper(), logging.INFO),
            f"Workflow {self.execution.workflow_id} - Execution {self.execution_id}: {message}"
        )