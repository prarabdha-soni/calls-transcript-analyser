# Scaling Guide for Sales Call Analytics API

This guide provides comprehensive instructions for scaling the Sales Call Analytics API to handle high load scenarios.

## Table of Contents

1. [Performance Optimizations](#performance-optimizations)
2. [Database Scaling](#database-scaling)
3. [Application Scaling](#application-scaling)
4. [Load Testing](#load-testing)
5. [Monitoring and Metrics](#monitoring-and-metrics)
6. [Production Deployment](#production-deployment)

## Performance Optimizations

### 1. Database Optimizations

Run the database optimization script to add performance indexes and materialized views:

```bash
python scripts/optimize_database.py
```

This script will:
- Create performance indexes for common query patterns
- Add materialized views for analytics
- Optimize connection pool settings
- Run VACUUM and ANALYZE for better query planning

### 2. Application Optimizations

The optimized API (`app/api_optimized.py`) includes:

- **Caching**: Redis-based caching for API responses
- **Connection Pooling**: Optimized database connection management
- **Query Optimization**: Raw SQL queries for better performance
- **Compression**: GZip middleware for response compression
- **Performance Monitoring**: Real-time metrics collection

### 3. Caching Strategy

The application uses a multi-level caching strategy:

```python
# Cache API responses for different TTLs
@cache_response(ttl=60)    # Calls list - 1 minute
@cache_response(ttl=300)   # Call details - 5 minutes
@cache_response(ttl=600)   # Recommendations - 10 minutes
@cache_response(ttl=300)   # Analytics - 5 minutes
```

## Database Scaling

### 1. PostgreSQL Configuration

Add these optimizations to your `postgresql.conf`:

```ini
# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Write performance
checkpoint_completion_target = 0.9
wal_buffers = 16MB

# Query optimization
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200

# Connection settings
max_connections = 200
```

### 2. Connection Pooling

The application uses optimized connection pooling:

```python
# Connection pool settings
pool_size = 20
max_overflow = 30
pool_timeout = 30
pool_pre_ping = True
pool_recycle = 3600
```

### 3. Read Replicas

For high read loads, consider setting up PostgreSQL read replicas:

```bash
# Primary database (writes)
DATABASE_URL=postgresql://user:pass@primary-host/db

# Read replicas (reads)
DATABASE_URL_READ_REPLICA=postgresql://user:pass@replica-host/db
```

## Application Scaling

### 1. Horizontal Scaling

Run multiple API instances:

```bash
# Start 3 optimized instances
python scripts/scale_app.py --instances 3 --optimized

# Or run scaling demo
python scripts/scale_app.py --demo
```

### 2. Load Balancer Configuration

The scaling script generates load balancer configuration:

```json
{
  "upstream_servers": [
    "http://localhost:8000",
    "http://localhost:8001", 
    "http://localhost:8002"
  ],
  "health_check_interval": 30,
  "health_check_timeout": 5,
  "load_balancing_method": "round_robin"
}
```

### 3. Process Management

Use process managers for production:

```bash
# Using Supervisor
[program:sales-api]
command=uvicorn app.api_optimized:app --host 0.0.0.0 --port 8000
directory=/path/to/app
autostart=true
autorestart=true
```

## Load Testing

### 1. Basic Load Test

```bash
# Run comprehensive load test
python scripts/load_test.py --ingestion-calls 1000 --concurrent-queries 500

# Test specific endpoints
python scripts/load_test.py --base-url http://localhost:8000
```

### 2. High Load Testing

```bash
# Test with high concurrency
python scripts/load_test.py \
  --ingestion-calls 5000 \
  --concurrent-queries 2000 \
  --concurrent-requests 100
```

### 3. Performance Metrics

The load test provides detailed metrics:

- **Requests per second**
- **Response times** (avg, min, max, 95th, 99th percentile)
- **Error rates**
- **Throughput analysis**

## Monitoring and Metrics

### 1. Performance Endpoints

```bash
# Get performance metrics
curl http://localhost:8000/metrics

# Get detailed performance stats
curl http://localhost:8000/api/v1/performance

# Health check with performance data
curl http://localhost:8000/health
```

### 2. Key Metrics to Monitor

- **API Response Times**: Target < 200ms for 95th percentile
- **Cache Hit Rate**: Target > 80%
- **Database Connection Pool**: Monitor pool utilization
- **Error Rates**: Target < 1%
- **Throughput**: Requests per second

### 3. Resource Monitoring

```bash
# Monitor system resources
python scripts/scale_app.py --monitor

# Check instance health
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

## Production Deployment

### 1. Docker Compose for Production

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/sales_calls
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    deploy:
      replicas: 3
      
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: sales_calls
      POSTGRES_USER: sales_user
      POSTGRES_PASSWORD: sales_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
      
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api

volumes:
  postgres_data:
```

### 2. Nginx Load Balancer

```nginx
# nginx.conf
upstream api_servers {
    server api:8000;
    server api:8001;
    server api:8002;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://api_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sales-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sales-api
  template:
    metadata:
      labels:
        app: sales-api
    spec:
      containers:
      - name: api
        image: sales-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
---
apiVersion: v1
kind: Service
metadata:
  name: sales-api-service
spec:
  selector:
    app: sales-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Performance Benchmarks

### Expected Performance

With optimizations enabled:

- **API Response Time**: < 100ms (95th percentile)
- **Database Queries**: < 50ms average
- **Cache Hit Rate**: > 85%
- **Throughput**: 1000+ requests/second
- **Concurrent Users**: 500+ simultaneous users

### Scaling Factors

- **Vertical Scaling**: Increase CPU/memory for single instance
- **Horizontal Scaling**: Add more instances behind load balancer
- **Database Scaling**: Read replicas, connection pooling
- **Caching**: Redis cluster, CDN for static content

## Troubleshooting

### Common Issues

1. **High Response Times**
   - Check database indexes
   - Verify cache hit rates
   - Monitor connection pool usage

2. **Memory Issues**
   - Increase worker memory limits
   - Optimize query result sizes
   - Enable response compression

3. **Database Bottlenecks**
   - Add read replicas
   - Optimize slow queries
   - Increase connection pool size

### Performance Tuning

```bash
# Monitor real-time performance
watch -n 1 'curl -s http://localhost:8000/metrics | jq'

# Check cache performance
curl -s http://localhost:8000/api/v1/performance | jq '.cache_hit_rate'

# Test database performance
python scripts/optimize_database.py
```

## Conclusion

This scaling guide provides a comprehensive approach to handling high load scenarios. The key components are:

1. **Database optimization** with proper indexes and materialized views
2. **Application caching** with Redis for frequently accessed data
3. **Horizontal scaling** with multiple API instances
4. **Load balancing** for distributing traffic
5. **Monitoring and metrics** for performance tracking

Start with the basic optimizations and gradually scale up based on your specific load requirements. 