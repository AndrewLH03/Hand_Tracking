#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Utilities Test Script

This script tests the RobotConnection class to verify that it works properly
with both startup.py and robot_preflight_check.py.

Usage:
    python test_robot_utils.py [--robot-ip 192.168.1.6] [--quick]

Options:
    --robot-ip IP    Robot IP address (default: 192.168.1.6)
    --quick          Run quick test (no movement)
    --preflight      Run full preflight check
    --startup        Test startup movement function
"""

import sys
import argparse
import time
from robot_utils import RobotConnection, ROBOT_API_AVAILABLE

def test_network_connectivity(robot):
    """Test network connectivity to robot"""
    print("\n=== Testing Network Connectivity ===")
    success, message = robot.test_network_connectivity()
    print(f"Network test: {'✅ Success' if success else '❌ Failed'} - {message}")
    return success

def test_connection(robot):
    """Test API connection to robot"""
    print("\n=== Testing API Connection ===")
    success, message = robot.connect()
    print(f"Connection test: {'✅ Success' if success else '❌ Failed'} - {message}")
    return success

def test_status(robot):
    """Test robot status and enablement"""
    print("\n=== Testing Robot Status ===")
    
    # Clear errors
    clear_success, clear_message = robot.clear_errors()
    print(f"Clear errors: {'✅ Success' if clear_success else '❌ Failed'} - {clear_message}")
    
    # Check alarms
    alarm_ok, errors = robot.check_robot_alarms()
    print(f"Alarm check: {'✅ Success' if alarm_ok else '❌ Failed'} - {errors if errors else 'No errors'}")
    
    # Get robot mode
    mode, description = robot.get_robot_mode()
    print(f"Robot mode: {mode} - {description}")
    
    # Enable robot
    enable_success, enable_message = robot.enable_robot()
    print(f"Robot enable: {'✅ Success' if enable_success else '❌ Failed'} - {enable_message}")
    
    # Get position
    pos_success, position = robot.get_position()
    if pos_success:
        print(f"Current position: X={position[0]:.1f}, Y={position[1]:.1f}, Z={position[2]:.1f}")
    else:
        print("❌ Failed to get position")
    
    return enable_success and alarm_ok

def test_movement(robot):
    """Test robot movement"""
    print("\n=== Testing Robot Movement ===")
    success, message = robot.test_movement(use_packing_position=True)
    print(f"Movement test: {'✅ Success' if success else '❌ Failed'} - {message}")
    return success

def simulate_startup_test(robot_ip):
    """Simulate the test_robot_movement function from startup.py"""
    print("\n=== Testing startup.py Movement Function ===")
    
    if not ROBOT_API_AVAILABLE:
        print("⚠️  Robot API not available - skipping movement test")
        return True
    
    print(f"Connecting to robot at {robot_ip}...")
    
    # Create a RobotConnection instance
    robot = RobotConnection(robot_ip)
    
    try:
        # Test network connectivity
        success, message = robot.test_network_connectivity()
        if not success:
            print(f"❌ Network connectivity test failed: {message}")
            return False
        print(f"✓ Network connection: {message}")
        
        # Connect to robot
        success, message = robot.connect()
        if not success:
            print(f"❌ Robot connection failed: {message}")
            return False
        print(f"✓ Robot connection: {message}")
        
        # Enable robot
        success, message = robot.enable_robot()
        if not success:
            print(f"❌ Robot enablement failed: {message}")
            return False
        print(f"✓ Robot enabled: {message}")
        
        # Perform movement test
        success, message = robot.test_movement(use_packing_position=True)
        if not success:
            print(f"❌ Movement test failed: {message}")
            return False
        
        print(f"✅ Robot movement test successful: {message}")
        return True
            
    except Exception as e:
        print(f"❌ Robot movement test failed: {e}")
        return False
        
    finally:
        # Clean up connections
        robot.disconnect()

def run_preflight_test(robot):
    """Run full preflight check"""
    print("\n=== Running Full Preflight Check ===")
    success, results, messages = robot.perform_preflight_check()
    
    print("\n=== Preflight Results ===")
    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}: {messages.get(test_name, '')}")
    
    return success

def main():
    parser = argparse.ArgumentParser(description="Robot Utilities Test")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick test without movement")
    parser.add_argument("--preflight", action="store_true", 
                       help="Run full preflight check")
    parser.add_argument("--startup", action="store_true", 
                       help="Test startup movement function")
    
    args = parser.parse_args()
    
    print("Robot Utilities Test")
    print("=" * 50)
    print(f"Robot IP: {args.robot_ip}")
    print(f"Quick Test: {'Yes' if args.quick else 'No'}")
    print(f"API Available: {'Yes' if ROBOT_API_AVAILABLE else 'No'}")
    
    if args.startup:
        # Test the startup.py movement function
        success = simulate_startup_test(args.robot_ip)
        print(f"\nStartup Test: {'✅ Passed' if success else '❌ Failed'}")
        return success
    
    # Create robot connection
    robot = RobotConnection(args.robot_ip)
    
    try:
        # Step 1: Test network connectivity
        if not test_network_connectivity(robot):
            print("❌ Network connectivity test failed")
            return False
        
        # Step 2: Test connection
        if not test_connection(robot):
            print("❌ Connection test failed")
            return False
        
        # Step 3: Test robot status
        if not test_status(robot):
            print("❌ Robot status test failed")
            return False
        
        # Step 4: Test movement (skip if quick test)
        if not args.quick:
            if not test_movement(robot):
                print("❌ Movement test failed")
                return False
        else:
            print("\n⚡ Skipping movement test (quick mode)")
        
        # Run full preflight check if requested
        if args.preflight:
            if not run_preflight_test(robot):
                print("❌ Preflight check failed")
                return False
        
        print("\n✅ All tests passed!")
        return True
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Test cancelled by user")
        return False
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        return False
    finally:
        # Always disconnect properly
        robot.disconnect()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
