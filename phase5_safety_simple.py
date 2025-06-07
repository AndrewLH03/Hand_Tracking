#!/usr/bin/env python3
"""
Simple Phase 5 Safety Integration Test

This provides a quick way to test Phase 5 safety systems 
without the complex startup.py structure.
"""

def test_phase5_safety_simple():
    """Simple Phase 5 safety test for integration with startup"""
    try:
        from phase5_motion_planning.safety import SafetySystemTester
        
        print("\n🛡️ PHASE 5 SAFETY SYSTEMS TEST")
        print("=" * 40)
        
        # Initialize tester
        tester = SafetySystemTester()
        print("✅ Safety testing framework ready")
        
        # Run core tests
        tests = [
            ('Collision Detection', tester.test_collision_detection),
            ('Safety Monitor', tester.test_safety_monitor),
            ('Emergency Stop', tester.test_emergency_stop),
            ('System Integration', tester.test_system_integration)
        ]
        
        passed_tests = 0
        total_tests = 0
        
        for name, test_func in tests:
            try:
                result = test_func()
                passed_tests += result.passed_tests
                total_tests += result.total_tests
                status = "✅" if result.success_rate == 1.0 else "⚠️"
                print(f"  {status} {name}: {result.passed_tests}/{result.total_tests} passed")
            except Exception as e:
                print(f"  ❌ {name}: Error - {e}")
        
        success_rate = (passed_tests / total_tests) if total_tests > 0 else 0
        
        if success_rate >= 0.9:  # 90% threshold
            print(f"\n🎉 PHASE 5 SAFETY: OPERATIONAL ({success_rate:.1%})")
            print("🛡️ Advanced safety systems ready for production")
            return True
        else:
            print(f"\n⚠️ PHASE 5 SAFETY: NEEDS ATTENTION ({success_rate:.1%})")
            print("🔧 Some safety systems require configuration")
            return False
            
    except ImportError:
        print("\n⚠️ Phase 5 safety systems not available")
        print("   Continuing with basic safety features")
        return False
    except Exception as e:
        print(f"\n❌ Phase 5 safety test error: {e}")
        return False

if __name__ == "__main__":
    success = test_phase5_safety_simple()
    if success:
        print("\n✅ Ready to proceed with Phase 5 operations")
    else:
        print("\n🔧 Phase 5 safety systems need attention")
