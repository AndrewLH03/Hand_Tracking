#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 5 Safety Systems Package

This package provides comprehensive safety and collision detection systems
for the advanced motion planning framework.

Components:
- AutoSafetyManager: Automatic background safety system management
- CollisionDetector: Real-time collision detection and avoidance
- SafetyMonitor: Centralized safety monitoring and event management
- EmergencyStop: Emergency stop coordination and response

Author: TCP-to-ROS Migration Team
Created: Phase 5 Day 2 Implementation
"""

__version__ = "1.0.0"
__author__ = "TCP-to-ROS Migration Team"

# Simplified automatic safety system
from .auto_safety_manager import (
    start_automatic_safety_systems,
    get_safety_status,
    emergency_shutdown,
    graceful_shutdown
)

# Core safety system components (for advanced usage)
from .collision_detector import CollisionDetector, CollisionType, SafetyZone
from .safety_monitor import SafetyMonitor, SafetyAlert, SafetyLevel
from .emergency_stop import EmergencyStop, EmergencyLevel

# Testing framework (optional)
try:
    from .safety_tests import SafetySystemTester, TestResult, SafetyTestSuite
    TESTING_AVAILABLE = True
except ImportError:
    TESTING_AVAILABLE = False

__all__ = [
    # Simplified automatic interface
    'start_automatic_safety_systems',
    'get_safety_status',
    'emergency_shutdown',
    'graceful_shutdown',
    
    # Core components
    'CollisionDetector',
    'CollisionType', 
    'SafetyZone',
    'SafetyMonitor',
    'SafetyAlert',
    'SafetyLevel',
    'EmergencyStop',
    'EmergencyLevel',
]

# Add testing components if available
if TESTING_AVAILABLE:
    __all__.extend(['SafetySystemTester', 'TestResult', 'SafetyTestSuite'])

def initialize_safety_systems():
    """Initialize all Phase 5 safety systems automatically"""
    print("🛡️ Phase 5 Safety Systems Initializing...")
    success = start_automatic_safety_systems()
    
    if success:
        status = get_safety_status()
        for component, state in status.items():
            if state == 'READY' or state == 'ACTIVE':
                print(f"✅ {component.replace('_', ' ').title()}: {state}")
            else:
                print(f"⚠️ {component.replace('_', ' ').title()}: {state}")
    
    return success
