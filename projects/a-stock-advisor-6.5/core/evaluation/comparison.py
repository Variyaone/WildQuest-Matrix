"""
绩效对比分析

对比多个因子或策略的表现。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy as np

from .metrics import PerformanceMetricsCalculator


@dataclass
class ComparisonResult:
    """对比结果"""
    name: str
    category: str
    metrics: Dict[str, float]
    rank: int = 0
    percentile: float = 0.0
    is_winner: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'category': self.category,
            'metrics': self.metrics,
            'rank': self.rank,
            'percentile': self.percentile,
            'is_winner': self.is_winner
        }


class PerformanceComparison:
    """
    绩效对比分析
    
    对比多个因子或策略的表现。
    """
    
    def __init__(
        self,
        risk_free_rate: float = 0.03,
        trading_days: int = 252
    ):
        """
        初始化对比分析器
        
        Args:
            risk_free_rate: 无风险利率
            trading_days: 年交易日数
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
    
    def compare_factors(
        self,
        factors_data: Dict[str, pd.DataFrame],
        return_data: pd.DataFrame,
        metrics: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        对比因子表现
        
        Args:
            factors_data: 因子数据字典 {因子名: 因子数据}
            return_data: 收益数据
            metrics: 对比指标列表
            
        Returns:
            pd.DataFrame: 对比结果
        """
        if metrics is None:
            metrics = ['ic_mean', 'ir', 'coverage', 'turnover']
        
        results = []
        
        for factor_name, factor_data in factors_data.items():
            factor_result = {'factor_name': factor_name}
            
            ic_results = self._calculate_factor_ic(factor_data, return_data)
            factor_result['ic_mean'] = ic_results['ic_mean']
            factor_result['ic_std'] = ic_results['ic_std']
            factor_result['ir'] = ic_results['ir']
            
            utility_results = self._calculate_factor_utility(factor_data)
            factor_result['coverage'] = utility_results['coverage']
            factor_result['turnover'] = utility_results['turnover']
            
            results.append(factor_result)
        
        df = pd.DataFrame(results)
        
        if 'ic_mean' in df.columns:
            df['ic_rank'] = df['ic_mean'].abs().rank(ascending=False)
        
        if 'ir' in df.columns:
            df['ir_rank'] = df['ir'].abs().rank(ascending=False)
        
        return df
    
    def compare_strategies(
        self,
        strategies_returns: Dict[str, pd.Series],
        benchmark_returns: Optional[pd.Series] = None,
        metrics: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        对比策略表现
        
        Args:
            strategies_returns: 策略收益率字典 {策略名: 收益率序列}
            benchmark_returns: 基准收益率
            metrics: 对比指标列表
            
        Returns:
            pd.DataFrame: 对比结果
        """
        if metrics is None:
            metrics = ['total_return', 'annual_return', 'sharpe_ratio', 'max_drawdown', 'volatility']
        
        results = []
        
        for strategy_name, returns in strategies_returns.items():
            strategy_result = {'strategy_name': strategy_name}
            
            strategy_result['total_return'] = PerformanceMetricsCalculator.total_return(returns)
            strategy_result['annual_return'] = PerformanceMetricsCalculator.annual_return(
                returns, self.trading_days
            )
            strategy_result['volatility'] = PerformanceMetricsCalculator.volatility(
                returns, self.trading_days
            )
            strategy_result['max_drawdown'] = PerformanceMetricsCalculator.max_drawdown(returns)
            strategy_result['sharpe_ratio'] = PerformanceMetricsCalculator.sharpe_ratio(
                returns, self.risk_free_rate, self.trading_days
            )
            strategy_result['sortino_ratio'] = PerformanceMetricsCalculator.sortino_ratio(
                returns, self.risk_free_rate, self.trading_days
            )
            strategy_result['calmar_ratio'] = PerformanceMetricsCalculator.calmar_ratio(
                returns, self.trading_days
            )
            
            if benchmark_returns is not None:
                strategy_result['excess_return'] = strategy_result['annual_return'] - \
                    PerformanceMetricsCalculator.annual_return(benchmark_returns, self.trading_days)
                strategy_result['information_ratio'] = PerformanceMetricsCalculator.information_ratio(
                    returns, benchmark_returns, self.trading_days
                )
                strategy_result['beta'] = PerformanceMetricsCalculator.beta(returns, benchmark_returns)
                strategy_result['alpha'] = PerformanceMetricsCalculator.alpha(
                    returns, benchmark_returns, self.risk_free_rate, self.trading_days
                )
            
            results.append(strategy_result)
        
        df = pd.DataFrame(results)
        
        df['return_rank'] = df['annual_return'].rank(ascending=False)
        df['sharpe_rank'] = df['sharpe_ratio'].rank(ascending=False)
        df['drawdown_rank'] = df['max_drawdown'].rank(ascending=True)
        
        return df
    
    def compare_with_benchmark(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
        benchmark_name: str = "基准"
    ) -> Dict[str, Any]:
        """
        与基准对比
        
        Args:
            returns: 策略收益率
            benchmark_returns: 基准收益率
            benchmark_name: 基准名称
            
        Returns:
            Dict: 对比结果
        """
        aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
        
        if len(aligned_returns) == 0:
            return {'error': '无重叠数据'}
        
        strategy_cum = (1 + aligned_returns).cumprod()
        benchmark_cum = (1 + aligned_benchmark).cumprod()
        
        excess_returns = aligned_returns - aligned_benchmark
        
        tracking_error = PerformanceMetricsCalculator.tracking_error(
            aligned_returns, aligned_benchmark, self.trading_days
        )
        
        information_ratio = PerformanceMetricsCalculator.information_ratio(
            aligned_returns, aligned_benchmark, self.trading_days
        )
        
        beta = PerformanceMetricsCalculator.beta(aligned_returns, aligned_benchmark)
        alpha = PerformanceMetricsCalculator.alpha(
            aligned_returns, aligned_benchmark, self.risk_free_rate, self.trading_days
        )
        
        win_rate = (aligned_returns > aligned_benchmark).mean()
        
        correlation = aligned_returns.corr(aligned_benchmark)
        
        return {
            'strategy': {
                'total_return': PerformanceMetricsCalculator.total_return(aligned_returns),
                'annual_return': PerformanceMetricsCalculator.annual_return(aligned_returns, self.trading_days),
                'volatility': PerformanceMetricsCalculator.volatility(aligned_returns, self.trading_days),
                'max_drawdown': PerformanceMetricsCalculator.max_drawdown(aligned_returns),
                'sharpe_ratio': PerformanceMetricsCalculator.sharpe_ratio(
                    aligned_returns, self.risk_free_rate, self.trading_days
                )
            },
            'benchmark': {
                'name': benchmark_name,
                'total_return': PerformanceMetricsCalculator.total_return(aligned_benchmark),
                'annual_return': PerformanceMetricsCalculator.annual_return(aligned_benchmark, self.trading_days),
                'volatility': PerformanceMetricsCalculator.volatility(aligned_benchmark, self.trading_days),
                'max_drawdown': PerformanceMetricsCalculator.max_drawdown(aligned_benchmark)
            },
            'comparison': {
                'excess_return': PerformanceMetricsCalculator.annual_return(aligned_returns, self.trading_days) -
                    PerformanceMetricsCalculator.annual_return(aligned_benchmark, self.trading_days),
                'tracking_error': tracking_error,
                'information_ratio': information_ratio,
                'beta': beta,
                'alpha': alpha,
                'win_rate': win_rate,
                'correlation': correlation
            },
            'cumulative': {
                'strategy': strategy_cum.iloc[-1] if len(strategy_cum) > 0 else 1,
                'benchmark': benchmark_cum.iloc[-1] if len(benchmark_cum) > 0 else 1
            }
        }
    
    def compare_periods(
        self,
        returns: pd.Series,
        periods: Dict[str, Tuple[str, str]]
    ) -> pd.DataFrame:
        """
        分阶段对比
        
        Args:
            returns: 收益率序列
            periods: 阶段定义 {阶段名: (开始日期, 结束日期)}
            
        Returns:
            pd.DataFrame: 各阶段对比结果
        """
        results = []
        
        for period_name, (start_date, end_date) in periods.items():
            if isinstance(returns.index, pd.DatetimeIndex):
                period_returns = returns.loc[start_date:end_date]
            else:
                period_returns = returns.loc[
                    (returns.index >= start_date) & (returns.index <= end_date)
                ]
            
            if len(period_returns) == 0:
                continue
            
            result = {
                'period': period_name,
                'start_date': start_date,
                'end_date': end_date,
                'trading_days': len(period_returns),
                'total_return': PerformanceMetricsCalculator.total_return(period_returns),
                'annual_return': PerformanceMetricsCalculator.annual_return(
                    period_returns, self.trading_days
                ),
                'volatility': PerformanceMetricsCalculator.volatility(
                    period_returns, self.trading_days
                ),
                'max_drawdown': PerformanceMetricsCalculator.max_drawdown(period_returns),
                'sharpe_ratio': PerformanceMetricsCalculator.sharpe_ratio(
                    period_returns, self.risk_free_rate, self.trading_days
                )
            }
            
            results.append(result)
        
        return pd.DataFrame(results)
    
    def compare_parameters(
        self,
        strategy_func: callable,
        param_grid: Dict[str, List[Any]],
        data: pd.DataFrame,
        base_params: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        参数敏感性对比
        
        Args:
            strategy_func: 策略函数
            param_grid: 参数网格
            data: 回测数据
            base_params: 基础参数
            
        Returns:
            pd.DataFrame: 参数对比结果
        """
        import itertools
        
        results = []
        base_params = base_params or {}
        
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        for combination in itertools.product(*param_values):
            params = dict(zip(param_names, combination))
            full_params = {**base_params, **params}
            
            try:
                returns = strategy_func(data, **full_params)
                
                if returns is None or len(returns) == 0:
                    continue
                
                result = {
                    **{f'param_{k}': v for k, v in params.items()},
                    'total_return': PerformanceMetricsCalculator.total_return(returns),
                    'annual_return': PerformanceMetricsCalculator.annual_return(
                        returns, self.trading_days
                    ),
                    'sharpe_ratio': PerformanceMetricsCalculator.sharpe_ratio(
                        returns, self.risk_free_rate, self.trading_days
                    ),
                    'max_drawdown': PerformanceMetricsCalculator.max_drawdown(returns)
                }
                
                results.append(result)
                
            except Exception as e:
                continue
        
        return pd.DataFrame(results)
    
    def _calculate_factor_ic(
        self,
        factor_data: pd.DataFrame,
        return_data: pd.DataFrame
    ) -> Dict[str, float]:
        """计算因子IC"""
        ics = []
        
        for date in factor_data.index:
            if date not in return_data.index:
                continue
            
            factor_vals = factor_data.loc[date].dropna()
            return_vals = return_data.loc[date].dropna()
            
            common_stocks = factor_vals.index.intersection(return_vals.index)
            
            if len(common_stocks) < 10:
                continue
            
            ic = factor_vals[common_stocks].corr(return_vals[common_stocks], method='spearman')
            
            if pd.notna(ic):
                ics.append(ic)
        
        if not ics:
            return {'ic_mean': 0.0, 'ic_std': 0.0, 'ir': 0.0}
        
        ic_mean = np.mean(ics)
        ic_std = np.std(ics)
        ir = ic_mean / ic_std if ic_std > 0 else 0.0
        
        return {
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'ir': ir
        }
    
    def _calculate_factor_utility(self, factor_data: pd.DataFrame) -> Dict[str, float]:
        """计算因子实用性"""
        total_cells = factor_data.size
        valid_cells = factor_data.notna().sum().sum()
        coverage = valid_cells / total_cells if total_cells > 0 else 0
        
        turnovers = []
        for i in range(1, len(factor_data)):
            prev_vals = factor_data.iloc[i-1].dropna()
            curr_vals = factor_data.iloc[i].dropna()
            
            common_stocks = prev_vals.index.intersection(curr_vals.index)
            
            if len(common_stocks) < 10:
                continue
            
            prev_ranks = prev_vals[common_stocks].rank()
            curr_ranks = curr_vals[common_stocks].rank()
            
            rank_changes = abs(curr_ranks - prev_ranks).mean()
            max_change = len(common_stocks)
            turnover = rank_changes / max_change if max_change > 0 else 0
            turnovers.append(turnover)
        
        avg_turnover = np.mean(turnovers) if turnovers else 0
        
        return {
            'coverage': coverage,
            'turnover': avg_turnover
        }
    
    def generate_comparison_report(
        self,
        comparison_df: pd.DataFrame,
        title: str = "绩效对比报告"
    ) -> str:
        """
        生成对比报告
        
        Args:
            comparison_df: 对比结果DataFrame
            title: 报告标题
            
        Returns:
            str: 报告内容
        """
        report = f"""
{title}
{'=' * 50}

"""
        
        if len(comparison_df) == 0:
            return report + "无数据"
        
        numeric_cols = comparison_df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if col.endswith('_rank'):
                continue
            
            report += f"\n{col}:\n"
            report += f"  最佳: {comparison_df.iloc[comparison_df[col].idxmax()][comparison_df.columns[0]]} "
            report += f"({comparison_df[col].max():.4f})\n"
            report += f"  最差: {comparison_df.iloc[comparison_df[col].idxmin()][comparison_df.columns[0]]} "
            report += f"({comparison_df[col].min():.4f})\n"
            report += f"  平均: {comparison_df[col].mean():.4f}\n"
            report += f"  标准差: {comparison_df[col].std():.4f}\n"
        
        return report
