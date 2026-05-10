"""
Example 16: PySide6 Speed Race
Benchmarks different data update strategies using PySide6 + QtChart:
  1. update() — one bar at a time (serial JS calls)
  2. update_bars() — batch OHLCV (single JS call)
  3. update_from_ticks() — batch ticks (single JS call)
  4. set() — full data replacement

Uses randomly generated data and measures elapsed time for each method.
"""
import sys
import time
import pandas as pd
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout,
    QTextEdit, QLabel, QSpinBox, QFormLayout, QGroupBox
)
from PySide6.QtCore import Qt
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


def generate_ticks(num_ticks: int, start_time, start_price: float = 105.0) -> pd.DataFrame:
    """Generate random tick data within a single bar's timeframe."""
    np.random.seed(int(time.time()) % 10000)
    times = pd.date_range(start_time, periods=num_ticks, freq='3s')
    prices = start_price + np.cumsum(np.random.randn(num_ticks) * 0.1)
    return pd.DataFrame({
        'time': times,
        'price': prices,
        'volume': np.random.randint(10, 200, num_ticks),
    })


class SpeedRaceWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Update Speed Race')
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ── Chart ──
        self.chart = QtChart(inner_width=1.0, inner_height=1.0)
        self.chart.legend(visible=True, ohlc=True, persistent=True)
        main_layout.addWidget(self.chart.get_webview(), stretch=3)

        # ── Controls ──
        controls = QHBoxLayout()

        # Settings group
        settings_group = QGroupBox('Settings')
        settings_layout = QFormLayout(settings_group)
        self.spin_bars = QSpinBox()
        self.spin_bars.setRange(10, 5000)
        self.spin_bars.setValue(500)
        self.spin_bars.setSuffix(' bars')
        settings_layout.addRow('Batch size:', self.spin_bars)

        self.spin_ticks = QSpinBox()
        self.spin_ticks.setRange(10, 50000)
        self.spin_ticks.setValue(1000)
        self.spin_ticks.setSuffix(' ticks')
        settings_layout.addRow('Tick count:', self.spin_ticks)
        controls.addWidget(settings_group)

        # Buttons group
        btn_group = QGroupBox('Run Test')
        btn_layout = QVBoxLayout(btn_group)

        btn_row1 = QHBoxLayout()
        self.btn_update = QPushButton('🏃 update() × N')
        self.btn_update.clicked.connect(self.run_update_race)
        self.btn_batch = QPushButton('🚀 update_bars()')
        self.btn_batch.clicked.connect(self.run_batch_race)
        btn_row1.addWidget(self.btn_update)
        btn_row1.addWidget(self.btn_batch)

        btn_row2 = QHBoxLayout()
        self.btn_ticks = QPushButton('⚡ update_from_ticks()')
        self.btn_ticks.clicked.connect(self.run_tick_race)
        self.btn_set = QPushButton('🔄 set() full replace')
        self.btn_set.clicked.connect(self.run_set_race)
        btn_row2.addWidget(self.btn_ticks)
        btn_row2.addWidget(self.btn_set)

        btn_row3 = QHBoxLayout()
        self.btn_all = QPushButton('🏆 Run All')
        self.btn_all.clicked.connect(self.run_all)
        self.btn_reset = QPushButton('Reset Chart')
        self.btn_reset.clicked.connect(self.reset_chart)
        btn_row3.addWidget(self.btn_all)
        btn_row3.addWidget(self.btn_reset)

        btn_layout.addLayout(btn_row1)
        btn_layout.addLayout(btn_row2)
        btn_layout.addLayout(btn_row3)
        controls.addWidget(btn_group)

        main_layout.addLayout(controls)

        # ── Log ──
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        self.log.setStyleSheet("background: #1e1e1e; color: #d4d4d4; font-family: Consolas;")
        main_layout.addWidget(self.log)

        # ── Init chart ──
        self.base_data = generate_bars(100, seed=42)
        self.chart.set(self.base_data)
        self.log.append("✅ Chart initialized with 100 bars.\n")

    def log_msg(self, msg: str):
        self.log.append(msg)
        # auto scroll
        self.log.verticalScrollBar().setValue(
            self.log.verticalScrollBar().maximum()
        )

    def reset_chart(self):
        self.chart.reset()
        self.base_data = generate_bars(100, seed=42)
        self.chart.set(self.base_data)
        self.log.append("🔄 Chart reset.\n")

    def run_update_race(self):
        """Test: N individual update() calls."""
        n = self.spin_bars.value()
        new_bars = generate_bars(n, seed=np.random.randint(0, 10000))
        last_time = pd.to_datetime(self.base_data.iloc[-1]['time'], unit='s')
        new_times = pd.date_range(last_time, periods=n + 1, freq='1min')[1:]
        new_bars['time'] = new_times

        self.log_msg(f"🏃 Running update() × {n}...")
        start = time.perf_counter()

        for _, row in new_bars.iterrows():
            self.chart.update(row)

        elapsed = time.perf_counter() - start
        self.log_msg(f"   ✅ update() × {n}: {elapsed:.4f}s ({elapsed/n*1000:.3f}ms/bar)\n")

        # Keep data consistent
        self.base_data = pd.concat([self.base_data, new_bars], ignore_index=True)

    def run_batch_race(self):
        """Test: single update_bars() call."""
        n = self.spin_bars.value()
        new_bars = generate_bars(n, seed=np.random.randint(0, 10000))
        last_time = pd.to_datetime(self.base_data.iloc[-1]['time'], unit='s')
        new_times = pd.date_range(last_time, periods=n + 1, freq='1min')[1:]
        new_bars['time'] = new_times

        self.log_msg(f"🚀 Running update_bars({n})...")
        start = time.perf_counter()

        self.chart.update_bars(new_bars)

        elapsed = time.perf_counter() - start
        self.log_msg(f"   ✅ update_bars({n}): {elapsed:.4f}s ({elapsed/n*1000:.3f}ms/bar)\n")

        self.base_data = pd.concat([self.base_data, new_bars], ignore_index=True)

    def run_tick_race(self):
        """Test: single update_from_ticks() call."""
        n = self.spin_ticks.value()
        last_time = pd.to_datetime(self.base_data.iloc[-1]['time'], unit='s')
        last_close = self.base_data.iloc[-1]['close']
        ticks = generate_ticks(n, last_time, last_close)

        self.log_msg(f"⚡ Running update_from_ticks({n})...")
        start = time.perf_counter()

        self.chart.update_from_ticks(ticks)

        elapsed = time.perf_counter() - start
        self.log_msg(f"   ✅ update_from_ticks({n}): {elapsed:.4f}s ({elapsed/n*1000:.3f}ms/tick)\n")
        # Track progression by appending last candle, so repeated runs don't fail
        last_candle = self.chart.candle_data.iloc[-1:].copy()
        self.base_data = pd.concat([self.base_data, last_candle], ignore_index=True)

    def run_set_race(self):
        """Test: full set() replacement with N bars."""
        n = self.spin_bars.value()
        new_data = generate_bars(n, seed=np.random.randint(0, 10000))

        self.log_msg(f"🔄 Running set({n} bars)...")
        start = time.perf_counter()

        self.chart.set(new_data)

        elapsed = time.perf_counter() - start
        self.log_msg(f"   ✅ set({n} bars): {elapsed:.4f}s ({elapsed/n*1000:.3f}ms/bar)\n")

        self.base_data = new_data

    def run_all(self):
        """Run all tests sequentially with fresh chart state."""
        self.reset_chart()
        self.log_msg("=" * 50)
        self.log_msg("🏆 Running all benchmarks...\n")

        self.run_set_race()
        self.run_batch_race()
        self.run_update_race()
        self.run_tick_race()

        self.log_msg("=" * 50)
        self.log_msg("🏆 All benchmarks complete!\n")


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    qapp = QApplication(sys.argv)

    window = SpeedRaceWindow()
    window.show()

    sys.exit(qapp.exec())
