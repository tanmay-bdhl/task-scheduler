from fastapi import APIRouter, HTTPException, status
import logging
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.schemas import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskResponse,
    TaskListResponse,
)

from app.services.tasks_service import (
    create_task_service,
    get_task_service,
    list_tasks_service
)
from app.repository import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/db-health")
def db_health():
    """Database health check endpoint."""
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        logger.debug("Database health check passed")
        return {"db": "ok"}
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )
    except Exception as e:
        logger.error(f"Unexpected error in database health check: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/tasks", response_model=TaskCreateResponse, status_code=201)
def create_task_api(payload: TaskCreateRequest):
    """API endpoint to create a new task."""
    logger.info(f"POST /tasks - Creating task: {payload.id}")
    try:
        return create_task_service(payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_task_api: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str):
    """API endpoint to get a task by ID."""
    logger.debug(f"GET /tasks/{task_id}")
    try:
        task = get_task_service(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/tasks", response_model=TaskListResponse)
def get_all_tasks():
    """API endpoint to list all tasks."""
    logger.debug("GET /tasks - Listing all tasks")
    try:
        return list_tasks_service()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_all_tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )