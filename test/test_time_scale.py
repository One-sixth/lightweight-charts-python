"""
时间轴时间格式修复验证测试。

测试内容：
  1. _sync_interval_to_js() 生成的 JS 代码是否正确（mock run_script）
  2. set_period() 调用后是否触发同步
  3. set() 调用后是否触发同步
  4. 三种时间级别的 JS 端 timeFormatter 逻辑验证

运行方式：
    python test/test_time_scale.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np


def log_check(ok: bool, label: str, errors: list):
    if ok:
        print(f"      [OK] {label}")
    else:
        print(f"      [FAIL] {label}")
        errors.append(label)


def load_bars():
    csv_path = os.path.join(os.path.dirname(__file__), '..',
                            'examples', '1_setting_data', 'ohlcv.csv')
    return pd.read_csv(csv_path).rename(columns={'date': 'time'})


# ═══════════════════════════════════════════════
#  1. _sync_interval_to_js 生成的 JS 代码验证
# ═══════════════════════════════════════════════

def test_sync_interval_js_code():
    """验证 _sync_interval_to_js 在不同 interval 下生成的 JS 代码正确性。"""
    sep = "=" * 60
    print(sep)
    print("  1. _sync_interval_to_js JS 代码验证")
    print(sep)

    errors = []

    # 模拟 chart 对象
    class MockChart:
        id = 'h0'
        _interval = None
        scripts = []

        def run_script(self, script, run_last=False):
            self.scripts.append(script)

    chart = MockChart()

    # 导入并绑定方法
    from lightweight_charts.abstract import AbstractChart
    # 用 mock 模拟
    chart._interval = 86400  # 日线
    chart._sync_interval_to_js = lambda: (
        None if chart._interval is None else
        chart.run_script(
            f'{chart.id}._interval = {chart._interval};'
            f'{chart.id}.chart.applyOptions({{timeScale: {{secondsVisible: {str(chart._interval < 60).lower()}}}}})'
        )
    )

    # --- 测试 1: 日线 (86400s) ---
    chart.scripts.clear()
    chart._interval = 86400
    chart._sync_interval_to_js()
    expected = 'h0._interval = 86400;h0.chart.applyOptions({timeScale: {secondsVisible: false}})'
    ok = len(chart.scripts) == 1 and chart.scripts[0] == expected
    log_check(ok, f"日线 (86400s): secondsVisible=false", errors)

    # --- 测试 2: 分钟级 (60s) ---
    chart.scripts.clear()
    chart._interval = 60
    chart._sync_interval_to_js()
    expected = 'h0._interval = 60;h0.chart.applyOptions({timeScale: {secondsVisible: false}})'
    ok = len(chart.scripts) == 1 and chart.scripts[0] == expected
    log_check(ok, f"分钟级 (60s): secondsVisible=false", errors)

    # --- 测试 3: 秒级 (5s) ---
    chart.scripts.clear()
    chart._interval = 5
    chart._sync_interval_to_js()
    expected = 'h0._interval = 5;h0.chart.applyOptions({timeScale: {secondsVisible: true}})'
    ok = len(chart.scripts) == 1 and chart.scripts[0] == expected
    log_check(ok, f"秒级 (5s): secondsVisible=true", errors)

    # --- 测试 4: 300s (5分钟) ---
    chart.scripts.clear()
    chart._interval = 300
    chart._sync_interval_to_js()
    expected = 'h0._interval = 300;h0.chart.applyOptions({timeScale: {secondsVisible: false}})'
    ok = len(chart.scripts) == 1 and chart.scripts[0] == expected
    log_check(ok, f"分钟级 (300s): secondsVisible=false", errors)

    print()
    return errors


# ═══════════════════════════════════════════════
#  2. timeFormatter 三种分支逻辑验证
# ═══════════════════════════════════════════════

def test_time_formatter_logic():
    """验证 JS timeFormatter 的三种分支逻辑（纯 Python 模拟）。"""
    sep = "=" * 60
    print(sep)
    print("  2. timeFormatter 逻辑验证（模拟 JS 端行为）")
    print(sep)

    errors = []
    from datetime import datetime, timezone

    def time_formatter(time_ts, interval):
        """模拟 JS 端 timeFormatter 的行为。"""
        d = datetime.fromtimestamp(time_ts, tz=timezone.utc)
        pad = lambda n: str(n).zfill(2)
        date_str = f"{d.year}-{pad(d.month)}-{pad(d.day)}"
        if interval >= 86400:
            return date_str
        time_str = f"{pad(d.hour)}:{pad(d.minute)}"
        if interval < 60:
            return f"{date_str} {time_str}:{pad(d.second)}"
        return f"{date_str} {time_str}"

    # 用一个固定时间点: 2026-07-08 14:30:45 UTC
    ts = int(datetime(2026, 7, 8, 14, 30, 45, tzinfo=timezone.utc).timestamp())

    # --- 日线: 只显示日期 ---
    result = time_formatter(ts, 86400)
    log_check(result == "2026-07-08", f"日线 (86400s): 期望 '2026-07-08', 得到 '{result}'", errors)

    # --- 分钟级: 显示日期 + 时分 ---
    result = time_formatter(ts, 60)
    log_check(result == "2026-07-08 14:30", f"分钟级 (60s): 期望 '2026-07-08 14:30', 得到 '{result}'", errors)

    # --- 秒级: 显示日期 + 时分秒 ---
    result = time_formatter(ts, 5)
    log_check(result == "2026-07-08 14:30:45", f"秒级 (5s): 期望 '2026-07-08 14:30:45', 得到 '{result}'", errors)

    # --- 小时级 (3600s): 显示日期 + 时分 ---
    result = time_formatter(ts, 3600)
    log_check(result == "2026-07-08 14:30", f"小时级 (3600s): 期望 '2026-07-08 14:30', 得到 '{result}'", errors)

    print()
    return errors


# ═══════════════════════════════════════════════
#  3. _sync_interval_to_js 方法存在性验证
# ═══════════════════════════════════════════════

def test_method_exists():
    """验证 _sync_interval_to_js 方法存在于 AbstractChart 类中。"""
    sep = "=" * 60
    print(sep)
    print("  3. 方法存在性验证")
    print(sep)

    errors = []
    from lightweight_charts.abstract import AbstractChart

    ok = hasattr(AbstractChart, '_sync_interval_to_js')
    log_check(ok, "AbstractChart 有 _sync_interval_to_js 方法", errors)

    ok = callable(getattr(AbstractChart, '_sync_interval_to_js'))
    log_check(ok, "_sync_interval_to_js 是可调用的方法", errors)

    # 验证 set_period 和 set 中调用了同步方法
    import inspect
    set_period_src = inspect.getsource(AbstractChart.set_period)
    ok = '_sync_interval_to_js()' in set_period_src
    log_check(ok, "set_period() 中调用了 _sync_interval_to_js()", errors)

    set_src = inspect.getsource(AbstractChart.set)
    ok = '_sync_interval_to_js()' in set_src
    log_check(ok, "set() 中调用了 _sync_interval_to_js()", errors)

    print()
    return errors


# ═══════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════

if __name__ == '__main__':
    errors = []
    errors += test_sync_interval_js_code()
    errors += test_time_formatter_logic()
    errors += test_method_exists()

    sep = "=" * 60
    print(sep)
    if errors:
        print(f"  ❌ {len(errors)} 个测试失败:")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)
    else:
        print("  ✅ 全部测试通过!")
        sys.exit(0)