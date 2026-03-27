# 测试套件

## 概述

这是 A股顾问系统 v6.5.0 的测试套件包。

## 统计

- **测试文件数**: 17
- **总大小**: 176.1 KB
- **当前覆盖率**: 53%
- **目标覆盖率**: 70%

## 使用方法

### 1. 安装依赖

```bash
pip install pytest pytest-cov pytest-mock pandas numpy
```

### 2. 运行测试

```bash
# 运行所有测试
python run_tests.py

# 运行测试（不含覆盖率）
python run_tests.py --no-cov

# 安静模式
python run_tests.py -q
```

### 3. 查看覆盖率报告

运行测试后，覆盖率报告会生成在 `htmlcov/` 目录下。

## 测试模块

- root

## 打包时间

2026-03-28T04:44:46.279482

## 注意事项

1. 运行测试前请确保项目根目录在 PYTHONPATH 中
2. 部分测试可能需要数据库或网络连接
3. 建议在虚拟环境中运行测试
