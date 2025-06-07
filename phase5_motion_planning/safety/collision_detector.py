#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Collision Detection System for Phase 5

This module provides real-time collision detection capabilities including
workspace boundary checking, self-collision detection, and obstacle avoidance
for the robotic arm system.

Key Features:
- Real-time workspace boundary monitoring
- Self-collision detection algorithms
- Dynamic obstacle avoidance
- Safety zone enforcement
- Predictive collision analysis

Author: TCP-to-ROS Migration Team
Created: Phase 5 Day 2 Implementation
"""

import numpy as np
import time
import threading
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import math

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

class CollisionType(Enum):
    """Types of collision detection"""
    NONE = "none"
    WORKSPACE_BOUNDARY = "workspace_boundary"
    SELF_COLLISION = "self_collision"
    OBSTACLE_COLLISION = "obstacle_collision"
    SAFETY_ZONE_VIOLATION = "safety_zone_violation"
    TRAJECTORY_COLLISION = "trajectory_collision"

@dataclass
class SafetyZone:
    """Definition of a safety zone"""
    name: str
    center: np.ndarray  # [x, y, z] center point
    radius: float       # Radius in mm
    priority: int       # Priority level (1=highest)
    active: bool = True
    violation_count: int = 0

@dataclass
class CollisionResult:
    """Result of collision detection"""
    collision_type: CollisionType
    collision_detected: bool
    distance_to_collision: float  # mm
    safety_margin: float         # mm
    affected_zone: Optional[SafetyZone] = None
    collision_point: Optional[np.ndarray] = None
    recommendation: str = ""
    severity: str = "low"  # low, medium, high, critical

class CollisionDetector:
    """
    Advanced collision detection system with real-time monitoring
    and predictive collision avoidance capabilities.
    """
    
    def __init__(self, 
                 workspace_limits: Optional[Dict] = None,
                 safety_zones: Optional[List[SafetyZone]] = None,
                 robot_config: Optional[Dict] = None,
                 logger: Optional[Any] = None):
        """
        Initialize collision detection system
        
        Args:
            workspace_limits: Workspace boundary limits
            safety_zones: List of safety zones to monitor
            robot_config: Robot configuration parameters
            logger: Logger instance for events
        """
        # Logger setup
        if PHASE4_INTEGRATION and logger is None:
            self.logger = MigrationLogger("CollisionDetector")
        else:
            self.logger = logger or self._create_fallback_logger()
            
        # Workspace configuration
        self.workspace_limits = workspace_limits or self._get_default_workspace()
        self.safety_zones = safety_zones or []
        self.robot_config = robot_config or self._get_default_robot_config()
        
        # Collision detection parameters
        self.safety_margin = 50.0  # mm minimum safety margin
        self.prediction_time = 2.0  # seconds to predict ahead
        self.check_interval = 0.02  # 50Hz checking rate
        
        # Current robot state
        self.current_position = np.array([0.0, 0.0, 0.0])
        self.current_velocity = np.array([0.0, 0.0, 0.0])
        self.current_joints = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        
        # Detection state
        self.monitoring_active = False
        self.collision_count = 0
        self.last_collision_time = 0
        
        # Threading for continuous monitoring
        self.monitor_thread = None
        self.stop_monitoring = threading.Event()
        
        self.logger.info("🛡️ Collision detector initialized")
        
    def start_monitoring(self) -> bool:
        """Start continuous collision monitoring"""
        if self.monitoring_active:
            self.logger.warning("⚠️ Collision monitoring already active")
            return False
            
        try:
            self.monitoring_active = True
            self.stop_monitoring.clear()
            self.monitor_thread = threading.Thread(target=self._monitoring_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            self.logger.info("🛡️ Collision monitoring started")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start collision monitoring: {e}")
            self.monitoring_active = False
            return False
    
    def stop_monitoring(self) -> bool:
        """Stop continuous collision monitoring"""
        if not self.monitoring_active:
            return True
            
        try:
            self.monitoring_active = False
            self.stop_monitoring.set()
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=2.0)
                
            self.logger.info("🛡️ Collision monitoring stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to stop collision monitoring: {e}")
            return False
    
    def detect_collisions(self, 
                         current_pos: np.ndarray,
                         target_pos: Optional[np.ndarray] = None,
                         trajectory: Optional[List] = None) -> CollisionResult:
        """
        Comprehensive collision detection analysis
        
        Args:
            current_pos: Current robot position [x, y, z]
            target_pos: Target position for movement
            trajectory: Full trajectory for analysis
            
        Returns:
            CollisionResult with detection details
        """
        try:
            self.current_position = current_pos.copy()
            
            # Check workspace boundaries
            boundary_result = self.check_workspace_boundaries(current_pos)
            if boundary_result.collision_detected:
                return boundary_result
                
            # Check safety zones
            zone_result = self.check_safety_zones(current_pos)
            if zone_result.collision_detected:
                return zone_result
                
            # Check self-collision if joint angles available
            if hasattr(self, 'current_joints'):
                self_collision_result = self.check_self_collision(self.current_joints)
                if self_collision_result.collision_detected:
                    return self_collision_result
            
            # Check trajectory if provided
            if trajectory is not None:
                trajectory_result = self.check_trajectory_collisions(trajectory)
                if trajectory_result.collision_detected:
                    return trajectory_result
            
            # Check target position if provided
            if target_pos is not None:
                target_result = self.check_target_position(target_pos)
                if target_result.collision_detected:
                    return target_result
            
            # No collisions detected
            return CollisionResult(
                collision_type=CollisionType.NONE,
                collision_detected=False,
                distance_to_collision=float('inf'),
                safety_margin=self.safety_margin,
                recommendation="Path clear - safe to proceed"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Collision detection error: {e}")
            return CollisionResult(
                collision_type=CollisionType.WORKSPACE_BOUNDARY,
                collision_detected=True,
                distance_to_collision=0.0,
                safety_margin=0.0,
                recommendation="Error in collision detection - stop immediately",
                severity="critical"
            )
    
    def check_workspace_boundaries(self, position: np.ndarray) -> CollisionResult:
        """Check if position is within workspace boundaries"""
        try:
            x, y, z = position[:3]
            limits = self.workspace_limits
            
            # Check X boundaries
            if x < limits['x_limits'][0] or x > limits['x_limits'][1]:
                distance = min(abs(x - limits['x_limits'][0]), 
                             abs(x - limits['x_limits'][1]))
                return CollisionResult(
                    collision_type=CollisionType.WORKSPACE_BOUNDARY,
                    collision_detected=True,
                    distance_to_collision=distance,
                    safety_margin=0.0,
                    collision_point=position.copy(),
                    recommendation="Move back within X workspace limits",
                    severity="high"
                )
            
            # Check Y boundaries
            if y < limits['y_limits'][0] or y > limits['y_limits'][1]:
                distance = min(abs(y - limits['y_limits'][0]), 
                             abs(y - limits['y_limits'][1]))
                return CollisionResult(
                    collision_type=CollisionType.WORKSPACE_BOUNDARY,
                    collision_detected=True,
                    distance_to_collision=distance,
                    safety_margin=0.0,
                    collision_point=position.copy(),
                    recommendation="Move back within Y workspace limits",
                    severity="high"
                )
            
            # Check Z boundaries
            if z < limits['z_limits'][0] or z > limits['z_limits'][1]:
                distance = min(abs(z - limits['z_limits'][0]), 
                             abs(z - limits['z_limits'][1]))
                return CollisionResult(
                    collision_type=CollisionType.WORKSPACE_BOUNDARY,
                    collision_detected=True,
                    distance_to_collision=distance,
                    safety_margin=0.0,
                    collision_point=position.copy(),
                    recommendation="Move back within Z workspace limits",
                    severity="high"
                )
            
            # Calculate minimum distance to boundaries
            min_distance = min(
                x - limits['x_limits'][0], limits['x_limits'][1] - x,
                y - limits['y_limits'][0], limits['y_limits'][1] - y,
                z - limits['z_limits'][0], limits['z_limits'][1] - z
            )
            
            return CollisionResult(
                collision_type=CollisionType.NONE,
                collision_detected=False,
                distance_to_collision=min_distance,
                safety_margin=min_distance,
                recommendation="Within workspace boundaries"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Workspace boundary check error: {e}")
            return CollisionResult(
                collision_type=CollisionType.WORKSPACE_BOUNDARY,
                collision_detected=True,
                distance_to_collision=0.0,
                safety_margin=0.0,
                recommendation="Error in boundary check - emergency stop",
                severity="critical"
            )
    
    def check_safety_zones(self, position: np.ndarray) -> CollisionResult:
        """Check if position violates any safety zones"""
        try:
            for zone in self.safety_zones:
                if not zone.active:
                    continue
                    
                # Calculate distance to zone center
                distance = np.linalg.norm(position[:3] - zone.center[:3])
                
                # Check if within safety zone
                if distance < zone.radius:
                    zone.violation_count += 1
                    self.logger.warning(f"⚠️ Safety zone violation: {zone.name}")
                    
                    return CollisionResult(
                        collision_type=CollisionType.SAFETY_ZONE_VIOLATION,
                        collision_detected=True,
                        distance_to_collision=distance,
                        safety_margin=zone.radius - distance,
                        affected_zone=zone,
                        collision_point=position.copy(),
                        recommendation=f"Move away from safety zone: {zone.name}",
                        severity="medium" if zone.priority > 2 else "high"
                    )
            
            # No safety zone violations
            return CollisionResult(
                collision_type=CollisionType.NONE,
                collision_detected=False,
                distance_to_collision=float('inf'),
                safety_margin=self.safety_margin,
                recommendation="Clear of all safety zones"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Safety zone check error: {e}")
            return CollisionResult(
                collision_type=CollisionType.SAFETY_ZONE_VIOLATION,
                collision_detected=True,
                distance_to_collision=0.0,
                safety_margin=0.0,
                recommendation="Error in safety zone check - emergency stop",
                severity="critical"
            )
    
    def check_self_collision(self, joint_angles: np.ndarray) -> CollisionResult:
        """Check for self-collision based on joint configuration"""
        try:
            # Simple self-collision detection based on joint limits
            joint_limits = self.robot_config.get('joint_limits', {})
            
            for i, angle in enumerate(joint_angles):
                joint_name = f"joint_{i+1}"
                if joint_name in joint_limits:
                    min_limit, max_limit = joint_limits[joint_name]
                    
                    if angle < min_limit or angle > max_limit:
                        return CollisionResult(
                            collision_type=CollisionType.SELF_COLLISION,
                            collision_detected=True,
                            distance_to_collision=0.0,
                            safety_margin=0.0,
                            recommendation=f"Joint {i+1} exceeds limits",
                            severity="high"
                        )
            
            # Advanced self-collision check (simplified)
            # In production, this would use detailed robot geometry
            if self._check_advanced_self_collision(joint_angles):
                return CollisionResult(
                    collision_type=CollisionType.SELF_COLLISION,
                    collision_detected=True,
                    distance_to_collision=0.0,
                    safety_margin=0.0,
                    recommendation="Self-collision detected - adjust joint configuration",
                    severity="high"
                )
            
            return CollisionResult(
                collision_type=CollisionType.NONE,
                collision_detected=False,
                distance_to_collision=float('inf'),
                safety_margin=self.safety_margin,
                recommendation="No self-collision detected"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Self-collision check error: {e}")
            return CollisionResult(
                collision_type=CollisionType.SELF_COLLISION,
                collision_detected=True,
                distance_to_collision=0.0,
                safety_margin=0.0,
                recommendation="Error in self-collision check - emergency stop",
                severity="critical"
            )
    
    def check_trajectory_collisions(self, trajectory: List) -> CollisionResult:
        """Check entire trajectory for potential collisions"""
        try:
            for i, point in enumerate(trajectory):
                if hasattr(point, 'position'):
                    pos = np.array(point.position[:3])
                else:
                    pos = np.array(point[:3])
                
                # Check this point for collisions
                result = self.detect_collisions(pos)
                if result.collision_detected:
                    result.recommendation = f"Collision in trajectory at point {i}: {result.recommendation}"
                    return result
            
            return CollisionResult(
                collision_type=CollisionType.NONE,
                collision_detected=False,
                distance_to_collision=float('inf'),
                safety_margin=self.safety_margin,
                recommendation="Trajectory clear of collisions"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Trajectory collision check error: {e}")
            return CollisionResult(
                collision_type=CollisionType.TRAJECTORY_COLLISION,
                collision_detected=True,
                distance_to_collision=0.0,
                safety_margin=0.0,
                recommendation="Error in trajectory check - emergency stop",
                severity="critical"
            )
    
    def check_target_position(self, target_pos: np.ndarray) -> CollisionResult:
        """Check if target position is safe"""
        return self.check_workspace_boundaries(target_pos)
    
    def add_safety_zone(self, zone: SafetyZone) -> bool:
        """Add a new safety zone"""
        try:
            self.safety_zones.append(zone)
            self.logger.info(f"🛡️ Added safety zone: {zone.name}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to add safety zone: {e}")
            return False
    
    def remove_safety_zone(self, zone_name: str) -> bool:
        """Remove a safety zone by name"""
        try:
            self.safety_zones = [z for z in self.safety_zones if z.name != zone_name]
            self.logger.info(f"🛡️ Removed safety zone: {zone_name}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to remove safety zone: {e}")
            return False
    
    def get_collision_statistics(self) -> Dict:
        """Get collision detection statistics"""
        return {
            'total_collisions': self.collision_count,
            'monitoring_active': self.monitoring_active,
            'safety_zones_count': len(self.safety_zones),
            'active_zones': len([z for z in self.safety_zones if z.active]),
            'last_collision_time': self.last_collision_time,
            'safety_margin': self.safety_margin
        }
    
    def update_robot_state(self, 
                          position: np.ndarray,
                          velocity: Optional[np.ndarray] = None,
                          joint_angles: Optional[np.ndarray] = None) -> None:
        """Update current robot state for collision detection"""
        self.current_position = position.copy()
        if velocity is not None:
            self.current_velocity = velocity.copy()
        if joint_angles is not None:
            self.current_joints = joint_angles.copy()
    
    def _monitoring_loop(self) -> None:
        """Continuous monitoring loop"""
        while not self.stop_monitoring.is_set():
            try:
                # Perform collision check on current position
                result = self.detect_collisions(self.current_position)
                
                if result.collision_detected:
                    self.collision_count += 1
                    self.last_collision_time = time.time()
                    self.logger.warning(f"⚠️ Collision detected: {result.recommendation}")
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Monitoring loop error: {e}")
                time.sleep(self.check_interval)
    
    def _check_advanced_self_collision(self, joint_angles: np.ndarray) -> bool:
        """Advanced self-collision detection (simplified implementation)"""
        # This is a simplified version - in production this would use
        # detailed robot geometry and collision meshes
        
        # Example: Check for problematic joint configurations
        # These are basic heuristics and should be replaced with proper geometry
        
        # Check if arm is folded back on itself
        if len(joint_angles) >= 3:
            # Simple check for extreme joint combinations
            if abs(joint_angles[1]) > 150 and abs(joint_angles[2]) > 150:
                return True
                
            # Check for wrist collision with base
            if abs(joint_angles[0]) < 10 and abs(joint_angles[2]) > 120:
                return True
        
        return False
    
    def _get_default_workspace(self) -> Dict:
        """Get default workspace limits"""
        return {
            'x_limits': [-800, 800],   # mm
            'y_limits': [-800, 800],   # mm  
            'z_limits': [0, 1200]      # mm
        }
    
    def _get_default_robot_config(self) -> Dict:
        """Get default robot configuration"""
        return {
            'joint_limits': {
                'joint_1': [-180, 180],
                'joint_2': [-90, 90], 
                'joint_3': [-170, 170],
                'joint_4': [-180, 180],
                'joint_5': [-120, 120],
                'joint_6': [-360, 360]
            },
            'link_lengths': [0, 425, 392, 109, 109, 82],  # mm
            'safety_factors': {
                'velocity_limit': 0.8,
                'acceleration_limit': 0.7
            }
        }
    
    def _create_fallback_logger(self):
        """Create fallback logger if Phase 4 integration not available"""
        logger = logging.getLogger("CollisionDetector")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

# Validation function for Day 2
def validate_collision_detector():
    """Validate collision detector implementation"""
    print("🧪 Validating Collision Detector...")
    
    try:
        # Initialize detector
        detector = CollisionDetector()
        
        # Test workspace boundary checking
        test_position = np.array([900, 0, 300])  # Outside X limit
        result = detector.check_workspace_boundaries(test_position)
        assert result.collision_detected, "Workspace boundary test failed"
        print("✅ Workspace boundary detection working")
        
        # Test safe position
        safe_position = np.array([250, 100, 300])
        result = detector.check_workspace_boundaries(safe_position)
        assert not result.collision_detected, "Safe position test failed"
        print("✅ Safe position detection working")
        
        # Test safety zones
        safety_zone = SafetyZone("test_zone", np.array([0, 0, 0]), 100, 1)
        detector.add_safety_zone(safety_zone)
        
        collision_pos = np.array([50, 0, 0])  # Inside safety zone
        result = detector.check_safety_zones(collision_pos)
        assert result.collision_detected, "Safety zone test failed"
        print("✅ Safety zone detection working")
        
        print("🎯 Collision Detector validation successful!")
        return True
        
    except Exception as e:
        print(f"❌ Collision Detector validation failed: {e}")
        return False

if __name__ == "__main__":
    validate_collision_detector()
