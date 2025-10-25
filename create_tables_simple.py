#!/usr/bin/env python3
"""
Simple script to create database tables
"""
import os
import sys

# Set the database URL
os.environ['DATABASE_URL'] = 'postgresql://ariWeinberg:ariWeinberg@172.17.0.2:5432/ariWeinberg'

# Add the mock-server directory to the path
sys.path.append('services/mock-server')

try:
    from database import engine
    from models import Base
    
    print("Creating database tables...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database tables created successfully!")
    print("Tables created:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")
        
except Exception as e:
    print(f"❌ Error creating tables: {e}")
    sys.exit(1)
