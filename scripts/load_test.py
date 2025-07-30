#!/usr/bin/env python3
"""
Load Testing Script for Sales Call Analytics API
Tests both data ingestion and API query performance under high load.
"""

import asyncio
import aiohttp
import time
import random
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
import argparse
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data_ingestion import CallTranscriptGenerator, DataIngestionPipeline
from app.crud import CRUD


@dataclass
class LoadTestResult:
    """Results from a load test"""

    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    error_rate: float
    response_times: List[float]


class LoadTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.results: List[LoadTestResult] = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_api_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        params: Dict = None,
        data: Dict = None,
        concurrent_requests: int = 10,
        total_requests: int = 100,
    ) -> LoadTestResult:
        """Test a specific API endpoint under load"""
        print(
            f"Testing {method} {endpoint} with {concurrent_requests} concurrent requests, {total_requests} total"
        )

        response_times = []
        successful_requests = 0
        failed_requests = 0
        start_time = time.time()

        async def make_request():
            nonlocal successful_requests, failed_requests
            request_start = time.time()
            try:
                if method == "GET":
                    async with self.session.get(
                        f"{self.base_url}{endpoint}", params=params
                    ) as response:
                        await response.text()
                elif method == "POST":
                    async with self.session.post(
                        f"{self.base_url}{endpoint}", json=data
                    ) as response:
                        await response.text()

                if response.status < 400:
                    successful_requests += 1
                else:
                    failed_requests += 1

            except Exception as e:
                failed_requests += 1
                print(f"Request failed: {e}")

            response_time = time.time() - request_start
            response_times.append(response_time)

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(concurrent_requests)

        async def limited_request():
            async with semaphore:
                await make_request()

        # Create tasks for all requests
        tasks = [limited_request() for _ in range(total_requests)]
        await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        result = LoadTestResult(
            test_name=f"{method} {endpoint}",
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_time=total_time,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            requests_per_second=(
                successful_requests / total_time if total_time > 0 else 0
            ),
            error_rate=failed_requests / total_requests if total_requests > 0 else 0,
            response_times=response_times,
        )

        self.results.append(result)
        return result

    async def test_data_ingestion_load(
        self, num_calls: int = 1000, batch_size: int = 50
    ) -> LoadTestResult:
        """Test data ingestion performance under load"""
        print(
            f"Testing data ingestion with {num_calls} calls in batches of {batch_size}"
        )

        start_time = time.time()
        successful_ingestions = 0
        failed_ingestions = 0
        response_times = []

        # Initialize pipeline
        pipeline = DataIngestionPipeline()

        # Generate all calls first
        generator = CallTranscriptGenerator()
        all_calls = []

        for i in range(num_calls):
            call_data = generator.generate_call()
            all_calls.append(call_data)

        # Process in batches
        for i in range(0, len(all_calls), batch_size):
            batch = all_calls[i : i + batch_size]
            batch_start = time.time()

            try:
                await pipeline.ingest_calls_batch(batch)
                successful_ingestions += len(batch)
            except Exception as e:
                failed_ingestions += len(batch)
                print(f"Batch ingestion failed: {e}")

            batch_time = time.time() - batch_start
            response_times.append(batch_time)

        total_time = time.time() - start_time

        result = LoadTestResult(
            test_name="Data Ingestion",
            total_requests=num_calls,
            successful_requests=successful_ingestions,
            failed_requests=failed_ingestions,
            total_time=total_time,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            requests_per_second=(
                successful_ingestions / total_time if total_time > 0 else 0
            ),
            error_rate=failed_ingestions / num_calls if num_calls > 0 else 0,
            response_times=response_times,
        )

        self.results.append(result)
        return result

    async def test_concurrent_queries(
        self, num_queries: int = 500, concurrent_requests: int = 20
    ) -> LoadTestResult:
        """Test concurrent query performance"""
        print(
            f"Testing concurrent queries: {num_queries} queries with {concurrent_requests} concurrent"
        )

        # Generate random query parameters
        def generate_query_params():
            params = {}
            if random.random() > 0.5:
                params["limit"] = random.randint(10, 100)
            if random.random() > 0.5:
                params["offset"] = random.randint(0, 1000)
            if random.random() > 0.3:
                params["agent_id"] = f"AGENT_{random.randint(1, 100)}"
            if random.random() > 0.3:
                # Random date range
                start_date = datetime.now() - timedelta(days=random.randint(1, 30))
                end_date = start_date + timedelta(days=random.randint(1, 7))
                params["from_date"] = start_date.isoformat()
                params["to_date"] = end_date.isoformat()
            if random.random() > 0.5:
                params["min_sentiment"] = random.uniform(-1, 0)
                params["max_sentiment"] = random.uniform(0, 1)
            return params

        response_times = []
        successful_requests = 0
        failed_requests = 0
        start_time = time.time()

        async def make_query_request():
            nonlocal successful_requests, failed_requests
            params = generate_query_params()
            request_start = time.time()

            try:
                async with self.session.get(
                    f"{self.base_url}/api/v1/calls", params=params
                ) as response:
                    await response.text()

                if response.status < 400:
                    successful_requests += 1
                else:
                    failed_requests += 1

            except Exception as e:
                failed_requests += 1
                print(f"Query request failed: {e}")

            response_time = time.time() - request_start
            response_times.append(response_time)

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(concurrent_requests)

        async def limited_request():
            async with semaphore:
                await make_query_request()

        # Create tasks for all requests
        tasks = [limited_request() for _ in range(num_queries)]
        await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        result = LoadTestResult(
            test_name="Concurrent Queries",
            total_requests=num_queries,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_time=total_time,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            requests_per_second=(
                successful_requests / total_time if total_time > 0 else 0
            ),
            error_rate=failed_requests / num_queries if num_queries > 0 else 0,
            response_times=response_times,
        )

        self.results.append(result)
        return result

    def print_results(self):
        """Print all test results in a formatted way"""
        print("\n" + "=" * 80)
        print("LOAD TEST RESULTS")
        print("=" * 80)

        for result in self.results:
            print(f"\n{result.test_name}")
            print("-" * 50)
            print(f"Total Requests: {result.total_requests}")
            print(f"Successful: {result.successful_requests}")
            print(f"Failed: {result.failed_requests}")
            print(f"Error Rate: {result.error_rate:.2%}")
            print(f"Total Time: {result.total_time:.2f}s")
            print(f"Requests/Second: {result.requests_per_second:.2f}")
            print(f"Avg Response Time: {result.avg_response_time:.3f}s")
            print(f"Min Response Time: {result.min_response_time:.3f}s")
            print(f"Max Response Time: {result.max_response_time:.3f}s")

            if result.response_times:
                p95 = sorted(result.response_times)[
                    int(len(result.response_times) * 0.95)
                ]
                p99 = sorted(result.response_times)[
                    int(len(result.response_times) * 0.99)
                ]
                print(f"95th Percentile: {p95:.3f}s")
                print(f"99th Percentile: {p99:.3f}s")

    def save_results(self, filename: str = "load_test_results.json"):
        """Save results to JSON file"""
        results_data = []
        for result in self.results:
            results_data.append(
                {
                    "test_name": result.test_name,
                    "total_requests": result.total_requests,
                    "successful_requests": result.successful_requests,
                    "failed_requests": result.failed_requests,
                    "total_time": result.total_time,
                    "avg_response_time": result.avg_response_time,
                    "min_response_time": result.min_response_time,
                    "max_response_time": result.max_response_time,
                    "requests_per_second": result.requests_per_second,
                    "error_rate": result.error_rate,
                    "response_times": result.response_times,
                }
            )

        with open(filename, "w") as f:
            json.dump(results_data, f, indent=2)

        print(f"\nResults saved to {filename}")


async def main():
    parser = argparse.ArgumentParser(
        description="Load test the Sales Call Analytics API"
    )
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="Base URL of the API"
    )
    parser.add_argument(
        "--ingestion-calls", type=int, default=1000, help="Number of calls to ingest"
    )
    parser.add_argument(
        "--concurrent-queries",
        type=int,
        default=500,
        help="Number of concurrent queries",
    )
    parser.add_argument(
        "--concurrent-requests",
        type=int,
        default=20,
        help="Number of concurrent requests",
    )
    parser.add_argument(
        "--save-results", action="store_true", help="Save results to JSON file"
    )

    args = parser.parse_args()

    async with LoadTester(args.base_url) as tester:
        # Test API endpoints
        await tester.test_api_endpoint(
            "/api/v1/calls", concurrent_requests=10, total_requests=100
        )
        await tester.test_api_endpoint(
            "/api/v1/analytics/agents", concurrent_requests=5, total_requests=50
        )

        # Test data ingestion
        await tester.test_data_ingestion_load(args.ingestion_calls, batch_size=50)

        # Test concurrent queries
        await tester.test_concurrent_queries(
            args.concurrent_queries, args.concurrent_requests
        )

        # Print and save results
        tester.print_results()

        if args.save_results:
            tester.save_results()


if __name__ == "__main__":
    asyncio.run(main())
