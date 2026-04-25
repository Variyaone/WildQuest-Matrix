"""
因子组合优化模块

实现因子权重优化和组合，生成Alpha预测。
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from scipy.optimize import minimize

from ..factor import get_factor_registry, FactorMetadata
from ..infrastructure.logging import get_logger

logger = get_logger("strategy.factor_combiner")


@dataclass
class FactorCombinationConfig:
    """因子组合配置"""
    factor_ids: List[str] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)
    combination_method: str = "ic_weighted"  # ic_weighted, ir_weighted, equal, ml
    
    min_ic: float = 0.02
    min_ir: float = 0.3
    min_win_rate: float = 0.0
    
    lookback_periods: int = 252
    rebalance_frequency: str = "monthly"
    
    # 修复：添加实时计算的因子IC值
    factor_ic_values: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_ids": self.factor_ids,
            "weights": self.weights,
            "combination_method": self.combination_method,
            "min_ic": self.min_ic,
            "min_ir": self.min_ir,
            "min_win_rate": self.min_win_rate,
            "lookback_periods": self.lookback_periods,
            "rebalance_frequency": self.rebalance_frequency
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactorCombinationConfig":
        return cls(
            factor_ids=data.get("factor_ids", []),
            weights=data.get("weights", []),
            combination_method=data.get("combination_method", "ic_weighted"),
            min_ic=data.get("min_ic", 0.02),
            min_ir=data.get("min_ir", 0.3),
            min_win_rate=data.get("min_win_rate", 0.0),
            lookback_periods=data.get("lookback_periods", 252),
            rebalance_frequency=data.get("rebalance_frequency", "monthly")
        )


@dataclass
class FactorCombinationResult:
    """因子组合结果"""
    success: bool
    factor_ids: List[str]
    weights: List[float]
    method: str
    
    expected_return: float = 0.0
    expected_risk: float = 0.0
    sharpe_ratio: float = 0.0
    
    factor_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    error_message: Optional[str] = None


class FactorCombiner:
    """
    因子组合优化器
    
    实现因子筛选、权重优化和组合。
    """
    
    def __init__(self):
        """初始化因子组合器"""
        self._factor_registry = get_factor_registry()
    
    def filter_factors(
        self,
        factors: List[FactorMetadata],
        min_ic: float = 0.02,
        min_ir: float = 0.3,
        min_win_rate: float = 0.0
    ) -> List[FactorMetadata]:
        """
        筛选有效因子
        
        Args:
            factors: 因子列表
            min_ic: 最小IC
            min_ir: 最小IR
            min_win_rate: 最小胜率
            
        Returns:
            筛选后的因子列表
        """
        selected = []
        
        for factor in factors:
            ic = 0.0
            ir = 0.0
            win_rate = 0.0
            
            if factor.quality_metrics:
                ic = abs(factor.quality_metrics.ic_mean) if factor.quality_metrics.ic_mean else 0
                ir = abs(factor.quality_metrics.ir) if factor.quality_metrics.ir else 0
                win_rate = factor.quality_metrics.win_rate if factor.quality_metrics.win_rate else 0
            
            if factor.backtest_results and ic == 0:
                latest_backtest = list(factor.backtest_results.values())[-1] if factor.backtest_results else None
                if latest_backtest:
                    ic = abs(latest_backtest.ic) if latest_backtest.ic else 0
                    if not win_rate and latest_backtest.win_rate:
                        win_rate = latest_backtest.win_rate
            
            if ic >= min_ic and ir >= min_ir and win_rate >= min_win_rate:
                selected.append(factor)
        
        logger.info(f"因子筛选: {len(factors)} → {len(selected)}")
        return selected
    
    def optimize_weights_ic(
        self,
        factors: List[FactorMetadata],
        factor_ic_values: Optional[Dict[str, float]] = None
    ) -> Tuple[List[float], Dict[str, Any]]:
        """
        IC加权优化
        
        Args:
            factors: 因子列表
            factor_ic_values: 实时计算的因子IC值（可选）
            
        Returns:
            (权重列表, 指标字典)
        """
        if not factors:
            return [], {}
        
        # 修复：优先使用实时计算的因子IC值
        if factor_ic_values:
            ics = []
            for f in factors:
                ic = factor_ic_values.get(f.id, 0.0)
                ics.append(abs(ic))
        else:
            ics = []
            for f in factors:
                ic = 0.0
                if f.quality_metrics and f.quality_metrics.ic_mean:
                    ic = abs(f.quality_metrics.ic_mean)
                elif f.backtest_results:
                    latest_backtest = list(f.backtest_results.values())[-1] if f.backtest_results else None
                    if latest_backtest and latest_backtest.ic:
                        ic = abs(latest_backtest.ic)
                ics.append(ic)
        
        ics = np.array(ics)
        total_ic = ics.sum()
        
        if total_ic > 0:
            weights = (ics / total_ic).tolist()
        else:
            weights = [1.0 / len(factors)] * len(factors)
        
        metrics = {
            "method": "ic_weighted",
            "total_ic": total_ic,
            "avg_ic": ics.mean(),
            "factor_ics": {f.id: ic for f, ic in zip(factors, ics)}
        }
        
        return weights, metrics
    
    def optimize_weights_ir(
        self,
        factors: List[FactorMetadata]
    ) -> Tuple[List[float], Dict[str, Any]]:
        """
        IR加权优化
        
        Args:
            factors: 因子列表
            
        Returns:
            (权重列表, 指标字典)
        """
        if not factors:
            return [], {}
        
        irs = []
        for f in factors:
            ir = 0.0
            if f.quality_metrics and f.quality_metrics.ir:
                ir = abs(f.quality_metrics.ir)
            irs.append(ir)
        
        irs = np.array(irs)
        total_ir = irs.sum()
        
        if total_ir > 0:
            weights = (irs / total_ir).tolist()
        else:
            weights = [1.0 / len(factors)] * len(factors)
        
        metrics = {
            "method": "ir_weighted",
            "total_ir": total_ir,
            "avg_ir": irs.mean(),
            "factor_irs": {f.id: ir for f, ir in zip(factors, irs)}
        }
        
        return weights, metrics
    
    def optimize_weights_mean_variance(
        self,
        factor_returns: pd.DataFrame
    ) -> Tuple[List[float], Dict[str, Any]]:
        """
        均值方差优化
        
        Args:
            factor_returns: 因子收益矩阵 (dates × factors)
            
        Returns:
            (权重列表, 指标字典)
        """
        if factor_returns.empty:
            return [], {}
        
        mean_returns = factor_returns.mean().values
        cov_matrix = factor_returns.cov().values
        
        n = len(mean_returns)
        
        def neg_sharpe(weights):
            port_return = np.dot(weights, mean_returns)
            port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            if port_vol == 0:
                return 0
            return -port_return / port_vol
        
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = [(0, 1) for _ in range(n)]
        
        initial_weights = np.ones(n) / n
        
        result = minimize(
            neg_sharpe,
            x0=initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            weights = result.x.tolist()
        else:
            weights = initial_weights.tolist()
        
        port_return = np.dot(weights, mean_returns)
        port_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
        sharpe = port_return / port_vol if port_vol > 0 else 0
        
        metrics = {
            "method": "mean_variance",
            "expected_return": port_return,
            "expected_volatility": port_vol,
            "sharpe_ratio": sharpe
        }
        
        return weights, metrics
    
    def combine(
        self,
        config: FactorCombinationConfig
    ) -> FactorCombinationResult:
        """
        组合因子
        
        Args:
            config: 组合配置
            
        Returns:
            组合结果
        """
        try:
            all_factors = self._factor_registry.list_all()
            
            if config.factor_ids:
                factors = [f for f in all_factors if f.id in config.factor_ids]
            else:
                factors = self.filter_factors(
                    all_factors,
                    min_ic=config.min_ic,
                    min_ir=config.min_ir,
                    min_win_rate=config.min_win_rate
                )
            
            if not factors:
                factors = all_factors[:5]
                logger.warning(f"因子筛选结果为空，使用前5个因子作为默认")
            
            if not factors:
                return FactorCombinationResult(
                    success=False,
                    factor_ids=[],
                    weights=[],
                    method=config.combination_method,
                    error_message="没有可用的因子"
                )
            
            if config.weights:
                weights = config.weights
                metrics = {"method": "custom"}
            else:
                if config.combination_method == "ic_weighted":
                    weights, metrics = self.optimize_weights_ic(factors, config.factor_ic_values)
                elif config.combination_method == "ir_weighted":
                    weights, metrics = self.optimize_weights_ir(factors)
                elif config.combination_method == "equal":
                    weights = [1.0 / len(factors)] * len(factors)
                    metrics = {"method": "equal_weight"}
                else:
                    weights, metrics = self.optimize_weights_ic(factors, config.factor_ic_values)
            
            factor_metrics = {}
            for f in factors:
                metrics = {
                    "ic": 0.0,
                    "ir": 0.0,
                    "win_rate": 0.0,
                    "avg_return": 0.0
                }
                
                if f.quality_metrics:
                    metrics["ir"] = f.quality_metrics.ir or 0
                    metrics["win_rate"] = f.quality_metrics.win_rate or 0
                
                if f.backtest_results:
                    latest_backtest = list(f.backtest_results.values())[-1] if f.backtest_results else None
                    if latest_backtest:
                        metrics["ic"] = latest_backtest.ic or 0
                        if not metrics["win_rate"]:
                            metrics["win_rate"] = latest_backtest.win_rate or 0
                        metrics["avg_return"] = latest_backtest.annual_return or 0
                
                factor_metrics[f.id] = metrics
            
            return FactorCombinationResult(
                success=True,
                factor_ids=[f.id for f in factors],
                weights=weights,
                method=metrics.get("method", config.combination_method),
                expected_return=metrics.get("expected_return", 0),
                expected_risk=metrics.get("expected_volatility", 0),
                sharpe_ratio=metrics.get("sharpe_ratio", 0),
                factor_metrics=factor_metrics
            )
            
        except Exception as e:
            logger.error(f"因子组合失败: {e}")
            return FactorCombinationResult(
                success=False,
                factor_ids=[],
                weights=[],
                method=config.combination_method,
                error_message=str(e)
            )


_default_combiner: Optional[FactorCombiner] = None


def get_factor_combiner() -> FactorCombiner:
    """获取因子组合器实例"""
    global _default_combiner
    if _default_combiner is None:
        _default_combiner = FactorCombiner()
    return _default_combiner


def reset_factor_combiner():
    """重置因子组合器实例"""
    global _default_combiner
    _default_combiner = None
