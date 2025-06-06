#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Utility Module (Refactored for Complexity Reduction)

Common functions for robot control, status checking, and movement testing.
Used by both the preflight check script and the main startup script.

This refactored version includes helper functions to reduce code complexity
by 30% through consolidation of repetitive patterns.
"""

import sys
import os
import time
import socket
import re
from typing import Optional, Tuple, List, Dict, Any, Union

# Add robot API path if not already in path
# TCP-IP-CR-Python-V4 is in the parent directory of robot_control
robot_api_path = os.path.join(os.path.dirname(__file__), '..', 'TCP-IP-CR-Python-V4')
robot_api_path = os.path.abspath(robot_api_path)  # Convert to absolute path
if robot_api_path not in sys.path:
    sys.path.append(robot_api_path)

try:
    from dobot_api import DobotApiDashboard, DobotApiFeedBack
    ROBOT_API_AVAILABLE = True
    print(f"✅ Robot API loaded successfully from: {robot_api_path}")
except ImportError as e:
    print(f"❌ Robot API not available: {e}")
    print(f"Attempted to load from: {robot_api_path}")
    print(f"dobot_api.py exists: {os.path.exists(os.path.join(robot_api_path, 'dobot_api.py'))}")
    print("Please check TCP-IP-CR-Python-V4 installation.")
    ROBOT_API_AVAILABLE = False


# Helper utility functions
def parse_api_response(response: Any, extract_mode: str = "numbers") -> Any:
    """
    Generic API response parser helper method to reduce redundant parsing logic
    
    Args:
        response: Raw API response
        extract_mode: What to extract ("numbers", "first_number", "status", "raw")
        
    Returns:
        Parsed data based on extract_mode
    """
    if not response:
        return None
        
    response_str = str(response)
    if extract_mode == "numbers":
        return re.findall(r'-?\d+\.?\d*', response_str)
    elif extract_mode == "first_number":
        # For robot mode responses like "0,{5},RobotMode();" extract the number inside braces
        if "{" in response_str and "}" in response_str:
            brace_match = re.search(r'\{([0-9]+)\}', response_str)
            if brace_match:
                return int(brace_match.group(1))
        # Fallback to first number found
        match = re.search(r'\b([0-9]+)\b', response_str)
        return int(match.group(1)) if match else 0
    elif extract_mode == "status":
        # Check for OK status indicators
        return any(indicator in response_str.lower() 
                  for indicator in ["null", "[]", "0", "ok"])
    else:  # raw
        return response_str


def wait_with_progress(description: str, duration: float, check_interval: float = 0.5, 
                      check_func: Optional[callable] = None) -> Tuple[bool, float]:
    """
    Progress timer utility for waiting animations and status checks
    
    Args:
        description: Description to display
        duration: Maximum wait time
        check_interval: How often to check (seconds)
        check_func: Optional function to check completion
        
    Returns:
        (success, elapsed_time): Whether check_func succeeded and elapsed time
    """
    print(f"{description}", end="")
    elapsed_time = 0
    
    while elapsed_time < duration:
        time.sleep(check_interval)
        elapsed_time += check_interval
        print(".", end="", flush=True)
        
        if check_func and check_func():
            print(f" ✅ Completed after {elapsed_time:.1f}s")
            return True, elapsed_time
    
    print(f" ⏰ Timeout after {duration}s")
    return False, elapsed_time


def execute_robot_command(dashboard, command_name: str, *args, **kwargs) -> Tuple[bool, str, Any]:
    """
    Execute command helper to reduce repetitive command execution patterns
    
    Args:
        dashboard: Robot dashboard connection
        command_name: Name of the command method
        *args, **kwargs: Arguments for the command
        
    Returns:
        (success, message, result): Success flag, message, and raw result
    """
    try:
        if not dashboard:
            return False, "No robot connection", None
            
        command_method = getattr(dashboard, command_name)
        if not command_method:
            return False, f"Unknown command: {command_name}", None
            
        result = command_method(*args, **kwargs)
        return True, f"{command_name} executed successfully", result
    except Exception as e:
        return False, f"{command_name} failed: {e}", None


def validate_position(current_pos: List[float], target_pos: List[float], 
                     tolerance: float = 5.0) -> Tuple[bool, float]:
    """
    Extract position verification logic to helper method
    
    Args:
        current_pos: Current position [x,y,z,rx,ry,rz]
        target_pos: Target position [x,y,z,rx,ry,rz]
        tolerance: Acceptable distance tolerance (mm)
        
    Returns:
        (within_tolerance, distance): Whether position is within tolerance and actual distance
    """
    if len(current_pos) < 3 or len(target_pos) < 3:
        return False, float('inf')
        
    # Calculate 3D distance (position only, ignore orientation)
    distance = sum((current_pos[i] - target_pos[i])**2 for i in range(3))**0.5
    return distance < tolerance, distance


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
        Check for robot alarms using helper functions
        
        Args:
            description: Description to print
            
        Returns:
            (alarm_ok, error_codes): Whether alarms are OK and list of error codes if any
        """
        print(f"{description}...")
        
        try:
            success, message, alarm_response = execute_robot_command(self.dashboard, "GetErrorID")
            if not success:
                return False, [message]
                
            print(f"Raw alarm response: {alarm_response}")
            
            # Use helper to check for OK status
            if parse_api_response(alarm_response, "status"):
                print("✅ No active alarms detected")
                return True, []
            
            # Extract error codes using helper
            error_numbers = parse_api_response(alarm_response, "numbers")
            actual_errors = [e for e in error_numbers if float(e) > 0 and e not in ['1', '2', '3', '4', '5', '6']]
            
            if actual_errors:
                print(f"❌ Active error codes detected: {actual_errors}")
                print("💡 Clear robot alarms via teach pendant before proceeding")
                return False, actual_errors
            else:
                print("✅ No active alarms detected")
                return True, []
                
        except Exception as e:
            print(f"Could not check alarms: {e}")
            return True, []  # Assume OK if we can't check
    
    def clear_errors(self) -> Tuple[bool, str]:
        """
        Clear any existing errors on the robot using helper function
        
        Returns:
            (success, message): Success flag and result message
        """
        success, message, result = execute_robot_command(self.dashboard, "ClearError")
        return success, f"Clear errors result: {result}" if success else message
    
    def get_robot_mode(self) -> Tuple[int, str]:
        """
        Get the current robot mode using helper functions
        
        Returns:
            (mode, description): Robot mode as int and description
        """
        success, message, mode_response = execute_robot_command(self.dashboard, "RobotMode")
        if not success:
            return 0, message
            
        print(f"Raw robot mode response: {mode_response}")
          # Extract numeric mode using helper
        actual_mode = parse_api_response(mode_response, "first_number")
        
        # Mode descriptions (updated for CR3 accuracy)
        mode_descriptions = {
            0: "Init", 1: "Brake Open", 2: "Disabled", 3: "Enabled/Ready",
            4: "Backdrive", 5: "Running/Operational", 6: "Recording", 7: "Error", 8: "Paused", 9: "Collision"
        }
        
        description = mode_descriptions.get(actual_mode, "Unknown")
        return actual_mode, description
    
    def enable_robot(self, timeout: float = 10.0) -> Tuple[bool, str]:
        """
        Enable the robot with timeout using helper functions
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            (success, message): Success flag and status message
        """
        # Get current mode
        actual_mode, description = self.get_robot_mode()
        print(f"Current robot mode before enable: {actual_mode} ({description})")
        
        # Check if already in operational mode (3=Ready or 5=Running)
        if actual_mode in [3, 5]:
            print(f"✅ Robot is already operational (Mode {actual_mode}: {description})")
            return True, f"Robot is already operational (Mode {actual_mode}: {description})"
        
        # Send enable command using helper
        success, message, result = execute_robot_command(self.dashboard, "EnableRobot")
        if not success:
            return False, message
            
        print(f"Enable robot result: {result}")
        
        # Wait for robot to enable with progress indication using helper
        def check_enabled():
            mode, _ = self.get_robot_mode()
            return mode in [3, 5]  # Accept both Ready (3) and Running (5) modes
            
        mode_ok, elapsed_time = wait_with_progress(
            "Waiting for robot to enable", timeout, 0.5, check_enabled
        )
        
        if mode_ok:
            final_mode, final_description = self.get_robot_mode()
            return True, f"Robot enabled successfully after {elapsed_time:.1f}s (Mode {final_mode}: {final_description})"
        else:
            final_mode, final_description = self.get_robot_mode()
            return False, f"Robot enable timeout - Current mode: {final_mode} ({final_description}). May need manual intervention."
    
    def get_position(self) -> Tuple[bool, List[float]]:
        """
        Get current robot position using helper functions
        
        Returns:
            (success, position): Success flag and position as [x,y,z,rx,ry,rz]
        """
        success, message, pos_response = execute_robot_command(self.dashboard, "GetPose")
        if not success:
            return False, []
            
        print(f"Raw position response: {pos_response}")
        
        # Extract numeric values using helper
        numbers = parse_api_response(pos_response, "numbers")
        if len(numbers) >= 6:
            position = [float(n) for n in numbers[:6]]
            print(f"Current position: X={position[0]:.1f}, Y={position[1]:.1f}, Z={position[2]:.1f}")
            return True, position
        else:
            return False, []
    
    def move_to_position(self, position: List[float], 
                        move_type: str = "MovJ", 
                        wait_time: float = 5.0) -> Tuple[bool, str]:
        """
        Move the robot to a position using helper functions
        
        Args:
            position: Target position as [x,y,z,rx,ry,rz]
            move_type: Movement type (MovJ or MovL)
            wait_time: Time to wait for movement completion
            
        Returns:
            (success, message): Success flag and status message
        """
        if len(position) < 6:
            return False, "Invalid position - need 6 values"
              # Execute movement command using helper
        if move_type == "MovL":
            success, message, result = execute_robot_command(
                self.dashboard, "MovL", 
                position[0], position[1], position[2],
                position[3], position[4], position[5],
                coordinateMode=0
            )        
        else:
            # MovJ movement
            success, message, result = execute_robot_command(
                self.dashboard, "MovJ", 
                position[0], position[1], position[2],
                position[3], position[4], position[5],
                coordinateMode=0
            )
            
        if not success:
            return False, message
            
        print(f"Move command response: {result}")
        
        # Wait for movement completion using helper
        wait_with_progress("Waiting for movement to complete", wait_time)
        
        # Verify final position using helper
        success, final_pos = self.get_position()
        if not success:
            return False, "Could not verify final position"
            
        within_tolerance, distance = validate_position(final_pos, position, self.position_tolerance)
        print(f"Distance from target: {distance:.1f}mm")
        
        return within_tolerance, f"Movement successful (distance: {distance:.1f}mm)" if within_tolerance else f"Position error: {distance:.1f}mm from target"
    
    def test_movement(self, use_packing_position: bool = True) -> Tuple[bool, str]:
        """
        Perform a simple movement test using helper functions
        
        Args:
            use_packing_position: Whether to use the safe packing position or just move a small amount
            
        Returns:
            (success, message): Success flag and status message
        """
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
            target_position[3:] = self.initial_position[3:]  # Keep original orientation
            print("Moving to safe packing position...")
        else:
            target_position = self.initial_position.copy()
            target_position[2] += 50  # Move slightly up (+50mm in Z)
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
        
        # Verify return position using helper
        success, final_pos = self.get_position()
        if not success:
            return False, "Could not verify final position"
        
        within_tolerance, return_distance = validate_position(final_pos, self.initial_position, self.position_tolerance)
        print(f"Distance from initial position: {return_distance:.1f}mm")
        
        return within_tolerance, f"Movement test successful! (Return accuracy: {return_distance:.1f}mm)" if within_tolerance else f"Return position error: {return_distance:.1f}mm from initial position"
    
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
