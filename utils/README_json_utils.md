# JSON工具类使用说明

## 概述

`json_utils.py` 提供了一套完整的JSON处理工具，包括格式验证、错误修复、安全解析等功能。

## 主要功能

### 1. JSON格式验证
```python
from utils.json_utils import is_json

# 检查字符串是否为有效JSON
is_valid = is_json('{"name": "test"}')  # True
is_valid = is_json('{name: "test"}')    # False
```

### 2. 安全JSON解析
```python
from utils.json_utils import parse_json

# 基础解析
data = parse_json('{"name": "test", "value": 123}')
# 返回: {'name': 'test', 'value': 123}

# 自动修复常见错误
data = parse_json('{"name": "test", "value": 123,}')  # 末尾多余逗号
data = parse_json('{name: "test", value: 123}')      # 键名缺少引号
data = parse_json('{"name": "test"; "value": 123}')  # 分号问题

# 从文本中提取JSON
data = parse_json('Some text {"name": "test"} more text')
# 返回: {'name': 'test'}
```

### 3. JSON格式修复
```python
from utils.json_utils import fix_json

# 修复常见格式问题
fixed = fix_json('{"name": "test", "value": 123,}')
# 返回: '{"name": "test", "value": 123}'

fixed = fix_json('{name: "test", value: 123}')
# 返回: '{"name": "test", "value": 123}'
```

## JSONUtils类方法

### 静态方法

#### `is_valid_json(text: str) -> bool`
判断字符串是否是有效的JSON格式。

#### `extract_json_from_text(text: str) -> Optional[str]`
从文本中提取JSON字符串部分。

#### `fix_common_json_issues(text: str) -> str`
修复常见的JSON格式问题：
- 将 `";` 替换为 `",`
- 将 `';` 替换为 `',`
- 为缺少引号的键名添加引号
- 移除对象/数组末尾的多余逗号

#### `safe_parse_json(text: str, fix_errors: bool = True) -> Optional[Dict[str, Any]]`
安全解析JSON字符串，支持自动错误修复。

#### `parse_json_with_fallback(text: str, fallback_value: Any = None) -> Any`
解析JSON，失败时返回备用值。

#### `format_json(data: Union[Dict, str], indent: int = 2) -> str`
格式化JSON数据，输出美观的JSON字符串。

#### `validate_json_structure(data: Dict[str, Any], required_keys: list = None) -> bool`
验证JSON数据结构是否包含必需的键。

## 便捷函数

```python
from utils.json_utils import is_json, parse_json, fix_json

# 快捷函数
is_json(text)           # 等同于 JSONUtils.is_valid_json(text)
parse_json(text)        # 等同于 JSONUtils.safe_parse_json(text)
fix_json(text)          # 等同于 JSONUtils.fix_common_json_issues(text)
```

## 在项目中的使用

### structured_data.py中的应用
```python
from utils.json_utils import parse_json

def _parse_ai_json(self, ai_result: str) -> Dict[str, Any]:
    """解析AI返回的JSON字符串"""
    if not ai_result or not ai_result.strip():
        raise ValueError("AI结果为空")
    
    # 使用JSON工具类进行解析
    parsed_data = parse_json(ai_result, fix_errors=True)
    
    if parsed_data is None:
        raise ValueError(f"JSON解析失败: {ai_result[:100]}...")
    
    return parsed_data
```

## 错误处理

- 所有方法都有完善的错误处理机制
- 解析失败时会记录详细的调试信息
- 支持优雅降级，避免程序崩溃

## 日志记录

工具类使用标准的Python日志系统：
- `DEBUG`: 详细的解析过程信息
- `WARNING`: 解析失败或数据问题警告
- `ERROR`: 严重错误信息

## 测试

运行测试：
```bash
python utils/json_utils.py
```

测试包含各种边界情况和常见的JSON格式问题。

## 注意事项

1. 键名自动修复功能相对简单，复杂情况可能需要手动处理
2. 工具类优先使用Python标准库功能
3. 所有修复操作都是非破坏性的，原始数据不会被修改
4. 建议在生产环境中启用详细日志以便调试
