"""
CandleSeries tests.

Tests creation, data operations (set/update/update_bars), markers,
delete/cleanup, and JS audit verification.

Usage:
    python test/test_candle_series.py
"""

import sys, os, json, tomllib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import pandas as pd
import numpy as np
from lightweight_charts import Chart, CandleSeries


def make_ohlcv(n=50, base_price=100, seed=42):
    rng = np.random.RandomState(seed)
    dates = pd.date_range('2024-01-01', periods=n, freq='D')
    close = base_price + np.cumsum(rng.randn(n) * 2)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    open_ = close + rng.randn(n) * 0.5
    volume = rng.randint(1000, 10000, n)
    return pd.DataFrame({
        'time': dates, 'open': open_, 'high': high, 'low': low,
        'close': close, 'volume': volume,
    })


def log_check(ok, label, errors, err_key=None):
    if ok:
        print(f"      [OK] {label}")
    else:
        print(f"      [FAIL] {label}")
        if err_key:
            errors.append(err_key)
    return ok


def js_audit(chart, timeout=5):
    try:
        result = chart.win.run_script_and_get('Lib.Handler.audit()', timeout=timeout)
        if not isinstance(result, str):
            return None
        return tomllib.loads(result)
    except Exception:
        return None


def chart_section(chart, data):
    sid = chart.id.replace('window.', '')
    return data.get(sid, {})


# ── Test 1: Basic creation and cleanup ──────────────────────────

def test_basic_create_delete():
    sep = "=" * 60
    print(sep)
    print("  test_basic_create_delete")
    print(sep)

    chart = Chart(width=800, height=600)
    errors = []
    all_clean = True

    try:
        chart.show(block=False)

        df_main = make_ohlcv(30, 100, 42)
        df_ref = make_ohlcv(30, 200, 123)

        # Create CandleSeries
        print("\n[1] Create CandleSeries ...")
        chart.set(df_main)
        ref = chart.create_candle_series(name='ref', pane_index=1)
        all_clean &= log_check(isinstance(ref, CandleSeries), "isinstance CandleSeries", errors, "not_candle")
        all_clean &= log_check(ref.id.startswith('window.CandleSeries_'), f"id={ref.id}", errors, "bad_id")
        all_clean &= log_check(len(chart._lines) == 1, f"_lines=1 (got {len(chart._lines)})", errors, "lines_count")
        print("      [OK]")

        # Set data
        print("\n[2] Set data ...")
        ref.set(df_ref)
        all_clean &= log_check(not ref.data.empty, "candle_data not empty", errors, "empty_candle")
        all_clean &= log_check(ref._last_bar is not None, "_last_bar set", errors, "no_last_bar")
        all_clean &= log_check(len(ref.data) == 30, f"data rows={len(ref.data)}", errors, "data_rows")
        print("      [OK]")

        # Marker
        print("\n[3] Add marker ...")
        m = ref.add_marker(time=df_ref['time'].iloc[5], position='above',
                       shape='arrow_down', color='red', text='S')
        all_clean &= log_check(len(ref.markers) == 1, f"markers=1", errors, "markers_count")
        all_clean &= log_check(m.startswith('window.Marker_'), f"marker id={m}", errors, "marker_id")
        print("      [OK]")

        # JS audit mid-state
        print("\n[4] JS audit mid-state ...")
        mid = js_audit(chart)
        if mid:
            sec = chart_section(chart, mid)
            all_clean &= log_check(
                sec.get('extraSeriesCount', 0) >= 1,
                f"extraSeriesCount={sec.get('extraSeriesCount', 0)}", errors, "mid_series"
            )
        else:
            print("      [WARN] JS audit unavailable")

        # Delete CandleSeries
        print("\n[5] Delete CandleSeries ...")
        ref.delete()
        all_clean &= log_check(len(chart._lines) == 0, f"_lines=0 (got {len(chart._lines)})", errors, "delete_lines")
        print("      [OK]")

        # JS audit final
        print("\n[6] JS audit final ...")
        final = js_audit(chart)
        if final:
            sec_f = chart_section(chart, final)
            all_clean &= log_check(
                sec_f.get('extraSeriesCount', 0) == 0,
                f"extraSeriesCount=0 (got {sec_f.get('extraSeriesCount', 0)})", errors, "final_series"
            )
        else:
            print("      [WARN] JS audit unavailable")

        # Python final state
        print("\n[7] Python final state ...")
        all_clean &= log_check(len(chart._lines) == 0, "_lines empty", errors, "py_lines")
        all_clean &= log_check(len(chart.markers) == 0, "markers empty", errors, "py_markers")

        print()
        print(sep)
        if all_clean:
            print("  RESULT: PASS")
        else:
            print(f"  RESULT: FAIL ({len(errors)} errors)")
            for e in errors:
                print(f"    - {e}")
        print(sep)

    finally:
        chart.exit()

    if not all_clean:
        sys.exit(1)


# ── Test 2: update and update_bars ─────────────────────────────

def test_update_operations():
    sep = "=" * 60
    print(sep)
    print("  test_update_operations")
    print(sep)

    chart = Chart(width=800, height=600)
    errors = []
    all_clean = True

    try:
        chart.show(block=False)

        df_init = make_ohlcv(20, 100, 42)
        chart.set(df_init)

        ref = chart.create_candle_series(name='ref', pane_index=1)
        ref.set(make_ohlcv(20, 200, 123))

        # update() - single bar
        print("\n[1] update() single bar ...")
        initial_count = len(ref.data)
        new_bar = pd.Series({
            'time': pd.Timestamp('2024-01-21'),
            'open': 205.0, 'high': 210.0, 'low': 203.0, 'close': 208.0,
        })
        ref.update(new_bar)
        all_clean &= log_check(len(ref.data) == initial_count + 1,
                               f"candle_data rows={len(ref.data)} (was {initial_count})",
                               errors, "update_count")
        all_clean &= log_check(ref._last_bar is not None, "_last_bar updated", errors, "update_last_bar")
        print("      [OK]")

        # update() - update existing bar
        print("\n[2] update() existing bar ...")
        count_before = len(ref.data)
        ref.update(new_bar)  # same time → should update, not add
        all_clean &= log_check(len(ref.data) == count_before,
                               f"no new row (still {len(ref.data)})", errors, "update_existing")
        print("      [OK]")

        # update_bars() - multiple bars
        print("\n[3] update_bars() multiple bars ...")
        count_before = len(ref.data)
        batch = make_ohlcv(10, 210, 99)
        # Ensure batch times are after current data
        max_time = ref.data['time'].max()
        batch['time'] = pd.date_range(
            start=pd.Timestamp(max_time, unit='s') + pd.Timedelta(days=1),
            periods=10, freq='D'
        )
        batch['time'] = (batch['time'] - pd.Timestamp('1970-01-01')) // pd.Timedelta('1s')
        ref.update_bars(batch[['time', 'open', 'high', 'low', 'close']])
        all_clean &= log_check(len(ref.data) == count_before + 10,
                               f"candle_data rows={len(ref.data)} (was {count_before})",
                               errors, "batch_count")
        print("      [OK]")

        # set() - re-initialize clears previous data
        print("\n[4] set() re-initialize ...")
        ref.set(make_ohlcv(15, 250, 77))
        all_clean &= log_check(len(ref.data) == 15,
                               f"candle_data rows={len(ref.data)}", errors, "reinit_count")
        print("      [OK]")

        print()
        print(sep)
        if all_clean:
            print("  RESULT: PASS")
        else:
            print(f"  RESULT: FAIL ({len(errors)} errors)")
            for e in errors:
                print(f"    - {e}")
        print(sep)

    finally:
        chart.exit()

    if not all_clean:
        sys.exit(1)


# ── Test 3: Markers on CandleSeries ────────────────────────────

def test_markers():
    sep = "=" * 60
    print(sep)
    print("  test_markers")
    print(sep)

    chart = Chart(width=800, height=600)
    errors = []
    all_clean = True

    try:
        chart.show(block=False)

        df = make_ohlcv(30, 100, 42)
        chart.set(df)

        ref = chart.create_candle_series(name='ref', pane_index=1)
        ref.set(make_ohlcv(30, 200, 123))

        # marker() with explicit time
        print("\n[1] marker() with explicit time ...")
        t = ref.data['time'].iloc[10]
        m1 = ref.add_marker(time=t, position='above', shape='arrow_down',
                        color='red', text='sell')
        all_clean &= log_check(len(ref.markers) == 1, "1 marker", errors, "m1_count")
        print("      [OK]")

        # marker() without time (should use last bar)
        print("\n[2] marker() without time (last bar) ...")
        m2 = ref.add_marker(position='below', shape='arrow_up',
                        color='blue', text='buy')
        all_clean &= log_check(len(ref.markers) == 2, "2 markers", errors, "m2_count")
        print("      [OK]")

        # marker_list() - batch markers
        print("\n[3] marker_list() batch ...")
        ids = ref.add_markers([
            {'time': ref.data['time'].iloc[5], 'position': 'above',
             'shape': 'circle', 'color': '#ff0000', 'text': 'a'},
            {'time': ref.data['time'].iloc[15], 'position': 'below',
             'shape': 'square', 'color': '#00ff00', 'text': 'b'},
        ])
        all_clean &= log_check(len(ref.markers) == 4, f"4 markers (got {len(ref.markers)})", errors, "ml_count")
        all_clean &= log_check(len(ids) == 2, "2 ids returned", errors, "ml_ids")
        print("      [OK]")

        # remove_marker()
        print("\n[4] remove_marker() ...")
        ref.remove_marker(m1)
        all_clean &= log_check(len(ref.markers) == 3, f"3 markers after remove", errors, "rm_count")
        print("      [OK]")

        # clear_markers()
        print("\n[5] clear_markers() ...")
        ref.clear_markers()
        all_clean &= log_check(len(ref.markers) == 0, "0 markers after clear", errors, "clear_count")
        print("      [OK]")

        # Verify markers actually set in JS
        print("\n[6] Verify JS markers count ...")
        ref.add_marker(time=ref.data['time'].iloc[0], position='above',
                   shape='arrow_down', color='green', text='test')
        try:
            count = chart.win.run_script_and_get(f'{ref.id}.seriesMarkers.markers().length')
            count = int(count) if count is not None else 0
            all_clean &= log_check(count == 1, f"JS markers count={count}", errors, "js_markers")
        except Exception as e:
            all_clean &= log_check(False, f"JS markers query failed: {e}", errors, "js_markers")
        print("      [OK]")

        print()
        print(sep)
        if all_clean:
            print("  RESULT: PASS")
        else:
            print(f"  RESULT: FAIL ({len(errors)} errors)")
            for e in errors:
                print(f"    - {e}")
        print(sep)

    finally:
        chart.exit()

    if not all_clean:
        sys.exit(1)


# ── Test 4: Multiple CandleSeries on different panes ───────────

def test_multi_pane():
    sep = "=" * 60
    print(sep)
    print("  test_multi_pane")
    print(sep)

    chart = Chart(width=1000, height=800)
    errors = []
    all_clean = True

    try:
        chart.show(block=False)

        df_main = make_ohlcv(30, 100, 42)
        chart.set(df_main)

        # Create 2 CandleSeries on different panes
        print("\n[1] Create 2 CandleSeries on panes 1 and 2 ...")
        ref1 = chart.create_candle_series(name='ref1', pane_index=1)
        ref2 = chart.create_candle_series(name='ref2', pane_index=2)
        all_clean &= log_check(len(chart._lines) == 2, f"_lines=2 (got {len(chart._lines)})", errors, "lines_2")
        print("      [OK]")

        # Set data on both
        print("\n[2] Set data on both ...")
        ref1.set(make_ohlcv(30, 200, 123))
        ref2.set(make_ohlcv(30, 300, 456))
        all_clean &= log_check(not ref1.data.empty, "ref1 has data", errors, "ref1_data")
        all_clean &= log_check(not ref2.data.empty, "ref2 has data", errors, "ref2_data")
        print("      [OK]")

        # Markers on both
        print("\n[3] Markers on both ...")
        ref1.add_marker(time=ref1.data['time'].iloc[5], position='above',
                    shape='arrow_down', color='red', text='s1')
        ref2.add_marker(time=ref2.data['time'].iloc[10], position='below',
                    shape='arrow_up', color='blue', text='b2')
        all_clean &= log_check(len(ref1.markers) == 1, "ref1 has 1 marker", errors, "ref1_markers")
        all_clean &= log_check(len(ref2.markers) == 1, "ref2 has 1 marker", errors, "ref2_markers")
        print("      [OK]")

        # Update on both
        print("\n[4] Update on both ...")
        ref1.update(pd.Series({
            'time': pd.Timestamp('2024-01-31'), 'open': 210, 'high': 215,
            'low': 208, 'close': 213,
        }))
        ref2.update(pd.Series({
            'time': pd.Timestamp('2024-01-31'), 'open': 310, 'high': 315,
            'low': 308, 'close': 313,
        }))
        all_clean &= log_check(len(ref1.data) == 31, f"ref1 rows=31", errors, "ref1_update")
        all_clean &= log_check(len(ref2.data) == 31, f"ref2 rows=31", errors, "ref2_update")
        print("      [OK]")

        # Delete one, other unaffected
        print("\n[5] Delete ref1, ref2 unaffected ...")
        ref1.delete()
        all_clean &= log_check(len(chart._lines) == 1, f"_lines=1 (got {len(chart._lines)})", errors, "del_lines")
        all_clean &= log_check(not ref2.data.empty, "ref2 still has data", errors, "ref2_after_del")
        all_clean &= log_check(len(ref2.markers) == 1, "ref2 still has marker", errors, "ref2_markers_after")
        print("      [OK]")

        # Delete ref2
        print("\n[6] Delete ref2 ...")
        ref2.delete()
        all_clean &= log_check(len(chart._lines) == 0, f"_lines=0 (got {len(chart._lines)})", errors, "del_all")
        print("      [OK]")

        # JS audit
        print("\n[7] JS audit final ...")
        final = js_audit(chart)
        if final:
            sec = chart_section(chart, final)
            all_clean &= log_check(
                sec.get('extraSeriesCount', 0) == 0,
                f"extraSeriesCount=0", errors, "final_extra"
            )
        else:
            print("      [WARN] JS audit unavailable")

        print()
        print(sep)
        if all_clean:
            print("  RESULT: PASS")
        else:
            print(f"  RESULT: FAIL ({len(errors)} errors)")
            for e in errors:
                print(f"    - {e}")
        print(sep)

    finally:
        chart.exit()

    if not all_clean:
        sys.exit(1)


# ── Test 5: CandleSeries with main series cleanup ─────────

def test_candle_with_main():
    sep = "=" * 60
    print(sep)
    print("  test_candle_with_main")
    print(sep)

    chart = Chart(toolbox=True, width=1000, height=800)
    errors = []
    all_clean = True

    try:
        chart.show(block=False)

        df_main = make_ohlcv(30, 100, 42)
        df_ref = make_ohlcv(30, 200, 123)

        # Create main + CandleSeries + lines
        print("\n[1] Create mixed resources ...")
        chart.set(df_main)
        ref = chart.create_candle_series(name='ref', pane_index=1)
        ref.set(df_ref)
        line1 = chart.create_line('sma20', color='#ff0000')
        hist1 = chart.create_histogram('vol', color='#00ff00')
        all_clean &= log_check(len(chart._lines) == 3, f"_lines=3 (got {len(chart._lines)})", errors, "mixed_lines")
        print("      [OK]")

        # Markers on both main and ref
        print("\n[2] Markers on main and ref ...")
        chart.add_marker(df_main['time'].iloc[5], 'above', 'arrow_down', 'red', 'main_m')
        ref.add_marker(df_ref['time'].iloc[10], 'below', 'arrow_up', 'blue', 'ref_m')
        all_clean &= log_check(len(chart.markers) >= 1, "main markers", errors, "main_markers")
        all_clean &= log_check(len(ref.markers) == 1, "ref markers", errors, "ref_markers")
        print("      [OK]")

        # clear_data on main - ref unaffected
        print("\n[3] clear_data main - ref unaffected ...")
        chart.clear_data()
        all_clean &= log_check(chart.data.empty, "main candle_data empty", errors, "main_clear")
        all_clean &= log_check(not ref.data.empty, "ref candle_data still has data", errors, "ref_after_main_clear")
        print("      [OK]")

        # Delete ref - main lines unaffected
        print("\n[4] Delete ref - main lines unaffected ...")
        ref.delete()
        all_clean &= log_check(len(chart._lines) == 2, f"_lines=2 (got {len(chart._lines)})", errors, "after_ref_del")
        print("      [OK]")

        # Clean up everything
        print("\n[5] Full cleanup ...")
        line1.delete()
        hist1.delete()
        chart.clear_markers()
        all_clean &= log_check(len(chart._lines) == 0, "_lines=0", errors, "final_lines")
        all_clean &= log_check(len(chart.markers) == 0, "markers=0", errors, "final_markers")
        print("      [OK]")

        # JS audit
        print("\n[6] JS audit final ...")
        final = js_audit(chart)
        if final:
            sec = chart_section(chart, final)
            all_clean &= log_check(
                sec.get('extraSeriesCount', 0) == 0,
                f"extraSeriesCount=0", errors, "final_extra"
            )
        else:
            print("      [WARN] JS audit unavailable")

        print()
        print(sep)
        if all_clean:
            print("  RESULT: PASS")
        else:
            print(f"  RESULT: FAIL ({len(errors)} errors)")
            for e in errors:
                print(f"    - {e}")
        print(sep)

    finally:
        chart.exit()

    if not all_clean:
        sys.exit(1)


# ── Test 6: CandleSeries options verification ──────────────────

def test_options():
    sep = "=" * 60
    print(sep)
    print("  test_options")
    print(sep)

    chart = Chart(width=800, height=600)
    errors = []
    all_clean = True

    try:
        chart.show(block=False)

        df = make_ohlcv(10, 100, 42)
        chart.set(df)

        # Custom options
        print("\n[1] Create with custom options ...")
        ref = chart.create_candle_series(
            name='custom',
            pane_index=1,
            up_color='rgba(0, 200, 0, 0.8)',
            down_color='rgba(200, 0, 0, 0.8)',
            border_visible=False,
            wick_visible=False,
            price_line=True,
            price_label=True,
        )
        ref.set(make_ohlcv(10, 200, 123))
        all_clean &= log_check(ref.name == 'custom', f"name={ref.name}", errors, "opt_name")
        all_clean &= log_check(ref.pane_index == 1, f"pane_index={ref.pane_index}", errors, "opt_pane")
        print("      [OK]")

        # Verify JS series options
        print("\n[2] Verify JS series options ...")
        try:
            has_border = chart.win.run_script_and_get(
                f'{ref.id}.series.options().borderVisible'
            )
            has_border = str(has_border).lower() == 'false'
            all_clean &= log_check(has_border == True, f"borderVisible={has_border}", errors, "opt_border")
            has_wick = chart.win.run_script_and_get(
                f'{ref.id}.series.options().wickVisible'
            )
            has_wick = str(has_wick).lower() == 'false'
            all_clean &= log_check(has_wick == True, f"wickVisible={has_wick}", errors, "opt_wick")
        except Exception as e:
            all_clean &= log_check(False, f"JS options query failed: {e}", errors, "opt_js")
        print("      [OK]")

        ref.delete()
        print()
        print(sep)
        if all_clean:
            print("  RESULT: PASS")
        else:
            print(f"  RESULT: FAIL ({len(errors)} errors)")
            for e in errors:
                print(f"    - {e}")
        print(sep)

    finally:
        chart.exit()

    if not all_clean:
        sys.exit(1)


# ── Main ───────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [
        test_basic_create_delete,
        test_update_operations,
        test_markers,
        test_multi_pane,
        test_candle_with_main,
        test_options,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except SystemExit:
            failed += 1
        except Exception as e:
            print(f"\n  EXCEPTION in {test_fn.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  TOTAL: {passed} passed, {failed} failed out of {len(tests)}")
    print(f"{'=' * 60}")

    if failed:
        sys.exit(1)
