#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration Logger - Centralized logging for migration process

Provides robust logging capabilities that don't rely on terminal output,
making debugging and testing more reliable across different environments.
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class MigrationLogger:
    """
    Centralized logger for migration process with file and console output
    """
    
    def __init__(self, name: str = "migration", log_dir: str = None):
        self.name = name
        
        # Create log directory
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create file handler
        log_file = self.log_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.log_file_path = str(log_file)
        self.logger.info(f"Migration logger initialized - Log file: {self.log_file_path}")
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """Log critical message"""
        self.logger.critical(message)
    
    def test_start(self, test_name: str):
        """Log test start"""
        self.info(f"🚀 Starting test: {test_name}")
        self.info("=" * 60)
    
    def test_end(self, test_name: str, success: bool):
        """Log test end"""
        status = "✅ PASSED" if success else "❌ FAILED"
        self.info(f"🏁 Test completed: {test_name} - {status}")
        self.info("=" * 60)
    
    def phase_start(self, phase_name: str):
        """Log phase start"""
        self.info(f"📋 Phase started: {phase_name}")
        self.info("-" * 50)
    
    def phase_end(self, phase_name: str, success: bool):
        """Log phase end"""
        status = "✅ COMPLETED" if success else "❌ FAILED"
        self.info(f"📊 Phase finished: {phase_name} - {status}")
        self.info("-" * 50)
    
    def step(self, message: str):
        """Log a step"""
        self.info(f"🔧 {message}")
    
    def result(self, message: str, success: bool):
        """Log a result"""
        icon = "✅" if success else "❌"
        self.info(f"{icon} {message}")
    
    def metrics(self, metrics: Dict[str, Any]):
        """Log metrics"""
        self.info("📊 Metrics:")
        for key, value in metrics.items():
            self.info(f"  {key}: {value}")
    
    def get_log_content(self) -> str:
        """Get current log file content"""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading log file: {e}"
    
    def save_test_results(self, results: Dict[str, Any]):
        """Save test results to separate file"""
        results_file = self.log_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            import json
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            self.info(f"📄 Test results saved to: {results_file}")
        except Exception as e:
            self.error(f"Failed to save test results: {e}")


def get_logger(name: str = "migration") -> MigrationLogger:
    """
    Get a logger instance (backward compatibility function)
    
    Args:
        name: Logger name
        
    Returns:
        MigrationLogger instance
    """
    return MigrationLogger(name)


def setup_logging(name: str = "migration", log_dir: str = None) -> MigrationLogger:
    """
    Setup logging (backward compatibility function)
    
    Args:
        name: Logger name
        log_dir: Log directory path
        
    Returns:
        MigrationLogger instance
    """
    return MigrationLogger(name, log_dir)


# Global logger instance
migration_logger = MigrationLogger()

# Convenience functions
def log_info(message: str):
    migration_logger.info(message)

def log_debug(message: str):
    migration_logger.debug(message)

def log_warning(message: str):
    migration_logger.warning(message)

def log_error(message: str):
    migration_logger.error(message)

def log_step(message: str):
    migration_logger.step(message)

def log_result(message: str, success: bool):
    migration_logger.result(message, success)

def log_metrics(metrics: Dict[str, Any]):
    migration_logger.metrics(metrics)


if __name__ == "__main__":
    # Test the logger
    print("🧪 Testing Migration Logger...")
    
    logger = MigrationLogger("test")
    
    logger.test_start("Logger Test")
    logger.phase_start("Basic Logging")
    
    logger.info("This is an info message")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    logger.step("Testing step logging")
    logger.result("Step completed successfully", True)
    logger.result("Step failed", False)
    
    logger.metrics({
        'test_count': 5,
        'success_rate': 0.8,
        'avg_time': 1.234
    })
    
    logger.phase_end("Basic Logging", True)
    logger.test_end("Logger Test", True)
    
    print(f"Log file created at: {logger.log_file_path}")
    print("✅ Logger test completed successfully")
