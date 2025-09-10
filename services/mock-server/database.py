"""
Database configuration and session management for FuzeAgent Mock Server
"""
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

# Database URL - defaults to PostgreSQL with FuzeAgentMock schema
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://ariWeinberg:ariWeinberg@172.17.0.2:5432/ariWeinberg"
)

# Create engine with schema support
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,  # Set to True for SQL debugging
    connect_args={
        "options": "-csearch_path=FuzeAgentMock,public"
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# Metadata for schema operations
metadata = MetaData(schema="FuzeAgentMock")

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
    from . import models
    Base.metadata.create_all(bind=engine)

def drop_all_tables():
    """Drop all tables (for testing/reset)"""
    Base.metadata.drop_all(bind=engine)
