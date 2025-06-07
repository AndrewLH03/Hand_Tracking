#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Control Package

Consolidated robot control system with unified connection management,
utilities, and streamlined architecture.

This package eliminates redundancy from the previous scattered modules
and provides a clean, maintainable interface for robot control operations.
"""

# Import from consolidated modules
from .core_api import (
    DobotApiDashboard,
    DobotApiFeedback,
    ConnectionManager,
    test_robot_connection,
    check_robot_alarms,
    RobotStatusMonitor
)

from .utilities import (
    parse_api_response,
    wait_with_progress,
    execute_robot_command,
    format_position,
    validate_position_values,
    calculate_movement_time,
    retry_operation,
    safe_float_conversion,
    safe_int_conversion
)

from .robot_controller import (
    RobotController,
    IntegratedRobotSystem,
    HandTrackingServer,
    CoordinateTransformer
)

# Backward compatibility aliases
RobotSystem = IntegratedRobotSystem
MediaPipeToRobotTransformer = CoordinateTransformer
validate_position = validate_position_values  # Function alias

from .ros_bridge import (
    RobotApiAdapter,
    EnhancedRobotConnection,
    BackendType,
    MigrationFeature,
    create_dobot_api,
    create_migration_adapter,
    is_ros_available
)

# Import migration logger for backward compatibility
from .migration_logger import (
    get_logger,
    setup_logging
)

# Package metadata
__version__ = "2.0.0"
__author__ = "Robot Control Team"
__description__ = "Consolidated Robot Control System"

# Main exports
__all__ = [
    # Core API
    'DobotApiDashboard',
    'DobotApiFeedback', 
    'ConnectionManager',
    'test_robot_connection',
    'check_robot_alarms',
    'RobotStatusMonitor',
    
    # Utilities
    'parse_api_response',
    'wait_with_progress', 
    'execute_robot_command',
    'format_position',
    'validate_position_values',
    'calculate_movement_time',
    'retry_operation',
    'safe_float_conversion',
    'safe_int_conversion',    # Robot Control
    'RobotController',
    'IntegratedRobotSystem',
    'RobotSystem',  # Backward compatibility alias
    'HandTrackingServer',
    'CoordinateTransformer',
    'MediaPipeToRobotTransformer',  # Backward compatibility alias
    'validate_position',
    
    # ROS Bridge
    'RobotApiAdapter',
    'EnhancedRobotConnection',
    'BackendType',
    'MigrationFeature',
    'create_dobot_api',
    'create_migration_adapter',
    'is_ros_available',
    
    # Logging
    'get_logger',
    'setup_logging'
]