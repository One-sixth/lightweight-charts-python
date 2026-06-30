"""
VolumeSeries 数据聚合独立测试。

验证 VolumeSeries 的 set/update_bars/update_ticks 在各种场景下的行为。
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from lightweight_charts import Chart


def log_check(ok, label, errors, err_key=None):
    if ok:
        print(f"      [OK] {label}")
    else:
        print(f"      [FAIL] {label}")
        if err_key:
            errors.append(err_key)
    return ok


# ═══════════════════════════════════════════════════════
#  测试 1: bar 模式 set — 基本功能
# ═══════════════════════════════════════════════════════

def test_bar_set():
    sep = "=" * 60
    print(sep)
    print("  test_bar_set")
    print(sep)

    errors = []
    all_clean = True

    chart = Chart()
    vol = chart.volume

    # ── [1] 基本 set ──
    print("\n[1] Basic set ...")
    df = pd.DataFrame({
        'time':  [1, 2, 3, 4, 5],
        'value': [100, 200, 150, 300, 250],
        'open':  [10.0, 11.0, 10.5, 12.0, 11.5],
        'close': [10.5, 10.8, 11.0, 11.8, 12.0],
    })
    vol.set(df)

    all_clean &= log_check(len(vol.data) == 5, f"rows={len(vol.data)}==5", errors, "set_count")
    all_clean &= log_check(vol.data.iloc[0]['value'] == 100, f"t1 value=100", errors, "set_t1_val")
    all_clean &= log_check(vol.data.iloc[0]['open'] == 10.0, f"t1 open=10.0", errors, "set_t1_open")
    all_clean &= log_check(vol.data.iloc[0]['close'] == 10.5, f"t1 close=10.5", errors, "set_t1_close")

    # ── [2] set 覆盖旧数据 ──
    print("\n[2] set() overwrites old data ...")
    df2 = pd.DataFrame({
        'time':  [10, 11, 12],
        'value': [50, 60, 70],
        'open':  [20.0, 21.0, 22.0],
        'close': [20.5, 21.5, 22.5],
    })
    vol.set(df2)
    all_clean &= log_check(len(vol.data) == 3, f"rows={len(vol.data)}==3", errors, "overwrite_count")
    all_clean &= log_check(vol.data.iloc[0]['value'] == 50, f"t10 value=50", errors, "overwrite_t10")

    chart.exit()
    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 2: bar 模式 update_bars — 追加 + 重复时间合并
# ═══════════════════════════════════════════════════════

def test_bar_update_bars():
    sep = "=" * 60
    print(sep)
    print("  test_bar_update_bars")
    print(sep)

    errors = []
    all_clean = True

    chart = Chart()
    vol = chart.volume

    # 初始数据
    df = pd.DataFrame({
        'time':  [1, 2, 3],
        'value': [100, 200, 150],
        'open':  [10.0, 11.0, 10.5],
        'close': [10.5, 10.8, 11.0],
    })
    vol.set(df)

    # ── [1] 追加新 bar ──
    print("\n[1] Append new bars ...")
    new_bars = pd.DataFrame({
        'time':  [4, 5],
        'value': [300, 250],
        'open':  [12.0, 11.5],
        'close': [11.8, 12.0],
    })
    vol.update_bars(new_bars)
    all_clean &= log_check(len(vol.data) == 5, f"rows={len(vol.data)}==5", errors, "append_count")
    all_clean &= log_check(vol.data.iloc[-1]['value'] == 250, f"t5 value=250", errors, "append_t5")

    # ── [2] 重复时间 bar — last 模式取最后一条 ──
    print("\n[2] Duplicate time bars → last value wins ...")
    dup_bars = pd.DataFrame({
        'time':  [5, 6],
        'value': [999, 400],    # t5 重复，value=999 应该覆盖旧的 250
        'open':  [99.0, 13.0],
        'close': [99.5, 13.5],
    })
    vol.update_bars(dup_bars)
    all_clean &= log_check(len(vol.data) == 6, f"rows={len(vol.data)}==6 (t5 覆盖 + t6 追加)", errors, "dup_count")

    t5_row = vol.data[vol.data['time'] == 5].iloc[0]
    all_clean &= log_check(t5_row['value'] == 999, f"t5 value=999 (last wins)", errors, "dup_t5_val")
    all_clean &= log_check(t5_row['open'] == 99.0, f"t5 open=99.0", errors, "dup_t5_open")

    # ── [3] 旧数据被过滤 ──
    print("\n[3] Old data filtered by _last_bar ...")
    old_bars = pd.DataFrame({
        'time':  [2, 7],  # t2 是旧数据，应该被过滤
        'value': [888, 500],
        'open':  [8.0, 14.0],
        'close': [8.5, 14.5],
    })
    vol.update_bars(old_bars)
    all_clean &= log_check(len(vol.data) == 7, f"rows={len(vol.data)}==7 (t2 filtered, t7 appended)", errors, "filter_count")

    chart.exit()
    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 3: tick 模式 update_ticks — 基本聚合
# ═══════════════════════════════════════════════════════

def test_tick_basic():
    sep = "=" * 60
    print(sep)
    print("  test_tick_basic")
    print(sep)

    errors = []
    all_clean = True

    chart = Chart()
    vol = chart.volume

    # 先 set 一些初始数据，让 _last_bar 有值
    df_init = pd.DataFrame({
        'time':  [100, 200, 300],
        'value': [10, 20, 30],
        'open':  [1.0, 2.0, 3.0],
        'close': [1.5, 2.5, 3.5],
    })
    vol.set(df_init)

    # ── [1] 基本 tick 聚合（tick 落在新时间 → 追加） ──
    print("\n[1] Basic tick aggregation → append new bars ...")
    ticks = pd.DataFrame({
        'time':  [400, 400, 400, 500, 500],
        'value': [100, 200, 150, 80, 120],
        'price': [10.0, 10.5, 10.2, 11.0, 11.3],
    })
    vol.update_ticks(ticks)

    # t400: volume=100+200+150=450, open=10.0(first price), close=10.2(last price)
    # t500: volume=80+120=200, open=11.0(first price), close=11.3(last price)
    all_clean &= log_check(len(vol.data) == 5, f"rows={len(vol.data)}==5 (3 init + 2 tick groups)", errors, "tick_count")

    t400 = vol.data[vol.data['time'] == 400].iloc[0]
    all_clean &= log_check(t400['value'] == 450, f"t400 value=100+200+150={t400['value']}", errors, "tick_t400_vol")
    all_clean &= log_check(t400['open'] == 10.0, f"t400 open=first(price)=10.0, got={t400['open']}", errors, "tick_t400_open")
    all_clean &= log_check(t400['close'] == 10.2, f"t400 close=last(price)=10.2, got={t400['close']}", errors, "tick_t400_close")

    t500 = vol.data[vol.data['time'] == 500].iloc[0]
    all_clean &= log_check(t500['value'] == 200, f"t500 value=80+120={t500['value']}", errors, "tick_t500_vol")
    all_clean &= log_check(t500['open'] == 11.0, f"t500 open=11.0, got={t500['open']}", errors, "tick_t500_open")
    all_clean &= log_check(t500['close'] == 11.3, f"t500 close=11.3, got={t500['close']}", errors, "tick_t500_close")

    chart.exit()
    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 4: tick 模式 — 累加 volume（_cumulative_volume）
# ═══════════════════════════════════════════════════════

def test_tick_cumulative():
    sep = "=" * 60
    print(sep)
    print("  test_tick_cumulative")
    print(sep)

    errors = []
    all_clean = True

    chart = Chart()
    vol = chart.volume

    # 初始数据：last bar = t=200
    df_init = pd.DataFrame({
        'time':  [100, 200],
        'value': [50, 60],
        'open':  [1.0, 2.0],
        'close': [1.5, 2.5],
    })
    vol.set(df_init)

    # ── [1] tick 落在最后一条 bar (t=200) 上 → volume 累加 ──
    print("\n[1] Tick on last bar → cumulative volume ...")
    ticks = pd.DataFrame({
        'time':  [200, 200],
        'value': [30, 20],     # merge: 30+20=50, cumulative: 60+50=110
        'price': [2.2, 2.3],
    })
    vol.update_ticks(ticks)

    t200 = vol.data[vol.data['time'] == 200].iloc[0]
    all_clean &= log_check(t200['value'] == 110, f"t200 value=60+(30+20)={t200['value']}", errors, "cum_t200_vol")
    all_clean &= log_check(len(vol.data) == 2, f"rows={len(vol.data)}==2", errors, "cum_count")

    # ── [2] tick 落在新时间 (t=300) → 追加 ──
    print("\n[2] Tick on new time → append ...")
    ticks2 = pd.DataFrame({
        'time':  [300, 300],
        'value': [40, 60],
        'price': [3.0, 3.5],
    })
    vol.update_ticks(ticks2)
    all_clean &= log_check(len(vol.data) == 3, f"rows={len(vol.data)}==3", errors, "append_count")

    # ── [3] tick 落在非最后 bar (t=100) → 被 filter_old_bars 丢弃 ──
    print("\n[3] Tick on non-last bar → filtered out ...")
    ticks3 = pd.DataFrame({
        'time':  [100, 100],
        'value': [10, 20],
        'price': [1.0, 1.1],
    })
    vol.update_ticks(ticks3)
    all_clean &= log_check(len(vol.data) == 3, f"rows={len(vol.data)}==3 (unchanged)", errors, "filter_count")
    # t100 的 value 不应变化
    t100_val = vol.data[vol.data['time'] == 100].iloc[0]['value']
    all_clean &= log_check(t100_val == 50, f"t100 value still=50 (not updated)", errors, "filter_val")

    chart.exit()
    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 5: 涨跌着色验证
# ═══════════════════════════════════════════════════════

def test_color():
    sep = "=" * 60
    print(sep)
    print("  test_color")
    print(sep)

    errors = []
    all_clean = True

    chart = Chart()
    vol = chart.volume

    df = pd.DataFrame({
        'time':  [1, 2, 3],
        'value': [100, 200, 300],
        'open':  [10.0, 11.0, 12.0],
        'close': [10.5, 10.8, 13.0],  # t1 涨, t2 跌, t3 涨
    })
    vol.set(df)

    # ── [1] data 中 open/close 正确保存 ──
    print("\n[1] open/close preserved in data ...")
    all_clean &= log_check(vol.data.iloc[0]['open'] == 10.0, f"t1 open=10.0", errors, "color_t1_open")
    all_clean &= log_check(vol.data.iloc[0]['close'] == 10.5, f"t1 close=10.5", errors, "color_t1_close")
    all_clean &= log_check(vol.data.iloc[1]['open'] == 11.0, f"t2 open=11.0", errors, "color_t2_open")
    all_clean &= log_check(vol.data.iloc[1]['close'] == 10.8, f"t2 close=10.8 (down)", errors, "color_t2_close")

    # ── [2] tick 模式的 open/close 从 price 生成 ──
    print("\n[2] Tick mode: open/close from price ...")
    chart2 = Chart()
    vol2 = chart2.volume
    vol2.set(pd.DataFrame({
        'time': [100], 'value': [10], 'open': [1.0], 'close': [1.5],
    }))

    ticks = pd.DataFrame({
        'time':  [200, 200, 200],
        'value': [10, 20, 30],
        'price': [5.0, 4.5, 4.0],  # 价格下降 → close < open → 跌
    })
    vol2.update_ticks(ticks)

    t200 = vol2.data[vol2.data['time'] == 200].iloc[0]
    all_clean &= log_check(t200['open'] == 5.0, f"t200 open=first(price)=5.0", errors, "tick_color_open")
    all_clean &= log_check(t200['close'] == 4.0, f"t200 close=last(price)=4.0", errors, "tick_color_close")

    chart.exit()
    chart2.exit()
    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  测试 6: 缺列报错
# ═══════════════════════════════════════════════════════

def test_missing_columns():
    sep = "=" * 60
    print(sep)
    print("  test_missing_columns")
    print(sep)

    errors = []
    all_clean = True

    chart = Chart()
    vol = chart.volume

    # ── [1] bar 模式缺 open/close ──
    print("\n[1] bar mode: missing open/close → ValueError ...")
    try:
        vol.set(pd.DataFrame({'time': [1], 'value': [100]}))
        all_clean &= log_check(False, "should raise ValueError", errors, "bar_missing")
    except ValueError as e:
        all_clean &= log_check(True, f"raised ValueError: {e}", errors, "bar_missing")

    # ── [2] tick 模式缺 price ──
    print("\n[2] tick mode: missing price → ValueError ...")
    vol2 = chart.volume
    try:
        vol2.update_ticks(pd.DataFrame({'time': [1], 'value': [100]}))
        all_clean &= log_check(False, "should raise ValueError", errors, "tick_missing")
    except ValueError as e:
        all_clean &= log_check(True, f"raised ValueError: {e}", errors, "tick_missing")

    chart.exit()
    print()
    print(f"  RESULT: {'PASS' if all_clean else 'FAIL ({0} errors)'.format(len(errors))}")
    return all_clean


# ═══════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════

if __name__ == '__main__':
    results = []
    results.append(('bar_set', test_bar_set()))
    results.append(('bar_update_bars', test_bar_update_bars()))
    results.append(('tick_basic', test_tick_basic()))
    results.append(('tick_cumulative', test_tick_cumulative()))
    results.append(('color', test_color()))
    results.append(('missing_columns', test_missing_columns()))

    print()
    print("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"  {passed}/{total} tests passed")
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"    [{status}] {name}")
    print("=" * 60)
