"""
Feature tests: unique functionality not covered by test_cleanup.py.

Tests:
  1. DataFrame column renaming (pure Python, no window needed)
  2. Line creation returns correct objects (no window needed)
  3. Screenshot returns data (window needed)
  4. Topbar switcher fires events (window needed)
  5. Topbar button fires events (window needed)

Usage:
    python test/test_features.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
import asyncio
from lightweight_charts.util import normal_df
from lightweight_charts import Chart


def log_check(ok: bool, label: str, errors: list, err_key: str = None):
    """Unified check logging."""
    if ok:
        print(f"      [OK] {label}")
    else:
        print(f"      [FAIL] {label}")
        if err_key:
            errors.append(err_key)
    return ok


def load_bars():
    """Load OHLCV test data and normalize column names."""
    csv_path = os.path.join(os.path.dirname(__file__), '..',
                            'examples', '1_setting_data', 'ohlcv.csv')
    return pd.read_csv(csv_path).rename(columns={'date': 'time'})


# ──────────────────────────────────────────────
#  1. Data column renaming (pure Python, no UI)
# ──────────────────────────────────────────────

def test_data_column_renaming():
    sep = "=" * 60
    print(sep)
    print("  test_data_column_renaming")
    print(sep)

    chart = Chart()
    errors = []
    all_clean = True

    bars = load_bars()

    # Already lowercase with time column — should pass through
    result = normal_df(bars)
    ok = 'time' in result.columns and 'open' in result.columns
    all_clean &= log_check(ok, "lowercase columns pass through", errors, "rename_lower")

    # Index as time
    df_idx = bars.set_index('time')
    result2 = normal_df(df_idx)
    ok = 'time' in result2.columns
    all_clean &= log_check(ok, "index used as time", errors, "rename_index")

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")

    print(sep)
    chart.exit()
    return all_clean


# ──────────────────────────────────────────────
#  2. Line creation and list tracking (no UI)
# ──────────────────────────────────────────────

def test_line_list_tracking():
    sep = "=" * 60
    print(sep)
    print("  test_line_list_tracking")
    print(sep)

    chart = Chart()
    errors = []
    all_clean = True

    l1 = chart.create_line('line_a', color='#ff0000')
    l2 = chart.create_line('line_b', color='#00ff00')

    lines = chart.lines()
    all_clean &= log_check(len(lines) == 2, "lines() returns 2 lines", errors, "lines_count")
    all_clean &= log_check(lines[0] is l1, "lines()[0] matches first line", errors, "lines_first")
    all_clean &= log_check(lines[1] is l2, "lines()[1] matches second line", errors, "lines_second")
    all_clean &= log_check(l1.name == 'line_a', "line name preserved", errors, "line_name")
    all_clean &= log_check(l1.color == '#ff0000', "line color preserved", errors, "line_color")

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")

    print(sep)
    chart.exit()
    return all_clean


# ──────────────────────────────────────────────
#  3. Screenshot (needs window)
# ──────────────────────────────────────────────

def test_screenshot():
    sep = "=" * 60
    print(sep)
    print("  test_screenshot")
    print(sep)

    chart = Chart(width=400, height=300)
    bars = load_bars()
    errors = []
    all_clean = True

    try:
        chart.set(bars)
        chart.show(block=False)
        import time
        time.sleep(2)

        data = chart.screenshot()
        all_clean &= log_check(data is not None, "screenshot returns data", errors, "screenshot_none")
        all_clean &= log_check(len(data) > 1000, f"screenshot size {len(data)} bytes", errors, "screenshot_small")
        all_clean &= log_check(isinstance(data, bytes), "screenshot is bytes", errors, "screenshot_type")

    finally:
        chart.exit()

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")

    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  4. Topbar switcher event (needs window)
# ──────────────────────────────────────────────

def test_topbar_switcher():
    sep = "=" * 60
    print(sep)
    print("  test_topbar_switcher")
    print(sep)

    chart = Chart(width=400, height=300)
    errors = []
    all_clean = True
    fired = []

    def on_switch(c):
        fired.append(True)
        c.exit()

    try:
        chart.topbar.switcher('mode', ('off', 'on'), func=on_switch)
        # Queue the click script BEFORE show — it runs when the window loads
        chart.run_script(
            f'{chart.topbar["mode"].id}.intervalElements[1]'
            f'.dispatchEvent(new Event("click"))',
            run_last=True
        )
        # show(block=True) runs the event loop; callback calls exit() to unblock
        chart.show(block=True)

        all_clean &= log_check(len(fired) > 0, "switcher event fired", errors, "switcher_event")

    finally:
        chart.exit()

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")

    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  5. Topbar button event (needs window)
# ──────────────────────────────────────────────

def test_topbar_button():
    sep = "=" * 60
    print(sep)
    print("  test_topbar_button")
    print(sep)

    chart = Chart(width=400, height=300)
    errors = []
    all_clean = True
    fired = []

    def on_click(c):
        fired.append(True)
        c.exit()

    try:
        chart.topbar.button('btn', 'Click Me', func=on_click)
        chart.run_script(
            f'{chart.topbar["btn"].id}.elem.dispatchEvent(new Event("click"))',
            run_last=True
        )
        # show(block=True) runs the event loop; callback calls exit() to unblock
        chart.show(block=True)

        all_clean &= log_check(len(fired) > 0, "button event fired", errors, "button_event")

    finally:
        chart.exit()

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")

    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  Runner
# ──────────────────────────────────────────────

if __name__ == '__main__':
    results = []

    print("\n")
    results.append(('data_column_renaming', test_data_column_renaming()))
    results.append(('line_list_tracking',   test_line_list_tracking()))

    # Window-requiring tests
    results.append(('screenshot',            test_screenshot()))
    results.append(('topbar_switcher',       test_topbar_switcher()))
    results.append(('topbar_button',         test_topbar_button()))

    print("\n")
    print("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"  {passed}/{total} tests passed")
    for name, ok in results:
        mark = "PASS" if ok else "FAIL"
        print(f"    [{mark}] {name}")
    print("=" * 60)

    sys.exit(0 if all(ok for _, ok in results) else 1)
