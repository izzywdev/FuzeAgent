#!/usr/bin/env python3
"""
Script to create database tables for the mock server
"""
import os
import sys
sys.path.append('services/mock-server')

from services.mock-server.database import engine
from services.mock-server import models

def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    
    # Create all tables
    models.Base.metadata.create_all(bind=engine)
    
    print("✅ Database tables created successfully!")
    print("Tables created:")
    for table_name in models.Base.metadata.tables.keys():
        print(f"  - {table_name}")

if __name__ == "__main__":
    create_tables()
