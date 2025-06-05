#!/usr/bin/env python3
"""
Robot Utilities Test Script

A command-line tool to test the functionality of the robot_utils.py module.
This script can be run directly to validate the module works correctly.

Usage:
    python test_robot_utils.py --help
    python test_robot_utils.py --test-api          # Test API availability
    python test_robot_utils.py --test-init         # Test initialization
    python test_robot_utils.py --test-network      # Test network connectivity
    python test_robot_utils.py --test-all          # Run all tests
"""

import os
import sys
import argparse
import time

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Robot Utilities Test")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    parser.add_argument("--test-api", action="store_true", 
                       help="Test API availability")
    parser.add_argument("--test-init", action="store_true", 
                       help="Test initialization")
    parser.add_argument("--test-network", action="store_true", 
                       help="Test network connectivity")
    parser.add_argument("--test-all", action="store_true", 
                       help="Run all tests")
    
    args = parser.parse_args()
    
    # If no test is specified, run all tests
    if not any([args.test_api, args.test_init, args.test_network, args.test_all]):
        args.test_all = True
    
    print("ROBOT UTILITIES TEST SCRIPT")
    print("=" * 40)
    print(f"Robot IP: {args.robot_ip}")
    print("-" * 40)
    
    # Import robot_utils module
    try:
        sys.path.append('..')
        print("Importing robot_utils module...")
        from robot_utils import RobotConnection, ROBOT_API_AVAILABLE
        print("✓ Successfully imported robot_utils module")
    except ImportError as e:
        print(f"✗ Failed to import robot_utils module: {e}")
        print("Make sure robot_utils.py is in the parent directory.")
        return 1
    
    # Test API availability
    if args.test_api or args.test_all:
        print("\nTEST: API AVAILABILITY")
        print("-" * 40)
        print(f"Robot API available: {ROBOT_API_AVAILABLE}")
        if ROBOT_API_AVAILABLE:
            print("✓ Robot API is available")
        else:
            print("✗ Robot API is not available")
    
    # Test initialization
    if args.test_init or args.test_all:
        print("\nTEST: INITIALIZATION")
        print("-" * 40)
        try:
            print(f"Creating RobotConnection with IP: {args.robot_ip}")
            robot = RobotConnection(args.robot_ip)
            print("✓ Successfully created RobotConnection instance")
            
            # Check attributes
            expected_attrs = ["robot_ip", "dashboard_port", "move_port", "feed_port", 
                             "dashboard", "position_tolerance", "safe_packing_position"]
            
            print("Checking attributes...")
            for attr in expected_attrs:
                if hasattr(robot, attr):
                    print(f"✓ Has attribute: {attr}")
                else:
                    print(f"✗ Missing attribute: {attr}")
        except Exception as e:
            print(f"✗ Failed to initialize RobotConnection: {e}")
    
    # Test network connectivity
    if args.test_network or args.test_all:
        print("\nTEST: NETWORK CONNECTIVITY")
        print("-" * 40)
        try:
            print(f"Creating RobotConnection with IP: {args.robot_ip}")
            robot = RobotConnection(args.robot_ip)
            
            print(f"Testing network connectivity to {args.robot_ip}...")
            success, message = robot.test_network_connectivity()
            if success:
                print(f"✓ Network test succeeded: {message}")
            else:
                print(f"✗ Network test failed: {message}")
            
            print(f"Testing with invalid IP (192.168.999.999)...")
            invalid_robot = RobotConnection("192.168.999.999")
            success, message = invalid_robot.test_network_connectivity()
            if not success:
                print(f"✓ Invalid IP test correctly failed: {message}")
            else:
                print(f"✗ Invalid IP test unexpectedly succeeded: {message}")
        except Exception as e:
            print(f"✗ Error during network connectivity test: {e}")
    
    print("\nTEST SUMMARY")
    print("=" * 40)
    print("Robot utilities test completed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
