#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROS Service Bridge

Provides Python interface to ROS-6AXis C++ services via subprocess calls.
This bridge allows the existing Python codebase to communicate with the 
ROS-based robot control system while maintaining API compatibility.
"""

import os
import sys
import json
import time
import subprocess
import threading
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ROSServiceStatus(Enum):
    """Status of ROS services"""
    UNKNOWN = 0
    RUNNING = 1
    STOPPED = 2
    ERROR = 3


@dataclass
class ROSServiceResponse:
    """Standardized ROS service response"""
    success: bool
    data: Any
    message: str
    timestamp: float


class ROSServiceBridge:
    """
    Bridge between Python and ROS C++ services
    """
    
    def __init__(self, robot_ip: str = "192.168.1.6", 
                 ros_workspace: str = None):
        self.robot_ip = robot_ip
        self.ros_workspace = ros_workspace or self._find_ros_workspace()
        self.ros_executable = None
        self.ros_process = None
        self.service_status = ROSServiceStatus.UNKNOWN
        self._lock = threading.Lock()
        
        # Service mappings from TCP commands to ROS services
        self.service_mappings = {
            # Dashboard commands
            'EnableRobot': '/dobot_bringup/srv/EnableRobot',
            'DisableRobot': '/dobot_bringup/srv/DisableRobot',
            'ClearError': '/dobot_bringup/srv/ClearError',
            'ResetRobot': '/dobot_bringup/srv/ResetRobot',
            'RobotMode': '/dobot_bringup/srv/RobotMode',
            'GetErrorID': '/dobot_bringup/srv/GetErrorID',
            'PowerOn': '/dobot_bringup/srv/PowerOn',
            'PowerOff': '/dobot_bringup/srv/PowerOff',
            'BrakeHold': '/dobot_bringup/srv/BrakeHold',
            'BrakeRelease': '/dobot_bringup/srv/BrakeRelease',
            'EmergencyStop': '/dobot_bringup/srv/EmergencyStop',
            
            # Movement commands
            'MovJ': '/dobot_bringup/srv/MovJ',
            'MovL': '/dobot_bringup/srv/MovL',
            'GetPose': '/dobot_bringup/srv/GetPose',
            'GetAngle': '/dobot_bringup/srv/GetAngle',
            
            # Speed/Acceleration commands
            'SpeedFactor': '/dobot_bringup/srv/SpeedFactor',
            'SpeedJ': '/dobot_bringup/srv/SpeedJ',
            'SpeedL': '/dobot_bringup/srv/SpeedL',
            'AccJ': '/dobot_bringup/srv/AccJ',
            'AccL': '/dobot_bringup/srv/AccL',
        }
    
    def _find_ros_workspace(self) -> str:
        """Find ROS workspace directory"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        ros_path = os.path.join(parent_dir, 'TCP-IP-ROS-6AXis')
        
        if os.path.exists(ros_path):
            return ros_path
        
        # Fallback: search in common locations
        possible_paths = [
            os.path.join(parent_dir, 'TCP-IP-ROS-6AXis'),
            os.path.join(os.path.expanduser('~'), 'TCP-IP-ROS-6AXis'),
            '/opt/TCP-IP-ROS-6AXis'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return ros_path  # Return default even if not found
    
    def _find_ros_executable(self) -> Optional[str]:
        """Find the ROS executable for CR3"""
        executable_paths = [
            os.path.join(self.ros_workspace, 'rosdemo_v4', 'build', 'rosdemo_v4'),
            os.path.join(self.ros_workspace, 'rosdemo_v4', 'rosdemo_v4'),
            os.path.join(self.ros_workspace, 'dobot_v4_bringup', 'build', 'dobot_v4_bringup'),
            os.path.join(self.ros_workspace, 'dobot_v4_bringup', 'dobot_v4_bringup'),
        ]
        
        for path in executable_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def build_ros_workspace(self) -> Tuple[bool, str]:
        """Build the ROS workspace"""
        try:
            if not os.path.exists(self.ros_workspace):
                return False, f"ROS workspace not found: {self.ros_workspace}"
            
            # Try to build using catkin_make or colcon
            build_commands = [
                ['catkin_make'],
                ['colcon', 'build'],
                ['make']
            ]
            
            for cmd in build_commands:
                try:
                    result = subprocess.run(
                        cmd, 
                        cwd=self.ros_workspace,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout
                    )
                    
                    if result.returncode == 0:
                        return True, f"ROS workspace built successfully with {cmd[0]}"
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            
            return False, "Failed to build ROS workspace with any method"
            
        except Exception as e:
            return False, f"Build error: {e}"
    
    def start_ros_services(self) -> Tuple[bool, str]:
        """Start ROS services"""
        try:
            with self._lock:
                if self.ros_process and self.ros_process.poll() is None:
                    return True, "ROS services already running"
                
                # Find executable
                self.ros_executable = self._find_ros_executable()
                if not self.ros_executable:
                    # Try to build first
                    build_success, build_msg = self.build_ros_workspace()
                    if not build_success:
                        return False, f"ROS executable not found and build failed: {build_msg}"
                    
                    self.ros_executable = self._find_ros_executable()
                    if not self.ros_executable:
                        return False, "ROS executable still not found after build"
                
                # Start ROS process
                self.ros_process = subprocess.Popen(
                    [self.ros_executable, self.robot_ip],
                    cwd=os.path.dirname(self.ros_executable),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Wait a moment for startup
                time.sleep(2.0)
                
                # Check if process is still running
                if self.ros_process.poll() is None:
                    self.service_status = ROSServiceStatus.RUNNING
                    return True, f"ROS services started successfully (PID: {self.ros_process.pid})"
                else:
                    stdout, stderr = self.ros_process.communicate()
                    return False, f"ROS process failed to start: {stderr}"
        
        except Exception as e:
            return False, f"Failed to start ROS services: {e}"
    
    def stop_ros_services(self) -> None:
        """Stop ROS services"""
        with self._lock:
            if self.ros_process:
                try:
                    self.ros_process.terminate()
                    self.ros_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.ros_process.kill()
                    self.ros_process.wait()
                finally:
                    self.ros_process = None
                    self.service_status = ROSServiceStatus.STOPPED
    
    def is_ros_available(self) -> bool:
        """Check if ROS services are available"""
        return (self.service_status == ROSServiceStatus.RUNNING and 
                self.ros_process and 
                self.ros_process.poll() is None)
    
    def call_service(self, service_name: str, request_data: Dict = None) -> ROSServiceResponse:
        """
        Call a ROS service
        
        Args:
            service_name: Name of the service (TCP command name)
            request_data: Service request data
            
        Returns:
            ROSServiceResponse with result
        """
        try:
            if not self.is_ros_available():
                start_success, start_msg = self.start_ros_services()
                if not start_success:
                    return ROSServiceResponse(
                        success=False,
                        data=None,
                        message=f"ROS services not available: {start_msg}",
                        timestamp=time.time()
                    )
            
            # Get ROS service name
            ros_service = self.service_mappings.get(service_name)
            if not ros_service:
                return ROSServiceResponse(
                    success=False,
                    data=None,
                    message=f"Unknown service: {service_name}",
                    timestamp=time.time()
                )
            
            # For now, simulate service calls since we need actual ROS environment
            # In a real implementation, this would use rosservice call or equivalent
            return self._simulate_service_call(service_name, request_data)
            
        except Exception as e:
            return ROSServiceResponse(
                success=False,
                data=None,
                message=f"Service call failed: {e}",
                timestamp=time.time()
            )
    
    def _simulate_service_call(self, service_name: str, request_data: Dict = None) -> ROSServiceResponse:
        """
        Simulate ROS service calls for testing
        TODO: Replace with actual ROS service calls when ROS environment is set up
        """
        simulation_data = {
            'RobotMode': {'mode': 5, 'description': 'Running'},
            'GetErrorID': {'errors': []},
            'EnableRobot': {'result': 'OK'},
            'DisableRobot': {'result': 'OK'},
            'ClearError': {'result': 'OK'},
            'GetPose': {'pose': [0, 0, 0, 0, 0, 0]},
            'GetAngle': {'angles': [0, 0, 0, 0, 0, 0]},
            'MovJ': {'result': 'OK'},
            'MovL': {'result': 'OK'},
            'PowerOn': {'result': 'OK'},
            'PowerOff': {'result': 'OK'},
            'BrakeHold': {'result': 'OK'},
            'BrakeRelease': {'result': 'OK'},
            'EmergencyStop': {'result': 'OK'},
            'SpeedFactor': {'result': 'OK'},
            'SpeedJ': {'result': 'OK'},
            'SpeedL': {'result': 'OK'},
            'AccJ': {'result': 'OK'},
            'AccL': {'result': 'OK'},
        }
        
        data = simulation_data.get(service_name, {'result': 'OK'})
        
        return ROSServiceResponse(
            success=True,
            data=data,
            message=f"Simulated {service_name} call successful",
            timestamp=time.time()
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of ROS services"""
        return {
            'service_status': self.service_status.name,
            'ros_workspace': self.ros_workspace,
            'ros_executable': self.ros_executable,
            'process_running': self.is_ros_available(),
            'robot_ip': self.robot_ip,
            'available_services': list(self.service_mappings.keys())
        }


class ROSDashboard:
    """
    ROS Dashboard API providing same interface as TCP Dashboard
    """
    
    def __init__(self, robot_ip: str = "192.168.1.6"):
        self.robot_ip = robot_ip
        self.bridge = ROSServiceBridge(robot_ip)
        self._connected = False
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to ROS services"""
        success, message = self.bridge.start_ros_services()
        self._connected = success
        return success, message
    
    def disconnect(self) -> None:
        """Disconnect from ROS services"""
        self.bridge.stop_ros_services()
        self._connected = False
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected and self.bridge.is_ros_available()
    
    # Dashboard Commands (matching TCP API)
    def enable_robot(self) -> Any:
        """Enable robot"""
        response = self.bridge.call_service('EnableRobot')
        return response.data if response.success else None
    
    def disable_robot(self) -> Any:
        """Disable robot"""
        response = self.bridge.call_service('DisableRobot')
        return response.data if response.success else None
    
    def clear_error(self) -> Any:
        """Clear robot errors"""
        response = self.bridge.call_service('ClearError')
        return response.data if response.success else None
    
    def reset_robot(self) -> Any:
        """Reset robot"""
        response = self.bridge.call_service('ResetRobot')
        return response.data if response.success else None
    
    def robot_mode(self) -> Any:
        """Get robot mode"""
        response = self.bridge.call_service('RobotMode')
        return response.data if response.success else None
    
    def get_error_id(self) -> Any:
        """Get error IDs"""
        response = self.bridge.call_service('GetErrorID')
        return response.data if response.success else None
    
    def power_on(self) -> Any:
        """Power on robot"""
        response = self.bridge.call_service('PowerOn')
        return response.data if response.success else None
    
    def power_off(self) -> Any:
        """Power off robot"""
        response = self.bridge.call_service('PowerOff')
        return response.data if response.success else None
    
    def brake_hold(self) -> Any:
        """Hold brake"""
        response = self.bridge.call_service('BrakeHold')
        return response.data if response.success else None
    
    def brake_release(self) -> Any:
        """Release brake"""
        response = self.bridge.call_service('BrakeRelease')
        return response.data if response.success else None
    
    def emergency_stop(self) -> Any:
        """Emergency stop"""
        response = self.bridge.call_service('EmergencyStop')
        return response.data if response.success else None
    
    def mov_j(self, joint_positions: List[float], *args) -> Any:
        """Joint movement"""
        request_data = {'joints': joint_positions, 'args': args}
        response = self.bridge.call_service('MovJ', request_data)
        return response.data if response.success else None
    
    def mov_l(self, cartesian_coords: List[float], *args) -> Any:
        """Linear movement"""
        request_data = {'coords': cartesian_coords, 'args': args}
        response = self.bridge.call_service('MovL', request_data)
        return response.data if response.success else None
    
    def get_pose(self) -> Any:
        """Get current pose"""
        response = self.bridge.call_service('GetPose')
        return response.data if response.success else None
    
    def get_angle(self) -> Any:
        """Get current joint angles"""
        response = self.bridge.call_service('GetAngle')
        return response.data if response.success else None
    
    def speed_factor(self, factor: float) -> Any:
        """Set speed factor"""
        request_data = {'factor': factor}
        response = self.bridge.call_service('SpeedFactor', request_data)
        return response.data if response.success else None
    
    def speed_j(self, speed: float) -> Any:
        """Set joint speed"""
        request_data = {'speed': speed}
        response = self.bridge.call_service('SpeedJ', request_data)
        return response.data if response.success else None
    
    def speed_l(self, speed: float) -> Any:
        """Set linear speed"""
        request_data = {'speed': speed}
        response = self.bridge.call_service('SpeedL', request_data)
        return response.data if response.success else None
    
    def acc_j(self, acceleration: float) -> Any:
        """Set joint acceleration"""
        request_data = {'acceleration': acceleration}
        response = self.bridge.call_service('AccJ', request_data)
        return response.data if response.success else None
    
    def acc_l(self, acceleration: float) -> Any:
        """Set linear acceleration"""
        request_data = {'acceleration': acceleration}
        response = self.bridge.call_service('AccL', request_data)
        return response.data if response.success else None


class ROSFeedback:
    """
    ROS Feedback API providing same interface as TCP Feedback
    """
    
    def __init__(self, robot_ip: str = "192.168.1.6"):
        self.robot_ip = robot_ip
        self.bridge = ROSServiceBridge(robot_ip)
        self._connected = False
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to ROS feedback services"""
        success, message = self.bridge.start_ros_services()
        self._connected = success
        return success, message
    
    def disconnect(self) -> None:
        """Disconnect from ROS feedback services"""
        self.bridge.stop_ros_services()
        self._connected = False
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected and self.bridge.is_ros_available()
    
    def get_feedback_data(self) -> Any:
        """Get feedback data (simulated for now)"""
        # In actual implementation, this would get real-time feedback from ROS
        return {
            'timestamp': time.time(),
            'pose': [0, 0, 0, 0, 0, 0],
            'angles': [0, 0, 0, 0, 0, 0],
            'status': 'OK'
        }


# Factory function
def create_ros_api(robot_ip: str = "192.168.1.6") -> Tuple[ROSDashboard, ROSFeedback]:
    """
    Factory function to create ROS API instances
    """
    dashboard = ROSDashboard(robot_ip)
    feedback = ROSFeedback(robot_ip)
    return dashboard, feedback


# Check if ROS workspace is available
def is_ros_available() -> bool:
    """Check if ROS workspace is available (lightweight check)"""
    # Quick check without creating full bridge instance
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    ros_path = os.path.join(parent_dir, 'TCP-IP-ROS-6AXis')
    
    # Check if ROS workspace exists
    if os.path.exists(ros_path):
        # Quick check for essential ROS files
        rosdemo_path = os.path.join(ros_path, 'rosdemo_v4')
        return os.path.exists(rosdemo_path)
    
    return False


# Export
__all__ = [
    'ROSServiceBridge', 'ROSDashboard', 'ROSFeedback', 
    'create_ros_api', 'is_ros_available', 'ROSServiceResponse'
]
