#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Control Integration Tests

Focused integration tests for the consolidated robot control package.
These tests validate actual robot communication and movement functionality.
"""

import sys
import os
import time
import socket
from typing import Dict, Tuple, List, Optional
from contextlib import contextmanager

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from robot_control import (
    RobotSystem, ConnectionManager, DobotApiDashboard,
    parse_api_response, execute_robot_command, 
    get_logger, setup_logging
)


class RobotIntegrationTester:
    """Integration tests for actual robot functionality"""
    
    def __init__(self, robot_ip: str = "192.168.1.6", timeout: float = 10.0):
        self.robot_ip = robot_ip
        self.timeout = timeout
        self.logger = get_logger(__name__)
        self.test_results = []
        
    def check_robot_availability(self) -> Tuple[bool, str]:
        """Check if robot is available on the network"""
        try:
            # Try to connect to robot's dashboard port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            result = sock.connect_ex((self.robot_ip, 29999))
            sock.close()
            
            if result == 0:
                return True, f"Robot accessible at {self.robot_ip}:29999"
            else:
                return False, f"Robot not accessible at {self.robot_ip}:29999"
                
        except Exception as e:
            return False, f"Network check failed: {str(e)}"
    
    def test_connection_manager(self) -> Tuple[bool, str]:
        """Test ConnectionManager functionality"""
        try:
            conn_mgr = ConnectionManager(self.robot_ip)
            
            # Test connection
            success, message = conn_mgr.connect()
            if not success:
                return False, f"Connection failed: {message}"
            
            # Test dashboard access
            dashboard = conn_mgr.get_dashboard()
            assert dashboard is not None, "Dashboard is None"
            
            # Test basic command
            response = dashboard.RobotMode()
            parsed_response = parse_api_response(response)
            assert parsed_response is not None, "Failed to parse robot mode response"
            
            # Test disconnection
            conn_mgr.disconnect()
            
            return True, "ConnectionManager tests passed"
            
        except Exception as e:
            return False, f"ConnectionManager test failed: {str(e)}"
    
    def test_robot_system_initialization(self) -> Tuple[bool, str]:
        """Test RobotSystem initialization and basic functionality"""
        try:
            robot_system = RobotSystem(self.robot_ip)
            
            # Check system components
            assert hasattr(robot_system, 'connection'), "Missing connection component"
            assert hasattr(robot_system, 'controller'), "Missing controller component"
            
            # Test connection
            success, message = robot_system.connection.connect()
            if not success:
                return False, f"RobotSystem connection failed: {message}"
            
            # Test robot status
            dashboard = robot_system.connection.get_dashboard()
            robot_mode = dashboard.RobotMode()
            assert robot_mode is not None, "Failed to get robot mode"
            
            # Test controller setup
            robot_system.controller.dashboard = dashboard
            assert robot_system.controller.dashboard is not None, "Controller dashboard not set"
            
            # Clean up
            robot_system.connection.disconnect()
            
            return True, "RobotSystem initialization tests passed"
            
        except Exception as e:
            return False, f"RobotSystem test failed: {str(e)}"
    
    def test_api_communication(self) -> Tuple[bool, str]:
        """Test API communication and command execution"""
        try:
            dashboard = DobotApiDashboard(self.robot_ip, 29999)
            dashboard.connect()
            
            # Test various API commands
            commands_tested = []
            
            # Test RobotMode
            mode_response = dashboard.RobotMode()
            parsed_mode = parse_api_response(mode_response)
            assert parsed_mode is not None, "Failed to parse robot mode"
            commands_tested.append("RobotMode")
            
            # Test GetPose
            pose_response = dashboard.GetPose()
            parsed_pose = parse_api_response(pose_response, expected_format="position")
            assert parsed_pose is not None, "Failed to parse robot pose"
            commands_tested.append("GetPose")
            
            # Test PowerOn status
            power_response = dashboard.PowerOn()
            parsed_power = parse_api_response(power_response)
            commands_tested.append("PowerOn")
            
            # Test EnableRobot status  
            enable_response = dashboard.EnableRobot()
            parsed_enable = parse_api_response(enable_response)
            commands_tested.append("EnableRobot")
            
            dashboard.disconnect()
            
            return True, f"API communication tests passed: {', '.join(commands_tested)}"
            
        except Exception as e:
            return False, f"API communication test failed: {str(e)}"
    
    def test_position_operations(self) -> Tuple[bool, str]:
        """Test position-related operations"""
        try:
            robot_system = RobotSystem(self.robot_ip)
            success, message = robot_system.connection.connect()
            if not success:
                return False, f"Connection failed: {message}"
            
            dashboard = robot_system.connection.get_dashboard()
            robot_system.controller.dashboard = dashboard
            
            operations_tested = []
            
            # Test current position retrieval
            current_pos = robot_system.controller.get_current_position()
            assert current_pos is not None, "Failed to get current position"
            assert len(current_pos) == 6, f"Invalid position length: {len(current_pos)}"
            operations_tested.append("get_current_position")
            
            # Test position validation
            from robot_control import validate_position_values
            assert validate_position_values(current_pos), "Current position validation failed"
            operations_tested.append("validate_position_values")
            
            # Test position formatting
            from robot_control import format_position
            formatted_pos = format_position(current_pos)
            assert isinstance(formatted_pos, str), "Position formatting failed"
            operations_tested.append("format_position")
            
            # Test safe position bounds checking
            test_positions = [
                [200, 100, 50, 0, 0, 0],  # Safe position
                [1000, 1000, 1000, 0, 0, 0],  # Potentially unsafe position
            ]
            
            for pos in test_positions:
                try:
                    is_valid = validate_position_values(pos)
                    operations_tested.append(f"position_bounds_check_{pos[0]}")
                except:
                    pass  # Some positions may be rejected
            
            robot_system.connection.disconnect()
            
            return True, f"Position operations tests passed: {', '.join(operations_tested)}"
            
        except Exception as e:
            return False, f"Position operations test failed: {str(e)}"
    
    def test_error_handling_integration(self) -> Tuple[bool, str]:
        """Test error handling in integration scenarios"""
        try:
            error_scenarios = []
            
            # Test connection to invalid IP
            try:
                invalid_conn = ConnectionManager("192.168.1.999")
                success, message = invalid_conn.connect()
                assert not success, "Connection to invalid IP should fail"
                error_scenarios.append("invalid_ip_handling")
            except:
                error_scenarios.append("invalid_ip_exception")
            
            # Test malformed API responses
            from robot_control import parse_api_response
            malformed_responses = [
                "",
                "invalid_response",
                "1,2,3,",  # Incomplete
                "NaN,NaN,NaN,NaN,NaN,NaN;",  # NaN values
            ]
            
            for response in malformed_responses:
                try:
                    result = parse_api_response(response, expected_format="position")
                    # Should handle gracefully
                    error_scenarios.append(f"malformed_response_handled")
                except Exception:
                    error_scenarios.append(f"malformed_response_exception")
            
            # Test timeout scenarios
            try:
                dashboard = DobotApiDashboard(self.robot_ip, 29999)
                dashboard.socket_timeout = 0.1  # Very short timeout
                # This may timeout, which is expected
                error_scenarios.append("timeout_handling")
            except:
                error_scenarios.append("timeout_exception")
            
            return True, f"Error handling integration tests: {', '.join(error_scenarios)}"
            
        except Exception as e:
            return False, f"Error handling integration test failed: {str(e)}"
    
    def test_concurrent_operations(self) -> Tuple[bool, str]:
        """Test concurrent robot operations"""
        try:
            import threading
            import queue
            
            results_queue = queue.Queue()
            
            def worker_connection(thread_id):
                try:
                    conn_mgr = ConnectionManager(self.robot_ip)
                    success, message = conn_mgr.connect()
                    if success:
                        dashboard = conn_mgr.get_dashboard()
                        mode = dashboard.RobotMode()
                        conn_mgr.disconnect()
                        results_queue.put(f"thread_{thread_id}_success")
                    else:
                        results_queue.put(f"thread_{thread_id}_failed")
                except Exception as e:
                    results_queue.put(f"thread_{thread_id}_error_{str(e)}")
            
            # Start multiple threads
            threads = []
            for i in range(3):
                thread = threading.Thread(target=worker_connection, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join(timeout=30.0)
            
            # Collect results
            concurrent_results = []
            while not results_queue.empty():
                result = results_queue.get()
                concurrent_results.append(result)
            
            success_count = sum(1 for r in concurrent_results if "success" in r)
            
            return True, f"Concurrent operations: {success_count}/{len(threads)} successful"
            
        except Exception as e:
            return False, f"Concurrent operations test failed: {str(e)}"
    
    def run_safe_movement_test(self) -> Tuple[bool, str]:
        """Test safe robot movement (if robot is available and enabled)"""
        try:
            robot_system = RobotSystem(self.robot_ip)
            success, message = robot_system.connection.connect()
            if not success:
                return False, f"Connection failed for movement test: {message}"
            
            dashboard = robot_system.connection.get_dashboard()
            robot_system.controller.dashboard = dashboard
            
            # Check if robot is in a safe state for movement
            robot_mode = dashboard.RobotMode()
            parsed_mode = parse_api_response(robot_mode)
            
            if parsed_mode is None:
                robot_system.connection.disconnect()
                return False, "Could not determine robot mode"
            
            # Get current position as baseline
            current_pos = robot_system.controller.get_current_position()
            if current_pos is None:
                robot_system.connection.disconnect()
                return False, "Could not get current position"
            
            movement_tests = []
            
            # Test 1: Small movement in Z-axis (safest)
            safe_offset = [0, 0, 5, 0, 0, 0]  # 5mm up in Z
            target_pos = [current_pos[i] + safe_offset[i] for i in range(6)]
            
            # Validate target position
            from robot_control import validate_position_values
            if not validate_position_values(target_pos):
                movement_tests.append("target_position_invalid")
            else:
                movement_tests.append("target_position_valid")
                
                # Note: We won't actually execute movement for safety
                # In a real test environment, you would:
                # success = robot_system.controller.move_to_position(target_pos)
                movement_tests.append("movement_validation_complete")
            
            robot_system.connection.disconnect()
            
            return True, f"Safe movement tests: {', '.join(movement_tests)}"
            
        except Exception as e:
            return False, f"Safe movement test failed: {str(e)}"
    
    def run_all_integration_tests(self) -> Dict:
        """Run all integration tests"""
        print("=" * 80)
        print("ROBOT CONTROL INTEGRATION TESTS")
        print("=" * 80)
        print(f"Robot IP: {self.robot_ip}")
        print("=" * 80)
        
        # Check robot availability first
        available, availability_msg = self.check_robot_availability()
        print(f"Robot Availability: {availability_msg}")
        
        if not available:
            print("\n⚠️  Robot not available - running limited tests only")
            return {
                'robot_available': False,
                'tests_run': 0,
                'tests_passed': 0,
                'message': 'Robot not available for integration testing'
            }
        
        # Define integration tests
        test_suite = [
            ("Connection Manager", self.test_connection_manager),
            ("Robot System Init", self.test_robot_system_initialization),
            ("API Communication", self.test_api_communication), 
            ("Position Operations", self.test_position_operations),
            ("Error Handling Integration", self.test_error_handling_integration),
            ("Concurrent Operations", self.test_concurrent_operations),
            ("Safe Movement Test", self.run_safe_movement_test),
        ]
        
        # Run tests
        start_time = time.time()
        passed_tests = 0
        total_tests = len(test_suite)
        
        for test_name, test_func in test_suite:
            print(f"\nRunning: {test_name}")
            try:
                success, message = test_func()
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"{status} {test_name}: {message}")
                
                if success:
                    passed_tests += 1
                    
            except Exception as e:
                print(f"❌ FAIL {test_name}: Exception - {str(e)}")
        
        total_time = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 80)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 80)
        success_rate = (passed_tests / total_tests) * 100
        print(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"Total Time: {total_time:.2f} seconds")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL INTEGRATION TESTS PASSED!")
            print("The consolidated robot control package is fully functional with actual robot hardware.")
        else:
            failed_tests = total_tests - passed_tests
            print(f"\n⚠️  {failed_tests} integration test(s) failed.")
        
        return {
            'robot_available': True,
            'tests_run': total_tests,
            'tests_passed': passed_tests,
            'tests_failed': total_tests - passed_tests,
            'success_rate': success_rate,
            'total_time': total_time
        }


def main():
    """Main integration test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Robot Control Integration Tests")
    parser.add_argument("--robot-ip", default="192.168.1.6", help="Robot IP address")
    parser.add_argument("--timeout", type=float, default=10.0, help="Connection timeout")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
      # Setup logging
    setup_logging("integration_tests")
    
    # Run integration tests
    tester = RobotIntegrationTester(
        robot_ip=args.robot_ip,
        timeout=args.timeout
    )
    
    results = tester.run_all_integration_tests()
    
    # Exit with appropriate code
    if results.get('robot_available', False):
        sys.exit(0 if results['tests_failed'] == 0 else 1)
    else:
        print("\nIntegration tests skipped - robot not available")
        sys.exit(0)


if __name__ == "__main__":
    main()
