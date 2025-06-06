#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Control Module

Handles robot movement commands, position management, and control operations.
Consolidated from robot_utils.py to eliminate duplication.
"""

import time
import math
from typing import Optional, Tuple, List, Dict, Any
from .robot_connection import (
    RobotConnection, parse_api_response, wait_with_progress, 
    execute_robot_command, ROBOT_API_AVAILABLE
)


def validate_position(current_pos: List[float], target_pos: List[float], 
                     tolerance: float = 5.0) -> Tuple[bool, float]:
    """
    Validate if current position is within tolerance of target position
    
    Args:
        current_pos: Current position [x,y,z,rx,ry,rz]
        target_pos: Target position [x,y,z,rx,ry,rz]
        tolerance: Acceptable distance tolerance (mm)
        
    Returns:
        (within_tolerance, distance): Whether position is within tolerance and actual distance
    """
    if len(current_pos) < 3 or len(target_pos) < 3:
        return False, float('inf')
        
    # Calculate 3D distance (position only, ignore orientation)
    distance = math.sqrt(sum((current_pos[i] - target_pos[i])**2 for i in range(3)))
    return distance < tolerance, distance


class RobotController:
    """Robot controller class handling movement and position operations"""
    
    def __init__(self, robot_connection: RobotConnection):
        """
        Initialize robot controller with connection manager
        
        Args:
            robot_connection: RobotConnection instance for connectivity
        """
        self.connection = robot_connection
        self.dashboard = robot_connection.dashboard
        
        # Movement parameters
        self.position_tolerance = 5.0  # mm
        self.safe_packing_position = [250, 0, 300, 0, 0, 0]  # Safe packing position
        
        # Robot state
        self.initial_position = None
    
    def get_position(self) -> Tuple[bool, List[float]]:
        """
        Get current robot position
        
        Returns:
            (success, position): Success flag and position as [x,y,z,rx,ry,rz]
        """
        success, message, pos_response = execute_robot_command(self.dashboard, "GetPose")
        if not success:
            return False, []
            
        print(f"Raw position response: {pos_response}")
        
        # Extract numeric values using helper
        numbers = parse_api_response(pos_response, "numbers")
        if len(numbers) >= 6:
            position = [float(n) for n in numbers[:6]]
            print(f"Current position: X={position[0]:.1f}, Y={position[1]:.1f}, Z={position[2]:.1f}")
            return True, position
        else:
            return False, []
    
    def move_to_position(self, position: List[float], 
                        move_type: str = "MovJ", 
                        wait_time: float = 5.0) -> Tuple[bool, str]:
        """
        Move the robot to a position
        
        Args:
            position: Target position as [x,y,z,rx,ry,rz]
            move_type: Movement type (MovJ or MovL)
            wait_time: Time to wait for movement completion
            
        Returns:
            (success, message): Success flag and status message
        """
        if len(position) < 6:
            return False, "Invalid position - need 6 values"
        
        # Execute movement command
        if move_type == "MovL":
            success, message, result = execute_robot_command(
                self.dashboard, "MovL", 
                position[0], position[1], position[2],
                position[3], position[4], position[5],
                coordinateMode=0
            )        
        else:
            # MovJ movement
            success, message, result = execute_robot_command(
                self.dashboard, "MovJ", 
                position[0], position[1], position[2],
                position[3], position[4], position[5],
                coordinateMode=0
            )
            
        if not success:
            return False, message
            
        print(f"Move command response: {result}")
        
        # Wait for movement completion
        wait_with_progress("Waiting for movement to complete", wait_time)
        
        # Verify final position
        success, final_pos = self.get_position()
        if not success:
            return False, "Could not verify final position"
            
        within_tolerance, distance = validate_position(final_pos, position, self.position_tolerance)
        print(f"Distance from target: {distance:.1f}mm")
        
        return within_tolerance, f"Movement successful (distance: {distance:.1f}mm)" if within_tolerance else f"Position error: {distance:.1f}mm from target"
    
    def test_movement(self, use_packing_position: bool = True) -> Tuple[bool, str]:
        """
        Perform a movement test
        
        Args:
            use_packing_position: Whether to use the safe packing position or just move a small amount
            
        Returns:
            (success, message): Success flag and status message
        """
        # Store initial position if not already stored
        if not self.initial_position:
            success, position = self.get_position()
            if not success:
                return False, "Could not get initial position"
            self.initial_position = position
        
        print(f"Initial position: {self.initial_position}")
        
        # Determine target position
        if use_packing_position:
            target_position = self.safe_packing_position.copy()
            print("Moving to safe packing position with safe orientation...")
        else:
            target_position = self.initial_position.copy()
            target_position[2] += 50  # Move slightly up (+50mm in Z)
            print("Moving slightly up (+50mm in Z)...")
        
        # Move to target position
        success, message = self.move_to_position(target_position)
        if not success:
            return False, f"Failed to move to target: {message}"
        
        # Return to initial position
        print("Returning to initial position...")
        success, message = self.move_to_position(self.initial_position)
        if not success:
            return False, f"Failed to return to initial position: {message}"
        
        # Verify return position
        success, final_pos = self.get_position()
        if not success:
            return False, "Could not verify final position"
        
        within_tolerance, return_distance = validate_position(final_pos, self.initial_position, self.position_tolerance)
        print(f"Distance from initial position: {return_distance:.1f}mm")
        
        return within_tolerance, f"Movement test successful! (Return accuracy: {return_distance:.1f}mm)" if within_tolerance else f"Return position error: {return_distance:.1f}mm from initial position"
    
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
    
    def emergency_stop(self) -> Tuple[bool, str]:
        """Emergency stop the robot"""
        success, message, result = execute_robot_command(self.dashboard, "EmergencyStop")
        return success, f"Emergency stop result: {result}" if success else message
    
    def pause_robot(self) -> Tuple[bool, str]:
        """Pause robot movement"""
        success, message, result = execute_robot_command(self.dashboard, "Pause")
        return success, f"Pause result: {result}" if success else message
    
    def continue_robot(self) -> Tuple[bool, str]:
        """Continue robot movement after pause"""
        success, message, result = execute_robot_command(self.dashboard, "Continue")
        return success, f"Continue result: {result}" if success else message


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
        """Run preflight check using connection methods"""
        return self.connection.perform_preflight_check()
    
    def disconnect(self):
        """Disconnect from robot safely"""
        self.connection.disconnect()


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