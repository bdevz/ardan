#!/usr/bin/env python3
"""
Database management CLI for the Upwork Automation System
"""
import asyncio
import click
import json
from pathlib import Path

from connection import init_db, close_db, check_db_health, get_pool_stats, reset_pool
from indexes import DatabaseIndexManager, optimize_database
from backup import DatabaseBackupManager
from shared.utils import setup_logging

logger = setup_logging("database.cli")


@click.group()
def cli():
    """Database management commands for Upwork Automation System"""
    pass


@cli.command()
def init():
    """Initialize the database"""
    async def _init():
        try:
            await init_db()
            click.echo("✅ Database initialized successfully")
        except Exception as e:
            click.echo(f"❌ Failed to initialize database: {e}")
            raise click.Abort()
        finally:
            await close_db()
    
    asyncio.run(_init())


@cli.command()
def health():
    """Check database health"""
    async def _health():
        try:
            health_status = await check_db_health()
            
            if health_status["healthy"]:
                click.echo("✅ Database is healthy")
                click.echo(f"Response time: {health_status['response_time_ms']:.2f}ms")
                
                if "database_info" in health_status:
                    db_info = health_status["database_info"]
                    click.echo(f"Database: {db_info['name']}")
                    click.echo(f"User: {db_info['user']}")
                    click.echo(f"Version: {' '.join(db_info['version'])}")
            else:
                click.echo("❌ Database is unhealthy")
                if health_status.get("error"):
                    click.echo(f"Error: {health_status['error']}")
            
            # Show pool stats
            pool_stats = health_status.get("pool_stats", {})
            if pool_stats:
                click.echo("\n📊 Connection Pool Stats:")
                click.echo(f"  Active connections: {pool_stats.get('checked_out_connections', 0)}")
                click.echo(f"  Pool size limit: {pool_stats.get('pool_size_limit', 0)}")
                click.echo(f"  Max overflow: {pool_stats.get('max_overflow', 0)}")
                
        except Exception as e:
            click.echo(f"❌ Health check failed: {e}")
            raise click.Abort()
        finally:
            await close_db()
    
    asyncio.run(_health())


@cli.command()
def pool_stats():
    """Show connection pool statistics"""
    async def _pool_stats():
        try:
            stats = await get_pool_stats()
            
            click.echo("📊 Connection Pool Statistics:")
            click.echo(f"  Total connections: {stats.get('total_connections', 0)}")
            click.echo(f"  Active connections: {stats.get('checked_out_connections', 0)}")
            click.echo(f"  Overflow connections: {stats.get('overflow_connections', 0)}")
            click.echo(f"  Invalid connections: {stats.get('invalid_connections', 0)}")
            click.echo(f"  Pool size limit: {stats.get('pool_size_limit', 0)}")
            click.echo(f"  Max overflow: {stats.get('max_overflow', 0)}")
            click.echo(f"  Health check failures: {stats.get('health_check_failures', 0)}")
            
            if stats.get('last_health_check'):
                import time
                last_check = time.strftime('%Y-%m-%d %H:%M:%S', 
                                         time.localtime(stats['last_health_check']))
                click.echo(f"  Last health check: {last_check}")
                
        except Exception as e:
            click.echo(f"❌ Failed to get pool stats: {e}")
            raise click.Abort()
        finally:
            await close_db()
    
    asyncio.run(_pool_stats())


@cli.command()
def reset_pool_cmd():
    """Reset the connection pool"""
    async def _reset_pool():
        try:
            await reset_pool()
            click.echo("✅ Connection pool reset successfully")
        except Exception as e:
            click.echo(f"❌ Failed to reset pool: {e}")
            raise click.Abort()
    
    asyncio.run(_reset_pool())


@cli.group()
def indexes():
    """Database index management commands"""
    pass


@indexes.command()
def create():
    """Create performance indexes"""
    async def _create_indexes():
        try:
            from connection import get_db
            async with get_db() as session:
                await DatabaseIndexManager.create_performance_indexes(session)
            click.echo("✅ Performance indexes created successfully")
        except Exception as e:
            click.echo(f"❌ Failed to create indexes: {e}")
            raise click.Abort()
        finally:
            await close_db()
    
    asyncio.run(_create_indexes())


@indexes.command()
def drop():
    """Drop performance indexes"""
    async def _drop_indexes():
        try:
            from connection import get_db
            async with get_db() as session:
                await DatabaseIndexManager.drop_performance_indexes(session)
            click.echo("✅ Performance indexes dropped successfully")
        except Exception as e:
            click.echo(f"❌ Failed to drop indexes: {e}")
            raise click.Abort()
        finally:
            await close_db()
    
    asyncio.run(_drop_indexes())


@indexes.command()
@click.option('--table', help='Analyze specific table (default: all tables)')
def analyze(table):
    """Analyze table statistics"""
    async def _analyze():
        try:
            from connection import get_db
            async with get_db() as session:
                stats = await DatabaseIndexManager.analyze_table_stats(session, table)
            
            if table:
                click.echo(f"📊 Statistics for table '{table}':")
                for col in stats.get('columns', []):
                    click.echo(f"  {col['column']}: {col['distinct_values']} distinct values")
            else:
                click.echo("📊 Database Statistics:")
                for table_stat in stats.get('tables', []):
                    click.echo(f"  {table_stat['table']}: {table_stat['live_tuples']} live tuples")
                    
        except Exception as e:
            click.echo(f"❌ Failed to analyze: {e}")
            raise click.Abort()
        finally:
            await close_db()
    
    asyncio.run(_analyze())


@indexes.command()
def optimize():
    """Run full database optimization"""
    async def _optimize():
        try:
            from connection import get_db
            async with get_db() as session:
                stats = await optimize_database(session)
            click.echo("✅ Database optimization completed")
            
            if 'tables' in stats:
                click.echo(f"📊 Optimized {len(stats['tables'])} tables")
                
        except Exception as e:
            click.echo(f"❌ Failed to optimize database: {e}")
            raise click.Abort()
        finally:
            await close_db()
    
    asyncio.run(_optimize())


@cli.group()
def backup():
    """Database backup and recovery commands"""
    pass


@backup.command()
@click.option('--type', 'backup_type', default='full', 
              type=click.Choice(['full', 'schema', 'data']),
              help='Type of backup to create')
@click.option('--compress/--no-compress', default=True,
              help='Compress the backup file')
def create_backup(backup_type, compress):
    """Create a database backup"""
    async def _create_backup():
        try:
            manager = DatabaseBackupManager()
            metadata = await manager.create_backup(backup_type, compress)
            
            click.echo(f"✅ {backup_type.title()} backup created successfully")
            click.echo(f"📁 File: {metadata['file_path']}")
            click.echo(f"📏 Size: {metadata['file_size']:,} bytes")
            click.echo(f"🗜️ Compressed: {'Yes' if metadata['compressed'] else 'No'}")
            
        except Exception as e:
            click.echo(f"❌ Failed to create backup: {e}")
            raise click.Abort()
    
    asyncio.run(_create_backup())


@backup.command()
@click.argument('backup_path')
@click.option('--type', 'restore_type', default='full',
              type=click.Choice(['full', 'schema', 'data']),
              help='Type of restore to perform')
def restore(backup_path, restore_type):
    """Restore a database backup"""
    async def _restore():
        try:
            manager = DatabaseBackupManager()
            success = await manager.restore_backup(backup_path, restore_type)
            
            if success:
                click.echo(f"✅ {restore_type.title()} restore completed successfully")
            else:
                click.echo(f"❌ {restore_type.title()} restore failed")
                raise click.Abort()
                
        except Exception as e:
            click.echo(f"❌ Failed to restore backup: {e}")
            raise click.Abort()
    
    asyncio.run(_restore())


@backup.command()
def list_backups():
    """List available backups"""
    try:
        manager = DatabaseBackupManager()
        backups = manager.list_backups()
        
        if not backups:
            click.echo("No backups found")
            return
        
        click.echo("📋 Available Backups:")
        click.echo()
        
        for backup in backups:
            click.echo(f"  📁 {backup['backup_name']}")
            click.echo(f"     Type: {backup['backup_type']}")
            click.echo(f"     Size: {backup['file_size']:,} bytes")
            click.echo(f"     Created: {backup['created_at']}")
            click.echo(f"     File: {backup['file_path']}")
            click.echo()
            
    except Exception as e:
        click.echo(f"❌ Failed to list backups: {e}")
        raise click.Abort()


@backup.command()
@click.argument('backup_path')
def verify(backup_path):
    """Verify backup integrity"""
    async def _verify():
        try:
            manager = DatabaseBackupManager()
            result = await manager.verify_backup(backup_path)
            
            if result['valid']:
                click.echo("✅ Backup is valid")
                click.echo(f"📏 File size: {result['file_size']:,} bytes")
                
                if result.get('metadata'):
                    metadata = result['metadata']
                    click.echo(f"📋 Type: {metadata.get('backup_type', 'unknown')}")
                    click.echo(f"📅 Created: {metadata.get('created_at', 'unknown')}")
            else:
                click.echo("❌ Backup is invalid")
                click.echo(f"Error: {result['error']}")
                
        except Exception as e:
            click.echo(f"❌ Failed to verify backup: {e}")
            raise click.Abort()
    
    asyncio.run(_verify())


@backup.command()
@click.option('--keep-days', default=30, help='Keep backups newer than this many days')
@click.option('--keep-count', default=10, help='Keep this many recent backups regardless of age')
def cleanup(keep_days, keep_count):
    """Clean up old backup files"""
    try:
        manager = DatabaseBackupManager()
        deleted_count = manager.cleanup_old_backups(keep_days, keep_count)
        
        click.echo(f"✅ Cleaned up {deleted_count} old backups")
        click.echo(f"📅 Kept backups newer than {keep_days} days")
        click.echo(f"📊 Kept {keep_count} most recent backups")
        
    except Exception as e:
        click.echo(f"❌ Failed to cleanup backups: {e}")
        raise click.Abort()


@cli.command()
def migrate():
    """Run database migrations using Alembic"""
    try:
        import subprocess
        result = subprocess.run(['alembic', 'upgrade', 'head'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            click.echo("✅ Database migrations completed successfully")
            if result.stdout:
                click.echo(result.stdout)
        else:
            click.echo("❌ Database migrations failed")
            if result.stderr:
                click.echo(result.stderr)
            raise click.Abort()
            
    except FileNotFoundError:
        click.echo("❌ Alembic not found. Please install alembic: pip install alembic")
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Migration failed: {e}")
        raise click.Abort()


@cli.command()
@click.option('--message', '-m', required=True, help='Migration message')
def create_migration(message):
    """Create a new database migration"""
    try:
        import subprocess
        result = subprocess.run(['alembic', 'revision', '--autogenerate', '-m', message],
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            click.echo(f"✅ Migration created: {message}")
            if result.stdout:
                click.echo(result.stdout)
        else:
            click.echo("❌ Failed to create migration")
            if result.stderr:
                click.echo(result.stderr)
            raise click.Abort()
            
    except FileNotFoundError:
        click.echo("❌ Alembic not found. Please install alembic: pip install alembic")
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Failed to create migration: {e}")
        raise click.Abort()


if __name__ == '__main__':
    cli()