#!/usr/bin/env python3
"""
CR3 Robot Control Module

This module controls the DoBot CR3 robot based on hand tracking coordinates.
It receives shoulder and wrist coordinates from the hand tracking system and
translates them to robot movements.

The coordinate system mapping:
- Shoulder coordinates represent the robot base (0,0,0 for the robot)
- Wrist coordinates represent the TCP (Tool Center Point) position
"""

import sys
import os
import threading
import time
import socket
import json
import queue
import math
from typing import Optional, Tuple, Dict, Any

# Add the TCP-IP-CR-Python-V4 directory to the path to import dobot_api
sys.path.append(os.path.join(os.path.dirname(__file__), 'TCP-IP-CR-Python-V4'))

from dobot_api import DobotApiDashboard, DobotApiFeedBack
try:
    from .robot_connection import RobotConnection
    from .robot_control import RobotController
except ImportError:
    from robot_connection import RobotConnection
    from robot_control import RobotController

class CoordinateTransformer:
    """Handles coordinate transformation from MediaPipe to robot coordinates"""
    
    def __init__(self, workspace_size: float = 400.0, height_offset: float = 200.0):
        """
        Initialize coordinate transformer
        
        Args:
            workspace_size: Size of the workspace in mm (robot can reach)
            height_offset: Z offset to keep robot above table surface in mm
        """
        self.workspace_size = workspace_size
        self.height_offset = height_offset
        
        # Calibration parameters for proper scaling
        self.human_arm_reach = 0.4  # Typical arm reach in MediaPipe normalized coordinates
        self.robot_reach_scale = 0.7  # Use 70% of robot workspace for safety
        self.movement_scale_factor = 0.6  # Scale down movements for precision
        
        # Coordinate system transformation parameters
        # MediaPipe: X=left->right, Y=top->bottom, Z=away from camera
        # Robot: X=forward, Y=left, Z=up (typical robot coordinate system)
        self.axis_mapping = {
            'x_scale': -1.0,  # Invert X axis
            'y_scale': 1.0,   # Keep Y axis same
            'z_scale': -1.0   # Invert Z axis
        }
        
        # Safety workspace boundaries (mm)
        self.safe_bounds = {
            'x_min': -200, 'x_max': 300,    # Robot forward/backward reach
            'y_min': -250, 'y_max': 250,    # Robot left/right reach  
            'z_min': 100,  'z_max': 400     # Robot height range
        }
        
        # Debug mode for coordinate tracking
        self.debug = True
        
    def transform_to_robot_coords(self, shoulder: list, wrist: list) -> Tuple[float, float, float]:
        """
        Transform MediaPipe coordinates to robot coordinates with proper scaling and validation
        
        Args:
            shoulder: [x, y, z] normalized coordinates (0-1) from MediaPipe
            wrist: [x, y, z] normalized coordinates (0-1) from MediaPipe
            
        Returns:
            tuple: (x, y, z) coordinates in robot coordinate system (mm)
        """
        if self.debug:
            print(f"Input - Shoulder: [{shoulder[0]:.3f}, {shoulder[1]:.3f}, {shoulder[2]:.3f}]")
            print(f"Input - Wrist: [{wrist[0]:.3f}, {wrist[1]:.3f}, {wrist[2]:.3f}]")
        
        # Calculate relative position from shoulder to wrist
        rel_x = wrist[0] - shoulder[0]
        rel_y = wrist[1] - shoulder[1] 
        rel_z = wrist[2] - shoulder[2]
        
        if self.debug:
            print(f"Relative: [{rel_x:.3f}, {rel_y:.3f}, {rel_z:.3f}]")
        
        # Apply coordinate system transformation and scaling
        # Transform MediaPipe coordinates to robot coordinate system
        robot_x = (rel_y * self.axis_mapping['x_scale'] * 
                  self.workspace_size * self.robot_reach_scale * self.movement_scale_factor)
        robot_y = (rel_x * self.axis_mapping['y_scale'] * 
                  self.workspace_size * self.robot_reach_scale * self.movement_scale_factor)
        robot_z = (rel_z * self.axis_mapping['z_scale'] * 
                  self.workspace_size * self.robot_reach_scale * self.movement_scale_factor) + self.height_offset
        
        if self.debug:
            print(f"Pre-validation: X:{robot_x:.1f}, Y:{robot_y:.1f}, Z:{robot_z:.1f}")
        
        # Apply safety limits and validation
        robot_x, robot_y, robot_z = self.validate_position(robot_x, robot_y, robot_z)
        
        if self.debug:
            print(f"Final robot coords: X:{robot_x:.1f}, Y:{robot_y:.1f}, Z:{robot_z:.1f}")
            print("-" * 50)
        
        return robot_x, robot_y, robot_z
    
    def validate_position(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """
        Validate and constrain robot position to safe workspace boundaries
        
        Args:
            x, y, z: Proposed robot coordinates in mm
            
        Returns:
            tuple: (x, y, z) validated and constrained coordinates
        """
        # Apply safety bounds
        x_safe = max(self.safe_bounds['x_min'], min(self.safe_bounds['x_max'], x))
        y_safe = max(self.safe_bounds['y_min'], min(self.safe_bounds['y_max'], y))
        z_safe = max(self.safe_bounds['z_min'], min(self.safe_bounds['z_max'], z))
        
        # Check if any coordinates were constrained
        if x != x_safe or y != y_safe or z != z_safe:
            if self.debug:
                print(f"WARNING: Position constrained from ({x:.1f}, {y:.1f}, {z:.1f}) to ({x_safe:.1f}, {y_safe:.1f}, {z_safe:.1f})")
        
        return x_safe, y_safe, z_safe
    
    def calibrate_workspace(self, test_movements: list) -> bool:
        """
        Calibrate the coordinate transformation based on test movements
        
        Args:
            test_movements: List of (shoulder, wrist, expected_robot_pos) tuples for calibration
            
        Returns:
            bool: True if calibration was successful
        """
        print("Starting workspace calibration...")
        
        # Calculate scaling factors based on test movements
        total_error = 0.0
        valid_movements = 0
        
        for shoulder, wrist, expected_pos in test_movements:
            calculated_pos = self.transform_to_robot_coords(shoulder, wrist)
            
            # Calculate error
            error = math.sqrt(
                (calculated_pos[0] - expected_pos[0])**2 +
                (calculated_pos[1] - expected_pos[1])**2 +
                (calculated_pos[2] - expected_pos[2])**2
            )
            
            total_error += error
            valid_movements += 1
            
            print(f"Test movement - Expected: {expected_pos}, Calculated: {calculated_pos}, Error: {error:.1f}mm")
        
        if valid_movements > 0:
            avg_error = total_error / valid_movements
            print(f"Calibration complete. Average error: {avg_error:.1f}mm")
            
            # Adjust scaling factors if error is too high
            if avg_error > 50:  # 50mm tolerance
                adjustment_factor = 50 / avg_error
                self.movement_scale_factor *= adjustment_factor
                print(f"Adjusted movement scale factor to: {self.movement_scale_factor:.3f}")
            
            return True
        else:
            print("Calibration failed - no valid test movements")
            return False
    
    def set_debug_mode(self, debug: bool):
        """Enable or disable debug output"""
        self.debug = debug
        
    def get_workspace_info(self) -> Dict[str, Any]:
        """Get current workspace configuration information"""
        return {
            'workspace_size': self.workspace_size,
            'height_offset': self.height_offset,
            'human_arm_reach': self.human_arm_reach,
            'robot_reach_scale': self.robot_reach_scale,
            'movement_scale_factor': self.movement_scale_factor,
            'safe_bounds': self.safe_bounds,
            'axis_mapping': self.axis_mapping
        }

class HandTrackingServer:
    """TCP server to receive coordinates from hand tracking"""
    
    def __init__(self, host: str = 'localhost', port: int = 8888):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.coordinate_queue = queue.Queue()
        
    def start_server(self):
        """Start the TCP server to listen for hand tracking data"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.running = True
            print(f"Hand tracking server listening on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.socket.accept()
                    print(f"Hand tracking client connected from {address}")
                    
                    buffer = ""
                    while self.running:
                        data = client_socket.recv(1024)
                        if not data:
                            break
                            
                        try:
                            # Decode and add to buffer
                            buffer += data.decode('utf-8')
                            
                            # Process complete JSON messages (delimited by newlines)
                            while '\n' in buffer:
                                line, buffer = buffer.split('\n', 1)
                                if line.strip():
                                    coordinate_data = json.loads(line.strip())
                                    self.coordinate_queue.put(coordinate_data)
                                    
                        except json.JSONDecodeError as e:
                            print(f"Invalid JSON received from hand tracking: {e}")
                            buffer = ""  # Clear buffer on error
                            
                except socket.error as e:
                    if self.running:
                        print(f"Socket error: {e}")
                        time.sleep(1)
                        
        except Exception as e:
            print(f"Server error: {e}")
            
    def stop_server(self):
        """Stop the TCP server"""
        self.running = False
        if self.socket:
            self.socket.close()
            
    def get_latest_coordinates(self) -> Optional[Dict[str, Any]]:
        """Get the latest coordinates from the queue"""
        try:
            # Get the most recent coordinates, discard old ones
            latest_coords = None
            while not self.coordinate_queue.empty():
                latest_coords = self.coordinate_queue.get_nowait()
            return latest_coords
        except queue.Empty:
            return None

class CR3RobotController:
    """Main controller for the CR3 robot with hand tracking integration"""
    
    def __init__(self, robot_ip: str = "192.168.1.6"):
        """
        Initialize the robot controller
        
        Args:
            robot_ip: IP address of the CR3 robot
        """
        self.robot_ip = robot_ip
        
        # Use consolidated robot control classes
        self.robot_connection = RobotConnection(robot_ip)
        self.robot_controller = RobotController(self.robot_connection)
        
        # Control objects
        self.coordinate_transformer = CoordinateTransformer()
        self.hand_tracking_server = HandTrackingServer()
        
        # State variables
        self.running = False
        self.current_position = [0.0, 0.0, 200.0, 0.0, 0.0, 0.0]  # x, y, z, rx, ry, rz
        self.lock = threading.Lock()
        
        # Movement parameters
        self.movement_threshold = 5.0  # mm - minimum movement to execute
        
    def connect_robot(self) -> bool:
        """Connect to the CR3 robot using consolidated connection class"""
        return self.robot_connection.connect()[0]
        
    def enable_robot(self) -> bool:
        """Enable the robot using consolidated connection class"""
        return self.robot_connection.enable_robot()[0]
        
    def disable_robot(self):
        """Disable the robot using consolidated connection class"""
        self.robot_connection.disconnect()
        
    def move_to_position(self, x: float, y: float, z: float, 
                        rx: float = 0.0, ry: float = 0.0, rz: float = 0.0) -> bool:
        """
        Move robot to specified position using consolidated controller
        
        Args:
            x, y, z: Position coordinates in mm
            rx, ry, rz: Rotation angles in degrees
            
        Returns:
            bool: True if movement command was sent successfully
        """
        try:
            # Check if movement is significant enough
            distance = math.sqrt(
                (x - self.current_position[0])**2 + 
                (y - self.current_position[1])**2 + 
                (z - self.current_position[2])**2
            )
            
            if distance < self.movement_threshold:
                return True  # Movement too small, skip
                
            # Use consolidated robot controller
            success, message = self.robot_controller.move_to_position([x, y, z, rx, ry, rz])
            
            if success:
                with self.lock:
                    self.current_position = [x, y, z, rx, ry, rz]
                return True
            else:
                print(f"Movement failed: {message}")
                return False
                
        except Exception as e:
            print(f"Error moving robot: {e}")
            return False
              # Robot control methods moved to robot_connection.py and robot_control.py
    # Use RobotConnection and RobotController classes for robot operations
            
    def process_hand_tracking_data(self):
        """Process incoming hand tracking data and move robot accordingly"""
        while self.running:
            try:
                # Get latest coordinates
                coord_data = self.hand_tracking_server.get_latest_coordinates()
                
                if coord_data and 'shoulder' in coord_data and 'wrist' in coord_data:
                    shoulder = coord_data['shoulder']
                    wrist = coord_data['wrist']
                    
                    # Transform coordinates to robot space
                    robot_x, robot_y, robot_z = self.coordinate_transformer.transform_to_robot_coords(
                        shoulder, wrist
                    )
                    
                    # Move robot to new position
                    self.move_to_position(robot_x, robot_y, robot_z)
                    
                    # Print current position for debugging
                    print(f"Target position: X:{robot_x:.1f}, Y:{robot_y:.1f}, Z:{robot_z:.1f}")
                    
                time.sleep(0.05)  # 20 Hz update rate
                
            except Exception as e:
                print(f"Error processing hand tracking data: {e}")
                time.sleep(0.1)
                
    def start(self):
        """Start the robot controller"""
        print("Starting CR3 Robot Controller...")
        
        # Connect to robot
        if not self.connect_robot():
            return False
            
        # Enable robot
        if not self.enable_robot():
            return False
            
        # Start hand tracking server in a separate thread
        server_thread = threading.Thread(target=self.hand_tracking_server.start_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Start processing thread
        self.running = True
        process_thread = threading.Thread(target=self.process_hand_tracking_data)
        process_thread.daemon = True
        process_thread.start()
        
        print("Robot controller started successfully")
        print("Waiting for hand tracking data...")
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.stop()
            
        return True
        
    def stop(self):
        """Stop the robot controller"""
        print("Stopping robot controller...")
        self.running = False
        
        # Stop hand tracking server
        self.hand_tracking_server.stop_server()
        
        # Disable robot
        self.disable_robot()
        
        print("Robot controller stopped")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CR3 Robot Controller with Hand Tracking")
    parser.add_argument("--robot-ip", default="192.168.1.6", 
                       help="IP address of the CR3 robot")
    parser.add_argument("--server-port", type=int, default=8888,
                       help="Port for hand tracking server")
    parser.add_argument("--workspace-size", type=float, default=400.0,
                       help="Robot workspace size in mm")
    
    args = parser.parse_args()
    
    # Create and start robot controller
    controller = CR3RobotController(robot_ip=args.robot_ip)
    controller.coordinate_transformer.workspace_size = args.workspace_size
    controller.hand_tracking_server.port = args.server_port
    
    controller.start()

if __name__ == "__main__":
    main()