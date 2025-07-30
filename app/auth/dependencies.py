from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.auth.jwt_service import jwt_service
from app.auth.models import TokenData
from app.config import settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenData:
    """Get current authenticated user from JWT token or master token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Check for Authorization header
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise credentials_exception

    # Accept both Bearer <token> and master token
    token = None
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]
    else:
        token = auth_header.strip()

    # Check for master token
    if token == settings.master_api_token:
        return TokenData(username="master", user_id="master", role="admin")

    # Otherwise, check JWT
    payload = jwt_service.verify_token(token)
    if payload is None:
        raise credentials_exception
    return TokenData(**payload)


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    if not current_user:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def require_admin(
    current_user: TokenData = Depends(get_current_active_user),
) -> TokenData:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user
