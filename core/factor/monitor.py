"""
因子衰减监控模块

监控因子表现随时间的衰减情况，预警因子失效。

改进版本:
- 量化衰减阈值（IC/IR下降百分比）
- 自动触发重新验证
- 滚动窗口监控
- 多维度衰减评估
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import os

import pandas as pd
import numpy as np

from .registry import FactorMetadata, get_factor_registry
from .validator import ICAnalyzer, ICAnalysisResult
from ..infrastructure.exceptions import FactorException
from ..infrastructure.logging import get_logger


class DecayLevel(Enum):
    """
    衰减等级
    
    基于IC下降百分比判定:
    - NONE: IC下降 < 10%
    - MILD: IC下降 10-20%
    - MODERATE: IC下降 20-40%
    - SEVERE: IC下降 40-60%
    - CRITICAL: IC下降 > 60%
    """
    NONE = "无衰减"
    MILD = "轻微衰减"
    MODERATE = "中度衰减"
    SEVERE = "严重衰减"
    CRITICAL = "临界失效"


class DecayAction(Enum):
    """衰减触发动作"""
    NONE = "无动作"
    MONITOR = "持续监控"
    ALERT = "发出预警"
    REVALIDATE = "触发重新验证"
    DISABLE = "停用因子"


@dataclass
class DecayThresholds:
    """衰减阈值配置"""
    ic_decline_mild: float = 0.10
    ic_decline_moderate: float = 0.20
    ic_decline_severe: float = 0.40
    ic_decline_critical: float = 0.60
    
    ir_decline_mild: float = 0.15
    ir_decline_moderate: float = 0.30
    ir_decline_severe: float = 0.50
    
    ic_absolute_min: float = 0.02
    ir_absolute_min: float = 0.20
    
    rolling_window: int = 60
    short_term_window: int = 20


@dataclass
class DecayMetrics:
    """
    衰减指标
    
    Attributes:
        factor_id: 因子ID
        current_ic: 当前IC
        historical_ic: 历史IC（基准）
        ic_change: IC绝对变化
        current_ir: 当前IR
        historical_ir: 历史IR
        ir_change: IR绝对变化
        ic_change_pct: IC变化百分比
        ir_change_pct: IR变化百分比
        decay_level: 衰减等级
        decay_trend: 衰减趋势
        recommended_action: 建议动作
        rolling_ic_series: 滚动IC序列
        warning_message: 预警信息
        should_revalidate: 是否需要重新验证
    """
    factor_id: str
    current_ic: float
    historical_ic: float
    ic_change: float
    current_ir: float
    historical_ir: float
    ir_change: float
    ic_change_pct: float = 0.0
    ir_change_pct: float = 0.0
    decay_level: DecayLevel = DecayLevel.NONE
    decay_trend: str = "stable"
    recommended_action: DecayAction = DecayAction.NONE
    rolling_ic_series: Optional[pd.Series] = None
    warning_message: Optional[str] = None
    should_revalidate: bool = False


@dataclass
class DecayReport:
    """衰减报告"""
    report_date: str
    total_factors: int
    healthy_factors: int
    decaying_factors: int
    critical_factors: int
    factor_metrics: List[DecayMetrics] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class RollingICCalculator:
    """
    滚动IC计算器
    
    计算因子的滚动IC序列。
    """
    
    @staticmethod
    def calculate_rolling_ic(
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        window: int = 60,
        factor_col: str = "factor_value",
        return_col: str = "forward_return",
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> pd.Series:
        """
        计算滚动IC
        
        Args:
            factor_df: 因子数据
            return_df: 收益数据
            window: 滚动窗口
            factor_col: 因子值列名
            return_col: 收益列名
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            pd.Series: 滚动IC序列
        """
        ic_series = ICAnalyzer.calculate_ic_series(
            factor_df, return_df,
            factor_col, return_col,
            date_col, stock_col
        )
        
        rolling_ic = ic_series.rolling(window=window).mean()
        
        return rolling_ic


class DecayDetector:
    """
    衰减检测器
    
    检测因子衰减程度，基于量化阈值判定。
    """
    
    def __init__(self, thresholds: Optional[DecayThresholds] = None):
        """
        初始化衰减检测器
        
        Args:
            thresholds: 衰减阈值配置
        """
        self.thresholds = thresholds or DecayThresholds()
    
    def detect_decay(
        self,
        current_ic: float,
        historical_ic: float,
        current_ir: float,
        historical_ir: float
    ) -> Tuple[DecayLevel, str, DecayAction]:
        """
        检测衰减程度
        
        Args:
            current_ic: 当前IC
            historical_ic: 历史IC
            current_ir: 当前IR
            historical_ir: 历史IR
            
        Returns:
            Tuple[DecayLevel, str, DecayAction]: 衰减等级、趋势、建议动作
        """
        if historical_ic == 0:
            return DecayLevel.NONE, "stable", DecayAction.MONITOR
        
        ic_change_pct = (current_ic - historical_ic) / abs(historical_ic)
        ir_change_pct = (current_ir - historical_ir) / abs(historical_ir) if historical_ir != 0 else 0
        
        ic_decline = abs(ic_change_pct) if ic_change_pct < 0 else 0
        
        if current_ic < self.thresholds.ic_absolute_min and current_ic < historical_ic:
            level = DecayLevel.CRITICAL
            trend = "declining"
            action = DecayAction.DISABLE
        elif ic_decline >= self.thresholds.ic_decline_critical:
            level = DecayLevel.CRITICAL
            trend = "declining"
            action = DecayAction.DISABLE
        elif ic_decline >= self.thresholds.ic_decline_severe:
            level = DecayLevel.SEVERE
            trend = "declining"
            action = DecayAction.REVALIDATE
        elif ic_decline >= self.thresholds.ic_decline_moderate:
            level = DecayLevel.MODERATE
            trend = "declining"
            action = DecayAction.REVALIDATE
        elif ic_decline >= self.thresholds.ic_decline_mild:
            level = DecayLevel.MILD
            trend = "stable"
            action = DecayAction.ALERT
        elif ic_change_pct > 0.15:
            level = DecayLevel.NONE
            trend = "improving"
            action = DecayAction.NONE
        else:
            level = DecayLevel.NONE
            trend = "stable"
            action = DecayAction.NONE
        
        if current_ir < self.thresholds.ir_absolute_min and level == DecayLevel.NONE:
            level = DecayLevel.MILD
            action = DecayAction.ALERT
        
        return level, trend, action
    
    def should_trigger_revalidation(
        self,
        metrics: DecayMetrics
    ) -> bool:
        """
        判断是否应触发重新验证
        
        Args:
            metrics: 衰减指标
            
        Returns:
            bool: 是否需要重新验证
        """
        if metrics.decay_level in [DecayLevel.MODERATE, DecayLevel.SEVERE, DecayLevel.CRITICAL]:
            return True
        
        if metrics.current_ic < self.thresholds.ic_absolute_min:
            return True
        
        if metrics.current_ir < self.thresholds.ir_absolute_min:
            return True
        
        return False


class FactorMonitor:
    """
    因子衰减监控器
    
    监控因子表现衰减情况，自动触发重新验证。
    """
    
    def __init__(
        self,
        lookback_days: int = 252,
        short_term_days: int = 60,
        thresholds: Optional[DecayThresholds] = None
    ):
        """
        初始化因子监控器
        
        Args:
            lookback_days: 历史回看天数
            short_term_days: 短期观察天数
            thresholds: 衰减阈值配置
        """
        self.lookback_days = lookback_days
        self.short_term_days = short_term_days
        self.thresholds = thresholds or DecayThresholds()
        self._registry = get_factor_registry()
        self._detector = DecayDetector(self.thresholds)
        self.logger = get_logger("factor.monitor")
    
    def monitor_factor(
        self,
        factor_id: str,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        historical_ic: Optional[float] = None,
        historical_ir: Optional[float] = None
    ) -> DecayMetrics:
        """
        监控单个因子
        
        Args:
            factor_id: 因子ID
            factor_df: 因子数据
            return_df: 收益数据
            historical_ic: 历史IC（可选）
            historical_ir: 历史IR（可选）
            
        Returns:
            DecayMetrics: 衰减指标
        """
        factor = self._registry.get(factor_id)
        
        if historical_ic is None:
            if factor and factor.quality_metrics:
                historical_ic = factor.quality_metrics.ic_mean
            else:
                historical_ic = 0.03
        
        if historical_ir is None:
            if factor and factor.quality_metrics:
                historical_ir = factor.quality_metrics.ir
            else:
                historical_ir = 0.3
        
        ic_series = ICAnalyzer.calculate_ic_series(factor_df, return_df)
        ic_result = ICAnalyzer.analyze_ic(ic_series)
        
        current_ic = ic_result.ic_mean
        current_ir = ic_result.ic_ir
        
        ic_change = current_ic - historical_ic
        ir_change = current_ir - historical_ir
        
        ic_change_pct = ic_change / abs(historical_ic) if historical_ic != 0 else 0
        ir_change_pct = ir_change / abs(historical_ir) if historical_ir != 0 else 0
        
        decay_level, decay_trend, recommended_action = self._detector.detect_decay(
            current_ic, historical_ic,
            current_ir, historical_ir
        )
        
        should_revalidate = self._detector.should_trigger_revalidation(
            DecayMetrics(
                factor_id=factor_id,
                current_ic=current_ic,
                historical_ic=historical_ic,
                ic_change=ic_change,
                current_ir=current_ir,
                historical_ir=historical_ir,
                ir_change=ir_change
            )
        )
        
        warning_message = None
        if decay_level in [DecayLevel.SEVERE, DecayLevel.CRITICAL]:
            warning_message = (
                f"因子 {factor_id} 出现{decay_level.value}！"
                f"IC从 {historical_ic:.4f} 下降到 {current_ic:.4f} ({ic_change_pct:.1%})"
            )
        elif decay_level == DecayLevel.MODERATE:
            warning_message = (
                f"因子 {factor_id} 出现中度衰减，请关注。"
                f"IC从 {historical_ic:.4f} 下降到 {current_ic:.4f} ({ic_change_pct:.1%})"
            )
        elif decay_level == DecayLevel.MILD:
            warning_message = (
                f"因子 {factor_id} 出现轻微衰减。"
                f"IC从 {historical_ic:.4f} 变化到 {current_ic:.4f}"
            )
        
        if should_revalidate:
            self.logger.warning(f"因子 {factor_id} 需要重新验证: {warning_message}")
        
        rolling_ic = RollingICCalculator.calculate_rolling_ic(
            factor_df, return_df, window=self.thresholds.rolling_window
        )
        
        return DecayMetrics(
            factor_id=factor_id,
            current_ic=current_ic,
            historical_ic=historical_ic,
            ic_change=ic_change,
            ic_change_pct=ic_change_pct,
            current_ir=current_ir,
            historical_ir=historical_ir,
            ir_change=ir_change,
            ir_change_pct=ir_change_pct,
            decay_level=decay_level,
            decay_trend=decay_trend,
            recommended_action=recommended_action,
            rolling_ic_series=rolling_ic,
            warning_message=warning_message,
            should_revalidate=should_revalidate
        )
    
    def monitor_all_factors(
        self,
        factor_data: Dict[str, pd.DataFrame],
        return_df: pd.DataFrame
    ) -> DecayReport:
        """
        监控所有因子
        
        Args:
            factor_data: 因子数据字典
            return_df: 收益数据
            
        Returns:
            DecayReport: 衰减报告
        """
        metrics_list = []
        healthy_count = 0
        decaying_count = 0
        critical_count = 0
        
        for factor_id, factor_df in factor_data.items():
            metrics = self.monitor_factor(factor_id, factor_df, return_df)
            metrics_list.append(metrics)
            
            if metrics.decay_level == DecayLevel.NONE:
                healthy_count += 1
            elif metrics.decay_level in [DecayLevel.SEVERE, DecayLevel.CRITICAL]:
                critical_count += 1
            else:
                decaying_count += 1
        
        metrics_list.sort(key=lambda x: x.decay_level.value, reverse=True)
        
        recommendations = self._generate_recommendations(metrics_list)
        
        return DecayReport(
            report_date=datetime.now().strftime("%Y-%m-%d"),
            total_factors=len(factor_data),
            healthy_factors=healthy_count,
            decaying_factors=decaying_count,
            critical_factors=critical_count,
            factor_metrics=metrics_list,
            recommendations=recommendations
        )
    
    def _generate_recommendations(
        self,
        metrics_list: List[DecayMetrics]
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        critical_factors = [
            m for m in metrics_list 
            if m.decay_level == DecayLevel.CRITICAL
        ]
        if critical_factors:
            recommendations.append(
                f"建议立即停用以下因子: {', '.join(m.factor_id for m in critical_factors[:5])}"
            )
        
        severe_factors = [
            m for m in metrics_list 
            if m.decay_level == DecayLevel.SEVERE
        ]
        if severe_factors:
            recommendations.append(
                f"建议降低以下因子的权重: {', '.join(m.factor_id for m in severe_factors[:5])}"
            )
        
        improving_factors = [
            m for m in metrics_list 
            if m.decay_trend == "improving"
        ]
        if improving_factors:
            recommendations.append(
                f"以下因子表现正在改善，可考虑增加权重: {', '.join(m.factor_id for m in improving_factors[:3])}"
            )
        
        if not recommendations:
            recommendations.append("所有因子表现正常，建议继续保持当前配置")
        
        return recommendations
    
    def generate_decay_chart_data(
        self,
        metrics: DecayMetrics
    ) -> Dict[str, Any]:
        """
        生成衰减图表数据
        
        Args:
            metrics: 衰减指标
            
        Returns:
            Dict[str, Any]: 图表数据
        """
        if metrics.rolling_ic_series is None:
            return {}
        
        rolling_ic = metrics.rolling_ic_series.dropna()
        
        return {
            "factor_id": metrics.factor_id,
            "dates": [str(d) for d in rolling_ic.index],
            "rolling_ic": rolling_ic.values.tolist(),
            "historical_ic": metrics.historical_ic,
            "current_ic": metrics.current_ic,
            "decay_level": metrics.decay_level.value
        }
    
    def get_factor_health_score(
        self,
        metrics: DecayMetrics
    ) -> float:
        """
        计算因子健康分数
        
        Args:
            metrics: 衰减指标
            
        Returns:
            float: 健康分数 (0-100)
        """
        base_score = 100
        
        decay_penalties = {
            DecayLevel.NONE: 0,
            DecayLevel.MILD: 10,
            DecayLevel.MODERATE: 30,
            DecayLevel.SEVERE: 60,
            DecayLevel.CRITICAL: 90
        }
        
        penalty = decay_penalties.get(metrics.decay_level, 0)
        
        if metrics.decay_trend == "improving":
            penalty = max(0, penalty - 10)
        elif metrics.decay_trend == "declining":
            penalty = min(100, penalty + 10)
        
        return max(0, base_score - penalty)


_default_monitor: Optional[FactorMonitor] = None


def get_factor_monitor(
    lookback_days: int = 252,
    short_term_days: int = 60,
    warning_threshold: float = 0.3
) -> FactorMonitor:
    """获取全局因子监控器实例"""
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = FactorMonitor(lookback_days, short_term_days, warning_threshold)
    return _default_monitor


def reset_factor_monitor():
    """重置全局因子监控器"""
    global _default_monitor
    _default_monitor = None
