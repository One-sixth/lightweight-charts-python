"""
HTMLChart Example - Grid layout + Absolute position

Generates two HTML files:
1. html_chart_demo.html        - 2 subcharts x 2 panes (grid layout)
2. html_chart_demo_abs.html    - 2 charts with set_position (absolute layout)

Demonstrates:
- create_subchart() for independent chart instances
- pane_index for vertical splitting within each subchart
- set_position() for absolute pixel-free positioning
"""

import pandas as pd
import numpy as np
from lightweight_charts import HTMLChart


def generate_ohlcv_data(days=120):
    """Generate simulated OHLCV data"""
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    np.random.seed(42)
    base_price = 100.0
    returns = np.random.normal(0.001, 0.018, days)
    prices = base_price * np.cumprod(1 + returns)

    data = []
    for i, date in enumerate(dates):
        open_price = prices[i] * (1 + np.random.uniform(-0.008, 0.008))
        high_price = max(open_price, prices[i]) * (1 + np.random.uniform(0, 0.015))
        low_price = min(open_price, prices[i]) * (1 - np.random.uniform(0, 0.015))
        close_price = prices[i]
        volume = int(np.random.uniform(800, 12000))

        data.append({
            'time': date.strftime('%Y-%m-%d'),
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
    return pd.DataFrame(data)


def calculate_sma(df, period=20):
    """Simple Moving Average"""
    return pd.DataFrame({
        'time': df['time'],
        'value': df['close'].rolling(window=period).mean()
    }).dropna()


def calculate_bollinger_bands(df, period=20, std_dev=2):
    """Bollinger Bands"""
    sma = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    bb_upper = sma + std * std_dev
    bb_lower = sma - std * std_dev
    return pd.DataFrame({
        'time': df['time'],
        'BB Upper': bb_upper,
        'BB Lower': bb_lower,
    }).dropna()


def generate_signals(df):
    """SMA golden/death cross signals"""
    sma10 = df['close'].rolling(10).mean()
    sma30 = df['close'].rolling(30).mean()
    signals = []
    held = False
    for i in range(30, len(df)):
        if not held and sma10.iloc[i] > sma30.iloc[i] and sma10.iloc[i - 1] <= sma30.iloc[i - 1]:
            signals.append({
                'time': df.iloc[i]['time'],
                'position': 'below',
                'color': '#e91e63',
                'shape': 'arrow_up',
                'text': f"Buy {df.iloc[i]['close']:.1f}"
            })
            held = True
        elif held and sma10.iloc[i] < sma30.iloc[i] and sma10.iloc[i - 1] >= sma30.iloc[i - 1]:
            signals.append({
                'time': df.iloc[i]['time'],
                'position': 'above',
                'color': '#00bcd4',
                'shape': 'arrow_down',
                'text': f"Sell {df.iloc[i]['close']:.1f}"
            })
            held = False
    return signals


def demo():
    """HTMLChart demo: 2 subcharts x 2 panes"""
    print("[HTMLChart] 2 subcharts x 2 panes")
    print("=" * 40)

    # Generate data
    print("[1/4] Generating data...")
    df = generate_ohlcv_data(120)
    vol_df = df[['time', 'volume']].rename(columns={'volume': 'value'})

    # ================================================================
    # Main chart: 2x1 grid, position=211 (top)
    # ================================================================
    print("[2/4] Subchart 1: K-line + SMA + BB + markers...")
    chart = HTMLChart(width=1200, height=1200, position=211)
    chart.set(df)
    chart.legend(visible=True)

    # SMA
    sma10 = calculate_sma(df, 10)
    sma20 = calculate_sma(df, 20)
    chart.create_line('SMA 10', color='#e91e63', width=1).set(sma10)
    chart.create_line('SMA 20', color='#2196f3', width=1).set(sma20)

    # Bollinger Bands
    bb = calculate_bollinger_bands(df, 20, 2)
    bb_upper = pd.DataFrame({'time': bb['time'], 'value': bb['BB Upper']})
    bb_lower = pd.DataFrame({'time': bb['time'], 'value': bb['BB Lower']})
    chart.create_line('BB Upper', color='#9c27b0', width=1, style='dotted').set(bb_upper)
    chart.create_line('BB Lower', color='#9c27b0', width=1, style='dotted').set(bb_lower)

    # Buy/sell markers
    for sig in generate_signals(df):
        chart.marker(**sig)

    # Subchart 1 Volume: pane 1
    print("[3/4] Subchart 1: Volume...")
    chart.create_histogram('Volume', color='#26a69a', price_line=False, price_label=False, pane_index=1).set(vol_df)

    # ================================================================
    # Subchart 2: position=212 (bottom)
    # ================================================================
    print("[4/4] Subchart 2: K-line + Volume...")
    sub2 = chart.create_subchart(position=212)
    sub2.legend(visible=True)
    sub2.set(df)

    # Subchart 2 Volume: pane 1
    sub2.create_histogram('Volume', color='#ff9800', price_line=False, price_label=False, pane_index=1).set(vol_df)

    # Export
    output_path = 'html_chart_demo.html'
    chart.export(output_path)

    print(f"\nDone! Exported: {output_path}")
    print(f"Total: {len(df)} bars")
    print()
    print("Layout:")
    print("  [Subchart 1] K-line + SMA + BB + markers  (pane 0)")
    print("  [Subchart 1] Volume                        (pane 1)")
    print("  [Subchart 2] K-line                        (pane 0)")
    print("  [Subchart 2] Volume                        (pane 1)")


def demo_absolute():
    """HTMLChart demo: absolute position with set_position()"""
    print("\n[HTMLChart] Absolute Position Demo")
    print("=" * 40)

    print("[1/3] Generating data...")
    df = generate_ohlcv_data(120)
    vol_df = df[['time', 'volume']].rename(columns={'volume': 'value'})

    # ================================================================
    # Chart 1: top-left quarter (0, 0, 50%, 50%)
    # ================================================================
    print("[2/3] Chart 1: top-left (0,0,50%,50%)...")
    chart = HTMLChart(width=1200, height=800)
    chart.set(df)
    chart.legend(visible=True)
    chart.set_position(x=0, y=0, width=0.5, height=0.5)

    # SMA
    sma10 = calculate_sma(df, 10)
    chart.create_line('SMA 10', color='#e91e63', width=1).set(sma10)

    # Buy/sell markers
    for sig in generate_signals(df):
        chart.marker(**sig)

    # ================================================================
    # Chart 2: bottom-right quarter (50%, 50%, 50%, 50%)
    # ================================================================
    print("[3/3] Chart 2: bottom-right (50%,50%,50%,50%)...")
    sub2 = chart.create_subchart(position=111)
    sub2.legend(visible=True)
    sub2.set(df)
    sub2.set_position(x=0.5, y=0.5, width=0.5, height=0.5)

    # Volume
    sub2.create_histogram('Volume', color='#ff9800', price_line=False, price_label=False, pane_index=1).set(vol_df)

    # Export
    output_path = 'html_chart_demo_abs.html'
    chart.export(output_path)

    print(f"\nDone! Exported: {output_path}")
    print(f"Total: {len(df)} bars")
    print()
    print("Layout:")
    print("  [Chart 1] K-line + SMA + markers   (set_position 0,0,50%,50%)")
    print("  [Chart 2] K-line + Volume           (set_position 50%,50%,50%,50%)")


if __name__ == '__main__':
    demo()
    demo_absolute()
