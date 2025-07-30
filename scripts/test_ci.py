#!/usr/bin/env python3
"""
Local CI test script to verify the GitHub Actions workflow steps
"""
import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{'='*50}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*50}")

    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        print("✅ SUCCESS")
        if result.stdout:
            print("Output:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        print("Error:", e.stderr)
        return False


def main():
    """Run CI steps locally."""
    print("🚀 Starting local CI test...")

    # Step 1: Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        return False

    # Step 2: Run linting
    if not run_command("black --check --diff .", "Running Black linting"):
        return False

    if not run_command("isort --check-only --diff .", "Running isort linting"):
        return False

    if not run_command(
        "mypy app/ --ignore-missing-imports", "Running mypy type checking"
    ):
        return False

    # Step 3: Run basic tests (without database)
    if not run_command(
        "python -m pytest tests/test_basic.py -v", "Running basic tests"
    ):
        return False

    print("\n🎉 Local CI test completed successfully!")
    print("Note: Full tests with database require PostgreSQL and Redis services.")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
