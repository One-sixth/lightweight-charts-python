"""
Example 13: Batch Update
Demonstrates update_bars() and update_ticks() for batch incremental updates
using randomly generated data.

This example shows:
1. update_bars() — batch OHLCV incremental update
2. update_ticks() — batch tick incremental update
3. TopBar — displaying status updates to the user
"""
import pandas as pd
import numpy as np
from time import sleep
from lightweight_charts import Chart


def generate_initial_bars(num_bars: int = 100, start_price: float = 100.0) -> pd.DataFrame:
    """Generate random OHLCV data for initial display."""
    np.random.seed(42)
    times = pd.date_range('2020-01-01', periods=num_bars, freq='5min')
    prices = start_price + np.cumsum(np.random.randn(num_bars) * 0.5)

    data = []
    for i, t in enumerate(times):
        base = prices[i]
        data.append({
            'time': t,
            'open': base + np.random.randn() * 0.1,
            'high': base + abs(np.random.randn()) * 0.5 + 0.1,
            'low': base - abs(np.random.randn()) * 0.5 - 0.1,
            'close': base + np.random.randn() * 0.2,
            'volume': int(np.random.exponential(1000)),
            'open_interest': int(np.random.exponential(1000)*100),
        })
    return pd.DataFrame(data)


def generate_next_bars(num_bars: int = 30, last_bar=None) -> pd.DataFrame:
    """Generate the next batch of OHLCV bars for incremental update."""
    if last_bar is not None:
        last_time = pd.to_datetime(last_bar['time'], unit='s')
        last_close = last_bar['close']
    else:
        last_time = pd.Timestamp('2020-01-01')
        last_close = 100.0

    times = pd.date_range(last_time, periods=num_bars + 1, freq='5min')[1:]
    prices = last_close + np.cumsum(np.random.randn(num_bars) * 0.5)

    data = []
    for i, t in enumerate(times):
        base = prices[i]
        data.append({
            'time': t,
            'open': base + np.random.randn() * 0.1,
            'high': base + abs(np.random.randn()) * 0.5 + 0.1,
            'low': base - abs(np.random.randn()) * 0.5 - 0.1,
            'close': base + np.random.randn() * 0.2,
            'volume': int(np.random.exponential(1000)),
            'open_interest': int(np.random.exponential(1000)*100),
        })
    return pd.DataFrame(data)


def generate_ticks(num_ticks: int = 200, last_bar=None) -> pd.DataFrame:
    """Generate random tick data for batch tick update."""
    if last_bar is not None:
        last_time = pd.to_datetime(last_bar['time'], unit='s')
        last_close = last_bar['close']
    else:
        last_time = pd.Timestamp('2020-01-01')
        last_close = 100.0

    # Simulate ticks spanning at least 30 minutes (10s intervals × 200 = ~33min)
    times = pd.date_range(last_time, periods=num_ticks, freq='10s')
    prices = last_close + np.cumsum(np.random.randn(num_ticks) * 0.02)

    return pd.DataFrame({
        'time': times,
        'price': prices,
        'volume': np.random.randint(10, 200, num_ticks),
        'open_interest': np.random.randint(10, 2000, num_ticks) * 100,
    })


if __name__ == '__main__':
    chart = Chart(title='Batch Update Demo', width=1000, height=600)
    chart.legend(visible=True, ohlc=True, persistent=True)

    # Create a topbar textbox for status messages
    chart.topbar.textbox('status', '⏳ 正在初始化...', 'left')
    status = chart.topbar['status']

    chart.show()

    # ── Step 1: Generate and set initial data ──
    status.set('⏳ 正在生成初始数据...')
    print("Generating initial data...")
    initial_df = generate_initial_bars(100)
    chart.set(initial_df)

    # Add a moving average line for reference
    sma = initial_df['close'].rolling(20).mean()
    sma_df = pd.DataFrame({
        'time': initial_df['time'],
        'value': sma,
    }).dropna()

    sma_line = chart.create_line(name='SMA 20', color='rgba(255, 165, 0, 0.6)')
    sma_line.set(sma_df)

    status.set('✅ 初始数据就绪，即将开始批量更新...')
    print("✅ Initial data ready")
    sleep(2)

    # ── Step 2: 4 rounds of alternating bar/tick updates ──
    last_bar = initial_df.iloc[-1]
    bar_colors = ['#26A69A', '#FF9800', '#E040FB', '#42A5F5']

    for i in range(4):
        is_bar = (i % 2 == 0)  # bar: 0,2  tick: 1,3

        if is_bar:
            label = 'K 线'
            count = 30
            # ⏳ 预告
            status.set(f'⏳ 即将添加 {count} 根 {label}，请稍候...')
            print(f"\n[{i+1}/4] ⏳ Adding {count} bars in 3s...")
            next_bars = generate_next_bars(count, last_bar)
            sleep(3)
            # ▶ 执行
            status.set(f'▶ 正在添加 {count} 根 {label}...')
            print(f"    ▶ Adding {count} bars via update_bars()...")
            chart.update_bars(next_bars)
            # 在数据更新后加 marker（确保时间在可见范围内）
            chart.add_marker(
                time=next_bars.iloc[0]['time'],
                text=f'▶ Batch {i+1}: {count} bars',
                position='below',
                shape='arrow_up',
                color=bar_colors[i],
            )
            last_bar = next_bars.iloc[-1]
            status.set(f'✅ 已添加 {count} 根 {label}')
            print(f"    ✅ Added {count} bars")
        else:
            label = '笔 Tick'
            count = 200
            # ⏳ 预告
            status.set(f'⏳ 即将添加 {count} {label}，请稍候...')
            print(f"\n[{i+1}/4] ⏳ Adding {count} ticks in 3s...")
            ticks = generate_ticks(count, last_bar)
            sleep(3)
            # ▶ 执行
            status.set(f'▶ 正在添加 {count} {label}...')
            print(f"    ▶ Adding {count} ticks via update_ticks()...")
            chart.update_ticks(ticks)
            # 在数据更新后加 marker（确保时间在可见范围内）
            chart.add_marker(
                time=ticks.iloc[0]['time'],
                text=f'▶ Batch {i+1}: {count} ticks',
                position='below',
                shape='arrow_up',
                color=bar_colors[i],
            )
            last_bar = {'time': ticks.iloc[-1]['time'], 'close': ticks.iloc[-1]['price']}
            status.set(f'✅ 已添加 {count} {label}')
            print(f"    ✅ Added {count} ticks")

        # Short pause between rounds (except after the last)
        if i < 3:
            sleep(0.5)

    # ── Step 3: Final marker ──
    chart.add_marker(
        time=last_bar['time'] if isinstance(last_bar, dict) else last_bar.iloc[-1]['time'],
        text='🏁 Batch Update Complete',
        position='above',
        shape='arrow_up',
        color='#FFD700',
    )
    status.set('🎉 批量更新演示完成！')
    print("\n✅ Batch update demo complete!")
    print("   - update_bars(): Batch OHLCV incremental update")
    print("   - update_ticks(): Batch tick incremental update")

    chart.show(wait=120)
    chart.exit()
