#!/usr/bin/env python3
"""
Script to set up the database schema and tables
"""
import os
import sys

# Set the database URL
os.environ['DATABASE_URL'] = 'postgresql://ariWeinberg:StrongPassword123@172.17.0.2:5432/ariWeinberg'

# Add the mock-server directory to the path
sys.path.append('services/mock-server')

try:
    from database import engine
    from models import Base
    
    print("Setting up database...")
    
    # Create the schema first
    with engine.connect() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS \"FuzeAgentMock\";")
        conn.commit()
        print("✅ Schema 'FuzeAgentMock' created")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database tables created successfully!")
    print("Tables created:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")
        
except Exception as e:
    print(f"❌ Error setting up database: {e}")
    sys.exit(1)
