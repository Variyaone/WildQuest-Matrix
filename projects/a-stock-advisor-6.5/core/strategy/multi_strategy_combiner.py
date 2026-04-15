"""
多策略组合器

将多个策略的信号/持仓组合在一起，实现策略级资金分配。
支持：等权重、风险平价、均值方差、Black-Litterman等方法。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import logging

logger = logging.getLogger(__name__)


class AllocationMethod(Enum):
    """资金分配方法"""
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    MEAN_VARIANCE = "mean_variance"
    MIN_CORRELATION = "min_correlation"
    BLACK_LITTERMAN = "black_litterman"
    KELLY = "kelly"
    CUSTOM = "custom"


@dataclass
class StrategyAllocation:
    """策略资金分配"""
    strategy_id: str
    strategy_name: str
    weight: float
    capital: float
    expected_return: float = 0.0
    expected_risk: float = 0.0
    contribution_to_risk: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'weight': self.weight,
            'capital': self.capital,
            'expected_return': self.expected_return,
            'expected_risk': self.expected_risk,
            'contribution_to_risk': self.contribution_to_risk
        }


@dataclass
class MultiStrategyResult:
    """多策略组合结果"""
    success: bool
    allocations: List[StrategyAllocation] = field(default_factory=list)
    total_capital: float = 0.0
    expected_return: float = 0.0
    expected_risk: float = 0.0
    sharpe_ratio: float = 0.0
    diversification_ratio: float = 1.0
    method: str = ""
    correlation_matrix: Optional[pd.DataFrame] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'allocations': [a.to_dict() for a in self.allocations],
            'total_capital': self.total_capital,
            'expected_return': self.expected_return,
            'expected_risk': self.expected_risk,
            'sharpe_ratio': self.sharpe_ratio,
            'diversification_ratio': self.diversification_ratio,
            'method': self.method,
            'error_message': self.error_message
        }
    
    def get_weights_dict(self) -> Dict[str, float]:
        """获取策略权重字典"""
        return {a.strategy_id: a.weight for a in self.allocations}


@dataclass
class StrategyPerformance:
    """策略历史表现"""
    strategy_id: str
    strategy_name: str
    returns: pd.Series
    sharpe_ratio: float = 0.0
    annual_return: float = 0.0
    annual_volatility: float = 0.0
    max_drawdown: float = 0.0
    
    def __post_init__(self):
        if len(self.returns) > 0:
            self.annual_return = (1 + self.returns.mean()) ** 252 - 1
            self.annual_volatility = self.returns.std() * np.sqrt(252)
            if self.annual_volatility > 0:
                self.sharpe_ratio = (self.annual_return - 0.03) / self.annual_volatility
            
            cum = (1 + self.returns).cumprod()
            running_max = cum.cummax()
            drawdown = (cum - running_max) / running_max
            self.max_drawdown = abs(drawdown.min())


class MultiStrategyCombiner:
    """
    多策略组合器
    
    将多个策略的资金分配组合在一起，实现风险分散和收益增强。
    """
    
    def __init__(
        self,
        total_capital: float = 1000000.0,
        risk_free_rate: float = 0.03,
        min_strategy_weight: float = 0.05,
        max_strategy_weight: float = 0.50,
        target_volatility: Optional[float] = None
    ):
        """
        初始化多策略组合器
        
        Args:
            total_capital: 总资金
            risk_free_rate: 无风险利率
            min_strategy_weight: 单策略最小权重
            max_strategy_weight: 单策略最大权重
            target_volatility: 目标波动率（可选）
        """
        self.total_capital = total_capital
        self.risk_free_rate = risk_free_rate
        self.min_strategy_weight = min_strategy_weight
        self.max_strategy_weight = max_strategy_weight
        self.target_volatility = target_volatility
        
        self._strategy_performances: Dict[str, StrategyPerformance] = {}
        self._correlation_matrix: Optional[pd.DataFrame] = None
    
    def add_strategy(
        self,
        strategy_id: str,
        strategy_name: str,
        returns: pd.Series
    ):
        """
        添加策略历史表现
        
        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            returns: 策略日收益率序列
        """
        perf = StrategyPerformance(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            returns=returns
        )
        self._strategy_performances[strategy_id] = perf
        self._correlation_matrix = None
    
    def add_strategies(self, strategies: Dict[str, pd.Series]):
        """
        批量添加策略
        
        Args:
            strategies: {策略ID: 收益率序列}
        """
        for sid, returns in strategies.items():
            self.add_strategy(sid, sid, returns)
    
    def _build_correlation_matrix(self) -> pd.DataFrame:
        """构建策略相关性矩阵"""
        if self._correlation_matrix is not None:
            return self._correlation_matrix
        
        returns_dict = {
            sid: perf.returns 
            for sid, perf in self._strategy_performances.items()
        }
        
        returns_df = pd.DataFrame(returns_dict)
        self._correlation_matrix = returns_df.corr()
        
        return self._correlation_matrix
    
    def _build_covariance_matrix(self) -> np.ndarray:
        """构建协方差矩阵"""
        returns_dict = {
            sid: perf.returns 
            for sid, perf in self._strategy_performances.items()
        }
        
        returns_df = pd.DataFrame(returns_dict)
        cov_matrix = returns_df.cov().values * 252
        
        return cov_matrix
    
    def allocate(
        self,
        method: AllocationMethod = AllocationMethod.EQUAL_WEIGHT,
        custom_weights: Optional[Dict[str, float]] = None,
        views: Optional[Dict[str, float]] = None
    ) -> MultiStrategyResult:
        """
        执行策略资金分配
        
        Args:
            method: 分配方法
            custom_weights: 自定义权重（仅当method=CUSTOM时使用）
            views: Black-Litterman观点 {策略ID: 预期超额收益}
            
        Returns:
            MultiStrategyResult: 分配结果
        """
        if len(self._strategy_performances) == 0:
            return MultiStrategyResult(
                success=False,
                error_message="没有添加任何策略"
            )
        
        strategy_ids = list(self._strategy_performances.keys())
        n = len(strategy_ids)
        
        if method == AllocationMethod.EQUAL_WEIGHT:
            weights = self._allocate_equal_weight(n)
        elif method == AllocationMethod.RISK_PARITY:
            weights = self._allocate_risk_parity()
        elif method == AllocationMethod.MEAN_VARIANCE:
            weights = self._allocate_mean_variance()
        elif method == AllocationMethod.MIN_CORRELATION:
            weights = self._allocate_min_correlation()
        elif method == AllocationMethod.KELLY:
            weights = self._allocate_kelly()
        elif method == AllocationMethod.BLACK_LITTERMAN:
            weights = self._allocate_black_litterman(views)
        elif method == AllocationMethod.CUSTOM:
            if custom_weights is None:
                return MultiStrategyResult(
                    success=False,
                    error_message="自定义权重方法需要提供custom_weights参数"
                )
            weights = self._allocate_custom(custom_weights, strategy_ids)
        else:
            weights = self._allocate_equal_weight(n)
        
        return self._build_result(weights, method.value)
    
    def _allocate_equal_weight(self, n: int) -> np.ndarray:
        """等权重分配"""
        return np.array([1.0 / n] * n)
    
    def _allocate_risk_parity(self) -> np.ndarray:
        """风险平价分配"""
        cov_matrix = self._build_covariance_matrix()
        n = cov_matrix.shape[0]
        
        def risk_parity_objective(weights):
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            marginal_risk = np.dot(cov_matrix, weights) / portfolio_vol
            risk_contributions = weights * marginal_risk
            target_risk = portfolio_vol / n
            return np.sum((risk_contributions - target_risk) ** 2)
        
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = [(self.min_strategy_weight, self.max_strategy_weight) for _ in range(n)]
        initial = np.array([1.0 / n] * n)
        
        result = minimize(
            risk_parity_objective,
            initial,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            return result.x
        else:
            logger.warning(f"风险平价优化失败: {result.message}，使用等权重")
            return self._allocate_equal_weight(n)
    
    def _allocate_mean_variance(self) -> np.ndarray:
        """均值方差分配"""
        cov_matrix = self._build_covariance_matrix()
        expected_returns = np.array([
            self._strategy_performances[sid].annual_return
            for sid in self._strategy_performances.keys()
        ])
        n = len(expected_returns)
        
        def objective(weights):
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            return -portfolio_return + 0.5 * portfolio_variance
        
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = [(self.min_strategy_weight, self.max_strategy_weight) for _ in range(n)]
        initial = np.array([1.0 / n] * n)
        
        result = minimize(
            objective,
            initial,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            return result.x
        else:
            logger.warning(f"均值方差优化失败: {result.message}，使用等权重")
            return self._allocate_equal_weight(n)
    
    def _allocate_min_correlation(self) -> np.ndarray:
        """最小相关性分配"""
        corr_matrix = self._build_correlation_matrix().values
        n = corr_matrix.shape[0]
        
        def objective(weights):
            avg_correlation = 0
            count = 0
            for i in range(n):
                for j in range(i + 1, n):
                    avg_correlation += weights[i] * weights[j] * corr_matrix[i, j]
                    count += 1
            return avg_correlation / count if count > 0 else 0
        
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = [(self.min_strategy_weight, self.max_strategy_weight) for _ in range(n)]
        initial = np.array([1.0 / n] * n)
        
        result = minimize(
            objective,
            initial,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            return result.x
        else:
            logger.warning(f"最小相关性优化失败: {result.message}，使用等权重")
            return self._allocate_equal_weight(n)
    
    def _allocate_kelly(self) -> np.ndarray:
        """凯利准则分配"""
        expected_returns = np.array([
            self._strategy_performances[sid].annual_return
            for sid in self._strategy_performances.keys()
        ])
        cov_matrix = self._build_covariance_matrix()
        
        try:
            inv_cov = np.linalg.inv(cov_matrix)
            excess_returns = expected_returns - self.risk_free_rate
            kelly_weights = np.dot(inv_cov, excess_returns)
            kelly_weights = kelly_weights / np.sum(kelly_weights)
            
            kelly_weights = np.clip(
                kelly_weights,
                self.min_strategy_weight,
                self.max_strategy_weight
            )
            kelly_weights = kelly_weights / np.sum(kelly_weights)
            
            return kelly_weights
        except np.linalg.LinAlgError:
            logger.warning("协方差矩阵不可逆，使用等权重")
            return self._allocate_equal_weight(len(expected_returns))
    
    def _allocate_black_litterman(
        self,
        views: Optional[Dict[str, float]] = None
    ) -> np.ndarray:
        """Black-Litterman分配"""
        strategy_ids = list(self._strategy_performances.keys())
        n = len(strategy_ids)
        cov_matrix = self._build_covariance_matrix()
        
        market_weights = np.array([1.0 / n] * n)
        expected_returns = np.array([
            self._strategy_performances[sid].annual_return
            for sid in strategy_ids
        ])
        
        pi = np.dot(cov_matrix, market_weights) * 2.5
        
        if views is None or len(views) == 0:
            bl_returns = pi
        else:
            P = np.zeros((len(views), n))
            Q = np.zeros(len(views))
            omega = np.zeros((len(views), len(views)))
            
            for i, (sid, view_return) in enumerate(views.items()):
                if sid in strategy_ids:
                    idx = strategy_ids.index(sid)
                    P[i, idx] = 1
                    Q[i] = view_return
                    omega[i, i] = 0.01
            
            tau = 0.05
            tau_cov = tau * cov_matrix
            
            M1 = np.linalg.inv(tau_cov)
            M2 = np.dot(P.T, np.dot(np.linalg.inv(omega), P))
            M3 = np.dot(M1, pi) + np.dot(P.T, np.dot(np.linalg.inv(omega), Q))
            
            bl_returns = np.dot(np.linalg.inv(M1 + M2), M3)
        
        def objective(weights):
            portfolio_return = np.dot(weights, bl_returns)
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            return -portfolio_return + 0.5 * portfolio_variance
        
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = [(self.min_strategy_weight, self.max_strategy_weight) for _ in range(n)]
        initial = np.array([1.0 / n] * n)
        
        result = minimize(
            objective,
            initial,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            return result.x
        else:
            logger.warning(f"Black-Litterman优化失败: {result.message}，使用等权重")
            return self._allocate_equal_weight(n)
    
    def _allocate_custom(
        self,
        custom_weights: Dict[str, float],
        strategy_ids: List[str]
    ) -> np.ndarray:
        """自定义权重分配"""
        weights = np.array([
            custom_weights.get(sid, 0) for sid in strategy_ids
        ])
        
        total = np.sum(weights)
        if total > 0:
            weights = weights / total
        else:
            weights = np.array([1.0 / len(strategy_ids)] * len(strategy_ids))
        
        return weights
    
    def _build_result(
        self,
        weights: np.ndarray,
        method: str
    ) -> MultiStrategyResult:
        """构建分配结果"""
        strategy_ids = list(self._strategy_performances.keys())
        cov_matrix = self._build_covariance_matrix()
        expected_returns = np.array([
            self._strategy_performances[sid].annual_return
            for sid in strategy_ids
        ])
        
        portfolio_return = np.dot(weights, expected_returns)
        portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
        portfolio_vol = np.sqrt(portfolio_variance)
        
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
        
        volatilities = np.sqrt(np.diag(cov_matrix))
        diversification_ratio = np.dot(weights, volatilities) / portfolio_vol if portfolio_vol > 0 else 1
        
        allocations = []
        for i, sid in enumerate(strategy_ids):
            perf = self._strategy_performances[sid]
            allocation = StrategyAllocation(
                strategy_id=sid,
                strategy_name=perf.strategy_name,
                weight=weights[i],
                capital=weights[i] * self.total_capital,
                expected_return=expected_returns[i],
                expected_risk=volatilities[i],
                contribution_to_risk=weights[i] * volatilities[i] / portfolio_vol if portfolio_vol > 0 else 0
            )
            allocations.append(allocation)
        
        return MultiStrategyResult(
            success=True,
            allocations=allocations,
            total_capital=self.total_capital,
            expected_return=portfolio_return,
            expected_risk=portfolio_vol,
            sharpe_ratio=sharpe,
            diversification_ratio=diversification_ratio,
            method=method,
            correlation_matrix=self._build_correlation_matrix()
        )
    
    def analyze_diversification(self) -> Dict[str, Any]:
        """
        分析组合分散化程度
        
        Returns:
            Dict: 分散化分析结果
        """
        if len(self._strategy_performances) < 2:
            return {'error': '需要至少2个策略'}
        
        corr_matrix = self._build_correlation_matrix()
        
        upper_triangle = corr_matrix.values[np.triu_indices(len(corr_matrix), k=1)]
        avg_correlation = np.mean(upper_triangle)
        max_correlation = np.max(upper_triangle)
        min_correlation = np.min(upper_triangle)
        
        high_corr_pairs = []
        strategy_ids = list(self._strategy_performances.keys())
        for i in range(len(strategy_ids)):
            for j in range(i + 1, len(strategy_ids)):
                if corr_matrix.iloc[i, j] > 0.7:
                    high_corr_pairs.append({
                        'strategy_1': strategy_ids[i],
                        'strategy_2': strategy_ids[j],
                        'correlation': corr_matrix.iloc[i, j]
                    })
        
        return {
            'average_correlation': avg_correlation,
            'max_correlation': max_correlation,
            'min_correlation': min_correlation,
            'high_correlation_pairs': high_corr_pairs,
            'diversification_score': 1 - avg_correlation,
            'correlation_matrix': corr_matrix.to_dict()
        }
    
    def rebalance(
        self,
        current_allocations: Dict[str, float],
        target_method: AllocationMethod = AllocationMethod.RISK_PARITY,
        rebalance_threshold: float = 0.05
    ) -> Dict[str, Any]:
        """
        再平衡分析
        
        Args:
            current_allocations: 当前策略权重
            target_method: 目标分配方法
            rebalance_threshold: 再平衡阈值
            
        Returns:
            Dict: 再平衡建议
        """
        target_result = self.allocate(method=target_method)
        if not target_result.success:
            return {'error': target_result.error_message}
        
        target_weights = target_result.get_weights_dict()
        
        rebalance_trades = []
        for sid in target_weights:
            current = current_allocations.get(sid, 0)
            target = target_weights[sid]
            diff = target - current
            
            if abs(diff) > rebalance_threshold:
                rebalance_trades.append({
                    'strategy_id': sid,
                    'current_weight': current,
                    'target_weight': target,
                    'adjustment': diff,
                    'capital_adjustment': diff * self.total_capital,
                    'action': 'increase' if diff > 0 else 'decrease'
                })
        
        return {
            'need_rebalance': len(rebalance_trades) > 0,
            'rebalance_trades': rebalance_trades,
            'target_weights': target_weights,
            'current_weights': current_allocations
        }


def create_strategy_combiner(
    strategies: Dict[str, pd.Series],
    total_capital: float = 1000000.0,
    **kwargs
) -> MultiStrategyCombiner:
    """
    创建多策略组合器的便捷函数
    
    Args:
        strategies: {策略ID: 收益率序列}
        total_capital: 总资金
        **kwargs: 其他参数
        
    Returns:
        MultiStrategyCombiner: 组合器实例
    """
    combiner = MultiStrategyCombiner(total_capital=total_capital, **kwargs)
    combiner.add_strategies(strategies)
    return combiner
