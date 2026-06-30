"""
数据聚合正确性测试。

使用多种随机数据源（不同时间级别的 bar 和 tick 数据），
验证 candle / volume / OI / Line / Histogram 的数据聚合是否正确。

测试内容：
  1. set() 全量设置 — 不同频率数据
  2. update_bar() 单条更新
  3. update_bars() 批量更新
  4. update_from_ticks() tick 聚合
  5. 重复时间戳合并（merge_value_by_time）
  6. Python 端数据一致性
  7. 纯函数单元测试（get_df_interval_offset / normal_df / time_to_bar_time / merge_value_by_time）
  8. 跨时间级别聚合测试（5s→1min / 1min→5min / 1h→daily / 多级链式）
  9. 混沌测试（随机混合 ticks + bars + 不同时间级别，每步校验）
  10. 边界情况测试（空 DataFrame / 单行 / 乱序 / 重复时间戳）

Usage:
    python test/test_data_aggregation.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

import time
import pandas as pd
import numpy as np
from lightweight_charts import Chart
from lightweight_charts.util import (
    merge_value_by_time, merge_volume_by_time, normal_df, time_to_bar_time,
    get_df_interval_offset, filter_old_bars,
)


def ts_to_dt(ts):
    """UNIX 时间戳(float/int) → pd.Timestamp"""
    return pd.Timestamp(ts, unit='s', tz=None)


def dt_to_ts(dt):
    """pd.Timestamp → UNIX 时间戳(float)"""
    return (dt - pd.Timestamp("1970-01-01")) / pd.Timedelta('1s')


def log_check(ok, label, errors, err_key=None):
    if ok:
        print(f"      [OK] {label}")
    else:
        print(f"      [FAIL] {label}")
        if err_key:
            errors.append(err_key)
    return ok


# ═══════════════════════════════════════════════════════
#  数据生成器
# ═══════════════════════════════════════════════════════

def make_bar_data(n=30, freq='D', base_price=100, seed=42):
    """生成 bar 级别 OHLCV + OI + Line 数据。"""
    rng = np.random.RandomState(seed)
    dates = pd.date_range('2024-01-01', periods=n, freq=freq)
    close = base_price + np.cumsum(rng.randn(n) * 2)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    open_ = close + rng.randn(n) * 0.5
    volume = rng.randint(1000, 10000, n).astype(float)
    oi = rng.randint(5000, 20000, n).astype(float)
    sma = pd.Series(close).rolling(5, min_periods=1).mean().values
    rsi = 50 + rng.randn(n) * 10
    return pd.DataFrame({
        'time': dates, 'open': open_, 'high': high, 'low': low,
        'close': close, 'volume': volume, 'open_interest': oi,
        'SMA_5': sma, 'RSI_14': rsi,
    })


def make_tick_data(n=200, start_time=None, base_price=100, seed=99):
    """生成 tick 级别数据（秒级时间戳），时间在 start_time 之后。"""
    rng = np.random.RandomState(seed)
    if start_time is None:
        start_time = pd.Timestamp('2024-01-01')
    # 随机秒级偏移，集中在几个 1 分钟窗口内
    seconds = rng.randint(0, 300, n)
    minutes = np.repeat(np.arange(n // 10 + 1)[:n], 10)[:n]
    times = start_time + pd.to_timedelta(minutes, unit='min') + pd.to_timedelta(seconds, unit='s')
    times = pd.Series(times).sort_values().reset_index(drop=True)
    price = base_price + np.cumsum(rng.randn(n) * 0.3)
    volume = rng.randint(10, 500, n).astype(float)
    oi = rng.randint(1000, 5000, n).astype(float)
    return pd.DataFrame({
        'time': times, 'price': price, 'volume': volume, 'open_interest': oi,
    })


# ═══════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════

def create_full_chart():
    """创建包含所有系列类型的图表。"""
    chart = Chart(width=1000, height=600)
    chart.show(block=False)

    line_sma = chart.create_line(name='SMA_5', color='rgba(255, 200, 0, 0.8)', width=2)
    line_rsi = chart.create_line(name='RSI_14', color='rgba(100, 200, 255, 0.6)', width=1, pane_index=1)
    hist_vol = chart.create_histogram(name='vol_hist', color='rgba(100, 200, 100, 0.5)', pane_index=2)

    return chart, line_sma, line_rsi, hist_vol


def verify_set(chart, df, label, errors):
    """验证 set() 后 Python 端数据一致性（行数 + 值）。"""
    all_clean = True

    # ── 行数校验 ──
    ok = len(chart.data) == len(df)
    all_clean &= log_check(ok, f"{label} candle rows={len(chart.data)} == {len(df)}", errors, f"{label}_candle_rows")

    ok = len(chart.volume.data) == len(df)
    all_clean &= log_check(ok, f"{label} volume rows={len(chart.volume.data)} == {len(df)}", errors, f"{label}_vol_rows")

    ok = len(chart.oi.data) == len(df)
    all_clean &= log_check(ok, f"{label} oi rows={len(chart.oi.data)} == {len(df)}", errors, f"{label}_oi_rows")

    # ── 值校验：candle OHLC ──
    for col in ('open', 'high', 'low', 'close'):
        match = np.allclose(chart.data[col].values, df[col].values, rtol=1e-6)
        all_clean &= log_check(match, f"{label} candle.{col} values match", errors, f"{label}_candle_{col}")

    # ── 值校验：volume ──
    match = np.allclose(chart.volume.data['value'].values, df['volume'].values, rtol=1e-6)
    all_clean &= log_check(match, f"{label} volume values match", errors, f"{label}_vol_values")

    # ── 值校验：OI ──
    match = np.allclose(chart.oi.data['value'].values, df['open_interest'].values, rtol=1e-6)
    all_clean &= log_check(match, f"{label} OI values match", errors, f"{label}_oi_values")

    # ── _last_bar 时间一致 ──
    ok = chart.candle._last_bar['time'] == chart.volume._last_bar['time']
    all_clean &= log_check(ok, f"{label} candle._last_bar == volume._last_bar", errors, f"{label}_last_bar_match")

    ok = chart.candle._last_bar['time'] == chart.oi._last_bar['time']
    all_clean &= log_check(ok, f"{label} candle._last_bar == oi._last_bar", errors, f"{label}_last_bar_oi_match")

    return all_clean


def assert_close(actual, expected, label, errors, tol=1e-6):
    """校验两个 DataFrame 是否近似相等（忽略列顺序）。返回 True/False。"""
    if actual is None or expected is None:
        if actual is not expected:
            errors.append(f"{label}: one is None")
            print(f"      [FAIL] {label}: actual={'None' if actual is None else 'df'}, expected={'None' if expected is None else 'df'}")
            return False
        return True
    if len(actual) != len(expected):
        errors.append(f"{label}: rows {len(actual)} != {len(expected)}")
        print(f"      [FAIL] {label}: rows {len(actual)} != {len(expected)}")
        return False
    for col in expected.columns:
        if col not in actual.columns:
            errors.append(f"{label}: missing column '{col}'")
            print(f"      [FAIL] {label}: missing column '{col}'")
            return False
        if not np.allclose(actual[col].values, expected[col].values, atol=tol, equal_nan=True):
            diff = actual[col].values - expected[col].values
            errors.append(f"{label}: {col} mismatch (max diff={np.max(np.abs(diff)):.8f})")
            print(f"      [FAIL] {label}: {col} mismatch (max diff={np.max(np.abs(diff)):.8f})")
            return False
    print(f"      [OK] {label}")
    return True


def compute_expected(expected, new_bars, chart, is_ticks=False, cumulative_volume=False,
                     prev_last_bar=None):
    """
    模拟 chart 的聚合管线，计算期望结果（仅 OHLC 列）。

    对每批 new_bars（原始 tick 或 bar），复刻：
      normal_df → time_to_bar_time → merge_value_by_time
      → update_from_ticks OHLC 聚合（is_ticks=True 时）
      → last-bar 继承（open 不变, high=max, low=min）
      → filter 旧数据 → concat + dedup（replace-or-append）

    返回的 DataFrame 仅含 time/open/high/low/close，与 chart.candle.data 对齐。

    :param expected: 当前期望状态（DataFrame），None 表示尚未初始化
    :param new_bars: 本批输入数据（DataFrame，原始 tick 或 bar）
    :param chart: 真实 Chart 实例（用于获取 interval/offset）
    :param is_ticks: True 表示输入是 tick 数据，需要 OHLC 聚合
    :param cumulative_volume: update_from_ticks 的 cumulative_volume 参数
    :param prev_last_bar: 操作前的 candle._last_bar（用于 last-bar 继承），None 则跳过继承
    :return: 更新后的期望状态（DataFrame，time/open/high/low/close）
    """
    if new_bars is None or new_bars.empty:
        return expected

    # 1. clean（复刻 AbstractChart.update_from_ticks 的清洗路径）
    #    tick 路径：normal_df + time_to_bar_time（不做 merge_value_by_time！）
    #    bar 路径：normal_df + time_to_bar_time + merge_value_by_time
    df = normal_df(new_bars)
    df = time_to_bar_time(df, chart._offset, chart._interval)
    if not is_ticks:
        df = merge_value_by_time(df)

    # 2. tick 路径 OHLC 聚合：AbstractChart 将 price → value 后交给 CandleSeries
    if is_ticks and 'price' in df.columns:
        df = df.rename(columns={'price': 'value'})
    if is_ticks and 'value' in df.columns:
        group_df = df.groupby('time')
        bars = pd.DataFrame({
            'time': list(group_df.groups),
            'open': group_df['value'].first().values,
            'high': group_df['value'].max().values,
            'low': group_df['value'].min().values,
            'close': group_df['value'].last().values,
        })
        df = bars

    # 只保留 OHLC 列（与 chart.candle.data 对齐）
    ohlc_cols = ['time', 'open', 'high', 'low', 'close']
    df = df[[c for c in ohlc_cols if c in df.columns]]

    # 4. filter 旧数据
    if expected is not None and not expected.empty:
        last_time = expected.iloc[-1]['time']
        df = df[df['time'] >= last_time]
        if df.empty:
            return expected

    # 5. replace-or-append（精确复刻 CandleSeries.update_bars 的逻辑）
    #    关键：仅在第一个新 bar 的时间 == 最后一根旧 bar 的时间时做 OHLC 合并
    #    其他情况下，新 bar 简单追加，不会和旧 bar 合并
    #    ⚠️ OHLC 合并只作用于 df.iloc[0]（第一个新 bar），剩余 bar 直接追加
    if expected is None or expected.empty:
        return df.reset_index(drop=True)
    result = expected.copy()
    if len(df) > 0 and df.iloc[0]['time'] == result.iloc[-1]['time']:
        # OHLC 合并：保留旧 open，用第一个新 bar 的 high/low/close + 旧 high/low 取极值
        new_row = df.iloc[0].copy()
        new_row['open'] = result.iloc[-1]['open']
        new_row['high'] = max(result.iloc[-1]['high'], new_row['high'])
        new_row['low'] = min(result.iloc[-1]['low'], new_row['low'])
        result = pd.concat([result.iloc[:-1], new_row.to_frame().T, df.iloc[1:]], ignore_index=True)
    else:
        # 简单追加
        result = pd.concat([result, df], ignore_index=True)
    return result.reset_index(drop=True)


# ═══════════════════════════════════════════════════════
#  测试 1: set() 全量设置 — 不同频率
# ═══════════════════════════════════════════════════════

def test_set_different_frequencies():
    sep = "=" * 60
    print(sep)
    print("  test_set_different_frequencies")
    print(sep)

    chart, line_sma, line_rsi, hist_vol = create_full_chart()
    errors = []
    all_clean = True

    # 1a. 日线
    print("\n[1a] set() daily bars ...")
    df = make_bar_data(30, 'D', 100, 42)
    chart.set(df)
    line_sma.set(df[['time', 'SMA_5']].rename(columns={'SMA_5': 'value'}))
    line_rsi.set(df[['time', 'RSI_14']].rename(columns={'RSI_14': 'value'}))
    all_clean &= verify_set(chart, df, "daily", errors)
    all_clean &= log_check(len(line_sma.data) == 30, f"daily SMA rows={len(line_sma.data)}", errors, "daily_sma")
    all_clean &= log_check(len(line_rsi.data) == 30, f"daily RSI rows={len(line_rsi.data)}", errors, "daily_rsi")

    # 1b. 5 分钟线
    print("\n[1b] set() 5min bars ...")
    df = make_bar_data(50, '5min', 200, 55)
    chart.set(df)
    line_sma.set(df[['time', 'SMA_5']].rename(columns={'SMA_5': 'value'}))
    line_rsi.set(df[['time', 'RSI_14']].rename(columns={'RSI_14': 'value'}))
    all_clean &= verify_set(chart, df, "5min", errors)

    # 1c. 1 分钟线
    print("\n[1c] set() 1min bars ...")
    df = make_bar_data(60, 'min', 150, 77)
    chart.set(df)
    line_sma.set(df[['time', 'SMA_5']].rename(columns={'SMA_5': 'value'}))
    line_rsi.set(df[['time', 'RSI_14']].rename(columns={'RSI_14': 'value'}))
    all_clean &= verify_set(chart, df, "1min", errors)

    # 1d. 1 小时线
    print("\n[1d] set() 1h bars ...")
    df = make_bar_data(40, 'h', 300, 88)
    chart.set(df)
    line_sma.set(df[['time', 'SMA_5']].rename(columns={'SMA_5': 'value'}))
    line_rsi.set(df[['time', 'RSI_14']].rename(columns={'RSI_14': 'value'}))
    all_clean &= verify_set(chart, df, "1h", errors)

    chart.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 2: update_bar() 单条更新
# ═══════════════════════════════════════════════════════

def test_update_bar():
    sep = "=" * 60
    print(sep)
    print("  test_update_bar")
    print(sep)

    chart, line_sma, line_rsi, hist_vol = create_full_chart()
    errors = []
    all_clean = True

    df = make_bar_data(20, 'D', 100, 42)
    chart.set(df)
    line_sma.set(df[['time', 'SMA_5']].rename(columns={'SMA_5': 'value'}))
    line_rsi.set(df[['time', 'RSI_14']].rename(columns={'RSI_14': 'value'}))
    initial_rows = len(chart.data)

    # 单条新 bar
    print("\n[1] update_bar() append new bar ...")
    new_bar = pd.Series({
        'time': pd.Timestamp('2024-01-21'),
        'open': 105, 'high': 108, 'low': 103, 'close': 107,
        'volume': 5000, 'open_interest': 8000,
        'SMA_5': 104, 'RSI_14': 55,
    }, index=['time', 'open', 'high', 'low', 'close', 'volume', 'open_interest', 'SMA_5', 'RSI_14'])
    chart.update_bar(new_bar)
    line_sma.update_bar(pd.Series({'time': new_bar['time'], 'value': new_bar['SMA_5']}))
    line_rsi.update_bar(pd.Series({'time': new_bar['time'], 'value': new_bar['RSI_14']}))
    all_clean &= log_check(len(chart.data) == initial_rows + 1, f"rows={len(chart.data)} == {initial_rows + 1}", errors, "append_rows")
    all_clean &= log_check(len(line_sma.data) == initial_rows + 1, f"SMA rows={len(line_sma.data)}", errors, "append_sma")

    # 值校验：追加的 bar 所有字段
    last = chart.data.iloc[-1]
    all_clean &= log_check(last['open'] == 105, f"append open={last['open']}==105", errors, "append_open")
    all_clean &= log_check(last['high'] == 108, f"append high={last['high']}==108", errors, "append_high")
    all_clean &= log_check(last['low'] == 103, f"append low={last['low']}==103", errors, "append_low")
    all_clean &= log_check(last['close'] == 107, f"append close={last['close']}==107", errors, "append_close")
    all_clean &= log_check(chart.volume.data.iloc[-1]['value'] == 5000, f"append volume=5000", errors, "append_vol")
    all_clean &= log_check(chart.oi.data.iloc[-1]['value'] == 8000, f"append OI=8000", errors, "append_oi")

    # 更新同一时间
    print("\n[2] update_bar() update existing bar ...")
    update_bar = pd.Series({
        'time': pd.Timestamp('2024-01-21'),
        'open': 105, 'high': 110, 'low': 102, 'close': 109,
        'volume': 6000, 'open_interest': 8500,
        'SMA_5': 106, 'RSI_14': 60,
    }, index=['time', 'open', 'high', 'low', 'close', 'volume', 'open_interest', 'SMA_5', 'RSI_14'])
    chart.update_bar(update_bar)
    line_sma.update_bar(pd.Series({'time': update_bar['time'], 'value': update_bar['SMA_5']}))
    line_rsi.update_bar(pd.Series({'time': update_bar['time'], 'value': update_bar['RSI_14']}))
    all_clean &= log_check(len(chart.data) == initial_rows + 1, f"rows still {len(chart.data)} (no duplicate)", errors, "update_no_dup")
    # 值校验：更新后的 bar 所有字段
    last = chart.data.iloc[-1]
    all_clean &= log_check(last['high'] == 110, f"update high={last['high']}==110", errors, "update_high")
    all_clean &= log_check(last['low'] == 102, f"update low={last['low']}==102", errors, "update_low")
    all_clean &= log_check(last['close'] == 109, f"update close={last['close']}==109", errors, "update_close")
    all_clean &= log_check(chart.volume.data.iloc[-1]['value'] == 6000, f"update volume=6000", errors, "update_vol")
    all_clean &= log_check(chart.oi.data.iloc[-1]['value'] == 8500, f"update OI=8500", errors, "update_oi")

    chart.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 3: update_bars() 批量更新
# ═══════════════════════════════════════════════════════

def test_update_bars():
    sep = "=" * 60
    print(sep)
    print("  test_update_bars")
    print(sep)

    chart, line_sma, line_rsi, hist_vol = create_full_chart()
    errors = []
    all_clean = True

    df = make_bar_data(20, 'D', 100, 42)
    chart.set(df)
    line_sma.set(df[['time', 'SMA_5']].rename(columns={'SMA_5': 'value'}))
    line_rsi.set(df[['time', 'RSI_14']].rename(columns={'RSI_14': 'value'}))
    initial_rows = len(chart.data)

    # 批量追加
    print("\n[1] update_bars() batch append ...")
    batch = make_bar_data(10, 'D', 100, 99)
    batch['time'] = pd.date_range('2024-01-21', periods=10, freq='D')
    chart.update_bars(batch)
    line_sma.update_bars(batch[['time', 'SMA_5']].rename(columns={'SMA_5': 'value'}))
    line_rsi.update_bars(batch[['time', 'RSI_14']].rename(columns={'RSI_14': 'value'}))
    all_clean &= log_check(len(chart.data) == initial_rows + 10, f"rows={len(chart.data)} == {initial_rows + 10}", errors, "batch_rows")
    all_clean &= log_check(len(line_sma.data) == initial_rows + 10, f"SMA rows={len(line_sma.data)}", errors, "batch_sma")

    # 值校验：批量追加后最后几行的 OHLCV + OI 与输入一致
    for i in range(-3, 0):
        row_in = batch.iloc[i]
        row_out = chart.data.iloc[i]
        all_clean &= log_check(
            row_out['open'] == row_in['open'] and row_out['high'] == row_in['high']
            and row_out['low'] == row_in['low'] and row_out['close'] == row_in['close'],
            f"batch bar[{i}] OHLC match", errors, f"batch_ohlc_{i}"
        )
    # volume/OI 值校验
    vol_last3 = chart.volume.data['value'].iloc[-3:].values
    oi_last3 = chart.oi.data['value'].iloc[-3:].values
    all_clean &= log_check(np.allclose(vol_last3, batch['volume'].iloc[-3:].values), f"batch volume last3 match", errors, "batch_vol")
    all_clean &= log_check(np.allclose(oi_last3, batch['open_interest'].iloc[-3:].values), f"batch OI last3 match", errors, "batch_oi")

    # 批量部分重叠（首条与已有最后一条相同时间 → OHLC 合并，不新增行）
    print("\n[2] update_bars() batch with overlap ...")
    overlap = batch.iloc[:3].copy()
    overlap['time'] = chart.data.iloc[-1]['time']  # 全部 3 条都是同一时间
    last_before = chart.data.iloc[-1].copy()  # 快照：合并前的最后一根
    chart.update_bars(overlap)
    # 首条同时间 bar 与已有最后一根做 OHLC 合并：open=旧保留, high=max, low=min, close=最后一条
    # merge_value_by_time 先将 3 条同时间 bar 聚合为 1 条，再做边界替换
    expected = initial_rows + 10
    all_clean &= log_check(len(chart.data) == expected, f"rows={len(chart.data)} == {expected} (overlap updates, no new rows)", errors, "overlap_rows")
    last_chart = chart.data.iloc[-1]
    all_clean &= log_check(
        last_chart['open'] == last_before['open']  # 旧 open 保留
        and last_chart['high'] == max(last_before['high'], overlap['high'].max())
        and last_chart['low'] == min(last_before['low'], overlap['low'].min())
        and last_chart['close'] == overlap.iloc[-1]['close'],
        f"overlap bar OHLC merged correctly", errors, "overlap_ohlc"
    )
    # volume: sum
    all_clean &= log_check(
        chart.volume.data.iloc[-1]['value'] == overlap['volume'].sum(),
        f"overlap volume={chart.volume.data.iloc[-1]['value']} == sum={overlap['volume'].sum()}", errors, "overlap_vol"
    )
    # OI: last
    all_clean &= log_check(
        chart.oi.data.iloc[-1]['value'] == overlap.iloc[-1]['open_interest'],
        f"overlap OI updated to last", errors, "overlap_oi"
    )

    chart.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 4: update_from_ticks() tick 聚合
# ═══════════════════════════════════════════════════════

def test_update_ticks():
    sep = "=" * 60
    print(sep)
    print("  test_update_from_ticks")
    print(sep)

    chart, line_sma, line_rsi, hist_vol = create_full_chart()
    errors = []
    all_clean = True

    # 先设置一个基准 bar（截止到 2024-01-05）
    df_base = make_bar_data(5, 'D', 100, 42)
    chart.set(df_base)
    initial_rows = len(chart.data)

    # 生成 tick 数据（从基准数据之后开始）
    print("\n[1] update_from_ticks() basic ...")
    last_time = chart.candle._last_bar['time']
    ticks = make_tick_data(100, start_time=ts_to_dt(last_time) + pd.Timedelta(days=1), base_price=100, seed=99)
    chart.update_ticks(ticks)

    # tick 聚合后应该产生新 bar
    ok = len(chart.data) > initial_rows
    all_clean &= log_check(ok, f"rows grew: {initial_rows} -> {len(chart.data)}", errors, "tick_grow")

    # volume 和 oi 也应该增长
    ok = len(chart.volume.data) > initial_rows
    all_clean &= log_check(ok, f"vol rows grew: {initial_rows} -> {len(chart.volume.data)}", errors, "tick_vol_grow")
    ok = len(chart.oi.data) > initial_rows
    all_clean &= log_check(ok, f"oi rows grew: {initial_rows} -> {len(chart.oi.data)}", errors, "tick_oi_grow")

    # ── 值校验：手动聚合 tick → 与 chart 内部结果比对 ──
    # 先用 normal_df + time_to_bar_time 处理 tick 数据（与库内部一致）
    from lightweight_charts.util import normal_df, time_to_bar_time
    ticks_clean = normal_df(ticks)
    ticks_clean = time_to_bar_time(ticks_clean, offset=chart._offset, interval=chart._interval)
    # 按 time 分组聚合
    grouped = ticks_clean.groupby('time')
    expected_open = grouped['price'].first()
    expected_high = grouped['price'].max()
    expected_low = grouped['price'].min()
    expected_close = grouped['price'].last()
    expected_vol = grouped['volume'].sum()
    expected_oi = grouped['open_interest'].last()
    expected_times = list(grouped.groups)

    # 只比较新增的 bar（chart.data 中 initial_rows 之后的部分）
    new_candle = chart.data.iloc[initial_rows:]
    new_vol = chart.volume.data.iloc[initial_rows:]
    new_oi = chart.oi.data.iloc[initial_rows:]

    # 时间对齐：chart 可能合并了部分 bar，逐行匹配
    for idx, exp_t in enumerate(expected_times):
        # 在 chart 新增数据中找到对应时间
        candle_match = new_candle[new_candle['time'] == exp_t]
        vol_match = new_vol[new_vol['time'] == exp_t]
        oi_match = new_oi[new_oi['time'] == exp_t]
        if len(candle_match) == 0:
            all_clean &= log_check(False, f"tick time {exp_t} not in candle", errors, f"tick_candle_miss_{idx}")
            continue
        c = candle_match.iloc[0]
        all_clean &= log_check(c['open'] == expected_open.iloc[idx], f"tick open={c['open']:.4f}=={expected_open.iloc[idx]:.4f}", errors, f"tick_open_{idx}")
        all_clean &= log_check(c['high'] == expected_high.iloc[idx], f"tick high={c['high']:.4f}=={expected_high.iloc[idx]:.4f}", errors, f"tick_high_{idx}")
        all_clean &= log_check(c['low'] == expected_low.iloc[idx], f"tick low={c['low']:.4f}=={expected_low.iloc[idx]:.4f}", errors, f"tick_low_{idx}")
        all_clean &= log_check(c['close'] == expected_close.iloc[idx], f"tick close={c['close']:.4f}=={expected_close.iloc[idx]:.4f}", errors, f"tick_close_{idx}")
        if len(vol_match) > 0:
            all_clean &= log_check(
                vol_match.iloc[0]['value'] == expected_vol.iloc[idx],
                f"tick volume={vol_match.iloc[0]['value']}=={expected_vol.iloc[idx]}", errors, f"tick_vol_{idx}"
            )
        if len(oi_match) > 0:
            all_clean &= log_check(
                oi_match.iloc[0]['value'] == expected_oi.iloc[idx],
                f"tick OI={oi_match.iloc[0]['value']}=={expected_oi.iloc[idx]}", errors, f"tick_oi_{idx}"
            )

    # candle / volume / oi 的 _last_bar 时间应一致
    all_clean &= log_check(
        chart.candle._last_bar['time'] == chart.volume._last_bar['time'],
        "candle._last_bar == volume._last_bar after ticks",
        errors, "tick_last_bar_match"
    )

    # 重复 tick 聚合（累积 volume）
    print("\n[2] update_from_ticks() cumulative volume ...")
    rows_before = len(chart.data)
    ticks2 = make_tick_data(50, start_time=ts_to_dt(chart.candle._last_bar['time']) + pd.Timedelta(days=1), base_price=100, seed=77)
    chart.update_ticks(ticks2)
    all_clean &= log_check(len(chart.data) >= rows_before, f"rows >= {rows_before}", errors, "cum_vol_rows")

    chart.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 5: 重复时间戳合并（merge_value_by_time 纯函数）
# ═══════════════════════════════════════════════════════

def test_duplicate_time_merge():
    sep = "=" * 60
    print(sep)
    print("  test_duplicate_time_merge")
    print(sep)

    errors = []
    all_clean = True

    # 直接测试 merge_value_by_time 纯函数（不经过 set，避免 interval 检测问题）
    rng = np.random.RandomState(77)
    rows = []
    for i in range(10):
        for _ in range(rng.randint(2, 4)):
            rows.append({
                'time': 1704067200 + i * 86400,  # 日线秒级时间戳
                'open': 100 + rng.randn(),
                'high': 102 + abs(rng.randn()),
                'low': 98 - abs(rng.randn()),
                'close': 100 + rng.randn(),
                'volume': rng.randint(100, 1000),
                'open_interest': rng.randint(5000, 10000),
            })
    df = pd.DataFrame(rows)
    unique_times = df['time'].nunique()
    print(f"\n  Input: {len(df)} rows, {unique_times} unique times")

    # normal_df + merge_value_by_time
    df = normal_df(df)
    merged = merge_value_by_time(df)

    print("\n[1] merge_value_by_time result ...")
    all_clean &= log_check(
        len(merged) == unique_times,
        f"merged rows={len(merged)} == {unique_times}",
        errors, "merge_count"
    )

    # 验证 OHLC 聚合
    print("\n[2] Verify OHLC merge values ...")
    for t in df['time'].unique()[:3]:
        group = df[df['time'] == t]
        merged_row = merged[merged['time'] == t]
        if len(merged_row) == 1:
            all_clean &= log_check(
                merged_row.iloc[0]['high'] == group['high'].max(),
                f"high={merged_row.iloc[0]['high']:.4f} == max={group['high'].max():.4f}",
                errors, f"merge_high_{t}"
            )
            all_clean &= log_check(
                merged_row.iloc[0]['low'] == group['low'].min(),
                f"low={merged_row.iloc[0]['low']:.4f} == min={group['low'].min():.4f}",
                errors, f"merge_low_{t}"
            )

    # 验证 volume 聚合（sum）
    print("\n[3] Verify volume merge (sum) ...")
    for t in df['time'].unique()[:3]:
        group = df[df['time'] == t]
        merged_row = merged[merged['time'] == t]
        if len(merged_row) == 1:
            all_clean &= log_check(
                merged_row.iloc[0]['volume'] == group['volume'].sum(),
                f"volume={merged_row.iloc[0]['volume']} == sum={group['volume'].sum()}",
                errors, f"merge_vol_{t}"
            )

    # 验证 OI 聚合（last）
    print("\n[4] Verify OI merge (last) ...")
    for t in df['time'].unique()[:3]:
        group = df[df['time'] == t]
        merged_row = merged[merged['time'] == t]
        if len(merged_row) == 1:
            all_clean &= log_check(
                merged_row.iloc[0]['open_interest'] == group['open_interest'].iloc[-1],
                f"oi={merged_row.iloc[0]['open_interest']} == last={group['open_interest'].iloc[-1]}",
                errors, f"merge_oi_{t}"
            )

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 6: _last_bar 过滤一致性
# ═══════════════════════════════════════════════════════

def test_last_bar_filter():
    sep = "=" * 60
    print(sep)
    print("  test_last_bar_filter")
    print(sep)

    chart, line_sma, line_rsi, hist_vol = create_full_chart()
    errors = []
    all_clean = True

    df = make_bar_data(20, 'D', 100, 42)
    chart.set(df)
    initial_rows = len(chart.data)

    # 传入包含旧数据 + 新数据的混合
    print("\n[1] update_bars() with old + new data ...")
    old_bar = df.iloc[-1:].copy()  # 旧 bar
    new_bar = make_bar_data(3, 'D', 100, 88)
    new_bar['time'] = pd.date_range('2024-01-21', periods=3, freq='D')
    mixed = pd.concat([old_bar, new_bar], ignore_index=True)

    chart.update_bars(mixed)

    # 旧 bar 会被 >= 过滤保留（时间 == _last_bar），新 bar 追加
    # 但旧 bar 是更新已有 bar（同时间），不新增行
    expected = initial_rows + 3
    all_clean &= log_check(
        len(chart.data) == expected,
        f"rows={len(chart.data)} == {expected} (old bar filtered/merged, new bars appended)",
        errors, "filter_rows"
    )
    all_clean &= log_check(
        len(chart.volume.data) == expected,
        f"vol rows={len(chart.volume.data)} == {expected}",
        errors, "filter_vol"
    )
    all_clean &= log_check(
        len(chart.oi.data) == expected,
        f"oi rows={len(chart.oi.data)} == {expected}",
        errors, "filter_oi"
    )

    # 完全旧数据 — 不应增长
    print("\n[2] update_bars() with only old data ...")
    rows_before = len(chart.data)
    chart.update_bars(df.iloc[:5])
    all_clean &= log_check(
        len(chart.data) == rows_before,
        f"rows unchanged: {len(chart.data)} == {rows_before}",
        errors, "filter_no_growth"
    )

    chart.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 7: Line/Histogram 使用 value 列设置数据
# ═══════════════════════════════════════════════════════

def test_line_value_column():
    sep = "=" * 60
    print(sep)
    print("  test_line_value_column")
    print(sep)

    chart = Chart(width=800, height=600)
    chart.show(block=False)
    errors = []
    all_clean = True

    line_sma = chart.create_line(name='MySMA', color='yellow', width=2)
    line_rsi = chart.create_line(name='rsi', color='cyan', width=1)
    hist = chart.create_histogram(name='vol_hist', color='green')

    df = make_bar_data(20, 'D', 100, 42)
    sma_values = df['close'].rolling(5, min_periods=1).mean()
    rsi_values = pd.Series(50 + np.random.RandomState(42).randn(20) * 10)

    print("\n[1] set() with value column ...")
    chart.set(df)
    line_sma.set(pd.DataFrame({'time': df['time'], 'value': sma_values}))
    line_rsi.set(pd.DataFrame({'time': df['time'], 'value': rsi_values}))
    hist.set(pd.DataFrame({'time': df['time'], 'value': df['volume']}))

    all_clean &= log_check(
        len(line_sma.data) == 20,
        f"MySMA rows={len(line_sma.data)}",
        errors, "value_upper"
    )
    all_clean &= log_check(
        len(line_rsi.data) == 20,
        f"rsi rows={len(line_rsi.data)}",
        errors, "value_lower"
    )
    all_clean &= log_check(
        len(hist.data) == 20,
        f"hist rows={len(hist.data)}",
        errors, "value_hist"
    )

    # 验证数据值正确
    print("\n[2] Verify data values match ...")
    all_clean &= log_check(
        abs(line_sma.data.iloc[-1]['value'] - sma_values.iloc[-1]) < 0.01,
        f"MySMA last value matches",
        errors, "value_upper_val"
    )
    all_clean &= log_check(
        abs(line_rsi.data.iloc[-1]['value'] - rsi_values.iloc[-1]) < 0.01,
        f"rsi last value matches",
        errors, "value_lower_val"
    )

    # 验证缺少 value 列时抛出异常
    print("\n[3] Verify missing value column raises error ...")
    try:
        line_sma.set(pd.DataFrame({'time': df['time'], 'close': df['close']}))
        all_clean &= log_check(False, "should have raised ValueError", errors, "value_missing_raises")
    except ValueError:
        all_clean &= log_check(True, "ValueError raised for missing value column", errors, "value_missing_raises")

    chart.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 7: 纯函数单元测试
# ═══════════════════════════════════════════════════════

def test_util_functions():
    sep = "=" * 60
    print(sep)
    print("  test_util_functions")
    print(sep)

    errors = []
    all_clean = True

    # ── get_df_interval_offset ──
    print("\n[1] get_df_interval_offset() ...")
    cases = [
        (1,    '1s',   0),     # 1s, no offset
        (5,    '5s',   0),     # 5s
        (60,   '1min', 0),     # 1min
        (300,  '5min', 0),     # 5min
        (3600, '1h',   0),     # 1h
    ]
    for interval_sec, label, _ in cases:
        base = pd.Timestamp('2024-01-01')
        times = [base + pd.Timedelta(seconds=interval_sec * i) for i in range(20)]
        df = pd.DataFrame({'time': times, 'value': np.arange(20, dtype=float)})
        df = normal_df(df)
        det_interval, offset = get_df_interval_offset(df)
        ok = det_interval == interval_sec
        all_clean &= log_check(ok, f"{label}: interval={det_interval}=={interval_sec}", errors, f"interval_{label}")

    # ── normal_df 格式处理 ──
    print("\n[2] normal_df() format handling ...")
    # index 作为 time
    df_idx = pd.DataFrame({'value': range(5)}, index=pd.date_range('2024-01-01', periods=5, freq='D'))
    ndf = normal_df(df_idx)
    all_clean &= log_check('time' in ndf.columns, "index→time", errors, "normal_df_index")
    # Unix 时间戳（int）
    base_ts = int(pd.Timestamp('2024-01-01').timestamp())
    df_ts = pd.DataFrame({'time': [base_ts + 86400 * i for i in range(5)], 'value': range(5)})
    ndf = normal_df(df_ts)
    all_clean &= log_check(ndf['time'].dtype in (np.int64, np.float64),
                            "unix timestamp passthrough", errors, "normal_df_ts")

    # ── time_to_bar_time 边界对齐 ──
    print("\n[3] time_to_bar_time() boundary alignment ...")
    base = pd.Timestamp('2024-01-01 00:00:00')
    test_times = [
        pd.Timestamp('2024-01-01 12:03:45'),  # → 12:00:00 (1h)
        pd.Timestamp('2024-01-01 12:07:22'),  # → 12:05:00 (5min)
        pd.Timestamp('2024-01-01 12:07:37'),  # → 12:07:35 (5s)
    ]
    intervals = [3600, 300, 5]
    offsets = [0, 0, 0]
    expected_hms = [(12, 0, 0), (12, 5, 0), (12, 7, 35)]
    for tt, intv, off, (h, m, s) in zip(test_times, intervals, offsets, expected_hms):
        ts = int((base + pd.Timedelta(hours=tt.hour, minutes=tt.minute, seconds=tt.second) - base).total_seconds())
        aligned = int(time_to_bar_time(ts, off, intv))
        aligned_dt = pd.Timestamp(aligned, unit='s')
        ok = aligned_dt.hour == h and aligned_dt.minute == m and aligned_dt.second == s
        all_clean &= log_check(ok,
                                f"{tt.strftime('%H:%M:%S')} → {aligned_dt.strftime('%H:%M:%S')} (intv={intv}s)",
                                errors, f"align_{tt.strftime('%H%M%S')}")
    # Series 输入（3 个值：ts+1→ts, ts+61→ts+60, ts+121→ts+120 → 3 unique）
    series_in = pd.Series([ts + 1, ts + 61, ts + 121])
    aligned_series = time_to_bar_time(series_in, 0, 60)
    all_clean &= log_check(len(aligned_series) == 3 and aligned_series.nunique() == 3,
                            "Series alignment: 3 inputs → 3 unique", errors, "align_series")
    # DataFrame 输入
    df_in = pd.DataFrame({'time': [ts + 1, ts + 61], 'value': [1.0, 2.0]})
    aligned_df = time_to_bar_time(df_in, 0, 60)
    all_clean &= log_check('time' in aligned_df.columns and aligned_df['time'].nunique() == 2,
                            "DataFrame alignment", errors, "align_df")

    # ── merge_value_by_time OHLC 语义 ──
    print("\n[4] merge_value_by_time() OHLC semantics ...")
    t = int(pd.Timestamp('2024-01-01').timestamp())
    df = pd.DataFrame({
        'time': [t, t, t],
        'open': [100.0, 102.0, 101.0],
        'high': [105.0, 110.0, 108.0],
        'low':  [98.0,  99.0,  97.0],
        'close': [103.0, 107.0, 109.0],
        'volume': [1000.0, 2000.0, 3000.0],
        'open_interest': [5000.0, 6000.0, 7000.0],
    })
    merged = merge_value_by_time(df)
    all_clean &= log_check(merged.iloc[0]['open'] == 100.0, "open=first=100", errors, "merge_open")
    all_clean &= log_check(merged.iloc[0]['high'] == 110.0, "high=max=110", errors, "merge_high")
    all_clean &= log_check(merged.iloc[0]['low'] == 97.0, "low=min=97", errors, "merge_low")
    all_clean &= log_check(merged.iloc[0]['close'] == 109.0, "close=last=109", errors, "merge_close")
    all_clean &= log_check(merged.iloc[0]['volume'] == 6000.0, "volume=sum=6000", errors, "merge_vol")
    all_clean &= log_check(merged.iloc[0]['open_interest'] == 7000.0, "OI=last=7000", errors, "merge_oi")
    # 不同时间 → 不合并
    df2 = pd.DataFrame({'time': [t, t + 60], 'value': [1.0, 2.0]})
    merged2 = merge_value_by_time(df2)
    all_clean &= log_check(len(merged2) == 2, "different times not merged", errors, "merge_no_merge")

    chart = Chart()
    chart.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 8: 跨时间级别聚合测试
# ═══════════════════════════════════════════════════════

def test_cross_level_aggregation():
    sep = "=" * 60
    print(sep)
    print("  test_cross_level_aggregation")
    print(sep)

    errors = []
    all_clean = True

    def verify_agg(chart, expected, label):
        """校验 chart.candle.data 与期望结果（OHLC + 时间）。"""
        nonlocal all_clean
        cols = ['time', 'open', 'high', 'low', 'close']
        all_clean &= assert_close(chart.candle.data[cols], expected[cols], label, errors)

    # ── [1] 5s → 1min ──
    print("\n[1] 5s → 1min aggregation ...")
    base = pd.Timestamp('2024-01-01')
    t_1min = int(base.timestamp())
    times_5s = [t_1min + i * 5 for i in range(12)]
    rng = np.random.RandomState(101)
    prices = 100 + np.cumsum(rng.randn(12) * 0.5)
    highs = prices + rng.uniform(0.1, 0.5, 12)
    lows = prices - rng.uniform(0.1, 0.5, 12)
    df_5s = pd.DataFrame({
        'time': [pd.Timestamp(t, unit='s') for t in times_5s],
        'open': prices, 'high': highs, 'low': lows, 'close': prices,
        'volume': rng.randint(100, 500, 12).astype(float),
        'open_interest': rng.randint(1000, 5000, 12).astype(float),
    })
    # 手动聚合：groupby aligned time
    df_5s_norm = normal_df(df_5s)
    df_5s_norm = time_to_bar_time(df_5s_norm, 0, 60)
    expected = merge_value_by_time(df_5s_norm)
    # chart.set_period(60) 锁定 1min，再 set 5s 数据 → 自动对齐聚合
    chart = Chart()
    chart.set_period(60)
    chart.set(df_5s)
    verify_agg(chart, expected, "5s→1min")
    all_clean &= log_check(chart.candle._last_bar['time'] == expected.iloc[-1]['time'],
                            "5s→1min last_bar time", errors, "5s_1min_last")
    chart.exit()

    # ── [2] 1min → 5min ──
    print("\n[2] 1min → 5min aggregation ...")
    t_5min = int(pd.Timestamp('2024-01-02').timestamp())
    times_1min = [t_5min + i * 60 for i in range(5)]
    rng = np.random.RandomState(102)
    prices = 200 + np.cumsum(rng.randn(5) * 1.0)
    highs = prices + rng.uniform(0.5, 2, 5)
    lows = prices - rng.uniform(0.5, 2, 5)
    df_1min = pd.DataFrame({
        'time': [pd.Timestamp(t, unit='s') for t in times_1min],
        'open': prices, 'high': highs, 'low': lows, 'close': prices,
        'volume': rng.randint(500, 2000, 5).astype(float),
    })
    df_1min_norm = normal_df(df_1min)
    df_1min_norm = time_to_bar_time(df_1min_norm, 0, 300)
    expected = merge_value_by_time(df_1min_norm)
    chart = Chart()
    chart.set_period(300)
    chart.set(df_1min)
    verify_agg(chart, expected, "1min→5min")
    all_clean &= log_check(chart.candle._last_bar['time'] == expected.iloc[-1]['time'],
                            "1min→5min last_bar time", errors, "1min_5min_last")
    chart.exit()

    # ── [3] 1h → daily ──
    print("\n[3] 1h → daily aggregation ...")
    chart = Chart()
    chart.set_period(86400)
    t_day = int(pd.Timestamp('2024-01-01').timestamp())
    # 8 条 1h bars（模拟交易时段 09:00-17:00）
    times_1h = [t_day + 3600 * 9 + i * 3600 for i in range(8)]
    rng = np.random.RandomState(103)
    prices = 500 + np.cumsum(rng.randn(8) * 3)
    highs = prices + rng.uniform(1, 5, 8)
    lows = prices - rng.uniform(1, 5, 8)
    df_1h = pd.DataFrame({
        'time': [pd.Timestamp(t, unit='s') for t in times_1h],
        'open': prices, 'high': highs, 'low': lows, 'close': prices,
        'volume': rng.randint(1000, 10000, 8).astype(float),
        'open_interest': rng.randint(20000, 80000, 8).astype(float),
    })
    chart.set(df_1h)
    df_1h_norm = normal_df(df_1h)
    df_1h_norm = time_to_bar_time(df_1h_norm, 0, 86400)
    expected = merge_value_by_time(df_1h_norm)
    verify_agg(chart, expected, "1h→daily")
    all_clean &= log_check(chart.candle._last_bar['open'] == expected.iloc[-1]['open'],
                            "1h→daily open", errors, "1h_day_open")
    all_clean &= log_check(chart.candle._last_bar['high'] == expected.iloc[-1]['high'],
                            "1h→daily high", errors, "1h_day_high")
    all_clean &= log_check(chart.candle._last_bar['low'] == expected.iloc[-1]['low'],
                            "1h→daily low", errors, "1h_day_low")
    all_clean &= log_check(chart.candle._last_bar['close'] == expected.iloc[-1]['close'],
                            "1h→daily close", errors, "1h_day_close")
    chart.exit()

    # ── [4] 多级链式聚合：1s → 1min → 5min → 1h ──
    print("\n[4] Multi-level chain: 1s → 1min → 5min → 1h ...")
    rng = np.random.RandomState(104)
    t_base = int(pd.Timestamp('2024-01-01 09:00:00').timestamp())
    n_seconds = 300  # 5 minutes of 1s data
    times = [t_base + i for i in range(n_seconds)]
    prices = 100 + np.cumsum(rng.randn(n_seconds) * 0.1)

    chain_intervals = [
        (60,    '1min'),
        (300,   '5min'),
        (3600,  '1h'),
    ]
    for intv_sec, label in chain_intervals:
        chart = Chart()
        chart.set_period(intv_sec)
        df_1s = pd.DataFrame({
            'time': [pd.Timestamp(t, unit='s') for t in times],
            'open': prices, 'high': prices + 0.5, 'low': prices - 0.5, 'close': prices,
            'volume': np.ones(n_seconds) * 100.0,
        })
        chart.set(df_1s)
        df_1s_norm = normal_df(df_1s)
        df_1s_norm = time_to_bar_time(df_1s_norm, 0, intv_sec)
        expected = merge_value_by_time(df_1s_norm)
        verify_agg(chart, expected, f"1s→{label} chain")
        chart.exit()

    # ── [5] 边界对齐校验 ──
    print("\n[5] Boundary alignment verification ...")
    for intv_sec, label in [(60, '1min'), (300, '5min'), (3600, '1h')]:
        chart = Chart()
        chart.set_period(intv_sec)
        base_t = int(pd.Timestamp('2024-01-01').timestamp())
        n_bars = 10
        times = [base_t + intv_sec * i for i in range(n_bars)]
        df = pd.DataFrame({
            'time': [pd.Timestamp(t, unit='s') for t in times],
            'open': 100 + np.arange(n_bars, dtype=float),
            'high': 101 + np.arange(n_bars, dtype=float),
            'low': 99 + np.arange(n_bars, dtype=float),
            'close': 100 + np.arange(n_bars, dtype=float),
        })
        chart.set(df)
        expected_times = [base_t + intv_sec * i for i in range(n_bars)]
        actual_times = chart.candle.data['time'].values.tolist()
        all_clean &= log_check(actual_times == expected_times,
                                f"{label} boundary alignment", errors, f"boundary_{label}")
        chart.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 9: 混沌测试
# ═══════════════════════════════════════════════════════

def make_random_ticks(n, start_ts, price_range=(90, 110), vol_range=(10, 500), seed=None):
    """生成随机 tick 数据。"""
    rng = np.random.RandomState(seed)
    times = sorted(start_ts + rng.randint(0, 1800, n))
    prices = price_range[0] + rng.random(n) * (price_range[1] - price_range[0])
    volumes = vol_range[0] + rng.random(n) * (vol_range[1] - vol_range[0])
    return pd.DataFrame({
        'time': [pd.Timestamp(t, unit='s') for t in times],
        'price': prices,
        'volume': volumes,
    })


def make_random_bars(n, start_ts, interval_sec, price_range=(90, 110), vol_range=(100, 5000), seed=None):
    """生成随机 bar 数据。"""
    rng = np.random.RandomState(seed)
    times = [start_ts + interval_sec * i for i in range(n)]
    base = price_range[0] + rng.random(n) * (price_range[1] - price_range[0])
    return pd.DataFrame({
        'time': [pd.Timestamp(t, unit='s') for t in times],
        'open': base + rng.randn(n) * 0.5,
        'high': base + rng.uniform(0.5, 2, n),
        'low': base - rng.uniform(0.5, 2, n),
        'close': base + rng.randn(n) * 0.5,
        'volume': vol_range[0] + rng.random(n) * (vol_range[1] - vol_range[0]),
    })


def verify_chaos(chart, expected, step, op_desc, errors):
    """混沌测试每步校验：chart.candle.data 与 expected 比较。"""
    if expected is None or expected.empty:
        return True
    cols = ['time', 'open', 'high', 'low', 'close']
    if len(chart.candle.data) != len(expected):
        errors.append(f"step {step}: rows {len(chart.candle.data)} != {len(expected)}")
        print(f"      [FAIL] step {step} ({op_desc}): rows {len(chart.candle.data)} != {len(expected)}")
        print(f"             actual times: {chart.candle.data['time'].values.tolist()}")
        print(f"             expected times: {expected['time'].values.tolist()}")
        return False
    for col in cols:
        if col not in chart.candle.data.columns or col not in expected.columns:
            continue
        if not np.allclose(chart.candle.data[col].values, expected[col].values, atol=1e-6, equal_nan=True):
            actual_vals = chart.candle.data[col].values
            expected_vals = expected[col].values
            diffs = np.abs(actual_vals - expected_vals)
            worst_idx = np.argmax(diffs)
            errors.append(f"step {step}: {col} mismatch (diff={diffs[worst_idx]:.8f})")
            print(f"      [FAIL] step {step} ({op_desc}): {col} mismatch")
            print(f"             worst at idx={worst_idx}: actual={actual_vals[worst_idx]:.8f} expected={expected_vals[worst_idx]:.8f} diff={diffs[worst_idx]:.8f}")
            print(f"             actual times: {chart.candle.data['time'].values.tolist()}")
            print(f"             expected times: {expected['time'].values.tolist()}")
            return False
    print(f"      [OK] step {step:3d} ({op_desc})")
    return True


def test_chaos_random_mixed():
    """混沌测试：100 步随机混合 ticks + bars + 不同时间级别，每步校验。"""
    sep = "=" * 60
    print(sep)
    print("  test_chaos_random_mixed (100 steps)")
    print(sep)

    chart = Chart()
    errors = []
    all_clean = True
    rng = np.random.RandomState(42)

    # 初始化：20 条 daily bars
    init_df = make_bar_data(20, 'D', 100, 42)
    chart.set(init_df)
    expected = chart.candle.data[['time', 'open', 'high', 'low', 'close']].copy()

    # 所有 update 操作都会追加到 init_df 之后
    last_ts = int(init_df.iloc[-1]['time'].timestamp())

    for step in range(1, 101):
        r = rng.random()
        if r < 0.4:
            # ── tick 更新 ──
            n_ticks = rng.randint(3, 40)
            start = last_ts + rng.randint(60, 3600)
            cumvol = rng.random() < 0.5
            ticks = make_random_ticks(n_ticks, start, seed=step)
            prev = chart.candle._last_bar.copy() if chart.candle._last_bar is not None else None
            chart.update_ticks(ticks)
            expected = compute_expected(expected, ticks, chart,
                                        is_ticks=True, cumulative_volume=cumvol,
                                        prev_last_bar=prev)
            all_clean &= verify_chaos(chart, expected, step,
                                      f"ticks(n={n_ticks},cum={cumvol})", errors)
        elif r < 0.8:
            # ── bar 更新（随机时间级别）──
            freq_sec = rng.choice([60, 300, 900, 3600])
            n_bars = rng.randint(2, 15)
            start = last_ts + rng.randint(60, 3600)
            bars = make_random_bars(n_bars, start, freq_sec, seed=step)
            chart.update_bars(bars)
            expected = compute_expected(expected, bars, chart)
            all_clean &= verify_chaos(chart, expected, step,
                                      f"bars(n={n_bars},freq={freq_sec}s)", errors)
        else:
            # ── 混合：先 ticks 后 bars ──
            n_ticks = rng.randint(3, 20)
            start_t = last_ts + rng.randint(60, 1800)
            ticks = make_random_ticks(n_ticks, start_t, seed=step)
            prev = chart.candle._last_bar.copy() if chart.candle._last_bar is not None else None
            chart.update_ticks(ticks)
            expected = compute_expected(expected, ticks, chart,
                                        is_ticks=True, cumulative_volume=False,
                                        prev_last_bar=prev)

            freq_sec = rng.choice([60, 300, 900])
            n_bars = rng.randint(2, 8)
            start_b = start_t + rng.randint(60, 600)
            bars = make_random_bars(n_bars, start_b, freq_sec, seed=step + 1000)
            chart.update_bars(bars)
            expected = compute_expected(expected, bars, chart)
            all_clean &= verify_chaos(chart, expected, step,
                                      f"mixed(ticks={n_ticks},bars={n_bars})", errors)

        # 更新 last_ts 追踪
        if expected is not None and not expected.empty:
            last_ts = int(expected.iloc[-1]['time'])

    chart.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


def test_chaos_multi_level_fusion():
    """混沌测试：不同时间级别 bar 融合到同一 chart，每步校验。"""
    sep = "=" * 60
    print(sep)
    print("  test_chaos_multi_level_fusion")
    print(sep)

    chart = Chart()
    errors = []
    all_clean = True
    rng = np.random.RandomState(77)

    # 初始化：5min bars
    t0 = int(pd.Timestamp('2024-01-02').timestamp())
    init_bars = make_random_bars(10, t0, 300, seed=77)
    chart.set(init_bars)
    expected = chart.candle.data[['time', 'open', 'high', 'low', 'close']].copy()

    # 序列：不同时间级别的操作
    ops = [
        ('bars',   300,   5,   '5min bars'),
        ('bars',   60,    8,   '1min bars'),
        ('bars',   3600,  3,   '1h bars'),
        ('ticks',  None,  30,  '30s ticks'),
        ('bars',   900,   4,   '15min bars'),
        ('ticks',  None,  20,  '20s ticks'),
        ('bars',   60,    10,  '1min bars #2'),
        ('bars',   3600,  2,   '1h bars #2'),
    ]

    last_ts = t0 + 300 * 9  # end of initial bars
    for i, (op_type, freq_sec, count, label) in enumerate(ops):
        start = last_ts + rng.randint(60, 600)
        if op_type == 'ticks':
            cumvol = rng.random() < 0.5
            ticks = make_random_ticks(count, start, seed=100 + i)
            prev = chart.candle._last_bar.copy() if chart.candle._last_bar is not None else None
            chart.update_ticks(ticks)
            expected = compute_expected(expected, ticks, chart,
                                        is_ticks=True, cumulative_volume=cumvol,
                                        prev_last_bar=prev)
        else:
            bars = make_random_bars(count, start, freq_sec, seed=200 + i)
            chart.update_bars(bars)
            expected = compute_expected(expected, bars, chart)
        all_clean &= verify_chaos(chart, expected, i + 1, label, errors)
        if expected is not None and not expected.empty:
            last_ts = int(expected.iloc[-1]['time'])

    chart.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


def test_chaos_last_bar_inheritance():
    """混沌测试：连续 ticks 落在同一 bar 窗口内，验证 replace-or-append 行为（open 取新 tick 的 first 值）。"""
    sep = "=" * 60
    print(sep)
    print("  test_chaos_last_bar_inheritance")
    print(sep)

    chart = Chart()
    errors = []
    all_clean = True
    rng = np.random.RandomState(55)

    # 初始化：1min bars
    t0 = int(pd.Timestamp('2024-01-03 09:00:00').timestamp())
    init_bars = make_random_bars(5, t0, 60, seed=55)
    chart.set(init_bars)
    expected = chart.candle.data[['time', 'open', 'high', 'low', 'close']].copy()

    # 连续 5 批 ticks，全部落在同一 5min 窗口内
    # 每批都会 replace-or-append 到同一时间窗口的 bar
    for batch in range(5):
        # ticks 落在 t0+300 到 t0+300+299 的 5min 窗口内
        ticks = make_random_ticks(
            rng.randint(5, 20),
            t0 + 300 + batch * 10,
            price_range=(95 + batch, 105 + batch),
            seed=500 + batch,
        )
        prev = chart.candle._last_bar.copy() if chart.candle._last_bar is not None else None
        chart.update_ticks(ticks)
        expected = compute_expected(expected, ticks, chart,
                                    is_ticks=True, cumulative_volume=False,
                                    prev_last_bar=prev)
        all_clean &= verify_chaos(chart, expected, batch + 1,
                                  f"inherit batch {batch}", errors)

    # 测试 cumulative_volume=True
    chart2 = Chart()
    chart2.set(init_bars)
    expected2 = chart2.candle.data[['time', 'open', 'high', 'low', 'close']].copy()

    for batch in range(5):
        ticks = make_random_ticks(
            rng.randint(5, 20),
            t0 + 300 + batch * 10,
            price_range=(95, 105),
            vol_range=(100, 500),
            seed=600 + batch,
        )
        prev2 = chart2.candle._last_bar.copy() if chart2.candle._last_bar is not None else None
        chart2.update_ticks(ticks)
        expected2 = compute_expected(expected2, ticks, chart2,
                                     is_ticks=True, cumulative_volume=True,
                                     prev_last_bar=prev2)
        all_clean &= verify_chaos(chart2, expected2, batch + 1,
                                  f"cum inherit batch {batch}", errors)

    chart.exit()
    chart2.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 10: 边界情况
# ═══════════════════════════════════════════════════════

def test_edge_cases():
    sep = "=" * 60
    print(sep)
    print("  test_edge_cases")
    print(sep)

    errors = []
    all_clean = True

    # ── [1] 空 DataFrame ──
    print("\n[1] Empty DataFrame handling ...")
    chart = Chart()
    df = make_bar_data(10, 'D', 100, 42)
    chart.set(df)
    n_before = len(chart.candle.data)
    chart.update_bars(pd.DataFrame())
    all_clean &= log_check(len(chart.candle.data) == n_before,
                            "update_bars(empty) no change", errors, "empty_update_bars")
    chart.update_ticks(pd.DataFrame())
    all_clean &= log_check(len(chart.candle.data) == n_before,
                            "update_from_ticks(empty) no change", errors, "empty_update_ticks")
    chart.exit()

    # ── [2] 单行数据 ──
    print("\n[2] Single row data ...")
    chart = Chart()
    # set() 需要 ≥2 行才能推断 interval，单行用 set_period + update_bar
    chart.set_period(86400)
    single = pd.Series({
        'time': pd.Timestamp('2024-01-01'),
        'open': 100.0, 'high': 105.0, 'low': 95.0, 'close': 102.0,
        'volume': 5000.0,
    })
    chart.update_bar(single)
    all_clean &= log_check(len(chart.candle.data) == 1,
                            "single row set", errors, "single_set")
    all_clean &= log_check(chart.candle.data.iloc[0]['open'] == 100.0,
                            "single row open", errors, "single_open")
    all_clean &= log_check(chart.candle.data.iloc[0]['high'] == 105.0,
                            "single row high", errors, "single_high")
    all_clean &= log_check(chart.candle.data.iloc[0]['close'] == 102.0,
                            "single row close", errors, "single_close")
    # 追加单行
    single2 = pd.Series({
        'time': pd.Timestamp('2024-01-02'),
        'open': 102.0, 'high': 108.0, 'low': 100.0, 'close': 106.0,
        'volume': 6000.0,
    })
    chart.update_bar(single2)
    all_clean &= log_check(len(chart.candle.data) == 2,
                            "single row append", errors, "single_append")
    all_clean &= log_check(chart.candle.data.iloc[1]['close'] == 106.0,
                            "appended row close", errors, "single_append_close")
    chart.exit()

    # ── [3] 乱序 tick 数据 ──
    print("\n[3] Out-of-order tick data ...")
    chart = Chart()
    t0 = int(pd.Timestamp('2024-01-01').timestamp())
    chart.set(make_bar_data(5, 'D', 100, 42))
    # 乱序 ticks（时间不单调）
    tick_times = [t0 + 86400 + s for s in [30, 10, 50, 5, 25, 40]]
    tick_prices = [100, 101, 99, 102, 98, 103]
    ticks = pd.DataFrame({
        'time': [pd.Timestamp(t, unit='s') for t in tick_times],
        'price': tick_prices,
    })
    chart.update_ticks(ticks)
    # groupby 不依赖顺序，结果应与排序后一致
    sorted_ticks = ticks.sort_values('time').reset_index(drop=True)
    chart2 = Chart()
    chart2.set(make_bar_data(5, 'D', 100, 42))
    chart2.update_ticks(sorted_ticks)
    all_clean &= log_check(
        np.allclose(chart.candle.data.values, chart2.candle.data.values, atol=1e-6),
        "out-of-order ticks same result", errors, "ooo_ticks")
    chart.exit()
    chart2.exit()

    # ── [4] 重复时间戳 bar ──
    print("\n[4] Duplicate timestamp bars ...")
    chart = Chart()
    t = pd.Timestamp('2024-01-01')
    chart.set(pd.DataFrame({
        'time': [t, t + pd.Timedelta(days=1)],
        'open': [100.0, 102.0], 'high': [105.0, 108.0],
        'low': [95.0, 100.0], 'close': [102.0, 105.0],
        'volume': [1000.0, 2000.0],
    }))
    dup_bars = pd.DataFrame({
        'time': [t + pd.Timedelta(days=2)] * 3,
        'open': [102.0, 103.0, 101.0],
        'high': [108.0, 110.0, 107.0],
        'low': [100.0, 101.0, 99.0],
        'close': [105.0, 107.0, 109.0],
        'volume': [2000.0, 3000.0, 4000.0],
    })
    chart.update_bars(dup_bars)
    # 应该合并为 1 条（同一时间），open=first, high=max, low=min, close=last
    all_clean &= log_check(len(chart.candle.data) == 3,
                            "dup bars merged to 1 (+ initial 2)", errors, "dup_count")
    merged_bar = chart.candle.data.iloc[-1]
    all_clean &= log_check(merged_bar['open'] == 102.0, "dup open=first=102", errors, "dup_open")
    all_clean &= log_check(merged_bar['high'] == 110.0, "dup high=max=110", errors, "dup_high")
    all_clean &= log_check(merged_bar['low'] == 99.0, "dup low=min=99", errors, "dup_low")
    all_clean &= log_check(merged_bar['close'] == 109.0, "dup close=last=109", errors, "dup_close")
    chart.exit()

    # ── [5] set() 后再 set() 覆盖 ──
    print("\n[5] set() overwrite ...")
    chart = Chart()
    df1 = make_bar_data(10, 'D', 100, 42)
    chart.set(df1)
    n1 = len(chart.candle.data)
    df2 = make_bar_data(20, 'D', 200, 99)
    chart.set(df2)
    all_clean &= log_check(len(chart.candle.data) == 20,
                            f"overwrite: {n1}→{len(chart.candle.data)}", errors, "overwrite_count")
    all_clean &= log_check(chart.candle.data.iloc[0]['open'] != df1.iloc[0]['open'],
                            "overwrite: data changed", errors, "overwrite_data")
    chart.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试: filter_old_bars 纯函数
# ═══════════════════════════════════════════════════════

def test_filter_old_bars():
    sep = "=" * 60
    print(sep)
    print("  test_filter_old_bars")
    print(sep)

    errors = []
    all_clean = True

    df = pd.DataFrame({
        'time': [100, 200, 300, 400, 500],
        'value': [10, 20, 30, 40, 50],
    })

    # ── [1] last_bar_time=None → 不过滤 ──
    print("\n[1] last_bar_time=None → no filter ...")
    result = filter_old_bars(df, last_bar_time=None)
    all_clean &= log_check(len(result) == 5, f"rows={len(result)}==5", errors, "none")

    # ── [2] last_bar_time=300 → 保留 >=300 ──
    print("\n[2] last_bar_time=300 → keep >=300 ...")
    result = filter_old_bars(df, last_bar_time=300)
    all_clean &= log_check(len(result) == 3, f"rows={len(result)}==3", errors, "filter_count")
    all_clean &= log_check(result.iloc[0]['time'] == 300, f"first={result.iloc[0]['time']}==300", errors, "filter_first")

    # ── [3] last_bar_time=0 → 全部保留 ──
    print("\n[3] last_bar_time=0 → keep all ...")
    result = filter_old_bars(df, last_bar_time=0)
    all_clean &= log_check(len(result) == 5, f"rows={len(result)}==5", errors, "zero")

    # ── [4] last_bar_time=999 → 全部丢弃 ──
    print("\n[4] last_bar_time=999 → drop all ...")
    result = filter_old_bars(df, last_bar_time=999)
    all_clean &= log_check(len(result) == 0, f"rows={len(result)}==0", errors, "drop_all")

    # ── [5] 单调递增检查 ──
    print("\n[5] Non-monotonic → ValueError ...")
    df_bad = pd.DataFrame({'time': [300, 100, 200], 'value': [1, 2, 3]})
    try:
        filter_old_bars(df_bad)
        all_clean &= log_check(False, "should raise ValueError", errors, "mono")
    except ValueError:
        all_clean &= log_check(True, "raised ValueError", errors, "mono")

    # ── [6] 空 DataFrame ──
    print("\n[6] Empty DataFrame → no error ...")
    result = filter_old_bars(pd.DataFrame(), last_bar_time=100)
    all_clean &= log_check(len(result) == 0, f"rows={len(result)}==0", errors, "empty")

    # ── [7] last_bar_time 正好等于某行时间 → 该行保留 ──
    print("\n[7] Exact match → keep ...")
    result = filter_old_bars(df, last_bar_time=200)
    all_clean &= log_check(len(result) == 4, f"rows={len(result)}==4", errors, "exact_match")
    all_clean &= log_check(result.iloc[0]['time'] == 200, f"first={result.iloc[0]['time']}==200", errors, "exact_first")

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试: merge_volume_by_time 纯函数
# ═══════════════════════════════════════════════════════

def test_merge_volume_by_time():
    from lightweight_charts.util import merge_volume_by_time

    sep = "=" * 60
    print(sep)
    print("  test_merge_volume_by_time")
    print(sep)

    errors = []
    all_clean = True

    # ── [1] Bar 模式：基本合并 ──
    print("\n[1] Bar mode: basic merge ...")
    df_bar = pd.DataFrame({
        'time':  [1, 1, 2, 2, 2],
        'value': [100, 200, 50, 30, 70],
        'open':  [10.0, 10.5, 11.0, 11.2, 11.1],
        'close': [10.5, 10.8, 11.2, 11.3, 11.4],
    })
    result = merge_volume_by_time(df_bar, is_tick=False)
    all_clean &= log_check(list(result.columns) == ['time', 'value', 'open', 'close'],
                            f"columns={list(result.columns)}", errors, "bar_cols")
    all_clean &= log_check(len(result) == 2, f"rows={len(result)}==2", errors, "bar_rows")

    row1 = result[result['time'] == 1].iloc[0]
    all_clean &= log_check(row1['value'] == 200, f"t1 value=last={row1['value']}", errors, "bar_t1_vol")
    all_clean &= log_check(row1['open'] == 10.0, f"t1 open=first=10.0, got={row1['open']}", errors, "bar_t1_open")
    all_clean &= log_check(row1['close'] == 10.8, f"t1 close=last=10.8, got={row1['close']}", errors, "bar_t1_close")

    row2 = result[result['time'] == 2].iloc[0]
    all_clean &= log_check(row2['value'] == 70, f"t2 value=last={row2['value']}", errors, "bar_t2_vol")
    all_clean &= log_check(row2['open'] == 11.0, f"t2 open=first=11.0, got={row2['open']}", errors, "bar_t2_open")
    all_clean &= log_check(row2['close'] == 11.4, f"t2 close=last=11.4, got={row2['close']}", errors, "bar_t2_close")

    # ── [2] Bar 模式：单行（无合并） ──
    print("\n[2] Bar mode: single row ...")
    df_single = pd.DataFrame({
        'time': [1], 'value': [500], 'open': [20.0], 'close': [21.0],
    })
    result = merge_volume_by_time(df_single, is_tick=False)
    all_clean &= log_check(len(result) == 1, f"rows={len(result)}==1", errors, "bar_single_rows")
    all_clean &= log_check(result.iloc[0]['value'] == 500, f"value=500", errors, "bar_single_vol")

    # ── [3] Tick 模式：基本合并 ──
    print("\n[3] Tick mode: basic merge ...")
    df_tick = pd.DataFrame({
        'time':  [1, 1, 1, 2, 2],
        'value': [100, 200, 150, 80, 120],
        'price': [10.0, 10.5, 10.2, 11.0, 11.3],
    })
    result = merge_volume_by_time(df_tick, is_tick=True)
    all_clean &= log_check(list(result.columns) == ['time', 'value', 'open', 'close'],
                            f"columns={list(result.columns)}", errors, "tick_cols")
    all_clean &= log_check(len(result) == 2, f"rows={len(result)}==2", errors, "tick_rows")

    row1 = result[result['time'] == 1].iloc[0]
    all_clean &= log_check(row1['value'] == 450, f"t1 value=100+200+150={row1['value']}", errors, "tick_t1_vol")
    all_clean &= log_check(row1['open'] == 10.0, f"t1 open=first(price)=10.0, got={row1['open']}", errors, "tick_t1_open")
    all_clean &= log_check(row1['close'] == 10.2, f"t1 close=last(price)=10.2, got={row1['close']}", errors, "tick_t1_close")

    row2 = result[result['time'] == 2].iloc[0]
    all_clean &= log_check(row2['value'] == 200, f"t2 value=80+120={row2['value']}", errors, "tick_t2_vol")
    all_clean &= log_check(row2['open'] == 11.0, f"t2 open=first(price)=11.0, got={row2['open']}", errors, "tick_t2_open")
    all_clean &= log_check(row2['close'] == 11.3, f"t2 close=last(price)=11.3, got={row2['close']}", errors, "tick_t2_close")

    # ── [4] Tick 模式：单条 tick（open == close） ──
    print("\n[4] Tick mode: single tick per time ...")
    df_single_tick = pd.DataFrame({
        'time': [1, 2, 3],
        'value': [50, 60, 70],
        'price': [10.0, 11.0, 12.0],
    })
    result = merge_volume_by_time(df_single_tick, is_tick=True)
    all_clean &= log_check(len(result) == 3, f"rows={len(result)}==3", errors, "tick_single_rows")
    for i, (_, row) in enumerate(result.iterrows()):
        all_clean &= log_check(row['open'] == row['close'],
                                f"t{i+1} open==close=={row['open']}", errors, f"tick_single_{i}")

    # ── [5] Bar 模式：缺列报错 ──
    print("\n[5] Bar mode: missing columns → ValueError ...")
    try:
        merge_volume_by_time(pd.DataFrame({'time': [1], 'value': [100]}), is_tick=False)
        all_clean &= log_check(False, "should raise ValueError", errors, "bar_missing")
    except ValueError as e:
        all_clean &= log_check(True, f"raised ValueError: {e}", errors, "bar_missing")

    # ── [6] Tick 模式：缺列报错 ──
    print("\n[6] Tick mode: missing columns → ValueError ...")
    try:
        merge_volume_by_time(pd.DataFrame({'time': [1], 'value': [100]}), is_tick=True)
        all_clean &= log_check(False, "should raise ValueError", errors, "tick_missing")
    except ValueError as e:
        all_clean &= log_check(True, f"raised ValueError: {e}", errors, "tick_missing")

    # ── [7] 数据完整性：无 NaN ──
    print("\n[7] No NaN in output ...")
    df_vol = pd.DataFrame({
        'time': [1, 1, 2, 2, 2],
        'value': [10, 20, 30, 40, 50],
        'open': [1.0, 2.0, 3.0, 4.0, 5.0],
        'close': [1.5, 2.5, 3.5, 4.5, 5.5],
    })
    result = merge_volume_by_time(df_vol)
    all_clean &= log_check(not result.isnull().any().any(), "no NaN in bar result", errors, "bar_nan")

    df_tick_nan = pd.DataFrame({
        'time': [1, 1, 2],
        'value': [10, 20, 30],
        'price': [1.0, 2.0, 3.0],
    })
    result = merge_volume_by_time(df_tick_nan, is_tick=True)
    all_clean &= log_check(not result.isnull().any().any(), "no NaN in tick result", errors, "tick_nan")

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════

if __name__ == '__main__':
    # start_time = time.time()

    results = []
    results.append(('set_different_frequencies', test_set_different_frequencies()))
    results.append(('update_bar', test_update_bar()))
    results.append(('update_bars', test_update_bars()))
    results.append(('update_ticks', test_update_ticks()))
    results.append(('duplicate_time_merge', test_duplicate_time_merge()))
    results.append(('last_bar_filter', test_last_bar_filter()))
    results.append(('line_value_column', test_line_value_column()))
    results.append(('util_functions', test_util_functions()))
    results.append(('cross_level_aggregation', test_cross_level_aggregation()))
    results.append(('chaos_random_mixed', test_chaos_random_mixed()))
    results.append(('chaos_multi_level_fusion', test_chaos_multi_level_fusion()))
    results.append(('chaos_last_bar_inheritance', test_chaos_last_bar_inheritance()))
    results.append(('edge_cases', test_edge_cases()))
    results.append(('filter_old_bars', test_filter_old_bars()))
    results.append(('merge_volume_by_time', test_merge_volume_by_time()))

    print()
    print("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"  {passed}/{total} tests passed")
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"    [{status}] {name}")
    print("=" * 60)

    # print(f"  Total time: {time.time() - start_time:.2f} seconds")
