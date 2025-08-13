# Database Module

This module provides comprehensive database functionality for the Upwork Automation System, including ORM models, connection management, performance optimization, backup/recovery, and migration support.

## Components

### 1. Connection Management (`connection.py`)
- Async PostgreSQL connection with optimized pooling
- Health monitoring and automatic recovery
- Connection pool statistics and management
- Background health monitoring task

### 2. ORM Models (`models.py`)
- SQLAlchemy async models for all data entities
- Proper relationships and constraints
- Performance-optimized indexes
- Enum support for status fields

### 3. Database Schema (`init.sql`)
- Complete PostgreSQL schema definition
- Proper indexes for performance
- Default system configuration
- Trigger functions for automatic timestamps

### 4. Migration Support (`alembic/`)
- Alembic configuration for database versioning
- Initial migration script
- Support for schema evolution

### 5. Performance Optimization (`indexes.py`)
- Advanced performance indexes
- Table statistics analysis
- Query performance monitoring
- Database optimization utilities

### 6. Backup & Recovery (`backup.py`)
- Automated backup creation (full, schema, data)
- Backup compression and metadata
- Restore functionality
- Backup verification and cleanup

### 7. Database CLI (`cli.py`)
- Command-line interface for database management
- Health checks and monitoring
- Backup/restore operations
- Index management
- Migration support

## Usage

### Basic Setup

```python
from api.database.connection import init_db, get_db
from api.database.models import JobModel, ProposalModel

# Initialize database
await init_db()

# Use database session
async with get_db() as session:
    job = JobModel(title="Test Job", ...)
    session.add(job)
    await session.commit()
```

### Health Monitoring

```python
from api.database.connection import check_db_health, health_monitor

# Check database health
health = await check_db_health()
print(f"Database healthy: {health['healthy']}")

# Start background monitoring
await health_monitor.start()
```

### Performance Optimization

```python
from api.database.indexes import optimize_database

async with get_db() as session:
    # Run full optimization
    stats = await optimize_database(session)
    print(f"Optimized {len(stats['tables'])} tables")
```

### Backup Operations

```python
from api.database.backup import create_backup, restore_backup

# Create backup
metadata = await create_backup("full", compress=True)
print(f"Backup created: {metadata['file_path']}")

# Restore backup
success = await restore_backup("backup_file.sql.gz", "full")
```

## CLI Usage

The database CLI provides convenient command-line access to all database operations:

```bash
# Initialize database
python api/database/cli.py init

# Check health
python api/database/cli.py health

# Create performance indexes
python api/database/cli.py indexes create

# Create backup
python api/database/cli.py backup create-backup --type full

# List backups
python api/database/cli.py backup list-backups

# Run migrations
python api/database/cli.py migrate

# Optimize database
python api/database/cli.py indexes optimize
```

## Configuration

Database configuration is managed through environment variables:

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/upwork_automation
DEBUG=false
```

## Performance Features

### Connection Pooling
- Pool size: 20 connections
- Max overflow: 30 connections
- Connection recycling: 1 hour
- Pre-ping health checks

### Indexes
- Composite indexes for common queries
- GIN indexes for array and full-text search
- Partial indexes for filtered queries
- Regular VACUUM and ANALYZE operations

### Monitoring
- Real-time connection pool statistics
- Query performance tracking
- Health check monitoring
- Automatic error recovery

## Backup Strategy

### Backup Types
- **Full**: Complete database with schema and data
- **Schema**: Structure only (tables, indexes, constraints)
- **Data**: Data only (useful for migrations)

### Backup Features
- Automatic compression
- Metadata tracking
- Integrity verification
- Automated cleanup of old backups

### Recovery
- Point-in-time recovery support
- Selective restore options
- Backup verification before restore

## Testing

Run the database integration tests:

```bash
pytest tests/test_database_integration.py -v
```

Tests cover:
- Connection management
- CRUD operations for all models
- Transaction handling
- Concurrent access
- Index performance
- Backup/restore functionality

## Migration Management

### Creating Migrations

```bash
# Auto-generate migration from model changes
python api/database/cli.py create-migration -m "Add new field to jobs table"

# Run migrations
python api/database/cli.py migrate
```

### Manual Migrations

For complex changes, create manual migrations in `alembic/versions/`:

```python
def upgrade() -> None:
    # Add custom migration logic
    op.execute("CREATE INDEX CONCURRENTLY ...")

def downgrade() -> None:
    # Add rollback logic
    op.execute("DROP INDEX ...")
```

## Troubleshooting

### Connection Issues
```bash
# Check database health
python api/database/cli.py health

# Reset connection pool
python api/database/cli.py reset-pool-cmd
```

### Performance Issues
```bash
# Analyze table statistics
python api/database/cli.py indexes analyze

# Run optimization
python api/database/cli.py indexes optimize
```

### Backup Issues
```bash
# Verify backup integrity
python api/database/cli.py backup verify backup_file.sql.gz

# List available backups
python api/database/cli.py backup list-backups
```

## Security Considerations

- Database credentials stored in environment variables
- Connection encryption in production
- Regular security updates for PostgreSQL
- Backup encryption for sensitive data
- Access logging and monitoring

## Monitoring and Alerting

The database module provides comprehensive monitoring:

- Connection pool health
- Query performance metrics
- Backup success/failure tracking
- Disk space monitoring
- Error rate tracking

Set up alerts for:
- Database connection failures
- High connection pool usage
- Slow query performance
- Backup failures
- Disk space issues