#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Controller Module

Consolidated robot control functionality from robot_control.py, CR3_Control.py,
and control-related parts of other modules. Provides unified interface for
robot movement, positioning, and coordinate transformation.

Features:
- Unified robot movement commands
- Coordinate system transformation (MediaPipe to robot coordinates)
- Position validation and safety checking
- Hand tracking integration
- Safe movement patterns and collision avoidance
"""

import time
import math
import socket
import json
import queue
import threading
from typing import Optional, Tuple, List, Dict, Any, Union
from enum import Enum

from .core_api import CoreRobotAPI, get_robot_api
from .utilities import (
    parse_api_response, wait_with_progress, execute_robot_command,
    format_position, validate_position_values, calculate_distance_3d,
    calculate_movement_time, validate_position_tolerance, clamp_value,
    interpolate_positions, DEFAULT_WORKSPACE_LIMITS, SAFE_POSITIONS
)
from .migration_logger import get_logger

# Get logger instance
logger = get_logger(__name__)


class MovementMode(Enum):
    """Robot movement modes"""
    JOINT = "joint"      # Joint space movement
    LINEAR = "linear"    # Linear/Cartesian movement
    ARC = "arc"          # Arc movement
    SERVO = "servo"      # Servo control


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
        
        # Coordinate system offsets
        self.robot_base_offset = [200.0, 0.0, self.height_offset]  # Robot base position
        
        # Movement constraints
        self.max_speed = 100.0  # mm/s
        self.min_speed = 10.0   # mm/s
        self.safety_margin = 50.0  # mm from workspace boundaries
    
    def mediapipe_to_robot(self, shoulder: List[float], wrist: List[float]) -> List[float]:
        """
        Transform MediaPipe coordinates to robot coordinates
        
        Args:
            shoulder: Shoulder coordinates from MediaPipe [x, y, z]
            wrist: Wrist coordinates from MediaPipe [x, y, z]
            
        Returns:
            Robot coordinates [x, y, z, rx, ry, rz]
        """
        if not shoulder or not wrist or len(shoulder) < 3 or len(wrist) < 3:
            return SAFE_POSITIONS['home']
        
        # Calculate relative position (wrist relative to shoulder)
        rel_x = wrist[0] - shoulder[0]
        rel_y = wrist[1] - shoulder[1] 
        rel_z = wrist[2] - shoulder[2]
        
        # Scale to robot workspace
        scale_factor = (self.workspace_size * self.robot_reach_scale) / self.human_arm_reach
        
        # Transform coordinates (MediaPipe Y is up, robot Z is up)
        robot_x = self.robot_base_offset[0] + (rel_x * scale_factor)
        robot_y = self.robot_base_offset[1] + (rel_z * scale_factor)  # MP Z -> Robot Y
        robot_z = self.robot_base_offset[2] - (rel_y * scale_factor)  # MP Y -> Robot Z (inverted)
        
        # Apply safety constraints
        robot_x = clamp_value(robot_x, -self.workspace_size + self.safety_margin, 
                             self.workspace_size - self.safety_margin)
        robot_y = clamp_value(robot_y, -self.workspace_size + self.safety_margin,
                             self.workspace_size - self.safety_margin)
        robot_z = clamp_value(robot_z, self.height_offset,
                             self.height_offset + self.workspace_size - self.safety_margin)
        
        # Default orientation (pointing down)
        return [robot_x, robot_y, robot_z, 0.0, 90.0, 0.0]
    
    def validate_robot_position(self, position: List[float]) -> Tuple[bool, str]:
        """
        Validate if robot position is safe and reachable
        
        Args:
            position: Robot position [x, y, z, rx, ry, rz]
            
        Returns:
            (valid, message): Whether position is valid and validation message
        """
        return validate_position_values(position, DEFAULT_WORKSPACE_LIMITS)


class HandTrackingServer:
    """TCP server to receive coordinates from hand tracking system"""
    
    def __init__(self, host: str = 'localhost', port: int = 8888):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.coordinate_queue = queue.Queue(maxsize=10)
        self.server_thread = None
        
    def start_server(self):
        """Start the TCP server to listen for hand tracking data"""
        if self.running:
            return
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.running = True
            
            logger.info(f"Hand tracking server started on {self.host}:{self.port}")
            
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start hand tracking server: {e}")
            self.running = False
    
    def _server_loop(self):
        """Main server loop to handle incoming connections"""
        while self.running:
            try:
                client_socket, address = self.socket.accept()
                logger.info(f"Hand tracking client connected from {address}")
                
                self._handle_client(client_socket)
                
            except Exception as e:
                if self.running:  # Only log if we're supposed to be running
                    logger.error(f"Server error: {e}")
    
    def _handle_client(self, client_socket):
        """Handle individual client connection"""
        try:
            buffer = ""
            while self.running:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                buffer += data
                
                # Process complete messages (newline-separated)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            coordinates = json.loads(line.strip())
                            
                            # Add to queue (remove old if full)
                            if self.coordinate_queue.full():
                                try:
                                    self.coordinate_queue.get_nowait()
                                except queue.Empty:
                                    pass
                            
                            self.coordinate_queue.put_nowait(coordinates)
                            
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON received: {line}")
                        except queue.Full:
                            pass  # Queue full, skip this update
                            
        except Exception as e:
            logger.error(f"Client handling error: {e}")
        finally:
            client_socket.close()
    
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


class RobotController:
    """Main robot controller class handling movement and position operations"""
    
    def __init__(self, robot_ip: str = "192.168.1.6"):
        """
        Initialize robot controller
        
        Args:
            robot_ip: IP address of the robot
        """
        self.robot_ip = robot_ip
        self.robot_api = get_robot_api(robot_ip)
        self.coordinate_transformer = CoordinateTransformer()
        
        # Movement parameters
        self.default_speed = 50.0  # Default movement speed (%)
        self.max_speed = 100.0
        self.min_speed = 5.0
        
        # Position tracking
        self.last_position = None
        self.target_position = None
        
        # Safety parameters
        self.max_movement_distance = 100.0  # mm per move
        self.position_tolerance = 5.0  # mm
        
        # Status
        self.initialized = False
        self.last_error = None
    
    def initialize(self) -> Tuple[bool, str]:
        """Initialize the robot controller"""
        try:
            # Initialize robot API
            success, message = self.robot_api.initialize()
            if not success:
                self.last_error = message
                return False, f"API initialization failed: {message}"
            
            # Connect to robot
            success, message = self.robot_api.connect()
            if not success:
                self.last_error = message
                return False, f"Connection failed: {message}"
            
            # Clear alarms and enable robot
            success, message = self.robot_api.clear_robot_alarms()
            if not success:
                logger.warning(f"Could not clear alarms: {message}")
            
            success, message = self.robot_api.enable_robot()
            if not success:
                self.last_error = message
                return False, f"Robot enable failed: {message}"
            
            # Get initial position
            try:
                pos_response = self.robot_api.dashboard.GetPose()
                self.last_position = parse_api_response(pos_response, "numbers")
                if not self.last_position or len(self.last_position) < 6:
                    self.last_position = SAFE_POSITIONS['home']
            except Exception as e:
                logger.warning(f"Could not get initial position: {e}")
                self.last_position = SAFE_POSITIONS['home']
            
            self.initialized = True
            logger.info("✅ Robot controller initialized successfully")
            return True, "Robot controller initialized successfully"
            
        except Exception as e:
            self.last_error = str(e)
            return False, f"Initialization failed: {e}"
    
    def move_to_position(self, position: List[float], speed: float = None, 
                        mode: MovementMode = MovementMode.LINEAR) -> Tuple[bool, str]:
        """
        Move robot to specified position
        
        Args:
            position: Target position [x,y,z,rx,ry,rz]
            speed: Movement speed (0-100%), uses default if None
            mode: Movement mode (joint/linear/arc)
            
        Returns:
            (success, message): Movement result
        """
        if not self.initialized:
            return False, "Robot controller not initialized"
        
        if not self.robot_api.is_connected():
            return False, "Robot not connected"
        
        # Validate position
        valid, message = self.coordinate_transformer.validate_robot_position(position)
        if not valid:
            return False, f"Invalid position: {message}"
        
        # Use default speed if not specified
        if speed is None:
            speed = self.default_speed
        else:
            speed = clamp_value(speed, self.min_speed, self.max_speed)
        
        # Check movement distance for safety
        if self.last_position:
            distance = calculate_distance_3d(self.last_position, position)
            if distance > self.max_movement_distance:
                return False, f"Movement distance {distance:.1f}mm exceeds maximum {self.max_movement_distance}mm"
        
        try:
            # Execute movement based on mode
            if mode == MovementMode.LINEAR:
                command = f"MovL({position[0]:.2f},{position[1]:.2f},{position[2]:.2f},{position[3]:.2f},{position[4]:.2f},{position[5]:.2f},speedL={speed})"
                result = self.robot_api.dashboard.MovL(
                    position[0], position[1], position[2],
                    position[3], position[4], position[5]
                )
            elif mode == MovementMode.JOINT:
                result = self.robot_api.dashboard.MovJ(
                    position[0], position[1], position[2],
                    position[3], position[4], position[5]
                )
            else:
                return False, f"Movement mode {mode} not implemented"
            
            # Check result
            status = parse_api_response(result, "status")
            if status == 0:
                self.target_position = position[:]
                estimated_time = calculate_movement_time(
                    calculate_distance_3d(self.last_position or SAFE_POSITIONS['home'], position),
                    speed * 10  # Convert percentage to mm/s roughly
                )
                
                logger.info(f"Movement command sent: {format_position(position)}")
                return True, f"Movement started (estimated time: {estimated_time:.1f}s)"
            else:
                return False, f"Movement command failed with status {status}"
                
        except Exception as e:
            self.last_error = str(e)
            return False, f"Movement failed: {e}"
    
    def move_with_hand_tracking(self, shoulder: List[float], wrist: List[float]) -> Tuple[bool, str]:
        """
        Move robot based on hand tracking coordinates
        
        Args:
            shoulder: Shoulder coordinates from MediaPipe
            wrist: Wrist coordinates from MediaPipe
            
        Returns:
            (success, message): Movement result
        """
        # Transform coordinates
        robot_position = self.coordinate_transformer.mediapipe_to_robot(shoulder, wrist)
        
        # Move to position
        return self.move_to_position(robot_position, speed=30.0)  # Slower for hand tracking
    
    def move_relative(self, x_offset: float = 0, y_offset: float = 0, z_offset: float = 0,
                     rx_offset: float = 0, ry_offset: float = 0, rz_offset: float = 0) -> Tuple[bool, str]:
        """
        Move robot relative to current position
        
        Args:
            x_offset, y_offset, z_offset: Position offsets (mm)
            rx_offset, ry_offset, rz_offset: Rotation offsets (degrees)
            
        Returns:
            (success, message): Movement result
        """
        if not self.last_position:
            return False, "Current position unknown"
        
        # Calculate target position
        target_position = [
            self.last_position[0] + x_offset,
            self.last_position[1] + y_offset,
            self.last_position[2] + z_offset,
            self.last_position[3] + rx_offset,
            self.last_position[4] + ry_offset,
            self.last_position[5] + rz_offset
        ]
        
        return self.move_to_position(target_position)
    
    def move_to_safe_position(self, position_name: str = 'home') -> Tuple[bool, str]:
        """
        Move to a predefined safe position
        
        Args:
            position_name: Name of safe position ('home', 'packing', 'observation', 'service')
            
        Returns:
            (success, message): Movement result
        """
        if position_name not in SAFE_POSITIONS:
            return False, f"Unknown safe position: {position_name}"
        
        position = SAFE_POSITIONS[position_name][:]
        return self.move_to_position(position, speed=self.default_speed)
    
    def get_current_position(self) -> Tuple[bool, List[float], str]:
        """
        Get current robot position
        
        Returns:
            (success, position, message): Current position result
        """
        if not self.robot_api.is_connected():
            return False, [], "Robot not connected"
        
        try:
            pos_response = self.robot_api.dashboard.GetPose()
            position = parse_api_response(pos_response, "numbers")
            
            if position and len(position) >= 6:
                self.last_position = position[:]
                return True, position, "Position retrieved successfully"
            else:
                return False, [], "Invalid position response"
                
        except Exception as e:
            return False, [], f"Failed to get position: {e}"
    
    def wait_for_movement_complete(self, timeout: float = 30.0) -> Tuple[bool, str]:
        """
        Wait for current movement to complete
        
        Args:
            timeout: Maximum time to wait (seconds)
            
        Returns:
            (success, message): Wait result
        """
        if not self.target_position:
            return True, "No movement in progress"
        
        start_time = time.time()
        
        def check_position_reached():
            try:
                success, current_pos, _ = self.get_current_position()
                if success and current_pos:
                    within_tolerance, distance = validate_position_tolerance(
                        current_pos, self.target_position, self.position_tolerance
                    )
                    return within_tolerance
            except Exception:
                pass
            return False
        
        success, wait_time = wait_with_progress(
            "Waiting for movement completion",
            timeout,
            check_interval=0.5,
            check_func=check_position_reached
        )
        
        if success and check_position_reached():
            self.target_position = None
            return True, f"Movement completed in {wait_time:.1f}s"
        else:
            return False, "Movement did not complete within timeout"
    
    def emergency_stop(self) -> Tuple[bool, str]:
        """
        Emergency stop the robot
        
        Returns:
            (success, message): Stop result
        """
        if not self.robot_api.is_connected():
            return False, "Robot not connected"
        
        try:
            # Try multiple stop methods
            self.robot_api.dashboard.EmergencyStop()
            self.robot_api.dashboard.Stop()
            
            self.target_position = None
            logger.warning("🛑 Emergency stop activated")
            return True, "Emergency stop activated"
            
        except Exception as e:
            return False, f"Emergency stop failed: {e}"
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive controller status"""
        status = {
            'initialized': self.initialized,
            'connected': self.robot_api.is_connected() if self.robot_api else False,
            'last_position': self.last_position,
            'target_position': self.target_position,
            'last_error': self.last_error,
            'robot_ip': self.robot_ip
        }
        
        # Add robot API status
        if self.robot_api:
            status.update(self.robot_api.get_robot_status())
        
        return status
    
    def disconnect(self):
        """Disconnect from robot safely"""
        if self.robot_api:
            self.robot_api.disconnect()
        self.initialized = False


class IntegratedRobotSystem:
    """
    Complete robot system integrating hand tracking and robot control
    Replaces CR3RobotController from CR3_Control.py
    """
    
    def __init__(self, robot_ip: str = "192.168.1.6", hand_tracking_port: int = 8888):
        self.robot_ip = robot_ip
        self.hand_tracking_port = hand_tracking_port
        
        # Components - initialize with proper error handling
        try:
            self.robot_controller = RobotController(robot_ip)
            logger.info(f"Robot controller initialized for {robot_ip}")
        except Exception as e:
            logger.warning(f"Robot controller initialization failed: {e}")
            self.robot_controller = None
            
        try:
            self.hand_tracking_server = HandTrackingServer('localhost', hand_tracking_port)
            logger.info(f"Hand tracking server initialized on port {hand_tracking_port}")
        except Exception as e:
            logger.warning(f"Hand tracking server initialization failed: {e}")
            self.hand_tracking_server = None
        
        # Control state
        self.running = False
        self.hand_tracking_enabled = False
        self.last_update_time = time.time()
        self.update_interval = 0.1  # 10 Hz
        
        # Statistics
        self.total_movements = 0
        self.successful_movements = 0
    
    def initialize(self) -> Tuple[bool, str]:
        """Initialize the complete system"""
        try:
            # Initialize robot controller
            success, message = self.robot_controller.initialize()
            if not success:
                return False, f"Robot initialization failed: {message}"
            
            # Start hand tracking server
            self.hand_tracking_server.start_server()
            
            logger.info("✅ Integrated robot system initialized")
            return True, "System initialized successfully"
            
        except Exception as e:
            return False, f"System initialization failed: {e}"
    
    def start_hand_tracking_control(self):
        """Start hand tracking control loop"""
        if not self.robot_controller.initialized:
            logger.error("Robot controller not initialized")
            return
        
        self.hand_tracking_enabled = True
        self.running = True
        
        logger.info("🎯 Hand tracking control started")
        
        while self.running:
            try:
                # Get latest coordinates
                coordinates = self.hand_tracking_server.get_latest_coordinates()
                
                if coordinates and 'shoulder' in coordinates and 'wrist' in coordinates:
                    shoulder = coordinates['shoulder']
                    wrist = coordinates['wrist']
                    
                    # Move robot based on hand tracking
                    success, message = self.robot_controller.move_with_hand_tracking(shoulder, wrist)
                    
                    self.total_movements += 1
                    if success:
                        self.successful_movements += 1
                    else:
                        logger.warning(f"Hand tracking movement failed: {message}")
                
                # Control update rate
                elapsed = time.time() - self.last_update_time
                if elapsed < self.update_interval:
                    time.sleep(self.update_interval - elapsed)
                
                self.last_update_time = time.time()
                
            except KeyboardInterrupt:
                logger.info("Hand tracking control interrupted by user")
                break
            except Exception as e:
                logger.error(f"Hand tracking control error: {e}")
                time.sleep(1.0)  # Pause on error
        
        self.hand_tracking_enabled = False
        logger.info("🛑 Hand tracking control stopped")
    
    def stop(self):
        """Stop the system"""
        self.running = False
        self.hand_tracking_enabled = False
        self.hand_tracking_server.stop_server()
        self.robot_controller.disconnect()
        
        logger.info("System stopped")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics"""
        success_rate = 0.0
        if self.total_movements > 0:
            success_rate = (self.successful_movements / self.total_movements) * 100
        
        return {
            'total_movements': self.total_movements,
            'successful_movements': self.successful_movements,
            'success_rate': success_rate,
            'hand_tracking_enabled': self.hand_tracking_enabled,
            'running': self.running,
            'robot_status': self.robot_controller.get_status()
        }


# Factory functions for easy instantiation
def create_robot_controller(robot_ip: str = "192.168.1.6") -> RobotController:
    """Create and initialize a robot controller"""
    controller = RobotController(robot_ip)
    return controller


def create_integrated_system(robot_ip: str = "192.168.1.6", 
                           hand_tracking_port: int = 8888) -> IntegratedRobotSystem:
    """Create an integrated robot system"""
    system = IntegratedRobotSystem(robot_ip, hand_tracking_port)
    return system
