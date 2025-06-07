#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Testing Utilities

Shared robot testing functions used by both robot_preflight_check.py and startup.py
to eliminate code duplication and provide consistent testing behavior.
"""

from typing import Dict, Tuple, Optional
from robot_control import RobotSystem


class RobotTester:
    """Shared robot testing functionality"""
    
    def __init__(self, robot_ip: str = "192.168.1.6", timeout: float = 10.0):
        self.robot_ip = robot_ip
        self.timeout = timeout
        self.robot_system = RobotSystem(robot_ip)
    
    def test_basic_connectivity(self) -> Tuple[bool, str]:
        """Test basic network connectivity and robot connection"""
        # Network connectivity
        success, message = self.robot_system.connection.test_network_connectivity()
        if not success:
            return False, f"Network connectivity failed: {message}"
        
        # Robot API connection
        success, message = self.robot_system.connection.connect()
        if not success:
            return False, f"Robot API connection failed: {message}"
        
        return True, "Basic connectivity successful"
    
    def test_robot_readiness(self) -> Tuple[bool, str]:
        """Test robot status and enablement"""
        # Clear any existing errors
        self.robot_system.connection.clear_errors()
        
        # Check alarms before enablement
        alarm_ok, _ = self.robot_system.connection.check_robot_alarms()
        if not alarm_ok:
            return False, "Robot has active alarms before enablement"
        
        # Enable robot
        success, message = self.robot_system.connection.enable_robot(self.timeout)
        if not success:
            return False, f"Robot enablement failed: {message}"
        
        # Check alarms after enablement
        alarm_ok, _ = self.robot_system.connection.check_robot_alarms()
        if not alarm_ok:
            return False, "Robot has active alarms after enablement"
        
        return True, "Robot enabled and ready"
    
    def test_movement_capability(self) -> Tuple[bool, str]:
        """Test robot movement capability"""
        # Update controller dashboard reference
        self.robot_system.controller.dashboard = self.robot_system.connection.get_dashboard()
        
        # Perform movement test
        success, message = self.robot_system.controller.test_movement(use_packing_position=True)
        return success, message
    
    def run_quick_test(self) -> Tuple[bool, str]:
        """Run quick test without movement"""
        # Test basic connectivity
        success, message = self.test_basic_connectivity()
        if not success:
            return False, message
        
        # Test robot readiness (no movement)
        success, message = self.test_robot_readiness()
        return success, message
    
    def run_full_test(self) -> Tuple[bool, Dict[str, bool], Dict[str, str]]:
        """Run comprehensive test with movement"""
        test_results = {}
        test_messages = {}
        
        # Test 1: Basic connectivity
        success, message = self.test_basic_connectivity()
        test_results["Connectivity"] = success
        test_messages["Connectivity"] = message
        if not success:
            return False, test_results, test_messages
        
        # Test 2: Robot readiness
        success, message = self.test_robot_readiness()
        test_results["Robot Readiness"] = success
        test_messages["Robot Readiness"] = message
        if not success:
            return False, test_results, test_messages
        
        # Test 3: Movement capability
        success, message = self.test_movement_capability()
        test_results["Movement"] = success
        test_messages["Movement"] = message
        
        overall_success = all(test_results.values())
        return overall_success, test_results, test_messages
    
    def run_interactive_test(self, prompt_on_failure: bool = True) -> bool:
        """Run test with user interaction (for startup.py)"""
        try:
            # Test basic connectivity
            success, message = self.test_basic_connectivity()
            if not success:
                print(f"❌ {message}")
                if prompt_on_failure:
                    response = input("\nContinue anyway? (y/N): ")
                    return response.lower().startswith('y')
                return False
            print(f"✓ Network and API connection: {message}")
            
            # Test robot readiness
            success, message = self.test_robot_readiness()
            if not success:
                print(f"❌ {message}")
                if prompt_on_failure:
                    response = input("\nContinue anyway? (y/N): ")
                    return response.lower().startswith('y')
                return False
            print(f"✓ Robot status: {message}")
            
            # Test movement
            success, message = self.test_movement_capability()
            if not success:
                print(f"❌ Movement test failed: {message}")
                if prompt_on_failure:
                    response = input("\nContinue anyway? (y/N): ")
                    return response.lower().startswith('y')
                return False
            
            print(f"✅ Robot movement test successful: {message}")
            return True
            
        except Exception as e:
            print(f"❌ Robot test failed: {e}")
            print("This could indicate:")
            print("- Robot is not powered on or connected")
            print("- Network connectivity issues")
            print("- Robot is in manual mode or has errors")
            print("- Emergency stop is activated")
            
            if prompt_on_failure:
                response = input("\nContinue anyway? (y/N): ")
                return response.lower().startswith('y')
            return False
        
        finally:
            # Clean up connections
            self.cleanup()
    
    def cleanup(self):
        """Clean up robot connections"""
        try:
            self.robot_system.connection.disconnect()
        except Exception:
            pass  # Ignore cleanup errors


# Convenience functions for common use cases
def quick_robot_test(robot_ip: str = "192.168.1.6") -> bool:
    """Quick robot connectivity test without movement"""
    tester = RobotTester(robot_ip)
    try:
        success, message = tester.run_quick_test()
        return success
    finally:
        tester.cleanup()


def full_robot_test(robot_ip: str = "192.168.1.6") -> Tuple[bool, Dict[str, bool], Dict[str, str]]:
    """Full robot test with movement"""
    tester = RobotTester(robot_ip)
    try:
        return tester.run_full_test()
    finally:
        tester.cleanup()


def interactive_robot_test(robot_ip: str = "192.168.1.6") -> bool:
    """Interactive robot test with user prompts"""
    tester = RobotTester(robot_ip)
    return tester.run_interactive_test()
