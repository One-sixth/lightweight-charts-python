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

Usage:
    python test/test_data_aggregation.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.dirname(__file__))

import time
import pandas as pd
import numpy as np
from lightweight_charts import Chart
from lightweight_charts.util import merge_value_by_time, normal_df


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
    all_clean &= verify_set(chart, df, "daily", errors)
    all_clean &= log_check(len(line_sma.data) == 30, f"daily SMA rows={len(line_sma.data)}", errors, "daily_sma")
    all_clean &= log_check(len(line_rsi.data) == 30, f"daily RSI rows={len(line_rsi.data)}", errors, "daily_rsi")

    # 1b. 5 分钟线
    print("\n[1b] set() 5min bars ...")
    df = make_bar_data(50, '5min', 200, 55)
    chart.set(df)
    all_clean &= verify_set(chart, df, "5min", errors)

    # 1c. 1 分钟线
    print("\n[1c] set() 1min bars ...")
    df = make_bar_data(60, 'min', 150, 77)
    chart.set(df)
    all_clean &= verify_set(chart, df, "1min", errors)

    # 1d. 1 小时线
    print("\n[1d] set() 1h bars ...")
    df = make_bar_data(40, 'h', 300, 88)
    chart.set(df)
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
    initial_rows = len(chart.data)

    # 批量追加
    print("\n[1] update_bars() batch append ...")
    batch = make_bar_data(10, 'D', 100, 99)
    batch['time'] = pd.date_range('2024-01-21', periods=10, freq='D')
    chart.update_bars(batch)
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

    # 批量部分重叠（首条与已有最后一条相同时间 → 更新已有，不新增行）
    print("\n[2] update_bars() batch with overlap ...")
    overlap = batch.iloc[:3].copy()
    overlap['time'] = chart.data.iloc[-1]['time']  # 全部 3 条都是同一时间
    chart.update_bars(overlap)
    # 全部 3 条时间 == _last_bar 时间 → 都是更新已有 bar，不新增行
    expected = initial_rows + 10
    all_clean &= log_check(len(chart.data) == expected, f"rows={len(chart.data)} == {expected} (overlap updates, no new rows)", errors, "overlap_rows")
    # 值校验：3 条同时间 bar 经 merge_value_by_time 合并
    # OHLC: open=第一条, high=max, low=min, close=最后一条
    last_chart = chart.data.iloc[-1]
    all_clean &= log_check(
        last_chart['open'] == overlap.iloc[0]['open'] and last_chart['high'] == overlap['high'].max()
        and last_chart['low'] == overlap['low'].min() and last_chart['close'] == overlap.iloc[-1]['close'],
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

def test_update_from_ticks():
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
    chart.update_from_ticks(ticks)

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
    expected_vol = grouped['volume'].last()
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
    chart.update_from_ticks(ticks2, cumulative_volume=True)
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
#  测试 7: Line/Histogram 名字大小写保留
# ═══════════════════════════════════════════════════════

def test_line_name_case_preserved():
    sep = "=" * 60
    print(sep)
    print("  test_line_name_case_preserved")
    print(sep)

    chart = Chart(width=800, height=600)
    chart.show(block=False)
    errors = []
    all_clean = True

    # 创建大小写混合名字的 Line
    line_upper = chart.create_line(name='MySMA', color='yellow', width=2)
    line_lower = chart.create_line(name='rsi', color='cyan', width=1)

    df = make_bar_data(20, 'D', 100, 42)
    df['MySMA'] = df['close'].rolling(5, min_periods=1).mean()
    df['rsi'] = 50 + np.random.RandomState(42).randn(20) * 10

    print("\n[1] set() with mixed-case line names ...")
    chart.set(df)

    all_clean &= log_check(
        len(line_upper.data) == 20,
        f"MySMA rows={len(line_upper.data)}",
        errors, "case_upper"
    )
    all_clean &= log_check(
        len(line_lower.data) == 20,
        f"rsi rows={len(line_lower.data)}",
        errors, "case_lower"
    )

    # 验证数据值正确（不被小写化后丢失）
    print("\n[2] Verify data values match ...")
    all_clean &= log_check(
        abs(line_upper.data.iloc[-1]['value'] - df['MySMA'].iloc[-1]) < 0.01,
        f"MySMA last value matches",
        errors, "case_upper_val"
    )

    chart.exit()

    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════

if __name__ == '__main__':
    start_time = time.time()

    results = []
    results.append(('set_different_frequencies', test_set_different_frequencies()))
    results.append(('update_bar', test_update_bar()))
    results.append(('update_bars', test_update_bars()))
    results.append(('update_from_ticks', test_update_from_ticks()))
    results.append(('duplicate_time_merge', test_duplicate_time_merge()))
    results.append(('last_bar_filter', test_last_bar_filter()))
    results.append(('line_name_case_preserved', test_line_name_case_preserved()))

    print()
    print("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"  {passed}/{total} tests passed")
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"    [{status}] {name}")
    print("=" * 60)

    print(f"  Total time: {time.time() - start_time:.2f} seconds")
