#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Control Performance Benchmarks

Performance benchmarks to ensure the consolidated robot control package
maintains or improves performance compared to the original scattered implementation.
"""

import sys
import os
import time
import gc
import psutil
import statistics
from typing import Dict, List, Tuple, Callable, Any
from contextlib import contextmanager
from memory_profiler import profile
import cProfile
import pstats
from io import StringIO

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from robot_control import (
    parse_api_response, safe_float_conversion, safe_int_conversion,
    format_position, validate_position_values, calculate_movement_time,
    retry_operation, ConnectionManager, RobotSystem,
    get_logger, setup_logging
)


class BenchmarkTimer:
    """Context manager for timing operations"""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        
    @property
    def elapsed_time(self) -> float:
        if self.start_time is not None and self.end_time is not None:
            return self.end_time - self.start_time
        return 0.0


class PerformanceBenchmark:
    """Performance benchmark utilities"""
    
    def __init__(self):
        self.results = {}
        self.logger = get_logger(__name__)
        
    @contextmanager
    def measure_time(self, operation_name: str):
        """Context manager to measure execution time"""
        start_time = time.perf_counter()
        start_memory = self.get_memory_usage()
        yield
        end_time = time.perf_counter()
        end_memory = self.get_memory_usage()
        
        execution_time = end_time - start_time
        memory_delta = end_memory - start_memory
        
        self.results[operation_name] = {
            'execution_time': execution_time,
            'memory_delta': memory_delta,
            'timestamp': time.time()
        }
        
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def run_multiple_times(self, func: Callable, iterations: int = 1000) -> Dict[str, float]:
        """Run a function multiple times and collect statistics"""
        times = []
        
        # Warm up
        for _ in range(10):
            func()
        
        # Actual measurements
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append(end - start)
        
        return {
            'min_time': min(times),
            'max_time': max(times),
            'mean_time': statistics.mean(times),
            'median_time': statistics.median(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
            'iterations': iterations
        }


class RobotControlBenchmarks:
    """Main benchmarking class for robot control package"""
    
    def __init__(self):
        self.benchmark = PerformanceBenchmark()
        self.logger = get_logger(__name__)
        self.results = {}
        
    def benchmark_imports(self) -> Dict[str, Any]:
        """Benchmark import performance"""
        print("Running import benchmarks...")
        
        # Test cold import
        with self.benchmark.measure_time('cold_import'):
            import importlib
            if 'robot_control' in sys.modules:
                del sys.modules['robot_control']
            import robot_control
        
        # Test warm import
        with self.benchmark.measure_time('warm_import'):
            import robot_control
        
        return self.benchmark.results
    
    def benchmark_utility_functions(self) -> Dict[str, Any]:
        """Benchmark utility function performance"""
        print("Running utility function benchmarks...")
        
        # Test parse_api_response
        test_response = "ok,1,2,3.5,4.2,-1.0"
        stats = self.benchmark.run_multiple_times(
            lambda: parse_api_response(test_response), 10000
        )
        self.results['parse_api_response'] = stats
        
        # Test safe_float_conversion
        stats = self.benchmark.run_multiple_times(
            lambda: safe_float_conversion("3.14159"), 10000
        )
        self.results['safe_float_conversion'] = stats
        
        # Test format_position
        stats = self.benchmark.run_multiple_times(
            lambda: format_position([100.5, 200.3, 150.7, 45.0, 90.0, 0.0]), 5000
        )
        self.results['format_position'] = stats
        
        # Test validate_position_values
        test_position = [100, 200, 150, 45, 90, 0]
        stats = self.benchmark.run_multiple_times(
            lambda: validate_position_values(test_position), 5000
        )
        self.results['validate_position_values'] = stats
        
        return self.results
    
    def benchmark_connection_manager(self) -> Dict[str, Any]:
        """Benchmark connection manager operations"""
        print("Running connection manager benchmarks...")
        
        # Test connection manager initialization
        with self.benchmark.measure_time('connection_manager_init'):
            conn_mgr = ConnectionManager("192.168.1.6", 29999)
        
        return self.benchmark.results
    
    def benchmark_robot_system(self) -> Dict[str, Any]:
        """Benchmark robot system operations (mock mode)"""
        print("Running robot system benchmarks...")
        
        # Test robot system initialization
        with self.benchmark.measure_time('robot_system_init'):
            robot = RobotSystem("192.168.1.6")
        
        return self.benchmark.results
    
    def benchmark_concurrent_operations(self) -> Dict[str, Any]:
        """Benchmark concurrent operations"""
        print("Running concurrent operation benchmarks...")
        import threading
        
        def worker_task():
            for _ in range(100):
                parse_api_response("ok,1,2,3.5")
                safe_float_conversion("3.14159")
        
        # Single thread
        with self.benchmark.measure_time('single_thread'):
            worker_task()
        
        # Multiple threads
        with self.benchmark.measure_time('multi_thread'):
            threads = []
            for _ in range(4):
                thread = threading.Thread(target=worker_task)
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
        
        return self.benchmark.results
    
    @profile
    def memory_intensive_operations(self):
        """Memory-intensive operations for profiling"""
        # Simulate heavy operations
        large_data = []
        for i in range(10000):
            position = format_position([i, i+1, i+2, i+3, i+4, i+5])
            large_data.append(position)
        
        # Process the data
        for pos in large_data:
            parse_api_response(f"ok,{pos}")
        
        return len(large_data)
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all performance benchmarks"""
        print("=" * 60)
        print("ROBOT CONTROL PERFORMANCE BENCHMARKS")
        print("=" * 60)
        
        all_results = {}
        
        try:
            # Import benchmarks
            import_results = self.benchmark_imports()
            all_results['imports'] = import_results
            
            # Utility function benchmarks
            utility_results = self.benchmark_utility_functions()
            all_results['utilities'] = utility_results
            
            # Connection manager benchmarks
            connection_results = self.benchmark_connection_manager()
            all_results['connection_manager'] = connection_results
            
            # Robot system benchmarks
            robot_results = self.benchmark_robot_system()
            all_results['robot_system'] = robot_results
            
            # Concurrent operation benchmarks
            concurrent_results = self.benchmark_concurrent_operations()
            all_results['concurrent_ops'] = concurrent_results
            
            # Memory profiling
            print("Running memory-intensive operations...")
            operations_count = self.memory_intensive_operations()
            all_results['memory_operations'] = {'operations_count': operations_count}
            
        except Exception as e:
            self.logger.error(f"Benchmark error: {e}")
            all_results['error'] = str(e)
        
        return all_results
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a performance report"""
        report = []
        report.append("ROBOT CONTROL PERFORMANCE REPORT")
        report.append("=" * 50)
        report.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        for category, data in results.items():
            if category == 'error':
                report.append(f"ERROR: {data}")
                continue
                
            report.append(f"{category.upper()} BENCHMARKS:")
            report.append("-" * 30)
            
            if isinstance(data, dict):
                for operation, metrics in data.items():
                    if isinstance(metrics, dict):
                        if 'execution_time' in metrics:
                            report.append(f"  {operation}: {metrics['execution_time']:.6f}s")
                            if 'memory_delta' in metrics:
                                report.append(f"    Memory delta: {metrics['memory_delta']:.2f} MB")
                        elif 'mean_time' in metrics:
                            report.append(f"  {operation}:")
                            report.append(f"    Mean: {metrics['mean_time']:.6f}s")
                            report.append(f"    Min: {metrics['min_time']:.6f}s")
                            report.append(f"    Max: {metrics['max_time']:.6f}s")
                            report.append(f"    Std Dev: {metrics['std_dev']:.6f}s")
                            report.append(f"    Iterations: {metrics['iterations']}")
                    else:
                        report.append(f"  {operation}: {metrics}")
            report.append("")
        
        return "\n".join(report)


def main():
    """Main benchmarking function"""
    benchmark_suite = RobotControlBenchmarks()
    results = benchmark_suite.run_all_benchmarks()
    
    # Generate and print report
    report = benchmark_suite.generate_report(results)
    print(report)
    
    # Save report to file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_file = f"performance_report_{timestamp}.txt"
    
    try:
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\nPerformance report saved to: {report_file}")
    except Exception as e:
        print(f"Failed to save report: {e}")
    
    return results


if __name__ == "__main__":
    main()
