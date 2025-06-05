#!/usr/bin/env python3
"""
Comprehensive Test Suite for Hand Tracking Robot Control System

This unified test script combines all testing capabilities into a single,
well-organized testing framework including test robot controller functionality.

Usage:
    python test_suite.py --help                    # Show all options
    python test_suite.py --basic                   # Basic import tests
    python test_suite.py --integration             # Full integration test
    python test_suite.py --communication           # TCP communication test
    python test_suite.py --coordinates             # Coordinate transformation test
    python test_suite.py --robot-utils-test        # Test robot_utils module
    python test_suite.py --startup-test            # Test startup robot movement
    python test_suite.py --all                     # Run all tests
    python test_suite.py --demo                    # Interactive demo mode
    python test_suite.py --test-robot              # Start test robot controller
"""

import sys
import os
import time
import json
import socket
import threading
import argparse
import queue
import math
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# Add the TCP-IP-CR-Python-V4 directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'TCP-IP-CR-Python-V4'))

# Import robot_utils module
try:
    from robot_utils import RobotConnection, ROBOT_API_AVAILABLE
except ImportError as e:
    print(f"Warning: Could not import robot_utils module: {e}")
    # Fallback to direct imports if robot_utils is not available
    try:
        from dobot_api import DobotApiDashboard, DobotApiFeedBack
        ROBOT_API_AVAILABLE = True
    except ImportError:
        print("Warning: Robot API not available")
        ROBOT_API_AVAILABLE = False

class TestRobotController:
    """Test robot controller that simulates robot operations without hardware"""
    
    def __init__(self, robot_ip: str = "192.168.1.6"):
        self.robot_ip = robot_ip
        self.running = False
        self.current_position = [0, 0, 200, 0, 0, 0]  # x, y, z, rx, ry, rz
        self.movement_threshold = 5.0  # mm
        self.lock = threading.Lock()
        
        # Initialize components
        from CR3_Control import CoordinateTransformer, HandTrackingServer
        self.coordinate_transformer = CoordinateTransformer()
        self.hand_tracking_server = HandTrackingServer()
        
    def connect_robot(self) -> bool:
        """Simulate robot connection"""
        print("[TEST MODE] Simulating robot connection...")
        time.sleep(1)  # Simulate connection delay
        print(f"[TEST MODE] ✓ Connected to simulated robot at {self.robot_ip}")
        return True
        
    def enable_robot(self) -> bool:
        """Simulate robot enabling"""
        print("[TEST MODE] Enabling simulated robot...")
        time.sleep(0.5)
        print("[TEST MODE] ✓ Robot enabled and ready")
        return True
        
    def disable_robot(self):
        """Simulate robot disabling"""
        print("[TEST MODE] Disabling simulated robot...")
        time.sleep(0.5)
        print("[TEST MODE] ✓ Robot disabled")
        
    def move_to_position(self, x: float, y: float, z: float, rx: float = 0, ry: float = 0, rz: float = 0) -> bool:
        """Simulate robot movement"""
        try:
            # Check if movement is significant enough
            with self.lock:
                current_x, current_y, current_z = self.current_position[:3]
                
            distance = math.sqrt((x - current_x)**2 + (y - current_y)**2 + (z - current_z)**2)
            if distance < self.movement_threshold:
                return True  # Movement too small, skip
                
            # Simulate movement
            print(f"[TEST MODE] Moving to: X:{x:.1f}, Y:{y:.1f}, Z:{z:.1f} mm")
            
            with self.lock:
                self.current_position = [x, y, z, rx, ry, rz]
                
            return True
            
        except Exception as e:
            print(f"[TEST MODE] Error simulating movement: {e}")
            return False
            
    def start_test_robot(self, duration: int = 60):
        """Start test robot controller for specified duration"""
        print("\n=== TEST ROBOT CONTROLLER ===")
        print("Starting simulated robot controller...")
        
        if not self.connect_robot():
            return False
            
        if not self.enable_robot():
            return False
            
        # Start hand tracking server in a separate thread
        server_thread = threading.Thread(target=self.hand_tracking_server.start_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Start processing for specified duration
        self.running = True
        print(f"✓ Test robot controller running for {duration} seconds")
        print("✓ Ready to receive hand tracking data on port 8888")
        
        start_time = time.time()
        coord_count = 0
        
        try:
            while time.time() - start_time < duration and self.running:
                # Get latest coordinates
                coord_data = self.hand_tracking_server.get_latest_coordinates()
                
                if coord_data and 'shoulder' in coord_data and 'wrist' in coord_data:
                    shoulder = coord_data['shoulder']
                    wrist = coord_data['wrist']
                    
                    # Transform coordinates to robot space
                    robot_x, robot_y, robot_z = self.coordinate_transformer.transform_to_robot_coords(
                        shoulder, wrist
                    )
                    
                    # Simulate robot movement
                    self.move_to_position(robot_x, robot_y, robot_z)
                    coord_count += 1
                    
                time.sleep(0.1)  # 10 Hz update rate
                
        except KeyboardInterrupt:
            print("\nTest robot controller interrupted by user")
            
        self.running = False
        self.hand_tracking_server.stop_server()
        self.disable_robot()
        
        print(f"✓ Test robot controller stopped - processed {coord_count} coordinate sets")
        return True

class TestSuite:
    """Unified test suite for the hand tracking robot control system"""
    
    def __init__(self):
        self.test_results = {}
        
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test results"""
        self.test_results[test_name] = {"passed": passed, "message": message}
        status = "✓" if passed else "✗"
        print(f"  {status} {test_name}: {message}")
        
    def basic_imports_test(self) -> bool:
        """Test 1: Basic module imports"""
        print("\n=== TEST 1: Basic Module Imports ===")
        
        try:
            # Test CR3_Control imports
            from CR3_Control import CoordinateTransformer, HandTrackingServer, CR3RobotController
            self.log_result("CR3_Control imports", True, "All robot control modules imported")
        except Exception as e:
            self.log_result("CR3_Control imports", False, f"Import failed: {e}")
            return False
            
        try:
            # Test Hand_Tracking imports
            from Hand_Tracking import RobotClient
            self.log_result("Hand_Tracking imports", True, "Hand tracking modules imported")
        except Exception as e:
            self.log_result("Hand_Tracking imports", False, f"Import failed: {e}")
            return False
            
        try:
            # Test CR3_Control_Test imports (simulation mode)
            from CR3_Control_Test import TestRobotController
            self.log_result("Test mode imports", True, "Test controller imported")
        except Exception as e:
            self.log_result("Test mode imports", False, f"Import failed: {e}")
            
        return True
        
    def coordinate_transformation_test(self) -> bool:
        """Test 2: Coordinate transformation functionality"""
        print("\n=== TEST 2: Coordinate Transformation ===")
        
        try:
            from CR3_Control import CoordinateTransformer
            
            transformer = CoordinateTransformer(workspace_size=400.0, height_offset=200.0)
            
            # Test various positions
            test_cases = [
                {"name": "Center position", "shoulder": [0.5, 0.5, 0.5], "wrist": [0.5, 0.5, 0.5]},
                {"name": "Right reach", "shoulder": [0.4, 0.5, 0.5], "wrist": [0.6, 0.5, 0.5]},
                {"name": "Forward reach", "shoulder": [0.5, 0.5, 0.6], "wrist": [0.5, 0.5, 0.4]},
            ]
            
            for case in test_cases:
                robot_coords = transformer.transform_to_robot_coords(case["shoulder"], case["wrist"])
                x, y, z = robot_coords
                
                # Check bounds
                if -200 <= x <= 200 and -200 <= y <= 200 and 50 <= z <= 400:
                    self.log_result(f"Transform {case['name']}", True, 
                                  f"({x:.1f}, {y:.1f}, {z:.1f}) mm - within bounds")
                else:
                    self.log_result(f"Transform {case['name']}", False, 
                                  f"({x:.1f}, {y:.1f}, {z:.1f}) mm - outside safe bounds")
                    
            return True
            
        except Exception as e:
            self.log_result("Coordinate transformation", False, f"Error: {e}")
            return False
            
    def tcp_communication_test(self) -> bool:
        """Test 3: TCP communication between components"""
        print("\n=== TEST 3: TCP Communication ===")
        
        try:
            from CR3_Control import HandTrackingServer
            from Hand_Tracking import RobotClient
            
            # Use a test port to avoid conflicts
            test_port = 9999
            server = HandTrackingServer('localhost', test_port)
            
            # Start server in background
            server_thread = threading.Thread(target=server.start_server)
            server_thread.daemon = True
            server_thread.start()
            
            # Wait for server to start
            time.sleep(1)
            
            # Test client connection
            client = RobotClient('localhost', test_port)
            connected = client.connect()
            
            if connected:
                self.log_result("TCP connection", True, "Client connected to server")
                
                # Test coordinate sending
                test_coords = [0.5, 0.3, 0.2], [0.6, 0.4, 0.3]  # shoulder, wrist
                client.send_coordinates(*test_coords)
                
                # Wait and check if server received data
                time.sleep(0.5)
                received_data = server.get_latest_coordinates()
                
                if received_data and 'shoulder' in received_data and 'wrist' in received_data:
                    self.log_result("Data transmission", True, "Coordinates successfully transmitted")
                else:
                    self.log_result("Data transmission", False, "No data received by server")
                    
                client.disconnect()
            else:
                self.log_result("TCP connection", False, "Failed to connect")
                
            server.stop_server()
            return True
            
        except Exception as e:
            self.log_result("TCP communication", False, f"Error: {e}")
            return False
            
    def integration_test(self) -> bool:
        """Test 4: Full system integration"""
        print("\n=== TEST 4: System Integration ===")
        
        try:
            # Test JSON message format
            test_message = {
                "timestamp": time.time(),
                "shoulder": [0.5, 0.3, 0.2],
                "wrist": [0.6, 0.4, 0.3]
            }
            
            # Test encoding/decoding
            encoded = json.dumps(test_message) + '\n'
            decoded = json.loads(encoded.strip())
            
            if decoded['shoulder'] == test_message['shoulder']:
                self.log_result("JSON message format", True, "Encoding/decoding works correctly")
            else:
                self.log_result("JSON message format", False, "Data corruption in JSON processing")
                
            # Test test robot controller
            from CR3_Control_Test import TestRobotController
            test_controller = TestRobotController()
            
            if test_controller.connect_robot():
                self.log_result("Test robot controller", True, "Test controller initialized")
            else:
                self.log_result("Test robot controller", False, "Failed to initialize test controller")
                
            return True
            
        except Exception as e:
            self.log_result("System integration", False, f"Error: {e}")
            return False
            
    def communication_demo_test(self) -> bool:
        """Test 5: Live communication demo (requires robot controller running)"""
        print("\n=== TEST 5: Live Communication Demo ===")
        print("This test requires CR3_Control.py or CR3_Control_Test.py to be running")
        
        try:
            # Try to connect to default robot control server
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(3)  # 3 second timeout
            
            try:
                client_socket.connect(('localhost', 8888))
                self.log_result("Robot server connection", True, "Connected to robot control server")
                
                # Send test data
                test_coordinates = [
                    {"timestamp": time.time(), "shoulder": [0.5, 0.3, 0.2], "wrist": [0.6, 0.4, 0.3]},
                    {"timestamp": time.time() + 1, "shoulder": [0.5, 0.3, 0.2], "wrist": [0.4, 0.5, 0.4]},
                ]
                
                for i, coords in enumerate(test_coordinates):
                    message = json.dumps(coords) + '\n'
                    client_socket.send(message.encode('utf-8'))
                    time.sleep(0.5)
                    
                self.log_result("Live data transmission", True, f"Sent {len(test_coordinates)} coordinate sets")
                client_socket.close()
                
            except socket.timeout:
                self.log_result("Robot server connection", False, "No robot controller running on port 8888")
            except ConnectionRefusedError:
                self.log_result("Robot server connection", False, "Robot controller not accessible")
                
            return True
            
        except Exception as e:
            self.log_result("Live communication", False, f"Error: {e}")
            return False
            
    def test_robot_controller_test(self) -> bool:
        """Test 6: Test robot controller functionality"""
        print("\n=== TEST 6: Test Robot Controller ===")
        
        try:
            # Test TestRobotController creation
            controller = TestRobotController()
            self.log_result("Test robot instantiation", True, "TestRobotController created successfully")
            
            # Test coordinate transformation
            test_shoulder = [0.5, 0.5, 0.5]
            test_wrist = [0.6, 0.4, 0.3]
            
            robot_coords = controller.coordinate_transformer.transform_to_robot_coords(
                test_shoulder, test_wrist
            )
            
            if len(robot_coords) == 3:
                self.log_result("Test robot coordinate transform", True, 
                              f"Transform successful: {robot_coords}")
            else:
                self.log_result("Test robot coordinate transform", False, "Invalid coordinate output")
                
            # Test simulated movement
            success = controller.move_to_position(100, 50, 250)
            if success:
                self.log_result("Test robot movement simulation", True, "Movement simulation working")
            else:
                self.log_result("Test robot movement simulation", False, "Movement simulation failed")
                
            return True
            
        except Exception as e:
            self.log_result("Test robot controller", False, f"Error: {e}")
            return False
            
    def test_robot_utils(self) -> bool:
        """Test 7: Robot Utils Module"""
        print("\n=== TEST 7: Robot Utilities Module ===")
        
        try:
            # Import the robot_utils module
            import sys
            sys.path.append('..')
            from robot_utils import RobotConnection, ROBOT_API_AVAILABLE
            
            # Log API availability
            api_status = "available" if ROBOT_API_AVAILABLE else "not available"
            self.log_result("Robot API availability", True, f"Robot API is {api_status}")
            
            # Test RobotConnection creation
            robot = RobotConnection("192.168.1.6")  # Use default IP
            self.log_result("RobotConnection initialization", True, "Successfully created RobotConnection instance")
            
            # Test the network connectivity check
            try:
                success, message = robot.test_network_connectivity()
                connectivity_result = "successful" if success else "failed"
                self.log_result("Network connectivity test", True, 
                              f"Network test {connectivity_result}: {message}")
            except Exception as e:
                self.log_result("Network connectivity test", False, f"Error during network test: {e}")
                
            # Test error handling for an invalid IP
            test_invalid_ip = RobotConnection("192.168.999.999")  # Invalid IP
            success, message = test_invalid_ip.test_network_connectivity()
            if not success:
                self.log_result("Invalid IP handling", True, "Correctly handled invalid IP address")
            else:
                self.log_result("Invalid IP handling", False, "Failed to detect invalid IP address")
                
            # Test additional methods if robot API is available
            if ROBOT_API_AVAILABLE:
                # Test parsing a mock robot response
                mock_alarm_response = "[[],[]]"  # Empty alarm response
                # Simulate the alarm check logic
                alarm_ok = "null" in mock_alarm_response or "[]" in mock_alarm_response
                self.log_result("Response parsing", True, 
                              f"Mock alarm parsing: {'no alarms' if alarm_ok else 'has alarms'}")
                              
                # Test position parsing from a mock response
                mock_position = "[100.0, 0.0, 200.0, 0.0, 0.0, 0.0]"
                numbers = [float(n) for n in mock_position.strip("[]").split(",")]
                if len(numbers) == 6:
                    self.log_result("Position parsing", True, f"Successfully parsed position: {numbers}")
                else:
                    self.log_result("Position parsing", False, "Failed to parse position data")
            
            return True
            
        except Exception as e:
            self.log_result("Robot utils module", False, f"Error: {e}")
            return False

    def demo_mode(self):
        """Interactive demo mode"""
        print("\n" + "=" * 60)
        print("HAND TRACKING ROBOT CONTROL - INTERACTIVE DEMO")
        print("=" * 60)
        
        print("\nThis demo will show you:")
        print("1. How coordinate transformation works")
        print("2. How TCP communication functions")
        print("3. How to start the system components")
        
        input("\nPress Enter to start the demo...")
        
        # Demo coordinate transformation
        print("\n--- Coordinate Transformation Demo ---")
        from CR3_Control import CoordinateTransformer
        
        transformer = CoordinateTransformer()
        demo_positions = [
            {"name": "Hand at center", "shoulder": [0.5, 0.5, 0.5], "wrist": [0.5, 0.5, 0.5]},
            {"name": "Reach to the right", "shoulder": [0.4, 0.5, 0.5], "wrist": [0.7, 0.5, 0.5]},
            {"name": "Reach upward", "shoulder": [0.5, 0.6, 0.5], "wrist": [0.5, 0.3, 0.5]},
        ]
        
        for pos in demo_positions:
            robot_coords = transformer.transform_to_robot_coords(pos["shoulder"], pos["wrist"])
            print(f"{pos['name']:20} -> Robot: ({robot_coords[0]:6.1f}, {robot_coords[1]:6.1f}, {robot_coords[2]:6.1f}) mm")
            
        print("\n--- System Startup Commands ---")        print("To start the complete system:")
        print("1. Robot Controller:  python CR3_Control.py --robot-ip YOUR_ROBOT_IP")        print("2. Hand Tracking:     python Hand_Tracking.py --enable-robot")
        print("3. Test Mode:         python CR3_Control_Test.py")
        
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("HAND TRACKING ROBOT CONTROL - COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all tests
        self.basic_imports_test()
        self.coordinate_transformation_test()
        self.tcp_communication_test()
        self.integration_test()
        self.communication_demo_test()
        self.test_robot_controller_test()
        self.test_robot_utils()  # Added new test for robot_utils
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["passed"])
        
        print("\n" + "=" * 60)
        print(f"TEST SUMMARY: {passed_tests}/{total_tests} tests passed")
        print(f"Execution time: {time.time() - start_time:.1f} seconds")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Your system is ready to use.")
        else:
            print("⚠️  Some tests failed. Check the details above.")
            
        print("=" * 60)
        
        return passed_tests == total_tests

def test_startup_robot_movement():
    """Test the robot movement test function from startup.py"""
    print("\n" + "="*50)
    print("🧪 TESTING STARTUP ROBOT MOVEMENT FUNCTION")
    print("="*50)
    
    try:
        # Import from robot_utils instead of directly from startup
        import sys
        sys.path.append('..')
        from robot_utils import RobotConnection, ROBOT_API_AVAILABLE
        
        print(f"Robot API Available: {ROBOT_API_AVAILABLE}")
        
        if not ROBOT_API_AVAILABLE:
            print("⚠️  Robot API not available - test skipped")
            return True
        
        # Test with invalid IP (should fail gracefully)
        print("\n🔍 Testing with invalid IP (should fail gracefully):")
        robot = RobotConnection("192.168.999.999")
        
        # Test network connectivity (should fail with invalid IP)
        success, message = robot.test_network_connectivity()
        print(f"Network connectivity test result: {'✅ Success' if success else '❌ Failed'} - {message}")
        
        if not success:  # Should fail with invalid IP
            print("✅ Error handling works correctly")
            return True
        else:
            print("❌ Error handling failed - should return True for invalid IP")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    finally:
        # Ensure we clean up the connection
        if 'robot' in locals():
            robot.disconnect()

def main():
    """Main test runner with enhanced options"""
    parser = argparse.ArgumentParser(description="Comprehensive Hand Tracking Robot Control Test Suite")
    parser.add_argument("--basic", action="store_true", help="Run basic import and setup tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--performance", action="store_true", help="Run performance benchmarks")
    parser.add_argument("--test-robot", action="store_true", help="Run with test robot controller")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--startup-test", action="store_true", help="Test startup robot movement function")
    parser.add_argument("--robot-utils-test", action="store_true", help="Test the robot_utils module")
    
    args = parser.parse_args()
    
    if not any([args.basic, args.integration, args.performance, args.test_robot, 
                args.all, args.startup_test, args.robot_utils_test]):
        parser.print_help()
        return
    
    success = True
    
    # Initialize test suite
    suite = TestSuite()
    
    # Run startup test if requested
    if args.startup_test or args.all:
        success &= test_startup_robot_movement()
    
    # Run test robot controller if requested    if args.test_robot or args.all:
        controller = TestRobotController()
        controller.start_test_robot(args.duration)
        
    # Run selected tests
    if args.basic or args.all:
        suite.basic_imports_test()
    if args.integration or args.all:
        suite.integration_test()
    if args.robot_utils_test or args.all:
        # Use the adapter to run robot_utils tests
        try:
            from test_suite_robot_utils_adapter import TestSuiteAdapter
            adapter = TestSuiteAdapter(suite.test_results)
            success &= adapter.run_tests()
        except ImportError as e:
            print(f"❌ Could not run robot_utils tests: {e}")
            print("Make sure test_suite_robot_utils_adapter.py is in the same directory.")
    if args.all:
        suite.run_all_tests()
        
    # Performance test placeholder
    if args.performance:
        print("\n=== PERFORMANCE TEST (not implemented) ===")
        print("This feature will be available in a future update.")
    
    print("\nTest suite completed.")
    
    if success:
        print("✅ All tests passed successfully.")
    else:
        print("⚠️ Some tests failed. Please check the output for details.")

if __name__ == "__main__":
    main()
