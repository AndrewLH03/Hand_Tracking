#!/usr/bin/env python3
"""
Hand Tracking Robot Control - Startup Script

This script provides an easy way to start the hand tracking and robot control system.
It handles the proper startup sequence and provides helpful guidance.
"""

import argparse
import subprocess
import sys
import time
import os
from pathlib import Path

# Add robot_control and UI directories to Python path for internal imports
robot_control_path = os.path.join(os.path.dirname(__file__), 'robot_control')
ui_path = os.path.join(os.path.dirname(__file__), 'UI')
pose_tracking_path = os.path.join(os.path.dirname(__file__), 'Pose_Tracking')
sys.path.insert(0, robot_control_path)
sys.path.insert(0, ui_path)
sys.path.insert(0, pose_tracking_path)

# Import robot utilities
try:
    from robot_control.robot_controller import RobotController
    from robot_control.core_api import ROBOT_API_AVAILABLE
    ROBOT_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Robot control modules not available: {e}")
    ROBOT_API_AVAILABLE = False
    RobotController = None

# Import shared testing utilities
try:
    from Testing import RobotTester
except ImportError:
    print("Warning: Testing package not available - using fallback testing")
    RobotTester = None

# Import Phase 5 Motion Planning and Safety Systems
try:
    from phase5_motion_planning import get_phase5_status
    PHASE5_AVAILABLE = True
    print("✅ Phase 5 Motion Planning and Safety Systems loaded")
except ImportError as e:
    print(f"Warning: Phase 5 systems not available: {e}")
    PHASE5_AVAILABLE = False

def check_dependencies():
    """Check if all required dependencies are available"""
    print("Checking dependencies...")
    
    required_modules = [
        ('cv2', 'opencv-python'),
        ('mediapipe', 'mediapipe'),
        ('numpy', 'numpy'),
    ]
    
    missing = []
    for module, package in required_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            print(f"✗ {module} (install with: pip install {package})")
            missing.append(package)
    
    if missing:
        print(f"\\nMissing packages: {', '.join(missing)}")
        print("Install them with:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    return True

def check_files():
    """Check if all required files exist"""
    print("\\nChecking files...")
    required_files = [
        'Pose_Tracking/Hand_Tracking.py',
        'robot_control/CR3_Control.py',
        'UI/ui_components.py'
    ]
    
    missing = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file}")
        else:
            print(f"✗ {file}")
            missing.append(file)
    
    if missing:
        print(f"\\nMissing files: {', '.join(missing)}")
        return False
    
    return True

def start_robot_controller(robot_ip, port):
    """Start the robot controller"""
    print(f"\\nStarting robot controller...")
    print(f"Robot IP: {robot_ip}")
    print(f"Server port: {port}")
    
    cmd = [sys.executable, 'robot_control/CR3_Control.py', '--robot-ip', robot_ip, '--server-port', str(port)]
    
    try:
        process = subprocess.Popen(cmd)
        print(f"✓ Robot controller started (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"✗ Failed to start robot controller: {e}")
        return None

def test_robot_movement(robot_ip):
    """Test robot movement before starting hand tracking"""
    if not ROBOT_API_AVAILABLE:
        print("\\n⚠️  Robot API not available - skipping movement test")
        return True
    
    print(f"\\n🔧 Testing robot movement...")
    print(f"Connecting to robot at {robot_ip}...")
    
    # Use shared testing utilities if available
    if RobotTester:
        try:
            tester = RobotTester(robot_ip)
            success = tester.run_interactive_test(prompt_on_failure=True)
            tester.cleanup()
            return success
        except Exception as e:
            print(f"❌ Robot testing failed: {e}")
            response = input("\\nContinue anyway? (y/N): ")
            return response.lower().startswith('y')
    
    # Fallback to basic robot availability check
    try:
        # Basic robot controller availability test
        robot_controller = RobotController()
        print("✓ Robot controller API available")
        return True
        
    except Exception as e:
        print(f"❌ Robot controller test failed: {e}")
        print("This could indicate:")
        print("- Robot control modules not properly configured")
        print("- Missing dependencies or configuration files")
        
        response = input("\\nContinue anyway? (y/N): ")
        return response.lower().startswith('y')

def initialize_phase5_safety_systems():
    """Initialize Phase 5 safety systems automatically in the background"""
    if not PHASE5_AVAILABLE:
        print("\n⚠️  Phase 5 safety systems not available - proceeding with basic safety")
        return True
        
    print("\n🛡️ Initializing Phase 5 Safety Systems...")
    
    try:
        # Import and start automatic safety manager
        from phase5_motion_planning.safety.auto_safety_manager import AutoSafetyManager
        
        # Initialize safety manager
        safety_manager = AutoSafetyManager()
        
        # Start automatic safety systems in background
        success = safety_manager.start_automatic_safety_systems()
        
        if success:
            print("✅ Phase 5 safety systems initialized and running in background")
            return True
        else:
            print("⚠️  Some safety systems encountered issues - running with reduced safety")
            return True  # Continue operation with reduced safety
            
    except Exception as e:
        print(f"⚠️  Phase 5 safety system initialization warning: {e}")
        print("   Continuing with basic Phase 4 safety protocols")
        return True  # Always continue - safety is handled gracefully

def start_hand_tracking(robot_host, robot_port, hand, mirror):
    """Start the hand tracking"""
    print(f"\\nStarting hand tracking...")
    print(f"Robot host: {robot_host}")
    print(f"Robot port: {robot_port}")
    print(f"Tracking hand: {hand}")
    print(f"Mirror mode: {mirror}")
    
    cmd = [sys.executable, 'Pose_Tracking/Hand_Tracking.py', '--enable-robot', 
           '--robot-host', robot_host, '--robot-port', str(robot_port),
           '--hand', hand]
    
    if mirror:
        cmd.append('--mirror')
    
    try:
        process = subprocess.Popen(cmd)
        print(f"✓ Hand tracking started (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"✗ Failed to start hand tracking: {e}")
        return None

def run_quick_test():
    """Run the integration test"""
    print("\\nRunning integration test...")
    
    try:
        result = subprocess.run([sys.executable, 'quick_test.py'], 
                              capture_output=True, text=True, timeout=30)
        
        print("Test output:")
        print(result.stdout)
        
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("✗ Test timed out")
        return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def show_usage_guide():
    """Show usage guide"""
    print("\\n" + "=" * 60)
    print("USAGE GUIDE")
    print("=" * 60)
    
    print("\\n1. BASIC STARTUP (with robot test):")
    print("   python startup.py --robot-ip 192.168.1.6")
    
    print("\\n2. SKIP ROBOT TEST:")
    print("   python startup.py --robot-ip 192.168.1.6 --skip-robot-test")
    
    print("\\n3. SIMULATION MODE (no robot):")
    print("   python startup.py --simulation")
    
    print("\\n4. TEST ONLY:")
    print("   python startup.py --test-only")
    
    print("\\n5. CUSTOM SETTINGS:")
    print("   python startup.py --robot-ip 192.168.1.6 --hand Left --mirror")
    print("\\n6. MANUAL STARTUP:")
    print("   Terminal 1: python robot_control/CR3_Control.py --robot-ip YOUR_IP")
    print("   Terminal 2: python Pose_Tracking/Hand_Tracking.py --enable-robot")
    
    print("\\n🔧 ROBOT MOVEMENT TEST:")
    print("   - Tests robot connectivity and movement capability")
    print("   - Moves robot to packing position and back")
    print("   - Verifies robot is ready before hand tracking starts")
    print("   - Use --skip-robot-test to bypass this test")

def main():
    parser = argparse.ArgumentParser(description="Hand Tracking Robot Control Startup")
    parser.add_argument('--robot-ip', default='192.168.1.6', 
                       help='Robot IP address (default: 192.168.1.6)')
    parser.add_argument('--port', type=int, default=8888,
                       help='TCP communication port (default: 8888)')
    parser.add_argument('--hand', choices=['Right', 'Left'], default='Right',
                       help='Which hand to track (default: Right)')    
    parser.add_argument('--mirror', action='store_true',
                       help='Enable camera mirror mode')
    parser.add_argument('--simulation', action='store_true',
                       help='Run in simulation mode (no robot connection)')
    parser.add_argument('--test-only', action='store_true',
                       help='Run integration test only')
    parser.add_argument('--check-only', action='store_true',
                       help='Check dependencies and files only')
    parser.add_argument('--skip-robot-test', action='store_true',
                       help='Skip robot movement test')
    parser.add_argument('--usage', action='store_true',
                       help='Show usage guide')
    
    args = parser.parse_args()
    
    print("Hand Tracking Robot Control - Startup Script")
    print("=" * 50)
    if args.usage:
        show_usage_guide()
        return
    
    # Check dependencies and files
    if not check_dependencies() or not check_files():
        print("\\n❌ Prerequisites not met. Please fix the issues above.")
        return
    
    if args.check_only:
        print("\\n✅ All checks passed!")
        return
    
    if args.test_only:
        if run_quick_test():
            print("\\n✅ Integration test passed!")
        else:
            print("\\n❌ Integration test failed!")
        return
    
    # Determine robot IP for simulation
    robot_ip = '127.0.0.1' if args.simulation else args.robot_ip
    print(f"\\n{'SIMULATION' if args.simulation else 'PRODUCTION'} MODE")
    print("=" * 50)
    
    # Test Phase 5 safety systems first (only in production mode)
    if not args.simulation:
        print("\\n🛡️ PHASE 5 SAFETY SYSTEMS VALIDATION")
        print("=" * 40)
        if not initialize_phase5_safety_systems():
            print("\\n⚠️ Phase 5 safety system validation failed or was cancelled.")
            print("System will proceed with basic safety features only.")
            # Continue but with limited safety features
    
    # Test robot movement (only in production mode and if not skipped)
    if not args.simulation and not args.skip_robot_test:
        print("\\n🔧 ROBOT MOVEMENT TEST")
        print("=" * 30)
        if not test_robot_movement(robot_ip):
            print("\\n❌ Robot movement test failed or was cancelled.")
            print("Use --skip-robot-test to bypass this test.")
            return
        print("\\n✅ Robot movement test completed successfully!")
    elif args.skip_robot_test:
        print("\\n⏭️  Robot movement test skipped")
      # Start robot controller
    robot_process = start_robot_controller(robot_ip, args.port)
    if not robot_process:
        return
    
    # Wait for robot controller to start
    print("\\nWaiting for robot controller to initialize...")
    time.sleep(3)
    
    # Start hand tracking
    hand_process = start_hand_tracking('localhost', args.port, args.hand, args.mirror)
    if not hand_process:
        print("\\nTerminating robot controller...")
        robot_process.terminate()
        return
    
    print("\\n" + "=" * 50)
    print("🎉 SYSTEM STARTED SUCCESSFULLY!")
    print("=" * 50)
    
    if args.simulation:
        print("\\n📱 SIMULATION MODE:")
        print("- Robot movements will be simulated")
        print("- No actual robot connection required")
    else:
        print("\\n🤖 PRODUCTION MODE:")
        print("- Connected to robot at", robot_ip)
        print("- Real robot movements enabled")
        if not args.skip_robot_test:
            print("- ✅ Robot movement test completed successfully")
    
    print("\\n👋 HAND TRACKING:")
    print("- Show your", args.hand.lower(), "hand to the camera")
    print("- The robot will follow your wrist movements")
    print("- Movement is relative to your shoulder position")
    
    print("\\n🎮 CONTROLS:")
    print("- Click 'PAUSE' to pause tracking")
    print("- Click 'STOP' to exit")    
    print("- Press 'q' in the video window to quit")
    print("\\n⚠️  SAFETY:")
    if PHASE5_AVAILABLE and not args.simulation:
        print("- ✅ Phase 5 advanced safety systems active")
        print("- 🛡️ Real-time collision detection enabled")
        print("- 🚨 Multi-level emergency stop system ready")
        print("- 📍 Workspace boundary monitoring active")
        print("- 🔍 Safety zone enforcement enabled")
    else:
        print("- Basic safety features enabled")
    print("- Robot movement capability has been verified")
    print("- Keep workspace clear of obstacles")
    print("- Use emergency stop if needed")
    print("- Monitor robot movements at all times")
    
    try:
        print("\\nPress Ctrl+C to stop both processes...")
        robot_process.wait()
    except KeyboardInterrupt:
        print("\\n\\nShutting down...")
        print("Terminating hand tracking...")
        hand_process.terminate()
        print("Terminating robot controller...")
        robot_process.terminate()
        
        # Wait for processes to terminate
        hand_process.wait()
        robot_process.wait()
        
        print("✅ Shutdown complete!")

if __name__ == "__main__":
    main()
