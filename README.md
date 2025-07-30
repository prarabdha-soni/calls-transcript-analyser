# Sales Call Analytics API

A Python microservice that ingests sales call transcripts, stores them durably, and serves actionable conversation analytics through a REST API.

## Features

- **Async Data Ingestion**: Pipeline for ingesting 200+ call transcripts with AI processing
- **PostgreSQL Storage**: Durable storage with proper indexing and full-text search
- **AI Insights**: Sentiment analysis and sentence embeddings for call similarity
- **REST API**: FastAPI-based API with comprehensive endpoints
- **Real-time Analytics**: WebSocket support for real-time sentiment streaming
- **Comprehensive Testing**: 70%+ test coverage with pytest
- **Docker Support**: Containerized deployment with docker-compose
- **CI/CD Pipeline**: GitHub Actions workflow with automated testing and deployment

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Source   │───▶│  Async Pipeline │───▶│   PostgreSQL    │
│   (Synthetic)   │    │   (aiohttp)     │    │   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   AI Insights   │
                       │ (Sentiment +    │
                       │  Embeddings)    │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   FastAPI       │
                       │   REST API      │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   WebSocket     │
                       │ (Real-time)     │
                       └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL (for production)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sales-call-analytics
   ```

2. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Run database migrations**
   ```bash
   docker-compose exec app alembic upgrade head
   ```

4. **Ingest sample data**
   ```bash
   docker-compose exec app python scripts/ingest_data.py
   ```

5. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. **Run migrations**
   ```bash
   alembic upgrade head
   ```

4. **Start the application**
   ```bash
   uvicorn app.api:app --reload
   ```

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/calls` | Get calls with filtering and pagination |
| GET | `/api/v1/calls/{call_id}` | Get specific call details |
| GET | `/api/v1/calls/{call_id}/recommendations` | Get similar calls and coaching tips |
| GET | `/api/v1/analytics/agents` | Get agent analytics leaderboard |

### Query Parameters

#### GET /api/v1/calls
- `limit` (int, 1-100): Number of results per page (default: 50)
- `offset` (int, ≥0): Number of results to skip (default: 0)
- `agent_id` (string): Filter by agent ID
- `from_date` (datetime): Filter calls from this date
- `to_date` (datetime): Filter calls to this date
- `min_sentiment` (float, -1 to 1): Minimum sentiment score
- `max_sentiment` (float, -1 to 1): Maximum sentiment score

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ws/sentiment/{call_id}` | Real-time sentiment streaming |

### Example Usage

```bash
# Get all calls
curl "http://localhost:8000/api/v1/calls"

# Get calls for a specific agent
curl "http://localhost:8000/api/v1/calls?agent_id=AGENT_001"

# Get calls with sentiment filter
curl "http://localhost:8000/api/v1/calls?min_sentiment=0.5"

# Get agent analytics
curl "http://localhost:8000/api/v1/analytics/agents"
```

## Data Model

### Call Entity
```python
{
    "id": "uuid",
    "call_id": "CALL_12345",
    "agent_id": "AGENT_001",
    "customer_id": "CUST_001",
    "language": "en",
    "start_time": "2024-01-01T10:00:00Z",
    "duration_seconds": 300,
    "transcript": "Agent: Hello...\nCustomer: Hi...",
    "agent_talk_ratio": 0.65,
    "customer_sentiment_score": 0.8,
    "embedding": "[0.1, 0.2, ...]",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z"
}
```

## AI Features

### Sentiment Analysis
- Uses `distilbert-base-uncased-finetuned-sst-2-english` model
- Analyzes customer speech only
- Returns score from -1 (negative) to +1 (positive)

### Sentence Embeddings
- Uses `sentence-transformers/all-MiniLM-L6-v2` model
- Generates 384-dimensional embeddings
- Enables semantic similarity search

### Talk Ratio Calculation
- Calculates agent_words / total_words
- Excludes filler tokens and system messages
- Helps identify agent dominance in conversations

## Machine Learning Models Used

- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Sentiment Model:** `distilbert-base-uncased-finetuned-sst-2-english`

## Database Schema

### Indexes
- `call_id`: Unique index for fast lookups
- `agent_id`: Index for agent filtering
- `start_time`: Index for date range queries
- `transcript`: GIN index for full-text search

### Full-Text Search
Uses PostgreSQL's `to_tsvector` with GIN index for efficient text search on transcripts.

## Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py
```

### Test Coverage
- Unit tests for all modules
- Integration tests for API endpoints
- WebSocket functionality tests
- AI insights module tests

## Deployment

### Docker
```bash
# Build image
docker build -t sales-call-analytics .

# Run container
docker run -p 8000:8000 sales-call-analytics
```

### Production
1. Set up PostgreSQL database
2. Configure environment variables
3. Run migrations: `alembic upgrade head`
4. Start the application: `uvicorn app.api:app --host 0.0.0.0 --port 8000`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:password@localhost/sales_calls` |
| `DATABASE_URL_ASYNC` | Async PostgreSQL connection string | `postgresql+asyncpg://user:password@localhost/sales_calls` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `SECRET_KEY` | JWT secret key | `your-secret-key-here` |
| `OPENAI_API_KEY` | (optional, for LLM integration) | `None` |
