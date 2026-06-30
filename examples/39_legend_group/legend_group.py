"""
Legend 分组功能演示

功能：
- group='MA' 的均线组：SMA 20 + EMA 50 同一行，♦ MA 组开关
- group='MOM' 的动量组：ROC + Momentum 同一行，♦ MOM 组开关
- 无组的 RSI 独立一行
- OHLC + Volume 显示在顶部
"""
import pandas as pd
from lightweight_charts import Chart


def calculate_sma(df, period=50):
    return pd.DataFrame({
        'time': df['time'],
        'value': df['close'].rolling(window=period).mean()
    }).dropna()


def calculate_ema(df, period=20):
    return pd.DataFrame({
        'time': df['time'],
        'value': df['close'].ewm(span=period, adjust=False).mean()
    }).dropna()


def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return pd.DataFrame({'time': df['time'], 'value': rsi}).dropna()


def calculate_roc(df, period=10):
    return pd.DataFrame({
        'time': df['time'],
        'value': df['close'].pct_change(periods=period) * 100
    }).dropna()


def calculate_momentum(df, period=10):
    return pd.DataFrame({
        'time': df['time'],
        'value': df['close'] - df['close'].shift(period)
    }).dropna()


def calculate_stochastic(df, k_period=14, d_period=3):
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    k = (df['close'] - low_min) / (high_max - low_min) * 100
    d = k.rolling(window=d_period).mean()
    return pd.DataFrame({'time': df['time'], 'value': k}).dropna()


if __name__ == '__main__':
    chart = Chart()
    chart.legend(visible=True, ohlc=True, percent=True, lines=True)

    df = pd.read_csv('../4_line_indicators/ohlcv.csv').rename(columns={'date': 'time'})
    chart.set(df)

    # ── MA 组（pane 0）：两个均线放在同一行 ──
    sma20 = chart.create_line('SMA 20', color='rgb(255, 200, 0)', width=1, group='MA')
    sma20.set(calculate_sma(df, period=20))

    ema50 = chart.create_line('EMA 50', color='rgb(0, 180, 255)', width=1, group='MA')
    ema50.set(calculate_ema(df, period=50))

    # ── MOM 组（pane 0）：动量指标同一行 ──
    roc = chart.create_line('ROC 10', color='rgb(255, 100, 100)', width=1, group='MOM')
    roc.set(calculate_roc(df, period=10))

    momentum = chart.create_line('MOM 10', color='rgb(100, 255, 100)', width=1, group='MOM')
    momentum.set(calculate_momentum(df, period=10))

    # ── pane 0 无组：独立指标 ──
    bb_mid = chart.create_line('BB Mid 20', color='rgb(255, 255, 255)', width=1, style='dotted')
    bb_mid.set(calculate_sma(df, period=20))

    atr = chart.create_line('ATR 14', color='rgb(200, 200, 200)', width=1, pane_index=0)

    def calculate_atr(df, period=14):
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return pd.DataFrame({'time': df['time'], 'value': atr}).dropna()

    atr.set(calculate_atr(df, period=14))

    # ── OSC 组（pane 1）：振荡指标同一行 ──
    rsi = chart.create_line('RSI 14', color='rgb(200, 100, 255)', pane_index=1, group='OSC')
    rsi.set(calculate_rsi(df, period=14))

    stoch = chart.create_line('%K 14', color='rgb(255, 255, 100)', pane_index=1, group='OSC')
    stoch.set(calculate_stochastic(df))

    # ── pane 1 无组：独立指标 ──
    def calculate_williams_r(df, period=14):
        highest_high = df['high'].rolling(window=period).max()
        lowest_low = df['low'].rolling(window=period).min()
        wr = (highest_high - df['close']) / (highest_high - lowest_low) * -100
        return pd.DataFrame({'time': df['time'], 'value': wr}).dropna()

    wr = chart.create_line('Williams %R', color='rgb(100, 200, 255)', pane_index=1)
    wr.set(calculate_williams_r(df, period=14))

    def calculate_cci(df, period=20):
        tp = (df['high'] + df['low'] + df['close']) / 3
        sma_tp = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: abs(x - x.mean()).mean())
        cci = (tp - sma_tp) / (0.015 * mad)
        return pd.DataFrame({'time': df['time'], 'value': cci}).dropna()

    cci = chart.create_line('CCI 20', color='rgb(255, 150, 100)', pane_index=1)
    cci.set(calculate_cci(df, period=20))

    chart.show(wait=120)
    chart.exit()
