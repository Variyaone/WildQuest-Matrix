# OKX Trading 完善的回测引擎

基于Qlib、VNPy、ai_quant_trade的实践经验，实现了一个完善的回测引擎。

## 核心功能

### 1. 订单簿深度检查
- 从历史数据推断订单簿深度
- 基于ATR（平均真实波幅）设定深度阈值
- 大订单超出深度时拒绝执行
- 考虑成交量对流动性的影响

### 2. 滑点模拟
- 支持多种滑点模型：
  - `size_based`: 基于订单大小
  - `linear`: 线性模型
  - `exponential`: 指数模型
- 按订单大小计算滑点（0.05%-0.2%）
- 市价单滑点更大
- 基于市场流动性动态调整

### 3. 市场冲击
- 大订单影响价格的模型
- 支持多种市场冲击模型：
  - `linear`: 线性模型
  - `sqrt`: 平方根模型（阿尔法法则）
  - `exponential`: 指数模型
- 基于订单大小和日均交易量计算

### 4. 手续费模拟
- OKX交易费率：
  - Maker: 0.08%
  - Taker: 0.1%
- 自动识别订单类型
- 计算每笔交易的总成本

### 5. 回测结果输出
- JSON格式回测报告
- 包含所有关键指标：
  - 总收益率 / 年化收益率
  - 最大回撤
  - 夏普比率 / 索提诺比率 / 卡尔玛比率
  - 胜率 / 盈亏比
  - 交易次数 / 平均持仓时间
  - 手续费统计 / 滑点统计 / 市场冲击统计

## 架构设计

### 核心类

```python
class BacktestEngine:
    """回测引擎主类"""
    def __init__(self, initial_capital, ...)
    def run_backtest(self, data, strategy, params)
    def generate_report(self, result, filepath)

class MarketEnvironment:
    """市场环境模拟器"""
    - get_orderbook_depth(): 推断订单簿深度
    - get_liquidity(): 获取市场流动性

class OrderExecutor:
    """订单执行器"""
    - execute_order(): 执行订单，考虑滑点和市场冲击
    - calculate_slippage(): 计算滑点
    - calculate_market_impact(): 计算市场冲击
    - calculate_commission(): 计算手续费

class BaseStrategy:
    """策略基类"""
    - generate_signals(): 生成交易信号
    - on_trade(): 成交回调
    - on_order_filled(): 订单成交回调
```

## 使用示例

### 1. 创建自定义策略

```python
from backtest import BacktestEngine, BaseStrategy, Order, OrderType, OrderSide
import pandas as pd
from datetime import datetime

class MyStrategy(BaseStrategy):
    def __init__(self, name: str, params: dict):
        super().__init__(name, params)
        self.fast_period = params.get('fast_period', 10)
        self.slow_period = params.get('slow_period', 30)
        self.position_size = params.get('position_size', 100)

    def generate_signals(self, data, positions, current_time):
        orders = []

        for symbol, df in data.items():
            if len(df) < self.slow_period:
                continue

            # 计算指标
            df['fast_ma'] = df['close'].rolling(self.fast_period).mean()
            df['slow_ma'] = df['close'].rolling(self.slow_period).mean()

            # 获取当前和前一行
            current_row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) > 1 else current_row

            # 交叉信号
            if prev_row['fast_ma'] <= prev_row['slow_ma'] and current_row['fast_ma'] > current_row['slow_ma']:
                if symbol not in positions:
                    orders.append(Order(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=self.position_size
                    ))

            elif prev_row['fast_ma'] >= prev_row['slow_ma'] and current_row['fast_ma'] < current_row['slow_ma']:
                if symbol in positions:
                    orders.append(Order(
                        symbol=symbol,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        quantity=positions[symbol].quantity
                    ))

        return orders
```

### 2. 运行回测

```python
# 创建回测引擎
engine = BacktestEngine(
    initial_capital=100000,
    maker_commission=0.0008,      # Maker手续费 0.08%
    taker_commission=0.0010,      # Taker手续费 0.1%
    slippage_model='size_based',  # 滑点模型
    market_impact_model='linear'  # 市场冲击模型
)

# 创建策略
strategy = MyStrategy(
    name="MyAwesomeStrategy",
    params={
        'fast_period': 10,
        'slow_period': 30,
        'position_size': 50
    }
)

# 准备数据（需要包含 open, high, low, close, volume）
data = {
    'BTC-USDT': your_dataframe,
    'ETH-USDT': another_dataframe
}

# 运行回测
result = engine.run_backtest(data, strategy)

# 打印摘要
engine.print_backtest_summary(result)

# 生成JSON报告
report = engine.generate_report(result, 'my_backtest_report.json')
```

### 3. 使用示例策略

```python
from backtest import BacktestEngine, create_sample_strategy

# 使用内置的示例策略（均线交叉）
strategy = create_sample_strategy("SampleStrategy")
strategy.params = {
    'fast_period': 10,
    'slow_period': 30,
    'position_size': 50
}

# 运行回测（同上）
```

## 回测报告

回测报告为JSON格式，包含以下字段：

```json
{
  "strategy_name": "策略名称",
  "backtest_period": {
    "start": "起始日期",
    "end": "结束日期"
  },
  "capital": {
    "initial": 初始资金,
    "final": 最终资金
  },
  "returns": {
    "total": 总收益率,
    "total_pct": "总收益率百分比",
    "annual": 年化收益率,
    "annual_pct": "年化收益率百分比"
  },
  "risk_metrics": {
    "max_drawdown": 最大回撤,
    "max_drawdown_pct": "最大回撤百分比",
    "volatility": 波动率,
    "volatility_pct": "波动率百分比"
  },
  "risk_adjusted_returns": {
    "sharpe_ratio": 夏普比率,
    "sortino_ratio": 索提诺比率,
    "calmar_ratio": 卡尔玛比率
  },
  "trading_metrics": {
    "total_trades": 总交易次数,
    "win_rate": 胜率,
    "win_rate_pct": "胜率百分比",
    "profit_factor": 盈亏比,
    "avg_win": 平均盈利,
    "avg_loss": 平均亏损,
    "avg_holding_time_hours": 平均持仓时间
  },
  "costs": {
    "total_commission": 手续费总额,
    "total_slippage": 滑点总额,
    "total_market_impact": 市场冲击总额
  },
  "trades": [交易明细...],
  "equity_curve": [权益曲线...]
}
```

## 技术细节

### 订单簿深度计算

订单簿深度基于以下因素推断：
1. **ATR（平均真实波幅）**：波动越大，流动性可能越差
2. **成交量**：成交量越大，流动性越好
3. **价格位置**：距离开盘价越远，流动性可能越差

计算公式：
```
base_depth_mult = 1.0 / (atr / price * 10)
volume_mult = current_volume / avg_volume
total_depth = price * volume_mult * base_depth_mult * 1000
```

### 滑点模型

#### 1. Size-based 模型
```
trade_ratio = order_value / liquidity
slippage = min_slippage + (max_slippage - min_slippage) * min(trade_ratio, 1.0)
```

#### 2. Linear 模型
```
slippage = min_slippage + coeff * trade_ratio
```

#### 3. Exponential 模型
```
slippage = min_slippage * exp(5 * trade_ratio)
```

### 市场冲击模型

#### 1. Linear 模型
```
daily_ratio = order_value / daily_volume
market_impact = coeff * daily_ratio
```

#### 2. Sqrt 模型（阿尔法法则）
```
market_impact = coeff * sqrt(daily_ratio)
```

#### 3. Exponential 模型
```
market_impact = coeff * exp(daily_ratio * 10)
```

## 性能指标说明

| 指标 | 说明 | 计算方法 |
|------|------|---------|
| 总收益率 | 整个回测期间的总收益 | (最终资金 - 初始资金) / 初始资金 |
| 年化收益率 | 年化后的收益率 | (最终资金/初始资金)^{1/years} - 1 |
| 最大回撤 | 账户价值从峰值下跌的最大百分比 | max((peak - value) / peak) |
| 夏普比率 | 风险调整收益 | (年化收益 - 无风险利率) / 年化波动率 |
| 索提诺比率 | 只考虑下行风险的风险调整收益 | 年化收益 / 下行波动率 |
| 卡尔玛比率 | 收益与最大回撤的比率 | 年化收益 / |最大回撤| |
| 胜率 | 盈利交易占总交易的比例 | 盈利交易数 / 总交易数 |
| 盈亏比 | 平均盈利与平均亏损的比率 | 平均盈利 / |平均亏损| |

## 测试

运行内置测试：

```bash
python3 backtest/backtest_engine.py
```

这将生成一个示例回测报告 `backtest_report.json`。

## 参考资料

- **Qlib**: Microsoft开源的量化投资平台
- **VNPy**: 专业的量化交易框架
- **ai_quant_trade**: AI增强的量化交易系统
- **阿尔法法则**: 市场影响的平方根模型

## 更新日志

### v1.0.0 (2026-02-25)
- ✅ 实现订单簿深度检查
- ✅ 实现滑点模拟（支持多种模型）
- ✅ 实现市场冲击模拟（支持多种模型）
- ✅ 实现手续费模拟（支持OKX费率）
- ✅ 实现完整的回测结果输出
- ✅ 支持自定义策略
- ✅ 提供示例策略和测试代码
