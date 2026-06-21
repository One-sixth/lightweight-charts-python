"""
Resource cleanup test.

Tests that all resource types can be created and then completely cleaned up.
Verifies both Python side and JS side (via audit).

Usage:
    python test/test_cleanup.py
"""

import sys, os, json, tomllib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import pandas as pd
import numpy as np
from lightweight_charts import Chart


def make_oi_data(num_bars: int = 50):
    np.random.seed(42)
    dates = pd.date_range('2025-01-01', periods=num_bars, freq='D')
    price = 100.0
    rows = []
    for i in range(num_bars):
        price += np.random.normal(0, 2)
        rows.append({
            'date': dates[i], 'open': round(price + np.random.normal(0, 1), 2),
            'high': round(price + abs(np.random.normal(0, 1.5)), 2),
            'low': round(price - abs(np.random.normal(0, 1.5)), 2),
            'close': round(price, 2),
            'volume': int(np.random.randint(1000, 50000)),
            'open_interest': int(10000 + i * 100 + np.random.randint(-500, 1500)),
        })
    return pd.DataFrame(rows)


def log_check(ok: bool, label: str, errors: list, err_key: str = None):
    """Unified check logging: [OK] or [FAIL] with optional error tracking."""
    if ok:
        print(f"      [OK] {label}")
    else:
        print(f"      [FAIL] {label}")
        if err_key:
            errors.append(err_key)
    return ok


def js_audit(chart, timeout=5):
    """
    Safely call JS Handler.audit(), with exception protection.
    Returns TOML-parsed dict, or None on failure.

    IMPORTANT: This function MUST succeed for the test to be valid.
    If js_audit returns None (timeout or execution failure), it indicates a critical issue:
    - JS runtime may be unresponsive
    - Handler.audit() may not be properly defined
    - The chart may have failed to initialize correctly
    Tests should treat a None return as a test failure.
    """
    try:
        result = chart.win.run_script_and_get('Lib.Handler.audit()', timeout=timeout)
        if not isinstance(result, str):
            return None
        return tomllib.loads(result)
    except Exception as e:
        print(f"      [FAIL] JS audit failed: {e}")
        return None


def chart_section(chart, data):
    """
    Look up the handler section for a chart in TOML-parsed audit data.
    TOML keys are like 'Chart_1', while chart.id is 'window.Chart_1'.
    JS audit() iterates Object.keys(window), so keys don't have 'window.' prefix.
    """
    sid = chart.id.replace('window.', '')
    return data.get(sid, {})


def _expected_handlers(toolbox: bool) -> int:
    """返回清理后 handlers 的预期数量。ToolBox 注册 save_drawings handler。"""
    return 1 if toolbox else 0


def _test_resource_full_cleanup_impl(toolbox: bool):
    sep = "=" * 60
    print(sep)
    suffix = " (toolbox=True)" if toolbox else " (toolbox=False)"
    print(f"  test_resource_full_cleanup{suffix}")
    print(sep)

    chart = Chart(toolbox=toolbox, position=211)
    bars = make_oi_data(50)
    errors = []
    all_clean = True

    try:
        print("\n[1] Launch chart ...")
        chart.show(block=False)
        print("      [OK]")

        # --- Baseline JS state ---
        print("\n[1a] Baseline JS audit (TOML) ...")
        baseline_audit = js_audit(chart)
        if baseline_audit is not None:
            # Filter out Handler-type sections
            baseline_keys = {k for k, v in baseline_audit.items()
                             if isinstance(v, dict) and v.get('type') != 'Handler'}
            print(f"      handler sections: {sum(1 for v in baseline_audit.values() if isinstance(v, dict) and v.get('type') == 'Handler')}")
            print(f"      non-handler keys: {len(baseline_keys)}")
            for k in sorted(baseline_keys):
                print(f"        {k}")
        else:
            print("      [FAIL] baseline audit unavailable")

        all_clean &= log_check(
            baseline_audit is not None, "baseline audit reachable", errors, "baseline_audit_unreachable"
        )

        print("\n[2] Create resources ...")
        chart.set(bars)
        assert not chart.candle_data.empty
        print("  2a. set() [OK]")

        line1 = chart.create_line('line1', color='#ff0000')
        line2 = chart.create_line('line2', color='#00ff00')
        assert len(chart._lines) == 2
        print("  2b. create_line x2 [OK]")

        hist1 = chart.create_histogram('hist1', color='#ff00ff')
        assert len(chart._lines) == 3
        print("  2b2. create_histogram [OK]")

        chart.marker(bars['date'].iloc[5], 'above', 'circle', '#ff0000', 'm1')
        chart.marker(bars['date'].iloc[10], 'below', 'arrow_up', '#00ff00', 'm2')
        chart.marker_list([
            {'time': bars['date'].iloc[15], 'position': 'above', 'shape': 'square',
             'color': '#0000bf', 'text': 'm3'},
            {'time': bars['date'].iloc[20], 'position': 'below', 'shape': 'circle',
             'color': '#ffff00', 'text': 'm4'},
        ])
        assert len(chart.markers) >= 4
        print("  2c. markers [OK]")

        hl = chart.horizontal_line(105, color='#ff8800', width=3, text='HLine')
        vl = chart.vertical_line(bars['date'].iloc[15], color='#8800ff', width=2)
        tl = chart.trend_line(bars['date'].iloc[10], 95, bars['date'].iloc[30], 110,
                              line_color='#00ffff', width=3)
        bx = chart.box(bars['date'].iloc[5], 90, bars['date'].iloc[25], 115,
                       color='#ff00ff', fill_color='rgba(255,0,255,0.1)')
        rl = chart.ray_line(bars['date'].iloc[20], 100, color='#00ff88', width=2, text='Ray')
        vs = chart.vertical_span(bars['date'].iloc[12], bars['date'].iloc[18],
                                 color='rgba(255,200,0,0.15)')
        assert len(chart._drawings) == 6
        print("  2d. drawables [OK]")

        pl = chart.create_price_line(price=102, title='PL', price_label=True)
        print("  2e. price_line [OK]")

        sub = chart.create_subchart(position=212)
        assert sub.id in chart.subcharts
        print("  2f. subchart [OK]")

        chart.legend(visible=True, persistent=True)
        tbl = chart.create_table(width=0.3, height=0.3, headings=('Col A', 'Col B'),
                           widths=(0.5, 0.5))
        assert len(chart._tables) == 1
        print("  2g. legend + table [OK]")

        def my_handler(): pass
        chart.events.new_bar += my_handler
        chart.win.handlers['test_handler'] = lambda: None
        print("  2h. event handlers [OK]")

        # Verify mid-state via JS audit
        print("\n[3] JS audit mid-state ...")
        mid = js_audit(chart)
        if mid:
            print(f"      sections: {len(mid)}")
            main = chart_section(chart, mid)
            all_clean &= log_check(
                chart.oi is not None, "OI series present (Python side)", errors, "mid_oi_missing"
            )
            all_clean &= log_check(
                main.get('extraSeriesCount', 0) >= 3,  # 2 lines + 1 hist
                f"extraSeriesCount={main.get('extraSeriesCount', 0)} >= 3", errors, "mid_seriesList_short"
            )
            print(f"      extraSeriesCount: {main.get('extraSeriesCount', 0)}")
        else:
            print("      [FAIL] mid-state JS audit unavailable")

        # Python-side mid-state
        print("\n[3a] Python audit mid-state ...")
        full = chart.audit()
        all_clean &= log_check(full['chart']['has_data'], "chart has data", errors, "mid_no_data")
        all_clean &= log_check(len(full['lines']) == 3, f"lines={len(full['lines'])}", errors, "mid_lines_count")
        all_clean &= log_check(len(full['drawings']) == 6, f"drawings={len(full['drawings'])}", errors, "mid_drawings_count")
        all_clean &= log_check(len(full['tables']) == 1, f"tables={len(full['tables'])}", errors, "mid_tables_count")
        all_clean &= log_check(len(full['price_lines']) == 1, "price_lines=1", errors, "mid_price_lines")
        print()
        for entry in full['lines']:
            print(f"      line: {entry['id']} ({entry['type']}) name={entry['name']}")
        for entry in full['drawings']:
            print(f"      draw: {entry['id']} ({entry['type']})")
        for entry in full['tables']:
            print(f"      table: {entry['id']}")
        print("      [OK] Python-side audit confirms all resources present")

        print("\n[4] Delete resources ...")
        chart.clear_data()
        all_clean &= log_check(chart.candle_data.empty, "candle_data cleared", errors, "candle_data_not_empty")
        print("  4a. clear_data() [OK]")

        chart.remove_marker(list(chart.markers.keys())[0])
        chart.remove_marker(list(chart.markers.keys())[0])
        chart.clear_markers()
        all_clean &= log_check(len(chart.markers) == 0, "markers cleared", errors, "markers_not_empty")
        print("  4b. markers [OK]")

        line1.delete()
        line2.delete()
        hist1.delete()
        all_clean &= log_check(len(chart._lines) == 0, "_lines cleared", errors, "lines_not_empty")
        print("  4c. lines + histograms [OK]")

        hl.delete()
        vl.delete()
        tl.delete()
        bx.delete()
        rl.delete()
        vs.delete()
        all_clean &= log_check(len(chart._drawings) == 0, "_drawings cleared", errors, "drawings_not_empty")
        print("  4e. drawables [OK]")

        pl.delete()
        all_clean &= log_check(len(chart._price_lines) == 0, "_price_lines cleared", errors, "price_lines_not_empty")
        print("  4f. price_line [OK]")

        # --- Subchart cleanup: check Handler._all before & after ---
        print("\n[4g-1] Subchart: Handler._all count before remove ...")
        before_all = js_audit(chart)
        n_before = len(before_all) if before_all else -1
        print(f"      TOML sections: {n_before}")

        chart.remove_subchart(sub.id)
        all_clean &= log_check(sub.id not in chart.subcharts, "subchart removed from Python", errors, "subchart_py")
        print("  4g. subchart [OK]")

        sub_key = sub.id.replace('window.', '')
        print("\n[4g-2] Subchart: Handler._all count after remove ...")
        after_all = js_audit(chart)
        n_after = len(after_all) if after_all else -1
        print(f"      TOML sections: {n_after}")
        if after_all and before_all:
            all_clean &= log_check(
                n_after <= n_before, f"Sections did not grow ({n_before} -> {n_after})",
                errors, "sections_grew"
            )
            # Check sub.id no longer in audit output
            sub_still_present = sub_key in after_all
            all_clean &= log_check(
                not sub_still_present, "subchart section removed from audit",
                errors, "subchart_section_leak"
            )
        else:
            print("      [FAIL] cannot verify subchart removal (JS audit unavailable)")
            errors.append("subchart_audit_failed")

        chart.legend(visible=False)
        tbl.delete()
        all_clean &= log_check(len(chart._tables) == 0, "_tables cleared", errors, "tables_not_empty")
        chart.events.new_bar -= my_handler
        chart.win.remove_handler('test_handler')
        expected = _expected_handlers(toolbox)
        all_clean &= log_check(
            len(chart.win.handlers) == expected,
            f"handlers cleared (expect {expected}, got {len(chart.win.handlers)})",
            errors, "handlers_not_empty"
        )
        print("  4h. handlers + table [OK]")

        # --- Final JS audit: seriesList, OI, window globals ---
        print("\n[5] JS audit final state ...")
        final = js_audit(chart)

        if final and baseline_audit:
            main_final = chart_section(chart, final)
            baseline_main = chart_section(chart, baseline_audit)

            bl_extra = baseline_main.get('extraSeriesCount', 0)
            fn_extra = main_final.get('extraSeriesCount', 0)
            print(f"      baseline extraSeriesCount: {bl_extra}")
            print(f"      final   extraSeriesCount: {fn_extra}")
            print(f"      final   hasOpenInterest:   {main_final.get('hasOpenInterest')}")

            all_clean &= log_check(
                fn_extra == bl_extra,
                "extraSeriesCount back to baseline", errors, "extraSeries_leak"
            )
            all_clean &= log_check(
                chart.oi is not None,
                "OI series present (Python side)", errors, "oi_js_missing"
            )

            # Non-handler leak check
            # VolumeSeries/OpenInterestSeries 是主图表默认创建的，不算泄漏
            def _non_handler_keys(d):
                return {k for k, v in d.items()
                        if isinstance(v, dict) and v.get('type') != 'Handler'
                        and not k.startswith(('VolumeSeries_', 'OpenInterestSeries_'))}

            wg_baseline = _non_handler_keys(baseline_audit)
            wg_final = _non_handler_keys(final)
            leaked = wg_final - wg_baseline
            print(f"      baseline non-handler keys: {len(wg_baseline)}")
            print(f"      final   non-handler keys: {len(wg_final)}")
            print(f"      leaked (new) keys: {len(leaked)}")
            for k in sorted(leaked):
                print(f"        LEAKED: {k}")
            all_clean &= log_check(
                len(leaked) == 0, "no window global leaks", errors, "window_global_leak"
            )
        else:
            print("      [FAIL] final JS audit unavailable - cannot verify JS cleanup")
            errors.append("final_audit_failed")

        # --- Python-side final state ---
        print("\n[6] Python-side final state ...")
        expected = _expected_handlers(toolbox)
        py_checks = [
            (chart.candle_data.empty, "candle_data", "py_candle_data"),
            (len(chart._lines) == 0, "_lines", "py_lines"),
            (len(chart._price_lines) == 0, "_price_lines", "py_price_lines"),
            (len(chart._drawings) == 0, "_drawings", "py_drawings"),
            (len(chart._tables) == 0, "_tables", "py_tables"),
            (len(chart.markers) == 0, "markers", "py_markers"),
            (len(chart.win.handlers) == expected, f"handlers (expect {expected})", "py_handlers"),
            (chart.events.new_bar._callable is None, "Emitter handler", "py_emitter"),
        ]
        for ok, name, ek in py_checks:
            all_clean &= log_check(ok, name, errors, ek)
        print()

        # --- Final verdict ---
        print(sep)
        if all_clean:
            print("  RESULT: PASS")
            print(sep)
        else:
            print(f"  RESULT: FAIL ({len(errors)} errors)")
            for e in errors:
                print(f"    - {e}")
            print(sep)

    finally:
        chart.exit()

    if not all_clean:
        sys.exit(1)


def test_resource_full_cleanup():
    """Run full cleanup test with toolbox=True then toolbox=False."""
    _test_resource_full_cleanup_impl(toolbox=True)
    _test_resource_full_cleanup_impl(toolbox=False)


def _test_multi_chart_cleanup_impl(toolbox: bool):
    sep = "=" * 60
    print(sep)
    suffix = " (toolbox=True)" if toolbox else " (toolbox=False)"
    print(f"  test_multi_chart_cleanup{suffix}")
    print(sep)

    bars = make_oi_data(30)
    errors = []
    all_clean = True

    # --- Create 2 charts ---
    print("\n[1] Create 2 charts ...")
    chart1 = Chart(title='Chart-1', toolbox=toolbox)
    chart2 = Chart(title='Chart-2', toolbox=toolbox)
    print("      [OK]")

    chart1.show(block=False)
    chart2.show(block=False)

    # Wait for both to load
    time.sleep(2)
    print("      [OK] both charts launched")

    try:
        # --- Create resources in chart1 ---
        print("\n[2] Create resources in chart1 ...")
        chart1.set(bars)
        line1 = chart1.create_line('ch1', color='#ff0000')
        hl1 = chart1.horizontal_line(105, color='#ff8800', width=2, text='HL')
        tbl1 = chart1.create_table(width=0.2, height=0.2, headings=('A', 'B'), widths=(0.5, 0.5))
        print(f"      lines={len(chart1._lines)}, drawings={len(chart1._drawings)}, tables={len(chart1._tables)}")
        all_clean &= log_check(len(chart1._lines) == 1, "chart1 has 1 line", errors, "mc1_line")
        all_clean &= log_check(len(chart1._drawings) == 1, "chart1 has 1 drawing", errors, "mc1_draw")
        all_clean &= log_check(len(chart1._tables) == 1, "chart1 has 1 table", errors, "mc1_table")

        # --- Create resources in chart2 ---
        print("\n[3] Create resources in chart2 ...")
        chart2.set(bars)
        line2a = chart2.create_line('ch2a', color='#00ff00')
        line2b = chart2.create_line('ch2b', color='#0000ff')
        vl2 = chart2.vertical_line(bars['date'].iloc[5], color='#8800ff', width=2)
        print(f"      lines={len(chart2._lines)}, drawings={len(chart2._drawings)}, tables={len(chart2._tables)}")
        all_clean &= log_check(len(chart2._lines) == 2, "chart2 has 2 lines", errors, "mc2_lines")
        all_clean &= log_check(len(chart2._drawings) == 1, "chart2 has 1 drawing", errors, "mc2_draw")
        all_clean &= log_check(len(chart2._tables) == 0, "chart2 has 0 tables", errors, "mc2_table")

        # --- Clean up chart1 only ---
        print("\n[4] Clean up chart1 ...")
        chart1.clear_data()
        line1.delete()
        hl1.delete()
        tbl1.delete()
        chart1._clear_handlers()
        print(f"      chart1: lines={len(chart1._lines)}, drawings={len(chart1._drawings)}, tables={len(chart1._tables)}")
        all_clean &= log_check(len(chart1._lines) == 0, "chart1 _lines cleared", errors, "mc1_clean_lines")
        all_clean &= log_check(len(chart1._drawings) == 0, "chart1 _drawings cleared", errors, "mc1_clean_draw")
        all_clean &= log_check(len(chart1._tables) == 0, "chart1 _tables cleared", errors, "mc1_clean_table")

        # --- Verify chart2 unaffected ---
        print("\n[5] Verify chart2 unaffected ...")
        print(f"      chart2: lines={len(chart2._lines)}, drawings={len(chart2._drawings)}, tables={len(chart2._tables)}")
        all_clean &= log_check(len(chart2._lines) == 2, "chart2 still has 2 lines", errors, "mc2_still_has_lines")
        all_clean &= log_check(len(chart2._drawings) == 1, "chart2 still has 1 drawing", errors, "mc2_still_has_draw")
        all_clean &= log_check(len(chart2._tables) == 0, "chart2 still has 0 tables", errors, "mc2_still_no_table")

        # JS audit: chart2's handler still has series
        js2 = js_audit(chart2)
        if js2:
            h2 = chart_section(chart2, js2)
            all_clean &= log_check(
                bool(h2) and h2.get('extraSeriesCount', 0) >= 2,
                "chart2 JS still has series", errors, "mc2_js_series"
            )
        else:
            print("      [FAIL] chart2 JS audit unavailable")
            errors.append("chart2_audit_failed")

        # --- Clean up chart2 ---
        print("\n[6] Clean up chart2 ...")
        chart2.clear_data()
        line2a.delete()
        line2b.delete()
        vl2.delete()
        chart2._clear_handlers()
        print(f"      chart2: lines={len(chart2._lines)}, drawings={len(chart2._drawings)}, tables={len(chart2._tables)}")
        all_clean &= log_check(len(chart2._lines) == 0, "chart2 _lines cleared", errors, "mc2_clean_lines")
        all_clean &= log_check(len(chart2._drawings) == 0, "chart2 _drawings cleared", errors, "mc2_clean_draw")

        # --- Verify chart1 still clean ---
        print("\n[7] Verify chart1 still clean ...")
        all_clean &= log_check(len(chart1._lines) == 0, "chart1 still has 0 lines", errors, "mc1_still_clean")
        all_clean &= log_check(len(chart1._drawings) == 0, "chart1 still has 0 drawings", errors, "mc1_still_clean_draw")

        print()
        print(sep)
        if all_clean:
            print("  RESULT: PASS")
            print(sep)
        else:
            print(f"  RESULT: FAIL ({len(errors)} errors)")
            for e in errors:
                print(f"    - {e}")
            print(sep)

    finally:
        chart1.exit()
        chart2.exit()

    if not all_clean:
        sys.exit(1)


def test_multi_chart_cleanup():
    """Run multi-chart cleanup test with toolbox=True then toolbox=False."""
    _test_multi_chart_cleanup_impl(toolbox=True)
    _test_multi_chart_cleanup_impl(toolbox=False)


def test_reset_cleanup():
    """验证 reset() 后 candle/volume/oi 全部被删除，再 set() 能正确重建。"""
    sep = "=" * 60
    print(sep)
    print("  test_reset_cleanup")
    print(sep)

    bars = make_oi_data(30)
    errors = []
    all_clean = True

    chart = Chart(title='Reset Test', toolbox=True)
    chart.show(block=False)
    time.sleep(1)

    try:
        # --- Step 1: set data (should auto-create volume/oi) ---
        print("\n[1] set() ...")
        chart.set(bars)
        all_clean &= log_check(
            chart.candle is not None, "candle exists", errors, "r_candle"
        )
        all_clean &= log_check(
            chart.volume is not None, "volume created", errors, "r_vol"
        )
        all_clean &= log_check(
            chart.oi is not None, "oi created", errors, "r_oi"
        )
        all_clean &= log_check(
            not chart.candle.candle_data.empty, "candle has data", errors, "r_candle_data"
        )
        all_clean &= log_check(
            len(chart.candle.markers) == 0, "no markers yet", errors, "r_markers_init"
        )
        print(f"      candle id: {chart.candle.id}")
        print(f"      volume id: {chart.volume.id}")
        print(f"      oi id:     {chart.oi.id}")

        # --- Step 2: add markers and lines ---
        print("\n[2] Add markers + lines ...")
        chart.marker(bars['date'].iloc[5], 'above', 'circle', 'red', 'm1')
        line1 = chart.create_line('line1', color='#ff0000')
        line1.set(bars[['date', 'close']].rename(columns={'date': 'time', 'close': 'line1'}))
        all_clean &= log_check(len(chart.candle.markers) == 1, "1 marker", errors, "r_marker_added")
        all_clean &= log_check(len(chart._lines) == 1, "1 line", errors, "r_line_added")

        # --- Step 3: verify JS side has the series ---
        print("\n[3] Verify JS series exist ...")
        js_check = chart.win.run_script_and_get(
            f'({chart.candle.id}.series !== null) && ({chart.volume.id}.series !== null) && ({chart.oi.id}.series !== null)',
            timeout=5
        )
        all_clean &= log_check(js_check == True, "all 3 JS series exist", errors, "r_js_series_exist")
        print(f"      JS check: {js_check}")

        # --- Step 4: reset() ---
        print("\n[4] reset() ...")
        chart.reset()
        all_clean &= log_check(
            chart.candle_data.empty, "candle_data empty", errors, "r_reset_candle_empty"
        )
        all_clean &= log_check(
            chart.volume is None, "volume is None", errors, "r_reset_vol_none"
        )
        all_clean &= log_check(
            chart.oi is None, "oi is None", errors, "r_reset_oi_none"
        )
        all_clean &= log_check(
            len(chart.markers) == 0, "markers cleared", errors, "r_reset_markers"
        )
        all_clean &= log_check(
            len(chart._lines) == 0, "lines cleared", errors, "r_reset_lines"
        )
        all_clean &= log_check(
            chart._interval is None, "interval reset to None", errors, "r_reset_interval"
        )
        print("      [OK] Python state verified")

        # --- Step 5: verify JS side series are deleted ---
        print("\n[5] Verify JS series deleted ...")
        handler_id = chart.id
        js_check2 = chart.win.run_script_and_get(
            f'({handler_id}.series === null) && ({handler_id}.volumeSeries === null) && ({handler_id}.openInterestSeries === null)',
            timeout=5
        )
        all_clean &= log_check(js_check2 == True, "Handler refs are null", errors, "r_js_handler_null")
        print(f"      JS check: {js_check2}")

        # --- Step 6: set() again (should recreate volume/oi) ---
        print("\n[6] set() again ...")
        chart.set(bars)
        all_clean &= log_check(
            chart.volume is not None, "volume recreated", errors, "r_recreate_vol"
        )
        all_clean &= log_check(
            chart.oi is not None, "oi recreated", errors, "r_recreate_oi"
        )
        all_clean &= log_check(
            not chart.candle.candle_data.empty, "candle has data again", errors, "r_recreate_candle_data"
        )
        print(f"      volume id: {chart.volume.id}")
        print(f"      oi id:     {chart.oi.id}")

        # --- Step 7: verify fixed IDs are preserved ---
        print("\n[7] Verify fixed IDs preserved ...")
        base = chart.id.replace('window.', '')
        all_clean &= log_check(
            chart.candle.id == f'window.{base}_candle',
            f"candle id = window.{base}_candle", errors, "r_id_candle"
        )
        all_clean &= log_check(
            chart.volume.id == f'window.{base}_volume',
            f"volume id = window.{base}_volume", errors, "r_id_volume"
        )
        all_clean &= log_check(
            chart.oi.id == f'window.{base}_oi',
            f"oi id = window.{base}_oi", errors, "r_id_oi"
        )

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


if __name__ == '__main__':
    test_resource_full_cleanup()
    print("\n")
    test_multi_chart_cleanup()
    print("\n")
    test_reset_cleanup()
