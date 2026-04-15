"""
组合优化器模块

支持多种优化方法:
- equal_weight: 等权重优化
- risk_parity: 风险平价优化
- mean_variance: 均值方差优化
- max_diversification: 最大分散化优化
- black_litterman: Black-Litterman优化
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from scipy.optimize import minimize

from core.infrastructure.exceptions import AppException, ErrorCode

logger = logging.getLogger(__name__)


class OptimizationStatus(Enum):
    """优化状态"""
    SUCCESS = "success"
    FAILED = "failed"
    FALLBACK = "fallback"
    INVALID_INPUT = "invalid_input"


@dataclass
class OptimizationResult:
    """优化结果"""
    status: OptimizationStatus
    weights: Dict[str, float] = field(default_factory=dict)
    method: str = ""
    message: str = ""
    fallback_used: bool = False
    original_method: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def is_success(self) -> bool:
        return self.status == OptimizationStatus.SUCCESS
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'weights': self.weights,
            'method': self.method,
            'message': self.message,
            'fallback_used': self.fallback_used,
            'original_method': self.original_method,
            'details': self.details
        }


class OptimizationError(AppException):
    """优化错误异常"""
    
    def __init__(self, message: str, details: Optional[Dict] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.STRATEGY_ERROR,
            details=details or {},
            cause=cause
        )


class PortfolioOptimizer:
    """
    组合优化器
    
    支持多种优化方法:
    - equal_weight: 等权重优化
    - risk_parity: 风险平价
    - mean_variance: 均值方差优化
    - max_diversification: 最大分散化
    - black_litterman: Black-Litterman模型
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.optimization_method = self.config.get("method", "equal_weight")
        self.max_single_weight = self.config.get("max_single_weight", 0.15)
        self.min_weight = self.config.get("min_weight", 0.01)
        self.risk_aversion = self.config.get("risk_aversion", 1.0)
        self.allow_fallback = self.config.get("allow_fallback", True)
        self.tau = self.config.get("tau", 0.05)
    
    def _validate_inputs(
        self,
        stock_scores: dict,
        expected_returns: dict = None,
        cov_matrix = None
    ) -> Tuple[bool, str]:
        """验证输入参数"""
        if not stock_scores:
            return False, "股票得分为空"
        
        if not isinstance(stock_scores, dict):
            return False, f"股票得分必须是字典类型，当前类型: {type(stock_scores)}"
        
        for code, score in stock_scores.items():
            if not isinstance(code, str):
                return False, f"股票代码必须是字符串类型，当前类型: {type(code)}"
            if not isinstance(score, (int, float)):
                return False, f"股票得分必须是数值类型，{code} 当前类型: {type(score)}"
        
        if expected_returns is not None:
            if not isinstance(expected_returns, dict):
                return False, f"预期收益率必须是字典类型，当前类型: {type(expected_returns)}"
        
        if cov_matrix is not None:
            if not isinstance(cov_matrix, np.ndarray):
                return False, f"协方差矩阵必须是numpy数组类型，当前类型: {type(cov_matrix)}"
            n = len(stock_scores)
            if cov_matrix.shape != (n, n):
                return False, f"协方差矩阵形状 {cov_matrix.shape} 与股票数量 {n} 不匹配"
        
        return True, ""
    
    def optimize(
        self,
        stock_scores: dict,
        expected_returns: dict = None,
        cov_matrix = None,
        views: dict = None,
        view_confidences: dict = None
    ) -> OptimizationResult:
        """
        优化组合权重
        
        Args:
            stock_scores: 股票得分字典 {stock_code: score}
            expected_returns: 预期收益率字典 {stock_code: return}
            cov_matrix: 协方差矩阵
            views: Black-Litterman观点 {stock_code: view_return}
            view_confidences: 观点置信度 {stock_code: confidence}
            
        Returns:
            OptimizationResult: 包含状态、权重、错误信息等
        """
        valid, error_msg = self._validate_inputs(stock_scores, expected_returns, cov_matrix)
        if not valid:
            logger.error(f"输入参数验证失败: {error_msg}")
            return OptimizationResult(
                status=OptimizationStatus.INVALID_INPUT,
                method="none",
                message=error_msg,
                details={'error_type': 'validation_error'}
            )
        
        stock_codes = list(stock_scores.keys())
        
        if self.optimization_method == "equal_weight":
            return self._optimize_equal_weight(stock_codes)
        elif self.optimization_method == "risk_parity":
            return self._optimize_risk_parity(stock_codes, cov_matrix)
        elif self.optimization_method == "mean_variance":
            return self._optimize_mean_variance(stock_codes, expected_returns, cov_matrix)
        elif self.optimization_method == "max_diversification":
            return self._optimize_max_diversification(stock_codes, cov_matrix)
        elif self.optimization_method == "black_litterman":
            return self._optimize_black_litterman(
                stock_codes, expected_returns, cov_matrix, views, view_confidences
            )
        else:
            logger.warning(f"未知的优化方法: {self.optimization_method}, 使用等权重")
            result = self._optimize_equal_weight(stock_codes)
            result.fallback_used = True
            result.original_method = self.optimization_method
            return result
    
    def _optimize_equal_weight(self, stock_codes: List[str]) -> OptimizationResult:
        """等权重优化"""
        n = len(stock_codes)
        weight = 1.0 / n
        
        weights = {code: weight for code in stock_codes}
        
        logger.info(f"等权重优化完成: {n} 只股票, 单只权重 {weight*100:.2f}%")
        
        return OptimizationResult(
            status=OptimizationStatus.SUCCESS,
            weights=weights,
            method="equal_weight",
            message=f"成功分配等权重给 {n} 只股票",
            details={'stock_count': n, 'weight_per_stock': weight}
        )
    
    def _optimize_risk_parity(
        self,
        stock_codes: List[str],
        cov_matrix = None
    ) -> OptimizationResult:
        """风险平价优化"""
        n = len(stock_codes)
        
        if cov_matrix is None:
            error_msg = "协方差矩阵为空，无法执行风险平价优化"
            logger.error(error_msg)
            
            if self.allow_fallback:
                logger.warning("降级为等权重优化")
                result = self._optimize_equal_weight(stock_codes)
                result.fallback_used = True
                result.original_method = "risk_parity"
                result.status = OptimizationStatus.FALLBACK
                result.message = f"风险平价优化失败(缺少协方差矩阵)，已降级为等权重"
                return result
            
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                method="risk_parity",
                message=error_msg,
                details={'error_type': 'missing_cov_matrix'}
            )
        
        def risk_parity_objective(weights):
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            marginal_risk = np.dot(cov_matrix, weights) / portfolio_volatility
            risk_contributions = weights * marginal_risk
            target_risk = portfolio_volatility / n
            
            return np.sum((risk_contributions - target_risk) ** 2)
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        ]
        
        bounds = [(self.min_weight, self.max_single_weight) for _ in range(n)]
        
        initial_weights = np.array([1.0 / n] * n)
        
        result = minimize(
            risk_parity_objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            weights = {code: w for code, w in zip(stock_codes, result.x)}
            logger.info(f"风险平价优化完成: {len(weights)} 只股票")
            
            return OptimizationResult(
                status=OptimizationStatus.SUCCESS,
                weights=weights,
                method="risk_parity",
                message="风险平价优化成功",
                details={'iterations': result.nit, 'objective_value': result.fun}
            )
        else:
            error_msg = f"风险平价优化失败: {result.message}"
            logger.error(error_msg)
            
            if self.allow_fallback:
                logger.warning("降级为等权重优化")
                fallback_result = self._optimize_equal_weight(stock_codes)
                fallback_result.fallback_used = True
                fallback_result.original_method = "risk_parity"
                fallback_result.status = OptimizationStatus.FALLBACK
                fallback_result.message = f"风险平价优化失败({result.message})，已降级为等权重"
                return fallback_result
            
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                method="risk_parity",
                message=error_msg,
                details={'error_type': 'optimization_failed', 'scipy_message': result.message}
            )
    
    def _optimize_mean_variance(
        self,
        stock_codes: List[str],
        expected_returns: dict = None,
        cov_matrix = None
    ) -> OptimizationResult:
        """均值方差优化"""
        n = len(stock_codes)
        
        if cov_matrix is None:
            error_msg = "协方差矩阵为空，无法执行均值方差优化"
            logger.error(error_msg)
            
            if self.allow_fallback:
                logger.warning("降级为等权重优化")
                result = self._optimize_equal_weight(stock_codes)
                result.fallback_used = True
                result.original_method = "mean_variance"
                result.status = OptimizationStatus.FALLBACK
                result.message = f"均值方差优化失败(缺少协方差矩阵)，已降级为等权重"
                return result
            
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                method="mean_variance",
                message=error_msg,
                details={'error_type': 'missing_cov_matrix'}
            )
        
        if expected_returns is None:
            error_msg = "预期收益率为空，无法执行均值方差优化"
            logger.error(error_msg)
            
            if self.allow_fallback:
                logger.warning("降级为等权重优化")
                result = self._optimize_equal_weight(stock_codes)
                result.fallback_used = True
                result.original_method = "mean_variance"
                result.status = OptimizationStatus.FALLBACK
                result.message = f"均值方差优化失败(缺少预期收益率)，已降级为等权重"
                return result
            
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                method="mean_variance",
                message=error_msg,
                details={'error_type': 'missing_expected_returns'}
            )
        
        mu = np.array([expected_returns.get(code, 0) for code in stock_codes])
        
        def mean_variance_objective(weights):
            portfolio_return = np.dot(weights, mu)
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            return -portfolio_return + self.risk_aversion * portfolio_variance
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        ]
        
        bounds = [(self.min_weight, self.max_single_weight) for _ in range(n)]
        
        initial_weights = np.array([1.0 / n] * n)
        
        result = minimize(
            mean_variance_objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            weights = {code: w for code, w in zip(stock_codes, result.x)}
            logger.info(f"均值方差优化完成: {len(weights)} 只股票")
            
            return OptimizationResult(
                status=OptimizationStatus.SUCCESS,
                weights=weights,
                method="mean_variance",
                message="均值方差优化成功",
                details={
                    'iterations': result.nit,
                    'objective_value': result.fun,
                    'risk_aversion': self.risk_aversion
                }
            )
        else:
            error_msg = f"均值方差优化失败: {result.message}"
            logger.error(error_msg)
            
            if self.allow_fallback:
                logger.warning("降级为等权重优化")
                fallback_result = self._optimize_equal_weight(stock_codes)
                fallback_result.fallback_used = True
                fallback_result.original_method = "mean_variance"
                fallback_result.status = OptimizationStatus.FALLBACK
                fallback_result.message = f"均值方差优化失败({result.message})，已降级为等权重"
                return fallback_result
            
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                method="mean_variance",
                message=error_msg,
                details={'error_type': 'optimization_failed', 'scipy_message': result.message}
            )
    
    def _optimize_max_diversification(
        self,
        stock_codes: List[str],
        cov_matrix = None
    ) -> OptimizationResult:
        """最大分散化优化"""
        n = len(stock_codes)
        
        if cov_matrix is None:
            error_msg = "协方差矩阵为空，无法执行最大分散化优化"
            logger.error(error_msg)
            
            if self.allow_fallback:
                logger.warning("降级为等权重优化")
                result = self._optimize_equal_weight(stock_codes)
                result.fallback_used = True
                result.original_method = "max_diversification"
                result.status = OptimizationStatus.FALLBACK
                result.message = f"最大分散化优化失败(缺少协方差矩阵)，已降级为等权重"
                return result
            
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                method="max_diversification",
                message=error_msg,
                details={'error_type': 'missing_cov_matrix'}
            )
        
        volatilities = np.sqrt(np.diag(cov_matrix))
        
        def max_diversification_objective(weights):
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            weighted_avg_volatility = np.dot(weights, volatilities)
            diversification_ratio = weighted_avg_volatility / portfolio_volatility
            return -diversification_ratio
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        ]
        
        bounds = [(self.min_weight, self.max_single_weight) for _ in range(n)]
        
        initial_weights = np.array([1.0 / n] * n)
        
        result = minimize(
            max_diversification_objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            weights = {code: w for code, w in zip(stock_codes, result.x)}
            logger.info(f"最大分散化优化完成: {len(weights)} 只股票")
            
            return OptimizationResult(
                status=OptimizationStatus.SUCCESS,
                weights=weights,
                method="max_diversification",
                message="最大分散化优化成功",
                details={'iterations': result.nit, 'objective_value': result.fun}
            )
        else:
            error_msg = f"最大分散化优化失败: {result.message}"
            logger.error(error_msg)
            
            if self.allow_fallback:
                logger.warning("降级为等权重优化")
                fallback_result = self._optimize_equal_weight(stock_codes)
                fallback_result.fallback_used = True
                fallback_result.original_method = "max_diversification"
                fallback_result.status = OptimizationStatus.FALLBACK
                fallback_result.message = f"最大分散化优化失败({result.message})，已降级为等权重"
                return fallback_result
            
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                method="max_diversification",
                message=error_msg,
                details={'error_type': 'optimization_failed', 'scipy_message': result.message}
            )
    
    def _optimize_black_litterman(
        self,
        stock_codes: List[str],
        expected_returns: dict = None,
        cov_matrix = None,
        views: dict = None,
        view_confidences: dict = None
    ) -> OptimizationResult:
        """Black-Litterman优化"""
        n = len(stock_codes)
        
        if cov_matrix is None:
            error_msg = "协方差矩阵为空，无法执行Black-Litterman优化"
            logger.error(error_msg)
            
            if self.allow_fallback:
                logger.warning("降级为等权重优化")
                result = self._optimize_equal_weight(stock_codes)
                result.fallback_used = True
                result.original_method = "black_litterman"
                result.status = OptimizationStatus.FALLBACK
                result.message = f"Black-Litterman优化失败(缺少协方差矩阵)，已降级为等权重"
                return result
            
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                method="black_litterman",
                message=error_msg,
                details={'error_type': 'missing_cov_matrix'}
            )
        
        market_weights = np.array([1.0 / n] * n)
        
        if expected_returns:
            pi = np.array([expected_returns.get(code, 0) for code in stock_codes])
        else:
            pi = np.dot(cov_matrix, market_weights) * self.risk_aversion
        
        if views is None or len(views) == 0:
            bl_returns = pi
            logger.info("无观点输入，使用市场均衡收益")
        else:
            P = np.zeros((len(views), n))
            Q = np.zeros(len(views))
            omega = np.zeros((len(views), len(views)))
            
            for i, (stock_code, view_return) in enumerate(views.items()):
                if stock_code in stock_codes:
                    idx = stock_codes.index(stock_code)
                    P[i, idx] = 1
                    Q[i] = view_return
                    
                    confidence = 1.0
                    if view_confidences and stock_code in view_confidences:
                        confidence = view_confidences[stock_code]
                    omega[i, i] = 1.0 / confidence if confidence > 0 else 1.0
            
            tau_sigma_inv = np.linalg.inv(self.tau * cov_matrix)
            omega_inv = np.linalg.inv(omega)
            
            bl_returns = np.linalg.inv(
                tau_sigma_inv + np.dot(P.T, np.dot(omega_inv, P))
            ) @ (
                np.dot(tau_sigma_inv, pi) + np.dot(P.T, np.dot(omega_inv, Q))
            )
            
            logger.info(f"Black-Litterman融合 {len(views)} 个观点")
        
        def mean_variance_objective(weights):
            portfolio_return = np.dot(weights, bl_returns)
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            return -portfolio_return + self.risk_aversion * portfolio_variance
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        ]
        
        bounds = [(self.min_weight, self.max_single_weight) for _ in range(n)]
        
        initial_weights = np.array([1.0 / n] * n)
        
        result = minimize(
            mean_variance_objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            weights = {code: w for code, w in zip(stock_codes, result.x)}
            logger.info(f"Black-Litterman优化完成: {len(weights)} 只股票")
            
            return OptimizationResult(
                status=OptimizationStatus.SUCCESS,
                weights=weights,
                method="black_litterman",
                message="Black-Litterman优化成功",
                details={
                    'iterations': result.nit,
                    'objective_value': result.fun,
                    'view_count': len(views) if views else 0,
                    'tau': self.tau
                }
            )
        else:
            error_msg = f"Black-Litterman优化失败: {result.message}"
            logger.error(error_msg)
            
            if self.allow_fallback:
                logger.warning("降级为等权重优化")
                fallback_result = self._optimize_equal_weight(stock_codes)
                fallback_result.fallback_used = True
                fallback_result.original_method = "black_litterman"
                fallback_result.status = OptimizationStatus.FALLBACK
                fallback_result.message = f"Black-Litterman优化失败({result.message})，已降级为等权重"
                return fallback_result
            
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                method="black_litterman",
                message=error_msg,
                details={'error_type': 'optimization_failed', 'scipy_message': result.message}
            )


__all__ = [
    'OptimizationStatus',
    'OptimizationResult',
    'OptimizationError',
    'PortfolioOptimizer',
]
