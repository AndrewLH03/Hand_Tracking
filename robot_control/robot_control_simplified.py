#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Control Module (Simplified)

Simplified robot control module that delegates to robot_utils.py for main functionality.
Reduces duplication by using consolidated methods from RobotConnection class.
"""

import time
from typing import Optional, Tuple, List, Dict, Any
from .robot_utils import RobotConnection, validate_position, ROBOT_API_AVAILABLE


class RobotController:
    """Simplified robot controller that delegates to RobotConnection"""
    
    def __init__(self, robot_connection: RobotConnection):
        """
        Initialize robot controller with connection manager
        
        Args:
            robot_connection: RobotConnection instance for connectivity
        """
        self.connection = robot_connection
        
        # Movement parameters
        self.position_tolerance = 5.0  # mm
        self.safe_packing_position = [250, 0, 300, 0, 0, 0]  # Safe packing position
        
        # Robot state
        self.initial_position = None
    
    def get_position(self) -> Tuple[bool, List[float]]:
        """Delegate to RobotConnection for position retrieval"""
        return self.connection.get_position()
    
    def move_to_position(self, position: List[float], 
                        move_type: str = "MovJ", 
                        wait_time: float = 5.0) -> Tuple[bool, str]:
        """Delegate to RobotConnection for movement"""
        return self.connection.move_to_position(position, move_type, wait_time)
    
    def test_movement(self, use_packing_position: bool = True) -> Tuple[bool, str]:
        """Delegate to RobotConnection for movement testing"""
        return self.connection.test_movement(use_packing_position)
    
    def move_to_safe_packing_position(self) -> Tuple[bool, str]:
        """Move robot to safe packing position"""
        return self.move_to_position(self.safe_packing_position, "MovJ")
    
    def move_relative(self, x_offset: float = 0, y_offset: float = 0, z_offset: float = 0) -> Tuple[bool, str]:
        """
        Move robot relative to current position
        
        Args:
            x_offset: X offset in mm
            y_offset: Y offset in mm  
            z_offset: Z offset in mm
            
        Returns:
            (success, message): Success flag and status message
        """
        # Get current position
        success, current_pos = self.get_position()
        if not success:
            return False, "Could not get current position"
        
        # Calculate target position
        target_pos = current_pos.copy()
        target_pos[0] += x_offset
        target_pos[1] += y_offset
        target_pos[2] += z_offset
        
        return self.move_to_position(target_pos)
    
    def set_position_tolerance(self, tolerance: float):
        """Set position tolerance for movement verification"""
        self.position_tolerance = tolerance
        self.connection.position_tolerance = tolerance
    
    def set_safe_packing_position(self, position: List[float]):
        """Set the safe packing position"""
        if len(position) >= 6:
            self.safe_packing_position = position.copy()


# Complete robot system integration
class RobotSystem:
    """Complete robot system with connection and control integration"""
    
    def __init__(self, robot_ip: str = "192.168.1.6"):
        """
        Initialize complete robot system
        
        Args:
            robot_ip: IP address of the robot
        """
        self.connection = RobotConnection(robot_ip)
        self.controller = RobotController(self.connection)
    
    def perform_preflight_check(self):
        """Delegate to RobotConnection for preflight check"""
        return self.connection.perform_preflight_check()
    
    def disconnect(self):
        """Disconnect from robot safely"""
        self.connection.disconnect()


# Simple usage example
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Robot Control Test")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="Robot IP address (default: 192.168.1.6)")
    
    args = parser.parse_args()
    
    # Create robot system
    robot_system = RobotSystem(args.robot_ip)
    
    try:
        # Run preflight check
        success, results, messages = robot_system.perform_preflight_check()
        
        if success:
            print("\nTesting additional control functions...")
            
            # Test relative movement
            success, message = robot_system.controller.move_relative(z_offset=10)
            print(f"Relative move: {message}")
            
            # Test safe packing position
            success, message = robot_system.controller.move_to_safe_packing_position()
            print(f"Safe packing: {message}")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Test cancelled by user")
    finally:
        # Always disconnect properly
        robot_system.disconnect()
