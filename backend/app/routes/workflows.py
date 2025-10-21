from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import logging
from datetime import datetime

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.workflow_engine import WorkflowEngine
from app.db.models.workflow import (
    Workflow, WorkflowNode, WorkflowConnection,
    WorkflowExecution, WorkflowExecutionLog, WorkflowTemplate
)
from app.db.models.user import User
from app.schemas.workflow import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    WorkflowNodeCreate, WorkflowNodeUpdate, WorkflowNodeResponse,
    WorkflowConnectionCreate, WorkflowConnectionResponse,
    WorkflowExecutionCreate, WorkflowExecutionResponse,
    WorkflowExecutionLogResponse, WorkflowTemplateResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Workflow CRUD
@router.post("/", response_model=WorkflowResponse)
async def create_workflow(
    workflow: WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_workflow = Workflow(
        name=workflow.name,
        description=workflow.description,
        user_id=current_user.id,
        project_id=workflow.project_id,
        tags=workflow.tags,
        settings=workflow.settings
    )
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    return db_workflow

@router.get("/", response_model=List[WorkflowResponse])
async def get_workflows(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Workflow).filter(Workflow.user_id == current_user.id)
    if project_id:
        query = query.filter(Workflow.project_id == project_id)
    workflows = query.offset(skip).limit(limit).all()
    return workflows

@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow

@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: int,
    workflow_update: WorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    for field, value in workflow_update.dict(exclude_unset=True).items():
        setattr(workflow, field, value)

    db.commit()
    db.refresh(workflow)
    return workflow

@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    db.delete(workflow)
    db.commit()
    return {"message": "Workflow deleted successfully"}

# Workflow Nodes
@router.post("/{workflow_id}/nodes", response_model=WorkflowNodeResponse)
async def create_workflow_node(
    workflow_id: int,
    node: WorkflowNodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify workflow ownership
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    db_node = WorkflowNode(
        workflow_id=workflow_id,
        node_type=node.node_type,
        name=node.name,
        position_x=node.position_x,
        position_y=node.position_y,
        config=node.config,
        settings=node.settings
    )
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return db_node

@router.get("/{workflow_id}/nodes", response_model=List[WorkflowNodeResponse])
async def get_workflow_nodes(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify workflow ownership
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    nodes = db.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow_id).all()
    return nodes

@router.put("/{workflow_id}/nodes/{node_id}", response_model=WorkflowNodeResponse)
async def update_workflow_node(
    workflow_id: int,
    node_id: int,
    node_update: WorkflowNodeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify workflow ownership
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    node = db.query(WorkflowNode).filter(
        WorkflowNode.id == node_id,
        WorkflowNode.workflow_id == workflow_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    for field, value in node_update.dict(exclude_unset=True).items():
        setattr(node, field, value)

    db.commit()
    db.refresh(node)
    return node

# Workflow Connections
@router.post("/{workflow_id}/connections", response_model=WorkflowConnectionResponse)
async def create_workflow_connection(
    workflow_id: int,
    connection: WorkflowConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify workflow ownership
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Verify nodes exist in this workflow
    source_node = db.query(WorkflowNode).filter(
        WorkflowNode.id == connection.source_node_id,
        WorkflowNode.workflow_id == workflow_id
    ).first()
    target_node = db.query(WorkflowNode).filter(
        WorkflowNode.id == connection.target_node_id,
        WorkflowNode.workflow_id == workflow_id
    ).first()

    if not source_node or not target_node:
        raise HTTPException(status_code=400, detail="Invalid node IDs")

    db_connection = WorkflowConnection(
        workflow_id=workflow_id,
        source_node_id=connection.source_node_id,
        target_node_id=connection.target_node_id,
        source_handle=connection.source_handle,
        target_handle=connection.target_handle,
        config=connection.config
    )
    db.add(db_connection)
    db.commit()
    db.refresh(db_connection)
    return db_connection

@router.get("/{workflow_id}/connections", response_model=List[WorkflowConnectionResponse])
async def get_workflow_connections(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify workflow ownership
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    connections = db.query(WorkflowConnection).filter(WorkflowConnection.workflow_id == workflow_id).all()
    return connections

# Workflow Execution
@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: int,
    execution_data: WorkflowExecutionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify workflow ownership
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Create execution record
    db_execution = WorkflowExecution(
        workflow_id=workflow_id,
        user_id=current_user.id,
        input_data=execution_data.input_data,
        status="pending"
    )
    db.add(db_execution)
    db.commit()
    db.refresh(db_execution)

    # Start background execution
    background_tasks.add_task(execute_workflow_background, db_execution.id, db)

    return db_execution

@router.get("/{workflow_id}/executions", response_model=List[WorkflowExecutionResponse])
async def get_workflow_executions(
    workflow_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify workflow ownership
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.user_id == current_user.id
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    executions = db.query(WorkflowExecution).filter(
        WorkflowExecution.workflow_id == workflow_id
    ).order_by(WorkflowExecution.created_at.desc()).offset(skip).limit(limit).all()
    return executions

@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_workflow_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    execution = db.query(WorkflowExecution).join(Workflow).filter(
        WorkflowExecution.id == execution_id,
        Workflow.user_id == current_user.id
    ).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution

@router.get("/executions/{execution_id}/logs", response_model=List[WorkflowExecutionLogResponse])
async def get_execution_logs(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify execution ownership
    execution = db.query(WorkflowExecution).join(Workflow).filter(
        WorkflowExecution.id == execution_id,
        Workflow.user_id == current_user.id
    ).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    logs = db.query(WorkflowExecutionLog).filter(
        WorkflowExecutionLog.execution_id == execution_id
    ).order_by(WorkflowExecutionLog.timestamp).all()
    return logs

# Workflow Templates
@router.get("/templates", response_model=List[WorkflowTemplateResponse])
async def get_workflow_templates(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(WorkflowTemplate).filter(WorkflowTemplate.is_public == True)
    if category:
        query = query.filter(WorkflowTemplate.category == category)
    templates = query.offset(skip).limit(limit).all()
    return templates

@router.post("/templates", response_model=WorkflowTemplateResponse)
async def create_workflow_template(
    template_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_template = WorkflowTemplate(
        name=template_data["name"],
        description=template_data.get("description"),
        category=template_data.get("category"),
        tags=template_data.get("tags", []),
        is_public=template_data.get("is_public", False),
        created_by=current_user.id,
        data=template_data["data"],
        thumbnail_url=template_data.get("thumbnail_url")
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

# Background task for workflow execution
async def execute_workflow_background(execution_id: int, db: Session):
    execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
    if not execution:
        return

    try:
        # Initialize workflow engine
        engine = WorkflowEngine(db, execution_id)
        
        # Execute the workflow
        result = await engine.execute()
        
        # Result handling is done inside the engine,
        # which updates the execution record with status, progress, output, etc.
        logger.info(f"Workflow execution {execution_id} completed with status: {result.get('success')}")
        
    except Exception as e:
        logger.error(f"Workflow execution {execution_id} failed with error: {str(e)}", exc_info=True)
        execution.status = "failed"
        execution.error_message = str(e)
        execution.completed_at = datetime.utcnow()
        db.commit()