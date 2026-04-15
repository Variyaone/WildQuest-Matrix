"""
风险指标计算模块

计算各类风险指标，包括VaR、CVaR、最大回撤、波动率、Beta等。
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from scipy import stats


@dataclass
class RiskMetricsResult:
    """风险指标计算结果"""
    var_95: float = 0.0
    var_99: float = 0.0
    cvar_95: float = 0.0
    cvar_99: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    volatility: float = 0.0
    annualized_volatility: float = 0.0
    beta: float = 0.0
    correlation: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    downside_deviation: float = 0.0
    tracking_error: float = 0.0
    information_ratio: float = 0.0
    calculated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "var_95": self.var_95,
            "var_99": self.var_99,
            "cvar_95": self.cvar_95,
            "cvar_99": self.cvar_99,
            "max_drawdown": self.max_drawdown,
            "current_drawdown": self.current_drawdown,
            "volatility": self.volatility,
            "annualized_volatility": self.annualized_volatility,
            "beta": self.beta,
            "correlation": self.correlation,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "downside_deviation": self.downside_deviation,
            "tracking_error": self.tracking_error,
            "information_ratio": self.information_ratio,
            "calculated_at": self.calculated_at.isoformat()
        }


class RiskMetricsCalculator:
    """
    风险指标计算器
    
    计算投资组合的各类风险指标。
    """
    
    TRADING_DAYS_PER_YEAR = 252
    RISK_FREE_RATE = 0.03
    
    def __init__(
        self,
        trading_days_per_year: int = 252,
        risk_free_rate: float = 0.03
    ):
        self.trading_days_per_year = trading_days_per_year
        self.risk_free_rate = risk_free_rate
    
    def calculate_var(
        self,
        returns: np.ndarray,
        confidence_level: float = 0.95
    ) -> float:
        """
        计算VaR（风险价值）
        
        Args:
            returns: 收益率序列
            confidence_level: 置信水平（0.95或0.99）
            
        Returns:
            VaR值（正数表示潜在损失）
        """
        if len(returns) == 0:
            return 0.0
        
        returns = np.asarray(returns)
        var = np.percentile(returns, (1 - confidence_level) * 100)
        return abs(var)
    
    def calculate_cvar(
        self,
        returns: np.ndarray,
        confidence_level: float = 0.95
    ) -> float:
        """
        计算CVaR（条件风险价值/期望损失）
        
        Args:
            returns: 收益率序列
            confidence_level: 置信水平
            
        Returns:
            CVaR值（正数表示潜在损失）
        """
        if len(returns) == 0:
            return 0.0
        
        returns = np.asarray(returns)
        var = np.percentile(returns, (1 - confidence_level) * 100)
        cvar = returns[returns <= var].mean() if len(returns[returns <= var]) > 0 else var
        return abs(cvar)
    
    def calculate_max_drawdown(
        self,
        nav_series: np.ndarray
    ) -> Tuple[float, float, int, int]:
        """
        计算最大回撤
        
        Args:
            nav_series: 净值序列
            
        Returns:
            (最大回撤, 当前回撤, 最大回撤开始位置, 最大回撤结束位置)
        """
        if len(nav_series) == 0:
            return 0.0, 0.0, 0, 0
        
        nav_series = np.asarray(nav_series)
        peak = nav_series[0]
        max_dd = 0.0
        max_dd_start = 0
        max_dd_end = 0
        current_peak_idx = 0
        
        for i, nav in enumerate(nav_series):
            if nav > peak:
                peak = nav
                current_peak_idx = i
            
            dd = (peak - nav) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
                max_dd_start = current_peak_idx
                max_dd_end = i
        
        current_dd = (peak - nav_series[-1]) / peak if peak > 0 else 0
        
        return max_dd, current_dd, max_dd_start, max_dd_end
    
    def calculate_volatility(
        self,
        returns: np.ndarray,
        annualize: bool = True
    ) -> float:
        """
        计算波动率
        
        Args:
            returns: 收益率序列
            annualize: 是否年化
            
        Returns:
            波动率
        """
        if len(returns) < 2:
            return 0.0
        
        returns = np.asarray(returns)
        vol = np.std(returns, ddof=1)
        
        if annualize:
            vol *= np.sqrt(self.trading_days_per_year)
        
        return vol
    
    def calculate_beta(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> float:
        """
        计算Beta
        
        Args:
            portfolio_returns: 组合收益率序列
            benchmark_returns: 基准收益率序列
            
        Returns:
            Beta值
        """
        if len(portfolio_returns) < 2 or len(benchmark_returns) < 2:
            return 0.0
        
        portfolio_returns = np.asarray(portfolio_returns)
        benchmark_returns = np.asarray(benchmark_returns)
        
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        portfolio_returns = portfolio_returns[-min_len:]
        benchmark_returns = benchmark_returns[-min_len:]
        
        covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns, ddof=1)
        
        if benchmark_variance == 0:
            return 0.0
        
        return covariance / benchmark_variance
    
    def calculate_correlation(
        self,
        returns_a: np.ndarray,
        returns_b: np.ndarray
    ) -> float:
        """
        计算相关系数
        
        Args:
            returns_a: 序列A收益率
            returns_b: 序列B收益率
            
        Returns:
            相关系数
        """
        if len(returns_a) < 2 or len(returns_b) < 2:
            return 0.0
        
        returns_a = np.asarray(returns_a)
        returns_b = np.asarray(returns_b)
        
        min_len = min(len(returns_a), len(returns_b))
        returns_a = returns_a[-min_len:]
        returns_b = returns_b[-min_len:]
        
        correlation = np.corrcoef(returns_a, returns_b)[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def calculate_sharpe_ratio(
        self,
        returns: np.ndarray,
        annualize: bool = True
    ) -> float:
        """
        计算夏普比率
        
        Args:
            returns: 收益率序列
            annualize: 是否年化
            
        Returns:
            夏普比率
        """
        if len(returns) < 2:
            return 0.0
        
        returns = np.asarray(returns)
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        
        if std_return == 0:
            return 0.0
        
        if annualize:
            mean_return *= self.trading_days_per_year
            std_return *= np.sqrt(self.trading_days_per_year)
        
        excess_return = mean_return - self.risk_free_rate / self.trading_days_per_year * (self.trading_days_per_year if annualize else 1)
        
        return excess_return / std_return
    
    def calculate_sortino_ratio(
        self,
        returns: np.ndarray,
        annualize: bool = True
    ) -> float:
        """
        计算索提诺比率
        
        Args:
            returns: 收益率序列
            annualize: 是否年化
            
        Returns:
            索提诺比率
        """
        if len(returns) < 2:
            return 0.0
        
        returns = np.asarray(returns)
        mean_return = np.mean(returns)
        
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return float('inf')
        
        if len(downside_returns) < 2:
            return 0.0
        
        downside_std = np.std(downside_returns, ddof=1)
        
        if downside_std == 0:
            return 0.0
        
        if annualize:
            mean_return *= self.trading_days_per_year
            downside_std *= np.sqrt(self.trading_days_per_year)
        
        excess_return = mean_return - self.risk_free_rate / self.trading_days_per_year * (self.trading_days_per_year if annualize else 1)
        
        return excess_return / downside_std
    
    def calculate_calmar_ratio(
        self,
        returns: np.ndarray,
        nav_series: np.ndarray
    ) -> float:
        """
        计算卡玛比率
        
        Args:
            returns: 收益率序列
            nav_series: 净值序列
            
        Returns:
            卡玛比率
        """
        if len(returns) < 2 or len(nav_series) < 2:
            return 0.0
        
        annualized_return = np.mean(returns) * self.trading_days_per_year
        max_dd, _, _, _ = self.calculate_max_drawdown(nav_series)
        
        if max_dd == 0:
            return float('inf')
        
        return annualized_return / max_dd
    
    def calculate_downside_deviation(
        self,
        returns: np.ndarray,
        target_return: float = 0.0,
        annualize: bool = True
    ) -> float:
        """
        计算下行标准差
        
        Args:
            returns: 收益率序列
            target_return: 目标收益率
            annualize: 是否年化
            
        Returns:
            下行标准差
        """
        if len(returns) < 2:
            return 0.0
        
        returns = np.asarray(returns)
        downside_returns = returns - target_return
        downside_returns = downside_returns[downside_returns < 0]
        
        if len(downside_returns) == 0:
            return 0.0
        
        downside_std = np.sqrt(np.mean(downside_returns ** 2))
        
        if annualize:
            downside_std *= np.sqrt(self.trading_days_per_year)
        
        return downside_std
    
    def calculate_tracking_error(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        annualize: bool = True
    ) -> float:
        """
        计算跟踪误差
        
        Args:
            portfolio_returns: 组合收益率序列
            benchmark_returns: 基准收益率序列
            annualize: 是否年化
            
        Returns:
            跟踪误差
        """
        if len(portfolio_returns) < 2 or len(benchmark_returns) < 2:
            return 0.0
        
        portfolio_returns = np.asarray(portfolio_returns)
        benchmark_returns = np.asarray(benchmark_returns)
        
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        if min_len < 2:
            return 0.0
        
        portfolio_returns = portfolio_returns[-min_len:]
        benchmark_returns = benchmark_returns[-min_len:]
        
        active_returns = portfolio_returns - benchmark_returns
        tracking_error = np.std(active_returns, ddof=1)
        
        if annualize:
            tracking_error *= np.sqrt(self.trading_days_per_year)
        
        return tracking_error
    
    def calculate_information_ratio(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> float:
        """
        计算信息比率
        
        Args:
            portfolio_returns: 组合收益率序列
            benchmark_returns: 基准收益率序列
            
        Returns:
            信息比率
        """
        if len(portfolio_returns) < 2 or len(benchmark_returns) < 2:
            return 0.0
        
        portfolio_returns = np.asarray(portfolio_returns)
        benchmark_returns = np.asarray(benchmark_returns)
        
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        if min_len < 2:
            return 0.0
        
        portfolio_returns = portfolio_returns[-min_len:]
        benchmark_returns = benchmark_returns[-min_len:]
        
        active_returns = portfolio_returns - benchmark_returns
        mean_active_return = np.mean(active_returns)
        tracking_error = np.std(active_returns, ddof=1)
        
        if tracking_error == 0:
            return 0.0
        
        return mean_active_return * self.trading_days_per_year / (tracking_error * np.sqrt(self.trading_days_per_year))
    
    def calculate_all_metrics(
        self,
        returns: np.ndarray,
        nav_series: np.ndarray,
        benchmark_returns: Optional[np.ndarray] = None
    ) -> RiskMetricsResult:
        """
        计算所有风险指标
        
        Args:
            returns: 收益率序列
            nav_series: 净值序列
            benchmark_returns: 基准收益率序列（可选）
            
        Returns:
            RiskMetricsResult: 风险指标结果
        """
        returns = np.asarray(returns) if len(returns) > 0 else np.array([])
        nav_series = np.asarray(nav_series) if len(nav_series) > 0 else np.array([])
        
        max_dd, current_dd, _, _ = self.calculate_max_drawdown(nav_series)
        
        result = RiskMetricsResult(
            var_95=self.calculate_var(returns, 0.95),
            var_99=self.calculate_var(returns, 0.99),
            cvar_95=self.calculate_cvar(returns, 0.95),
            cvar_99=self.calculate_cvar(returns, 0.99),
            max_drawdown=max_dd,
            current_drawdown=current_dd,
            volatility=self.calculate_volatility(returns, annualize=False),
            annualized_volatility=self.calculate_volatility(returns, annualize=True),
            sharpe_ratio=self.calculate_sharpe_ratio(returns),
            sortino_ratio=self.calculate_sortino_ratio(returns),
            calmar_ratio=self.calculate_calmar_ratio(returns, nav_series),
            downside_deviation=self.calculate_downside_deviation(returns),
            calculated_at=datetime.now()
        )
        
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            benchmark_returns = np.asarray(benchmark_returns)
            result.beta = self.calculate_beta(returns, benchmark_returns)
            result.correlation = self.calculate_correlation(returns, benchmark_returns)
            result.tracking_error = self.calculate_tracking_error(returns, benchmark_returns)
            result.information_ratio = self.calculate_information_ratio(returns, benchmark_returns)
        
        return result


def calculate_portfolio_concentration(
    weights: Dict[str, float],
    industry_mapping: Dict[str, str]
) -> Dict[str, Any]:
    """
    计算组合集中度
    
    Args:
        weights: 股票权重字典 {stock_code: weight}
        industry_mapping: 行业映射 {stock_code: industry}
        
    Returns:
        集中度指标字典
    """
    if not weights:
        return {
            "max_single_weight": 0.0,
            "industry_concentration": {},
            "max_industry_weight": 0.0,
            "effective_stocks": 0.0
        }
    
    max_single_weight = max(weights.values()) if weights else 0.0
    
    industry_weights = {}
    for stock, weight in weights.items():
        industry = industry_mapping.get(stock, "Unknown")
        industry_weights[industry] = industry_weights.get(industry, 0) + weight
    
    max_industry_weight = max(industry_weights.values()) if industry_weights else 0.0
    
    effective_stocks = 1.0 / sum(w ** 2 for w in weights.values()) if weights else 0.0
    
    return {
        "max_single_weight": max_single_weight,
        "industry_concentration": industry_weights,
        "max_industry_weight": max_industry_weight,
        "effective_stocks": effective_stocks
    }


def calculate_position_usage(
    positions: Dict[str, float],
    total_capital: float
) -> Dict[str, Any]:
    """
    计算仓位使用情况
    
    Args:
        positions: 持仓市值字典 {stock_code: market_value}
        total_capital: 总资金
        
    Returns:
        仓位使用情况字典
    """
    total_position = sum(positions.values()) if positions else 0.0
    position_ratio = total_position / total_capital if total_capital > 0 else 0.0
    cash_ratio = 1.0 - position_ratio
    
    return {
        "total_position": total_position,
        "total_capital": total_capital,
        "position_ratio": position_ratio,
        "cash_ratio": cash_ratio,
        "position_count": len(positions)
    }
