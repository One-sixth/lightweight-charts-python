import {
    IChartApi,
    IPaneApi,
    IPanePrimitive,
    PaneAttachedParameter,
    Time,
} from 'lightweight-charts';
import { ensureDefined } from './helpers/assertions';

/**
 * PanePluginBase — 实现 IPanePrimitive 接口的基类。
 *
 * 与 PluginBase（ISeriesPrimitive）的区别：
 * - 附着到 pane 而非 series
 * - 构造时传入 pane 引用（PaneAttachedParameter 不含 pane）
 * - 没有 series 引用、没有 priceAxisViews/timeAxisViews
 */
export abstract class PanePluginBase implements IPanePrimitive<Time> {
    private _chart: IChartApi | undefined = undefined;
    private _pane: IPaneApi<Time>;
    private _requestUpdate?: () => void;

    constructor(pane: IPaneApi<Time>) {
        this._pane = pane;
    }

    protected requestUpdate(): void {
        if (this._requestUpdate) this._requestUpdate();
    }

    public attached({ chart, requestUpdate }: PaneAttachedParameter<Time>) {
        this._chart = chart;
        this._requestUpdate = requestUpdate;
        this.requestUpdate();
    }

    public detached() {
        this._chart = undefined;
        this._requestUpdate = undefined;
    }

    public get chart(): IChartApi {
        return ensureDefined(this._chart);
    }

    public get pane(): IPaneApi<Time> {
        return this._pane;
    }
}
