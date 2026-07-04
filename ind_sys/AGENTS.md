# ind_sys AGENTS.md

> 给未来 agent 的指引 — 纯数据指标系统子包

---

## 项目定位

**ind_sys** 是 lightweight-charts-onesixth 的纯数据指标系统子包（`ind_sys/`）。它提供声明式、扁平化、引用式的数据模型，与渲染层完全解耦。

---

## 核心架构

```
System (根容器)
├── Window[]      — 窗口（极简：name + display_name）
├── Chart[]       — 图表（interval 必选 + precision + position + xy + sync_id）
└── Series[]      — 数据系列（8种类型，全量属性，声明不带 data）
```

- 所有实体同级，通过名称引用关联
- 结构声明后不可变，只能改数据和属性
- Series 声明时**不带 data**，数据通过链式 API 设置

### 8 种 Series 类型

candle / ohlc_bar / line / area / baseline / histogram / volume / open_interest

---

## 当前状态（v0.3）

| 模块 | 状态 |
|------|------|
| 3 dataclass + build() + SystemLayout | ✅ |
| 链式 API（set/append/pop/add_marker） | ✅ |
| Adapter.render() → 主库 Chart | ✅（只处理首个 Window） |
| live 同步线程（互斥锁 + 0.1s检测） | ✅ |
| 冒烟测试 | ✅ |
| 示例 1_minimal | ✅ 简单（1Chart/2Pane） |
| 示例 2_demo | ✅ 复杂（2Window/5Chart/22Series） |
| Drawing / PriceLine / TopBar / Table | ⏳ 暂不实现 |
| 多 Window 渲染 | ⏳ 待实现 |
| 序列化 (JSON/YAML) | ⏳ 待实现 |

---

## 关键原则

### ⚠️ 同步线程是唯一的渲染通道
- **不允许直连渲染层**——所有数据更新必须通过 `sys_obj['name'].set/append/pop`
- 渲染由同步线程（`build(live=True)` 启动的守护线程）自动完成
- 同步线程检测频率 0.1 秒，数据更新可以更快（如 0.25 秒）
- 每个 series 有独立的 `threading.Lock`（`defaultdict` 管理），保护推送原子性

### append_data 是 replace-or-append
- 新数据首条 time == 已有最后一条 time → 替换最后一条 + 追加其余
- 否则 → 纯追加
- 不会影响除最后一条外的任何已有数据

### 使用 chart.show(block=True)
- `block=True` 阻塞直到用户关闭窗口，同步线程在此期间持续工作
- `block=False`（默认）会立即返回，随后 `stop_sync()` 会杀死同步线程

### Series 版本号追踪
- `set/append/pop/add_marker` 都会递增对应 series 的 `_series_versions[name]`
- 同步线程通过比较版本号定位变化，只同步有变化的 series

---

## 文件索引

| 文件 | 说明 |
|------|------|
| `models.py` | System/Window/Chart/Series + SystemLayout + SeriesAccessor + parse_interval |
| `adapter.py` | Adapter.render() + _series_kwargs() |
| `IND_SYS_DESIGN.md` | 设计文档 v0.3 |
| `IND_SYS_NEXT_STEPS.md` | 下一步指南 |
| `MEMORY.md` | 子系统专属记忆（含完整 API 参考） |
| `examples/1_minimal/minimal.py` | 最小示例 |
| `examples/2_demo/demo.py` | 复杂示例 |
| `tests/smoke_test.py` | 冒烟测试 |

---

## 改代码前必读

1. **先读 MEMORY.md** — 了解当前状态和设计决策
2. **同步线程修改要谨慎** — 确保 `_series_locks` 正确使用
3. **新增 Series 类型** — 需在 `adapter.py` 的 `_FACTORY` 和 `_series_kwargs` 中注册
4. **修改 append_data** — 保持 replace-or-append 语义
5. **冒烟测试** — 修改后必须跑 `python -m ind_sys.tests.smoke_test`

---

*泰斗先生 × 小音，2026-07-04*