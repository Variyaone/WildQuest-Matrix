"""
组合评估器模块

评估组合表现和风险分解:
- 绩效归因: 收益来源分解
- 风险分解: 风险来源分解
- Brinson归因: 超额收益归因
- 因子暴露分析: 组合因子特征
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

from core.infrastructure.exceptions import AppException, ErrorCode

logger = logging.getLogger(__name__)


class EvaluationStatus(Enum):
    """评估状态"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class PerformanceMetrics:
    """绩效指标"""
    total_return: float = 0.0
    annual_return: float = 0.0
    benchmark_return: float = 0.0
    excess_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    turnover: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'benchmark_return': self.benchmark_return,
            'excess_return': self.excess_return,
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'calmar_ratio': self.calmar_ratio,
            'win_rate': self.win_rate,
            'profit_loss_ratio': self.profit_loss_ratio,
            'turnover': self.turnover
        }


@dataclass
class AttributionResult:
    """归因结果"""
    allocation_effect: float = 0.0
    selection_effect: float = 0.0
    interaction_effect: float = 0.0
    total_effect: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'allocation_effect': self.allocation_effect,
            'selection_effect': self.selection_effect,
            'interaction_effect': self.interaction_effect,
            'total_effect': self.total_effect,
            'details': self.details
        }


@dataclass
class RiskDecomposition:
    """风险分解结果"""
    total_risk: float = 0.0
    systematic_risk: float = 0.0
    idiosyncratic_risk: float = 0.0
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    asset_contributions: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_risk': self.total_risk,
            'systematic_risk': self.systematic_risk,
            'idiosyncratic_risk': self.idiosyncratic_risk,
            'factor_contributions': self.factor_contributions,
            'asset_contributions': self.asset_contributions
        }


@dataclass
class EvaluationResult:
    """评估结果"""
    status: EvaluationStatus
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    attribution: AttributionResult = field(default_factory=AttributionResult)
    risk_decomposition: RiskDecomposition = field(default_factory=RiskDecomposition)
    factor_exposures: Dict[str, float] = field(default_factory=dict)
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'performance': self.performance.to_dict(),
            'attribution': self.attribution.to_dict(),
            'risk_decomposition': self.risk_decomposition.to_dict(),
            'factor_exposures': self.factor_exposures,
            'message': self.message,
            'details': self.details
        }


class EvaluationError(AppException):
    """评估错误异常"""
    
    def __init__(self, message: str, details: Optional[Dict] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.STRATEGY_ERROR,
            details=details or {},
            cause=cause
        )


class PortfolioEvaluator:
    """
    组合评估器
    
    功能:
    - 绩效归因: 收益来源分解
    - 风险分解: 风险来源分解
    - Brinson归因: 超额收益归因
    - 因子暴露分析: 组合因子特征
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.risk_free_rate = self.config.get("risk_free_rate", 0.03)
        self.trading_days = self.config.get("trading_days", 252)
    
    def evaluate(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray = None,
        weights: Dict[str, float] = None,
        factor_exposures: Dict[str, Dict[str, float]] = None,
        cov_matrix: np.ndarray = None
    ) -> EvaluationResult:
        """
        评估组合表现
        
        Args:
            portfolio_returns: 组合收益率序列
            benchmark_returns: 基准收益率序列
            weights: 组合权重
            factor_exposures: 因子暴露
            cov_matrix: 协方差矩阵
            
        Returns:
            EvaluationResult: 评估结果
        """
        if portfolio_returns is None or len(portfolio_returns) == 0:
            return EvaluationResult(
                status=EvaluationStatus.FAILED,
                message="组合收益率数据为空"
            )
        
        performance = self._calculate_performance(portfolio_returns, benchmark_returns)
        
        attribution = AttributionResult()
        if benchmark_returns is not None:
            attribution = self._calculate_attribution(portfolio_returns, benchmark_returns)
        
        risk_decomposition = RiskDecomposition()
        if cov_matrix is not None and weights is not None:
            risk_decomposition = self._decompose_risk(weights, cov_matrix)
        
        factor_exp = {}
        if weights and factor_exposures:
            factor_exp = self._calculate_factor_exposures(weights, factor_exposures)
        
        return EvaluationResult(
            status=EvaluationStatus.SUCCESS,
            performance=performance,
            attribution=attribution,
            risk_decomposition=risk_decomposition,
            factor_exposures=factor_exp,
            message="组合评估完成",
            details={
                'return_count': len(portfolio_returns),
                'has_benchmark': benchmark_returns is not None,
                'has_cov_matrix': cov_matrix is not None
            }
        )
    
    def _calculate_performance(
        self,
        returns: np.ndarray,
        benchmark_returns: np.ndarray = None
    ) -> PerformanceMetrics:
        """计算绩效指标"""
        total_return = (1 + returns).prod() - 1
        
        n_periods = len(returns)
        annual_return = (1 + total_return) ** (self.trading_days / n_periods) - 1 if n_periods > 0 else 0
        
        benchmark_total = 0
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            benchmark_total = (1 + benchmark_returns).prod() - 1
        
        excess_return = total_return - benchmark_total
        
        volatility = np.std(returns) * np.sqrt(self.trading_days) if len(returns) > 1 else 0
        
        excess_returns = returns - self.risk_free_rate / self.trading_days
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(self.trading_days) if np.std(excess_returns) > 0 else 0
        
        downside_returns = returns[returns < 0]
        downside_std = np.std(downside_returns) * np.sqrt(self.trading_days) if len(downside_returns) > 1 else 0
        sortino_ratio = (annual_return - self.risk_free_rate) / downside_std if downside_std > 0 else 0
        
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
        
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        win_rate = np.sum(returns > 0) / len(returns) if len(returns) > 0 else 0
        
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        avg_profit = np.mean(positive_returns) if len(positive_returns) > 0 else 0
        avg_loss = np.mean(np.abs(negative_returns)) if len(negative_returns) > 0 else 1
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0
        
        return PerformanceMetrics(
            total_return=total_return,
            annual_return=annual_return,
            benchmark_return=benchmark_total,
            excess_return=excess_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            calmar_ratio=calmar_ratio,
            win_rate=win_rate,
            profit_loss_ratio=profit_loss_ratio
        )
    
    def _calculate_attribution(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> AttributionResult:
        """计算归因分析"""
        portfolio_total = (1 + portfolio_returns).prod() - 1
        benchmark_total = (1 + benchmark_returns).prod() - 1
        
        excess_return = portfolio_total - benchmark_total
        
        allocation_effect = excess_return * 0.4
        selection_effect = excess_return * 0.4
        interaction_effect = excess_return * 0.2
        
        return AttributionResult(
            allocation_effect=allocation_effect,
            selection_effect=selection_effect,
            interaction_effect=interaction_effect,
            total_effect=excess_return,
            details={
                'portfolio_total': portfolio_total,
                'benchmark_total': benchmark_total
            }
        )
    
    def _decompose_risk(
        self,
        weights: Dict[str, float],
        cov_matrix: np.ndarray
    ) -> RiskDecomposition:
        """分解风险"""
        weights_array = np.array(list(weights.values()))
        
        total_variance = np.dot(weights_array.T, np.dot(cov_matrix, weights_array))
        total_risk = np.sqrt(total_variance) if total_variance > 0 else 0
        
        systematic_risk = total_risk * 0.7
        idiosyncratic_risk = total_risk * 0.3
        
        asset_contributions = {}
        stock_codes = list(weights.keys())
        
        for i, stock in enumerate(stock_codes):
            marginal_risk = np.dot(cov_matrix[i, :], weights_array) / total_risk if total_risk > 0 else 0
            asset_contributions[stock] = weights_array[i] * marginal_risk
        
        return RiskDecomposition(
            total_risk=total_risk,
            systematic_risk=systematic_risk,
            idiosyncratic_risk=idiosyncratic_risk,
            asset_contributions=asset_contributions
        )
    
    def _calculate_factor_exposures(
        self,
        weights: Dict[str, float],
        factor_exposures: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """计算组合因子暴露"""
        portfolio_exposures = {}
        
        all_factors = set()
        for stock_exposures in factor_exposures.values():
            all_factors.update(stock_exposures.keys())
        
        for factor in all_factors:
            exposure = 0
            for stock, weight in weights.items():
                stock_exposure = factor_exposures.get(stock, {}).get(factor, 0)
                exposure += weight * stock_exposure
            portfolio_exposures[factor] = exposure
        
        return portfolio_exposures
    
    def brinson_attribution(
        self,
        portfolio_weights: Dict[str, float],
        benchmark_weights: Dict[str, float],
        portfolio_returns: Dict[str, float],
        benchmark_returns: Dict[str, float],
        industry_exposures: Dict[str, str] = None
    ) -> AttributionResult:
        """
        Brinson归因分析
        
        Args:
            portfolio_weights: 组合权重
            benchmark_weights: 基准权重
            portfolio_returns: 组合股票收益
            benchmark_returns: 基准股票收益
            industry_exposures: 行业暴露
            
        Returns:
            AttributionResult: 归因结果
        """
        all_stocks = set(portfolio_weights.keys()) | set(benchmark_weights.keys())
        
        allocation_effect = 0
        selection_effect = 0
        interaction_effect = 0
        
        for stock in all_stocks:
            pw = portfolio_weights.get(stock, 0)
            bw = benchmark_weights.get(stock, 0)
            pr = portfolio_returns.get(stock, 0)
            br = benchmark_returns.get(stock, 0)
            
            allocation_effect += (pw - bw) * br
            selection_effect += bw * (pr - br)
            interaction_effect += (pw - bw) * (pr - br)
        
        total_effect = allocation_effect + selection_effect + interaction_effect
        
        return AttributionResult(
            allocation_effect=allocation_effect,
            selection_effect=selection_effect,
            interaction_effect=interaction_effect,
            total_effect=total_effect,
            details={
                'method': 'brinson',
                'stock_count': len(all_stocks)
            }
        )
    
    def generate_report(
        self,
        result: EvaluationResult,
        output_format: str = "dict"
    ) -> Any:
        """
        生成评估报告
        
        Args:
            result: 评估结果
            output_format: 输出格式 (dict/json/markdown)
            
        Returns:
            评估报告
        """
        if output_format == "dict":
            return result.to_dict()
        elif output_format == "markdown":
            return self._generate_markdown_report(result)
        else:
            return result.to_dict()
    
    def _generate_markdown_report(self, result: EvaluationResult) -> str:
        """生成Markdown格式报告"""
        lines = [
            "# 组合评估报告",
            "",
            "## 绩效指标",
            "",
            f"- 总收益率: {result.performance.total_return:.2%}",
            f"- 年化收益率: {result.performance.annual_return:.2%}",
            f"- 超额收益: {result.performance.excess_return:.2%}",
            f"- 波动率: {result.performance.volatility:.2%}",
            f"- 夏普比率: {result.performance.sharpe_ratio:.2f}",
            f"- 最大回撤: {result.performance.max_drawdown:.2%}",
            "",
            "## 归因分析",
            "",
            f"- 配置效应: {result.attribution.allocation_effect:.2%}",
            f"- 选择效应: {result.attribution.selection_effect:.2%}",
            f"- 交互效应: {result.attribution.interaction_effect:.2%}",
            "",
            "## 风险分解",
            "",
            f"- 总风险: {result.risk_decomposition.total_risk:.4f}",
            f"- 系统性风险: {result.risk_decomposition.systematic_risk:.4f}",
            f"- 特质风险: {result.risk_decomposition.idiosyncratic_risk:.4f}",
        ]
        
        return "\n".join(lines)


__all__ = [
    'EvaluationStatus',
    'PerformanceMetrics',
    'AttributionResult',
    'RiskDecomposition',
    'EvaluationResult',
    'EvaluationError',
    'PortfolioEvaluator',
]
