#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Utilities Module

Consolidated utility functions from robot_utilities.py, robot_connection.py,
and other modules to eliminate duplication and provide shared functionality.

Features:
- API response parsing
- Progress tracking utilities
- Position validation and formatting
- Movement calculations
- Error handling helpers
"""

import time
import re
import math
from typing import Any, List, Union, Tuple, Optional, Dict, Callable


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
        if numbers:
            try:
                return [float(num) for num in numbers]
            except ValueError:
                return None
        return None
    else:
        return response_str


def wait_with_progress(description: str, duration: float, check_interval: float = 0.5, 
                      check_func: Optional[Callable] = None) -> Tuple[bool, float]:
    """
    Wait for a specified duration with progress indication and optional condition checking
    
    Args:
        description: Description of what we're waiting for
        duration: How long to wait (seconds)
        check_interval: How often to check condition (seconds)
        check_func: Optional function to check if we can stop waiting early
        
    Returns:
        (success, actual_wait_time): Whether condition was met and actual wait time
    """
    start_time = time.time()
    elapsed = 0
    
    print(f"⏳ {description}...")
    
    while elapsed < duration:
        time.sleep(min(check_interval, duration - elapsed))
        elapsed = time.time() - start_time
        
        # Check condition if provided
        if check_func and check_func():
            print(f"✅ {description} completed early (after {elapsed:.1f}s)")
            return True, elapsed
        
        # Show progress
        progress = min(elapsed / duration, 1.0) * 100
        print(f"    Progress: {progress:.1f}% ({elapsed:.1f}/{duration}s)", end='\r')
    
    print(f"\n✅ {description} completed (after {elapsed:.1f}s)")
    return True, elapsed


def execute_robot_command(dashboard, command_name: str, *args, **kwargs) -> Tuple[bool, str, Any]:
    """
    Execute a robot command with proper error handling and response parsing
    
    Args:
        dashboard: Robot dashboard API object
        command_name: Name of the command to execute
        *args: Positional arguments for the command
        **kwargs: Keyword arguments for the command
        
    Returns:
        (success, message, response): Command execution result
    """
    try:
        if not hasattr(dashboard, command_name):
            return False, f"Command '{command_name}' not available", None
        
        command_func = getattr(dashboard, command_name)
        
        # Execute command
        response = command_func(*args, **kwargs)
        
        # Parse response for status
        status = parse_api_response(response, "status")
        
        if status == 0:
            return True, f"Command '{command_name}' executed successfully", response
        else:
            return False, f"Command '{command_name}' failed with status {status}", response
            
    except Exception as e:
        return False, f"Command '{command_name}' failed: {e}", None


def format_position(position: List[float], precision: int = 2) -> str:
    """
    Format position coordinates for display
    
    Args:
        position: Position coordinates [x,y,z,rx,ry,rz]
        precision: Decimal places to show
        
    Returns:
        Formatted position string
    """
    if not position or len(position) < 6:
        return "Invalid position"
    
    return (f"X:{position[0]:.{precision}f} Y:{position[1]:.{precision}f} Z:{position[2]:.{precision}f} "
            f"RX:{position[3]:.{precision}f} RY:{position[4]:.{precision}f} RZ:{position[5]:.{precision}f}")


def validate_position_values(position: List[float], limits: Dict[str, Tuple[float, float]] = None) -> Tuple[bool, str]:
    """
    Validate position values are within acceptable ranges
    
    Args:
        position: Position coordinates [x,y,z,rx,ry,rz]
        limits: Optional position limits dict with keys 'x','y','z','rx','ry','rz'
        
    Returns:
        (valid, message): Whether position is valid and validation message
    """
    if not position or len(position) < 6:
        return False, "Position must have 6 coordinates [x,y,z,rx,ry,rz]"
    
    # Check for invalid values
    for i, coord in enumerate(position):
        if not isinstance(coord, (int, float)) or math.isnan(coord) or math.isinf(coord):
            coord_names = ['x', 'y', 'z', 'rx', 'ry', 'rz']
            return False, f"Invalid {coord_names[i]} coordinate: {coord}"
    
    # Check limits if provided
    if limits:
        coord_names = ['x', 'y', 'z', 'rx', 'ry', 'rz']
        for i, coord in enumerate(position):
            coord_name = coord_names[i]
            if coord_name in limits:
                min_val, max_val = limits[coord_name]
                if coord < min_val or coord > max_val:
                    return False, f"{coord_name} coordinate {coord} outside limits [{min_val}, {max_val}]"
    
    return True, "Position values are valid"


def calculate_distance_3d(pos1: List[float], pos2: List[float]) -> float:
    """
    Calculate 3D Euclidean distance between two positions
    
    Args:
        pos1: First position [x,y,z,...]
        pos2: Second position [x,y,z,...]
        
    Returns:
        Distance in mm
    """
    if len(pos1) < 3 or len(pos2) < 3:
        return float('inf')
    
    return math.sqrt(sum((pos1[i] - pos2[i])**2 for i in range(3)))


def calculate_movement_time(distance: float, speed: float = 100.0) -> float:
    """
    Calculate estimated movement time based on distance and speed
    
    Args:
        distance: Distance to travel (mm)
        speed: Movement speed (mm/s)
        
    Returns:
        Estimated time (seconds)
    """
    if speed <= 0:
        return float('inf')
    
    # Add acceleration/deceleration overhead (roughly 20% extra time)
    base_time = distance / speed
    return base_time * 1.2


def validate_position_tolerance(current_pos: List[float], target_pos: List[float], 
                               tolerance: float = 5.0) -> Tuple[bool, float]:
    """
    Validate if current position is within tolerance of target position
    
    Args:
        current_pos: Current position [x,y,z,rx,ry,rz]
        target_pos: Target position [x,y,z,rx,ry,rz]
        tolerance: Acceptable distance tolerance (mm)
        
    Returns:
        (within_tolerance, distance): Whether position is within tolerance and actual distance
    """
    if len(current_pos) < 3 or len(target_pos) < 3:
        return False, float('inf')
    
    distance = calculate_distance_3d(current_pos, target_pos)
    return distance < tolerance, distance


def normalize_coordinates(coordinates: List[float], source_range: Tuple[float, float], 
                         target_range: Tuple[float, float]) -> List[float]:
    """
    Normalize coordinates from one range to another
    
    Args:
        coordinates: Input coordinates
        source_range: (min, max) of source range
        target_range: (min, max) of target range
        
    Returns:
        Normalized coordinates
    """
    source_min, source_max = source_range
    target_min, target_max = target_range
    
    source_span = source_max - source_min
    target_span = target_max - target_min
    
    normalized = []
    for coord in coordinates:
        if source_span == 0:
            normalized.append(target_min)
        else:
            # Normalize to 0-1 range, then scale to target range
            norm_value = (coord - source_min) / source_span
            scaled_value = target_min + (norm_value * target_span)
            normalized.append(scaled_value)
    
    return normalized


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp a value to be within specified bounds
    
    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Clamped value
    """
    return max(min_val, min(value, max_val))


def interpolate_positions(start_pos: List[float], end_pos: List[float], 
                         t: float) -> List[float]:
    """
    Linearly interpolate between two positions
    
    Args:
        start_pos: Starting position
        end_pos: Ending position
        t: Interpolation parameter (0.0 to 1.0)
        
    Returns:
        Interpolated position
    """
    t = clamp_value(t, 0.0, 1.0)
    
    if len(start_pos) != len(end_pos):
        raise ValueError("Positions must have same dimensions")
    
    return [start_pos[i] + t * (end_pos[i] - start_pos[i]) 
            for i in range(len(start_pos))]


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float with fallback
    
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


def safe_list_conversion(value: Any, expected_length: int = 6, 
                        default: float = 0.0) -> List[float]:
    """
    Safely convert a value to a list of floats
    
    Args:
        value: Value to convert (list, tuple, string, etc.)
        expected_length: Expected length of result list
        default: Default value for missing elements
        
    Returns:
        List of floats with expected length
    """
    result = [default] * expected_length
    
    try:
        if isinstance(value, (list, tuple)):
            for i, v in enumerate(value[:expected_length]):
                result[i] = safe_float_conversion(v, default)
        elif isinstance(value, str):
            # Try to parse as comma-separated values
            parts = value.split(',')
            for i, part in enumerate(parts[:expected_length]):
                result[i] = safe_float_conversion(part.strip(), default)
        else:
            # Single value - put in first position
            result[0] = safe_float_conversion(value, default)
    except Exception:
        pass  # Return default-filled list
    
    return result


def create_position_dict(position: List[float]) -> Dict[str, float]:
    """
    Convert position list to named dictionary
    
    Args:
        position: Position coordinates [x,y,z,rx,ry,rz]
        
    Returns:
        Dictionary with named coordinates
    """
    names = ['x', 'y', 'z', 'rx', 'ry', 'rz']
    result = {}
    
    for i, name in enumerate(names):
        if i < len(position):
            result[name] = position[i]
        else:
            result[name] = 0.0
    
    return result


def format_time_duration(seconds: float) -> str:
    """
    Format time duration in human-readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted time string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def generate_move_command_string(position: List[float], speed: float = 100.0) -> str:
    """
    Generate robot move command string
    
    Args:
        position: Target position [x,y,z,rx,ry,rz]
        speed: Movement speed percentage (0-100)
        
    Returns:
        Formatted move command string
    """
    if len(position) < 6:
        position.extend([0.0] * (6 - len(position)))
    
    return (f"MovL({position[0]:.2f},{position[1]:.2f},{position[2]:.2f},"
            f"{position[3]:.2f},{position[4]:.2f},{position[5]:.2f},speedL={speed})")


# Common robot workspace limits (in mm)
DEFAULT_WORKSPACE_LIMITS = {
    'x': (-400.0, 400.0),
    'y': (-400.0, 400.0), 
    'z': (0.0, 400.0),
    'rx': (-180.0, 180.0),
    'ry': (-180.0, 180.0),
    'rz': (-180.0, 180.0)
}

# Common safe positions
SAFE_POSITIONS = {
    'home': [200.0, 0.0, 200.0, 0.0, 0.0, 0.0],
    'packing': [200.0, 200.0, 100.0, 0.0, 90.0, 0.0],
    'observation': [0.0, -300.0, 300.0, 0.0, 0.0, 0.0],
    'service': [0.0, 0.0, 400.0, 0.0, 0.0, 0.0]
}
