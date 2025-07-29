from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.models import UserCreate, UserLogin, Token, User
from app.auth.jwt_service import jwt_service
from datetime import timedelta
from app.auth.dependencies import get_current_active_user, TokenData

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Mock user database (replace with real database)
users_db = {
    "admin": {
        "id": "1",
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": jwt_service.get_password_hash("admin123"),
        "role": "admin",
        "is_active": True,
        "created_at": "2025-01-01T00:00:00"
    },
    "user": {
        "id": "2", 
        "username": "user",
        "email": "user@example.com",
        "hashed_password": jwt_service.get_password_hash("user123"),
        "role": "user",
        "is_active": True,
        "created_at": "2025-01-01T00:00:00"
    }
}

@router.post("/register", response_model=User)
async def register_user(user: UserCreate):
    """Register a new user"""
    if user.username in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    hashed_password = jwt_service.get_password_hash(user.password)
    user_data = {
        "id": str(len(users_db) + 1),
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed_password,
        "role": user.role,
        "is_active": True,
        "created_at": "2025-01-01T00:00:00"
    }
    
    users_db[user.username] = user_data
    
    return User(**{k: v for k, v in user_data.items() if k != "hashed_password"})

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token"""
    user_data = users_db.get(form_data.username)
    
    if not user_data or not jwt_service.verify_password(form_data.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=jwt_service.access_token_expire_minutes)
    access_token = jwt_service.create_access_token(
        data={
            "sub": user_data["username"],
            "user_id": user_data["id"],
            "role": user_data["role"]
        },
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        expires_in=jwt_service.access_token_expire_minutes * 60,
        user_id=user_data["id"]
    )

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: TokenData = Depends(get_current_active_user)):
    """Get current user information"""
    user_data = users_db.get(current_user.username)
    return User(**{k: v for k, v in user_data.items() if k != "hashed_password"}) 