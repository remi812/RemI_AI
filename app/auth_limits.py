"""Single-worker admission control. Shared classroom IPs get a separate, larger allowance."""
import hashlib
import time
from collections import deque
from contextlib import contextmanager
from threading import BoundedSemaphore, Lock
from fastapi import HTTPException

_slots = BoundedSemaphore(3)
_lock = Lock()
_windows = {}


@contextmanager
def admission(ip, email):
    now = time.monotonic()
    keys = [(("ip",ip),240), (("mail",hashlib.sha256(email.encode()).digest()),16)]
    with _lock:
        for key, window in list(_windows.items()):
            while window and window[0] <= now-900:
                window.popleft()
            if not window:
                del _windows[key]
        if any(len(_windows.get(key,())) >= cap for key,cap in keys) or len(_windows)>8000:
            raise HTTPException(429,"Слишком много попыток. Попробуйте через 15 минут.",headers={"Retry-After":"900"})
        if not _slots.acquire(blocking=False):
            raise HTTPException(429,"Сервис занят. Попробуйте через несколько секунд.",headers={"Retry-After":"5"})
        for key,_ in keys:
            _windows.setdefault(key,deque()).append(now)
    try:
        yield
    finally:
        _slots.release()
