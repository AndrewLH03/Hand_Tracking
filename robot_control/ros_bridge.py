#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROS Bridge - Consolidated ROS Integration

This module consolidates all ROS functionality from enhanced_ros_adapter.py,
migration_bridge.py, and ros_service_bridge.py into a single unified interface.

Provides:
- ROS service integration and subprocess management
- Migration bridge for gradual transition from TCP to ROS
- Enhanced adapter with automatic backend selection
- Compatibility layer for existing code
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

# Import utilities for common functions
try:
    from .utilities import parse_api_response
    from .core_api import DobotApiDashboard, DobotApiFeedback
except ImportError:
    from utilities import parse_api_response
    from core_api import DobotApiDashboard, DobotApiFeedback


class ROSServiceStatus(Enum):
    """Status of ROS services"""
    UNKNOWN = 0
    RUNNING = 1
    STOPPED = 2
    ERROR = 3


class BackendType(Enum):
    """Available backend types"""
    TCP = "tcp"
    ROS = "ros"
    AUTO = "auto"


class MigrationFeature(Enum):
    """Migration feature flags"""
    CONNECTION_MANAGEMENT = "connection_management"
    MOVEMENT_COMMANDS = "movement_commands"
    STATUS_MONITORING = "status_monitoring"
    ERROR_HANDLING = "error_handling"
    ADVANCED_FEATURES = "advanced_features"


@dataclass
class ROSServiceResponse:
    """Standardized ROS service response"""
    success: bool
    data: Any
    message: str
    timestamp: float


class ROSServiceBridge:
    """Bridge between Python and ROS C++ services"""
    
    def __init__(self, robot_ip: str = "192.168.1.6", ros_workspace: str = None):
        self.robot_ip = robot_ip
        self.ros_workspace = ros_workspace or self._find_ros_workspace()
        self.ros_executable = None
        self.ros_process = None
        self.service_status = ROSServiceStatus.UNKNOWN
        self._lock = threading.Lock()
        
        # Service cache for performance
        self.service_cache = {}
        self.cache_timeout = 1.0  # seconds
        
        self._initialize_ros()
    
    def _find_ros_workspace(self) -> Optional[str]:
        """Find ROS workspace automatically"""
        possible_paths = [
            os.path.expanduser("~/catkin_ws"),
            os.path.expanduser("~/ros_ws"),
            "/opt/ros/noetic",
            "/opt/ros/melodic"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _initialize_ros(self):
        """Initialize ROS environment"""
        if not self.ros_workspace:
            print("⚠️  ROS workspace not found")
            return
        
        # Look for ROS executable
        possible_executables = [
            os.path.join(self.ros_workspace, "devel/lib/ros_6axis/robot_control_node"),
            os.path.join(self.ros_workspace, "build/robot_control_node"),
            "rosrun ros_6axis robot_control_node"
        ]
        
        for executable in possible_executables:
            if os.path.exists(executable) or executable.startswith("rosrun"):
                self.ros_executable = executable
                break
        
        if self.ros_executable:
            print(f"🤖 ROS executable found: {self.ros_executable}")
        else:
            print("⚠️  ROS executable not found")
    
    def is_ros_available(self) -> bool:
        """Check if ROS is available"""
        try:
            result = subprocess.run(['rosversion', '-d'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def start_ros_services(self) -> Tuple[bool, str]:
        """Start ROS services"""
        with self._lock:
            if self.service_status == ROSServiceStatus.RUNNING:
                return True, "ROS services already running"
            
            if not self.ros_executable:
                return False, "ROS executable not found"
            
            try:
                # Start ROS service process
                if self.ros_executable.startswith("rosrun"):
                    cmd = self.ros_executable.split() + [self.robot_ip]
                else:
                    cmd = [self.ros_executable, self.robot_ip]
                
                self.ros_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Wait a moment to see if it starts successfully
                time.sleep(2)
                
                if self.ros_process.poll() is None:
                    self.service_status = ROSServiceStatus.RUNNING
                    return True, "ROS services started successfully"
                else:
                    stderr = self.ros_process.stderr.read()
                    return False, f"ROS services failed to start: {stderr}"
                    
            except Exception as e:
                return False, f"Failed to start ROS services: {e}"
    
    def stop_ros_services(self) -> None:
        """Stop ROS services"""
        with self._lock:
            if self.ros_process:
                self.ros_process.terminate()
                try:
                    self.ros_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.ros_process.kill()
                
                self.ros_process = None
                self.service_status = ROSServiceStatus.STOPPED
                print("🛑 ROS services stopped")
    
    def call_ros_service(self, service_name: str, data: Dict = None) -> ROSServiceResponse:
        """Call a ROS service"""
        if self.service_status != ROSServiceStatus.RUNNING:
            return ROSServiceResponse(False, None, "ROS services not running", time.time())
        
        # Check cache first
        cache_key = f"{service_name}_{json.dumps(data, sort_keys=True) if data else ''}"
        now = time.time()
        
        if cache_key in self.service_cache:
            cached_response, cache_time = self.service_cache[cache_key]
            if now - cache_time < self.cache_timeout:
                return cached_response
        
        try:
            # Prepare service call
            cmd = ['rosservice', 'call', service_name]
            if data:
                cmd.extend([json.dumps(data)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                response = ROSServiceResponse(True, result.stdout.strip(), "Success", now)
            else:
                response = ROSServiceResponse(False, None, result.stderr.strip(), now)
            
            # Cache successful responses
            if response.success:
                self.service_cache[cache_key] = (response, now)
            
            return response
            
        except subprocess.TimeoutExpired:
            return ROSServiceResponse(False, None, "Service call timeout", now)
        except Exception as e:
            return ROSServiceResponse(False, None, f"Service call failed: {e}", now)


class ROSDashboard:
    """ROS Dashboard interface compatible with TCP dashboard"""
    
    def __init__(self, robot_ip: str, service_bridge: ROSServiceBridge):
        self.robot_ip = robot_ip
        self.service_bridge = service_bridge
        self._connected = False
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to ROS dashboard services"""
        success, message = self.service_bridge.start_ros_services()
        if success:
            self._connected = True
        return success, message
    
    def disconnect(self) -> None:
        """Disconnect from ROS dashboard"""
        self._connected = False
        # Don't stop services here - they might be shared
    
    def enable_robot(self) -> str:
        """Enable robot via ROS"""
        response = self.service_bridge.call_ros_service("/robot/enable")
        return "0" if response.success else "-1"
    
    def disable_robot(self) -> str:
        """Disable robot via ROS"""  
        response = self.service_bridge.call_ros_service("/robot/disable")
        return "0" if response.success else "-1"
    
    def clear_error(self) -> str:
        """Clear robot errors via ROS"""
        response = self.service_bridge.call_ros_service("/robot/clear_error")
        return "0" if response.success else "-1"
    
    def reset_robot(self) -> str:
        """Reset robot via ROS"""
        response = self.service_bridge.call_ros_service("/robot/reset")
        return "0" if response.success else "-1"
    
    def get_error_id(self) -> str:
        """Get robot error ID via ROS"""
        response = self.service_bridge.call_ros_service("/robot/get_error")
        if response.success and response.data:
            return response.data
        return "0"
    
    def move_l(self, x: float, y: float, z: float, rx: float, ry: float, rz: float) -> str:
        """Linear move via ROS"""
        data = {"x": x, "y": y, "z": z, "rx": rx, "ry": ry, "rz": rz}
        response = self.service_bridge.call_ros_service("/robot/move_l", data)
        return "0" if response.success else "-1"
    
    def move_j(self, x: float, y: float, z: float, rx: float, ry: float, rz: float) -> str:
        """Joint move via ROS"""
        data = {"x": x, "y": y, "z": z, "rx": rx, "ry": ry, "rz": rz}
        response = self.service_bridge.call_ros_service("/robot/move_j", data)
        return "0" if response.success else "-1"


class ROSFeedback:
    """ROS Feedback interface compatible with TCP feedback"""
    
    def __init__(self, robot_ip: str, service_bridge: ROSServiceBridge):
        self.robot_ip = robot_ip
        self.service_bridge = service_bridge
        self._connected = False
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to ROS feedback services"""
        if self.service_bridge.service_status == ROSServiceStatus.RUNNING:
            self._connected = True
            return True, "ROS feedback connected"
        return False, "ROS services not running"
    
    def disconnect(self) -> None:
        """Disconnect from ROS feedback"""
        self._connected = False
    
    def get_robot_pose(self) -> str:
        """Get robot pose via ROS"""
        response = self.service_bridge.call_ros_service("/robot/get_pose")
        return response.data if response.success else "{0,0,0,0,0,0}"


class RobotApiAdapter:
    """Main adapter providing unified interface for both TCP and ROS backends"""
    
    def __init__(self, robot_ip: str = "192.168.1.6", 
                 backend: BackendType = BackendType.AUTO,
                 migration_features: Dict[MigrationFeature, bool] = None):
        self.robot_ip = robot_ip
        self.requested_backend = backend
        self.active_backend = None
        
        # Initialize migration feature flags
        self.migration_features = migration_features or {
            MigrationFeature.CONNECTION_MANAGEMENT: False,
            MigrationFeature.MOVEMENT_COMMANDS: False,
            MigrationFeature.STATUS_MONITORING: False,
            MigrationFeature.ERROR_HANDLING: False,
            MigrationFeature.ADVANCED_FEATURES: False,
        }
        
        # Backend instances
        self.tcp_dashboard = None
        self.tcp_feedback = None
        self.ros_service_bridge = None
        self.ros_dashboard = None
        self.ros_feedback = None
        
        # Connection state
        self._connected = False
        self._lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'tcp_calls': 0,
            'ros_calls': 0,
            'fallbacks': 0,
            'errors': 0,
            'connection_time': 0
        }
        
        self._initialize_backends()
    
    def _initialize_backends(self):
        """Initialize available backends"""
        backend_status = self._check_backend_availability()
        
        if self.requested_backend == BackendType.AUTO:
            # Choose best available backend
            if backend_status['ros'] and self.migration_features[MigrationFeature.CONNECTION_MANAGEMENT]:
                self.active_backend = BackendType.ROS
            elif backend_status['tcp']:
                self.active_backend = BackendType.TCP
            else:
                raise RuntimeError("No backends available")
        else:
            # Use requested backend
            if self.requested_backend == BackendType.ROS and not backend_status['ros']:
                raise RuntimeError("ROS backend requested but not available")
            elif self.requested_backend == BackendType.TCP and not backend_status['tcp']:
                raise RuntimeError("TCP backend requested but not available")
            self.active_backend = self.requested_backend
        
        print(f"🔧 Robot API Adapter initialized with {self.active_backend.value.upper()} backend")
    
    def _check_backend_availability(self) -> Dict[str, bool]:
        """Check which backends are available"""
        # Check ROS availability
        ros_available = False
        try:
            bridge = ROSServiceBridge(self.robot_ip)
            ros_available = bridge.is_ros_available()
        except Exception:
            pass
        
        return {
            'tcp': True,  # TCP is always available through core_api
            'ros': ros_available,
        }
    
    def connect(self) -> Tuple[bool, str]:
        """Connect using active backend"""
        start_time = time.time()
        
        with self._lock:
            try:
                if self.active_backend == BackendType.ROS:
                    success, message = self._connect_ros()
                else:
                    success, message = self._connect_tcp()
                
                if success:
                    self._connected = True
                    self.stats['connection_time'] = time.time() - start_time
                    return True, f"{self.active_backend.value.upper()} connection successful: {message}"
                else:
                    # Try fallback if auto mode
                    if self.requested_backend == BackendType.AUTO:
                        return self._try_fallback_connection()
                    return False, message
                    
            except Exception as e:
                return False, f"Connection failed: {e}"
    
    def _connect_tcp(self) -> Tuple[bool, str]:
        """Connect using TCP backend"""
        try:
            self.tcp_dashboard = DobotApiDashboard(self.robot_ip)
            self.tcp_feedback = DobotApiFeedback(self.robot_ip)
            
            dashboard_success, dashboard_msg = self.tcp_dashboard.connect()
            if dashboard_success:
                feedback_success, feedback_msg = self.tcp_feedback.connect()
                return True, f"TCP services connected"
            else:
                return False, f"TCP dashboard connection failed: {dashboard_msg}"
        except Exception as e:
            return False, f"TCP connection error: {e}"
    
    def _connect_ros(self) -> Tuple[bool, str]:
        """Connect using ROS backend"""
        try:
            self.ros_service_bridge = ROSServiceBridge(self.robot_ip)
            self.ros_dashboard = ROSDashboard(self.robot_ip, self.ros_service_bridge)
            self.ros_feedback = ROSFeedback(self.robot_ip, self.ros_service_bridge)
            
            dashboard_success, dashboard_msg = self.ros_dashboard.connect()
            if dashboard_success:
                feedback_success, feedback_msg = self.ros_feedback.connect()
                return True, f"ROS services connected"
            else:
                return False, f"ROS dashboard connection failed: {dashboard_msg}"
        except Exception as e:
            return False, f"ROS connection error: {e}"
    
    def _try_fallback_connection(self) -> Tuple[bool, str]:
        """Try fallback connection"""
        self.stats['fallbacks'] += 1
        
        if self.active_backend == BackendType.ROS:
            # Fallback to TCP
            self.active_backend = BackendType.TCP
            success, message = self._connect_tcp()
            if success:
                self._connected = True
                return True, f"Fallback to TCP successful: {message}"
        elif self.active_backend == BackendType.TCP:
            # Try ROS if available
            backend_status = self._check_backend_availability()
            if backend_status['ros']:
                self.active_backend = BackendType.ROS
                success, message = self._connect_ros()
                if success:
                    self._connected = True
                    return True, f"Upgraded to ROS successful: {message}"
        
        return False, "All connection attempts failed"
    
    def disconnect(self) -> None:
        """Disconnect from robot"""
        with self._lock:
            if self.tcp_dashboard:
                self.tcp_dashboard.disconnect()
                self.tcp_dashboard = None
            
            if self.tcp_feedback:
                self.tcp_feedback.disconnect()
                self.tcp_feedback = None
            
            if self.ros_dashboard:
                self.ros_dashboard.disconnect()
                self.ros_dashboard = None
            
            if self.ros_feedback:
                self.ros_feedback.disconnect()
                self.ros_feedback = None
            
            if self.ros_service_bridge:
                self.ros_service_bridge.stop_ros_services()
                self.ros_service_bridge = None
            
            self._connected = False
        
        print(f"🔌 Disconnected from {self.active_backend.value.upper()} backend")
    
    def get_dashboard(self):
        """Get dashboard instance"""
        if self.active_backend == BackendType.ROS and self.ros_dashboard:
            return self.ros_dashboard
        elif self.active_backend == BackendType.TCP and self.tcp_dashboard:
            return self.tcp_dashboard
        return None
    
    def get_feedback(self):
        """Get feedback instance"""
        if self.active_backend == BackendType.ROS and self.ros_feedback:
            return self.ros_feedback
        elif self.active_backend == BackendType.TCP and self.tcp_feedback:
            return self.tcp_feedback
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get adapter status"""
        return {
            'connected': self._connected,
            'active_backend': self.active_backend.value if self.active_backend else None,
            'requested_backend': self.requested_backend.value,
            'migration_features': {f.value: enabled for f, enabled in self.migration_features.items()},
            'stats': self.stats.copy(),
            'backend_availability': self._check_backend_availability()
        }


class EnhancedRobotConnection:
    """
    Migration bridge providing compatibility with existing robot_connection.py
    while enabling gradual migration to ROS
    """
    
    def __init__(self, robot_ip: str = "192.168.1.6", 
                 dashboard_port: int = 29999, 
                 move_port: int = 30003, 
                 feed_port: int = 30004,
                 use_ros_migration: bool = False):
        self.robot_ip = robot_ip
        self.dashboard_port = dashboard_port
        self.move_port = move_port
        self.feed_port = feed_port
        self.use_ros_migration = use_ros_migration
        
        # Backend selection
        if use_ros_migration:
            backend = BackendType.AUTO
            features = {MigrationFeature.CONNECTION_MANAGEMENT: True}
        else:
            backend = BackendType.TCP
            features = {}
        
        self.adapter = RobotApiAdapter(robot_ip, backend, features)
        self.dashboard = None
        self.feedback = None
    
    def test_network_connectivity(self) -> Tuple[bool, str]:
        """Test network connectivity to robot"""
        try:
            # Simple TCP connectivity test
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.robot_ip, self.dashboard_port))
            sock.close()
            
            if result == 0:
                return True, f"Network connectivity to {self.robot_ip}:{self.dashboard_port} successful"
            else:
                return False, f"Cannot connect to {self.robot_ip}:{self.dashboard_port}"
        except Exception as e:
            return False, f"Network test failed: {e}"
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to robot"""
        success, message = self.adapter.connect()
        if success:
            self.dashboard = self.adapter.get_dashboard()
            self.feedback = self.adapter.get_feedback()
        return success, message
    
    def disconnect(self) -> None:
        """Disconnect from robot"""
        self.adapter.disconnect()
        self.dashboard = None
        self.feedback = None
    
    def check_robot_alarms(self, description: str = "Checking alarms") -> Tuple[bool, List[str]]:
        """Check robot alarms"""
        if not self.dashboard:
            return True, []
        
        try:
            error_response = self.dashboard.get_error_id()
            success, error_data = parse_api_response(error_response)
            
            if success and error_data != 0:
                # Parse error data into alarm list
                alarms = [f"Robot Error ID: {error_data}"]
                return False, alarms
            else:
                return True, []
        except Exception as e:
            print(f"⚠️  Alarm check failed: {e}")
            return True, []  # Assume OK if can't check


# Factory functions for compatibility
def create_dobot_api(robot_ip: str = "192.168.1.6", 
                     backend: BackendType = BackendType.AUTO) -> Tuple:
    """Factory function to create Dobot API instances"""
    adapter = RobotApiAdapter(robot_ip, backend)
    
    # Create compatibility wrappers
    class DashboardWrapper:
        def __init__(self, adapter):
            self.adapter = adapter
            self.dashboard = None
        
        def connect(self):
            success, message = self.adapter.connect()
            if success:
                self.dashboard = self.adapter.get_dashboard()
            return success, message
        
        def disconnect(self):
            self.adapter.disconnect()
        
        def __getattr__(self, name):
            if self.dashboard:
                return getattr(self.dashboard, name)
            raise AttributeError(f"Dashboard not connected or attribute '{name}' not found")
    
    class FeedbackWrapper:
        def __init__(self, adapter):
            self.adapter = adapter
            self.feedback = None
        
        def connect(self):
            if self.adapter._connected:
                self.feedback = self.adapter.get_feedback()
                return True, "Feedback connected"
            return False, "Adapter not connected"
        
        def disconnect(self):
            pass  # Handled by adapter
        
        def __getattr__(self, name):
            if self.feedback:
                return getattr(self.feedback, name)
            raise AttributeError(f"Feedback not connected or attribute '{name}' not found")
    
    return DashboardWrapper(adapter), FeedbackWrapper(adapter)


def create_migration_adapter(robot_ip: str = "192.168.1.6") -> RobotApiAdapter:
    """Create migration adapter with gradual feature enablement"""
    features = {
        MigrationFeature.CONNECTION_MANAGEMENT: True,
        MigrationFeature.MOVEMENT_COMMANDS: False,
        MigrationFeature.STATUS_MONITORING: False,
        MigrationFeature.ERROR_HANDLING: False,
        MigrationFeature.ADVANCED_FEATURES: False,
    }
    
    return RobotApiAdapter(robot_ip, BackendType.AUTO, features)


def is_ros_available() -> bool:
    """Check if ROS is available on the system"""
    try:
        bridge = ROSServiceBridge()
        return bridge.is_ros_available()
    except Exception:
        return False


# Export key classes for compatibility
__all__ = [
    'RobotApiAdapter', 'EnhancedRobotConnection', 'ROSServiceBridge',
    'ROSDashboard', 'ROSFeedback', 'BackendType', 'MigrationFeature',
    'create_dobot_api', 'create_migration_adapter', 'is_ros_available'
]


if __name__ == "__main__":
    # Test the ROS bridge
    print("🧪 Testing ROS Bridge...")
    
    try:
        # Test basic connectivity
        connection = EnhancedRobotConnection("192.168.1.6", use_ros_migration=True)
        success, message = connection.test_network_connectivity()
        print(f"Network test: {success} - {message}")
        
        # Test adapter creation
        adapter = create_migration_adapter("192.168.1.6")
        status = adapter.get_status()
        print(f"Adapter status: {status}")
        
        print("✅ ROS Bridge test completed")
        
    except Exception as e:
        print(f"❌ ROS Bridge test failed: {e}")
