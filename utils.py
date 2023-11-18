from threading import Lock
from typing import Callable


class CancellationToken:
    def __init__(self) -> None:
        self._callbacks: list[Callable[[], None]] = []
        self._is_canceled = False
        self._is_completed = False
        self._lock = Lock()

    def on_cancel(self, callback: Callable[[], None]) -> None:
        if self.is_active:
            with self._lock:
                if self.is_active:
                    self._callbacks.append(callback)
                    return

        callback()

    def remove_callback(self, callback: Callable[[], None]) -> None:
        self._callbacks.remove(callback)

    def cancel(self) -> None:
        with self._lock:
            if not self.is_active:
                return

            self._is_canceled = True

        for f in [x for x in self._callbacks]:
            f()

    def complete(self) -> None:
        with self._lock:
            if not self.is_active:
                return

            self._is_completed = True

    @property
    def is_cancelled(self) -> bool:
        return self._is_canceled

    @property
    def is_completed(self) -> bool:
        return self._is_completed

    @property
    def is_active(self) -> bool:
        return not self._is_canceled and not self._is_completed


class MaxSizeList(object):
    def __init__(self, size: int = 0):
        self._size: int = size
        self._data: list = []
        self._iteration_index: int

    def add(self, st):
        if 0 < self._size == len(self._data):
            self._data.pop(0)
        self._data.append(st)

    @property
    def data(self):
        return self._data
