# API 文档

## 版本信息
- **版本**: v2.0
- **更新日期**: 2026-04-03
- **维护者**: 陈默

---

## 核心API

### 1. FactorCombiner - 因子组合器

#### 概述
因子组合器用于优化因子权重，生成因子组合配置。

#### 导入
```python
from core.strategy import FactorCombiner, FactorCombinationConfig
```

---

#### 类: FactorCombinationConfig

**配置参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| factor_ids | List[str] | 否 | [] | 指定因子ID列表 |
| weights | List[float] | 否 | [] | 自定义权重 |
| combination_method | str | 否 | "ic_weighted" | 组合方法 |
| min_ic | float | 否 | 0.03 | 最小IC值 |
| min_ir | float | 否 | 1.5 | 最小IR值 |
| min_win_rate | float | 否 | 0.0 | 最小胜率 |

**组合方法**
- `ic_weighted` - IC加权优化
- `ir_weighted` - IR加权优化
- `equal` - 等权组合

**示例**
```python
config = FactorCombinationConfig(
    factor_ids=["F00001", "F00002", "F00003"],
    combination_method="ic_weighted",
    min_ic=0.03,
    min_ir=1.5
)
```

---

#### 类: FactorCombinationResult

**返回字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否成功 |
| factor_ids | List[str] | 因子ID列表 |
| weights | List[float] | 因子权重 |
| method | str | 组合方法 |
| metrics | Dict | 组合指标 |
| error_message | str | 错误信息 |

---

#### 类: FactorCombiner

**方法: combine**

组合因子并优化权重

**参数**
```python
def combine(
    self,
    config: FactorCombinationConfig
) -> FactorCombinationResult
```

| 参数 | 类型 | 说明 |
|------|------|------|
| config | FactorCombinationConfig | 组合配置 |

**返回**
- `FactorCombinationResult` - 组合结果

**示例**
```python
combiner = FactorCombiner()
config = FactorCombinationConfig(
    combination_method="ic_weighted"
)
result = combiner.combine(config)

if result.success:
    print(f"筛选因子: {len(result.factor_ids)}")
    print(f"权重: {result.weights}")
else:
    print(f"失败: {result.error_message}")
```

---

**方法: filter_factors**

筛选符合条件的因子

**参数**
```python
def filter_factors(
    self,
    factors: List[FactorMetadata],
    min_ic: float = 0.03,
    min_ir: float = 1.5,
    min_win_rate: float = 0.0
) -> List[FactorMetadata]
```

| 参数 | 类型 | 说明 |
|------|------|------|
| factors | List[FactorMetadata] | 因子列表 |
| min_ic | float | 最小IC值 |
| min_ir | float | 最小IR值 |
| min_win_rate | float | 最小胜率 |

**返回**
- `List[FactorMetadata]` - 筛选后的因子列表

**示例**
```python
from core.factor import get_factor_registry

registry = get_factor_registry()
all_factors = registry.list_all()

combiner = FactorCombiner()
filtered = combiner.filter_factors(
    all_factors,
    min_ic=0.05,
    min_ir=2.0
)
```

---

**方法: optimize_weights_ic**

IC加权优化

**参数**
```python
def optimize_weights_ic(
    self,
    factors: List[FactorMetadata]
) -> Tuple[List[float], Dict]
```

| 参数 | 类型 | 说明 |
|------|------|------|
| factors | List[FactorMetadata] | 因子列表 |

**返回**
- `Tuple[List[float], Dict]` - (权重列表, 指标字典)

**示例**
```python
weights, metrics = combiner.optimize_weights_ic(factors)
print(f"权重: {weights}")
print(f"总IC: {metrics['total_ic']}")
```

---

**方法: optimize_weights_ir**

IR加权优化

**参数**
```python
def optimize_weights_ir(
    self,
    factors: List[FactorMetadata]
) -> Tuple[List[float], Dict]
```

| 参数 | 类型 | 说明 |
|------|------|------|
| factors | List[FactorMetadata] | 因子列表 |

**返回**
- `Tuple[List[float], Dict]` - (权重列表, 指标字典)

---

### 2. AlphaGenerator - Alpha生成器

#### 概述
Alpha生成器基于因子组合生成Alpha预测值。

#### 导入
```python
from core.strategy import AlphaGenerator
```

---

#### 类: AlphaGenerationResult

**返回字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否成功 |
| date | str | 日期 |
| alpha_values | Dict[str, float] | Alpha值 {股票: 值} |
| ranked_stocks | List[str] | 排序后的股票列表 |
| scores | List[float] | 评分列表 |
| factor_ids | List[str] | 因子ID列表 |
| factor_weights | List[float] | 因子权重 |
| total_stocks | int | 总股票数 |
| valid_stocks | int | 有效股票数 |
| error_message | str | 错误信息 |

---

#### 类: AlphaGenerator

**方法: generate**

生成Alpha

**参数**
```python
def generate(
    self,
    config: FactorCombinationConfig,
    date: str,
    factor_data: Optional[Dict[str, pd.DataFrame]] = None
) -> AlphaGenerationResult
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| config | FactorCombinationConfig | 是 | 因子组合配置 |
| date | str | 是 | 日期 (YYYY-MM-DD) |
| factor_data | Dict[str, DataFrame] | 否 | 因子数据 (不提供则自动加载) |

**返回**
- `AlphaGenerationResult` - Alpha生成结果

**示例**
```python
generator = AlphaGenerator()

# 方式1: 自动加载因子数据
result = generator.generate(config, "2024-01-01")

# 方式2: 提供因子数据
factor_data = {
    "F00001": df1,
    "F00002": df2
}
result = generator.generate(config, "2024-01-01", factor_data)

if result.success:
    print(f"有效股票: {result.valid_stocks}")
    print(f"Top 10: {result.ranked_stocks[:10]}")
```

---

**方法: generate_batch**

批量生成Alpha

**参数**
```python
def generate_batch(
    self,
    config: FactorCombinationConfig,
    dates: List[str],
    factor_data: Optional[Dict[str, pd.DataFrame]] = None
) -> Dict[str, AlphaGenerationResult]
```

| 参数 | 类型 | 说明 |
|------|------|------|
| config | FactorCombinationConfig | 因子组合配置 |
| dates | List[str] | 日期列表 |
| factor_data | Dict[str, DataFrame] | 因子数据 |

**返回**
- `Dict[str, AlphaGenerationResult]` - {日期: 结果}

**示例**
```python
dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
results = generator.generate_batch(config, dates)

for date, result in results.items():
    if result.success:
        print(f"{date}: {len(result.ranked_stocks)} stocks")
```

---

### 3. StrategyDesigner - 策略设计器

#### 概述
策略设计器用于创建和管理策略。

#### 导入
```python
from core.strategy import StrategyDesigner, StrategyType, RebalanceFrequency
```

---

#### 方法: create_custom

创建自定义策略

**参数**
```python
def create_custom(
    self,
    name: str,
    description: str,
    strategy_type: StrategyType,
    factor_ids: List[str],
    factor_weights: Optional[List[float]] = None,
    combination_method: str = "ic_weighted",
    rebalance_freq: RebalanceFrequency = RebalanceFrequency.WEEKLY,
    max_positions: int = 20,
    risk_params: Optional[RiskParams] = None,
    tags: Optional[List[str]] = None
) -> StrategyMetadata
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| name | str | 是 | - | 策略名称 |
| description | str | 是 | - | 策略描述 |
| strategy_type | StrategyType | 是 | - | 策略类型 |
| factor_ids | List[str] | 是 | - | 因子ID列表 |
| factor_weights | List[float] | 否 | None | 因子权重 |
| combination_method | str | 否 | "ic_weighted" | 组合方法 |
| rebalance_freq | RebalanceFrequency | 否 | WEEKLY | 调仓频率 |
| max_positions | int | 否 | 20 | 最大持仓数 |
| risk_params | RiskParams | 否 | None | 风控参数 |
| tags | List[str] | 否 | [] | 标签 |

**返回**
- `StrategyMetadata` - 策略元数据

**示例**
```python
designer = StrategyDesigner()

strategy = designer.create_custom(
    name="多因子策略",
    description="基于IC加权的多因子选股策略",
    strategy_type=StrategyType.MULTI_FACTOR,
    factor_ids=["F00001", "F00002", "F00003"],
    combination_method="ic_weighted",
    rebalance_freq=RebalanceFrequency.WEEKLY,
    max_positions=20
)

print(f"策略ID: {strategy.id}")
```

---

#### 方法: create_from_template

从模板创建策略

**参数**
```python
def create_from_template(
    self,
    template_id: str,
    name: Optional[str] = None,
    customizations: Optional[Dict[str, Any]] = None
) -> StrategyMetadata
```

| 参数 | 类型 | 说明 |
|------|------|------|
| template_id | str | 模板ID |
| name | str | 策略名称 |
| customizations | Dict | 自定义配置 |

**示例**
```python
strategy = designer.create_from_template(
    template_id="multi_factor_basic",
    name="我的多因子策略",
    customizations={
        "max_positions": 30,
        "rebalance_freq": "daily"
    }
)
```

---

### 4. StrategyBacktester - 策略回测器

#### 概述
策略回测器用于回测策略表现。

#### 导入
```python
from core.strategy import StrategyBacktester, BacktestMode
```

---

#### 方法: backtest

回测策略

**参数**
```python
def backtest(
    self,
    strategy: Union[str, StrategyMetadata],
    price_data: pd.DataFrame,
    factor_data: Dict[str, pd.DataFrame],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    mode: BacktestMode = BacktestMode.FULL
) -> BacktestResult
```

| 参数 | 类型 | 说明 |
|------|------|------|
| strategy | str/StrategyMetadata | 策略ID或元数据 |
| price_data | DataFrame | 价格数据 |
| factor_data | Dict[str, DataFrame] | 因子数据 |
| start_date | str | 开始日期 |
| end_date | str | 结束日期 |
| mode | BacktestMode | 回测模式 |

**返回**
- `BacktestResult` - 回测结果

**示例**
```python
backtester = StrategyBacktester(
    initial_capital=1000000,
    commission_rate=0.0003
)

result = backtester.backtest(
    strategy="ST00001",
    price_data=price_df,
    factor_data=factor_dict,
    start_date="2023-01-01",
    end_date="2023-12-31"
)

if result.success:
    print(f"总收益: {result.total_return:.2%}")
    print(f"年化收益: {result.annual_return:.2%}")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"最大回撤: {result.max_drawdown:.2%}")
```

---

## 完整示例

### 示例1: 因子组合和Alpha生成

```python
from core.strategy import (
    FactorCombiner,
    AlphaGenerator,
    FactorCombinationConfig
)
from core.factor import get_factor_registry

# 1. 获取因子
registry = get_factor_registry()
factors = registry.list_all()

# 2. 组合因子
combiner = FactorCombiner()
config = FactorCombinationConfig(
    min_ic=0.03,
    min_ir=1.5,
    combination_method="ic_weighted"
)
result = combiner.combine(config)

if result.success:
    print(f"筛选因子: {len(result.factor_ids)}")
    
    # 3. 生成Alpha
    generator = AlphaGenerator()
    alpha_result = generator.generate(
        result,
        date="2024-01-01"
    )
    
    if alpha_result.success:
        print(f"Top 10 股票:")
        for i, stock in enumerate(alpha_result.ranked_stocks[:10], 1):
            score = alpha_result.scores[i-1]
            print(f"  [{i}] {stock}: {score:.4f}")
```

---

### 示例2: 创建并回测策略

```python
from core.strategy import (
    StrategyDesigner,
    StrategyBacktester,
    StrategyType,
    RebalanceFrequency
)

# 1. 创建策略
designer = StrategyDesigner()
strategy = designer.create_custom(
    name="测试策略",
    description="测试多因子策略",
    strategy_type=StrategyType.MULTI_FACTOR,
    factor_ids=["F00001", "F00002", "F00003"],
    max_positions=20
)

# 2. 准备数据
# (假设已有price_data和factor_data)

# 3. 回测策略
backtester = StrategyBacktester()
result = backtester.backtest(
    strategy=strategy,
    price_data=price_data,
    factor_data=factor_data,
    start_date="2023-01-01",
    end_date="2023-12-31"
)

# 4. 查看结果
print(f"年化收益: {result.annual_return:.2%}")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"最大回撤: {result.max_drawdown:.2%}")
```

---

## 错误处理

### 常见错误

#### 1. 因子组合失败
```python
result = combiner.combine(config)
if not result.success:
    print(f"错误: {result.error_message}")
    # 可能原因:
    # - 没有符合条件的因子
    # - 因子数据缺失
    # - 参数设置不合理
```

#### 2. Alpha生成失败
```python
alpha_result = generator.generate(config, date)
if not alpha_result.success:
    print(f"错误: {alpha_result.error_message}")
    # 可能原因:
    # - 因子数据不可用
    # - 日期无效
    # - 因子组合失败
```

#### 3. 策略创建失败
```python
try:
    strategy = designer.create_custom(...)
except StrategyException as e:
    print(f"错误: {e}")
    # 可能原因:
    # - 参数无效
    # - 因子不存在
    # - 配置冲突
```

---

## 最佳实践

### 1. 因子组合
- 使用合理的筛选阈值
- 定期重新优化权重
- 监控因子表现

### 2. Alpha生成
- 使用最新的因子数据
- 验证Alpha分布
- 监控Alpha衰减

### 3. 策略管理
- 设置合理的参数
- 定期回测验证
- 监控实盘表现

---

**文档维护**: 开发团队  
**最后更新**: 2026-04-03
