"""
Database configuration and session management for FuzeAgent Backend Service
"""
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Generator

# Database URL from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/fuzeagent"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,  # Set to True for SQL debugging
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# Metadata for schema operations
metadata = MetaData()

def get_db() -> Generator:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    # Import all models to ensure they are registered
    try:
        from . import models
        base = models.Base
    except ImportError:
        import models
        base = models.Base
    
    base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
    print(f"Created {len(base.metadata.tables)} tables")
    for table_name in base.metadata.tables.keys():
        print(f"  - {table_name}")

def drop_all_tables():
    """Drop all tables (for testing/reset)"""
    try:
        from . import models
        base = models.Base
    except ImportError:
        import models
        base = models.Base
    
    base.metadata.drop_all(bind=engine)
    print("✅ All tables dropped successfully!")

def reset_db():
    """Drop all tables and recreate them"""
    print("Resetting database...")
    drop_all_tables()
    init_db()
