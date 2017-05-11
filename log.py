# -*- coding: utf-8 -*-
import logging
import logging.config

logger_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "normal": {"format": "%(asctime)s %(name)s %(levelname)s %(message)s"},
        "simple": {"format": "%(name)s %(levelname)s %(message)s"}
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "DEBUG"
        },
        "log_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "normal",
            "level": "DEBUG",
            "filename": "coroutine.log",
            "maxBytes": 10240000,
            "backupCount": 3
        }
    },
    "root": {
        "handlers": ["console", "log_file"],
        "level": "DEBUG"
    }
}

logging.config.dictConfig(logger_config)


def getLogger(name):
    return logging.getLogger(name)
