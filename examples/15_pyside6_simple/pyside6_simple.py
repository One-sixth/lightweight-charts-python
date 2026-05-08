"""
Example 15: PySide6 Simple Test
Demonstrates using lightweight-charts with PySide6 (QtChart).
The chart is embedded in a PySide6 window with random OHLCV data.

This example tests:
1. QtChart embedding in a PySide6 QMainWindow
2. Random data generation and display
3. Basic interaction (legend, markers)
"""
import sys
import pandas as pd
import numpy as np
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import QTimer
from lightweight_charts.widgets import QtChart


def generate_bars(num_bars: int, freq: str = '1min', start_price: float = 100.0,
                  seed: int = 42) -> pd.DataFrame:
    """Generate random OHLCV data."""
    np.random.seed(seed)
    times = pd.date_range('2020-01-01 09:30', periods=num_bars, freq=freq)
    prices = start_price + np.cumsum(np.random.randn(num_bars) * 0.3)
    
    data = []
    for i, t in enumerate(times):
        base = prices[i]
        data.append({
            'time': t,
            'open': base + np.random.randn() * 0.05,
            'high': base + abs(np.random.randn()) * 0.3 + 0.05,
            'low': base - abs(np.random.randn()) * 0.3 - 0.05,
            'close': base + np.random.randn() * 0.1,
            'volume': int(np.random.exponential(800)),
        })
    return pd.DataFrame(data)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PySide6 + Lightweight Charts')
        self.resize(1000, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Create chart
        self.chart = QtChart(inner_width=1.0, inner_height=1.0)
        self.chart.legend(visible=True, ohlc=True, persistent=True)
        layout.addWidget(self.chart.get_webview())

        # Button bar
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton('Add 10 Bars')
        self.btn_add.clicked.connect(self.on_add_bars)
        self.btn_marker = QPushButton('Add Marker')
        self.btn_marker.clicked.connect(self.on_add_marker)
        self.btn_reset = QPushButton('Reset')
        self.btn_reset.clicked.connect(self.on_reset)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_marker)
        btn_layout.addWidget(self.btn_reset)
        layout.addLayout(btn_layout)

        # Load initial data
        self.bar_count = 100
        self.initial_df = generate_bars(self.bar_count)
        self.chart.set(self.initial_df)

        # Auto-update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_tick)

    def on_add_bars(self):
        """Add 10 new bars via update_bars()."""
        new_df = generate_bars(10, seed=np.random.randint(0, 10000))
        # Shift time to continue from last bar
        last_time = pd.to_datetime(self.initial_df.iloc[-1]['time'])
        new_times = pd.date_range(last_time, periods=11, freq='1min')[1:]
        new_df['time'] = new_times
        self.chart.update_bars(new_df)
        self.bar_count += 10
        self.initial_df = pd.concat([self.initial_df, new_df], ignore_index=True)

    def on_add_marker(self):
        """Add a marker at the latest bar."""
        last_bar = self.initial_df.iloc[-1]
        self.chart.marker(
            time=last_bar['time'],
            text=f'Bar #{self.bar_count}',
            position='above',
            shape='arrow_up',
            color='#FFD700'
        )

    def on_reset(self):
        """Reset chart and reload initial data."""
        self.chart.reset()
        self.initial_df = generate_bars(100)
        self.chart.set(self.initial_df)
        self.bar_count = 100

    def on_timer_tick(self):
        """Auto-add one bar via update()."""
        new_df = generate_bars(1, seed=np.random.randint(0, 10000))
        last_time = pd.to_datetime(self.initial_df.iloc[-1]['time'])
        new_df['time'] = [last_time + pd.Timedelta(minutes=1)]
        self.chart.update(new_df.iloc[0])
        self.initial_df = pd.concat([self.initial_df, new_df], ignore_index=True)
        self.bar_count += 1


if __name__ == '__main__':
    app = sys.argv[0] if len(sys.argv) > 1 else ''
    # Note: QApplication must be created before QtChart
    from PySide6.QtWidgets import QApplication
    qapp = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(qapp.exec())