"""
信号模块 - 已废弃 (DEPRECATED)

⚠️ 警告：此模块已废弃，不再维护

## 废弃时间
2026-04-03

## 废弃原因
架构重构：采用因子 → Alpha → 策略的新架构，移除信号层

## 替代方案
- 因子组合：使用 `core.strategy.FactorCombiner`
- Alpha生成：使用 `core.strategy.AlphaGenerator`
- 策略创建：使用 `core.strategy.StrategyDesigner`

## 迁移指南

### 旧代码（已废弃）
```python
from core.signal import SignalGenerator, SignalConfig

signal_config = SignalConfig(
    signal_ids=["S00001"],
    weights=[1.0]
)
```

### 新代码（推荐）
```python
from core.strategy import FactorCombiner, FactorCombinationConfig

factor_config = FactorCombinationConfig(
    factor_ids=["F00001", "F00002"],
    combination_method="ic_weighted"
)

combiner = FactorCombiner()
result = combiner.combine(factor_config)
```

## 数据备份
旧的信号数据已备份到：`data/backup_signals_20260403/`

## 相关文档
- [TODO.md](../../TODO.md) - 待办事项
- [REFACTOR_SUMMARY.md](../../REFACTOR_SUMMARY.md) - 重构总结
- [COMPLETION_REPORT.md](../../COMPLETION_REPORT.md) - 完成报告

## 注意事项
- 此模块保留仅供参考
- 不建议在新项目中使用
- 如需迁移旧策略，请联系架构负责人

## 联系人
架构重构负责人：陈默
"""

import warnings

warnings.warn(
    "信号模块已废弃，请使用 core.strategy.FactorCombiner 和 core.strategy.AlphaGenerator",
    DeprecationWarning,
    stacklevel=2
)
