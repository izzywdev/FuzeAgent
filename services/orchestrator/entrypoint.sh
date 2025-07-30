#!/bin/bash
set -e

echo "🚀 Starting FuzeAgent Orchestrator..."

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
python -c "
import asyncio
import asyncpg
import os
import time

async def wait_for_db():
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:password@postgres:5432/ai_context')
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = await asyncpg.connect(db_url)
            await conn.execute('SELECT 1')
            await conn.close()
            print('✅ Database connection successful!')
            return
        except Exception as e:
            retry_count += 1
            print(f'🔄 Database connection attempt {retry_count}/{max_retries} failed: {e}')
            if retry_count < max_retries:
                time.sleep(2)
            else:
                print('❌ Failed to connect to database after maximum retries')
                raise e

asyncio.run(wait_for_db())
"

# Run migrations if requested
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "🔄 Running database migrations..."
    python migrate.py up
    echo "✅ Migrations completed"
fi

# Check migration status
echo "📊 Checking migration status..."
python migrate.py status

# Start the application
echo "🎯 Starting API server..."
exec uvicorn main_with_hierarchy:app --host 0.0.0.0 --port 8000 --reload