#!/usr/bin/env python3
"""
System Benchmark and Performance Test

This script benchmarks the performance of various system components
and provides detailed performance metrics.

Usage:
    python benchmark.py                     # Run all benchmarks
    python benchmark.py --coords-only       # Test coordinate transformation only
    python benchmark.py --network-only      # Test network performance only
    python benchmark.py --verbose           # Show detailed output
"""

import argparse
import time
import threading
import json
import statistics
from typing import List, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class PerformanceBenchmark:
    """Benchmark system performance"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = {}
        
    def log(self, message: str):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            print(f"[BENCHMARK] {message}")
            
    def benchmark_coordinate_transformation(self, iterations: int = 10000) -> Dict[str, float]:
        """Benchmark coordinate transformation performance"""
        print(f"\n=== Coordinate Transformation Benchmark ({iterations:,} iterations) ===")
        
        try:
            from CR3_Control import CoordinateTransformer
            
            transformer = CoordinateTransformer(workspace_size=400.0, height_offset=200.0)
            
            # Generate test data
            import random
            test_data = []
            for _ in range(iterations):
                shoulder = [random.random(), random.random(), random.random()]
                wrist = [random.random(), random.random(), random.random()]
                test_data.append((shoulder, wrist))
                
            # Benchmark transformation
            times = []
            results = []
            
            print("Running coordinate transformations...")
            start_time = time.time()
            
            for i, (shoulder, wrist) in enumerate(test_data):
                transform_start = time.perf_counter()
                result = transformer.transform_to_robot_coords(shoulder, wrist)
                transform_end = time.perf_counter()
                
                times.append((transform_end - transform_start) * 1000)  # Convert to ms
                results.append(result)
                
                if self.verbose and (i + 1) % 1000 == 0:
                    self.log(f"Completed {i + 1:,}/{iterations:,} transformations")
                    
            total_time = time.time() - start_time
            
            # Calculate statistics
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            median_time = statistics.median(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0
            
            # Results
            benchmark_results = {
                "iterations": iterations,
                "total_time": total_time,
                "avg_time_ms": avg_time,
                "min_time_ms": min_time,
                "max_time_ms": max_time,
                "median_time_ms": median_time,
                "std_dev_ms": std_dev,
                "transforms_per_second": iterations / total_time
            }
            
            print(f"✓ Transformation Rate: {benchmark_results['transforms_per_second']:,.0f} transforms/second")
            print(f"✓ Average Time: {avg_time:.3f} ms per transformation")
            print(f"✓ Time Range: {min_time:.3f} - {max_time:.3f} ms")
            print(f"✓ Standard Deviation: {std_dev:.3f} ms")
            
            # Validate results (check that coordinates are reasonable)
            valid_results = 0
            for x, y, z in results:
                if -300 <= x <= 300 and -300 <= y <= 300 and 0 <= z <= 600:
                    valid_results += 1
                    
            print(f"✓ Valid Results: {valid_results}/{iterations} ({100*valid_results/iterations:.1f}%)")
            
            return benchmark_results
            
        except Exception as e:
            print(f"✗ Coordinate transformation benchmark failed: {e}")
            return {}
            
    def benchmark_json_serialization(self, iterations: int = 50000) -> Dict[str, float]:
        """Benchmark JSON serialization/deserialization performance"""
        print(f"\n=== JSON Serialization Benchmark ({iterations:,} iterations) ===")
        
        try:
            # Generate test data
            test_messages = []
            for i in range(iterations):
                message = {
                    "timestamp": time.time() + i,
                    "shoulder": [0.5 + i*0.001, 0.3, 0.2],
                    "wrist": [0.6 + i*0.001, 0.4, 0.3],
                    "frame_id": i
                }
                test_messages.append(message)
                
            # Benchmark serialization
            serialize_times = []
            deserialize_times = []
            serialized_data = []
            
            print("Running JSON serialization...")
            
            # Serialize
            for i, message in enumerate(test_messages):
                start = time.perf_counter()
                serialized = json.dumps(message)
                end = time.perf_counter()
                
                serialize_times.append((end - start) * 1000000)  # Convert to microseconds
                serialized_data.append(serialized)
                
                if self.verbose and (i + 1) % 10000 == 0:
                    self.log(f"Serialized {i + 1:,}/{iterations:,} messages")
                    
            # Deserialize
            print("Running JSON deserialization...")
            for i, serialized in enumerate(serialized_data):
                start = time.perf_counter()
                deserialized = json.loads(serialized)
                end = time.perf_counter()
                
                deserialize_times.append((end - start) * 1000000)  # Convert to microseconds
                
                if self.verbose and (i + 1) % 10000 == 0:
                    self.log(f"Deserialized {i + 1:,}/{iterations:,} messages")
                    
            # Calculate statistics
            serialize_avg = statistics.mean(serialize_times)
            deserialize_avg = statistics.mean(deserialize_times)
            
            # Average message size
            avg_size = statistics.mean([len(data.encode('utf-8')) for data in serialized_data[:1000]])
            
            benchmark_results = {
                "iterations": iterations,
                "serialize_avg_us": serialize_avg,
                "deserialize_avg_us": deserialize_avg,
                "total_avg_us": serialize_avg + deserialize_avg,
                "avg_message_size_bytes": avg_size,
                "messages_per_second": 1000000 / (serialize_avg + deserialize_avg)
            }
            
            print(f"✓ Serialization: {serialize_avg:.1f} μs per message")
            print(f"✓ Deserialization: {deserialize_avg:.1f} μs per message")
            print(f"✓ Total JSON Processing: {serialize_avg + deserialize_avg:.1f} μs per message")
            print(f"✓ Average Message Size: {avg_size:.0f} bytes")
            print(f"✓ Processing Rate: {benchmark_results['messages_per_second']:,.0f} messages/second")
            
            return benchmark_results
            
        except Exception as e:
            print(f"✗ JSON serialization benchmark failed: {e}")
            return {}
            
    def benchmark_tcp_throughput(self, duration: int = 10) -> Dict[str, float]:
        """Benchmark TCP communication throughput"""
        print(f"\n=== TCP Throughput Benchmark ({duration} seconds) ===")
        
        try:
            from CR3_Control import HandTrackingServer
            import socket
            
            # Start server
            test_port = 9998
            server = HandTrackingServer('localhost', test_port)
            
            server_thread = threading.Thread(target=server.start_server)
            server_thread.daemon = True
            server_thread.start()
            
            time.sleep(1)  # Wait for server to start
            
            # Connect client
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('localhost', test_port))
            
            # Send data continuously
            messages_sent = 0
            bytes_sent = 0
            start_time = time.time()
            
            print("Sending continuous data...")
            
            while time.time() - start_time < duration:
                message = {
                    "timestamp": time.time(),
                    "shoulder": [0.5, 0.3, 0.2],
                    "wrist": [0.6, 0.4, 0.3],
                    "frame_id": messages_sent
                }
                
                data = json.dumps(message) + '\n'
                bytes_data = data.encode('utf-8')
                
                client.send(bytes_data)
                messages_sent += 1
                bytes_sent += len(bytes_data)
                
                if self.verbose and messages_sent % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = messages_sent / elapsed
                    self.log(f"Sent {messages_sent:,} messages ({rate:.0f} msg/sec)")
                    
            elapsed_time = time.time() - start_time
            
            # Cleanup
            client.close()
            server.stop_server()
            
            # Calculate results
            message_rate = messages_sent / elapsed_time
            throughput_mbps = (bytes_sent * 8) / (elapsed_time * 1000000)  # Megabits per second
            avg_message_size = bytes_sent / messages_sent if messages_sent > 0 else 0
            
            benchmark_results = {
                "duration": elapsed_time,
                "messages_sent": messages_sent,
                "bytes_sent": bytes_sent,
                "message_rate": message_rate,
                "throughput_mbps": throughput_mbps,
                "avg_message_size": avg_message_size
            }
            
            print(f"✓ Messages Sent: {messages_sent:,}")
            print(f"✓ Data Sent: {bytes_sent:,} bytes ({bytes_sent/1024:.1f} KB)")
            print(f"✓ Message Rate: {message_rate:.0f} messages/second")
            print(f"✓ Throughput: {throughput_mbps:.2f} Mbps")
            print(f"✓ Average Message Size: {avg_message_size:.0f} bytes")
            
            return benchmark_results
            
        except Exception as e:
            print(f"✗ TCP throughput benchmark failed: {e}")
            return {}
            
    def run_all_benchmarks(self):
        """Run complete benchmark suite"""
        print("HAND TRACKING ROBOT CONTROL - PERFORMANCE BENCHMARK")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run benchmarks
        self.results["coordinate_transform"] = self.benchmark_coordinate_transformation(10000)
        self.results["json_processing"] = self.benchmark_json_serialization(50000)
        self.results["tcp_throughput"] = self.benchmark_tcp_throughput(10)
        
        total_time = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        
        if "coordinate_transform" in self.results and self.results["coordinate_transform"]:
            ct = self.results["coordinate_transform"]
            print(f"Coordinate Transformation: {ct['transforms_per_second']:,.0f} transforms/sec")
            
        if "json_processing" in self.results and self.results["json_processing"]:
            jp = self.results["json_processing"]
            print(f"JSON Processing: {jp['messages_per_second']:,.0f} messages/sec")
            
        if "tcp_throughput" in self.results and self.results["tcp_throughput"]:
            tcp = self.results["tcp_throughput"]
            print(f"TCP Throughput: {tcp['message_rate']:.0f} messages/sec, {tcp['throughput_mbps']:.2f} Mbps")
            
        print(f"\nTotal benchmark time: {total_time:.1f} seconds")
        print("=" * 60)
        
        # Performance assessment
        self.assess_performance()
        
    def assess_performance(self):
        """Assess system performance and provide recommendations"""
        print("\nPERFORMANCE ASSESSMENT")
        print("-" * 30)
        
        recommendations = []
        
        # Check coordinate transformation performance
        if "coordinate_transform" in self.results and self.results["coordinate_transform"]:
            ct = self.results["coordinate_transform"]
            if ct["transforms_per_second"] > 50000:
                print("✓ Coordinate transformation: EXCELLENT")
            elif ct["transforms_per_second"] > 20000:
                print("✓ Coordinate transformation: GOOD")
            elif ct["transforms_per_second"] > 10000:
                print("⚠ Coordinate transformation: ACCEPTABLE")
            else:
                print("✗ Coordinate transformation: POOR")
                recommendations.append("Consider optimizing coordinate transformation algorithm")
                
        # Check TCP throughput
        if "tcp_throughput" in self.results and self.results["tcp_throughput"]:
            tcp = self.results["tcp_throughput"]
            if tcp["message_rate"] > 5000:
                print("✓ TCP throughput: EXCELLENT")
            elif tcp["message_rate"] > 1000:
                print("✓ TCP throughput: GOOD")
            elif tcp["message_rate"] > 500:
                print("⚠ TCP throughput: ACCEPTABLE")
            else:
                print("✗ TCP throughput: POOR")
                recommendations.append("Check network configuration and reduce TCP overhead")
                
        # Real-time capability assessment
        min_required_rate = 30  # 30 Hz for smooth robot control
        
        print(f"\nReal-time Capability Assessment (minimum {min_required_rate} Hz required):")
        
        if "tcp_throughput" in self.results and self.results["tcp_throughput"]:
            tcp_rate = self.results["tcp_throughput"]["message_rate"]
            if tcp_rate >= min_required_rate:
                print(f"✓ System can handle real-time control at {tcp_rate:.0f} Hz")
            else:
                print(f"✗ System may struggle with real-time control (only {tcp_rate:.0f} Hz)")
                recommendations.append("Optimize system for higher message rates")
                
        if recommendations:
            print("\nRecommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        else:
            print("\n🎉 System performance is optimal for real-time robot control!")

def main():
    parser = argparse.ArgumentParser(description="Hand Tracking Robot Control Performance Benchmark")
    parser.add_argument("--coords-only", action="store_true", help="Test coordinate transformation only")
    parser.add_argument("--network-only", action="store_true", help="Test network performance only")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--iterations", type=int, default=10000, help="Number of iterations for coordinate test")
    parser.add_argument("--duration", type=int, default=10, help="Duration for network test (seconds)")
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark(verbose=args.verbose)
    
    try:
        if args.coords_only:
            benchmark.benchmark_coordinate_transformation(args.iterations)
        elif args.network_only:
            benchmark.benchmark_tcp_throughput(args.duration)
        else:
            benchmark.run_all_benchmarks()
            
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
    except Exception as e:
        print(f"Benchmark failed: {e}")

if __name__ == "__main__":
    main()
