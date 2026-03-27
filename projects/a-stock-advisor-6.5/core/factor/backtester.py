"""
因子回测器模块

多维度回测因子有效性，支持不同时间段、交易品、持仓周期和分组的回测。
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import pandas as pd
import numpy as np

from .registry import FactorMetadata, BacktestResult, get_factor_registry
from .validator import ICAnalyzer
from ..infrastructure.exceptions import FactorException


class MarketType(Enum):
    """市场类型"""
    BULL = "bull_market"
    BEAR = "bear_market"
    SIDEWAYS = "sideways"
    ALL = "all_market"


class HoldingPeriod(Enum):
    """持仓周期"""
    ONE_DAY = 1
    FIVE_DAYS = 5
    TEN_DAYS = 10
    TWENTY_DAYS = 20


@dataclass
class GroupBacktestResult:
    """分组回测结果"""
    group_id: int
    avg_return: float
    cumulative_return: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    stock_count: int


@dataclass
class FactorBacktestResult:
    """因子回测结果"""
    factor_id: str
    success: bool
    market_type: MarketType
    holding_period: HoldingPeriod
    n_groups: int
    group_results: List[GroupBacktestResult] = field(default_factory=list)
    spread_return: float = 0.0
    ic_mean: float = 0.0
    ic_series: Optional[pd.Series] = None
    turnover_rate: float = 0.0
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class MarketClassifier:
    """
    市场环境分类器
    
    根据指数表现判断市场类型。
    """
    
    @staticmethod
    def classify_market(
        index_returns: pd.Series,
        bull_threshold: float = 0.2,
        bear_threshold: float = -0.2
    ) -> MarketType:
        """
        分类市场环境
        
        Args:
            index_returns: 指数收益率序列
            bull_threshold: 牛市阈值
            bear_threshold: 熊市阈值
            
        Returns:
            MarketType: 市场类型
        """
        cumulative_return = (1 + index_returns).prod() - 1
        
        if cumulative_return >= bull_threshold:
            return MarketType.BULL
        elif cumulative_return <= bear_threshold:
            return MarketType.BEAR
        else:
            return MarketType.SIDEWAYS
    
    @staticmethod
    def get_market_periods(
        index_df: pd.DataFrame,
        window: int = 60,
        date_col: str = "date",
        return_col: str = "pct_chg"
    ) -> pd.DataFrame:
        """
        获取各时期的市场类型
        
        Args:
            index_df: 指数数据
            window: 滚动窗口
            date_col: 日期列名
            return_col: 收益率列名
            
        Returns:
            pd.DataFrame: 包含市场类型的DataFrame
        """
        index_df = index_df.copy()
        index_df[return_col] = index_df[return_col] / 100 if index_df[return_col].abs().max() > 1 else index_df[return_col]
        
        rolling_return = index_df[return_col].rolling(window=window).sum()
        
        market_types = rolling_return.apply(
            lambda x: MarketClassifier.classify_market(pd.Series([x]))
        )
        
        index_df['market_type'] = market_types
        return index_df


class GroupConstructor:
    """
    分组构建器
    
    根据因子值构建股票分组。
    """
    
    @staticmethod
    def construct_groups(
        factor_df: pd.DataFrame,
        n_groups: int = 5,
        factor_col: str = "factor_value",
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> pd.DataFrame:
        """
        构建因子分组
        
        Args:
            factor_df: 因子数据
            n_groups: 分组数量
            factor_col: 因子值列名
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            pd.DataFrame: 包含分组的DataFrame
        """
        factor_df = factor_df.copy()
        
        def assign_group(group):
            group[factor_col] = pd.to_numeric(group[factor_col], errors='coerce')
            valid_mask = ~group[factor_col].isna()
            
            group.loc[valid_mask, 'factor_group'] = pd.qcut(
                group.loc[valid_mask, factor_col],
                n_groups,
                labels=False,
                duplicates='drop'
            )
            
            return group
        
        factor_df = factor_df.groupby(date_col, group_keys=False).apply(assign_group)
        
        return factor_df


class PortfolioSimulator:
    """
    组合模拟器
    
    模拟因子组合的表现。
    """
    
    @staticmethod
    def simulate_group_portfolio(
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        group_id: int,
        holding_period: int = 5,
        factor_col: str = "factor_value",
        return_col: str = "forward_return",
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> Tuple[pd.Series, float, float]:
        """
        模拟单组组合表现
        
        Args:
            factor_df: 因子数据（含分组）
            return_df: 收益数据
            group_id: 组别ID
            holding_period: 持仓周期
            factor_col: 因子值列名
            return_col: 收益列名
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            Tuple[pd.Series, float, float]: 收益序列、胜率、换手率
        """
        group_df = factor_df[factor_df['factor_group'] == group_id].copy()
        
        merged = pd.merge(
            group_df[[date_col, stock_col]],
            return_df[[date_col, stock_col, return_col]],
            on=[date_col, stock_col],
            how="inner"
        )
        
        if merged.empty:
            return pd.Series(), 0.0, 0.0
        
        daily_returns = merged.groupby(date_col)[return_col].mean()
        
        win_rate = (daily_returns > 0).sum() / len(daily_returns)
        
        dates = sorted(factor_df[date_col].unique())
        rebalance_dates = dates[::holding_period]
        
        turnover_rates = []
        prev_stocks = set()
        
        for rebalance_date in rebalance_dates:
            current_stocks = set(
                group_df[group_df[date_col] == rebalance_date][stock_col]
            )
            
            if prev_stocks:
                turnover = len(current_stocks.symmetric_difference(prev_stocks)) / max(len(prev_stocks), 1)
                turnover_rates.append(turnover)
            
            prev_stocks = current_stocks
        
        avg_turnover = np.mean(turnover_rates) if turnover_rates else 0.0
        
        return daily_returns, win_rate, avg_turnover
    
    @staticmethod
    def calculate_performance_metrics(returns: pd.Series) -> Dict[str, float]:
        """
        计算绩效指标
        
        Args:
            returns: 收益序列
            
        Returns:
            Dict[str, float]: 绩效指标
        """
        if returns.empty:
            return {
                "cumulative_return": 0.0,
                "annual_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "volatility": 0.0
            }
        
        cumulative_return = (1 + returns).prod() - 1
        
        n_periods = len(returns)
        annual_return = (1 + cumulative_return) ** (252 / n_periods) - 1
        
        volatility = returns.std() * np.sqrt(252)
        
        risk_free_rate = 0.03
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0.0
        
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            "cumulative_return": cumulative_return,
            "annual_return": annual_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "volatility": volatility
        }


class FactorBacktester:
    """
    因子回测器
    
    多维度回测因子有效性。
    """
    
    def __init__(self):
        """初始化因子回测器"""
        self._registry = get_factor_registry()
    
    def backtest(
        self,
        factor_id: str,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        index_df: Optional[pd.DataFrame] = None,
        n_groups: int = 5,
        holding_period: HoldingPeriod = HoldingPeriod.FIVE_DAYS,
        market_type: MarketType = MarketType.ALL,
        factor_col: str = "factor_value",
        return_col: str = "forward_return",
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> FactorBacktestResult:
        """
        回测因子
        
        Args:
            factor_id: 因子ID
            factor_df: 因子数据
            return_df: 收益数据
            index_df: 指数数据（用于市场分类）
            n_groups: 分组数量
            holding_period: 持仓周期
            market_type: 市场类型
            factor_col: 因子值列名
            return_col: 收益列名
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            FactorBacktestResult: 回测结果
        """
        try:
            if market_type != MarketType.ALL and index_df is not None:
                market_df = MarketClassifier.get_market_periods(index_df)
                market_dates = market_df[market_df['market_type'] == market_type][date_col].tolist()
                
                factor_df = factor_df[factor_df[date_col].isin(market_dates)]
                return_df = return_df[return_df[date_col].isin(market_dates)]
            
            grouped_factor = GroupConstructor.construct_groups(
                factor_df, n_groups, factor_col, date_col, stock_col
            )
            
            group_results = []
            group_returns = {}
            
            for group_id in range(n_groups):
                returns, win_rate, turnover = PortfolioSimulator.simulate_group_portfolio(
                    grouped_factor, return_df, group_id,
                    holding_period.value, factor_col, return_col,
                    date_col, stock_col
                )
                
                if returns.empty:
                    continue
                
                metrics = PortfolioSimulator.calculate_performance_metrics(returns)
                
                group_result = GroupBacktestResult(
                    group_id=group_id,
                    avg_return=returns.mean(),
                    cumulative_return=metrics["cumulative_return"],
                    win_rate=win_rate,
                    sharpe_ratio=metrics["sharpe_ratio"],
                    max_drawdown=metrics["max_drawdown"],
                    stock_count=grouped_factor[grouped_factor['factor_group'] == group_id][stock_col].nunique()
                )
                
                group_results.append(group_result)
                group_returns[group_id] = returns
            
            spread_return = 0.0
            if len(group_results) >= 2:
                top_group = max(group_results, key=lambda x: x.group_id)
                bottom_group = min(group_results, key=lambda x: x.group_id)
                spread_return = top_group.cumulative_return - bottom_group.cumulative_return
            
            ic_series = ICAnalyzer.calculate_ic_series(
                factor_df, return_df,
                factor_col, return_col,
                date_col, stock_col
            )
            ic_mean = ic_series.mean()
            
            avg_turnover = np.mean([gr.win_rate for gr in group_results]) if group_results else 0.0
            
            result = FactorBacktestResult(
                factor_id=factor_id,
                success=True,
                market_type=market_type,
                holding_period=holding_period,
                n_groups=n_groups,
                group_results=group_results,
                spread_return=spread_return,
                ic_mean=ic_mean,
                ic_series=ic_series,
                turnover_rate=avg_turnover,
                details={
                    "group_returns": {k: v.to_dict() for k, v in group_returns.items()},
                    "total_periods": len(ic_series)
                }
            )
            
            backtest_result = BacktestResult(
                annual_return=group_results[-1].cumulative_return if group_results else 0.0,
                sharpe_ratio=group_results[-1].sharpe_ratio if group_results else 0.0,
                max_drawdown=group_results[-1].max_drawdown if group_results else 0.0,
                win_rate=group_results[-1].win_rate if group_results else 0.0,
                ic=ic_mean
            )
            
            self._registry.update_backtest_result(
                factor_id, 
                market_type.value, 
                backtest_result
            )
            
            return result
            
        except Exception as e:
            return FactorBacktestResult(
                factor_id=factor_id,
                success=False,
                market_type=market_type,
                holding_period=holding_period,
                n_groups=n_groups,
                error_message=str(e)
            )
    
    def multi_dimension_backtest(
        self,
        factor_id: str,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        index_df: Optional[pd.DataFrame] = None,
        n_groups_list: List[int] = None,
        holding_periods: List[HoldingPeriod] = None,
        market_types: List[MarketType] = None
    ) -> Dict[str, FactorBacktestResult]:
        """
        多维度回测
        
        Args:
            factor_id: 因子ID
            factor_df: 因子数据
            return_df: 收益数据
            index_df: 指数数据
            n_groups_list: 分组数量列表
            holding_periods: 持仓周期列表
            market_types: 市场类型列表
            
        Returns:
            Dict[str, FactorBacktestResult]: 各维度回测结果
        """
        n_groups_list = n_groups_list or [5, 10]
        holding_periods = holding_periods or [HoldingPeriod.FIVE_DAYS, HoldingPeriod.TEN_DAYS]
        market_types = market_types or [MarketType.ALL]
        
        results = {}
        
        for n_groups in n_groups_list:
            for holding_period in holding_periods:
                for market_type in market_types:
                    key = f"{market_type.value}_ng{n_groups}_hp{holding_period.value}"
                    
                    results[key] = self.backtest(
                        factor_id=factor_id,
                        factor_df=factor_df,
                        return_df=return_df,
                        index_df=index_df,
                        n_groups=n_groups,
                        holding_period=holding_period,
                        market_type=market_type
                    )
        
        return results
    
    def generate_backtest_report(
        self,
        result: FactorBacktestResult
    ) -> str:
        """
        生成回测报告
        
        Args:
            result: 回测结果
            
        Returns:
            str: 报告文本
        """
        if not result.success:
            return f"回测失败: {result.error_message}"
        
        lines = [
            f"因子回测报告 - {result.factor_id}",
            "=" * 50,
            f"市场类型: {result.market_type.value}",
            f"持仓周期: {result.holding_period.value}天",
            f"分组数量: {result.n_groups}",
            "",
            "分组表现:",
            "-" * 50,
        ]
        
        for gr in result.group_results:
            lines.extend([
                f"  第{gr.group_id + 1}组:",
                f"    累计收益: {gr.cumulative_return:.2%}",
                f"    夏普比率: {gr.sharpe_ratio:.2f}",
                f"    最大回撤: {gr.max_drawdown:.2%}",
                f"    胜率: {gr.win_rate:.2%}",
                f"    股票数: {gr.stock_count}",
            ])
        
        lines.extend([
            "",
            "综合指标:",
            "-" * 50,
            f"  多空收益差: {result.spread_return:.2%}",
            f"  平均IC: {result.ic_mean:.4f}",
            f"  换手率: {result.turnover_rate:.2%}",
        ])
        
        return "\n".join(lines)


_default_backtester: Optional[FactorBacktester] = None


def get_factor_backtester() -> FactorBacktester:
    """获取全局因子回测器实例"""
    global _default_backtester
    if _default_backtester is None:
        _default_backtester = FactorBacktester()
    return _default_backtester


def reset_factor_backtester():
    """重置全局因子回测器"""
    global _default_backtester
    _default_backtester = None
