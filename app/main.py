from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.repository import engine, enable_wal
from app.models import metadata
from app.api import router
from app.repository import SessionLocal, reset_running_tasks
import threading
from app.scheduler import scheduler_loop
import logging
from app.config import setup_logging, MAX_CONCURRENT_TASKS

# Setup logging
logger = setup_logging()

app = FastAPI(title="Distributed Task Scheduler")

app.include_router(router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={"path": request.url.path, "method": request.method}
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred",
            "error_type": type(exc).__name__
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for request validation errors."""
    logger.warning(
        f"Validation error: {exc.errors()}",
        extra={"path": request.url.path, "method": request.method}
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )


@app.on_event("startup")
def on_startup():
    """Initialize database and start scheduler on application startup."""
    try:
        logger.info("Starting application...")
        
        # Enable WAL mode for SQLite
        enable_wal()
        logger.info("WAL mode enabled for SQLite")
        
        # Create database tables
        metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
        
        # Reset any tasks that were running before crash
        with SessionLocal() as session:
            reset_running_tasks(session)
        logger.info("Reset any tasks in RUNNING state from previous session")
        
        # Start scheduler thread
        scheduler_thread = threading.Thread(
            target=scheduler_loop,
            daemon=True,
            name="SchedulerThread"
        )
        scheduler_thread.start()
        logger.info(f"Scheduler thread started (max concurrent tasks: {MAX_CONCURRENT_TASKS})")
        logger.info("Server started successfully")
        
    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        raise


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
