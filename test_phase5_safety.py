#!/usr/bin/env python3
"""
Phase 5 Safety Systems Test Script

This script provides a comprehensive test of all Phase 5 safety systems
without requiring the full startup.py to work.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_phase5_safety_systems():
    """Test Phase 5 safety systems independently"""
    print("🛡️ PHASE 5 SAFETY SYSTEMS TEST")
    print("=" * 50)
    
    try:
        # Test imports
        print("\n📦 Testing imports...")
        from phase5_motion_planning.safety import (
            SafetySystemTester, SafetyMonitor, CollisionDetector, 
            EmergencyStop, get_safety_status, initialize_safety_systems
        )
        print("✅ All safety imports successful")
        
        # Test package status
        print("\n📊 Checking safety package status...")
        status = get_safety_status()
        for component, state in status.items():
            status_icon = "✅" if state == "READY" else "🔄" if state == "INITIALIZING" else "❌"
            print(f"   {status_icon} {component.replace('_', ' ').title()}: {state}")
        
        # Initialize safety systems
        print("\n🔧 Initializing safety systems...")
        init_result = initialize_safety_systems()
        if init_result:
            print("✅ Safety systems initialized successfully")
        else:
            print("❌ Safety systems initialization failed")
            return False
        
        # Test SafetySystemTester
        print("\n🧪 Testing SafetySystemTester...")
        try:
            tester = SafetySystemTester()
            print("✅ SafetySystemTester instantiated successfully")
            
            # Test each component
            print("\n🔍 Running comprehensive safety tests...")
            
            # 1. Collision Detection Test
            print("   📡 Testing collision detection...")
            collision_result = tester.test_collision_detection()
            if collision_result.success:
                print(f"   ✅ Collision detection: {collision_result.message}")
            else:
                print(f"   ❌ Collision detection failed: {collision_result.message}")
            
            # 2. Safety Monitor Test
            print("   🛡️ Testing safety monitor...")
            monitor_result = tester.test_safety_monitor()
            if monitor_result.success:
                print(f"   ✅ Safety monitor: {monitor_result.message}")
            else:
                print(f"   ❌ Safety monitor failed: {monitor_result.message}")
            
            # 3. Emergency Stop Test
            print("   🚨 Testing emergency stop...")
            emergency_result = tester.test_emergency_stop()
            if emergency_result.success:
                print(f"   ✅ Emergency stop: {emergency_result.message}")
            else:
                print(f"   ❌ Emergency stop failed: {emergency_result.message}")
            
            # 4. Workspace Boundaries Test
            print("   📐 Testing workspace boundaries...")
            workspace_result = tester.test_workspace_boundaries()
            if workspace_result.success:
                print(f"   ✅ Workspace boundaries: {workspace_result.message}")
            else:
                print(f"   ❌ Workspace boundaries failed: {workspace_result.message}")
            
            # 5. Safety Zones Test
            print("   🔺 Testing safety zones...")
            zone_result = tester.test_safety_zones()
            if zone_result.success:
                print(f"   ✅ Safety zones: {zone_result.message}")
            else:
                print(f"   ❌ Safety zones failed: {zone_result.message}")
            
            # 6. Integration Test
            print("   🔗 Testing Phase 4 integration...")
            integration_result = tester.test_integration()
            if integration_result.success:
                print(f"   ✅ Phase 4 integration: {integration_result.message}")
            else:
                print(f"   ❌ Phase 4 integration failed: {integration_result.message}")
            
            # Summary
            all_tests = [
                collision_result, monitor_result, emergency_result,
                workspace_result, zone_result, integration_result
            ]
            
            passed_tests = sum(1 for test in all_tests if test.success)
            total_tests = len(all_tests)
            
            print(f"\n📈 TEST RESULTS: {passed_tests}/{total_tests} tests passed")
            
            if passed_tests == total_tests:
                print("🎉 ALL PHASE 5 SAFETY TESTS PASSED!")
                print("🛡️ Advanced safety systems are fully operational")
                return True
            else:
                print(f"⚠️ {total_tests - passed_tests} tests failed")
                print("🔧 Phase 5 safety systems need attention")
                return False
                
        except Exception as e:
            print(f"❌ SafetySystemTester error: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure Phase 5 safety systems are properly installed")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_individual_components():
    """Test individual safety components"""
    print("\n🔧 INDIVIDUAL COMPONENT TESTS")
    print("=" * 40)
    
    try:
        from phase5_motion_planning.safety import CollisionDetector, SafetyMonitor, EmergencyStop
        
        # Test CollisionDetector
        print("\n📡 Testing CollisionDetector...")
        try:
            detector = CollisionDetector()
            print("✅ CollisionDetector instantiated")
            # Add basic functionality test here if needed
        except Exception as e:
            print(f"❌ CollisionDetector error: {e}")
        
        # Test SafetyMonitor
        print("\n🛡️ Testing SafetyMonitor...")
        try:
            monitor = SafetyMonitor()
            print("✅ SafetyMonitor instantiated")
            # Add basic functionality test here if needed
        except Exception as e:
            print(f"❌ SafetyMonitor error: {e}")
        
        # Test EmergencyStop
        print("\n🚨 Testing EmergencyStop...")
        try:
            emergency = EmergencyStop()
            print("✅ EmergencyStop instantiated")
            # Add basic functionality test here if needed
        except Exception as e:
            print(f"❌ EmergencyStop error: {e}")
            
        print("\n✅ Individual component tests completed")
        
    except Exception as e:
        print(f"❌ Component test error: {e}")

def main():
    """Main test function"""
    print("Phase 5 Safety Systems - Standalone Test")
    print("=" * 60)
    
    # Test the full safety system
    safety_result = test_phase5_safety_systems()
    
    # Test individual components
    test_individual_components()
    
    # Final summary
    print("\n" + "=" * 60)
    if safety_result:
        print("🎉 PHASE 5 SAFETY SYSTEMS: FULLY OPERATIONAL")
        print("🛡️ Ready for production use")
    else:
        print("⚠️ PHASE 5 SAFETY SYSTEMS: NEEDS ATTENTION")
        print("🔧 Check individual component status")
    
    print("\n📋 Next Steps:")
    if safety_result:
        print("- ✅ Safety systems are ready")
        print("- 🚀 Can proceed with Day 3 dashboard implementation")
        print("- 🔗 Integration with startup.py can continue")
    else:
        print("- 🔧 Fix any failed safety tests")
        print("- 🛠️ Review component configurations")
        print("- ⚠️ Do not proceed to production without safety validation")

if __name__ == "__main__":
    main()
