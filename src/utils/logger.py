import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import os

class JSONFormatter(logging.Formatter):
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if self.include_extra:
            extra_fields = {
                key: value
                for key, value in record.__dict__.items()
                if key not in [
                    "name", "msg", "args", "created", "filename", "funcName",
                    "levelname", "levelno", "lineno", "module", "msecs",
                    "message", "pathname", "process", "processName",
                    "relativeCreated", "thread", "threadName", "exc_info",
                    "exc_text", "stack_info"
                ]
            }
            if extra_fields:
                log_data["extra"] = extra_fields

        environment = os.getenv("ENVIRONMENT")
        if environment:
            log_data["environment"] = environment

        request_id = os.getenv("AWS_REQUEST_ID")
        if request_id:
            log_data["request_id"] = request_id

        return json.dumps(log_data, default=str)

class CloudWatchFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": int(record.created * 1000),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)

def get_logger(
        name: str,
        level: Optional[str] = None,
        format_type: str = "json"
) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    logger.setLevel(getattr(logging, log_level.upper()))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)

    if format_type == "json":
        formatter = JSONFormatter()
    elif format_type == "cloudwatch":
        formatter = CloudWatchFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFomatter(formatter)
    logger.addHandler(handler)

    logger.propagate = False
    return logger

def log_with_context(
        logger: logging.Logger,
        level: str,
        message: str,
    **context: Any
) -> None:
    log_method = getattr(logger, level.lower())
    log_method(message, extra=context)

def log_incident(
        logger: logging.Logger,
        incident_id: str,
        failure_type: str,
    service: str,
    severity: str,
    **kwargs: Any
) -> None:
    log_with_context(
        logger,
        "info",
        f"Incident {incident_id} detected",
        incident_id=incident_id,
        failure_type=failure_type,
        service=service,
        severity=severity,
        **kwargs
    )

def log_remediation(
        logger: logging.Logger,
        incident_id: str,
        action: str,
    action: str,
    status: str,
    confidence: float,
    **kwargs: Any
) -> None:
    log_with_context(
        logger, 
        "info",
        f"Remediation action {action} for incident {incident_id}: {status}",
        incident_id=incident_id,
        action=action,
        status=status,
        confidence=confidence, 
        **kwargs
    )

def log_error_with_context(
        logger: logging.Logger,
        error: Exception,
        context: Dict[str, Any]
) -> None:
    logger.error(
        f"Error occurred: {str(error)}",
        exc_info=True,
        extra={"error_context": context}
    )

def log_performance_metric(
    logger: logging.Logger,
        operation: str,
        duration_ms: float,
    success: bool,
    **kwargs: Any
) -> None:
    log_with_context(
        logger,
        "info",
        f"Performance metric for {operation}",
        operation=operation,
        duration_ms=duration_ms,
        success=success,
        metric_type="performance",
        **kwargs
    )

def log_api_call(
        logger: logging.Logger,
        service: str,
        method: str,
        endpoint: str,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        **kwargs: Any
) -> None:
    log_with_context(
        logger,
        "debug",
        f"API call to {service}.{method}",
        service=service,
        method=method, 
        endpoint=endpoint,
        status_code=status_code, 
        duration_ms=duration_ms,
        **kwargs
    )

class ContextLogger:
    def __init__(self, logger: logging.Logger, **default_context: Any):
        self.logger = logger
        self.default_context = default_context

    def _log(self, level: str, message: str, **context: Any) -> None:
        merged_context = {**self.default_context, **context}
        log_with_context(self.logger, level, message, **merged_context)

    def debug(self, message: str, **context: Any) -> None:
        self._log("debug", message, **context)

    def info(self, message: str, **context: Any) -> None:
        self._log("info", message, **context)

    def warning(self, message: str, **context: Any) -> None:
        self._log("warning", message, **context)

    def error(self, message: str, **context: Any) -> None:
        self._log("error", message, **context)

    def critical(self, message: str, **context: Any) -> None:
        self._log("critical", message, **context)

def create_context_logger(name: str, **default_context: Any) -> ContextLogger:
    logger = get_logger(name)
    return ContextLogger(logger, **default_context)

def setup_lamdba_logging() -> logging.Logger:
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFomatter(JSONFormatter())

    log_level = os.getenv("LOG_LEVEL", "INFO")
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(handler)

    return root_logger

class LoggerAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: Any) -> tuple:
        if "extra" in kwargs:
            kwargs["extra"].update(self.extra)
        else:
            kwargs["extra"] = self.extra
        return msg, kwargs

def get_adapter(logger: logging.Logger, **context: Any) LoggerAdapter:
    return LoggerAdapter(logger, context)

def mask_sensitive_data(data: Dict[str, Any], sensitive_keys: list = None) -> Dict[str, Any]:
    if sensitive_keys is None:
        sensitive_keys = ["password", "token", "secret", "key", "credential", "authorization"]

    masked = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            masked_data[key] = "***REDACTED***"
        elif isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value, sensitive_keys)
        elif isinstance(value, list):
            masked_data[key] = [
                mask_sensitive_data(item, sensitive_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked_data[key] = value
    return masked_data

def safe_log_dict(logger: logging.Logger, level: str, message: str, data: Dict[str, Any]) -> None:
    masked_data = mask_sensitive_data(data)
    log_with_context(logger, level, message, **masked_data)
