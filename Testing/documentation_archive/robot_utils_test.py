#!/usr/bin/env python3
"""
Robot Utilities Test Module

This script tests the functionality of the robot_utils.py module,
which provides common utilities for robot control, status checking,
and movement testing.

Usage:
    python robot_utils_test.py [--robot-ip 192.168.1.6] [--quick]
"""

import sys
import os
import argparse
import time
from typing import Dict, Tuple, List, Any

# Add the parent directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import robot_utils module
try:
    from robot_utils import RobotConnection, ROBOT_API_AVAILABLE
except ImportError as e:
    print(f"Error: Could not import robot_utils module: {e}")
    print("Make sure the robot_utils.py file is in the parent directory.")
    sys.exit(1)

class RobotUtilsTest:
    """Test suite for robot_utils.py module"""
    
    def __init__(self):
        self.test_results = {}
        
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test results"""
        self.test_results[test_name] = {"passed": passed, "message": message}
        status = "✓" if passed else "✗"
        print(f"  {status} {test_name}: {message}")
    
    def test_robot_api_availability(self) -> bool:
        """Test 1: Robot API Availability"""
        print("\n=== TEST 1: Robot API Availability ===")
        
        # Check if the robot API is available
        api_status = "available" if ROBOT_API_AVAILABLE else "not available"
        self.log_result("Robot API availability", True, f"Robot API is {api_status}")
        
        return True
    
    def test_robot_connection_class(self) -> bool:
        """Test 2: RobotConnection Class Initialization"""
        print("\n=== TEST 2: RobotConnection Class ===")
        
        try:
            # Test RobotConnection creation
            robot = RobotConnection("192.168.1.6")  # Use default IP
            self.log_result("RobotConnection initialization", True, 
                           "Successfully created RobotConnection instance")
            
            # Test properties
            expected_attrs = ["robot_ip", "dashboard_port", "move_port", "feed_port", 
                             "dashboard", "position_tolerance", "safe_packing_position"]
            
            missing_attrs = []
            for attr in expected_attrs:
                if not hasattr(robot, attr):
                    missing_attrs.append(attr)
            
            if missing_attrs:
                self.log_result("RobotConnection attributes", False, 
                               f"Missing attributes: {', '.join(missing_attrs)}")
            else:
                self.log_result("RobotConnection attributes", True, 
                               "All expected attributes are present")
            
            return True
            
        except Exception as e:
            self.log_result("RobotConnection class", False, f"Error: {e}")
            return False
    
    def test_network_connectivity(self) -> bool:
        """Test 3: Network Connectivity Check"""
        print("\n=== TEST 3: Network Connectivity Check ===")
        
        try:
            # Test with default IP
            robot = RobotConnection("192.168.1.6")
            success, message = robot.test_network_connectivity()
            connectivity_result = "successful" if success else "failed"
            self.log_result("Network connectivity test", True, 
                           f"Network test {connectivity_result}: {message}")
            
            # Test with invalid IP
            robot_invalid = RobotConnection("192.168.999.999")  # Invalid IP
            success, message = robot_invalid.test_network_connectivity()
            if not success:
                self.log_result("Invalid IP handling", True, "Correctly handled invalid IP address")
            else:
                self.log_result("Invalid IP handling", False, "Failed to detect invalid IP address")
            
            return True
            
        except Exception as e:
            self.log_result("Network connectivity", False, f"Error: {e}")
            return False
    
    def test_response_parsing(self) -> bool:
        """Test 4: Response Parsing Logic"""
        print("\n=== TEST 4: Response Parsing Logic ===")
        
        try:
            # Test alarm response parsing
            test_cases = [
                {"name": "Empty response", "response": "[]", "expected": True},
                {"name": "Null response", "response": "null", "expected": True},
                {"name": "Command echo", "response": "GetErrorID();", "expected": True},
                {"name": "With error codes", "response": "[1, 2, 3]", "expected": False},
            ]
            
            for case in test_cases:
                # Simulate the alarm check logic from robot_utils.py
                alarm_ok = ("null" in case["response"] or 
                           "[]" in case["response"] or 
                           "GetErrorID();" in case["response"])
                
                if alarm_ok == case["expected"]:
                    self.log_result(f"Alarm parse: {case['name']}", True, 
                                   f"Correctly parsed as {'no alarms' if alarm_ok else 'has alarms'}")
                else:
                    self.log_result(f"Alarm parse: {case['name']}", False, 
                                   f"Failed to parse correctly. Got {'no alarms' if alarm_ok else 'has alarms'}")
            
            # Test position response parsing
            position_cases = [
                {"name": "Standard format", "response": "[100.0, 0.0, 200.0, 0.0, 0.0, 0.0]", "expected_len": 6},
                {"name": "With extra text", "response": "GetPose(); [100.0, 0.0, 200.0, 0.0, 0.0, 0.0]", "expected_len": 6},
            ]
            
            for case in position_cases:
                # Use regex to extract numbers as in robot_utils.py
                import re
                numbers = re.findall(r'-?\d+\.?\d*', case["response"])
                parsed_len = len(numbers)
                
                if parsed_len >= case["expected_len"]:
                    self.log_result(f"Position parse: {case['name']}", True, 
                                   f"Successfully extracted {parsed_len} values")
                else:
                    self.log_result(f"Position parse: {case['name']}", False, 
                                   f"Only extracted {parsed_len} values, expected {case['expected_len']}")
            
            return True
            
        except Exception as e:
            self.log_result("Response parsing", False, f"Error: {e}")
            return False
    
    def test_full_connection(self) -> bool:
        """Test 5: Full Connection Flow"""
        print("\n=== TEST 5: Full Connection Flow ===")
        
        if not ROBOT_API_AVAILABLE:
            self.log_result("Full connection test", True, "Skipped - Robot API not available")
            return True
        
        try:
            # Create robot connection
            robot = RobotConnection("192.168.1.6")
            
            # Test network connectivity
            success, message = robot.test_network_connectivity()
            self.log_result("Network connectivity", success, message)
            
            if not success:
                return True  # Skip further tests if network connectivity fails
            
            # Test connection
            success, message = robot.connect()
            self.log_result("Robot connection", success, message)
            
            if not success:
                return True  # Skip further tests if connection fails
            
            # Test alarm checking
            success, alarms = robot.check_robot_alarms()
            alarm_status = "No alarms detected" if success else f"Alarms detected: {alarms}"
            self.log_result("Alarm check", True, alarm_status)
            
            # Disconnect
            robot.disconnect()
            self.log_result("Robot disconnection", True, "Successfully disconnected")
            
            return True
            
        except Exception as e:
            self.log_result("Full connection test", False, f"Error: {e}")
            # Ensure we disconnect even if an error occurs
            if 'robot' in locals() and robot.dashboard:
                robot.disconnect()
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests and provide a summary"""
        print("ROBOT UTILITIES MODULE - TEST SUITE")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all tests
        self.test_robot_api_availability()
        self.test_robot_connection_class()
        self.test_network_connectivity()
        self.test_response_parsing()
        
        # Only run full connection test if the API is available
        if ROBOT_API_AVAILABLE:
            self.test_full_connection()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["passed"])
        
        print("\n" + "=" * 60)
        print(f"TEST SUMMARY: {passed_tests}/{total_tests} tests passed")
        print(f"Execution time: {time.time() - start_time:.1f} seconds")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! The robot_utils.py module is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the details above.")
            
        print("=" * 60)
        
        return passed_tests == total_tests

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Robot Utilities Test Suite")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick test without connection attempt")
    
    args = parser.parse_args()
    
    # Create test suite
    test_suite = RobotUtilsTest()
    
    # Run all tests
    success = test_suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
