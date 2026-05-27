"""测试 position 参数解析功能"""
import warnings
import pytest
from lightweight_charts.util import parse_position, _validate_grid


class TestStringConversion:
    """测试字符串格式到网格布局的转换"""
    
    def test_left_conversion(self):
        """测试 'left' → 1行2列，第1个位置"""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = parse_position('left')
            assert result == {'nrows': 1, 'ncols': 2, 'index': 1}
    
    def test_right_conversion(self):
        """测试 'right' → 1行2列，第2个位置"""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = parse_position('right')
            assert result == {'nrows': 1, 'ncols': 2, 'index': 2}
    
    def test_top_conversion(self):
        """测试 'top' → 2行1列，第1个位置"""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = parse_position('top')
            assert result == {'nrows': 2, 'ncols': 1, 'index': 1}
    
    def test_bottom_conversion(self):
        """测试 'bottom' → 2行1列，第2个位置"""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = parse_position('bottom')
            assert result == {'nrows': 2, 'ncols': 1, 'index': 2}
    
    def test_string_deprecation_warning(self):
        """测试字符串格式发出弃用警告"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            parse_position('left')
            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "已弃用" in str(w[-1].message)


class TestIntegerConversion:
    """测试整数格式到网格布局的转换"""
    
    def test_valid_integer(self):
        """测试有效的3位整数"""
        result = parse_position(221)
        assert result == {'nrows': 2, 'ncols': 2, 'index': 1}
    
    def test_invalid_integer_length(self):
        """测试无效长度的整数"""
        with pytest.raises(ValueError, match="整数格式必须是3位数字"):
            parse_position(12)
        
        with pytest.raises(ValueError, match="整数格式必须是3位数字"):
            parse_position(1234)
    
    def test_invalid_integer_zero(self):
        """测试包含零的整数"""
        with pytest.raises(ValueError, match="列数必须是正整数"):
            parse_position(101)


class TestTupleConversion:
    """测试元组格式到网格布局的转换"""
    
    def test_valid_tuple(self):
        """测试有效的元组"""
        result = parse_position((2, 2, 3))
        assert result == {'nrows': 2, 'ncols': 2, 'index': 3}
    
    def test_invalid_tuple_length(self):
        """测试无效长度的元组"""
        with pytest.raises(ValueError, match="无效的 position 格式"):
            parse_position((2, 2))
        
        with pytest.raises(ValueError, match="无效的 position 格式"):
            parse_position((2, 2, 3, 4))
    
    def test_invalid_tuple_values(self):
        """测试元组中包含无效值"""
        with pytest.raises(ValueError, match="行数必须是正整数"):
            parse_position((0, 2, 1))
        
        with pytest.raises(ValueError, match="列数必须是正整数"):
            parse_position((2, 0, 1))
        
        with pytest.raises(ValueError, match="位置索引必须是正整数"):
            parse_position((2, 2, 0))
        
        with pytest.raises(ValueError, match="超出网格范围"):
            parse_position((2, 2, 5))


class TestValidation:
    """测试网格参数验证"""
    
    def test_valid_grid(self):
        """测试有效的网格参数"""
        # 不应抛出异常
        _validate_grid(2, 2, 3)
    
    def test_invalid_nrows(self):
        """测试无效的行数"""
        with pytest.raises(ValueError, match="行数必须是正整数"):
            _validate_grid(0, 2, 1)
        
        with pytest.raises(ValueError, match="行数必须是正整数"):
            _validate_grid(-1, 2, 1)
    
    def test_invalid_ncols(self):
        """测试无效的列数"""
        with pytest.raises(ValueError, match="列数必须是正整数"):
            _validate_grid(2, 0, 1)
        
        with pytest.raises(ValueError, match="列数必须是正整数"):
            _validate_grid(2, -1, 1)
    
    def test_invalid_index(self):
        """测试无效的位置索引"""
        with pytest.raises(ValueError, match="位置索引必须是正整数"):
            _validate_grid(2, 2, 0)
        
        with pytest.raises(ValueError, match="位置索引必须是正整数"):
            _validate_grid(2, 2, -1)
        
        with pytest.raises(ValueError, match="超出网格范围"):
            _validate_grid(2, 2, 5)
