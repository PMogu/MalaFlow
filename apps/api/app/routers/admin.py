from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "DELETE"])
def admin_api_removed(path: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Admin has moved to the session-based /admin console.",
    )
