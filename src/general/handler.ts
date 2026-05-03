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
    Time,
    createChart,
    CandlestickSeries,
    HistogramSeries,
    LineSeries,
    createTextWatermark,
    createSeriesMarkers,
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
        return JSON.stringify(Handler._all.map(h => ({
            id: h.id,
            hasSeries: !!h.series,
            hasVolumeSeries: !!h.volumeSeries,
            hasOpenInterestSeries: !!h.openInterestSeries,
            hasLegend: !!h.legend,
            hasTopBar: !!h._topBar,
            hasToolBox: !!h.toolBox,
            subchartsCount: h._seriesList.length,
            interval: h._interval,
            seriesListLength: h._seriesList.length,
        })));
    }

    public static auditFull(): string {
        return JSON.stringify(Handler._all.map(h => {
            const legendLines = h.legend?._lines?.map((l: any) => ({
                name: l.name,
                paneIndex: l.paneIndex,
                color: l.color,
            })) || [];
            return {
                id: h.id,
                series: {
                    hasCandlestick: !!h.series,
                    hasVolume: !!h.volumeSeries,
                    hasOpenInterest: !!h.openInterestSeries,
                    extraSeriesCount: h._seriesList.length,
                    legendLines: legendLines,
                },
                legend: {
                    visible: h.legend?.div?.style?.display !== 'none',
                    ohlcEnabled: !!(h.legend as any)?.ohlcEnabled,
                    persistent: !!(h.legend as any)?.persistent,
                },
                hasToolBox: !!h.toolBox,
                hasTopBar: !!h._topBar,
            };
        }));
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

    public series: ISeriesApi<SeriesType>;
    public volumeSeries: ISeriesApi<SeriesType>;
    public openInterestSeries: ISeriesApi<SeriesType> | null = null;
    public _interval: number = 86400;

    public legend: Legend;
    private _topBar: TopBar | undefined;
    public toolBox: ToolBox | undefined;
    public spinner: HTMLDivElement | undefined;

    public _seriesList: ISeriesApi<SeriesType>[] = [];
    private resize_hdr_height: number = 8;
    public watermark: any;
    public seriesMarkers: any;

    // TODO find a better solution rather than the 'position' parameter
    constructor(
        chartId: string,
        innerWidth: number,
        innerHeight: number,
        position: string,
        autoSize: boolean,
        paneIndex: number = 0
    ) {
        this.reSize = this.reSize.bind(this)

        this.id = chartId
        this.scale = {
            width: innerWidth,
            height: innerHeight,
        }

        this.wrapper = document.createElement('div')
        this.wrapper.classList.add("handler");
        this.wrapper.style.float = position

        this.div = document.createElement('div')
        this.div.style.position = 'relative'

        this.wrapper.appendChild(this.div);
        window.containerDiv.append(this.wrapper)

        // --- add this block to enable mouse‐drag height resizing ---
        const handle = document.createElement('div');
        handle.classList.add('resize-handle');
        this.wrapper.appendChild(handle);

        let startY, startHeight;
        const onMouseMove = (e) => {
          const delta = e.clientY - startY;
          const newH = Math.max(50, startHeight + delta); // min height 50px
          this.wrapper.style.height = `${newH}px`;
          // Resize the chart canvas accordingly:
          this.chart.resize(this.wrapper.offsetWidth, newH-this.resize_hdr_height);
        };
        const onMouseUp = () => {
          document.removeEventListener('mousemove', onMouseMove);
          document.removeEventListener('mouseup', onMouseUp);
        };
        handle.addEventListener('mousedown', (e) => {
          // prevent selecting text, etc.
          e.preventDefault();
          startY = e.clientY;
          startHeight = this.wrapper.getBoundingClientRect().height;
          document.addEventListener('mousemove', onMouseMove);
          document.addEventListener('mouseup', onMouseUp);
        });

        this.chart = this._createChart();
        this.series = this.createCandlestickSeries(paneIndex);
        this.volumeSeries = this.createVolumeSeries(paneIndex);
        this.seriesMarkers = createSeriesMarkers(this.series, []);

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


    reSize() {
      let topBarOffset = this.scale.height !== 0 ? this._topBar?._div.offsetHeight || 0 : 0
        if (this.scale.height >= 0) {
            this.chart.resize(window.innerWidth * this.scale.width, (window.innerHeight * this.scale.height) - topBarOffset - this.resize_hdr_height)
            this.wrapper.style.width = `${100 * this.scale.width}%`
            this.wrapper.style.height = `${100 * this.scale.height}%`
        }
        else {
            var chart_height: number = Math.ceil(Math.abs(this.scale.height));
            this.chart.resize(window.containerDiv.offsetWidth * this.scale.width, chart_height - topBarOffset - this.resize_hdr_height)
            this.wrapper.style.width = `${100 * this.scale.width}%`
            this.wrapper.style.height = `${chart_height}px`
        }

        // TODO definitely a better way to do this
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
        return createChart(this.div, {
      width: window.containerDiv.offsetWidth * this.scale.width,
      height: this.scale.height<0 ? Math.ceil(Math.abs(this.scale.height)) : window.innerHeight * this.scale.height,
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

    createCandlestickSeries(paneIndex?: number) {
        const up = 'rgba(39, 157, 130, 100)'
        const down = 'rgba(200, 97, 100, 100)'
        const candleSeries = this.chart.addSeries(
            CandlestickSeries, {
                upColor: up, borderUpColor: up, wickUpColor: up,
                downColor: down, borderDownColor: down, wickDownColor: down
            },
            paneIndex
        );
        candleSeries.priceScale().applyOptions({
            scaleMargins: {top: 0.2, bottom: 0.2},
        });
        return candleSeries;
    }

    createVolumeSeries(paneIndex?: number) {
        const volumeSeries = this.chart.addSeries(
            HistogramSeries,
            {
                color: '#26a69a',
                priceFormat: {type: 'volume'},
                priceScaleId: 'volume_scale',
            },
            paneIndex
        );
        volumeSeries.priceScale().applyOptions({
            scaleMargins: {top: 0.8, bottom: 0},
        });
        return volumeSeries;
    }

    createOpenInterestSeries(paneIndex?: number) {
        const oiSeries = this.chart.addSeries(
            LineSeries,
            {
                color: '#F5A623',
                lineWidth: 1,
                priceScaleId: 'oi_scale',
                lastValueVisible: false,
                priceLineVisible: false,
                crosshairMarkerVisible: true,
                autoscale: true,
            },
            paneIndex
        );
        oiSeries.priceScale().applyOptions({
            scaleMargins: {top: 0.8, bottom: 0},
            autoScale: true,
        });
        this.openInterestSeries = oiSeries;
        return oiSeries;
    }

    createLineSeries(name: string, options: DeepPartial<LineStyleOptions & SeriesOptionsCommon>, paneIndex: number = 0)
    {
        const line = this.chart.addSeries(LineSeries, {...options}, paneIndex);
        this._seriesList.push(line);
        this.legend.makeSeriesRow(name, line, paneIndex)

        return {
            name: name,
            series: line,
        }
    }

    createHistogramSeries(name: string, options: DeepPartial<HistogramStyleOptions & SeriesOptionsCommon>, paneIndex: number = 0)
    {
        const line = this.chart.addSeries(
            HistogramSeries,
            { ...options },
            paneIndex
        );
        this._seriesList.push(line);
        this.legend.makeSeriesRow(name, line, paneIndex);
        return {
            name: name,
            series: line,
        };
    }

    createToolBox() {
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
        // 1) Crosshair
        handlers.forEach((source) => {
            source.chart.subscribeCrosshairMove((param) => {
                handlers.forEach((target) => {
                    if (target === source) return;
                    if (!param.time) {
                        target.chart.clearCrosshairPosition();
                        return;
                    }
                    // get the point from the source series (for legend update)
                    const point = param.seriesData.get(source.series) || null;
                    // set the crosshair on the target chart
                    target.chart.setCrosshairPosition(0, param.time, target.series);
                    // update the legend on the target
                    if (point) {
                        const event = {
                            time: param.time,
                            point: point,
                        } as any;
                        target.legend.legendHandler(event, true);
                    }
                });
            });
        });

        if (crosshairOnly) return;

        // 2) Visible range synchronization
        handlers.forEach((source) => {
            source.chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
                handlers.forEach((target) => {
                    if (target === source || !range) return;
                    target.chart.timeScale().setVisibleLogicalRange(range);
                });
            });
        });
    }

    public static syncCharts(childChart:Handler, parentChart: Handler, crosshairOnly = false) {
        function crosshairHandler(chart: Handler, point: any, param: any) {
            if (!param.time) {
                chart.chart.clearCrosshairPosition();
                return;
            }
            chart.chart.setCrosshairPosition(0, param.time, chart.series);
            if (point)
                chart.legend.legendHandler(point, true);
        }

        function getPoint(series: ISeriesApi<SeriesType>, param: MouseEventParams) {
            if (!param.time) return null;
            return param.seriesData.get(series) || null;
        }

        const childTimeScale = childChart.chart.timeScale();
        const parentTimeScale = parentChart.chart.timeScale();

        const setChildRange = (timeRange: LogicalRange | null) => {
            if(timeRange) childTimeScale.setVisibleLogicalRange(timeRange);
        }
        const setParentRange = (timeRange: LogicalRange | null) => {
            if(timeRange) parentTimeScale.setVisibleLogicalRange(timeRange);
        }

        const setParentCrosshair = (param: MouseEventParams) => {
            crosshairHandler(parentChart, getPoint(childChart.series, param), param)
        }
        const setChildCrosshair = (param: MouseEventParams) => {
            crosshairHandler(childChart, getPoint(parentChart.series, param), param)
        }

        parentChart.chart.subscribeCrosshairMove(setChildCrosshair);
        childChart.chart.subscribeCrosshairMove(setParentCrosshair);

        if (crosshairOnly)
            return

        childChart.chart.timeScale().subscribeVisibleLogicalRangeChange(setParentRange);
        parentChart.chart.timeScale().subscribeVisibleLogicalRangeChange(setChildRange);
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

        // TODO below can be css (animate)
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
