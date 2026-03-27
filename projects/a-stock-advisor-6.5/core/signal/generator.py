"""
信号生成器模块

根据因子和规则生成交易信号，支持单因子信号、多因子组合信号、条件触发信号和自适应信号。
"""

from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import numpy as np

from .registry import (
    SignalMetadata, 
    SignalRules, 
    SignalDirection,
    SignalStrength,
    get_signal_registry
)
from ..factor import get_factor_engine, get_factor_storage
from ..infrastructure.exceptions import SignalException


@dataclass
class GeneratedSignal:
    """生成的信号"""
    signal_id: str
    date: str
    stock_code: str
    direction: SignalDirection
    strength: SignalStrength
    score: float
    factor_values: Dict[str, float]
    confidence: float = 0.0
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "date": self.date,
            "stock_code": self.stock_code,
            "direction": self.direction.value,
            "strength": self.strength.value,
            "score": self.score,
            "factor_values": self.factor_values,
            "confidence": self.confidence,
            "metadata": self.metadata or {}
        }


@dataclass
class SignalGenerationResult:
    """信号生成结果"""
    success: bool
    signal_id: str
    signals: List[GeneratedSignal] = None
    total_count: int = 0
    error_message: Optional[str] = None
    generation_time: float = 0.0


class FactorCombiner:
    """
    因子组合器
    
    支持多种因子组合方法。
    """
    
    @staticmethod
    def weighted_sum(
        factor_values: pd.DataFrame,
        weights: Dict[str, float]
    ) -> pd.Series:
        """
        加权求和
        
        Args:
            factor_values: 因子值DataFrame
            weights: 权重字典
            
        Returns:
            pd.Series: 组合得分
        """
        score = pd.Series(0.0, index=factor_values.index)
        total_weight = sum(weights.values())
        
        for factor_id, weight in weights.items():
            if factor_id in factor_values.columns:
                score += factor_values[factor_id] * (weight / total_weight)
        
        return score
    
    @staticmethod
    def rank_average(
        factor_values: pd.DataFrame,
        weights: Dict[str, float]
    ) -> pd.Series:
        """
        排名平均
        
        Args:
            factor_values: 因子值DataFrame
            weights: 权重字典
            
        Returns:
            pd.Series: 组合得分
        """
        rank_df = pd.DataFrame(index=factor_values.index)
        
        for factor_id in weights.keys():
            if factor_id in factor_values.columns:
                rank_df[factor_id] = factor_values[factor_id].rank(pct=True)
        
        return FactorCombiner.weighted_sum(rank_df, weights)
    
    @staticmethod
    def zscore_sum(
        factor_values: pd.DataFrame,
        weights: Dict[str, float]
    ) -> pd.Series:
        """
        Z分数求和
        
        Args:
            factor_values: 因子值DataFrame
            weights: 权重字典
            
        Returns:
            pd.Series: 组合得分
        """
        zscore_df = pd.DataFrame(index=factor_values.index)
        
        for factor_id in weights.keys():
            if factor_id in factor_values.columns:
                col = factor_values[factor_id]
                mean = col.mean()
                std = col.std()
                if std > 0:
                    zscore_df[factor_id] = (col - mean) / std
                else:
                    zscore_df[factor_id] = 0
        
        return FactorCombiner.weighted_sum(zscore_df, weights)


class SignalStrengthCalculator:
    """
    信号强度计算器
    
    根据得分计算信号强度。
    """
    
    STRONG_THRESHOLD = 0.8
    MEDIUM_THRESHOLD = 0.5
    WEAK_THRESHOLD = 0.2
    
    @staticmethod
    def calculate(score: float, threshold: float = 0.0) -> SignalStrength:
        """
        计算信号强度
        
        Args:
            score: 信号得分
            threshold: 阈值
            
        Returns:
            SignalStrength: 信号强度
        """
        adjusted_score = score - threshold
        
        if adjusted_score >= SignalStrengthCalculator.STRONG_THRESHOLD:
            return SignalStrength.STRONG
        elif adjusted_score >= SignalStrengthCalculator.MEDIUM_THRESHOLD:
            return SignalStrength.MEDIUM
        elif adjusted_score >= SignalStrengthCalculator.WEAK_THRESHOLD:
            return SignalStrength.WEAK
        else:
            return SignalStrength.WEAK


class SignalGenerator:
    """
    信号生成器
    
    根据因子和规则生成交易信号。
    """
    
    def __init__(self):
        """初始化信号生成器"""
        self._registry = get_signal_registry()
        self._factor_engine = get_factor_engine()
        self._factor_storage = get_factor_storage()
        self._combiner = FactorCombiner()
    
    def generate(
        self,
        signal: Union[str, SignalMetadata],
        factor_data: Dict[str, pd.DataFrame],
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> SignalGenerationResult:
        """
        生成信号
        
        Args:
            signal: 信号ID或信号元数据
            factor_data: 因子数据字典
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            SignalGenerationResult: 生成结果
        """
        start_time = datetime.now()
        
        if isinstance(signal, str):
            signal_meta = self._registry.get(signal)
            if signal_meta is None:
                return SignalGenerationResult(
                    success=False,
                    signal_id=signal,
                    error_message=f"信号不存在: {signal}"
                )
        else:
            signal_meta = signal
        
        signal_id = signal_meta.id
        
        try:
            signals = self._generate_signals(
                signal_meta, 
                factor_data,
                date_col,
                stock_col
            )
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            return SignalGenerationResult(
                success=True,
                signal_id=signal_id,
                signals=signals,
                total_count=len(signals),
                generation_time=generation_time
            )
            
        except Exception as e:
            return SignalGenerationResult(
                success=False,
                signal_id=signal_id,
                error_message=str(e)
            )
    
    def _generate_signals(
        self,
        signal_meta: SignalMetadata,
        factor_data: Dict[str, pd.DataFrame],
        date_col: str,
        stock_col: str
    ) -> List[GeneratedSignal]:
        """生成信号列表"""
        rules = signal_meta.rules
        
        missing_factors = [f for f in rules.factors if f not in factor_data]
        if missing_factors:
            raise SignalException(
                f"缺少因子数据: {missing_factors}",
                signal_id=signal_meta.id
            )
        
        combined_scores = self._combine_factors(rules, factor_data, date_col, stock_col)
        
        signals = []
        
        for date, group in combined_scores.groupby(date_col):
            for _, row in group.iterrows():
                score = row['score']
                
                if score >= rules.threshold:
                    strength = SignalStrengthCalculator.calculate(score, rules.threshold)
                    
                    factor_values = {}
                    for factor_id in rules.factors:
                        factor_df = factor_data[factor_id]
                        mask = (factor_df[date_col] == date) & (factor_df[stock_col] == row[stock_col])
                        if mask.any():
                            factor_values[factor_id] = factor_df.loc[mask, 'factor_value'].iloc[0]
                    
                    signal = GeneratedSignal(
                        signal_id=signal_meta.id,
                        date=str(date),
                        stock_code=row[stock_col],
                        direction=signal_meta.direction,
                        strength=strength,
                        score=score,
                        factor_values=factor_values,
                        confidence=min(score / (rules.threshold + 1), 1.0)
                    )
                    signals.append(signal)
        
        return signals
    
    def _combine_factors(
        self,
        rules: SignalRules,
        factor_data: Dict[str, pd.DataFrame],
        date_col: str,
        stock_col: str
    ) -> pd.DataFrame:
        """组合因子"""
        first_factor = factor_data[rules.factors[0]]
        combined = first_factor[[date_col, stock_col]].copy()
        
        factor_values_wide = pd.DataFrame({
            date_col: first_factor[date_col],
            stock_col: first_factor[stock_col]
        })
        
        for factor_id in rules.factors:
            factor_df = factor_data[factor_id]
            factor_values_wide = factor_values_wide.merge(
                factor_df[[date_col, stock_col, 'factor_value']].rename(
                    columns={'factor_value': factor_id}
                ),
                on=[date_col, stock_col],
                how='left'
            )
        
        weights = dict(zip(rules.factors, rules.weights)) if rules.weights else {f: 1.0 for f in rules.factors}
        
        if rules.combination_method == "weighted_sum":
            combined['score'] = self._combiner.weighted_sum(
                factor_values_wide[rules.factors], 
                weights
            )
        elif rules.combination_method == "rank_average":
            combined['score'] = self._combiner.rank_average(
                factor_values_wide[rules.factors], 
                weights
            )
        elif rules.combination_method == "zscore_sum":
            combined['score'] = self._combiner.zscore_sum(
                factor_values_wide[rules.factors], 
                weights
            )
        else:
            combined['score'] = self._combiner.weighted_sum(
                factor_values_wide[rules.factors], 
                weights
            )
        
        return combined
    
    def generate_batch(
        self,
        signal_ids: List[str],
        factor_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, SignalGenerationResult]:
        """
        批量生成信号
        
        Args:
            signal_ids: 信号ID列表
            factor_data: 因子数据字典
            
        Returns:
            Dict[str, SignalGenerationResult]: 生成结果字典
        """
        results = {}
        
        for signal_id in signal_ids:
            results[signal_id] = self.generate(signal_id, factor_data)
        
        return results
    
    def generate_with_conditions(
        self,
        signal: SignalMetadata,
        factor_data: Dict[str, pd.DataFrame],
        conditions: Dict[str, Callable],
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> SignalGenerationResult:
        """
        带条件生成信号
        
        Args:
            signal: 信号元数据
            factor_data: 因子数据字典
            conditions: 条件函数字典
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            SignalGenerationResult: 生成结果
        """
        result = self.generate(signal, factor_data, date_col, stock_col)
        
        if not result.success or not result.signals:
            return result
        
        filtered_signals = []
        for sig in result.signals:
            passed = True
            for cond_name, cond_func in conditions.items():
                if not cond_func(sig):
                    passed = False
                    break
            
            if passed:
                filtered_signals.append(sig)
        
        result.signals = filtered_signals
        result.total_count = len(filtered_signals)
        
        return result
    
    def create_custom_signal(
        self,
        name: str,
        description: str,
        factor_ids: List[str],
        weights: List[float],
        threshold: float,
        direction: SignalDirection,
        source: str = "自研"
    ) -> SignalMetadata:
        """
        创建自定义信号
        
        Args:
            name: 信号名称
            description: 信号描述
            factor_ids: 因子ID列表
            weights: 权重列表
            threshold: 阈值
            direction: 信号方向
            source: 来源
            
        Returns:
            SignalMetadata: 创建的信号元数据
        """
        from .registry import SignalType, SignalRules
        
        rules = SignalRules(
            factors=factor_ids,
            weights=weights,
            threshold=threshold,
            combination_method="weighted_sum"
        )
        
        return self._registry.register(
            name=name,
            description=description,
            signal_type=SignalType.STOCK_SELECTION,
            direction=direction,
            rules=rules,
            source=source
        )


_default_generator: Optional[SignalGenerator] = None


def get_signal_generator() -> SignalGenerator:
    """获取全局信号生成器实例"""
    global _default_generator
    if _default_generator is None:
        _default_generator = SignalGenerator()
    return _default_generator


def reset_signal_generator():
    """重置全局信号生成器"""
    global _default_generator
    _default_generator = None
