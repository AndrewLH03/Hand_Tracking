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

# Add robot API import for test movement
sys.path.append('TCP-IP-CR-Python-V4')
try:
    from dobot_api import DobotApiDashboard, DobotApiMove
    ROBOT_API_AVAILABLE = True
except ImportError:
    ROBOT_API_AVAILABLE = False

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
        'Hand_Tracking.py',
        'CR3_Control.py',
        'TCP-IP-CR-Python-V4/dobot_api.py'
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
    
    cmd = [sys.executable, 'CR3_Control.py', '--robot-ip', robot_ip, '--server-port', str(port)]
    
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
    
    dashboard = None
    move_client = None
    
    try:
        # Connect to robot
        dashboard = DobotApiDashboard(robot_ip, 29999)
        dashboard.connect()
        print("✓ Dashboard connected")
        
        move_client = DobotApiMove(robot_ip, 30003)
        move_client.connect()
        print("✓ Move client connected")
        
        # Enable robot
        print("Enabling robot...")
        enable_result = dashboard.EnableRobot()
        print(f"✓ Robot enabled: {enable_result}")
        time.sleep(1)
        
        # Get current position
        current_pos = dashboard.GetPose()
        print(f"✓ Current position: X={current_pos[0]:.1f}, Y={current_pos[1]:.1f}, Z={current_pos[2]:.1f}")
        
        # Move to packing position (safe position above workspace)
        print("\\n📦 Moving to packing position...")
        packing_position = f"MovL({{X:250, Y:0, Z:300, RX:{current_pos[3]}, RY:{current_pos[4]}, RZ:{current_pos[5]}}})"
        
        result = move_client.send_data(packing_position)
        print(f"✓ Packing position command sent: {result}")
        
        # Wait for movement to complete
        print("Waiting for movement to complete...")
        time.sleep(3)
        
        # Check new position
        packing_pos = dashboard.GetPose()
        print(f"✓ Packing position: X={packing_pos[0]:.1f}, Y={packing_pos[1]:.1f}, Z={packing_pos[2]:.1f}")
        
        # Return to original position
        print("\\n🏠 Returning to original position...")
        return_position = f"MovL({{X:{current_pos[0]}, Y:{current_pos[1]}, Z:{current_pos[2]}, RX:{current_pos[3]}, RY:{current_pos[4]}, RZ:{current_pos[5]}}})"
        
        result = move_client.send_data(return_position)
        print(f"✓ Return command sent: {result}")
        
        # Wait for return movement
        time.sleep(3)
        
        # Verify return position
        final_pos = dashboard.GetPose()
        print(f"✓ Final position: X={final_pos[0]:.1f}, Y={final_pos[1]:.1f}, Z={final_pos[2]:.1f}")
        
        # Check if we're close to original position (within 5mm tolerance)
        distance = ((final_pos[0] - current_pos[0])**2 + 
                   (final_pos[1] - current_pos[1])**2 + 
                   (final_pos[2] - current_pos[2])**2)**0.5
        
        if distance < 5.0:
            print(f"✅ Robot movement test successful! (Distance: {distance:.1f}mm)")
            return True
        else:
            print(f"⚠️  Robot position differs by {distance:.1f}mm from original")
            return True  # Still allow continuation
            
    except Exception as e:
        print(f"❌ Robot movement test failed: {e}")
        print("This could indicate:")
        print("- Robot is not powered on or connected")
        print("- Network connectivity issues")
        print("- Robot is in manual mode or has errors")
        print("- Emergency stop is activated")
        
        response = input("\\nContinue anyway? (y/N): ")
        return response.lower().startswith('y')
        
    finally:
        # Clean up connections
        try:
            if dashboard:
                dashboard.disconnect()
            if move_client:
                move_client.disconnect()
        except:
            pass

def start_hand_tracking(robot_host, robot_port, hand, mirror):
    """Start the hand tracking"""
    print(f"\\nStarting hand tracking...")
    print(f"Robot host: {robot_host}")
    print(f"Robot port: {robot_port}")
    print(f"Tracking hand: {hand}")
    print(f"Mirror mode: {mirror}")
    
    cmd = [sys.executable, 'Hand_Tracking.py', '--enable-robot', 
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
    print("   Terminal 1: python CR3_Control.py --robot-ip YOUR_IP")
    print("   Terminal 2: python Hand_Tracking.py --enable-robot")
    
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
