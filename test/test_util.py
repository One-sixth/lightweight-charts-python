"""
Utility function tests: pure Python, no window needed.

Tests:
  1. format_datetime — datetime formatting with timezone
  2. snake_to_camel — snake_case to camelCase
  3. js_json — dict to JS JSON.parse code
  4. jbool — boolean to JS string
  5. as_enum — string enum to numeric index
  6. marker_shape / marker_position — shape/position name conversion
  7. df_data — DataFrame to clean records (NaN filtering)
  8. series_data — Series to [{index, value}] format
  9. js_data — DataFrame to JSON string
 10. Emitter — sync event emitter (+=, _emit, -=)
 11. parse_event_message — handler + args splitting
 12. _convert_timeframe — polygon timeframe parsing
 13. _get_sec_type — ticker prefix to security type

Usage:
    python test/test_util.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

from lightweight_charts.util import (
    format_datetime,
    snake_to_camel,
    js_json,
    jbool,
    as_enum,
    marker_shape,
    marker_position,
    df_data,
    series_data,
    js_data,
    Emitter,
    parse_event_message,
    LINE_STYLE,
    MARKER_SHAPE,
    MARKER_POSITION,
)
from lightweight_charts.polygon import _convert_timeframe, _get_sec_type


def log_check(ok: bool, label: str, errors: list, err_key: str = None):
    """Unified check logging."""
    if ok:
        print(f"      [OK] {label}")
    else:
        print(f"      [FAIL] {label}")
        if err_key:
            errors.append(err_key)
    return ok


# ──────────────────────────────────────────────
#  1. format_datetime
# ──────────────────────────────────────────────

def test_format_datetime():
    sep = "=" * 60
    print(sep)
    print("  test_format_datetime")
    print(sep)

    errors = []
    all_clean = True

    # 1a) No tz — just date + time
    dt = datetime(2026, 5, 11, 14, 30, 45)
    result = format_datetime(dt)
    all_clean &= log_check(
        result == '2026-05-11 14:30',
        "no tz: '2026-05-11 14:30'",
        errors, "fmt_notz"
    )

    # 1b) With timezone string — naive datetime treated as that tz
    result = format_datetime(dt, 'Asia/Shanghai')
    all_clean &= log_check(
        result.startswith('2026-05-11 14:30 GMT+0800'),
        "naive dt + 'Asia/Shanghai' format",
        errors, "fmt_shanghai"
    )

    # 1c) Aware datetime converted to target tz
    dt_utc = datetime(2026, 5, 11, 6, 30, tzinfo=timezone.utc)
    result = format_datetime(dt_utc, 'Asia/Shanghai')
    all_clean &= log_check(
        result.startswith('2026-05-11 14:30 GMT+0800'),
        "UTC → Shanghai conversion",
        errors, "fmt_utc2sh"
    )

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  2. snake_to_camel
# ──────────────────────────────────────────────

def test_snake_to_camel():
    sep = "=" * 60
    print(sep)
    print("  test_snake_to_camel")
    print(sep)

    errors = []
    all_clean = True

    cases = [
        ('hello_world',   'helloWorld'),
        ('foo',           'foo'),
        ('a_b_c',         'aBC'),
        ('price_format',  'priceFormat'),
        ('color',         'color'),
        ('',              ''),
    ]
    for inp, expected in cases:
        result = snake_to_camel(inp)
        ok = result == expected
        all_clean &= log_check(
            ok, f"snake_to_camel({inp!r}) → {result!r} (expected {expected!r})",
            errors, f"stc_{inp}"
        )

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  3. js_json
# ──────────────────────────────────────────────

def test_js_json():
    sep = "=" * 60
    print(sep)
    print("  test_js_json")
    print(sep)

    errors = []
    all_clean = True

    # Basic dict
    d = {'price_format': 2, 'color': '#ff0000'}
    result = js_json(d)
    all_clean &= log_check(
        result.startswith("JSON.parse("),
        "js_json wraps in JSON.parse()",
        errors, "jj_wrap"
    )

    # None values filtered out
    d2 = {'visible': True, 'width': None, 'title': 'test'}
    result2 = js_json(d2)
    all_clean &= log_check(
        '"width"' not in result2,
        "js_json filters None values",
        errors, "jj_none"
    )

    # Snake_case → camelCase
    d3 = {'price_format': 2, 'line_style': 0}
    result3 = js_json(d3)
    all_clean &= log_check(
        'priceFormat' in result3 and 'lineStyle' in result3,
        "js_json converts snake_case to camelCase",
        errors, "jj_camel"
    )

    # 'self' key filtered
    d4 = {'self': 'something', 'value': 42}
    result4 = js_json(d4)
    all_clean &= log_check(
        '"self"' not in result4 and '"value"' in result4,
        "js_json filters 'self' key",
        errors, "jj_self"
    )

    # Valid JSON output
    import ast
    try:
        parsed = json.loads(result.split("'")[1] if "'" in result else result[12:-2])
        ok = True
    except Exception:
        ok = False
    all_clean &= log_check(ok, "js_json produces valid JSON", errors, "jj_valid")

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  4. jbool
# ──────────────────────────────────────────────

def test_jbool():
    sep = "=" * 60
    print(sep)
    print("  test_jbool")
    print(sep)

    errors = []
    all_clean = True

    all_clean &= log_check(jbool(True) == 'true', 'True → true', errors, 'jb_true')
    all_clean &= log_check(jbool(False) == 'false', 'False → false', errors, 'jb_false')
    all_clean &= log_check(jbool(1) is None, 'int 1 → None', errors, 'jb_int')
    all_clean &= log_check(jbool(None) is None, 'None → None', errors, 'jb_none')

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  5. as_enum
# ──────────────────────────────────────────────

def test_as_enum():
    sep = "=" * 60
    print(sep)
    print("  test_as_enum")
    print(sep)

    errors = []
    all_clean = True

    # LINE_STYLE: solid=0, dotted=1, dashed=2, large_dashed=3, sparse_dotted=4
    all_clean &= log_check(as_enum('solid', LINE_STYLE) == 0, 'solid → 0', errors, 'ae_solid')
    all_clean &= log_check(as_enum('dashed', LINE_STYLE) == 2, 'dashed → 2', errors, 'ae_dashed')
    all_clean &= log_check(as_enum('sparse_dotted', LINE_STYLE) == 4, 'sparse_dotted → 4', errors, 'ae_sparse')
    all_clean &= log_check(as_enum('unknown', LINE_STYLE) == -1, 'unknown → -1', errors, 'ae_unknown')

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  6. marker_shape / marker_position
# ──────────────────────────────────────────────

def test_marker_conversions():
    sep = "=" * 60
    print(sep)
    print("  test_marker_conversions")
    print(sep)

    errors = []
    all_clean = True

    # marker_shape
    all_clean &= log_check(marker_shape('arrow_up') == 'arrowUp', 'arrow_up → arrowUp', errors, 'ms_up')
    all_clean &= log_check(marker_shape('arrow_down') == 'arrowDown', 'arrow_down → arrowDown', errors, 'ms_down')
    all_clean &= log_check(marker_shape('circle') == 'circle', 'circle → circle (passthru)', errors, 'ms_circle')
    all_clean &= log_check(marker_shape('square') == 'square', 'square → square (passthru)', errors, 'ms_square')

    # marker_position
    all_clean &= log_check(marker_position('above') == 'aboveBar', 'above → aboveBar', errors, 'mp_above')
    all_clean &= log_check(marker_position('below') == 'belowBar', 'below → belowBar', errors, 'mp_below')
    all_clean &= log_check(marker_position('inside') == 'inBar', 'inside → inBar', errors, 'mp_inside')
    all_clean &= log_check(marker_position('atPriceMiddle') == 'atPriceMiddle', 'atPriceMiddle', errors, 'mp_mid')
    all_clean &= log_check(marker_position('atPriceTop') == 'atPriceTop', 'atPriceTop', errors, 'mp_top')
    all_clean &= log_check(marker_position('atPriceBottom') == 'atPriceBottom', 'atPriceBottom', errors, 'mp_btm')
    all_clean &= log_check(marker_position('unknown') is None, 'unknown → None', errors, 'mp_unknown')

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  7. df_data — DataFrame NaN filtering
# ──────────────────────────────────────────────

def test_df_data():
    sep = "=" * 60
    print(sep)
    print("  test_df_data")
    print(sep)

    errors = []
    all_clean = True

    # DataFrame with NaN
    df = pd.DataFrame({
        'time': ['2026-05-01', '2026-05-02'],
        'open': [100.0, None],
        'close': [101.0, 102.0],
    })
    result = df_data(df)

    all_clean &= log_check(
        isinstance(result, list) and len(result) == 2,
        "df_data returns list of 2 records",
        errors, "df_len"
    )
    all_clean &= log_check(
        'open' not in result[1],  # None should be filtered
        "NaN values filtered from records",
        errors, "df_nan"
    )
    all_clean &= log_check(
        result[0].get('open') == 100.0,
        "non-NaN values preserved",
        errors, "df_value"
    )

    # Series input (note: current impl does NOT filter NaN for Series, just returns dict)
    s = pd.Series({'a': 1.0, 'b': float('nan'), 'c': 3.0})
    result_s = df_data(s)
    all_clean &= log_check(
        isinstance(result_s, dict),
        "df_data(Series) returns dict",
        errors, "df_series_type"
    )
    all_clean &= log_check(
        'b' in result_s,  # Series branch does no NaN filtering
        "df_data(Series) preserves NaN (current behavior)",
        errors, "df_series_nan"
    )

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  8. series_data — Series to [{index, value}]
# ──────────────────────────────────────────────

def test_series_data():
    sep = "=" * 60
    print(sep)
    print("  test_series_data")
    print(sep)

    errors = []
    all_clean = True

    s = pd.Series({'a': 1.5, 'b': 2.0, 'c': 3.14159})
    result = series_data(s)

    all_clean &= log_check(
        isinstance(result, list) and len(result) == 3,
        "series_data returns list of 3",
        errors, "sd_len"
    )
    all_clean &= log_check(
        result[2] == {'index': 'c', 'value': '3.1416'},
        "float formatted to 4 decimals",
        errors, "sd_float"
    )
    all_clean &= log_check(
        result[0] == {'index': 'a', 'value': '1.5000'},
        "non-integer float formatted correctly",
        errors, "sd_float2"
    )

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  9. js_data — DataFrame to JSON string
# ──────────────────────────────────────────────

def test_js_data():
    sep = "=" * 60
    print(sep)
    print("  test_js_data")
    print(sep)

    errors = []
    all_clean = True

    df = pd.DataFrame({
        'time': ['2026-05-01'],
        'open': [100.0],
        'volume': [None],
    })
    result = js_data(df)

    all_clean &= log_check(
        isinstance(result, str),
        "js_data returns string",
        errors, "jd_type"
    )
    all_clean &= log_check(
        'volume' not in result,
        "NaN values removed from JSON",
        errors, "jd_nan"
    )
    all_clean &= log_check(
        '2026-05-01' in result,
        "valid data present in JSON",
        errors, "jd_value"
    )

    # Series
    s = pd.Series({'a': 1, 'b': 2})
    result_s = js_data(s)
    all_clean &= log_check(
        isinstance(result_s, str),
        "js_data(Series) returns string",
        errors, "jd_series_type"
    )

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  10. Emitter
# ──────────────────────────────────────────────

def test_emitter():
    sep = "=" * 60
    print(sep)
    print("  test_emitter")
    print(sep)

    errors = []
    all_clean = True

    emitted = []

    def handler(value):
        emitted.append(value)

    e = Emitter()

    # __iadd__ (register)
    e += handler
    e._emit(42)
    all_clean &= log_check(
        emitted == [42],
        "emit yields 42",
        errors, "em_emit"
    )

    # __isub__ (unregister)
    e -= handler
    e._emit(99)
    all_clean &= log_check(
        emitted == [42],  # should NOT append 99
        "after -=, emit no-ops",
        errors, "em_isub"
    )

    # Double register — overwrites, only last fires
    emitted2 = []
    e2 = Emitter()
    e2 += lambda v: emitted2.append(f'first:{v}')
    e2 += lambda v: emitted2.append(f'second:{v}')
    e2._emit(1)
    all_clean &= log_check(
        len(emitted2) == 1 and 'second' in emitted2[0],
        "second handler overwrites first",
        errors, "em_overwrite"
    )

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  11. parse_event_message
# ──────────────────────────────────────────────

def test_parse_event_message():
    sep = "=" * 60
    print(sep)
    print("  test_parse_event_message")
    print(sep)

    errors = []
    all_clean = True

    # Simulate a window with handlers
    class FakeWindow:
        def __init__(self):
            self.handlers = {
                'myEvent': lambda *a: a,
                'click': lambda *a: a,
            }

    win = FakeWindow()

    # Basic message
    func, args = parse_event_message(win, 'myEvent_~_arg1;;;arg2')
    all_clean &= log_check(
        func is win.handlers['myEvent'],
        "correct handler resolved",
        errors, "pm_handler"
    )
    all_clean &= log_check(
        args == ['arg1', 'arg2'],
        "correct args split",
        errors, "pm_args"
    )

    # Single arg, no separators
    func, args = parse_event_message(win, 'click_~_hello')
    all_clean &= log_check(
        args == ['hello'],
        "single arg works",
        errors, "pm_single"
    )

    # Empty args
    func, args = parse_event_message(win, 'click_~_')
    all_clean &= log_check(
        args == [''],
        "empty message yields [''],",
        errors, "pm_empty"
    )

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  12. _convert_timeframe (polygon)
# ──────────────────────────────────────────────

def test_convert_timeframe():
    sep = "=" * 60
    print(sep)
    print("  test_convert_timeframe")
    print(sep)

    errors = []
    all_clean = True

    # Minute frames
    mult, span = _convert_timeframe('1min')
    all_clean &= log_check(mult == '1' and span == 'minute', '1min → 1, minute', errors, 'tf_1min')
    mult, span = _convert_timeframe('15min')
    all_clean &= log_check(mult == '15' and span == 'minute', '15min → 15, minute', errors, 'tf_15min')

    # Hour frames
    mult, span = _convert_timeframe('1H')
    all_clean &= log_check(mult == '1' and span == 'hour', '1H → 1, hour', errors, 'tf_1h')
    mult, span = _convert_timeframe('4H')
    all_clean &= log_check(mult == '4' and span == 'hour', '4H → 4, hour', errors, 'tf_4h')

    # Day
    mult, span = _convert_timeframe('D')
    all_clean &= log_check(mult == 1 and span == 'day', 'D → 1, day', errors, 'tf_day')

    # Week
    mult, span = _convert_timeframe('W')
    all_clean &= log_check(mult == 1 and span == 'week', 'W → 1, week', errors, 'tf_week')

    # Month
    mult, span = _convert_timeframe('M')
    all_clean &= log_check(mult == 1 and span == 'month', 'M → 1, month', errors, 'tf_month')

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  13. _get_sec_type (polygon)
# ──────────────────────────────────────────────

def test_get_sec_type():
    sep = "=" * 60
    print(sep)
    print("  test_get_sec_type")
    print(sep)

    errors = []
    all_clean = True

    all_clean &= log_check(_get_sec_type('AAPL') == 'stocks', 'AAPL → stocks', errors, 'st_stock')
    all_clean &= log_check(_get_sec_type('MSFT') == 'stocks', 'MSFT → stocks', errors, 'st_stock2')
    all_clean &= log_check(_get_sec_type('O:ABC') == 'options', 'O: → options', errors, 'st_option')
    all_clean &= log_check(_get_sec_type('I:SPX') == 'indices', 'I: → indices', errors, 'st_index')
    all_clean &= log_check(_get_sec_type('C:EUR/USD') == 'forex', 'C: → forex', errors, 'st_forex')
    all_clean &= log_check(_get_sec_type('X:BTCUSD') == 'crypto', 'X: → crypto', errors, 'st_crypto')
    all_clean &= log_check(_get_sec_type('EUR/USD') == 'forex', 'EUR/USD → forex (slash)', errors, 'st_slash')

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
        for e in errors:
            print(f"    - {e}")
    print(sep)
    return all_clean


# ──────────────────────────────────────────────
#  Runner
# ──────────────────────────────────────────────

if __name__ == '__main__':
    results = []

    print("\n")
    results.append(('format_datetime',       test_format_datetime()))
    results.append(('snake_to_camel',        test_snake_to_camel()))
    results.append(('js_json',               test_js_json()))
    results.append(('jbool',                 test_jbool()))
    results.append(('as_enum',               test_as_enum()))
    results.append(('marker_conversions',    test_marker_conversions()))
    results.append(('df_data',               test_df_data()))
    results.append(('series_data',           test_series_data()))
    results.append(('js_data',               test_js_data()))
    results.append(('emitter',               test_emitter()))
    results.append(('parse_event_message',   test_parse_event_message()))
    results.append(('convert_timeframe',     test_convert_timeframe()))
    results.append(('get_sec_type',          test_get_sec_type()))

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
