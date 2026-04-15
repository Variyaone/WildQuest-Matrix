"""
abu信号加载模块

从abu量化信号配置文件加载信号定义到系统。
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

ABU_SIGNALS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "strategies", "abu_signals.json"
)


def load_abu_signals(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载abu信号配置
    
    Args:
        file_path: 信号配置文件路径
        
    Returns:
        信号配置字典
    """
    path = file_path or ABU_SIGNALS_FILE
    
    if not os.path.exists(path):
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_all_signals(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    获取所有信号列表
    
    Args:
        file_path: 信号配置文件路径
        
    Returns:
        信号列表
    """
    data = load_abu_signals(file_path)
    signals = []
    
    categories = data.get("signal_categories", {})
    for category_id, category_data in categories.items():
        category_name = category_data.get("name", category_id)
        category_desc = category_data.get("description", "")
        
        for signal_id, signal_data in category_data.get("signals", {}).items():
            signals.append({
                "id": signal_id,
                "name": signal_data.get("name", signal_id),
                "type": signal_data.get("type", "neutral"),
                "strength": signal_data.get("strength", "medium"),
                "category": signal_data.get("category", category_name),
                "description": signal_data.get("description", ""),
                "parent_category": category_name,
                "parent_category_id": category_id
            })
    
    return signals


def get_signals_by_category(category: str, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    按类别获取信号
    
    Args:
        category: 信号类别 (pattern_signals, ma_signals, kline_signals, indicator_signals)
        file_path: 信号配置文件路径
        
    Returns:
        信号列表
    """
    data = load_abu_signals(file_path)
    categories = data.get("signal_categories", {})
    
    if category not in categories:
        return []
    
    category_data = categories[category]
    signals = []
    
    for signal_id, signal_data in category_data.get("signals", {}).items():
        signals.append({
            "id": signal_id,
            "name": signal_data.get("name", signal_id),
            "type": signal_data.get("type", "neutral"),
            "strength": signal_data.get("strength", "medium"),
            "category": signal_data.get("category", ""),
            "description": signal_data.get("description", "")
        })
    
    return signals


def get_signals_by_type(signal_type: str, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    按类型获取信号 (buy, sell, neutral)
    
    Args:
        signal_type: 信号类型
        file_path: 信号配置文件路径
        
    Returns:
        信号列表
    """
    all_signals = get_all_signals(file_path)
    return [s for s in all_signals if s["type"] == signal_type]


def get_signal_strategies(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    获取abu信号策略列表
    
    Args:
        file_path: 信号配置文件路径
        
    Returns:
        策略列表
    """
    data = load_abu_signals(file_path)
    strategies = data.get("signal_strategies", {})
    
    result = []
    for strategy_id, strategy_data in strategies.items():
        result.append({
            "id": strategy_id,
            "name": strategy_data.get("name", strategy_id),
            "description": strategy_data.get("description", ""),
            "signals": strategy_data.get("signals", []),
            "weights": strategy_data.get("weights", []),
            "source": strategy_data.get("source", "abu量化")
        })
    
    return result


def get_signal_info(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    获取信号库信息
    
    Args:
        file_path: 信号配置文件路径
        
    Returns:
        信号库信息
    """
    data = load_abu_signals(file_path)
    
    if not data:
        return {"error": "abu信号配置文件不存在"}
    
    categories = data.get("signal_categories", {})
    total_signals = 0
    category_stats = {}
    type_stats = {"buy": 0, "sell": 0, "neutral": 0}
    
    for cat_id, cat_data in categories.items():
        cat_name = cat_data.get("name", cat_id)
        cat_signals = cat_data.get("signals", {})
        cat_count = len(cat_signals)
        total_signals += cat_count
        category_stats[cat_name] = cat_count
        
        for signal_data in cat_signals.values():
            signal_type = signal_data.get("type", "neutral")
            type_stats[signal_type] = type_stats.get(signal_type, 0) + 1
    
    strategies = data.get("signal_strategies", {})
    
    return {
        "total_signals": total_signals,
        "total_strategies": len(strategies),
        "category_stats": category_stats,
        "type_stats": type_stats,
        "categories": list(categories.keys()),
        "metadata": data.get("metadata", {})
    }


def list_buy_signals(file_path: Optional[str] = None) -> List[Dict[str, str]]:
    """
    列出所有买入信号
    
    Args:
        file_path: 信号配置文件路径
        
    Returns:
        买入信号列表
    """
    buy_signals = get_signals_by_type("buy", file_path)
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "category": s["category"],
            "strength": s["strength"]
        }
        for s in buy_signals
    ]


def list_sell_signals(file_path: Optional[str] = None) -> List[Dict[str, str]]:
    """
    列出所有卖出信号
    
    Args:
        file_path: 信号配置文件路径
        
    Returns:
        卖出信号列表
    """
    sell_signals = get_signals_by_type("sell", file_path)
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "category": s["category"],
            "strength": s["strength"]
        }
        for s in sell_signals
    ]


def search_signals(keyword: str, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    搜索信号
    
    Args:
        keyword: 搜索关键词
        file_path: 信号配置文件路径
        
    Returns:
        匹配的信号列表
    """
    all_signals = get_all_signals(file_path)
    keyword = keyword.lower()
    
    return [
        s for s in all_signals
        if keyword in s["name"].lower() or 
           keyword in s["description"].lower() or
           keyword in s["category"].lower()
    ]
