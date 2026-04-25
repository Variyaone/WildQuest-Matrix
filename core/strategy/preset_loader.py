"""
预置策略导入模块

从预设的策略库导入经典量化策略到系统策略注册表。
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from .registry import (
    StrategyRegistry,
    StrategyMetadata,
    StrategyType,
    StrategyStatus,
    RebalanceFrequency,
    RiskParams,
    get_strategy_registry
)
from .factor_combiner import FactorCombinationConfig


PRESET_STRATEGIES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "strategies", "preset_strategies.json"
)


def load_preset_strategies(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    加载预置策略配置
    
    Args:
        file_path: 策略配置文件路径
        
    Returns:
        策略配置列表
    """
    path = file_path or PRESET_STRATEGIES_FILE
    
    if not os.path.exists(path):
        return []
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get("preset_strategies", [])


def get_strategy_type(type_str: str) -> StrategyType:
    """将字符串转换为策略类型枚举"""
    type_mapping = {
        "选股策略": StrategyType.STOCK_SELECTION,
        "择时策略": StrategyType.TIMING,
        "套利策略": StrategyType.ARBITRAGE,
        "趋势跟踪": StrategyType.TREND_FOLLOWING,
        "均值回归": StrategyType.MEAN_REVERSION,
        "多因子策略": StrategyType.MULTI_FACTOR,
        "自定义策略": StrategyType.CUSTOM
    }
    return type_mapping.get(type_str, StrategyType.STOCK_SELECTION)


def get_rebalance_freq(freq_str: str) -> RebalanceFrequency:
    """将字符串转换为调仓频率枚举"""
    freq_mapping = {
        "daily": RebalanceFrequency.DAILY,
        "weekly": RebalanceFrequency.WEEKLY,
        "biweekly": RebalanceFrequency.BIWEEKLY,
        "monthly": RebalanceFrequency.MONTHLY,
        "quarterly": RebalanceFrequency.QUARTERLY
    }
    return freq_mapping.get(freq_str, RebalanceFrequency.WEEKLY)


def import_preset_strategy(
    strategy_config: Dict[str, Any],
    registry: Optional[StrategyRegistry] = None
) -> Optional[StrategyMetadata]:
    """
    导入单个预置策略
    
    Args:
        strategy_config: 策略配置字典
        registry: 策略注册表实例
        
    Returns:
        导入的策略元数据，失败返回None
    """
    if registry is None:
        registry = get_strategy_registry()
    
    existing = registry.get_by_name(strategy_config["name"])
    if existing is not None:
        return existing
    
    try:
        factor_data = strategy_config.get("factor_config", {})
        factor_config = FactorCombinationConfig(
            factor_ids=factor_data.get("factor_ids", []),
            weights=factor_data.get("weights", []),
            combination_method=factor_data.get("combination_method", "ic_weighted"),
            min_ic=factor_data.get("min_ic", 0.03),
            min_ir=factor_data.get("min_ir", 1.5)
        )
        
        risk_data = strategy_config.get("risk_params", {})
        risk_params = RiskParams(
            max_single_weight=risk_data.get("max_single_weight", 0.1),
            max_industry_weight=risk_data.get("max_industry_weight", 0.3),
            stop_loss=risk_data.get("stop_loss", -0.1),
            take_profit=risk_data.get("take_profit", 0.2),
            max_drawdown=risk_data.get("max_drawdown", -0.15),
            position_limit=risk_data.get("position_limit", 0.95)
        )
        
        strategy = registry.register(
            name=strategy_config["name"],
            description=strategy_config["description"],
            strategy_type=get_strategy_type(strategy_config["strategy_type"]),
            factor_config=factor_config,
            rebalance_freq=get_rebalance_freq(strategy_config["rebalance_freq"]),
            max_positions=strategy_config.get("max_positions", 20),
            risk_params=risk_params,
            source=strategy_config.get("source", "预置策略"),
            tags=strategy_config.get("tags", []),
            parameters=strategy_config.get("parameters", {}),
            benchmark=strategy_config.get("benchmark", "000300.SH")
        )
        
        return strategy
        
    except Exception as e:
        print(f"导入策略失败 [{strategy_config['name']}]: {e}")
        return None


def import_all_preset_strategies(
    file_path: Optional[str] = None,
    registry: Optional[StrategyRegistry] = None
) -> Dict[str, Any]:
    """
    导入所有预置策略
    
    Args:
        file_path: 策略配置文件路径
        registry: 策略注册表实例
        
    Returns:
        导入结果统计
    """
    if registry is None:
        registry = get_strategy_registry()
    
    preset_strategies = load_preset_strategies(file_path)
    
    result = {
        "total": len(preset_strategies),
        "imported": 0,
        "skipped": 0,
        "failed": 0,
        "strategies": []
    }
    
    for config in preset_strategies:
        strategy = import_preset_strategy(config, registry)
        
        if strategy is not None:
            existing = registry.get_by_name(config["name"])
            if existing and existing.id == strategy.id:
                result["skipped"] += 1
            else:
                result["imported"] += 1
            result["strategies"].append({
                "id": strategy.id,
                "name": strategy.name,
                "type": strategy.strategy_type.value
            })
        else:
            result["failed"] += 1
    
    return result


def get_preset_strategy_info(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    获取预置策略信息
    
    Args:
        file_path: 策略配置文件路径
        
    Returns:
        预置策略信息
    """
    path = file_path or PRESET_STRATEGIES_FILE
    
    if not os.path.exists(path):
        return {"error": "预置策略文件不存在"}
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    strategies = data.get("preset_strategies", [])
    sources = data.get("strategy_sources", [])
    metadata = data.get("metadata", {})
    
    type_counts = {}
    for s in strategies:
        t = s.get("strategy_type", "未知")
        type_counts[t] = type_counts.get(t, 0) + 1
    
    return {
        "total_strategies": len(strategies),
        "strategy_types": type_counts,
        "sources": sources,
        "metadata": metadata,
        "strategies": [
            {
                "name": s["name"],
                "type": s["strategy_type"],
                "description": s["description"][:50] + "..." if len(s["description"]) > 50 else s["description"],
                "tags": s.get("tags", [])
            }
            for s in strategies
        ]
    }


def list_preset_strategies(file_path: Optional[str] = None) -> List[Dict[str, str]]:
    """
    列出所有预置策略名称和类型
    
    Args:
        file_path: 策略配置文件路径
        
    Returns:
        策略列表
    """
    preset_strategies = load_preset_strategies(file_path)
    
    return [
        {
            "name": s["name"],
            "type": s["strategy_type"],
            "source": s.get("source", "预置策略"),
            "tags": ", ".join(s.get("tags", []))
        }
        for s in preset_strategies
    ]
