# Design Notes: Sales Call Analytics API

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Technical Choices](#key-technical-choices)
3. [Database Design & Indexing Strategy](#database-design--indexing-strategy)
4. [Error Handling Strategy](#error-handling-strategy)
5. [Scaling Strategy](#scaling-strategy)
6. [Performance Optimizations](#performance-optimizations)
7. [Security Considerations](#security-considerations)
8. [Monitoring & Observability](#monitoring--observability)

## Architecture Overview

The Sales Call Analytics API is designed as a **microservice architecture** with the following key components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   PostgreSQL    │    │     Redis       │
│   (Async)       │◄──►│   (Primary DB)  │    │   (Caching)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Pipeline │    │   Alembic       │    │   Load Balancer │
│   (Async)       │    │   (Migrations)  │    │   (Nginx)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Design Principles

1. **Async-First**: All I/O operations are asynchronous for better concurrency
2. **Caching Strategy**: Multi-level caching for frequently accessed data
3. **Horizontal Scalability**: Stateless design for easy scaling
4. **Performance Monitoring**: Real-time metrics and observability
5. **Fault Tolerance**: Graceful error handling and recovery

## Key Technical Choices

### 1. **FastAPI + Uvicorn**

**Why FastAPI?**
- **Performance**: Built on Starlette and Pydantic, offering near-native performance
- **Async Support**: Native async/await support for high concurrency
- **Type Safety**: Automatic request/response validation with Pydantic
- **Auto Documentation**: OpenAPI/Swagger documentation generation
- **Modern Python**: Leverages Python 3.7+ features

**Why Uvicorn?**
- **ASGI Server**: Native async support
- **High Performance**: Built on uvloop for better performance
- **Production Ready**: Stable and battle-tested

```python
@app.get("/api/v1/calls")
async def get_calls(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    agent_id: Optional[str] = None
) -> CallListResponse:
    pass
```

### 2. **PostgreSQL + SQLAlchemy**

**Why PostgreSQL?**
- **ACID Compliance**: Full transactional support
- **Advanced Indexing**: GIN indexes for full-text search
- **JSON Support**: Native JSONB for flexible data storage
- **Performance**: Excellent query optimizer and execution engine
- **Extensions**: Rich ecosystem (pg_trgm, full-text search)

**Why SQLAlchemy?**
- **ORM + Raw SQL**: Best of both worlds
- **Async Support**: SQLAlchemy 2.0 with async capabilities
- **Type Safety**: Integration with Pydantic models
- **Migration Support**: Alembic integration

```python
async def get_calls_optimized(session: AsyncSession, **filters):
    query = """
    SELECT c.*, a.name as agent_name 
    FROM calls c 
    JOIN agents a ON c.agent_id = a.id 
    WHERE c.start_time >= :from_date
    """
    result = await session.execute(text(query), filters)
    return result.fetchall()
```

### 3. **Redis for Caching**

**Why Redis?**
- **In-Memory Performance**: Sub-millisecond response times
- **Data Structures**: Rich set of data structures (strings, hashes, sets)
- **Persistence**: Optional persistence for durability
- **Pub/Sub**: Real-time communication capabilities
- **Clustering**: Horizontal scaling support

```python
@cache_response(ttl=60) 
async def get_calls_list(**filters):
    cache_key = f"calls:{hash(str(filters))}"
    return await cache_manager.get_or_set(cache_key, fetch_calls, filters)
```

### 4. **Async Programming Model**

**Why Async?**
- **Concurrency**: Handle thousands of concurrent connections
- **I/O Efficiency**: Non-blocking database and network operations
- **Resource Efficiency**: Lower memory footprint per connection
- **Scalability**: Better CPU utilization

```python
async def process_calls_batch(calls: List[Call]):
    tasks = [process_single_call(call) for call in calls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]
```

## Database Design & Indexing Strategy

### 1. **Table Schema Design**

```sql
CREATE TABLE calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id VARCHAR(50) UNIQUE NOT NULL,
    agent_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    start_time TIMESTAMP NOT NULL,
    duration_seconds INTEGER NOT NULL,
    transcript TEXT NOT NULL,
    agent_talk_ratio FLOAT NOT NULL,
    customer_sentiment_score FLOAT NOT NULL,
    embedding TEXT NOT NULL,  -- JSON array of floats
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2. **Indexing Strategy**

**Primary Indexes (Performance Critical):**
```sql
-- Composite index for most common query pattern
CREATE INDEX idx_calls_agent_date ON calls (agent_id, start_time DESC);

-- Sentiment analysis queries
CREATE INDEX idx_calls_sentiment ON calls (customer_sentiment_score);

-- Duration-based filtering
CREATE INDEX idx_calls_duration ON calls (duration_seconds);

-- Language filtering
CREATE INDEX idx_calls_language ON calls (language);

-- Analytics queries (multi-column)
CREATE INDEX idx_calls_analytics ON calls (agent_id, customer_sentiment_score, agent_talk_ratio);
```

**Specialized Indexes:**
```sql
-- Full-text search on transcripts
CREATE INDEX idx_calls_transcript_fts ON calls USING gin (to_tsvector('english', transcript));

-- Embedding similarity search (if using pg_trgm)
CREATE INDEX idx_calls_embedding_gin ON calls USING gin (embedding gin_trgm_ops);
```

**Index Rationale:**

1. **`idx_calls_agent_date`**: Most queries filter by agent and sort by date
2. **`idx_calls_sentiment`**: Sentiment analysis is a key feature
3. **`idx_calls_analytics`**: Multi-column index for complex analytics queries
4. **`idx_calls_transcript_fts`**: Full-text search on call transcripts
5. **Partial indexes**: For recent data queries (last 30 days)

### 3. **Materialized Views for Analytics**

```sql
-- Pre-computed agent analytics
CREATE MATERIALIZED VIEW mv_agent_analytics AS
SELECT 
    agent_id,
    COUNT(*) as total_calls,
    AVG(customer_sentiment_score) as avg_sentiment,
    AVG(agent_talk_ratio) as avg_talk_ratio,
    AVG(duration_seconds) as avg_duration,
    MIN(start_time) as first_call,
    MAX(start_time) as last_call
FROM calls
GROUP BY agent_id;

-- Daily statistics
CREATE MATERIALIZED VIEW mv_daily_stats AS
SELECT 
    DATE(start_time) as call_date,
    COUNT(*) as total_calls,
    AVG(duration_seconds) as avg_duration,
    AVG(customer_sentiment_score) as avg_sentiment
FROM calls
GROUP BY DATE(start_time);
```

## Error Handling Strategy

### 1. **Multi-Level Error Handling**

```python
# Application-level error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Log the error for debugging
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )
```

### 2. **Database Error Handling**

```python
# Database operation wrapper
async def safe_db_operation(operation: Callable, *args, **kwargs):
    try:
        return await operation(*args, **kwargs)
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Resource already exists")
    except asyncpg.ForeignKeyViolationError:
        raise HTTPException(status_code=400, detail="Invalid reference")
    except asyncpg.ConnectionError:
        raise HTTPException(status_code=503, detail="Database unavailable")
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")
```

### 3. **Cache Error Handling**

```python
async def get_cached_data(key: str, fallback_func: Callable):
    try:
        cached = await cache_manager.get(key)
        if cached:
            return cached
    except Exception as e:
        logger.warning(f"Cache error: {e}")
    
    data = await fallback_func()
    
    try:
        await cache_manager.set(key, data)
    except Exception as e:
        logger.warning(f"Cache set error: {e}")
    
    return data
```

### 4. **Circuit Breaker Pattern**

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise e
```

## Scaling Strategy

### 1. **Horizontal Scaling Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Load Balancer │    │   Load Balancer │
│   (Nginx)       │    │   (Nginx)       │    │   (Nginx)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Instance  │    │   API Instance  │    │   API Instance  │
│   (Port 8000)   │    │   (Port 8001)   │    │   (Port 8002)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   PostgreSQL Cluster    │
                    │   (Primary + Replicas) │
                    └─────────────────────────┘
```

### 2. **Data Ingestion Scaling**

**Batch Processing Strategy:**
```python
class BatchIngestionPipeline:
    def __init__(self, batch_size=100, max_workers=4):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
    
    async def ingest_large_dataset(self, calls: List[Call]):
        # Split into batches
        batches = [calls[i:i + self.batch_size] 
                  for i in range(0, len(calls), self.batch_size)]
        
        # Process batches concurrently
        tasks = [self.process_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if not isinstance(r, Exception)]
    
    async def process_batch(self, batch: List[Call]):
        async with self.semaphore:
            # Use bulk insert for efficiency
            await self.bulk_insert_calls(batch)
            # Process AI insights in parallel
            await self.process_ai_insights(batch)
```

**Streaming Ingestion:**
```python
class StreamingIngestionPipeline:
    def __init__(self, buffer_size=1000):
        self.buffer_size = buffer_size
        self.buffer = []
        self.lock = asyncio.Lock()
    
    async def ingest_stream(self, call_stream: AsyncIterator[Call]):
        async for call in call_stream:
            async with self.lock:
                self.buffer.append(call)
                
                if len(self.buffer) >= self.buffer_size:
                    await self.flush_buffer()
    
    async def flush_buffer(self):
        if self.buffer:
            batch = self.buffer.copy()
            self.buffer.clear()
            # Process batch asynchronously
            asyncio.create_task(self.process_batch(batch))
```

### 3. **Query Traffic Scaling**

**Read Replicas Strategy:**
```python
class DatabaseRouter:
    def __init__(self, primary_url: str, replica_urls: List[str]):
        self.primary_url = primary_url
        self.replica_urls = replica_urls
        self.current_replica = 0
    
    async def get_read_connection(self):
        # Round-robin load balancing for read replicas
        replica_url = self.replica_urls[self.current_replica]
        self.current_replica = (self.current_replica + 1) % len(self.replica_urls)
        return create_async_engine(replica_url)
    
    async def get_write_connection(self):
        # Always use primary for writes
        return create_async_engine(self.primary_url)
```

**Query Optimization:**
```python
class QueryOptimizer:
    @staticmethod
    async def optimize_calls_query(session: AsyncSession, **filters):
        # Build dynamic query based on filters
        query = """
        SELECT c.*, 
               a.name as agent_name,
               cu.name as customer_name
        FROM calls c
        LEFT JOIN agents a ON c.agent_id = a.agent_id
        LEFT JOIN customers cu ON c.customer_id = cu.customer_id
        WHERE 1=1
        """
        
        params = {}
        
        # Add filters dynamically
        if filters.get('agent_id'):
            query += " AND c.agent_id = :agent_id"
            params['agent_id'] = filters['agent_id']
        
        if filters.get('from_date'):
            query += " AND c.start_time >= :from_date"
            params['from_date'] = filters['from_date']
        
        # Add pagination
        query += " ORDER BY c.start_time DESC LIMIT :limit OFFSET :offset"
        params['limit'] = filters.get('limit', 50)
        params['offset'] = filters.get('offset', 0)
        
        result = await session.execute(text(query), params)
        return result.fetchall()
```

### 4. **Caching Strategy**

**Multi-Level Caching:**
```python
class MultiLevelCache:
    def __init__(self):
        self.l1_cache = {}  # In-memory cache
        self.l2_cache = redis.Redis()  # Redis cache
        self.l3_cache = None  # Database (fallback)
    
    async def get(self, key: str):
        # L1: In-memory cache (fastest)
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # L2: Redis cache
        try:
            cached = await self.l2_cache.get(key)
            if cached:
                self.l1_cache[key] = cached
                return cached
        except Exception:
            pass
        
        # L3: Database (slowest)
        data = await self.fetch_from_database(key)
        
        # Cache in both levels
        try:
            await self.l2_cache.set(key, data, ex=300)
            self.l1_cache[key] = data
        except Exception:
            pass
        
        return data
```

## Performance Optimizations

### 1. **Connection Pooling**

```python
# Optimized connection pool settings
engine = create_async_engine(
    database_url,
    pool_size=20,           # Base pool size
    max_overflow=30,        # Additional connections
    pool_timeout=30,        # Connection timeout
    pool_pre_ping=True,     # Verify connections
    pool_recycle=3600,      # Recycle connections every hour
    echo=False              # Disable SQL logging in production
)
```

### 2. **Response Compression**

```python
# GZip compression for large responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom compression for specific endpoints
@app.middleware("http")
async def compress_large_responses(request: Request, call_next):
    response = await call_next(request)
    
    if response.headers.get("content-length"):
        size = int(response.headers["content-length"])
        if size > 1000:
            response.headers["content-encoding"] = "gzip"
    
    return response
```

### 3. **Background Task Processing**

```python
# Process heavy tasks in background
@app.post("/api/v1/calls/bulk")
async def bulk_ingest_calls(
    calls_data: List[dict],
    background_tasks: BackgroundTasks
):
    # Start background processing
    background_tasks.add_task(process_bulk_calls, calls_data)
    
    return {
        "message": f"Processing {len(calls_data)} calls in background",
        "status": "processing"
    }
```

## Security Considerations

### 1. **Input Validation**

```python
# Strict input validation
class CallCreate(BaseModel):
    call_id: str = Field(..., min_length=1, max_length=50, regex=r"^[A-Z0-9_]+$")
    agent_id: str = Field(..., min_length=1, max_length=50)
    transcript: str = Field(..., min_length=10, max_length=10000)
    duration_seconds: int = Field(..., ge=1, le=3600)
    
    @validator('call_id')
    def validate_call_id(cls, v):
        if not v.isalnum() and '_' not in v:
            raise ValueError('Call ID must be alphanumeric with underscores')
        return v
```

### 2. **Rate Limiting**

```python
# Rate limiting middleware
class RateLimiter:
    def __init__(self, requests_per_minute=60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}
    
    async def check_rate_limit(self, client_ip: str):
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if req_time > minute_ago
            ]
        else:
            self.requests[client_ip] = []
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        self.requests[client_ip].append(now)
```

### 3. **SQL Injection Prevention**

```python
# Always use parameterized queries
async def get_calls_by_agent(session: AsyncSession, agent_id: str):
    # ✅ Safe - parameterized query
    query = "SELECT * FROM calls WHERE agent_id = :agent_id"
    result = await session.execute(text(query), {"agent_id": agent_id})
    
    # ❌ Dangerous - string concatenation
    # query = f"SELECT * FROM calls WHERE agent_id = '{agent_id}'"
    
    return result.fetchall()
```

## Monitoring & Observability

### 1. **Performance Metrics**

```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "api_calls": {},
            "query_times": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0
        }
    
    def record_api_call(self, endpoint: str, method: str, duration: float):
        key = f"{method}_{endpoint}"
        if key not in self.metrics["api_calls"]:
            self.metrics["api_calls"][key] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0
            }
        
        metric = self.metrics["api_calls"][key]
        metric["count"] += 1
        metric["total_time"] += duration
        metric["avg_time"] = metric["total_time"] / metric["count"]
```

### 2. **Health Checks**

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": await check_database_health(),
        "cache": await check_cache_health(),
        "performance": {
            "cache_hit_rate": performance_monitor.get_cache_hit_rate(),
            "avg_response_time": performance_monitor.get_avg_response_time()
        }
    }
```

### 3. **Distributed Tracing**

```python
# OpenTelemetry integration
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize tracing
tracer = trace.get_tracer(__name__)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Custom spans for database operations
async def get_calls_with_tracing(**filters):
    with tracer.start_as_current_span("database.query") as span:
        span.set_attribute("query.type", "calls")
        span.set_attribute("query.filters", str(filters))
        
        result = await get_calls(**filters)
        
        span.set_attribute("query.result_count", len(result))
        return result
```

## Conclusion

This design provides a robust, scalable foundation for the Sales Call Analytics API with:

1. **High Performance**: Async architecture with optimized database queries
2. **Scalability**: Horizontal scaling with load balancing
3. **Reliability**: Comprehensive error handling and fault tolerance
4. **Observability**: Real-time monitoring and metrics
5. **Security**: Input validation and rate limiting
6. **Maintainability**: Clean architecture with separation of concerns

The system is designed to handle high load scenarios while maintaining performance and reliability through intelligent caching, connection pooling, and horizontal scaling strategies. 