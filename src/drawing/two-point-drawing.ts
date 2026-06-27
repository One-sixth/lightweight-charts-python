import { IPaneApi, Time } from 'lightweight-charts';
import { Point } from './data-source';
import { DrawingOptions } from './options';
import { Drawing } from './drawing';
import { TwoPointDrawingPaneView } from './pane-view';


export abstract class TwoPointDrawing extends Drawing {
    _paneViews: TwoPointDrawingPaneView[] = [];

    protected _hovered: boolean = false;

    constructor(
        pane: IPaneApi<Time>,
        p1: Point,
        p2: Point,
        options?: Partial<DrawingOptions>
    ) {
        super(pane, options);
        this.points.push(p1);
        this.points.push(p2);
    }

    setFirstPoint(point: Point) {
        this.updatePoints(point);
    }

    setSecondPoint(point: Point) {
        this.updatePoints(null, point);
    }

    get p1() { return this.points[0]; }
    get p2() { return this.points[1]; }

    get hovered() { return this._hovered; }
}
