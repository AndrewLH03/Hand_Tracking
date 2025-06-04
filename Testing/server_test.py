#!/usr/bin/env python3
"""
Robot Server Communication Test

This script tests communication with a running robot controller server.
Use this to verify that the robot control server is working correctly.

Requirements:
- CR3_Control.py or CR3_Control_Test.py must be running
- Server must be listening on specified port (default: 8888)

Usage:
    python server_test.py                          # Test with default settings
    python server_test.py --host 192.168.1.100    # Test remote robot
    python server_test.py --port 9999             # Test different port
    python server_test.py --continuous            # Send continuous test data
"""

import argparse
import json
import socket
import time
import threading
from typing import List, Dict, Any

class RobotServerTest:
    """Test communication with robot control server"""
    
    def __init__(self, host: str = 'localhost', port: int = 8888):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to robot control server"""
        try:
            print(f"Attempting to connect to robot server at {self.host}:{self.port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print("✓ Successfully connected to robot control server")
            return True
            
        except ConnectionRefusedError:
            print("✗ Connection refused - robot control server not running")
            return False
        except socket.timeout:
            print("✗ Connection timeout - server not responding")
            return False
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from server"""
        if self.socket:
            self.socket.close()
            self.connected = False
            print("Disconnected from server")
            
    def send_coordinate_data(self, shoulder: List[float], wrist: List[float]) -> bool:
        """Send coordinate data to server"""
        if not self.connected:
            print("Not connected to server")
            return False
            
        try:
            message = {
                "timestamp": time.time(),
                "shoulder": shoulder,
                "wrist": wrist
            }
            
            data = json.dumps(message) + '\n'
            self.socket.send(data.encode('utf-8'))
            return True
            
        except Exception as e:
            print(f"Failed to send data: {e}")
            return False
            
    def run_basic_test(self) -> bool:
        """Run basic communication test"""
        print("\n=== Basic Communication Test ===")
        
        if not self.connect():
            return False
            
        # Test coordinate sets
        test_data = [
            {"name": "Center position", "shoulder": [0.5, 0.5, 0.5], "wrist": [0.5, 0.5, 0.5]},
            {"name": "Right reach", "shoulder": [0.4, 0.5, 0.5], "wrist": [0.7, 0.5, 0.5]},
            {"name": "Left reach", "shoulder": [0.6, 0.5, 0.5], "wrist": [0.3, 0.5, 0.5]},
            {"name": "Forward reach", "shoulder": [0.5, 0.5, 0.6], "wrist": [0.5, 0.5, 0.3]},
            {"name": "Upward reach", "shoulder": [0.5, 0.6, 0.5], "wrist": [0.5, 0.3, 0.5]},
        ]
        
        print(f"Sending {len(test_data)} coordinate sets...")
        
        for i, data in enumerate(test_data):
            success = self.send_coordinate_data(data["shoulder"], data["wrist"])
            if success:
                print(f"✓ Sent {data['name']}: shoulder{data['shoulder']} -> wrist{data['wrist']}")
            else:
                print(f"✗ Failed to send {data['name']}")
                
            time.sleep(0.5)  # Brief pause between sends
            
        self.disconnect()
        print("✓ Basic communication test completed")
        return True
        
    def run_continuous_test(self, duration: int = 30):
        """Run continuous data transmission test"""
        print(f"\n=== Continuous Test ({duration} seconds) ===")
        
        if not self.connect():
            return False
            
        print("Sending continuous coordinate data...")
        print("(Simulating hand movement)")
        
        start_time = time.time()
        count = 0
        
        try:
            while time.time() - start_time < duration:
                # Simulate hand movement in a circle
                t = (time.time() - start_time) * 2  # 2 rad/sec
                
                # Fixed shoulder
                shoulder = [0.5, 0.5, 0.5]
                
                # Moving wrist in circular pattern
                import math
                wrist = [
                    0.5 + 0.1 * math.cos(t),  # X: ±0.1 around center
                    0.5 + 0.1 * math.sin(t),  # Y: ±0.1 around center
                    0.5                        # Z: constant
                ]
                
                if self.send_coordinate_data(shoulder, wrist):
                    count += 1
                    if count % 10 == 0:  # Print every 10th message
                        print(f"Sent {count} messages, wrist at ({wrist[0]:.2f}, {wrist[1]:.2f}, {wrist[2]:.2f})")
                else:
                    break
                    
                time.sleep(0.1)  # 10 Hz update rate
                
        except KeyboardInterrupt:
            print("\nContinuous test interrupted by user")
            
        self.disconnect()
        print(f"✓ Continuous test completed - sent {count} messages")
        
    def run_stress_test(self, messages: int = 1000):
        """Run stress test with rapid message sending"""
        print(f"\n=== Stress Test ({messages} messages) ===")
        
        if not self.connect():
            return False
            
        print("Sending rapid-fire coordinate data...")
        
        start_time = time.time()
        success_count = 0
        
        for i in range(messages):
            # Generate random-ish coordinates
            import random
            shoulder = [0.5, 0.5, 0.5]
            wrist = [
                0.3 + 0.4 * random.random(),  # X: 0.3 to 0.7
                0.3 + 0.4 * random.random(),  # Y: 0.3 to 0.7
                0.3 + 0.4 * random.random()   # Z: 0.3 to 0.7
            ]
            
            if self.send_coordinate_data(shoulder, wrist):
                success_count += 1
            else:
                break
                
            if (i + 1) % 100 == 0:
                print(f"Progress: {i + 1}/{messages} messages sent")
                
        elapsed = time.time() - start_time
        rate = success_count / elapsed if elapsed > 0 else 0
        
        self.disconnect()
        print(f"✓ Stress test completed:")
        print(f"  Messages sent: {success_count}/{messages}")
        print(f"  Time elapsed: {elapsed:.1f} seconds")
        print(f"  Message rate: {rate:.1f} messages/second")

def main():
    parser = argparse.ArgumentParser(description="Robot Server Communication Test")
    parser.add_argument("--host", default="localhost", help="Server host address")
    parser.add_argument("--port", type=int, default=8888, help="Server port")
    parser.add_argument("--continuous", action="store_true", help="Run continuous test")
    parser.add_argument("--stress", action="store_true", help="Run stress test")
    parser.add_argument("--duration", type=int, default=30, help="Duration for continuous test (seconds)")
    parser.add_argument("--messages", type=int, default=1000, help="Number of messages for stress test")
    
    args = parser.parse_args()
    
    print("ROBOT SERVER COMMUNICATION TEST")
    print("=" * 40)
    print(f"Target: {args.host}:{args.port}")
    print("Make sure CR3_Control.py or CR3_Control_Test.py is running!")
    
    tester = RobotServerTest(args.host, args.port)
    
    try:
        if args.continuous:
            tester.run_continuous_test(args.duration)
        elif args.stress:
            tester.run_stress_test(args.messages)
        else:
            # Run basic test by default
            tester.run_basic_test()
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        tester.disconnect()
    except Exception as e:
        print(f"Test failed with error: {e}")
        tester.disconnect()

if __name__ == "__main__":
    main()
