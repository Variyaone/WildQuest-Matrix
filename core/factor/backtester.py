"""
因子回测器模块

多维度回测因子有效性，支持不同时间段、交易品、持仓周期和分组的回测。
集成：未来函数检测、交易成本模型、涨跌停过滤、IC显著性检验。
增强：多频率支持（日线/小时线）、精确涨跌停判断、执行价格模拟。
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

import pandas as pd
import numpy as np
from scipy import stats

from .registry import FactorMetadata, BacktestResult, get_factor_registry
from .validator import ICAnalyzer
from ..infrastructure.exceptions import FactorException
from ..backtest.lookahead_guard import LookAheadGuard, LookAheadBiasError
from .enhanced_daily_backtest import (
    EnhancedDailyConfig,
    EnhancedDailyBacktest,
    EnhancedLimitHandler,
    ExecutionPriceSimulator,
    OvernightGapAnalyzer,
    PriceType,
    get_enhanced_daily_config
)
from .hourly_backtest import (
    HourlyBacktestConfig,
    HourlyBacktester,
    HourlyFrequency,
    get_hourly_backtester
)

logger = logging.getLogger(__name__)


class BacktestFrequency(Enum):
    """回测频率"""
    DAILY = "daily"
    HOURLY = "hourly"
    MINUTE_60 = "60m"
    MINUTE_30 = "30m"
    MINUTE_15 = "15m"
    MINUTE_5 = "5m"
    MINUTE_1 = "1m"


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
    ONE_HOUR = 1
    FOUR_HOURS = 4


@dataclass
class TransactionCosts:
    """交易成本配置"""
    commission: float = 0.0003
    stamp_duty: float = 0.001
    slippage: float = 0.0005
    
    @property
    def buy_cost(self) -> float:
        return self.commission + self.slippage
    
    @property
    def sell_cost(self) -> float:
        return self.commission + self.stamp_duty + self.slippage
    
    @property
    def round_trip_cost(self) -> float:
        return self.buy_cost + self.sell_cost


@dataclass
class ICStatistics:
    """IC统计检验结果"""
    ic_mean: float
    ic_std: float
    ic_ir: float
    t_statistic: float
    p_value: float
    ci_lower: float
    ci_upper: float
    is_significant: bool
    significance_level: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ic_mean": self.ic_mean,
            "ic_std": self.ic_std,
            "ic_ir": self.ic_ir,
            "t_statistic": self.t_statistic,
            "p_value": self.p_value,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "is_significant": self.is_significant,
            "significance_level": self.significance_level
        }


@dataclass
class MonotonicityTest:
    """单调性检验结果"""
    is_monotonic: bool
    spearman_corr: float
    spearman_pvalue: float
    group_returns: List[float]
    trend_direction: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_monotonic": self.is_monotonic,
            "spearman_corr": self.spearman_corr,
            "spearman_pvalue": self.spearman_pvalue,
            "group_returns": self.group_returns,
            "trend_direction": self.trend_direction
        }


@dataclass
class BacktestCredibility:
    """回测可信度评估"""
    total_score: float
    lookahead_check: bool
    trading_constraints: bool
    transaction_costs: bool
    ic_significance: bool
    monotonicity: bool
    data_quality: float
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_score": self.total_score,
            "lookahead_check": self.lookahead_check,
            "trading_constraints": self.trading_constraints,
            "transaction_costs": self.transaction_costs,
            "ic_significance": self.ic_significance,
            "monotonicity": self.monotonicity,
            "data_quality": self.data_quality,
            "warnings": self.warnings
        }


@dataclass
class GroupBacktestResult:
    """分组回测结果"""
    group_id: int
    avg_return: float
    cumulative_return: float
    cumulative_return_net: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    sharpe_ratio_net: float = 0.0
    max_drawdown: float = 0.0
    stock_count: int = 0
    turnover: float = 0.0


@dataclass
class OOSValidationResult:
    """样本外验证结果"""
    train_ic: float
    test_ic: float
    ic_decay_rate: float
    train_sharpe: float
    test_sharpe: float
    train_return: float
    test_return: float
    is_valid: bool
    decay_warning: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "train_ic": self.train_ic,
            "test_ic": self.test_ic,
            "ic_decay_rate": self.ic_decay_rate,
            "train_sharpe": self.train_sharpe,
            "test_sharpe": self.test_sharpe,
            "train_return": self.train_return,
            "test_return": self.test_return,
            "is_valid": self.is_valid,
            "decay_warning": self.decay_warning
        }


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
    spread_return_net: float = 0.0
    ic_mean: float = 0.0
    ic_series: Optional[pd.Series] = None
    ic_statistics: Optional[ICStatistics] = None
    monotonicity: Optional[MonotonicityTest] = None
    credibility: Optional[BacktestCredibility] = None
    oos_validation: Optional[OOSValidationResult] = None
    trading_calendar_valid: bool = True
    non_trading_days_filtered: int = 0
    turnover_rate: float = 0.0
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class TradingConstraints:
    """
    交易约束处理器
    
    处理涨跌停、停牌等交易限制。
    """
    
    LIMIT_UP_THRESHOLD = 9.9
    LIMIT_DOWN_THRESHOLD = -9.9
    
    @staticmethod
    def filter_tradable_stocks(
        df: pd.DataFrame,
        date_col: str = "date",
        pct_chg_col: str = "pct_chg",
        volume_col: str = "volume"
    ) -> pd.DataFrame:
        """
        过滤可交易股票
        
        Args:
            df: 数据DataFrame
            date_col: 日期列名
            pct_chg_col: 涨跌幅列名
            volume_col: 成交量列名
            
        Returns:
            pd.DataFrame: 过滤后的DataFrame
        """
        df = df.copy()
        
        if pct_chg_col in df.columns:
            df['_limit_up'] = df[pct_chg_col] >= TradingConstraints.LIMIT_UP_THRESHOLD
            df['_limit_down'] = df[pct_chg_col] <= TradingConstraints.LIMIT_DOWN_THRESHOLD
            df['_tradable'] = ~(df['_limit_up'] | df['_limit_down'])
        else:
            df['_tradable'] = True
        
        if volume_col in df.columns:
            df['_suspended'] = df[volume_col] == 0
            df['_tradable'] = df['_tradable'] & (~df['_suspended'])
        
        return df
    
    @staticmethod
    def apply_trading_constraints(
        factor_df: pd.DataFrame,
        price_df: Optional[pd.DataFrame] = None,
        date_col: str = "date",
        stock_col: str = "stock_code",
        pct_chg_col: str = "pct_chg",
        volume_col: str = "volume"
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        应用交易约束
        
        Args:
            factor_df: 因子数据
            price_df: 价格数据（用于涨跌停判断）
            date_col: 日期列名
            stock_col: 股票代码列名
            pct_chg_col: 涨跌幅列名
            volume_col: 成交量列名
            
        Returns:
            Tuple[pd.DataFrame, Dict]: 过滤后的因子数据和统计信息
        """
        stats_info = {
            "original_count": len(factor_df),
            "filtered_count": len(factor_df),
            "limit_up_count": 0,
            "limit_down_count": 0,
            "suspended_count": 0
        }
        
        if price_df is None or pct_chg_col not in price_df.columns:
            return factor_df, stats_info
        
        merged = factor_df.merge(
            price_df[[date_col, stock_col, pct_chg_col, volume_col]] if volume_col in price_df.columns 
            else price_df[[date_col, stock_col, pct_chg_col]],
            on=[date_col, stock_col],
            how='left'
        )
        
        if pct_chg_col in merged.columns:
            limit_up_mask = merged[pct_chg_col] >= TradingConstraints.LIMIT_UP_THRESHOLD
            limit_down_mask = merged[pct_chg_col] <= TradingConstraints.LIMIT_DOWN_THRESHOLD
            stats_info["limit_up_count"] = limit_up_mask.sum()
            stats_info["limit_down_count"] = limit_down_mask.sum()
            
            tradable_mask = ~(limit_up_mask | limit_down_mask)
        else:
            tradable_mask = pd.Series([True] * len(merged), index=merged.index)
        
        if volume_col in merged.columns:
            suspended_mask = merged[volume_col] == 0
            stats_info["suspended_count"] = suspended_mask.sum()
            tradable_mask = tradable_mask & (~suspended_mask)
        
        filtered_df = factor_df[tradable_mask.values].copy()
        stats_info["filtered_count"] = len(filtered_df)
        
        return filtered_df, stats_info


class ICSignificanceTester:
    """
    IC显著性检验器
    """
    
    @staticmethod
    def test(
        ic_series: pd.Series,
        alpha: float = 0.05
    ) -> ICStatistics:
        """
        执行IC显著性检验
        
        Args:
            ic_series: IC序列
            alpha: 显著性水平
            
        Returns:
            ICStatistics: 检验结果
        """
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        n = len(ic_series)
        
        if ic_std == 0 or n == 0:
            return ICStatistics(
                ic_mean=ic_mean,
                ic_std=ic_std,
                ic_ir=0.0,
                t_statistic=0.0,
                p_value=1.0,
                ci_lower=ic_mean,
                ci_upper=ic_mean,
                is_significant=False,
                significance_level="insufficient_data"
            )
        
        ic_ir = ic_mean / ic_std
        
        t_statistic = ic_mean / (ic_std / np.sqrt(n))
        
        p_value = 2 * (1 - stats.t.cdf(abs(t_statistic), df=n-1))
        
        se = ic_std / np.sqrt(n)
        ci_lower = ic_mean - stats.t.ppf(1 - alpha/2, df=n-1) * se
        ci_upper = ic_mean + stats.t.ppf(1 - alpha/2, df=n-1) * se
        
        is_significant = p_value < alpha
        
        if p_value < 0.01:
            significance_level = "highly_significant"
        elif p_value < 0.05:
            significance_level = "significant"
        elif p_value < 0.1:
            significance_level = "marginally_significant"
        else:
            significance_level = "not_significant"
        
        return ICStatistics(
            ic_mean=ic_mean,
            ic_std=ic_std,
            ic_ir=ic_ir,
            t_statistic=t_statistic,
            p_value=p_value,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            is_significant=is_significant,
            significance_level=significance_level
        )


class MonotonicityAnalyzer:
    """
    单调性分析器
    """
    
    @staticmethod
    def test(
        group_results: List[GroupBacktestResult]
    ) -> Optional[MonotonicityTest]:
        """
        测试分组收益单调性
        
        Args:
            group_results: 分组结果列表
            
        Returns:
            MonotonicityTest: 检验结果
        """
        if len(group_results) < 2:
            return None
        
        sorted_results = sorted(group_results, key=lambda x: x.group_id)
        group_returns = [gr.cumulative_return for gr in sorted_results]
        group_ids = list(range(len(group_returns)))
        
        if len(set(group_returns)) < 2:
            return MonotonicityTest(
                is_monotonic=True,
                spearman_corr=1.0,
                spearman_pvalue=0.0,
                group_returns=group_returns,
                trend_direction="flat"
            )
        
        corr, pvalue = stats.spearmanr(group_ids, group_returns)
        
        is_monotonic = abs(corr) > 0.7 and pvalue < 0.1
        
        if corr > 0.5:
            trend_direction = "increasing"
        elif corr < -0.5:
            trend_direction = "decreasing"
        else:
            trend_direction = "non_monotonic"
        
        return MonotonicityTest(
            is_monotonic=is_monotonic,
            spearman_corr=corr,
            spearman_pvalue=pvalue,
            group_returns=group_returns,
            trend_direction=trend_direction
        )


class OOSValidator:
    """
    样本外验证器
    
    执行训练集/测试集分割，验证因子稳健性。
    """
    
    @staticmethod
    def validate(
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        backtester: 'FactorBacktester',
        train_ratio: float = 0.7,
        date_col: str = "date",
        **backtest_kwargs
    ) -> Optional[OOSValidationResult]:
        """
        执行样本外验证
        
        Args:
            factor_df: 因子数据
            return_df: 收益数据
            backtester: 回测器实例
            train_ratio: 训练集比例
            date_col: 日期列名
            **backtest_kwargs: 回测参数
            
        Returns:
            OOSValidationResult: 验证结果
        """
        dates = sorted(factor_df[date_col].unique())
        if len(dates) < 20:
            return None
        
        split_idx = int(len(dates) * train_ratio)
        train_dates = set(dates[:split_idx])
        test_dates = set(dates[split_idx:])
        
        train_factor = factor_df[factor_df[date_col].isin(train_dates)]
        test_factor = factor_df[factor_df[date_col].isin(test_dates)]
        train_return = return_df[return_df[date_col].isin(train_dates)]
        test_return = return_df[return_df[date_col].isin(test_dates)]
        
        train_result = backtester._run_backtest(
            factor_df=train_factor,
            return_df=train_return,
            **backtest_kwargs
        )
        
        test_result = backtester._run_backtest(
            factor_df=test_factor,
            return_df=test_return,
            **backtest_kwargs
        )
        
        if not train_result['success'] or not test_result['success']:
            return None
        
        train_ic = train_result['ic_mean']
        test_ic = test_result['ic_mean']
        
        if abs(train_ic) > 0.0001:
            ic_decay_rate = (train_ic - test_ic) / abs(train_ic)
        else:
            ic_decay_rate = 0.0
        
        train_sharpe = train_result['group_results'][-1]['sharpe_ratio_net'] if train_result['group_results'] else 0.0
        test_sharpe = test_result['group_results'][-1]['sharpe_ratio_net'] if test_result['group_results'] else 0.0
        
        train_return_val = train_result['group_results'][-1]['cumulative_return_net'] if train_result['group_results'] else 0.0
        test_return_val = test_result['group_results'][-1]['cumulative_return_net'] if test_result['group_results'] else 0.0
        
        is_valid = ic_decay_rate < 0.5 and test_ic * train_ic > 0
        
        decay_warning = ""
        if ic_decay_rate > 0.5:
            decay_warning = f"IC衰减率过高: {ic_decay_rate:.1%}"
        elif test_ic * train_ic < 0:
            decay_warning = "训练集和测试集IC方向相反"
        elif abs(test_ic) < abs(train_ic) * 0.3:
            decay_warning = "测试集IC显著低于训练集"
        
        return OOSValidationResult(
            train_ic=train_ic,
            test_ic=test_ic,
            ic_decay_rate=ic_decay_rate,
            train_sharpe=train_sharpe,
            test_sharpe=test_sharpe,
            train_return=train_return_val,
            test_return=test_return_val,
            is_valid=is_valid,
            decay_warning=decay_warning
        )


class TradingCalendarValidator:
    """
    交易日历校验器
    
    校验数据日期是否为交易日。
    """
    
    @staticmethod
    def validate_dates(
        df: pd.DataFrame,
        date_col: str = "date"
    ) -> Tuple[pd.DataFrame, int, List[str]]:
        """
        校验并过滤非交易日
        
        Args:
            df: 数据DataFrame
            date_col: 日期列名
            
        Returns:
            Tuple[pd.DataFrame, int, List[str]]: 过滤后的数据、过滤数量、警告列表
        """
        warnings = []
        
        try:
            from ..backtest.trading_calendar import get_trading_calendar
            calendar = get_trading_calendar()
            
            dates = df[date_col].unique()
            non_trading_dates = []
            
            for d in dates:
                if hasattr(d, 'date'):
                    d = d.date()
                elif isinstance(d, str):
                    from datetime import datetime
                    d = datetime.strptime(d, "%Y-%m-%d").date()
                
                if not calendar.is_trading_day(d):
                    non_trading_dates.append(d)
            
            if non_trading_dates:
                filtered_df = df[~df[date_col].isin(non_trading_dates)].copy()
                filtered_count = len(df) - len(filtered_df)
                warnings.append(f"过滤非交易日数据: {len(non_trading_dates)}个日期, {filtered_count}条记录")
                return filtered_df, filtered_count, warnings
            
            return df, 0, warnings
            
        except Exception as e:
            warnings.append(f"交易日历校验失败: {e}")
            return df, 0, warnings


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
            
            if valid_mask.sum() < n_groups:
                group.loc[valid_mask, 'factor_group'] = 0
                return group
            
            try:
                group.loc[valid_mask, 'factor_group'] = pd.qcut(
                    group.loc[valid_mask, factor_col],
                    n_groups,
                    labels=False,
                    duplicates='drop'
                )
            except ValueError:
                group.loc[valid_mask, 'factor_group'] = 0
            
            return group
        
        factor_df = factor_df.groupby(date_col, group_keys=False).apply(assign_group)
        
        return factor_df


class PortfolioSimulator:
    """
    组合模拟器
    
    模拟因子组合的表现，包含交易成本。
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
        stock_col: str = "stock_code",
        transaction_costs: Optional[TransactionCosts] = None
    ) -> Tuple[pd.Series, float, float, float]:
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
            transaction_costs: 交易成本配置
            
        Returns:
            Tuple[pd.Series, float, float, float]: 收益序列、胜率、换手率、年化成本
        """
        costs = transaction_costs or TransactionCosts()
        
        group_df = factor_df[factor_df['factor_group'] == group_id].copy()
        
        merged = pd.merge(
            group_df[[date_col, stock_col]],
            return_df[[date_col, stock_col, return_col]],
            on=[date_col, stock_col],
            how="inner"
        )
        
        if merged.empty:
            return pd.Series(), 0.0, 0.0, 0.0
        
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
        
        n_periods = len(daily_returns)
        periods_per_year = 252
        rebalance_per_year = periods_per_year / holding_period
        annual_turnover = avg_turnover * rebalance_per_year
        annual_cost = annual_turnover * costs.round_trip_cost
        
        return daily_returns, win_rate, avg_turnover, annual_cost
    
    @staticmethod
    def calculate_performance_metrics(
        returns: pd.Series,
        annual_cost: float = 0.0
    ) -> Dict[str, float]:
        """
        计算绩效指标
        
        Args:
            returns: 收益序列
            annual_cost: 年化交易成本
            
        Returns:
            Dict[str, float]: 绩效指标
        """
        if returns.empty:
            return {
                "cumulative_return": 0.0,
                "cumulative_return_net": 0.0,
                "annual_return": 0.0,
                "annual_return_net": 0.0,
                "sharpe_ratio": 0.0,
                "sharpe_ratio_net": 0.0,
                "max_drawdown": 0.0,
                "volatility": 0.0
            }
        
        cumulative_return = (1 + returns).prod() - 1
        
        n_periods = len(returns)
        annual_return = (1 + cumulative_return) ** (252 / n_periods) - 1
        
        annual_return_net = annual_return - annual_cost
        cumulative_return_net = (1 + annual_return_net) ** (n_periods / 252) - 1
        
        volatility = returns.std() * np.sqrt(252)
        
        risk_free_rate = 0.03
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0.0
        sharpe_ratio_net = (annual_return_net - risk_free_rate) / volatility if volatility > 0 else 0.0
        
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            "cumulative_return": cumulative_return,
            "cumulative_return_net": cumulative_return_net,
            "annual_return": annual_return,
            "annual_return_net": annual_return_net,
            "sharpe_ratio": sharpe_ratio,
            "sharpe_ratio_net": sharpe_ratio_net,
            "max_drawdown": max_drawdown,
            "volatility": volatility
        }


class CredibilityAssessor:
    """
    回测可信度评估器
    """
    
    @staticmethod
    def assess(
        lookahead_violations: int,
        trading_constraints_applied: bool,
        transaction_costs_applied: bool,
        ic_statistics: Optional[ICStatistics],
        monotonicity: Optional[MonotonicityTest],
        data_quality_score: float,
        warnings: List[str]
    ) -> BacktestCredibility:
        """
        评估回测可信度
        
        Args:
            lookahead_violations: 未来函数违规次数
            trading_constraints_applied: 是否应用交易约束
            transaction_costs_applied: 是否应用交易成本
            ic_statistics: IC统计检验结果
            monotonicity: 单调性检验结果
            data_quality_score: 数据质量评分
            warnings: 警告列表
            
        Returns:
            BacktestCredibility: 可信度评估结果
        """
        score = 0.0
        
        lookahead_check = lookahead_violations == 0
        if lookahead_check:
            score += 25
        else:
            warnings.append(f"检测到 {lookahead_violations} 个未来函数违规")
        
        trading_constraints = trading_constraints_applied
        if trading_constraints:
            score += 15
        else:
            warnings.append("未应用交易约束（涨跌停/停牌过滤）")
        
        transaction_costs = transaction_costs_applied
        if transaction_costs:
            score += 20
        else:
            warnings.append("未应用交易成本模型")
        
        ic_significance = ic_statistics is not None and ic_statistics.is_significant
        if ic_significance:
            score += 15
        elif ic_statistics is not None:
            warnings.append(f"IC不显著 (p={ic_statistics.p_value:.4f})")
        
        monotonicity_check = monotonicity is not None and monotonicity.is_monotonic
        if monotonicity_check:
            score += 10
        elif monotonicity is not None:
            warnings.append(f"分组收益单调性不足 (corr={monotonicity.spearman_corr:.2f})")
        
        score += data_quality_score * 15 / 100
        
        return BacktestCredibility(
            total_score=min(score, 100),
            lookahead_check=lookahead_check,
            trading_constraints=trading_constraints,
            transaction_costs=transaction_costs,
            ic_significance=ic_significance,
            monotonicity=monotonicity_check,
            data_quality=data_quality_score,
            warnings=warnings
        )


class FactorBacktester:
    """
    因子回测器
    
    多维度回测因子有效性，集成未来函数检测、交易成本、交易约束等。
    支持多频率回测（日线/小时线）和增强版日线回测。
    """
    
    def __init__(
        self,
        transaction_costs: Optional[TransactionCosts] = None,
        enable_lookahead_guard: bool = True,
        strict_lookahead_check: bool = True,
        apply_trading_constraints: bool = True,
        validate_trading_calendar: bool = True,
        enable_oos_validation: bool = False,
        frequency: BacktestFrequency = BacktestFrequency.DAILY,
        enhanced_config: Optional[EnhancedDailyConfig] = None,
        hourly_config: Optional[HourlyBacktestConfig] = None,
        use_enhanced_daily: bool = True
    ):
        """
        初始化因子回测器
        
        Args:
            transaction_costs: 交易成本配置
            enable_lookahead_guard: 是否启用未来函数检测
            strict_lookahead_check: 是否严格模式
            apply_trading_constraints: 是否应用交易约束
            validate_trading_calendar: 是否校验交易日历
            enable_oos_validation: 是否启用样本外验证
            frequency: 回测频率
            enhanced_config: 增强版日线配置
            hourly_config: 小时线配置
            use_enhanced_daily: 是否使用增强版日线回测
        """
        self._registry = get_factor_registry()
        self._transaction_costs = transaction_costs or TransactionCosts()
        self._enable_lookahead_guard = enable_lookahead_guard
        self._strict_lookahead_check = strict_lookahead_check
        self._apply_trading_constraints = apply_trading_constraints
        self._validate_trading_calendar = validate_trading_calendar
        self._enable_oos_validation = enable_oos_validation
        self._lookahead_guard = LookAheadGuard(
            strict_mode=strict_lookahead_check,
            raise_on_violation=False
        ) if enable_lookahead_guard else None
        
        self._frequency = frequency
        self._use_enhanced_daily = use_enhanced_daily
        self._enhanced_config = enhanced_config or EnhancedDailyConfig()
        self._hourly_config = hourly_config or HourlyBacktestConfig()
        
        if frequency != BacktestFrequency.DAILY:
            self._hourly_backtester = get_hourly_backtester(
                frequency=frequency.value,
                trading_hours_only=hourly_config.trading_hours_only if hourly_config else True
            )
        else:
            self._hourly_backtester = None
        
        if use_enhanced_daily:
            self._enhanced_backtest = EnhancedDailyBacktest(self._enhanced_config)
        else:
            self._enhanced_backtest = None
    
    def _validate_data(
        self,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> Tuple[bool, float, List[str]]:
        """
        验证数据质量
        
        Args:
            factor_df: 因子数据
            return_df: 收益数据
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            Tuple[bool, float, List[str]]: 是否通过、质量评分、警告列表
        """
        warnings = []
        score = 100.0
        
        required_cols = [date_col, stock_col]
        for col in required_cols:
            if col not in factor_df.columns:
                warnings.append(f"因子数据缺少列: {col}")
                score -= 20
        
        if 'factor_value' not in factor_df.columns:
            warnings.append("因子数据缺少 factor_value 列")
            score -= 20
        
        if 'forward_return' not in return_df.columns:
            warnings.append("收益数据缺少 forward_return 列")
            score -= 20
        
        factor_nan_ratio = factor_df.isna().sum().sum() / (len(factor_df) * len(factor_df.columns))
        if factor_nan_ratio > 0.1:
            warnings.append(f"因子数据缺失率过高: {factor_nan_ratio:.2%}")
            score -= 10
        
        return len(warnings) == 0, max(0, score), warnings
    
    def backtest(
        self,
        factor_id: str,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        price_df: Optional[pd.DataFrame] = None,
        index_df: Optional[pd.DataFrame] = None,
        n_groups: int = 5,
        holding_period: HoldingPeriod = HoldingPeriod.FIVE_DAYS,
        market_type: MarketType = MarketType.ALL,
        factor_col: str = "factor_value",
        return_col: str = "forward_return",
        date_col: str = "date",
        stock_col: str = "stock_code",
        stock_pool: str = "全市场",
        record_score: bool = True,
        enable_oos_validation: Optional[bool] = None,
        train_ratio: float = 0.7
    ) -> FactorBacktestResult:
        """
        回测因子
        
        Args:
            factor_id: 因子ID
            factor_df: 因子数据
            return_df: 收益数据
            price_df: 价格数据（用于涨跌停判断）
            index_df: 指数数据（用于市场分类）
            n_groups: 分组数量
            holding_period: 持仓周期
            market_type: 市场类型
            factor_col: 因子值列名
            return_col: 收益列名
            date_col: 日期列名
            stock_col: 股票代码列名
            stock_pool: 股票池
            record_score: 是否记录评分
            enable_oos_validation: 是否启用样本外验证（None则使用实例配置）
            train_ratio: 训练集比例
            
        Returns:
            FactorBacktestResult: 回测结果
        """
        warnings_list = []
        lookahead_violations = 0
        trading_constraints_applied = False
        transaction_costs_applied = True
        trading_calendar_valid = True
        non_trading_days_filtered = 0
        
        try:
            data_valid, data_quality_score, data_warnings = self._validate_data(
                factor_df, return_df, date_col, stock_col
            )
            warnings_list.extend(data_warnings)
            
            if not data_valid:
                return FactorBacktestResult(
                    factor_id=factor_id,
                    success=False,
                    market_type=market_type,
                    holding_period=holding_period,
                    n_groups=n_groups,
                    error_message="数据验证失败: " + "; ".join(data_warnings)
                )
            
            if self._validate_trading_calendar:
                factor_df, ntd_filtered, calendar_warnings = TradingCalendarValidator.validate_dates(
                    factor_df, date_col
                )
                return_df, ntd_filtered_r, _ = TradingCalendarValidator.validate_dates(
                    return_df, date_col
                )
                non_trading_days_filtered = ntd_filtered + ntd_filtered_r
                warnings_list.extend(calendar_warnings)
                if non_trading_days_filtered > 0:
                    trading_calendar_valid = True
            
            if self._lookahead_guard:
                dates = sorted(factor_df[date_col].unique())
                for current_date in dates:
                    self._lookahead_guard.set_bar_time(current_date)
                    
                    current_factor = factor_df[factor_df[date_col] == current_date]
                    future_data = factor_df[factor_df[date_col] > current_date]
                    
                    if len(future_data) > 0:
                        lookahead_violations += 1
                
                if self._lookahead_guard.has_violations():
                    lookahead_violations += len(self._lookahead_guard.get_violations())
            
            if market_type != MarketType.ALL and index_df is not None:
                market_df = MarketClassifier.get_market_periods(index_df)
                market_dates = market_df[market_df['market_type'] == market_type][date_col].tolist()
                
                factor_df = factor_df[factor_df[date_col].isin(market_dates)]
                return_df = return_df[return_df[date_col].isin(market_dates)]
            
            if self._apply_trading_constraints and price_df is not None:
                factor_df, constraint_stats = TradingConstraints.apply_trading_constraints(
                    factor_df, price_df, date_col, stock_col
                )
                trading_constraints_applied = True
                
                if constraint_stats["limit_up_count"] > 0 or constraint_stats["limit_down_count"] > 0:
                    warnings_list.append(
                        f"过滤涨跌停: {constraint_stats['limit_up_count']}个涨停, "
                        f"{constraint_stats['limit_down_count']}个跌停"
                    )
            
            grouped_factor = GroupConstructor.construct_groups(
                factor_df, n_groups, factor_col, date_col, stock_col
            )
            
            group_results = []
            group_returns = {}
            
            for group_id in range(n_groups):
                returns, win_rate, turnover, annual_cost = PortfolioSimulator.simulate_group_portfolio(
                    grouped_factor, return_df, group_id,
                    holding_period.value, factor_col, return_col,
                    date_col, stock_col, self._transaction_costs
                )
                
                if returns.empty:
                    continue
                
                metrics = PortfolioSimulator.calculate_performance_metrics(returns, annual_cost)
                
                group_result = GroupBacktestResult(
                    group_id=group_id,
                    avg_return=returns.mean(),
                    cumulative_return=metrics["cumulative_return"],
                    cumulative_return_net=metrics["cumulative_return_net"],
                    win_rate=win_rate,
                    sharpe_ratio=metrics["sharpe_ratio"],
                    sharpe_ratio_net=metrics["sharpe_ratio_net"],
                    max_drawdown=metrics["max_drawdown"],
                    stock_count=grouped_factor[grouped_factor['factor_group'] == group_id][stock_col].nunique(),
                    turnover=turnover
                )
                
                group_results.append(group_result)
                group_returns[group_id] = returns
            
            spread_return = 0.0
            spread_return_net = 0.0
            if len(group_results) >= 2:
                top_group = max(group_results, key=lambda x: x.group_id)
                bottom_group = min(group_results, key=lambda x: x.group_id)
                spread_return = top_group.cumulative_return - bottom_group.cumulative_return
                spread_return_net = top_group.cumulative_return_net - bottom_group.cumulative_return_net
            
            ic_series = ICAnalyzer.calculate_ic_series(
                factor_df, return_df,
                factor_col, return_col,
                date_col, stock_col
            )
            ic_mean = ic_series.mean()
            
            ic_statistics = ICSignificanceTester.test(ic_series)
            
            monotonicity = MonotonicityAnalyzer.test(group_results)
            
            avg_turnover = np.mean([gr.turnover for gr in group_results]) if group_results else 0.0
            
            credibility = CredibilityAssessor.assess(
                lookahead_violations=lookahead_violations,
                trading_constraints_applied=trading_constraints_applied,
                transaction_costs_applied=transaction_costs_applied,
                ic_statistics=ic_statistics,
                monotonicity=monotonicity,
                data_quality_score=data_quality_score,
                warnings=warnings_list
            )
            
            oos_validation = None
            if enable_oos_validation or (enable_oos_validation is None and self._enable_oos_validation):
                oos_validation = OOSValidator.validate(
                    factor_df=factor_df,
                    return_df=return_df,
                    backtester=self,
                    train_ratio=train_ratio,
                    date_col=date_col,
                    n_groups=n_groups,
                    holding_period=holding_period,
                    market_type=market_type,
                    factor_col=factor_col,
                    return_col=return_col,
                    stock_col=stock_col
                )
            
            result = FactorBacktestResult(
                factor_id=factor_id,
                success=True,
                market_type=market_type,
                holding_period=holding_period,
                n_groups=n_groups,
                group_results=group_results,
                spread_return=spread_return,
                spread_return_net=spread_return_net,
                ic_mean=ic_mean,
                ic_series=ic_series,
                ic_statistics=ic_statistics,
                monotonicity=monotonicity,
                credibility=credibility,
                oos_validation=oos_validation,
                trading_calendar_valid=trading_calendar_valid,
                non_trading_days_filtered=non_trading_days_filtered,
                turnover_rate=avg_turnover,
                details={
                    "group_returns": {k: v.to_dict() for k, v in group_returns.items()},
                    "total_periods": len(ic_series),
                    "transaction_costs": {
                        "commission": self._transaction_costs.commission,
                        "stamp_duty": self._transaction_costs.stamp_duty,
                        "slippage": self._transaction_costs.slippage,
                        "round_trip_cost": self._transaction_costs.round_trip_cost
                    }
                }
            )
            
            backtest_result = BacktestResult(
                annual_return=group_results[-1].cumulative_return_net if group_results else 0.0,
                sharpe_ratio=group_results[-1].sharpe_ratio_net if group_results else 0.0,
                max_drawdown=group_results[-1].max_drawdown if group_results else 0.0,
                win_rate=group_results[-1].win_rate if group_results else 0.0,
                ic=ic_mean
            )
            
            self._registry.update_backtest_result(
                factor_id, 
                market_type.value, 
                backtest_result
            )
            
            if record_score:
                self._record_score(
                    factor_id=factor_id,
                    stock_pool=stock_pool,
                    result=result,
                    ic_series=ic_series
                )
            
            return result
            
        except Exception as e:
            logger.error(f"回测失败: {e}")
            return FactorBacktestResult(
                factor_id=factor_id,
                success=False,
                market_type=market_type,
                holding_period=holding_period,
                n_groups=n_groups,
                error_message=str(e)
            )
    
    def _record_score(
        self,
        factor_id: str,
        stock_pool: str,
        result: FactorBacktestResult,
        ic_series: pd.Series
    ):
        """
        记录评分快照
        
        Args:
            factor_id: 因子ID
            stock_pool: 股票池
            result: 回测结果
            ic_series: IC序列
        """
        try:
            from .scorer import get_factor_scorer
            from .registry import FactorQualityMetrics
            scorer = get_factor_scorer()
            
            ic_std = ic_series.std() if ic_series is not None and len(ic_series) > 0 else 0
            ic_ir = result.ic_mean / ic_std if ic_std > 0 else 0
            ic_t = result.ic_mean / ic_std if ic_std > 0 else 0
            
            win_rate = result.group_results[-1].win_rate if result.group_results else 0.0
            turnover = result.turnover_rate if hasattr(result, 'turnover_rate') else 0.0
            
            annual_spread = result.spread_return if hasattr(result, 'spread_return') else 0.0
            annual_spread_net = result.spread_return_net if hasattr(result, 'spread_return_net') else 0.0
            
            min_quantile_return = result.group_results[0].cumulative_return if result.group_results else 0.0
            max_quantile_return = result.group_results[-1].cumulative_return if result.group_results else 0.0
            quantile_spread = max_quantile_return - min_quantile_return
            
            metrics = FactorQualityMetrics(
                ic_mean=result.ic_mean,
                ic_std=ic_std,
                ir=ic_ir,
                ic_t=ic_t,
                win_rate=win_rate,
                annual_spread=annual_spread,
                annual_spread_net=annual_spread_net,
                turnover=turnover,
                min_quantile_return=min_quantile_return,
                max_quantile_return=max_quantile_return,
                quantile_spread=quantile_spread
            )
            
            backtest_dict = {
                "annual_return": result.group_results[-1].cumulative_return_net if result.group_results else 0.0,
                "annual_return_gross": result.group_results[-1].cumulative_return if result.group_results else 0.0,
                "sharpe_ratio": result.group_results[-1].sharpe_ratio_net if result.group_results else 0.0,
                "sharpe_ratio_gross": result.group_results[-1].sharpe_ratio if result.group_results else 0.0,
                "max_drawdown": result.group_results[-1].max_drawdown if result.group_results else 0.0,
                "win_rate": result.group_results[-1].win_rate if result.group_results else 0.0,
                "turnover": result.turnover_rate,
                "spread_return": result.spread_return,
                "spread_return_net": result.spread_return_net,
                "period": f"{result.market_type.value}_ng{result.n_groups}_hp{result.holding_period.value}",
                "n_groups": result.n_groups,
                "holding_period": result.holding_period.value,
                "market_type": result.market_type.value
            }
            
            if result.ic_statistics:
                backtest_dict["ic_statistics"] = result.ic_statistics.to_dict()
            
            if result.monotonicity:
                backtest_dict["monotonicity"] = result.monotonicity.to_dict()
            
            if result.credibility:
                backtest_dict["credibility"] = result.credibility.to_dict()
            
            if result.oos_validation:
                backtest_dict["oos_validation"] = result.oos_validation.to_dict()
            
            backtest_dict["trading_calendar_valid"] = result.trading_calendar_valid
            backtest_dict["non_trading_days_filtered"] = result.non_trading_days_filtered
            
            scorer.record_score_snapshot(
                factor_id=factor_id,
                stock_pool=stock_pool,
                backtest_result=backtest_dict,
                quality_metrics=metrics
            )
            
            self._update_validation_status(factor_id, result)
        except Exception as e:
            logger.warning(f"记录评分失败: {e}")
    
    def _update_validation_status(
        self,
        factor_id: str,
        result: FactorBacktestResult
    ):
        """
        更新因子验证状态
        
        Args:
            factor_id: 因子ID
            result: 回测结果
        """
        try:
            from .registry import ValidationStatus
            
            if not result.success:
                return
            
            credibility_score = result.credibility.total_score if result.credibility else 0
            oos_valid = result.oos_validation.is_valid if result.oos_validation else False
            
            if credibility_score >= 70 and oos_valid:
                validation_status = ValidationStatus.VALIDATED_OOS
            elif credibility_score >= 70:
                validation_status = ValidationStatus.VALIDATED
            elif credibility_score >= 50:
                validation_status = ValidationStatus.VALIDATED
            else:
                validation_status = ValidationStatus.FAILED
            
            self._registry.update_validation_status(
                factor_id=factor_id,
                validation_status=validation_status,
                credibility_score=credibility_score,
                oos_valid=oos_valid
            )
            
        except Exception as e:
            logger.warning(f"更新验证状态失败: {e}")
    
    def _run_backtest(
        self,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        price_df: Optional[pd.DataFrame] = None,
        n_groups: int = 5,
        holding_period: HoldingPeriod = HoldingPeriod.FIVE_DAYS,
        market_type: MarketType = MarketType.ALL,
        factor_col: str = "factor_value",
        return_col: str = "forward_return",
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> Dict[str, Any]:
        """
        内部回测方法（用于样本外验证）
        
        Args:
            factor_df: 因子数据
            return_df: 收益数据
            price_df: 价格数据
            n_groups: 分组数量
            holding_period: 持仓周期
            market_type: 市场类型
            factor_col: 因子值列名
            return_col: 收益列名
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            Dict[str, Any]: 回测结果字典
        """
        try:
            grouped_factor = GroupConstructor.construct_groups(
                factor_df, n_groups, factor_col, date_col, stock_col
            )
            
            group_results = []
            
            for group_id in range(n_groups):
                returns, win_rate, turnover, annual_cost = PortfolioSimulator.simulate_group_portfolio(
                    grouped_factor, return_df, group_id,
                    holding_period.value, factor_col, return_col,
                    date_col, stock_col, self._transaction_costs
                )
                
                if returns.empty:
                    continue
                
                metrics = PortfolioSimulator.calculate_performance_metrics(returns, annual_cost)
                
                group_results.append({
                    'group_id': group_id,
                    'cumulative_return': metrics["cumulative_return"],
                    'cumulative_return_net': metrics["cumulative_return_net"],
                    'sharpe_ratio': metrics["sharpe_ratio"],
                    'sharpe_ratio_net': metrics["sharpe_ratio_net"],
                    'max_drawdown': metrics["max_drawdown"],
                    'win_rate': win_rate,
                    'turnover': turnover
                })
            
            ic_series = ICAnalyzer.calculate_ic_series(
                factor_df, return_df,
                factor_col, return_col,
                date_col, stock_col
            )
            ic_mean = ic_series.mean()
            
            return {
                'success': True,
                'ic_mean': ic_mean,
                'group_results': group_results
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'ic_mean': 0.0,
                'group_results': []
            }
    
    def multi_dimension_backtest(
        self,
        factor_id: str,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        price_df: Optional[pd.DataFrame] = None,
        index_df: Optional[pd.DataFrame] = None,
        n_groups_list: List[int] = None,
        holding_periods: List[HoldingPeriod] = None,
        market_types: List[MarketType] = None,
        stock_pool: str = "全市场",
        force_oos_validation: bool = True,
        train_ratio: float = 0.7,
        robustness_check: bool = True
    ) -> Dict[str, FactorBacktestResult]:
        """
        多维度回测
        
        Args:
            factor_id: 因子ID
            factor_df: 因子数据
            return_df: 收益数据
            price_df: 价格数据
            index_df: 指数数据
            n_groups_list: 分组数量列表
            holding_periods: 持仓周期列表
            market_types: 市场类型列表
            stock_pool: 股票池
            force_oos_validation: 是否强制样本外验证
            train_ratio: 训练集比例
            robustness_check: 是否进行稳健性检验
            
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
                        price_df=price_df,
                        index_df=index_df,
                        n_groups=n_groups,
                        holding_period=holding_period,
                        market_type=market_type,
                        stock_pool=stock_pool,
                        enable_oos_validation=force_oos_validation,
                        train_ratio=train_ratio
                    )
        
        if robustness_check and results:
            robustness_report = self._check_robustness(results)
            for key, result in results.items():
                if result.details is None:
                    result.details = {}
                result.details["robustness_check"] = robustness_report
        
        return results
    
    def _check_robustness(
        self,
        results: Dict[str, FactorBacktestResult]
    ) -> Dict[str, Any]:
        """
        稳健性检验
        
        Args:
            results: 多维度回测结果
            
        Returns:
            Dict[str, Any]: 稳健性报告
        """
        successful_results = {k: v for k, v in results.items() if v.success}
        
        if not successful_results:
            return {"is_robust": False, "reason": "所有回测均失败"}
        
        ic_values = [v.ic_mean for v in successful_results.values()]
        sharpe_values = [
            v.group_results[-1].sharpe_ratio_net 
            for v in successful_results.values() 
            if v.group_results
        ]
        
        ic_consistent = all(ic * ic_values[0] > 0 for ic in ic_values) if ic_values else False
        ic_std = np.std(ic_values) if len(ic_values) > 1 else 0
        ic_cv = ic_std / abs(np.mean(ic_values)) if np.mean(ic_values) != 0 else float('inf')
        
        sharpe_consistent = all(s > 0 for s in sharpe_values) if sharpe_values else False
        
        oos_valid_count = sum(
            1 for v in successful_results.values() 
            if v.oos_validation and v.oos_validation.is_valid
        )
        oos_total = sum(
            1 for v in successful_results.values() 
            if v.oos_validation is not None
        )
        oos_pass_rate = oos_valid_count / oos_total if oos_total > 0 else 1.0
        
        credibility_scores = [
            v.credibility.total_score 
            for v in successful_results.values() 
            if v.credibility
        ]
        avg_credibility = np.mean(credibility_scores) if credibility_scores else 0
        
        is_robust = (
            ic_consistent and
            ic_cv < 0.5 and
            sharpe_consistent and
            oos_pass_rate >= 0.5 and
            avg_credibility >= 50
        )
        
        warnings = []
        if not ic_consistent:
            warnings.append("IC方向不一致")
        if ic_cv >= 0.5:
            warnings.append(f"IC波动过大 (CV={ic_cv:.2f})")
        if not sharpe_consistent:
            warnings.append("夏普比率不稳定")
        if oos_pass_rate < 0.5:
            warnings.append(f"样本外验证通过率低 ({oos_pass_rate:.0%})")
        if avg_credibility < 50:
            warnings.append(f"平均可信度低 ({avg_credibility:.0f})")
        
        return {
            "is_robust": is_robust,
            "ic_consistent": ic_consistent,
            "ic_cv": ic_cv,
            "sharpe_consistent": sharpe_consistent,
            "oos_pass_rate": oos_pass_rate,
            "avg_credibility": avg_credibility,
            "warnings": warnings
        }
    
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
            "=" * 60,
            f"市场类型: {result.market_type.value}",
            f"持仓周期: {result.holding_period.value}天",
            f"分组数量: {result.n_groups}",
            "",
            "分组表现:",
            "-" * 60,
        ]
        
        for gr in result.group_results:
            lines.extend([
                f"  第{gr.group_id + 1}组:",
                f"    累计收益(毛): {gr.cumulative_return:.2%}",
                f"    累计收益(净): {gr.cumulative_return_net:.2%}",
                f"    夏普比率(毛): {gr.sharpe_ratio:.2f}",
                f"    夏普比率(净): {gr.sharpe_ratio_net:.2f}",
                f"    最大回撤: {gr.max_drawdown:.2%}",
                f"    胜率: {gr.win_rate:.2%}",
                f"    换手率: {gr.turnover:.2%}",
                f"    股票数: {gr.stock_count}",
            ])
        
        lines.extend([
            "",
            "综合指标:",
            "-" * 60,
            f"  多空收益差(毛): {result.spread_return:.2%}",
            f"  多空收益差(净): {result.spread_return_net:.2%}",
            f"  平均IC: {result.ic_mean:.4f}",
            f"  换手率: {result.turnover_rate:.2%}",
        ])
        
        if result.ic_statistics:
            lines.extend([
                "",
                "IC显著性检验:",
                "-" * 60,
                f"  IC均值: {result.ic_statistics.ic_mean:.4f}",
                f"  IC标准差: {result.ic_statistics.ic_std:.4f}",
                f"  ICIR: {result.ic_statistics.ic_ir:.4f}",
                f"  t统计量: {result.ic_statistics.t_statistic:.4f}",
                f"  p值: {result.ic_statistics.p_value:.4f}",
                f"  95%置信区间: [{result.ic_statistics.ci_lower:.4f}, {result.ic_statistics.ci_upper:.4f}]",
                f"  显著性: {'是' if result.ic_statistics.is_significant else '否'} ({result.ic_statistics.significance_level})",
            ])
        
        if result.monotonicity:
            lines.extend([
                "",
                "单调性检验:",
                "-" * 60,
                f"  是否单调: {'是' if result.monotonicity.is_monotonic else '否'}",
                f"  Spearman相关系数: {result.monotonicity.spearman_corr:.4f}",
                f"  p值: {result.monotonicity.spearman_pvalue:.4f}",
                f"  趋势方向: {result.monotonicity.trend_direction}",
                f"  各组收益: {[f'{r:.2%}' for r in result.monotonicity.group_returns]}",
            ])
        
        if result.credibility:
            lines.extend([
                "",
                "可信度评估:",
                "-" * 60,
                f"  总分: {result.credibility.total_score:.1f}/100",
                f"  未来函数检测: {'✓' if result.credibility.lookahead_check else '✗'}",
                f"  交易约束: {'✓' if result.credibility.trading_constraints else '✗'}",
                f"  交易成本: {'✓' if result.credibility.transaction_costs else '✗'}",
                f"  IC显著性: {'✓' if result.credibility.ic_significance else '✗'}",
                f"  单调性: {'✓' if result.credibility.monotonicity else '✗'}",
                f"  数据质量: {result.credibility.data_quality:.1f}%",
            ])
            
            if result.credibility.warnings:
                lines.extend([
                    "",
                    "警告:",
                    "-" * 60,
                ])
                for warning in result.credibility.warnings:
                    lines.append(f"  ⚠ {warning}")
        
        if result.oos_validation:
            lines.extend([
                "",
                "样本外验证:",
                "-" * 60,
                f"  训练集IC: {result.oos_validation.train_ic:.4f}",
                f"  测试集IC: {result.oos_validation.test_ic:.4f}",
                f"  IC衰减率: {result.oos_validation.ic_decay_rate:.1%}",
                f"  训练集夏普: {result.oos_validation.train_sharpe:.2f}",
                f"  测试集夏普: {result.oos_validation.test_sharpe:.2f}",
                f"  训练集收益: {result.oos_validation.train_return:.2%}",
                f"  测试集收益: {result.oos_validation.test_return:.2%}",
                f"  验证通过: {'✓' if result.oos_validation.is_valid else '✗'}",
            ])
            if result.oos_validation.decay_warning:
                lines.append(f"  ⚠ {result.oos_validation.decay_warning}")
        
        lines.extend([
            "",
            "交易日历校验:",
            "-" * 60,
            f"  校验通过: {'✓' if result.trading_calendar_valid else '✗'}",
            f"  过滤非交易日记录: {result.non_trading_days_filtered}条",
        ])
        
        if result.details and "robustness_check" in result.details:
            rb = result.details["robustness_check"]
            lines.extend([
                "",
                "稳健性检验:",
                "-" * 60,
                f"  整体稳健: {'✓' if rb.get('is_robust', False) else '✗'}",
                f"  IC方向一致: {'✓' if rb.get('ic_consistent', False) else '✗'}",
                f"  IC变异系数: {rb.get('ic_cv', 0):.2f}",
                f"  夏普稳定: {'✓' if rb.get('sharpe_consistent', False) else '✗'}",
                f"  样本外通过率: {rb.get('oos_pass_rate', 0):.0%}",
                f"  平均可信度: {rb.get('avg_credibility', 0):.0f}",
            ])
            if rb.get("warnings"):
                for warning in rb["warnings"]:
                    lines.append(f"  ⚠ {warning}")
        
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
