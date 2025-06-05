#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CR3 Robot Pre-flight Verification Script (Using robot_utils)

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
import argparse
from robot_utils import RobotConnection


def main():
    """Main function - run preflight check using RobotConnection"""
    parser = argparse.ArgumentParser(description="CR3 Robot Pre-flight Check")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick test without movement")
    
    args = parser.parse_args()
    
    # Create robot connection
    robot = RobotConnection(args.robot_ip)
    
    try:
        # For quick test, we skip the movement test
        if args.quick:
            # Connect to robot
            print("🚀 ROBOT PRE-FLIGHT CHECK STARTING (QUICK MODE)")
            print(f"Robot IP: {args.robot_ip}")
            print("="*60)
            
            # Step 1: Test network connectivity
            print("\n" + "="*60)
            print("🌐 TEST 1: NETWORK CONNECTIVITY")
            print("="*60)
            success, message = robot.test_network_connectivity()
            if not success:
                print(f"❌ Network connectivity test failed: {message}")
                return False
            print(f"✅ Network connectivity test passed: {message}")
            
            # Step 2: Connect to robot
            print("\n" + "="*60)
            print("🤖 TEST 2: ROBOT API CONNECTION")
            print("="*60)
            success, message = robot.connect()
            if not success:
                print(f"❌ Robot API connection test failed: {message}")
                return False
            print(f"✅ Robot API connection test passed: {message}")
            
            # Step 3: Clear errors and check alarms
            print("\n" + "="*60)
            print("⚕️ TEST 3: ROBOT STATUS")
            print("="*60)
            robot.clear_errors()
            alarm_ok, errors = robot.check_robot_alarms()
            if not alarm_ok:
                print(f"❌ Robot has active alarms: {errors}")
                return False
            print("✅ Robot status check passed: No active alarms")
            
            print("\n🎉 QUICK PRE-FLIGHT CHECK PASSED - Robot ready for operation!")
            return True
        else:
            # Full test including movement
            success, results, messages = robot.perform_preflight_check()
            return success
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Pre-flight check cancelled by user")
        return False
    except Exception as e:
        print(f"\n❌ Pre-flight check error: {e}")
        return False
    finally:
        # Always disconnect properly
        robot.disconnect()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
