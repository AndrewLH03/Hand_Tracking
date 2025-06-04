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
        
    def transform_to_robot_coords(self, shoulder: list, wrist: list) -> Tuple[float, float, float]:
        """
        Transform MediaPipe coordinates to robot coordinates
        
        Args:
            shoulder: [x, y, z] normalized coordinates (0-1) from MediaPipe
            wrist: [x, y, z] normalized coordinates (0-1) from MediaPipe
            
        Returns:
            tuple: (x, y, z) coordinates in robot coordinate system (mm)
        """
        # Calculate relative position from shoulder to wrist
        rel_x = wrist[0] - shoulder[0]
        rel_y = wrist[1] - shoulder[1] 
        rel_z = wrist[2] - shoulder[2]
        
        # Scale to robot workspace
        # MediaPipe coordinates are normalized (0-1), we need to scale appropriately
        robot_x = rel_x * self.workspace_size
        robot_y = rel_y * self.workspace_size
        robot_z = -rel_z * self.workspace_size + self.height_offset  # Invert Z and add offset
        
        # Apply safety limits
        robot_x = max(-self.workspace_size/2, min(self.workspace_size/2, robot_x))
        robot_y = max(-self.workspace_size/2, min(self.workspace_size/2, robot_y))
        robot_z = max(50, min(self.workspace_size, robot_z))  # Keep above table
        
        return robot_x, robot_y, robot_z

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
        self.dashboard_port = 29999
        self.feed_port = 30004
        
        # Robot connection objects
        self.dashboard = None
        self.feed = None
        
        # Control objects
        self.coordinate_transformer = CoordinateTransformer()
        self.hand_tracking_server = HandTrackingServer()
        
        # State variables
        self.running = False
        self.robot_enabled = False
        self.current_position = [0.0, 0.0, 200.0, 0.0, 0.0, 0.0]  # x, y, z, rx, ry, rz
        self.lock = threading.Lock()
        
        # Movement parameters
        self.movement_speed = 50  # mm/s
        self.movement_threshold = 5.0  # mm - minimum movement to execute
        
    def connect_robot(self) -> bool:
        """Connect to the CR3 robot"""
        try:
            print(f"Connecting to robot at {self.robot_ip}...")
            
            # Connect to dashboard (control interface)
            self.dashboard = DobotApiDashboard(self.robot_ip, self.dashboard_port)
            
            # Connect to feedback interface
            self.feed = DobotApiFeedBack(self.robot_ip, self.feed_port)
            
            print("Robot connected successfully")
            return True
            
        except Exception as e:
            print(f"Failed to connect to robot: {e}")
            return False
            
    def enable_robot(self) -> bool:
        """Enable the robot"""
        try:
            if not self.dashboard:
                print("Robot not connected")
                return False
                
            print("Enabling robot...")
            result = self.dashboard.EnableRobot()
            
            if "0" in result:  # Check for success
                self.robot_enabled = True
                print("Robot enabled successfully")
                return True
            else:
                print(f"Failed to enable robot: {result}")
                return False
                
        except Exception as e:
            print(f"Error enabling robot: {e}")
            return False
            
    def disable_robot(self):
        """Disable the robot"""
        try:
            if self.dashboard and self.robot_enabled:
                print("Disabling robot...")
                self.dashboard.DisableRobot()
                self.robot_enabled = False
                print("Robot disabled")
        except Exception as e:
            print(f"Error disabling robot: {e}")
            
    def move_to_position(self, x: float, y: float, z: float, 
                        rx: float = 0.0, ry: float = 0.0, rz: float = 0.0) -> bool:
        """
        Move robot to specified position using linear movement
        
        Args:
            x, y, z: Position coordinates in mm
            rx, ry, rz: Rotation angles in degrees
            
        Returns:
            bool: True if movement command was sent successfully
        """
        try:
            if not self.robot_enabled:
                return False
                
            # Check if movement is significant enough
            distance = math.sqrt(
                (x - self.current_position[0])**2 + 
                (y - self.current_position[1])**2 + 
                (z - self.current_position[2])**2
            )
            
            if distance < self.movement_threshold:
                return True  # Movement too small, skip
                
            # Use MovL (linear movement) with pose coordinates
            result = self.dashboard.MovL(x, y, z, rx, ry, rz, 
                                       coordinateMode=0,  # pose mode
                                       speed=self.movement_speed)
            
            if "0" in result:  # Check for success
                with self.lock:
                    self.current_position = [x, y, z, rx, ry, rz]
                return True
            else:
                print(f"Movement failed: {result}")
                return False
                
        except Exception as e:
            print(f"Error moving robot: {e}")
            return False
            
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