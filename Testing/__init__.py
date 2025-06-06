#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testing Package for Robot Control System

Simplified testing utilities package that provides robot testing functionality
for startup.py and robot_preflight_check.py

This package eliminates code duplication by providing shared testing utilities.
"""

from .robot_testing_utils import (
    RobotTester,
    quick_robot_test,
    full_robot_test,
    interactive_robot_test
)

__all__ = [
    'RobotTester',
    'quick_robot_test', 
    'full_robot_test',
    'interactive_robot_test'
]
