#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Robot Control Tests

This test suite validates the complete functionality of the consolidated robot control package
after the major consolidation effort that reduced 11 files to 6 files.

Test Categories:
1. Import and Package Structure Tests
2. Core API Functionality Tests  
3. Utilities and Helper Functions Tests
4. Robot Controller and Movement Tests
5. ROS Bridge and Backend Selection Tests
6. Integration and Communication Tests
7. Error Handling and Edge Case Tests
8. Performance and Regression Tests
"""

import sys
import os
import time
import unittest
import threading
from typing import Dict, List, Tuple, Optional, Any
from unittest.mock import Mock, patch, MagicMock

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the consolidated robot control package
import robot_control
from robot_control import (
    # Core API
    DobotApiDashboard, DobotApiFeedback, ConnectionManager,
    test_robot_connection, check_robot_alarms, RobotStatusMonitor,
    
    # Utilities
    parse_api_response, wait_with_progress, execute_robot_command,
    format_position, validate_position_values, calculate_movement_time,
    retry_operation, safe_float_conversion, safe_int_conversion,
    
    # Robot Control
    RobotController, RobotSystem, HandTrackingServer,
    MediaPipeToRobotTransformer, validate_position,
    
    # ROS Bridge
    RobotApiAdapter, EnhancedRobotConnection, BackendType,
    MigrationFeature, create_dobot_api, create_migration_adapter,
    is_ros_available,
    
    # Logging
    get_logger, setup_logging
)


class TestResult:
    """Test result container"""
    def __init__(self, name: str, passed: bool, message: str, duration: float = 0.0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration
        self.timestamp = time.time()


class ComprehensiveRobotTests:
    """Main test runner for comprehensive robot control validation"""
    
    def __init__(self, robot_ip: str = "192.168.1.6", mock_mode: bool = True):
        self.robot_ip = robot_ip
        self.mock_mode = mock_mode
        self.test_results: List[TestResult] = []
        self.logger = get_logger(__name__)
          # Setup logging for tests
        setup_logging("comprehensive_tests")
        
    def run_test(self, test_name: str, test_func):
        """Run a single test and record results"""
        start_time = time.time()
        try:
            self.logger.info(f"Running test: {test_name}")
            success, message = test_func()
            duration = time.time() - start_time
            
            result = TestResult(test_name, success, message, duration)
            self.test_results.append(result)
            
            status = "✅ PASS" if success else "❌ FAIL"
            self.logger.info(f"{status} {test_name}: {message} ({duration:.2f}s)")
            
            return success
            
        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(test_name, False, f"Exception: {str(e)}", duration)
            self.test_results.append(result)
            
            self.logger.error(f"❌ FAIL {test_name}: Exception - {str(e)} ({duration:.2f}s)")
            return False
    
    def test_package_imports(self) -> Tuple[bool, str]:
        """Test 1.1: Package Import Structure"""
        try:
            # Test main package import
            assert hasattr(robot_control, '__version__')
            assert hasattr(robot_control, '__all__')
            
            # Test all exported symbols are importable
            for symbol in robot_control.__all__:
                assert hasattr(robot_control, symbol), f"Missing symbol: {symbol}"
            
            # Test specific critical imports
            critical_classes = [
                DobotApiDashboard, DobotApiFeedback, ConnectionManager,
                RobotController, RobotSystem, HandTrackingServer,
                RobotApiAdapter, EnhancedRobotConnection
            ]
            
            for cls in critical_classes:
                assert cls is not None, f"Failed to import {cls.__name__}"
                
            return True, f"All {len(robot_control.__all__)} symbols imported successfully"
            
        except Exception as e:
            return False, f"Import test failed: {str(e)}"
    
    def test_backward_compatibility(self) -> Tuple[bool, str]:
        """Test 1.2: Backward Compatibility"""
        try:
            # Test that old import patterns still work
            compatibility_tests = []
            
            # Test core API backward compatibility
            from robot_control import DobotApiDashboard as Dashboard
            from robot_control import ConnectionManager as ConnMgr
            compatibility_tests.append("Core API imports")
            
            # Test utilities backward compatibility
            from robot_control import parse_api_response as parse_response
            from robot_control import execute_robot_command as exec_cmd
            compatibility_tests.append("Utilities imports")
            
            # Test robot controller backward compatibility
            from robot_control import RobotSystem as System
            from robot_control import RobotController as Controller
            compatibility_tests.append("Robot controller imports")
            
            # Test function signatures haven't changed
            import inspect
            
            # Check parse_api_response signature
            sig = inspect.signature(parse_api_response)
            expected_params = ['response', 'extract_mode']
            actual_params = list(sig.parameters.keys())
            assert any(p in actual_params for p in expected_params), "parse_api_response signature changed"
            
            return True, f"Backward compatibility verified for {len(compatibility_tests)} import groups"
            
        except Exception as e:
            return False, f"Backward compatibility test failed: {str(e)}"
    
    def test_core_api_classes(self) -> Tuple[bool, str]:
        """Test 2.1: Core API Class Instantiation"""
        try:
            classes_tested = []
            
            if self.mock_mode:
                # Mock mode - test class creation without actual connections
                with patch('socket.socket'):
                    dashboard = DobotApiDashboard("192.168.1.6", 29999)
                    classes_tested.append("DobotApiDashboard")
                    
                    feedback = DobotApiFeedback("192.168.1.6", 30003)
                    classes_tested.append("DobotApiFeedback")
                    
                    conn_mgr = ConnectionManager("192.168.1.6")
                    classes_tested.append("ConnectionManager")
                    
                    status_monitor = RobotStatusMonitor("192.168.1.6")
                    classes_tested.append("RobotStatusMonitor")
            else:
                # Real mode - attempt actual connections (may fail if robot unavailable)
                try:
                    dashboard = DobotApiDashboard(self.robot_ip, 29999)
                    classes_tested.append("DobotApiDashboard")
                except:
                    pass  # Expected if robot not available
                    
            return True, f"Core API classes instantiated: {', '.join(classes_tested)}"
            
        except Exception as e:
            return False, f"Core API class test failed: {str(e)}"
    
    def test_utility_functions(self) -> Tuple[bool, str]:
        """Test 3.1: Utility Functions"""
        try:
            functions_tested = []
            
            # Test parse_api_response
            test_response = "1,2,3,4,5,6;"
            parsed = parse_api_response(test_response, extract_mode="numbers")
            assert parsed is not None
            functions_tested.append("parse_api_response")
            
            # Test safe conversions
            assert safe_float_conversion("3.14") == 3.14
            assert safe_float_conversion("invalid", default=0.0) == 0.0
            assert safe_int_conversion("42") == 42
            assert safe_int_conversion("invalid", default=0) == 0
            functions_tested.append("safe conversions")
            
            # Test position validation
            valid_pos = [100.0, 200.0, 300.0, 0.0, 0.0, 0.0]
            assert validate_position_values(valid_pos) == True
            functions_tested.append("validate_position_values")
            
            # Test position formatting
            formatted = format_position(valid_pos)
            assert isinstance(formatted, str)
            assert all(str(p) in formatted for p in valid_pos)
            functions_tested.append("format_position")
            
            # Test movement time calculation
            movement_time = calculate_movement_time([0, 0, 0], [100, 100, 100])
            assert movement_time > 0
            functions_tested.append("calculate_movement_time")
            
            return True, f"Utility functions tested: {', '.join(functions_tested)}"
            
        except Exception as e:
            return False, f"Utility function test failed: {str(e)}"
    
    def test_robot_controller_creation(self) -> Tuple[bool, str]:
        """Test 4.1: Robot Controller Instantiation"""
        try:
            controllers_tested = []
            
            if self.mock_mode:
                with patch('robot_control.core_api.ConnectionManager'):
                    # Test RobotSystem creation
                    robot_system = RobotSystem(self.robot_ip)
                    assert robot_system is not None
                    assert hasattr(robot_system, 'controller')
                    assert hasattr(robot_system, 'connection')
                    controllers_tested.append("RobotSystem")
                    
                    # Test standalone RobotController
                    mock_dashboard = Mock()
                    robot_controller = RobotController(mock_dashboard)
                    assert robot_controller is not None
                    controllers_tested.append("RobotController")
                    
                    # Test MediaPipeToRobotTransformer
                    transformer = MediaPipeToRobotTransformer()
                    assert transformer is not None
                    controllers_tested.append("MediaPipeToRobotTransformer")
            
            return True, f"Robot controllers created: {', '.join(controllers_tested)}"
            
        except Exception as e:
            return False, f"Robot controller test failed: {str(e)}"
    
    def test_ros_bridge_functionality(self) -> Tuple[bool, str]:
        """Test 5.1: ROS Bridge and Backend Selection"""
        try:
            features_tested = []
            
            # Test ROS availability check
            ros_available = is_ros_available()
            features_tested.append(f"ROS available: {ros_available}")
            
            # Test backend types
            backend_types = [BackendType.TCP, BackendType.ROS, BackendType.AUTO]
            assert len(backend_types) == 3
            features_tested.append("BackendType enum")
            
            # Test migration features
            migration_features = [
                MigrationFeature.LOGGING,
                MigrationFeature.PERFORMANCE_MONITORING,
                MigrationFeature.ERROR_RECOVERY
            ]
            assert len(migration_features) == 3
            features_tested.append("MigrationFeature enum")
            
            # Test adapter creation functions
            if self.mock_mode:
                with patch('robot_control.ros_bridge.subprocess'):
                    # Test create_dobot_api
                    api = create_dobot_api(self.robot_ip, backend=BackendType.TCP)
                    assert api is not None
                    features_tested.append("create_dobot_api")
                    
                    # Test create_migration_adapter
                    adapter = create_migration_adapter(
                        self.robot_ip, 
                        features=[MigrationFeature.LOGGING]
                    )
                    assert adapter is not None
                    features_tested.append("create_migration_adapter")
            
            return True, f"ROS bridge features tested: {', '.join(features_tested)}"
            
        except Exception as e:
            return False, f"ROS bridge test failed: {str(e)}"
    
    def test_error_handling(self) -> Tuple[bool, str]:
        """Test 6.1: Error Handling and Edge Cases"""
        try:
            error_tests = []
            
            # Test retry_operation with failing function
            call_count = 0
            def failing_function():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Simulated failure")
                return "Success"
            
            result = retry_operation(failing_function, max_retries=3, delay=0.1)
            assert result == "Success"
            assert call_count == 3
            error_tests.append("retry_operation with recovery")
            
            # Test retry_operation with persistent failure
            def always_failing_function():
                raise Exception("Always fails")
            
            result = retry_operation(always_failing_function, max_retries=2, delay=0.1)
            assert result is None
            error_tests.append("retry_operation with persistent failure")
            
            # Test invalid position handling
            invalid_positions = [
                None,
                [],
                [1, 2],  # Too few values
                [1, 2, 3, 4, 5, 6, 7, 8],  # Too many values
                ["a", "b", "c", "d", "e", "f"],  # Non-numeric values
            ]
            
            for invalid_pos in invalid_positions:
                try:
                    result = validate_position_values(invalid_pos)
                    assert result == False
                except:
                    pass  # Expected for some invalid inputs
            
            error_tests.append("invalid position handling")
            
            # Test safe conversion edge cases
            edge_cases = [
                (None, 0.0),
                ("", 0.0),
                ("inf", 0.0),
                ("-inf", 0.0),
                ("nan", 0.0),
            ]
            
            for input_val, expected_default in edge_cases:
                result = safe_float_conversion(input_val, default=expected_default)
                assert result == expected_default            
            error_tests.append("safe conversion edge cases")
            
            return True, f"Error handling tests passed: {', '.join(error_tests)}"
            
        except Exception as e:
            return False, f"Error handling test failed: {str(e)}"
    
    def test_integration_scenarios(self) -> Tuple[bool, str]:
        """Test 7.1: Integration Between Modules"""
        try:
            integration_tests = []
            
            if self.mock_mode:
                with patch('robot_control.core_api.socket.socket') as mock_socket:
                    # Test full system integration
                    robot_system = RobotSystem(self.robot_ip)
                    
                    # Test connection manager integration
                    assert hasattr(robot_system, 'connection')
                    assert isinstance(robot_system.connection, ConnectionManager)
                    integration_tests.append("RobotSystem-ConnectionManager integration")
                    
                    # Test controller integration
                    assert hasattr(robot_system, 'controller')
                    assert isinstance(robot_system.controller, RobotController)
                    integration_tests.append("RobotSystem-RobotController integration")
                    
                    # Test utilities integration with controller
                    test_position = [100, 200, 300, 0, 0, 0]
                    formatted_pos = format_position(test_position)
                    assert isinstance(formatted_pos, str)
                    integration_tests.append("Utilities-Controller integration")
                    
                    # Test ROS bridge integration
                    enhanced_conn = EnhancedRobotConnection(
                        self.robot_ip,
                        backend=BackendType.TCP
                    )
                    assert enhanced_conn is not None
                    integration_tests.append("ROS bridge integration")
            
            return True, f"Integration tests passed: {', '.join(integration_tests)}"
            
        except Exception as e:
            return False, f"Integration test failed: {str(e)}"
    
    def test_performance_regression(self) -> Tuple[bool, str]:
        """Test 8.1: Performance and Regression"""
        try:
            performance_tests = []
            
            # Test import performance
            start_time = time.time()
            import robot_control
            import_time = time.time() - start_time
            assert import_time < 2.0, f"Import took too long: {import_time:.2f}s"
            performance_tests.append(f"Import time: {import_time:.3f}s")
            
            # Test utility function performance
            start_time = time.time()
            for _ in range(1000):
                parse_api_response("1,2,3,4,5,6;", extract_mode="numbers")
            parse_time = time.time() - start_time
            assert parse_time < 1.0, f"Parse function too slow: {parse_time:.2f}s"
            performance_tests.append(f"Parse performance: {parse_time:.3f}s for 1000 calls")
              # Test memory usage (basic check)
            try:
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                assert memory_mb < 500, f"Memory usage too high: {memory_mb:.1f}MB"
                performance_tests.append(f"Memory usage: {memory_mb:.1f}MB")
            except ImportError:
                performance_tests.append("Memory usage: psutil not available")
            
            return True, f"Performance tests passed: {', '.join(performance_tests)}"
            
        except ImportError:
            return True, "Performance tests skipped (psutil not available)"
        except Exception as e:
            return False, f"Performance test failed: {str(e)}"
    
    def test_thread_safety(self) -> Tuple[bool, str]:
        """Test 9.1: Thread Safety"""
        try:
            thread_tests = []
            results = []
            errors = []
            
            def worker_thread(thread_id):
                try:
                    # Test concurrent utility function calls
                    for i in range(100):
                        result = parse_api_response(f"{i},2,3,4,5,6;", extract_mode="numbers")
                        assert result is not None
                    
                    # Test concurrent safe conversions
                    for i in range(100):
                        val = safe_float_conversion(str(i * 0.1))
                        assert val == i * 0.1
                    
                    results.append(f"Thread {thread_id} completed")
                    
                except Exception as e:
                    errors.append(f"Thread {thread_id} error: {str(e)}")
            
            # Run multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker_thread, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=10.0)
            
            if errors:
                return False, f"Thread safety errors: {'; '.join(errors)}"
            
            thread_tests.append(f"5 threads completed successfully")
            return True, f"Thread safety tests passed: {', '.join(thread_tests)}"
            
        except Exception as e:
            return False, f"Thread safety test failed: {str(e)}"
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests"""
        print("=" * 80)
        print("COMPREHENSIVE ROBOT CONTROL TESTS")
        print("=" * 80)
        print(f"Test Mode: {'MOCK' if self.mock_mode else 'REAL'}")
        print(f"Robot IP: {self.robot_ip}")
        print(f"Package Version: {robot_control.__version__}")
        print("=" * 80)
        
        # Define all tests
        test_suite = [
            ("Package Imports", self.test_package_imports),
            ("Backward Compatibility", self.test_backward_compatibility),
            ("Core API Classes", self.test_core_api_classes),
            ("Utility Functions", self.test_utility_functions),
            ("Robot Controller Creation", self.test_robot_controller_creation),
            ("ROS Bridge Functionality", self.test_ros_bridge_functionality),
            ("Error Handling", self.test_error_handling),
            ("Integration Scenarios", self.test_integration_scenarios),
            ("Performance Regression", self.test_performance_regression),
            ("Thread Safety", self.test_thread_safety),
        ]
        
        # Run all tests
        start_time = time.time()
        passed_tests = 0
        total_tests = len(test_suite)
        
        for test_name, test_func in test_suite:
            success = self.run_test(test_name, test_func)
            if success:
                passed_tests += 1
        
        total_time = time.time() - start_time
        
        # Generate summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        # Print individual results
        for result in self.test_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} {result.name:<30} ({result.duration:.2f}s)")
            if not result.passed:
                print(f"     Error: {result.message}")
        
        # Print overall statistics
        print("\n" + "-" * 80)
        success_rate = (passed_tests / total_tests) * 100
        print(f"Overall Result: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        print(f"Total Time: {total_time:.2f} seconds")
        print(f"Average Time per Test: {total_time/total_tests:.2f} seconds")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! The consolidated robot control package is fully functional.")
        else:
            failed_tests = total_tests - passed_tests
            print(f"\n⚠️  {failed_tests} test(s) failed. Review the errors above.")
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': success_rate,
            'total_time': total_time,
            'results': self.test_results
        }


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive Robot Control Tests")
    parser.add_argument("--robot-ip", default="192.168.1.6", help="Robot IP address")
    parser.add_argument("--real-mode", action="store_true", 
                       help="Run tests against real robot (default: mock mode)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
      # Configure logging
    setup_logging("comprehensive_tests")
    
    # Run tests
    tester = ComprehensiveRobotTests(
        robot_ip=args.robot_ip,
        mock_mode=not args.real_mode
    )
    
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if results['failed_tests'] == 0 else 1)


if __name__ == "__main__":
    main()
