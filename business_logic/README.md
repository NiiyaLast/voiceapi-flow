# business_logic 目录结构设计

## 📁 目录结构

```
business_logic/
├── __init__.py                         # 业务逻辑模块初始化
├── business_logic.py                   # 通用业务逻辑路由器
├── task1/                              # 任务模块
│   ├── __init__.py                     # 模块初始化，导出所有组件
│   ├── processor.py                    # 任务主处理器
│   ├── excel_ai_processor.py           # Excel数据处理与AI调用
│   └── score_dimension_expander.py     # 评分维度展开器
└── [future_tasks]/                     # 未来其他任务模块
    ├── __init__.py
    └── processor.py
```

## 🏗️ 设计原则

### 1. 任务特定目录
- 每个任务都有自己的子目录（如 `task1/`）
- 任务目录包含该任务所需的所有组件和工具
- 便于任务的独立开发、测试和维护

### 2. 标准化命名
- 每个任务目录都包含 `processor.py` 作为主处理器
- 每个任务目录都有 `__init__.py` 导出主要类
- 便于统一的导入和使用

### 3. 工具组织
在每个任务目录下，可以添加：
- `tools/` - 任务特定的工具模块
- `validators/` - 数据验证器
- `transformers/` - 数据转换器
- `constants.py` - 任务常量
- `exceptions.py` - 任务特定异常

## 📋 使用方式

### 路由器导入
```python
# business_logic.py 中的路由
if self.task_name == "task1":
    from .task1 import Task1Processor
    return Task1Processor(self.config, self.task_config)
```

### 直接导入
```python
# 在其他模块中直接使用
from business_logic.task1 import Task1Processor
```

## 🔧 扩展新任务

### 1. 创建任务目录
```bash
mkdir business_logic/new_task_name
```

### 2. 创建必要文件
```python
# business_logic/new_task_name/__init__.py
from .processor import NewTaskProcessor
__all__ = ['NewTaskProcessor']

# business_logic/new_task_name/processor.py
class NewTaskProcessor:
    def __init__(self, config, task_config):
        # 初始化逻辑
        pass
    
    def execute_task_flow(self, input_data):
        # 任务执行逻辑
        pass
```

### 3. 更新路由器
```python
# business_logic/business_logic.py
def route_to_processor(self):
    if self.task_name == "task1":
        from .task1 import Task1Processor
        return Task1Processor(self.config, self.task_config)
    elif self.task_name == "new_task_name":
        from .new_task_name import NewTaskProcessor
        return NewTaskProcessor(self.config, self.task_config)
    else:
        raise ValueError(f"不支持的任务类型: {self.task_name}")
```

## 💡 优势

1. **模块化**: 每个任务独立管理，互不干扰
2. **可扩展**: 新增任务只需创建新目录
3. **标准化**: 统一的目录结构和命名规范
4. **维护性**: 任务相关代码集中管理
5. **测试友好**: 每个任务可以独立测试

## 🎯 未来规划

### task1 目录可能包含的工具：
- `tools/excel_processor.py` - Excel处理工具
- `tools/score_calculator.py` - 评分计算工具
- `tools/data_validator.py` - 数据验证工具
- `transformers/ai_result_transformer.py` - AI结果转换器
- `validators/input_validator.py` - 输入验证器
- `constants.py` - 驾驶评估常量定义
- `exceptions.py` - 驾驶评估特定异常

这样的组织方式让每个任务的代码更加内聚，维护更加容易。
