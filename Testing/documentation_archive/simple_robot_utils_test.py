#!/usr/bin/env python3
"""
Simple Robot Utils Test

A simplified script to test the robot_utils.py module.
This can be used as an example for integrating the module into the main test suite.

Usage:
    python simple_robot_utils_test.py [--robot-ip 192.168.1.6]
"""

import sys
import os
import argparse

# Add the parent directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Simple Robot Utils Test")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                      help="Robot IP address (default: 192.168.1.6)")
    
    args = parser.parse_args()
    
    print("=== SIMPLE ROBOT UTILS TEST ===")
    
    # Import robot_utils module
    try:
        from robot_control.robot_utils import RobotConnection, ROBOT_API_AVAILABLE
        print(f"✓ Imported robot_utils module successfully")
        print(f"✓ Robot API available: {ROBOT_API_AVAILABLE}")
        
        # Create robot connection
        print(f"\nCreating RobotConnection with IP: {args.robot_ip}")
        robot = RobotConnection(args.robot_ip)
        print("✓ Created RobotConnection instance")
        
        # Test network connectivity
        print("\nTesting network connectivity...")
        success, message = robot.test_network_connectivity()
        print(f"Network test: {'✓ Success' if success else '✗ Failed'} - {message}")
        
        # Test with invalid IP
        print("\nTesting with invalid IP (192.168.999.999)...")
        invalid_robot = RobotConnection("192.168.999.999")
        success, message = invalid_robot.test_network_connectivity()
        print(f"Invalid IP test: {'✓ Failed as expected' if not success else '✗ Unexpected success'} - {message}")
        
        print("\n=== TEST COMPLETE ===")
        return 0
        
    except ImportError as e:
        print(f"✗ Could not import robot_utils module: {e}")
        print("Make sure robot_utils.py is in the parent directory.")
        return 1
    except Exception as e:
        print(f"✗ Error during test: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
