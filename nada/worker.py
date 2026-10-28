"""Run blocking work (HTTP) off the UI thread and deliver results back on it."""

import traceback
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QObject, Signal, Slot

from .api import ApiError
from .auth import AuthError


class Async(QObject):
    _done = Signal(object, object, object)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="nada")
        self._done.connect(self._dispatch)

    def run(self, fn, on_ok=None, on_err=None):
        def job():
            try:
                result = fn()
            except Exception as e:  # delivered to the UI thread
                if not isinstance(e, (ApiError, AuthError)):
                    traceback.print_exc()
                self._done.emit(on_err or self._default_err, None, e)
            else:
                if on_ok:
                    self._done.emit(on_ok, result, None)
        self._pool.submit(job)

    def _default_err(self, e):
        self.error.emit(str(e))

    @Slot(object, object, object)
    def _dispatch(self, callback, result, err):
        callback(err if err is not None else result)

    def shutdown(self):
        self._pool.shutdown(wait=False, cancel_futures=True)
