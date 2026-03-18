"""Structlog configuration for the application.

Called once at startup from both the FastAPI entry point (main.py) and the
Celery worker entry point (celery_worker.py) so all log output is structured JSON.

Mandatory fields per observability-standards.md:
  timestamp, level, service, environment, trace_id, span_id

trace_id and span_id default to "-"; they can be overridden per-request via
structlog.contextvars.bind_contextvars() in future request middleware.
"""

import logging

import structlog
from structlog.contextvars import bind_contextvars

from app.core.config import settings


def configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            # add_logger_name is intentionally omitted — it reads Logger.name which
            # PrintLogger does not expose. Use structlog.contextvars for logger identity.
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.ExceptionRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    bind_contextvars(
        service=settings.app_name,
        environment="development" if settings.debug else "production",
        trace_id="-",
        span_id="-",
    )
