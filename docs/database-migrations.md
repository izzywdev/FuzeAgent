# Database Migrations Guide

This guide covers the comprehensive database migration system implemented for FuzeAgent.

## Overview

The migration system provides:
- **Version Control**: Track schema changes with timestamped migrations
- **Rollback Support**: Safely revert changes when needed
- **Audit Logging**: Track all database changes automatically
- **Data Seeding**: Manage initial and reference data
- **Docker Integration**: Automatic migrations on container startup
- **CLI Tools**: Both Docker and standalone migration management

## Migration System Architecture

### Components

1. **MigrationManager** (`migration_manager.py`): Core migration engine
2. **Migration CLI** (`migrate.py`): Command-line interface for migrations
3. **Standalone CLI** (`migrate-cli.py`): Local development tool
4. **Docker Integration**: Automatic migrations via `entrypoint.sh`
5. **API Endpoints**: Runtime migration management via REST API

### Migration Files

Migrations are stored in `services/orchestrator/migrations/` with the naming convention:
```
YYYYMMDD_HHMMSS_description.py
```

Example: `20250129_120001_initial_schema.py`

## Usage

### Docker Environment (Automatic)

Migrations run automatically when the orchestrator container starts:

```bash
# Start with automatic migrations (default)
docker-compose up orchestrator

# Skip migrations on startup
RUN_MIGRATIONS=false docker-compose up orchestrator
```

### Standalone CLI (Local Development)

```bash
# Show migration status
python migrate-cli.py status

# Apply all pending migrations
python migrate-cli.py up

# Apply migrations up to specific version
python migrate-cli.py up 20250129_120003

# Rollback to specific version
python migrate-cli.py down 20250129_120001

# Create new migration
python migrate-cli.py create add_user_preferences

# Reset database (DANGER!)
python migrate-cli.py reset
```

### Docker CLI

```bash
# Run migrations inside container
docker-compose exec orchestrator python migrate.py status
docker-compose exec orchestrator python migrate.py up
docker-compose exec orchestrator python migrate.py down 20250129_120002
```

### API Endpoints

```bash
# Get migration status
curl http://localhost:8000/migrations/status

# Apply pending migrations
curl -X POST http://localhost:8000/migrations/apply

# Rollback to version
curl -X POST http://localhost:8000/migrations/rollback/20250129_120001
```

## Creating Migrations

### Using the CLI

```bash
python migrate-cli.py create add_user_settings
```

This creates a new migration file with the template:

```python
"""
Migration: add_user_settings
Created: 2025-01-29T15:30:00
"""

async def upgrade(conn):
    """Apply the migration"""
    await conn.execute("""
        CREATE TABLE user_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            settings JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ Created user_settings table")

async def downgrade(conn):
    """Rollback the migration"""
    await conn.execute("DROP TABLE IF EXISTS user_settings CASCADE;")
    print("✅ Dropped user_settings table")
```

### Best Practices

1. **Atomic Operations**: Each migration should be a single logical change
2. **Reversible**: Always implement both `upgrade()` and `downgrade()`
3. **Data Safety**: Use transactions for complex operations
4. **Testing**: Test both upgrade and downgrade paths
5. **Dependencies**: Consider foreign key constraints and data dependencies

## Available Migrations

### Current Schema Migrations

1. **20250129_120001_initial_schema.py**
   - Creates base tables: organizations, teams, agents, tasks, interactions
   - Establishes primary key and foreign key relationships
   - Enables vector extension for AI embeddings

2. **20250129_120002_add_indexes.py**
   - Adds performance indexes for common queries
   - Creates vector search index for embeddings
   - Establishes unique constraints

3. **20250129_120003_seed_initial_data.py**
   - Seeds default organization and team
   - Creates sample IzzyAI CEO agent
   - Provides consistent default IDs for testing

4. **20250129_120004_add_audit_logs.py**
   - Creates audit logging system
   - Implements automatic change tracking triggers
   - Tracks INSERT/UPDATE/DELETE operations

## Migration States and Tracking

### Schema Migrations Table

The system automatically creates a `schema_migrations` table:

```sql
CREATE TABLE schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64),
    execution_time_ms INTEGER
);
```

### Migration Status

```bash
python migrate-cli.py status
```

Example output:
```
🔍 Checking migration status...
📊 Migration Status:
   Total migrations: 4
   Applied: 4
   Pending: 0
   Last applied: 20250129_120004_add_audit_logs (2025-01-29 12:05:23)

✅ Database is up to date!
```

## Rollback Strategy

### Safe Rollback

```bash
# Rollback to previous version
python migrate-cli.py down 20250129_120003
```

### Rollback Considerations

1. **Data Loss**: Rollbacks may cause data loss - always backup first
2. **Dependencies**: Consider foreign key constraints
3. **Production**: Never rollback in production without proper planning
4. **Testing**: Test rollback procedures in staging environment

## Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql://postgres:password@localhost:5434/ai_context

# Migrations directory (optional)
MIGRATIONS_DIR=/custom/path/to/migrations

# Docker: Skip automatic migrations
RUN_MIGRATIONS=false
```

## Production Deployment

### Recommended Workflow

1. **Staging**: Test migrations in staging environment
2. **Backup**: Always backup production database before migrations
3. **Maintenance Mode**: Consider enabling maintenance mode during migrations
4. **Monitoring**: Monitor migration execution and performance
5. **Rollback Plan**: Have a tested rollback strategy ready

### CI/CD Integration

```yaml
# Example GitHub Actions workflow
- name: Run Database Migrations
  run: |
    python migrate-cli.py status
    python migrate-cli.py up
    python migrate-cli.py status
```

## Troubleshooting

### Common Issues

1. **Connection Failures**: Check DATABASE_URL and network connectivity
2. **Permission Errors**: Ensure database user has necessary privileges
3. **Migration Conflicts**: Resolve version conflicts manually
4. **Rollback Failures**: Check for data dependencies and foreign keys

### Debug Mode

```bash
# Enable verbose logging
PYTHONPATH=services/orchestrator python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from migrate import main
import asyncio
asyncio.run(main())
"
```

### Manual Recovery

```sql
-- Check migration status manually
SELECT * FROM schema_migrations ORDER BY version;

-- Manually mark migration as applied (emergency only)
INSERT INTO schema_migrations (version, name) 
VALUES ('20250129_120001', 'initial_schema');

-- Remove failed migration record
DELETE FROM schema_migrations WHERE version = '20250129_120005';
```

## Advanced Features

### Audit Logging

Automatic change tracking for organizations, teams, and agents:

```sql
-- View audit log
SELECT * FROM audit_logs 
WHERE table_name = 'agents' 
ORDER BY changed_at DESC 
LIMIT 10;
```

### Custom Migration Hooks

```python
async def upgrade(conn):
    """Migration with custom validation"""
    
    # Pre-migration validation
    count = await conn.fetchval("SELECT COUNT(*) FROM agents")
    if count > 1000:
        raise Exception("Too many agents for migration")
    
    # Apply changes
    await conn.execute("ALTER TABLE agents ADD COLUMN new_field VARCHAR(100);")
    
    # Post-migration data update
    await conn.execute("UPDATE agents SET new_field = 'default' WHERE new_field IS NULL;")
    
    print(f"✅ Updated {count} agent records")
```

## Security Considerations

1. **Permissions**: Migration user should have DDL privileges
2. **Backups**: Always backup before schema changes
3. **Validation**: Validate migration scripts before deployment
4. **Audit Trail**: All changes are logged automatically
5. **Access Control**: Restrict migration execution to authorized personnel

## Monitoring and Alerting

### Performance Metrics

- Migration execution time (stored in `schema_migrations.execution_time_ms`)
- Database size changes
- Index rebuild times
- Lock duration during DDL operations

### Alerting

Set up alerts for:
- Long-running migrations (> 5 minutes)
- Migration failures
- Unexpected rollbacks
- Large numbers of pending migrations

This migration system provides a robust, production-ready solution for managing database schema changes in FuzeAgent.