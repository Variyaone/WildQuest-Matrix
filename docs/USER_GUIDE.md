# 用户使用指南

## 版本信息
- **版本**: v2.1
- **更新日期**: 2026-04-15
- **作者**: 陈默

---

## 快速开始

### 1. 系统要求
- Python 3.8+
- 必要依赖: pandas, numpy, scipy

### 2. 安装
```bash
cd /path/to/a-stock-advisor-6.5
pip install -r requirements.txt
```

### 3. 验证安装
```bash
python3 verify_system.py
```

---

## 核心功能

### 功能1: 因子管理

#### 查看因子列表
```python
from core.factor import get_factor_registry

registry = get_factor_registry()
factors = registry.list_all()

print(f"总因子数: {len(factors)}")
for factor in factors[:5]:
    print(f"  - {factor.id}: {factor.name} (IC={factor.ic:.4f})")
```

#### 筛选高质量因子
```python
from core.strategy import FactorCombiner

combiner = FactorCombiner()
high_quality = combiner.filter_factors(
    factors,
    min_ic=0.05,    # IC > 0.05
    min_ir=2.0,     # IR > 2.0
    min_win_rate=0.55  # 胜率 > 55%
)

print(f"高质量因子: {len(high_quality)}")
```

---

### 功能2: 因子组合

#### IC加权组合
```python
from core.strategy import FactorCombiner, FactorCombinationConfig

combiner = FactorCombiner()
config = FactorCombinationConfig(
    combination_method="ic_weighted",
    min_ic=0.03,
    min_ir=1.5
)

result = combiner.combine(config)

if result.success:
    print(f"筛选因子: {len(result.factor_ids)}")
    print(f"权重: {result.weights}")
    print(f"总IC: {result.metrics.get('total_ic', 0):.4f}")
```

#### IR加权组合
```python
config = FactorCombinationConfig(
    combination_method="ir_weighted",
    min_ic=0.03,
    min_ir=1.5
)

result = combiner.combine(config)
```

#### 等权组合
```python
config = FactorCombinationConfig(
    combination_method="equal",
    factor_ids=["F00001", "F00002", "F00003"]
)

result = combiner.combine(config)
```

#### 自定义权重
```python
config = FactorCombinationConfig(
    factor_ids=["F00001", "F00002", "F00003"],
    weights=[0.5, 0.3, 0.2]
)

result = combiner.combine(config)
```

---

### 功能3: Alpha生成

#### 生成单日Alpha
```python
from core.strategy import AlphaGenerator

generator = AlphaGenerator()
alpha_result = generator.generate(
    config,
    date="2024-01-01"
)

if alpha_result.success:
    print(f"有效股票: {alpha_result.valid_stocks}")
    print(f"Top 10 股票:")
    for i in range(10):
        stock = alpha_result.ranked_stocks[i]
        score = alpha_result.scores[i]
        print(f"  [{i+1}] {stock}: {score:.4f}")
```

#### 批量生成Alpha
```python
dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
results = generator.generate_batch(config, dates)

for date, result in results.items():
    if result.success:
        print(f"{date}: {len(result.ranked_stocks)} stocks")
```

---

### 功能4: 策略创建

#### 从模板创建
```python
from core.strategy import StrategyDesigner

designer = StrategyDesigner()

# 查看可用模板
templates = designer.list_templates()
for tid, template in templates.items():
    print(f"  - {tid}: {template.name}")

# 从模板创建
strategy = designer.create_from_template(
    template_id="multi_factor_basic",
    name="我的多因子策略"
)

print(f"策略ID: {strategy.id}")
print(f"策略名称: {strategy.name}")
```

#### 创建自定义策略
```python
from core.strategy import StrategyType, RebalanceFrequency, RiskParams

strategy = designer.create_custom(
    name="自定义策略",
    description="基于动量和价值因子的策略",
    strategy_type=StrategyType.MULTI_FACTOR,
    factor_ids=["F00001", "F00002"],
    combination_method="ic_weighted",
    rebalance_freq=RebalanceFrequency.WEEKLY,
    max_positions=20,
    risk_params=RiskParams(
        max_single_weight=0.1,
        max_industry_weight=0.3,
        stop_loss=-0.1,
        take_profit=0.2
    ),
    tags=["多因子", "动量", "价值"]
)

print(f"创建成功: {strategy.id}")
```

---

### 功能5: 策略回测

#### 基础回测
```python
from core.strategy import StrategyBacktester

backtester = StrategyBacktester(
    initial_capital=1000000,
    commission_rate=0.0003
)

result = backtester.backtest(
    strategy=strategy,
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
    print(f"胜率: {result.win_rate:.2%}")
```

#### 查看详细结果
```python
# 持仓历史
for position in result.positions[:5]:
    print(f"  {position.date}: {position.stock_code} "
          f"权重={position.weight:.2%}")

# 收益曲线
returns = result.daily_returns
print(f"收益天数: {len(returns)}")
```

---

## 功能6: 每日管线

### 统一管线执行

```bash
# 交互式菜单
./asa

# 直接执行标准管线
python -m core.daily --mode standard

# 快速模式（跳过部分步骤）
python -m core.daily --mode fast

# 实盘模式（包含交易执行）
python -m core.daily --mode live

# 回测模式
python -m core.daily --mode backtest
```

### 测试模式参数

```bash
# 限制股票和因子数量
python -m core.daily --mode fast --max-stocks 50 --max-factors 10

# 禁用质量门控
python -m core.daily --mode fast --no-quality-gate
```

### 管线执行步骤

| 模式 | 执行步骤 | 质量门控 | 交易执行 |
|------|---------|---------|---------|
| standard | Step 0-11 (全部) | ✅ 严格 | ❌ 跳过 |
| fast | Step 0,1,3,5-8,11 (核心) | ⚠️ 宽松 | ❌ 跳过 |
| live | Step 0-11 (全部) | ✅ 严格 | ✅ 执行 |
| backtest | Step 3-7 (因子+策略) | ✅ 严格 | ❌ 跳过 |

### Python API调用

```python
from core.daily.unified_pipeline import run_unified_pipeline

result = run_unified_pipeline(
    mode="fast",
    max_stocks=50,
    max_factors=10,
    enable_quality_gate=True,
    quality_gate_strict=True
)

if result.success:
    print("管线执行成功!")
    print(f"决策: {result.decision}")
    print(f"选中股票: {len(result.selected_stocks)}")
```

---

## 功能7: 飞书推送

### 配置

在 `.env` 文件中配置：

```bash
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
ASA_NOTIFICATION_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
ASA_NOTIFICATION_ENABLED=true
```

### 推送内容

推送报告包含：
- 市场概况（指数涨跌、成交量、北向资金）
- 组合表现（收益、回撤、夏普比率）
- 持仓分析（股票名称、权重、行业分布）
- 交易记录
- 因子表现
- 风险监控（VaR、Beta、风险预警）
- 明日计划

### 手动触发推送

```python
from core.daily.notifier import DailyNotifier, TradeInstruction

notifier = DailyNotifier()

# 推送日报
notifier.send_daily_report(
    report_path="./data/reports/daily/daily_report_2026-04-15.md"
)
```

---

## 完整工作流程

### 标准流程

```
1. 因子筛选
   ↓
2. 因子组合
   ↓
3. Alpha生成
   ↓
4. 策略创建
   ↓
5. 策略回测
   ↓
6. 策略优化
```

### 示例代码

```python
from core.factor import get_factor_registry
from core.strategy import (
    FactorCombiner,
    AlphaGenerator,
    StrategyDesigner,
    StrategyBacktester,
    FactorCombinationConfig,
    StrategyType,
    RebalanceFrequency
)

# Step 1: 因子筛选
print("Step 1: 因子筛选")
registry = get_factor_registry()
all_factors = registry.list_all()
print(f"总因子数: {len(all_factors)}")

# Step 2: 因子组合
print("\nStep 2: 因子组合")
combiner = FactorCombiner()
config = FactorCombinationConfig(
    min_ic=0.03,
    min_ir=1.5,
    combination_method="ic_weighted"
)
combination_result = combiner.combine(config)
print(f"筛选因子: {len(combination_result.factor_ids)}")

# Step 3: Alpha生成
print("\nStep 3: Alpha生成")
generator = AlphaGenerator()
alpha_result = generator.generate(config, "2024-01-01")
print(f"有效股票: {alpha_result.valid_stocks}")

# Step 4: 策略创建
print("\nStep 4: 策略创建")
designer = StrategyDesigner()
strategy = designer.create_custom(
    name="完整流程策略",
    description="从因子到策略的完整流程",
    strategy_type=StrategyType.MULTI_FACTOR,
    factor_ids=combination_result.factor_ids[:5],
    max_positions=20
)
print(f"策略ID: {strategy.id}")

# Step 5: 策略回测
print("\nStep 5: 策略回测")
# (需要准备price_data和factor_data)
# backtester = StrategyBacktester()
# result = backtester.backtest(strategy, price_data, factor_data)
# print(f"年化收益: {result.annual_return:.2%}")

print("\n✅ 流程完成!")
```

---

## 高级功能

### 1. 因子组合优化

#### 自定义优化目标
```python
# IC最大化
config = FactorCombinationConfig(
    combination_method="ic_weighted",
    min_ic=0.05  # 更严格的IC要求
)

# IR最大化
config = FactorCombinationConfig(
    combination_method="ir_weighted",
    min_ir=2.0  # 更严格的IR要求
)
```

#### 指定因子组合
```python
# 只使用特定因子
config = FactorCombinationConfig(
    factor_ids=["F00001", "F00002", "F00003"],
    combination_method="ic_weighted"
)
```

---

### 2. Alpha分析

#### Alpha分布分析
```python
import numpy as np

alpha_values = list(alpha_result.alpha_values.values())
print(f"Alpha统计:")
print(f"  均值: {np.mean(alpha_values):.4f}")
print(f"  标准差: {np.std(alpha_values):.4f}")
print(f"  最大值: {np.max(alpha_values):.4f}")
print(f"  最小值: {np.min(alpha_values):.4f}")
print(f"  中位数: {np.median(alpha_values):.4f}")
```

#### Top/Bottom分析
```python
top_10 = alpha_result.ranked_stocks[:10]
bottom_10 = alpha_result.ranked_stocks[-10:]

print(f"Top 10 平均分数: {np.mean(alpha_result.scores[:10]):.4f}")
print(f"Bottom 10 平均分数: {np.mean(alpha_result.scores[-10:]):.4f}")
```

---

### 3. 策略管理

#### 查看所有策略
```python
from core.strategy import get_strategy_registry

registry = get_strategy_registry()
strategies = registry.list_all()

for strategy in strategies:
    print(f"  - {strategy.id}: {strategy.name}")
```

#### 更新策略
```python
strategy.max_positions = 30
strategy.rebalance_freq = RebalanceFrequency.DAILY
registry.update(strategy)
```

#### 删除策略
```python
registry.delete(strategy.id)
```

---

## 最佳实践

### 1. 因子选择
- ✅ IC > 0.03
- ✅ IR > 1.5
- ✅ 胜率 > 55%
- ✅ 定期重新评估

### 2. 组合优化
- ✅ 使用IC或IR加权
- ✅ 定期重新优化
- ✅ 监控组合表现
- ✅ 避免过度拟合

### 3. Alpha生成
- ✅ 使用最新数据
- ✅ 标准化Alpha值
- ✅ 验证分布合理性
- ✅ 监控Alpha衰减

### 4. 策略管理
- ✅ 明确策略类型
- ✅ 设置合理参数
- ✅ 定期回测验证
- ✅ 监控实盘表现

### 5. 风险控制
- ✅ 设置止损止盈
- ✅ 控制单股权重
- ✅ 控制行业权重
- ✅ 监控最大回撤

---

## 常见问题

### Q1: 因子组合失败怎么办？
**A**: 检查以下项目：
1. 因子数据是否完整
2. 筛选阈值是否合理
3. 是否有符合条件的因子

```python
# 降低筛选标准
config = FactorCombinationConfig(
    min_ic=0.01,  # 降低IC要求
    min_ir=1.0    # 降低IR要求
)
```

### Q2: Alpha生成失败怎么办？
**A**: 检查以下项目：
1. 因子数据是否可用
2. 日期是否有效
3. 因子组合是否成功

```python
# 检查因子数据
from core.factor import get_factor_storage
storage = get_factor_storage()
data = storage.load("F00001", "2024-01-01")
print(f"数据可用: {data is not None}")
```

### Q3: 如何提高回测速度？
**A**: 优化方法：
1. 使用更少的时间段
2. 减少持仓数量
3. 使用增量回测

```python
# 使用较短的时间段
result = backtester.backtest(
    strategy,
    price_data,
    factor_data,
    start_date="2023-10-01",  # 缩短时间
    end_date="2023-12-31"
)
```

### Q4: 如何验证系统完整性？
**A**: 运行验证脚本：
```bash
python3 verify_system.py
```

---

## 故障排查

### 问题1: 导入错误
```python
# 错误
ImportError: cannot import name 'SignalConfig'

# 解决
# SignalConfig已废弃，使用FactorCombinationConfig
from core.strategy import FactorCombinationConfig
```

### 问题2: 数据缺失
```python
# 检查数据
from core.data import get_data_manager
manager = get_data_manager()
status = manager.check_data_availability("000001.SZ", "2024-01-01")
print(f"数据状态: {status}")
```

### 问题3: 性能问题
```python
# 使用缓存
from core.factor import get_factor_storage
storage = get_factor_storage()
storage.enable_cache()

# 使用批量操作
results = generator.generate_batch(config, dates)
```

---

## 更新日志

### v2.1 (2026-04-15)
- ✅ 新增每日管线功能
- ✅ 新增飞书推送功能
- ✅ 数据源优化（BaoStock优先）
- ✅ 股票名称和行业信息支持
- ✅ 鲁棒性回测验证

### v2.0 (2026-04-03)
- ✅ 新架构: 因子 → Alpha → 策略
- ✅ 新增FactorCombiner模块
- ✅ 新增AlphaGenerator模块
- ✅ 移除信号层
- ✅ 更新策略创建流程

### v1.0 (历史版本)
- 旧架构: 因子 → 信号 → 策略
- 信号层未实现

---

## 技术支持

### 文档
- [架构文档](docs/ARCHITECTURE.md)
- [API文档](docs/API.md)
- [TODO清单](TODO.md)

### 联系方式
- 架构负责人: 陈默

---

**最后更新**: 2026-04-15
