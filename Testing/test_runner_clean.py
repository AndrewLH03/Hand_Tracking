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
    """Unified test runner for all system components"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.test_results = {}
        self.robot_test = None
        self.communication_test = None
        self.performance_test = None
        
        # Load test modules
        self.load_test_modules()
    
    def load_test_modules(self):
        """Load all available test modules"""
        print("Loading test modules...")
        
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
                # Only run connection and system tests in quick mode
                print("\n=== QUICK ROBOT TESTS ===")
                tester.test_connection()
                tester.test_robot_system()
            else:
                # Run all robot tests
                tester.run_all_tests()
            
            # Merge results
            self.test_results.update(tester.test_results)
            return True
            
        except Exception as e:
            print(f"✗ Error running robot tests: {e}")
            return False
    
    def run_communication_tests(self):
        """Run communication tests"""
        if not self.communication_test:
            print("✗ Communication test module not available")
            return False
        
        try:
            print("\n=== COMMUNICATION TESTS ===")
            tester = self.communication_test.CommunicationTester()
            tester.run_all_tests()
            self.test_results.update(tester.test_results)
            return True
        except Exception as e:
            print(f"✗ Error running communication tests: {e}")
            return False
    
    def run_performance_tests(self):
        """Run performance tests"""
        if not self.performance_test:
            print("✗ Performance test module not available")
            return False
        
        try:
            print("\n=== PERFORMANCE TESTS ===")
            tester = self.performance_test.PerformanceTester()
            tester.run_all_tests()
            self.test_results.update(tester.test_results)
            return True
        except Exception as e:
            print(f"✗ Error running performance tests: {e}")
            return False
    
    def run_all_tests(self, robot_ip="192.168.1.6", quick=False):
        """Run all available tests"""
        print("\n" + "="*60)
        print("🧪 RUNNING ALL SYSTEM TESTS")
        print("="*60)
        
        success_count = 0
        total_count = 0
        
        # Robot tests
        total_count += 1
        if self.run_robot_tests(robot_ip, quick):
            success_count += 1
        
        # Communication tests
        if self.communication_test:
            total_count += 1
            if self.run_communication_tests():
                success_count += 1
        
        # Performance tests (skip in quick mode)
        if not quick and self.performance_test:
            total_count += 1
            if self.run_performance_tests():
                success_count += 1
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"Tests passed: {success_count}/{total_count}")
        
        if success_count == total_count:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            print("❌ SOME TESTS FAILED")
            return False
    
    def show_available_tests(self):
        """Show which test modules are available"""
        print("\n📋 Available Test Modules:")
        print("="*40)
        
        modules = [
            ("Robot Tests", self.robot_test),
            ("Communication Tests", self.communication_test),
            ("Performance Tests", self.performance_test)
        ]
        
        for name, module in modules:
            status = "✓ Available" if module else "✗ Not found"
            print(f"{name:20} {status}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Unified Test Runner for Robotic Arm Hand Tracking System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--robot", action="store_true", 
                       help="Run robot tests")
    parser.add_argument("--communication", action="store_true", 
                       help="Run communication tests")
    parser.add_argument("--performance", action="store_true", 
                       help="Run performance tests")
    parser.add_argument("--all", action="store_true", 
                       help="Run all tests")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick tests only (no time-consuming tests)")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    parser.add_argument("--list", action="store_true", 
                       help="List available test modules")
    
    args = parser.parse_args()
    
    # Create test runner
    runner = TestRunner()
    
    # Handle list command
    if args.list:
        runner.show_available_tests()
        return
    
    # If no specific test is requested, show help
    if not any([args.robot, args.communication, args.performance, args.all]):
        parser.print_help()
        print("\nUse --list to see available test modules")
        return
    
    # Run requested tests
    start_time = time.time()
    success = True
    
    if args.all:
        success = runner.run_all_tests(args.robot_ip, args.quick)
    else:
        if args.robot:
            success &= runner.run_robot_tests(args.robot_ip, args.quick)
        if args.communication:
            success &= runner.run_communication_tests()
        if args.performance and not args.quick:
            success &= runner.run_performance_tests()
    
    # Final summary
    duration = time.time() - start_time
    print(f"\n⏱️  Total test duration: {duration:.2f} seconds")
    
    if success:
        print("🎉 Test run completed successfully!")
        sys.exit(0)
    else:
        print("❌ Test run completed with failures!")
        sys.exit(1)


if __name__ == "__main__":
    main()
