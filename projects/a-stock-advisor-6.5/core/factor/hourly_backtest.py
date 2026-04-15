"""
小时线回测模块

支持日内小时级别的因子回测：
1. 交易时段过滤
2. 日内VWAP计算
3. 涨跌停精确判断
4. 小时线因子计算
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
import logging

import pandas as pd
import numpy as np

from .enhanced_daily_backtest import (
    EnhancedLimitHandler,
    ExecutionPriceSimulator,
    PriceType,
    TradingStatus
)

logger = logging.getLogger(__name__)


class HourlyFrequency(Enum):
    """小时线频率"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    MINUTE_60 = "60m"
    HOURLY = "h"


@dataclass
class HourlyBacktestConfig:
    """小时线回测配置"""
    frequency: HourlyFrequency = HourlyFrequency.HOURLY
    trading_hours_only: bool = True
    include_pre_market: bool = False
    include_after_hours: bool = False
    price_type: PriceType = PriceType.CLOSE
    limit_up_threshold: float = 9.9
    limit_down_threshold: float = -9.9
    intraday_slippage: float = 0.0005
    use_intraday_vwap: bool = True
    aggregate_to_daily: bool = False
    morning_start: time = time(9, 30)
    morning_end: time = time(11, 30)
    afternoon_start: time = time(13, 0)
    afternoon_end: time = time(15, 0)


@dataclass
class HourlyBar:
    """小时线Bar数据"""
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    vwap: float
    is_trading_hour: bool
    session: str


class TradingSessionManager:
    """
    交易时段管理器
    
    管理A股交易时段
    """
    
    MORNING_SESSION = (time(9, 30), time(11, 30))
    AFTERNOON_SESSION = (time(13, 0), time(15, 0))
    PRE_MARKET = (time(9, 15), time(9, 25))
    AFTER_HOURS = (time(15, 0), time(15, 30))
    LUNCH_BREAK = (time(11, 30), time(13, 0))
    
    @staticmethod
    def get_session(t: time) -> str:
        """
        获取交易时段名称
        
        Args:
            t: 时间
            
        Returns:
            str: 时段名称
        """
        if TradingSessionManager.PRE_MARKET[0] <= t < TradingSessionManager.PRE_MARKET[1]:
            return "pre_market"
        elif TradingSessionManager.MORNING_SESSION[0] <= t < TradingSessionManager.MORNING_SESSION[1]:
            return "morning"
        elif TradingSessionManager.LUNCH_BREAK[0] <= t < TradingSessionManager.LUNCH_BREAK[1]:
            return "lunch_break"
        elif TradingSessionManager.AFTERNOON_SESSION[0] <= t < TradingSessionManager.AFTERNOON_SESSION[1]:
            return "afternoon"
        elif TradingSessionManager.AFTER_HOURS[0] <= t < TradingSessionManager.AFTER_HOURS[1]:
            return "after_hours"
        else:
            return "non_trading"
    
    @staticmethod
    def is_trading_time(
        t: time,
        include_pre_market: bool = False,
        include_after_hours: bool = False
    ) -> bool:
        """
        判断是否为交易时间
        
        Args:
            t: 时间
            include_pre_market: 是否包含集合竞价
            include_after_hours: 是否包含盘后
            
        Returns:
            bool: 是否为交易时间
        """
        session = TradingSessionManager.get_session(t)
        
        if session in ["morning", "afternoon"]:
            return True
        if include_pre_market and session == "pre_market":
            return True
        if include_after_hours and session == "after_hours":
            return True
        
        return False
    
    @staticmethod
    def get_trading_hours_mask(
        times: pd.Series,
        include_pre_market: bool = False,
        include_after_hours: bool = False
    ) -> pd.Series:
        """
        获取交易时段掩码
        
        Args:
            times: 时间序列
            include_pre_market: 是否包含集合竞价
            include_after_hours: 是否包含盘后
            
        Returns:
            pd.Series: 布尔掩码
        """
        return times.apply(
            lambda t: TradingSessionManager.is_trading_time(
                t, include_pre_market, include_after_hours
            )
        )


class IntradayFactorCalculator:
    """
    日内因子计算器
    
    在小时线数据上计算因子
    """
    
    @staticmethod
    def calculate_intraday_momentum(
        df: pd.DataFrame,
        close_col: str = "close",
        datetime_col: str = "datetime",
        window: int = 4
    ) -> pd.Series:
        """
        计算日内动量因子
        
        Args:
            df: 小时线数据
            close_col: 收盘价列名
            datetime_col: 时间列名
            window: 窗口期（小时数）
            
        Returns:
            pd.Series: 动量因子值
        """
        return df[close_col].pct_change(window)
    
    @staticmethod
    def calculate_intraday_volatility(
        df: pd.DataFrame,
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        window: int = 4
    ) -> pd.Series:
        """
        计算日内波动率因子
        
        Args:
            df: 小时线数据
            high_col: 最高价列名
            low_col: 最低价列名
            close_col: 收盘价列名
            window: 窗口期
            
        Returns:
            pd.Series: 波动率因子值
        """
        high_low_ratio = (df[high_col] - df[low_col]) / df[close_col]
        return high_low_ratio.rolling(window).std()
    
    @staticmethod
    def calculate_intraday_volume_pattern(
        df: pd.DataFrame,
        volume_col: str = "volume",
        datetime_col: str = "datetime",
        stock_col: str = "stock_code"
    ) -> pd.DataFrame:
        """
        计算日内成交量模式因子
        
        Args:
            df: 小时线数据
            volume_col: 成交量列名
            datetime_col: 时间列名
            stock_col: 股票代码列名
            
        Returns:
            pd.DataFrame: 包含成交量模式的DataFrame
        """
        df = df.copy()
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df['hour'] = df[datetime_col].dt.hour
        df['date'] = df[datetime_col].dt.date
        
        hourly_volume = df.groupby(['date', 'hour'])[volume_col].transform('sum')
        daily_volume = df.groupby(['date'])[volume_col].transform('sum')
        
        df['volume_ratio'] = hourly_volume / daily_volume
        
        return df
    
    @staticmethod
    def calculate_vwap_deviation(
        df: pd.DataFrame,
        close_col: str = "close",
        vwap_col: str = "intraday_vwap"
    ) -> pd.Series:
        """
        计算VWAP偏离因子
        
        Args:
            df: 小时线数据
            close_col: 收盘价列名
            vwap_col: VWAP列名
            
        Returns:
            pd.Series: VWAP偏离因子值
        """
        return (df[close_col] - df[vwap_col]) / df[vwap_col]


class HourlyLimitHandler:
    """
    小时线涨跌停处理器
    
    在日内数据上精确判断涨跌停
    """
    
    @staticmethod
    def detect_intraday_limit(
        df: pd.DataFrame,
        open_col: str = "open",
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        prev_close_col: str = "prev_close",
        threshold: float = 9.9
    ) -> pd.DataFrame:
        """
        检测日内涨跌停状态
        
        Args:
            df: 小时线数据
            open_col: 开盘价列名
            high_col: 最高价列名
            low_col: 最低价列名
            close_col: 收盘价列名
            prev_close_col: 前收盘价列名
            threshold: 涨跌停阈值
            
        Returns:
            pd.DataFrame: 包含涨跌停状态的DataFrame
        """
        df = df.copy()
        
        limit_up_price = df[prev_close_col] * (1 + threshold / 100)
        limit_down_price = df[prev_close_col] * (1 - threshold / 100)
        
        df['limit_up_price'] = limit_up_price
        df['limit_down_price'] = limit_down_price
        
        df['is_at_limit_up'] = df[high_col] >= limit_up_price * 0.998
        df['is_at_limit_down'] = df[low_col] <= limit_down_price * 1.002
        
        df['is_limit_up_locked'] = (
            df['is_at_limit_up'] & 
            (df[high_col] == df[low_col]) & 
            (df[high_col] == df[close_col])
        )
        df['is_limit_down_locked'] = (
            df['is_at_limit_down'] & 
            (df[high_col] == df[low_col]) & 
            (df[low_col] == df[close_col])
        )
        
        return df
    
    @staticmethod
    def get_intraday_tradable_status(
        df: pd.DataFrame,
        datetime_col: str = "datetime"
    ) -> pd.DataFrame:
        """
        获取日内可交易状态
        
        Args:
            df: 包含涨跌停状态的DataFrame
            datetime_col: 时间列名
            
        Returns:
            pd.DataFrame: 包含可交易状态的DataFrame
        """
        df = df.copy()
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        
        df['can_buy'] = ~df['is_limit_up_locked']
        df['can_sell'] = ~df['is_limit_down_locked']
        
        return df


class HourlyBacktester:
    """
    小时线回测器
    
    执行小时线级别的因子回测
    """
    
    def __init__(self, config: Optional[HourlyBacktestConfig] = None):
        self.config = config or HourlyBacktestConfig()
    
    def prepare_hourly_data(
        self,
        df: pd.DataFrame,
        datetime_col: str = "datetime",
        open_col: str = "open",
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        volume_col: str = "volume",
        amount_col: str = "amount",
        stock_col: str = "stock_code"
    ) -> pd.DataFrame:
        """
        准备小时线回测数据
        
        Args:
            df: 原始数据
            datetime_col: 时间列名
            open_col: 开盘价列名
            high_col: 最高价列名
            low_col: 最低价列名
            close_col: 收盘价列名
            volume_col: 成交量列名
            amount_col: 成交额列名
            stock_col: 股票代码列名
            
        Returns:
            pd.DataFrame: 准备好的数据
        """
        df = df.copy()
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        
        df['_time'] = df[datetime_col].dt.time
        df['session'] = df['_time'].apply(TradingSessionManager.get_session)
        df['is_trading_hour'] = TradingSessionManager.get_trading_hours_mask(
            df['_time'],
            self.config.include_pre_market,
            self.config.include_after_hours
        )
        
        if self.config.trading_hours_only:
            df = df[df['is_trading_hour']]
        
        df['date'] = df[datetime_col].dt.date
        df['hour'] = df[datetime_col].dt.hour
        
        df = df.sort_values([stock_col, datetime_col])
        df['prev_close'] = df.groupby(stock_col)[close_col].shift(1)
        
        df['prev_close'] = df.groupby(['date', stock_col])['prev_close'].transform(
            lambda x: x.fillna(method='ffill')
        )
        
        df = HourlyLimitHandler.detect_intraday_limit(
            df, open_col, high_col, low_col, close_col, 'prev_close',
            self.config.limit_up_threshold
        )
        
        df = HourlyLimitHandler.get_intraday_tradable_status(df, datetime_col)
        
        if amount_col in df.columns:
            df['cum_amount'] = df.groupby(['date', stock_col])[amount_col].cumsum()
            df['cum_volume'] = df.groupby(['date', stock_col])[volume_col].cumsum()
            df['intraday_vwap'] = df['cum_amount'] / df['cum_volume']
        else:
            df['intraday_vwap'] = (
                df.groupby(['date', stock_col])
                .apply(lambda g: (g[close_col] * g[volume_col]).cumsum() / g[volume_col].cumsum())
                .reset_index(level=[0, 1], drop=True)
            )
        
        df = df.drop(columns=['_time'])
        
        return df
    
    def calculate_hourly_returns(
        self,
        df: pd.DataFrame,
        close_col: str = "close",
        datetime_col: str = "datetime",
        stock_col: str = "stock_code"
    ) -> pd.DataFrame:
        """
        计算小时收益率
        
        Args:
            df: 小时线数据
            close_col: 收盘价列名
            datetime_col: 时间列名
            stock_col: 股票代码列名
            
        Returns:
            pd.DataFrame: 包含收益的数据
        """
        df = df.copy()
        
        df['hourly_return'] = df.groupby(stock_col)[close_col].pct_change()
        
        df['next_hour_return'] = df.groupby(stock_col)['hourly_return'].shift(-1)
        
        df['date'] = pd.to_datetime(df[datetime_col]).dt.date
        df['daily_return'] = df.groupby(['date', stock_col])[close_col].transform(
            lambda x: x.iloc[-1] / x.iloc[0] - 1
        )
        
        return df
    
    def run_hourly_backtest(
        self,
        factor_df: pd.DataFrame,
        price_df: pd.DataFrame,
        datetime_col: str = "datetime",
        factor_col: str = "factor_value",
        stock_col: str = "stock_code",
        close_col: str = "close"
    ) -> Dict[str, Any]:
        """
        执行小时线回测
        
        Args:
            factor_df: 因子数据
            price_df: 价格数据
            datetime_col: 时间列名
            factor_col: 因子值列名
            stock_col: 股票代码列名
            close_col: 收盘价列名
            
        Returns:
            Dict[str, Any]: 回测结果
        """
        prepared_df = self.prepare_hourly_data(
            price_df, datetime_col, stock_col=stock_col
        )
        
        prepared_df = self.calculate_hourly_returns(
            prepared_df, close_col, datetime_col, stock_col
        )
        
        merged = factor_df.merge(
            prepared_df,
            on=[datetime_col, stock_col],
            how='inner'
        )
        
        merged = merged.sort_values([datetime_col, stock_col])
        
        merged['factor_rank'] = merged.groupby(datetime_col)[factor_col].rank()
        
        n_groups = 5
        merged['factor_group'] = merged.groupby(datetime_col)['factor_rank'].transform(
            lambda x: pd.qcut(x, n_groups, labels=False, duplicates='drop')
        )
        
        group_returns = {}
        for group_id in range(n_groups):
            group_df = merged[merged['factor_group'] == group_id]
            group_returns[f'group_{group_id}'] = {
                'mean_return': group_df['next_hour_return'].mean(),
                'std_return': group_df['next_hour_return'].std(),
                'count': len(group_df)
            }
        
        from scipy import stats
        ic_series = merged.groupby(datetime_col).apply(
            lambda g: stats.spearmanr(g[factor_col], g['next_hour_return'])[0]
            if len(g) > 1 else np.nan
        )
        
        return {
            'success': True,
            'group_returns': group_returns,
            'ic_mean': ic_series.mean(),
            'ic_std': ic_series.std(),
            'ic_ir': ic_series.mean() / ic_series.std() if ic_series.std() > 0 else 0,
            'total_records': len(merged),
            'config': {
                'frequency': self.config.frequency.value,
                'trading_hours_only': self.config.trading_hours_only,
                'price_type': self.config.price_type.value
            }
        }
    
    def aggregate_hourly_to_daily(
        self,
        df: pd.DataFrame,
        datetime_col: str = "datetime",
        open_col: str = "open",
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        volume_col: str = "volume",
        amount_col: str = "amount",
        stock_col: str = "stock_code"
    ) -> pd.DataFrame:
        """
        将小时线聚合为日线
        
        Args:
            df: 小时线数据
            datetime_col: 时间列名
            open_col: 开盘价列名
            high_col: 最高价列名
            low_col: 最低价列名
            close_col: 收盘价列名
            volume_col: 成交量列名
            amount_col: 成交额列名
            stock_col: 股票代码列名
            
        Returns:
            pd.DataFrame: 日线数据
        """
        df = df.copy()
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df['date'] = df[datetime_col].dt.date
        
        agg_dict = {
            open_col: 'first',
            high_col: 'max',
            low_col: 'min',
            close_col: 'last',
            volume_col: 'sum',
        }
        
        if amount_col in df.columns:
            agg_dict[amount_col] = 'sum'
        
        daily_df = df.groupby(['date', stock_col]).agg(agg_dict).reset_index()
        
        return daily_df


def get_hourly_backtester(
    frequency: str = "h",
    trading_hours_only: bool = True,
    price_type: str = "close",
    **kwargs
) -> HourlyBacktester:
    """
    获取小时线回测器
    
    Args:
        frequency: 频率 (1m/5m/15m/30m/60m/h)
        trading_hours_only: 仅交易时段
        price_type: 执行价格类型
        **kwargs: 其他参数
        
    Returns:
        HourlyBacktester: 回测器实例
    """
    freq_map = {
        "1m": HourlyFrequency.MINUTE_1,
        "5m": HourlyFrequency.MINUTE_5,
        "15m": HourlyFrequency.MINUTE_15,
        "30m": HourlyFrequency.MINUTE_30,
        "60m": HourlyFrequency.MINUTE_60,
        "h": HourlyFrequency.HOURLY,
    }
    
    price_type_map = {
        "open": PriceType.OPEN,
        "close": PriceType.CLOSE,
        "vwap": PriceType.VWAP,
        "high": PriceType.HIGH,
        "low": PriceType.LOW,
    }
    
    config = HourlyBacktestConfig(
        frequency=freq_map.get(frequency, HourlyFrequency.HOURLY),
        trading_hours_only=trading_hours_only,
        price_type=price_type_map.get(price_type, PriceType.CLOSE),
        **kwargs
    )
    
    return HourlyBacktester(config)
