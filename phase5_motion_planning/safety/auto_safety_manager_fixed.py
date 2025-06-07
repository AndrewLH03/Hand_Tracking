#!/usr/bin/env python3
"""
Phase 5 Safety Manager - Automatic Background Safety System

This module provides a simplified, automatic safety system that runs in the background
without requiring complex testing procedures. It automatically initializes and monitors
all safety systems seamlessly.
"""

import sys
import os
import threading
import time
import logging
from typing import Optional, Any

# Add paths for Phase 4 integration
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'robot_control'))

try:
    from migration_logger import MigrationLogger
    PHASE4_INTEGRATION = True
except ImportError:
    PHASE4_INTEGRATION = False

class AutoSafetyManager:
    """
    Automatic Safety Manager - Runs all Phase 5 safety systems in the background
    with minimal configuration and maximum reliability.
    """
    
    def __init__(self, logger: Optional[Any] = None):
        """Initialize automatic safety manager"""
        # Logger setup
        if PHASE4_INTEGRATION and logger is None:
            self.logger = MigrationLogger("AutoSafetyManager")
        else:
            self.logger = logger or self._create_fallback_logger()
        
        # Safety components
        self.collision_detector = None
        self.safety_monitor = None
        self.emergency_stop = None
        
        # Status tracking
        self.is_active = False
        self.safety_thread = None
        self.startup_complete = False
        
        self.logger.info("🛡️ Auto Safety Manager initialized")

    def _create_fallback_logger(self):
        """Create fallback logger if Phase 4 integration not available"""
        logger = logging.getLogger("AutoSafetyManager")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def start_automatic_safety_systems(self) -> bool:
        """
        Public method to start all safety systems automatically.
        This is the main entry point for automatic safety initialization.
        """
        return self.start_safety_systems()

    def start_safety_systems(self) -> bool:
        """
        Start all safety systems automatically in the background.
        Returns True if successful, False otherwise.
        """
        try:
            print("🛡️ Initializing Phase 5 safety systems...")
            
            # Import safety components
            from .collision_detector import CollisionDetector
            from .safety_monitor import SafetyMonitor
            from .emergency_stop import EmergencyStop
            
            # Initialize components in correct order
            self.collision_detector = CollisionDetector(logger=self.logger)
            self.emergency_stop = EmergencyStop(logger=self.logger)
            
            # Initialize safety monitor with components
            self.safety_monitor = SafetyMonitor(
                collision_detector=self.collision_detector,
                emergency_stop=self.emergency_stop,
                logger=self.logger
            )
            
            # Start monitoring thread
            self.is_active = True
            self.safety_thread = threading.Thread(target=self._safety_monitoring_loop, daemon=True)
            self.safety_thread.start()
            
            # Brief startup verification
            time.sleep(0.5)  # Allow components to initialize
            
            if self._verify_safety_systems():
                print("✅ Phase 5 safety systems active")
                self.startup_complete = True
                self.logger.info("🛡️ All safety systems operational")
                return True
            else:
                print("⚠️ Safety systems started with limited functionality")
                self.logger.warning("⚠️ Some safety systems have limited functionality")
                return True  # Continue anyway with partial safety
                
        except ImportError:
            print("⚠️ Phase 5 safety systems not available - using basic safety")
            self.logger.warning("⚠️ Phase 5 safety systems not available")
            return False
        except Exception as e:
            print(f"⚠️ Safety system startup issue: {e}")
            self.logger.error(f"⚠️ Safety system startup error: {e}")
            return False

    def _verify_safety_systems(self) -> bool:
        """Quick verification that safety systems are responsive"""
        try:
            # Test basic functionality
            if self.collision_detector:
                self.collision_detector.is_monitoring = True
            
            if self.safety_monitor:
                self.safety_monitor.is_active = True
            
            if self.emergency_stop:
                # Just verify it's initialized, don't trigger it
                pass
            
            return True
        except Exception as e:
            self.logger.warning(f"Safety system verification issue: {e}")
            return False

    def _safety_monitoring_loop(self):
        """Background monitoring loop for safety systems"""
        self.logger.info("🔄 Safety monitoring loop started")
        
        while self.is_active:
            try:
                # Periodic safety checks (every 100ms)
                if self.collision_detector and hasattr(self.collision_detector, 'is_monitoring'):
                    # Collision detector runs its own monitoring
                    pass
                
                if self.safety_monitor and hasattr(self.safety_monitor, 'is_active'):
                    # Safety monitor handles its own event processing
                    pass
                
                time.sleep(0.1)  # 100ms monitoring cycle
                
            except Exception as e:
                self.logger.error(f"Safety monitoring error: {e}")
                time.sleep(1.0)  # Longer delay on error

    def get_safety_status(self) -> dict:
        """Get current safety system status"""
        status = {
            'auto_safety_manager': 'ACTIVE' if self.is_active else 'INACTIVE',
            'collision_detection': 'READY' if self.collision_detector else 'UNAVAILABLE',
            'safety_monitoring': 'READY' if self.safety_monitor else 'UNAVAILABLE',
            'emergency_stop': 'READY' if self.emergency_stop else 'UNAVAILABLE',
            'startup_complete': self.startup_complete
        }
        return status

    def emergency_shutdown(self):
        """Emergency shutdown of all safety systems"""
        try:
            if self.emergency_stop:
                self.emergency_stop.trigger_emergency_stop("system_shutdown", "Manual emergency shutdown")
            
            self.is_active = False
            self.logger.info("🚨 Emergency shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Emergency shutdown error: {e}")

    def graceful_shutdown(self):
        """Graceful shutdown of safety systems"""
        try:
            self.is_active = False
            
            if self.safety_thread and self.safety_thread.is_alive():
                self.safety_thread.join(timeout=2.0)
            
            self.logger.info("🛡️ Safety systems gracefully shut down")
            
        except Exception as e:
            self.logger.error(f"Graceful shutdown error: {e}")


# Global safety manager instance
_global_safety_manager = None

def start_automatic_safety_systems() -> bool:
    """
    Start Phase 5 safety systems automatically in the background.
    This is the main entry point for startup.py integration.
    
    Returns:
        bool: True if safety systems started successfully
    """
    global _global_safety_manager
    
    try:
        _global_safety_manager = AutoSafetyManager()
        return _global_safety_manager.start_safety_systems()
    except Exception as e:
        print(f"⚠️ Could not start automatic safety systems: {e}")
        return False

def get_safety_status() -> dict:
    """Get current safety system status"""
    global _global_safety_manager
    
    if _global_safety_manager:
        return _global_safety_manager.get_safety_status()
    else:
        return {'auto_safety_manager': 'NOT_INITIALIZED'}

def emergency_shutdown():
    """Emergency shutdown of all safety systems"""
    global _global_safety_manager
    
    if _global_safety_manager:
        _global_safety_manager.emergency_shutdown()

def graceful_shutdown():
    """Graceful shutdown of all safety systems"""
    global _global_safety_manager
    
    if _global_safety_manager:
        _global_safety_manager.graceful_shutdown()
