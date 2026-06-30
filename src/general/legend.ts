import { ISeriesApi, Logical, MouseEventParams, PriceFormatBuiltIn, SeriesType } from "lightweight-charts";
import { Handler } from "./handler";
import { htmlToElement } from "./global-params";

interface LineElement {
    name: string;
    paneIndex: number;
    group: string | null;
    div: HTMLDivElement;
    row: HTMLDivElement | null;       // standalone 行（group=null 时使用）
    toggle: HTMLDivElement;
    series: ISeriesApi<SeriesType>;
    solid: string;
    /** 个人眼睛的 on 状态（用于组开关同步） */
    individualOn: boolean;
}

interface GroupElement {
    row: HTMLDivElement;              // 组行 DOM
    groupToggle: HTMLDivElement;      // ♦ 组开关
    groupNameSpan: HTMLSpanElement;   // 组名文字
    elements: LineElement[];          // 组内所有 series
    on: boolean;                      // 组可见状态
    individualOnList: boolean[];      // 每个 series 的个人开关状态
}

type LineDictionary = {
    [key: number]: LineElement[];
}

export class Legend {
    private handler: Handler;
    public div: HTMLDivElement;
    public seriesContainer: HTMLDivElement

    private ohlcEnabled: boolean = false;
    private percentEnabled: boolean = false;
    private linesEnabled: boolean = false;
    private colorBasedOnCandle: boolean = false;
    public persistent: boolean = false;
    public shorthand: boolean = true;

    private text: HTMLSpanElement;
    private candle: HTMLDivElement;
    public _lines: LineElement[] = [];
    private _lines_grp: LineDictionary = {};
    private _groups: { [groupName: string]: GroupElement } = {};

    constructor(handler: Handler) {
        this.legendHandler = this.legendHandler.bind(this)

        this.handler = handler;
        this.ohlcEnabled = false;
        this.percentEnabled = false
        this.linesEnabled = false
        this.persistent = false
        this.shorthand = true
        this.colorBasedOnCandle = false

        this.div = document.createElement('div');
        this.div.classList.add("legend")
        this.div.style.maxWidth = `${(handler.scale.width * 100) - 8}vw`
        this.div.style.display = 'none';

        const seriesWrapper = document.createElement('div');
        seriesWrapper.style.display = 'flex';
        seriesWrapper.style.flexDirection = 'row';
        this.seriesContainer = document.createElement("div");
        this.seriesContainer.classList.add("series-container");

        this.text = document.createElement('span')
        this.text.style.lineHeight = '1.8'
        this.candle = document.createElement('div')

        seriesWrapper.appendChild(this.seriesContainer);
        this.div.appendChild(this.text)
        this.div.appendChild(this.candle)
        this.div.appendChild(seriesWrapper)
        handler.div.appendChild(this.div)

        handler.chart.subscribeCrosshairMove(this.legendHandler)
    }

    toJSON() {
        // Exclude the chart attribute from serialization
        const {_lines, _groups, handler, ...serialized} = this;
        return serialized;
    }

    /**
     * 清理 legend 资源：取消 crosshair 订阅、移除 DOM、清空内部状态。
     * 用于 reset_sub() 时清理子图的 legend。
     */
    public cleanup() {
        this.handler.chart.unsubscribeCrosshairMove(this.legendHandler);
        this.div.remove();
        this._lines = [];
        this._lines_grp = {};
        this._groups = {};
    }

    /**
     * 重建 legend DOM 并重新订阅 crosshair 事件。
     * 在 cleanup() 之后、需要恢复 legend 时调用。
     * 重建后 div 附加到 handler.div，默认隐藏 (display:none)，
     * 由 Python 端 legend(visible=True) 控制显示。
     */
    public recreate() {
        // 重建 DOM 结构（与 constructor 一致）
        this.div = document.createElement('div');
        this.div.classList.add("legend")
        this.div.style.maxWidth = `${(this.handler.scale.width * 100) - 8}vw`
        this.div.style.display = 'none';

        const seriesWrapper = document.createElement('div');
        seriesWrapper.style.display = 'flex';
        seriesWrapper.style.flexDirection = 'row';
        this.seriesContainer = document.createElement("div");
        this.seriesContainer.classList.add("series-container");

        this.text = document.createElement('span')
        this.text.style.lineHeight = '1.8'
        this.candle = document.createElement('div')

        seriesWrapper.appendChild(this.seriesContainer);
        this.div.appendChild(this.text)
        this.div.appendChild(this.candle)
        this.div.appendChild(seriesWrapper)
        this.handler.div.appendChild(this.div)

        // 重新订阅 crosshair 事件
        this.handler.chart.subscribeCrosshairMove(this.legendHandler)
    }

    /**
     * 创建组行 DOM 并追加到 seriesContainer。
     */
    private _renderGroupRow(groupName: string, elements: LineElement[]) {
        const row = document.createElement('div');
        row.classList.add('legend-group-row');
        row.style.display = 'flex';
        row.style.alignItems = 'center';
        row.style.gap = '2px';

        // ♦ 组开关
        const groupToggle = document.createElement('div');
        groupToggle.classList.add('legend-group-toggle');
        groupToggle.style.cursor = 'pointer';
        groupToggle.style.marginRight = '4px';

        const groupNameSpan = document.createElement('span');
        groupNameSpan.style.fontSize = '11px';
        groupNameSpan.style.color = 'inherit';
        groupNameSpan.style.opacity = '0.7';
        groupNameSpan.style.marginRight = '4px';
        groupNameSpan.innerText = `♦ ${groupName}`;

        groupToggle.appendChild(groupNameSpan);
        row.appendChild(groupToggle);

        // 组内每个 series 的颜色方块+名称+个人眼睛
        for (const el of elements) {
            row.appendChild(el.div);
            row.appendChild(el.toggle);
        }

        this.seriesContainer.appendChild(row);

        // 组开关点击事件
        let groupOn = true;
        groupToggle.addEventListener('click', () => {
            groupOn = !groupOn;
            const grp = this._groups[groupName];
            if (!grp) return;
            grp.on = groupOn;
            grp.groupNameSpan.innerText = groupOn ? `♦ ${groupName}` : `♢ ${groupName}`;
            grp.groupNameSpan.style.opacity = groupOn ? '0.7' : '0.4';
            // 同步所有 series 可见性 + 个人眼睛图标
            for (let i = 0; i < grp.elements.length; i++) {
                grp.elements[i].series.applyOptions({ visible: groupOn });
                grp.individualOnList[i] = groupOn;
                this._updateToggleIcon(grp.elements[i].toggle, groupOn);
            }
        });

        this._groups[groupName] = {
            row,
            groupToggle,
            groupNameSpan,
            elements,
            on: true,
            individualOnList: elements.map(() => true),
        };
    }

    /**
     * 更新个人眼睛图标的 open/closed 状态。
     */
    private _updateToggleIcon(toggle: HTMLDivElement, on: boolean) {
        const strokeColor = '#FFF';
        const openEye = `
    <path style="fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;stroke:${strokeColor};stroke-opacity:1;stroke-miterlimit:4;" d="M 21.998437 12 C 21.998437 12 18.998437 18 12 18 C 5.001562 18 2.001562 12 2.001562 12 C 2.001562 12 5.001562 6 12 6 C 18.998437 6 21.998437 12 21.998437 12 Z M 21.998437 12 " transform="matrix(0.833333,0,0,0.833333,0,0)"/>
    <path style="fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;stroke:${strokeColor};stroke-opacity:1;stroke-miterlimit:4;" d="M 15 12 C 15 13.654687 13.654687 15 12 15 C 10.345312 15 9 13.654687 9 12 C 9 10.345312 10.345312 9 12 9 C 13.654687 9 15 10.345312 15 12 Z M 15 12 " transform="matrix(0.833333,0,0,0.833333,0,0)"/>`;
        const closedEye = `
    <path style="fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;stroke:${strokeColor};stroke-opacity:1;stroke-miterlimit:4;" d="M 20.001562 9 C 20.001562 9 19.678125 9.665625 18.998437 10.514062 M 12 14.001562 C 10.392187 14.001562 9.046875 13.589062 7.95 12.998437 M 12 14.001562 C 13.607812 14.001562 14.953125 13.589062 16.05 12.998437 M 12 14.001562 L 12 17.498437 M 3.998437 9 C 3.998437 9 4.354687 9.735937 5.104687 10.645312 M 7.95 12.998437 L 5.001562 15.998437 M 7.95 12.998437 C 6.689062 12.328125 5.751562 11.423437 5.104687 10.645312 M 16.05 12.998437 L 18.501562 15.998437 M 16.05 12.998437 C 17.38125 12.290625 18.351562 11.320312 18.998437 10.514062 M 5.104687 10.645312 L 2.001562 12 M 18.998437 10.514062 L 21.998437 12 " transform="matrix(0.833333,0,0,0.833333,0,0)"/>`;
        const svgEl = toggle.querySelector('svg g');
        if (svgEl) {
            svgEl.innerHTML = on ? openEye : closedEye;
        }
    }

    /**
     * 从 Series 颜色中提取纯色（用于 legend 颜色方块）。
     */
    private _extractColor(series: ISeriesApi<SeriesType>): string {
        const options = series.options() as any;
        const seriesType = series.seriesType();
        let color: string;
        if (seriesType === 'Line' || seriesType === 'Histogram') {
            color = options.color;
        } else if (seriesType === 'Area') {
            color = options.topColor;
        } else {
            if ('color' in options) {
                color = options.color;
            } else if ('topColor' in options) {
                color = options.topColor;
            } else {
                color = options.baseLineColor;
            }
        }
        return color.startsWith('rgba') ? color.replace(/[^,]+(?=\))/, '1') : color;
    }

    makeSeriesRow(name: string, series: ISeriesApi<SeriesType>, paneIndex: number, group: string | null = null) {
        const strokeColor = '#FFF';
        let openEye = `
    <path style="fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;stroke:${strokeColor};stroke-opacity:1;stroke-miterlimit:4;" d="M 21.998437 12 C 21.998437 12 18.998437 18 12 18 C 5.001562 18 2.001562 12 2.001562 12 C 2.001562 12 5.001562 6 12 6 C 18.998437 6 21.998437 12 21.998437 12 Z M 21.998437 12 " transform="matrix(0.833333,0,0,0.833333,0,0)"/>
    <path style="fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;stroke:${strokeColor};stroke-opacity:1;stroke-miterlimit:4;" d="M 15 12 C 15 13.654687 13.654687 15 12 15 C 10.345312 15 9 13.654687 9 12 C 9 10.345312 10.345312 9 12 9 C 13.654687 9 15 10.345312 15 12 Z M 15 12 " transform="matrix(0.833333,0,0,0.833333,0,0)"/>\`
    `
        let closedEye = `
    <path style="fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;stroke:${strokeColor};stroke-opacity:1;stroke-miterlimit:4;" d="M 20.001562 9 C 20.001562 9 19.678125 9.665625 18.998437 10.514062 M 12 14.001562 C 10.392187 14.001562 9.046875 13.589062 7.95 12.998437 M 12 14.001562 C 13.607812 14.001562 14.953125 13.589062 16.05 12.998437 M 12 14.001562 L 12 17.498437 M 3.998437 9 C 3.998437 9 4.354687 9.735937 5.104687 10.645312 M 7.95 12.998437 L 5.001562 15.998437 M 7.95 12.998437 C 6.689062 12.328125 5.751562 11.423437 5.104687 10.645312 M 16.05 12.998437 L 18.501562 15.998437 M 16.05 12.998437 C 17.38125 12.290625 18.351562 11.320312 18.998437 10.514062 M 5.104687 10.645312 L 2.001562 12 M 18.998437 10.514062 L 21.998437 12 " transform="matrix(0.833333,0,0,0.833333,0,0)"/>
    `

        let row = document.createElement('div')
        row.style.display = 'flex'
        row.style.alignItems = 'center'
        let div = document.createElement('div')
        let toggle = document.createElement('div')
        toggle.classList.add('legend-toggle-switch');

        let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("width", "22");
        svg.setAttribute("height", "16");

        let g = document.createElementNS("http://www.w3.org/2000/svg", "g");
        g.innerHTML = openEye

        let on = true
        toggle.addEventListener('click', () => {
            if (on) {
                on = false
                g.innerHTML = closedEye
                series.applyOptions({ visible: false })
            } else {
                on = true
                series.applyOptions({ visible: true })
                g.innerHTML = openEye
            }
            // 如果属于组，同步组开关状态
            if (group) {
                const grp = this._groups[group];
                if (grp) {
                    const idx = grp.elements.findIndex(e => e.series === series);
                    if (idx >= 0) {
                        grp.individualOnList[idx] = on;
                        // 如果所有个人开关都关了，组开关也关
                        const anyOn = grp.individualOnList.some(v => v);
                        grp.on = anyOn;
                        grp.groupNameSpan.innerText = anyOn ? `♦ ${group}` : `♢ ${group}`;
                        grp.groupNameSpan.style.opacity = anyOn ? '0.7' : '0.4';
                    }
                }
            }
        })

        svg.appendChild(g)
        toggle.appendChild(svg);

        const solid = this._extractColor(series);

        const element: LineElement = {
            name: name,
            paneIndex: paneIndex,
            group: group,
            div: div,
            row: group ? null : row,  // 有组时 row 由组行管理
            toggle: toggle,
            series: series,
            solid: solid,
            individualOn: true,
        };

        this._lines.push(element);

        if (group) {
            // === 分组模式 ===
            if (!this._groups[group]) {
                // 首次出现此组名：创建组行 + ♦ 组开关 + 组名
                this._renderGroupRow(group, [element]);
            } else {
                // 已有此组：追加到组行
                const grp = this._groups[group];
                grp.elements.push(element);
                grp.individualOnList.push(true);
                // 追加颜色方块+名称和眼睛到组行
                grp.row.appendChild(div);
                grp.row.appendChild(toggle);
            }
        } else {
            // === 独立模式（原行为） ===
            row.appendChild(div)
            row.appendChild(toggle)
            this.seriesContainer.appendChild(row)
            // 重新排序渲染
            this._rerenderContainer();
        }
    }

    /**
     * 重新渲染 seriesContainer：按 pane 分组，组行 + 独立行 + <br> 分隔。
     */
    private _rerenderContainer() {
        this._lines.sort((a, b) => a.paneIndex - b.paneIndex);
        this._lines_grp = this._lines.reduce((acc: LineDictionary, item: LineElement) => {
            if (!acc[item.paneIndex]) {
                acc[item.paneIndex] = [];
            }
            acc[item.paneIndex].push(item);
            return acc;
        }, {});

        this.seriesContainer.innerHTML = '';
        for (const k in this._lines_grp) {
            const paneLines = this._lines_grp[k];
            // 按 group 分桶
            const ungrouped: LineElement[] = [];
            const grouped: { [groupName: string]: LineElement[] } = {};

            for (const l of paneLines) {
                if (l.group) {
                    if (!grouped[l.group]) grouped[l.group] = [];
                    grouped[l.group].push(l);
                } else {
                    ungrouped.push(l);
                }
            }

            // 先渲染有组的 series
            for (const groupName in grouped) {
                if (this._groups[groupName]) {
                    this.seriesContainer.appendChild(this._groups[groupName].row);
                }
            }
            // 再渲染无组的 series
            for (const l of ungrouped) {
                this.seriesContainer.appendChild(l.row!);
            }

            this.seriesContainer.appendChild(htmlToElement("<br>")!);
        }
    }

    legendItemFormat(num: number, decimal: number) {
      return num.toFixed(decimal).toString().padStart(8, ' ')
    }

    shorthandFormat(num: number) {
        const absNum = Math.abs(num)
        if (absNum >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (absNum >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString().padStart(8, ' ');
    }

    legendHandler(param: MouseEventParams, usingPoint= false) {
        if (!this.ohlcEnabled && !this.linesEnabled && !this.percentEnabled) return;
        if (!this.handler.series) return;
        const options: any = this.handler.series.options()

        if (!param.time && !this.persistent) {
            this.candle.style.color = 'transparent'
            this.candle.innerHTML = this.candle.innerHTML.replace(options['upColor'], '').replace(options['downColor'], '')
            return
        }

        let data: any;
        let logical: Logical | null = null;

        if (usingPoint) {
            const timeScale = this.handler.chart.timeScale();
            let coordinate = param.time ? timeScale.timeToCoordinate(param.time) : null;
            if (coordinate)
                logical = timeScale.coordinateToLogical(coordinate.valueOf())
            if (logical)
                data = this.handler.series.dataByIndex(logical.valueOf())
        }
        else {
            data = param.seriesData.get(this.handler.series);
        }

        this.candle.style.color = ''
        if (!param.time) return
        let str = '<span style="line-height: 1.8;">'
        if (data) {
            if (this.ohlcEnabled) {
                str += `O ${this.legendItemFormat(data.open, this.handler.precision)} `
                str += `| H ${this.legendItemFormat(data.high, this.handler.precision)} `
                str += `| L ${this.legendItemFormat(data.low, this.handler.precision)} `
                str += `| C ${this.legendItemFormat(data.close, this.handler.precision)} `
            }

            if (this.handler.volumeSeries) {
                let volumeData: any;
                if (logical) {
                    volumeData = this.handler.volumeSeries.dataByIndex(logical)
                }
                else {
                    volumeData = param.seriesData.get(this.handler.volumeSeries)
                }
                if (volumeData) {
                    str += this.ohlcEnabled ? `| V ${this.shorthand ? this.shorthandFormat(volumeData.value) : volumeData.value}` : ''
                }
            }

            if (this.handler.openInterestSeries) {
                let oiData: any
                if (logical) {
                    oiData = this.handler.openInterestSeries.dataByIndex(logical)
                } else {
                    oiData = param.seriesData.get(this.handler.openInterestSeries)
                }
                if (oiData) {
                    str += `| OI ${this.shorthand ? this.shorthandFormat(oiData.value) : oiData.value}`
                }
            }

            if (this.percentEnabled) {
              let percentMove = ((data.close - data.open) / data.open) * 100;
              let color = percentMove > 0 ? options["upColor"] : options["downColor"];
              let percentStr = `${percentMove >= 0 ? "+" : ""}${percentMove.toFixed(2)} %`;

              if (this.colorBasedOnCandle) {
                str += `| <span style="color: ${color};">${percentStr}</span>`;
              }
              else {
                str += "| " + percentStr;
              }
            }
        }
        this.candle.innerHTML = str + '</span>'

        this._lines.forEach((e) => {
            if (!this.linesEnabled) {
                // 隐藏：独立行或组行
                if (e.row) {
                    e.row.style.display = 'none'
                } else if (e.group) {
                    const grp = this._groups[e.group];
                    if (grp) grp.row.style.display = 'none';
                }
                return
            }

            // 显示：独立行或组行
            if (e.row) {
                e.row.style.display = 'flex'
            } else if (e.group) {
                const grp = this._groups[e.group];
                if (grp) grp.row.style.display = 'flex';
            }

            let data
            if (usingPoint && logical) {
                data = e.series.dataByIndex(logical) as any
            }
            else {
                data = param.seriesData.get(e.series) as any
            }
            if (!data) return;

            // OHLC 类型的 series（Bar/Candlestick）特殊处理
            const seriesType = e.series.seriesType();
            if (seriesType === 'Bar' || seriesType === 'Candlestick') {
                if (data.open === undefined) return;
                let ohlcStr = `<span style="color: ${e.solid};">️■</span>    ${e.name} : `
                ohlcStr += `O ${this.legendItemFormat(data.open, this.handler.precision)} `
                ohlcStr += `| H ${this.legendItemFormat(data.high, this.handler.precision)} `
                ohlcStr += `| L ${this.legendItemFormat(data.low, this.handler.precision)} `
                ohlcStr += `| C ${this.legendItemFormat(data.close, this.handler.precision)}`
                e.div.innerHTML = ohlcStr
                return
            }

            // 普通 value 类型的 series
            if (data.value === undefined) return;
            const format = e.series.options().priceFormat as PriceFormatBuiltIn
            const price = this.legendItemFormat(data.value, format.precision)
            e.div.innerHTML = `<span style="color: ${e.solid};">️■</span>    ${e.name} : ${price}`
        })
    }
}
