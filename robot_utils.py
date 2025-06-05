#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Utility Module

Common functions for robot control, status checking, and movement testing.
Used by both the preflight check script and the main startup script.
"""

import sys
import os
import time
import socket
import re
from typing import Optional, Tuple, List, Dict, Any, Union

# Add robot API path if not already in path
robot_api_path = os.path.join(os.path.dirname(__file__), 'TCP-IP-CR-Python-V4')
if robot_api_path not in sys.path:
    sys.path.append(robot_api_path)

try:
    from dobot_api import DobotApiDashboard, DobotApiFeedBack
    ROBOT_API_AVAILABLE = True
except ImportError as e:
    print(f"❌ Robot API not available: {e}")
    print("Please check TCP-IP-CR-Python-V4 installation.")
    ROBOT_API_AVAILABLE = False


class RobotConnection:
    """Class to handle robot connections and common operations"""
    
    def __init__(self, robot_ip: str = "192.168.1.6", dashboard_port: int = 29999, 
                 move_port: int = 30003, feed_port: int = 30004):
        """
        Initialize robot connection
        
        Args:
            robot_ip: IP address of the robot
            dashboard_port: Port for dashboard commands
            move_port: Port for movement commands
            feed_port: Port for feedback
        """
        self.robot_ip = robot_ip
        self.dashboard_port = dashboard_port
        self.move_port = move_port
        self.feed_port = feed_port
        
        # Connection objects
        self.dashboard = None
        self.feedbacks = None
        
        # Movement parameters
        self.position_tolerance = 5.0  # mm
        self.safe_packing_position = [250, 0, 300, 0, 0, 0]  # Safe packing position
        
        # Robot state
        self.initial_position = None
    
    def test_network_connectivity(self) -> Tuple[bool, str]:
        """
        Test basic network connectivity to the robot
        
        Returns:
            (success, message): Success flag and status message
        """
        try:
            # Test robot dashboard port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            result = sock.connect_ex((self.robot_ip, self.dashboard_port))
            sock.close()
            
            if result == 0:
                return True, f"Robot accessible at {self.robot_ip}:{self.dashboard_port}"
            else:
                return False, f"Cannot reach {self.robot_ip}:{self.dashboard_port}"
        except Exception as e:            
            return False, f"Network error: {e}"
    
    def connect(self) -> Tuple[bool, str]:
        """
        Connect to the robot dashboard
        
        Returns:
            (success, message): Success flag and status message
        """
        if not ROBOT_API_AVAILABLE:
            return False, "Robot API not available"
        
        try:
            # Create dashboard connection
            self.dashboard = DobotApiDashboard(self.robot_ip, self.dashboard_port)
            
            # Test connection with basic command
            mode_response = self.dashboard.RobotMode()
            
            if mode_response and len(mode_response) > 0:
                robot_mode = mode_response[0] if isinstance(mode_response, list) else mode_response
                return True, f"Connected, Robot mode: {robot_mode}"
            else:
                return False, "No response from robot"
                
        except Exception as e:            
            return False, f"Connection failed: {e}"
    
    def disconnect(self) -> None:
        """
        Disconnect from robot safely
        """
        if self.dashboard:
            try:
                # Use the dashboard's built-in disconnect method if available
                if hasattr(self.dashboard, 'disconnect'):
                    self.dashboard.disconnect()
                elif hasattr(self.dashboard, 'close'):
                    self.dashboard.close()
            except Exception as e:
                # Ignore socket closing errors during cleanup
                if "10038" not in str(e) and "not a socket" not in str(e).lower():
                    print(f"Note: Error during disconnect: {e}")
            finally:
                self.dashboard = None
        
        if self.feedbacks:
            try:
                if hasattr(self.feedbacks, 'disconnect'):
                    self.feedbacks.disconnect()
                elif hasattr(self.feedbacks, 'close'):
                    self.feedbacks.close()
            except Exception:
                pass
            finally:
                self.feedbacks = None
    
    def check_robot_alarms(self, description: str = "Checking for robot alarms") -> Tuple[bool, List[str]]:
        """
        Check for robot alarms
        
        Args:
            description: Description to print
            
        Returns:
            (alarm_ok, error_codes): Whether alarms are OK and list of error codes if any
        """
        print(f"{description}...")
        alarm_ok = True
        actual_errors = []
        
        try:
            if not self.dashboard:
                return False, ["No robot connection"]
                
            alarm_response = self.dashboard.GetErrorID()
            print(f"Raw alarm response: {alarm_response}")
            
            if alarm_response:
                alarm_str = str(alarm_response)
                
                # Check for actual error indicators
                # The response contains "null" and empty arrays when no errors
                # Also check for GetErrorID command echo which is part of normal response
                if ("null" in alarm_str or 
                    "[]" in alarm_str or 
                    "GetErrorID();" in alarm_str or
                    alarm_str.strip() in ['0', '[]', 'null']):
                    alarm_ok = True
                    print("✅ No active alarms detected")
                else:
                    # Look for actual numeric error codes (not 0, not in command echo)
                    # Find actual error numbers (non-zero, not part of command formatting)
                    error_numbers = re.findall(r'\b([1-9][0-9]*)\b', alarm_str)
                    # Filter out numbers that are part of the API response formatting
                    actual_errors = [e for e in error_numbers if e not in ['0', '1', '2', '3', '4', '5', '6'] or len(error_numbers) == 1]
                    
                    if actual_errors:
                        alarm_ok = False
                        print(f"❌ Active error codes detected: {actual_errors}")
                        print("💡 Clear robot alarms via teach pendant before proceeding")
                    else:
                        alarm_ok = True
                        print("✅ No active alarms detected")
            else:
                alarm_ok = True
                print("✅ No alarm response (assuming OK)")
                
        except Exception as e:
            print(f"Could not check alarms: {e}")
            alarm_ok = True  # Assume OK if we can't check
            
        return alarm_ok, actual_errors
    
    def clear_errors(self) -> Tuple[bool, str]:
        """
        Clear any existing errors on the robot
        
        Returns:
            (success, message): Success flag and result message
        """
        try:
            if not self.dashboard:
                return False, "No robot connection"
                
            clear_result = self.dashboard.ClearError()
            return True, f"Clear errors result: {clear_result}"
        except Exception as e:
            return False, f"Could not clear errors: {e}"
    
    def get_robot_mode(self) -> Tuple[int, str]:
        """
        Get the current robot mode
        
        Returns:
            (mode, description): Robot mode as int and description
        """
        try:
            if not self.dashboard:
                return 0, "No robot connection"
                
            mode_response = self.dashboard.RobotMode()
            
            if mode_response:
                robot_mode_str = str(mode_response)
                print(f"Raw robot mode response: {robot_mode_str}")
                
                # Extract just the numeric mode from complex response
                mode_match = re.search(r'\b([0-9]+)\b', robot_mode_str)
                if mode_match:
                    actual_mode = int(mode_match.group(1))
                else:
                    actual_mode = 0
                
                # Mode descriptions
                mode_descriptions = {
                    0: "Unknown",
                    1: "Initializing",
                    2: "Standby",
                    3: "Disabled",
                    4: "Ready",
                    5: "Running",
                    6: "Error",
                    7: "Disconnected",
                    8: "Paused"
                }
                
                description = mode_descriptions.get(actual_mode, "Unknown")
                return actual_mode, description
            else:
                return 0, "No response"
        except Exception as e:
            return 0, f"Error getting mode: {e}"
    
    def enable_robot(self, timeout: float = 10.0) -> Tuple[bool, str]:
        """
        Enable the robot with timeout
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            (success, message): Success flag and status message
        """
        try:
            if not self.dashboard:
                return False, "No robot connection"
                
            # Get current mode
            actual_mode, description = self.get_robot_mode()
            
            # Only enable if not already in running mode
            if actual_mode == 5:
                return True, "Robot is already in running mode"
            
            # Send enable command
            enable_result = self.dashboard.EnableRobot()
            print(f"Enable robot result: {enable_result}")
            
            # Wait for robot to enable with timeout and progress indication
            print("Waiting for robot to enable", end="")
            check_interval = 0.5  # seconds
            elapsed_time = 0
            mode_ok = False
            
            while elapsed_time < timeout:
                time.sleep(check_interval)
                elapsed_time += check_interval
                print(".", end="", flush=True)
                
                # Check if robot is now enabled
                try:
                    new_mode, _ = self.get_robot_mode()
                    if new_mode == 5:  # Successfully enabled
                        mode_ok = True
                        print(f"\n✅ Robot enabled successfully (mode {new_mode}) after {elapsed_time:.1f}s")
                        break
                except Exception:
                    continue  # Keep trying
            
            if not mode_ok:
                print(f"\n⏰ Timeout waiting for robot to enable after {timeout}s")
                # One final check
                final_mode, _ = self.get_robot_mode()
                mode_ok = final_mode == 5
                
                if not mode_ok:
                    return False, "Robot enable timeout - may need manual intervention"
            
            return mode_ok, f"Robot enabled successfully after {elapsed_time:.1f}s"
            
        except Exception as e:
            return False, f"Failed to enable robot: {e}"
    
    def get_position(self) -> Tuple[bool, List[float]]:
        """
        Get current robot position
        
        Returns:
            (success, position): Success flag and position as [x,y,z,rx,ry,rz]
        """
        try:
            if not self.dashboard:
                return False, []
                
            pos_response = self.dashboard.GetPose()
            if pos_response:
                # Parse position data from complex response
                position_str = str(pos_response)
                print(f"Raw position response: {position_str}")
                # Extract numeric values from the response
                numbers = re.findall(r'-?\d+\.?\d*', position_str)
                if len(numbers) >= 6:
                    position = [float(n) for n in numbers[:6]]
                    print(f"Current position: X={position[0]:.1f}, Y={position[1]:.1f}, Z={position[2]:.1f}")
                    return True, position
                else:
                    return False, []
            else:
                return False, []
        except Exception as e:
            print(f"Could not get position: {e}")
            return False, []
    
    def move_to_position(self, position: List[float], 
                        move_type: str = "MovJ", 
                        wait_time: float = 5.0) -> Tuple[bool, str]:
        """
        Move the robot to a position
        
        Args:
            position: Target position as [x,y,z,rx,ry,rz]
            move_type: Movement type (MovJ or MovL)
            wait_time: Time to wait for movement completion
            
        Returns:
            (success, message): Success flag and status message
        """
        try:
            if not self.dashboard:
                return False, "No robot connection"
                
            if len(position) < 6:
                return False, "Invalid position - need 6 values"
                
            # Create the movement command
            if move_type == "MovL":
                # Use MovL method directly
                result = self.dashboard.MovL(
                    position[0], position[1], position[2],
                    position[3], position[4], position[5],
                    coordinateMode=0
                )
            else:
                # Use generic mov method with MovJ
                move_cmd = f"MovJ({','.join(map(str, position))})"
                result = self.dashboard.mov(move_cmd)
                
            print(f"Move command response: {result}")
            
            # Wait for movement to complete with progress indication
            print("Waiting for movement to complete", end="")
            check_interval = 0.5
            elapsed_time = 0
            
            while elapsed_time < wait_time:
                time.sleep(check_interval)
                elapsed_time += check_interval
                print(".", end="", flush=True)
            
            print(f"\nMovement wait completed after {elapsed_time:.1f}s")
            
            # Check final position
            success, final_pos = self.get_position()
            if not success:
                return False, "Could not verify final position"
                
            # Check distance from target (first 3 coordinates only - position)
            distance = sum((final_pos[i] - position[i])**2 for i in range(3))**0.5
            print(f"Distance from target: {distance:.1f}mm")
            
            if distance < self.position_tolerance:
                return True, f"Movement successful (distance: {distance:.1f}mm)"
            else:
                return False, f"Position error: {distance:.1f}mm from target"
                
        except Exception as e:
            return False, f"Movement failed: {e}"
    
    def test_movement(self, use_packing_position: bool = True) -> Tuple[bool, str]:
        """
        Perform a simple movement test
        
        Args:
            use_packing_position: Whether to use the safe packing position or just move a small amount
            
        Returns:
            (success, message): Success flag and status message
        """
        try:
            if not self.dashboard:
                return False, "No robot connection"
                
            # Store initial position if not already stored
            if not self.initial_position:
                success, position = self.get_position()
                if not success:
                    return False, "Could not get initial position"
                self.initial_position = position
            
            print(f"Initial position: {self.initial_position}")
            
            # Determine target position
            if use_packing_position:
                target_position = self.safe_packing_position.copy()
                # Keep original orientation
                target_position[3:] = self.initial_position[3:]
                print("Moving to safe packing position...")
            else:
                # Just move slightly up (+50mm in Z)
                target_position = self.initial_position.copy()
                target_position[2] += 50
                print("Moving slightly up (+50mm in Z)...")
            
            # Move to target position
            success, message = self.move_to_position(target_position)
            if not success:
                return False, f"Failed to move to target: {message}"
            
            # Return to initial position
            print("Returning to initial position...")
            success, message = self.move_to_position(self.initial_position)
            if not success:
                return False, f"Failed to return to initial position: {message}"
            
            # Verify return position
            success, final_pos = self.get_position()
            if not success:
                return False, "Could not verify final position"
            
            # Check distance from initial
            return_distance = sum((final_pos[i] - self.initial_position[i])**2 for i in range(3))**0.5
            print(f"Distance from initial position: {return_distance:.1f}mm")
            
            if return_distance < self.position_tolerance:
                return True, f"Movement test successful! (Return accuracy: {return_distance:.1f}mm)"
            else:
                return False, f"Return position error: {return_distance:.1f}mm from initial position"
            
        except Exception as e:
            return False, f"Movement test failed: {e}"
    
    def perform_preflight_check(self) -> Tuple[bool, Dict[str, bool], Dict[str, str]]:
        """
        Perform a comprehensive preflight check
        
        Returns:
            (overall_success, test_results, test_messages)
        """
        test_results = {}
        test_messages = {}
        
        # Step 1: Network connectivity
        print("\n" + "="*60)
        print("🌐 TEST 1: NETWORK CONNECTIVITY")
        print("="*60)
        
        success, message = self.test_network_connectivity()
        test_results["Network Connectivity"] = success
        test_messages["Network Connectivity"] = message
        status = "✅" if success else "❌"
        print(f"{status} Network Connectivity: {message}")
        
        if not success:
            return False, test_results, test_messages
        
        # Step 2: Robot connection
        print("\n" + "="*60)
        print("🤖 TEST 2: ROBOT API CONNECTION")
        print("="*60)
        
        success, message = self.connect()
        test_results["Robot API Connection"] = success
        test_messages["Robot API Connection"] = message
        status = "✅" if success else "❌"
        print(f"{status} Robot API Connection: {message}")
        
        if not success:
            return False, test_results, test_messages
        
        # Step 3: Robot status
        print("\n" + "="*60)
        print("⚕️ TEST 3: ROBOT STATUS & ENABLEMENT")
        print("="*60)
        
        # Clear errors
        self.clear_errors()
        time.sleep(1)
        
        # Check alarms BEFORE robot enablement
        pre_alarm_ok, pre_errors = self.check_robot_alarms("Checking for robot alarms BEFORE enablement")
        
        # Enable robot
        mode_ok, mode_message = self.enable_robot()
        
        # Check alarms AFTER robot enablement
        post_alarm_ok, post_errors = self.check_robot_alarms("Checking for robot alarms AFTER enablement")
        
        # Get position for reference
        self.get_position()
        
        # Final status assessment
        alarm_ok = pre_alarm_ok and post_alarm_ok
        status_success = mode_ok and alarm_ok
        
        if status_success:
            status_msg = "Robot enabled and ready"
        else:
            issues = []
            if not mode_ok:
                issues.append("mode not ready")
            if not alarm_ok:
                issues.append("active alarms")
            status_msg = f"Robot not ready: {', '.join(issues)}"
        
        test_results["Robot Status"] = status_success
        test_messages["Robot Status"] = status_msg
        status = "✅" if status_success else "❌"
        print(f"{status} Robot Status: {status_msg}")
        
        if not status_success:
            return False, test_results, test_messages
        
        # Step 4: Movement test
        print("\n" + "="*60)
        print("🏃 TEST 4: MOVEMENT TEST")
        print("="*60)
        
        success, message = self.test_movement(use_packing_position=True)
        test_results["Movement Test"] = success
        test_messages["Movement Test"] = message
        status = "✅" if success else "❌"
        print(f"{status} Movement Test: {message}")
        
        # Overall result
        overall_success = all(test_results.values())
        
        # Summary
        print("\n" + "="*60)
        print("📋 PRE-FLIGHT CHECK SUMMARY")
        print("="*60)
        
        for test_name, passed in test_results.items():
            status = "✅" if passed else "❌"
            print(f"{status} {test_name}")
        
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        print(f"\nTests passed: {passed_tests}/{total_tests}")
        
        if overall_success:
            print("\n🎉 ALL TESTS PASSED - Robot ready for operation!")
        else:
            print(f"\n❌ {total_tests - passed_tests} test(s) failed - Check issues above")
        
        return overall_success, test_results, test_messages


# Simple usage example
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Robot Utilities Test")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick test without movement")
    
    args = parser.parse_args()
    
    # Create robot connection
    robot = RobotConnection(args.robot_ip)
    
    try:
        # Run tests
        success, results, messages = robot.perform_preflight_check()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Test cancelled by user")
        sys.exit(1)
    finally:
        # Always disconnect properly
        robot.disconnect()
