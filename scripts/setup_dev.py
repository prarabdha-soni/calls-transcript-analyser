#!/usr/bin/env python3
"""
Development setup script for the Sales Call Analytics API.
This script helps set up the development environment.
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def setup_environment():
    """Set up the development environment."""

    # Check if we're in the right directory
    if not Path("requirements.txt").exists():
        print("❌ Please run this script from the project root directory")
        return False

    # Create virtual environment if it doesn't exist
    if not Path(".venv").exists():
        print("📦 Creating virtual environment...")
        if not run_command("python -m venv .venv", "Creating virtual environment"):
            return False

    # Determine the correct pip and python paths
    if os.name == "nt":  # Windows
        pip_path = ".venv\\Scripts\\pip"
        python_path = ".venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        pip_path = ".venv/bin/pip"
        python_path = ".venv/bin/python"

    # Install dependencies
    if not run_command(
        f"{pip_path} install -r requirements.txt", "Installing dependencies"
    ):
        return False

    # Install development dependencies
    if not run_command(
        f"{pip_path} install -e .[dev]", "Installing development dependencies"
    ):
        return False

    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        print("📝 Creating .env file from template...")
        if Path("env.example").exists():
            with open("env.example", "r") as f:
                env_content = f.read()
            with open(".env", "w") as f:
                f.write(env_content)
            print("✅ .env file created from template")
        else:
            print("⚠️  No env.example found, please create .env manually")

    print("✅ Development environment setup completed!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your database credentials")
    print("2. Start PostgreSQL and Redis (or use docker-compose)")
    print("3. Run: alembic upgrade head")
    print("4. Run: python scripts/ingest_data.py")
    print("5. Run: uvicorn app.api:app --reload")

    return True


def run_tests():
    """Run the test suite."""

    # Determine the correct python path
    if os.name == "nt":  # Windows
        python_path = ".venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        python_path = ".venv/bin/python"

    if run_command(f"{python_path} -m pytest tests/ -v", "Running tests"):
        print("✅ All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False


def run_linting():
    """Run code linting."""

    # Determine the correct python path
    if os.name == "nt":  # Windows
        python_path = ".venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        python_path = ".venv/bin/python"

    linting_passed = True

    # Run black
    if not run_command(f"{python_path} -m black --check .", "Running black"):
        linting_passed = False

    # Run isort
    if not run_command(f"{python_path} -m isort --check-only .", "Running isort"):
        linting_passed = False

    # Run mypy
    if not run_command(f"{python_path} -m mypy app/", "Running mypy"):
        linting_passed = False

    if linting_passed:
        print("✅ All linting checks passed!")
    else:
        print("❌ Some linting checks failed!")

    return linting_passed


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/setup_dev.py [setup|test|lint|all]")
        return

    command = sys.argv[1].lower()

    if command == "setup":
        setup_environment()
    elif command == "test":
        run_tests()
    elif command == "lint":
        run_linting()
    elif command == "all":
        if setup_environment():
            run_linting()
            run_tests()
    else:
        print("Unknown command. Use: setup, test, lint, or all")


if __name__ == "__main__":
    main()
