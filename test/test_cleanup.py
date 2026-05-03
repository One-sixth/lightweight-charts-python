"""
Resource cleanup test.

Tests that all resource types can be created and then completely cleaned up.
Verifies both Python side and JS side (via audit).

Usage:
    python test/test_cleanup.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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


def test_resource_full_cleanup():
    sep = "=" * 60
    print(sep)
    print("  test_resource_full_cleanup")
    print(sep)

    chart = Chart(toolbox=True)
    bars = make_oi_data(50)
    errors = []
    all_clean = True

    try:
        print("\n[1] Launch chart ...")
        chart.show(block=False)
        chart.clear_handlers()
        print("      [OK]")

        # Capture baseline JS state
        baseline_audit = json.loads(chart.win.run_script_and_get('Lib.Handler.audit()', timeout=5))
        print("      baseline handlers:", len(baseline_audit))

        print("\n[2] Create resources ...")
        chart.set(bars)
        assert not chart.candle_data.empty
        assert not chart._open_interest_data.empty
        print("  2a. set() [OK]")

        line1 = chart.create_line('line1', color='#ff0000')
        line2 = chart.create_line('line2', color='#00ff00')
        assert len(chart._lines) == 2
        print("  2b. create_line x2 [OK]")

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
        print("  2d. drawables [OK]")

        pl = chart.create_price_line(price=102, title='PL', price_label=True)
        print("  2e. price_line [OK]")

        sub = chart.create_subchart(position='bottom', width=1.0, height=0.3)
        assert sub.id in chart.subcharts
        print("  2f. subchart [OK]")

        chart.legend(visible=True, persistent=True)
        tbl = chart.create_table(width=0.3, height=0.3, headings=('Col A', 'Col B'),
                           widths=(0.5, 0.5))
        print("  2g. legend + table [OK]")

        def my_handler(): pass
        chart.events.new_bar += my_handler
        chart.win.handlers['test_handler'] = lambda: None
        print("  2h. event handlers [OK]")

        # Verify mid-state via JS audit
        print("\n[3] JS audit mid-state ...")
        mid = json.loads(chart.win.run_script_and_get('Lib.Handler.audit()', timeout=5))
        print("      auditors:", len(mid))
        # main handler has OI + 2 extra series in _seriesList
        main = [h for h in mid if h['id'] == chart.id][0]
        assert main['hasOpenInterestSeries']
        assert main['seriesListLength'] >= 2  # 2 line series
        print("      [OK] main handler: OI=%s, seriesList=%d" % (
            main['hasOpenInterestSeries'], main['seriesListLength']))

        # Full audit demo
        print("\n[3a] audit(full=True) demo ...")
        full = chart.audit(full=True)
        print("   chart.has_data:           %s" % full['chart']['has_data'])
        print("   lines:                    %d" % len(full['lines']))
        print("   price_lines:              %d" % len(full['price_lines']))
        print("   markers:                  %d" % len(full['markers']))
        print("   subcharts:                %d" % len(full['subcharts']))
        print("   tables:                   %d" % len(full['tables']))
        if full['lines']:
            print("   first line:               %s (%s)" % (full['lines'][0]['id'], full['lines'][0]['name']))
        print("      [OK] full audit works")

        print("\n[4] Delete resources ...")
        chart.clear_data()
        assert chart.candle_data.empty
        assert chart._open_interest_data.empty
        print("  4a. clear_data() [OK]")

        chart.remove_marker(list(chart.markers.keys())[0])
        chart.remove_marker(list(chart.markers.keys())[0])
        chart.clear_markers()
        assert len(chart.markers) == 0
        print("  4b. markers [OK]")

        line1.delete()
        line2.delete()
        assert len(chart._lines) == 0
        print("  4c. lines [OK]")

        chart.delete_open_interest()
        print("  4d. OI [OK]")

        hl.delete()
        vl.delete()
        tl.delete()
        bx.delete()
        rl.delete()
        vs.delete()
        print("  4e. drawables [OK]")

        pl.delete()
        assert len(chart._price_lines) == 0
        print("  4f. price_line [OK]")

        chart.remove_subchart(sub.id)
        assert sub.id not in chart.subcharts
        print("  4g. subchart [OK]")

        chart.legend(visible=False)
        tbl.delete()  # removes table handler
        chart.events.new_bar -= my_handler
        chart.win.remove_handler('test_handler')
        assert len(chart.win.handlers) == 0
        print("  4h. handlers [OK]")

        # Final JS audit
        print("\n[5] JS audit final state ...")
        final = json.loads(chart.win.run_script_and_get('Lib.Handler.audit()', timeout=5))

        # Check only our main handler
        main_final = [h for h in final if h['id'] == chart.id][0]
        # seriesCount should be back to length matching baseline
        baseline_main = [h for h in baseline_audit if h['id'] == chart.id][0]

        print("      baseline seriesListLength:", baseline_main['seriesListLength'])
        print("      final   seriesListLength:", main_final['seriesListLength'])
        print("      final   openInterestSeries:", main_final['hasOpenInterestSeries'])
        print("      final   subchartsCount:", main_final['subchartsCount'])

        if main_final['seriesListLength'] == baseline_main['seriesListLength']:
            print("      [OK] seriesList clean")
        else:
            print("      [FAIL] seriesList leak!")
            errors.append("JS seriesList leak")
            all_clean = False

        if not main_final['hasOpenInterestSeries']:
            print("      [OK] OI cleaned")
        else:
            print("      [FAIL] OI not cleaned!")
            errors.append("OI not cleaned in JS")
            all_clean = False

        if main_final['subchartsCount'] == 0:
            print("      [OK] subcharts clean")
        else:
            print("      [FAIL] subcharts leak!")
            errors.append("subcharts leak")
            all_clean = False

        # Python-side final state
        print("\n[6] Python-side final state ...")
        py_checks = [
            (chart.candle_data.empty, "candle_data"),
            (chart._open_interest_data.empty, "OI data"),
            (len(chart._lines) == 0, "_lines"),
            (len(chart._price_lines) == 0, "_price_lines"),
            (len(chart.markers) == 0, "markers"),
            (len(chart.win.handlers) == 0, "handlers"),
            (chart.events.new_bar._callable is None, "Emitter handler"),
        ]
        for ok, name in py_checks:
            print("    [%s] %s" % ("OK" if ok else "FAIL", name))
            if not ok:
                errors.append(name)
                all_clean = False

        print()
        print(sep)
        print("  %s" % ("PASS" if all_clean else "FAIL: %d errors" % len(errors)))
        print(sep)

    finally:
        chart.exit()

    if not all_clean:
        sys.exit(1)


if __name__ == '__main__':
    test_resource_full_cleanup()
