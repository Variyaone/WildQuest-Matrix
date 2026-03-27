"""
测试阶段四核心模块
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试因子库导入
from core.factor import (
    FactorCategory, FactorSubCategory, FactorClassification,
    FactorRegistry, FactorEngine, FactorValidator, FactorBacktester,
    FactorScorer, FactorStorage, FactorMiner, FactorMonitor
)
print('✓ 因子库模块导入成功')

# 测试信号库导入
from core.signal import (
    SignalType, SignalDirection, SignalRegistry, SignalGenerator,
    SignalFilter, SignalQualityAssessor, SignalStorage
)
print('✓ 信号库模块导入成功')

# 测试策略库导入
from core.strategy import (
    StrategyType, StrategyRegistry, StrategyDesigner, StockSelector,
    StrategyBacktester, StrategyOptimizer, StrategyStorage
)
print('✓ 策略库模块导入成功')

# 测试核心模块导入
from core import (
    FactorRegistry, get_factor_registry,
    SignalRegistry, get_signal_registry,
    StrategyRegistry, get_strategy_registry
)
print('✓ 核心模块导入成功')

# 测试因子分类
classification = FactorClassification()
categories = classification.get_all_categories()
print(f'✓ 因子分类体系包含 {len(categories)} 个一级分类')

# 测试因子注册表
registry = get_factor_registry()
print(f'✓ 因子注册表初始化成功')

# 测试信号注册表
signal_registry = get_signal_registry()
print(f'✓ 信号注册表初始化成功')

# 测试策略注册表
strategy_registry = get_strategy_registry()
print(f'✓ 策略注册表初始化成功')

print()
print('阶段四核心模块重构完成！')
