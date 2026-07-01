# Lightweight Charts 功能对比文档

> 本文档对比官方库 `lightweight-charts` v5.2.0 与我们的库 `lightweight-charts-python` v2.8.6 的功能差异。
> 
> 生成日期：2026-07-01

---

## 📋 版本信息

| 属性 | 官方库 (lightweight-charts) | 我们的库 (lightweight-charts-python) |
|------|---------------------------|-------------------------------------|
| **版本号** | v5.2.0 | v2.8.6 |
| **技术栈** | TypeScript + Canvas | Python + TypeScript (WebView) |
| **许可证** | Apache-2.0 | MIT |
| **运行时依赖** | fancy-canvas@2.1.0 | pywebview |
| **源码位置** | `D:\Data\github_repo\lightweight-charts` | `D:\Data\github_repo\lightweight-charts-onesixth` |

---

## 📊 功能对比总览

### ✅ 已实现功能

| 功能类别 | 功能点 | 官方库 | 我们的库 | 备注 |
|---------|--------|--------|----------|------|
| **系列类型** | LineSeries (折线) | ✅ | ✅ | |
| | HistogramSeries (柱状图) | ✅ | ✅ | |
| | AreaSeries (面积图) | ✅ | ✅ | |
| | BaselineSeries (基准线) | ✅ | ✅ | |
| | BarSeries (美国线/OHLC) | ✅ | ✅ | 我们叫 OHLCBarSeries |
| | CandlestickSeries (K线) | ✅ | ✅ | 我们叫 CandleSeries |
| **图表核心** | resize() | ✅ | ✅ | |
| | screenshot() | ✅ | ✅ | |
| | addSeries() | ✅ | ✅ | 我们用 create_xxx_series() |
| | removeSeries() | ✅ | ✅ | 我们用 series.delete() |
| | subscribeClick() | ✅ | ✅ | 通过 Events 类 |
| | subscribeCrosshairMove() | ✅ | ✅ | 通过 Events 类 |
| **数据操作** | setData() | ✅ | ✅ | 我们用 set() |
| | update() | ✅ | ✅ | 我们用 update_bar() |
| | updateBars() | ✅ | ✅ | 我们用 update_bars() |
| | updateTicks() | ✅ | ✅ | 我们用 update_ticks() |
| **标记系统** | markers | ✅ | ✅ | |
| | SeriesMarkers 插件 | ✅ | ✅ | |
| **价格线** | createPriceLine() | ✅ | ✅ | |
| | removePriceLine() | ✅ | ✅ | |
| **绘图工具** | HorizontalLine | ✅ | ✅ | |
| | TrendLine | ✅ | ✅ | |
| | Box | ✅ | ✅ | |
| | VerticalLine | ✅ | ✅ | |
| | RayLine | ✅ | ✅ | |
| | VerticalSpan | ✅ | ✅ | |
| **Pane Primitive** | attachPrimitive() | ✅ | ✅ | 用于 DrawingSeries |
| | detachPrimitive() | ✅ | ✅ | |

---

### ❌ 缺失功能（官方库有，我们没有）

#### 🔴 **高优先级缺失**

| 功能 | 说明 | 实现难度 | 优先级 |
|------|------|----------|--------|
| **CustomSeries** | 用户可创建自定义系列类型，实现自定义渲染逻辑 | 高 | ⭐⭐⭐ |
| **applyOptions()** | 动态应用图表选项 | 中 | ⭐⭐⭐ |
| **options()** | 获取当前图表选项 | 中 | ⭐⭐⭐ |
| **remove()** | 删除图表对象 | 低 | ⭐⭐⭐ |
| **subscribeDblClick()** | 双击事件订阅 | 低 | ⭐⭐⭐ |

#### 🟡 **中优先级缺失**

| 功能 | 说明 | 实现难度 | 优先级 |
|------|------|----------|--------|
| **ITimeScaleApi** | 时间轴完整API | 中 | ⭐⭐ |
| | scrollPosition() | 低 | |
| | scrollToPosition() | 低 | |
| | scrollToRealTime() | 低 | |
| | getVisibleRange() | 中 | |
| | setVisibleRange() | 中 | |
| | getVisibleLogicalRange() | 中 | |
| | setVisibleLogicalRange() | 中 | |
| | subscribeVisibleLogicalRangeChange() | 中 | |
| | subscribeVisibleTimeRangeChange() | 中 | |
| | subscribeSizeChange() | 低 | |
| **IPriceScaleApi** | 价格轴完整API | 中 | ⭐⭐ |
| | width() | 低 | |
| | applyOptions() | 中 | |
| | options() | 中 | |
| | subscribeWidthChange() | 低 | |
| **本地化选项** | 多语言支持 | 中 | ⭐⭐ |
| **panes()** | 获取所有面板 | 低 | ⭐⭐ |

#### 🟢 **低优先级缺失**

| 功能 | 说明 | 实现难度 | 优先级 |
|------|------|----------|--------|
| **Series Primitive** | 完整的 ISeriesPrimitive 接口 | 高 | ⭐ |
| **自定义渲染器** | 用户自定义渲染逻辑 | 高 | ⭐ |
| **IPriceAxisView** | 价格轴标签视图接口 | 中 | ⭐ |
| **ITimeAxisView** | 时间轴标签视图接口 | 中 | ⭐ |

---

### 🌟 **我们独有的功能（官方库没有）**

#### 1. **扩展系列类型**

| 系列类型 | 说明 | 优势 |
|---------|------|------|
| **VolumeSeries** | 成交量系列 | 自动涨跌着色，基于 open/close |
| **OpenInterestSeries** | 持仓量系列 | 期货数据分析专用 |

#### 2. **UI 组件**

| 组件 | 说明 | 优势 |
|------|------|------|
| **TopBar** | 顶部工具栏 | 按钮、开关、菜单、文本控件 |
| **Table** | 表格组件 | 实时数据展示 |
| **ToolBox** | 绘图工具箱 | 支持跨 Pane 绘图，可自定义工具 |

#### 3. **绘图系统**

| 功能 | 说明 | 优势 |
|------|------|------|
| **DrawingSeries** | 基于 Pane Primitive 的绘图系列 | 更灵活的绘图管理 |
| **ToolBox 回调系统** | 绘图变更通知 | 支持自定义持久化逻辑 |
| **跨 Pane 绘图** | 工具固定在 Pane 0，但可在任意 Pane 绘图 | 更好的用户体验 |

#### 4. **多种图表实现**

| 实现 | 说明 | 优势 |
|------|------|------|
| **HtmlTabChart** | 多标签图表 | 单个 HTML 文件支持多个图表 |
| **ReflexChart** | Reflex 框架集成 | 支持 Reflex 前端框架 |
| **CrossProcessChart** | 跨进程图表 | 可嵌入 Qt 等桌面框架 |
| **PolygonChart** | Polygon.io API 集成 | 实时金融数据源 |

#### 5. **数据处理增强**

| 功能 | 说明 | 优势 |
|------|------|------|
| **set→update_bars 委托模式** | 高效的数据更新 | 首批用 setData，后续用 per-row update |
| **统一输入契约** | 所有系列接受相同列格式 | 简化 API，降低学习成本 |
| **VolumeSeries 自动着色** | 基于 open/close 自动着色 | 无需手动设置颜色 |
| **chart.data 属性** | 合并所有系列数据 | 方便获取完整数据 |

#### 6. **开发体验**

| 功能 | 说明 | 优势 |
|------|------|------|
| **AGENT.md** | Agent 操作指南 | AI 友好的开发文档 |
| **QUICK_REFERENCE.md** | 快查文档 | 1886 行完整 API 参考 |
| **MEMORY.md** | 项目长期记忆 | 记录所有决策和教训 |
| **40+ 示例** | 丰富的示例代码 | 快速上手 |
| **8 个测试套件** | 完整的测试覆盖 | 保证代码质量 |

---

## 📈 功能覆盖率分析

### 按类别统计

| 类别 | 官方库功能数 | 我们已实现 | 覆盖率 | 备注 |
|------|------------|-----------|--------|------|
| 系列类型 | 7 | 6 | 85.7% | 缺少 CustomSeries |
| 图表核心 API | 15 | 8 | 53.3% | 缺少 applyOptions/options 等 |
| 数据操作 | 5 | 5 | 100% | 完全覆盖 |
| 标记系统 | 3 | 3 | 100% | 完全覆盖 |
| 价格线 | 2 | 2 | 100% | 完全覆盖 |
| 绘图工具 | 6 | 6 | 100% | 完全覆盖 |
| 时间轴 API | 10 | 0 | 0% | 完全缺失 |
| 价格轴 API | 4 | 0 | 0% | 完全缺失 |
| Primitive 支持 | 4 | 1 | 25% | 只有 Pane Primitive |
| 事件系统 | 4 | 2 | 50% | 缺少 DblClick |

### 总体覆盖率

- **核心功能覆盖率**：~70%（高频使用的功能基本覆盖）
- **扩展功能覆盖率**：~30%（时间轴/价格轴/Primitive 缺失较多）
- **我们独有功能**：15+ 项

---

## 🎯 建议实现路径

### 第一阶段：基础 API 补全（1-2 周）

1. **applyOptions / options**
   - 实现图表选项的动态更新
   - 难度：中
   - 价值：高

2. **remove()**
   - 图表生命周期管理
   - 难度：低
   - 价值：高

3. **subscribeDblClick()**
   - 双击事件支持
   - 难度：低
   - 价值：中

### 第二阶段：时间轴/价格轴 API（2-3 周）

1. **ITimeScaleApi 实现**
   - scrollPosition / scrollToPosition
   - getVisibleRange / setVisibleRange
   - subscribeVisibleLogicalRangeChange
   - 难度：中
   - 价值：高

2. **IPriceScaleApi 实现**
   - width / applyOptions / options
   - subscribeWidthChange
   - 难度：中
   - 价值：中

### 第三阶段：高级扩展（4-6 周）

1. **CustomSeries 支持**
   - 实现 ICustomSeriesPaneView 接口
   - 提供 Python 端的自定义渲染 API
   - 难度：高
   - 价值：高（扩展性）

2. **Series Primitive 完整支持**
   - 实现 ISeriesPrimitive 接口
   - 支持自定义价格轴/时间轴视图
   - 难度：高
   - 价值：中

---

## 💡 设计建议

### 1. 保持 Pythonic 风格

官方库是 TypeScript API，我们的库应该保持 Pythonic 风格：

```python
# 官方库风格
chart.applyOptions({ layout: { background: { color: '#000' } } })

# 我们的风格（建议）
chart.apply_options(layout__background__color='#000')
# 或
chart.options(layout={'background': {'color': '#000'}})
```

### 2. 利用现有架构

我们的库已经有 `Window` 类作为 JS 桥接层，可以轻松添加新 API：

```python
# 在 Window 类中添加
def apply_options(self, options: dict):
    self.run_script(f'{self.id}.chart.applyOptions({js_json(options)})')

def options(self) -> dict:
    return self.run_script_and_get(f'JSON.stringify({self.id}.chart.options())')
```

### 3. 保持向后兼容

所有新 API 应该：
- 不破坏现有代码
- 提供合理的默认值
- 在文档中明确标注新增功能

---

## 📝 总结

### 我们的优势

1. **Python 生态集成**：Jupyter、Qt、HTML、Streamlit
2. **金融数据专用**：VolumeSeries、OpenInterestSeries
3. **交互式绘图**：ToolBox、DrawingSeries、跨 Pane 绘图
4. **多种部署方式**：桌面、Web、Notebook
5. **AI 友好文档**：AGENT.md、QUICK_REFERENCE.md、MEMORY.md

### 需要提升的方面

1. **API 完整性**：时间轴/价格轴 API 缺失
2. **扩展性**：CustomSeries、Series Primitive 支持不足
3. **动态配置**：applyOptions/options 缺失

### 核心价值主张

> **我们的库不是官方库的简单封装，而是针对 Python 生态和金融数据可视化的增强版本。**
> 
> 我们提供了官方库没有的功能（VolumeSeries、ToolBox、HtmlTabChart 等），同时保持了与官方库的核心兼容性。
> 
> 未来的方向是：**补齐缺失的 API，增强扩展性，同时保持我们的独特优势。**

---

*最后更新：2026-07-01 19:30*
