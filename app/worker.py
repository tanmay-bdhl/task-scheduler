import time
import logging
from app.repository import (
    SessionLocal,
    mark_task_completed,
    mark_task_failed,
)

logger = logging.getLogger(__name__)

def execute_task(task_id: str, duration_ms: int):
    """
    Simulates task execution.
    Runs inside a worker thread.
    """
    logger.info(f"Starting execution of task {task_id} (duration: {duration_ms}ms)")
    
    try:
        # Simulate work
        time.sleep(duration_ms / 1000)

        # Mark completed
        try:
            with SessionLocal() as session:
                mark_task_completed(session, task_id)
            logger.info(f"Task {task_id} completed successfully")
        except Exception as e:
            logger.error(
                f"Failed to mark task {task_id} as completed: {e}",
                exc_info=True,
                extra={"task_id": task_id}
            )
            raise

    except KeyboardInterrupt:
        logger.warning(f"Task {task_id} interrupted by keyboard")
        raise
    except Exception as e:
        logger.error(
            f"Task {task_id} failed during execution: {e}",
            exc_info=True,
            extra={"task_id": task_id, "duration_ms": duration_ms}
        )
        # Mark failed on any error
        try:
            with SessionLocal() as session:
                mark_task_failed(session, task_id)
            logger.info(f"Task {task_id} marked as FAILED")
        except Exception as db_error:
            logger.critical(
                f"Failed to mark task {task_id} as failed in database: {db_error}",
                exc_info=True,
                extra={"task_id": task_id}
            )
