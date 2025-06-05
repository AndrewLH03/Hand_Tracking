# Documentation Archive

This folder contains selected original test files that have been preserved for reference and documentation purposes. These files were part of the original testing framework before it was consolidated into the four main test files (test_robot.py, test_communication.py, test_performance.py, and test_runner.py).

## Files in this Archive

### benchmark.py

Original performance benchmarking script that provided detailed metrics for:
- Coordinate transformation performance
- Network communication throughput
- System resource usage

This script served as the foundation for the more comprehensive `test_performance.py`.

### robot_utils_test.py

Comprehensive test suite for the `robot_utils.py` module, including:
- API availability testing
- Connection testing
- Network connectivity testing
- Response parsing
- Robot control testing

This was consolidated into the robot testing functionality in `test_robot.py`.

### simple_robot_utils_test.py

A simplified example of using the `robot_utils.py` module, demonstrating:
- Basic connection testing
- Network connectivity checking
- Simple robot control

This file provides a good starting point for understanding how to use the `robot_utils.py` module.

### test_suite.py

The original comprehensive test suite that combined all testing capabilities:
- Basic import tests
- Coordinate transformation tests
- TCP communication tests
- Integration tests
- Robot utilities tests
- Test robot controller

This was the foundation for the current modular testing framework.

## Usage Notes

These files are preserved for reference only and should not be used directly. The current testing framework provides all the same functionality in a more modular and maintainable format.

For current testing, please use:
- `test_robot.py` - For robot-related tests
- `test_communication.py` - For communication-related tests
- `test_performance.py` - For performance benchmarking
- `test_runner.py` - Main entry point for all tests
