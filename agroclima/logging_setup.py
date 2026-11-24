"""Logs locais com rotação; não registra payloads seriais ou respostas HTTP."""

import logging
from logging.handlers import RotatingFileHandler
import sys
import threading


def configure_logging(paths):
    paths.logs.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("agroclima")
    for handler in list(logger.handlers):
        if getattr(handler, "_agroclima", False):
            logger.removeHandler(handler)
            handler.close()
    handler = RotatingFileHandler(
        paths.logs / "agroclima.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler._agroclima = True
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def install_exception_hooks():
    old_sys, old_thread = sys.excepthook, threading.excepthook

    def unexpected(kind, value, traceback):
        logging.getLogger("agroclima").error(
            "Exceção inesperada", exc_info=(kind, value, traceback)
        )
        old_sys(kind, value, traceback)

    def thread_error(args):
        logging.getLogger("agroclima").error(
            "Exceção inesperada em thread",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        old_thread(args)

    sys.excepthook, threading.excepthook = unexpected, thread_error

    def restore():
        sys.excepthook, threading.excepthook = old_sys, old_thread

    return restore
