"""
Database backup and recovery procedures for the Upwork Automation System
"""
import asyncio
import os
import subprocess
import shutil
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.utils import setup_logging

logger = setup_logging("database.backup")


class DatabaseBackupManager:
    """Manages database backup and recovery operations"""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Parse database URL for connection details
        self.db_config = self._parse_database_url(settings.database_url)
    
    def _parse_database_url(self, url: str) -> Dict[str, str]:
        """Parse database URL into connection components"""
        # postgresql://user:password@host:port/database
        if url.startswith("postgresql://"):
            url = url[13:]  # Remove postgresql://
        
        if "@" in url:
            auth, host_db = url.split("@", 1)
            if ":" in auth:
                user, password = auth.split(":", 1)
            else:
                user, password = auth, ""
        else:
            user, password = "", ""
            host_db = url
        
        if "/" in host_db:
            host_port, database = host_db.rsplit("/", 1)
        else:
            host_port, database = host_db, ""
        
        if ":" in host_port:
            host, port = host_port.split(":", 1)
        else:
            host, port = host_port, "5432"
        
        return {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database
        }
    
    async def create_backup(self, backup_type: str = "full", compress: bool = True) -> Dict[str, str]:
        """Create a database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"upwork_automation_{backup_type}_{timestamp}"
        
        if backup_type == "full":
            return await self._create_full_backup(backup_name, compress)
        elif backup_type == "schema":
            return await self._create_schema_backup(backup_name, compress)
        elif backup_type == "data":
            return await self._create_data_backup(backup_name, compress)
        else:
            raise ValueError(f"Unknown backup type: {backup_type}")
    
    async def _create_full_backup(self, backup_name: str, compress: bool) -> Dict[str, str]:
        """Create a full database backup using pg_dump"""
        backup_file = self.backup_dir / f"{backup_name}.sql"
        
        # Build pg_dump command
        cmd = [
            "pg_dump",
            f"--host={self.db_config['host']}",
            f"--port={self.db_config['port']}",
            f"--username={self.db_config['user']}",
            "--verbose",
            "--clean",
            "--if-exists",
            "--create",
            "--format=plain",
            f"--file={backup_file}",
            self.db_config['database']
        ]
        
        # Set password environment variable
        env = os.environ.copy()
        if self.db_config['password']:
            env['PGPASSWORD'] = self.db_config['password']
        
        try:
            logger.info(f"Creating full backup: {backup_name}")
            
            # Run pg_dump
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"pg_dump failed: {error_msg}")
            
            # Compress if requested
            final_file = backup_file
            if compress:
                final_file = await self._compress_file(backup_file)
                backup_file.unlink()  # Remove uncompressed file
            
            # Get file size
            file_size = final_file.stat().st_size
            
            # Create metadata
            metadata = {
                "backup_name": backup_name,
                "backup_type": "full",
                "file_path": str(final_file),
                "file_size": file_size,
                "compressed": compress,
                "created_at": datetime.now().isoformat(),
                "database": self.db_config['database'],
                "pg_dump_version": await self._get_pg_dump_version()
            }
            
            # Save metadata
            metadata_file = final_file.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Full backup created: {final_file} ({file_size:,} bytes)")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to create full backup: {e}")
            # Cleanup on failure
            if backup_file.exists():
                backup_file.unlink()
            raise
    
    async def _create_schema_backup(self, backup_name: str, compress: bool) -> Dict[str, str]:
        """Create a schema-only backup"""
        backup_file = self.backup_dir / f"{backup_name}_schema.sql"
        
        cmd = [
            "pg_dump",
            f"--host={self.db_config['host']}",
            f"--port={self.db_config['port']}",
            f"--username={self.db_config['user']}",
            "--schema-only",
            "--verbose",
            "--clean",
            "--if-exists",
            "--create",
            f"--file={backup_file}",
            self.db_config['database']
        ]
        
        env = os.environ.copy()
        if self.db_config['password']:
            env['PGPASSWORD'] = self.db_config['password']
        
        try:
            logger.info(f"Creating schema backup: {backup_name}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"pg_dump schema failed: {error_msg}")
            
            final_file = backup_file
            if compress:
                final_file = await self._compress_file(backup_file)
                backup_file.unlink()
            
            file_size = final_file.stat().st_size
            
            metadata = {
                "backup_name": backup_name,
                "backup_type": "schema",
                "file_path": str(final_file),
                "file_size": file_size,
                "compressed": compress,
                "created_at": datetime.now().isoformat(),
                "database": self.db_config['database']
            }
            
            metadata_file = final_file.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Schema backup created: {final_file}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to create schema backup: {e}")
            if backup_file.exists():
                backup_file.unlink()
            raise
    
    async def _create_data_backup(self, backup_name: str, compress: bool) -> Dict[str, str]:
        """Create a data-only backup"""
        backup_file = self.backup_dir / f"{backup_name}_data.sql"
        
        cmd = [
            "pg_dump",
            f"--host={self.db_config['host']}",
            f"--port={self.db_config['port']}",
            f"--username={self.db_config['user']}",
            "--data-only",
            "--verbose",
            "--disable-triggers",
            f"--file={backup_file}",
            self.db_config['database']
        ]
        
        env = os.environ.copy()
        if self.db_config['password']:
            env['PGPASSWORD'] = self.db_config['password']
        
        try:
            logger.info(f"Creating data backup: {backup_name}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"pg_dump data failed: {error_msg}")
            
            final_file = backup_file
            if compress:
                final_file = await self._compress_file(backup_file)
                backup_file.unlink()
            
            file_size = final_file.stat().st_size
            
            metadata = {
                "backup_name": backup_name,
                "backup_type": "data",
                "file_path": str(final_file),
                "file_size": file_size,
                "compressed": compress,
                "created_at": datetime.now().isoformat(),
                "database": self.db_config['database']
            }
            
            metadata_file = final_file.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Data backup created: {final_file}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to create data backup: {e}")
            if backup_file.exists():
                backup_file.unlink()
            raise
    
    async def restore_backup(self, backup_path: str, restore_type: str = "full") -> bool:
        """Restore a database backup"""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        # Decompress if needed
        if backup_file.suffix == '.gz':
            decompressed_file = await self._decompress_file(backup_file)
            sql_file = decompressed_file
            cleanup_decompressed = True
        else:
            sql_file = backup_file
            cleanup_decompressed = False
        
        try:
            logger.info(f"Restoring backup: {backup_path}")
            
            if restore_type == "full":
                success = await self._restore_full_backup(sql_file)
            elif restore_type == "schema":
                success = await self._restore_schema_backup(sql_file)
            elif restore_type == "data":
                success = await self._restore_data_backup(sql_file)
            else:
                raise ValueError(f"Unknown restore type: {restore_type}")
            
            if success:
                logger.info(f"Backup restored successfully: {backup_path}")
            else:
                logger.error(f"Failed to restore backup: {backup_path}")
            
            return success
            
        finally:
            # Cleanup decompressed file if we created it
            if cleanup_decompressed and sql_file.exists():
                sql_file.unlink()
    
    async def _restore_full_backup(self, sql_file: Path) -> bool:
        """Restore a full backup using psql"""
        cmd = [
            "psql",
            f"--host={self.db_config['host']}",
            f"--port={self.db_config['port']}",
            f"--username={self.db_config['user']}",
            "--verbose",
            f"--file={sql_file}",
            self.db_config['database']
        ]
        
        env = os.environ.copy()
        if self.db_config['password']:
            env['PGPASSWORD'] = self.db_config['password']
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"psql restore failed: {error_msg}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore full backup: {e}")
            return False
    
    async def _restore_schema_backup(self, sql_file: Path) -> bool:
        """Restore a schema backup"""
        return await self._restore_full_backup(sql_file)
    
    async def _restore_data_backup(self, sql_file: Path) -> bool:
        """Restore a data backup"""
        return await self._restore_full_backup(sql_file)
    
    async def _compress_file(self, file_path: Path) -> Path:
        """Compress a file using gzip"""
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        
        with open(file_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return compressed_path
    
    async def _decompress_file(self, file_path: Path) -> Path:
        """Decompress a gzipped file"""
        if not file_path.suffix == '.gz':
            return file_path
        
        decompressed_path = file_path.with_suffix('')
        
        with gzip.open(file_path, 'rb') as f_in:
            with open(decompressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return decompressed_path
    
    async def _get_pg_dump_version(self) -> str:
        """Get pg_dump version"""
        try:
            process = await asyncio.create_subprocess_exec(
                "pg_dump", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                return "unknown"
                
        except Exception:
            return "unknown"
    
    def list_backups(self) -> List[Dict[str, str]]:
        """List all available backups"""
        backups = []
        
        for metadata_file in self.backup_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                backups.append(metadata)
            except Exception as e:
                logger.warning(f"Failed to read backup metadata {metadata_file}: {e}")
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return backups
    
    def cleanup_old_backups(self, keep_days: int = 30, keep_count: int = 10) -> int:
        """Clean up old backup files"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        backups = self.list_backups()
        
        # Keep the most recent backups regardless of age
        backups_to_keep = backups[:keep_count]
        backups_to_check = backups[keep_count:]
        
        deleted_count = 0
        
        for backup in backups_to_check:
            try:
                created_at = datetime.fromisoformat(backup['created_at'])
                
                if created_at < cutoff_date:
                    # Delete backup file and metadata
                    backup_file = Path(backup['file_path'])
                    metadata_file = backup_file.with_suffix('.json')
                    
                    if backup_file.exists():
                        backup_file.unlink()
                    if metadata_file.exists():
                        metadata_file.unlink()
                    
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {backup['backup_name']}")
                    
            except Exception as e:
                logger.warning(f"Failed to delete backup {backup.get('backup_name')}: {e}")
        
        logger.info(f"Cleaned up {deleted_count} old backups")
        return deleted_count
    
    async def verify_backup(self, backup_path: str) -> Dict[str, any]:
        """Verify backup integrity"""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            return {"valid": False, "error": "Backup file not found"}
        
        try:
            # Check if file is readable
            file_size = backup_file.stat().st_size
            
            if file_size == 0:
                return {"valid": False, "error": "Backup file is empty"}
            
            # If compressed, try to decompress
            if backup_file.suffix == '.gz':
                try:
                    with gzip.open(backup_file, 'rt') as f:
                        # Read first few lines to verify it's a valid SQL dump
                        first_lines = [f.readline() for _ in range(5)]
                except Exception as e:
                    return {"valid": False, "error": f"Failed to decompress backup: {e}"}
            else:
                with open(backup_file, 'r') as f:
                    first_lines = [f.readline() for _ in range(5)]
            
            # Check if it looks like a PostgreSQL dump
            content = ''.join(first_lines).lower()
            if 'postgresql' not in content and 'pg_dump' not in content:
                return {"valid": False, "error": "File does not appear to be a PostgreSQL dump"}
            
            # Load metadata if available
            metadata_file = backup_file.with_suffix('.json')
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            
            return {
                "valid": True,
                "file_size": file_size,
                "metadata": metadata,
                "first_lines": first_lines[:3]  # Return first 3 lines for inspection
            }
            
        except Exception as e:
            return {"valid": False, "error": f"Verification failed: {e}"}


# Convenience functions
async def create_backup(backup_type: str = "full", compress: bool = True) -> Dict[str, str]:
    """Create a database backup"""
    manager = DatabaseBackupManager()
    return await manager.create_backup(backup_type, compress)


async def restore_backup(backup_path: str, restore_type: str = "full") -> bool:
    """Restore a database backup"""
    manager = DatabaseBackupManager()
    return await manager.restore_backup(backup_path, restore_type)


def list_backups() -> List[Dict[str, str]]:
    """List all available backups"""
    manager = DatabaseBackupManager()
    return manager.list_backups()


def cleanup_old_backups(keep_days: int = 30, keep_count: int = 10) -> int:
    """Clean up old backup files"""
    manager = DatabaseBackupManager()
    return manager.cleanup_old_backups(keep_days, keep_count)


async def verify_backup(backup_path: str) -> Dict[str, any]:
    """Verify backup integrity"""
    manager = DatabaseBackupManager()
    return await manager.verify_backup(backup_path)