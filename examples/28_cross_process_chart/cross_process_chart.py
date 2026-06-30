"""
Example 28: CrossProcessChart - 跨进程窗口嵌入 Qt
演示将 pywebview 图表窗口嵌入到 PySide6 QWidget 中。

原理：
- 图表运行在独立子进程（pywebview）
- 通过 HWND 句柄嵌入到 Qt 布局
- 类似 Chrome 多进程窗口嵌入架构
"""
import sys
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QHBoxLayout, QPushButton, QSplitter
)
from PySide6.QtCore import Qt
from lightweight_charts import CrossProcessChart


def generate_bars(num_bars: int, freq: str = '1min', start_price: float = 100.0,
                  seed: int = 42) -> pd.DataFrame:
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
        self.setWindowTitle('CrossProcessChart Demo')
        self.resize(1200, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Orientation.Vertical)

        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)

        self.chart = CrossProcessChart(
            parent=chart_container,
            width=800, height=500,
            title='AAPL',
            toolbox=True
        )
        self.chart.legend(visible=True, persistent=True)
        chart_layout.addWidget(self.chart.widget)

        self.initial_df = generate_bars(200)
        self.chart.set(self.initial_df)

        splitter.addWidget(chart_container)

        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)

        self.btn_add = QPushButton('Add 10 Bars')
        self.btn_add.clicked.connect(self.on_add_bars)
        self.btn_marker = QPushButton('Add Marker')
        self.btn_marker.clicked.connect(self.on_add_marker)
        self.btn_reset = QPushButton('Reset')
        self.btn_reset.clicked.connect(self.on_reset)
        self.btn_resize = QPushButton('Toggle Size')
        self.btn_resize.clicked.connect(self.on_toggle_size)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_marker)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_resize)

        splitter.addWidget(btn_container)
        splitter.setSizes([600, 100])

        layout.addWidget(splitter)
        self._is_small = False

    def on_add_bars(self):
        new_df = generate_bars(10, seed=np.random.randint(0, 10000))
        last_time = pd.to_datetime(self.initial_df.iloc[-1]['time'])
        new_times = pd.date_range(last_time, periods=11, freq='1min')[1:]
        new_df['time'] = new_times
        self.chart.update_bars(new_df)
        self.initial_df = pd.concat([self.initial_df, new_df], ignore_index=True)

    def on_add_marker(self):
        last_bar = self.initial_df.iloc[-1]
        self.chart.add_marker(
            time=last_bar['time'],
            text='Marker',
            position='above',
            shape='arrow_up',
            color='#FFD700'
        )

    def on_reset(self):
        self.chart.reset()
        self.initial_df = generate_bars(200)
        self.chart.set(self.initial_df)

    def on_toggle_size(self):
        if self._is_small:
            self.chart.resize(800, 500)
        else:
            self.chart.resize(600, 300)
        self._is_small = not self._is_small

    def closeEvent(self, event):
        self.chart.exit()
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
