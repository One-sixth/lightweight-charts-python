"""调试 crosshair sync 是否正常工作"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import pandas as pd, numpy as np
from lightweight_charts import Chart


def main():
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=50, freq='D')
    p = 100.0
    rows = []
    for d in dates:
        o = p; h = p+abs(np.random.normal(0,1.5)); l = p-abs(np.random.normal(0,1.5)); c = p+np.random.normal(0,1)
        rows.append({'time': d, 'open': round(o,2), 'high': round(h,2), 'low': round(l,2), 'close': round(c,2), 'volume': int(np.random.randint(1000,5000))})
        p = c
    bars = pd.DataFrame(rows)

    chart = Chart(width=1000, height=400, position=(1,2,1))
    sub = chart.create_subchart(position=(1,2,2))
    chart.set(bars); sub.set(bars)
    chart.legend(visible=True); sub.legend(visible=True)

    chart.show(block=False)
    time.sleep(1)

    # 检查 sync 前的状态
    before = chart.win.run_script_and_get('''
    JSON.stringify(Lib.Handler._all.map(h => ({
        id: h.id,
        synced: h._syncedHandlers || [],
        cbKeys: Object.keys(h._syncCallbacks || {})
    })))
    ''', timeout=3)
    print("Before sync_charts:", before)

    # 执行同步
    chart.sync_charts()
    time.sleep(0.5)

    # 检查 sync 后的状态
    after = chart.win.run_script_and_get('''
    JSON.stringify(Lib.Handler._all.map(h => ({
        id: h.id,
        synced: h._syncedHandlers || [],
        cbKeys: Object.keys(h._syncCallbacks || {})
    })))
    ''', timeout=3)
    print("After sync_charts:", after)

    # 检查 sub chart legend 状态
    info = chart.win.run_script_and_get('''
    JSON.stringify({
        mainId: window.Chart_1 ? window.Chart_1.id : 'NOT FOUND',
        subId: window.AbstractChart_3 ? window.AbstractChart_3.id : 'NOT FOUND',
        subHasLegend: !!(window.AbstractChart_3 && window.AbstractChart_3.legend),
        subLegendDivExists: !!(window.AbstractChart_3 && window.AbstractChart_3.legend && window.AbstractChart_3.legend.div),
        subLegendDisplay: window.AbstractChart_3 && window.AbstractChart_3.legend && window.AbstractChart_3.legend.div ? window.AbstractChart_3.legend.div.style.display : 'N/A'
    })
    ''', timeout=3)
    print("Chart info:", info)

    # 检查 sync callback 详情
    sync_detail = chart.win.run_script_and_get('''
    (() => {
        const main = Lib.Handler._all[0];
        const sub = Lib.Handler._all[1];
        if (!main || !sub) return JSON.stringify({error: 'handlers not found'});
        const hasSync = main._syncedHandlers && main._syncedHandlers.includes(sub.id);
        const cb = main._syncCallbacks && main._syncCallbacks[sub.id];
        return JSON.stringify({
            mainId: main.id,
            subId: sub.id,
            hasSync: hasSync,
            hasCallback: !!cb,
            hasCrosshairCb: !!(cb && cb.crosshair),
            syncedHandlers: main._syncedHandlers || [],
            cbKeys: Object.keys(main._syncCallbacks || {})
        });
    })()
    ''', timeout=3)
    print("Sync detail:", sync_detail)

    print("\n请在浏览器中移动鼠标到左侧 main chart 上，观察右侧 sub chart 的十字光标是否同步移动")
    print("按 Enter 退出...")
    input()
    chart.close()


if __name__ == '__main__':
    main()
