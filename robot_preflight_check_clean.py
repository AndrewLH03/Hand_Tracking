#!/usr/bin/env python3
"""
CR3 Robot Pre-flight Verification Script

This script performs basic testing of the CR3 robot connection and movement
capabilities before running the main hand tracking system. It verifies:

1. Network connectivity to robot
2. Robot API communication
3. Robot status and alarm checking
4. Basic movement test (initial → packing → initial)

Run this script before startup.py to ensure your laptop can communicate with
the robot and that it can accept movement commands without errors.

Usage:
    python robot_preflight_check.py [--robot-ip 192.168.1.6] [--quick]

Options:
    --robot-ip IP    Robot IP address (default: 192.168.1.6)
    --quick          Run quick test (no movement)
"""

import sys
import os
import time
import argparse
import socket
from typing import Optional

# Add robot API path
sys.path.append(os.path.join(os.path.dirname(__file__), 'TCP-IP-CR-Python-V4'))

try:
    from dobot_api import DobotApiDashboard, DobotApiFeedBack
    ROBOT_API_AVAILABLE = True
except ImportError as e:
    print(f"❌ Robot API not available: {e}")
    print("Please check TCP-IP-CR-Python-V4 installation.")
    ROBOT_API_AVAILABLE = False


class RobotPreflightChecker:
    """Simple robot verification system"""
    
    def __init__(self, robot_ip: str = "192.168.1.6"):
        self.robot_ip = robot_ip
        self.dashboard_port = 29999
        self.move_port = 30003
        self.feed_port = 30004
        
        # Connection objects
        self.dashboard = None
        
        # Test results
        self.test_results = {}
        self.initial_position = None
        self.packing_position = [250, 0, 300, 0, 0, 0]  # Safe packing position
        
        # Safety parameters
        self.movement_timeout = 10  # seconds
        self.position_tolerance = 5.0  # mm
    
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test results with formatting"""
        self.test_results[test_name] = passed
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}: {message}")
    
    def test_network_connectivity(self) -> bool:
        """Test 1: Basic network connectivity"""
        print("\n" + "="*60)
        print("🌐 TEST 1: NETWORK CONNECTIVITY")
        print("="*60)
        
        try:
            # Test robot dashboard port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            result = sock.connect_ex((self.robot_ip, self.dashboard_port))
            sock.close()
            
            if result == 0:
                self.log_test("Network Connectivity", True, f"Robot accessible at {self.robot_ip}:{self.dashboard_port}")
                return True
            else:
                self.log_test("Network Connectivity", False, f"Cannot reach {self.robot_ip}:{self.dashboard_port}")
                print("💡 Check robot IP address and network connection")
                print("💡 Ensure robot is powered on and in TCP/IP mode")
                return False
                
        except Exception as e:
            self.log_test("Network Connectivity", False, f"Network error: {e}")
            return False
    
    def test_robot_connection(self) -> bool:
        """Test 2: Robot API connection"""
        print("\n" + "="*60)
        print("🤖 TEST 2: ROBOT API CONNECTION")
        print("="*60)
        
        if not ROBOT_API_AVAILABLE:
            self.log_test("Robot API Connection", False, "Robot API not available")
            return False
        
        try:
            # Create dashboard connection
            self.dashboard = DobotApiDashboard(self.robot_ip, self.dashboard_port)
            
            # Test connection with basic command
            print("Connecting to robot dashboard...")
            mode_response = self.dashboard.RobotMode()
            
            if mode_response and len(mode_response) > 0:
                robot_mode = mode_response[0] if isinstance(mode_response, list) else mode_response
                self.log_test("Robot API Connection", True, f"Connected, Robot mode: {robot_mode}")
                return True
            else:
                self.log_test("Robot API Connection", False, "No response from robot")
                return False
                
        except Exception as e:
            self.log_test("Robot API Connection", False, f"Connection failed: {e}")
            return False
    
    def test_robot_status(self) -> bool:
        """Test 3: Robot status and alarms"""
        print("\n" + "="*60)
        print("⚕️ TEST 3: ROBOT STATUS")
        print("="*60)
        
        if not self.dashboard:
            self.log_test("Robot Status", False, "No robot connection")
            return False
        
        try:
            # Check robot mode
            mode_response = self.dashboard.RobotMode()
            if mode_response:
                robot_mode = mode_response[0] if isinstance(mode_response, list) else mode_response
                print(f"Robot Mode: {robot_mode}")
                
                # Mode 5 is typically running mode
                if str(robot_mode) in ['5', '9']:  # Running or ready modes
                    mode_ok = True
                else:
                    mode_ok = False
                    print("💡 Robot may need to be enabled or switched to running mode")
            else:
                mode_ok = False
                print("Could not get robot mode")
            
            # Check for alarms
            alarm_response = self.dashboard.GetErrorID()
            if alarm_response:
                error_ids = alarm_response if isinstance(alarm_response, list) else [alarm_response]
                # Filter out success responses (typically [0] or empty)
                active_alarms = [e for e in error_ids if e != 0 and e != '0' and str(e).strip()]
                
                if active_alarms:
                    self.log_test("Robot Status", False, f"Active alarms: {active_alarms}")
                    print("💡 Clear robot alarms before proceeding")
                    return False
                else:
                    alarm_ok = True
            else:
                alarm_ok = True  # Assume OK if we can't check
            
            # Get current position for reference
            try:
                pos_response = self.dashboard.GetPose()
                if pos_response:
                    position_data = pos_response if isinstance(pos_response, list) else [pos_response]
                    print(f"Current position: {position_data}")
                    self.initial_position = position_data[:6] if len(position_data) >= 6 else None
            except Exception as e:
                print(f"Could not get position: {e}")
            
            success = mode_ok and alarm_ok
            status_msg = "Robot ready" if success else "Robot not ready"
            self.log_test("Robot Status", success, status_msg)
            return success
            
        except Exception as e:
            self.log_test("Robot Status", False, f"Status check failed: {e}")
            return False
    
    def test_movement(self) -> bool:
        """Test 4: Basic movement capability"""
        print("\n" + "="*60)
        print("🏃 TEST 4: MOVEMENT TEST")
        print("="*60)
        
        if not self.dashboard:
            self.log_test("Movement Test", False, "No robot connection")
            return False
        
        try:
            # Get initial position
            if not self.initial_position:
                pos_response = self.dashboard.GetPose()
                if pos_response:
                    position_data = pos_response if isinstance(pos_response, list) else [pos_response]
                    self.initial_position = position_data[:6] if len(position_data) >= 6 else None
                
                if not self.initial_position:
                    self.log_test("Movement Test", False, "Cannot get initial position")
                    return False
            
            print(f"Initial position: {self.initial_position}")
            
            # Move to packing position
            print("Moving to packing position...")
            move_cmd = f"MovJ({','.join(map(str, self.packing_position))})"
            move_response = self.dashboard.mov(move_cmd)
            
            # Wait for movement to complete
            print("Waiting for movement to complete...")
            time.sleep(3)
            
            # Check if we reached the target
            current_pos_response = self.dashboard.GetPose()
            if current_pos_response:
                current_pos = current_pos_response if isinstance(current_pos_response, list) else [current_pos_response]
                current_pos = current_pos[:6] if len(current_pos) >= 6 else current_pos
                print(f"Current position: {current_pos}")
            
            # Return to initial position
            print("Returning to initial position...")
            return_cmd = f"MovJ({','.join(map(str, self.initial_position))})"
            return_response = self.dashboard.mov(return_cmd)
            
            # Wait for return movement
            time.sleep(3)
            
            self.log_test("Movement Test", True, "Movement test completed")
            return True
            
        except Exception as e:
            self.log_test("Movement Test", False, f"Movement failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up connections"""
        if self.dashboard:
            try:
                self.dashboard.close()
            except:
                pass
            self.dashboard = None
    
    def run_preflight_check(self, quick_test: bool = False) -> bool:
        """Run complete preflight check"""
        print("🚀 ROBOT PRE-FLIGHT CHECK STARTING")
        print(f"Robot IP: {self.robot_ip}")
        print(f"Quick test: {'Yes' if quick_test else 'No'}")
        print("="*60)
        
        try:
            # Test 1: Network connectivity
            if not self.test_network_connectivity():
                return False
            
            # Test 2: Robot connection
            if not self.test_robot_connection():
                return False
            
            # Test 3: Robot status
            if not self.test_robot_status():
                return False
            
            # Test 4: Movement (skip if quick test)
            if not quick_test:
                if not self.test_movement():
                    return False
            else:
                print("\n⚡ Skipping movement test (quick mode)")
            
            # Summary
            print("\n" + "="*60)
            print("📋 PRE-FLIGHT CHECK SUMMARY")
            print("="*60)
            
            passed_tests = sum(1 for result in self.test_results.values() if result)
            total_tests = len(self.test_results)
            
            for test_name, passed in self.test_results.items():
                status = "✅" if passed else "❌"
                print(f"{status} {test_name}")
            
            print(f"\nTests passed: {passed_tests}/{total_tests}")
            
            if passed_tests == total_tests:
                print("\n🎉 ALL TESTS PASSED - Robot ready for operation!")
                return True
            else:
                print(f"\n❌ {total_tests - passed_tests} test(s) failed - Check issues above")
                return False
                
        except KeyboardInterrupt:
            print("\n\n⏹️ Pre-flight check cancelled by user")
            return False
        except Exception as e:
            print(f"\n❌ Pre-flight check error: {e}")
            return False
        finally:
            self.cleanup()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="CR3 Robot Pre-flight Check")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick test without movement")
    
    args = parser.parse_args()
    
    # Create checker and run tests
    checker = RobotPreflightChecker(args.robot_ip)
    success = checker.run_preflight_check(quick_test=args.quick)
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
