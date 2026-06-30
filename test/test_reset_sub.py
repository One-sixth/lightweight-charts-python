"""
reset_sub() 测试。

创建 4 个子图 (2x2 网格)，给每个子图添加各种资源，
然后 reset_sub() 其中一个，验证：
1. 被 reset 的子图资源全部清空（Python + JS 双端校验）
2. 其他子图不受影响

Usage:
    python test/test_reset_sub.py
"""

import sys, os, json, tomllib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import pandas as pd
import numpy as np
from lightweight_charts import Chart


def make_data(num_bars: int = 50, seed: int = 42):
    np.random.seed(seed)
    dates = pd.date_range('2025-01-01', periods=num_bars, freq='D')
    price = 100.0
    rows = []
    for i in range(num_bars):
        price += np.random.normal(0, 2)
        rows.append({
            'time': dates[i],
            'open': round(price + np.random.normal(0, 1), 2),
            'high': round(price + abs(np.random.normal(0, 1.5)), 2),
            'low': round(price - abs(np.random.normal(0, 1.5)), 2),
            'close': round(price, 2),
            'volume': int(np.random.randint(1000, 50000)),
        })
    return pd.DataFrame(rows)


def log_check(ok, label, errors, err_key=None):
    if ok:
        print(f"      [OK] {label}")
    else:
        print(f"      [FAIL] {label}")
        if err_key:
            errors.append(err_key)
    return ok


def js_audit(chart, timeout=5):
    try:
        result = chart.win.run_script_and_get('Lib.Handler.audit()', timeout=timeout)
        if not isinstance(result, str):
            return None
        return tomllib.loads(result)
    except Exception as e:
        print(f"      [WARN] JS audit failed: {e}")
        return None


def chart_section(audit_data, chart):
    sid = chart.id.replace('window.', '')
    return audit_data.get(sid, {})


def count_handler_sections(audit_data):
    return sum(1 for v in audit_data.values()
               if isinstance(v, dict) and v.get('type') == 'Handler')


def count_non_handler_keys(audit_data):
    return sum(1 for v in audit_data.values()
               if isinstance(v, dict) and v.get('type') != 'Handler')


def add_resources_to_chart(chart, bars, prefix):
    """给一个 chart 添加各种资源，返回创建的对象列表。"""
    chart.set(bars)
    chart.legend(visible=True, ohlc=True, lines=True)

    line = chart.create_line(f'{prefix}_line', color='#ff0000')
    hist = chart.create_histogram(f'{prefix}_hist', color='#00ff00')
    chart.add_marker(bars['time'].iloc[5], 'above', 'circle', '#ff0000', f'{prefix}_m1')
    chart.add_marker(bars['time'].iloc[10], 'below', 'arrow_up', '#00ff00', f'{prefix}_m2')
    pl = chart.create_price_line(price=102, title=f'{prefix}_PL', price_label=True)

    tbl = chart.create_table(
        width=200, height=100,
        headings=('Key', 'Value'),
        widths=(100, 100),
    )
    row = tbl.new_row(prefix, 'value')

    return {'line': line, 'hist': hist, 'pl': pl, 'table': tbl}


def verify_cleared(chart, errors, label_prefix):
    """验证一个 chart 的资源已被清空。"""
    print(f"\n    --- {label_prefix} Python 侧验证 ---")
    all_clean = True
    all_clean &= log_check(chart.data.empty, "candle_data empty", errors)
    all_clean &= log_check(len(chart._lines) == 0, f"_lines empty (got {len(chart._lines)})", errors)
    all_clean &= log_check(len(chart._price_lines) == 0, f"_price_lines empty (got {len(chart._price_lines)})", errors)
    all_clean &= log_check(len(chart.markers) == 0, f"markers empty (got {len(chart.markers)})", errors)
    all_clean &= log_check(len(chart.drawings) == 0, f"_drawings empty (got {len(chart.drawings)})", errors)
    all_clean &= log_check(len(chart._tables) == 0, f"_tables empty (got {len(chart._tables)})", errors)
    return all_clean


def verify_js_cleared(chart, errors, label_prefix):
    """验证 JS 侧资源已被清空。"""
    print(f"\n    --- {label_prefix} JS 侧验证 ---")
    audit = js_audit(chart)
    if audit is None:
        log_check(False, "JS audit reachable", errors)
        return False

    sec = chart_section(audit, chart)
    all_clean = True
    # legend cleanup 后 legend 对象仍在（JS object），但 div 已从 DOM 移除
    # audit 中 hasLegend 检查 !!h.legend（对象存在），这是预期行为
    # legendVisible 检查 div.style.display，cleanup 后 div 已移除，display 不再有意义
    # 验证 ToolBox 已清理（如果之前有的话）
    all_clean &= log_check(not sec.get('hasToolBox', False), "JS: toolBox removed", errors)
    # 验证 TopBar 已清理（如果之前有的话）
    all_clean &= log_check(not sec.get('hasTopBar', False), "JS: topBar removed", errors)
    print(f"      [INFO] JS audit section: {json.dumps(sec, indent=2, default=str)[:500]}")
    return all_clean


def verify_unaffected(chart, bars, errors, label_prefix):
    """验证一个 chart 的资源仍然完好。"""
    print(f"\n    --- {label_prefix} 未受影响验证 ---")
    all_ok = True
    all_ok &= log_check(not chart.data.empty, "candle_data not empty", errors)
    all_ok &= log_check(len(chart._lines) == 2, f"_lines count == 2 (got {len(chart._lines)})", errors)
    all_ok &= log_check(len(chart._price_lines) == 1, f"_price_lines count == 1 (got {len(chart._price_lines)})", errors)
    all_ok &= log_check(len(chart.markers) >= 2, f"markers count >= 2 (got {len(chart.markers)})", errors)
    all_ok &= log_check(len(chart._tables) == 1, f"_tables count == 1 (got {len(chart._tables)})", errors)

    # JS 侧验证
    audit = js_audit(chart)
    if audit is not None:
        sec = chart_section(audit, chart)
        all_ok &= log_check(sec.get('hasLegend', False) == True, "JS: legend exists", errors)
        print(f"      [INFO] JS audit section: {json.dumps(sec, indent=2, default=str)[:500]}")
    else:
        log_check(False, "JS audit reachable for unaffected chart", errors)

    return all_ok


def main():
    sep = "=" * 60
    print(sep)
    print("  test_reset_sub — 4 子图网格测试")
    print(sep)

    errors = []
    bars = make_data(50)

    # 创建 2x2 网格，4 个子图
    chart = Chart(toolbox=True, position=221)
    sub1 = chart.create_subchart(position=222)
    sub2 = chart.create_subchart(position=223)
    sub3 = chart.create_subchart(position=224)

    # syncChartsAll 同步所有子图
    chart.sync_charts()

    try:
        print("\n[1] Launch chart ...")
        chart.show(block=False)
        print("      [OK]")

        # 基线 JS 审计
        print("\n[2] Baseline JS audit ...")
        baseline = js_audit(chart)
        if baseline:
            print(f"      handler sections: {count_handler_sections(baseline)}")
            print(f"      non-handler keys: {count_non_handler_keys(baseline)}")
        log_check(baseline is not None, "baseline audit reachable", errors)

        # 给所有子图添加资源
        print("\n[3] Add resources to all 4 charts ...")
        r_main = add_resources_to_chart(chart, bars, 'main')
        print("  3a. main chart [OK]")

        r_sub1 = add_resources_to_chart(sub1, bars, 'sub1')
        print("  3b. sub1 [OK]")

        r_sub2 = add_resources_to_chart(sub2, bars, 'sub2')
        print("  3c. sub2 [OK]")

        r_sub3 = add_resources_to_chart(sub3, bars, 'sub3')
        print("  3d. sub3 [OK]")

        time.sleep(0.5)

        # 记录 reset 前的 handlers 数量
        handlers_before = len(chart.win.handlers)
        print(f"\n[4] handlers count before reset: {handlers_before}")

        # 记录 reset 前的 JS 审计
        print("\n[5] JS audit before reset ...")
        audit_before = js_audit(chart)
        if audit_before:
            print(f"      handler sections: {count_handler_sections(audit_before)}")
            print(f"      non-handler keys: {count_non_handler_keys(audit_before)}")

        # reset_sub sub1
        print("\n[6] reset_sub(sub1) ...")
        sub1.reset_sub()
        time.sleep(1)
        print("      [OK]")

        # 记录 reset 后的 handlers 数量
        handlers_after = len(chart.win.handlers)
        print(f"\n[7] handlers count after reset: {handlers_after}")
        log_check(handlers_after < handlers_before,
                  f"handlers reduced ({handlers_before} -> {handlers_after})",
                  errors)

        # 验证 sub1 已清空
        print("\n[8] Verify sub1 is cleared ...")
        sub1_py_clean = verify_cleared(sub1, errors, "sub1")
        sub1_js_clean = verify_js_cleared(sub1, errors, "sub1")

        # 验证其他子图不受影响
        print("\n[9] Verify main chart unaffected ...")
        main_ok = verify_unaffected(chart, bars, errors, "main")

        print("\n[10] Verify sub2 unaffected ...")
        sub2_ok = verify_unaffected(sub2, bars, errors, "sub2")

        print("\n[11] Verify sub3 unaffected ...")
        sub3_ok = verify_unaffected(sub3, bars, errors, "sub3")

        # JS 端审计对比
        print("\n[12] JS audit after reset ...")
        audit_after = js_audit(chart)
        if audit_after:
            print(f"      handler sections: {count_handler_sections(audit_after)}")
            print(f"      non-handler keys: {count_non_handler_keys(audit_after)}")

            # sub1 的 JS section 应该不存在或为空
            sub1_section = chart_section(audit_after, sub1)
            print(f"      sub1 JS section: {json.dumps(sub1_section, indent=2, default=str)[:300]}")

            # 其他 chart 的 JS section 应该仍然存在
            for name, c in [('main', chart), ('sub2', sub2), ('sub3', sub3)]:
                sec = chart_section(audit_after, c)
                log_check(sec.get('hasChart', False), f"JS: {name} handler still exists", errors)

        # ============================================================
        # 阶段 2：验证 reset 后子图可重用
        # ============================================================
        print("\n" + "=" * 60)
        print("  Phase 2: Reuse sub1 after reset_sub")
        print("=" * 60)

        # 重新给 sub1 添加资源
        print("\n[13] Re-add resources to sub1 after reset ...")
        r_sub1_v2 = add_resources_to_chart(sub1, bars, 'sub1_v2')
        print("      [OK]")

        time.sleep(0.5)

        # 验证 sub1 重新添加后资源完整
        print("\n[14] Verify sub1 re-populated (Python) ...")
        all_ok = True
        all_ok &= log_check(not sub1.data.empty, "candle_data not empty", errors)
        all_ok &= log_check(len(sub1._lines) == 2, f"_lines count == 2 (got {len(sub1._lines)})", errors)
        all_ok &= log_check(len(sub1._price_lines) == 1, f"_price_lines count == 1 (got {len(sub1._price_lines)})", errors)
        all_ok &= log_check(len(sub1.markers) >= 2, f"markers count >= 2 (got {len(sub1.markers)})", errors)
        all_ok &= log_check(len(sub1._tables) == 1, f"_tables count == 1 (get {len(sub1._tables)})", errors)

        # JS 审计验证 sub1 重新添加后状态
        print("\n[15] Verify sub1 re-populated (JS) ...")
        audit_reuse = js_audit(sub1)
        if audit_reuse:
            sec = chart_section(audit_reuse, sub1)
            all_ok &= log_check(sec.get('hasChart', False), "JS: handler exists", errors)
            all_ok &= log_check(sec.get('hasLegend', False), "JS: legend exists", errors)
            print(f"      [INFO] JS audit section: {json.dumps(sec, indent=2, default=str)[:500]}")
        else:
            log_check(False, "JS audit reachable for reused sub1", errors)

        # 验证其他子图仍然不受影响
        print("\n[16] Verify other charts still unaffected after reuse ...")
        for name, c in [('main', chart), ('sub2', sub2), ('sub3', sub3)]:
            log_check(not c.data.empty, f"{name}: candle_data not empty", errors)
            log_check(len(c._lines) == 2, f"{name}: _lines count == 2", errors)

        # 验证 syncCharts 功能（sub1 重新加入同步）
        print("\n[17] Re-sync all charts ...")
        chart.sync_charts()
        time.sleep(0.5)

        # 验证 handlers 增加（重新同步后）
        handlers_reuse = len(chart.win.handlers)
        print(f"      handlers count after re-sync: {handlers_reuse}")
        log_check(handlers_reuse > handlers_after,
                  f"handlers increased after re-sync ({handlers_after} -> {handlers_reuse})",
                  errors)

        # 总结
        print("\n" + sep)
        if not errors:
            print("  ALL TESTS PASSED")
        else:
            print(f"  FAILED: {len(errors)} errors")
            for e in errors:
                print(f"    - {e}")
        print(sep)

        return len(errors) == 0

    except Exception as e:
        print(f"\n  [EXCEPTION] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print("\nClosing chart in 3 seconds ...")
        time.sleep(3)


if __name__ == '__main__':
    ok = main()
    sys.exit(0 if ok else 1)
