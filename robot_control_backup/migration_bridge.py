#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration Bridge Module

This module provides the compatibility bridge between the existing robot_connection.py
module and the new enhanced ROS adapter. It allows gradual migration while maintaining
all existing functionality.

The bridge provides:
- Drop-in replacement for robot_connection imports
- Gradual feature migration with fallback
- Enhanced error handling and monitoring
- Service discovery and auto-configuration
"""

import sys
import os
import time
from typing import Optional, Tuple, List, Dict, Any

# Import enhanced adapter
try:
    from .enhanced_ros_adapter import (
        RobotApiAdapter, BackendType, MigrationFeature,
        create_migration_adapter, ROBOT_API_AVAILABLE
    )
    ENHANCED_ADAPTER_AVAILABLE = True
except ImportError:
    try:
        from enhanced_ros_adapter import (
            RobotApiAdapter, BackendType, MigrationFeature, 
            create_migration_adapter, ROBOT_API_AVAILABLE
        )
        ENHANCED_ADAPTER_AVAILABLE = True
    except ImportError:
        ENHANCED_ADAPTER_AVAILABLE = False
        print("⚠️  Enhanced adapter not available, using fallback")
        # Create dummy classes to prevent import errors
        class BackendType:
            TCP = "tcp"
            ROS = "ros"
        class MigrationFeature:
            CONNECTION_MANAGEMENT = "connection_management"
            MOVEMENT_COMMANDS = "movement_commands" 
            STATUS_MONITORING = "status_monitoring"
            ERROR_HANDLING = "error_handling"
            ADVANCED_FEATURES = "advanced_features"
        ROBOT_API_AVAILABLE = False

# Import original robot_connection as fallback
try:
    from .robot_connection import RobotConnection as OriginalRobotConnection
    ORIGINAL_CONNECTION_AVAILABLE = True
except ImportError:
    try:
        from robot_connection import RobotConnection as OriginalRobotConnection
        ORIGINAL_CONNECTION_AVAILABLE = True
    except ImportError:
        ORIGINAL_CONNECTION_AVAILABLE = False
        print("⚠️  Original robot_connection not available")


class EnhancedRobotConnection:
    """
    Enhanced robot connection that can use either the original implementation
    or the new ROS adapter based on configuration and availability
    """
    
    def __init__(self, robot_ip: str = "192.168.1.6", 
                 dashboard_port: int = 29999, 
                 move_port: int = 30003, 
                 feed_port: int = 30004,
                 use_ros_migration: bool = False):
        """
        Initialize enhanced robot connection
        
        Args:
            robot_ip: IP address of the robot
            dashboard_port: Port for dashboard commands  
            move_port: Port for movement commands
            feed_port: Port for feedback
            use_ros_migration: Enable ROS migration features
        """
        self.robot_ip = robot_ip
        self.dashboard_port = dashboard_port
        self.move_port = move_port
        self.feed_port = feed_port
        self.use_ros_migration = use_ros_migration
        
        # Backend instances
        self.original_connection = None
        self.migration_adapter = None
        self.active_backend = None
        
        # Migration status
        self.migration_features_enabled = {
            MigrationFeature.CONNECTION_MANAGEMENT: False,
            MigrationFeature.MOVEMENT_COMMANDS: False,
            MigrationFeature.STATUS_MONITORING: False,
            MigrationFeature.ERROR_HANDLING: False,
            MigrationFeature.ADVANCED_FEATURES: False,
        }
        
        self._initialize_backends()
    
    def _initialize_backends(self):
        """Initialize available backends"""
        if self.use_ros_migration and ENHANCED_ADAPTER_AVAILABLE:
            try:
                self.migration_adapter = create_migration_adapter(self.robot_ip)
                self.active_backend = "migration"
                print("🚀 Using ROS migration adapter")
            except Exception as e:
                print(f"⚠️  Migration adapter failed, using original: {e}")
                self._use_original_backend()
        else:
            self._use_original_backend()
    
    def _use_original_backend(self):
        """Use original robot connection"""
        if ORIGINAL_CONNECTION_AVAILABLE:
            self.original_connection = OriginalRobotConnection(
                self.robot_ip, self.dashboard_port, 
                self.move_port, self.feed_port
            )
            self.active_backend = "original"
            print("🔧 Using original robot connection")
        else:
            raise RuntimeError("No robot connection backend available")
    
    def test_network_connectivity(self) -> Tuple[bool, str]:
        """Test basic network connectivity to the robot"""
        if self.active_backend == "migration" and self.migration_adapter:
            # Use enhanced connectivity test
            return self._test_enhanced_connectivity()
        elif self.original_connection:
            return self.original_connection.test_network_connectivity()
        else:
            return False, "No connection backend available"
    
    def _test_enhanced_connectivity(self) -> Tuple[bool, str]:
        """Enhanced connectivity test using migration adapter"""
        try:
            # Check backend availability
            backend_status = self.migration_adapter._check_backend_availability()
            
            if backend_status['ros']:
                # Test ROS connectivity
                success, message = self.migration_adapter._connect_ros()
                if success:
                    self.migration_adapter.disconnect()
                    return True, f"ROS connectivity OK: {message}"
            
            if backend_status['tcp']:
                # Test TCP connectivity  
                success, message = self.migration_adapter._connect_tcp()
                if success:
                    self.migration_adapter.disconnect()
                    return True, f"TCP connectivity OK: {message}"
            
            return False, "No backends available for connectivity test"
            
        except Exception as e:
            return False, f"Enhanced connectivity test failed: {e}"
    
    def connect(self) -> Tuple[bool, str]:
        """Connect to the robot"""
        if self.active_backend == "migration" and self.migration_adapter:
            return self.migration_adapter.connect()
        elif self.original_connection:
            return self.original_connection.connect()
        else:
            return False, "No connection backend available"
    
    def disconnect(self) -> None:
        """Disconnect from robot safely"""
        if self.active_backend == "migration" and self.migration_adapter:
            self.migration_adapter.disconnect()
        elif self.original_connection:
            self.original_connection.disconnect()
    
    def check_robot_alarms(self, description: str = "Checking for robot alarms") -> Tuple[bool, List[str]]:
        """Check and parse robot alarms"""
        if self.active_backend == "migration" and self.migration_features_enabled[MigrationFeature.ERROR_HANDLING]:
            return self._check_alarms_enhanced(description)
        elif self.original_connection:
            return self.original_connection.check_robot_alarms(description)
        else:
            return True, []  # Assume OK if can't check
    
    def _check_alarms_enhanced(self, description: str) -> Tuple[bool, List[str]]:
        """Enhanced alarm checking with ROS capabilities"""
        try:
            dashboard = self.migration_adapter.get_dashboard()
            if not dashboard:
                return True, []
            
            # Get error information
            error_response = dashboard.get_error_id()
            
            if not error_response:
                print("✅ No alarms detected (enhanced)")
                return True, []
            
            # Parse enhanced error response
            if isinstance(error_response, dict):
                errors = error_response.get('errors', [])
                if errors:
                    print(f"❌ Active errors detected (enhanced): {errors}")
                    return False, errors
                else:
                    print("✅ No active alarms detected (enhanced)")
                    return True, []
            
            return True, []
            
        except Exception as e:
            print(f"Enhanced alarm check failed: {e}, using fallback")
            # Fallback to original if available
            if self.original_connection:
                return self.original_connection.check_robot_alarms(description)
            return True, []
    
    def clear_errors(self) -> Tuple[bool, str]:
        """Clear robot errors"""
        if self.active_backend == "migration" and self.migration_adapter:
            try:
                dashboard = self.migration_adapter.get_dashboard()
                if dashboard:
                    result = dashboard.clear_error()
                    return True, f"Enhanced clear errors result: {result}"
                return False, "No dashboard available"
            except Exception as e:
                return False, f"Enhanced clear errors failed: {e}"
        elif self.original_connection:
            return self.original_connection.clear_errors()
        else:
            return False, "No connection backend available"
    
    def get_robot_mode(self) -> Tuple[int, str]:
        """Get the current robot mode"""
        if self.active_backend == "migration" and self.migration_features_enabled[MigrationFeature.STATUS_MONITORING]:
            return self._get_robot_mode_enhanced()
        elif self.original_connection:
            return self.original_connection.get_robot_mode()
        else:
            return 0, "No connection backend available"
    
    def _get_robot_mode_enhanced(self) -> Tuple[int, str]:
        """Enhanced robot mode detection"""
        try:
            dashboard = self.migration_adapter.get_dashboard()
            if not dashboard:
                return 0, "No dashboard available"
            
            mode_response = dashboard.robot_mode()
            
            if isinstance(mode_response, dict):
                mode = mode_response.get('mode', 0)
                description = mode_response.get('description', 'Unknown')
                return mode, description
            elif isinstance(mode_response, (list, tuple)) and len(mode_response) > 0:
                return int(mode_response[0]), "Enhanced mode detection"
            else:
                return 0, "Unable to parse enhanced mode response"
                
        except Exception as e:
            print(f"Enhanced mode detection failed: {e}")
            # Fallback to original
            if self.original_connection:
                return self.original_connection.get_robot_mode()
            return 0, f"Enhanced mode detection error: {e}"
    
    def enable_robot(self, timeout: float = 10.0) -> Tuple[bool, str]:
        """Enable the robot with timeout"""
        if self.active_backend == "migration" and self.migration_adapter:
            return self._enable_robot_enhanced(timeout)
        elif self.original_connection:
            return self.original_connection.enable_robot(timeout)
        else:
            return False, "No connection backend available"
    
    def _enable_robot_enhanced(self, timeout: float) -> Tuple[bool, str]:
        """Enhanced robot enabling with ROS capabilities"""
        try:
            dashboard = self.migration_adapter.get_dashboard()
            if not dashboard:
                return False, "No dashboard available"
            
            # Get current mode
            current_mode, description = self.get_robot_mode()
            print(f"Current robot mode (enhanced): {current_mode} ({description})")
            
            # Check if already enabled
            if current_mode in [3, 5]:
                return True, f"Robot already operational (Enhanced Mode {current_mode}: {description})"
            
            # Enable robot
            enable_result = dashboard.enable_robot()
            print(f"Enhanced enable result: {enable_result}")
            
            # Wait for enable with timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                mode, desc = self.get_robot_mode()
                if mode in [3, 5]:
                    elapsed = time.time() - start_time
                    return True, f"Robot enabled successfully (enhanced) after {elapsed:.1f}s (Mode {mode}: {desc})"
                time.sleep(0.5)
            
            final_mode, final_desc = self.get_robot_mode()
            return False, f"Enhanced enable timeout - Current mode: {final_mode} ({final_desc})"
            
        except Exception as e:
            print(f"Enhanced robot enable failed: {e}")
            # Fallback to original
            if self.original_connection:
                return self.original_connection.enable_robot(timeout)
            return False, f"Enhanced enable error: {e}"
    
    def get_dashboard(self):
        """Get the dashboard connection for use by robot control module"""
        if self.active_backend == "migration" and self.migration_adapter:
            return self.migration_adapter.get_dashboard()
        elif self.original_connection:
            return self.original_connection.get_dashboard()
        else:
            return None
    
    def is_robot_connected(self) -> bool:
        """Check if robot is connected"""
        if self.active_backend == "migration" and self.migration_adapter:
            return self.migration_adapter.is_connected()
        elif self.original_connection:
            return self.original_connection.is_robot_connected()
        else:
            return False
    
    def is_robot_enabled(self) -> bool:
        """Check if robot is enabled"""
        if self.original_connection:
            return self.original_connection.is_robot_enabled()
        else:
            # For migration adapter, check mode
            mode, _ = self.get_robot_mode()
            return mode in [3, 5]
    
    def enable_migration_feature(self, feature: MigrationFeature) -> bool:
        """Enable a specific migration feature"""
        if self.active_backend == "migration" and self.migration_adapter:
            self.migration_features_enabled[feature] = True
            return self.migration_adapter.enable_migration_feature(feature)
        return False
    
    def disable_migration_feature(self, feature: MigrationFeature) -> bool:
        """Disable a specific migration feature"""
        if self.active_backend == "migration" and self.migration_adapter:
            self.migration_features_enabled[feature] = False
            return self.migration_adapter.disable_migration_feature(feature)
        return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get migration status and statistics"""
        if self.active_backend == "migration" and self.migration_adapter:
            return {
                'active_backend': self.active_backend,
                'migration_features': self.migration_features_enabled.copy(),
                'adapter_status': self.migration_adapter.get_status(),
                'migration_available': True
            }
        else:
            return {
                'active_backend': self.active_backend,
                'migration_features': {},
                'adapter_status': {},
                'migration_available': False
            }


# Compatibility function - drop-in replacement for robot_connection.RobotConnection
def RobotConnection(robot_ip: str = "192.168.1.6", 
                   dashboard_port: int = 29999, 
                   move_port: int = 30003, 
                   feed_port: int = 30004,
                   enable_ros_migration: bool = False):
    """
    Factory function that returns either EnhancedRobotConnection or OriginalRobotConnection
    based on availability and configuration
    """
    if enable_ros_migration or not ORIGINAL_CONNECTION_AVAILABLE:
        return EnhancedRobotConnection(
            robot_ip, dashboard_port, move_port, feed_port, 
            use_ros_migration=True
        )
    else:
        return OriginalRobotConnection(robot_ip, dashboard_port, move_port, feed_port)


# Configuration
MIGRATION_CONFIG = {
    'auto_enable_features': False,
    'fallback_on_failure': True,
    'enhanced_monitoring': True,
    'statistics_collection': True
}


# Export flags
MIGRATION_AVAILABLE = (ENHANCED_ADAPTER_AVAILABLE and ROBOT_API_AVAILABLE)


if __name__ == "__main__":
    # Test the migration bridge
    print("🧪 Testing Migration Bridge...")
    
    try:
        # Test with migration enabled
        robot_conn = RobotConnection("192.168.1.6", enable_ros_migration=True)
        
        print("Testing network connectivity...")
        success, message = robot_conn.test_network_connectivity()
        print(f"Network: {success} - {message}")
        
        if success:
            print("Connecting to robot...")
            success, message = robot_conn.connect()
            print(f"Connection: {success} - {message}")
            
            if success:
                print("Getting migration status...")
                status = robot_conn.get_migration_status()
                print(f"Migration status: {status}")
                
                print("Testing alarm check...")
                alarm_ok, errors = robot_conn.check_robot_alarms()
                print(f"Alarms: OK={alarm_ok}, Errors={errors}")
        
        robot_conn.disconnect()
        print("✅ Migration bridge test completed successfully")
        
    except Exception as e:
        print(f"❌ Migration bridge test failed: {e}")
        import traceback
        traceback.print_exc()
