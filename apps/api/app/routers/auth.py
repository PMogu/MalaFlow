from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import current_user
from app.models import User
from app.schemas import LoginInput
from app.services import auth as auth_service
from app.services.formatters import user_out

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginInput, db: Session = Depends(get_db)) -> dict:
    return auth_service.login(db, payload.phone, payload.password)


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return {"user": user_out(user)}
