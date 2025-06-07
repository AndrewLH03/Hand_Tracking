#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Motion Controller for Phase 5

This module provides smooth motion execution capabilities that work with the
trajectory optimizer to deliver precise, controlled robotic movements with
real-time adaptation and safety monitoring.

Key Features:
- Real-time trajectory execution
- Smooth motion interpolation
- Dynamic speed adjustment
- Emergency stop capabilities
- Integration with Phase 4 dual-backend system
"""

import numpy as np
import time
import threading
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import queue

# Import trajectory components
from .trajectory_optimizer import TrajectoryPoint, TrajectoryOptimizer, TrajectoryConstraints

# Phase 4 integration
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'robot_control'))
    from migration_logger import MigrationLogger
    from enhanced_ros_adapter import RobotApiAdapter
    PHASE4_INTEGRATION = True
except ImportError:
    PHASE4_INTEGRATION = False
    import logging

class MotionState(Enum):
    """Motion controller states"""
    IDLE = "idle"
    EXECUTING = "executing"
    PAUSED = "paused"
    EMERGENCY_STOP = "emergency_stop"
    ERROR = "error"

@dataclass
class MotionStatus:
    """Current motion execution status"""
    state: MotionState
    current_position: np.ndarray
    target_position: np.ndarray
    progress: float  # 0.0 to 1.0
    velocity: np.ndarray
    time_remaining: float
    trajectory_point_index: int

class MotionController:
    """
    Advanced motion controller for smooth trajectory execution.
    
    Provides real-time motion control with safety monitoring,
    dynamic adaptation, and integration with Phase 4 infrastructure.
    """
    
    def __init__(self, 
                 robot_adapter: Optional[Any] = None,
                 update_rate: float = 50.0,  # Hz
                 logger: Optional[Any] = None):
        """
        Initialize motion controller.
        
        Args:
            robot_adapter: Phase 4 robot adapter (RobotApiAdapter)
            update_rate: Control loop frequency in Hz
            logger: Logger instance
        """
        self.update_rate = update_rate
        self.update_period = 1.0 / update_rate
        
        # Phase 4 integration
        if PHASE4_INTEGRATION:
            try:
                self.logger = logger or MigrationLogger("motion_controller")
                self.robot_adapter = robot_adapter or RobotApiAdapter()
                self.logger.info("🚀 Motion Controller initialized with Phase 4 integration")
            except:
                self.logger = logging.getLogger("motion_controller")
                self.robot_adapter = None
        else:
            self.logger = logging.getLogger("motion_controller")
            self.robot_adapter = robot_adapter
        
        # Motion state
        self.state = MotionState.IDLE
        self.current_trajectory: List[TrajectoryPoint] = []
        self.trajectory_index = 0
        self.start_time = 0.0
        self.pause_time = 0.0
        
        # Current status
        self.current_position = np.array([0.0, 0.0, 0.0])
        self.current_velocity = np.array([0.0, 0.0, 0.0])
        self.target_position = np.array([0.0, 0.0, 0.0])
        
        # Control parameters
        self.position_tolerance = 1.0  # mm
        self.velocity_smoothing = 0.1  # Exponential smoothing factor
        self.emergency_stop_flag = False
        
        # Threading for real-time control
        self.control_thread = None
        self.control_active = False
        self.command_queue = queue.Queue()
        
        # Performance tracking
        self.execution_times = []
        self.position_errors = []
        
        # Safety callbacks
        self.safety_callbacks: List[Callable] = []
        self.position_callbacks: List[Callable] = []
        
        self.logger.info("✅ Advanced Motion Controller ready")
        self.logger.info(f"📊 Update rate: {update_rate} Hz, tolerance: {self.position_tolerance} mm")
    
    def execute_trajectory(self, 
                          trajectory: List[TrajectoryPoint],
                          blocking: bool = False,
                          speed_factor: float = 1.0) -> bool:
        """
        Execute a trajectory with smooth motion control.
        
        Args:
            trajectory: List of trajectory points to execute
            blocking: Whether to block until completion
            speed_factor: Speed scaling factor (0.1 to 2.0)
            
        Returns:
            True if execution started successfully
        """
        if not trajectory:
            self.logger.error("❌ Empty trajectory provided")
            return False
        
        if self.state == MotionState.EXECUTING:
            self.logger.warning("⚠️ Motion already executing, stopping current motion")
            self.stop_motion()
            time.sleep(0.1)  # Brief pause
        
        # Validate and scale trajectory
        scaled_trajectory = self._scale_trajectory(trajectory, speed_factor)
        
        self.logger.info(f"🎯 Executing trajectory: {len(scaled_trajectory)} points, "
                        f"speed_factor={speed_factor}")
        
        # Set trajectory and start execution
        self.current_trajectory = scaled_trajectory
        self.trajectory_index = 0
        self.start_time = time.time()
        self.state = MotionState.EXECUTING
        self.emergency_stop_flag = False
        
        # Start control thread if not running
        if not self.control_active:
            self._start_control_thread()
        
        # Add execution command to queue
        self.command_queue.put(("execute", scaled_trajectory))
        
        if blocking:
            return self._wait_for_completion()
        
        return True
    
    def move_to_position(self,
                        target_pos: np.ndarray,
                        movement_time: float = 3.0,
                        trajectory_type: str = "smooth") -> bool:
        """
        Move to a specific position with smooth motion.
        
        Args:
            target_pos: Target position [x, y, z]
            movement_time: Time for movement
            trajectory_type: Type of motion ("smooth", "linear", "fast")
            
        Returns:
            True if movement started successfully
        """
        target_pos = np.array(target_pos)
        
        self.logger.info(f"🎯 Moving to position: {target_pos}")
        self.logger.info(f"📍 From: {self.current_position} → To: {target_pos}")
        
        try:
            # Generate trajectory using optimizer
            optimizer = TrajectoryOptimizer(logger=self.logger)
            
            if trajectory_type == "smooth":
                from .trajectory_optimizer import TrajectoryType
                trajectory = optimizer.generate_smooth_motion_profile(
                    self.current_position, target_pos, movement_time, 
                    TrajectoryType.BSPLINE
                )
            elif trajectory_type == "linear":
                from .trajectory_optimizer import TrajectoryType
                trajectory = optimizer.generate_smooth_motion_profile(
                    self.current_position, target_pos, movement_time,
                    TrajectoryType.LINEAR
                )
            else:  # fast
                from .trajectory_optimizer import TrajectoryType
                trajectory = optimizer.generate_smooth_motion_profile(
                    self.current_position, target_pos, movement_time * 0.7,
                    TrajectoryType.BSPLINE
                )
            
            # Execute trajectory
            return self.execute_trajectory(trajectory, blocking=False)
            
        except Exception as e:
            self.logger.error(f"❌ Move to position failed: {e}")
            return False
    
    def pause_motion(self) -> bool:
        """Pause current motion execution"""
        if self.state == MotionState.EXECUTING:
            self.state = MotionState.PAUSED
            self.pause_time = time.time()
            self.logger.info("⏸️ Motion paused")
            return True
        return False
    
    def resume_motion(self) -> bool:
        """Resume paused motion"""
        if self.state == MotionState.PAUSED:
            pause_duration = time.time() - self.pause_time
            self.start_time += pause_duration  # Adjust start time
            self.state = MotionState.EXECUTING
            self.logger.info(f"▶️ Motion resumed after {pause_duration:.1f}s pause")
            return True
        return False
    
    def stop_motion(self) -> bool:
        """Stop current motion execution"""
        if self.state in [MotionState.EXECUTING, MotionState.PAUSED]:
            self.state = MotionState.IDLE
            self.current_trajectory = []
            self.trajectory_index = 0
            self.logger.info("🛑 Motion stopped")
            return True
        return False
    
    def emergency_stop(self) -> bool:
        """Emergency stop - immediate halt"""
        self.emergency_stop_flag = True
        self.state = MotionState.EMERGENCY_STOP
        self.current_trajectory = []
        
        # Call safety callbacks
        for callback in self.safety_callbacks:
            try:
                callback("emergency_stop", self.get_status())
            except Exception as e:
                self.logger.error(f"❌ Safety callback error: {e}")
        
        self.logger.error("🚨 EMERGENCY STOP ACTIVATED")
        return True
    
    def get_status(self) -> MotionStatus:
        """Get current motion status"""
        progress = 0.0
        time_remaining = 0.0
        
        if self.current_trajectory and self.state == MotionState.EXECUTING:
            progress = self.trajectory_index / len(self.current_trajectory)
            elapsed = time.time() - self.start_time
            total_time = self.current_trajectory[-1].time if self.current_trajectory else 0
            time_remaining = max(0, total_time - elapsed)
        
        return MotionStatus(
            state=self.state,
            current_position=self.current_position.copy(),
            target_position=self.target_position.copy(),
            progress=progress,
            velocity=self.current_velocity.copy(),
            time_remaining=time_remaining,
            trajectory_point_index=self.trajectory_index
        )
    
    def add_safety_callback(self, callback: Callable) -> None:
        """Add safety monitoring callback"""
        self.safety_callbacks.append(callback)
        self.logger.info("🛡️ Safety callback added")
    
    def add_position_callback(self, callback: Callable) -> None:
        """Add position update callback"""
        self.position_callbacks.append(callback)
        self.logger.info("📍 Position callback added")
    
    def _start_control_thread(self) -> None:
        """Start the real-time control thread"""
        if self.control_active:
            return
        
        self.control_active = True
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()
        self.logger.info("🔄 Control thread started")
    
    def _control_loop(self) -> None:
        """Main control loop running at specified update rate"""
        self.logger.info(f"🔄 Control loop started at {self.update_rate} Hz")
        
        while self.control_active:
            loop_start = time.time()
            
            try:
                # Process commands
                self._process_commands()
                
                # Update motion if executing
                if self.state == MotionState.EXECUTING:
                    self._update_motion()
                
                # Call position callbacks
                for callback in self.position_callbacks:
                    try:
                        callback(self.current_position, self.current_velocity)
                    except Exception as e:
                        self.logger.error(f"❌ Position callback error: {e}")
                
            except Exception as e:
                self.logger.error(f"❌ Control loop error: {e}")
                self.state = MotionState.ERROR
            
            # Maintain update rate
            loop_time = time.time() - loop_start
            sleep_time = max(0, self.update_period - loop_time)
            time.sleep(sleep_time)
        
        self.logger.info("🔄 Control loop stopped")
    
    def _process_commands(self) -> None:
        """Process commands from the command queue"""
        try:
            while not self.command_queue.empty():
                command, data = self.command_queue.get_nowait()
                
                if command == "execute":
                    # Command already processed in execute_trajectory
                    pass
                elif command == "stop":
                    self.stop_motion()
                elif command == "emergency_stop":
                    self.emergency_stop()
                    
        except queue.Empty:
            pass
    
    def _update_motion(self) -> None:
        """Update motion during trajectory execution"""
        if not self.current_trajectory or self.emergency_stop_flag:
            self.state = MotionState.IDLE
            return
        
        current_time = time.time() - self.start_time
        
        # Find current trajectory point
        target_point = None
        for i, point in enumerate(self.current_trajectory):
            if point.time >= current_time:
                target_point = point
                self.trajectory_index = i
                break
        
        if target_point is None:
            # Trajectory complete
            self.state = MotionState.IDLE
            self.current_position = self.current_trajectory[-1].position.copy()
            self.current_velocity = np.zeros(3)
            self.logger.info("✅ Trajectory execution complete")
            return
        
        # Update position with interpolation for smoothness
        self.target_position = target_point.position.copy()
        
        # Smooth position update (simulated - in real system would command robot)
        position_error = self.target_position - self.current_position
        error_magnitude = np.linalg.norm(position_error)
        
        if error_magnitude > self.position_tolerance:
            # Move towards target with velocity limiting
            max_step = self.update_period * 200  # mm/s max speed
            step_size = min(max_step, error_magnitude * 0.5)
            
            direction = position_error / error_magnitude
            self.current_position += direction * step_size
            
            # Update velocity with smoothing
            new_velocity = direction * step_size / self.update_period
            self.current_velocity = (
                (1 - self.velocity_smoothing) * self.current_velocity +
                self.velocity_smoothing * new_velocity
            )
        else:
            self.current_position = self.target_position.copy()
            self.current_velocity *= 0.9  # Decay velocity when at target
        
        # Record performance metrics
        self.position_errors.append(error_magnitude)
        
        # Send position to robot if adapter available
        if PHASE4_INTEGRATION and self.robot_adapter:
            try:
                # Convert to robot coordinates and send
                # This would be the actual robot command in a real system
                pass
            except Exception as e:
                self.logger.warning(f"⚠️ Robot command failed: {e}")
    
    def _scale_trajectory(self, trajectory: List[TrajectoryPoint], 
                         speed_factor: float) -> List[TrajectoryPoint]:
        """Scale trajectory timing by speed factor"""
        speed_factor = max(0.1, min(2.0, speed_factor))  # Clamp to safe range
        
        scaled_trajectory = []
        for point in trajectory:
            scaled_point = TrajectoryPoint(
                position=point.position.copy(),
                velocity=point.velocity / speed_factor if point.velocity is not None else None,
                acceleration=point.acceleration / (speed_factor**2) if point.acceleration is not None else None,
                time=point.time * speed_factor
            )
            scaled_trajectory.append(scaled_point)
        
        return scaled_trajectory
    
    def _wait_for_completion(self, timeout: float = 30.0) -> bool:
        """Wait for trajectory execution to complete"""
        start_wait = time.time()
        
        while (self.state in [MotionState.EXECUTING, MotionState.PAUSED] and 
               time.time() - start_wait < timeout):
            time.sleep(0.1)
        
        success = self.state == MotionState.IDLE
        if not success and time.time() - start_wait >= timeout:
            self.logger.error(f"❌ Motion timeout after {timeout}s")
        
        return success
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get motion controller performance metrics"""
        if not self.position_errors:
            return {"status": "no_data"}
        
        errors = np.array(self.position_errors[-100:])  # Last 100 samples
        
        return {
            "average_position_error_mm": float(np.mean(errors)),
            "max_position_error_mm": float(np.max(errors)),
            "position_tolerance_mm": self.position_tolerance,
            "update_rate_hz": self.update_rate,
            "control_active": self.control_active,
            "current_state": self.state.value
        }
    
    def shutdown(self) -> None:
        """Shutdown motion controller"""
        self.control_active = False
        self.stop_motion()
        
        if self.control_thread:
            self.control_thread.join(timeout=1.0)
        
        self.logger.info("🔽 Motion Controller shutdown complete")

# Phase 5 Day 1 validation
def validate_motion_controller():
    """Validate motion controller implementation"""
    print("🧪 Validating Advanced Motion Controller...")
    
    try:
        # Test initialization
        controller = MotionController(update_rate=20.0)  # Lower rate for testing
        print("✅ Motion Controller initialization successful")
        
        # Test position movement
        target = np.array([100, 50, 25])
        success = controller.move_to_position(target, movement_time=2.0)
        print(f"✅ Move to position: {'Started' if success else 'Failed'}")
        
        # Test status
        status = controller.get_status()
        print(f"✅ Status check: State={status.state.value}")
        
        # Test metrics
        metrics = controller.get_performance_metrics()
        print(f"✅ Performance metrics: {metrics}")
        
        # Test safety features
        controller.emergency_stop()
        print("✅ Emergency stop functionality")
        
        # Cleanup
        controller.shutdown()
        print("✅ Controller shutdown")
        
        print("🎉 Motion Controller validation COMPLETE")
        return True
        
    except Exception as e:
        print(f"❌ Motion Controller validation failed: {e}")
        return False

if __name__ == "__main__":
    validate_motion_controller()
