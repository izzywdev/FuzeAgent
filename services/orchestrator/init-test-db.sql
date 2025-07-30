-- Initialize test database with required extensions and settings

-- Enable vector extension for RAG functionality
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID extension for ID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone for consistent test results
SET timezone = 'UTC';

-- Create test user if needed (optional)
-- CREATE USER test_user WITH PASSWORD 'test_password';
-- GRANT ALL PRIVILEGES ON DATABASE ai_context_test TO test_user;