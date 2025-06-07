#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCP API Core Module - LAZY IMPORT VERSION

Extracted core TCP functionality from robot_connection.py to provide
a clean interface for the compatibility bridge during ROS migration.
This module wraps the original TCP-IP-CR-Python-V4 API with a standardized interface.

KEY FEATURE: Lazy import strategy to prevent hanging when robot is disconnected.
The dobot_api module is only imported when actual connection is attempted.
"""

import sys
import os
import time
import socket
from typing import Optional, Tuple, List, Dict, Any, Union

# Global state variables
TCP_API_AVAILABLE = None  # None = not checked, True = available, False = unavailable
DobotApiDashboard = None
DobotApiFeedBack = None
_TCP_API_PATH = None


def _check_tcp_api_availability():
    """
    Check if TCP API is available WITHOUT importing it (to prevent hanging)
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Multiple path search strategies
    robot_api_paths = [
        os.path.join(current_dir, '..', 'TCP-IP-CR-Python-V4'),
        os.path.join(os.path.dirname(current_dir), 'TCP-IP-CR-Python-V4'),
        r'c:\Users\maboy\OneDrive\Desktop\Robotic_Arm\Hand_Tracking\TCP-IP-CR-Python-V4'
    ]
    
    for robot_api_path in robot_api_paths:
        robot_api_path = os.path.abspath(robot_api_path)
        dobot_api_file = os.path.join(robot_api_path, 'dobot_api.py')
        if os.path.exists(dobot_api_file):
            return True, robot_api_path
    
    return False, None


def _lazy_import_tcp_api():
    """
    Lazy import function that imports dobot_api only when needed
    This prevents hanging during module import when robot is disconnected
    """
    global TCP_API_AVAILABLE, DobotApiDashboard, DobotApiFeedBack, _TCP_API_PATH
    
    if TCP_API_AVAILABLE is True:
        return True  # Already successfully imported
    
    if TCP_API_AVAILABLE is False:
        return False  # Previously failed, don't try again
    
    # First time check
    available, robot_api_path = _check_tcp_api_availability()
    if not available:
        print("❌ TCP API not available - dobot_api.py not found")
        TCP_API_AVAILABLE = False
        return False
    
    _TCP_API_PATH = robot_api_path
    
    # Add to path if not already there
    if robot_api_path not in sys.path:
        sys.path.insert(0, robot_api_path)
    
    try:
        # Import with explicit module reloading if needed
        if 'dobot_api' in sys.modules:
            import importlib
            importlib.reload(sys.modules['dobot_api'])
        
        import dobot_api
        DobotApiDashboard = dobot_api.DobotApiDashboard
        DobotApiFeedBack = dobot_api.DobotApiFeedBack
        TCP_API_AVAILABLE = True
        print(f"✅ TCP API imported successfully from: {robot_api_path}")
        return True
    except Exception as e:
        print(f"⚠️ Failed to import dobot_api: {e}")
        TCP_API_AVAILABLE = False
        return False


# Dummy classes for when TCP API is not available
class DummyDobotApiDashboard:
    def __init__(self, ip: str, port: int = 29999):
        self.ip = ip
        self.port = port
        self.connected = False
        self.socket_dobot = 0
    
    def EnableRobot(self) -> str:
        return "DummyTCP:EnableRobot"
    
    def DisableRobot(self) -> str:
        return "DummyTCP:DisableRobot"
    
    def ClearError(self) -> str:
        return "DummyTCP:ClearError"
    
    def RobotMode(self) -> str:
        return "DummyTCP:RobotMode"
    
    def MovJ(self, x: float, y: float, z: float, rx: float, ry: float, rz: float) -> str:
        return f"DummyTCP:MovJ({x},{y},{z},{rx},{ry},{rz})"
    
    def MovL(self, x: float, y: float, z: float, rx: float, ry: float, rz: float) -> str:
        return f"DummyTCP:MovL({x},{y},{z},{rx},{ry},{rz})"
    
    def GetPose(self) -> str:
        return "DummyTCP:GetPose"
    
    def close(self):
        pass


class DummyDobotApiFeedBack:
    def __init__(self, ip: str, port: int = 30004):
        self.ip = ip
        self.port = port
        self.connected = False
        self.socket_dobot = 0
    
    def GetRobotMode(self) -> str:
        return "DummyTCP:GetRobotMode"
    
    def close(self):
        pass


class TCPDashboard:
    """
    Wrapper for TCP Dashboard API providing standardized interface
    Uses lazy import to prevent hanging during module load
    """
    
    def __init__(self, robot_ip: str = "192.168.1.6", port: int = 29999):
        self.robot_ip = robot_ip
        self.port = port
        self._dashboard = None
        self._connected = False
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to robot dashboard with lazy import"""
        # Try to import TCP API only when connection is needed
        if not _lazy_import_tcp_api():
            return False, "TCP API not available"
        
        try:
            # Use real or dummy class based on availability
            dashboard_class = DobotApiDashboard if TCP_API_AVAILABLE else DummyDobotApiDashboard
            self._dashboard = dashboard_class(self.robot_ip, self.port)
            
            # For dummy class, mark as connected
            if not TCP_API_AVAILABLE:
                self._connected = True
                return True, "TCP Dashboard connected (dummy mode)"
            
            # For real class, test connection with timeout
            try:
                # Quick network test first
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)  # 2 second timeout
                result = sock.connect_ex((self.robot_ip, self.port))
                sock.close()
                
                if result == 0:
                    self._connected = True
                    return True, "TCP Dashboard connected successfully"
                else:
                    return False, f"Robot not reachable at {self.robot_ip}:{self.port}"
            except Exception as e:
                return False, f"Connection test failed: {e}"
                
        except Exception as e:
            return False, f"TCP connection failed: {e}"
    
    def disconnect(self) -> None:
        """Disconnect from robot dashboard"""
        if self._dashboard:
            try:
                if hasattr(self._dashboard, 'disconnect'):
                    self._dashboard.disconnect()
                elif hasattr(self._dashboard, 'close'):
                    self._dashboard.close()
            except Exception:
                pass
            finally:
                self._dashboard = None
                self._connected = False
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected and self._dashboard is not None
    
    # Core Dashboard Commands
    def enable_robot(self) -> Any:
        """Enable robot"""
        if not self._dashboard:
            raise RuntimeError("Not connected")
        return self._dashboard.EnableRobot()
    
    def disable_robot(self) -> Any:
        """Disable robot"""
        if not self._dashboard:
            raise RuntimeError("Not connected")
        return self._dashboard.DisableRobot()
    
    def clear_error(self) -> Any:
        """Clear robot errors"""
        if not self._dashboard:
            raise RuntimeError("Not connected")
        return self._dashboard.ClearError()
    
    def robot_mode(self) -> Any:
        """Get robot mode"""
        if not self._dashboard:
            raise RuntimeError("Not connected")
        return self._dashboard.RobotMode()


class TCPFeedback:
    """
    Wrapper for TCP Feedback API providing standardized interface
    Uses lazy import to prevent hanging during module load
    """
    
    def __init__(self, robot_ip: str = "192.168.1.6", port: int = 30004):
        self.robot_ip = robot_ip
        self.port = port
        self._feedback = None
        self._connected = False
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to robot feedback with lazy import"""
        # Try to import TCP API only when connection is needed
        if not _lazy_import_tcp_api():
            return False, "TCP API not available"
        
        try:
            # Use real or dummy class based on availability
            feedback_class = DobotApiFeedBack if TCP_API_AVAILABLE else DummyDobotApiFeedBack
            self._feedback = feedback_class(self.robot_ip, self.port)
            
            self._connected = True
            if TCP_API_AVAILABLE:
                return True, "TCP Feedback connected successfully"
            else:
                return True, "TCP Feedback connected (dummy mode)"
        except Exception as e:
            return False, f"TCP feedback connection failed: {e}"
    
    def disconnect(self) -> None:
        """Disconnect from robot feedback"""
        if self._feedback:
            try:
                if hasattr(self._feedback, 'close'):
                    self._feedback.close()
            except Exception:
                pass
            finally:
                self._feedback = None
                self._connected = False
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected and self._feedback is not None


class TCPApiCore:
    """
    Core TCP API wrapper providing unified interface for robot control
    Uses lazy import strategy to prevent hanging during module load
    """
    
    def __init__(self, robot_ip: str = "192.168.1.6", 
                 dashboard_port: int = 29999, 
                 feedback_port: int = 30004):
        self.robot_ip = robot_ip
        self.dashboard_port = dashboard_port
        self.feedback_port = feedback_port
        
        self.dashboard = TCPDashboard(robot_ip, dashboard_port)
        self.feedback = TCPFeedback(robot_ip, feedback_port)
        
        self._connected = False
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to robot (dashboard and feedback)"""
        dashboard_success, dashboard_msg = self.dashboard.connect()
        if not dashboard_success:
            return False, f"Dashboard connection failed: {dashboard_msg}"
        
        feedback_success, feedback_msg = self.feedback.connect()
        if not feedback_success:
            # Dashboard connected but feedback failed - continue with warning
            print(f"Warning: Feedback connection failed: {feedback_msg}")
        
        self._connected = dashboard_success
        return True, "TCP API connected successfully"
    
    def disconnect(self) -> None:
        """Disconnect from robot"""
        self.dashboard.disconnect()
        self.feedback.disconnect()
        self._connected = False
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected and self.dashboard.is_connected()
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test basic connectivity without importing heavy libraries"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)  # Short timeout to prevent hanging
            result = sock.connect_ex((self.robot_ip, self.dashboard_port))
            sock.close()
            
            if result == 0:
                return True, f"TCP connection test successful to {self.robot_ip}:{self.dashboard_port}"
            else:
                return False, f"Cannot reach {self.robot_ip}:{self.dashboard_port}"
        except Exception as e:
            return False, f"TCP connection test failed: {e}"


# Factory function for backward compatibility
def create_tcp_api(robot_ip: str = "192.168.1.6", 
                   dashboard_port: int = 29999, 
                   feedback_port: int = 30004) -> TCPApiCore:
    """
    Factory function to create TCP API instance
    """
    return TCPApiCore(robot_ip, dashboard_port, feedback_port)


# Check availability on module load (safe - no imports)
available, path = _check_tcp_api_availability()
if available:
    print(f"✅ TCP API available at: {path}")
else:
    print("⚠️ TCP API not found - will use dummy mode")


# Export availability status
__all__ = [
    'TCPDashboard', 'TCPFeedback', 'TCPApiCore', 
    'create_tcp_api', 'TCP_API_AVAILABLE'
]