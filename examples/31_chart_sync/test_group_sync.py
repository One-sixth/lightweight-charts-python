"""
Group-based sync smoke test

测试场景:
1. 基本组同步：两个子图加入同一组
2. reset_sub + set 自动恢复同步
3. 混合 sync_crosshairs_only
4. 多组独立同步
"""
import pandas as pd
import numpy as np
from lightweight_charts import Chart


def gen_data(seed, base=100, n=60):
    np.random.seed(seed)
    dates = pd.date_range('2024-01-01', periods=n, freq='D')
    p = base
    rows = []
    for d in dates:
        o, h, l, c = p, p+abs(np.random.normal(0,1)), p-abs(np.random.normal(0,1)), p+np.random.normal(0,0.5)
        rows.append({'time': d, 'open': round(o,2), 'high': round(h,2),
                      'low': round(l,2), 'close': round(c,2),
                      'volume': int(np.random.randint(1000,5000))})
        p = c
    return pd.DataFrame(rows)


def main():
    df1 = gen_data(1, 100)
    df2 = gen_data(2, 50)
    df3 = gen_data(3, 200)

    # ── 场景 1+2: 基本组同步 + reset 恢复 ──
    # 3 图水平排列，A 是 main，B 和 C 加入 "group1"
    chart_a = Chart(width=1400, height=350, title='A (main, no sync)', position=(2, 3, 1))
    chart_a.legend(visible=True)

    chart_b = chart_a.create_subchart(
        position=(2, 3, 2), sync_id='group1')
    chart_b.set(df2)
    chart_b.legend(visible=True)

    chart_c = chart_a.create_subchart(
        position=(2, 3, 3), sync_id='group1')
    chart_c.set(df3)
    chart_c.legend(visible=True)

    chart_a.set(df1)

    # A 的 topbar: reset B 按钮
    def on_reset_b(chart):
        chart_b.reset_sub()
        chart_b.set(df2)
        chart_b.legend(visible=True)
        print('[Reset B] Done - test B<->C sync')
    chart_a.topbar.textbox('info', 'Click Reset B, then test B<->C sync', align='left')
    # chart_a.topbar.button('reset_b', 'Reset B', func=on_reset_b)

    # ── 场景 3: 混合 sync_crosshairs_only ──
    # D 和 E 加入 "group2"，D=full sync, E=crosshair only
    chart_d = chart_a.create_subchart(
        position=(2, 3, 4), sync_id='group2')
    chart_d.set(df1.copy())
    chart_d.legend(visible=True)

    chart_e = chart_a.create_subchart(
        position=(2, 3, 5), sync_id='group2', sync_crosshairs_only=True)
    chart_e.set(df2.copy())
    chart_e.legend(visible=True)

    chart_f = chart_a.create_subchart(
        position=(2, 3, 6), sync_id='group2')
    chart_f.set(df3.copy())
    chart_f.legend(visible=True)

    chart_d.topbar.textbox('grp2', 'group2: D=full, E=crosshair, F=full', align='left')

    print('=== Group Sync Test ===')
    print('Layout (2 rows x 3 cols):')
    print('  Row 1: A(no sync) | B(group1) | C(group1)')
    print('  Row 2: D(group2)  | E(group2) | F(group2)')
    print()
    print('Test steps:')
    print('  1. Move mouse on B -> C should sync (group1)')
    print('  2. Click [Reset B] -> B re-fills, B<->C still syncs')
    print('  3. Move mouse on D -> E,F should sync crosshair (group2)')
    print('  4. Scroll D -> E should NOT scroll (crosshair only), F should scroll')
    print('  5. A is independent, never syncs with anyone')

    chart_a.show(block=True)


if __name__ == '__main__':
    main()
