# WildQuest Matrix

**A股量化投顾系统** | 版本: 6.5.2 | 状态: Beta | 许可证: MIT

## 项目简介

WildQuest Matrix 是 Variya 开发的数据驱动智能投资决策平台，专注于A股市场的量化选股、组合优化和风险管理。系统采用分层架构设计，从数据获取到交易执行形成完整的量化投资管线。

### 核心特性

- **统一数据层**: 支持多数据源（AKShare、BaoStock、yfinance）的统一接入和增量更新
- **因子库管理**: 完整的因子注册、计算、验证、回测和评分系统
- **增强版验证**: 多等级验证标准、无效分数检测、样本外验证
- **快速入库**: 支持从论文/文本/批量等多种方式快速录入因子和策略
- **多频率回测**: 支持日线、小时线（60m/30m/15m/5m/1m）等多种频率回测
- **增强版日线回测**: 精确涨跌停判断、VWAP执行价格、隔夜跳空风险调整
- **鲁棒性回测**: 存续偏差检查、滚动回测、流动性约束、黑天鹅事件模拟
- **压力测试**: 极端场景风险测试、市场环境分类回测
- **信号库管理**: 信号生成、过滤和质量评估系统
- **策略库管理**: 策略设计、回测、优化和执行系统
- **组合优化**: 支持等权、风险平价、均值方差、Black-Litterman等多种优化方法
- **风控系统**: 事前、事中、事后全流程风控
- **回测引擎**: 事件驱动和向量化双模式回测
- **前置检查**: 统一的数据契约和质量验证系统
- **LLM审核**: 自动审核报告是否满足交易要求（盈利能力、风险控制、可操作性）
- **问题根源诊断**: 智能诊断问题根源（策略、因子、风险、数据）
- **根本问题修复**: 自动修复根本问题（优化因子、调整策略、加强风控、更新数据）

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          支撑层 (贯穿全流程)                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │调度中心  │ │监控中心  │ │存储中心  │ │日志中心  │ │配置中心  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
          ↓                ↓                ↓                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据层                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ 市场数据    │  │ 财务数据    │  │ 参考数据    │  │ 元数据索引  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
          ↓                ↓                ↓                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                              因子层                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │因子注册表│ │因子计算器│ │因子验证器│ │因子回测器│ │因子挖掘器│           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                              信号层                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│  │信号注册表│ │信号生成器│ │信号过滤器│ │信号评估器│                        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                              策略层                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │策略注册表│ │策略设计器│ │股票选择器│ │策略回测器│ │策略优化器│           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                           组合优化层                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │组合优化器│ │中性化处理│ │约束管理器│ │再平衡策略│ │组合评估器│           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                              风控层                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│  │事前风控  │ │事中风控  │ │事后风控  │ │风控报告  │                        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                           执行层                                             │
│  ┌─────────────────────┐      ┌─────────────────────┐                       │
│  │     实盘模式        │      │     仿真模式        │                       │
│  └─────────────────────┘      └─────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                           分析层                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│  │绩效追踪  │ │归因分析  │ │风险报告  │ │可视化展示│                        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 目录结构

```
a-stock-advisor-6.5/
├── config/                     # 配置文件
│   ├── pipeline_config.json    # 管线配置
│   ├── risk_limits.json        # 风控限制
│   ├── factor_config.json      # 因子配置
│   ├── strategy_config.json    # 策略配置
│   ├── risk_config.json        # 风险控制配置
│   └── *.example               # 配置示例
├── core/                       # 核心代码
│   ├── backtest/               # 回测系统
│   ├── daily/                  # 每日任务
│   ├── evaluation/             # 绩效评估
│   ├── factor/                 # 因子库
│   ├── infrastructure/         # 基础设施
│   ├── monitor/                # 监控系统
│   ├── portfolio/              # 组合优化
│   ├── risk/                   # 风控系统
│   ├── signal/                 # 信号库
│   ├── strategy/               # 策略库
│   ├── trading/                # 交易执行
│   └── validation/             # 前置检查
├── tests/                      # 测试文件
├── docs/                       # 文档
├── llm_review_report.py        # LLM审核报告脚本
├── fix_root_cause.py           # 修复根本问题脚本
├── full_workflow_with_diagnosis.py  # 完整工作流脚本
├── test_diagnosis_and_fix.py   # 测试诊断和修复流程脚本
├── pyproject.toml              # 项目配置
├── requirements.txt            # 依赖列表
└── Makefile                    # 构建命令
```

## 快速开始

### 环境要求

- Python >= 3.9
- 操作系统: macOS / Linux / Windows

### 安装

```bash
# 克隆项目
git clone https://github.com/quant-team/a-stock-advisor.git
cd a-stock-advisor

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 基本使用

```bash
# 运行测试
make test

# 代码格式化
make format

# 类型检查
make typecheck

# 运行 lint
make lint
```

## 核心模块

### 数据层 (Data Layer)

统一的数据获取和管理系统，支持增量更新和多数据源切换。

```python
from core.data import get_data_fetcher, get_unified_updater

# 获取数据
fetcher = get_data_fetcher()
data = fetcher.get_history("000001.SZ", start="2020-01-01", end="2025-12-31")

# 增量更新
updater = get_unified_updater()
updater.incremental_update(stock_list=["000001.SZ"], data_types=["daily"])
```

### 因子库 (Factor Library)

完整的因子管理系统，支持因子注册、计算、验证和评分。

```python
from core.factor import get_factor_engine, get_factor_registry, get_factor_validator

# 注册因子
registry = get_factor_registry()
registry.register(
    id="F00001",
    name="动量因子_20日收益率",
    formula="close / close.shift(20) - 1",
    category="动量类"
)

# 计算因子
engine = get_factor_engine()
result = engine.compute_single("F00001", market_data)

# 验证因子
validator = get_factor_validator()
report = validator.validate("F00001", factor_values)
```

#### 快速入库

支持多种方式快速录入外部因子和策略：

```python
from core.factor import get_factor_quick_entry

quick_entry = get_factor_quick_entry()

# 手动录入因子
result = quick_entry.quick_add(
    name="动量因子_20日",
    formula="close / close.shift(20) - 1",
    description="20日动量因子",
    source="用户分享",
    tags=["动量", "趋势"]
)

# 从文本解析录入
text = """
名称: 反转因子_5日
公式: -1 * (close / close.shift(5) - 1)
描述: 5日反转因子
来源: 学术论文
"""
result = quick_entry.quick_add_from_text(text)

# 从论文录入
result = quick_entry.quick_add_from_paper(
    paper_title="Momentum Investing",
    paper_url="https://example.com/paper.pdf",
    author="Smith et al.",
    factor_name="动量因子",
    formula="close / close.shift(12) - 1"
)

# 批量录入
factors = [
    {"name": "因子1", "formula": "formula1", "source": "用户分享"},
    {"name": "因子2", "formula": "formula2", "source": "用户分享"}
]
results = quick_entry.quick_add_batch(factors)
```

#### 增强版因子验证

多等级验证标准，支持无效分数检测和样本外验证：

```python
from core.factor import get_enhanced_validator, ValidationLevel

# 获取验证器 (支持 BASIC/STANDARD/STRICT/COMPREHENSIVE 四个等级)
validator = get_enhanced_validator(ValidationLevel.STRICT)

# 执行验证
result = validator.validate_factor(
    factor_id="F00001",
    factor_df=factor_data,
    return_df=return_data,
    stock_pool="全市场",
    enable_oos=True,
    train_ratio=0.7
)

# 检查验证结果
print(f"验证通过: {result.passed}")
print(f"综合评分: {result.overall_score}")
print(f"评级: {result.grade}")
print(f"问题列表: {result.issues}")
print(f"改进建议: {result.recommendations}")
```

验证等级标准：

| 等级 | IC阈值 | IR阈值 | t统计量 | 覆盖率 | 交易日 |
|------|--------|--------|---------|--------|--------|
| BASIC | 0.01 | 0.15 | 1.0 | 50 | 50 |
| STANDARD | 0.02 | 0.25 | 1.65 | 100 | 100 |
| STRICT | 0.03 | 0.35 | 1.96 | 200 | 200 |
| COMPREHENSIVE | 0.04 | 0.50 | 2.58 | 300 | 250 |

#### 复测因子

使用历史回测参数重新验证因子：

```python
from core.factor import BacktestParameterRecorder, get_factor_registry

registry = get_factor_registry()

# 获取历史回测参数
params = BacktestParameterRecorder.get_retest_params(
    registry, 
    factor_id="F00001", 
    stock_pool="全市场"
)

# 查看历史参数
if params:
    print(f"股票池: {params['stock_pool']}")
    print(f"分组数: {params['n_groups']}")
    print(f"样本外验证: {params['enable_oos']}")
```

#### 多频率回测

支持日线和小时线等多种频率的回测：

```python
from core.factor import (
    FactorBacktester,
    BacktestFrequency,
    HourlyBacktester,
    HourlyFrequency
)

# 日线回测（默认）
daily_backtester = FactorBacktester(
    frequency=BacktestFrequency.DAILY,
    use_enhanced_daily=True
)

# 小时线回测
hourly_backtester = FactorBacktester(
    frequency=BacktestFrequency.HOURLY,
    use_enhanced_daily=False
)

# 或直接使用小时线回测器
hourly = HourlyBacktester(
    config=HourlyBacktestConfig(
        frequency=HourlyFrequency.MINUTE_60,
        trading_hours_only=True
    )
)
```

支持的频率：

| 频率 | 说明 | 适用场景 |
|------|------|----------|
| daily | 日线 | 中长期因子验证 |
| 60m | 60分钟线 | 日内因子验证 |
| 30m | 30分钟线 | 短线因子验证 |
| 15m | 15分钟线 | 高频因子验证 |
| 5m | 5分钟线 | 超短线因子验证 |
| 1m | 1分钟线 | 极短线因子验证 |

#### 增强版日线回测

提供更精确的日线回测功能：

```python
from core.factor import (
    EnhancedDailyBacktest,
    EnhancedDailyConfig,
    PriceType,
    get_enhanced_daily_config
)

# 配置增强版回测
config = get_enhanced_daily_config(
    price_type="vwap",      # 执行价格类型
    gap_penalty=0.001,      # 隔夜跳空惩罚
    limit_up_threshold=9.9  # 涨跌停阈值
)

backtest = EnhancedDailyBacktest(config)

# 准备数据（自动检测涨跌停、计算VWAP等）
enhanced_df = backtest.prepare_data(price_df)

# 获取统计信息
stats = backtest.get_backtest_statistics(enhanced_df)
print(f"涨停次数: {stats['limit_up_count']}")
print(f"跌停次数: {stats['limit_down_count']}")
print(f"可买入: {stats['buyable_count']}")
print(f"可卖出: {stats['sellable_count']}")
```

执行价格类型：

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| open | 开盘价 | 开盘买入策略 |
| close | 收盘价 | 收盘买入策略 |
| vwap | 成交量加权均价 | 大额交易模拟 |
| high | 最高价 | 保守买入假设 |
| low | 最低价 | 保守卖出假设 |
| avg_open_close | 开盘收盘均价 | 均衡假设 |

### 信号库 (Signal Library)

信号生成和过滤系统。

```python
from core.signal import get_signal_generator, get_signal_filter

# 生成信号
generator = get_signal_generator()
signals = generator.generate(factor_values)

# 过滤信号
signal_filter = get_signal_filter()
valid_signals = signal_filter.filter(signals, min_strength=0.6)
```

### 策略库 (Strategy Library)

策略设计和回测系统。

```python
from core.strategy import get_strategy_designer, get_strategy_backtester

# 设计策略
designer = get_strategy_designer()
strategy = designer.create(
    name="多因子选股策略",
    signals=["S00001", "S00002"],
    rebalance_freq="weekly"
)

# 回测策略
backtester = get_strategy_backtester()
result = backtester.run(strategy, start="2020-01-01", end="2025-12-31")
```

### 组合优化 (Portfolio Optimization)

多种组合优化方法。

```python
from core.portfolio import PortfolioOptimizer, PortfolioNeutralizer

# 组合优化
optimizer = PortfolioOptimizer(config={"method": "risk_parity"})
result = optimizer.optimize(stock_scores)

# 中性化处理
neutralizer = PortfolioNeutralizer()
neutral_weights = neutralizer.neutralize(weights, method="industry")
```

### 风控系统 (Risk Management)

全流程风控。

```python
from core.risk import PreTradeRiskChecker, PostTradeAnalyzer

# 事前风控
pre_risk = PreTradeRiskChecker()
check_result = pre_risk.check(trade_instructions, portfolio_state)

# 事后风控
post_risk = PostTradeAnalyzer()
risk_report = post_risk.analyze(trade_results)
```

### 鲁棒性回测 (Robust Backtest)

完整的鲁棒性验证框架，确保策略在不同市场环境下的稳定性。

```python
from core.backtest import (
    create_robust_framework,
    RobustBacktestConfig,
    create_event_simulator,
    MarketRegimeClassifier,
    MarketRegime
)

# 创建鲁棒性回测框架
config = RobustBacktestConfig(
    enable_survivorship_bias_check=True,    # 存续偏差检查
    enable_walk_forward=True,                # 滚动回测
    enable_liquidity_check=True,             # 流动性约束
    enable_event_simulation=True,            # 黑天鹅事件模拟
    enable_market_regime=True,               # 市场环境分类
    enable_turnover_constraint=True,         # 换手率约束
    enable_overfitting_check=True,           # 过拟合检测
    min_ic_threshold=0.02,
    min_sharpe_threshold=0.5
)

framework = create_robust_framework(config)

# 执行完整鲁棒性检查
result = framework.run_full_robustness_check(
    factor_df=factor_data,
    return_df=return_data,
    market_data=market_data,
    index_data=index_data,
    backtest_func=my_backtest_function
)

if result.passed:
    print(f"策略通过鲁棒性验证，得分: {result.overall_score:.2f}")
else:
    print(f"策略未通过验证: {result.warnings}")
```

#### 核心模块

| 模块 | 功能 | 说明 |
|------|------|------|
| 股票池快照 | 存续偏差检查 | 时点股票池快照，消除存续偏差 |
| 滚动回测 | 时间窗口偏差 | Walk-Forward验证，消除时间窗口偏差 |
| 流动性检查 | 流动性约束 | 参与率限制，防止流动性陷阱 |
| 事件模拟 | 黑天鹅模拟 | 模拟股灾/熔断/恐慌等极端事件 |
| 市场冲击 | 冲击成本模型 | 多因子市场冲击成本计算 |
| 市场环境 | 牛熊震荡分类 | 强制按市场环境分别回测 |
| 换手率约束 | 过度交易限制 | 限制日/月/年换手率 |
| 过拟合检测 | 参数敏感性 | 检测训练测试差距和参数敏感性 |

#### 压力测试场景

```python
from core.backtest import create_event_simulator

simulator = create_event_simulator(stress_test_mode=True)

# 生成压力测试场景
scenarios = simulator.generate_stress_scenarios(
    base_date=date(2023, 1, 1),
    scenario_count=5
)

# 模拟极端事件冲击
for scenario in scenarios:
    impact = simulator.simulate_event_impact_on_portfolio(
        event=scenario,
        portfolio_value=1000000,
        positions=my_positions,
        market_data=market_data
    )
    print(f"{scenario.description}: 冲击 {impact['impact_pct']:.1%}")
```

#### 市场环境分类

```python
from core.backtest import MarketRegimeClassifier, MarketRegime

classifier = MarketRegimeClassifier()

# 分类市场环境
regime = classifier.classify_regime(index_returns)

if regime == MarketRegime.BULL:
    print("牛市环境")
elif regime == MarketRegime.BEAR:
    print("熊市环境")
elif regime == MarketRegime.SIDEWAYS:
    print("震荡市环境")
```

## 数据契约与质量检查

系统采用严格的数据契约和质量检查机制：

### 硬性要求 (H1-H5)

| 编号 | 要求 | 检查内容 |
|------|------|----------|
| H1 | 数据非空 | 行数 > 0 |
| H2 | 必需字段完整 | 7个字段齐全 |
| H3 | 时间序列连续 | 缺失率 < 10% |
| H4 | 价格逻辑一致 | high/low关系正确 |
| H5 | 无未来数据泄露 | 无穿越数据 |

### 弹性要求 (E1-E5)

| 编号 | 要求 | 理想标准 |
|------|------|----------|
| E1 | 数据完整性 | ≥99% |
| E2 | 数据时效性 | <24小时 |
| E3 | 质量分数 | ≥80分 |
| E4 | 多源一致性 | ≥95% |
| E5 | 异常值比例 | <0.5% |

## LLM审核与根本问题修复

系统内置智能审核和自动修复机制，确保报告质量并自动解决常见问题。

### LLM审核

自动审核报告是否满足交易要求：

**审核标准：**
- 能够盈利：年化收益≥5%，夏普比率≥0.5，胜率≥50%
- 风险可控：最大回撤≤-20%，波动率≤30%
- 可以操作：有明确的买入数量和价格，买入信号数量≥5个

**使用方法：**
```bash
# LLM审核报告
python3 llm_review_report.py data/reports/daily/daily_report_2026-04-28_201232.md
```

### 问题根源诊断

智能诊断问题根源：

**盈利能力问题：**
- 年化收益低 → 胜率低（因子问题）或胜率正常（策略问题）
- 夏普比率低 → 波动率高（风险控制问题）或波动率正常（策略问题）
- 胜率低 → 平均IC低（因子问题）或平均IC正常（策略问题）

**风险控制问题：**
- 最大回撤大 → 风险控制问题（没有止损机制）
- 波动率高 → 换手率高（策略问题）或换手率正常（风险控制问题）

**可操作性问题：**
- 没有买入信号 → 没有选中的股票（因子问题）或有选中的股票（策略问题）
- 买入信号少 → 选中的股票少（因子问题）或选中的股票正常（策略问题）
- 没有明确的价格 → 数据问题
- 没有明确的数量 → 策略问题

### 根本问题修复

根据诊断结果，自动修复根本问题：

**因子问题修复：**
- 优化因子组合：移除低质量因子，添加高质量因子
- 提高因子质量：增加因子权重

**策略问题修复：**
- 优化持仓周期：调整持仓周期，降低换手率
- 改进止盈止损策略：添加止盈止损机制
- 调整选股参数：放宽选股条件，优化选股逻辑
- 修复交易执行逻辑：添加交易数量计算

**风险控制问题修复：**
- 添加止损机制：启用止损，优化止损点设置
- 优化仓位管理：降低最大仓位，降低单只股票权重
- 降低风险暴露：分散投资，控制风险暴露

**数据问题修复：**
- 重新获取股票数据：运行数据更新脚本
- 确保数据完整：检查数据更新时间，重新获取缺失数据

**使用方法：**
```bash
# 修复根本问题
python3 fix_root_cause.py <diagnoses_json>

# 完整工作流（包含LLM审核和根本问题修复）
python3 full_workflow_with_diagnosis.py

# 测试诊断和修复流程
python3 test_diagnosis_and_fix.py
```

### 审核流程

```
生成报告 → LLM审核报告 → 审核通过 → 推送报告
                    ↓
                 审核不通过
                    ↓
              诊断问题根源
                    ↓
              修复根本问题
                    ↓
              重新运行工作流
                    ↓
              重新审核报告
```

### 配置文件

系统使用配置文件管理因子、策略和风险控制参数：

**因子配置 (config/factor_config.json)：**
```json
{
  "factor_selection": {
    "max_correlation": 0.8,
    "min_ic": 0.02
  },
  "factors": {
    "momentum_20d": {
      "ic": 0.05,
      "name": "20日动量",
      "weight": 0.15
    }
  }
}
```

**策略配置 (config/strategy_config.json)：**
```json
{
  "holding_period": 5,
  "top_n": 30,
  "take_profit": {
    "enabled": true,
    "threshold": 0.1
  },
  "stop_loss": {
    "enabled": true,
    "threshold": -0.05
  }
}
```

**风险控制配置 (config/risk_config.json)：**
```json
{
  "max_position": 0.95,
  "single_stock_weight": 0.1,
  "stop_loss": {
    "enabled": true,
    "threshold": -0.05,
    "method": "percentage"
  }
}
```

## 配置说明

### 主配置 (config/settings.yaml)

```yaml
app:
  name: "A股量化投顾系统"
  version: "6.5.2"
  mode: "production"

paths:
  data_root: "./data"
  log_root: "./logs"
  report_root: "./reports"

logging:
  level: "INFO"
  format: "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
```

### 风控配置 (config/risk_limits.json)

```json
{
  "position_limits": {
    "max_single_weight": 0.12,
    "max_industry_weight": 0.30,
    "max_total_position": 0.95
  },
  "stop_loss": {
    "single_stock_stop": 0.10,
    "portfolio_stop": 0.15
  }
}
```

## 测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest -m unit

# 运行集成测试
pytest -m integration

# 查看覆盖率
pytest --cov=core --cov-report=html
```

## 开发指南

### 代码风格

- 使用 Black 格式化代码
- 使用 isort 排序导入
- 使用 mypy 进行类型检查
- 使用 flake8 进行 lint 检查

### 提交规范

- feat: 新功能
- fix: 修复 bug
- docs: 文档更新
- refactor: 重构
- test: 测试相关
- chore: 构建/工具相关

## 性能指标

| 指标 | 目标值 |
|------|--------|
| 测试覆盖率 | ≥70% |
| 数据存储 | ≤5GB |
| 因子计算(5000股) | ≤15秒 |
| 数据获取(并发) | ≤60秒 |

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request。

## 联系方式

- 项目主页: https://github.com/quant-team/a-stock-advisor
- 问题反馈: https://github.com/quant-team/a-stock-advisor/issues
