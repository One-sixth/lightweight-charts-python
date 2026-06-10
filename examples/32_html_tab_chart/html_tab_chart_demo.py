"""
HtmlTabChart 功能演示 - Tab 切换式多策略回测结果展示

功能展示：
1. 多策略切换（侧边栏）
2. 交易明细展示（双击跳转）
3. 绩效指标展示
4. 策略参数展示
5. 技术指标（均线、布林带）
6. 买卖标记
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from lightweight_charts import HtmlTabChart


def generate_ohlcv_data(days=100):
    """生成模拟 OHLCV 数据"""
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    
    # 模拟价格走势
    np.random.seed(42)
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, days)
    prices = base_price * np.cumprod(1 + returns)
    
    # 生成 OHLCV
    data = []
    for i, date in enumerate(dates):
        open_price = prices[i] * (1 + np.random.uniform(-0.01, 0.01))
        high_price = max(open_price, prices[i]) * (1 + np.random.uniform(0, 0.02))
        low_price = min(open_price, prices[i]) * (1 - np.random.uniform(0, 0.02))
        close_price = prices[i]
        volume = np.random.randint(1000, 10000)
        
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
    """计算简单移动平均线"""
    return pd.DataFrame({
        'time': df['time'],
        f'SMA {period}': df['close'].rolling(window=period).mean()
    }).dropna()


def calculate_bollinger_bands(df, period=20, std_dev=2):
    """计算布林带"""
    sma = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    
    return pd.DataFrame({
        'time': df['time'],
        'BB Middle': sma,
        'BB Upper': sma + (std * std_dev),
        'BB Lower': sma - (std * std_dev)
    }).dropna()


def generate_trades(df, strategy_name):
    """生成模拟交易记录"""
    trades = []
    num_trades = np.random.randint(5, 15)
    
    for i in range(num_trades):
        # 随机选择开仓和平仓时间
        open_idx = np.random.randint(0, len(df) - 10)
        close_idx = np.random.randint(open_idx + 1, min(open_idx + 10, len(df)))
        
        # 随机方向
        is_long = np.random.random() > 0.5
        size = np.random.choice([1, 2, 5, 10]) * (1 if is_long else -1)
        
        open_price = df.iloc[open_idx]['open'] * (1 + np.random.uniform(-0.005, 0.005))
        close_price = df.iloc[close_idx]['close'] * (1 + np.random.uniform(-0.005, 0.005))
        
        # 计算盈亏
        pnl = (close_price - open_price) * size
        commission = abs(size) * 0.1
        pnlcomm = pnl - commission
        return_pct = pnlcomm / (abs(size) * open_price) * 100
        
        trades.append({
            'type': 0,  # 0=成交，1=订单
            'ref': f'{strategy_name}_{i+1:03d}',
            'size': int(size),
            'tradeid': f'T{i+1:04d}',
            'dateopen': str(df.iloc[open_idx]['time']),
            'priceopen': round(float(open_price), 2),
            'dateclose': str(df.iloc[close_idx]['time']),
            'priceclose': round(float(close_price), 2),
            'pnlcomm': round(float(pnlcomm), 2),
            'return_pct': round(float(return_pct), 2),
            'commission': round(float(commission), 2),
            'barlen': int(close_idx - open_idx)
        })
    
    return trades


def add_trade_markers(chart, trades):
    """根据交易记录添加买卖标记"""
    for trade in trades:
        # 开仓标记
        chart.marker(
            time=trade['dateopen'],
            position='below' if trade['size'] > 0 else 'above',
            color='red' if trade['size'] > 0 else 'green',
            shape='arrow_up' if trade['size'] > 0 else 'arrow_down',
            text=f"开仓 {trade['size']}手"
        )
        
        # 平仓标记
        chart.marker(
            time=trade['dateclose'],
            position='above' if trade['size'] > 0 else 'below',
            color='green' if trade['size'] > 0 else 'red',
            shape='arrow_down' if trade['size'] > 0 else 'arrow_up',
            text=f"平仓 {trade['pnlcomm']:.1f}"
        )


def generate_performance_metrics():
    """生成模拟绩效指标"""
    return pd.Series({
        '总收益率': f'{np.random.uniform(-10, 30):.2f}%',
        '年化收益率': f'{np.random.uniform(-5, 20):.2f}%',
        '最大回撤': f'{np.random.uniform(-15, -5):.2f}%',
        '夏普比率': f'{np.random.uniform(-0.5, 2.0):.2f}',
        '胜率': f'{np.random.uniform(40, 65):.1f}%',
        '盈亏比': f'{np.random.uniform(0.8, 2.5):.2f}',
        '交易次数': f'{np.random.randint(10, 50)}',
        '平均持仓天数': f'{np.random.uniform(1, 10):.1f}'
    })


def generate_parameters():
    """生成模拟策略参数"""
    return pd.Series({
        '均线周期': np.random.choice([5, 10, 20, 50]),
        '止损比例': f'{np.random.uniform(1, 5):.1f}%',
        '止盈比例': f'{np.random.uniform(3, 10):.1f}%',
        '仓位大小': np.random.choice([1, 2, 5, 10]),
        '最大持仓': np.random.choice([1, 3, 5])
    })


def demo():
    """演示 HtmlTabChart 功能"""
    print("🎯 HtmlTabChart 功能演示")
    print("=" * 50)
    
    # 生成模拟数据
    print("📊 生成模拟数据...")
    df = generate_ohlcv_data(100)
    
    # 创建图表
    chart = HtmlTabChart(
        width=1200, 
        height=800
    )
    
    # 启用图例
    chart.legend(visible=True)
    
    # ========== 策略1: 均线交叉策略 ==========
    print("📈 添加策略1: 均线交叉策略")
    chart.set_name('均线交叉策略')
    chart.set(df)
    
    # 添加均线指标
    sma10 = calculate_sma(df, period=10)
    sma20 = calculate_sma(df, period=20)
    sma50 = calculate_sma(df, period=50)
    
    line_sma10 = chart.create_line('SMA 10', color='blue', price_line=False, price_label=False)
    line_sma10.set(sma10)
    
    line_sma20 = chart.create_line('SMA 20', color='red', price_line=False, price_label=False)
    line_sma20.set(sma20)
    
    line_sma50 = chart.create_line('SMA 50', color='green', price_line=False, price_label=False)
    line_sma50.set(sma50)
    
    # 添加交易记录
    trades1 = generate_trades(df, 'MA_Cross')
    chart.set_trades(trades1)
    
    # 添加买卖标记
    add_trade_markers(chart, trades1)
    
    # 添加绩效指标
    perf1 = generate_performance_metrics()
    chart.set_performance_metrics(perf1, '均线交叉策略')
    
    # 添加策略参数
    params1 = generate_parameters()
    chart.set_parameters_list(params1)
    
    # 开始新策略窗口
    chart.new_window()
    
    # ========== 策略2: 布林带策略 ==========
    print("📈 添加策略2: 布林带策略")
    chart.set_name('布林带策略')
    chart.legend(visible=True)  # 新窗口需要重新设置图例
    chart.set(df)
    
    # 添加布林带指标
    bb = calculate_bollinger_bands(df, period=20, std_dev=2)
    
    line_bb_middle = chart.create_line('BB Middle', color='orange', price_line=False, price_label=False)
    line_bb_middle.set(bb[['time', 'BB Middle']])
    
    line_bb_upper = chart.create_line('BB Upper', color='red', price_line=False, price_label=False)
    line_bb_upper.set(bb[['time', 'BB Upper']])
    
    line_bb_lower = chart.create_line('BB Lower', color='green', price_line=False, price_label=False)
    line_bb_lower.set(bb[['time', 'BB Lower']])
    
    # 添加交易记录
    trades2 = generate_trades(df, 'Bollinger')
    chart.set_trades(trades2)
    
    # 添加买卖标记
    add_trade_markers(chart, trades2)
    
    # 添加绩效指标
    perf2 = generate_performance_metrics()
    chart.set_performance_metrics(perf2, '布林带策略')
    
    # 添加策略参数
    params2 = generate_parameters()
    chart.set_parameters_list(params2)
    
    # ========== 导出 HTML 文件 ==========
    print("💾 导出 HTML 文件...")
    filename = 'html_tab_chart_demo.html'
    chart.export(filename)

    # ========== 导出 iframe 嵌入测试页面（双文件方案） ==========
    #
    # 为什么需要两个文件？
    # 曾尝试过多种单文件方案，均存在无法解决的问题：
    #   - srcdoc：将 500K+ HTML 作为属性值内嵌，浏览器渲染时产生异常嵌套/重复层
    #   - data:base64 URI：null origin 导致 addEventListener 对 tab 切换失效
    #   - blob: URI：同 data URI，null origin 限制
    #   - Shadow DOM：模板使用 :root / html[data-theme] / document.documentElement，
    #     Shadow DOM 内不存在这些元素，CSS 变量和主题切换全部失效
    #   - innerHTML 直接插入：浏览器不执行 innerHTML 中的 <script> 标签
    #
    # 最终方案：外壳 HTML 文件 + 图表内容 HTML 文件，通过 <iframe src="..."> 引用。
    # 两个文件放在同一目录即可。
    #
    print("💾 导出 iframe 嵌入测试页面...")

    # 1. 图表内容文件
    chart_content_filename = 'html_tab_chart_iframe_content.html'
    with open(chart_content_filename, 'w', encoding='utf-8') as f:
        f.write(chart.get_html())

    # 2. 外壳文件，通过 src 引用图表内容
    iframe_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Iframe Embed Test</title>
    <style>
        body {{
            margin: 0; padding: 20px 30px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f0f2f5; color: #333;
        }}
        h1 {{ color: #1a73e8; margin-bottom: 8px; }}
        .desc {{
            color: #666; margin-bottom: 20px; line-height: 1.6;
        }}
        .desc code {{
            background: #e8eaed; padding: 2px 6px; border-radius: 3px;
            color: #c7254e; font-size: 13px;
        }}
        .chart-frame {{
            width: 100%; max-width: 1200px; height: 800px;
            border: 2px solid #ccc; border-radius: 8px; overflow: hidden;
            box-shadow: 0 2px 12px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <h1>Iframe Embed Test</h1>
    <p class="desc">
        The chart below is loaded via
        <code>&lt;iframe src="{chart_content_filename}"&gt;</code>.<br>
        Both files must be placed in the same directory.
    </p>
    <div class="chart-frame">
        <iframe src="{chart_content_filename}" style="width:100%;height:100%;border:none;" allowfullscreen></iframe>
    </div>
</body>
</html>'''
    iframe_filename = 'html_tab_chart_iframe_demo.html'
    with open(iframe_filename, 'w', encoding='utf-8') as f:
        f.write(iframe_html)

    print("=" * 50)
    print(f"✅ 演示完成！")
    print(f"📁 独立文件: {filename}")
    print(f"📁 iframe外壳: {iframe_filename}")
    print(f"📁 iframe内容: {chart_content_filename}")
    print(f"🌐 请在浏览器中打开 iframe 外壳文件查看效果")
    print()
    print("🔍 功能验证清单:")
    print("  1. 左侧策略切换 - 点击切换不同策略的K线图")
    print("  2. 技术指标 - 均线(SMA)和布林带(BB)")
    print("  3. 买卖标记 - 红色箭头做多，绿色箭头做空")
    print("  4. 交易记录表格 - 显示开仓/平仓详情")
    print("  5. 绩效指标面板 - 显示夏普比率、最大回撤等")
    print("  6. 策略参数面板 - 显示策略配置参数")
    print("  7. 双击跳转 - 双击交易记录中的日期跳转到K线位置")
    print("  8. 图例显示 - 左上角显示所有指标名称")
    print("  9. iframe嵌入 - 打开 iframe 测试文件验证嵌入渲染")


if __name__ == '__main__':
    demo()