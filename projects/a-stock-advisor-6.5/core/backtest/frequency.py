"""
多频率数据支持模块

支持日级、小时级、分钟级等多种频率的回测。
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, date, timedelta
from enum import Enum
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class BarFrequency(Enum):
    """Bar频率"""
    TICK = "tick"
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    MINUTE_60 = "60m"
    DAILY = "d"
    WEEKLY = "w"
    MONTHLY = "M"
    
    @property
    def minutes(self) -> int:
        """获取分钟数"""
        mapping = {
            BarFrequency.TICK: 0,
            BarFrequency.MINUTE_1: 1,
            BarFrequency.MINUTE_5: 5,
            BarFrequency.MINUTE_15: 15,
            BarFrequency.MINUTE_30: 30,
            BarFrequency.MINUTE_60: 60,
            BarFrequency.DAILY: 1440,
            BarFrequency.WEEKLY: 10080,
            BarFrequency.MONTHLY: 43200,
        }
        return mapping[self]
    
    @property
    def is_intraday(self) -> bool:
        """是否为日内频率"""
        return self in [
            BarFrequency.TICK,
            BarFrequency.MINUTE_1,
            BarFrequency.MINUTE_5,
            BarFrequency.MINUTE_15,
            BarFrequency.MINUTE_30,
            BarFrequency.MINUTE_60,
        ]
    
    @property
    def pandas_freq(self) -> str:
        """获取pandas频率字符串"""
        mapping = {
            BarFrequency.TICK: "S",
            BarFrequency.MINUTE_1: "1min",
            BarFrequency.MINUTE_5: "5min",
            BarFrequency.MINUTE_15: "15min",
            BarFrequency.MINUTE_30: "30min",
            BarFrequency.MINUTE_60: "h",
            BarFrequency.DAILY: "D",
            BarFrequency.WEEKLY: "W",
            BarFrequency.MONTHLY: "ME",
        }
        return mapping[self]


@dataclass
class FrequencyConfig:
    """频率配置"""
    frequency: BarFrequency
    trading_hours_only: bool = True
    include_pre_market: bool = False
    include_after_hours: bool = False
    
    TRADING_HOURS = [
        ("09:30", "11:30"),
        ("13:00", "15:00"),
    ]
    
    PRE_MARKET = ("09:15", "09:25")
    AFTER_HOURS = ("15:00", "15:30")
    
    def get_time_ranges(self) -> List[tuple]:
        """获取时间范围"""
        ranges = []
        
        if self.include_pre_market:
            ranges.append(self.PRE_MARKET)
        
        if self.trading_hours_only:
            ranges.extend(self.TRADING_HOURS)
        
        if self.include_after_hours:
            ranges.append(self.AFTER_HOURS)
        
        return ranges


class DataResampler:
    """
    数据重采样器
    
    将高频数据转换为低频数据。
    """
    
    @staticmethod
    def resample(
        data: pd.DataFrame,
        target_freq: BarFrequency,
        time_column: str = 'datetime',
        ohlcv_columns: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        重采样数据
        
        Args:
            data: 原始数据
            target_freq: 目标频率
            time_column: 时间列名
            ohlcv_columns: OHLCV列映射
            
        Returns:
            pd.DataFrame: 重采样后的数据
        """
        if ohlcv_columns is None:
            ohlcv_columns = {
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'amount': 'amount'
            }
        
        df = data.copy()
        
        if time_column in df.columns:
            df[time_column] = pd.to_datetime(df[time_column])
            df = df.set_index(time_column)
        
        freq_str = target_freq.pandas_freq
        
        agg_dict = {}
        if ohlcv_columns.get('open') in df.columns:
            agg_dict[ohlcv_columns['open']] = 'first'
        if ohlcv_columns.get('high') in df.columns:
            agg_dict[ohlcv_columns['high']] = 'max'
        if ohlcv_columns.get('low') in df.columns:
            agg_dict[ohlcv_columns['low']] = 'min'
        if ohlcv_columns.get('close') in df.columns:
            agg_dict[ohlcv_columns['close']] = 'last'
        if ohlcv_columns.get('volume') in df.columns:
            agg_dict[ohlcv_columns['volume']] = 'sum'
        if ohlcv_columns.get('amount') in df.columns:
            agg_dict[ohlcv_columns['amount']] = 'sum'
        
        other_cols = [c for c in df.columns if c not in agg_dict]
        for col in other_cols:
            agg_dict[col] = 'last'
        
        resampled = df.resample(freq_str).agg(agg_dict)
        
        resampled = resampled.dropna(subset=[ohlcv_columns.get('close', 'close')])
        
        resampled = resampled.reset_index()
        
        return resampled
    
    @staticmethod
    def aggregate_to_daily(
        data: pd.DataFrame,
        time_column: str = 'datetime',
        stock_column: str = 'stock_code'
    ) -> pd.DataFrame:
        """
        聚合为日线数据
        
        Args:
            data: 原始数据
            time_column: 时间列名
            stock_column: 股票代码列名
            
        Returns:
            pd.DataFrame: 日线数据
        """
        df = data.copy()
        df['date'] = pd.to_datetime(df[time_column]).dt.date
        
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'amount': 'sum',
        }
        
        other_cols = [c for c in df.columns if c not in agg_dict and c not in [time_column, 'date', stock_column]]
        for col in other_cols:
            agg_dict[col] = 'last'
        
        daily = df.groupby([stock_column, 'date']).agg(agg_dict).reset_index()
        
        return daily


class MultiFrequencyBacktestEngine:
    """
    多频率回测引擎基类
    
    支持不同频率的回测执行。
    """
    
    def __init__(
        self,
        frequency: BarFrequency = BarFrequency.DAILY,
        frequency_config: Optional[FrequencyConfig] = None
    ):
        """
        初始化多频率回测引擎
        
        Args:
            frequency: 回测频率
            frequency_config: 频率配置
        """
        self.frequency = frequency
        self.frequency_config = frequency_config or FrequencyConfig(frequency=frequency)
        
        self._estimated_time_factor = self._calculate_time_factor()
    
    def _calculate_time_factor(self) -> float:
        """
        计算时间因子
        
        用于估算不同频率回测的相对时间消耗。
        """
        daily_bars_per_year = 252
        
        if self.frequency == BarFrequency.DAILY:
            return 1.0
        elif self.frequency == BarFrequency.WEEKLY:
            return 0.2
        elif self.frequency == BarFrequency.MONTHLY:
            return 0.05
        elif self.frequency.is_intraday:
            daily_bars = self._estimate_daily_bars()
            return daily_bars / daily_bars_per_year
        else:
            return 1.0
    
    def _estimate_daily_bars(self) -> int:
        """估算每日bar数量"""
        if not self.frequency.is_intraday:
            return 1
        
        minutes_per_bar = self.frequency.minutes
        trading_minutes_per_day = 4 * 60
        
        return trading_minutes_per_day // minutes_per_bar
    
    def estimate_backtest_time(
        self,
        trading_days: int,
        time_per_bar_ms: float = 1.0
    ) -> float:
        """
        估算回测时间
        
        Args:
            trading_days: 交易日数量
            time_per_bar_ms: 每个bar的处理时间（毫秒）
            
        Returns:
            float: 预估时间（秒）
        """
        if self.frequency == BarFrequency.DAILY:
            total_bars = trading_days
        elif self.frequency == BarFrequency.WEEKLY:
            total_bars = trading_days // 5
        elif self.frequency == BarFrequency.MONTHLY:
            total_bars = trading_days // 20
        else:
            daily_bars = self._estimate_daily_bars()
            total_bars = trading_days * daily_bars
        
        return (total_bars * time_per_bar_ms) / 1000
    
    def get_bar_iterator(
        self,
        data: pd.DataFrame,
        time_column: str = 'datetime',
        stock_column: str = 'stock_code'
    ) -> Any:
        """
        获取bar迭代器
        
        Args:
            data: 数据
            time_column: 时间列名
            stock_column: 股票代码列名
            
        Returns:
            迭代器
        """
        df = data.copy()
        
        if time_column in df.columns:
            df[time_column] = pd.to_datetime(df[time_column])
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            time_column = 'date'
        
        df = df.sort_values(time_column)
        
        if self.frequency == BarFrequency.DAILY:
            return self._iterate_daily(df, time_column, stock_column)
        elif self.frequency == BarFrequency.WEEKLY:
            return self._iterate_weekly(df, time_column, stock_column)
        elif self.frequency == BarFrequency.MONTHLY:
            return self._iterate_monthly(df, time_column, stock_column)
        elif self.frequency.is_intraday:
            return self._iterate_intraday(df, time_column, stock_column)
        else:
            return self._iterate_daily(df, time_column, stock_column)
    
    def _iterate_daily(self, df: pd.DataFrame, time_column: str, stock_column: str):
        """日频迭代"""
        if 'date' not in df.columns and time_column != 'date':
            df['date'] = pd.to_datetime(df[time_column]).dt.date
        
        for date_val, group in df.groupby('date'):
            yield {
                'datetime': pd.to_datetime(date_val),
                'date': date_val,
                'data': group,
                'bar_type': 'daily'
            }
    
    def _iterate_weekly(self, df: pd.DataFrame, time_column: str, stock_column: str):
        """周频迭代"""
        df['week'] = pd.to_datetime(df[time_column]).dt.isocalendar().week
        df['year'] = pd.to_datetime(df[time_column]).dt.year
        
        for (year, week), group in df.groupby(['year', 'week']):
            yield {
                'datetime': pd.to_datetime(group[time_column].iloc[0]),
                'date': group[time_column].iloc[0],
                'data': group,
                'bar_type': 'weekly'
            }
    
    def _iterate_monthly(self, df: pd.DataFrame, time_column: str, stock_column: str):
        """月频迭代"""
        df['month'] = pd.to_datetime(df[time_column]).dt.to_period('M')
        
        for month, group in df.groupby('month'):
            yield {
                'datetime': pd.to_datetime(group[time_column].iloc[0]),
                'date': group[time_column].iloc[0],
                'data': group,
                'bar_type': 'monthly'
            }
    
    def _iterate_intraday(self, df: pd.DataFrame, time_column: str, stock_column: str):
        """日内频率迭代"""
        df['date'] = pd.to_datetime(df[time_column]).dt.date
        
        for date_val, day_group in df.groupby('date'):
            if self.frequency == BarFrequency.MINUTE_1:
                df['bar_time'] = pd.to_datetime(day_group[time_column]).dt.floor('1min')
            elif self.frequency == BarFrequency.MINUTE_5:
                df['bar_time'] = pd.to_datetime(day_group[time_column]).dt.floor('5min')
            elif self.frequency == BarFrequency.MINUTE_15:
                df['bar_time'] = pd.to_datetime(day_group[time_column]).dt.floor('15min')
            elif self.frequency == BarFrequency.MINUTE_30:
                df['bar_time'] = pd.to_datetime(day_group[time_column]).dt.floor('30min')
            elif self.frequency == BarFrequency.MINUTE_60:
                df['bar_time'] = pd.to_datetime(day_group[time_column]).dt.floor('h')
            else:
                df['bar_time'] = pd.to_datetime(day_group[time_column])
            
            for bar_time, bar_group in day_group.groupby('bar_time'):
                yield {
                    'datetime': bar_time,
                    'date': date_val,
                    'data': bar_group,
                    'bar_type': 'intraday'
                }


class FrequencyAwareBacktestConfig:
    """
    频率感知的回测配置
    
    根据数据频率自动调整回测参数。
    """
    
    DEFAULT_PARAMS = {
        BarFrequency.TICK: {
            'slippage_rate': 0.0001,
            'commission_rate': 0.0002,
            'max_position_hold_time': timedelta(hours=4),
        },
        BarFrequency.MINUTE_1: {
            'slippage_rate': 0.0002,
            'commission_rate': 0.0003,
            'max_position_hold_time': timedelta(days=1),
        },
        BarFrequency.MINUTE_5: {
            'slippage_rate': 0.0003,
            'commission_rate': 0.0003,
            'max_position_hold_time': timedelta(days=2),
        },
        BarFrequency.MINUTE_15: {
            'slippage_rate': 0.0004,
            'commission_rate': 0.0003,
            'max_position_hold_time': timedelta(days=3),
        },
        BarFrequency.MINUTE_30: {
            'slippage_rate': 0.0005,
            'commission_rate': 0.0003,
            'max_position_hold_time': timedelta(days=5),
        },
        BarFrequency.MINUTE_60: {
            'slippage_rate': 0.0006,
            'commission_rate': 0.0003,
            'max_position_hold_time': timedelta(days=10),
        },
        BarFrequency.DAILY: {
            'slippage_rate': 0.001,
            'commission_rate': 0.0003,
            'max_position_hold_time': timedelta(days=30),
        },
        BarFrequency.WEEKLY: {
            'slippage_rate': 0.002,
            'commission_rate': 0.0003,
            'max_position_hold_time': timedelta(days=60),
        },
        BarFrequency.MONTHLY: {
            'slippage_rate': 0.003,
            'commission_rate': 0.0003,
            'max_position_hold_time': timedelta(days=90),
        },
    }
    
    @classmethod
    def get_params(cls, frequency: BarFrequency) -> Dict[str, Any]:
        """
        获取频率相关的默认参数
        
        Args:
            frequency: 频率
            
        Returns:
            Dict: 参数字典
        """
        return cls.DEFAULT_PARAMS.get(frequency, cls.DEFAULT_PARAMS[BarFrequency.DAILY]).copy()
    
    @classmethod
    def estimate_backtest_duration(
        cls,
        frequency: BarFrequency,
        start_date: date,
        end_date: date,
        stock_count: int = 100,
        complexity_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        估算回测持续时间
        
        Args:
            frequency: 频率
            start_date: 开始日期
            end_date: 结束日期
            stock_count: 股票数量
            complexity_factor: 策略复杂度因子
            
        Returns:
            Dict: 估算结果
        """
        trading_days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                trading_days += 1
            current += timedelta(days=1)
        
        engine = MultiFrequencyBacktestEngine(frequency)
        base_time = engine.estimate_backtest_time(trading_days)
        
        adjusted_time = base_time * stock_count * complexity_factor
        
        return {
            'frequency': frequency.value,
            'trading_days': trading_days,
            'stock_count': stock_count,
            'estimated_seconds': adjusted_time,
            'estimated_minutes': adjusted_time / 60,
            'time_factor': engine._estimated_time_factor,
            'recommendation': cls._get_recommendation(frequency, trading_days, stock_count)
        }
    
    @classmethod
    def _get_recommendation(cls, frequency: BarFrequency, trading_days: int, stock_count: int) -> str:
        """获取建议"""
        if frequency.is_intraday:
            if trading_days > 250 and stock_count > 500:
                return "建议：高频数据+长周期+多股票，考虑分批回测或使用并行处理"
            elif trading_days > 250:
                return "建议：高频数据+长周期，回测时间可能较长，建议先小样本测试"
            else:
                return "建议：日内频率回测，注意数据质量和交易时间过滤"
        else:
            return "建议：低频回测，时间消耗可控"


def detect_data_frequency(
    data: pd.DataFrame,
    time_column: str = 'datetime'
) -> BarFrequency:
    """
    检测数据频率
    
    Args:
        data: 数据
        time_column: 时间列名
        
    Returns:
        BarFrequency: 检测到的频率
    """
    if time_column not in data.columns:
        if 'date' in data.columns:
            time_column = 'date'
        else:
            return BarFrequency.DAILY
    
    times = pd.to_datetime(data[time_column]).sort_values()
    
    if len(times) < 2:
        return BarFrequency.DAILY
    
    diffs = times.diff().dropna()
    
    median_diff = diffs.median()
    
    if median_diff < timedelta(minutes=2):
        return BarFrequency.MINUTE_1
    elif median_diff < timedelta(minutes=7):
        return BarFrequency.MINUTE_5
    elif median_diff < timedelta(minutes=20):
        return BarFrequency.MINUTE_15
    elif median_diff < timedelta(minutes=45):
        return BarFrequency.MINUTE_30
    elif median_diff < timedelta(hours=2):
        return BarFrequency.MINUTE_60
    elif median_diff < timedelta(days=2):
        return BarFrequency.DAILY
    elif median_diff < timedelta(days=10):
        return BarFrequency.WEEKLY
    else:
        return BarFrequency.MONTHLY
