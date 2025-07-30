#!/usr/bin/env python3
"""
Standalone Database Migration CLI for FuzeAgent

This script can be run outside of Docker for local development and CI/CD.

Usage:
    python migrate-cli.py --help
    python migrate-cli.py status
    python migrate-cli.py up
    python migrate-cli.py down 20250129_120002  
    python migrate-cli.py create add_user_preferences
    python migrate-cli.py reset

Environment Variables:
    DATABASE_URL - PostgreSQL connection string
    MIGRATIONS_DIR - Path to migrations directory (optional)
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the orchestrator directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent / "services" / "orchestrator"))

try:
    from migrate import main as migrate_main
except ImportError as e:
    print(f"❌ Failed to import migration modules: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

if __name__ == "__main__":
    # Set default database URL for local development
    if "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5434/ai_context"
    
    print("🔧 FuzeAgent Migration CLI")
    print(f"📍 Database: {os.environ.get('DATABASE_URL', 'Not set')}")
    print(f"📁 Migrations: {os.environ.get('MIGRATIONS_DIR', 'Using default')}")
    print("-" * 50)
    
    # Run the migration CLI
    asyncio.run(migrate_main())