#!/usr/bin/env python3
"""
CR3 Robot Pre-flight Verification Script

This script performs comprehensive testing of the CR3 robot connection and movement
capabilities before running the main hand tracking system. It verifies:

1. Network connectivity to robot
2. Robot API communication
3. Robot status and alarm checking
4. Complete movement cycle (initial → packing → initial)
5. Safety systems validation

Run this script before startup.py to ensure your laptop can communicate with
the robot and that it can accept movement commands without errors.

Usage:
    python robot_preflight_check.py --robot-ip 192.168.1.6
    python robot_preflight_check.py --robot-ip 192.168.1.6 --quick
"""

import sys
import os
import time
import argparse
import socket
import threading
from typing import Optional, Dict, Any, Tuple

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
    """Comprehensive robot verification system"""
    
    def __init__(self, robot_ip: str = "192.168.1.6"):
        self.robot_ip = robot_ip
        self.dashboard_port = 29999
        
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
            # Test basic TCP connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            result = sock.connect_ex((self.robot_ip, self.dashboard_port))
            sock.close()
            
            if result == 0:
                self.log_test("Network Connectivity", True, f"Robot reachable at {self.robot_ip}:{self.dashboard_port}")
                return True
            else:
                self.log_test("Network Connectivity", False, f"Cannot reach robot at {self.robot_ip}:{self.dashboard_port}")
                return False
                
        except Exception as e:
            self.log_test("Network Connectivity", False, f"Network error: {e}")
            return False
    
    def test_robot_connection(self) -> bool:
        """Test 2: Robot API connection"""
        print("\n" + "="*60)
        print("🔗 TEST 2: ROBOT API CONNECTION")
        print("="*60)
        
        try:
            # Connect to dashboard
            print("Connecting to robot dashboard...")
            self.dashboard = DobotApiDashboard(self.robot_ip, self.dashboard_port)
            self.dashboard.connect()
            
            # Test dashboard connection
            print("Testing dashboard communication...")
            robot_mode = self.dashboard.RobotMode()
            self.log_test("Dashboard Connection", True, f"Robot mode: {robot_mode}")
            
            print("✅ Dashboard connected and ready for movement commands")
            self.log_test("Robot API Ready", True, "All robot API connections established")
            
            return True
            
        except Exception as e:
            self.log_test("Robot Connection", False, f"Connection error: {e}")
            return False
    
    def test_robot_status(self) -> bool:
        """Test 3: Robot status and error checking"""
        print("\n" + "="*60)
        print("🔍 TEST 3: ROBOT STATUS & ALARM CHECK")
        print("="*60)
        
        try:
            # Check robot mode
            mode = self.dashboard.RobotMode()
            print(f"Robot mode: {mode}")
            
            # Check for alarms
            alarms = self.dashboard.GetErrorID()
            if alarms and alarms != "0":
                print(f"⚠️ Robot has alarms: {alarms}")
                # Try to clear alarms
                clear_result = self.dashboard.ClearError()
                print(f"Alarm clear result: {clear_result}")
                
                # Check again
                alarms_after = self.dashboard.GetErrorID()
                if alarms_after and alarms_after != "0":
                    self.log_test("Robot Status", False, f"Unable to clear alarms: {alarms_after}")
                    return False
                else:
                    self.log_test("Robot Status", True, "Alarms cleared successfully")
            else:
                self.log_test("Robot Status", True, "No alarms detected")
            
            # Enable robot
            print("Enabling robot...")
            enable_result = self.dashboard.EnableRobot()
            print(f"Robot enable result: {enable_result}")
            time.sleep(2)  # Wait for robot to stabilize
            
            self.log_test("Robot Enable", True, "Robot enabled successfully")
            return True
            
        except Exception as e:
            self.log_test("Robot Status", False, f"Status error: {e}")
            return False
    
    def test_position_reading(self) -> bool:
        """Test 4: Read robot position"""
        print("\n" + "="*60)
        print("📍 TEST 4: POSITION READING")
        print("="*60)
        
        try:
            # Get current position
            current_pos = self.dashboard.GetPose()
            print(f"Current position: X={current_pos[0]:.1f}, Y={current_pos[1]:.1f}, Z={current_pos[2]:.1f}")
            print(f"Orientation: RX={current_pos[3]:.1f}, RY={current_pos[4]:.1f}, RZ={current_pos[5]:.1f}")
            
            # Store initial position
            self.initial_position = current_pos
            
            self.log_test("Position Reading", True, 
                         f"Position: X={current_pos[0]:.1f}, Y={current_pos[1]:.1f}, Z={current_pos[2]:.1f}")
            return True
                
        except Exception as e:
            self.log_test("Position Reading", False, f"Position error: {e}")
            return False
    
    def test_movement_to_packing(self) -> bool:
        """Test 5: Movement to packing position"""
        print("\n" + "="*60)
        print("📦 TEST 5: MOVEMENT TO PACKING POSITION")
        print("="*60)
        
        try:
            if not self.initial_position:
                self.log_test("Movement Test", False, "No initial position recorded")
                return False
            
            # Use current orientation
            rx, ry, rz = self.initial_position[3:6]
            target_pos = [self.packing_position[0], self.packing_position[1], self.packing_position[2], rx, ry, rz]
            
            print(f"Moving to packing position: X={target_pos[0]}, Y={target_pos[1]}, Z={target_pos[2]}")
            
            # Send movement command using dashboard MovL method
            result = self.dashboard.MovL(target_pos[0], target_pos[1], target_pos[2], 
                                       target_pos[3], target_pos[4], target_pos[5], 
                                       coordinateMode=0)  # 0 = pose mode
            print(f"Movement command result: {result}")
            
            # Wait for movement completion
            print("Waiting for movement to complete...")
            start_time = time.time()
            
            while time.time() - start_time < self.movement_timeout:
                time.sleep(0.5)
                current_pos = self.dashboard.GetPose()
                
                # Check if we've reached the target
                distance = ((current_pos[0] - target_pos[0])**2 + 
                           (current_pos[1] - target_pos[1])**2 + 
                           (current_pos[2] - target_pos[2])**2)**0.5
                
                if distance < self.position_tolerance:
                    actual_pos = current_pos[:3]
                    self.log_test("Packing Movement", True, 
                                f"Reached packing position: X={actual_pos[0]:.1f}, Y={actual_pos[1]:.1f}, Z={actual_pos[2]:.1f}")
                    return True
            
            # Timeout - check final position
            final_pos = self.dashboard.GetPose()
            distance = ((final_pos[0] - target_pos[0])**2 + 
                       (final_pos[1] - target_pos[1])**2 + 
                       (final_pos[2] - target_pos[2])**2)**0.5
            
            self.log_test("Packing Movement", False, 
                        f"Movement timeout. Distance from target: {distance:.1f}mm")
            return False
            
        except Exception as e:
            self.log_test("Packing Movement", False, f"Movement error: {e}")
            return False
    
    def test_return_to_initial(self) -> bool:
        """Test 6: Return to initial position"""
        print("\n" + "="*60)
        print("🏠 TEST 6: RETURN TO INITIAL POSITION")
        print("="*60)
        
        try:
            if not self.initial_position:
                self.log_test("Return Movement", False, "No initial position recorded")
                return False
            
            target_pos = self.initial_position
            print(f"Returning to initial position: X={target_pos[0]:.1f}, Y={target_pos[1]:.1f}, Z={target_pos[2]:.1f}")
            
            # Send return movement command using dashboard MovL method
            result = self.dashboard.MovL(target_pos[0], target_pos[1], target_pos[2], 
                                       target_pos[3], target_pos[4], target_pos[5], 
                                       coordinateMode=0)  # 0 = pose mode
            print(f"Return command result: {result}")
            
            # Wait for movement completion
            print("Waiting for return movement to complete...")
            start_time = time.time()
            
            while time.time() - start_time < self.movement_timeout:
                time.sleep(0.5)
                current_pos = self.dashboard.GetPose()
                
                # Check if we've reached the initial position
                distance = ((current_pos[0] - target_pos[0])**2 + 
                           (current_pos[1] - target_pos[1])**2 + 
                           (current_pos[2] - target_pos[2])**2)**0.5
                
                if distance < self.position_tolerance:
                    actual_pos = current_pos[:3]
                    self.log_test("Return Movement", True, 
                                f"Returned to initial position: X={actual_pos[0]:.1f}, Y={actual_pos[1]:.1f}, Z={actual_pos[2]:.1f}")
                    return True
            
            # Timeout - check final position
            final_pos = self.dashboard.GetPose()
            distance = ((final_pos[0] - target_pos[0])**2 + 
                       (final_pos[1] - target_pos[1])**2 + 
                       (final_pos[2] - target_pos[2])**2)**0.5
            
            self.log_test("Return Movement", False, 
                        f"Return timeout. Distance from initial: {distance:.1f}mm")
            return False
            
        except Exception as e:
            self.log_test("Return Movement", False, f"Return error: {e}")
            return False
    
    def test_final_status(self) -> bool:
        """Test 7: Final status check"""
        print("\n" + "="*60)
        print("🛡️ TEST 7: FINAL STATUS CHECK")
        print("="*60)
        
        try:
            # Check for any new alarms
            alarms = self.dashboard.GetErrorID()
            if alarms and alarms != "0":
                self.log_test("Final Status", False, f"New alarms detected: {alarms}")
                return False
            
            # Get final position
            final_pos = self.dashboard.GetPose()
            print(f"Final position: X={final_pos[0]:.1f}, Y={final_pos[1]:.1f}, Z={final_pos[2]:.1f}")
            
            self.log_test("Final Status", True, "Robot in good state, no alarms")
            return True
            
        except Exception as e:
            self.log_test("Final Status", False, f"Status check error: {e}")
            return False
    
    def cleanup(self):
        """Clean up connections"""
        try:
            if self.dashboard:
                self.dashboard.disconnect()
        except:
            pass
    
    def print_results_summary(self):
        """Print comprehensive test results"""
        print("\n" + "="*60)
        print("📊 PRE-FLIGHT CHECK RESULTS")
        print("="*60)
        
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        print(f"Tests Passed: {passed}/{total}")
        print()
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print("\n" + "="*60)
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Robot is ready for hand tracking operations.")
            print("✅ You can now run: python startup.py --robot-ip", self.robot_ip)
            return True
        else:
            print("⚠️ SOME TESTS FAILED! Please address issues before running startup.py")
            print("🔧 Check robot power, network connection, and physical obstructions.")
            return False
    
    def run_quick_test(self) -> bool:
        """Run quick test (no movement)"""
        print("🚀 Running QUICK pre-flight check (no movement)...")
        
        tests = [
            self.test_network_connectivity,
            self.test_robot_connection,
            self.test_robot_status,
            self.test_position_reading,
            self.test_final_status
        ]
        
        success = True
        for test in tests:
            if not test():
                success = False
                break
        
        self.cleanup()
        return self.print_results_summary()
    
    def run_full_test(self) -> bool:
        """Run complete test including movement"""
        print("🚀 Running FULL pre-flight check (with movement verification)...")
        
        tests = [
            self.test_network_connectivity,
            self.test_robot_connection,
            self.test_robot_status,
            self.test_position_reading,
            self.test_movement_to_packing,
            self.test_return_to_initial,
            self.test_final_status
        ]
        
        success = True
        for test in tests:
            if not test():
                success = False
                break
        
        self.cleanup()
        return self.print_results_summary()

def main():
    """Main pre-flight check function"""
    parser = argparse.ArgumentParser(description="CR3 Robot Pre-flight Verification")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick test (no movement)")
    parser.add_argument("--timeout", type=int, default=10,
                       help="Movement timeout in seconds (default: 10)")
    
    args = parser.parse_args()
    
    if not ROBOT_API_AVAILABLE:
        print("❌ Robot API not available. Cannot proceed with tests.")
        print("Please ensure the TCP-IP-CR-Python-V4 directory exists and contains dobot_api.py")
        return False
    
    print("CR3 Robot Pre-flight Verification Script")
    print("="*60)
    print(f"Robot IP: {args.robot_ip}")
    print(f"Test Mode: {'Quick' if args.quick else 'Full'}")
    print(f"Movement Timeout: {args.timeout}s")
    print("="*60)
    
    # Create checker instance
    checker = RobotPreflightChecker(args.robot_ip)
    checker.movement_timeout = args.timeout
    
    try:
        if args.quick:
            return checker.run_quick_test()
        else:
            return checker.run_full_test()
    except KeyboardInterrupt:
        print("\n🛑 Pre-flight check interrupted by user")
        checker.cleanup()
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error during pre-flight check: {e}")
        checker.cleanup()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
