"""
Example 26: Series Batch Update
Demonstrates update_bars() and update_from_ticks() for Line and Histogram series,
with TopBar status and marker annotations.

This example shows:
1. How to append multiple data points to a Line series in one go
2. How to append multiple data points to a Histogram series in one go
3. Alternating between update_bars() and update_from_ticks() across batches
4. Performance comparison: N individual update() calls vs 1 update_bars() call
"""
import pandas as pd
import numpy as np
from time import perf_counter, sleep
from lightweight_charts import Chart


def generate_ohlcv(num_bars: int, seed: int = None) -> pd.DataFrame:
    """Generate random OHLCV data with a clear trend."""
    if seed is not None:
        np.random.seed(seed)
    times = pd.date_range('2020-01-01', periods=num_bars, freq='D')
    prices = 100.0 + np.cumsum(np.random.randn(num_bars) * 0.8)

    data = []
    for i, t in enumerate(times):
        base = prices[i]
        data.append({
            'time': t,
            'open': base + np.random.randn() * 0.2,
            'high': base + abs(np.random.randn()) * 0.6 + 0.2,
            'low': base - abs(np.random.randn()) * 0.6 - 0.2,
            'close': base + np.random.randn() * 0.2,
            'volume': int(np.random.exponential(1_000_000)),
        })
    return pd.DataFrame(data)


def df_to_ticks(df: pd.DataFrame) -> pd.DataFrame:
    """Convert a line/histogram DataFrame (time, value) to tick format (time, value, volume)."""
    result = df.copy()
    result['volume'] = 0
    return result[['time', 'value', 'volume']]


def calc_sma(df: pd.DataFrame, period: int) -> pd.DataFrame:
    sma = df['close'].rolling(window=period).mean()
    return pd.DataFrame({'time': df['time'], 'value': sma}).dropna()


def calc_ema(df: pd.DataFrame, period: int) -> pd.DataFrame:
    ema = df['close'].ewm(span=period, adjust=False).mean()
    return pd.DataFrame({'time': df['time'], 'value': ema}).dropna()


def calc_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return pd.DataFrame({'time': df['time'], 'value': rsi}).dropna()


if __name__ == '__main__':
    chart = Chart(
        title='Series Batch Update — Line & Histogram',
        width=1100,
        height=700,
    )
    chart.legend(visible=True)

    # Create topbar status textbox
    chart.topbar.textbox('status', '⏳ 正在初始化...', 'left')
    status = chart.topbar['status']

    chart.show()

    # ── Generate all 200 bars, show first 160, keep 40 for batch updates ──
    np.random.seed(42)
    all_data = generate_ohlcv(200, seed=42)
    initial = all_data.iloc[:160].copy()

    chart.set(initial)

    sma20_all = calc_sma(all_data, 20)
    sma20_init = sma20_all[sma20_all['time'].isin(initial['time'])].copy()

    ema10_all = calc_ema(all_data, 10)
    ema10_init = ema10_all[ema10_all['time'].isin(initial['time'])].copy()

    rsi_all = calc_rsi(all_data, 14)
    rsi_init = rsi_all[rsi_all['time'].isin(initial['time'])].copy()

    sma_line = chart.create_line('SMA 20', color='rgba(255, 140, 0, 0.7)', width=2)
    sma_line.set(sma20_init)

    ema_line = chart.create_line('EMA 10', color='rgba(65, 105, 225, 0.7)', width=1)
    ema_line.set(ema10_init)

    rsi_hist = chart.create_histogram(
        'RSI 14', color='rgba(128, 0, 128, 0.5)', pane_index=1,
    )
    rsi_hist.set(rsi_init)

    status.set('✅ 初始数据就绪，即将开始批量更新...')
    print("✅ Initial data loaded: 160 bars + SMA 20 + EMA 10 + RSI 14")
    sleep(2)

    # ── 4 rounds of alternating update_bars / update_from_ticks ──
    # Each round adds 10 bars worth of data (25 rows for indicators)
    batch_size = 10
    sma20_remaining = sma20_all.iloc[len(sma20_init):].copy()
    ema10_remaining = ema10_all.iloc[len(ema10_init):].copy()
    rsi_remaining = rsi_all.iloc[len(rsi_init):].copy()

    batch_colors = ['#26A69A', '#FF9800', '#E040FB', '#42A5F5']

    for i in range(4):
        is_bars = (i % 2 == 0)  # round 0,2 = update_bars; round 1,3 = update_from_ticks
        method = 'update_bars' if is_bars else 'update_ticks'
        label = 'K线 + 指标' if is_bars else 'Tick + 指标'

        # Slice this batch
        start = i * batch_size
        sma_batch = sma20_all.iloc[start + len(sma20_init):start + len(sma20_init) + batch_size].copy()
        ema_batch = ema10_all.iloc[start + len(ema10_init):start + len(ema10_init) + batch_size].copy()
        rsi_batch = rsi_all.iloc[start + len(rsi_init):start + len(rsi_init) + batch_size].copy()

        # Get the first time of this batch for the marker (used AFTER data update)
        first_time = sma_batch.iloc[0]['time'] if len(sma_batch) > 0 else None

        # Preview: topbar shows what's coming
        status.set(f'⏳ 即将添加 Batch {i+1}: {label}，{method}()...')
        print(f"\n[Batch {i+1}/4] ⏳ Adding {batch_size} rows via {method}() in 3s...")
        sleep(3)

        # Execute
        status.set(f'▶ 正在添加 Batch {i+1}: {label}...')
        t0 = perf_counter()

        if is_bars:
            sma_line.update_bars(sma_batch)
            ema_line.update_bars(ema_batch)
            rsi_hist.update_bars(rsi_batch)
        else:
            # Convert line/histogram data to tick format for update_ticks
            sma_ticks = df_to_ticks(sma_batch)
            ema_ticks = df_to_ticks(ema_batch)
            rsi_ticks = df_to_ticks(rsi_batch)
            sma_line.update_ticks(sma_ticks)
            ema_line.update_ticks(ema_ticks)
            rsi_hist.update_ticks(rsi_ticks)

        dt = perf_counter() - t0

        # Add marker on the line series (not chart, which targets candle)
        if first_time is not None:
            sma_line.add_marker(
                time=first_time,
                text=f'▶ Batch {i+1} ({method})',
                position='below',
                shape='arrow_up',
                color=batch_colors[i],
            )

        status.set(f'✅ Batch {i+1} 完成: {method}({len(sma_batch)} rows) → {dt*1000:.1f}ms')
        print(f"    ✅ {method}({len(sma_batch)} rows) → {dt*1000:.1f} ms")
        sleep(0.5)

    # ── Final summary ──
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print("update_bars()       — batch OHLCV / line data (single run_script call)")
    print("update_ticks()     — batch tick data (single run_script call)")
    print("Tip: Always prefer batch methods over individual update() calls!")
    print("=" * 60)

    sma_line.add_marker(
        time=all_data.iloc[-1]['time'],
        text='🏁 Demo Complete',
        position='above',
        shape='arrow_up',
        color='#FFD700',
    )
    status.set('🎉 演示完成！')
    print("\n✅ Demo complete!")

    chart.show(wait=120)
    chart.exit()
