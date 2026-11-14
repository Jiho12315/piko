"""로깅 설정. 파일(%APPDATA%/Piko/logs)과 콘솔에 남긴다."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

LOG_FILE_NAME = "piko.log"
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 3
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_ENCODING = "utf-8"

logger = logging.getLogger(__name__)


def setup_logging(log_dir: Path, level: int = logging.INFO) -> None:
    """루트 로거에 파일/콘솔 핸들러를 붙이고 처리되지 않은 예외를 로그로 남기게 한다."""
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(LOG_FORMAT)
    file_handler = RotatingFileHandler(
        log_dir / LOG_FILE_NAME,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding=LOG_ENCODING,
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # 콘솔 없는 exe(pythonw)에서는 sys.stderr가 None이다.
    if sys.stderr is not None:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    sys.excepthook = _log_uncaught_exception


def _log_uncaught_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
) -> None:
    """처리되지 않은 예외를 로그에 남긴다."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.critical("처리되지 않은 예외", exc_info=(exc_type, exc_value, exc_tb))
