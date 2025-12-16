Distributed Task Scheduler – Backend README

SERVER SPECIFICATIONS

Language: Python 3.10+
Framework: FastAPI
Database: SQLite (persistent, file-based)
ORM: SQLAlchemy
Concurrency Model: ThreadPoolExecutor
Max Concurrent Tasks: Configurable (default: 3)
Persistence Mode: SQLite with Write-Ahead Logging (WAL)
Execution Model: Background scheduler and worker pool
Task Execution: Simulated using sleep(duration_ms)

The database is the single source of truth for task state and execution guarantees.


API SPECIFICATIONS

1. Create Task
POST /tasks

Request Body:
{
  "id": "task-A",
  "type": "data_processing",
  "duration_ms": 5000,
  "dependencies": []
}

Response:
{
  "id": "task-A",
  "status": "QUEUED"
}

Errors:
- 409 Conflict: Task ID already exists
- 400 Bad Request: Missing dependency or dependency cycle detected


2. Get Task Status
GET /tasks/{id}

Response:
{
  "id": "task-A",
  "type": "data_processing",
  "duration_ms": 5000,
  "dependencies": [],
  "status": "COMPLETED"
}

Errors:
- 404 Not Found: Task does not exist


3. List Tasks
GET /tasks

Response:
[
  {
    "id": "task-A",
    "status": "COMPLETED"
  },
  {
    "id": "task-B",
    "status": "QUEUED"
  }
]


INSTRUCTIONS TO START THE SERVER

## Prerequisites

- Python 3.10 or higher
- pip
- macOS, Linux, or Windows

1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

2. Install dependencies
pip install -r requirements.txt

3. Start the server
uvicorn app.main:app --reload

Server URL by default:
http://127.0.0.1:8000

The scheduler and worker pool start automatically on application boot.


DESIGN CHOICES

Concurrency Model:
- Uses a fixed-size ThreadPoolExecutor to enforce concurrency limits
- Tasks are claimed using optimistic locking at the database level
- UPDATE statements with status conditions ensure only one worker can claim a task
- Prevents double execution under concurrent schedulers

Dependency Resolution:
- Task dependencies form a Directed Acyclic Graph (DAG)
- A task is eligible to run only when all dependencies are in COMPLETED state
- Cycle detection is performed at task creation using graph traversal
- Self-dependencies are explicitly rejected

Storage Strategy:
- SQLite is used to keep the system self-contained and dependency-free
- WAL mode enables safe concurrent reads and writes
- All task states are persisted; no in-memory state is required for correctness

Crash Recovery:
- On startup, tasks in RUNNING state are reset to QUEUED
- Scheduler resumes pending tasks automatically
- Guarantees no task is lost or permanently stuck due to crashes


SCALING TO 1 MILLION TASKS PER HOUR

To scale the system:
- Replace SQLite with PostgreSQL or a distributed SQL database
- Decouple scheduling and execution using a message queue
- Run workers as independent services with horizontal autoscaling
- Partition tasks by workflow, tenant, or task type
- Introduce batching, prioritization, and rate-limiting
- Use distributed locking or task leasing for multi-scheduler coordination

The current architecture allows these changes without altering the core task model.
