# RDAgent因子导入使用指南

## 问题背景

RDAgent自动挖掘的因子脚本使用`daily_pv.h5`格式（HDF5），包含所有股票的数据。但本项目使用Parquet格式按股票分区存储，且因子库需要特定的格式。因此需要转换器将RDAgent生成的因子脚本转换为项目可用的格式。

## 解决方案

已创建`RDAgentFactorConverter`转换器，可以：
1. 解析RDAgent生成的因子脚本
2. 转换数据访问方式（从HDF5改为接受DataFrame参数）
3. 转换列名映射（如`$close` -> `close`，`instrument` -> `stock_code`）
4. 提取因子元数据（名称、描述、依赖等）
5. 导入到因子库

## 使用方法

### 方法1：使用命令行工具（推荐）

```bash
# 使用默认路径导入因子
python3 scripts/import_rdagent_factors.py

# 指定workspace路径
python3 scripts/import_rdagent_factors.py --workspace /path/to/RD-Agent_workspace

# 指定输出文件
python3 scripts/import_rdagent_factors.py --output my_factors.json

# 导入并自动验证
python3 scripts/import_rdagent_factors.py --validate
```

### 方法2：使用Python API

```python
from core.rdagent_integration import import_rdagent_factors_to_library

# 导入RDAgent因子
result = import_rdagent_factors_to_library(
    workspace_path="git_ignore_folder/RD-Agent_workspace",
    output_file="converted_rdagent_factors.json",
    auto_validate=False,
)

print(f"成功导入: {result['success']} 个因子")
print(f"跳过: {result['skipped']} 个因子")
print(f"失败: {result['failed']} 个因子")
```

### 方法3：分步操作

```python
from core.rdagent_integration import (
    convert_rdagent_factors,
    import_converted_factors
)

# Step 1: 转换因子脚本
factors = convert_rdagent_factors(
    workspace_path="git_ignore_folder/RD-Agent_workspace",
    output_file="converted_rdagent_factors.json"
)

print(f"转换了 {len(factors)} 个因子")

# Step 2: 导入因子库
result = import_converted_factors(
    factors_file="converted_rdagent_factors.json",
    auto_validate=False
)

print(f"成功导入: {result['success']} 个因子")
```

## 转换示例

### 原始RDAgent脚本

```python
import pandas as pd

def calculate_momentum_10():
    # Load the data
    df = pd.read_hdf('daily_pv.h5', key='data')
    
    # Calculate the momentum factor
    df['momentum_10'] = (df['$close'] / df['$close'].shift(10)) - 1
    
    # Save the result to a HDF5 file
    df[['momentum_10']].to_hdf('result.h5', key='data', mode='w')

if __name__ == '__main__':
    calculate_momentum_10()
```

### 转换后的格式

```python
def calculate_factor(df):
    """
    计算因子: momentum_10
    
    Args:
        df: DataFrame, 包含 close, open, high, low, volume, date, stock_code 列
    
    Returns:
        Series: 因子值
    """
    return (df['close'] / df['close'].shift(10)) - 1
```

## 转换规则

### 列名映射

| RDAgent列名 | 项目列名 |
|------------|---------|
| `$close` | `close` |
| `$open` | `open` |
| `$high` | `high` |
| `$low` | `low` |
| `$volume` | `volume` |
| `instrument` | `stock_code` |
| `datetime` | `date` |

### 数据访问方式转换

- **原始**: 从`daily_pv.h5`读取所有股票数据
- **转换后**: 接受DataFrame参数，包含单只股票的数据

### 因子元数据提取

转换器会自动提取：
- **因子名称**: 从函数名或赋值语句中提取
- **描述**: 包含因子类型、回看期、滚动窗口等信息
- **依赖**: 因子计算所需的列（close, volume等）
- **变量说明**: 对依赖列和参数的说明

## 查看导入的因子

```python
from core.factor import get_factor_registry

# 获取因子注册表
registry = get_factor_registry()

# 列出所有因子
all_factors = registry.list_all()
print(f"共有 {len(all_factors)} 个因子")

# 查看RDAgent导入的因子
rdagent_factors = [f for f in all_factors if 'RDAgent' in f.source]
print(f"RDAgent因子: {len(rdagent_factors)} 个")

# 查看具体因子
factor = registry.get_by_name('momentum_10')
if factor:
    print(f"因子ID: {factor.id}")
    print(f"因子名称: {factor.name}")
    print(f"因子公式: {factor.formula}")
    print(f"因子描述: {factor.description}")
```

## 测试转换器

```bash
# 运行测试脚本
python3 scripts/test_rdagent_converter.py
```

测试脚本会：
1. 测试简单因子转换
2. 测试多行因子转换
3. 测试成交量因子转换
4. 验证转换后的公式语法
5. 验证公式可以正常执行

## 注意事项

1. **数据格式**: 转换后的因子函数接受DataFrame参数，需要包含必要的列（close, volume等）
2. **groupby操作**: 转换器会自动将`df.groupby('instrument')`转换为`df.groupby('stock_code')`
3. **返回值**: 函数返回一个pandas Series，包含因子值
4. **重复导入**: 如果因子名称已存在，会跳过导入
5. **验证**: 建议导入后进行因子验证，确保因子计算正确

## 故障排除

### 问题1: 转换失败

**原因**: 因子脚本格式不符合预期

**解决**: 检查脚本是否符合RDAgent的标准格式，或手动调整转换器逻辑

### 问题2: 导入失败

**原因**: 因子公式语法错误或依赖缺失

**解决**: 
- 检查转换后的公式是否正确
- 确保数据包含所需的列
- 查看错误日志获取详细信息

### 问题3: 因子计算错误

**原因**: 数据格式不匹配或公式逻辑问题

**解决**:
- 检查输入数据的格式
- 手动测试因子公式
- 使用`--validate`参数进行自动验证

## 相关文件

- **转换器**: `core/rdagent_integration/rdagent_factor_converter.py`
- **导入脚本**: `scripts/import_rdagent_factors.py`
- **测试脚本**: `scripts/test_rdagent_converter.py`
- **因子库**: `core/factor/`
- **快速入库**: `core/factor/quick_entry.py`

## 更新日志

### 2026-04-11
- 创建RDAgent因子转换器
- 支持自动转换列名和数据访问方式
- 支持提取因子元数据
- 支持批量导入到因子库
- 添加命令行工具和测试脚本
