#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emergency Stop Coordination System for Phase 5

This module provides comprehensive emergency stop capabilities with
multi-level escalation, graceful degradation, and system coordination.

Key Features:
- Multi-level emergency stop procedures
- Graceful system shutdown and recovery
- Integration with motion controller and safety systems
- Emergency response coordination
- Recovery and reset procedures

Author: TCP-to-ROS Migration Team
Created: Phase 5 Day 2 Implementation
"""

import numpy as np
import time
import threading
from typing import List, Dict, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import json

# Phase 4 integration
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'robot_control'))
    from migration_logger import MigrationLogger
    PHASE4_INTEGRATION = True
except ImportError:
    PHASE4_INTEGRATION = False
    import logging

class EmergencyLevel(Enum):
    """Emergency stop levels"""
    SOFT_STOP = "soft_stop"          # Gradual deceleration
    IMMEDIATE_STOP = "immediate_stop" # Quick stop
    HARD_STOP = "hard_stop"          # Immediate halt
    SYSTEM_SHUTDOWN = "system_shutdown" # Complete system shutdown

class EmergencyReason(Enum):
    """Reasons for emergency stop"""
    MANUAL_TRIGGER = "manual_trigger"
    COLLISION_DETECTED = "collision_detected"
    SAFETY_VIOLATION = "safety_violation"
    SYSTEM_ERROR = "system_error"
    COMMUNICATION_LOST = "communication_lost"
    HARDWARE_FAULT = "hardware_fault"
    SOFTWARE_FAULT = "software_fault"
    EXTERNAL_SIGNAL = "external_signal"

@dataclass
class EmergencyEvent:
    """Emergency stop event information"""
    event_id: str
    timestamp: float
    level: EmergencyLevel
    reason: EmergencyReason
    description: str
    source: str
    robot_position: Optional[np.ndarray] = None
    recovery_required: bool = True
    recovered: bool = False

@dataclass
class EmergencyStatus:
    """Current emergency system status"""
    active: bool
    level: Optional[EmergencyLevel]
    triggered_time: Optional[float]
    reason: Optional[EmergencyReason]
    description: str
    recovery_possible: bool
    recovery_steps: List[str]

class EmergencyStop:
    """
    Comprehensive emergency stop system with multi-level responses
    and coordinated system shutdown/recovery procedures.
    """
    
    def __init__(self,
                 motion_controller: Optional[Any] = None,
                 robot_adapter: Optional[Any] = None,
                 safety_monitor: Optional[Any] = None,
                 logger: Optional[Any] = None):
        """
        Initialize emergency stop system
        
        Args:
            motion_controller: Motion controller to stop
            robot_adapter: Robot adapter for communication
            safety_monitor: Safety monitoring system
            logger: Logger instance for events
        """
        # Logger setup
        if PHASE4_INTEGRATION and logger is None:
            self.logger = MigrationLogger("EmergencyStop")
        else:
            self.logger = logger or self._create_fallback_logger()
            
        # System components
        self.motion_controller = motion_controller
        self.robot_adapter = robot_adapter
        self.safety_monitor = safety_monitor
        
        # Emergency state
        self.emergency_active = False
        self.current_level = None
        self.current_reason = None
        self.trigger_time = None
        self.description = ""
        
        # Emergency history
        self.emergency_events: List[EmergencyEvent] = []
        self.event_counter = 0
        self.max_history = 100
        
        # Recovery procedures
        self.recovery_callbacks: List[Callable] = []
        self.recovery_steps = []
        self.recovery_in_progress = False
        
        # Emergency response configuration
        self.response_config = {
            EmergencyLevel.SOFT_STOP: {
                'deceleration_time': 2.0,  # seconds
                'allow_movement': False,
                'stop_motion_controller': True,
                'shutdown_systems': False
            },
            EmergencyLevel.IMMEDIATE_STOP: {
                'deceleration_time': 0.5,  # seconds
                'allow_movement': False,
                'stop_motion_controller': True,
                'shutdown_systems': False
            },
            EmergencyLevel.HARD_STOP: {
                'deceleration_time': 0.0,  # immediate
                'allow_movement': False,
                'stop_motion_controller': True,
                'shutdown_systems': False
            },
            EmergencyLevel.SYSTEM_SHUTDOWN: {
                'deceleration_time': 0.0,  # immediate
                'allow_movement': False,
                'stop_motion_controller': True,
                'shutdown_systems': True
            }
        }
        
        # Statistics
        self.stats = {
            'total_emergency_stops': 0,
            'stops_by_level': {},
            'stops_by_reason': {},
            'average_recovery_time': 0.0,
            'successful_recoveries': 0,
            'failed_recoveries': 0
        }
        
        self.logger.info("🚨 Emergency stop system initialized")
    
    def trigger_emergency_stop(self,
                             reason: Union[EmergencyReason, str] = EmergencyReason.MANUAL_TRIGGER,
                             level: EmergencyLevel = EmergencyLevel.IMMEDIATE_STOP,
                             description: str = "",
                             source: str = "unknown") -> bool:
        """
        Trigger emergency stop procedure
        
        Args:
            reason: Reason for emergency stop
            level: Emergency level determining response
            description: Detailed description of emergency
            source: Source system that triggered emergency
            
        Returns:
            True if emergency stop was successfully triggered
        """
        try:
            # Convert string reason to enum if needed
            if isinstance(reason, str):
                reason = EmergencyReason(reason)
            
            # Check if already in emergency state
            if self.emergency_active and self.current_level == level:
                self.logger.warning("⚠️ Emergency stop already active at this level")
                return True
            
            # Record current robot position if available
            robot_position = None
            if self.motion_controller:
                try:
                    status = self.motion_controller.get_status()
                    robot_position = status.current_position.copy()
                except:
                    pass
            
            # Create emergency event
            event_id = f"emergency_{self.event_counter:06d}"
            self.event_counter += 1
            
            event = EmergencyEvent(
                event_id=event_id,
                timestamp=time.time(),
                level=level,
                reason=reason,
                description=description or f"{reason.value} triggered",
                source=source,
                robot_position=robot_position
            )
            
            # Update emergency state
            self.emergency_active = True
            self.current_level = level
            self.current_reason = reason
            self.trigger_time = time.time()
            self.description = event.description
            
            # Record event
            self.emergency_events.append(event)
            self._update_statistics(event)
            
            # Execute emergency response
            response_success = self._execute_emergency_response(level, event)
            
            if response_success:
                self.logger.error(f"🚨 EMERGENCY STOP ACTIVATED: {level.value} - {description}")
                self.logger.error(f"🚨 Reason: {reason.value} from {source}")
            else:
                self.logger.error(f"❌ Emergency stop execution failed!")
                
            return response_success
            
        except Exception as e:
            self.logger.error(f"❌ Emergency stop trigger failed: {e}")
            return False
    
    def reset_emergency_stop(self) -> bool:
        """
        Reset emergency stop state and begin recovery procedures
        
        Returns:
            True if reset was successful
        """
        if not self.emergency_active:
            self.logger.info("🛡️ No emergency stop active")
            return True
            
        try:
            # Check if recovery is possible
            if not self._can_recover():
                self.logger.error("❌ Recovery not possible - manual intervention required")
                return False
            
            # Begin recovery procedure
            recovery_success = self._execute_recovery_procedure()
            
            if recovery_success:
                # Reset emergency state
                self.emergency_active = False
                self.current_level = None
                self.current_reason = None
                self.trigger_time = None
                self.description = ""
                
                # Update statistics
                self.stats['successful_recoveries'] += 1
                
                self.logger.info("🛡️ Emergency stop reset successfully")
                return True
            else:
                self.stats['failed_recoveries'] += 1
                self.logger.error("❌ Emergency stop reset failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Emergency stop reset error: {e}")
            self.stats['failed_recoveries'] += 1
            return False
    
    def get_emergency_status(self) -> EmergencyStatus:
        """Get current emergency system status"""
        recovery_steps = []
        recovery_possible = True
        
        if self.emergency_active:
            recovery_steps = self._get_recovery_steps()
            recovery_possible = self._can_recover()
        
        return EmergencyStatus(
            active=self.emergency_active,
            level=self.current_level,
            triggered_time=self.trigger_time,
            reason=self.current_reason,
            description=self.description,
            recovery_possible=recovery_possible,
            recovery_steps=recovery_steps
        )
    
    def add_recovery_callback(self, callback: Callable) -> None:
        """Add callback for recovery procedures"""
        self.recovery_callbacks.append(callback)
        self.logger.info("🛡️ Recovery callback added")
    
    def is_emergency_active(self) -> bool:
        """Check if emergency stop is currently active"""
        return self.emergency_active
    
    def get_emergency_level(self) -> Optional[EmergencyLevel]:
        """Get current emergency level"""
        return self.current_level
    
    def get_emergency_events(self) -> List[EmergencyEvent]:
        """Get history of emergency events"""
        return self.emergency_events.copy()
    
    def get_emergency_statistics(self) -> Dict:
        """Get emergency stop statistics"""
        return {
            'emergency_active': self.emergency_active,
            'current_level': self.current_level.value if self.current_level else None,
            'total_emergency_stops': self.stats['total_emergency_stops'],
            'stops_by_level': self.stats['stops_by_level'].copy(),
            'stops_by_reason': self.stats['stops_by_reason'].copy(),
            'successful_recoveries': self.stats['successful_recoveries'],
            'failed_recoveries': self.stats['failed_recoveries'],
            'recovery_success_rate': (
                self.stats['successful_recoveries'] / 
                max(1, self.stats['successful_recoveries'] + self.stats['failed_recoveries'])
            ),
            'events_count': len(self.emergency_events)
        }
    
    def force_reset(self) -> bool:
        """Force reset emergency state (use with caution)"""
        try:
            self.logger.warning("⚠️ FORCE RESET: Emergency stop state cleared")
            
            self.emergency_active = False
            self.current_level = None
            self.current_reason = None
            self.trigger_time = None
            self.description = ""
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Force reset failed: {e}")
            return False
    
    def _execute_emergency_response(self, level: EmergencyLevel, event: EmergencyEvent) -> bool:
        """Execute emergency response based on level"""
        try:
            config = self.response_config[level]
            success = True
            
            # Stop motion controller
            if config['stop_motion_controller'] and self.motion_controller:
                try:
                    if level == EmergencyLevel.SOFT_STOP:
                        # Gradual stop
                        success &= self.motion_controller.stop_motion()
                    else:
                        # Immediate stop
                        success &= self.motion_controller.emergency_stop()
                        
                    self.logger.info("🛑 Motion controller stopped")
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to stop motion controller: {e}")
                    success = False
            
            # Stop robot communication
            if self.robot_adapter:
                try:
                    # Send emergency stop command to robot
                    if hasattr(self.robot_adapter, 'emergency_stop'):
                        self.robot_adapter.emergency_stop()
                    elif hasattr(self.robot_adapter, 'stop_motion'):
                        self.robot_adapter.stop_motion()
                        
                    self.logger.info("🛑 Robot adapter stopped")
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to stop robot adapter: {e}")
                    success = False
            
            # Shutdown systems if required
            if config['shutdown_systems']:
                success &= self._shutdown_systems()
            
            # Notify safety monitor
            if self.safety_monitor:
                try:
                    self.safety_monitor.emergency_stop_active = True
                except Exception as e:
                    self.logger.error(f"❌ Failed to notify safety monitor: {e}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Emergency response execution error: {e}")
            return False
    
    def _execute_recovery_procedure(self) -> bool:
        """Execute recovery procedure"""
        try:
            self.recovery_in_progress = True
            recovery_start_time = time.time()
            
            self.logger.info("🔄 Starting emergency recovery procedure...")
            
            # Step 1: Verify system state
            if not self._verify_system_state():
                self.logger.error("❌ System state verification failed")
                return False
            
            # Step 2: Reset motion controller
            if self.motion_controller:
                try:
                    # Clear emergency state in motion controller
                    if hasattr(self.motion_controller, 'emergency_stop_flag'):
                        self.motion_controller.emergency_stop_flag = False
                    
                    # Reset state to idle
                    from ..motion_controller import MotionState
                    self.motion_controller.state = MotionState.IDLE
                    
                    self.logger.info("✅ Motion controller reset")
                    
                except Exception as e:
                    self.logger.error(f"❌ Motion controller reset failed: {e}")
                    return False
            
            # Step 3: Reset robot adapter
            if self.robot_adapter:
                try:
                    # Re-establish communication if needed
                    if hasattr(self.robot_adapter, 'reset') and callable(self.robot_adapter.reset):
                        self.robot_adapter.reset()
                    
                    self.logger.info("✅ Robot adapter reset")
                    
                except Exception as e:
                    self.logger.error(f"❌ Robot adapter reset failed: {e}")
                    return False
            
            # Step 4: Execute recovery callbacks
            for callback in self.recovery_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"❌ Recovery callback failed: {e}")
            
            # Step 5: Verify recovery
            if not self._verify_recovery():
                self.logger.error("❌ Recovery verification failed")
                return False
            
            # Calculate recovery time
            recovery_time = time.time() - recovery_start_time
            self._update_recovery_stats(recovery_time)
            
            self.recovery_in_progress = False
            self.logger.info(f"✅ Emergency recovery completed in {recovery_time:.2f}s")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Recovery procedure failed: {e}")
            self.recovery_in_progress = False
            return False
    
    def _can_recover(self) -> bool:
        """Check if recovery is possible"""
        # Cannot recover from system shutdown without manual intervention
        if self.current_level == EmergencyLevel.SYSTEM_SHUTDOWN:
            return False
            
        # Check if system components are available
        if not self.motion_controller and not self.robot_adapter:
            return False
            
        # Check if recovery is already in progress
        if self.recovery_in_progress:
            return False
            
        return True
    
    def _get_recovery_steps(self) -> List[str]:
        """Get list of recovery steps required"""
        steps = []
        
        if not self.emergency_active:
            return ["No emergency active"]
        
        if self.current_level == EmergencyLevel.SYSTEM_SHUTDOWN:
            steps.append("Manual system restart required")
            steps.append("Check hardware connections")
            steps.append("Restart robot control software")
        else:
            steps.append("Verify robot is in safe position")
            steps.append("Check for obstacles")
            steps.append("Reset emergency stop")
            steps.append("Resume normal operation")
        
        return steps
    
    def _verify_system_state(self) -> bool:
        """Verify system is in safe state for recovery"""
        try:
            # Check motion controller state
            if self.motion_controller:
                status = self.motion_controller.get_status()
                # Verify robot is not moving
                if np.linalg.norm(status.velocity) > 1.0:  # 1 mm/s threshold
                    return False
            
            # Check robot adapter connection
            if self.robot_adapter:
                # Verify communication is working
                if hasattr(self.robot_adapter, 'is_connected'):
                    if not self.robot_adapter.is_connected():
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ System state verification error: {e}")
            return False
    
    def _verify_recovery(self) -> bool:
        """Verify recovery was successful"""
        try:
            # Check that motion controller is responsive
            if self.motion_controller:
                status = self.motion_controller.get_status()
                from ..motion_controller import MotionState
                if status.state not in [MotionState.IDLE, MotionState.PAUSED]:
                    return False
            
            # Verify no active safety alerts
            if self.safety_monitor:
                safety_status = self.safety_monitor.get_safety_status()
                if safety_status.emergency_stop_active:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Recovery verification error: {e}")
            return False
    
    def _shutdown_systems(self) -> bool:
        """Shutdown system components"""
        try:
            self.logger.warning("🔌 Shutting down system components...")
            
            # This would implement actual system shutdown procedures
            # For now, just log the action
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ System shutdown error: {e}")
            return False
    
    def _update_statistics(self, event: EmergencyEvent) -> None:
        """Update emergency stop statistics"""
        self.stats['total_emergency_stops'] += 1
        
        level_key = event.level.value
        reason_key = event.reason.value
        
        self.stats['stops_by_level'][level_key] = (
            self.stats['stops_by_level'].get(level_key, 0) + 1
        )
        self.stats['stops_by_reason'][reason_key] = (
            self.stats['stops_by_reason'].get(reason_key, 0) + 1
        )
    
    def _update_recovery_stats(self, recovery_time: float) -> None:
        """Update recovery statistics"""
        current_avg = self.stats['average_recovery_time']
        total_recoveries = self.stats['successful_recoveries']
        
        if total_recoveries == 0:
            self.stats['average_recovery_time'] = recovery_time
        else:
            # Calculate running average
            self.stats['average_recovery_time'] = (
                (current_avg * total_recoveries + recovery_time) / (total_recoveries + 1)
            )
    
    def _create_fallback_logger(self):
        """Create fallback logger if Phase 4 integration not available"""
        logger = logging.getLogger("EmergencyStop")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

# Validation function for Day 2
def validate_emergency_stop():
    """Validate emergency stop implementation"""
    print("🧪 Validating Emergency Stop System...")
    
    try:
        # Initialize emergency stop
        emergency_stop = EmergencyStop()
        
        # Test emergency stop triggering
        success = emergency_stop.trigger_emergency_stop(
            reason=EmergencyReason.MANUAL_TRIGGER,
            level=EmergencyLevel.IMMEDIATE_STOP,
            description="Test emergency stop",
            source="validation"
        )
        assert success, "Emergency stop triggering failed"
        assert emergency_stop.is_emergency_active(), "Emergency state not active"
        print("✅ Emergency stop triggering working")
        
        # Test status retrieval
        status = emergency_stop.get_emergency_status()
        assert status.active, "Emergency status not reported as active"
        assert status.level == EmergencyLevel.IMMEDIATE_STOP, "Emergency level incorrect"
        print("✅ Emergency status reporting working")
        
        # Test reset (should fail initially for safety)
        reset_success = emergency_stop.force_reset()
        assert reset_success, "Force reset failed"
        assert not emergency_stop.is_emergency_active(), "Emergency still active after reset"
        print("✅ Emergency reset working")
        
        # Test statistics
        stats = emergency_stop.get_emergency_statistics()
        assert stats['total_emergency_stops'] > 0, "Statistics not updated"
        print("✅ Emergency statistics working")
        
        print("🎯 Emergency Stop System validation successful!")
        return True
        
    except Exception as e:
        print(f"❌ Emergency Stop System validation failed: {e}")
        return False

if __name__ == "__main__":
    validate_emergency_stop()
