"""Stdout + persistent file logging for production debugging."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_bot_logging() -> logging.Logger:
    log_level = os.getenv('BOT_LOG_LEVEL', 'INFO').upper()
    level = getattr(logging, log_level, logging.INFO)

    log_path = os.getenv('BOT_LOG_PATH', '/app/data/bot.log')
    fmt = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    root.addHandler(stream)

    file_handler: Optional[RotatingFileHandler] = None
    log_dir = os.path.dirname(log_path)
    if log_dir:
        try:
            os.makedirs(log_dir, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8',
            )
            file_handler.setFormatter(fmt)
            root.addHandler(file_handler)
        except OSError as exc:
            stream.handle(
                logging.LogRecord(
                    name='bot_logging',
                    level=logging.WARNING,
                    pathname=__file__,
                    lineno=0,
                    msg=f'Could not open log file {log_path}: {exc}',
                    args=(),
                    exc_info=None,
                )
            )

    logging.captureWarnings(True)
    return logging.getLogger('swingfox.telegram')
