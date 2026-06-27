"""
Example 13: Batch Update
Demonstrates update_bars() and update_from_ticks() for batch incremental updates
using randomly generated data.

This example shows:
1. update_bars() — batch OHLCV incremental update
2. update_from_ticks() — batch tick incremental update
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

    # Step 1: Generate and set initial data
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

    chart.show()

    # Step 2: Demonstrate update_bars() — batch OHLCV update
    print("\n=== update_bars() Demo ===")
    print("Adding 30 bars in batch...")

    next_bars = generate_next_bars(30, initial_df.iloc[-1])
    chart.update_bars(next_bars)
    print(f"✅ Updated {len(next_bars)} bars via update_bars()")
    sleep(1)

    # Step 3: Demonstrate update_from_ticks() — batch tick update
    print("\n=== update_from_ticks() Demo ===")
    print("Adding 200 ticks in batch...")

    ticks = generate_ticks(200, next_bars.iloc[-1])
    chart.update_from_ticks(ticks)
    print(f"✅ Updated {len(ticks)} ticks via update_from_ticks()")
    sleep(1)

    # Step 4: Add a marker to verify marker alignment
    chart.marker(
        time=next_bars.iloc[15]['time'],
        text='Batch Update Marker',
        position='above',
        shape='arrow_up',
        color='#FFD700'
    )
    print("\n✅ Marker added at batch-updated bar")

    # Step 5: Demonstrate update_bars() again to verify markers don't drift
    print("\n=== Verifying marker stability ===")
    print("Adding 10 more bars via update_bars()...")

    next_bar_new_start = {'time': ticks.iloc[-1]['time'], 'close': ticks.iloc[-1]['price']}
    more_bars = generate_next_bars(10, next_bar_new_start)
    chart.update_bars(more_bars)
    print("✅ Bars added, marker should remain stable")

    print("\n✅ Batch update demo complete!")
    print("   - update_bars(): Batch OHLCV incremental update")
    print("   - update_from_ticks(): Batch tick incremental update")
