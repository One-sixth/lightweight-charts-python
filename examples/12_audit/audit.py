"""
Creates a large number of chart resources to demonstrate
the JS-side audit engine (chart.audit(use_js=True)).

Run with:
    python examples/12_audit/audit.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import pandas as pd
import numpy as np
from lightweight_charts import Chart

if __name__ == '__main__':
    # ---- generate test data ----
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    price = 100.0
    rows = []
    for i in range(100):
        price += np.random.normal(0, 1.5)
        rows.append({
            'date': dates[i],
            'open': round(price + np.random.normal(0, 0.5), 2),
            'high': round(price + abs(np.random.normal(0, 0.8)), 2),
            'low': round(price - abs(np.random.normal(0, 0.8)), 2),
            'close': round(price, 2),
            'volume': int(np.random.randint(1000, 50000)),
            'open_interest': int(20000 + i * 150 + np.random.randint(-2000, 2000)),
        })
    df = pd.DataFrame(rows)

    # ---- create chart ----
    chart = Chart(toolbox=True, width=1000, height=700, position=211)
    chart.legend(visible=True, persistent=True, shorthand=True)
    chart.set(df)
    chart.show(block=False)

    import time
    time.sleep(2)

    # ========== create lots of resources ==========

    print("Creating resources ...")

    # 4 extra Line series (simulating indicators)
    for i, (name, color) in enumerate([
        ('SMA 20', '#ff0000'),
        ('SMA 50', '#00ff00'),
        ('EMA 12', '#ffff00'),
        ('Bollinger', '#ff00ff'),
    ]):
        line = chart.create_line(name, color=color, width=2)
        fake_data = pd.DataFrame({
            'time': dates,
            name: [price + np.random.normal(0, 2) for _ in range(100)],
        })
        line.set(fake_data)
        print(f"  created {name}")

    # 1 Histogram (e.g. volume indicator)
    hist = chart.create_histogram('Volume Osc', color='rgba(0,150,255,0.5)')
    hist_df = pd.DataFrame({
        'time': dates,
        'Volume Osc': np.random.rand(100) * 1000,
    })
    hist.set(hist_df)
    print("  created Volume Osc")

    # Price lines
    for i, price_val in enumerate([105, 110, 95, 98]):
        pl = chart.create_price_line(price=price_val, title=f'Level {i+1}',
                                     price_label=True, color='rgba(255,200,0,0.8)')
        print(f"  created price line at {price_val}")

    # Markers
    for i in range(8):
        chart.marker(
            time=dates[10 + i * 10],
            position='above' if i % 2 == 0 else 'below',
            shape='circle' if i % 2 == 0 else 'arrow_up',
            color='#ff0000' if i % 2 == 0 else '#00ff00',
            text=f'Event {i+1}',
        )
    print("  created 8 markers")

    # Drawings
    hl = chart.horizontal_line(price=102, color='#ff8800', width=2, text='Resistance')
    vl = chart.vertical_line(dates[30], color='#8800ff', width=2)
    tl = chart.trend_line(dates[10], 98, dates[60], 110, line_color='#00ffff')
    bx = chart.box(dates[20], 95, dates[50], 115, color='#ff00ff',
                   fill_color='rgba(255,0,255,0.1)')
    rl = chart.ray_line(dates[40], 100, color='#00ff88')
    vs = chart.vertical_span(dates[45], dates[70], color='rgba(252,219,3,0.12)')
    print("  created 6 drawings + 1 vertical span")

    # Subchart
    sub = chart.create_subchart(position=212)
    sub.create_line('RSI', color='#ff6600')
    sub_hist = sub.create_histogram('Momentum', color='rgba(0,200,100,0.4)')
    sub_time = pd.date_range('2024-01-01', periods=100, freq='D')
    sub.set(pd.DataFrame({'time': sub_time, 'open': 50, 'high': 55,
                          'low': 45, 'close': 52, 'volume': 1000}))
    sub.create_line('RSI').set(pd.DataFrame({
        'time': sub_time, 'RSI': np.random.rand(100) * 40 + 30,
    }))
    print("  created subchart with indicators")

    # Table
    tbl = chart.create_table(
        width=0.25, height=0.3,
        headings=('Symbol', 'Price', 'Chg%'),
        widths=(0.4, 0.3, 0.3),
        position=(0.7, 0.1),  # 使用相对坐标：右侧位置
    )
    for sym, pr, chg in [('AAPL', 198.5, '+1.2'), ('TSLA', 245.0, '-0.8'),
                           ('GOOG', 175.2, '+0.5'), ('MSFT', 420.3, '+2.1')]:
        tbl.new_row(sym, pr, chg)
    print("  created table with 4 rows")

    time.sleep(1)

    # ========== JS-side audit ==========
    print("\n" + "=" * 60)
    print("  chart.audit(use_js=True)")
    print("=" * 60)
    print()

    result = chart.audit(use_js=True)
    if isinstance(result, dict) and 'error' in result:
        print("AUDIT ERROR:", result['error'])
        print("Fallback:", result.get('fallback', 'N/A'))
    elif isinstance(result, str):
        # TOML-like format — print raw
        print(result)
    else:
        print(result)

    print()
    print("=" * 60)
    print("  Done — chart window stays open. Close it to exit.")
    print("=" * 60)

    chart.show(block=True)
