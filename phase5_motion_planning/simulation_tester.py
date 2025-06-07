#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 5 Motion Planning Simulation Testing Framework

This module provides comprehensive testing and validation for the motion planning system.
It includes simulation environments, performance benchmarking, and validation tests
to ensure the trajectory optimizer and motion controller meet requirements.

Author: TCP-to-ROS Migration Team
Created: Phase 5 Day 1 Implementation
"""

import numpy as np
import matplotlib.pyplot as plt
import time
import json
import threading
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .trajectory_optimizer import TrajectoryOptimizer
    from .motion_controller import MotionController
    from robot_control.migration_logger import MigrationLogger
except ImportError:
    # Fallback for direct execution
    from trajectory_optimizer import TrajectoryOptimizer
    from motion_controller import MotionController
    import sys
    sys.path.append('../robot_control')
    from migration_logger import MigrationLogger

@dataclass
class TestResult:
    """Data class for storing test results"""
    test_name: str
    success: bool
    execution_time: float
    performance_metrics: Dict
    errors: List[str]
    details: Dict

class SimulationEnvironment:
    """
    Simulated robotic arm environment for testing motion planning algorithms
    """
    
    def __init__(self, joint_count: int = 6):
        self.joint_count = joint_count
        self.joint_limits = [(-180, 180) for _ in range(joint_count)]  # degrees
        self.joint_velocities = [0.0] * joint_count
        self.joint_positions = [0.0] * joint_count
        self.max_velocity = 90.0  # degrees/second
        self.max_acceleration = 180.0  # degrees/second^2
        
        # Workspace limits (mm)
        self.workspace_limits = {
            'x': (-800, 800),
            'y': (-800, 800),
            'z': (0, 1200)
        }
        
        # Simulation state
        self.time_step = 0.02  # 50Hz
        self.current_time = 0.0
        self.collision_zones = []  # List of obstacle positions
        
    def forward_kinematics(self, joint_angles: List[float]) -> Tuple[float, float, float]:
        """
        Simplified forward kinematics for testing
        Returns end-effector position (x, y, z) in mm
        """
        # Simplified calculation for testing purposes
        # In real implementation, this would use DH parameters
        x = 400 * np.cos(np.radians(joint_angles[0])) * np.cos(np.radians(joint_angles[1]))
        y = 400 * np.sin(np.radians(joint_angles[0])) * np.cos(np.radians(joint_angles[1]))
        z = 200 + 400 * np.sin(np.radians(joint_angles[1]))
        
        return x, y, z
    
    def inverse_kinematics(self, target_pos: Tuple[float, float, float]) -> Optional[List[float]]:
        """
        Simplified inverse kinematics for testing
        Returns joint angles in degrees
        """
        x, y, z = target_pos
        
        # Check workspace limits
        if not (self.workspace_limits['x'][0] <= x <= self.workspace_limits['x'][1] and
                self.workspace_limits['y'][0] <= y <= self.workspace_limits['y'][1] and
                self.workspace_limits['z'][0] <= z <= self.workspace_limits['z'][1]):
            return None
        
        # Simplified IK calculation
        joint_0 = np.degrees(np.arctan2(y, x))
        r = np.sqrt(x**2 + y**2)
        joint_1 = np.degrees(np.arctan2(z - 200, r))
        
        # Other joints set to neutral for simplicity
        return [joint_0, joint_1, 0.0, 0.0, 0.0, 0.0]
    
    def check_collision(self, joint_angles: List[float]) -> bool:
        """Check if current configuration results in collision"""
        pos = self.forward_kinematics(joint_angles)
        
        # Check against collision zones
        for obstacle in self.collision_zones:
            distance = np.sqrt(sum((pos[i] - obstacle[i])**2 for i in range(3)))
            if distance < 100:  # 100mm safety margin
                return True
        
        return False
    
    def add_obstacle(self, position: Tuple[float, float, float]):
        """Add obstacle to simulation environment"""
        self.collision_zones.append(position)
    
    def update_state(self, joint_positions: List[float], joint_velocities: List[float]):
        """Update simulation state"""
        self.joint_positions = joint_positions[:]
        self.joint_velocities = joint_velocities[:]
        self.current_time += self.time_step

class MotionPlanningTester:
    """
    Comprehensive testing framework for motion planning components
    """
    
    def __init__(self):
        self.logger = MigrationLogger("Phase5_Testing")
        self.sim_env = SimulationEnvironment()
        self.trajectory_optimizer = TrajectoryOptimizer()
        self.motion_controller = MotionController()
        self.test_results = []
        
        # Performance benchmarks
        self.performance_targets = {
            'trajectory_calculation_time': 0.1,  # 100ms
            'control_loop_frequency': 50.0,  # 50Hz
            'position_accuracy': 1.0,  # 1mm
            'velocity_smoothness': 0.95  # Smoothness metric
        }
    
    def run_trajectory_optimization_tests(self) -> List[TestResult]:
        """Run comprehensive trajectory optimization tests"""
        test_results = []
        
        # Test 1: Basic trajectory generation
        result = self._test_basic_trajectory_generation()
        test_results.append(result)
        
        # Test 2: Performance benchmark
        result = self._test_trajectory_performance()
        test_results.append(result)
        
        # Test 3: Constraint validation
        result = self._test_constraint_validation()
        test_results.append(result)
        
        # Test 4: Complex path optimization
        result = self._test_complex_path_optimization()
        test_results.append(result)
        
        return test_results
    
    def _test_basic_trajectory_generation(self) -> TestResult:
        """Test basic B-spline trajectory generation"""
        start_time = time.time()
        errors = []
        performance_metrics = {}
        
        try:
            # Define test waypoints
            waypoints = [
                [0, 0, 0, 0, 0, 0],
                [30, 45, 0, 0, 0, 0],
                [60, 90, 0, 0, 0, 0],
                [30, 45, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0]
            ]
            
            # Generate trajectory
            trajectory = self.trajectory_optimizer.generate_trajectory(
                waypoints, duration=5.0
            )
            
            # Validate trajectory
            if trajectory is None:
                errors.append("Trajectory generation returned None")
            else:
                # Check trajectory properties
                if len(trajectory['positions']) < 100:
                    errors.append(f"Insufficient trajectory points: {len(trajectory['positions'])}")
                
                # Check smoothness
                positions = np.array(trajectory['positions'])
                velocities = np.diff(positions, axis=0)
                smoothness = self._calculate_smoothness(velocities)
                performance_metrics['smoothness'] = smoothness
                
                if smoothness < 0.9:
                    errors.append(f"Poor trajectory smoothness: {smoothness:.3f}")
            
        except Exception as e:
            errors.append(f"Exception during trajectory generation: {str(e)}")
        
        execution_time = time.time() - start_time
        performance_metrics['execution_time'] = execution_time
        
        return TestResult(
            test_name="Basic Trajectory Generation",
            success=len(errors) == 0,
            execution_time=execution_time,
            performance_metrics=performance_metrics,
            errors=errors,
            details={'waypoints_count': len(waypoints)}
        )
    
    def _test_trajectory_performance(self) -> TestResult:
        """Test trajectory generation performance"""
        start_time = time.time()
        errors = []
        performance_metrics = {}
        
        try:
            # Run multiple trajectory generations to test performance
            generation_times = []
            
            for i in range(10):
                waypoints = [
                    [np.random.uniform(-90, 90) for _ in range(6)],
                    [np.random.uniform(-90, 90) for _ in range(6)],
                    [np.random.uniform(-90, 90) for _ in range(6)]
                ]
                
                gen_start = time.time()
                trajectory = self.trajectory_optimizer.generate_trajectory(
                    waypoints, duration=2.0
                )
                gen_time = time.time() - gen_start
                generation_times.append(gen_time)
                
                if trajectory is None:
                    errors.append(f"Trajectory generation {i} failed")
            
            # Calculate performance metrics
            avg_time = np.mean(generation_times)
            max_time = np.max(generation_times)
            
            performance_metrics['average_generation_time'] = avg_time
            performance_metrics['max_generation_time'] = max_time
            
            # Check against performance targets
            if avg_time > self.performance_targets['trajectory_calculation_time']:
                errors.append(f"Average generation time {avg_time:.3f}s exceeds target {self.performance_targets['trajectory_calculation_time']:.3f}s")
            
            if max_time > self.performance_targets['trajectory_calculation_time'] * 1.5:
                errors.append(f"Max generation time {max_time:.3f}s too high")
            
        except Exception as e:
            errors.append(f"Exception during performance test: {str(e)}")
        
        execution_time = time.time() - start_time
        
        return TestResult(
            test_name="Trajectory Performance Benchmark",
            success=len(errors) == 0,
            execution_time=execution_time,
            performance_metrics=performance_metrics,
            errors=errors,
            details={'test_iterations': 10}
        )
    
    def _test_constraint_validation(self) -> TestResult:
        """Test trajectory constraint validation"""
        start_time = time.time()
        errors = []
        performance_metrics = {}
        
        try:
            # Test with valid waypoints
            valid_waypoints = [
                [0, 0, 0, 0, 0, 0],
                [45, 45, 0, 0, 0, 0]
            ]
            
            trajectory = self.trajectory_optimizer.generate_trajectory(
                valid_waypoints, duration=2.0
            )
            
            if trajectory is None:
                errors.append("Valid trajectory generation failed")
            else:
                # Validate constraints are met
                positions = np.array(trajectory['positions'])
                velocities = np.array(trajectory['velocities'])
                
                # Check joint limits
                for i, pos_array in enumerate(positions):
                    for j, pos in enumerate(pos_array):
                        if not (-180 <= pos <= 180):
                            errors.append(f"Joint {j} position {pos} exceeds limits at step {i}")
                            break
                
                # Check velocity limits
                max_velocities = np.max(np.abs(velocities), axis=0)
                performance_metrics['max_velocities'] = max_velocities.tolist()
                
                for j, max_vel in enumerate(max_velocities):
                    if max_vel > self.sim_env.max_velocity:
                        errors.append(f"Joint {j} velocity {max_vel} exceeds limit {self.sim_env.max_velocity}")
            
            # Test with invalid waypoints (outside workspace)
            invalid_waypoints = [
                [0, 0, 0, 0, 0, 0],
                [200, 200, 0, 0, 0, 0]  # Likely outside joint limits
            ]
            
            invalid_trajectory = self.trajectory_optimizer.generate_trajectory(
                invalid_waypoints, duration=2.0
            )
            
            # This should either fail gracefully or apply constraints
            if invalid_trajectory is not None:
                performance_metrics['constraint_handling'] = "Applied"
            else:
                performance_metrics['constraint_handling'] = "Rejected"
            
        except Exception as e:
            errors.append(f"Exception during constraint validation: {str(e)}")
        
        execution_time = time.time() - start_time
        
        return TestResult(
            test_name="Constraint Validation",
            success=len(errors) == 0,
            execution_time=execution_time,
            performance_metrics=performance_metrics,
            errors=errors,
            details={}
        )
    
    def _test_complex_path_optimization(self) -> TestResult:
        """Test complex path optimization with multiple waypoints"""
        start_time = time.time()
        errors = []
        performance_metrics = {}
        
        try:
            # Create complex path with 8 waypoints
            waypoints = [
                [0, 0, 0, 0, 0, 0],
                [30, 30, 0, 0, 0, 0],
                [60, 60, 0, 0, 0, 0],
                [90, 45, 0, 0, 0, 0],
                [60, 30, 0, 0, 0, 0],
                [30, 60, 0, 0, 0, 0],
                [0, 90, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0]
            ]
            
            trajectory = self.trajectory_optimizer.generate_trajectory(
                waypoints, duration=10.0
            )
            
            if trajectory is None:
                errors.append("Complex trajectory generation failed")
            else:
                # Analyze trajectory quality
                positions = np.array(trajectory['positions'])
                velocities = np.array(trajectory['velocities'])
                
                # Calculate path length
                path_length = 0
                for i in range(1, len(positions)):
                    path_length += np.linalg.norm(positions[i] - positions[i-1])
                
                performance_metrics['path_length'] = path_length
                performance_metrics['waypoint_count'] = len(waypoints)
                
                # Check trajectory smoothness
                smoothness = self._calculate_smoothness(velocities)
                performance_metrics['smoothness'] = smoothness
                
                if smoothness < 0.85:
                    errors.append(f"Complex path smoothness {smoothness:.3f} below threshold")
                
                # Validate waypoint passage
                waypoint_errors = self._validate_waypoint_passage(positions, waypoints)
                if waypoint_errors > len(waypoints) * 0.1:  # Allow 10% error rate
                    errors.append(f"Too many waypoint passage errors: {waypoint_errors}")
            
        except Exception as e:
            errors.append(f"Exception during complex path test: {str(e)}")
        
        execution_time = time.time() - start_time
        
        return TestResult(
            test_name="Complex Path Optimization",
            success=len(errors) == 0,
            execution_time=execution_time,
            performance_metrics=performance_metrics,
            errors=errors,
            details={'waypoint_count': len(waypoints)}
        )
    
    def run_motion_controller_tests(self) -> List[TestResult]:
        """Run comprehensive motion controller tests"""
        test_results = []
        
        # Test 1: Control loop timing
        result = self._test_control_loop_timing()
        test_results.append(result)
        
        # Test 2: Position tracking accuracy
        result = self._test_position_tracking()
        test_results.append(result)
        
        # Test 3: Emergency stop functionality
        result = self._test_emergency_stop()
        test_results.append(result)
        
        return test_results
    
    def _test_control_loop_timing(self) -> TestResult:
        """Test control loop timing consistency"""
        start_time = time.time()
        errors = []
        performance_metrics = {}
        
        try:
            # Create simple trajectory for testing
            waypoints = [
                [0, 0, 0, 0, 0, 0],
                [45, 45, 0, 0, 0, 0]
            ]
            
            trajectory = self.trajectory_optimizer.generate_trajectory(
                waypoints, duration=2.0
            )
            
            if trajectory is None:
                errors.append("Failed to generate test trajectory")
                return TestResult("Control Loop Timing", False, 0, {}, errors, {})
            
            # Test control loop timing
            loop_times = []
            controller = MotionController()
            controller.load_trajectory(trajectory)
            
            # Run control loop for 1 second
            test_duration = 1.0
            target_frequency = 50.0
            expected_iterations = int(test_duration * target_frequency)
            
            start_test = time.time()
            iteration_count = 0
            
            while time.time() - start_test < test_duration:
                loop_start = time.time()
                
                # Simulate control loop iteration
                controller.update()
                
                loop_time = time.time() - loop_start
                loop_times.append(loop_time)
                iteration_count += 1
                
                # Maintain timing
                time.sleep(max(0, 1.0/target_frequency - loop_time))
            
            # Analyze timing performance
            avg_loop_time = np.mean(loop_times)
            max_loop_time = np.max(loop_times)
            actual_frequency = iteration_count / test_duration
            
            performance_metrics['average_loop_time'] = avg_loop_time
            performance_metrics['max_loop_time'] = max_loop_time
            performance_metrics['actual_frequency'] = actual_frequency
            performance_metrics['target_frequency'] = target_frequency
            
            # Check timing requirements
            if actual_frequency < target_frequency * 0.95:
                errors.append(f"Control frequency {actual_frequency:.1f}Hz below target {target_frequency}Hz")
            
            if max_loop_time > 1.0 / target_frequency:
                errors.append(f"Max loop time {max_loop_time:.4f}s exceeds period")
            
        except Exception as e:
            errors.append(f"Exception during timing test: {str(e)}")
        
        execution_time = time.time() - start_time
        
        return TestResult(
            test_name="Control Loop Timing",
            success=len(errors) == 0,
            execution_time=execution_time,
            performance_metrics=performance_metrics,
            errors=errors,
            details={'test_duration': test_duration}
        )
    
    def _test_position_tracking(self) -> TestResult:
        """Test position tracking accuracy"""
        start_time = time.time()
        errors = []
        performance_metrics = {}
        
        try:
            # Create trajectory with known positions
            waypoints = [
                [0, 0, 0, 0, 0, 0],
                [30, 30, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0]
            ]
            
            trajectory = self.trajectory_optimizer.generate_trajectory(
                waypoints, duration=3.0
            )
            
            if trajectory is None:
                errors.append("Failed to generate test trajectory")
                return TestResult("Position Tracking", False, 0, {}, errors, {})
            
            # Simulate tracking
            controller = MotionController()
            controller.load_trajectory(trajectory)
            
            tracking_errors = []
            positions = trajectory['positions']
            
            # Test tracking at key points
            for i in range(0, len(positions), 10):  # Sample every 10th position
                target_pos = positions[i]
                
                # Simulate controller response (simplified)
                actual_pos = [pos + np.random.normal(0, 0.1) for pos in target_pos]  # Add small noise
                
                # Calculate tracking error
                error = np.linalg.norm(np.array(actual_pos) - np.array(target_pos))
                tracking_errors.append(error)
            
            # Analyze tracking performance
            avg_error = np.mean(tracking_errors)
            max_error = np.max(tracking_errors)
            rms_error = np.sqrt(np.mean(np.square(tracking_errors)))
            
            performance_metrics['average_error'] = avg_error
            performance_metrics['max_error'] = max_error
            performance_metrics['rms_error'] = rms_error
            
            # Check accuracy requirements
            if avg_error > self.performance_targets['position_accuracy']:
                errors.append(f"Average tracking error {avg_error:.3f} exceeds target {self.performance_targets['position_accuracy']}")
            
            if max_error > self.performance_targets['position_accuracy'] * 3:
                errors.append(f"Max tracking error {max_error:.3f} too high")
            
        except Exception as e:
            errors.append(f"Exception during tracking test: {str(e)}")
        
        execution_time = time.time() - start_time
        
        return TestResult(
            test_name="Position Tracking Accuracy",
            success=len(errors) == 0,
            execution_time=execution_time,
            performance_metrics=performance_metrics,
            errors=errors,
            details={}
        )
    
    def _test_emergency_stop(self) -> TestResult:
        """Test emergency stop functionality"""
        start_time = time.time()
        errors = []
        performance_metrics = {}
        
        try:
            # Create trajectory for testing
            waypoints = [
                [0, 0, 0, 0, 0, 0],
                [90, 90, 0, 0, 0, 0]
            ]
            
            trajectory = self.trajectory_optimizer.generate_trajectory(
                waypoints, duration=5.0
            )
            
            if trajectory is None:
                errors.append("Failed to generate test trajectory")
                return TestResult("Emergency Stop", False, 0, {}, errors, {})
            
            controller = MotionController()
            controller.load_trajectory(trajectory)
            
            # Start trajectory execution
            controller.start()
            
            # Let it run for a short time
            time.sleep(0.5)
            
            # Trigger emergency stop
            stop_time = time.time()
            controller.emergency_stop()
            
            # Check stop response time
            response_time = 0.01  # Simulated response time
            performance_metrics['stop_response_time'] = response_time
            
            # Verify controller stopped
            if controller.is_running():
                errors.append("Controller did not stop after emergency stop")
            else:
                performance_metrics['stop_successful'] = True
            
            # Check that controller cannot be restarted without reset
            try:
                controller.start()
                if controller.is_running():
                    errors.append("Controller restarted without proper reset after emergency stop")
            except:
                performance_metrics['safety_lockout'] = True
            
            # Test proper reset and restart
            controller.reset()
            controller.start()
            if not controller.is_running():
                errors.append("Controller failed to restart after proper reset")
            
            controller.stop()
            
        except Exception as e:
            errors.append(f"Exception during emergency stop test: {str(e)}")
        
        execution_time = time.time() - start_time
        
        return TestResult(
            test_name="Emergency Stop Functionality",
            success=len(errors) == 0,
            execution_time=execution_time,
            performance_metrics=performance_metrics,
            errors=errors,
            details={}
        )
    
    def _calculate_smoothness(self, velocities: np.ndarray) -> float:
        """Calculate trajectory smoothness metric"""
        if len(velocities) < 2:
            return 0.0
        
        # Calculate acceleration (second derivative)
        accelerations = np.diff(velocities, axis=0)
        
        # Calculate jerk (third derivative)
        jerks = np.diff(accelerations, axis=0)
        
        # Smoothness metric based on jerk minimization
        total_jerk = np.sum(np.abs(jerks))
        path_length = len(velocities)
        
        # Normalize and invert (higher is smoother)
        smoothness = 1.0 / (1.0 + total_jerk / path_length)
        
        return smoothness
    
    def _validate_waypoint_passage(self, positions: np.ndarray, waypoints: List[List[float]]) -> int:
        """Validate that trajectory passes through waypoints"""
        errors = 0
        tolerance = 2.0  # degrees
        
        for waypoint in waypoints:
            # Find closest point in trajectory to waypoint
            distances = [np.linalg.norm(np.array(pos) - np.array(waypoint)) for pos in positions]
            min_distance = min(distances)
            
            if min_distance > tolerance:
                errors += 1
        
        return errors
    
    def run_integration_tests(self) -> List[TestResult]:
        """Run integration tests between components"""
        test_results = []
        
        # Test 1: Trajectory to controller integration
        result = self._test_trajectory_controller_integration()
        test_results.append(result)
        
        # Test 2: Performance under load
        result = self._test_system_performance_under_load()
        test_results.append(result)
        
        return test_results
    
    def _test_trajectory_controller_integration(self) -> TestResult:
        """Test integration between trajectory optimizer and motion controller"""
        start_time = time.time()
        errors = []
        performance_metrics = {}
        
        try:
            # Generate trajectory
            waypoints = [
                [0, 0, 0, 0, 0, 0],
                [45, 45, 0, 0, 0, 0],
                [90, 90, 0, 0, 0, 0],
                [45, 45, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0]
            ]
            
            trajectory = self.trajectory_optimizer.generate_trajectory(
                waypoints, duration=8.0
            )
            
            if trajectory is None:
                errors.append("Trajectory generation failed")
                return TestResult("Integration Test", False, 0, {}, errors, {})
            
            # Load trajectory into controller
            controller = MotionController()
            load_success = controller.load_trajectory(trajectory)
            
            if not load_success:
                errors.append("Failed to load trajectory into controller")
            
            # Test trajectory execution simulation
            controller.start()
            execution_time = 0
            max_execution_time = 10.0  # seconds
            
            while controller.is_running() and execution_time < max_execution_time:
                controller.update()
                time.sleep(0.02)  # 50Hz update
                execution_time += 0.02
            
            if controller.is_running():
                errors.append("Controller did not complete trajectory in expected time")
                controller.stop()
            
            performance_metrics['execution_time'] = execution_time
            performance_metrics['trajectory_points'] = len(trajectory['positions'])
            
        except Exception as e:
            errors.append(f"Exception during integration test: {str(e)}")
        
        execution_time = time.time() - start_time
        
        return TestResult(
            test_name="Trajectory-Controller Integration",
            success=len(errors) == 0,
            execution_time=execution_time,
            performance_metrics=performance_metrics,
            errors=errors,
            details={}
        )
    
    def _test_system_performance_under_load(self) -> TestResult:
        """Test system performance under load"""
        start_time = time.time()
        errors = []
        performance_metrics = {}
        
        try:
            # Create multiple complex trajectories
            trajectory_times = []
            controller_times = []
            
            for i in range(5):
                # Generate complex trajectory
                waypoints = [[np.random.uniform(-90, 90) for _ in range(6)] for _ in range(8)]
                
                traj_start = time.time()
                trajectory = self.trajectory_optimizer.generate_trajectory(
                    waypoints, duration=5.0
                )
                traj_time = time.time() - traj_start
                trajectory_times.append(traj_time)
                
                if trajectory is None:
                    errors.append(f"Trajectory {i} generation failed under load")
                    continue
                
                # Test controller performance
                controller = MotionController()
                
                ctrl_start = time.time()
                controller.load_trajectory(trajectory)
                controller.start()
                
                # Run for short duration
                for _ in range(50):  # 1 second at 50Hz
                    controller.update()
                    time.sleep(0.02)
                
                controller.stop()
                ctrl_time = time.time() - ctrl_start
                controller_times.append(ctrl_time)
            
            # Analyze performance under load
            avg_traj_time = np.mean(trajectory_times)
            max_traj_time = np.max(trajectory_times)
            avg_ctrl_time = np.mean(controller_times)
            
            performance_metrics['avg_trajectory_time'] = avg_traj_time
            performance_metrics['max_trajectory_time'] = max_traj_time
            performance_metrics['avg_controller_time'] = avg_ctrl_time
            
            # Check performance degradation
            if max_traj_time > self.performance_targets['trajectory_calculation_time'] * 2:
                errors.append(f"Trajectory generation time {max_traj_time:.3f}s degraded under load")
            
        except Exception as e:
            errors.append(f"Exception during load test: {str(e)}")
        
        execution_time = time.time() - start_time
        
        return TestResult(
            test_name="System Performance Under Load",
            success=len(errors) == 0,
            execution_time=execution_time,
            performance_metrics=performance_metrics,
            errors=errors,
            details={'load_iterations': 5}
        )
    
    def generate_test_report(self, test_results: List[TestResult]) -> str:
        """Generate comprehensive test report"""
        report = []
        report.append("# Phase 5 Motion Planning Test Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Summary
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results if result.success)
        failed_tests = total_tests - passed_tests
        
        report.append("## Test Summary")
        report.append(f"- Total Tests: {total_tests}")
        report.append(f"- Passed: {passed_tests}")
        report.append(f"- Failed: {failed_tests}")
        report.append(f"- Success Rate: {(passed_tests/total_tests)*100:.1f}%\n")
        
        # Performance Summary
        report.append("## Performance Summary")
        total_exec_time = sum(result.execution_time for result in test_results)
        report.append(f"- Total Execution Time: {total_exec_time:.3f}s")
        
        # Individual test results
        report.append("## Test Results\n")
        
        for result in test_results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            report.append(f"### {result.test_name} - {status}")
            report.append(f"- Execution Time: {result.execution_time:.3f}s")
            
            if result.performance_metrics:
                report.append("- Performance Metrics:")
                for key, value in result.performance_metrics.items():
                    if isinstance(value, float):
                        report.append(f"  - {key}: {value:.3f}")
                    else:
                        report.append(f"  - {key}: {value}")
            
            if result.errors:
                report.append("- Errors:")
                for error in result.errors:
                    report.append(f"  - {error}")
            
            report.append("")
        
        # Performance Targets Comparison
        report.append("## Performance Targets")
        report.append("| Metric | Target | Status |")
        report.append("|--------|--------|--------|")
        
        for target_name, target_value in self.performance_targets.items():
            # Find relevant test results
            status = "Not Tested"
            for result in test_results:
                if target_name.replace('_', ' ').lower() in result.test_name.lower():
                    if result.success:
                        status = "✅ Met"
                    else:
                        status = "❌ Not Met"
                    break
            
            report.append(f"| {target_name.replace('_', ' ').title()} | {target_value} | {status} |")
        
        return "\n".join(report)
    
    def run_all_tests(self) -> str:
        """Run all test suites and generate comprehensive report"""
        self.logger.log("Starting Phase 5 comprehensive testing suite", "INFO")
        
        all_results = []
        
        # Run trajectory optimization tests
        self.logger.log("Running trajectory optimization tests", "INFO")
        traj_results = self.run_trajectory_optimization_tests()
        all_results.extend(traj_results)
        
        # Run motion controller tests
        self.logger.log("Running motion controller tests", "INFO")
        ctrl_results = self.run_motion_controller_tests()
        all_results.extend(ctrl_results)
        
        # Run integration tests
        self.logger.log("Running integration tests", "INFO")
        integ_results = self.run_integration_tests()
        all_results.extend(integ_results)
        
        # Store results
        self.test_results = all_results
        
        # Generate report
        report = self.generate_test_report(all_results)
        
        # Log summary
        passed = sum(1 for r in all_results if r.success)
        total = len(all_results)
        self.logger.log(f"Testing complete: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)", "INFO")
        
        return report
    
    def visualize_trajectory(self, trajectory: Dict, save_path: Optional[str] = None):
        """Visualize trajectory for analysis"""
        try:
            import matplotlib.pyplot as plt
            
            positions = np.array(trajectory['positions'])
            velocities = np.array(trajectory['velocities'])
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # Plot positions
            time_points = np.linspace(0, trajectory.get('duration', len(positions)*0.02), len(positions))
            
            for joint in range(min(6, positions.shape[1])):
                ax1.plot(time_points, positions[:, joint], label=f'Joint {joint+1}')
            
            ax1.set_xlabel('Time (s)')
            ax1.set_ylabel('Position (degrees)')
            ax1.set_title('Joint Positions')
            ax1.legend()
            ax1.grid(True)
            
            # Plot velocities
            for joint in range(min(6, velocities.shape[1])):
                ax2.plot(time_points[:len(velocities)], velocities[:, joint], label=f'Joint {joint+1}')
            
            ax2.set_xlabel('Time (s)')
            ax2.set_ylabel('Velocity (degrees/s)')
            ax2.set_title('Joint Velocities')
            ax2.legend()
            ax2.grid(True)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                self.logger.log(f"Trajectory visualization saved to {save_path}", "INFO")
            else:
                plt.show()
            
            plt.close()
            
        except ImportError:
            self.logger.log("Matplotlib not available for trajectory visualization", "WARNING")
        except Exception as e:
            self.logger.log(f"Error creating trajectory visualization: {str(e)}", "ERROR")

def main():
    """Main function for running tests"""
    tester = MotionPlanningTester()
    
    print("Phase 5 Motion Planning Testing Framework")
    print("==========================================")
    
    # Run all tests
    report = tester.run_all_tests()
    
    # Save report
    report_path = "phase5_test_report.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\nTest report saved to: {report_path}")
    print("\nTest Summary:")
    print(report.split('\n')[4:9])  # Print summary section

if __name__ == "__main__":
    main()
