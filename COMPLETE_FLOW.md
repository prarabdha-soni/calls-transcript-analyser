# Sales Call Analytics API - Complete Flow

## System Overview
This document walks you through how the Sales Call Analytics API works, from the moment data comes in to when analytics are delivered. The goal is to give you a clear, practical sense of the system’s moving parts and how they fit together.

## Architecture Flow

### 1. Data Ingestion Pipeline
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Faker Data    │───▶│  CallTranscript  │───▶│  AI Insights    │
│   Generation    │    │   Generator      │    │   Processing    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  PostgreSQL DB   │
                       │  (Raw + Analytics)│
                       └──────────────────┘
```

**How it works:**
1. **Synthetic Data Generation:** We use the `Faker` library to create realistic sales call data for testing and development.
2. **Transcript Generation:** The system builds out conversations, alternating between agent and customer, to mimic real-world calls.
3. **AI Processing:** Each transcript is analyzed for things like sentiment, talk ratios, and embeddings.
4. **Database Storage:** Both the raw call data and the analytics are saved in PostgreSQL for later querying.

### 2. Data Flow Details

#### A. Call Data Generation
```python
# Example of what’s generated for each call:
{
    "call_id": "CALL_12345678",
    "agent_id": "AGENT_1234", 
    "customer_id": "CUST_123456",
    "language": "en",
    "start_time": "2025-01-15T10:30:00",
    "duration_seconds": 450,
    "transcript": "Agent: Thank you for your time...\nCustomer: I'm interested in..."
}
```

#### B. AI Insights Processing
```python
# For each transcript, we extract:
- agent_talk_ratio: 0.65 (how much the agent spoke)
- customer_sentiment_score: 0.3 (from -1 to +1)
- embedding: [0.1, 0.2, ...] (384-dimensional vector)
```

#### C. Database Storage
```sql
-- Raw data and analytics are stored together in PostgreSQL
INSERT INTO calls (
    call_id, agent_id, customer_id, language, 
    start_time, duration_seconds, transcript,
    agent_talk_ratio, customer_sentiment_score, embedding
) VALUES (...);
```

### 3. API Request Flow

#### A. Authentication Flow
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │───▶│   /auth/    │───▶│  JWT Token  │
│  Request    │    │   login     │    │  Generated  │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │ Protected   │
                   │ Endpoints   │
                   └─────────────┘
```

#### B. API Endpoint Flow
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │───▶│  FastAPI    │───▶│  Database   │───▶│  Response   │
│  Request    │    │  Router     │    │  Query      │    │  (JSON)     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 4. Complete Request-Response Flow

#### Step 1: Authentication
```bash
# Register a new user
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "email": "user@example.com", "password": "password123"}'

# Log in to get your token
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=password123"
```

#### Step 2: API Requests
```bash
# Get a list of calls (requires authentication)
curl -X GET "http://localhost:8000/api/v1/calls?limit=10&agent_id=AGENT_1234" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get details for a specific call
curl -X GET "http://localhost:8000/api/v1/calls/CALL_12345678" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get recommendations for a call
curl -X GET "http://localhost:8000/api/v1/calls/CALL_12345678/recommendations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get analytics for agents
curl -X GET "http://localhost:8000/api/v1/analytics/agents" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. Database Query Flow

#### A. Calls Query with Filters
```sql
-- Example: Get all calls for a specific agent after a certain date
SELECT 
    call_id, agent_id, customer_id, language,
    start_time, duration_seconds, transcript,
    agent_talk_ratio, customer_sentiment_score
FROM calls 
WHERE agent_id = 'AGENT_1234' 
  AND start_time >= '2025-01-01'
ORDER BY start_time DESC
LIMIT 50 OFFSET 0;
```

#### B. Full-Text Search
```sql
-- Example: Find calls where "pricing discussion" is mentioned
SELECT * FROM calls 
WHERE to_tsvector('english', transcript) @@ plainto_tsquery('pricing discussion')
ORDER BY ts_rank(to_tsvector('english', transcript), plainto_tsquery('pricing discussion')) DESC;
```

#### C. Analytics Query
```sql
-- Example: Get analytics for all agents
SELECT 
    agent_id,
    COUNT(*) as total_calls,
    AVG(customer_sentiment_score) as avg_sentiment,
    AVG(agent_talk_ratio) as avg_talk_ratio
FROM calls 
GROUP BY agent_id 
ORDER BY avg_sentiment DESC;
```

### 6. Performance Optimization Flow

#### A. Caching Layer
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │───▶│   Redis     │───▶│  Database   │
│  Request    │    │   Cache     │    │  (if miss)  │
└─────────────┘    └─────────────┘    └─────────────┘
```

#### B. Connection Pooling
```python
# Example: SQLAlchemy async engine with connection pooling
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
```

### 7. Real-Time Features Flow

#### A. WebSocket Sentiment Streaming
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │───▶│  WebSocket  │───▶│  Real-time  │
│  Connection │    │  Endpoint   │    │  Sentiment  │
└─────────────┘    └─────────────┘    └─────────────┘
```

#### B. Background Job Processing
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Scheduler  │───▶│  Celery     │───▶│  Analytics  │
│  (Nightly)  │    │  Worker     │    │  Recalc     │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 8. Error Handling Flow

#### A. Multi-Level Error Handling
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │───▶│  FastAPI    │───▶│  Database   │
│  Request    │    │  Exception  │    │  Error      │
│             │    │  Handler    │    │  Handler    │
└─────────────┘    └─────────────┘    └─────────────┘
```

#### B. Circuit Breaker Pattern
```python
# For external service calls
@circuit_breaker(failure_threshold=5, recovery_timeout=60)
async def call_external_service():
    # External API call
    pass
```

### 9. Scaling Flow

#### A. Horizontal Scaling
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Load      │───▶│   Nginx     │───▶│  Multiple   │
│  Balancer   │    │   Proxy     │    │  API Instances│
└─────────────┘    └─────────────┘    └─────────────┘
```

#### B. Database Scaling
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   API       │───▶│  Primary    │───▶│  Read       │
│  Instances  │    │  Database   │    │  Replicas   │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 10. Monitoring Flow

#### A. Performance Monitoring
```python
# Metrics collection
@monitor_performance
async def get_calls():
    # API endpoint with performance tracking
    pass
```

#### B. Health Checks
```python
# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "cache": "connected"
    }
```

## Complete System Flow Summary

1. **Data Generation:** Faker creates synthetic call data for testing.
2. **AI Processing:** Transcripts are analyzed for insights like sentiment and talk ratio.
3. **Database Storage:** Everything is stored in PostgreSQL, with indexes for speed.
4. **API Authentication:** JWT keeps endpoints secure.
5. **Request Processing:** FastAPI handles async requests efficiently.
6. **Query Optimization:** Indexed queries keep things fast.
7. **Response Delivery:** JSON responses, often cached for speed.
8. **Real-time Features:** WebSocket streaming for live updates.
9. **Background Processing:** Celery handles heavy analytics jobs.
10. **Monitoring:** Performance and health checks keep things running smoothly.

## Key Technologies Used

- **Backend:** FastAPI, SQLAlchemy, PostgreSQL
- **Authentication:** JWT, bcrypt
- **Caching:** Redis
- **Background Jobs:** Celery
- **Real-time:** WebSockets
- **Monitoring:** Custom metrics, health checks
- **Testing:** Pytest, coverage
- **Deployment:** Docker, Docker Compose

This flow is designed to be robust, scalable, and easy to work with—whether you’re developing, deploying, or just exploring the system. 