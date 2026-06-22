"""
Test runner.

Usage:
    python -m test.run_tests

Or run individual test files directly:
    python test/test_cleanup.py
    python test/test_features.py
"""

if __name__ == '__main__':
    import subprocess, sys, os, time

    start_time = time.time()

    tests = [
        'test_cleanup.py',
        'test_features.py',
        'test_util.py',
        'test_candle_series.py',
        'test_data_aggregation.py',
        'test_position.py',
        'test_reset_sub.py',
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

    print(f"  Total time: {time.time() - start_time:.2f} seconds")

    sys.exit(0 if all(ok for _, ok in results) else 1)
