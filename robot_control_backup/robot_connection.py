#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Connection Management Module

Handles robot connectivity, network testing, connection establishment,
alarm checking, robot enabling, and basic status operations.
Used by both preflight check and main control systems.
"""

import sys
import os
import time
import socket
import re
from typing import Optional, Tuple, List, Dict, Any

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


# Helper utility functions for connection management
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


class RobotConnection:
    """Class to handle robot connectivity, status checking, and enabling"""
    
    def __init__(self, robot_ip: str = "192.168.1.6", dashboard_port: int = 29999, 
                 move_port: int = 30003, feed_port: int = 30004):
        """
        Initialize robot connection manager
        
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
        
        # Connection state
        self.is_connected = False
        self.is_enabled = False
    
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
                self.is_connected = True
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
                self.is_connected = False
                self.is_enabled = False
        
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
        Check and parse robot alarms
        
        Args:
            description: Description for progress display
            
        Returns:
            (alarm_ok, error_numbers): Whether alarms are OK and list of error codes
        """
        try:
            success, message, alarm_response = execute_robot_command(self.dashboard, "GetErrorID")
            if not success:
                print(f"Could not check alarms: {message}")
                return True, []  # Assume OK if we can't check
            
            print(f"Raw alarm response: {alarm_response}")
            
            # Extract error numbers using helper
            error_numbers = parse_api_response(alarm_response, "numbers")
            if not error_numbers:
                print("✅ No alarms detected")
                return True, []
                
            # Filter out normal status codes (1-6 are typically normal operational codes)
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
        """Clear robot errors"""
        success, message, result = execute_robot_command(self.dashboard, "ClearError")
        return success, f"Clear errors result: {result}" if success else message
    
    def get_robot_mode(self) -> Tuple[int, str]:
        """
        Get the current robot mode
        
        Returns:
            (mode, description): Robot mode as int and description
        """
        success, message, mode_response = execute_robot_command(self.dashboard, "RobotMode")
        if not success:
            return 0, message
            
        print(f"Raw robot mode response: {mode_response}")
        # Extract numeric mode
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
            self.is_enabled = True
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
            self.is_enabled = True
            return True, f"Robot enabled successfully after {elapsed_time:.1f}s (Mode {final_mode}: {final_description})"
        else:
            final_mode, final_description = self.get_robot_mode()
            return False, f"Robot enable timeout - Current mode: {final_mode} ({final_description}). May need manual intervention."
    
    def get_dashboard(self):
        """
        Get the dashboard connection for use by robot control module
        
        Returns:
            dashboard: The dashboard connection object or None
        """
        return self.dashboard
    
    def is_robot_connected(self) -> bool:
        """
        Check if robot is connected
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.is_connected and self.dashboard is not None
    
    def is_robot_enabled(self) -> bool:
        """
        Check if robot is enabled
        
        Returns:
            bool: True if enabled, False otherwise
        """
        return self.is_enabled


# Simple usage example
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Robot Connection Test")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    
    args = parser.parse_args()
    
    # Create robot connection
    robot_conn = RobotConnection(args.robot_ip)
    
    try:
        # Test connection
        print("Testing network connectivity...")
        success, message = robot_conn.test_network_connectivity()
        print(f"Network: {message}")
        
        if success:
            print("Connecting to robot...")
            success, message = robot_conn.connect()
            print(f"Connection: {message}")
            
            if success:
                print("Checking alarms...")
                alarm_ok, errors = robot_conn.check_robot_alarms()
                
                print("Enabling robot...")
                success, message = robot_conn.enable_robot()
                print(f"Enable: {message}")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Test cancelled by user")
    finally:
        # Always disconnect properly
        robot_conn.disconnect()
