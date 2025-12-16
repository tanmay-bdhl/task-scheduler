import os
import logging
import sys

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./tasks.db"
)

MAX_CONCURRENT_TASKS = int(
    os.getenv("MAX_CONCURRENT_TASKS", 3)
)

SCHEDULER_POLL_INTERVAL_MS = int(
    os.getenv("SCHEDULER_POLL_INTERVAL_MS", 500)
)

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

def setup_logging():
    """Configure application-wide logging."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)
