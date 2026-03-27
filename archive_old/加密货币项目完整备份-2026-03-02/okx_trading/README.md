# OKX交易系统核心框架

基于OKX API的量化交易系统框架，支持网格交易、风险管理、实时监控等功能。

## 目录结构

```
okx-trading/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── settings.py          # 配置管理
├── data/
│   ├── __init__.py
│   ├── collector.py         # WebSocket数据采集
│   └── storage.py           # SQLite数据存储
├── strategy/
│   ├── __init__.py
│   ├── base.py              # 策略基类
│   └── grid.py              # 网格交易策略
├── execution/
│   ├── __init__.py
│   ├── order_executor.py    # 订单执行器
│   └── risk_manager.py      # 风险管理器
├── monitor/
│   ├── __init__.py
│   └── monitor.py           # 系统监控
└── main.py                  # 主程序入口
```

## 核心模块

### 1. config/settings.py - 配置管理
- 加载和管理系统配置
- 提供配置访问接口
- 支持运行时修改配置

### 2. data/collector.py - 数据采集
- WebSocket实时连接管理
- K线数据订阅
- 自动重连机制
- 支持多频道订阅

### 3. data/storage.py - 数据存储
- SQLite数据库存储
- K线历史数据
- 订单记录
- 仓位跟踪
- 策略信号记录

### 4. strategy/base.py - 策略基类
- 定义策略通用接口
- 信号管理
- 仓位跟踪
- 数据缓存

### 5. strategy/grid.py - 网格交易策略
- 参数化网格设置
- 自动买卖触发
- 利润计算
- 支持多空双向

### 6. execution/order_executor.py - 订单执行
- OKX API订单执行
- 模拟执行器（测试用）
- 订单状态跟踪
- 批量操作支持

### 7. execution/risk_manager.py - 风险管理
- 仓位大小控制
- 止损止盈
- 保证金监控
- 订单风险检查

### 8. monitor/monitor.py - 系统监控
- 实时告警系统
- 性能指标收集
- 心跳监控
- 统计信息报告

## 快速开始

### 安装依赖
```bash
pip install ccxt websocket-client
```

### 配置文件
将OKX API配置保存到 `.commander/okx_config.json`:
```json
{
  "api_key": "your_api_key",
  "secret": "your_secret",
  "passphrase": "your_passphrase",
  "base_url": "https://www.okx.com",
  "simulated": true
}
```

### 运行系统

#### 模拟模式（推荐新手）
```bash
cd okx-trading
python main.py --simulated
```

#### 实盘模式（谨慎使用）
```bash
cd okx-trading
python main.py --live
```

## 使用示例

### 创建自定义策略

```python
from strategy.base import BaseStrategy, Signal

class MyStrategy(BaseStrategy):
    def initialize(self) -> bool:
        self.is_initialized = True
        return True

    def on_data(self, data: dict) -> Optional[Signal]:
        self.update_cache(data)

        # 实现你的交易逻辑
        if self.should_buy():
            return Signal(
                signal_type='buy',
                instrument_id='BTC-USDT-SWAP',
                price=current_price,
                amount=0.001
            )

        return None

    def generate_signal(self) -> Optional[Signal]:
        return None
```

### 配置网格策略

```python
grid_config = {
    'instrument_id': 'BTC-USDT-SWAP',
    'upper_price': 50000,
    'lower_price': 45000,
    'grid_count': 10,
    'grid_amount': 100,
    'position_side': 'long'
}

strategy = GridStrategy('MyGrid', grid_config)
```

## 风控参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| max_position_value | 1000 USDT | 单仓最大价值 |
| max_total_value | 5000 USDT | 总持仓最大价值 |
| stop_loss_percent | 2.0% | 止损百分比 |
| take_profit_percent | 5.0% | 止盈百分比 |
| max_leverage | 10x | 最大杠杆倍数 |

## 功能特性

✅ WebSocket实时数据流
✅ 多种K线周期支持
✅ 自动重连机制
✅ SQLite持久化存储
✅ 可插拔策略架构
✅ 风险管理系统
✅ 订单执行与跟踪
✅ 实时监控与告警
✅ 模拟交易模式

## 日志

系统运行日志保存在 `okx_trading.log`。

## 注意事项

1. **实盘交易前请充分测试**
2. 建议先用模拟模式熟悉系统
3. 合理设置风控参数
4. 注意账户资金安全

## 作者

Creator ✍️

## 版本

1.0.0
