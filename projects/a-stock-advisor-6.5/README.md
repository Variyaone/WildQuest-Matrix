# A股量化投顾系统 (A-Stock-Advisor)

**版本**: 6.5.0  
**状态**: Beta  
**许可证**: MIT

## 项目简介

A股量化投顾系统是一个数据驱动的智能投资决策平台，专注于A股市场的量化选股、组合优化和风险管理。系统采用分层架构设计，从数据获取到交易执行形成完整的量化投资管线。

### 核心特性

- **统一数据层**: 支持多数据源（AKShare、BaoStock、yfinance）的统一接入和增量更新
- **因子库管理**: 完整的因子注册、计算、验证、回测和评分系统
- **信号库管理**: 信号生成、过滤和质量评估系统
- **策略库管理**: 策略设计、回测、优化和执行系统
- **组合优化**: 支持等权、风险平价、均值方差、Black-Litterman等多种优化方法
- **风控系统**: 事前、事中、事后全流程风控
- **回测引擎**: 事件驱动和向量化双模式回测
- **前置检查**: 统一的数据契约和质量验证系统

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
from core.data import UnifiedDataFetcher, IncrementalUpdater

# 获取数据
fetcher = UnifiedDataFetcher()
data = fetcher.get_history("000001.SZ", start="2020-01-01", end="2025-12-31")

# 增量更新
updater = IncrementalUpdater()
updater.update_all()
```

### 因子库 (Factor Library)

完整的因子管理系统，支持因子注册、计算、验证和评分。

```python
from core.factor import FactorEngine, FactorRegistry, FactorValidator

# 注册因子
registry = FactorRegistry()
registry.register(
    id="F00001",
    name="动量因子_20日收益率",
    formula="close / close.shift(20) - 1",
    category="动量类"
)

# 计算因子
engine = FactorEngine()
factor_values = engine.calc_factor("F00001", market_data)

# 验证因子
validator = FactorValidator()
report = validator.validate("F00001", factor_values)
```

### 信号库 (Signal Library)

信号生成和过滤系统。

```python
from core.signal import SignalGenerator, SignalFilter

# 生成信号
generator = SignalGenerator()
signals = generator.generate(factor_values)

# 过滤信号
filter = SignalFilter()
valid_signals = filter.filter(signals, min_strength=0.6)
```

### 策略库 (Strategy Library)

策略设计和回测系统。

```python
from core.strategy import StrategyDesigner, StrategyBacktester

# 设计策略
designer = StrategyDesigner()
strategy = designer.create(
    name="多因子选股策略",
    signals=["S00001", "S00002"],
    rebalance_freq="weekly"
)

# 回测策略
backtester = StrategyBacktester()
result = backtester.run(strategy, start="2020-01-01", end="2025-12-31")
```

### 组合优化 (Portfolio Optimization)

多种组合优化方法。

```python
from core.portfolio import PortfolioOptimizer, Neutralizer

# 组合优化
optimizer = PortfolioOptimizer(method="risk_parity")
weights = optimizer.optimize(stock_selection)

# 中性化处理
neutralizer = Neutralizer()
neutral_weights = neutralizer.neutralize(weights, method="industry")
```

### 风控系统 (Risk Management)

全流程风控。

```python
from core.risk import PreTradeRisk, PostTradeRisk

# 事前风控
pre_risk = PreTradeRisk()
check_result = pre_risk.check(target_weights)

# 事后风控
post_risk = PostTradeRisk()
risk_report = post_risk.analyze(trade_results)
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

## 配置说明

### 主配置 (config/settings.yaml)

```yaml
app:
  name: "A股量化投顾系统"
  version: "6.5"
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
