"""
CLI tool for managing the task queue
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from uuid import UUID

import click
from tabulate import tabulate

# Add the parent directory to the path so we can import from api modules
sys.path.append(str(Path(__file__).parent.parent))

from services.task_queue_service import task_queue_service
from services.task_scheduler import task_scheduler
from services.queue_metrics_service import queue_metrics_service


@click.group()
def cli():
    """Task Queue Management CLI"""
    pass


@cli.command()
@click.option('--task-type', required=True, help='Type of task to enqueue')
@click.option('--data', required=True, help='Task data as JSON string')
@click.option('--priority', default=0, help='Task priority (higher = more important)')
@click.option('--max-retries', default=3, help='Maximum number of retries')
def enqueue(task_type: str, data: str, priority: int, max_retries: int):
    """Enqueue a new task"""
    async def _enqueue():
        try:
            task_data = json.loads(data)
        except json.JSONDecodeError as e:
            click.echo(f"Error: Invalid JSON data - {str(e)}", err=True)
            return
        
        try:
            await task_queue_service.initialize()
            task_id = await task_queue_service.enqueue_task(
                task_type=task_type,
                task_data=task_data,
                priority=priority,
                max_retries=max_retries
            )
            click.echo(f"Task enqueued successfully with ID: {task_id}")
        except Exception as e:
            click.echo(f"Error enqueuing task: {str(e)}", err=True)
        finally:
            await task_queue_service.close()
    
    asyncio.run(_enqueue())


@cli.command()
@click.argument('task_id', type=str)
def status(task_id: str):
    """Get task status by ID"""
    async def _status():
        try:
            task_uuid = UUID(task_id)
        except ValueError:
            click.echo(f"Error: Invalid task ID format", err=True)
            return
        
        try:
            await task_queue_service.initialize()
            task = await task_queue_service.get_task_status(task_uuid)
            
            if not task:
                click.echo(f"Task {task_id} not found")
                return
            
            # Display task information
            click.echo(f"Task ID: {task.id}")
            click.echo(f"Type: {task.task_type}")
            click.echo(f"Status: {task.status}")
            click.echo(f"Priority: {task.priority}")
            click.echo(f"Created: {task.created_at}")
            click.echo(f"Scheduled: {task.scheduled_at}")
            click.echo(f"Started: {task.started_at}")
            click.echo(f"Completed: {task.completed_at}")
            click.echo(f"Retry Count: {task.retry_count}/{task.max_retries}")
            
            if task.error_message:
                click.echo(f"Error: {task.error_message}")
            
            if task.task_data:
                click.echo(f"Data: {json.dumps(task.task_data, indent=2)}")
                
        except Exception as e:
            click.echo(f"Error getting task status: {str(e)}", err=True)
        finally:
            await task_queue_service.close()
    
    asyncio.run(_status())


@cli.command()
@click.argument('task_id', type=str)
def cancel(task_id: str):
    """Cancel a pending task"""
    async def _cancel():
        try:
            task_uuid = UUID(task_id)
        except ValueError:
            click.echo(f"Error: Invalid task ID format", err=True)
            return
        
        try:
            await task_queue_service.initialize()
            success = await task_queue_service.cancel_task(task_uuid)
            
            if success:
                click.echo(f"Task {task_id} cancelled successfully")
            else:
                click.echo(f"Task {task_id} not found or cannot be cancelled")
                
        except Exception as e:
            click.echo(f"Error cancelling task: {str(e)}", err=True)
        finally:
            await task_queue_service.close()
    
    asyncio.run(_cancel())


@cli.command()
def stats():
    """Show queue statistics"""
    async def _stats():
        try:
            await task_queue_service.initialize()
            stats = await task_queue_service.get_queue_stats()
            
            # Display overall stats
            click.echo("=== Queue Statistics ===")
            click.echo(f"Total Pending: {stats['total_pending']}")
            click.echo(f"Total Processing: {stats['total_processing']}")
            click.echo(f"Total Completed: {stats['total_completed']}")
            click.echo(f"Total Failed: {stats['total_failed']}")
            click.echo(f"Scheduled Tasks: {stats['scheduled_tasks']}")
            
            # Display queue breakdown
            if stats['queues']:
                click.echo("\n=== Queue Breakdown ===")
                queue_data = [[queue, count] for queue, count in stats['queues'].items()]
                click.echo(tabulate(queue_data, headers=['Queue', 'Pending Tasks'], tablefmt='grid'))
                
        except Exception as e:
            click.echo(f"Error getting queue stats: {str(e)}", err=True)
        finally:
            await task_queue_service.close()
    
    asyncio.run(_stats())


@cli.command()
@click.option('--days', default=30, help='Delete tasks older than this many days')
def cleanup(days: int):
    """Clean up old completed/failed tasks"""
    async def _cleanup():
        try:
            await task_queue_service.initialize()
            cleaned_count = await task_queue_service.cleanup_old_tasks(days)
            click.echo(f"Cleaned up {cleaned_count} old tasks (older than {days} days)")
        except Exception as e:
            click.echo(f"Error cleaning up tasks: {str(e)}", err=True)
        finally:
            await task_queue_service.close()
    
    asyncio.run(_cleanup())


@cli.group()
def scheduled():
    """Manage scheduled tasks"""
    pass


@scheduled.command()
def list():
    """List all scheduled tasks"""
    tasks = task_scheduler.get_scheduled_tasks()
    
    if not tasks:
        click.echo("No scheduled tasks found")
        return
    
    # Prepare data for table
    table_data = []
    for task in tasks:
        table_data.append([
            task['name'],
            task['task_type'],
            task['cron_expression'],
            task['priority'],
            'Yes' if task['enabled'] else 'No',
            task['last_run'] or 'Never',
            task['next_run'] or 'N/A'
        ])
    
    headers = ['Name', 'Type', 'Cron', 'Priority', 'Enabled', 'Last Run', 'Next Run']
    click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))


@scheduled.command()
@click.argument('name')
@click.argument('cron_expression')
@click.argument('task_type')
@click.argument('task_data')
@click.option('--priority', default=0, help='Task priority')
@click.option('--max-retries', default=3, help='Maximum retries')
def add(name: str, cron_expression: str, task_type: str, task_data: str, priority: int, max_retries: int):
    """Add a new scheduled task"""
    try:
        data = json.loads(task_data)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON data - {str(e)}", err=True)
        return
    
    try:
        task_scheduler.add_scheduled_task(
            name=name,
            cron_expression=cron_expression,
            task_type=task_type,
            task_data=data,
            priority=priority,
            max_retries=max_retries
        )
        click.echo(f"Scheduled task '{name}' added successfully")
    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
    except Exception as e:
        click.echo(f"Error adding scheduled task: {str(e)}", err=True)


@scheduled.command()
@click.argument('name')
def remove(name: str):
    """Remove a scheduled task"""
    success = task_scheduler.remove_scheduled_task(name)
    
    if success:
        click.echo(f"Scheduled task '{name}' removed successfully")
    else:
        click.echo(f"Scheduled task '{name}' not found")


@scheduled.command()
@click.argument('name')
def enable(name: str):
    """Enable a scheduled task"""
    success = task_scheduler.enable_task(name)
    
    if success:
        click.echo(f"Scheduled task '{name}' enabled")
    else:
        click.echo(f"Scheduled task '{name}' not found")


@scheduled.command()
@click.argument('name')
def disable(name: str):
    """Disable a scheduled task"""
    success = task_scheduler.disable_task(name)
    
    if success:
        click.echo(f"Scheduled task '{name}' disabled")
    else:
        click.echo(f"Scheduled task '{name}' not found")


@cli.command()
def health():
    """Show queue health metrics"""
    async def _health():
        try:
            metrics = await queue_metrics_service.get_queue_health_metrics()
            
            click.echo("=== Queue Health Metrics ===")
            click.echo(f"Health Score: {metrics['health_score']:.1f}/100")
            click.echo(f"Timestamp: {metrics['timestamp']}")
            
            # Basic stats
            basic = metrics['basic_stats']
            click.echo(f"\nPending: {basic['total_pending']}")
            click.echo(f"Processing: {basic['total_processing']}")
            click.echo(f"Completed: {basic['total_completed']}")
            click.echo(f"Failed: {basic['total_failed']}")
            
            # Failure rates
            if metrics['failure_rates']:
                click.echo("\n=== Failure Rates ===")
                failure_data = []
                for task_type, rates in metrics['failure_rates'].items():
                    failure_data.append([
                        task_type,
                        rates['total_tasks'],
                        rates['failed_tasks'],
                        f"{rates['failure_rate']:.2%}"
                    ])
                
                headers = ['Task Type', 'Total', 'Failed', 'Failure Rate']
                click.echo(tabulate(failure_data, headers=headers, tablefmt='grid'))
            
            # Processing times
            if metrics['processing_times']:
                click.echo("\n=== Processing Times ===")
                time_data = []
                for task_type, times in metrics['processing_times'].items():
                    time_data.append([
                        task_type,
                        f"{times['avg_seconds']:.1f}s",
                        f"{times['min_seconds']:.1f}s",
                        f"{times['max_seconds']:.1f}s",
                        times['task_count']
                    ])
                
                headers = ['Task Type', 'Avg Time', 'Min Time', 'Max Time', 'Count']
                click.echo(tabulate(time_data, headers=headers, tablefmt='grid'))
                
        except Exception as e:
            click.echo(f"Error getting health metrics: {str(e)}", err=True)
    
    asyncio.run(_health())


@cli.command()
@click.argument('task_type')
@click.option('--hours', default=24, help='Hours of history to analyze')
def analyze(task_type: str, hours: int):
    """Analyze metrics for a specific task type"""
    async def _analyze():
        try:
            metrics = await queue_metrics_service.get_task_type_metrics(task_type, hours)
            
            click.echo(f"=== Analysis for {task_type} (last {hours} hours) ===")
            click.echo(f"Total Tasks: {metrics['total_tasks']}")
            
            # Status distribution
            click.echo("\n=== Status Distribution ===")
            status_data = [[status, count] for status, count in metrics['status_distribution'].items()]
            click.echo(tabulate(status_data, headers=['Status', 'Count'], tablefmt='grid'))
            
            # Processing time stats
            proc_stats = metrics['processing_time_stats']
            if proc_stats['count'] > 0:
                click.echo(f"\n=== Processing Time Statistics ===")
                click.echo(f"Average: {proc_stats['avg_seconds']:.1f}s")
                click.echo(f"Minimum: {proc_stats['min_seconds']:.1f}s")
                click.echo(f"Maximum: {proc_stats['max_seconds']:.1f}s")
                click.echo(f"Sample Size: {proc_stats['count']}")
            
            # Recent tasks
            if metrics['recent_tasks']:
                click.echo(f"\n=== Recent Tasks (last 10) ===")
                recent_data = []
                for task in metrics['recent_tasks']:
                    recent_data.append([
                        task['id'][:8] + '...',
                        task['status'],
                        task['retry_count'],
                        task['created_at'][:19],
                        task['error_message'][:50] + '...' if task['error_message'] else ''
                    ])
                
                headers = ['Task ID', 'Status', 'Retries', 'Created', 'Error']
                click.echo(tabulate(recent_data, headers=headers, tablefmt='grid'))
                
        except Exception as e:
            click.echo(f"Error analyzing task type: {str(e)}", err=True)
    
    asyncio.run(_analyze())


if __name__ == '__main__':
    cli()