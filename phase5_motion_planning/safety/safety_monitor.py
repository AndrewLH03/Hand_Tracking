#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Safety Monitoring System for Phase 5

This module provides centralized safety monitoring, event management,
and escalation procedures for the robotic arm system.

Key Features:
- Centralized safety event coordination
- Multi-level alert system with escalation
- Integration with collision detection
- Real-time safety status monitoring
- Comprehensive safety logging and reporting

Author: TCP-to-ROS Migration Team
Created: Phase 5 Day 2 Implementation
"""

import numpy as np
import time
import threading
from typing import List, Dict, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import queue
import json

# Import collision detection
from .collision_detector import CollisionDetector, CollisionResult, CollisionType

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

class SafetyLevel(Enum):
    """Safety alert levels"""
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class SafetyEventType(Enum):
    """Types of safety events"""
    COLLISION_DETECTED = "collision_detected"
    WORKSPACE_VIOLATION = "workspace_violation"
    VELOCITY_EXCEEDED = "velocity_exceeded"
    POSITION_ERROR = "position_error"
    COMMUNICATION_LOST = "communication_lost"
    SYSTEM_ERROR = "system_error"
    EMERGENCY_STOP = "emergency_stop"
    SAFETY_ZONE_VIOLATION = "safety_zone_violation"

@dataclass
class SafetyAlert:
    """Safety alert information"""
    alert_id: str
    timestamp: float
    event_type: SafetyEventType
    level: SafetyLevel
    message: str
    source: str
    data: Dict[str, Any]
    acknowledged: bool = False
    resolved: bool = False
    escalated: bool = False

@dataclass
class SafetyStatus:
    """Current safety system status"""
    monitoring_active: bool
    last_check_time: float
    active_alerts: int
    total_alerts: int
    emergency_stop_active: bool
    collision_detector_status: bool
    system_health: str  # healthy, degraded, critical
    safety_score: float  # 0.0 to 1.0

class SafetyMonitor:
    """
    Comprehensive safety monitoring system that coordinates all
    safety-related components and provides centralized event management.
    """
    
    def __init__(self,
                 collision_detector: Optional[CollisionDetector] = None,
                 emergency_stop: Optional[Any] = None,
                 update_rate: float = 20.0,  # Hz
                 logger: Optional[Any] = None):
        """
        Initialize safety monitoring system
        
        Args:
            collision_detector: Collision detection system
            emergency_stop: Emergency stop system
            update_rate: Monitoring update frequency in Hz
            logger: Logger instance for events
        """
        # Logger setup
        if PHASE4_INTEGRATION and logger is None:
            self.logger = MigrationLogger("SafetyMonitor")
        else:
            self.logger = logger or self._create_fallback_logger()
            
        # Component integration
        self.collision_detector = collision_detector
        self.emergency_stop = emergency_stop
        self.update_rate = update_rate
        self.check_interval = 1.0 / update_rate
        
        # Safety monitoring state
        self.monitoring_active = False
        self.emergency_stop_active = False
        self.system_health = "healthy"
        
        # Alert management
        self.active_alerts: List[SafetyAlert] = []
        self.alert_history: List[SafetyAlert] = []
        self.alert_counter = 0
        self.max_history = 1000
        
        # Callbacks and escalation
        self.alert_callbacks: List[Callable] = []
        self.escalation_rules: Dict[SafetyLevel, float] = {
            SafetyLevel.INFO: 0.0,      # No escalation
            SafetyLevel.WARNING: 30.0,   # Escalate after 30 seconds
            SafetyLevel.DANGER: 10.0,    # Escalate after 10 seconds
            SafetyLevel.CRITICAL: 5.0,   # Escalate after 5 seconds
            SafetyLevel.EMERGENCY: 0.0   # Immediate action
        }
        
        # Safety thresholds
        self.safety_thresholds = {
            'max_velocity': 1000.0,      # mm/s
            'max_acceleration': 5000.0,  # mm/s²
            'position_tolerance': 5.0,   # mm
            'communication_timeout': 5.0, # seconds
            'max_active_alerts': 10
        }
        
        # Current robot state
        self.current_position = np.array([0.0, 0.0, 0.0])
        self.current_velocity = np.array([0.0, 0.0, 0.0])
        self.last_position_time = time.time()
        self.communication_last_seen = time.time()
        
        # Threading for monitoring
        self.monitor_thread = None
        self.stop_monitoring = threading.Event()
        self.alert_queue = queue.Queue()
        
        # Statistics
        self.stats = {
            'total_alerts': 0,
            'alerts_by_type': {},
            'alerts_by_level': {},
            'average_response_time': 0.0,
            'uptime': 0.0,
            'start_time': time.time()
        }
        
        self.logger.info("🛡️ Safety monitor initialized")
    
    def start_monitoring(self) -> bool:
        """Start comprehensive safety monitoring"""
        if self.monitoring_active:
            self.logger.warning("⚠️ Safety monitoring already active")
            return False
            
        try:
            self.monitoring_active = True
            self.stop_monitoring.clear()
            self.stats['start_time'] = time.time()
            
            # Start collision detector if available
            if self.collision_detector:
                self.collision_detector.start_monitoring()
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitoring_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            self.logger.info("🛡️ Safety monitoring started")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start safety monitoring: {e}")
            self.monitoring_active = False
            return False
    
    def stop_monitoring(self) -> bool:
        """Stop safety monitoring"""
        if not self.monitoring_active:
            return True
            
        try:
            self.monitoring_active = False
            self.stop_monitoring.set()
            
            # Stop collision detector
            if self.collision_detector:
                self.collision_detector.stop_monitoring()
            
            # Stop monitoring thread
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=2.0)
                
            self.logger.info("🛡️ Safety monitoring stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to stop safety monitoring: {e}")
            return False
    
    def validate_movement(self, 
                         current_pos: np.ndarray,
                         target_pos: np.ndarray,
                         velocity: Optional[np.ndarray] = None) -> Tuple[bool, str]:
        """
        Validate a proposed movement for safety
        
        Args:
            current_pos: Current robot position
            target_pos: Proposed target position
            velocity: Current velocity if available
            
        Returns:
            Tuple of (is_safe, reason)
        """
        try:
            # Update robot state
            self.update_robot_state(current_pos, velocity)
            
            # Check if emergency stop is active
            if self.emergency_stop_active:
                return False, "Emergency stop is active"
            
            # Check collision detection if available
            if self.collision_detector:
                collision_result = self.collision_detector.detect_collisions(
                    current_pos, target_pos
                )
                
                if collision_result.collision_detected:
                    self._trigger_alert(
                        SafetyEventType.COLLISION_DETECTED,
                        SafetyLevel.DANGER,
                        f"Collision detected: {collision_result.recommendation}",
                        "collision_detector",
                        {"collision_result": collision_result.__dict__}
                    )
                    return False, collision_result.recommendation
            
            # Check velocity limits
            if velocity is not None:
                velocity_magnitude = np.linalg.norm(velocity)
                if velocity_magnitude > self.safety_thresholds['max_velocity']:
                    self._trigger_alert(
                        SafetyEventType.VELOCITY_EXCEEDED,
                        SafetyLevel.WARNING,
                        f"Velocity {velocity_magnitude:.1f} exceeds limit {self.safety_thresholds['max_velocity']}",
                        "safety_monitor",
                        {"velocity": velocity_magnitude, "limit": self.safety_thresholds['max_velocity']}
                    )
                    return False, "Velocity exceeds safety limits"
            
            # Check position error
            position_error = np.linalg.norm(target_pos - current_pos)
            if position_error > 500.0:  # Large movement check
                self._trigger_alert(
                    SafetyEventType.POSITION_ERROR,
                    SafetyLevel.INFO,
                    f"Large movement detected: {position_error:.1f}mm",
                    "safety_monitor",
                    {"position_error": position_error}
                )
            
            return True, "Movement validated - safe to proceed"
            
        except Exception as e:
            self.logger.error(f"❌ Movement validation error: {e}")
            self._trigger_alert(
                SafetyEventType.SYSTEM_ERROR,
                SafetyLevel.CRITICAL,
                f"Safety validation error: {e}",
                "safety_monitor",
                {"error": str(e)}
            )
            return False, "Safety validation error - movement blocked"
    
    def trigger_emergency_stop(self, reason: str = "Manual trigger") -> bool:
        """Trigger emergency stop"""
        try:
            self.emergency_stop_active = True
            
            # Trigger emergency stop system if available
            if self.emergency_stop:
                self.emergency_stop.trigger_emergency_stop(reason)
            
            # Create emergency alert
            self._trigger_alert(
                SafetyEventType.EMERGENCY_STOP,
                SafetyLevel.EMERGENCY,
                f"Emergency stop activated: {reason}",
                "safety_monitor",
                {"reason": reason, "timestamp": time.time()}
            )
            
            self.logger.error(f"🚨 EMERGENCY STOP: {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Emergency stop failed: {e}")
            return False
    
    def reset_emergency_stop(self) -> bool:
        """Reset emergency stop state"""
        try:
            if not self.emergency_stop_active:
                return True
                
            # Reset emergency stop system
            if self.emergency_stop:
                reset_success = self.emergency_stop.reset_emergency_stop()
                if not reset_success:
                    return False
            
            self.emergency_stop_active = False
            
            # Clear emergency alerts
            self._resolve_alerts_by_type(SafetyEventType.EMERGENCY_STOP)
            
            self.logger.info("🛡️ Emergency stop reset")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Emergency stop reset failed: {e}")
            return False
    
    def add_alert_callback(self, callback: Callable) -> None:
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
        self.logger.info("🛡️ Alert callback added")
    
    def get_safety_status(self) -> SafetyStatus:
        """Get comprehensive safety system status"""
        active_alert_count = len(self.active_alerts)
        collision_detector_ok = (self.collision_detector is not None and 
                               self.collision_detector.monitoring_active)
        
        # Calculate safety score
        safety_score = self._calculate_safety_score()
        
        # Determine system health
        if self.emergency_stop_active:
            health = "emergency"
        elif active_alert_count > self.safety_thresholds['max_active_alerts']:
            health = "critical"
        elif active_alert_count > 5:
            health = "degraded"
        else:
            health = "healthy"
        
        return SafetyStatus(
            monitoring_active=self.monitoring_active,
            last_check_time=time.time(),
            active_alerts=active_alert_count,
            total_alerts=len(self.alert_history),
            emergency_stop_active=self.emergency_stop_active,
            collision_detector_status=collision_detector_ok,
            system_health=health,
            safety_score=safety_score
        )
    
    def get_active_alerts(self) -> List[SafetyAlert]:
        """Get list of active safety alerts"""
        return self.active_alerts.copy()
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a safety alert"""
        try:
            for alert in self.active_alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    self.logger.info(f"🛡️ Alert acknowledged: {alert_id}")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Failed to acknowledge alert: {e}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a safety alert"""
        try:
            for i, alert in enumerate(self.active_alerts):
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    resolved_alert = self.active_alerts.pop(i)
                    self.alert_history.append(resolved_alert)
                    self.logger.info(f"🛡️ Alert resolved: {alert_id}")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Failed to resolve alert: {e}")
            return False
    
    def update_robot_state(self, 
                          position: np.ndarray,
                          velocity: Optional[np.ndarray] = None) -> None:
        """Update current robot state for monitoring"""
        self.current_position = position.copy()
        if velocity is not None:
            self.current_velocity = velocity.copy()
        self.last_position_time = time.time()
        self.communication_last_seen = time.time()
        
        # Update collision detector if available
        if self.collision_detector:
            self.collision_detector.update_robot_state(position, velocity)
    
    def get_safety_statistics(self) -> Dict:
        """Get comprehensive safety statistics"""
        current_time = time.time()
        uptime = current_time - self.stats['start_time']
        
        return {
            'monitoring_active': self.monitoring_active,
            'uptime_seconds': uptime,
            'total_alerts': self.stats['total_alerts'],
            'active_alerts': len(self.active_alerts),
            'alerts_by_type': self.stats['alerts_by_type'].copy(),
            'alerts_by_level': self.stats['alerts_by_level'].copy(),
            'emergency_stops': self.stats['alerts_by_type'].get('emergency_stop', 0),
            'collision_detections': self.stats['alerts_by_type'].get('collision_detected', 0),
            'system_health': self.system_health,
            'safety_score': self._calculate_safety_score()
        }
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while not self.stop_monitoring.is_set():
            try:
                current_time = time.time()
                
                # Check communication timeout
                if (current_time - self.communication_last_seen > 
                    self.safety_thresholds['communication_timeout']):
                    self._trigger_alert(
                        SafetyEventType.COMMUNICATION_LOST,
                        SafetyLevel.CRITICAL,
                        "Communication timeout detected",
                        "safety_monitor",
                        {"last_seen": self.communication_last_seen}
                    )
                
                # Check alert escalation
                self._check_alert_escalation()
                
                # Process alert queue
                self._process_alert_queue()
                
                # Clean up old alerts
                self._cleanup_old_alerts()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Monitoring loop error: {e}")
                time.sleep(self.check_interval)
    
    def _trigger_alert(self,
                      event_type: SafetyEventType,
                      level: SafetyLevel,
                      message: str,
                      source: str,
                      data: Dict[str, Any]) -> str:
        """Trigger a safety alert"""
        try:
            alert_id = f"alert_{self.alert_counter:06d}"
            self.alert_counter += 1
            
            alert = SafetyAlert(
                alert_id=alert_id,
                timestamp=time.time(),
                event_type=event_type,
                level=level,
                message=message,
                source=source,
                data=data
            )
            
            self.active_alerts.append(alert)
            self.alert_queue.put(alert)
            
            # Update statistics
            self.stats['total_alerts'] += 1
            event_key = event_type.value
            level_key = level.value
            
            self.stats['alerts_by_type'][event_key] = (
                self.stats['alerts_by_type'].get(event_key, 0) + 1
            )
            self.stats['alerts_by_level'][level_key] = (
                self.stats['alerts_by_level'].get(level_key, 0) + 1
            )
            
            # Immediate action for emergency level
            if level == SafetyLevel.EMERGENCY:
                self.trigger_emergency_stop(f"Emergency alert: {message}")
            
            self.logger.warning(f"⚠️ Safety Alert [{level.value.upper()}]: {message}")
            return alert_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to trigger alert: {e}")
            return ""
    
    def _process_alert_queue(self) -> None:
        """Process queued alerts and notify callbacks"""
        try:
            while not self.alert_queue.empty():
                alert = self.alert_queue.get_nowait()
                
                # Notify all callbacks
                for callback in self.alert_callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        self.logger.error(f"❌ Alert callback error: {e}")
                        
        except queue.Empty:
            pass
        except Exception as e:
            self.logger.error(f"❌ Alert queue processing error: {e}")
    
    def _check_alert_escalation(self) -> None:
        """Check and perform alert escalation"""
        current_time = time.time()
        
        for alert in self.active_alerts:
            if alert.escalated or alert.acknowledged:
                continue
                
            escalation_time = self.escalation_rules.get(alert.level, 0.0)
            if escalation_time > 0 and (current_time - alert.timestamp) > escalation_time:
                # Escalate alert
                alert.escalated = True
                self._escalate_alert(alert)
    
    def _escalate_alert(self, alert: SafetyAlert) -> None:
        """Escalate an alert to higher level"""
        try:
            # Determine escalation level
            if alert.level == SafetyLevel.WARNING:
                new_level = SafetyLevel.DANGER
            elif alert.level == SafetyLevel.DANGER:
                new_level = SafetyLevel.CRITICAL
            elif alert.level == SafetyLevel.CRITICAL:
                new_level = SafetyLevel.EMERGENCY
            else:
                return  # No further escalation
            
            # Create escalated alert
            escalated_message = f"ESCALATED: {alert.message}"
            self._trigger_alert(
                alert.event_type,
                new_level,
                escalated_message,
                alert.source,
                {**alert.data, "escalated_from": alert.alert_id}
            )
            
            self.logger.warning(f"⚠️ Alert escalated: {alert.alert_id} → {new_level.value}")
            
        except Exception as e:
            self.logger.error(f"❌ Alert escalation error: {e}")
    
    def _resolve_alerts_by_type(self, event_type: SafetyEventType) -> None:
        """Resolve all alerts of a specific type"""
        alerts_to_resolve = [a for a in self.active_alerts if a.event_type == event_type]
        for alert in alerts_to_resolve:
            self.resolve_alert(alert.alert_id)
    
    def _cleanup_old_alerts(self) -> None:
        """Clean up old resolved alerts"""
        if len(self.alert_history) > self.max_history:
            # Keep only the most recent alerts
            self.alert_history = self.alert_history[-self.max_history:]
    
    def _calculate_safety_score(self) -> float:
        """Calculate overall safety score (0.0 to 1.0)"""
        if self.emergency_stop_active:
            return 0.0
            
        base_score = 1.0
        
        # Deduct for active alerts
        for alert in self.active_alerts:
            if alert.level == SafetyLevel.EMERGENCY:
                base_score -= 0.5
            elif alert.level == SafetyLevel.CRITICAL:
                base_score -= 0.3
            elif alert.level == SafetyLevel.DANGER:
                base_score -= 0.2
            elif alert.level == SafetyLevel.WARNING:
                base_score -= 0.1
        
        # Ensure score stays in valid range
        return max(0.0, min(1.0, base_score))
    
    def _create_fallback_logger(self):
        """Create fallback logger if Phase 4 integration not available"""
        logger = logging.getLogger("SafetyMonitor")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

# Validation function for Day 2
def validate_safety_monitor():
    """Validate safety monitor implementation"""
    print("🧪 Validating Safety Monitor...")
    
    try:
        # Initialize monitor
        monitor = SafetyMonitor()
        
        # Test alert triggering
        alert_id = monitor._trigger_alert(
            SafetyEventType.COLLISION_DETECTED,
            SafetyLevel.WARNING,
            "Test collision alert",
            "test_source",
            {"test": True}
        )
        assert alert_id, "Alert triggering failed"
        print("✅ Alert triggering working")
        
        # Test alert acknowledgment
        success = monitor.acknowledge_alert(alert_id)
        assert success, "Alert acknowledgment failed"
        print("✅ Alert acknowledgment working")
        
        # Test movement validation
        current_pos = np.array([250, 100, 300])
        target_pos = np.array([350, 200, 400])
        is_safe, reason = monitor.validate_movement(current_pos, target_pos)
        assert is_safe, f"Movement validation failed: {reason}"
        print("✅ Movement validation working")
        
        # Test safety status
        status = monitor.get_safety_status()
        assert hasattr(status, 'monitoring_active'), "Safety status failed"
        print("✅ Safety status reporting working")
        
        print("🎯 Safety Monitor validation successful!")
        return True
        
    except Exception as e:
        print(f"❌ Safety Monitor validation failed: {e}")
        return False

if __name__ == "__main__":
    validate_safety_monitor()
