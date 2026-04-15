"""
风险预算配置模块

为不同资产/因子分配风险预算:
- 因子风险预算: 各因子风险贡献分配
- 资产风险预算: 各资产风险贡献分配
- 动态风险预算: 根据市场状态调整
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from core.infrastructure.exceptions import AppException, ErrorCode

logger = logging.getLogger(__name__)


class RiskBudgetType(Enum):
    """风险预算类型"""
    FACTOR = "factor"
    ASSET = "asset"
    DYNAMIC = "dynamic"


class RiskBudgetStatus(Enum):
    """风险预算状态"""
    WITHIN_BUDGET = "within_budget"
    EXCEEDED = "exceeded"
    WARNING = "warning"


@dataclass
class RiskBudgetItem:
    """风险预算项"""
    name: str
    budget: float
    actual: float = 0.0
    deviation: float = 0.0
    within_budget: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'budget': self.budget,
            'actual': self.actual,
            'deviation': self.deviation,
            'within_budget': self.within_budget
        }


@dataclass
class RiskBudgetResult:
    """风险预算结果"""
    status: RiskBudgetStatus
    budget_type: RiskBudgetType
    items: List[RiskBudgetItem] = field(default_factory=list)
    total_budget: float = 0.0
    total_actual: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'budget_type': self.budget_type.value,
            'items': [item.to_dict() for item in self.items],
            'total_budget': self.total_budget,
            'total_actual': self.total_actual,
            'message': self.message,
            'details': self.details
        }


class RiskBudgetError(AppException):
    """风险预算错误异常"""
    
    def __init__(self, message: str, details: Optional[Dict] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.RISK_ERROR,
            details=details or {},
            cause=cause
        )


@dataclass
class RiskBudgetConfig:
    """风险预算配置"""
    default_risk_budget: Dict[str, float] = field(default_factory=lambda: {
        'momentum': 0.25,
        'value': 0.25,
        'quality': 0.25,
        'volatility': 0.25
    })
    risk_tolerance: float = 0.15
    max_single_risk: float = 0.05
    adjustment_factor: float = 0.5
    dynamic_adjustment: bool = False


class RiskBudgetManager:
    """
    风险预算管理器
    
    功能:
    - 分配风险预算
    - 检查风险预算执行情况
    - 调整风险预算
    """
    
    def __init__(self, config: RiskBudgetConfig = None):
        self.config = config or RiskBudgetConfig()
    
    def allocate(
        self,
        portfolio: dict,
        risk_budget: dict = None,
        cov_matrix: np.ndarray = None
    ) -> dict:
        """
        分配风险预算
        
        Args:
            portfolio: 组合权重 {stock_code: weight}
            risk_budget: 风险预算字典
            cov_matrix: 协方差矩阵
            
        Returns:
            风险预算分配
        """
        if risk_budget is None:
            risk_budget = self.config.default_risk_budget.copy()
        
        if not portfolio:
            logger.warning("组合为空，无法分配风险预算")
            return {}
        
        total_weight = sum(portfolio.values())
        
        risk_allocation = {}
        for stock, weight in portfolio.items():
            stock_risk_budget = {}
            for risk_type, budget in risk_budget.items():
                stock_risk_budget[risk_type] = budget * weight / total_weight if total_weight > 0 else 0
            
            risk_allocation[stock] = stock_risk_budget
        
        portfolio_risk = 0
        if cov_matrix is not None:
            weights_array = np.array(list(portfolio.values()))
            portfolio_risk = np.sqrt(np.dot(weights_array.T, np.dot(cov_matrix, weights_array)))
        
        logger.info(f"风险预算分配完成: {len(risk_allocation)} 只股票")
        
        return {
            'risk_budget': risk_budget,
            'risk_allocation': risk_allocation,
            'total_risk_budget': sum(risk_budget.values()),
            'portfolio_risk': portfolio_risk
        }
    
    def check(
        self,
        portfolio: dict,
        actual_risk: dict,
        risk_budget: dict = None
    ) -> RiskBudgetResult:
        """
        检查风险预算执行情况
        
        Args:
            portfolio: 组合权重
            actual_risk: 实际风险 {risk_type: risk_value}
            risk_budget: 风险预算
            
        Returns:
            RiskBudgetResult: 风险预算检查结果
        """
        if risk_budget is None:
            risk_budget = self.config.default_risk_budget.copy()
        
        items: List[RiskBudgetItem] = []
        all_within_budget = True
        has_warning = False
        
        for risk_type, budget in risk_budget.items():
            actual_value = actual_risk.get(risk_type, 0)
            deviation = actual_value - budget
            within_budget = actual_value <= budget
            
            if not within_budget:
                all_within_budget = False
                if deviation > budget * 0.2:
                    has_warning = True
            
            items.append(RiskBudgetItem(
                name=risk_type,
                budget=budget,
                actual=actual_value,
                deviation=deviation,
                within_budget=within_budget
            ))
        
        total_budget = sum(risk_budget.values())
        total_actual = sum(actual_risk.values())
        
        if all_within_budget:
            status = RiskBudgetStatus.WITHIN_BUDGET
            message = "所有风险预算均在控制范围内"
        elif has_warning:
            status = RiskBudgetStatus.WARNING
            message = "部分风险预算超限，需要关注"
        else:
            status = RiskBudgetStatus.EXCEEDED
            message = "风险预算超限"
        
        logger.info(f"风险预算检查: 总预算 {total_budget:.3f}, 实际 {total_actual:.3f}")
        
        return RiskBudgetResult(
            status=status,
            budget_type=RiskBudgetType.FACTOR,
            items=items,
            total_budget=total_budget,
            total_actual=total_actual,
            message=message,
            details={
                'all_within_budget': all_within_budget,
                'exceeded_count': sum(1 for item in items if not item.within_budget)
            }
        )
    
    def adjust_risk_budget(
        self,
        portfolio: dict,
        actual_risk: dict,
        adjustment_factor: float = None
    ) -> dict:
        """
        调整风险预算
        
        Args:
            portfolio: 组合权重
            actual_risk: 实际风险
            adjustment_factor: 调整因子 (0-1)
            
        Returns:
            调整后的风险预算
        """
        if adjustment_factor is None:
            adjustment_factor = self.config.adjustment_factor
        
        check_result = self.check(portfolio, actual_risk)
        
        adjusted_budget = self.config.default_risk_budget.copy()
        
        for item in check_result.items:
            if not item.within_budget:
                deviation = item.deviation
                adjustment = deviation * adjustment_factor
                adjusted_budget[item.name] = max(0.01, adjusted_budget[item.name] - adjustment)
        
        logger.info(f"风险预算调整: {len([item for item in check_result.items if not item.within_budget])} 个风险类型超限")
        
        return adjusted_budget
    
    def calculate_risk_contribution(
        self,
        weights: Dict[str, float],
        cov_matrix: np.ndarray,
        stock_codes: List[str] = None
    ) -> Dict[str, float]:
        """
        计算风险贡献
        
        Args:
            weights: 权重字典
            cov_matrix: 协方差矩阵
            stock_codes: 股票代码列表
            
        Returns:
            风险贡献字典
        """
        if stock_codes is None:
            stock_codes = list(weights.keys())
        
        weights_array = np.array([weights.get(code, 0) for code in stock_codes])
        
        portfolio_volatility = np.sqrt(np.dot(weights_array.T, np.dot(cov_matrix, weights_array)))
        
        if portfolio_volatility == 0:
            return {code: 0 for code in stock_codes}
        
        marginal_risk = np.dot(cov_matrix, weights_array) / portfolio_volatility
        
        risk_contributions = weights_array * marginal_risk
        
        return {code: rc for code, rc in zip(stock_codes, risk_contributions)}
    
    def calculate_factor_risk_budget(
        self,
        weights: Dict[str, float],
        factor_exposures: Dict[str, Dict[str, float]],
        factor_cov_matrix: np.ndarray,
        factor_names: List[str] = None
    ) -> Dict[str, float]:
        """
        计算因子风险预算
        
        Args:
            weights: 权重字典
            factor_exposures: 因子暴露 {stock_code: {factor: exposure}}
            factor_cov_matrix: 因子协方差矩阵
            factor_names: 因子名称列表
            
        Returns:
            因子风险贡献
        """
        if factor_names is None:
            factor_names = list(self.config.default_risk_budget.keys())
        
        stock_codes = list(weights.keys())
        n_factors = len(factor_names)
        
        portfolio_exposures = np.zeros(n_factors)
        for i, factor in enumerate(factor_names):
            for stock, weight in weights.items():
                exposure = factor_exposures.get(stock, {}).get(factor, 0)
                portfolio_exposures[i] += weight * exposure
        
        factor_variances = np.dot(portfolio_exposures.T, np.dot(factor_cov_matrix, portfolio_exposures))
        
        if factor_variances == 0:
            return {factor: 0 for factor in factor_names}
        
        factor_risk_contributions = {}
        for i, factor in enumerate(factor_names):
            marginal_contribution = np.dot(factor_cov_matrix[i, :], portfolio_exposures)
            factor_risk_contributions[factor] = portfolio_exposures[i] * marginal_contribution / np.sqrt(factor_variances)
        
        return factor_risk_contributions
    
    def dynamic_adjust(
        self,
        portfolio: dict,
        market_state: dict,
        base_budget: dict = None
    ) -> dict:
        """
        动态调整风险预算
        
        Args:
            portfolio: 组合权重
            market_state: 市场状态
            base_budget: 基础风险预算
            
        Returns:
            动态调整后的风险预算
        """
        if base_budget is None:
            base_budget = self.config.default_risk_budget.copy()
        
        adjusted_budget = base_budget.copy()
        
        volatility_regime = market_state.get('volatility_regime', 'normal')
        if volatility_regime == 'high':
            for factor in adjusted_budget:
                adjusted_budget[factor] *= 0.8
            logger.info("高波动环境，降低风险预算20%")
        elif volatility_regime == 'low':
            for factor in adjusted_budget:
                adjusted_budget[factor] *= 1.1
            logger.info("低波动环境，提高风险预算10%")
        
        trend_strength = market_state.get('trend_strength', 0)
        if abs(trend_strength) > 0.5:
            if trend_strength > 0:
                if 'momentum' in adjusted_budget:
                    adjusted_budget['momentum'] *= 1.2
            else:
                if 'momentum' in adjusted_budget:
                    adjusted_budget['momentum'] *= 0.8
        
        total_budget = sum(adjusted_budget.values())
        if total_budget > 0:
            adjusted_budget = {k: v / total_budget for k, v in adjusted_budget.items()}
        
        return adjusted_budget


__all__ = [
    'RiskBudgetType',
    'RiskBudgetStatus',
    'RiskBudgetItem',
    'RiskBudgetResult',
    'RiskBudgetConfig',
    'RiskBudgetError',
    'RiskBudgetManager',
]
