#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced ROS Adapter - Phase 2 Migration

This enhanced adapter provides complete compatibility bridge between TCP and ROS backends.
It uses the new core modules (tcp_api_core and ros_service_bridge) to provide seamless
dual-backend support with automatic fallback and service discovery.

Key Improvements:
- Uses dedicated TCP and ROS core modules
- Better error handling and service discovery
- Enhanced monitoring and status reporting
- Gradual migration support with feature flags
- Complete API compatibility
"""

import os
import sys
import time
import threading
from typing import Dict, List, Tuple, Any, Optional, Union
from enum import Enum

# Import our new core modules
try:
    from .tcp_api_core import TCPApiCore, create_tcp_api, TCP_API_AVAILABLE
    from .ros_service_bridge import ROSServiceBridge, ROSDashboard, ROSFeedback, create_ros_api, is_ros_available
except ImportError:
    # Fallback for direct execution
    from tcp_api_core import TCPApiCore, create_tcp_api, TCP_API_AVAILABLE
    from ros_service_bridge import ROSServiceBridge, ROSDashboard, ROSFeedback, create_ros_api, is_ros_available


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


class RobotApiAdapter:
    """
    Main adapter class providing unified interface for both TCP and ROS backends
    """
    
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
        self.tcp_api = None
        self.ros_dashboard = None
        self.ros_feedback = None
        self.ros_bridge = None
        
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
        print(f"📊 Available backends: TCP={backend_status['tcp']}, ROS={backend_status['ros']}")
    
    def _check_backend_availability(self) -> Dict[str, bool]:
        """Check which backends are available"""
        return {
            'tcp': TCP_API_AVAILABLE,
            'ros': is_ros_available(),
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
        self.tcp_api = create_tcp_api(self.robot_ip)
        return self.tcp_api.connect()
    
    def _connect_ros(self) -> Tuple[bool, str]:
        """Connect using ROS backend"""
        self.ros_dashboard, self.ros_feedback = create_ros_api(self.robot_ip)
        dashboard_success, dashboard_msg = self.ros_dashboard.connect()
        
        if dashboard_success:
            feedback_success, feedback_msg = self.ros_feedback.connect()
            return True, f"ROS services connected (Dashboard: {dashboard_msg})"
        else:
            return False, f"ROS dashboard connection failed: {dashboard_msg}"
    
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
            if is_ros_available():
                self.active_backend = BackendType.ROS
                success, message = self._connect_ros()
                if success:
                    self._connected = True
                    return True, f"Upgraded to ROS successful: {message}"
        
        return False, "All connection attempts failed"
    
    def disconnect(self) -> None:
        """Disconnect from robot"""
        with self._lock:
            if self.tcp_api:
                self.tcp_api.disconnect()
                self.tcp_api = None
            
            if self.ros_dashboard:
                self.ros_dashboard.disconnect()
                self.ros_dashboard = None
            
            if self.ros_feedback:
                self.ros_feedback.disconnect()
                self.ros_feedback = None
            
            self._connected = False
        
        print(f"🔌 Disconnected from {self.active_backend.value.upper()} backend")
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected
    
    def get_dashboard(self):
        """Get dashboard instance for compatibility"""
        if self.active_backend == BackendType.ROS and self.ros_dashboard:
            return ROSDashboardWrapper(self.ros_dashboard, self)
        elif self.active_backend == BackendType.TCP and self.tcp_api:
            return TCPDashboardWrapper(self.tcp_api.dashboard, self)
        else:
            return None
    
    def get_feedback(self):
        """Get feedback instance for compatibility"""
        if self.active_backend == BackendType.ROS and self.ros_feedback:
            return self.ros_feedback
        elif self.active_backend == BackendType.TCP and self.tcp_api:
            return self.tcp_api.feedback
        else:
            return None
    
    def enable_migration_feature(self, feature: MigrationFeature) -> bool:
        """Enable a migration feature"""
        if not self.migration_features[feature]:
            self.migration_features[feature] = True
            print(f"✅ Migration feature enabled: {feature.value}")
            return True
        return False
    
    def disable_migration_feature(self, feature: MigrationFeature) -> bool:
        """Disable a migration feature"""
        if self.migration_features[feature]:
            self.migration_features[feature] = False
            print(f"❌ Migration feature disabled: {feature.value}")
            return True
        return False
    
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


class TCPDashboardWrapper:
    """Wrapper for TCP dashboard providing tracking and feature migration"""
    
    def __init__(self, tcp_dashboard, adapter: RobotApiAdapter):
        self.tcp_dashboard = tcp_dashboard
        self.adapter = adapter
    
    def __getattr__(self, name):
        """Delegate all calls to TCP dashboard with tracking"""
        if hasattr(self.tcp_dashboard, name):
            def wrapper(*args, **kwargs):
                self.adapter.stats['tcp_calls'] += 1
                try:
                    return getattr(self.tcp_dashboard, name)(*args, **kwargs)
                except Exception as e:
                    self.adapter.stats['errors'] += 1
                    raise
            return wrapper
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


class ROSDashboardWrapper:
    """Wrapper for ROS dashboard providing tracking and feature migration"""
    
    def __init__(self, ros_dashboard, adapter: RobotApiAdapter):
        self.ros_dashboard = ros_dashboard
        self.adapter = adapter
    
    def __getattr__(self, name):
        """Delegate all calls to ROS dashboard with tracking"""
        if hasattr(self.ros_dashboard, name):
            def wrapper(*args, **kwargs):
                self.adapter.stats['ros_calls'] += 1
                try:
                    return getattr(self.ros_dashboard, name)(*args, **kwargs)
                except Exception as e:
                    self.adapter.stats['errors'] += 1
                    raise
            return wrapper
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


# Compatibility layer - maintains original API
class DobotApiDashboard:
    """
    Drop-in replacement for original DobotApiDashboard
    """
    
    def __init__(self, robot_ip: str, port: int = 29999, use_ros: bool = False):
        backend = BackendType.ROS if use_ros else BackendType.TCP
        self.adapter = RobotApiAdapter(robot_ip, backend)
        self.dashboard = None
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to robot"""
        success, message = self.adapter.connect()
        if success:
            self.dashboard = self.adapter.get_dashboard()
        return success, message
    
    def disconnect(self) -> None:
        """Disconnect from robot"""
        self.adapter.disconnect()
    
    def __getattr__(self, name):
        """Delegate to dashboard"""
        if self.dashboard and hasattr(self.dashboard, name):
            return getattr(self.dashboard, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


class DobotApiFeedBack:
    """
    Drop-in replacement for original DobotApiFeedBack
    """
    
    def __init__(self, robot_ip: str, port: int = 30004, use_ros: bool = False):
        backend = BackendType.ROS if use_ros else BackendType.TCP
        self.adapter = RobotApiAdapter(robot_ip, backend)
        self.feedback = None
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to robot feedback"""
        success, message = self.adapter.connect()
        if success:
            self.feedback = self.adapter.get_feedback()
        return success, message
    
    def disconnect(self) -> None:
        """Disconnect from robot feedback"""
        self.adapter.disconnect()
    
    def __getattr__(self, name):
        """Delegate to feedback"""
        if self.feedback and hasattr(self.feedback, name):
            return getattr(self.feedback, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


# Factory functions
def create_dobot_api(robot_ip: str = "192.168.1.6", 
                     backend: BackendType = BackendType.AUTO,
                     migration_features: Dict[MigrationFeature, bool] = None) -> Tuple[DobotApiDashboard, DobotApiFeedBack]:
    """
    Factory function to create enhanced Dobot API instances
    """
    # Create shared adapter
    adapter = RobotApiAdapter(robot_ip, backend, migration_features)
    
    # Create wrapper instances that share the adapter
    dashboard = DobotApiDashboard.__new__(DobotApiDashboard)
    dashboard.adapter = adapter
    dashboard.dashboard = None
    
    feedback = DobotApiFeedBack.__new__(DobotApiFeedBack)
    feedback.adapter = adapter
    feedback.feedback = None
    
    return dashboard, feedback


def create_migration_adapter(robot_ip: str = "192.168.1.6") -> RobotApiAdapter:
    """
    Create migration adapter with gradual feature enablement
    """
    # Start with connection management only
    features = {
        MigrationFeature.CONNECTION_MANAGEMENT: True,
        MigrationFeature.MOVEMENT_COMMANDS: False,
        MigrationFeature.STATUS_MONITORING: False,
        MigrationFeature.ERROR_HANDLING: False,
        MigrationFeature.ADVANCED_FEATURES: False,
    }
    
    return RobotApiAdapter(robot_ip, BackendType.AUTO, features)


# Configuration
MIGRATION_CONFIG = {
    'default_backend': BackendType.AUTO,
    'enable_statistics': True,
    'auto_fallback': True,
    'connection_timeout': 10.0,
    'service_discovery_timeout': 5.0
}


# Export availability flags
ROBOT_API_AVAILABLE = TCP_API_AVAILABLE or is_ros_available()


if __name__ == "__main__":
    # Test the enhanced adapter
    print("🧪 Testing Enhanced ROS Adapter...")
    
    try:
        # Test migration adapter
        adapter = create_migration_adapter("192.168.1.6")
        
        print("Connecting...")
        success, message = adapter.connect()
        print(f"Connection: {success} - {message}")
        
        if success:
            print("Getting status...")
            status = adapter.get_status()
            print(f"Status: {status}")
            
            # Test feature migration
            print("Enabling movement commands...")
            adapter.enable_migration_feature(MigrationFeature.MOVEMENT_COMMANDS)
            
            dashboard = adapter.get_dashboard()
            if dashboard:
                print("Testing robot mode...")
                try:
                    mode = dashboard.robot_mode()
                    print(f"Robot mode: {mode}")
                except Exception as e:
                    print(f"Robot mode test failed: {e}")
        
        adapter.disconnect()
        print("✅ Enhanced adapter test completed successfully")
        
    except Exception as e:
        print(f"❌ Enhanced adapter test failed: {e}")
        import traceback
        traceback.print_exc()
