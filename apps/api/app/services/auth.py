from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.security import create_access_token, verify_password
from app.services.formatters import user_out


def login(db: Session, phone: str, password: str) -> dict:
    user = db.scalar(select(User).where(User.phone == phone.strip()))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_CREDENTIALS")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ACCOUNT_INACTIVE")
    if user.role != "restaurant" or not user.restaurant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="RESTAURANT_LOGIN_ONLY")
    token = create_access_token(user.id, {"role": "restaurant"})
    return {"access_token": token, "token_type": "bearer", "user": user_out(user)}
