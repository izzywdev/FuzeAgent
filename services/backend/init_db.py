#!/usr/bin/env python3
"""
Database initialization script for FuzeAgent Backend Service
Run this script to create all database tables based on the schema
"""
import os
import sys

# Get the database URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/fuzeagent"
)

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database import engine
    import models  # Import to register models
    from database import init_db
    
    print("=" * 60)
    print("FuzeAgent Backend - Database Initialization")
    print("=" * 60)
    print(f"Database URL: {DATABASE_URL}")
    print("")
    
    # Initialize database
    init_db()
    
    print("")
    print("=" * 60)
    print("✅ Database initialization completed successfully!")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error initializing database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
