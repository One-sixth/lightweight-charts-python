# Subcharts

## Grid of 4

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    # setting position like matplotlib figure plot
    chart = Chart(position=221)
    chart2 = chart.create_subchart(position=222)
    chart3 = chart.create_subchart(position=223)
    chart4 = chart.create_subchart(position=224)

    chart.watermark('1')
    chart2.watermark('2')
    chart3.watermark('3')
    chart4.watermark('4')

    df = pd.read_csv('ohlcv.csv')
    chart.set(df)
    chart2.set(df)
    chart3.set(df)
    chart4.set(df)

    chart.show(block=True)

```
___

## Synced Charts

### Full Sync (Time Scale + Crosshair)

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart(inner_width=1, inner_height=0.8)
    chart.time_scale(visible=False)

    # 创建完全同步的子图表
    chart2 = chart.create_subchart(width=1, height=0.2, sync=True)
    line = chart2.create_line()
    
    df = pd.read_csv('ohlcv.csv')
    df2 = pd.read_csv('rsi.csv')

    chart.set(df)
    line.set(df2)

    chart.show(block=True)
```

### Crosshair Only Sync

```python
import pandas as pd
from lightweight_charts import Chart

if __name__ == '__main__':
    chart = Chart(width=1200, height=800)
    chart.legend(visible=True, persistent=True)

    df_main = pd.read_csv('ohlcv.csv')
    chart.set(df_main)

    # 创建仅同步十字光标的子图表（时间轴独立）
    subchart = chart.create_subchart(
        position=(2, 1, 2),
        sync=chart.id,
        sync_crosshairs_only=True
    )
    df_sub = pd.read_csv('another_ohlcv.csv')
    subchart.set(df_sub)

    chart.show(block=True)
```
___

## Grid of 4 with maximize buttons

```python
import pandas as pd
from lightweight_charts import Chart

# ascii symbols
FULLSCREEN = '■'
CLOSE = '×'


def on_max(target_chart):
    button = target_chart.topbar['max']
    if button.value == CLOSE:
        [c.resize(0.5, 0.5) for c in charts]
        button.set(FULLSCREEN)
    else:
        for chart in charts:
            width, height = (1, 1) if chart == target_chart else (0, 0)
            chart.resize(width, height)
        button.set(CLOSE)


if __name__ == '__main__':
    main_chart = Chart(inner_width=0.5, inner_height=0.5)
    charts = [
        main_chart,
        main_chart.create_subchart(position=(2, 2, 2), width=0.5, height=0.5),
        main_chart.create_subchart(position=(2, 2, 3), width=0.5, height=0.5),
        main_chart.create_subchart(position=(2, 2, 4), width=0.5, height=0.5),
    ]

    df = pd.read_csv('examples/1_setting_data/ohlcv.csv')
    for i, c in enumerate(charts):
        chart_number = str(i+1)
        c.watermark(chart_number)
        c.topbar.textbox('number', chart_number)
        c.topbar.button('max', FULLSCREEN, False, align='right', func=on_max)
        c.set(df)

    charts[0].show(block=True)
```
