# Hand Tracking Robot Control System

Real-time control of a DoBot CR3 robot using hand tracking via MediaPipe computer vision. This system tracks hand and pose landmarks to control robot movement in 3D space.

**Version:** 2.0  
**Status:** Production Ready  
**Last Updated:** June 2025

## 🚀 Quick Start

### Option 1: Automated Startup (with robot test)
```bash
python startup.py --robot-ip 192.168.1.6
```

### Option 2: Automated Startup (skip robot test)
```bash
python startup.py --robot-ip 192.168.1.6 --skip-robot-test
```

### Option 3: Manual Startup (with hardware)
```bash
# Terminal 1 - Robot Controller
python robot_control/CR3_Control.py --robot-ip 192.168.1.6

# Terminal 2 - Hand Tracking
python robot_control/Hand_Tracking.py --enable-robot
```

### Option 4: Test Mode (no hardware required)
```bash
# Terminal 1 - Test Robot Controller
python Testing/test_runner.py --robot

# Terminal 2 - Hand Tracking
python robot_control/Hand_Tracking.py --enable-robot
```

## 📋 System Overview

### Core Components

| File | Purpose | Hardware Required |
|------|---------|-------------------|
| `robot_control/Hand_Tracking.py` | MediaPipe hand tracking + camera | Camera |
| `robot_control/CR3_Control.py` | Real robot controller | DoBot CR3 Robot |
| `startup.py` | Automated system launcher | Optional |

### System Architecture

```
[Camera] → [robot_control/Hand_Tracking.py] → [TCP/IP] → [robot_control/CR3_Control.py] → [DoBot CR3]
    ↓           ↓                   ↓            ↓              ↓
MediaPipe   Coordinate         JSON over    Coordinate    Robot MovL
Detection   Extraction          Socket      Transform     Commands
```

### How It Works

1. **Hand Detection**: MediaPipe tracks hand and pose landmarks
2. **Coordinate Extraction**: Extract 3D positions of shoulder and wrist
3. **TCP Communication**: Send coordinates as JSON messages over network
4. **Coordinate Transformation**: Convert MediaPipe coordinates to robot space
5. **Robot Movement**: Send MovL commands to DoBot CR3 via API

## 🛠️ Installation

### Prerequisites
```bash
pip install opencv-python mediapipe numpy
```

### Robot API Setup
The DoBot CR3 API is included in `TCP-IP-CR-Python-V4/dobot_api.py`

### Network Setup
- Ensure robot and computer are on same network
- Default robot IP: `192.168.1.6`
- Default communication port: `8888`

## 🔧 Robot Movement Test

The startup script includes an automatic robot movement test to verify connectivity and functionality before starting hand tracking.

### What the Test Does
1. **Connects** to the robot at the specified IP address
2. **Enables** the robot for movement
3. **Records** the current robot position
4. **Moves** the robot to a safe packing position (X:250, Y:0, Z:300)
5. **Returns** the robot to its original position
6. **Verifies** the robot returned within 5mm tolerance

### Test Options
```bash
# Run with robot test (default)
python startup.py --robot-ip YOUR_ROBOT_IP

# Skip the robot test
python startup.py --robot-ip YOUR_ROBOT_IP --skip-robot-test

# Simulation mode (no robot test)
python startup.py --simulation
```

### Test Results
- ✅ **Success**: Robot moves correctly and is ready for hand tracking
- ❌ **Failure**: Shows specific error message and offers option to continue
- ⚠️ **Warning**: Position differs slightly but still functional

## 🔬 Pre-flight Robot Verification

**Before running the main system**, use the comprehensive robot verification script to ensure your laptop can communicate with the robot and that it accepts movement commands without errors.

### Quick Pre-flight Check
```bash
# Quick test (no movement, just connectivity and status)
python robot_preflight_check.py --robot-ip 192.168.1.6 --quick
```

### Full Pre-flight Check
```bash
# Complete test with movement verification
python robot_preflight_check.py --robot-ip 192.168.1.6

# With custom timeout
python robot_preflight_check.py --robot-ip 192.168.1.6 --timeout 15
```

### What the Pre-flight Check Does
1. **🌐 Network Connectivity**: Tests if robot is reachable on the network
2. **🔗 Robot API Connection**: Verifies dashboard and move client connections
3. **🔍 Robot Status**: Checks for alarms and clears them if possible
4. **📍 Position Reading**: Reads and validates current robot position
5. **📦 Packing Movement**: Moves robot to safe packing position (250, 0, 300)
6. **🏠 Return Movement**: Returns robot to original position
7. **🛡️ Final Status**: Confirms no alarms or errors after testing

### Pre-flight Results
- ✅ **All tests pass**: Robot is ready for hand tracking operations
- ❌ **Tests fail**: Address issues before running startup.py
- 🔧 **Specific guidance**: Each test provides detailed error information

## 📖 Usage Guide

### Hand_Tracking.py Options
```bash
python robot_control/Hand_Tracking.py --help

Options:
  --enable-robot          # Enable robot integration
  --robot-host HOST       # Robot controller host (default: localhost)
  --robot-port PORT       # Robot controller port (default: 8888)
  --hand-choice HAND      # Which hand to track: left, right, auto (default)
  --mirror-x              # Mirror X axis movement
  --camera-index INDEX    # Camera index (default: 0)
```

### CR3_Control.py Options
```bash
python robot_control/CR3_Control.py --help

Options:
  --robot-ip IP           # Robot IP address (default: 192.168.1.6)
  --server-port PORT      # TCP server port (default: 8888)
  --workspace-size SIZE   # Workspace size in mm (default: 400.0)
```

### Coordinate System

**MediaPipe Coordinates → Robot Coordinates**
- **Shoulder**: Reference point (robot base 0,0,0)
- **Wrist**: Target point (robot TCP position)
- **Mapping**: Relative wrist position from shoulder
- **Safety Bounds**: X/Y ±200mm, Z 50-400mm above table

### Interactive Controls

- **Mouse**: Click UI buttons for pause/resume/stop
- **Keyboard**: 'q' to quit, 'p' to pause/resume
- **Emergency Stop**: Close window or Ctrl+C

## 🧪 Testing & Verification

### Quick System Check
```bash
# Basic verification - test robot connectivity and utilities
python Testing/test_robot.py --connection

# Complete system test - all robot, communication, and performance tests
python Testing/test_runner.py --all

# Individual component testing
python Testing/test_robot.py --all           # Robot-specific tests
python Testing/test_communication.py --all  # TCP/IP communication tests  
python Testing/test_performance.py --all    # Performance benchmarking

# Quick connectivity check
python Testing/test_robot.py --utils
```

### Available Testing Modes

| Test Type | Command | Purpose |
|-----------|---------|---------|
| Robot Connection | `python Testing/test_robot.py --connection` | Test robot connectivity and API |
| Robot Movement | `python Testing/test_robot.py --movement` | Test robot movement capabilities |
| Robot System | `python Testing/test_robot.py --utils` | Test robot system module |
| All Robot Tests | `python Testing/test_robot.py --all` | Complete robot test suite |
| Communication | `python Testing/test_communication.py --all` | Test TCP/IP networking |
| Performance | `python Testing/test_performance.py --all` | Performance benchmarking |
| All Tests | `python Testing/test_runner.py --all` | Run all available tests |

For detailed testing documentation, see `Testing/README.md`

## 🔧 Configuration

### Robot Parameters
```python
# In CR3_Control.py
workspace_size = 400.0      # Robot reach in mm
height_offset = 200.0       # Z offset above table
movement_threshold = 5.0    # Minimum movement in mm
```

### Hand Tracking Parameters
```python
# In Hand_Tracking.py
detection_confidence = 0.5  # MediaPipe detection threshold
tracking_confidence = 0.5   # MediaPipe tracking threshold
max_hands = 2              # Maximum hands to detect
```

## 🚨 Safety Features

- **Workspace Bounds**: Configurable safe movement area (±200mm default)
- **Speed Limits**: Controlled robot movement speed
- **Height Protection**: Minimum Z height to prevent table collisions
- **Movement Threshold**: Filters out hand tremors and small movements
- **Connection Monitoring**: Automatic reconnection on network issues
- **Emergency Stop**: Multiple ways to immediately stop operation

## 🔍 Troubleshooting

### Common Issues

**Camera not detected:**
```bash
# Test different camera indices
python robot_control/Hand_Tracking.py --camera-index 1
```

**Robot connection failed:**
```bash
# Verify robot IP and network
ping 192.168.1.6
python robot_control/CR3_Control.py --robot-ip YOUR_ROBOT_IP
```

**No hand detection:**
- Ensure good lighting conditions
- Check camera permissions
- Make sure hand is clearly visible

**TCP connection issues:**
```bash
# Test with robot communication first
python Testing/test_communication.py --all
python Testing/test_robot.py --connection
```

**Import errors:**
```bash
# Verify all dependencies installed
python Testing/test_runner.py --all --quick
```

### Debug Commands
```bash
# Test coordinate transformation
python -c "from robot_control.CR3_Control import CoordinateTransformer; print('OK')"

# Test hand tracking modules  
python -c "from robot_control.Hand_Tracking import RobotClient; print('OK')"

# Test robot system
python -c "from robot_control.robot_control import RobotSystem; print('OK')"

# Full system verification
python Testing/test_runner.py --all
```

## 📁 Project Structure

```
Hand_Tracking/
├── robot_control/                 # Core robot control modules
│   ├── Hand_Tracking.py          # Main hand tracking with robot integration
│   ├── CR3_Control.py            # Robot controller (hardware required)
│   ├── robot_connection.py       # Robot connection management
│   └── robot_control.py          # Robot control and integration
├── startup.py                     # Automated startup script
├── README.md                      # This documentation
├── TCP-IP-CR-Python-V4/       # DoBot API directory
│   └── dobot_api.py           # Robot communication API
└── Testing/                   # Comprehensive testing suite
    ├── test_runner.py         # Main test runner interface
    ├── test_robot.py          # Robot-specific tests
    ├── test_communication.py  # Communication tests
    ├── test_performance.py    # Performance benchmarking
    └── README.md              # Testing documentation
```

## 🎯 Performance Specifications

### System Requirements
- **CPU**: Modern multi-core processor
- **RAM**: 4GB+ recommended
- **Camera**: USB webcam or integrated camera
- **Network**: Ethernet or WiFi connection to robot

### Performance Metrics
- **Hand Tracking**: 30+ FPS
- **Coordinate Processing**: 10,000+ transforms/second
- **TCP Throughput**: 1000+ messages/second
- **Robot Update Rate**: 10 Hz (configurable)

### Real-time Capability
The system is designed for real-time operation with sub-100ms latency from hand movement to robot response.

## 🚀 Advanced Usage

### Custom Gestures
Extend `robot_control/Hand_Tracking.py` to recognize specific hand gestures for different robot behaviors.

### Multi-Robot Control
Modify `robot_control/CR3_Control.py` to control multiple robots simultaneously.

### Workspace Calibration
Adjust coordinate transformation parameters for different working environments.

### Integration with Other Systems
The TCP communication protocol allows integration with other robotics frameworks.

## 📞 Support

### Getting Help
1. **Check error messages** - they provide specific guidance
2. **Run test suite** - `python Testing/test_runner.py --all`
3. **Test individual components** - `python Testing/test_robot.py --all`
4. **Verify hardware connections** - network, camera, robot power

### Contributing
This project provides a solid foundation for hand-controlled robotics applications. Feel free to extend and customize for your specific needs.

## 📝 Changelog

### Version 2.0 (June 2025)
- ✅ Integrated test robot controller for hardware-free testing
- ✅ Consolidated documentation into 2 comprehensive files
- ✅ Enhanced testing suite with performance benchmarking
- ✅ Added comprehensive troubleshooting guides
- ✅ Improved CLI options and user experience

### Version 1.0 (Initial Release)
- ✅ Basic hand tracking robot control functionality
- ✅ DoBot CR3 integration via TCP/IP
- ✅ MediaPipe-based hand detection
- ✅ Real-time coordinate transformation

## 📄 License

This project is provided as-is for educational and research purposes. The DoBot CR3 API is subject to its own licensing terms.

---

**🎉 Your hand tracking robot control system is ready for real-time operation!**
