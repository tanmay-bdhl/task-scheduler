from sqlalchemy import (
    Table,
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    MetaData,
    func,
)

metadata = MetaData()

class TaskStatus:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


tasks = Table(
    "tasks",
    metadata,
    Column("id", String, primary_key=True),
    Column("type", String, nullable=False),
    Column("duration_ms", Integer, nullable=False),
    Column("status", String, nullable=False),
    Column("created_at", DateTime, server_default=func.now()),
    Column(
        "updated_at",
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    ),
)

task_dependencies = Table(
    "task_dependencies",
    metadata,
    Column(
        "task_id",
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "depends_on_task_id",
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
