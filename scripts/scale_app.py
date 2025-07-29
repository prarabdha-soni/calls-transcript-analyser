#!/usr/bin/env python3
"""
Application Scaling Script
Runs multiple API instances and coordinates load balancing.
"""

import asyncio
import subprocess
import time
import signal
import sys
import os
import argparse
import json
from typing import List, Dict, Any
import psutil
import requests
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppScaler:
    """Application scaling and load balancing coordinator"""
    
    def __init__(self, base_port: int = 8000, num_instances: int = 3):
        self.base_port = base_port
        self.num_instances = num_instances
        self.processes: List[subprocess.Popen] = []
        self.health_check_urls: List[str] = []
        self.running = False
        
    def start_instances(self, use_optimized: bool = True):
        """Start multiple API instances"""
        logger.info(f"Starting {self.num_instances} API instances...")
        
        for i in range(self.num_instances):
            port = self.base_port + i
            health_url = f"http://localhost:{port}/health"
            self.health_check_urls.append(health_url)
            
            # Choose which API to run
            api_module = "app.api_optimized" if use_optimized else "app.api"
            
            # Start the process
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", 
                f"{api_module}:app",
                "--host", "0.0.0.0",
                "--port", str(port),
                "--workers", "1",  # Single worker per instance for now
                "--log-level", "info"
            ])
            
            self.processes.append(process)
            logger.info(f"Started instance {i+1} on port {port} (PID: {process.pid})")
            
            # Give each instance time to start
            time.sleep(2)
        
        self.running = True
        logger.info("All instances started")
    
    def stop_instances(self):
        """Stop all API instances"""
        logger.info("Stopping all API instances...")
        
        for i, process in enumerate(self.processes):
            try:
                process.terminate()
                process.wait(timeout=10)
                logger.info(f"Stopped instance {i+1}")
            except subprocess.TimeoutExpired:
                process.kill()
                logger.warning(f"Force killed instance {i+1}")
            except Exception as e:
                logger.error(f"Error stopping instance {i+1}: {e}")
        
        self.processes.clear()
        self.health_check_urls.clear()
        self.running = False
        logger.info("All instances stopped")
    
    async def check_health(self, url: str) -> Dict[str, Any]:
        """Check health of a single instance"""
        try:
            response = requests.get(url, timeout=5)
            return {
                "url": url,
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                "url": url,
                "status": "error",
                "error": str(e)
            }
    
    async def check_all_health(self) -> List[Dict[str, Any]]:
        """Check health of all instances"""
        tasks = [self.check_health(url) for url in self.health_check_urls]
        return await asyncio.gather(*tasks)
    
    def get_instance_urls(self) -> List[str]:
        """Get list of all instance URLs"""
        return [f"http://localhost:{self.base_port + i}" for i in range(self.num_instances)]
    
    def get_load_balancer_config(self) -> Dict[str, Any]:
        """Generate load balancer configuration"""
        return {
            "upstream_servers": self.get_instance_urls(),
            "health_check_interval": 30,
            "health_check_timeout": 5,
            "load_balancing_method": "round_robin"
        }
    
    async def run_load_test(self, target_url: str = None, duration: int = 60):
        """Run load test against the scaled application"""
        if not target_url:
            # Use first instance for load testing
            target_url = f"http://localhost:{self.base_port}"
        
        logger.info(f"Running load test against {target_url} for {duration} seconds...")
        
        # Import and run load test
        from scripts.load_test import LoadTester
        
        async with LoadTester(target_url) as tester:
            # Test with higher load
            await tester.test_api_endpoint("/api/v1/calls", concurrent_requests=50, total_requests=500)
            await tester.test_concurrent_queries(num_queries=1000, concurrent_requests=50)
            
            tester.print_results()
            tester.save_results("scaled_load_test_results.json")
    
    def monitor_resources(self):
        """Monitor system resources"""
        logger.info("Monitoring system resources...")
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        logger.info(f"CPU Usage: {cpu_percent}%")
        
        # Memory usage
        memory = psutil.virtual_memory()
        logger.info(f"Memory Usage: {memory.percent}% ({memory.used // 1024 // 1024}MB / {memory.total // 1024 // 1024}MB)")
        
        # Process information
        for i, process in enumerate(self.processes):
            try:
                proc_info = psutil.Process(process.pid)
                logger.info(f"Instance {i+1} - CPU: {proc_info.cpu_percent()}%, Memory: {proc_info.memory_info().rss // 1024 // 1024}MB")
            except psutil.NoSuchProcess:
                logger.warning(f"Instance {i+1} process not found")
    
    async def run_scaling_demo(self):
        """Run a complete scaling demonstration"""
        logger.info("Starting scaling demonstration...")
        
        try:
            # Start instances
            self.start_instances(use_optimized=True)
            
            # Wait for instances to be ready
            await asyncio.sleep(5)
            
            # Check health
            health_results = await self.check_all_health()
            logger.info("Health check results:")
            for result in health_results:
                logger.info(f"  {result}")
            
            # Monitor resources
            self.monitor_resources()
            
            # Run load test
            await self.run_load_test(duration=30)
            
            # Show load balancer config
            lb_config = self.get_load_balancer_config()
            logger.info("Load balancer configuration:")
            logger.info(json.dumps(lb_config, indent=2))
            
        finally:
            # Stop instances
            self.stop_instances()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal, stopping instances...")
    if hasattr(signal_handler, 'scaler'):
        signal_handler.scaler.stop_instances()
    sys.exit(0)


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Scale the Sales Call Analytics API")
    parser.add_argument("--instances", type=int, default=3, help="Number of instances to run")
    parser.add_argument("--base-port", type=int, default=8000, help="Base port for instances")
    parser.add_argument("--optimized", action="store_true", help="Use optimized API")
    parser.add_argument("--demo", action="store_true", help="Run scaling demonstration")
    parser.add_argument("--load-test", action="store_true", help="Run load test")
    parser.add_argument("--monitor", action="store_true", help="Monitor resources")
    
    args = parser.parse_args()
    
    # Create scaler
    scaler = AppScaler(base_port=args.base_port, num_instances=args.instances)
    
    # Set up signal handlers
    signal_handler.scaler = scaler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.demo:
            await scaler.run_scaling_demo()
        else:
            # Start instances
            scaler.start_instances(use_optimized=args.optimized)
            
            if args.load_test:
                await scaler.run_load_test()
            
            if args.monitor:
                while scaler.running:
                    scaler.monitor_resources()
                    await asyncio.sleep(10)
            else:
                # Keep running
                logger.info("Instances running. Press Ctrl+C to stop.")
                while scaler.running:
                    await asyncio.sleep(1)
                    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        scaler.stop_instances()


if __name__ == "__main__":
    asyncio.run(main()) 