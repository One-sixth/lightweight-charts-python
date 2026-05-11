"""
Test runner.

Usage:
    python -m test.run_tests

Or run individual test files directly:
    python test/test_cleanup.py
    python test/test_features.py
"""

if __name__ == '__main__':
    import subprocess, sys, os

    tests = [
        'test_cleanup.py',
        'test_features.py',
        'test_util.py',
    ]

    results = []
    for t in tests:
        print(f"\n--- Running {t} ---")
        ret = subprocess.run([sys.executable, t], cwd=os.path.dirname(__file__))
        ok = ret.returncode == 0
        results.append((t, ok))

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    print(f"  {passed}/{len(results)} test suites passed")
    for name, ok in results:
        mark = "PASS" if ok else "FAIL"
        print(f"    [{mark}] {name}")
    print("=" * 60)

    sys.exit(0 if all(ok for _, ok in results) else 1)
