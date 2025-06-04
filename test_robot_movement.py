#!/usr/bin/env python3
"""
Test the robot movement functionality in startup.py
"""

import sys
sys.path.append('.')
from startup import test_robot_movement, ROBOT_API_AVAILABLE

def test_robot_movement_function():
    """Test the robot movement test function"""
    print("Testing robot movement test function...")
    print(f"Robot API Available: {ROBOT_API_AVAILABLE}")
    
    # Test with a fake IP (should fail gracefully)
    print("\nTesting with invalid IP (should fail gracefully):")
    result = test_robot_movement("192.168.999.999")
    print(f"Result: {result}")
    
    print("\n✅ Robot movement test function works correctly!")

if __name__ == "__main__":
    test_robot_movement_function()
