"""Initial migration

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pg_trgm extension for fuzzy text matching (alternative to tsvector)
    # This allows trigram-based similarity searches for transcript content
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Create calls table
    op.create_table(
        "calls",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("call_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("agent_talk_ratio", sa.Float(), nullable=True),
        sa.Column("customer_sentiment_score", sa.Float(), nullable=True),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes with performance optimization comments

    # Unique index on call_id for fast lookups and data integrity
    op.create_index(op.f("ix_calls_call_id"), "calls", ["call_id"], unique=True)

    # Index on agent_id for filtering calls by agent (common query pattern)
    # Choice: B-tree index for equality and range queries on agent_id
    op.create_index(op.f("ix_calls_agent_id"), "calls", ["agent_id"], unique=False)

    # Index on start_time for date range queries and time-based analytics
    # Choice: B-tree index for efficient range scans on timestamps
    op.create_index(op.f("ix_calls_start_time"), "calls", ["start_time"], unique=False)

    # Full-text search index using GIN for transcript content search
    # Choice: GIN index with tsvector for fast text search, stemming, and relevance ranking
    # Alternative: pg_trgm extension for fuzzy matching, but tsvector is better for semantic search
    op.execute(
        "CREATE INDEX idx_transcript_fts ON calls USING gin(to_tsvector('english', transcript))"
    )

    # Additional trigram index for fuzzy matching on transcript content
    # This complements tsvector by enabling similarity searches and typo tolerance
    op.execute(
        "CREATE INDEX idx_transcript_trgm ON calls USING gin(transcript gin_trgm_ops)"
    )

    # Create agents table
    op.create_table(
        "agents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("total_calls", sa.Integer(), nullable=True),
        sa.Column("avg_sentiment", sa.Float(), nullable=True),
        sa.Column("avg_talk_ratio", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_agents_agent_id"), "agents", ["agent_id"], unique=True)
    op.create_index(op.f("ix_agents_email"), "agents", ["email"], unique=True)

    # Create customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_customers_customer_id"), "customers", ["customer_id"], unique=True
    )
    op.create_index(op.f("ix_customers_email"), "customers", ["email"], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_customers_email"), table_name="customers")
    op.drop_index(op.f("ix_customers_customer_id"), table_name="customers")
    op.drop_index(op.f("ix_agents_email"), table_name="agents")
    op.drop_index(op.f("ix_agents_agent_id"), table_name="agents")
    op.drop_index(op.f("ix_calls_start_time"), table_name="calls")
    op.drop_index(op.f("ix_calls_agent_id"), table_name="calls")
    op.drop_index(op.f("ix_calls_call_id"), table_name="calls")

    # Drop full-text search indexes
    op.execute("DROP INDEX IF EXISTS idx_transcript_trgm")
    op.execute("DROP INDEX IF EXISTS idx_transcript_fts")

    # Drop tables
    op.drop_table("customers")
    op.drop_table("agents")
    op.drop_table("calls")
