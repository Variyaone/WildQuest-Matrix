"""
绩效分析器

计算回测绩效指标。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import pandas as pd
import numpy as np


@dataclass
class PerformanceMetrics:
    """绩效指标"""
    total_return: float = 0.0
    annual_return: float = 0.0
    excess_return: float = 0.0
    volatility: float = 0.0
    downside_volatility: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    turnover_rate: float = 0.0
    trade_count: int = 0
    avg_holding_period: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    tracking_error: float = 0.0
    treynor_ratio: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'excess_return': self.excess_return,
            'volatility': self.volatility,
            'downside_volatility': self.downside_volatility,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_duration': self.max_drawdown_duration,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'information_ratio': self.information_ratio,
            'win_rate': self.win_rate,
            'profit_loss_ratio': self.profit_loss_ratio,
            'turnover_rate': self.turnover_rate,
            'trade_count': self.trade_count,
            'avg_holding_period': self.avg_holding_period,
            'var_95': self.var_95,
            'cvar_95': self.cvar_95,
            'skewness': self.skewness,
            'kurtosis': self.kurtosis,
            'beta': self.beta,
            'alpha': self.alpha,
            'tracking_error': self.tracking_error,
            'treynor_ratio': self.treynor_ratio,
            'details': self.details
        }
    
    def get_summary(self) -> str:
        """获取摘要"""
        return f"""
绩效指标摘要
================
收益指标:
  累计收益率: {self.total_return:.2%}
  年化收益率: {self.annual_return:.2%}
  超额收益率: {self.excess_return:.2%}

风险指标:
  年化波动率: {self.volatility:.2%}
  最大回撤: {self.max_drawdown:.2%}
  回撤持续: {self.max_drawdown_duration}天

风险调整收益:
  夏普比率: {self.sharpe_ratio:.2f}
  索提诺比率: {self.sortino_ratio:.2f}
  卡玛比率: {self.calmar_ratio:.2f}

交易指标:
  胜率: {self.win_rate:.2%}
  盈亏比: {self.profit_loss_ratio:.2f}
  换手率: {self.turnover_rate:.2%}
  交易次数: {self.trade_count}
"""


class PerformanceAnalyzer:
    """
    绩效分析器
    
    计算回测绩效指标。
    """
    
    TRADING_DAYS_PER_YEAR = 252
    RISK_FREE_RATE = 0.03
    
    def __init__(
        self,
        risk_free_rate: float = 0.03,
        trading_days: int = 252
    ):
        """
        初始化绩效分析器
        
        Args:
            risk_free_rate: 无风险利率
            trading_days: 年交易日数
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
    
    def analyze(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        positions: Optional[pd.DataFrame] = None,
        trades: Optional[List[Dict]] = None
    ) -> PerformanceMetrics:
        """
        分析绩效
        
        Args:
            returns: 收益率序列
            benchmark_returns: 基准收益率序列
            positions: 持仓数据
            trades: 交易记录
            
        Returns:
            PerformanceMetrics: 绩效指标
        """
        if len(returns) == 0:
            return PerformanceMetrics()
        
        metrics = PerformanceMetrics()
        
        metrics.total_return = self._calculate_total_return(returns)
        metrics.annual_return = self._calculate_annual_return(returns)
        metrics.volatility = self._calculate_volatility(returns)
        metrics.downside_volatility = self._calculate_downside_volatility(returns)
        
        drawdown_info = self._calculate_drawdown(returns)
        metrics.max_drawdown = drawdown_info['max_drawdown']
        metrics.max_drawdown_duration = drawdown_info['duration']
        
        metrics.sharpe_ratio = self._calculate_sharpe_ratio(returns)
        metrics.sortino_ratio = self._calculate_sortino_ratio(returns)
        metrics.calmar_ratio = self._calculate_calmar_ratio(
            metrics.annual_return, metrics.max_drawdown
        )
        
        metrics.var_95 = self._calculate_var(returns, 0.95)
        metrics.cvar_95 = self._calculate_cvar(returns, 0.95)
        
        metrics.skewness = returns.skew()
        metrics.kurtosis = returns.kurtosis()
        
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            aligned_returns, aligned_benchmark = returns.align(
                benchmark_returns, join='inner'
            )
            
            if len(aligned_returns) > 0:
                metrics.excess_return = metrics.annual_return - self._calculate_annual_return(aligned_benchmark)
                metrics.tracking_error = self._calculate_tracking_error(aligned_returns, aligned_benchmark)
                metrics.information_ratio = self._calculate_information_ratio(
                    aligned_returns, aligned_benchmark
                )
                metrics.beta = self._calculate_beta(aligned_returns, aligned_benchmark)
                metrics.alpha = self._calculate_alpha(
                    aligned_returns, aligned_benchmark, metrics.beta
                )
                metrics.treynor_ratio = self._calculate_treynor_ratio(
                    aligned_returns, metrics.beta
                )
        
        if trades:
            trade_metrics = self._analyze_trades(trades)
            metrics.win_rate = trade_metrics['win_rate']
            metrics.profit_loss_ratio = trade_metrics['profit_loss_ratio']
            metrics.trade_count = trade_metrics['trade_count']
            metrics.avg_holding_period = trade_metrics['avg_holding_period']
        
        if positions is not None and len(positions) > 0:
            metrics.turnover_rate = self._calculate_turnover(positions)
        
        return metrics
    
    def _calculate_total_return(self, returns: pd.Series) -> float:
        """计算累计收益率"""
        return (1 + returns).prod() - 1
    
    def _calculate_annual_return(self, returns: pd.Series) -> float:
        """计算年化收益率"""
        total_return = self._calculate_total_return(returns)
        n_years = len(returns) / self.trading_days
        if n_years <= 0:
            return 0.0
        if total_return <= -1:
            return -1.0
        return (1 + total_return) ** (1 / n_years) - 1
    
    def _calculate_volatility(self, returns: pd.Series) -> float:
        """计算年化波动率"""
        return returns.std() * np.sqrt(self.trading_days)
    
    def _calculate_downside_volatility(
        self,
        returns: pd.Series,
        target_return: float = 0.0
    ) -> float:
        """计算下行波动率"""
        downside_returns = returns[returns < target_return]
        if len(downside_returns) == 0:
            return 0.0
        return downside_returns.std() * np.sqrt(self.trading_days)
    
    def _calculate_drawdown(self, returns: pd.Series) -> Dict[str, Any]:
        """计算回撤"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        
        max_drawdown = drawdown.min()
        
        is_drawdown = drawdown < 0
        drawdown_groups = (is_drawdown != is_drawdown.shift()).cumsum()
        
        max_duration = 0
        for _, group in drawdown[is_drawdown].groupby(drawdown_groups[is_drawdown]):
            duration = len(group)
            if duration > max_duration:
                max_duration = duration
        
        return {
            'max_drawdown': max_drawdown,
            'duration': max_duration,
            'drawdown_series': drawdown
        }
    
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """计算夏普比率"""
        excess_returns = returns - self.risk_free_rate / self.trading_days
        if excess_returns.std() == 0:
            return 0.0
        return excess_returns.mean() / excess_returns.std() * np.sqrt(self.trading_days)
    
    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """计算索提诺比率"""
        excess_returns = returns - self.risk_free_rate / self.trading_days
        downside_vol = self._calculate_downside_volatility(returns, self.risk_free_rate / self.trading_days)
        if downside_vol == 0:
            return 0.0
        return excess_returns.mean() * self.trading_days / downside_vol
    
    def _calculate_calmar_ratio(
        self,
        annual_return: float,
        max_drawdown: float
    ) -> float:
        """计算卡玛比率"""
        if max_drawdown == 0:
            return 0.0
        return annual_return / abs(max_drawdown)
    
    def _calculate_var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """计算VaR"""
        return returns.quantile(1 - confidence)
    
    def _calculate_cvar(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """计算CVaR"""
        var = self._calculate_var(returns, confidence)
        return returns[returns <= var].mean()
    
    def _calculate_tracking_error(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> float:
        """计算跟踪误差"""
        excess = returns - benchmark_returns
        return excess.std() * np.sqrt(self.trading_days)
    
    def _calculate_information_ratio(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> float:
        """计算信息比率"""
        excess = returns - benchmark_returns
        tracking_error = self._calculate_tracking_error(returns, benchmark_returns)
        if tracking_error == 0:
            return 0.0
        return excess.mean() * self.trading_days / tracking_error
    
    def _calculate_beta(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> float:
        """计算Beta"""
        covariance = returns.cov(benchmark_returns)
        variance = benchmark_returns.var()
        if variance == 0:
            return 0.0
        return covariance / variance
    
    def _calculate_alpha(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
        beta: float
    ) -> float:
        """计算Alpha"""
        excess_return = returns.mean() - self.risk_free_rate / self.trading_days
        benchmark_excess = benchmark_returns.mean() - self.risk_free_rate / self.trading_days
        return (excess_return - beta * benchmark_excess) * self.trading_days
    
    def _calculate_treynor_ratio(
        self,
        returns: pd.Series,
        beta: float
    ) -> float:
        """计算特雷诺比率"""
        if beta == 0:
            return 0.0
        excess_return = returns.mean() * self.trading_days - self.risk_free_rate
        return excess_return / beta
    
    def _analyze_trades(self, trades: List[Dict]) -> Dict[str, Any]:
        """分析交易"""
        if not trades:
            return {
                'win_rate': 0.0,
                'profit_loss_ratio': 0.0,
                'trade_count': 0,
                'avg_holding_period': 0.0
            }
        
        profits = []
        losses = []
        holding_periods = []
        
        for trade in trades:
            pnl = trade.get('pnl', 0)
            if pnl > 0:
                profits.append(pnl)
            elif pnl < 0:
                losses.append(abs(pnl))
            
            if 'holding_period' in trade:
                holding_periods.append(trade['holding_period'])
        
        win_count = len(profits)
        loss_count = len(losses)
        total_trades = win_count + loss_count
        
        win_rate = win_count / total_trades if total_trades > 0 else 0.0
        
        avg_profit = np.mean(profits) if profits else 0.0
        avg_loss = np.mean(losses) if losses else 0.0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0.0
        
        avg_holding = np.mean(holding_periods) if holding_periods else 0.0
        
        return {
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'trade_count': total_trades,
            'avg_holding_period': avg_holding
        }
    
    def _calculate_turnover(self, positions: pd.DataFrame) -> float:
        """计算换手率"""
        if len(positions) < 2:
            return 0.0
        
        turnover_sum = 0.0
        for i in range(1, len(positions)):
            prev_pos = positions.iloc[i-1]
            curr_pos = positions.iloc[i]
            
            buys = curr_pos.get('buy_value', 0)
            sells = curr_pos.get('sell_value', 0)
            total_value = curr_pos.get('total_value', 1)
            
            turnover_sum += (buys + sells) / total_value
        
        return turnover_sum / (len(positions) - 1)
    
    def calculate_rolling_metrics(
        self,
        returns: pd.Series,
        window: int = 252
    ) -> pd.DataFrame:
        """
        计算滚动指标
        
        Args:
            returns: 收益率序列
            window: 滚动窗口
            
        Returns:
            pd.DataFrame: 滚动指标
        """
        rolling_return = returns.rolling(window).apply(
            lambda x: (1 + x).prod() - 1
        )
        
        rolling_vol = returns.rolling(window).std() * np.sqrt(self.trading_days)
        
        rolling_sharpe = returns.rolling(window).apply(
            lambda x: (x.mean() - self.risk_free_rate / self.trading_days) / x.std() * np.sqrt(self.trading_days)
            if x.std() > 0 else 0
        )
        
        rolling_drawdown = returns.rolling(window).apply(
            lambda x: ((1 + x).cumprod() - (1 + x).cumprod().cummax()).min()
        )
        
        return pd.DataFrame({
            'rolling_return': rolling_return,
            'rolling_volatility': rolling_vol,
            'rolling_sharpe': rolling_sharpe,
            'rolling_drawdown': rolling_drawdown
        })
    
    def calculate_monthly_returns(self, returns: pd.Series) -> pd.DataFrame:
        """
        计算月度收益
        
        Args:
            returns: 收益率序列
            
        Returns:
            pd.DataFrame: 月度收益表
        """
        if isinstance(returns.index, pd.DatetimeIndex):
            monthly = returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
        else:
            returns_copy = returns.copy()
            returns_copy.index = pd.to_datetime(returns_copy.index)
            monthly = returns_copy.resample('ME').apply(lambda x: (1 + x).prod() - 1)
        
        monthly_df = pd.DataFrame({
            'return': monthly
        })
        
        if len(monthly_df) > 0:
            monthly_df['year'] = monthly_df.index.year
            monthly_df['month'] = monthly_df.index.month
            
            pivot = monthly_df.pivot_table(
                values='return',
                index='year',
                columns='month',
                aggfunc='first'
            )
            
            pivot.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][:len(pivot.columns)]
            
            return pivot
        
        return pd.DataFrame()
    
    def generate_performance_report(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        positions: Optional[pd.DataFrame] = None,
        trades: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        生成绩效报告
        
        Args:
            returns: 收益率序列
            benchmark_returns: 基准收益率
            positions: 持仓数据
            trades: 交易记录
            
        Returns:
            Dict: 绩效报告
        """
        metrics = self.analyze(returns, benchmark_returns, positions, trades)
        
        rolling_metrics = self.calculate_rolling_metrics(returns)
        monthly_returns = self.calculate_monthly_returns(returns)
        
        cumulative_returns = (1 + returns).cumprod()
        
        drawdown_info = self._calculate_drawdown(returns)
        
        return {
            'metrics': metrics.to_dict(),
            'rolling_metrics': rolling_metrics.to_dict(),
            'monthly_returns': monthly_returns.to_dict() if len(monthly_returns) > 0 else {},
            'cumulative_returns': cumulative_returns.to_dict(),
            'drawdown_series': drawdown_info['drawdown_series'].to_dict(),
            'period': {
                'start': returns.index[0] if len(returns) > 0 else None,
                'end': returns.index[-1] if len(returns) > 0 else None,
                'trading_days': len(returns)
            }
        }
