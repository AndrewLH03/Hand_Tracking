#!/usr/bin/env python3
"""
Unified Test Runner for Robotic Arm Hand Tracking System

This is the main entry point for running all system tests.
It provides a unified interface to run robot, communication, and performance tests.

Usage:
    python test_runner.py --help                # Show all options
    python test_runner.py --robot               # Run robot tests
    python test_runner.py --communication       # Run communication tests
    python test_runner.py --performance         # Run performance tests
    python test_runner.py --all                 # Run all tests
    python test_runner.py --quick               # Run quick tests only
"""

import sys
import os
import time
import argparse
import importlib.util
from typing import Dict, Any, List, Tuple

def load_module(name, path):
    """Dynamically load a module from path"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class TestRunner:
    """Unified test runner for all system tests"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()
        
        # Ensure we're in the Testing directory
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Load test modules
        self.robot_test = None
        self.communication_test = None
        self.performance_test = None
        
        self._load_test_modules()
        
    def _load_test_modules(self):
        """Load all test modules"""
        # Load robot test module
        robot_path = os.path.join(self.base_dir, "test_robot.py")
        if os.path.exists(robot_path):
            try:
                self.robot_test = load_module("test_robot", robot_path)
                print("✓ Loaded robot test module")
            except Exception as e:
                print(f"✗ Failed to load robot test module: {e}")
        
        # Load communication test module
        comm_path = os.path.join(self.base_dir, "test_communication.py")
        if os.path.exists(comm_path):
            try:
                self.communication_test = load_module("test_communication", comm_path)
                print("✓ Loaded communication test module")
            except Exception as e:
                print(f"✗ Failed to load communication test module: {e}")
        
        # Load performance test module
        perf_path = os.path.join(self.base_dir, "test_performance.py")
        if os.path.exists(perf_path):
            try:
                self.performance_test = load_module("test_performance", perf_path)
                print("✓ Loaded performance test module")
            except Exception as e:
                print(f"✗ Failed to load performance test module: {e}")
    
    def run_robot_tests(self, robot_ip="192.168.1.6", quick=False):
        """Run robot tests"""
        if not self.robot_test:
            print("✗ Robot test module not available")
            return False
        
        try:
            # Create a robot tester
            tester = self.robot_test.RobotTester(robot_ip)
            
            if quick:
                # Only run connection and utils tests in quick mode
                print("\n=== QUICK ROBOT TESTS ===")
                tester.test_connection()
                tester.test_robot_utils()
            else:
                # Run all robot tests
                tester.run_all_tests()
            
            # Merge results
            self.test_results.update(tester.test_results)
            return True
            
        except Exception as e:
            print(f"✗ Error running robot tests: {e}")
            return False
    
    def run_communication_tests(self, host="localhost", port=8888, quick=False):
        """Run communication tests"""
        if not self.communication_test:
            print("✗ Communication test module not available")
            return False
        
        try:
            # Create a communication tester
            tester = self.communication_test.CommunicationTester(host, port)
            
            if quick:
                # Only run protocol test in quick mode
                print("\n=== QUICK COMMUNICATION TESTS ===")
                tester.test_protocol()
            else:
                # Run all communication tests
                tester.run_all_tests(include_continuous=False)
            
            # Merge results
            self.test_results.update(tester.test_results)
            return True
            
        except Exception as e:
            print(f"✗ Error running communication tests: {e}")
            return False
    
    def run_performance_tests(self, quick=False):
        """Run performance tests"""
        if not self.performance_test:
            print("✗ Performance test module not available")
            return False
        
        try:
            # Create a performance tester
            tester = self.performance_test.PerformanceTester()
            
            if quick:
                # Only run coordinate benchmark with fewer iterations
                print("\n=== QUICK PERFORMANCE TESTS ===")
                tester.benchmark_coordinate_transformation(iterations=1000)
            else:
                # Run all performance tests
                tester.run_all_tests()
            
            # Merge results
            self.test_results.update(tester.test_results)
            return True
            
        except Exception as e:
            print(f"✗ Error running performance tests: {e}")
            return False
    
    def run_all_tests(self, robot_ip="192.168.1.6", quick=False):
        """Run all tests"""
        print("\n" + "="*60)
        print("HAND TRACKING ROBOT CONTROL - COMPREHENSIVE TEST SUITE")
        print("="*60)
        
        # Run robot tests
        robot_success = self.run_robot_tests(robot_ip, quick)
        
        # Run communication tests
        comm_success = self.run_communication_tests(quick=quick)
        
        # Run performance tests
        perf_success = self.run_performance_tests(quick)
        
        # Print summary
        self.print_summary()
        
        return robot_success and comm_success and perf_success
    
    def print_summary(self):
        """Print test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["passed"])
        
        print("\n" + "="*60)
        print(f"TEST SUMMARY: {passed_tests}/{total_tests} tests passed")
        print(f"Execution time: {time.time() - self.start_time:.1f} seconds")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Your system is ready to use.")
        else:
            print("⚠️  Some tests failed. Check the details above.")
            
        print("="*60)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Unified Test Runner for Robotic Arm Hand Tracking")
    parser.add_argument("--robot", action="store_true", help="Run robot tests")
    parser.add_argument("--communication", action="store_true", help="Run communication tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument("--robot-ip", type=str, default="192.168.1.6", help="Robot IP address")
    parser.add_argument("--host", type=str, default="localhost", help="Server host address")
    parser.add_argument("--port", type=int, default=8888, help="Server port")
    
    args = parser.parse_args()
    
    # Create test runner
    runner = TestRunner()
    
    # Run tests
    if args.robot or args.all:
        runner.run_robot_tests(args.robot_ip, args.quick)
        
    if args.communication or args.all:
        runner.run_communication_tests(args.host, args.port, args.quick)
        
    if args.performance or args.all:
        runner.run_performance_tests(args.quick)
        
    if not (args.robot or args.communication or args.performance or args.all):
        parser.print_help()
    else:
        runner.print_summary()

if __name__ == "__main__":
    main()
