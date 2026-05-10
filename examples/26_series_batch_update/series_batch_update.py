"""
Example 26: Series Batch Update
Demonstrates update_batch() for Line and Histogram series.

This example shows:
1. How to append multiple data points to a Line series in one go
2. How to append multiple data points to a Histogram series in one go
3. Performance comparison: N individual update() calls vs 1 update_batch() call

The key benefit: update_batch() merges all JS commands into a single
run_script call, dramatically reducing communication overhead.
"""
import pandas as pd
import numpy as np
from time import perf_counter
from lightweight_charts import Chart


def generate_ohlcv(num_bars: int) -> pd.DataFrame:
    """Generate random OHLCV data with a clear trend."""
    np.random.seed(42)
    times = pd.date_range('2020-01-01', periods=num_bars, freq='D')
    base_price = 100.0
    prices = base_price + np.cumsum(np.random.randn(num_bars) * 0.8)

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


def calc_sma(df: pd.DataFrame, period: int, col: str = 'close') -> pd.DataFrame:
    """Calculate simple moving average for a given period."""
    sma = df[col].rolling(window=period).mean()
    return pd.DataFrame({
        'time': df['time'],
        f'SMA {period}': sma,
    }).dropna()


def calc_ema(df: pd.DataFrame, period: int, col: str = 'close') -> pd.DataFrame:
    """Calculate exponential moving average for a given period."""
    ema = df[col].ewm(span=period, adjust=False).mean()
    return pd.DataFrame({
        'time': df['time'],
        f'EMA {period}': ema,
    }).dropna()


def calc_rsi(df: pd.DataFrame, period: int = 14, col: str = 'close') -> pd.DataFrame:
    """Calculate RSI indicator."""
    delta = df[col].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return pd.DataFrame({
        'time': df['time'],
        'RSI 14': rsi,
    }).dropna()


if __name__ == '__main__':
    # ================================================================
    # Phase 1 - Initial setup with set()
    # ================================================================
    chart = Chart(
        title='Series Batch Update — Line & Histogram',
        width=1100,
        height=700,
    )
    chart.legend(visible=True)

    chart.show(False)

    # Generate all data up front (200 bars).
    # We'll only show the first 180 via set(), leaving 20 for batch update.
    np.random.seed(42)
    all_data = generate_ohlcv(200)

    # Initial: first 180 bars
    initial = all_data.iloc[:180].copy()
    chart.set(initial)

    # --- Line 1: SMA 20 (pane 0) ---
    sma20_all = calc_sma(all_data, 20)               # 181 rows (200 - 20 + 1)
    sma20_initial = sma20_all.iloc[:161].copy()      # first 161 rows for the initial 180 bars
    sma20_new = sma20_all.iloc[161:].copy()          # remaining 20 rows for the batch update

    sma20_line = chart.create_line('SMA 20', color='rgba(255, 140, 0, 0.7)', width=2)
    sma20_line.set(sma20_initial)

    # --- Line 2: EMA 10 (pane 0) ---
    ema10_all = calc_ema(all_data, 10)               # 200 rows
    ema10_initial = ema10_all.iloc[:180].copy()       # first 180 rows
    ema10_new = ema10_all.iloc[180:].copy()           # remaining 20 rows

    ema10_line = chart.create_line('EMA 10', color='rgba(65, 105, 225, 0.7)', width=1)
    ema10_line.set(ema10_initial)

    # --- Histogram: RSI 14 (pane 1) ---
    rsi_all = calc_rsi(all_data, 14)                 # 187 rows (200 - 14 + 1)
    rsi_initial = rsi_all.iloc[:167].copy()           # first 167 rows
    rsi_new = rsi_all.iloc[167:].copy()               # remaining 20 rows

    rsi_hist = chart.create_histogram(
        'RSI 14',
        color='rgba(128, 0, 128, 0.5)',
        pane_index=1,
    )
    rsi_hist.set(rsi_initial)

    chart.show(block=False)

    # ================================================================
    # Phase 2 - Line series: update_batch()
    # ================================================================
    print("\n" + "=" * 60)
    print("  PHASE 2: Line series — update_batch()")
    print("=" * 60)

    t0 = perf_counter()
    sma20_line.update_batch(sma20_new)
    dt = perf_counter() - t0
    print(f"[SMA 20]  update_batch({len(sma20_new)} rows) → {dt * 1000:.1f} ms")

    t0 = perf_counter()
    ema10_line.update_batch(ema10_new)
    dt = perf_counter() - t0
    print(f"[EMA 10]  update_batch({len(ema10_new)} rows) → {dt * 1000:.1f} ms")

    # ================================================================
    # Phase 3 - Histogram series: update_batch()
    # ================================================================
    print("\n" + "=" * 60)
    print("  PHASE 3: Histogram series — update_batch()")
    print("=" * 60)

    t0 = perf_counter()
    rsi_hist.update_batch(rsi_new)
    dt = perf_counter() - t0
    print(f"[RSI 14]  update_batch({len(rsi_new)} rows) → {dt * 1000:.1f} ms")

    # ================================================================
    # Phase 4 - Individual update() calls (comparison)
    # ================================================================
    print("\n" + "=" * 60)
    print("  PHASE 4: Individual update() calls (slow path)")
    print("=" * 60)

    # Generate 20 more bars and their EMA values
    extra = generate_ohlcv(20)
    # offset time so they come AFTER all_data
    last_time = pd.Timestamp(all_data.iloc[-1]['time'])
    extra['time'] = pd.date_range(last_time, periods=21, freq='D')[1:]

    # Calculate EMA on combined data, keep only rows after the last known time
    combined = pd.concat([all_data, extra], ignore_index=True)
    ema10_combined = calc_ema(combined, 10)
    # ema10_line.data stores times as Unix seconds (int)
    last_known_ts = ema10_line.data['time'].iloc[-1]
    ema10_combined['time_epoch'] = (
        pd.to_datetime(ema10_combined['time']) - pd.Timestamp("1970-01-01")
    ) // pd.Timedelta('1s')
    ema10_new_only = ema10_combined[
        ema10_combined['time_epoch'] > last_known_ts
    ].drop(columns='time_epoch')

    t0 = perf_counter()
    for _, row in ema10_new_only.iterrows():
        ema10_line.update(row)
    dt = perf_counter() - t0
    print(
        f"[EMA 10]  {len(ema10_new_only)} × update() calls"
        f" → {dt * 1000:.1f} ms  (compare to batch above)"
    )

    # ================================================================
    # Summary
    # ================================================================
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print("update_batch() — single run_script call for N data points")
    print("update()       — N individual run_script calls")
    print()
    print("Tip: Always prefer update_batch() when appending many points!")
    print()

    chart.show(True)
