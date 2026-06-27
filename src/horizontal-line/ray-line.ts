import {
    DeepPartial,
    IPaneApi,
    MouseEventParams,
    Time,
} from "lightweight-charts";
import { DiffPoint, Point } from "../drawing/data-source";
import { DrawingOptions } from "../drawing/options";
import { HorizontalLine } from "./horizontal-line";

export class RayLine extends HorizontalLine {
    _type = 'RayLine';

    constructor(pane: IPaneApi<Time>, point: Point, options: DeepPartial<DrawingOptions>) {
        super(pane, {...point}, options);
        this._point.time = point.time;
    }

    public updatePoints(...points: (Point | null)[]) {
        for (const p of points) if (p) this._point = p;
        this.requestUpdate();
    }

    _onDrag(diff: DiffPoint) {
        this._addDiffToPoint(this._point, diff.logical, diff.price);
        this.requestUpdate();
    }

    _mouseIsOverDrawing(param: MouseEventParams, tolerance = 4) {
        if (!param.point) return false;
        const series = this.pane.getSeries();
        const s = series && series.length > 0 ? series[0] : null;
        if (!s) return false;
        const y = s.priceToCoordinate(this._point.price);
        const x = this._point.time ? this.chart.timeScale().timeToCoordinate(this._point.time) : null;

        // 坐标转换失败时（点在数据范围外），仍用 param.point 近似检测
        const yOk = y !== null ? Math.abs(y - param.point.y) < tolerance : true;
        const xOk = x !== null ? param.point.x > x - tolerance : true;
        return yOk && xOk;
    }
}
