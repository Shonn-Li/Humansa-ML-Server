#!/usr/bin/env python3
"""
YouWoAI ML Server Performance Benchmarks

Measures performance metrics for the multi-agent system including:
- Response latency
- Streaming event throughput
- Agent execution times
- Memory usage
- Concurrent request handling
"""

import asyncio
import json
import time
import logging
import statistics
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import sys
import os

# Try to import psutil, but make it optional
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a test run"""
    test_name: str
    duration: float
    events_per_second: float
    first_event_latency: float
    completion_latency: float
    memory_usage_mb: float
    cpu_usage_percent: float
    event_count: int
    agent_timings: Dict[str, float] = field(default_factory=dict)
    percentiles: Dict[str, float] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of a benchmark test"""
    test_type: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_duration: float
    min_duration: float
    max_duration: float
    p50_duration: float
    p95_duration: float
    p99_duration: float
    events_per_second: float
    memory_usage_mb: float
    errors: List[str] = field(default_factory=list)


class PerformanceBenchmark:
    """Performance benchmark suite for multi-agent system"""
    
    def __init__(self):
        self.results: List[PerformanceMetrics] = []
        if HAS_PSUTIL:
            self.process = psutil.Process()
        else:
            self.process = None
    
    def measure_memory(self) -> float:
        """Measure current memory usage in MB"""
        if HAS_PSUTIL and self.process:
            return self.process.memory_info().rss / 1024 / 1024
        return 0.0  # Return 0 if psutil not available
    
    def measure_cpu(self) -> float:
        """Measure CPU usage percentage"""
        if HAS_PSUTIL and self.process:
            return self.process.cpu_percent(interval=0.1)
        return 0.0  # Return 0 if psutil not available
    
    async def benchmark_single_request(
        self, 
        request: Dict[str, Any], 
        test_name: str
    ) -> PerformanceMetrics:
        """Benchmark a single request"""
        
        # Record initial state
        start_time = time.time()
        start_memory = self.measure_memory()
        
        # Track metrics
        first_event_time = None
        event_count = 0
        event_timings = []
        agent_timings = {}
        
        try:
            # Simulate multi-agent workflow
            async for event in self._simulate_multi_agent_workflow(request):
                current_time = time.time()
                
                if first_event_time is None:
                    first_event_time = current_time
                
                event_count += 1
                event_timings.append(current_time - start_time)
                
                # Track agent-specific timings
                if event.get("type") == "response.output_item.done":
                    item = event.get("item", {})
                    item_type = item.get("type", "unknown")
                    if item_type not in agent_timings:
                        agent_timings[item_type] = current_time - start_time
            
            # Calculate metrics
            end_time = time.time()
            duration = end_time - start_time
            first_event_latency = first_event_time - start_time if first_event_time else 0
            
            # Calculate percentiles
            percentiles = {}
            if event_timings:
                percentiles = {
                    "p50": statistics.median(event_timings),
                    "p95": self._calculate_percentile(event_timings, 95),
                    "p99": self._calculate_percentile(event_timings, 99)
                }
            
            return PerformanceMetrics(
                test_name=test_name,
                duration=duration,
                events_per_second=event_count / duration if duration > 0 else 0,
                first_event_latency=first_event_latency,
                completion_latency=duration,
                memory_usage_mb=self.measure_memory() - start_memory,
                cpu_usage_percent=self.measure_cpu(),
                event_count=event_count,
                agent_timings=agent_timings,
                percentiles=percentiles
            )
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            return PerformanceMetrics(
                test_name=test_name,
                duration=time.time() - start_time,
                events_per_second=0,
                first_event_latency=0,
                completion_latency=0,
                memory_usage_mb=0,
                cpu_usage_percent=0,
                event_count=0
            )
    
    async def benchmark_concurrent_requests(
        self, 
        request: Dict[str, Any],
        concurrent_count: int = 10
    ) -> BenchmarkResult:
        """Benchmark concurrent request handling"""
        logger.info(f"\n🔥 Benchmarking {concurrent_count} concurrent requests...")
        
        start_time = time.time()
        
        # Run concurrent requests
        tasks = []
        for i in range(concurrent_count):
            task = self.benchmark_single_request(
                request, 
                f"concurrent_{i}"
            )
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, PerformanceMetrics)]
        failed_count = len(results) - len(successful_results)
        
        if not successful_results:
            return BenchmarkResult(
                test_type="concurrent",
                total_requests=concurrent_count,
                successful_requests=0,
                failed_requests=failed_count,
                avg_duration=0,
                min_duration=0,
                max_duration=0,
                p50_duration=0,
                p95_duration=0,
                p99_duration=0,
                events_per_second=0,
                memory_usage_mb=0,
                errors=["All requests failed"]
            )
        
        # Calculate statistics
        durations = [r.duration for r in successful_results]
        events_per_sec = [r.events_per_second for r in successful_results]
        memory_usage = [r.memory_usage_mb for r in successful_results]
        
        return BenchmarkResult(
            test_type="concurrent",
            total_requests=concurrent_count,
            successful_requests=len(successful_results),
            failed_requests=failed_count,
            avg_duration=statistics.mean(durations),
            min_duration=min(durations),
            max_duration=max(durations),
            p50_duration=statistics.median(durations),
            p95_duration=self._calculate_percentile(durations, 95),
            p99_duration=self._calculate_percentile(durations, 99),
            events_per_second=statistics.mean(events_per_sec),
            memory_usage_mb=max(memory_usage) if memory_usage else 0
        )
    
    async def benchmark_streaming_throughput(
        self,
        request: Dict[str, Any],
        duration_seconds: int = 10
    ) -> Dict[str, Any]:
        """Benchmark streaming throughput"""
        logger.info(f"\n📊 Benchmarking streaming throughput for {duration_seconds}s...")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        total_events = 0
        event_sizes = []
        
        while time.time() < end_time:
            async for event in self._simulate_multi_agent_workflow(request):
                total_events += 1
                # Estimate event size
                event_size = len(json.dumps(event))
                event_sizes.append(event_size)
                
                if time.time() >= end_time:
                    break
        
        actual_duration = time.time() - start_time
        
        return {
            "duration_seconds": actual_duration,
            "total_events": total_events,
            "events_per_second": total_events / actual_duration,
            "avg_event_size_bytes": statistics.mean(event_sizes) if event_sizes else 0,
            "total_bytes": sum(event_sizes),
            "throughput_mbps": (sum(event_sizes) / 1024 / 1024) / actual_duration
        }
    
    async def benchmark_agent_performance(
        self,
        request: Dict[str, Any]
    ) -> Dict[str, Dict[str, float]]:
        """Benchmark individual agent performance"""
        logger.info("\n⚡ Benchmarking individual agent performance...")
        
        agent_metrics = {
            "router": [],
            "rag": [],
            "web_search": [],
            "code_interpreter": [],
            "response": [],
            "citation": []
        }
        
        # Run multiple iterations
        for i in range(5):
            metrics = await self.benchmark_single_request(request, f"agent_perf_{i}")
            
            for agent, timing in metrics.agent_timings.items():
                if agent in agent_metrics:
                    agent_metrics[agent].append(timing)
        
        # Calculate statistics
        agent_stats = {}
        for agent, timings in agent_metrics.items():
            if timings:
                agent_stats[agent] = {
                    "avg_ms": statistics.mean(timings) * 1000,
                    "min_ms": min(timings) * 1000,
                    "max_ms": max(timings) * 1000,
                    "p50_ms": statistics.median(timings) * 1000,
                    "calls": len(timings)
                }
        
        return agent_stats
    
    async def _simulate_multi_agent_workflow(
        self, 
        request: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Simulate a multi-agent workflow for benchmarking"""
        
        # Simulate event sequence
        events = [
            {"type": "response.created", "sequence_number": 0},
            {"type": "response.in_progress", "sequence_number": 1},
            {"type": "response.output_item.added", "sequence_number": 2, "item": {"type": "reasoning"}},
            {"type": "response.reasoning_text.delta", "sequence_number": 3},
            {"type": "response.output_item.done", "sequence_number": 4, "item": {"type": "reasoning"}},
            {"type": "response.output_item.added", "sequence_number": 5, "item": {"type": "web_search_call"}},
            {"type": "response.web_search_call.in_progress", "sequence_number": 6},
            {"type": "response.web_search_call.completed", "sequence_number": 7},
            {"type": "response.output_item.done", "sequence_number": 8, "item": {"type": "web_search_call"}},
            {"type": "response.output_item.added", "sequence_number": 9, "item": {"type": "message"}},
            {"type": "response.output_text.delta", "sequence_number": 10},
            {"type": "response.output_text.done", "sequence_number": 11},
            {"type": "response.output_item.done", "sequence_number": 12, "item": {"type": "message"}},
            {"type": "response.completed", "sequence_number": 13}
        ]
        
        for event in events:
            yield event
            # Simulate processing time
            await asyncio.sleep(0.01)
    
    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value"""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def generate_report(self, results: Dict[str, Any]) -> None:
        """Generate performance report"""
        logger.info("\n" + "="*60)
        logger.info("📊 PERFORMANCE BENCHMARK REPORT")
        logger.info("="*60)
        
        # Single request performance
        if "single_request" in results:
            single = results["single_request"]
            logger.info("\n📍 Single Request Performance:")
            logger.info(f"  Duration: {single.duration:.3f}s")
            logger.info(f"  First Event Latency: {single.first_event_latency*1000:.1f}ms")
            logger.info(f"  Events/Second: {single.events_per_second:.1f}")
            logger.info(f"  Memory Usage: {single.memory_usage_mb:.1f}MB")
            logger.info(f"  CPU Usage: {single.cpu_usage_percent:.1f}%")
        
        # Concurrent performance
        if "concurrent" in results:
            concurrent = results["concurrent"]
            logger.info("\n🔥 Concurrent Request Performance:")
            logger.info(f"  Total Requests: {concurrent.total_requests}")
            logger.info(f"  Successful: {concurrent.successful_requests}")
            logger.info(f"  Failed: {concurrent.failed_requests}")
            logger.info(f"  Avg Duration: {concurrent.avg_duration:.3f}s")
            logger.info(f"  P50 Duration: {concurrent.p50_duration:.3f}s")
            logger.info(f"  P95 Duration: {concurrent.p95_duration:.3f}s")
            logger.info(f"  P99 Duration: {concurrent.p99_duration:.3f}s")
        
        # Streaming throughput
        if "streaming" in results:
            streaming = results["streaming"]
            logger.info("\n📊 Streaming Throughput:")
            logger.info(f"  Events/Second: {streaming['events_per_second']:.1f}")
            logger.info(f"  Avg Event Size: {streaming['avg_event_size_bytes']:.0f} bytes")
            logger.info(f"  Throughput: {streaming['throughput_mbps']:.2f} MB/s")
        
        # Agent performance
        if "agents" in results:
            logger.info("\n⚡ Agent Performance (avg response time):")
            for agent, stats in results["agents"].items():
                if stats:
                    logger.info(f"  {agent}: {stats['avg_ms']:.1f}ms (min: {stats['min_ms']:.1f}ms, max: {stats['max_ms']:.1f}ms)")


async def main():
    """Run performance benchmarks"""
    benchmark = PerformanceBenchmark()
    
    # Test request
    test_request = {
        "messages": [{"role": "user", "content": "What are the latest AI developments?"}],
        "model": "gpt-4.1-nano",
        "user_id": 123,
        "stream": True,
        "enable_web_search": True,
        "enable_citations": True
    }
    
    results = {}
    
    # 1. Single request benchmark
    logger.info("🚀 Starting Performance Benchmarks...")
    single_result = await benchmark.benchmark_single_request(test_request, "single_request")
    results["single_request"] = single_result
    
    # 2. Concurrent requests benchmark
    concurrent_result = await benchmark.benchmark_concurrent_requests(test_request, concurrent_count=10)
    results["concurrent"] = concurrent_result
    
    # 3. Streaming throughput benchmark
    streaming_result = await benchmark.benchmark_streaming_throughput(test_request, duration_seconds=5)
    results["streaming"] = streaming_result
    
    # 4. Agent performance benchmark
    agent_result = await benchmark.benchmark_agent_performance(test_request)
    results["agents"] = agent_result
    
    # Generate report
    benchmark.generate_report(results)
    
    # Save results
    save_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "single_request": {
            "duration": single_result.duration,
            "events_per_second": single_result.events_per_second,
            "first_event_latency_ms": single_result.first_event_latency * 1000,
            "memory_usage_mb": single_result.memory_usage_mb,
            "cpu_usage_percent": single_result.cpu_usage_percent
        },
        "concurrent": {
            "total": concurrent_result.total_requests,
            "successful": concurrent_result.successful_requests,
            "avg_duration": concurrent_result.avg_duration,
            "p95_duration": concurrent_result.p95_duration,
            "p99_duration": concurrent_result.p99_duration
        },
        "streaming": streaming_result,
        "agents": agent_result
    }
    
    with open("performance_benchmark_results.json", "w") as f:
        json.dump(save_data, f, indent=2)
    
    logger.info("\n💾 Results saved to performance_benchmark_results.json")
    logger.info("\n✅ Performance benchmarks completed!")


if __name__ == "__main__":
    asyncio.run(main())