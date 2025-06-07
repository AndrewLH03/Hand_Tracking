#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Connection Manager

Consolidates all connection logic from robot_connection.py, tcp_api_core.py,
enhanced_ros_adapter.py, and migration_bridge.py into a single, efficient module.

This eliminates redundancy and provides a centralized connection management system
for all robot control modules.
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


class ConnectionManager:
    """
    Unified connection manager that handles all robot connectivity
    Replaces redundant connection logic from multiple files
    """
    
    def __init__(self, robot_ip: str = "192.168.1.6", 
                 connection_type: ConnectionType = ConnectionType.AUTO,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 timeout: float = 5.0):
        
        self.robot_ip = robot_ip
        self.connection_type = connection_type
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.last_error = None
        self.connection_time = None
        self.retry_count = 0
        
        # Threading
        self._lock = threading.Lock()
        self._connection_thread = None
        
        # API instances
        self.tcp_api = None
        self.ros_dashboard = None
        self.ros_feedback = None
        
        # Lazy import state
        self._tcp_api_available = None
        self._ros_api_available = None
        self._dobot_api_module = None
        
        # Initialize API availability
        self._check_api_availability()
    
    def _check_api_availability(self):
        """Check which APIs are available without importing them"""
        # Check TCP API availability
        self._tcp_api_available = self._check_tcp_api_path()
        
        # Check ROS API availability (simplified check)
        self._ros_api_available = self._check_ros_availability()
        
        logger.info(f"API Availability - TCP: {self._tcp_api_available}, ROS: {self._ros_api_available}")
    
    def _check_tcp_api_path(self) -> bool:
        """Check if TCP API path exists"""
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
                self._tcp_api_path = robot_api_path
                return True
        
        return False
    
    def _check_ros_availability(self) -> bool:
        """Check if ROS is available"""
        try:
            import rospy
            import subprocess
            result = subprocess.run(['rosnode', 'list'], capture_output=True, timeout=2)
            return result.returncode == 0
        except (ImportError, subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _lazy_import_tcp_api(self) -> bool:
        """Lazy import TCP API only when needed"""
        if self._dobot_api_module is not None:
            return True
        
        if not self._tcp_api_available:
            return False
        
        # Add to path if not already there
        if self._tcp_api_path not in sys.path:
            sys.path.insert(0, self._tcp_api_path)
        
        try:
            # Import with explicit module reloading if needed
            if 'dobot_api' in sys.modules:
                import importlib
                importlib.reload(sys.modules['dobot_api'])
            
            import dobot_api
            self._dobot_api_module = dobot_api
            logger.info(f"✅ TCP API imported successfully from: {self._tcp_api_path}")
            return True
        except Exception as e:
            logger.error(f"⚠️ Failed to import dobot_api: {e}")
            return False
    
    def _lazy_import_ros_api(self) -> bool:
        """Lazy import ROS API only when needed"""
        if not self._ros_api_available:
            return False
        
        try:
            import rospy
            from std_srvs.srv import Empty
            from std_msgs.msg import String
            logger.info("✅ ROS API imported successfully")
            return True
        except ImportError as e:
            logger.error(f"⚠️ Failed to import ROS API: {e}")
            return False
    
    def test_network_connectivity(self) -> bool:
        """Test basic network connectivity to robot"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.robot_ip, 29999))  # Standard Dobot port
            sock.close()
            return result == 0
        except Exception as e:
            logger.error(f"Network connectivity test failed: {e}")
            return False
    
    def _determine_connection_type(self) -> ConnectionType:
        """Determine which connection type to use"""
        if self.connection_type != ConnectionType.AUTO:
            return self.connection_type
        
        # Auto-detection logic
        if self._ros_api_available and self._check_ros_services():
            return ConnectionType.ROS
        elif self._tcp_api_available and self.test_network_connectivity():
            return ConnectionType.TCP
        else:
            # Default to TCP if nothing else works
            return ConnectionType.TCP
    
    def _check_ros_services(self) -> bool:
        """Check if ROS services are available"""
        try:
            import rospy
            import rosservice
            services = rosservice.get_service_list()
            dobot_services = [s for s in services if 'dobot' in s.lower()]
            return len(dobot_services) > 0
        except:
            return False
    
    def connect(self) -> bool:
        """Main connection method with retry logic"""
        with self._lock:
            if self.state == ConnectionState.CONNECTED:
                return True
            
            self.state = ConnectionState.CONNECTING
            self.retry_count = 0
            
            while self.retry_count < self.max_retries:
                try:
                    connection_type = self._determine_connection_type()
                    
                    if connection_type == ConnectionType.TCP:
                        success = self._connect_tcp()
                    elif connection_type == ConnectionType.ROS:
                        success = self._connect_ros()
                    else:
                        success = False
                    
                    if success:
                        self.state = ConnectionState.CONNECTED
                        self.connection_time = time.time()
                        logger.info(f"✅ Connected via {connection_type.value}")
                        return True
                    
                except Exception as e:
                    self.last_error = str(e)
                    logger.error(f"Connection attempt {self.retry_count + 1} failed: {e}")
                
                self.retry_count += 1
                if self.retry_count < self.max_retries:
                    time.sleep(self.retry_delay * (2 ** self.retry_count))  # Exponential backoff
            
            self.state = ConnectionState.ERROR
            return False
    
    def _connect_tcp(self) -> bool:
        """Connect using TCP API"""
        if not self._lazy_import_tcp_api():
            return False
        
        try:
            dashboard = self._dobot_api_module.DobotApiDashboard(self.robot_ip, 29999)
            feedback = self._dobot_api_module.DobotApiFeedBack(self.robot_ip, 30003)
            
            # Test connection
            if hasattr(dashboard, 'Connect') and callable(dashboard.Connect):
                dashboard.Connect()
            
            # Store API instances
            self.tcp_api = {
                'dashboard': dashboard,
                'feedback': feedback
            }
            
            return True
        except Exception as e:
            logger.error(f"TCP connection failed: {e}")
            return False
    
    def _connect_ros(self) -> bool:
        """Connect using ROS API"""
        if not self._lazy_import_ros_api():
            return False
        
        try:
            import rospy
            if not rospy.get_node_uri():
                rospy.init_node('robot_connection_manager', anonymous=True)
            
            # Test ROS connection by checking services
            if not self._check_ros_services():
                return False
            
            # Store ROS connection info
            self.ros_dashboard = True  # Placeholder
            self.ros_feedback = True   # Placeholder
            
            return True
        except Exception as e:
            logger.error(f"ROS connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from robot"""
        with self._lock:
            try:
                if self.tcp_api:
                    # Close TCP connections
                    if hasattr(self.tcp_api.get('dashboard'), 'DisConnect'):
                        self.tcp_api['dashboard'].DisConnect()
                    self.tcp_api = None
                
                if self.ros_dashboard or self.ros_feedback:
                    # Close ROS connections
                    self.ros_dashboard = None
                    self.ros_feedback = None
                
                self.state = ConnectionState.DISCONNECTED
                logger.info("✅ Disconnected from robot")
                
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
    
    def is_connected(self) -> bool:
        """Check if currently connected"""
        return self.state == ConnectionState.CONNECTED
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get current connection information"""
        return {
            'state': self.state.value,
            'robot_ip': self.robot_ip,
            'connection_type': self._determine_connection_type().value if self.is_connected() else None,
            'connected_time': self.connection_time,
            'last_error': self.last_error,
            'retry_count': self.retry_count,
            'tcp_available': self._tcp_api_available,
            'ros_available': self._ros_api_available
        }
    
    def get_dashboard_api(self):
        """Get dashboard API instance (TCP or ROS)"""
        if self.tcp_api:
            return self.tcp_api.get('dashboard')
        elif self.ros_dashboard:
            return self.ros_dashboard
        return None
    
    def get_feedback_api(self):
        """Get feedback API instance (TCP or ROS)"""
        if self.tcp_api:
            return self.tcp_api.get('feedback')
        elif self.ros_feedback:
            return self.ros_feedback
        return None
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Global connection manager instance
_global_connection_manager = None


def get_connection_manager(robot_ip: str = "192.168.1.6", 
                          connection_type: ConnectionType = ConnectionType.AUTO) -> ConnectionManager:
    """Get global connection manager instance"""
    global _global_connection_manager
    
    if _global_connection_manager is None:
        _global_connection_manager = ConnectionManager(robot_ip, connection_type)
    
    return _global_connection_manager


def reset_connection_manager():
    """Reset global connection manager"""
    global _global_connection_manager
    
    if _global_connection_manager:
        _global_connection_manager.disconnect()
        _global_connection_manager = None


# Utility functions for backward compatibility
def test_robot_connection(robot_ip: str = "192.168.1.6") -> bool:
    """Test robot connection (backward compatibility)"""
    manager = get_connection_manager(robot_ip)
    return manager.test_network_connectivity()


def create_robot_connection(robot_ip: str = "192.168.1.6", 
                           connection_type: str = "auto") -> ConnectionManager:
    """Create robot connection (backward compatibility)"""
    conn_type = ConnectionType.AUTO
    if connection_type.lower() == "tcp":
        conn_type = ConnectionType.TCP
    elif connection_type.lower() == "ros":
        conn_type = ConnectionType.ROS
    
    return ConnectionManager(robot_ip, conn_type)
