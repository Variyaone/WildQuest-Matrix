# OKX模拟盘资金费套利测试

## 概述

本脚本用于在OKX模拟盘环境中测试资金费套利策略，验证自动化执行流程和策略性能。

## 目录结构

```
okx-temp/
├── simulation_funding_arbitrage.py  # 主测试脚本
└── README_simulation.md              # 本文档

results/simulation_logs/               # 测试日志目录
├── okx_trader.log                    # OKX交易日志
├── strategy.log                     # 策略执行日志
├── trades_YYYYMMDD_HHMMSS.json      # 交易历史
├── funding_YYYYMMDD_HHMMSS.json     # 资金费历史
├── equity_YYYYMMDD_HHMMSS.json      # 资金曲线
└── positions_YYYYMMDD_HHMMSS.json   # 持仓记录

.commander/
└── simulation_test_report.md        # 测试报告（自动生成）
```

## 依赖安装

```bash
pip install ccxt pandas numpy
```

## OKX模拟盘API密钥申请

1. 访问[OKX官网](https://www.okx.com/account/my-api)
2. 创建API密钥时选择**Demo Trading Environment**（模拟交易环境）
3. 获取以下信息：
   - API Key
   - Secret Key
   - Passphrase

## 环境变量配置

在运行前设置环境变量：

```bash
export OKX_SIMULATION_API_KEY='your-api-key'
export OKX_SIMULATION_SECRET_KEY='your-secret-key'
export OKX_SIMULATION_PASSPHRASE='your-passphrase'
```

或在脚本开始时直接设置（适用于快速测试）。

## 运行测试

### 基础运行

```bash
python okx-temp/simulation_funding_arbitrage.py
```

### 自定义配置

编辑脚本中的 `CONFIG` 字典：

```python
CONFIG = {
    'symbols': ['BTC/USDT:USDT', 'ETH/USDT:USDT'],  # 交易对
    'entry_threshold': 0.001,      # 入场阈值 0.1%
    'exit_threshold': 0.0005,      # 出场阈值 0.05%
    'position_ratio': 0.20,        # 单币种仓位比例 20%
    'max_leverage': 2,             # 最大杠杆 2倍
    'max_drawdown': 0.10,          # 最大回撤 10%
    'basis_alert_threshold': 0.01, # 基差告警阈值 1%
    'funding_check_interval': 300, # 检查间隔 5分钟
    'funding_settlement_interval': 28800,  # 8小时结算
}
```

修改 `main()` 函数中的运行时长：

```python
duration_hours = 72  # 测试72小时（3天）
```

## 策略逻辑

### 开仓条件

- 当前资金费率绝对值 > 入场阈值（默认0.1%）
- 费率 > 0：做空永续合约（收取资金费）
- 费率 < 0：跳过（负费率做空需要支付费用）

### 平仓条件

- 资金费率绝对值 < 出场阈值（默认0.05%）
- 回撤超过最大回撤限制（默认10%）
- 策略停止时自动平仓

### 风险控制

1. **仓位控制**：单币种仓位不超过总资金的20%
2. **杠杆控制**：最大使用2倍杠杆
3. **回撤止损**：回撤超过10%时强制平仓
4. **基差告警**：基差变化超过1%时发出告警

## 日志输出

脚本会实时输出日志到控制台和文件：

### 控制台输出示例

```
20:36:15 - INFO - ============================================================
20:36:15 - INFO - [2026-02-27 20:36:15] 执行检查
20:36:15 - INFO - ============================================================
20:36:15 - INFO - 账户资金: $100,000.00
20:36:15 - INFO - 总盈亏: $0.00
20:36:15 - INFO - 资金费收益: $0.00
20:36:15 - INFO - 回撤: 0.00%
20:36:15 - INFO - 交易次数: 0
20:36:15 - INFO - 当前持仓: 0
```

### 日志文件

- `okx_trader.log`：OKX API交互详细日志
- `strategy.log`：策略执行详细日志

## 数据输出

### JSON文件（实时保存）

- `trades_*.json`：所有开仓、平仓、告警记录
- `funding_*.json`：每次资金费结算记录
- `equity_*.json`：资金曲线数据
- `positions_*.json`：当前持仓快照

### 测试报告

测试结束时自动生成Markdown格式报告：

`.commander/simulation_test_report.md`

报告包含：
- 测试概况（配置）
- 收益指标（收益率、年化收益、资金费收益）
- 风险指标（最大回撤、夏普比率）
- 交易指标（交易次数、胜率、平均持仓时长）
- 持仓记录
- 交易历史最近10笔
- 总结和建议

## 常见问题

### Q: 为什么开仓失败？

A: 可能原因：
1. OKX模拟盘余额不足
2. API密钥权限不足（需要交易权限）
3. 市场暂时不可用
4. 检查日志文件 `okx_trader.log` 获取详细错误信息

### Q: 如何调整测试时长？

A: 修改 `main()` 函数中的 `duration_hours` 变量：

```python
duration_hours = 24  # 测试24小时
```

### Q: 可以同时测试多个币种吗？

A: 可以，在 `CONFIG` 中添加更多交易对：

```python
CONFIG = {
    'symbols': [
        'BTC/USDT:USDT',
        'ETH/USDT:USDT',
        'SOL/USDT:USDT',
        'DOGE/USDT:USDT'
    ],
    # ...
}
```

### Q: 负费率为什么不开仓？

A: 负费率时：
- 做空永续需要支付资金费（不利）
- 做多永续收取资金费（需要做空现货对冲）
- 简化版策略只做空永续赚取正费率

要支持负费率策略，需要实现现货买卖功能。

### Q: 如何查看测试结果？

A: 测试结束后查看：
1. `.commander/simulation_test_report.md` - 完整报告
2. `results/simulation_logs/` - 原始数据文件

## 注意事项

1. ⚠️ **这是模拟盘测试**，所有资金均为虚拟资金，不会产生真实盈亏
2. ✅ 测试前请确认已获取OKX模拟盘API密钥（非生产环境密钥）
3. ✅ 测试期间可随时按 `Ctrl+C` 停止，策略会自动平仓并生成报告
4. ✅ 定期查看日志文件，监控策略执行状态
5. ✅ 测试完成后根据报告数据评估策略是否适合实盘

## 交付物清单

- ✅ 测试脚本：`okx-temp/simulation_funding_arbitrage.py`
- ✅ 测试日志：`results/simulation_logs/`
- ✅ 测试报告：`.commander/simulation_test_report.md`

---

**作者**: 架构师 🏗️
**日期**: 2026-02-27
**版本**: 1.0
