"""
Database performance indexes and optimization utilities
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils import setup_logging

logger = setup_logging("database.indexes")


class DatabaseIndexManager:
    """Manages database indexes for performance optimization"""
    
    # Additional performance indexes beyond the basic ones in models
    PERFORMANCE_INDEXES = [
        # Jobs table performance indexes
        {
            "name": "idx_jobs_composite_search",
            "table": "jobs",
            "columns": ["status", "job_type", "hourly_rate", "client_rating"],
            "description": "Composite index for job search queries"
        },
        {
            "name": "idx_jobs_posted_date_desc",
            "table": "jobs",
            "columns": ["posted_date DESC"],
            "description": "Index for sorting jobs by posted date (newest first)"
        },
        {
            "name": "idx_jobs_match_score_desc",
            "table": "jobs",
            "columns": ["match_score DESC NULLS LAST"],
            "description": "Index for sorting jobs by match score"
        },
        {
            "name": "idx_jobs_skills_gin",
            "table": "jobs",
            "columns": ["skills_required"],
            "type": "GIN",
            "description": "GIN index for array search on skills"
        },
        {
            "name": "idx_jobs_title_text_search",
            "table": "jobs",
            "columns": ["to_tsvector('english', title)"],
            "type": "GIN",
            "description": "Full-text search index on job titles"
        },
        
        # Proposals table performance indexes
        {
            "name": "idx_proposals_job_status_created",
            "table": "proposals",
            "columns": ["job_id", "status", "created_at DESC"],
            "description": "Composite index for proposal queries by job and status"
        },
        {
            "name": "idx_proposals_bid_amount",
            "table": "proposals",
            "columns": ["bid_amount"],
            "description": "Index for bid amount analysis"
        },
        
        # Applications table performance indexes
        {
            "name": "idx_applications_submitted_date",
            "table": "applications",
            "columns": ["submitted_at DESC NULLS LAST"],
            "description": "Index for sorting applications by submission date"
        },
        {
            "name": "idx_applications_status_date",
            "table": "applications",
            "columns": ["status", "submitted_at DESC"],
            "description": "Composite index for application status queries"
        },
        {
            "name": "idx_applications_hired_date",
            "table": "applications",
            "columns": ["hired", "hire_date DESC NULLS LAST"],
            "description": "Index for tracking successful hires"
        },
        
        # Task queue performance indexes
        {
            "name": "idx_task_queue_processing",
            "table": "task_queue",
            "columns": ["status", "priority DESC", "scheduled_at"],
            "description": "Composite index for task queue processing"
        },
        {
            "name": "idx_task_queue_retry",
            "table": "task_queue",
            "columns": ["status", "retry_count", "max_retries"],
            "description": "Index for retry logic queries"
        },
        
        # Performance metrics indexes
        {
            "name": "idx_performance_metrics_composite",
            "table": "performance_metrics",
            "columns": ["metric_type", "time_period", "date_recorded DESC"],
            "description": "Composite index for metrics queries"
        },
        
        # Browser sessions indexes
        {
            "name": "idx_browser_sessions_active",
            "table": "browser_sessions",
            "columns": ["status", "session_type", "last_used_at DESC"],
            "description": "Index for finding active browser sessions"
        },
        {
            "name": "idx_browser_sessions_cleanup",
            "table": "browser_sessions",
            "columns": ["status", "expires_at"],
            "description": "Index for session cleanup queries"
        }
    ]
    
    @classmethod
    async def create_performance_indexes(cls, session: AsyncSession):
        """Create all performance indexes"""
        logger.info("Creating performance indexes...")
        
        created_count = 0
        skipped_count = 0
        
        for index_def in cls.PERFORMANCE_INDEXES:
            try:
                if await cls._index_exists(session, index_def["name"]):
                    logger.debug(f"Index {index_def['name']} already exists, skipping")
                    skipped_count += 1
                    continue
                
                await cls._create_index(session, index_def)
                created_count += 1
                logger.info(f"Created index: {index_def['name']}")
                
            except Exception as e:
                logger.error(f"Failed to create index {index_def['name']}: {e}")
        
        logger.info(f"Performance indexes created: {created_count}, skipped: {skipped_count}")
    
    @classmethod
    async def drop_performance_indexes(cls, session: AsyncSession):
        """Drop all performance indexes"""
        logger.info("Dropping performance indexes...")
        
        dropped_count = 0
        
        for index_def in cls.PERFORMANCE_INDEXES:
            try:
                if not await cls._index_exists(session, index_def["name"]):
                    continue
                
                await session.execute(text(f"DROP INDEX IF EXISTS {index_def['name']}"))
                dropped_count += 1
                logger.info(f"Dropped index: {index_def['name']}")
                
            except Exception as e:
                logger.error(f"Failed to drop index {index_def['name']}: {e}")
        
        await session.commit()
        logger.info(f"Performance indexes dropped: {dropped_count}")
    
    @classmethod
    async def _create_index(cls, session: AsyncSession, index_def: dict):
        """Create a single index"""
        index_type = index_def.get("type", "BTREE")
        columns = ", ".join(index_def["columns"])
        
        if index_type == "GIN":
            sql = f"CREATE INDEX {index_def['name']} ON {index_def['table']} USING GIN ({columns})"
        else:
            sql = f"CREATE INDEX {index_def['name']} ON {index_def['table']} ({columns})"
        
        await session.execute(text(sql))
        await session.commit()
    
    @classmethod
    async def _index_exists(cls, session: AsyncSession, index_name: str) -> bool:
        """Check if an index exists"""
        result = await session.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = :index_name
            )
        """), {"index_name": index_name})
        
        return result.scalar()
    
    @classmethod
    async def analyze_table_stats(cls, session: AsyncSession, table_name: str = None) -> dict:
        """Analyze table statistics for performance monitoring"""
        if table_name:
            # Analyze specific table
            await session.execute(text(f"ANALYZE {table_name}"))
            
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation
                FROM pg_stats 
                WHERE tablename = :table_name
                ORDER BY tablename, attname
            """), {"table_name": table_name})
            
            stats = result.fetchall()
            return {
                "table": table_name,
                "columns": [
                    {
                        "schema": row[0],
                        "table": row[1],
                        "column": row[2],
                        "distinct_values": row[3],
                        "correlation": row[4]
                    }
                    for row in stats
                ]
            }
        else:
            # Analyze all tables
            await session.execute(text("ANALYZE"))
            
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                ORDER BY schemaname, tablename
            """))
            
            stats = result.fetchall()
            return {
                "tables": [
                    {
                        "schema": row[0],
                        "table": row[1],
                        "inserts": row[2],
                        "updates": row[3],
                        "deletes": row[4],
                        "live_tuples": row[5],
                        "dead_tuples": row[6],
                        "last_vacuum": row[7],
                        "last_autovacuum": row[8],
                        "last_analyze": row[9],
                        "last_autoanalyze": row[10]
                    }
                    for row in stats
                ]
            }
    
    @classmethod
    async def get_slow_queries(cls, session: AsyncSession, limit: int = 10) -> list:
        """Get slow queries from pg_stat_statements (if available)"""
        try:
            result = await session.execute(text("""
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    rows,
                    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                FROM pg_stat_statements
                ORDER BY total_time DESC
                LIMIT :limit
            """), {"limit": limit})
            
            queries = result.fetchall()
            return [
                {
                    "query": row[0],
                    "calls": row[1],
                    "total_time": row[2],
                    "mean_time": row[3],
                    "rows": row[4],
                    "hit_percent": row[5]
                }
                for row in queries
            ]
        except Exception as e:
            logger.warning(f"pg_stat_statements not available: {e}")
            return []
    
    @classmethod
    async def vacuum_analyze_all(cls, session: AsyncSession):
        """Run VACUUM ANALYZE on all tables"""
        logger.info("Running VACUUM ANALYZE on all tables...")
        
        # Get all user tables
        result = await session.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        
        tables = [row[0] for row in result.fetchall()]
        
        for table in tables:
            try:
                await session.execute(text(f"VACUUM ANALYZE {table}"))
                logger.debug(f"VACUUM ANALYZE completed for {table}")
            except Exception as e:
                logger.error(f"VACUUM ANALYZE failed for {table}: {e}")
        
        logger.info(f"VACUUM ANALYZE completed for {len(tables)} tables")


# Convenience functions
async def create_all_indexes(session: AsyncSession):
    """Create all performance indexes"""
    await DatabaseIndexManager.create_performance_indexes(session)


async def drop_all_indexes(session: AsyncSession):
    """Drop all performance indexes"""
    await DatabaseIndexManager.drop_performance_indexes(session)


async def optimize_database(session: AsyncSession):
    """Run full database optimization"""
    logger.info("Starting database optimization...")
    
    # Create performance indexes
    await DatabaseIndexManager.create_performance_indexes(session)
    
    # Run VACUUM ANALYZE
    await DatabaseIndexManager.vacuum_analyze_all(session)
    
    # Get table statistics
    stats = await DatabaseIndexManager.analyze_table_stats(session)
    logger.info(f"Analyzed {len(stats.get('tables', []))} tables")
    
    logger.info("Database optimization completed")
    return stats