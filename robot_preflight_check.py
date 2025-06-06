#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CR3 Robot Pre-flight Verification Script (Simplified)

This script performs basic testing of the CR3 robot connection and movement
capabilities before running the main hand tracking system using the comprehensive
perform_preflight_check method from robot_utils.

Usage:
    python robot_preflight_check.py [--robot-ip 192.168.1.6] [--quick]

Options:
    --robot-ip IP    Robot IP address (default: 192.168.1.6)
    --quick          Run quick test (no movement)
"""

import sys
import argparse
from robot_control.robot_utils import RobotConnection


def main():
    """Main function - run preflight check using simplified approach"""
    parser = argparse.ArgumentParser(description="CR3 Robot Pre-flight Check")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick test without movement")
    
    args = parser.parse_args()
    
    print("🚀 ROBOT PRE-FLIGHT CHECK STARTING")
    if args.quick:
        print("(QUICK MODE - No Movement Test)")
    print(f"Robot IP: {args.robot_ip}")
    
    # Create robot connection
    robot = RobotConnection(args.robot_ip)
    
    try:
        if args.quick:
            # Quick test - just connectivity and status
            success = True
            
            # Network test
            net_success, net_msg = robot.test_network_connectivity()
            print(f"🌐 Network: {'✅' if net_success else '❌'} {net_msg}")
            success &= net_success
            
            if net_success:
                # Connection test
                conn_success, conn_msg = robot.connect()
                print(f"🤖 Connection: {'✅' if conn_success else '❌'} {conn_msg}")
                success &= conn_success
                
                if conn_success:
                    # Status test
                    robot.clear_errors()
                    alarm_ok, _ = robot.check_robot_alarms()
                    print(f"⚕️ Status: {'✅' if alarm_ok else '❌'} {'No alarms' if alarm_ok else 'Active alarms detected'}")
                    success &= alarm_ok
            
            print(f"\n{'🎉 QUICK CHECK PASSED' if success else '❌ QUICK CHECK FAILED'}")
            return success
        else:
            # Full preflight check with movement
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
