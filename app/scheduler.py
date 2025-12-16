from concurrent.futures import ThreadPoolExecutor
from app.config import MAX_CONCURRENT_TASKS, SCHEDULER_POLL_INTERVAL_MS
import time
import logging
from app.repository import (
    SessionLocal,
    find_runnable_tasks,
    mark_task_running,
    get_task_by_id,
)
from app.worker import execute_task

logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(
    max_workers=MAX_CONCURRENT_TASKS
)

def scheduler_loop():
    """
    Continuously polls for runnable tasks and dispatches them.
    """
    logger.info(f"Scheduler loop started (max workers: {MAX_CONCURRENT_TASKS})")
    
    while True:
        try:
            with SessionLocal() as session:
                # Determine available worker slots
                queue_size = executor._work_queue.qsize()
                available_slots = MAX_CONCURRENT_TASKS - queue_size

                if available_slots <= 0:
                    logger.debug(f"No available worker slots (queue size: {queue_size})")
                    time.sleep(SCHEDULER_POLL_INTERVAL_MS / 1000)
                    continue

                # Find runnable tasks
                try:
                    runnable_tasks = find_runnable_tasks(
                        session,
                        limit=available_slots,
                    )
                except Exception as e:
                    logger.error(f"Error finding runnable tasks: {e}", exc_info=True)
                    time.sleep(SCHEDULER_POLL_INTERVAL_MS / 1000)
                    continue
                
                if runnable_tasks:
                    logger.debug(f"Found {len(runnable_tasks)} runnable task(s): {runnable_tasks}")

                for task_id in runnable_tasks:
                    try:
                        # Attempt to lock task
                        locked = mark_task_running(session, task_id)
                        if not locked:
                            logger.debug(f"Task {task_id} was already claimed by another worker")
                            continue

                        # Fetch task details
                        row = get_task_by_id(session, task_id)
                        if not row:
                            logger.warning(f"Task {task_id} not found after marking as running")
                            continue
                            
                        task = row._mapping

                        # Submit to worker pool
                        executor.submit(
                            execute_task,
                            task_id,
                            task["duration_ms"],
                        )
                        logger.info(f"Task {task_id} submitted to worker pool (duration: {task['duration_ms']}ms)")
                        
                    except Exception as e:
                        logger.error(
                            f"Error processing task {task_id}: {e}",
                            exc_info=True,
                            extra={"task_id": task_id}
                        )

        except Exception as e:
            logger.error(
                f"Error in scheduler loop: {e}",
                exc_info=True
            )

        time.sleep(SCHEDULER_POLL_INTERVAL_MS / 1000)

