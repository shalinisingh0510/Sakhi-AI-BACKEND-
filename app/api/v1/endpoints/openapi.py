from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/openapi", tags=["openapi"])


@router.get(".json", include_in_schema=False)
def export_openapi(request: Request) -> JSONResponse:
    """Return the generated OpenAPI schema for API consumers."""
    return JSONResponse(
        content=request.app.openapi(),
        headers={
            "Content-Disposition": 'attachment; filename="sakhi-ai-openapi.json"',
        },
    )
