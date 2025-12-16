from sqlalchemy import (
    create_engine,
    text,
    select,
    update,
    insert,
    exists
)
from sqlalchemy.orm import sessionmaker, aliased
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging

from app.config import DATABASE_URL
from app.models import tasks, task_dependencies, TaskStatus

logger = logging.getLogger(__name__)


def enable_wal():
    """Enable Write-Ahead Logging for SQLite."""
    try:
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            conn.commit()
            logger.info("WAL mode enabled successfully")
    except Exception as e:
        logger.error(f"Failed to enable WAL mode: {e}", exc_info=True)
        raise

# SQLite-specific settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for threading
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)




def create_task(
    session,
    task_id: str,
    task_type: str,
    duration_ms: int,
    dependencies: list[str],
):
    """
    Insert a task and its dependencies atomically.
    """
    try:
        session.execute(
            insert(tasks).values(
                id=task_id,
                type=task_type,
                duration_ms=duration_ms,
                status=TaskStatus.QUEUED,
            )
        )

        for dep_id in dependencies:
            session.execute(
                insert(task_dependencies).values(
                    task_id=task_id,
                    depends_on_task_id=dep_id,
                )
            )

        session.commit()
        logger.debug(f"Task {task_id} created successfully with {len(dependencies)} dependencies")
    except IntegrityError as e:
        session.rollback()
        logger.warning(f"Integrity error creating task {task_id}: {e}")
        raise
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error creating task {task_id}: {e}", exc_info=True)
        raise


def get_task_by_id(session, task_id: str):
    stmt = select(tasks).where(tasks.c.id == task_id)
    result = session.execute(stmt).first()
    return result


def list_tasks(session):
    stmt = select(tasks)
    result = session.execute(stmt).all()
    return result


def find_runnable_tasks(session, limit: int):
    """Find tasks that are ready to run (QUEUED with all dependencies completed)."""
    try:
        dep_task = aliased(tasks)

        subquery = (
            select(1)
            .select_from(task_dependencies)
            .join(
                dep_task,
                task_dependencies.c.depends_on_task_id == dep_task.c.id,
            )
            .where(task_dependencies.c.task_id == tasks.c.id)
            .where(dep_task.c.status != TaskStatus.COMPLETED)
        )

        stmt = (
            select(tasks.c.id)
            .where(
                tasks.c.status == TaskStatus.QUEUED,
                ~exists(subquery),
            )
            .limit(limit)
        )

        return session.execute(stmt).scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Database error finding runnable tasks: {e}", exc_info=True)
        raise


def mark_task_running(session, task_id: str) -> bool:
    """
    Attempt to mark task as RUNNING.
    Returns True if successful, False if task was already taken.
    """
    try:
        stmt = (
            update(tasks)
            .where(
                tasks.c.id == task_id,
                tasks.c.status == TaskStatus.QUEUED,
            )
            .values(status=TaskStatus.RUNNING)
        )

        result = session.execute(stmt)
        if result.rowcount == 0:
            session.rollback()
            return False

        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error marking task {task_id} as running: {e}", exc_info=True)
        raise


def mark_task_completed(session, task_id: str):
    """Mark a task as completed."""
    try:
        result = session.execute(
            update(tasks)
            .where(tasks.c.id == task_id)
            .values(status=TaskStatus.COMPLETED)
        )
        session.commit()
        
        if result.rowcount == 0:
            logger.warning(f"Task {task_id} not found when marking as completed")
        else:
            logger.debug(f"Task {task_id} marked as COMPLETED")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error marking task {task_id} as completed: {e}", exc_info=True)
        raise


def mark_task_failed(session, task_id: str):
    """Mark a task as failed."""
    try:
        result = session.execute(
            update(tasks)
            .where(tasks.c.id == task_id)
            .values(status=TaskStatus.FAILED)
        )
        session.commit()
        
        if result.rowcount == 0:
            logger.warning(f"Task {task_id} not found when marking as failed")
        else:
            logger.debug(f"Task {task_id} marked as FAILED")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error marking task {task_id} as failed: {e}", exc_info=True)
        raise


def reset_running_tasks(session):
    """Reset tasks in RUNNING state to QUEUED (for crash recovery)."""
    try:
        result = session.execute(
            update(tasks)
            .where(tasks.c.status == TaskStatus.RUNNING)
            .values(status=TaskStatus.QUEUED)
        )
        session.commit()
        
        count = result.rowcount
        if count > 0:
            logger.info(f"Reset {count} task(s) from RUNNING to QUEUED state")
        else:
            logger.debug("No tasks in RUNNING state to reset")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error resetting running tasks: {e}", exc_info=True)
        raise

def load_dependency_graph(session) -> dict[str, list[str]]:
    """
    Returns adjacency list: task -> [dependencies]
    """
    graph: dict[str, list[str]] = {}

    rows = session.execute(
        select(
            task_dependencies.c.task_id,
            task_dependencies.c.depends_on_task_id,
        )
    ).all()

    for task_id, dep_id in rows:
        graph.setdefault(task_id, []).append(dep_id)

    return graph
