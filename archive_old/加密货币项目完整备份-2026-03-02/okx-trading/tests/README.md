# 单元测试

本目录包含OKX交易系统的单元测试。

## 测试文件

- `test_grid_strategy.py` - 网格策略测试
  - 策略初始化
  - 网格层级计算
  - 价格突破检测
  - 区间扩展逻辑
  - 订单成交更新

- `test_data_analyzer.py` - 数据验证测试
  - K线数据验证
  - Ticker数据验证
  - 订单簿数据验证
  - 数据完整性检查
  - 数据异常检测

- `test_exception_handling.py` - 异常处理测试
  - 异常类测试
  - 装饰器测试
  - 重试机制测试
  - 异常上下文测试

## 运行测试

### 运行所有测试
```bash
pytest
```

### 运行特定测试文件
```bash
pytest tests/test_grid_strategy.py
```

### 运行特定测试类
```bash
pytest tests/test_grid_strategy.py::TestGridStrategy
```

### 运行特定测试函数
```bash
pytest tests/test_grid_strategy.py::TestGridStrategy::test_initialization
```

### 生成覆盖率报告
```bash
pytest --cov=okx_trading --cov-report=html
```
覆盖率报告将生成在 `htmlcov/` 目录中。

### 显示详细输出
```bash
pytest -v
```

### 只运行单元测试（排除集成测试）
```bash
pytest -m unit
```

### 显示打印语句
```bash
pytest -s
```

## 测试覆盖目标

- 策略逻辑覆盖率 > 90%
- 数据验证覆盖率 > 90%
- 异常处理覆盖率 > 85%
- 总体覆盖率 > 80%

## 测试编写规范

1. 使用 `pytest` 框架
2. 测试类以 `Test` 开头
3. 测试函数以 `test_` 开头
4. 使用 `@pytest.fixture` 定义测试夹具
5. 测试函数应该有清晰的文档字符串
6. 每个测试应该独立，不依赖其他测试

## 测试依赖

运行测试需要安装以下包：

```bash
pip install pytest pytest-cov pytest-mock
```
