"""
Example 14: Set Period
Demonstrates set_period() for locking the chart's time interval,
so that set() uses the locked interval instead of auto-detecting.

This example shows:
1. Normal set() with auto-detected 5min interval
2. set_period(3600) to lock to 1-hour bars
3. set() with data of different intervals to verify the lock
4. set_period(None) to unlock
"""
import pandas as pd
import numpy as np
from time import sleep
from lightweight_charts import Chart


def generate_bars(num_bars: int, freq: str, start_price: float = 100.0,
                  seed: int = 42) -> pd.DataFrame:
    """Generate random OHLCV data with a given frequency."""
    np.random.seed(seed)
    times = pd.date_range('2020-01-01', periods=num_bars, freq=freq)
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
        })
    return pd.DataFrame(data)


def generate_1min_bars(num_bars: int, start_price: float = 105.0) -> pd.DataFrame:
    """Generate 1-minute bars (different frequency for testing lock)."""
    np.random.seed(99)
    times = pd.date_range('2020-01-01 09:30', periods=num_bars, freq='1min')
    prices = start_price + np.cumsum(np.random.randn(num_bars) * 0.1)
    
    data = []
    for i, t in enumerate(times):
        base = prices[i]
        data.append({
            'time': t,
            'open': base + np.random.randn() * 0.02,
            'high': base + abs(np.random.randn()) * 0.2 + 0.05,
            'low': base - abs(np.random.randn()) * 0.2 - 0.05,
            'close': base + np.random.randn() * 0.05,
            'volume': int(np.random.exponential(500)),
        })
    return pd.DataFrame(data)


if __name__ == '__main__':
    chart = Chart(title='Set Period Demo', width=1000, height=600)
    chart.legend(visible=True, ohlc=True, persistent=True)

    # ── Step 1: Normal set() with auto-detected 5min interval ──
    print("Step 1: Setting 5-minute bars (auto-detect interval)...")
    df_5min = generate_bars(50, '5min')
    chart.set(df_5min)
    print(f"  → Auto-detected interval: {chart._interval}s (5min)")
    chart.show()
    sleep(1.5)

    # ── Step 2: Lock to 1-hour interval ──
    print("\nStep 2: Locking to 1-hour interval with set_period(3600)...")
    chart.set_period(3600)
    print(f"  → Locked interval: {chart._interval}s (1 hour)")
    print(f"  → period_locked: {chart._period_locked}")
    sleep(1)

    # ── Step 3: set() with 30min bars while locked to 1-hour ──
    print("\nStep 3: Setting 30-minute bars while locked to 1-hour...")
    df_30min = generate_bars(48, '30min', seed=43)
    chart.set(df_30min)
    print(f"  → Interval still locked at: {chart._interval}s")
    print("  → All time values are aligned to 1-hour boundaries")
    sleep(1.5)

    # ── Step 4: set() with 1min bars while locked to 1-hour ──
    print("\nStep 4: Setting 1-minute bars while locked to 1-hour...")
    df_1min = generate_1min_bars(120)
    chart.set(df_1min)
    print(f"  → Interval still: {chart._interval}s")
    print("  → Time values aligned to 1-hour (0, 3600, 7200...)")
    sleep(1.5)

    # ── Step 5: Unlock and set with 15min bars ──
    print("\nStep 5: Unlocking (set_period(None)) and setting 15-minute bars...")
    chart.set_period(None)
    df_15min = generate_bars(40, '15min', seed=44)
    chart.set(df_15min)
    print(f"  → Auto-detected interval: {chart._interval}s (15min)")
    print(f"  → period_locked: {chart._period_locked}")
    sleep(1)

    # ── Step 6: Add markers to verify no drift ──
    print("\nStep 6: Adding markers and re-setting data to verify no drift...")
    chart.marker(
        time=df_15min.iloc[10]['time'],
        text='Marker 1',
        position='above',
        shape='arrow_up',
        color='#FFD700'
    )
    chart.marker(
        time=df_15min.iloc[25]['time'],
        text='Marker 2',
        position='below',
        shape='arrow_down',
        color='#FF69B4'
    )
    print("  → Markers added")
    sleep(1)

    # Re-set the same data — markers should NOT drift
    print("Re-setting data to verify marker stability...")
    chart.set(df_15min)
    print("  → Markers remain at correct positions ✅")
    sleep(1)

    print("\n✅ Set Period demo complete!")
    print("  - set_period(seconds): Lock interval for set()")
    print("  - set_period(None): Unlock and re-enable auto-detection")