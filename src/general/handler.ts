import {
    ColorType,
    CrosshairMode,
    DeepPartial,
    HistogramStyleOptions,
    IChartApi,
    ISeriesApi,
    LineStyleOptions,
    LogicalRange,
    MouseEventParams,
    SeriesOptionsCommon,
    SeriesType,
    createChart,
    CandlestickSeries,
    HistogramSeries,
    LineSeries,
    createTextWatermark,
} from "lightweight-charts";

import { GlobalParams, globalParamInit } from "./global-params";
import { Legend } from "./legend";
import { ToolBox } from "./toolbox";
import { TopBar } from "./topbar";


export interface Scale {
    width: number;
    height: number;
}


globalParamInit();
declare const window: GlobalParams;

export class Handler {
    public static _all: Handler[] = [];

    public static audit(): string {
        const lines: string[] = [];

        const q = (s: string) => `"${s.replace(/"/g, '\\"')}"`;  // TOML-safe quote

        const safeSection = (s: string): string =>
            s.replace(/^window\./, 'handler_').replace(/[^a-zA-Z0-9_.]/g, '_');

        const safeKey = (s: string): string => {
            if (/^[a-zA-Z_][a-zA-Z0-9_.]*$/.test(s)) return s;
            return `"${s.replace(/"/g, '\\"')}"`;
        };

        const dumpObj = (obj: any, prefix: string, depth: number, skipKeys?: Set<string>): string[] => {
            const res: string[] = [];
            if (depth > 2 || obj === null || obj === undefined) return res;
            if (typeof obj !== 'object' || Array.isArray(obj)) return res;
            for (const k of Object.keys(obj)) {
                if (k === 'id') continue;
                if (skipKeys?.has(k)) continue;
                const val = obj[k];
                const vt = typeof val;
                const fullKey = prefix ? `${prefix}.${safeKey(k)}` : safeKey(k);
                if (vt === 'string' || vt === 'number' || vt === 'boolean') {
                    res.push(`${fullKey} = ${vt === 'string' ? q(String(val)) : String(val)}`);
                } else if (vt === 'object' && val !== null && !Array.isArray(val)) {
                    // try one level deeper
                    const inner = dumpObj(val, fullKey, depth + 1, skipKeys);
                    if (inner.length > 0) {
                        res.push(...inner);
                    } else {
                        res.push(`${fullKey} = "(object)"`);
                    }
                }
                // skip arrays and functions
            }
            return res;
        };

        // Keys to skip in generic recursive dump (noisy API objects / DOM / internal)
        const SKIP_KEYS = new Set([
            'series', 'volumeSeries', 'openInterestSeries', 'chart',
            'wrapper', 'div', 'legend', 'toolBox', '_topBar',
            '_seriesList', 'commandFunctions',
            'reSize', '_createChart',
            'createLineSeries', 'createHistogramSeries', 'createCandleSeries', '_styleMap',
        ]);

        // Regex matching our custom window global variable names
        const GLOBALS_RE = /^(window\.|Chart_\d|Line_\d|Histogram_\d|CandleSeries_\d|VolumeSeries_\d|OpenInterestSeries_\d|PriceLine_\d|HorizontalLine_\d|VerticalLine_\d|TrendLine_\d|Box_\d|RayLine_\d|VerticalSpan_\d|AbstractChart_\d|Table_\d|Marker_\d|Drawing_\d)/;

        // Build a lookup: handler ID → Handler instance
        const handlerMap: Record<string, Handler> = {};
        for (const h of Handler._all) {
            handlerMap[h.id] = h;
        }

        // Helper: output handler-specific detail lines (API calls)
        const dumpHandlerDetail = (h: Handler, lines: string[]) => {
            // — generic recursive dump (2 levels deep, skipping noisy keys) —
            const dumped = dumpObj(h, '', 0, SKIP_KEYS);
            if (dumped.length > 0) lines.push(...dumped);

            // — presence flags for complex objects that were skipped —
            lines.push(`hasChart = ${!!h.chart}`);
            lines.push(`hasSeries = ${!!h.series}`);
            lines.push(`hasVolumeSeries = ${!!h.volumeSeries}`);
            lines.push(`hasOpenInterest = ${!!h.openInterestSeries}`);
            lines.push(`hasLegend = ${!!h.legend}`);
            lines.push(`hasToolBox = ${!!h.toolBox}`);
            lines.push(`hasTopBar = ${!!h._topBar}`);

            // — extra series (Line / Histogram) —
            for (let i = 0; i < h._seriesList.length; i++) {
                const s = h._seriesList[i];
                const prefix = `extraSeries.${i}`;
                try {
                    const opts = s.options() as any;
                    lines.push(`${prefix}.type = ${q(s.seriesType())}`);
                    if (opts.color) lines.push(`${prefix}.color = ${q(opts.color)}`);
                    if (opts.lineWidth) lines.push(`${prefix}.lineWidth = ${opts.lineWidth}`);
                    const dataLen = s.data().length;
                    if (dataLen >= 0) lines.push(`${prefix}.dataPoints = ${dataLen}`);
                } catch (_) {
                    lines.push(`${prefix}.type = ${q(s.seriesType())}`);
                }
            }

            // — volume series —
            if (h.volumeSeries) {
                try {
                    const volLen = h.volumeSeries.data().length;
                    if (volLen >= 0) lines.push(`volume.dataPoints = ${volLen}`);
                } catch (_) {}
            }

            // — open interest series —
            if (h.openInterestSeries) {
                try {
                    const opts = h.openInterestSeries.options() as any;
                    if (opts.color) lines.push(`openInterest.color = ${q(opts.color)}`);
                    const oiLen = h.openInterestSeries.data().length;
                    if (oiLen >= 0) lines.push(`openInterest.dataPoints = ${oiLen}`);
                } catch (_) {}
            }

            // — legend —
            if (h.legend) {
                lines.push(`legendVisible = ${h.legend.div?.style?.display !== 'none'}`);
                lines.push(`legendPersistent = ${!!(h.legend as any).persistent}`);
                lines.push(`legendShorthand = ${!!(h.legend as any).shorthand}`);
                if (h.legend?._lines) {
                    for (let i = 0; i < h.legend._lines.length; i++) {
                        const r = h.legend._lines[i];
                        const lp = `legendRow.${i}`;
                        lines.push(`${lp}.name = ${q(r.name ?? '')}`);
                        lines.push(`${lp}.color = ${q((r as any).color ?? '')}`);
                        if ((r as any).paneIndex !== undefined) {
                            lines.push(`${lp}.paneIndex = ${(r as any).paneIndex}`);
                        }
                    }
                }
            }

            // — candles & data —
            if (h.series) {
                try {
                    const candleLen = h.series.data().length;
                    if (candleLen >= 0) lines.push(`candleDataPoints = ${candleLen}`);
                } catch (_) {}
            }

            // — watermark —
            if (h.watermark) lines.push(`hasWatermark = true`);

            // — extra series count —
            lines.push(`extraSeriesCount = ${h._seriesList.length}`);
        };

        // — Single pass: iterate window globals, merge handler + non-handler —
        for (const key of Object.keys(window)) {
            if (!GLOBALS_RE.test(key)) continue;
            const v = (window as any)[key];
            if (v === null || v === undefined) continue;

            const section = safeSection(key);
            lines.push(`[${section}]`);
            lines.push(`id = ${q(key)}`);

            // Check if this window global is a Handler instance
            const handler = handlerMap[key] || handlerMap[`window.${key}`];
            if (handler) {
                lines.push(`type = ${q('Handler')}`);
                dumpHandlerDetail(handler, lines);
            } else {
                const typ = Array.isArray(v) ? 'array' : typeof v;
                lines.push(`type = ${q(typ)}`);
                if (typeof v === 'object' && v !== null && !Array.isArray(v)) {
                    const inner = dumpObj(v, '', 0);
                    if (inner.length > 0) lines.push(...inner);
                }
            }
        }

        return lines.join('\n');
    }

    public static removeFromSeriesList(handlerId: string, seriesWrapper: any): void {
        const h = Handler._all.find(h => h.id === handlerId);
        if (h) {
            // seriesWrapper is { name, series } — look up by .series reference
            const idx = h._seriesList.indexOf(seriesWrapper.series);
            if (idx >= 0) h._seriesList.splice(idx, 1);
        }
    }

    public static removeHandlerFromAll(handlerId: string): void {
        const idx = Handler._all.findIndex(h => h.id === handlerId);
        if (idx >= 0) Handler._all.splice(idx, 1);
    }

    public id: string;
    public commandFunctions: Function[] = [];

    public wrapper: HTMLDivElement;
    public div: HTMLDivElement;

    public chart: IChartApi;
    public scale: Scale;
    public precision: number = 2;

    public series: ISeriesApi<SeriesType> | null = null;
    public volumeSeries: ISeriesApi<SeriesType> | null = null;
    public openInterestSeries: ISeriesApi<SeriesType> | null = null;
    public _interval: number = 86400;

    public legend: Legend;
    private _topBar: TopBar | undefined;
    public toolBox: ToolBox | undefined;
    public spinner: HTMLDivElement | undefined;

    public _seriesList: ISeriesApi<SeriesType>[] = [];
    private resize_hdr_height: number = 8;
    public watermark: any;

    // syncCharts 同步追踪
    public _syncedHandlers: string[] = [];
    public _syncCallbacks: Record<string, {
        crosshair?: (param: MouseEventParams) => void,
        range?: (range: LogicalRange | null) => void,
        crosshairSource?: Handler,
        rangeSource?: Handler,
    }> = {};
    // 组同步：sync_id 作为组名
    public _syncGroup: string = '';
    public _syncCrosshairOnly: boolean = false;
    // 重入守卫：防止 crosshair 同步回调级联触发
    public _inSync: boolean = false;
    // range 同步守卫：防止 range 回调级联 + 冗余更新
    public _inRangeSync: boolean = false;
    public _lastSyncedRange: string = '';
    private gridPosition: { row: number; col: number } | null = null;
    private gridDimensions: { nrows: number; ncols: number } | null = null;
    private isGridLayout: boolean = false;
    private customPosition: { x: number; y: number; width: number; height: number } | null = null;
    private _originalHeight: string | null = null;

    constructor(
        chartId: string,
        innerWidth: number,
        innerHeight: number,
        nrows: number,
        ncols: number,
        index: number,
        autoSize: boolean
    ) {
        this.reSize = this.reSize.bind(this)

        this.id = chartId
        this.scale = {
            width: innerWidth,
            height: innerHeight,
        }

        this.wrapper = document.createElement('div')
        this.wrapper.classList.add("handler");
        
        // 设置网格布局
        this.setupGridLayout(nrows, ncols, index, innerWidth, innerHeight)
        this.isGridLayout = true

        this.div = document.createElement('div')
        this.div.style.position = 'relative'

        this.wrapper.appendChild(this.div);
        window.containerDiv.append(this.wrapper)

        // --- add this block to enable mouse‐drag height resizing ---
        const handle = document.createElement('div');
        handle.classList.add('resize-handle');
        this.wrapper.appendChild(handle);

        let startY= 0, startHeight = 0;
        const onMouseMove = (e: any) => {
          const delta = e.clientY - startY;
          const newH = Math.max(50, startHeight + delta); // min height 50px
          this.wrapper.style.height = `${newH}px`;
          // Resize the chart canvas accordingly (subtract topbar height like reSize does):
          const topBarOffset = this._topBar?._div.offsetHeight || 0;
          this.chart.resize(this.wrapper.offsetWidth, newH - topBarOffset - this.resize_hdr_height);
        };
        const onMouseUp = () => {
          document.removeEventListener('mousemove', onMouseMove);
          document.removeEventListener('mouseup', onMouseUp);
        };
        handle.addEventListener('mousedown', (e) => {
          // prevent selecting text, etc.
          e.preventDefault();
          // 首次拖拽时备份原始 height 值
          if (this._originalHeight === null) {
            this._originalHeight = this.wrapper.style.height || '';
          }
          startY = e.clientY;
          startHeight = this.wrapper.getBoundingClientRect().height;
          document.addEventListener('mousemove', onMouseMove);
          document.addEventListener('mouseup', onMouseUp);
        });

        // 双击操作柄：从备份恢复原始高度
        handle.addEventListener('dblclick', () => {
          if (this._originalHeight !== null) {
            // 恢复备份的原始高度，然后清除备份
            this.wrapper.style.height = this._originalHeight;
            this._originalHeight = null;
          }
          // 等浏览器重排后，按实际尺寸 resize chart
          requestAnimationFrame(() => this.reSize());
        });

        this.chart = this._createChart();
        this.series = null;
        this.volumeSeries = null;
        this.openInterestSeries = null;

        this.legend = new Legend(this)

        Handler._all.push(this);

        document.addEventListener('keydown', (event) => {
            for (let i = 0; i < this.commandFunctions.length; i++) {
                if (this.commandFunctions[i](event)) break
            }
        })
        window.handlerInFocus = this.id;
        this.wrapper.addEventListener('mouseover', () => window.handlerInFocus = this.id)

        this.reSize()
        if (!autoSize) return
        window.addEventListener('resize', () => this.reSize())
    }

    private setupGridLayout(nrows: number, ncols: number, index: number, 
                            widthRatio: number, heightRatio: number) {
        const container = window.containerDiv
        
        // 如果有自定义位置，跳过网格布局设置
        if (this.customPosition) {
            return
        }
        
        // 设置容器为 CSS Grid（仅在未设置时）
        if (!container.style.display || container.style.display !== 'grid') {
            container.style.display = 'grid'
            container.style.width = '100%'
            container.style.height = '100%'
        }
        // 只有当新模板与现有模板兼容时才更新
        const newCols = `repeat(${ncols}, 1fr)`
        const newRows = `repeat(${nrows}, 1fr)`
        if (!container.style.gridTemplateColumns || container.style.gridTemplateColumns === newCols) {
            container.style.gridTemplateColumns = newCols
        }
        if (!container.style.gridTemplateRows || container.style.gridTemplateRows === newRows) {
            container.style.gridTemplateRows = newRows
        }
        
        // 计算网格位置
        const row = Math.floor((index - 1) / ncols)
        const col = (index - 1) % ncols
        this.gridPosition = { row: row + 1, col: col + 1 }
        this.gridDimensions = { nrows, ncols }
        
        // 设置网格位置
        this.wrapper.style.gridRow = `${row + 1}`
        this.wrapper.style.gridColumn = `${col + 1}`
        
        // 关键：确保 Grid 子元素能正确缩小
        // min-width/min-height: 0 允许元素缩小到比内容更小
        this.wrapper.style.minWidth = '0'
        this.wrapper.style.minHeight = '0'
        // overflow: hidden 确保内容不溢出
        this.wrapper.style.overflow = 'hidden'
        // 确保占满网格单元（使用 width/height: 100% 而不是 auto）
        this.wrapper.style.width = '100%'
        this.wrapper.style.height = '100%'
        
        // 应用宽度和高度比例（相对于网格单元）
        // widthRatio/heightRatio = 1.0 表示占满网格单元
        // < 1.0 表示向内缩（对齐左上角），> 1.0 表示侵占其他网格
        if (widthRatio !== 1.0 || heightRatio !== 1.0) {
            this.wrapper.style.width = `${widthRatio * 100}%`
            this.wrapper.style.height = `${heightRatio * 100}%`
            // 对齐左上角
            this.wrapper.style.alignSelf = 'start'
            this.wrapper.style.justifySelf = 'start'
        }
        
        // 确保不使用 float
        this.wrapper.style.float = 'none'
    }

    getPosition(): { x: number; y: number; width: number; height: number } {
        const rect = this.wrapper.getBoundingClientRect()
        const containerRect = window.containerDiv.getBoundingClientRect()
        
        return {
            x: (rect.left - containerRect.left) / containerRect.width,
            y: (rect.top - containerRect.top) / containerRect.height,
            width: rect.width / containerRect.width,
            height: rect.height / containerRect.height
        }
    }

    setPosition(x: number | null, y: number | null, width: number | null, height: number | null) {
        // 计算网格默认值
        const getDefaultPosition = () => {
            if (this.gridPosition && this.gridDimensions) {
                return {
                    x: (this.gridPosition.col - 1) / this.gridDimensions.ncols,
                    y: (this.gridPosition.row - 1) / this.gridDimensions.nrows,
                    width: 1.0,
                    height: 1.0
                }
            }
            return { x: 0, y: 0, width: 1.0, height: 1.0 }
        }

        // 计算 topbar 高度偏移（与 reSize 保持一致）
        let topBarOffset = this.scale.height !== 0 ? this._topBar?._div.offsetHeight || 0 : 0
        
        // 如果全部为 null，恢复默认网格位置并退出绝对定位模式
        if (x === null && y === null && width === null && height === null) {
            this.customPosition = null
            const defaults = getDefaultPosition()
            
            // 恢复网格定位
            this.wrapper.style.position = ''
            this.wrapper.style.left = ''
            this.wrapper.style.top = ''
            this.wrapper.style.width = `${defaults.width * 100}%`
            this.wrapper.style.height = `${defaults.height * 100}%`
            this.wrapper.style.alignSelf = ''
            this.wrapper.style.justifySelf = ''
            
            // 恢复 gridRow/gridColumn
            if (this.gridPosition) {
                this.wrapper.style.gridRow = `${this.gridPosition.row}`
                this.wrapper.style.gridColumn = `${this.gridPosition.col}`
            }
            
            // 调整图表大小
            const rect = this.wrapper.getBoundingClientRect()
            this.chart.resize(rect.width, rect.height - topBarOffset - this.resize_hdr_height)
            return
        }
        
        // 合并默认值：null 参数使用默认值
        const defaults = getDefaultPosition()
        const finalX = x !== null ? x : defaults.x
        const finalY = y !== null ? y : defaults.y
        const finalWidth = width !== null ? width : defaults.width
        const finalHeight = height !== null ? height : defaults.height
        
        this.customPosition = { x: finalX, y: finalY, width: finalWidth, height: finalHeight }
        
        // 切换到绝对定位模式
        this.wrapper.style.position = 'absolute'
        this.wrapper.style.float = 'none'
        this.wrapper.style.gridRow = 'auto'
        this.wrapper.style.gridColumn = 'auto'
        
        // 设置位置和尺寸
        this.wrapper.style.left = `${finalX * 100}%`
        this.wrapper.style.top = `${finalY * 100}%`
        this.wrapper.style.width = `${finalWidth * 100}%`
        this.wrapper.style.height = `${finalHeight * 100}%`
        
        // 调整图表大小
        this.chart.resize(
            this.wrapper.offsetWidth,
            this.wrapper.offsetHeight - topBarOffset - this.resize_hdr_height
        )
    }


    reSize() {
      let topBarOffset = this.scale.height !== 0 ? this._topBar?._div.offsetHeight || 0 : 0
      
      // 如果有自定义位置（setPosition），只调整图表大小，不覆盖自定义位置
      if (this.customPosition) {
          const rect = this.wrapper.getBoundingClientRect()
          this.chart.resize(rect.width, rect.height - topBarOffset - this.resize_hdr_height)
          return
      }
      
      // 检测是否为 HtmlTabChart（通过检查专用标记）
      const isHtmlTabChart = document.getElementById('html-tab-chart-marker') !== null
      
      // 网格模式下
      if (this.isGridLayout) {
          // 统一使用 wrapper 实际尺寸，由 CSS Grid 管理行高
          const rect = this.wrapper.getBoundingClientRect()
          this.chart.resize(rect.width, rect.height - topBarOffset - this.resize_hdr_height)
          return
      }
      
      // 非网格模式
      if (this.scale.height >= 0) {
          if (isHtmlTabChart) {
              // HtmlTabChart: 动态获取导航栏高度
              const navEl = document.querySelector('nav')
              const navHeight = navEl ? navEl.offsetHeight : 45
              const availableHeight = window.innerHeight - navHeight
              this.chart.resize(window.innerWidth * this.scale.width, (availableHeight * this.scale.height) - topBarOffset - this.resize_hdr_height)
              this.wrapper.style.width = `${100 * this.scale.width}%`
              this.wrapper.style.height = `${100 * this.scale.height}%`
          } else {
              // 普通模式：使用原来的高度计算
              this.chart.resize(window.innerWidth * this.scale.width, (window.innerHeight * this.scale.height) - topBarOffset - this.resize_hdr_height)
              this.wrapper.style.width = `${100 * this.scale.width}%`
              this.wrapper.style.height = `${100 * this.scale.height}%`
          }
      } else {
          // 负高度模式：使用绝对像素值
          var chart_height: number = Math.ceil(Math.abs(this.scale.height));
          this.chart.resize(window.containerDiv.offsetWidth * this.scale.width, chart_height - topBarOffset - this.resize_hdr_height)
          this.wrapper.style.width = `${100 * this.scale.width}%`
          this.wrapper.style.height = `${chart_height}px`
      }

        // Hide toolbox when chart has zero dimensions (e.g., hidden subchart)
        if (this.scale.height === 0 || this.scale.width === 0) {
            // if (this.legend.div.style.display == 'flex') this.legend.div.style.display = 'none'
            if (this.toolBox) {
                this.toolBox.div.style.display = 'none'
            }
        }
        else {
            // this.legend.div.style.display = 'flex'
            if (this.toolBox) {
                this.toolBox.div.style.display = 'flex'
            }
        }
    }

    private _createChart() {
        let chartHeight: number
        if (this.scale.height < 0) {
            chartHeight = Math.ceil(Math.abs(this.scale.height))
        } else {
            const navEl = document.querySelector('nav')
            const navHeight = navEl ? navEl.offsetHeight : 0
            chartHeight = (window.innerHeight - navHeight) * this.scale.height
        }
        return createChart(this.div, {
      width: window.containerDiv.offsetWidth * this.scale.width,
      height: chartHeight,
      layout: {
        textColor: window.pane.color,
        background: {
          color: 'rgb(18,24,38)',
          type: ColorType.Solid,
        },
        fontSize: 12,
        panes: {
          separatorColor: 'lightgrey',
          separatorHoverColor: "rgba(255, 0, 0, 0.4)",
          enableResize: true,
        },
      },
      rightPriceScale: {
        scaleMargins: { top: 0.3, bottom: 0.25 },
      },
      timeScale: { timeVisible: true, secondsVisible: false },
      localization: {
        timeFormatter: (time: number) => {
          const d = new Date(time * 1000);
          const pad = (n: number) => n.toString().padStart(2, '0');
          const dateStr = `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`;
          if (this._interval >= 86400) return dateStr;
          return `${dateStr} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
        },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          labelBackgroundColor: 'rgb(46, 46, 46)',
        },
        horzLine: {
          labelBackgroundColor: 'rgb(55, 55, 55)',
        },
      },
      grid: {
        vertLines: { color: '#444', style:1 },
        horzLines: { color: '#444', style:1 },
      },
      handleScroll: { vertTouchDrag: true },
    });
  }

    /**
     * 创建折线系列。
     *
     * @param name - 系列名称，显示在图例中
     * @param options - 折线样式配置（颜色、线宽等）
     * @param paneIndex - 面板索引，0 = 与主 K 线同面板，>0 = 独立面板
     * @param dontAddList - 是否跳过 _seriesList 注册和 legend 图例行创建。
     *   默认 false（加入列表 + 创建图例行）。
     *   设为 true 时：
     *   - 不进入 _seriesList（audit 的 extraSeriesCount 不计入）
     *   - 不创建 legend 图例行（不会显示独立的颜色方块图例）
     *   适用场景：主图表的持仓量（OpenInterest）系列。
     *   它是图表的固有组件，生命周期由 AbstractChart 管理，
     *   不应被视为"额外系列"，也不应在 legend 中显示独立条目。
     *   持仓量数据通过 legendHandler 在 OHLC 文本中显示。
     */
    createLineSeries(name: string, options: DeepPartial<LineStyleOptions & SeriesOptionsCommon>, paneIndex: number = 0, dontAddList: boolean = false)
    {
        const line = this.chart.addSeries(LineSeries, {...options}, paneIndex);
        if (!dontAddList) {
            this._seriesList.push(line);
            this.legend.makeSeriesRow(name, line, paneIndex);
        }

        return {
            name: name,
            series: line,
        }
    }

    /**
     * 创建柱状图系列。
     *
     * @param name - 系列名称，显示在图例中
     * @param options - 柱状图样式配置（颜色、价格格式等）
     * @param paneIndex - 面板索引，0 = 与主 K 线同面板，>0 = 独立面板
     * @param dontAddList - 是否跳过 _seriesList 注册和 legend 图例行创建。
     *   默认 false（加入列表 + 创建图例行）。
     *   设为 true 时：
     *   - 不进入 _seriesList（audit 的 extraSeriesCount 不计入）
     *   - 不创建 legend 图例行（不会显示独立的颜色方块图例）
     *   适用场景：主图表的成交量（Volume）系列。
     *   它是图表的固有组件，生命周期由 AbstractChart 管理，
     *   不应被视为"额外系列"，也不应在 legend 中显示独立条目。
     *   成交量数据通过 legendHandler 在 OHLC 文本中显示。
     */
    createHistogramSeries(name: string, options: DeepPartial<HistogramStyleOptions & SeriesOptionsCommon>, paneIndex: number = 0, dontAddList: boolean = false)
    {
        const line = this.chart.addSeries(
            HistogramSeries,
            { ...options },
            paneIndex
        );
        if (!dontAddList) {
            this._seriesList.push(line);
            this.legend.makeSeriesRow(name, line, paneIndex);
        }
        return {
            name: name,
            series: line,
        };
    }

    /**
     * 创建独立 K 线系列。
     *
     * @param name - 系列名称，显示在图例中
     * @param options - K 线样式配置（颜色等）
     * @param paneIndex - 面板索引，0 = 与主 K 线同面板，>0 = 独立面板
     * @param dontAddList - 是否跳过 _seriesList 注册和 legend 图例行创建。
     *   默认 false（加入列表 + 创建图例行）。
     *   设为 true 时：
     *   - 不进入 _seriesList（audit 的 extraSeriesCount 不计入）
     *   - 不创建 legend 图例行（不会显示独立的颜色方块图例）
     *   适用场景：主图表的默认 K 线系列。
     *   它是图表的固有组件，生命周期由 AbstractChart 管理，
     *   不应被视为"额外系列"，也不应在 legend 中显示独立条目。
     *   K 线数据通过 legendHandler 在 OHLC 文本中显示。
     */
    createCandleSeries(name: string, options: DeepPartial<SeriesOptionsCommon>, paneIndex: number = 0, dontAddList: boolean = false)
    {
        const candle = this.chart.addSeries(
            CandlestickSeries,
            { ...options },
            paneIndex
        );
        if (!dontAddList) {
            this._seriesList.push(candle);
            this.legend.makeSeriesRow(name, candle, paneIndex);
        }
        return {
            name: name,
            series: candle,
        };
    }

    createToolBox() {
        if (!this.series) return;
        this.toolBox = new ToolBox(this.id, this.chart, this.series, this.commandFunctions);
        this.div.appendChild(this.toolBox.div);
    }

    createTopBar() {
        this._topBar = new TopBar(this);
        this.wrapper.prepend(this._topBar._div)
        return this._topBar;
    }

    toJSON() {
        // Exclude the chart attribute from serialization
        const {chart, ...serialized} = this;
        return serialized;
    }

    public static syncChartsAll(handlers:Handler[], crosshairOnly = false) {
        // 新增：存储同步关系
        handlers.forEach(h => {
            h._syncedHandlers = handlers.map(t => t.id).filter(id => id !== h.id);
        });

        // 1) Crosshair
        handlers.forEach((source) => {
            const crosshairCb = (param: MouseEventParams) => {
                // 重入守卫：防止 crosshair 同步级联触发
                if (source._inSync) return;
                source._inSync = true;
                try {
                    const time = param.time;
                    const srcSeries = source.series;
                    if (!srcSeries) return;
                    const point = time ? param.seriesData.get(srcSeries) || null : null;
                    for (let i = 0; i < handlers.length; i++) {
                        const target = handlers[i];
                        if (target === source) continue;
                        if (!target.series) continue;
                        try {
                            const tc = target.chart;
                            if (!time) { tc.clearCrosshairPosition(); continue; }
                            tc.setCrosshairPosition(0, time, target.series);
                            if (point && target.legend?.div) {
                                target.legend.legendHandler({ time, point } as any, true);
                            }
                        } catch (_) {}
                    }
                } finally {
                    source._inSync = false;
                }
            };
            source.chart.subscribeCrosshairMove(crosshairCb);
            // 存储回调引用（source 自己的回调订阅在自己 chart 上）
            source._syncCallbacks['__crosshairAll'] = {
                crosshair: crosshairCb,
                crosshairSource: source,
            };
        });

        if (crosshairOnly) return;

        // 2) Visible range synchronization
        handlers.forEach((source) => {
            const rangeCb = (range: LogicalRange | null) => {
                // 重入守卫：防止 range 回调级联触发
                if (source._inRangeSync) return;
                source._inRangeSync = true;
                try {
                    const rFrom = range?.from;
                    const rTo = range?.to;
                    const rangeKey = range ? `${rFrom}_${rTo}` : '';
                    if (rangeKey === source._lastSyncedRange) return;
                    source._lastSyncedRange = rangeKey;
                    for (let i = 0; i < handlers.length; i++) {
                        const target = handlers[i];
                        if (target === source || !range) continue;
                        try { target.chart.timeScale().setVisibleLogicalRange(range); } catch (_) {}
                    }
                } finally {
                    source._inRangeSync = false;
                }
            };
            source.chart.timeScale().subscribeVisibleLogicalRangeChange(rangeCb);
            source._syncCallbacks['__rangeAll'] = {
                range: rangeCb,
                rangeSource: source,
            };
        });
    }

    /**
     * 加入同步组。sync_id 作为组名，同组内所有 handler 自动同步。
     * 支持混合 crosshairOnly：组内任意 handler 设为 true 则该对仅同步十字光标。
     */
    public static joinSyncGroup(chartOrId: Handler | string, groupName: string, crosshairOnly: boolean = false) {
        // 如果传入字符串ID，查找对应的Handler对象
        let chart: Handler | undefined;
        if (typeof chartOrId === 'string') {
            chart = Handler._all.find(h => h.id === chartOrId);
            if (!chart) {
                console.error(`Handler not found for id: ${chartOrId}`);
                return;
            }
        } else {
            chart = chartOrId;
        }
        
        chart._syncGroup = groupName;
        chart._syncCrosshairOnly = crosshairOnly;

        // 找出同组所有 handler
        const groupHandlers = Handler._all.filter(h => h._syncGroup === groupName);

        // 清理同组所有旧 sync 回调
        groupHandlers.forEach(h => {
            for (const [, cb] of Object.entries(h._syncCallbacks)) {
                if (cb.crosshair && cb.crosshairSource) {
                    cb.crosshairSource.chart.unsubscribeCrosshairMove(cb.crosshair);
                }
                if (cb.range && cb.rangeSource) {
                    cb.rangeSource.chart.timeScale().unsubscribeVisibleLogicalRangeChange(cb.range);
                }
            }
            h._syncCallbacks = {};
            h._syncedHandlers = [];
        });

        // 重建同组同步
        if (groupHandlers.length > 1) {
            Handler.syncGroup(groupHandlers);
        }
    }

    /**
     * 组同步：根据每个 handler 的 _syncCrosshairOnly 设置，
     * 决定 crosshair 和 range 的同步范围。
     * - crosshair：所有同组 handler 互相同步
     * - range：仅 _syncCrosshairOnly=false 的 handler 之间同步
     */
    public static syncGroup(handlers: Handler[]) {
        // 更新 _syncedHandlers
        handlers.forEach(h => {
            h._syncedHandlers = handlers.map(t => t.id).filter(id => id !== h.id);
        });

        // 1) Crosshair sync — 所有 handler 互相同步
        handlers.forEach((source) => {
            const crosshairCb = (param: MouseEventParams) => {
                // 重入守卫：setCrosshairPosition 会触发目标图表的 crosshairMove，
                // 导致回调级联（N² 更新风暴）。检测到重入时直接跳过。
                if (source._inSync) return;
                source._inSync = true;
                try {
                    const time = param.time;
                    const srcSeries = source.series;
                    if (!srcSeries) return;
                    const point = time ? param.seriesData.get(srcSeries) || null : null;
                    for (let i = 0; i < handlers.length; i++) {
                        const target = handlers[i];
                        if (target === source) continue;
                        if (!target.series) continue;
                        try {
                            const tc = target.chart;
                            if (!time) { tc.clearCrosshairPosition(); continue; }
                            tc.setCrosshairPosition(0, time, target.series);
                            if (point && target.legend?.div) {
                                target.legend.legendHandler({ time, point } as any, true);
                            }
                        } catch (_) {}
                    }
                } finally {
                    source._inSync = false;
                }
            };
            source.chart.subscribeCrosshairMove(crosshairCb);
            // 存储回调引用（source 自己的回调订阅在自己 chart 上）
            source._syncCallbacks['__crosshairAll'] = {
                crosshair: crosshairCb,
                crosshairSource: source,
            };
        });

        // 2) Range sync — 仅 _syncCrosshairOnly=false 的 handler 之间同步
        const rangeHandlers = handlers.filter(h => !h._syncCrosshairOnly);
        if (rangeHandlers.length > 1) {
            rangeHandlers.forEach((source) => {
                const rangeCb = (range: LogicalRange | null) => {
                    // 重入守卫：setVisibleLogicalRange 会触发目标图表的
                    // visibleLogicalRangeChange，导致 range 回调级联（N² 更新风暴）
                    if (source._inRangeSync) return;
                    source._inRangeSync = true;
                    try {
                        const rFrom = range?.from;
                        const rTo = range?.to;
                        const rangeKey = range ? `${rFrom}_${rTo}` : '';
                        if (rangeKey === source._lastSyncedRange) return;
                        source._lastSyncedRange = rangeKey;
                        for (let i = 0; i < rangeHandlers.length; i++) {
                            const target = rangeHandlers[i];
                            if (target === source || !range) continue;
                            try { target.chart.timeScale().setVisibleLogicalRange(range); } catch (_) {}
                        }
                    } finally {
                        source._inRangeSync = false;
                    }
                };
                source.chart.timeScale().subscribeVisibleLogicalRangeChange(rangeCb);
                source._syncCallbacks['__rangeAll'] = {
                    range: rangeCb,
                    rangeSource: source,
                };
            });
        }
    }

    public static syncCharts(childChart:Handler, parentChart: Handler, crosshairOnly = false) {
        function crosshairHandler(chart: Handler, point: any, param: any) {
            if (!chart.series) return;
            if (!param.time) {
                chart.chart.clearCrosshairPosition();
                return;
            }
            chart.chart.setCrosshairPosition(0, param.time, chart.series);
            if (point)
                chart.legend.legendHandler(point, true);
        }

        function getPoint(series: ISeriesApi<SeriesType> | null, param: MouseEventParams) {
            if (!series || !param.time) return null;
            return param.seriesData.get(series) || null;
        }

        const childTimeScale = childChart.chart.timeScale();
        const parentTimeScale = parentChart.chart.timeScale();

        const setChildRange = (timeRange: LogicalRange | null) => {
            if (childChart._inRangeSync) return;
            childChart._inRangeSync = true;
            try { if(timeRange) childTimeScale.setVisibleLogicalRange(timeRange); } finally { childChart._inRangeSync = false; }
        }
        const setParentRange = (timeRange: LogicalRange | null) => {
            if (parentChart._inRangeSync) return;
            parentChart._inRangeSync = true;
            try { if(timeRange) parentTimeScale.setVisibleLogicalRange(timeRange); } finally { parentChart._inRangeSync = false; }
        }

        const setParentCrosshair = (param: MouseEventParams) => {
            crosshairHandler(parentChart, getPoint(childChart.series, param), param)
        }
        const setChildCrosshair = (param: MouseEventParams) => {
            crosshairHandler(childChart, getPoint(parentChart.series, param), param)
        }

        parentChart.chart.subscribeCrosshairMove(setChildCrosshair);
        childChart.chart.subscribeCrosshairMove(setParentCrosshair);

        // 存储回调引用 + 记录订阅源
        parentChart._syncCallbacks[childChart.id] = {
            crosshair: setChildCrosshair,
            crosshairSource: parentChart
        };
        childChart._syncCallbacks[parentChart.id] = {
            crosshair: setParentCrosshair,
            crosshairSource: childChart
        };
        parentChart._syncedHandlers.push(childChart.id);
        childChart._syncedHandlers.push(parentChart.id);

        if (crosshairOnly)
            return

        childChart.chart.timeScale().subscribeVisibleLogicalRangeChange(setParentRange);
        parentChart.chart.timeScale().subscribeVisibleLogicalRangeChange(setChildRange);

        // 存储 range 回调引用
        parentChart._syncCallbacks[childChart.id].range = setChildRange;
        parentChart._syncCallbacks[childChart.id].rangeSource = parentChart;
        childChart._syncCallbacks[parentChart.id].range = setParentRange;
        childChart._syncCallbacks[parentChart.id].rangeSource = childChart;
    }


    /**
     * 双向解除与指定 handler 的 sync 关联。
     * 从本图取消订阅其他图上的回调，清理同步列表。
     */
    public unsyncChart(handlerId: string) {
        const cb = this._syncCallbacks[handlerId];
        if (cb) {
            if (cb.crosshair && cb.crosshairSource) {
                cb.crosshairSource.chart.unsubscribeCrosshairMove(cb.crosshair);
            }
            if (cb.range && cb.rangeSource) {
                cb.rangeSource.chart.timeScale().unsubscribeVisibleLogicalRangeChange(cb.range);
            }
            delete this._syncCallbacks[handlerId];
        }
        this._syncedHandlers = this._syncedHandlers.filter(id => id !== handlerId);

        // 从其他图的同步列表中移除本图
        Handler._all.forEach(h => {
            if (h._syncedHandlers && h._syncedHandlers.includes(this.id)) {
                h._syncedHandlers = h._syncedHandlers.filter(id => id !== this.id);
            }
        });
    }

    /**
     * 重建指定 chart 的 sync 订阅（排除已删除的 handler）。
     * 取消旧回调，为剩余 targets 创建新回调并重新订阅。
     */
    public static _rebuildSync(chart: Handler, excludedId: string) {
        // 取消本图所有旧的 sync 回调
        for (const [, cb] of Object.entries(chart._syncCallbacks)) {
            if (cb.crosshair && cb.crosshairSource) {
                cb.crosshairSource.chart.unsubscribeCrosshairMove(cb.crosshair);
            }
            if (cb.range && cb.rangeSource) {
                cb.rangeSource.chart.timeScale().unsubscribeVisibleLogicalRangeChange(cb.range);
            }
        }
        chart._syncCallbacks = {};

        // 收集剩余的 targets
        const targets = chart._syncedHandlers
            .filter(id => id !== excludedId)
            .map(id => Handler._all.find(h => h.id === id))
            .filter(Boolean) as Handler[];

        if (targets.length === 0) return;

        // 重建 crosshair 同步
        const crosshairCb = (param: MouseEventParams) => {
            // 重入守卫：防止 crosshair 同步级联触发
            if (chart._inSync) return;
            chart._inSync = true;
            try {
                const time = param.time;
                const srcSeries = chart.series;
                if (!srcSeries) return;
                const point = time ? param.seriesData.get(srcSeries) || null : null;
                for (let i = 0; i < targets.length; i++) {
                    const target = targets[i];
                    if (!target.series) continue;
                    try {
                        if (!target.legend?.div) continue;
                        const tc = target.chart;
                        if (!time) { tc.clearCrosshairPosition(); continue; }
                        tc.setCrosshairPosition(0, time, target.series);
                        if (point) {
                            target.legend.legendHandler({ time, point } as any, true);
                        }
                    } catch (_) {}
                }
            } finally {
                chart._inSync = false;
            }
        };
        chart.chart.subscribeCrosshairMove(crosshairCb);

        // 存储新的回调引用
        for (let i = 0; i < targets.length; i++) {
            chart._syncCallbacks[targets[i].id] = {
                crosshair: crosshairCb,
                crosshairSource: chart
            };
        }

        // 重建 range 同步
        const rangeCb = (range: LogicalRange | null) => {
            // 重入守卫：防止 range 回调级联触发
            if (chart._inRangeSync) return;
            chart._inRangeSync = true;
            try {
                const rFrom = range?.from;
                const rTo = range?.to;
                const rangeKey = range ? `${rFrom}_${rTo}` : '';
                if (rangeKey === chart._lastSyncedRange) return;
                chart._lastSyncedRange = rangeKey;
                for (let i = 0; i < targets.length; i++) {
                    if (range) {
                        try { targets[i].chart.timeScale().setVisibleLogicalRange(range); } catch (_) {}
                    }
                }
            } finally {
                chart._inRangeSync = false;
            }
        };
        chart.chart.timeScale().subscribeVisibleLogicalRangeChange(rangeCb);
        for (let i = 0; i < targets.length; i++) {
            if (chart._syncCallbacks[targets[i].id]) {
                chart._syncCallbacks[targets[i].id].range = rangeCb;
                chart._syncCallbacks[targets[i].id].rangeSource = chart;
            }
        }
    }

    public static makeSearchBox(chart: Handler) {
        const searchWindow = document.createElement('div')
        searchWindow.classList.add('searchbox');
        searchWindow.style.display = 'none';

        const magnifyingGlass = document.createElement('div');
        magnifyingGlass.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="24px" height="24px" viewBox="0 0 24 24" version="1.1"><path style="fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;stroke:lightgray;stroke-opacity:1;stroke-miterlimit:4;" d="M 15 15 L 21 21 M 10 17 C 6.132812 17 3 13.867188 3 10 C 3 6.132812 6.132812 3 10 3 C 13.867188 3 17 6.132812 17 10 C 17 13.867188 13.867188 17 10 17 Z M 10 17 "/></svg>`

        const sBox = document.createElement('input');
        sBox.type = 'text';

        searchWindow.appendChild(magnifyingGlass)
        searchWindow.appendChild(sBox)
        chart.div.appendChild(searchWindow);

        chart.commandFunctions.push((event: KeyboardEvent) => {
            if (window.handlerInFocus !== chart.id || window.textBoxFocused)
                return false
            if (searchWindow.style.display === 'none') {
                if (/^[a-zA-Z0-9]$/.test(event.key)) {
                    searchWindow.style.display = 'flex';
                    sBox.focus();
                    return true
                }
                else return false
            }
            else if (event.key === 'Enter' || event.key === 'Escape') {
                if (event.key === 'Enter')
                    window.callbackFunction(`search${chart.id}_~_${sBox.value}`)
                searchWindow.style.display = 'none'
                sBox.value = ''
                return true
            }
            else return false
        })
        sBox.addEventListener('input', () => sBox.value = sBox.value.toUpperCase())
        return {
            window: searchWindow,
            box: sBox,
        }
    }

    public static makeSpinner(chart: Handler) {
        chart.spinner = document.createElement('div');
        chart.spinner.classList.add('spinner');
        chart.wrapper.appendChild(chart.spinner)

        // Spinner animation using requestAnimationFrame (could also be done with CSS animation)
        let rotation = 0;
        const speed = 10;
        function animateSpinner() {
            if (!chart.spinner) return;
            rotation += speed
            chart.spinner.style.transform = `translate(-50%, -50%) rotate(${rotation}deg)`
            requestAnimationFrame(animateSpinner)
        }
        animateSpinner();
    }

    private static readonly _styleMap = {
        '--bg-color': 'backgroundColor',
        '--hover-bg-color': 'hoverBackgroundColor',
        '--click-bg-color': 'clickBackgroundColor',
        '--active-bg-color': 'activeBackgroundColor',
        '--muted-bg-color': 'mutedBackgroundColor',
        '--border-color': 'borderColor',
        '--color': 'color',
        '--active-color': 'activeColor',
    }
    public static setRootStyles(styles: any) {
        const rootStyle = document.documentElement.style;
        for (const [property, valueKey] of Object.entries(this._styleMap)) {
            rootStyle.setProperty(property, styles[valueKey]);
        }
    }

  createWatermark(text: string, fontSize: number, color: string) {
    if (!this.watermark) {
      this.watermark = createTextWatermark(this.chart.panes()[0], {
        horzAlign: 'center',
        vertAlign: 'center',
        lines: [{
          text: text,
          color: color,
          fontSize: fontSize,
        }],
      });

      return;
    }

    this.watermark.applyOptions({
      lines: [{
        text: text,
        color: color,
        fontSize: fontSize,
      }]
    });
  }
}
