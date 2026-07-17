from fastapi import APIRouter, Request

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
def health_check(request: Request) -> dict:
    settings = get_settings()

    # Probe database connectivity
    db_status = "ok"
    db_error: str | None = None
    try:
        # Every store shares the same SQLite file; use auth store as the probe
        store = getattr(request.app.state, "auth_store", None)
        if store is not None and hasattr(store, "_connection"):
            store._connection.execute("SELECT 1").fetchone()
        else:
            db_status = "unknown"
    except Exception as exc:
        db_status = "error"
        db_error = str(exc)

    payload: dict = {
        "status": "ok" if db_status in ("ok", "unknown") else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": db_status,
    }
    if db_error:
        payload["database_error"] = db_error
    return payload

