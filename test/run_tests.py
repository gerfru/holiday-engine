#!/usr/bin/env python3
# run_tests.py - Simple test runner for Holiday Engine
import os
import sys
import subprocess

def run_tests():
    """Run all tests in the test directory"""
    
    print("🧪 Holiday Engine Test Bench")
    print("=" * 50)
    
    # Change to test directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(test_dir)
    
    # Try to run with pytest first
    try:
        print("🔍 Trying to run with pytest...")
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "test_pytest_bench.py", 
            "-v", "--tb=short"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Pytest execution successful!")
            print(result.stdout)
            return True
        else:
            print("❌ Pytest failed:")
            print(result.stdout)
            print(result.stderr)
            
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️ Pytest not available or timed out")
    
    # Fallback: run the test file directly
    print("\n🔄 Running tests directly...")
    try:
        result = subprocess.run([
            sys.executable, "test_pytest_bench.py"
        ], capture_output=True, text=True, timeout=30)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def run_individual_tests():
    """Run individual test files for comparison"""
    
    print("\n🔍 Running Individual Test Files:")
    print("=" * 40)
    
    test_files = [
        ("test_nearest_simple.py", "Distance calculation test"),
        ("test_port_soller.py", "Port de Soller test"),
        ("test_simple_lookup.py", "Normalization test"),
        ("test_comparison.py", "Simplified approach test")
    ]
    
    results = []
    
    for filename, description in test_files:
        if os.path.exists(filename):
            print(f"\n📋 {description} ({filename}):")
            try:
                result = subprocess.run([
                    sys.executable, filename
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print("✅ Passed")
                    # Show last few lines of output
                    lines = result.stdout.strip().split('\n')
                    for line in lines[-3:]:
                        if line.strip():
                            print(f"   {line}")
                    results.append(True)
                else:
                    print("❌ Failed")
                    print(f"   {result.stderr}")
                    results.append(False)
                    
            except subprocess.TimeoutExpired:
                print("⏰ Timed out")
                results.append(False)
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append(False)
        else:
            print(f"⚠️ {filename} not found")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n📊 Individual Tests: {passed}/{total} passed")
    
    return passed == total

if __name__ == "__main__":
    print("🚀 Starting Holiday Engine Test Suite")
    
    # Run pytest tests
    pytest_success = run_tests()
    
    # Run individual tests  
    individual_success = run_individual_tests()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 Test Suite Summary:")
    print(f"   Pytest tests: {'✅ PASSED' if pytest_success else '❌ FAILED'}")
    print(f"   Individual tests: {'✅ PASSED' if individual_success else '❌ FAILED'}")
    
    if pytest_success and individual_success:
        print("\n🎉 All tests passed! Your simplified resolver is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        sys.exit(1)