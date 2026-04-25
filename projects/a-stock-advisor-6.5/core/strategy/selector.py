"""
股票选择器模块 - 已废弃 (DEPRECATED)

⚠️ 警告：此模块已废弃，不再维护

## 废弃时间
2026-04-03

## 废弃原因
架构重构：使用AlphaGenerator替代StockSelector

## 替代方案
使用 `core.strategy.AlphaGenerator` 生成Alpha并选择股票

## 迁移指南

### 旧代码（已废弃）
```python
from core.strategy import StockSelector

selector = StockSelector()
result = selector.select(strategy, date, factor_data)
stocks = [s.stock_code for s in result.selections]
```

### 新代码（推荐）
```python
from core.strategy import AlphaGenerator

generator = AlphaGenerator()
alpha_result = generator.generate(strategy.factor_config, date, factor_data)
stocks = alpha_result.ranked_stocks[:strategy.max_positions]
```

## 相关文档
- [TODO.md](../../TODO.md) - 待办事项
- [REFACTOR_SUMMARY.md](../../REFACTOR_SUMMARY.md) - 重构总结

根据策略配置和信号选择股票。
"""

import warnings

warnings.warn(
    "StockSelector已废弃，请使用 core.strategy.AlphaGenerator",
    DeprecationWarning,
    stacklevel=2
)

from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import numpy as np

from .registry import StrategyMetadata, get_strategy_registry
from ..signal import (
    SignalGenerator, 
    SignalFilter, 
    FilterConfig,
    get_signal_generator,
    get_signal_filter
)
from ..factor import get_factor_storage
from ..infrastructure.exceptions import StrategyException


@dataclass
class StockSelection:
    """股票选择结果"""
    date: str
    stock_code: str
    score: float
    rank: int
    signals: Dict[str, float]
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "stock_code": self.stock_code,
            "score": self.score,
            "rank": self.rank,
            "signals": self.signals,
            "metadata": self.metadata or {}
        }


@dataclass
class SelectionResult:
    """选择结果"""
    success: bool
    strategy_id: str
    date: str
    selections: List[StockSelection]
    total_candidates: int
    selected_count: int
    error_message: Optional[str] = None


class ScoreCalculator:
    """
    得分计算器
    
    计算股票的综合得分。
    """
    
    @staticmethod
    def weighted_sum(
        signal_scores: Dict[str, float],
        weights: Dict[str, float]
    ) -> float:
        """加权求和"""
        total = 0.0
        total_weight = 0.0
        
        for signal_id, score in signal_scores.items():
            weight = weights.get(signal_id, 0)
            total += score * weight
            total_weight += weight
        
        return total / total_weight if total_weight > 0 else 0.0
    
    @staticmethod
    def rank_average(
        signal_ranks: Dict[str, int],
        weights: Dict[str, float]
    ) -> float:
        """排名平均"""
        total = 0.0
        total_weight = 0.0
        
        for signal_id, rank in signal_ranks.items():
            weight = weights.get(signal_id, 0)
            total += rank * weight
            total_weight += weight
        
        return total / total_weight if total_weight > 0 else 0.0


class StockSelector:
    """
    股票选择器
    
    根据策略配置选择股票。
    """
    
    def __init__(self):
        """初始化股票选择器"""
        self._registry = get_strategy_registry()
        self._signal_generator = get_signal_generator()
        self._signal_filter = get_signal_filter()
        self._factor_storage = get_factor_storage()
        self._score_calculator = ScoreCalculator()
    
    def select(
        self,
        strategy: Union[str, StrategyMetadata],
        date: str,
        factor_data: Dict[str, pd.DataFrame],
        industry_data: Optional[Dict[str, str]] = None,
        exclude_stocks: Optional[List[str]] = None
    ) -> SelectionResult:
        """
        选择股票
        
        Args:
            strategy: 策略ID或策略元数据
            date: 选择日期
            factor_data: 因子数据字典
            industry_data: 行业数据
            exclude_stocks: 排除股票列表
            
        Returns:
            SelectionResult: 选择结果
        """
        if isinstance(strategy, str):
            strategy_meta = self._registry.get(strategy)
            if strategy_meta is None:
                return SelectionResult(
                    success=False,
                    strategy_id=strategy,
                    date=date,
                    selections=[],
                    total_candidates=0,
                    selected_count=0,
                    error_message=f"策略不存在: {strategy}"
                )
        else:
            strategy_meta = strategy
        
        strategy_id = strategy_meta.id
        
        try:
            signal_results = self._signal_generator.generate_batch(
                strategy_meta.signals.signal_ids,
                factor_data
            )
            
            all_signals = []
            for signal_id, result in signal_results.items():
                if result.success:
                    date_signals = [s for s in result.signals if s.date == date]
                    all_signals.extend(date_signals)
            
            if not all_signals:
                return SelectionResult(
                    success=True,
                    strategy_id=strategy_id,
                    date=date,
                    selections=[],
                    total_candidates=0,
                    selected_count=0
                )
            
            filter_config = FilterConfig(
                max_signals_per_day=strategy_meta.max_positions * 3,
                exclude_stocks=exclude_stocks or []
            )
            
            filter_result = self._signal_filter.filter(all_signals, industry_data)
            
            if not filter_result.success:
                return SelectionResult(
                    success=False,
                    strategy_id=strategy_id,
                    date=date,
                    selections=[],
                    total_candidates=0,
                    selected_count=0,
                    error_message=filter_result.error_message
                )
            
            filtered_signals = filter_result.filtered_signals
            
            stock_scores = self._aggregate_signals(
                filtered_signals,
                strategy_meta.signals
            )
            
            selections = []
            sorted_stocks = sorted(
                stock_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for rank, (stock_code, score) in enumerate(sorted_stocks[:strategy_meta.max_positions]):
                signal_scores = {}
                for sig in filtered_signals:
                    if sig.stock_code == stock_code:
                        signal_scores[sig.signal_id] = sig.score
                
                selection = StockSelection(
                    date=date,
                    stock_code=stock_code,
                    score=score,
                    rank=rank + 1,
                    signals=signal_scores
                )
                selections.append(selection)
            
            return SelectionResult(
                success=True,
                strategy_id=strategy_id,
                date=date,
                selections=selections,
                total_candidates=len(stock_scores),
                selected_count=len(selections)
            )
            
        except Exception as e:
            return SelectionResult(
                success=False,
                strategy_id=strategy_id,
                date=date,
                selections=[],
                total_candidates=0,
                selected_count=0,
                error_message=str(e)
            )
    
    def _aggregate_signals(
        self,
        signals: List[Any],
        signal_config: Any
    ) -> Dict[str, float]:
        """聚合信号得分"""
        stock_signals: Dict[str, Dict[str, float]] = {}
        
        for sig in signals:
            if sig.stock_code not in stock_signals:
                stock_signals[sig.stock_code] = {}
            stock_signals[sig.stock_code][sig.signal_id] = sig.score
        
        weights = dict(zip(signal_config.signal_ids, signal_config.weights))
        
        stock_scores = {}
        for stock_code, sig_scores in stock_signals.items():
            if signal_config.combination_method == "weighted_sum":
                score = self._score_calculator.weighted_sum(sig_scores, weights)
            else:
                score = self._score_calculator.weighted_sum(sig_scores, weights)
            
            stock_scores[stock_code] = score
        
        return stock_scores
    
    def select_batch(
        self,
        strategy_id: str,
        dates: List[str],
        factor_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, SelectionResult]:
        """
        批量选择股票
        
        Args:
            strategy_id: 策略ID
            dates: 日期列表
            factor_data: 因子数据字典
            
        Returns:
            Dict[str, SelectionResult]: 选择结果字典
        """
        results = {}
        
        for date in dates:
            results[date] = self.select(strategy_id, date, factor_data)
        
        return results
    
    def get_rebalance_stocks(
        self,
        strategy_id: str,
        current_positions: List[str],
        new_selections: List[StockSelection]
    ) -> Dict[str, List[str]]:
        """
        获取调仓股票
        
        Args:
            strategy_id: 策略ID
            current_positions: 当前持仓
            new_selections: 新选择结果
            
        Returns:
            Dict[str, List[str]]: 调仓信息
        """
        new_stocks = {s.stock_code for s in new_selections}
        current_set = set(current_positions)
        
        to_buy = list(new_stocks - current_set)
        to_sell = list(current_set - new_stocks)
        to_hold = list(current_set & new_stocks)
        
        return {
            "buy": to_buy,
            "sell": to_sell,
            "hold": to_hold
        }


from typing import Union


_default_selector: Optional[StockSelector] = None


def get_stock_selector() -> StockSelector:
    """获取全局股票选择器实例"""
    global _default_selector
    if _default_selector is None:
        _default_selector = StockSelector()
    return _default_selector


def reset_stock_selector():
    """重置全局股票选择器"""
    global _default_selector
    _default_selector = None
