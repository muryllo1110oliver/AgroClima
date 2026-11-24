from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
import logging

_active = set()


class Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


class Task(QRunnable):
    def __init__(self, fn, done, failed):
        super().__init__()
        self.fn = fn
        self.signals = Signals()
        self.signals.done.connect(done)
        self.signals.failed.connect(failed)

    def run(self):
        try:
            self.signals.done.emit(self.fn())
        except Exception as e:
            logging.getLogger(__name__).error(
                "Tarefa assíncrona falhou: %s", type(e).__name__
            )
            self.signals.failed.emit(str(e))


def run_task(fn, done, failed):
    def success(result):
        try:
            done(result)
        finally:
            _active.discard(task)

    def failure(error):
        try:
            failed(error)
        finally:
            _active.discard(task)

    task = Task(fn, success, failure)
    _active.add(task)
    QThreadPool.globalInstance().start(task)
