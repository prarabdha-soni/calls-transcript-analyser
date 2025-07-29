# Database Indexing Strategy

## Overview
This document explains the indexing strategy implemented for the Sales Call Analytics API, including rationale for each index choice and performance considerations.

## Implemented Indexes

### 1. Primary Key Indexes
```sql
PRIMARY KEY (id)
```

**Rationale**: Ensures data integrity and provides fast lookups by primary key.

### 2. Unique Indexes
```sql
-- Call ID uniqueness
CREATE UNIQUE INDEX ix_calls_call_id ON calls (call_id);

-- Agent ID uniqueness  
CREATE UNIQUE INDEX ix_agents_agent_id ON agents (agent_id);
CREATE UNIQUE INDEX ix_agents_email ON agents (email);

-- Customer ID uniqueness
CREATE UNIQUE INDEX ix_customers_customer_id ON customers (customer_id);
CREATE UNIQUE INDEX ix_customers_email ON customers (email);
```

**Rationale**: 
- Ensures data integrity for business keys
- Enables fast lookups by business identifiers
- Prevents duplicate entries

### 3. Performance Indexes

#### Agent ID Index
```sql
CREATE INDEX ix_calls_agent_id ON calls (agent_id);
```

**Choice**: B-tree index
**Rationale**: 
- Most common query pattern: "Get all calls for agent X"
- B-tree excels at equality and range queries
- Supports queries like: `WHERE agent_id = 'AGENT_1234'`
- Enables efficient joins with agents table

#### Start Time Index
```sql
CREATE INDEX ix_calls_start_time ON calls (start_time);
```

**Choice**: B-tree index  
**Rationale**:
- Critical for time-based analytics and reporting
- Supports range queries: `WHERE start_time BETWEEN '2025-01-01' AND '2025-01-31'`
- Enables efficient date-based filtering and sorting
- Essential for time-series analysis

### 4. Full-Text Search Indexes

#### Tsvector Index (Primary)
```sql
CREATE INDEX idx_transcript_fts ON calls USING gin(to_tsvector('english', transcript));
```

**Choice**: GIN index with tsvector
**Rationale**:
- **Semantic Search**: Enables natural language queries
- **Stemming**: Automatically handles word variations (e.g., "pricing" matches "price")
- **Relevance Ranking**: PostgreSQL can rank results by relevance
- **Performance**: GIN indexes are optimized for full-text search
- **Query Examples**:
  ```sql
  -- Find calls discussing pricing
  WHERE to_tsvector('english', transcript) @@ plainto_tsquery('pricing discussion')
  
  -- Find calls with objection handling
  WHERE to_tsvector('english', transcript) @@ plainto_tsquery('objection handling')
  ```

#### Trigram Index (Complementary)
```sql
CREATE INDEX idx_transcript_trgm ON calls USING gin(transcript gin_trgm_ops);
```

**Choice**: GIN index with trigram operators
**Rationale**:
- **Fuzzy Matching**: Handles typos and approximate matches
- **Similarity Search**: Enables similarity-based queries
- **Complementary**: Works alongside tsvector for comprehensive text search
- **Query Examples**:
  ```sql
  -- Find similar transcripts (fuzzy matching)
  WHERE transcript % 'pricing discussion'
  
  -- Find transcripts with high similarity
  WHERE similarity(transcript, 'pricing discussion') > 0.3
  ```
## Performance Considerations

### Index Maintenance
- **Write Performance**: Each index adds overhead to INSERT/UPDATE operations
- **Storage**: Indexes consume additional disk space
- **Maintenance**: Regular VACUUM and ANALYZE operations required

### Query Optimization
- **Query Planner**: PostgreSQL automatically chooses optimal indexes
- **Statistics**: Regular ANALYZE ensures accurate query planning
- **Monitoring**: Track index usage with `pg_stat_user_indexes`

## Monitoring Index Usage

```sql
-- Check index usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE tablename = 'calls'
ORDER BY idx_scan DESC;

-- Check unused indexes
SELECT 
    schemaname,
    tablename,
    indexname
FROM pg_stat_user_indexes 
WHERE idx_scan = 0 AND tablename = 'calls';
```

## Future Considerations

### Potential Additional Indexes
1. **Composite Indexes**: For multi-column queries
   ```sql
   CREATE INDEX idx_calls_agent_time ON calls (agent_id, start_time);
   ```

2. **Partial Indexes**: For filtered queries
   ```sql
   CREATE INDEX idx_calls_recent ON calls (start_time) 
   WHERE start_time > NOW() - INTERVAL '30 days';
   ```

3. **Expression Indexes**: For computed values
   ```sql
   CREATE INDEX idx_calls_sentiment_range ON calls 
   WHERE customer_sentiment_score BETWEEN -1 AND 1;
   ```

### Scaling Considerations
- **Read Replicas**: Distribute read load across multiple instances
- **Partitioning**: Partition by date for large datasets
- **Materialized Views**: Pre-compute common analytics queries

This indexing strategy balances query performance with maintenance overhead, ensuring optimal performance for the Sales Call Analytics API. 