"""
信号过滤器模块

过滤低质量信号，支持信号强度阈值、历史胜率阈值、市场环境匹配、行业分散度等过滤维度。
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import numpy as np

from .registry import SignalMetadata, get_signal_registry
from .generator import GeneratedSignal, SignalGenerationResult
from ..infrastructure.exceptions import SignalException


@dataclass
class FilterConfig:
    """过滤器配置"""
    min_strength: str = "weak"
    min_win_rate: float = 0.0
    min_confidence: float = 0.0
    max_signals_per_day: int = 100
    max_industry_concentration: float = 0.3
    min_signal_count: int = 1
    exclude_stocks: List[str] = None
    include_stocks: List[str] = None
    
    def __post_init__(self):
        if self.exclude_stocks is None:
            self.exclude_stocks = []
        if self.include_stocks is None:
            self.include_stocks = []


@dataclass
class FilterResult:
    """过滤结果"""
    success: bool
    original_count: int
    filtered_count: int
    filtered_signals: List[GeneratedSignal]
    filter_stats: Dict[str, int]
    error_message: Optional[str] = None


class StrengthFilter:
    """
    信号强度过滤器
    
    根据信号强度过滤信号。
    """
    
    STRENGTH_ORDER = {"强": 3, "中": 2, "弱": 1}
    
    def __init__(self, min_strength: str = "weak"):
        """
        初始化强度过滤器
        
        Args:
            min_strength: 最小强度
        """
        self.min_strength = min_strength
        self.min_level = self.STRENGTH_ORDER.get(min_strength, 1)
    
    def filter(self, signals: List[GeneratedSignal]) -> List[GeneratedSignal]:
        """
        过滤信号
        
        Args:
            signals: 信号列表
            
        Returns:
            List[GeneratedSignal]: 过滤后的信号列表
        """
        return [
            s for s in signals 
            if self.STRENGTH_ORDER.get(s.strength.value, 0) >= self.min_level
        ]


class WinRateFilter:
    """
    历史胜率过滤器
    
    根据信号历史胜率过滤。
    """
    
    def __init__(self, min_win_rate: float = 0.5):
        """
        初始化胜率过滤器
        
        Args:
            min_win_rate: 最小胜率
        """
        self.min_win_rate = min_win_rate
        self._registry = get_signal_registry()
    
    def filter(self, signals: List[GeneratedSignal]) -> List[GeneratedSignal]:
        """
        过滤信号
        
        Args:
            signals: 信号列表
            
        Returns:
            List[GeneratedSignal]: 过滤后的信号列表
        """
        result = []
        
        for signal in signals:
            signal_meta = self._registry.get(signal.signal_id)
            
            if signal_meta and signal_meta.historical_performance:
                if signal_meta.historical_performance.win_rate >= self.min_win_rate:
                    result.append(signal)
            else:
                result.append(signal)
        
        return result


class ConfidenceFilter:
    """
    置信度过滤器
    
    根据信号置信度过滤。
    """
    
    def __init__(self, min_confidence: float = 0.5):
        """
        初始化置信度过滤器
        
        Args:
            min_confidence: 最小置信度
        """
        self.min_confidence = min_confidence
    
    def filter(self, signals: List[GeneratedSignal]) -> List[GeneratedSignal]:
        """
        过滤信号
        
        Args:
            signals: 信号列表
            
        Returns:
            List[GeneratedSignal]: 过滤后的信号列表
        """
        return [s for s in signals if s.confidence >= self.min_confidence]


class IndustryDiversificationFilter:
    """
    行业分散度过滤器
    
    确保信号在行业间分散。
    """
    
    def __init__(
        self, 
        max_concentration: float = 0.3,
        industry_data: Optional[Dict[str, str]] = None
    ):
        """
        初始化行业分散度过滤器
        
        Args:
            max_concentration: 最大行业集中度
            industry_data: 股票行业映射
        """
        self.max_concentration = max_concentration
        self.industry_data = industry_data or {}
    
    def filter(
        self, 
        signals: List[GeneratedSignal],
        date: Optional[str] = None
    ) -> List[GeneratedSignal]:
        """
        过滤信号
        
        Args:
            signals: 信号列表
            date: 日期
            
        Returns:
            List[GeneratedSignal]: 过滤后的信号列表
        """
        if not self.industry_data:
            return signals
        
        industry_counts: Dict[str, int] = {}
        total = len(signals)
        
        for signal in signals:
            industry = self.industry_data.get(signal.stock_code, "未知")
            industry_counts[industry] = industry_counts.get(industry, 0) + 1
        
        max_count = int(total * self.max_concentration)
        
        industry_selected: Dict[str, int] = {ind: 0 for ind in industry_counts}
        result = []
        
        for signal in signals:
            industry = self.industry_data.get(signal.stock_code, "未知")
            
            if industry_selected[industry] < max_count:
                result.append(signal)
                industry_selected[industry] += 1
        
        return result


class StockListFilter:
    """
    股票列表过滤器
    
    根据股票白名单/黑名单过滤。
    """
    
    def __init__(
        self,
        exclude_stocks: Optional[List[str]] = None,
        include_stocks: Optional[List[str]] = None
    ):
        """
        初始化股票列表过滤器
        
        Args:
            exclude_stocks: 排除股票列表
            include_stocks: 包含股票列表
        """
        self.exclude_stocks = set(exclude_stocks or [])
        self.include_stocks = set(include_stocks or [])
    
    def filter(self, signals: List[GeneratedSignal]) -> List[GeneratedSignal]:
        """
        过滤信号
        
        Args:
            signals: 信号列表
            
        Returns:
            List[GeneratedSignal]: 过滤后的信号列表
        """
        result = []
        
        for signal in signals:
            if signal.stock_code in self.exclude_stocks:
                continue
            
            if self.include_stocks and signal.stock_code not in self.include_stocks:
                continue
            
            result.append(signal)
        
        return result


class TopNFilter:
    """
    TopN过滤器
    
    只保留得分最高的N个信号。
    """
    
    def __init__(self, n: int = 100):
        """
        初始化TopN过滤器
        
        Args:
            n: 保留数量
        """
        self.n = n
    
    def filter(self, signals: List[GeneratedSignal]) -> List[GeneratedSignal]:
        """
        过滤信号
        
        Args:
            signals: 信号列表
            
        Returns:
            List[GeneratedSignal]: 过滤后的信号列表
        """
        sorted_signals = sorted(signals, key=lambda s: s.score, reverse=True)
        return sorted_signals[:self.n]


class SignalFilter:
    """
    信号过滤器
    
    整合多种过滤规则。
    """
    
    def __init__(self, config: Optional[FilterConfig] = None):
        """
        初始化信号过滤器
        
        Args:
            config: 过滤器配置
        """
        self.config = config or FilterConfig()
        
        self._strength_filter = StrengthFilter(self.config.min_strength)
        self._win_rate_filter = WinRateFilter(self.config.min_win_rate)
        self._confidence_filter = ConfidenceFilter(self.config.min_confidence)
        self._stock_filter = StockListFilter(
            self.config.exclude_stocks,
            self.config.include_stocks
        )
        self._topn_filter = TopNFilter(self.config.max_signals_per_day)
    
    def filter(
        self,
        signals: List[GeneratedSignal],
        industry_data: Optional[Dict[str, str]] = None
    ) -> FilterResult:
        """
        过滤信号
        
        Args:
            signals: 信号列表
            industry_data: 行业数据
            
        Returns:
            FilterResult: 过滤结果
        """
        try:
            original_count = len(signals)
            filter_stats = {}
            
            current_signals = signals
            filter_stats["original"] = original_count
            
            current_signals = self._strength_filter.filter(current_signals)
            filter_stats["after_strength"] = len(current_signals)
            
            current_signals = self._win_rate_filter.filter(current_signals)
            filter_stats["after_win_rate"] = len(current_signals)
            
            current_signals = self._confidence_filter.filter(current_signals)
            filter_stats["after_confidence"] = len(current_signals)
            
            current_signals = self._stock_filter.filter(current_signals)
            filter_stats["after_stock_list"] = len(current_signals)
            
            if industry_data:
                industry_filter = IndustryDiversificationFilter(
                    self.config.max_industry_concentration,
                    industry_data
                )
                current_signals = industry_filter.filter(current_signals)
                filter_stats["after_industry"] = len(current_signals)
            
            current_signals = self._topn_filter.filter(current_signals)
            filter_stats["after_topn"] = len(current_signals)
            
            return FilterResult(
                success=True,
                original_count=original_count,
                filtered_count=len(current_signals),
                filtered_signals=current_signals,
                filter_stats=filter_stats
            )
            
        except Exception as e:
            return FilterResult(
                success=False,
                original_count=len(signals),
                filtered_count=0,
                filtered_signals=[],
                filter_stats={},
                error_message=str(e)
            )
    
    def filter_by_date(
        self,
        signals: List[GeneratedSignal],
        date: str
    ) -> List[GeneratedSignal]:
        """
        按日期过滤信号
        
        Args:
            signals: 信号列表
            date: 日期
            
        Returns:
            List[GeneratedSignal]: 过滤后的信号列表
        """
        return [s for s in signals if s.date == date]
    
    def filter_by_custom(
        self,
        signals: List[GeneratedSignal],
        condition: Callable[[GeneratedSignal], bool]
    ) -> List[GeneratedSignal]:
        """
        自定义条件过滤
        
        Args:
            signals: 信号列表
            condition: 条件函数
            
        Returns:
            List[GeneratedSignal]: 过滤后的信号列表
        """
        return [s for s in signals if condition(s)]
    
    def deduplicate(
        self,
        signals: List[GeneratedSignal]
    ) -> List[GeneratedSignal]:
        """
        去重
        
        Args:
            signals: 信号列表
            
        Returns:
            List[GeneratedSignal]: 去重后的信号列表
        """
        seen = set()
        result = []
        
        for signal in signals:
            key = (signal.date, signal.stock_code, signal.signal_id)
            if key not in seen:
                seen.add(key)
                result.append(signal)
        
        return result
    
    def merge_signals(
        self,
        signals_list: List[List[GeneratedSignal]],
        merge_method: str = "best"
    ) -> List[GeneratedSignal]:
        """
        合并多组信号
        
        Args:
            signals_list: 信号列表的列表
            merge_method: 合并方法 ('best', 'union', 'intersection')
            
        Returns:
            List[GeneratedSignal]: 合并后的信号列表
        """
        if not signals_list:
            return []
        
        if merge_method == "best":
            all_signals = []
            for signals in signals_list:
                all_signals.extend(signals)
            return self._topn_filter.filter(all_signals)
        
        elif merge_method == "union":
            all_signals = []
            for signals in signals_list:
                all_signals.extend(signals)
            return self.deduplicate(all_signals)
        
        elif merge_method == "intersection":
            if len(signals_list) < 2:
                return signals_list[0] if signals_list else []
            
            signal_sets = []
            for signals in signals_list:
                signal_sets.append({
                    (s.date, s.stock_code) for s in signals
                })
            
            common_keys = signal_sets[0]
            for sset in signal_sets[1:]:
                common_keys = common_keys & sset
            
            result = []
            for signals in signals_list:
                for s in signals:
                    if (s.date, s.stock_code) in common_keys:
                        result.append(s)
            
            return self.deduplicate(result)
        
        return signals_list[0]


_default_filter: Optional[SignalFilter] = None


def get_signal_filter(config: Optional[FilterConfig] = None) -> SignalFilter:
    """获取全局信号过滤器实例"""
    global _default_filter
    if _default_filter is None or config is not None:
        _default_filter = SignalFilter(config)
    return _default_filter


def reset_signal_filter():
    """重置全局信号过滤器"""
    global _default_filter
    _default_filter = None
