#!/usr/bin/env python3
"""
Communication Test Module

This module provides testing for all communication aspects:
- TCP/IP server communication
- Hand tracking data transmission
- Robot control protocol testing

It can be run independently or through the test_runner.py script.

Usage:
    python test_communication.py --help                # Show all options
    python test_communication.py --server              # Test server connection
    python test_communication.py --protocol            # Test communication protocol
    python test_communication.py --continuous          # Run continuous data transmission test
    python test_communication.py --all                 # Run all communication tests
"""

import sys
import os
import time
import argparse
import json
import socket
import threading
import queue
from typing import Dict, Tuple, List, Any, Optional

# Add the parent directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class CommunicationTester:
    """Unified communication testing class"""
    
    def __init__(self, host="localhost", port=8888):
        self.host = host
        self.port = port
        self.test_results = {}
        self.running = False
        
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test results"""
        self.test_results[test_name] = {"passed": passed, "message": message}
        status = "✓" if passed else "✗"
        print(f"  {status} {test_name}: {message}")
    
    def test_server_connection(self) -> bool:
        """Test connection to the robot control server"""
        print("\n=== SERVER CONNECTION TEST ===")
        print("This test requires CR3_Control.py or CR3_Control_Test.py to be running")
        
        try:
            # Try to connect to the robot control server
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(3)  # 3 second timeout
            
            try:
                client_socket.connect((self.host, self.port))
                self.log_result("Server connection", True, f"Connected to server at {self.host}:{self.port}")
                client_socket.close()
                return True
                
            except socket.timeout:
                self.log_result("Server connection", False, f"Timeout connecting to {self.host}:{self.port}")
                return False
                
            except ConnectionRefusedError:
                self.log_result("Server connection", False, f"Connection refused by {self.host}:{self.port}")
                return False
                
        except Exception as e:
            self.log_result("Server connection", False, f"Error: {e}")
            return False
    
    def test_protocol(self) -> bool:
        """Test the communication protocol"""
        print("\n=== COMMUNICATION PROTOCOL TEST ===")
        
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
                return False
            
            # Test connection to server if possible
            if self.test_server_connection():
                # Try to send a test message
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(3)
                    client_socket.connect((self.host, self.port))
                    
                    message = json.dumps(test_message) + '\n'
                    client_socket.send(message.encode('utf-8'))
                    self.log_result("Message transmission", True, "Successfully sent test message")
                    
                    client_socket.close()
                    
                except Exception as e:
                    self.log_result("Message transmission", False, f"Error sending message: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.log_result("Protocol test", False, f"Error: {e}")
            return False
    
    def run_continuous_test(self, duration=10, interval=0.1):
        """Run continuous data transmission test"""
        print(f"\n=== CONTINUOUS COMMUNICATION TEST ({duration}s) ===")
        
        if not self.test_server_connection():
            print("Cannot connect to server. Please start the server first.")
            return False
        
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((self.host, self.port))
            
            self.running = True
            sent_count = 0
            start_time = time.time()
            
            print(f"Sending test data every {interval}s for {duration}s...")
            
            while time.time() - start_time < duration and self.running:
                # Generate test coordinates
                test_coordinates = {
                    "timestamp": time.time(),
                    "shoulder": [0.5 + (time.time() % 0.2), 0.3, 0.2],
                    "wrist": [0.6, 0.4 + (time.time() % 0.2), 0.3]
                }
                
                # Send the message
                message = json.dumps(test_coordinates) + '\n'
                client_socket.send(message.encode('utf-8'))
                sent_count += 1
                
                # Print progress every 10 messages
                if sent_count % 10 == 0:
                    elapsed = time.time() - start_time
                    print(f"  Sent {sent_count} messages ({sent_count/elapsed:.1f} msg/s)")
                
                # Wait for the next interval
                time.sleep(interval)
            
            elapsed_time = time.time() - start_time
            message_rate = sent_count / elapsed_time
            
            print(f"\nTest completed: Sent {sent_count} messages in {elapsed_time:.1f}s ({message_rate:.1f} msg/s)")
            self.log_result("Continuous transmission", True, 
                          f"Sent {sent_count} messages at {message_rate:.1f} msg/s")
            
            client_socket.close()
            return True
            
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
            self.running = False
            return False
            
        except Exception as e:
            self.log_result("Continuous test", False, f"Error: {e}")
            self.running = False
            return False
    
    def run_all_tests(self, include_continuous=False) -> bool:
        """Run all communication tests"""
        print("\n=== RUNNING ALL COMMUNICATION TESTS ===")
        
        # Run server connection test
        server_result = self.test_server_connection()
        
        # Run protocol test
        protocol_result = self.test_protocol()
        
        # Run continuous test if requested
        continuous_result = True
        if include_continuous and server_result:
            continuous_result = self.run_continuous_test(duration=5)
        
        # Print summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["passed"])
        
        print("\n=== COMMUNICATION TEST SUMMARY ===")
        print(f"Total tests: {total_tests}")
        print(f"Passed tests: {passed_tests}")
        
        return server_result and protocol_result and continuous_result

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Communication Test Module")
    parser.add_argument("--host", type=str, default="localhost", help="Server host address")
    parser.add_argument("--port", type=int, default=8888, help="Server port")
    parser.add_argument("--server", action="store_true", help="Test server connection")
    parser.add_argument("--protocol", action="store_true", help="Test communication protocol")
    parser.add_argument("--continuous", action="store_true", help="Run continuous data transmission test")
    parser.add_argument("--duration", type=int, default=10, help="Duration for continuous test (seconds)")
    parser.add_argument("--interval", type=float, default=0.1, help="Interval between messages (seconds)")
    parser.add_argument("--all", action="store_true", help="Run all communication tests")
    
    args = parser.parse_args()
    
    # Create a communication tester
    tester = CommunicationTester(args.host, args.port)
    
    # Run tests
    if args.server or args.all:
        tester.test_server_connection()
        
    if args.protocol or args.all:
        tester.test_protocol()
        
    if args.continuous or args.all:
        tester.run_continuous_test(args.duration, args.interval)
        
    if not (args.server or args.protocol or args.continuous or args.all):
        parser.print_help()

if __name__ == "__main__":
    main()
