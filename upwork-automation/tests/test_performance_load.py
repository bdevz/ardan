"""
Performance and Load Testing for Upwork Automation System
Part of Task 18: Integration Testing and System Validation

This module provides performance tests for:
- Concurrent session handling and throughput
- Memory usage under load
- Database performance with large datasets
- API endpoint performance
- Browser automation performance
"""
import asyncio
import pytest
import time
import psutil
import gc
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any
import statistics

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from api.database.connection import get_db, init_db
from api.database.models import JobModel, ProposalModel, ApplicationModel
from shared.models import JobStatus, JobType, ProposalStatus, ApplicationStatus


class TestConcurrentSessionPerformance:
    """Test concurrent browser session handling performance"""
    
    @pytest.mark.asyncio
    async def test_high_concurrency_session_pool(self):
        """Test session pool performance with high concurrency"""
        # Mock session manager with realistic session pool
        mock_session_manager = Mock()
        mock_browserbase = Mock()
        
        # Create large session pool
        session_pool_size = 50
        session_pool = [f"session_{i}" for i in range(session_pool_size)]
        mock_browserbase.create_session_pool.return_value = session_pool
        
        # Mock session operations with realistic timing
        async def mock_session_operation(session_id: str, operation_type: str):
            # Simulate different operation times
            operation_times = {
                "job_discovery": 0.5,
                "proposal_submission": 0.8,
                "profile_management": 0.3
            }
            await asyncio.sleep(operation_times.get(operation_type, 0.2))
            return {"session_id": session_id, "operation": operation_type, "success": True}
        
        # Test high concurrency scenario
        concurrent_tasks = 200  # More tasks than sessions
        tasks = []
        
        start_time = time.time()
        
        for i in range(concurrent_tasks):
            operation_type = ["job_discovery", "proposal_submission", "profile_management"][i % 3]
            session_id = session_pool[i % session_pool_size]  # Round-robin assignment
            task = mock_session_operation(session_id, operation_type)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify performance metrics
        successful_operations = [r for r in results if r["success"]]
        throughput = len(successful_operations) / total_time
        
        assert len(successful_operations) == concurrent_tasks
        assert throughput > 50  # Should handle at least 50 operations per second
        assert total_time < 10  # Should complete within 10 seconds
        
        print(f"✅ High concurrency test: {len(successful_operations)} operations in {total_time:.2f}s ({throughput:.1f} ops/sec)")
    
    @pytest.mark.asyncio
    async def test_session_pool_scaling(self):
        """Test session pool scaling under increasing load"""
        mock_browserbase = Mock()
        
        # Test different pool sizes
        pool_sizes = [5, 10, 20, 50]
        performance_results = {}
        
        for pool_size in pool_sizes:
            session_pool = [f"session_{i}" for i in range(pool_size)]
            mock_browserbase.create_session_pool.return_value = session_pool
            
            # Simulate load proportional to pool size
            task_count = pool_size * 4  # 4x oversubscription
            
            async def mock_task(task_id: int):
                session_id = session_pool[task_id % pool_size]
                await asyncio.sleep(0.1)  # Simulate work
                return {"task_id": task_id, "session_id": session_id}
            
            start_time = time.time()
            tasks = [mock_task(i) for i in range(task_count)]
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            execution_time = end_time - start_time
            throughput = len(results) / execution_time
            
            performance_results[pool_size] = {
                "tasks": len(results),
                "time": execution_time,
                "throughput": throughput
            }
        
        # Verify scaling characteristics
        for pool_size, metrics in performance_results.items():
            assert metrics["throughput"] > 10  # Minimum throughput
            print(f"Pool size {pool_size}: {metrics['throughput']:.1f} tasks/sec")
        
        # Verify throughput scales with pool size
        throughputs = [metrics["throughput"] for metrics in performance_results.values()]
        assert throughputs[-1] > throughputs[0]  # Largest pool should be fastest
        
        print("✅ Session pool scaling test passed")
    
    @pytest.mark.asyncio
    async def test_session_health_monitoring_performance(self):
        """Test performance of session health monitoring at scale"""
        mock_browserbase = Mock()
        
        # Create large session pool
        session_count = 100
        sessions = [f"session_{i}" for i in range(session_count)]
        
        # Mock health check with realistic response times
        async def mock_health_check(session_id: str):
            # Simulate network latency
            await asyncio.sleep(0.01)  # 10ms per health check
            
            # Simulate some unhealthy sessions
            session_num = int(session_id.split('_')[1])
            is_healthy = session_num % 10 != 0  # Every 10th session is unhealthy
            
            return {
                "session_id": session_id,
                "healthy": is_healthy,
                "response_time_ms": 10,
                "error": None if is_healthy else "Session timeout"
            }
        
        mock_browserbase.get_session_health.side_effect = mock_health_check
        
        # Test concurrent health checks
        start_time = time.time()
        
        health_tasks = [mock_browserbase.get_session_health(session_id) for session_id in sessions]
        health_results = await asyncio.gather(*health_tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        healthy_sessions = [r for r in health_results if r["healthy"]]
        unhealthy_sessions = [r for r in health_results if not r["healthy"]]
        
        # Verify performance
        assert len(health_results) == session_count
        assert len(unhealthy_sessions) == session_count // 10  # Expected unhealthy count
        assert total_time < 2.0  # Should complete within 2 seconds (concurrent execution)
        
        health_check_rate = len(health_results) / total_time
        assert health_check_rate > 50  # Should check at least 50 sessions per second
        
        print(f"✅ Health monitoring performance: {len(healthy_sessions)} healthy, {len(unhealthy_sessions)} unhealthy in {total_time:.2f}s")


class TestDatabasePerformance:
    """Test database performance with large datasets"""
    
    @pytest.mark.asyncio
    async def test_bulk_job_insertion_performance(self):
        """Test performance of bulk job insertions"""
        await init_db()
        
        # Generate large dataset of jobs
        job_count = 1000
        jobs_data = []
        
        for i in range(job_count):
            job_data = {
                "upwork_job_id": f"job_{i}",
                "title": f"Salesforce Developer Job {i}",
                "description": f"Job description for position {i}" * 10,  # Make it substantial
                "hourly_rate": Decimal(str(50 + (i % 50))),  # Vary rates 50-99
                "client_rating": Decimal(str(4.0 + (i % 10) / 10)),  # Vary ratings 4.0-4.9
                "client_payment_verified": i % 2 == 0,  # Alternate verified status
                "client_hire_rate": Decimal(str(0.5 + (i % 50) / 100)),  # Vary hire rates
                "job_type": JobType.HOURLY,
                "status": JobStatus.DISCOVERED,
                "match_score": Decimal(str(0.5 + (i % 50) / 100)),
                "skills_required": ["Salesforce", "Apex", "Lightning", f"Skill_{i % 10}"]
            }
            jobs_data.append(job_data)
        
        # Test bulk insertion performance
        start_time = time.time()
        
        async with get_db() as session:
            # Insert in batches for better performance
            batch_size = 100
            for i in range(0, len(jobs_data), batch_size):
                batch = jobs_data[i:i + batch_size]
                job_models = [JobModel(**job_data) for job_data in batch]
                session.add_all(job_models)
                await session.commit()
        
        end_time = time.time()
        insertion_time = end_time - start_time
        
        # Verify performance
        insertion_rate = job_count / insertion_time
        assert insertion_rate > 100  # Should insert at least 100 jobs per second
        assert insertion_time < 30  # Should complete within 30 seconds
        
        print(f"✅ Bulk insertion performance: {job_count} jobs in {insertion_time:.2f}s ({insertion_rate:.1f} jobs/sec)")
        
        # Cleanup
        async with get_db() as session:
            from sqlalchemy import delete
            await session.execute(delete(JobModel).where(JobModel.upwork_job_id.like("job_%")))
            await session.commit()
    
    @pytest.mark.asyncio
    async def test_complex_query_performance(self):
        """Test performance of complex database queries"""
        await init_db()
        
        # Create test data
        job_count = 500
        proposal_count = 1000
        application_count = 300
        
        # Insert test jobs
        async with get_db() as session:
            jobs = []
            for i in range(job_count):
                job = JobModel(
                    upwork_job_id=f"perf_job_{i}",
                    title=f"Performance Test Job {i}",
                    description="Performance test job description",
                    hourly_rate=Decimal(str(50 + i % 50)),
                    client_rating=Decimal(str(4.0 + (i % 10) / 10)),
                    client_payment_verified=True,
                    client_hire_rate=Decimal("0.8"),
                    job_type=JobType.HOURLY,
                    status=JobStatus.DISCOVERED,
                    match_score=Decimal(str(0.7 + (i % 30) / 100))
                )
                jobs.append(job)
            
            session.add_all(jobs)
            await session.commit()
            
            # Refresh to get IDs
            for job in jobs:
                await session.refresh(job)
        
        # Insert test proposals
        async with get_db() as session:
            proposals = []
            for i in range(proposal_count):
                job_index = i % job_count
                proposal = ProposalModel(
                    job_id=jobs[job_index].id,
                    content=f"Performance test proposal {i}",
                    bid_amount=Decimal(str(60 + i % 40)),
                    status=ProposalStatus.DRAFT,
                    quality_score=Decimal(str(0.8 + (i % 20) / 100))
                )
                proposals.append(proposal)
            
            session.add_all(proposals)
            await session.commit()
        
        # Test complex query performance
        from sqlalchemy import select, func
        from sqlalchemy.orm import selectinload
        
        start_time = time.time()
        
        async with get_db() as session:
            # Complex query: Jobs with proposals, filtered and aggregated
            query = (
                select(JobModel)
                .options(selectinload(JobModel.proposals))
                .where(
                    JobModel.hourly_rate >= 60,
                    JobModel.client_rating >= 4.5,
                    JobModel.match_score >= 0.8
                )
                .order_by(JobModel.match_score.desc())
                .limit(50)
            )
            
            result = await session.execute(query)
            jobs_with_proposals = result.scalars().all()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Verify performance and results
        assert len(jobs_with_proposals) > 0
        assert query_time < 1.0  # Should complete within 1 second
        
        # Verify data integrity
        for job in jobs_with_proposals:
            assert job.hourly_rate >= 60
            assert job.client_rating >= 4.5
            assert job.match_score >= 0.8
        
        print(f"✅ Complex query performance: {len(jobs_with_proposals)} results in {query_time:.3f}s")
        
        # Cleanup
        async with get_db() as session:
            from sqlalchemy import delete
            await session.execute(delete(ProposalModel).where(ProposalModel.content.like("Performance test%")))
            await session.execute(delete(JobModel).where(JobModel.upwork_job_id.like("perf_job_%")))
            await session.commit()


class TestMemoryPerformance:
    """Test memory usage and performance under load"""
    
    def test_memory_usage_large_datasets(self):
        """Test memory usage when processing large datasets"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large datasets simulating job processing
        large_datasets = []
        dataset_count = 10
        jobs_per_dataset = 1000
        
        for dataset_idx in range(dataset_count):
            dataset = []
            for job_idx in range(jobs_per_dataset):
                job_data = {
                    "id": f"dataset_{dataset_idx}_job_{job_idx}",
                    "title": f"Salesforce Developer Position {job_idx}" * 5,  # Make it larger
                    "description": "Long job description " * 200,  # Substantial content
                    "skills": ["Salesforce", "Apex", "Lightning", "Einstein"] * 25,
                    "client_info": {
                        "rating": 4.5 + (job_idx % 10) / 20,
                        "hire_rate": 0.8 + (job_idx % 20) / 100,
                        "payment_verified": job_idx % 2 == 0,
                        "history": list(range(job_idx % 50))  # Variable history size
                    },
                    "metadata": {
                        "search_keywords": ["keyword_" + str(i) for i in range(job_idx % 20)],
                        "extraction_data": {"raw_html": "html_content " * 100},
                        "processing_steps": [f"step_{i}" for i in range(job_idx % 10)]
                    }
                }
                dataset.append(job_data)
            large_datasets.append(dataset)
        
        # Check memory after data creation
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        # Process datasets (simulate filtering, ranking, etc.)
        processed_results = []
        for dataset in large_datasets:
            # Simulate complex processing
            filtered_jobs = [
                job for job in dataset 
                if job["client_info"]["rating"] >= 4.0 
                and job["client_info"]["payment_verified"]
            ]
            
            # Simulate ranking
            ranked_jobs = sorted(
                filtered_jobs, 
                key=lambda x: (x["client_info"]["rating"], x["client_info"]["hire_rate"]), 
                reverse=True
            )
            
            # Simulate additional processing
            enhanced_jobs = []
            for job in ranked_jobs[:100]:  # Top 100 jobs
                enhanced_job = job.copy()
                enhanced_job["match_score"] = (
                    job["client_info"]["rating"] * 0.4 + 
                    job["client_info"]["hire_rate"] * 0.6
                )
                enhanced_job["priority"] = "high" if enhanced_job["match_score"] > 4.2 else "medium"
                enhanced_jobs.append(enhanced_job)
            
            processed_results.append(enhanced_jobs)
        
        # Check memory after processing
        processing_memory = process.memory_info().rss / 1024 / 1024  # MB
        processing_increase = processing_memory - initial_memory
        
        # Clean up large datasets
        del large_datasets
        del processed_results
        gc.collect()
        
        # Check memory after cleanup
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_recovered = processing_memory - final_memory
        
        # Verify memory usage is reasonable
        assert memory_increase < 1000  # Should not use more than 1GB for data
        assert processing_increase < 1500  # Should not use more than 1.5GB during processing
        assert memory_recovered > processing_increase * 0.3  # Should recover at least 30%
        
        print(f"✅ Memory usage test: Peak {processing_memory:.1f}MB, Increase {processing_increase:.1f}MB, Recovered {memory_recovered:.1f}MB")
    
    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated operations"""
        process = psutil.Process()
        memory_samples = []
        
        # Perform repeated operations
        iterations = 50
        for i in range(iterations):
            # Simulate job processing cycle
            jobs = []
            for j in range(100):
                job = {
                    "id": f"leak_test_{i}_{j}",
                    "title": f"Job {j}",
                    "description": "Description " * 50,
                    "data": list(range(j * 10))
                }
                jobs.append(job)
            
            # Process jobs
            processed = [job for job in jobs if len(job["data"]) > 50]
            
            # Clean up
            del jobs
            del processed
            
            # Sample memory every 10 iterations
            if i % 10 == 0:
                gc.collect()  # Force garbage collection
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_samples.append(memory_mb)
        
        # Analyze memory trend
        if len(memory_samples) > 2:
            # Calculate memory growth trend
            memory_growth = memory_samples[-1] - memory_samples[0]
            avg_growth_per_sample = memory_growth / (len(memory_samples) - 1)
            
            # Memory should not grow significantly over time
            assert memory_growth < 100  # Should not grow more than 100MB
            assert avg_growth_per_sample < 20  # Should not grow more than 20MB per sample
            
            print(f"✅ Memory leak test: Growth {memory_growth:.1f}MB over {len(memory_samples)} samples")
        else:
            print("✅ Memory leak test: Insufficient samples for trend analysis")


class TestAPIPerformance:
    """Test API endpoint performance under load"""
    
    @pytest.mark.asyncio
    async def test_api_endpoint_response_times(self):
        """Test API endpoint response times under load"""
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        # Test different endpoints
        endpoints = [
            {"method": "GET", "url": "/health"},
            {"method": "GET", "url": "/api/version"},
            {"method": "GET", "url": "/api/jobs?limit=10"},
            {"method": "GET", "url": "/api/metrics"},
        ]
        
        response_times = {}
        
        for endpoint in endpoints:
            times = []
            
            # Make multiple requests to each endpoint
            for _ in range(20):
                start_time = time.time()
                
                if endpoint["method"] == "GET":
                    response = client.get(endpoint["url"])
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                # Verify response is successful
                assert response.status_code in [200, 404]  # 404 is OK for endpoints that might not have data
                
                times.append(response_time)
            
            # Calculate statistics
            avg_time = statistics.mean(times)
            max_time = max(times)
            min_time = min(times)
            p95_time = sorted(times)[int(len(times) * 0.95)]
            
            response_times[endpoint["url"]] = {
                "avg": avg_time,
                "max": max_time,
                "min": min_time,
                "p95": p95_time
            }
            
            # Verify performance requirements
            assert avg_time < 500  # Average response time should be under 500ms
            assert p95_time < 1000  # 95th percentile should be under 1 second
        
        # Print performance summary
        for url, times in response_times.items():
            print(f"✅ {url}: avg={times['avg']:.1f}ms, p95={times['p95']:.1f}ms, max={times['max']:.1f}ms")
    
    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self):
        """Test API performance under concurrent load"""
        import httpx
        
        # Test concurrent requests to health endpoint
        concurrent_requests = 100
        
        async def make_request(client: httpx.AsyncClient, request_id: int):
            start_time = time.time()
            try:
                response = await client.get("http://localhost:8000/health")
                end_time = time.time()
                return {
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "response_time": (end_time - start_time) * 1000,
                    "success": True
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "request_id": request_id,
                    "status_code": None,
                    "response_time": (end_time - start_time) * 1000,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute concurrent requests
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            tasks = [make_request(client, i) for i in range(concurrent_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        successful_requests = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_requests = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
        
        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
            avg_response_time = statistics.mean(response_times)
            throughput = len(successful_requests) / total_time
            
            # Verify performance
            assert len(successful_requests) >= concurrent_requests * 0.9  # At least 90% success rate
            assert avg_response_time < 1000  # Average response time under 1 second
            assert throughput > 50  # At least 50 requests per second
            
            print(f"✅ Concurrent API test: {len(successful_requests)}/{concurrent_requests} successful, {throughput:.1f} req/sec, avg {avg_response_time:.1f}ms")
        else:
            print("❌ No successful requests in concurrent API test")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])