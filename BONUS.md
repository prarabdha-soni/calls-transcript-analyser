# Bonus Features Implementation Guide

This guide explains how to implement the optional bonus features: JWT authentication, WebSocket real-time sentiment streaming, and background job processing.

## Table of Contents

1. [JWT Authentication Middleware](#jwt-authentication-middleware)
2. [WebSocket Real-Time Sentiment Streaming](#websocket-real-time-sentiment-streaming)
3. [Background Job Processing](#background-job-processing)
4. [Integration Examples](#integration-examples)

## JWT Authentication Middleware

### 1. **Authentication Models**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User(BaseModel):
    id: str
    username: str
    email: str
    role: str = "user"
    is_active: bool = True
    created_at: datetime

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "user"

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None
```

### 2. **JWT Authentication Service**

```python
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from app.config import settings

class JWTAuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            user_id: str = payload.get("user_id")
            role: str = payload.get("role")
            
            if username is None:
                return None
            
            return {
                "username": username,
                "user_id": user_id,
                "role": role
            }
        except jwt.PyJWTError:
            return None

# Global instance
jwt_service = JWTAuthService()
```

### 3. **Authentication Dependencies**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.auth.jwt_service import jwt_service
from app.auth.models import TokenData

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = jwt_service.verify_token(token)
    
    if payload is None:
        raise credentials_exception
    
    return TokenData(**payload)

async def get_current_active_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Get current active user"""
    if not current_user:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def require_admin(current_user: TokenData = Depends(get_current_active_user)) -> TokenData:
    """Require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
```

### 4. **Authentication Endpoints**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.models import UserCreate, UserLogin, Token, User
from app.auth.jwt_service import jwt_service
from app.auth.dependencies import get_current_active_user
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Mock user database (replace with real database)
users_db = {
    "admin": {
        "id": "1",
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": jwt_service.get_password_hash("admin123"),
        "role": "admin",
        "is_active": True
    },
    "user": {
        "id": "2", 
        "username": "user",
        "email": "user@example.com",
        "hashed_password": jwt_service.get_password_hash("user123"),
        "role": "user",
        "is_active": True
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
        "is_active": True
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
```

### 5. **Protected API Endpoints**

```python
from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_active_user, require_admin
from app.auth.models import TokenData
from app.schemas import CallListResponse
from app.crud import CRUD
from app.database import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1", tags=["Protected API"])

@router.get("/calls", response_model=CallListResponse)
async def get_calls_protected(
    current_user: TokenData = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
    limit: int = 50,
    offset: int = 0
):
    """Get calls (requires authentication)"""
    crud = CRUD()
    calls = await crud.get_calls(db, limit=limit, offset=offset)
    return calls

@router.get("/admin/analytics")
async def get_admin_analytics(
    current_user: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Get admin analytics (requires admin role)"""
    # Admin-only analytics
    return {
        "message": "Admin analytics",
        "user": current_user.username,
        "role": current_user.role
    }
```

## WebSocket Real-Time Sentiment Streaming

### 1. **WebSocket Manager**

```python
import asyncio
import json
import random
from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.sentiment_simulators: Dict[str, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, call_id: str):
        """Connect a WebSocket client to a call's sentiment stream"""
        await websocket.accept()
        
        if call_id not in self.active_connections:
            self.active_connections[call_id] = set()
        
        self.active_connections[call_id].add(websocket)
        
        # Start sentiment simulation if not already running
        if call_id not in self.sentiment_simulators:
            self.sentiment_simulators[call_id] = asyncio.create_task(
                self.simulate_sentiment(call_id)
            )
        
        print(f"Client connected to call {call_id}")
    
    def disconnect(self, websocket: WebSocket, call_id: str):
        """Disconnect a WebSocket client"""
        if call_id in self.active_connections:
            self.active_connections[call_id].discard(websocket)
            
            # If no more connections, stop simulation
            if not self.active_connections[call_id]:
                if call_id in self.sentiment_simulators:
                    self.sentiment_simulators[call_id].cancel()
                    del self.sentiment_simulators[call_id]
                del self.active_connections[call_id]
        
        print(f"Client disconnected from call {call_id}")
    
    async def send_sentiment_update(self, call_id: str, sentiment_data: dict):
        """Send sentiment update to all connected clients for a call"""
        if call_id in self.active_connections:
            message = json.dumps({
                "type": "sentiment_update",
                "call_id": call_id,
                "timestamp": datetime.now().isoformat(),
                **sentiment_data
            })
            
            # Send to all connected clients
            disconnected = set()
            for connection in self.active_connections[call_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    print(f"Error sending to client: {e}")
                    disconnected.add(connection)
            
            # Remove disconnected clients
            for connection in disconnected:
                self.active_connections[call_id].discard(connection)
    
    async def simulate_sentiment(self, call_id: str):
        """Simulate real-time sentiment updates for a call"""
        base_sentiment = random.uniform(-0.5, 0.5)
        sentiment_trend = random.choice([-0.1, 0.1])
        
        while True:
            try:
                # Simulate sentiment changes
                base_sentiment += sentiment_trend + random.uniform(-0.05, 0.05)
                base_sentiment = max(-1.0, min(1.0, base_sentiment))
                
                # Occasionally change trend
                if random.random() < 0.1:
                    sentiment_trend = random.choice([-0.1, 0.1])
                
                sentiment_data = {
                    "sentiment_score": round(base_sentiment, 3),
                    "confidence": random.uniform(0.7, 0.95),
                    "trend": "improving" if sentiment_trend > 0 else "declining",
                    "keywords": self._generate_keywords(base_sentiment)
                }
                
                await self.send_sentiment_update(call_id, sentiment_data)
                await asyncio.sleep(2)  # Update every 2 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in sentiment simulation: {e}")
                break
    
    def _generate_keywords(self, sentiment: float) -> list:
        """Generate keywords based on sentiment"""
        if sentiment > 0.5:
            return ["positive", "satisfied", "happy", "good"]
        elif sentiment > 0:
            return ["neutral", "okay", "fine"]
        elif sentiment > -0.5:
            return ["concerned", "unsure", "neutral"]
        else:
            return ["negative", "frustrated", "unhappy", "bad"]

# Global WebSocket manager
websocket_manager = WebSocketManager()
```

### 2. **WebSocket Endpoints**

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.websocket.manager import websocket_manager
from app.auth.dependencies import get_current_user_ws
from app.auth.models import TokenData
import json

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws/sentiment/{call_id}")
async def websocket_sentiment_endpoint(
    websocket: WebSocket,
    call_id: str,
    current_user: TokenData = Depends(get_current_user_ws)
):
    """WebSocket endpoint for real-time sentiment streaming"""
    await websocket_manager.connect(websocket, call_id)
    
    try:
        # Send initial connection message
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "call_id": call_id,
            "user": current_user.username,
            "message": "Connected to sentiment stream"
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (ping/pong, commands, etc.)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle client messages
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))
                
            except WebSocketDisconnect:
                websocket_manager.disconnect(websocket, call_id)
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break
                
    except Exception as e:
        print(f"WebSocket connection error: {e}")
        websocket_manager.disconnect(websocket, call_id)

@router.websocket("/ws/admin/sentiment/{call_id}")
async def websocket_admin_sentiment_endpoint(
    websocket: WebSocket,
    call_id: str,
    current_user: TokenData = Depends(get_current_user_ws)
):
    """Admin WebSocket endpoint with additional controls"""
    # Check if user is admin
    if current_user.role != "admin":
        await websocket.close(code=4003, reason="Admin access required")
        return
    
    await websocket_manager.connect(websocket, call_id)
    
    try:
        await websocket.send_text(json.dumps({
            "type": "admin_connection_established",
            "call_id": call_id,
            "user": current_user.username,
            "role": current_user.role,
            "message": "Admin connected to sentiment stream"
        }))
        
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle admin-specific commands
                if message.get("type") == "control_sentiment":
                    # Admin can control sentiment simulation
                    await websocket.send_text(json.dumps({
                        "type": "sentiment_control",
                        "message": "Sentiment control activated"
                    }))
                
            except WebSocketDisconnect:
                websocket_manager.disconnect(websocket, call_id)
                break
                
    except Exception as e:
        print(f"Admin WebSocket error: {e}")
        websocket_manager.disconnect(websocket, call_id)
```

### 3. **WebSocket Authentication**

```python
from fastapi import WebSocket, HTTPException
from app.auth.jwt_service import jwt_service
from app.auth.models import TokenData
import json

async def get_current_user_ws(websocket: WebSocket) -> TokenData:
    """Authenticate WebSocket connection"""
    try:
        # Get token from query parameters or headers
        token = websocket.query_params.get("token")
        if not token:
            # Try to get from headers
            auth_header = websocket.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Verify token
        payload = jwt_service.verify_token(token)
        if not payload:
            await websocket.close(code=4002, reason="Invalid token")
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return TokenData(**payload)
        
    except Exception as e:
        await websocket.close(code=4001, reason="Authentication failed")
        raise HTTPException(status_code=401, detail="Authentication failed")
```

## Background Job Processing

### 1. **Celery Configuration**

```python
from celery import Celery
from app.config import settings
import os

# Celery configuration
celery_app = Celery(
    "sales_analytics",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.background.tasks"]
)

# Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Optional: Configure periodic tasks
celery_app.conf.beat_schedule = {
    "nightly-analytics-recalculation": {
        "task": "app.background.tasks.recalculate_analytics",
        "schedule": 86400.0,  # 24 hours
    },
    "cleanup-old-data": {
        "task": "app.background.tasks.cleanup_old_data",
        "schedule": 604800.0,  # 7 days
    },
}
```

### 2. **Background Tasks**

```python
from celery import current_task
from app.background.celery_app import celery_app
from app.database import SessionLocal
from app.crud import CRUD
from app.models import Call
from sqlalchemy import text
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def recalculate_analytics(self):
    """Recalculate all analytics data nightly"""
    try:
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Starting analytics recalculation"}
        )
        
        db = SessionLocal()
        crud = CRUD()
        
        # Step 1: Recalculate agent analytics
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 20, "total": 100, "status": "Recalculating agent analytics"}
        )
        
        agent_analytics = crud.calculate_agent_analytics(db)
        
        # Step 2: Update materialized views
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 50, "total": 100, "status": "Updating materialized views"}
        )
        
        # Refresh materialized views
        db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_agent_analytics"))
        db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_stats"))
        db.commit()
        
        # Step 3: Generate reports
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 80, "total": 100, "status": "Generating reports"}
        )
        
        reports = generate_analytics_reports(db)
        
        # Step 4: Cleanup
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 95, "total": 100, "status": "Finalizing"}
        )
        
        db.close()
        
        return {
            "status": "SUCCESS",
            "message": "Analytics recalculation completed",
            "agent_count": len(agent_analytics),
            "reports_generated": len(reports)
        }
        
    except Exception as e:
        logger.error(f"Analytics recalculation failed: {e}")
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise

@celery_app.task(bind=True)
def process_bulk_calls(self, calls_data: list):
    """Process bulk call ingestion in background"""
    try:
        total_calls = len(calls_data)
        processed = 0
        
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": total_calls, "status": "Starting bulk processing"}
        )
        
        db = SessionLocal()
        crud = CRUD()
        
        # Process calls in batches
        batch_size = 50
        for i in range(0, total_calls, batch_size):
            batch = calls_data[i:i + batch_size]
            
            # Process batch
            await crud.bulk_create_calls(db, batch)
            
            processed += len(batch)
            progress = (processed / total_calls) * 100
            
            current_task.update_state(
                state="PROGRESS",
                meta={
                    "current": processed,
                    "total": total_calls,
                    "status": f"Processed {processed}/{total_calls} calls"
                }
            )
        
        db.close()
        
        return {
            "status": "SUCCESS",
            "message": f"Bulk processing completed",
            "processed_calls": processed
        }
        
    except Exception as e:
        logger.error(f"Bulk processing failed: {e}")
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise

@celery_app.task(bind=True)
def cleanup_old_data(self):
    """Clean up old data periodically"""
    try:
        current_task.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Starting cleanup"}
        )
        
        db = SessionLocal()
        
        # Delete calls older than 1 year
        cutoff_date = datetime.now() - timedelta(days=365)
        
        result = db.execute(
            text("DELETE FROM calls WHERE start_time < :cutoff_date"),
            {"cutoff_date": cutoff_date}
        )
        
        deleted_count = result.rowcount
        db.commit()
        db.close()
        
        return {
            "status": "SUCCESS",
            "message": f"Cleanup completed",
            "deleted_calls": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise

@celery_app.task(bind=True)
def generate_analytics_reports(self, db):
    """Generate analytics reports"""
    try:
        # Generate various reports
        reports = []
        
        # Daily summary report
        daily_report = db.execute(text("""
            SELECT 
                DATE(start_time) as date,
                COUNT(*) as total_calls,
                AVG(duration_seconds) as avg_duration,
                AVG(customer_sentiment_score) as avg_sentiment
            FROM calls 
            WHERE start_time >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(start_time)
            ORDER BY date DESC
        """)).fetchall()
        
        reports.append({
            "type": "daily_summary",
            "data": [dict(row) for row in daily_report]
        })
        
        # Agent performance report
        agent_report = db.execute(text("""
            SELECT 
                agent_id,
                COUNT(*) as total_calls,
                AVG(customer_sentiment_score) as avg_sentiment,
                AVG(agent_talk_ratio) as avg_talk_ratio
            FROM calls 
            WHERE start_time >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY agent_id
            ORDER BY avg_sentiment DESC
        """)).fetchall()
        
        reports.append({
            "type": "agent_performance",
            "data": [dict(row) for row in agent_report]
        })
        
        return reports
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise
```

### 3. **FastAPI Background Tasks Integration**

```python
from fastapi import BackgroundTasks
from app.background.celery_app import celery_app
from app.background.tasks import recalculate_analytics, process_bulk_calls
from typing import List, Dict, Any
import asyncio

class BackgroundTaskManager:
    def __init__(self):
        self.celery_app = celery_app
    
    async def schedule_analytics_recalculation(self) -> str:
        """Schedule analytics recalculation"""
        task = recalculate_analytics.delay()
        return task.id
    
    async def schedule_bulk_processing(self, calls_data: List[Dict[str, Any]]) -> str:
        """Schedule bulk call processing"""
        task = process_bulk_calls.delay(calls_data)
        return task.id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status and result"""
        task = self.celery_app.AsyncResult(task_id)
        
        if task.state == "PENDING":
            response = {
                "state": task.state,
                "current": 0,
                "total": 1,
                "status": "Task is pending..."
            }
        elif task.state != "FAILURE":
            response = {
                "state": task.state,
                "current": task.info.get("current", 0),
                "total": task.info.get("total", 1),
                "status": task.info.get("status", "")
            }
            if "result" in task.info:
                response["result"] = task.info["result"]
        else:
            response = {
                "state": task.state,
                "current": 1,
                "total": 1,
                "status": str(task.info)
            }
        
        return response

# Global task manager
task_manager = BackgroundTaskManager()
```

### 4. **Background Task Endpoints**

```python
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from app.background.fastapi_tasks import task_manager
from app.auth.dependencies import require_admin
from app.auth.models import TokenData
from app.schemas import CallCreate
from typing import List
import json

router = APIRouter(prefix="/api/v1/background", tags=["Background Tasks"])

@router.post("/analytics/recalculate")
async def trigger_analytics_recalculation(
    current_user: TokenData = Depends(require_admin)
):
    """Trigger analytics recalculation (admin only)"""
    try:
        task_id = await task_manager.schedule_analytics_recalculation()
        return {
            "message": "Analytics recalculation scheduled",
            "task_id": task_id,
            "status": "scheduled"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule task: {str(e)}")

@router.post("/calls/bulk")
async def trigger_bulk_call_processing(
    calls_data: List[CallCreate],
    current_user: TokenData = Depends(require_admin)
):
    """Trigger bulk call processing (admin only)"""
    try:
        # Convert to dict for serialization
        calls_dict = [call.dict() for call in calls_data]
        task_id = await task_manager.schedule_bulk_processing(calls_dict)
        
        return {
            "message": f"Bulk processing scheduled for {len(calls_data)} calls",
            "task_id": task_id,
            "status": "scheduled"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule task: {str(e)}")

@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: TokenData = Depends(require_admin)
):
    """Get background task status"""
    try:
        status = await task_manager.get_task_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

@router.get("/tasks")
async def list_active_tasks(
    current_user: TokenData = Depends(require_admin)
):
    """List all active background tasks"""
    try:
        # Get active tasks from Celery
        active_tasks = task_manager.celery_app.control.inspect().active()
        
        tasks = []
        for worker, worker_tasks in active_tasks.items():
            for task in worker_tasks:
                tasks.append({
                    "task_id": task["id"],
                    "name": task["name"],
                    "worker": worker,
                    "start_time": task["time_start"]
                })
        
        return {
            "active_tasks": tasks,
            "count": len(tasks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")
```

## Integration Examples

### 1. **Main Application Integration**

```python
from fastapi import FastAPI
from app.api import router as api_router
from app.auth.routes import router as auth_router
from app.websocket.routes import router as websocket_router
from app.api_protected import router as protected_router
from app.api_background import router as background_router
from app.config import settings

app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include all routers
app.include_router(auth_router, prefix="/auth")
app.include_router(api_router, prefix="/api/v1")
app.include_router(protected_router, prefix="/api/v1")
app.include_router(background_router, prefix="/api/v1/background")
app.include_router(websocket_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2. **Client Usage Examples**

**JWT Authentication:**
```bash
# Register user
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "email": "user@example.com", "password": "user123"}'

# Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=user123"

# Use protected endpoint
curl -X GET "http://localhost:8000/api/v1/calls" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**WebSocket Connection:**
```javascript
// Connect to sentiment stream
const ws = new WebSocket('ws://localhost:8000/ws/sentiment/CALL_123?token=YOUR_JWT_TOKEN');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Sentiment update:', data);
};

ws.onopen = function() {
    console.log('Connected to sentiment stream');
};
```

**Background Tasks:**
```bash
# Trigger analytics recalculation
curl -X POST "http://localhost:8000/api/v1/background/analytics/recalculate" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"

# Check task status
curl -X GET "http://localhost:8000/api/v1/background/tasks/TASK_ID" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

### 3. **Celery Worker Startup**

```bash
# Start Celery worker
celery -A app.background.celery_app worker --loglevel=info

# Start Celery beat (for scheduled tasks)
celery -A app.background.celery_app beat --loglevel=info
```

## Summary

This implementation provides:

1. **JWT Authentication**: Complete authentication system with role-based access control
2. **WebSocket Streaming**: Real-time sentiment updates with authentication
3. **Background Processing**: Celery-based task processing with progress tracking
4. **Integration**: All features work together seamlessly

The bonus features enhance the application with enterprise-grade authentication, real-time capabilities, and robust background processing for production use. 