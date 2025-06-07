#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core Robot API Module

Consolidated connection management and API access for all robot control functionality.
Combines logic from connection_manager.py, robot_connection.py, and tcp_api_core.py
to eliminate redundancy while providing unified interface.

Features:
- Unified TCP connection management
- Lazy import strategy for robot API
- Automatic connection retry and error handling
- Network connectivity testing
- Robot status monitoring and alarm management
"""

import sys
import os
import time
import socket
import threading
import subprocess
from typing import Optional, Tuple, List, Dict, Any, Union
from enum import Enum
import logging

# Configure logging
logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """Available connection types"""
    TCP = "tcp"
    ROS = "ros"
    AUTO = "auto"


class ConnectionState(Enum):
    """Connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RETRY = "retry"


# Global state for lazy import
_TCP_API_AVAILABLE = None
_DOBOT_API_MODULE = None
_TCP_API_PATH = None


def _find_robot_api_path():
    """Find the robot API path using multiple search strategies"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    search_paths = [
        os.path.join(current_dir, '..', 'TCP-IP-CR-Python-V4'),
        os.path.join(os.path.dirname(current_dir), 'TCP-IP-CR-Python-V4'),
        r'c:\Users\maboy\OneDrive\Desktop\Robotic_Arm\Hand_Tracking\TCP-IP-CR-Python-V4'
    ]
    
    for path in search_paths:
        abs_path = os.path.abspath(path)
        dobot_api_file = os.path.join(abs_path, 'dobot_api.py')
        if os.path.exists(dobot_api_file):
            return True, abs_path
    
    return False, None


def _lazy_import_robot_api():
    """Lazy import robot API only when needed to prevent hanging"""
    global _TCP_API_AVAILABLE, _DOBOT_API_MODULE, _TCP_API_PATH
    
    if _TCP_API_AVAILABLE is not None:
        return _TCP_API_AVAILABLE, _DOBOT_API_MODULE
    
    try:
        # Find API path
        found, api_path = _find_robot_api_path()
        if not found:
            logger.error("Robot API path not found")
            _TCP_API_AVAILABLE = False
            return False, None
        
        _TCP_API_PATH = api_path
        
        # Add to Python path if not already there
        if api_path not in sys.path:
            sys.path.insert(0, api_path)
        
        # Import the module
        import dobot_api
        _DOBOT_API_MODULE = dobot_api
        _TCP_API_AVAILABLE = True
        
        logger.info(f"✅ Robot API loaded successfully from: {api_path}")
        return True, dobot_api
        
    except ImportError as e:
        logger.error(f"❌ Failed to import robot API: {e}")
        _TCP_API_AVAILABLE = False
        _DOBOT_API_MODULE = None
        return False, None


class DummyRobotApi:
    """Dummy API for testing when robot is not available"""
    
    def __init__(self, *args, **kwargs):
        self.connected = False
        
    def Connect(self):
        return True, "Dummy connection successful"
        
    def Disconnect(self):
        return True, "Dummy disconnect successful"
        
    def ClearError(self):
        return "0,{},ClearError()"
        
    def RobotMode(self):
        return "0,0,5,RobotMode()"  # Mode 5 = idle
        
    def EnableRobot(self):
        return "0,{},EnableRobot()"
        
    def GetPose(self):
        return "0,200.0,0.0,200.0,0.0,0.0,0.0,GetPose()"


class CoreRobotAPI:
    """
    Core robot API class that provides unified access to robot functionality
    Consolidates connection management from multiple modules
    """
    
    def __init__(self, robot_ip: str = "192.168.1.6", 
                 connection_type: ConnectionType = ConnectionType.AUTO,
                 max_retries: int = 3,
                 retry_delay: float = 2.0,
                 timeout: float = 5.0):
        
        self.robot_ip = robot_ip
        self.connection_type = connection_type
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        self.dashboard_port = 29999
        self.feedback_port = 30004
        
        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.dashboard = None
        self.feedback = None
        self._lock = threading.Lock()
        
        # API availability
        self.api_available = False
        self.api_module = None
        
        # Connection statistics
        self.connection_attempts = 0
        self.last_error = None
        
    def initialize(self) -> Tuple[bool, str]:
        """Initialize the robot API and check availability"""
        try:
            # Try to import robot API
            self.api_available, self.api_module = _lazy_import_robot_api()
            
            if not self.api_available:
                logger.warning("Robot API not available, using dummy mode")
                return False, "Robot API not available - check TCP-IP-CR-Python-V4 installation"
            
            return True, "Robot API initialized successfully"
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to initialize robot API: {e}")
            return False, f"Initialization failed: {e}"
    
    def test_network_connectivity(self) -> Tuple[bool, str]:
        """Test basic network connectivity to robot"""
        try:
            # Test socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.robot_ip, self.dashboard_port))
            sock.close()
            
            if result == 0:
                return True, f"Network connectivity to {self.robot_ip}:{self.dashboard_port} successful"
            else:
                return False, f"Cannot reach {self.robot_ip}:{self.dashboard_port} - check network connection"
                
        except Exception as e:
            return False, f"Network test failed: {e}"
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to robot with retry logic"""
        with self._lock:
            if self.state == ConnectionState.CONNECTED:
                return True, "Already connected"
            
            self.state = ConnectionState.CONNECTING
            
            for attempt in range(self.max_retries):
                self.connection_attempts += 1
                
                try:
                    # Test network first
                    network_ok, network_msg = self.test_network_connectivity()
                    if not network_ok:
                        self.last_error = network_msg
                        continue
                    
                    # Initialize API if not done
                    if not self.api_available:
                        api_ok, api_msg = self.initialize()
                        if not api_ok:
                            self.last_error = api_msg
                            break
                    
                    # Create dashboard connection
                    if self.api_available:
                        self.dashboard = self.api_module.DobotApiDashboard(self.robot_ip, self.dashboard_port)
                        self.feedback = self.api_module.DobotApiFeedBack(self.robot_ip, self.feedback_port)
                    else:
                        self.dashboard = DummyRobotApi(self.robot_ip, self.dashboard_port)
                        self.feedback = DummyRobotApi(self.robot_ip, self.feedback_port)
                    
                    # Test connection
                    connect_result = self.dashboard.Connect()
                    if connect_result[0] if isinstance(connect_result, tuple) else True:
                        self.state = ConnectionState.CONNECTED
                        logger.info(f"✅ Connected to robot at {self.robot_ip}")
                        return True, f"Connected successfully (attempt {attempt + 1})"
                    
                except Exception as e:
                    self.last_error = str(e)
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
            
            self.state = ConnectionState.ERROR
            return False, f"Failed to connect after {self.max_retries} attempts. Last error: {self.last_error}"
    
    def disconnect(self) -> Tuple[bool, str]:
        """Disconnect from robot safely"""
        with self._lock:
            try:
                if self.dashboard and hasattr(self.dashboard, 'Disconnect'):
                    self.dashboard.Disconnect()
                
                if self.feedback and hasattr(self.feedback, 'Disconnect'):
                    self.feedback.Disconnect()
                
                self.dashboard = None
                self.feedback = None
                self.state = ConnectionState.DISCONNECTED
                
                logger.info("✅ Disconnected from robot")
                return True, "Disconnected successfully"
                
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
                return False, f"Disconnect error: {e}"
    
    def is_connected(self) -> bool:
        """Check if robot is connected"""
        return self.state == ConnectionState.CONNECTED and self.dashboard is not None
    
    def check_robot_alarms(self) -> Tuple[bool, List[str]]:
        """Check for robot alarms and errors"""
        if not self.is_connected():
            return False, ["Not connected to robot"]
        
        try:
            # Get alarm status
            alarm_response = self.dashboard.GetErrorID()
            if not alarm_response:
                return False, ["Failed to get alarm status"]
            
            # Parse alarm response
            from .utilities import parse_api_response
            error_numbers = parse_api_response(alarm_response, "numbers")
            
            if not error_numbers or (len(error_numbers) == 1 and error_numbers[0] == 0):
                return True, []  # No alarms
            
            # Convert error numbers to descriptions
            error_descriptions = [f"Error {int(num)}" for num in error_numbers if num != 0]
            return False, error_descriptions
            
        except Exception as e:
            return False, [f"Alarm check failed: {e}"]
    
    def clear_robot_alarms(self) -> Tuple[bool, str]:
        """Clear robot alarms"""
        if not self.is_connected():
            return False, "Not connected to robot"
        
        try:
            result = self.dashboard.ClearError()
            return True, "Alarms cleared successfully"
            
        except Exception as e:
            return False, f"Failed to clear alarms: {e}"
    
    def enable_robot(self) -> Tuple[bool, str]:
        """Enable robot for operation"""
        if not self.is_connected():
            return False, "Not connected to robot"
        
        try:
            # Clear any existing alarms first
            self.dashboard.ClearError()
            time.sleep(0.5)
            
            # Enable robot
            result = self.dashboard.EnableRobot()
            time.sleep(1.0)  # Wait for enable to complete
            
            # Verify robot mode
            mode_response = self.dashboard.RobotMode()
            from .utilities import parse_api_response
            actual_mode = parse_api_response(mode_response, "first_number")
            
            if actual_mode == 5:  # Mode 5 = enabled and idle
                return True, "Robot enabled successfully"
            else:
                return False, f"Robot not in correct mode (current: {actual_mode}, expected: 5)"
                
        except Exception as e:
            return False, f"Failed to enable robot: {e}"
    
    def get_robot_status(self) -> Dict[str, Any]:
        """Get comprehensive robot status"""
        status = {
            'connected': self.is_connected(),
            'state': self.state.value,
            'api_available': self.api_available,
            'connection_attempts': self.connection_attempts,
            'last_error': self.last_error,
            'robot_ip': self.robot_ip
        }
        
        if self.is_connected():
            try:
                # Get robot mode
                mode_response = self.dashboard.RobotMode()
                from .utilities import parse_api_response
                status['robot_mode'] = parse_api_response(mode_response, "first_number")
                
                # Get current position
                pos_response = self.dashboard.GetPose()
                status['current_position'] = parse_api_response(pos_response, "numbers")
                
                # Check alarms
                alarm_ok, alarms = self.check_robot_alarms()
                status['alarms'] = alarms
                status['alarm_free'] = alarm_ok
                
            except Exception as e:
                status['status_error'] = str(e)
        
        return status


# Factory function for easy instantiation
def create_robot_api(robot_ip: str = "192.168.1.6", **kwargs) -> CoreRobotAPI:
    """Create and initialize a robot API instance"""
    api = CoreRobotAPI(robot_ip, **kwargs)
    return api


# Global instance for shared access
_global_robot_api = None


def get_robot_api(robot_ip: str = "192.168.1.6") -> CoreRobotAPI:
    """Get or create global robot API instance"""
    global _global_robot_api
    
    if _global_robot_api is None or _global_robot_api.robot_ip != robot_ip:
        _global_robot_api = create_robot_api(robot_ip)
    
    return _global_robot_api
