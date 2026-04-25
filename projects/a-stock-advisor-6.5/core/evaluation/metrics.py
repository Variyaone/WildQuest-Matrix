"""
绩效指标计算库

提供标准化的绩效指标计算函数。
"""

from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class MetricResult:
    """指标计算结果"""
    name: str
    value: float
    description: str
    category: str
    unit: str = ""
    is_better_higher: bool = True


class PerformanceMetricsCalculator:
    """
    绩效指标计算器
    
    提供标准化的绩效指标计算。
    """
    
    TRADING_DAYS_PER_YEAR = 252
    
    @staticmethod
    def total_return(returns: pd.Series) -> float:
        """
        计算累计收益率
        
        Args:
            returns: 收益率序列
            
        Returns:
            float: 累计收益率
        """
        if len(returns) == 0:
            return 0.0
        return (1 + returns).prod() - 1
    
    @staticmethod
    def annual_return(returns: pd.Series, trading_days: int = 252) -> float:
        """
        计算年化收益率
        
        Args:
            returns: 收益率序列
            trading_days: 年交易日数
            
        Returns:
            float: 年化收益率
        """
        total_ret = PerformanceMetricsCalculator.total_return(returns)
        n_years = len(returns) / trading_days
        if n_years <= 0:
            return 0.0
        return (1 + total_ret) ** (1 / n_years) - 1
    
    @staticmethod
    def volatility(returns: pd.Series, trading_days: int = 252) -> float:
        """
        计算年化波动率
        
        Args:
            returns: 收益率序列
            trading_days: 年交易日数
            
        Returns:
            float: 年化波动率
        """
        if len(returns) == 0:
            return 0.0
        return returns.std() * np.sqrt(trading_days)
    
    @staticmethod
    def downside_volatility(
        returns: pd.Series,
        target_return: float = 0.0,
        trading_days: int = 252
    ) -> float:
        """
        计算下行波动率
        
        Args:
            returns: 收益率序列
            target_return: 目标收益率
            trading_days: 年交易日数
            
        Returns:
            float: 下行波动率
        """
        downside = returns[returns < target_return]
        if len(downside) == 0:
            return 0.0
        return downside.std() * np.sqrt(trading_days)
    
    @staticmethod
    def max_drawdown(returns: pd.Series) -> float:
        """
        计算最大回撤
        
        Args:
            returns: 收益率序列
            
        Returns:
            float: 最大回撤
        """
        if len(returns) == 0:
            return 0.0
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    @staticmethod
    def drawdown_duration(returns: pd.Series) -> int:
        """
        计算最大回撤持续时间
        
        Args:
            returns: 收益率序列
            
        Returns:
            int: 最大回撤持续天数
        """
        if len(returns) == 0:
            return 0
        
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        
        is_drawdown = drawdown < 0
        drawdown_groups = (is_drawdown != is_drawdown.shift()).cumsum()
        
        max_duration = 0
        for _, group in drawdown[is_drawdown].groupby(drawdown_groups[is_drawdown]):
            duration = len(group)
            if duration > max_duration:
                max_duration = duration
        
        return max_duration
    
    @staticmethod
    def sharpe_ratio(
        returns: pd.Series,
        risk_free_rate: float = 0.03,
        trading_days: int = 252
    ) -> float:
        """
        计算夏普比率
        
        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率
            trading_days: 年交易日数
            
        Returns:
            float: 夏普比率
        """
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / trading_days
        return excess_returns.mean() / excess_returns.std() * np.sqrt(trading_days)
    
    @staticmethod
    def sortino_ratio(
        returns: pd.Series,
        risk_free_rate: float = 0.03,
        trading_days: int = 252
    ) -> float:
        """
        计算索提诺比率
        
        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率
            trading_days: 年交易日数
            
        Returns:
            float: 索提诺比率
        """
        if len(returns) == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / trading_days
        downside_vol = PerformanceMetricsCalculator.downside_volatility(
            returns, risk_free_rate / trading_days, trading_days
        )
        
        if downside_vol == 0:
            return 0.0
        
        return excess_returns.mean() * trading_days / downside_vol
    
    @staticmethod
    def calmar_ratio(
        returns: pd.Series,
        trading_days: int = 252
    ) -> float:
        """
        计算卡玛比率
        
        Args:
            returns: 收益率序列
            trading_days: 年交易日数
            
        Returns:
            float: 卡玛比率
        """
        annual_ret = PerformanceMetricsCalculator.annual_return(returns, trading_days)
        max_dd = PerformanceMetricsCalculator.max_drawdown(returns)
        
        if max_dd == 0:
            return 0.0
        
        return annual_ret / abs(max_dd)
    
    @staticmethod
    def information_ratio(
        returns: pd.Series,
        benchmark_returns: pd.Series,
        trading_days: int = 252
    ) -> float:
        """
        计算信息比率
        
        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列
            trading_days: 年交易日数
            
        Returns:
            float: 信息比率
        """
        aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
        
        if len(aligned_returns) == 0:
            return 0.0
        
        excess = aligned_returns - aligned_benchmark
        tracking_error = excess.std() * np.sqrt(trading_days)
        
        if tracking_error == 0:
            return 0.0
        
        return excess.mean() * trading_days / tracking_error
    
    @staticmethod
    def tracking_error(
        returns: pd.Series,
        benchmark_returns: pd.Series,
        trading_days: int = 252
    ) -> float:
        """
        计算跟踪误差
        
        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列
            trading_days: 年交易日数
            
        Returns:
            float: 跟踪误差
        """
        aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
        
        if len(aligned_returns) == 0:
            return 0.0
        
        excess = aligned_returns - aligned_benchmark
        return excess.std() * np.sqrt(trading_days)
    
    @staticmethod
    def beta(
        returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> float:
        """
        计算Beta
        
        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列
            
        Returns:
            float: Beta
        """
        aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
        
        if len(aligned_returns) == 0:
            return 0.0
        
        covariance = aligned_returns.cov(aligned_benchmark)
        variance = aligned_benchmark.var()
        
        if variance == 0:
            return 0.0
        
        return covariance / variance
    
    @staticmethod
    def alpha(
        returns: pd.Series,
        benchmark_returns: pd.Series,
        risk_free_rate: float = 0.03,
        trading_days: int = 252
    ) -> float:
        """
        计算Alpha
        
        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列
            risk_free_rate: 无风险利率
            trading_days: 年交易日数
            
        Returns:
            float: Alpha
        """
        aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
        
        if len(aligned_returns) == 0:
            return 0.0
        
        beta_val = PerformanceMetricsCalculator.beta(aligned_returns, aligned_benchmark)
        
        excess_return = aligned_returns.mean() - risk_free_rate / trading_days
        benchmark_excess = aligned_benchmark.mean() - risk_free_rate / trading_days
        
        return (excess_return - beta_val * benchmark_excess) * trading_days
    
    @staticmethod
    def var(returns: pd.Series, confidence: float = 0.95) -> float:
        """
        计算VaR
        
        Args:
            returns: 收益率序列
            confidence: 置信水平
            
        Returns:
            float: VaR
        """
        if len(returns) == 0:
            return 0.0
        return returns.quantile(1 - confidence)
    
    @staticmethod
    def cvar(returns: pd.Series, confidence: float = 0.95) -> float:
        """
        计算CVaR
        
        Args:
            returns: 收益率序列
            confidence: 置信水平
            
        Returns:
            float: CVaR
        """
        if len(returns) == 0:
            return 0.0
        
        var_val = PerformanceMetricsCalculator.var(returns, confidence)
        return returns[returns <= var_val].mean()
    
    @staticmethod
    def win_rate(trades: List[Dict[str, Any]]) -> float:
        """
        计算胜率
        
        Args:
            trades: 交易列表
            
        Returns:
            float: 胜率
        """
        if not trades:
            return 0.0
        
        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        total = len([t for t in trades if t.get('pnl', 0) != 0])
        
        if total == 0:
            return 0.0
        
        return wins / total
    
    @staticmethod
    def profit_loss_ratio(trades: List[Dict[str, Any]]) -> float:
        """
        计算盈亏比
        
        Args:
            trades: 交易列表
            
        Returns:
            float: 盈亏比
        """
        profits = [t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0]
        losses = [abs(t.get('pnl', 0)) for t in trades if t.get('pnl', 0) < 0]
        
        if not profits or not losses:
            return 0.0
        
        return np.mean(profits) / np.mean(losses)
    
    @staticmethod
    def turnover_rate(
        positions: pd.DataFrame,
        trading_days: int = 252
    ) -> float:
        """
        计算换手率
        
        Args:
            positions: 持仓数据
            trading_days: 年交易日数
            
        Returns:
            float: 年化换手率
        """
        if len(positions) < 2:
            return 0.0
        
        turnover_sum = 0.0
        for i in range(1, len(positions)):
            buys = positions.iloc[i].get('buy_value', 0)
            sells = positions.iloc[i].get('sell_value', 0)
            total_value = positions.iloc[i].get('total_value', 1)
            
            turnover_sum += (buys + sells) / total_value if total_value > 0 else 0
        
        avg_turnover = turnover_sum / (len(positions) - 1)
        return avg_turnover * trading_days
    
    @staticmethod
    def ic_mean(factor_values: pd.Series, forward_returns: pd.Series) -> float:
        """
        计算IC均值
        
        Args:
            factor_values: 因子值序列
            forward_returns: 预测期收益序列
            
        Returns:
            float: IC均值
        """
        if len(factor_values) == 0 or len(forward_returns) == 0:
            return 0.0
        
        aligned_factor, aligned_returns = factor_values.align(forward_returns, join='inner')
        
        if len(aligned_factor) == 0:
            return 0.0
        
        return aligned_factor.corr(aligned_returns)
    
    @staticmethod
    def ic_std(
        factor_values: pd.DataFrame,
        forward_returns: pd.DataFrame
    ) -> float:
        """
        计算IC标准差
        
        Args:
            factor_values: 因子值DataFrame（按日期）
            forward_returns: 预测期收益DataFrame（按日期）
            
        Returns:
            float: IC标准差
        """
        if len(factor_values) == 0 or len(forward_returns) == 0:
            return 0.0
        
        ics = []
        for date in factor_values.index:
            if date in forward_returns.index:
                ic = factor_values.loc[date].corr(forward_returns.loc[date])
                if pd.notna(ic):
                    ics.append(ic)
        
        if len(ics) == 0:
            return 0.0
        
        return np.std(ics)
    
    @staticmethod
    def ir(
        factor_values: pd.DataFrame,
        forward_returns: pd.DataFrame
    ) -> float:
        """
        计算信息比率（IR）
        
        Args:
            factor_values: 因子值DataFrame
            forward_returns: 预测期收益DataFrame
            
        Returns:
            float: IR
        """
        if len(factor_values) == 0 or len(forward_returns) == 0:
            return 0.0
        
        ics = []
        for date in factor_values.index:
            if date in forward_returns.index:
                ic = factor_values.loc[date].corr(forward_returns.loc[date])
                if pd.notna(ic):
                    ics.append(ic)
        
        if len(ics) == 0:
            return 0.0
        
        ic_mean = np.mean(ics)
        ic_std = np.std(ics)
        
        if ic_std == 0:
            return 0.0
        
        return ic_mean / ic_std
    
    @staticmethod
    def monotonicity(group_returns: pd.Series) -> float:
        """
        计算单调性
        
        Args:
            group_returns: 分组收益序列
            
        Returns:
            float: 单调性得分
        """
        if len(group_returns) < 2:
            return 0.0
        
        diffs = np.diff(group_returns.values)
        positive = np.sum(diffs > 0)
        negative = np.sum(diffs < 0)
        total = len(diffs)
        
        if total == 0:
            return 0.0
        
        return max(positive, negative) / total
    
    @staticmethod
    def factor_coverage(factor_values: pd.Series) -> float:
        """
        计算因子覆盖率
        
        Args:
            factor_values: 因子值序列
            
        Returns:
            float: 覆盖率
        """
        if len(factor_values) == 0:
            return 0.0
        
        valid_count = factor_values.notna().sum()
        return valid_count / len(factor_values)
    
    @classmethod
    def calculate_all_metrics(
        cls,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        trades: Optional[List[Dict]] = None,
        positions: Optional[pd.DataFrame] = None,
        risk_free_rate: float = 0.03,
        trading_days: int = 252
    ) -> Dict[str, MetricResult]:
        """
        计算所有绩效指标
        
        Args:
            returns: 收益率序列
            benchmark_returns: 基准收益率
            trades: 交易列表
            positions: 持仓数据
            risk_free_rate: 无风险利率
            trading_days: 年交易日数
            
        Returns:
            Dict[str, MetricResult]: 指标结果字典
        """
        metrics = {}
        
        metrics['total_return'] = MetricResult(
            name='累计收益率',
            value=cls.total_return(returns),
            description='策略累计收益率',
            category='收益',
            unit='%',
            is_better_higher=True
        )
        
        metrics['annual_return'] = MetricResult(
            name='年化收益率',
            value=cls.annual_return(returns, trading_days),
            description='策略年化收益率',
            category='收益',
            unit='%',
            is_better_higher=True
        )
        
        metrics['volatility'] = MetricResult(
            name='年化波动率',
            value=cls.volatility(returns, trading_days),
            description='策略年化波动率',
            category='风险',
            unit='%',
            is_better_higher=False
        )
        
        metrics['max_drawdown'] = MetricResult(
            name='最大回撤',
            value=cls.max_drawdown(returns),
            description='策略最大回撤',
            category='风险',
            unit='%',
            is_better_higher=False
        )
        
        metrics['sharpe_ratio'] = MetricResult(
            name='夏普比率',
            value=cls.sharpe_ratio(returns, risk_free_rate, trading_days),
            description='风险调整后收益',
            category='风险调整',
            unit='',
            is_better_higher=True
        )
        
        metrics['sortino_ratio'] = MetricResult(
            name='索提诺比率',
            value=cls.sortino_ratio(returns, risk_free_rate, trading_days),
            description='下行风险调整后收益',
            category='风险调整',
            unit='',
            is_better_higher=True
        )
        
        metrics['calmar_ratio'] = MetricResult(
            name='卡玛比率',
            value=cls.calmar_ratio(returns, trading_days),
            description='回撤风险调整后收益',
            category='风险调整',
            unit='',
            is_better_higher=True
        )
        
        metrics['var_95'] = MetricResult(
            name='VaR(95%)',
            value=cls.var(returns, 0.95),
            description='95%置信水平下的在险价值',
            category='风险',
            unit='%',
            is_better_higher=False
        )
        
        if benchmark_returns is not None:
            metrics['excess_return'] = MetricResult(
                name='超额收益',
                value=cls.annual_return(returns, trading_days) - cls.annual_return(benchmark_returns, trading_days),
                description='相对基准的超额收益',
                category='收益',
                unit='%',
                is_better_higher=True
            )
            
            metrics['information_ratio'] = MetricResult(
                name='信息比率',
                value=cls.information_ratio(returns, benchmark_returns, trading_days),
                description='超额收益的稳定性',
                category='风险调整',
                unit='',
                is_better_higher=True
            )
            
            metrics['beta'] = MetricResult(
                name='Beta',
                value=cls.beta(returns, benchmark_returns),
                description='相对基准的系统性风险',
                category='风险',
                unit='',
                is_better_higher=False
            )
            
            metrics['alpha'] = MetricResult(
                name='Alpha',
                value=cls.alpha(returns, benchmark_returns, risk_free_rate, trading_days),
                description='超额收益能力',
                category='收益',
                unit='%',
                is_better_higher=True
            )
        
        if trades:
            metrics['win_rate'] = MetricResult(
                name='胜率',
                value=cls.win_rate(trades),
                description='盈利交易占比',
                category='交易',
                unit='%',
                is_better_higher=True
            )
            
            metrics['profit_loss_ratio'] = MetricResult(
                name='盈亏比',
                value=cls.profit_loss_ratio(trades),
                description='平均盈利/平均亏损',
                category='交易',
                unit='',
                is_better_higher=True
            )
        
        return metrics
