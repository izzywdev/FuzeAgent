-- Create database if it doesn't exist
SELECT 'CREATE DATABASE fuzeagent'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'fuzeagent')\gexec
