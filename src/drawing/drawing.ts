import {
    IPaneApi,
    Logical,
    MouseEventParams,
    Time,
} from 'lightweight-charts';

import { PanePluginBase } from '../pane-plugin-base';
import { DiffPoint, Point } from './data-source';
import { DrawingOptions, defaultOptions } from './options';
import { DrawingPaneView } from './pane-view';

export enum InteractionState {
    NONE,
    HOVERING,
    DRAGGING,
    DRAGGINGP1,
    DRAGGINGP2,
    DRAGGINGP3,
    DRAGGINGP4,
}

export abstract class Drawing extends PanePluginBase {
    _paneViews: DrawingPaneView[] = [];
    _options: DrawingOptions;

    abstract _type: string;
    protected _points: (Point|null)[] = [];

    protected _state: InteractionState = InteractionState.NONE;

    protected _startDragPoint: Point | null = null;
    protected _latestHoverPoint: any | null = null;

    protected static _mouseIsDown: boolean = false;

    /** 拖拽结束后由 DrawingTool 设置的回调 */
    public static _onDragEnd: (() => void) | null = null;

    public static hoveredObject: Drawing | null = null;
    public static lastHoveredObject: Drawing | null = null;

    protected _listeners: any[] = [];

    constructor(
        pane: IPaneApi<Time>,
        options?: Partial<DrawingOptions>
    ) {
        super(pane);
        this._options = {
            ...defaultOptions,
            ...options,
        };
    }

    updateAllViews() {
        this._paneViews.forEach(pw => pw.update());
    }

    paneViews() {
        return this._paneViews;
    }

    applyOptions(options: Partial<DrawingOptions>) {
        this._options = {
            ...this._options,
            ...options,
        }
        this.requestUpdate();
    }

    public updatePoints(...points: (Point | null)[]) {
        for (let i=0; i<this.points.length; i++) {
            if (points[i] == null) continue;
            this.points[i] = points[i] as Point;
        }
        this.requestUpdate();
    }

    detach() {
        this._options.lineColor = 'transparent';
        this.requestUpdate();
        this.pane.detachPrimitive(this);
        for (const s of this._listeners) {
            document.body.removeEventListener(s.name, s.listener);
        }
    }

    get points() {
        return this._points;
    }

    protected _subscribe(name: keyof DocumentEventMap, listener: any) {
        document.body.addEventListener(name, listener);
        this._listeners.push({name: name, listener: listener});
    }

    protected _unsubscribe(name: keyof DocumentEventMap, callback: any) {
        document.body.removeEventListener(name, callback);

        const toRemove = this._listeners.find((x) => x.name === name && x.listener === callback)
        this._listeners.splice(this._listeners.indexOf(toRemove), 1);
    }

    /**
     * 检查鼠标是否在当前 drawing 所属的 pane 上。
     * 直接用 MouseEventParams.paneIndex 与 this.pane.paneIndex() 比较。
     */
    protected _isMouseInMyPane(param: MouseEventParams): boolean {
        if (param.paneIndex === undefined) return true;
        return param.paneIndex === this.pane.paneIndex();
    }

    _handleHoverInteraction(param: MouseEventParams) {
        this._latestHoverPoint = param.point;

        // 已在拖拽中：不检查边界，让拖拽自由完成
        const isDragging = this._state === InteractionState.DRAGGING
            || this._state === InteractionState.DRAGGINGP1
            || this._state === InteractionState.DRAGGINGP2
            || this._state === InteractionState.DRAGGINGP3
            || this._state === InteractionState.DRAGGINGP4;

        if (isDragging) {
            this._handleDragInteraction(param);
            return;
        }

        // 未拖拽：检查 pane 边界，鼠标在其他 pane 上时忽略
        if (!this._isMouseInMyPane(param)) {
            if (this._state !== InteractionState.NONE) {
                this._moveToState(InteractionState.NONE);
                if (Drawing.hoveredObject === this) Drawing.hoveredObject = null;
            }
            return;
        }

        if (Drawing._mouseIsDown) {
            this._handleDragInteraction(param);
        } else {
            if (this._mouseIsOverDrawing(param)) {
                if (this._state != InteractionState.NONE) return;
                this._moveToState(InteractionState.HOVERING);
                Drawing.hoveredObject = Drawing.lastHoveredObject = this;
            } else {
                if (this._state == InteractionState.NONE) return;
                this._moveToState(InteractionState.NONE);
                if (Drawing.hoveredObject === this) Drawing.hoveredObject = null;
            }
        }
    }

    /**
     * 将鼠标事件转为 Point（时间+价格）。
     * 通过 pane.getSeries()[0] 获取 pane 上有数据的 series 做坐标转换。
     */
    public static _eventToPoint(param: MouseEventParams, pane: IPaneApi<Time>) {
        if (!pane || !param.point || !param.logical) return null;
        const series = pane.getSeries();
        if (!series || series.length === 0) return null;
        const barPrice = series[0].coordinateToPrice(param.point.y);
        if (barPrice == null) return null;
        return {
            time: param.time || null,
            logical: param.logical,
            price: barPrice,
        }
    }

    protected static _getDiff(p1: Point, p2: Point): DiffPoint {
        const diff: DiffPoint = {
            logical: p1.logical-p2.logical,
            price: p1.price-p2.price,
        }
        return diff;
    }

    /**
     * 通过 chart.timeScale() 将 logical index 转回 time，不再依赖 series.dataByIndex。
     */
    protected _addDiffToPoint(point: Point | null, logicalDiff: number, priceDiff: number) {
        if (!point) return;
        point.logical = point.logical + logicalDiff as Logical;
        point.price = point.price + priceDiff;
        // 用 chart.timeScale() 从 logical 恢复 time
        const timeScale = this.chart.timeScale();
        const coord = timeScale.logicalToCoordinate(point.logical as Logical);
        if (coord !== null) {
            const timeValue = timeScale.coordinateToTime(coord);
            point.time = timeValue !== null ? (timeValue as any) : null;
        } else {
            point.time = null;
        }
    }

    protected _handleMouseDownInteraction = () => {
        Drawing._mouseIsDown = true;
        this._onMouseDown();
    }

    protected _handleMouseUpInteraction = () => {
        const wasDragging = this._state === InteractionState.DRAGGING
            || this._state === InteractionState.DRAGGINGP1
            || this._state === InteractionState.DRAGGINGP2
            || this._state === InteractionState.DRAGGINGP3
            || this._state === InteractionState.DRAGGINGP4;
        Drawing._mouseIsDown = false;
        this._moveToState(InteractionState.HOVERING);
        if (wasDragging) {
            Drawing._onDragEnd?.();
        }
    }

    private _handleDragInteraction(param: MouseEventParams): void {
        if (this._state != InteractionState.DRAGGING &&
            this._state != InteractionState.DRAGGINGP1 &&
            this._state != InteractionState.DRAGGINGP2 &&
            this._state != InteractionState.DRAGGINGP3 &&
            this._state != InteractionState.DRAGGINGP4) {
            return;
        }
        const mousePoint = Drawing._eventToPoint(param, this.pane);
        if (!mousePoint) return;
        this._startDragPoint = this._startDragPoint || mousePoint;

        const diff = Drawing._getDiff(mousePoint, this._startDragPoint);
        this._onDrag(diff);
        this.requestUpdate();

        this._startDragPoint = mousePoint;
    }

    protected abstract _onMouseDown(): void;
    protected abstract _onDrag(diff: DiffPoint): void;
    protected abstract _moveToState(state: InteractionState): void;
    protected abstract _mouseIsOverDrawing(param: MouseEventParams): boolean;
}
