#!/usr/bin/env python3
"""
Performance Test Module

This module provides performance benchmarking for the system:
- Coordinate transformation performance
- Network communication throughput
- End-to-end latency measurements
- CPU and memory usage monitoring

It can be run independently or through the test_runner.py script.

Usage:
    python test_performance.py --help               # Show all options
    python test_performance.py --coords             # Test coordinate transformation performance
    python test_performance.py --network            # Test network performance
    python test_performance.py --system             # Test system performance (CPU, memory)
    python test_performance.py --all                # Run all performance tests
"""

import sys
import os
import time
import argparse
import json
import socket
import threading
import statistics
import random
import queue
from typing import Dict, Tuple, List, Any, Optional

# Add the parent directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Try to import psutil for system monitoring (optional)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. System monitoring will be limited.")

class PerformanceTester:
    """Performance testing class for benchmarking system components"""
    
    def __init__(self):
        self.test_results = {}
        
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test results"""
        self.test_results[test_name] = {"passed": passed, "message": message}
        status = "✓" if passed else "✗"
        print(f"  {status} {test_name}: {message}")
    
    def benchmark_coordinate_transformation(self, iterations=10000) -> bool:
        """Benchmark coordinate transformation performance"""
        print(f"\n=== COORDINATE TRANSFORMATION BENCHMARK ({iterations} iterations) ===")
        
        try:
            # Import coordinate transformer
            from CR3_Control import CoordinateTransformer
            transformer = CoordinateTransformer()
            
            # Generate random test data
            test_data = []
            for _ in range(iterations):
                shoulder = [random.random(), random.random(), random.random()]
                wrist = [random.random(), random.random(), random.random()]
                test_data.append((shoulder, wrist))
            
            # Measure performance
            durations = []
            start_time = time.time()
            
            for i, (shoulder, wrist) in enumerate(test_data):
                iter_start = time.time()
                robot_coords = transformer.transform_to_robot_coords(shoulder, wrist)
                durations.append(time.time() - iter_start)
                
                # Print progress
                if (i + 1) % (iterations // 10) == 0:
                    print(f"  Completed {i + 1}/{iterations} iterations...")
            
            total_time = time.time() - start_time
            avg_time = total_time / iterations
            
            # Calculate statistics
            min_time = min(durations) * 1000  # Convert to ms
            max_time = max(durations) * 1000
            avg_time_ms = avg_time * 1000
            median_time = statistics.median(durations) * 1000
            p95_time = sorted(durations)[int(iterations * 0.95)] * 1000
            
            # Log results
            self.log_result("Coordinate transformation", True, 
                          f"Processed {iterations} transforms in {total_time:.2f}s")
            
            print("\nPerformance statistics:")
            print(f"  Average time: {avg_time_ms:.3f} ms per transform")
            print(f"  Median time: {median_time:.3f} ms")
            print(f"  Min time: {min_time:.3f} ms")
            print(f"  Max time: {max_time:.3f} ms")
            print(f"  95th percentile: {p95_time:.3f} ms")
            print(f"  Throughput: {iterations/total_time:.1f} transforms/second")
            
            return True
            
        except Exception as e:
            self.log_result("Coordinate transformation", False, f"Error: {e}")
            return False
    
    def benchmark_network_performance(self, duration=5, interval=0.001) -> bool:
        """Benchmark network communication performance"""
        print(f"\n=== NETWORK PERFORMANCE BENCHMARK ({duration}s) ===")
        
        try:
            # Start a test server
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('localhost', 0))  # Use any available port
            server_socket.listen(1)
            
            server_port = server_socket.getsockname()[1]
            print(f"Started test server on port {server_port}")
            
            # Create queue for received messages
            message_queue = queue.Queue()
            server_running = threading.Event()
            server_running.set()
            
            # Server thread function
            def server_thread():
                try:
                    client, addr = server_socket.accept()
                    print(f"Client connected from {addr}")
                    
                    while server_running.is_set():
                        try:
                            data = client.recv(1024)
                            if not data:
                                break
                                
                            # Try to decode messages (may contain multiple)
                            try:
                                messages = data.decode('utf-8').split('\n')
                                for msg in messages:
                                    if msg:
                                        message_queue.put(json.loads(msg))
                            except:
                                pass
                                
                        except:
                            break
                            
                    client.close()
                    
                except Exception as e:
                    print(f"Server error: {e}")
                finally:
                    server_socket.close()
            
            # Start server thread
            thread = threading.Thread(target=server_thread)
            thread.daemon = True
            thread.start()
            
            # Wait for server to start
            time.sleep(0.5)
            
            # Create client and connect to server
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(('localhost', server_port))
            
            # Send test messages
            sent_count = 0
            start_time = time.time()
            
            try:
                while time.time() - start_time < duration:
                    # Generate test message
                    test_message = {
                        "timestamp": time.time(),
                        "shoulder": [random.random(), random.random(), random.random()],
                        "wrist": [random.random(), random.random(), random.random()]
                    }
                    
                    # Send message
                    message = json.dumps(test_message) + '\n'
                    client_socket.send(message.encode('utf-8'))
                    sent_count += 1
                    
                    # Print progress every 1000 messages
                    if sent_count % 1000 == 0:
                        elapsed = time.time() - start_time
                        print(f"  Sent {sent_count} messages ({sent_count/elapsed:.1f} msg/s)")
                    
                    # Wait for next interval
                    time.sleep(interval)
                    
            except KeyboardInterrupt:
                print("Test interrupted by user")
                
            # Calculate results
            elapsed_time = time.time() - start_time
            received_count = message_queue.qsize()
            
            # Clean up
            server_running.clear()
            client_socket.close()
            server_socket.close()
            
            # Log results
            message_rate = sent_count / elapsed_time
            delivery_ratio = received_count / sent_count * 100 if sent_count > 0 else 0
            
            self.log_result("Network performance", True, 
                          f"Sent {sent_count} messages at {message_rate:.1f} msg/s")
            
            print("\nNetwork performance statistics:")
            print(f"  Messages sent: {sent_count}")
            print(f"  Messages received: {received_count}")
            print(f"  Message rate: {message_rate:.1f} messages/second")
            print(f"  Delivery ratio: {delivery_ratio:.1f}%")
            
            return True
            
        except Exception as e:
            self.log_result("Network performance", False, f"Error: {e}")
            return False
    
    def monitor_system_performance(self, duration=10, interval=0.5) -> bool:
        """Monitor system performance during a test run"""
        print(f"\n=== SYSTEM PERFORMANCE MONITORING ({duration}s) ===")
        
        if not PSUTIL_AVAILABLE:
            self.log_result("System monitoring", False, "psutil not available - cannot monitor system")
            print("Please install psutil: pip install psutil")
            return False
        
        try:
            # Get current process
            process = psutil.Process()
            
            # Storage for metrics
            cpu_percent = []
            memory_percent = []
            memory_mb = []
            
            print("Monitoring system performance...")
            start_time = time.time()
            
            while time.time() - start_time < duration:
                # Collect metrics
                cpu_percent.append(process.cpu_percent())
                memory_info = process.memory_info()
                memory_percent.append(process.memory_percent())
                memory_mb.append(memory_info.rss / (1024 * 1024))  # Convert to MB
                
                # Print current values
                current_time = time.time() - start_time
                print(f"  Time: {current_time:.1f}s, CPU: {cpu_percent[-1]:.1f}%, Memory: {memory_mb[-1]:.1f} MB")
                
                # Wait for next measurement
                time.sleep(interval)
            
            # Calculate statistics
            avg_cpu = statistics.mean(cpu_percent)
            avg_memory = statistics.mean(memory_mb)
            max_cpu = max(cpu_percent)
            max_memory = max(memory_mb)
            
            # Log results
            self.log_result("System monitoring", True, 
                          f"Average CPU: {avg_cpu:.1f}%, Memory: {avg_memory:.1f} MB")
            
            print("\nSystem performance statistics:")
            print(f"  Average CPU usage: {avg_cpu:.1f}%")
            print(f"  Maximum CPU usage: {max_cpu:.1f}%")
            print(f"  Average memory usage: {avg_memory:.1f} MB")
            print(f"  Maximum memory usage: {max_memory:.1f} MB")
            
            return True
            
        except Exception as e:
            self.log_result("System monitoring", False, f"Error: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all performance tests"""
        print("\n=== RUNNING ALL PERFORMANCE TESTS ===")
        
        # Run coordinate transformation benchmark
        coords_result = self.benchmark_coordinate_transformation(iterations=5000)
        
        # Run network performance benchmark
        network_result = self.benchmark_network_performance(duration=3)
        
        # Run system monitoring
        system_result = True
        if PSUTIL_AVAILABLE:
            system_result = self.monitor_system_performance(duration=5)
        
        # Print summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["passed"])
        
        print("\n=== PERFORMANCE TEST SUMMARY ===")
        print(f"Total tests: {total_tests}")
        print(f"Passed tests: {passed_tests}")
        
        return coords_result and network_result and system_result

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Performance Test Module")
    parser.add_argument("--coords", action="store_true", help="Benchmark coordinate transformation")
    parser.add_argument("--network", action="store_true", help="Benchmark network performance")
    parser.add_argument("--system", action="store_true", help="Monitor system performance")
    parser.add_argument("--iterations", type=int, default=10000, help="Number of iterations for coordinate benchmark")
    parser.add_argument("--duration", type=int, default=5, help="Duration for network/system tests (seconds)")
    parser.add_argument("--all", action="store_true", help="Run all performance tests")
    
    args = parser.parse_args()
    
    # Create a performance tester
    tester = PerformanceTester()
    
    # Run tests
    if args.coords or args.all:
        tester.benchmark_coordinate_transformation(args.iterations)
        
    if args.network or args.all:
        tester.benchmark_network_performance(args.duration)
        
    if args.system or args.all:
        tester.monitor_system_performance(args.duration)
        
    if not (args.coords or args.network or args.system or args.all):
        parser.print_help()

if __name__ == "__main__":
    main()
