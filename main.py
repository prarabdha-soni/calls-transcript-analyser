#!/usr/bin/env python3
"""
Main entry point for the Sales Call Analytics API.
"""

import uvicorn
from app.api import app
from app.config import settings


def main():
    """Run the application."""
    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main() 