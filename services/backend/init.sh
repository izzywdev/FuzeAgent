#!/bin/bash
set -e

echo "🔧 Initializing FuzeAgent Backend Service..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -U postgres -d fuzeagent; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "✅ PostgreSQL is ready and 'fuzeagent' database exists!"

# Start the application
echo "🚀 Starting FastAPI application..."
exec python main.py
