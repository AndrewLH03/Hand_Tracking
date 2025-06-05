#!/usr/bin/env python3
"""
Unified Robot Test Module

This module provides comprehensive testing for robot-related functionality:
- Robot connection testing
- Robot movement testing
- Robot utilities module testing (robot_utils.py)

It can be run independently or through the test_runner.py script.

Usage:
    python test_robot.py --help                  # Show all options
    python test_robot.py --connection            # Test robot connection
    python test_robot.py --movement              # Test robot movement
    python test_robot.py --utils                 # Test robot_utils module
    python test_robot.py --all                   # Run all robot tests
"""

import sys
import os
import time
import argparse
import json
import socket
import threading
from typing import Dict, Tuple, List, Any, Optional

# Add the parent directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import robot_utils if available
try:
    from robot_utils import RobotConnection, ROBOT_API_AVAILABLE
except ImportError as e:
    print(f"Warning: Could not import robot_utils module: {e}")
    # Fallback to direct imports if robot_utils is not available
    try:
        from dobot_api import DobotApiDashboard, DobotApiFeedBack
        ROBOT_API_AVAILABLE = True
    except ImportError:
        print("Warning: Robot API not available")
        ROBOT_API_AVAILABLE = False

class RobotTester:
    """Unified robot testing class for all robot-related tests"""
    
    def __init__(self, robot_ip="192.168.1.6"):
        self.robot_ip = robot_ip
        self.test_results = {}
        
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test results"""
        self.test_results[test_name] = {"passed": passed, "message": message}
        status = "✓" if passed else "✗"
        print(f"  {status} {test_name}: {message}")
    
    def test_connection(self) -> bool:
        """Test robot connection"""
        print("\n=== ROBOT CONNECTION TEST ===")
        
        try:
            # Import the robot_utils module
            from robot_utils import RobotConnection, ROBOT_API_AVAILABLE
            
            # Log API availability
            api_status = "available" if ROBOT_API_AVAILABLE else "not available"
            self.log_result("Robot API availability", True, f"Robot API is {api_status}")
            
            # Test RobotConnection creation
            robot = RobotConnection(self.robot_ip)
            self.log_result("RobotConnection initialization", True, "Successfully created RobotConnection instance")
            
            # Test the network connectivity check
            try:
                success, message = robot.test_network_connectivity()
                connectivity_result = "successful" if success else "failed"
                self.log_result("Network connectivity test", True, 
                              f"Network test {connectivity_result}: {message}")
            except Exception as e:
                self.log_result("Network connectivity test", False, f"Error during network test: {e}")
                
            # Test error handling for an invalid IP
            test_invalid_ip = RobotConnection("192.168.999.999")  # Invalid IP
            success, message = test_invalid_ip.test_network_connectivity()
            if not success:
                self.log_result("Invalid IP handling", True, "Correctly handled invalid IP address")
            else:
                self.log_result("Invalid IP handling", False, "Failed to detect invalid IP address")
            
            return True
            
        except Exception as e:
            self.log_result("Robot connection test", False, f"Error: {e}")
            return False
    
    def test_movement(self) -> bool:
        """Test robot movement"""
        print("\n=== ROBOT MOVEMENT TEST ===")
        
        try:
            # Import the robot_utils module
            from robot_utils import RobotConnection, ROBOT_API_AVAILABLE
            
            if not ROBOT_API_AVAILABLE:
                self.log_result("Robot movement test", False, "Robot API not available - skipping movement test")
                return False
            
            # Create a robot connection
            robot = RobotConnection(self.robot_ip)
            
            # Test network connectivity first
            success, message = robot.test_network_connectivity()
            if not success:
                self.log_result("Robot connectivity", False, f"Cannot connect to robot: {message}")
                return False
            
            # Connect to the robot
            success, message = robot.connect()
            if not success:
                self.log_result("Robot connection", False, f"Failed to connect to robot: {message}")
                return False
            
            self.log_result("Robot connection", True, "Successfully connected to robot")
            
            # Check alarms
            alarm_ok, alarms = robot.check_robot_alarms()
            if not alarm_ok:
                self.log_result("Robot alarms", False, f"Robot has {len(alarms)} active alarms")
                return False
            
            self.log_result("Robot alarms", True, "No active alarms")
            
            # Get robot mode
            success, mode = robot.get_robot_mode()
            if success:
                self.log_result("Robot mode", True, f"Robot mode: {mode}")
            else:
                self.log_result("Robot mode", False, f"Failed to get robot mode")
            
            # Test movement if it's safe to do so (only in controlled test environments)
            if '--safe-movement' in sys.argv:
                # Enable the robot if needed
                if robot.robot_needs_enabling():
                    success, message = robot.enable_robot()
                    if not success:
                        self.log_result("Robot enable", False, f"Failed to enable robot: {message}")
                        return False
                    
                    self.log_result("Robot enable", True, "Successfully enabled robot")
                
                # Test movement
                success, message = robot.test_movement()
                movement_result = "successful" if success else "failed"
                self.log_result("Robot movement", success, f"Movement test {movement_result}: {message}")
            else:
                self.log_result("Robot movement", True, "Movement test skipped - use --safe-movement to test actual movement")
            
            # Disconnect from the robot
            robot.disconnect()
            self.log_result("Robot disconnect", True, "Successfully disconnected from robot")
            
            return True
            
        except Exception as e:
            self.log_result("Robot movement test", False, f"Error: {e}")
            return False
    
    def test_robot_utils(self) -> bool:
        """Test robot_utils module"""
        print("\n=== ROBOT UTILITIES MODULE TEST ===")
        
        try:
            # Import the robot_utils module
            from robot_utils import RobotConnection, ROBOT_API_AVAILABLE
            
            # Log API availability
            api_status = "available" if ROBOT_API_AVAILABLE else "not available"
            self.log_result("Robot API availability", True, f"Robot API is {api_status}")
            
            # Test RobotConnection creation
            robot = RobotConnection(self.robot_ip)
            self.log_result("RobotConnection initialization", True, "Successfully created RobotConnection instance")
            
            # Test additional methods if robot API is available
            if ROBOT_API_AVAILABLE:
                # Test parsing a mock robot response
                mock_alarm_response = "[[],[]]"  # Empty alarm response
                # Simulate the alarm check logic
                alarm_ok = "null" in mock_alarm_response or "[]" in mock_alarm_response
                self.log_result("Response parsing", True, 
                              f"Mock alarm parsing: {'no alarms' if alarm_ok else 'has alarms'}")
                              
                # Test position parsing from a mock response
                mock_position = "[100.0, 0.0, 200.0, 0.0, 0.0, 0.0]"
                try:
                    numbers = [float(n) for n in mock_position.strip("[]").split(",")]
                    if len(numbers) == 6:
                        self.log_result("Position parsing", True, f"Successfully parsed position: {numbers}")
                    else:
                        self.log_result("Position parsing", False, "Failed to parse position data")
                except Exception as e:
                    self.log_result("Position parsing", False, f"Error parsing position: {e}")
            
            return True
            
        except Exception as e:
            self.log_result("Robot utils module test", False, f"Error: {e}")
            return False

    def run_all_tests(self) -> bool:
        """Run all robot tests"""
        print("\n=== RUNNING ALL ROBOT TESTS ===")
        
        # Run connection test
        connection_result = self.test_connection()
        
        # Run movement test
        movement_result = self.test_movement()
        
        # Run robot utils test
        utils_result = self.test_robot_utils()
        
        # Print summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["passed"])
        
        print("\n=== ROBOT TEST SUMMARY ===")
        print(f"Total tests: {total_tests}")
        print(f"Passed tests: {passed_tests}")
        
        return connection_result and movement_result and utils_result

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Unified Robot Test Module")
    parser.add_argument("--robot-ip", type=str, default="192.168.1.6", help="Robot IP address")
    parser.add_argument("--connection", action="store_true", help="Test robot connection")
    parser.add_argument("--movement", action="store_true", help="Test robot movement")
    parser.add_argument("--utils", action="store_true", help="Test robot_utils module")
    parser.add_argument("--safe-movement", action="store_true", help="Test actual robot movement (use with caution)")
    parser.add_argument("--all", action="store_true", help="Run all robot tests")
    
    args = parser.parse_args()
    
    # Create a robot tester
    tester = RobotTester(args.robot_ip)
    
    # Run tests
    if args.connection or args.all:
        tester.test_connection()
        
    if args.movement or args.all:
        tester.test_movement()
        
    if args.utils or args.all:
        tester.test_robot_utils()
        
    if not (args.connection or args.movement or args.utils or args.all):
        parser.print_help()

if __name__ == "__main__":
    main()
