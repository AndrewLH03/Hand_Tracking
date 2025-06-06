#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CR3 Robot Pre-flight Verification Script

This script performs comprehensive testing of the CR3 robot connection and movement
capabilities before running the main hand tracking system. Contains the complete
perform_preflight_check method moved from robot_utils.py and robot_control.py.

Usage:
    python robot_preflight_check.py [--robot-ip 192.168.1.6] [--quick] [--timeout 15]

Options:
    --robot-ip IP    Robot IP address (default: 192.168.1.6)
    --quick          Run quick test (no movement)
    --timeout SEC    Test timeout in seconds (default: 10)
"""

import sys
import time
import argparse
from typing import Dict, Tuple
from robot_control.robot_control import RobotSystem


class RobotPreflightChecker:
    """Complete robot preflight checking functionality"""
    
    def __init__(self, robot_ip: str = "192.168.1.6", timeout: float = 10.0):
        self.robot_ip = robot_ip
        self.timeout = timeout
        self.robot_system = RobotSystem(robot_ip)
        
    def perform_preflight_check(self) -> Tuple[bool, Dict[str, bool], Dict[str, str]]:
        """
        Perform a comprehensive preflight check (moved from robot_utils.py/robot_control.py)
        
        Returns:
            (overall_success, test_results, test_messages)
        """
        test_results = {}
        test_messages = {}
        
        # Step 1: Network connectivity
        print("\n" + "="*60)
        print("🌐 TEST 1: NETWORK CONNECTIVITY")
        print("="*60)
        
        success, message = self.robot_system.connection.test_network_connectivity()
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
        
        success, message = self.robot_system.connection.connect()
        test_results["Robot API Connection"] = success
        test_messages["Robot API Connection"] = message
        status = "✅" if success else "❌"
        print(f"{status} Robot API Connection: {message}")
        
        if not success:
            return False, test_results, test_messages
        
        # Update controller dashboard reference
        self.robot_system.controller.dashboard = self.robot_system.connection.get_dashboard()
        
        # Step 3: Robot status
        print("\n" + "="*60)
        print("⚕️ TEST 3: ROBOT STATUS & ENABLEMENT")
        print("="*60)
        
        # Clear errors
        self.robot_system.connection.clear_errors()
        time.sleep(1)
        
        # Check alarms BEFORE robot enablement
        pre_alarm_ok, pre_errors = self.robot_system.connection.check_robot_alarms("Checking for robot alarms BEFORE enablement")
        
        # Enable robot
        mode_ok, mode_message = self.robot_system.connection.enable_robot(self.timeout)
        
        # Check alarms AFTER robot enablement
        post_alarm_ok, post_errors = self.robot_system.connection.check_robot_alarms("Checking for robot alarms AFTER enablement")
        
        # Get position for reference
        self.robot_system.controller.get_position()
        
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
        
        success, message = self.robot_system.controller.test_movement(use_packing_position=True)
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
    
    def run_quick_test(self) -> bool:
        """Run quick test without movement"""
        success = True
        
        # Network test
        net_success, net_msg = self.robot_system.connection.test_network_connectivity()
        print(f"🌐 Network: {'✅' if net_success else '❌'} {net_msg}")
        success &= net_success
        
        if net_success:
            # Connection test
            conn_success, conn_msg = self.robot_system.connection.connect()
            print(f"🤖 Connection: {'✅' if conn_success else '❌'} {conn_msg}")
            success &= conn_success
            
            if conn_success:
                # Status test
                self.robot_system.connection.clear_errors()
                alarm_ok, _ = self.robot_system.connection.check_robot_alarms()
                print(f"⚕️ Status: {'✅' if alarm_ok else '❌'} {'No alarms' if alarm_ok else 'Active alarms detected'}")
                success &= alarm_ok
        
        print(f"\n{'🎉 QUICK CHECK PASSED' if success else '❌ QUICK CHECK FAILED'}")
        return success
    
    def cleanup(self):
        """Clean up connections"""
        self.robot_system.connection.disconnect()


def main():
    """Main function - run preflight check"""
    parser = argparse.ArgumentParser(description="CR3 Robot Pre-flight Check")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick test without movement")
    parser.add_argument("--timeout", type=float, default=10.0,
                       help="Test timeout in seconds (default: 10)")
    
    args = parser.parse_args()
    
    print("🚀 ROBOT PRE-FLIGHT CHECK STARTING")
    if args.quick:
        print("(QUICK MODE - No Movement Test)")
    print(f"Robot IP: {args.robot_ip}")
    
    # Create preflight checker
    checker = RobotPreflightChecker(args.robot_ip, args.timeout)
    
    try:
        if args.quick:
            success = checker.run_quick_test()
        else:
            success, results, messages = checker.perform_preflight_check()
        
        return success
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Pre-flight check cancelled by user")
        return False
    except Exception as e:
        print(f"\n❌ Pre-flight check error: {e}")
        return False
    finally:
        # Always disconnect properly
        checker.cleanup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
