import {
    IChartApi,
    IPaneApi,
    Logical,
    MouseEventParams,
    Time,
} from 'lightweight-charts';
import { Drawing } from './drawing';
import { HorizontalLine } from '../horizontal-line/horizontal-line';


export class DrawingTool {
    public _chart: IChartApi;
    private _pane: IPaneApi<Time>;
    private _finishDrawingCallback: Function | null = null;

    /** 任意 drawing 变更后触发（创建/删除/清空/拖拽结束） */
    public onChanged: Function | null = null;

    private _drawings: Drawing[] = [];
    private _activeDrawing: Drawing | null = null;
    private _isDrawing: boolean = false;
    private _drawingType: (new (...args: any[]) => Drawing) | null = null;

    constructor(chart: IChartApi, pane: IPaneApi<Time>, finishDrawingCallback: Function | null = null) {
        this._chart = chart;
        this._pane = pane;
        this._finishDrawingCallback = finishDrawingCallback;

        // 设置 Drawing 的 drag-end 静态回调
        Drawing._onDragEnd = () => this.onChanged?.();

        this._chart.subscribeClick(this._clickHandler);
        this._chart.subscribeCrosshairMove(this._moveHandler);
    }

    public _clickHandler = (param: MouseEventParams) => this._onClick(param);
    public _moveHandler = (param: MouseEventParams) => this._onMouseMove(param);

    beginDrawing(DrawingType: new (...args: any[]) => Drawing) {
        this._drawingType = DrawingType;
        this._isDrawing = true;
    }

    stopDrawing() {
        this._isDrawing = false;
        this._activeDrawing = null;
    }

    get drawings() {
        return this._drawings;
    }

    addNewDrawing(drawing: Drawing) {
        this._pane.attachPrimitive(drawing);
        this._drawings.push(drawing);
    }

    delete(d: Drawing | null) {
        if (d == null) return;
        const idx = this._drawings.indexOf(d);
        if (idx == -1) return;
        this._drawings.splice(idx, 1)
        d.detach();
        this.onChanged?.();
    }

    clearDrawings() {
        for (const d of this._drawings) d.detach();
        this._drawings = [];
        this.onChanged?.();
    }

    repositionOnTime() {
        for (const drawing of this.drawings) {
            const newPoints = []
            for (const point of drawing.points) {
                if (!point) {
                    newPoints.push(point);
                    continue;
                }
                const logical = point.time ? this._chart.timeScale()
                    .coordinateToLogical(
                        this._chart.timeScale().timeToCoordinate(point.time) || 0
                    ) : point.logical;
                newPoints.push({
                    time: point.time,
                    logical: logical as Logical,
                    price: point.price,
                })
            }
            drawing.updatePoints(...newPoints);
        }
    }

    private _onClick(param: MouseEventParams) {
        if (!this._isDrawing) return;

        const point = Drawing._eventToPoint(param, this._pane);
        if (!point) return;

        if (this._activeDrawing == null) {
            if (this._drawingType == null) return;

            this._activeDrawing = new this._drawingType(this._pane, point, point);
            this._pane.attachPrimitive(this._activeDrawing);
            if (this._drawingType == HorizontalLine) this._onClick(param);
        }
        else {
            this._drawings.push(this._activeDrawing);
            this.stopDrawing();

            if (!this._finishDrawingCallback) return;
            this._finishDrawingCallback();
        }
    }

    private _onMouseMove(param: MouseEventParams) {
        if (!param) return;

        for (const t of this._drawings) t._handleHoverInteraction(param);

        if (!this._isDrawing || !this._activeDrawing) return;

        const point = Drawing._eventToPoint(param, this._pane);
        if (!point) return;
        this._activeDrawing.updatePoints(null, point);
    }
}
