"""
position 参数解析功能测试。

测试:
  1. 字符串格式 → 网格布局（left/right/top/bottom + 弃用警告）
  2. 整数格式 → 网格布局（有效/无效长度/零值）
  3. 元组格式 → 网格布局（有效/无效长度/无效值）
  4. _validate_grid 网格参数验证

Usage:
    python test/test_position.py
"""

import sys, os, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lightweight_charts.util import parse_position, _validate_grid


def log_check(ok: bool, label: str, errors: list, err_key: str = None):
    """统一检查日志。"""
    if ok:
        print(f"      [OK] {label}")
    else:
        print(f"      [FAIL] {label}")
        if err_key:
            errors.append(err_key)
    return ok


def test_string_conversion():
    """字符串格式 → 网格布局转换。"""
    sep = "=" * 60
    print(sep)
    print("  test_string_conversion")
    print(sep)

    errors = []
    all_clean = True

    # left → 1行2列，第1个位置
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = parse_position('left')
    all_clean &= log_check(
        result == {'nrows': 1, 'ncols': 2, 'index': 1},
        "left → 1x2 pos1", errors, "left"
    )

    # right → 1行2列，第2个位置
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = parse_position('right')
    all_clean &= log_check(
        result == {'nrows': 1, 'ncols': 2, 'index': 2},
        "right → 1x2 pos2", errors, "right"
    )

    # top → 2行1列，第1个位置
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = parse_position('top')
    all_clean &= log_check(
        result == {'nrows': 2, 'ncols': 1, 'index': 1},
        "top → 2x1 pos1", errors, "top"
    )

    # bottom → 2行1列，第2个位置
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = parse_position('bottom')
    all_clean &= log_check(
        result == {'nrows': 2, 'ncols': 1, 'index': 2},
        "bottom → 2x1 pos2", errors, "bottom"
    )

    # 弃用警告
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        parse_position('left')
    all_clean &= log_check(
        len(w) == 1 and issubclass(w[-1].category, DeprecationWarning) and "已弃用" in str(w[-1].message),
        "string → DeprecationWarning", errors, "deprecation"
    )

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
    return all_clean


def test_integer_conversion():
    """整数格式 → 网格布局转换。"""
    sep = "=" * 60
    print(sep)
    print("  test_integer_conversion")
    print(sep)

    errors = []
    all_clean = True

    # 有效 3 位整数
    result = parse_position(221)
    all_clean &= log_check(
        result == {'nrows': 2, 'ncols': 2, 'index': 1},
        "221 → 2x2 pos1", errors, "valid_221"
    )

    # 无效长度：2 位
    try:
        parse_position(12)
        all_clean &= log_check(False, "12 should raise ValueError", errors, "len_2")
    except ValueError as e:
        all_clean &= log_check(
            "整数格式必须是3位数字" in str(e),
            f"12 → correct error: {e}", errors, "len_2"
        )

    # 无效长度：4 位
    try:
        parse_position(1234)
        all_clean &= log_check(False, "1234 should raise ValueError", errors, "len_4")
    except ValueError as e:
        all_clean &= log_check(
            "整数格式必须是3位数字" in str(e),
            f"1234 → correct error: {e}", errors, "len_4"
        )

    # 包含零
    try:
        parse_position(101)
        all_clean &= log_check(False, "101 should raise ValueError", errors, "zero")
    except ValueError as e:
        all_clean &= log_check(
            "列数必须是正整数" in str(e),
            f"101 → correct error: {e}", errors, "zero"
        )

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
    return all_clean


def test_tuple_conversion():
    """元组格式 → 网格布局转换。"""
    sep = "=" * 60
    print(sep)
    print("  test_tuple_conversion")
    print(sep)

    errors = []
    all_clean = True

    # 有效元组
    result = parse_position((2, 2, 3))
    all_clean &= log_check(
        result == {'nrows': 2, 'ncols': 2, 'index': 3},
        "(2,2,3) → 2x2 pos3", errors, "valid_tuple"
    )

    # 无效长度：2 元素
    try:
        parse_position((2, 2))
        all_clean &= log_check(False, "(2,2) should raise ValueError", errors, "tuple_len_2")
    except ValueError as e:
        all_clean &= log_check(
            "无效的 position 格式" in str(e),
            f"(2,2) → correct error: {e}", errors, "tuple_len_2"
        )

    # 无效长度：4 元素
    try:
        parse_position((2, 2, 3, 4))
        all_clean &= log_check(False, "(2,2,3,4) should raise ValueError", errors, "tuple_len_4")
    except ValueError as e:
        all_clean &= log_check(
            "无效的 position 格式" in str(e),
            f"(2,2,3,4) → correct error: {e}", errors, "tuple_len_4"
        )

    # 行数为 0
    try:
        parse_position((0, 2, 1))
        all_clean &= log_check(False, "(0,2,1) should raise ValueError", errors, "tuple_row_0")
    except ValueError as e:
        all_clean &= log_check(
            "行数必须是正整数" in str(e),
            f"(0,2,1) → correct error: {e}", errors, "tuple_row_0"
        )

    # 列数为 0
    try:
        parse_position((2, 0, 1))
        all_clean &= log_check(False, "(2,0,1) should raise ValueError", errors, "tuple_col_0")
    except ValueError as e:
        all_clean &= log_check(
            "列数必须是正整数" in str(e),
            f"(2,0,1) → correct error: {e}", errors, "tuple_col_0"
        )

    # 位置索引为 0
    try:
        parse_position((2, 2, 0))
        all_clean &= log_check(False, "(2,2,0) should raise ValueError", errors, "tuple_idx_0")
    except ValueError as e:
        all_clean &= log_check(
            "位置索引必须是正整数" in str(e),
            f"(2,2,0) → correct error: {e}", errors, "tuple_idx_0"
        )

    # 超出网格范围
    try:
        parse_position((2, 2, 5))
        all_clean &= log_check(False, "(2,2,5) should raise ValueError", errors, "tuple_oob")
    except ValueError as e:
        all_clean &= log_check(
            "超出网格范围" in str(e),
            f"(2,2,5) → correct error: {e}", errors, "tuple_oob"
        )

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
    return all_clean


def test_validate_grid():
    """_validate_grid 网格参数验证。"""
    sep = "=" * 60
    print(sep)
    print("  test_validate_grid")
    print(sep)

    errors = []
    all_clean = True

    # 有效参数（不应抛异常）
    try:
        _validate_grid(2, 2, 3)
        all_clean &= log_check(True, "(2,2,3) valid", errors, "valid")
    except Exception as e:
        all_clean &= log_check(False, f"(2,2,3) should not raise: {e}", errors, "valid")

    # 无效行数：0
    try:
        _validate_grid(0, 2, 1)
        all_clean &= log_check(False, "(0,2,1) should raise", errors, "nrows_0")
    except ValueError as e:
        all_clean &= log_check(
            "行数必须是正整数" in str(e),
            f"(0,2,1) → correct error: {e}", errors, "nrows_0"
        )

    # 无效行数：-1
    try:
        _validate_grid(-1, 2, 1)
        all_clean &= log_check(False, "(-1,2,1) should raise", errors, "nrows_neg")
    except ValueError as e:
        all_clean &= log_check(
            "行数必须是正整数" in str(e),
            f"(-1,2,1) → correct error: {e}", errors, "nrows_neg"
        )

    # 无效列数：0
    try:
        _validate_grid(2, 0, 1)
        all_clean &= log_check(False, "(2,0,1) should raise", errors, "ncols_0")
    except ValueError as e:
        all_clean &= log_check(
            "列数必须是正整数" in str(e),
            f"(2,0,1) → correct error: {e}", errors, "ncols_0"
        )

    # 无效列数：-1
    try:
        _validate_grid(2, -1, 1)
        all_clean &= log_check(False, "(2,-1,1) should raise", errors, "ncols_neg")
    except ValueError as e:
        all_clean &= log_check(
            "列数必须是正整数" in str(e),
            f"(2,-1,1) → correct error: {e}", errors, "ncols_neg"
        )

    # 无效索引：0
    try:
        _validate_grid(2, 2, 0)
        all_clean &= log_check(False, "(2,2,0) should raise", errors, "idx_0")
    except ValueError as e:
        all_clean &= log_check(
            "位置索引必须是正整数" in str(e),
            f"(2,2,0) → correct error: {e}", errors, "idx_0"
        )

    # 无效索引：-1
    try:
        _validate_grid(2, 2, -1)
        all_clean &= log_check(False, "(2,2,-1) should raise", errors, "idx_neg")
    except ValueError as e:
        all_clean &= log_check(
            "位置索引必须是正整数" in str(e),
            f"(2,2,-1) → correct error: {e}", errors, "idx_neg"
        )

    # 超出范围
    try:
        _validate_grid(2, 2, 5)
        all_clean &= log_check(False, "(2,2,5) should raise", errors, "idx_oob")
    except ValueError as e:
        all_clean &= log_check(
            "超出网格范围" in str(e),
            f"(2,2,5) → correct error: {e}", errors, "idx_oob"
        )

    print()
    if all_clean:
        print("  RESULT: PASS")
    else:
        print(f"  RESULT: FAIL ({len(errors)} errors)")
    return all_clean


if __name__ == '__main__':
    results = []
    results.append(test_string_conversion())
    results.append(test_integer_conversion())
    results.append(test_tuple_conversion())
    results.append(test_validate_grid())

    print()
    print("=" * 60)
    if all(results):
        print("  OVERALL: ALL PASS")
    else:
        print(f"  OVERALL: {sum(results)}/{len(results)} passed")
    print("=" * 60)
