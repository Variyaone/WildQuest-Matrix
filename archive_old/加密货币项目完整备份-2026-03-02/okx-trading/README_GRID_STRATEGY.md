# 网格交易策略使用说明

## 快速开始

### 1. 配置策略

编辑配置文件 `config/grid_config.json`：

```json
{
  "symbol": "BTC-USDT",
  "current_price": 95000.00,
  "grid_count": 10,
  "price_range_percent": 10,
  "total_capital": 10000.0,
  "grid_type": "arithmetic"
}
```

### 2. 运行测试脚本

```bash
cd okx-trading
python3 test_grid_strategy.py
```

### 3. 在代码中使用

```python
from strategy.grid import GridStrategy
import json

# 加载配置
with open('config/grid_config.json', 'r') as f:
    config = json.load(f)

# 创建策略实例
strategy = GridStrategy(config)

# 启动策略
strategy.start()

# 价格更新回调（实时应用中从交易所获取价格）
strategy.on_price_update(93500.0)

# 获取交易信号
signal = strategy.calculate_signal(93500.0)

# 订单成交回调
if signal:
    order = {
        'id': 'order_1',
        'symbol': signal.symbol,
        'side': signal.action,
        'quantity': signal.quantity,
        'price': signal.price,
        'timestamp': timestamp
    }
    strategy.on_order_filled(order)
```

## 策略说明

### 核心原理

网格交易策略是一种在指定价格区间内进行低买高卖的量化交易策略：

1. **价格区间**: 基于当前价格±10%（可配置）
2. **网格划分**: 将区间划分为10个等分网格（可配置）
3. **每格资金**: 总资金 ÷ 网格数量
4. **买入信号**: 价格跌破某个网格下轨时买入该格
5. **卖出信号**: 价格突破某个网格上轨时卖出上一格的持仓

### 配置参数

| 参数 | 说明 | 示例 |
|------|------|------|
| symbol | 交易对 | "BTC-USDT" |
| current_price | 初始价格（用于计算区间） | 95000.0 |
| grid_count | 网格数量 | 10 |
| price_range_percent | 价格区间百分比 | 10（±10%） |
| total_capital | 总资金（USDT） | 10000.0 |
| grid_type | 网格类型 | "arithmetic"（等差）或"geometric"（等比） |

### 网格类型

- **arithmetic（等差）**: 每个网格的价格间距相同
  - 适合价格波动相对稳定的市场
  - 计算简单，易于理解

- **geometric（等比）**: 每个网格的价格比例相同
  - 适合价格波动较大的市场
  - 低价格区域网格更密集，高价格区域网格更稀疏

## 常用方法

### 策略控制

```python
# 启动策略
strategy.start()

# 停止策略
strategy.stop()

# 重置策略状态
strategy.reset()

# 重新计算网格（当价格超出原区间时）
strategy.recalculate_grid(new_price)
```

### 信息查询

```python
# 获取持仓信息
position_info = strategy.get_position_info()

# 获取网格状态
grid_status = strategy.get_grid_status()

# 获取未成交订单
pending_orders = strategy.get_pending_orders()

# 获取交易历史
trade_history = strategy.get_trade_history()
```

## 回调函数

### on_price_update(price)

当价格更新时调用此方法，策略会自动检查是否产生交易信号。

**参数:**
- `price`: 当前市场价格

### on_order_filled(order)

当订单成交后调用此方法，更新持仓和网格状态。

**参数:**
- `order`: 订单信息字典
  - `id`: 订单ID
  - `symbol`: 交易对
  - `side`: 买卖方向（"BUY"或"SELL"）
  - `quantity`: 成交数量
  - `price`: 成交价格
  - `timestamp`: 成交时间

## 注意事项

1. **价格区间**: 当价格超出设定的区间时，策略不会产生信号，需要调用`recalculate_grid()`重新计算网格
2. **初始资金**: 确保账户有足够资金支撑所有网格的买入
3. **风险控制**: 建议设置止损策略，避免在极端行情中损失扩大
4. **手续费**: 实际交易中需要考虑交易所手续费对收益的影响

## 实际应用示例

### 与OKX API集成

```python
from strategy.grid import GridStrategy
import json
from okx_api_client import OKXClient  # 假设已有API客户端

# 初始化API客户端
client = OKXClient(api_key, secret, passphrase)

# 加载配置
with open('config/grid_config.json', 'r') as f:
    config = json.load(f)

# 创建策略
strategy = GridStrategy(config)
strategy.start()

# 实时价格监听
while True:
    # 获取当前价格
    ticker = client.get_ticker(config['symbol'])
    current_price = float(ticker['last'])

    # 更新价格并获取信号
    strategy.on_price_update(current_price)
    signal = strategy.calculate_signal(current_price)

    if signal:
        # 下单
        if signal.action == 'BUY':
            order = client.place_order(
                symbol=signal.symbol,
                side='buy',
                type='limit',
                price=str(signal.price),
                amount=str(signal.quantity)
            )
        else:  # SELL
            order = client.place_order(
                symbol=signal.symbol,
                side='sell',
                type='limit',
                price=str(signal.price),
                amount=str(signal.quantity)
            )

        # 记录订单ID
        strategy.add_pending_order({
            'id': order['order_id'],
            'symbol': signal.symbol,
            'side': signal.action,
            'quantity': signal.quantity,
            'price': signal.price
        })

    # 检查订单成交
    pending_orders = strategy.get_pending_orders()
    for pending_order in pending_orders:
        order_status = client.get_order(pending_order['id'])
        if order_status['state'] == 'filled':
            strategy.on_order_filled({
                'id': pending_order['id'],
                'symbol': pending_order['symbol'],
                'side': pending_order['side'],
                'quantity': pending_order['quantity'],
                'price': float(order_status['avg_px']),
                'timestamp': int(order_status['u_time'])
            })
```

## 常见问题

### Q: 如何调整网格数量？

A: 修改配置文件中的 `grid_count` 参数。网格越多，每次买入的金额越小，风险越分散，但交易频率越高。

### Q: 如何调整价格区间？

A: 修改 `price_range_percent` 参数。区间越大，覆盖的价格范围越广，但单格的资金密度越低。

### Q: 如何处理价格超出区间？

A: 监控当前价格，当价格超出区间±5%时，可以调用 `strategy.recalculate_grid(new_price)` 基于新价格重新计算网格。

### Q: 等差网格和等比网格哪个更好？

A: 取决于市场特性：
- **等差网格**: 适合波动较小、趋势平稳的市场
- **等比网格**: 适合波动较大、趋势明显的市场（如牛市）

## 文件结构

```
okx-trading/
├── strategy/
│   ├── base.py          # 策略基类
│   ├── grid.py          # 网格交易策略
│   └── __init__.py
├── config/
│   └── grid_config.json # 网格策略配置
└── test_grid_strategy.py # 测试脚本
```

## 日志输出示例

```
============================================================
网格交易策略配置 - BTC-USDT
============================================================
当前价格: 95000.00 USDT
价格区间: [85500.00, 104500.00] (10%)
网格数量: 10
网格类型: 等差
总资金: 10000.00 USDT
每格资金: 1000.00 USDT

网格级别:
  网格 0: 85500.00 USDT - 数量: 0.011696
  网格 1: 87400.00 USDT - 数量: 0.011442
  ...
  网格 9: 102600.00 USDT - 数量: 0.009747
============================================================
```
