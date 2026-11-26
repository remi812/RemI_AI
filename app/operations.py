"""Process-local admission and health for the single-worker pilot."""
import os
import time
from collections import Counter
from threading import Lock
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
import psycopg
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.pilot_db import open_database

counts = Counter()
lock = Lock()


def readiness():
    state = {"database":False,"schema":False,"catalog":False}
    try:
        with open_database() as db:
            state["database"] = True
            state["schema"] = bool(db.execute("SELECT 1 FROM catalog_migrations WHERE version=20").fetchone())
            state["catalog"] = state["schema"] and bool(db.execute("SELECT 1 FROM release_catalog WHERE version=20").fetchone())
    except psycopg.Error:
        pass
    return state


@asynccontextmanager
async def lifespan(app):
    # Keep liveness available even when the schema is being prepared.
    app.state.catalog_ready = all((await run_in_threadpool(readiness)).values())
    yield


def resident_bytes():
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class Memory(ctypes.Structure):
            _fields_ = [("cb",wintypes.DWORD),("faults",wintypes.DWORD)] + [
                (name,ctypes.c_size_t) for name in ("peak","working","pp","p","np","n","page","peakpage")]
        data = Memory()
        data.cb = ctypes.sizeof(data)
        if ctypes.windll.psapi.GetProcessMemoryInfo(wintypes.HANDLE(-1),ctypes.byref(data),data.cb):
            return data.working
    elif os.path.isfile("/proc/self/statm"):
        with open("/proc/self/statm") as stat:
            return int(stat.read().split()[1])*os.sysconf("SC_PAGE_SIZE")
    return None


def install(app):
    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse({"detail":"Проверьте формат и длину введённых данных."},status_code=422)

    @app.exception_handler(psycopg.Error)
    async def unavailable(request, exc):
        return JSONResponse({"detail":"Сервис данных временно недоступен. Попробуйте ещё раз."},status_code=503)

    @app.get("/livez", include_in_schema=False)
    def live():
        return {"alive":True}

    @app.get("/readyz", include_in_schema=False)
    def ready():
        state = readiness()
        app.state.catalog_ready = all(state.values())
        return JSONResponse(state,status_code=200 if all(state.values()) else 503)

    @app.middleware("http")
    async def measure(request, next_handler):
        with lock:
            if counts["active"] >= int(os.getenv("REMI_MAX_REQUESTS","24")):
                counts["overload"] += 1
                return JSONResponse({"detail":"Сервис занят. Повторите попытку."},status_code=503)
            counts["active"] += 1
        start = time.monotonic()
        code = 500
        try:
            if request.url.path.startswith("/api/") and getattr(app.state,"catalog_ready",True) is False:
                app.state.catalog_ready = all((await run_in_threadpool(readiness)).values())
                if not app.state.catalog_ready:
                    code = 503
                    return JSONResponse({"detail":"Учебный каталог временно недоступен. Повторите загрузку."},status_code=code)
            response = await next_handler(request)
            code = response.status_code
            return response
        finally:
            with lock:
                counts["active"] -= 1
                counts["requests"] += 1
                counts["errors_5xx"] += int(code >= 500)
                counts["latency_ms_total"] += round(1000*(time.monotonic()-start))
