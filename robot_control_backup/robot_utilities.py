#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot Control Utilities

Consolidates utility functions that were scattered across multiple modules.
Eliminates redundancy by providing shared functionality for all robot control modules.
"""

import time
import re
from typing import Any, List, Union, Tuple, Optional, Dict


def parse_api_response(response: Any, extract_mode: str = "numbers") -> Any:
    """
    Generic API response parser helper method to reduce redundant parsing logic
    
    Args:
        response: Raw API response
        extract_mode: What to extract ("numbers", "first_number", "status", "raw")
        
    Returns:
        Parsed data based on extract_mode
    """
    if not response:
        return None
        
    response_str = str(response).strip()
    
    if extract_mode == "raw":
        return response_str
    elif extract_mode == "status":
        # Extract status code from response
        if "," in response_str:
            parts = response_str.split(",")
            try:
                return int(parts[0])
            except (ValueError, IndexError):
                return None
        return None
    elif extract_mode == "first_number":
        # Extract first numeric value
        numbers = re.findall(r'-?\d+\.?\d*', response_str)
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                return None
        return None
    elif extract_mode == "numbers":
        # Extract all numeric values
        numbers = re.findall(r'-?\d+\.?\d*', response_str)
        try:
            return [float(n) for n in numbers]
        except ValueError:
            return []
    
    return response_str


def wait_with_progress(message: str, wait_time: float, interval: float = 0.5) -> None:
    """
    Wait with progress indication
    
    Args:
        message: Message to display
        wait_time: Total time to wait (seconds)
        interval: Update interval (seconds)
    """
    print(f"{message}...")
    total_dots = int(wait_time / interval)
    
    for i in range(total_dots):
        time.sleep(interval)
        print(".", end="", flush=True)
    
    print(" ✅")


def execute_robot_command(api_instance: Any, command: str, *args, **kwargs) -> Tuple[bool, str, Any]:
    """
    Execute a robot command with error handling and response parsing
    
    Args:
        api_instance: Robot API instance (dashboard or feedback)
        command: Command name to execute
        *args: Command arguments
        **kwargs: Command keyword arguments
        
    Returns:
        (success, message, response): Success flag, status message, and raw response
    """
    if api_instance is None:
        return False, "API instance is None", None
    
    if not hasattr(api_instance, command):
        return False, f"Command '{command}' not found in API", None
    
    try:
        method = getattr(api_instance, command)
        
        # Execute command with arguments
        if args or kwargs:
            response = method(*args, **kwargs)
        else:
            response = method()
        
        # Parse response to check for errors
        if response is not None:
            response_str = str(response).strip()
            
            # Check for common error patterns
            if "error" in response_str.lower() or "fail" in response_str.lower():
                return False, f"Command failed: {response_str}", response
            
            # Check for numeric error codes (assuming 0 = success)
            numbers = parse_api_response(response, "numbers")
            if numbers and len(numbers) > 0:
                error_code = int(numbers[0])
                if error_code != 0:
                    return False, f"Command returned error code: {error_code}", response
        
        return True, "Command executed successfully", response
        
    except Exception as e:
        return False, f"Exception executing command '{command}': {str(e)}", None


def format_position(position: List[float], precision: int = 1) -> str:
    """
    Format position for display
    
    Args:
        position: Position array [x, y, z, rx, ry, rz]
        precision: Decimal precision
        
    Returns:
        Formatted position string
    """
    if len(position) < 6:
        return "Invalid position"
    
    return (f"X={position[0]:.{precision}f}, Y={position[1]:.{precision}f}, "
            f"Z={position[2]:.{precision}f}, RX={position[3]:.{precision}f}, "
            f"RY={position[4]:.{precision}f}, RZ={position[5]:.{precision}f}")


def validate_position_values(position: List[float], 
                           position_limits: Optional[Dict[str, Tuple[float, float]]] = None) -> Tuple[bool, str]:
    """
    Validate position values against limits
    
    Args:
        position: Position to validate [x, y, z, rx, ry, rz]
        position_limits: Optional limits dict with keys 'x', 'y', 'z', 'rx', 'ry', 'rz'
        
    Returns:
        (valid, message): Whether position is valid and reason if not
    """
    if len(position) < 6:
        return False, "Position must have 6 values [x, y, z, rx, ry, rz]"
    
    # Check for NaN or infinite values
    for i, val in enumerate(position):
        if not isinstance(val, (int, float)) or not (-1e6 < val < 1e6):
            labels = ['X', 'Y', 'Z', 'RX', 'RY', 'RZ']
            return False, f"Invalid {labels[i]} value: {val}"
    
    # Check against limits if provided
    if position_limits:
        labels = ['x', 'y', 'z', 'rx', 'ry', 'rz']
        for i, label in enumerate(labels):
            if label in position_limits:
                min_val, max_val = position_limits[label]
                if not (min_val <= position[i] <= max_val):
                    return False, f"{label.upper()} value {position[i]} outside limits [{min_val}, {max_val}]"
    
    return True, "Position valid"


def calculate_movement_time(start_pos: List[float], end_pos: List[float], 
                          speed: float = 100.0) -> float:
    """
    Estimate movement time based on distance and speed
    
    Args:
        start_pos: Starting position [x, y, z, rx, ry, rz]
        end_pos: Ending position [x, y, z, rx, ry, rz]  
        speed: Movement speed (mm/s or deg/s)
        
    Returns:
        Estimated time in seconds
    """
    if len(start_pos) < 3 or len(end_pos) < 3:
        return 5.0  # Default fallback
    
    # Calculate 3D distance for position
    pos_distance = sum((end_pos[i] - start_pos[i])**2 for i in range(3))**0.5
    
    # Calculate angular distance for orientation (if available)
    ang_distance = 0.0
    if len(start_pos) >= 6 and len(end_pos) >= 6:
        ang_distance = sum((end_pos[i] - start_pos[i])**2 for i in range(3, 6))**0.5
    
    # Estimate time (position dominates, add some for angular movement)
    estimated_time = max(pos_distance / speed, ang_distance / (speed * 0.1))
    
    # Add safety margin and minimum time
    return max(estimated_time * 1.5 + 1.0, 2.0)


def retry_operation(operation_func, max_retries: int = 3, retry_delay: float = 1.0, 
                   operation_name: str = "operation") -> Tuple[bool, Any, str]:
    """
    Retry an operation with exponential backoff
    
    Args:
        operation_func: Function to retry (should return (success, result))
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (doubles each attempt)
        operation_name: Name for logging purposes
        
    Returns:
        (success, result, message): Final success status, result, and message
    """
    last_error = ""
    
    for attempt in range(max_retries):
        try:
            success, result = operation_func()
            if success:
                if attempt > 0:
                    print(f"✅ {operation_name} succeeded on attempt {attempt + 1}")
                return True, result, f"{operation_name} successful"
            else:
                last_error = f"Attempt {attempt + 1} failed: {result}"
                
        except Exception as e:
            last_error = f"Attempt {attempt + 1} exception: {str(e)}"
        
        # Wait before retry (exponential backoff)
        if attempt < max_retries - 1:
            delay = retry_delay * (2 ** attempt)
            print(f"⏳ {operation_name} failed, retrying in {delay:.1f}s... ({last_error})")
            time.sleep(delay)
    
    return False, None, f"{operation_name} failed after {max_retries} attempts. Last error: {last_error}"


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float with fallback
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert value to int with fallback
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Int value or default
    """
    try:
        return int(float(value))  # Convert through float to handle "1.0" strings
    except (ValueError, TypeError):
        return default
