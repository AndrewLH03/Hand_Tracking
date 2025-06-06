#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CR3 Robot Pre-flight Verification Script

This script performs comprehensive testing of the CR3 robot connection and movement
capabilities before running the main hand tracking system. Contains the complete
perform_preflight_check method moved from robot_utils.py and robot_control.py.

Usage:
    python robot_preflight_check.py [--robot-ip 192.168.1.6] [--quick] [--timeout 15]

Options:
    --robot-ip IP    Robot IP address (default: 192.168.1.6)
    --quick          Run quick test (no movement)
    --timeout SEC    Test timeout in seconds (default: 10)
"""

import sys
import time
import argparse
from typing import Dict, Tuple
from robot_control.robot_control import RobotSystem
from Testing import RobotTester


class RobotPreflightChecker:
    """Complete robot preflight checking functionality"""
    
    def __init__(self, robot_ip: str = "192.168.1.6", timeout: float = 10.0):
        self.robot_ip = robot_ip
        self.timeout = timeout
        self.robot_tester = RobotTester(robot_ip, timeout)
        
    def perform_preflight_check(self) -> Tuple[bool, Dict[str, bool], Dict[str, str]]:
        """
        Perform a comprehensive preflight check using shared testing utilities
        
        Returns:
            (overall_success, test_results, test_messages)
        """
        print("\n" + "="*60)
        print("🚀 COMPREHENSIVE ROBOT PRE-FLIGHT CHECK")
        print("="*60)
        
        # Use shared testing utilities for consistent behavior
        overall_success, test_results, test_messages = self.robot_tester.run_full_test()
          # Enhanced reporting with detailed breakdown
        print("\n" + "="*60)
        print("📋 PRE-FLIGHT CHECK SUMMARY")
        print("="*60)
        
        for test_name, passed in test_results.items():
            status = "✅" if passed else "❌"
            message = test_messages[test_name]
            print(f"{status} {test_name}: {message}")
        
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        print(f"\nTests passed: {passed_tests}/{total_tests}")
        
        if overall_success:
            print("\n🎉 ALL TESTS PASSED - Robot ready for operation!")
        else:
            print(f"\n❌ {total_tests - passed_tests} test(s) failed - Check issues above")
        
        return overall_success, test_results, test_messages
    
    def run_quick_test(self) -> bool:
        """Run quick test without movement using shared utilities"""
        print("🔧 QUICK ROBOT CHECK")
        print("=" * 30)
        
        success, message = self.robot_tester.run_quick_test()
        
        status_text = "✅ QUICK CHECK PASSED" if success else "❌ QUICK CHECK FAILED"
        print(f"\n{status_text}: {message}")
        return success
    
    def cleanup(self):
        """Clean up connections"""
        self.robot_tester.cleanup()


def main():
    """Main function - run preflight check"""
    parser = argparse.ArgumentParser(description="CR3 Robot Pre-flight Check")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick test without movement")
    parser.add_argument("--timeout", type=float, default=10.0,
                       help="Test timeout in seconds (default: 10)")
    
    args = parser.parse_args()
    
    print("🚀 ROBOT PRE-FLIGHT CHECK STARTING")
    if args.quick:
        print("(QUICK MODE - No Movement Test)")
    print(f"Robot IP: {args.robot_ip}")
    
    # Create preflight checker
    checker = RobotPreflightChecker(args.robot_ip, args.timeout)
    
    try:
        if args.quick:
            success = checker.run_quick_test()
        else:
            success, results, messages = checker.perform_preflight_check()
        
        return success
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Pre-flight check cancelled by user")
        return False
    except Exception as e:
        print(f"\n❌ Pre-flight check error: {e}")
        return False
    finally:
        # Always disconnect properly
        checker.cleanup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
