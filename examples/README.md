# 示例目录说明

本目录包含 lightweight-charts-python 的示例代码，编号 1-30。

## 编号说明

| 编号 | 目录名 | 功能说明                                                            | 状态     |
|------|--------|-----------------------------------------------------------------|--------|
| 1 | `1_setting_data` | 基础：从 CSV 读取并显示 K 线                                              | ✅ 已实现  |
| 2 | `2_live_data` | 实时更新：逐条更新 K 线 + 价格标记                                            | ✅ 已实现  |
| 3 | `3_tick_data` | Tick 数据：从逐笔成交更新 K 线                                             | ✅ 已实现  |
| 4 | `4_line_indicators` | 折线指标：SMA 叠加到 K 线图                                               | ✅ 已实现  |
| 5 | `5_styling` | 样式定制：背景色/十字光标/水印/图例                                             | ✅ 已实现  |
| 6 | `6_callbacks` | 事件回调：搜索 + 时间切换 + 水平线移动                                          | ✅ 已实现  |
| 7 | `7_multi_pane` | 多面板：K线 + 多个子面板叠加指标                                              | ✅ 已实现  |
| 8 | `8_volume_open_interest` | 成交量 + 持仓量叠加，独立缩放                                                | ✅ 已实现  |
| 9 | `9_multi_chart` | 多 Chart 实例同时运行                                                  | ✅ 已实现  |
| 10 | `10_persistent_legend` | OHLC 常驻 + 简写开关示例                                                | ✅ 已实现  |
| 11 | `11_vertical_span` | 区域高亮：两日期区间 + 多点标记                                               | ✅ 已实现  |
| 12 | `12_audit` | 资源审计：展示 Python/JS 侧审计用法                                         | ✅ 已实现  |
| 13 | `13_batch_update` | 批量增量更新：`update_bars()` + `update_from_ticks()`                  | ✅ 已实现  |
| 14 | `14_set_period` | 锁定时间级别：`set_period()` 演示                                        | ✅ 已实现  |
| 15 | `15_pyside6_simple` | PySide6 + QtChart 嵌入测试                                          | ✅ 已实现  |
| 16 | `16_pyside6_race` | PySide6 速度赛跑：update vs update_bars vs set 对比                    | ✅ 已实现  |
| 17 | `17_v520_new_features` | v5.2.0 新特性集中示例，已拆开，分散到后面的示例中                        | ⚠️ 已删除 |
| 18 | `18_hovered_series_on_top` | `hovered_series_on_top` — 鼠标悬停时系列是否浮到顶层                 | ✅ 已实现  |
| 19 | `19_timescale_options` | `time_scale()` 新参数 — 像素偏移 / 数据合并 (conflation)                   | ✅ 已实现  |
| 20 | `20_tick_mark_density` | `tick_mark_density` — 价格轴标签密度控制 (1.0 / 2.5 / 6.0)               | ✅ 已实现  |
| 21 | `21_marker_auto_scale` | `marker_auto_scale()` — 标记是否参与价格轴自动缩放                           | ✅ 已实现  |
| 22 | `22_pop` | `pop(n)` — 从末尾移除 N 根 K 线                                        | ✅ 已实现  |
| 23 | `23_crosshair_move` | `events.crosshair_move` — 鼠标悬停实时回调 (Hit Testing)                | ✅ 已实现  |
| 24 | `24_price_format` | `set_price_format(type='base')` — 基础价格格式，避免浮点精度问题               | ✅ 已实现  |
| 25 | `25_screenshot_enhanced` | `screenshot(add_top_layer=True, include_crosshair=True)` — 增强截图 | ✅ 已实现  |
| 26 | `26_series_batch_update` | 系列批量更新：`update_batch()` 用于 Line 和 Histogram 系列 | ✅ 已实现  |
| 27 | `27_reflex_chart` | Reflex 嵌入：实时 bar 推送 + crosshair 回调 (postMessage 桥接) | ✅ 已实现  |
| 28 | `28_cross_process_chart` | CrossProcessChart：跨进程嵌入 PySide6 QWidget | ✅ 已实现  |
| 29 | `29_grid_layout` | 网格布局：position 参数三种格式 + get_position/set_position | ✅ 已实现  |
| 30 | `30_table_component` | 表格组件：自选股列表 + 持仓管理 + 动态更新 + 多表格布局 | ✅ 已实现  |
| 31 | `31_chart_sync` | 图表同步：`sync_id` 参数实现多图表时间轴和十字光标同步 | ✅ 已实现  |
| 32 | `32_html_tab_chart` | HtmlTabChart 功能演示：Tab切换多策略、交易明细、绩效指标 | ✅ 已实现  |
| 33 | `33_reset_sub` | reset_sub 子图内容重置：清空+重填+同步恢复+独立子图 | ✅ 已实现  |
