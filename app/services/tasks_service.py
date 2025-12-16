import traceback
import logging
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException, status

from app.repository import SessionLocal
from app.schemas import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskResponse,
    TaskListResponse,
)
from app.models import TaskStatus
from app.repository import (
    get_task_by_id,
    create_task,
    list_tasks,
    load_dependency_graph,
)
from app.dag import has_cycle

logger = logging.getLogger(__name__)


def create_task_service(payload: TaskCreateRequest) -> TaskCreateResponse:
    """Service function to create a new task."""
    logger.info(f"Creating task: {payload.id} (type: {payload.type}, dependencies: {payload.dependencies})")
    
    with SessionLocal() as session:
        try:
            # Check if task already exists
            if get_task_by_id(session, payload.id):
                logger.warning(f"Task creation failed: task {payload.id} already exists")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Task with this ID already exists",
                )

            # Validate all dependencies exist
            for dep_id in payload.dependencies:
                if not get_task_by_id(session, dep_id):
                    logger.warning(f"Task creation failed: dependency '{dep_id}' does not exist")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Dependency task '{dep_id}' does not exist",
                    )

            # Check for cycles in dependency graph
            graph = load_dependency_graph(session)
            graph[payload.id] = payload.dependencies

            if has_cycle(graph):
                logger.warning(f"Task creation failed: dependency cycle detected for task {payload.id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Task dependency cycle detected",
                )

            # Create the task
            create_task(
                session=session,
                task_id=payload.id,
                task_type=payload.type,
                duration_ms=payload.duration_ms,
                dependencies=payload.dependencies,
            )

            logger.info(f"Task {payload.id} created successfully")
            return TaskCreateResponse(
                id=payload.id,
                status=TaskStatus.QUEUED,
            )

        except IntegrityError as e:
            logger.error(f"Integrity error creating task {payload.id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Task or dependency already exists",
            )

        except HTTPException:
            raise

        except SQLAlchemyError as e:
            logger.error(f"Database error creating task {payload.id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while creating task",
            )

        except Exception as e:
            logger.error(f"Unexpected error creating task {payload.id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while creating task",
            )


def get_task_service(task_id: str) -> TaskResponse | None:
    """Service function to get a task by ID."""
    logger.debug(f"Fetching task: {task_id}")
    
    try:
        with SessionLocal() as session:
            row = get_task_by_id(session, task_id)
            if not row:
                logger.debug(f"Task {task_id} not found")
                return None

            task = row._mapping

            return TaskResponse(
                id=task["id"],
                type=task["type"],
                duration_ms=task["duration_ms"],
                status=task["status"],
            )
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while fetching task",
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching task",
        )


def list_tasks_service() -> TaskListResponse:
    """Service function to list all tasks."""
    logger.debug("Fetching all tasks")
    
    try:
        with SessionLocal() as session:
            rows = list_tasks(session)

            tasks = []
            for row in rows:
                task = row._mapping
                tasks.append(
                    TaskResponse(
                        id=task["id"],
                        type=task["type"],
                        duration_ms=task["duration_ms"],
                        status=task["status"],
                    )
                )

            logger.debug(f"Found {len(tasks)} task(s)")
            return TaskListResponse(tasks=tasks)
    except SQLAlchemyError as e:
        logger.error(f"Database error listing tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while listing tasks",
        )
    except Exception as e:
        logger.error(f"Unexpected error listing tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing tasks",
        )
