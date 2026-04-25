"""
增强版日线回测模块

提供更精确的日线回测功能：
1. 精确涨跌停判断（使用日内高低价）
2. 多种执行价格假设（VWAP/开盘/收盘）
3. 隔夜跳空风险调整
4. 小时线回测支持
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class PriceType(Enum):
    """执行价格类型"""
    OPEN = "open"
    CLOSE = "close"
    VWAP = "vwap"
    HIGH = "high"
    LOW = "low"
    AVG_OPEN_CLOSE = "avg_open_close"


class TradingStatus(Enum):
    """交易状态"""
    NORMAL = "normal"
    LIMIT_UP = "limit_up"
    LIMIT_DOWN = "limit_down"
    SUSPENDED = "suspended"
    LIMIT_UP_OPEN = "limit_up_open"
    LIMIT_DOWN_OPEN = "limit_down_open"


@dataclass
class EnhancedDailyConfig:
    """增强版日线回测配置"""
    price_type: PriceType = PriceType.CLOSE
    limit_up_threshold: float = 9.9
    limit_down_threshold: float = -9.9
    use_intraday_high_low: bool = True
    gap_risk_adjustment: float = 0.0
    overnight_gap_penalty: float = 0.001
    vwap_volume_weight: bool = True
    filter_limit_up_at_open: bool = True
    filter_limit_down_at_open: bool = True
    allow_buy_limit_up: bool = False
    allow_sell_limit_down: bool = False


@dataclass
class HourlyConfig:
    """小时线回测配置"""
    trading_hours_only: bool = True
    include_pre_market: bool = False
    include_after_hours: bool = False
    morning_session: Tuple[str, str] = ("09:30", "11:30")
    afternoon_session: Tuple[str, str] = ("13:00", "15:00")
    pre_market: Tuple[str, str] = ("09:15", "09:25")
    after_hours: Tuple[str, str] = ("15:00", "15:30")


class EnhancedLimitHandler:
    """
    增强版涨跌停处理器
    
    使用日内高低价精确判断涨跌停状态
    """
    
    @staticmethod
    def detect_limit_status(
        df: pd.DataFrame,
        open_col: str = "open",
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        prev_close_col: str = "prev_close",
        volume_col: str = "volume",
        threshold: float = 9.9
    ) -> pd.DataFrame:
        """
        精确检测涨跌停状态
        
        Args:
            df: 价格数据
            open_col: 开盘价列名
            high_col: 最高价列名
            low_col: 最低价列名
            close_col: 收盘价列名
            prev_close_col: 前收盘价列名
            volume_col: 成交量列名
            threshold: 涨跌停阈值
            
        Returns:
            pd.DataFrame: 包含交易状态的DataFrame
        """
        df = df.copy()
        
        if prev_close_col not in df.columns:
            df[prev_close_col] = df.groupby('stock_code')[close_col].shift(1)
        
        limit_up_price = df[prev_close_col] * (1 + threshold / 100)
        limit_down_price = df[prev_close_col] * (1 - threshold / 100)
        
        df['limit_up_price'] = limit_up_price
        df['limit_down_price'] = limit_down_price
        
        df['is_limit_up'] = (
            (df[high_col] >= limit_up_price * 0.998) &
            (df[close_col] >= limit_up_price * 0.998)
        )
        
        df['is_limit_down'] = (
            (df[low_col] <= limit_down_price * 1.002) &
            (df[close_col] <= limit_down_price * 1.002)
        )
        
        df['is_limit_up_at_open'] = df[open_col] >= limit_up_price * 0.998
        df['is_limit_down_at_open'] = df[open_col] <= limit_down_price * 1.002
        
        df['is_suspended'] = df[volume_col] == 0 if volume_col in df.columns else False
        
        df['trading_status'] = TradingStatus.NORMAL.value
        
        df.loc[df['is_suspended'], 'trading_status'] = TradingStatus.SUSPENDED.value
        df.loc[df['is_limit_up'], 'trading_status'] = TradingStatus.LIMIT_UP.value
        df.loc[df['is_limit_down'], 'trading_status'] = TradingStatus.LIMIT_DOWN.value
        df.loc[df['is_limit_up_at_open'] & ~df['is_limit_up'], 'trading_status'] = TradingStatus.LIMIT_UP_OPEN.value
        df.loc[df['is_limit_down_at_open'] & ~df['is_limit_down'], 'trading_status'] = TradingStatus.LIMIT_DOWN_OPEN.value
        
        return df
    
    @staticmethod
    def get_tradable_stocks(
        df: pd.DataFrame,
        allow_buy_limit_up: bool = False,
        allow_sell_limit_down: bool = False
    ) -> pd.DataFrame:
        """
        获取可交易股票
        
        Args:
            df: 包含交易状态的DataFrame
            allow_buy_limit_up: 是否允许买入涨停股
            allow_sell_limit_down: 是否允许卖出跌停股
            
        Returns:
            pd.DataFrame: 可交易股票的布尔掩码
        """
        normal_mask = df['trading_status'] == TradingStatus.NORMAL.value
        
        limit_up_open_mask = df['trading_status'] == TradingStatus.LIMIT_UP_OPEN.value
        limit_down_open_mask = df['trading_status'] == TradingStatus.LIMIT_DOWN_OPEN.value
        
        buyable_mask = normal_mask | limit_up_open_mask | limit_down_open_mask
        if allow_buy_limit_up:
            buyable_mask = buyable_mask | (df['trading_status'] == TradingStatus.LIMIT_UP.value)
        
        sellable_mask = normal_mask | limit_up_open_mask | limit_down_open_mask
        if allow_sell_limit_down:
            sellable_mask = sellable_mask | (df['trading_status'] == TradingStatus.LIMIT_DOWN.value)
        
        return pd.DataFrame({
            'buyable': buyable_mask & ~df['is_suspended'],
            'sellable': sellable_mask & ~df['is_suspended']
        })


class ExecutionPriceSimulator:
    """
    执行价格模拟器
    
    模拟不同执行价格假设下的成交价格
    """
    
    @staticmethod
    def calculate_vwap(
        df: pd.DataFrame,
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        volume_col: str = "volume",
        amount_col: str = "amount"
    ) -> pd.Series:
        """
        计算VWAP
        
        Args:
            df: 价格数据
            high_col: 最高价列名
            low_col: 最低价列名
            close_col: 收盘价列名
            volume_col: 成交量列名
            amount_col: 成交额列名
            
        Returns:
            pd.Series: VWAP序列
        """
        if amount_col in df.columns and volume_col in df.columns:
            vwap = df[amount_col] / df[volume_col]
            vwap = vwap.replace([np.inf, -np.inf], np.nan)
            return vwap.fillna(df[close_col])
        else:
            return (df[high_col] + df[low_col] + df[close_col]) / 3
    
    @staticmethod
    def get_execution_price(
        df: pd.DataFrame,
        price_type: PriceType,
        open_col: str = "open",
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        volume_col: str = "volume",
        amount_col: str = "amount",
        slippage: float = 0.0,
        is_buy: bool = True
    ) -> pd.Series:
        """
        获取执行价格
        
        Args:
            df: 价格数据
            price_type: 价格类型
            open_col: 开盘价列名
            high_col: 最高价列名
            low_col: 最低价列名
            close_col: 收盘价列名
            volume_col: 成交量列名
            amount_col: 成交额列名
            slippage: 滑点
            is_buy: 是否买入
            
        Returns:
            pd.Series: 执行价格序列
        """
        if price_type == PriceType.OPEN:
            base_price = df[open_col]
        elif price_type == PriceType.CLOSE:
            base_price = df[close_col]
        elif price_type == PriceType.HIGH:
            base_price = df[high_col]
        elif price_type == PriceType.LOW:
            base_price = df[low_col]
        elif price_type == PriceType.VWAP:
            base_price = ExecutionPriceSimulator.calculate_vwap(
                df, high_col, low_col, close_col, volume_col, amount_col
            )
        elif price_type == PriceType.AVG_OPEN_CLOSE:
            base_price = (df[open_col] + df[close_col]) / 2
        else:
            base_price = df[close_col]
        
        if slippage > 0:
            if is_buy:
                base_price = base_price * (1 + slippage)
            else:
                base_price = base_price * (1 - slippage)
        
        return base_price
    
    @staticmethod
    def simulate_execution_range(
        df: pd.DataFrame,
        open_col: str = "open",
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close"
    ) -> pd.DataFrame:
        """
        模拟执行价格范围
        
        Args:
            df: 价格数据
            
        Returns:
            pd.DataFrame: 包含价格范围的DataFrame
        """
        return pd.DataFrame({
            'price_low': df[low_col],
            'price_high': df[high_col],
            'price_open': df[open_col],
            'price_close': df[close_col],
            'price_range': df[high_col] - df[low_col],
            'price_range_pct': (df[high_col] - df[low_col]) / df[open_col]
        })


class OvernightGapAnalyzer:
    """
    隔夜跳空分析器
    
    分析和调整隔夜跳空风险
    """
    
    @staticmethod
    def calculate_overnight_gap(
        df: pd.DataFrame,
        open_col: str = "open",
        close_col: str = "close",
        date_col: str = "date",
        stock_col: str = "stock_code"
    ) -> pd.DataFrame:
        """
        计算隔夜跳空
        
        Args:
            df: 价格数据
            open_col: 开盘价列名
            close_col: 收盘价列名
            date_col: 日期列名
            stock_col: 股票代码列名
            
        Returns:
            pd.DataFrame: 包含隔夜跳空的DataFrame
        """
        df = df.copy()
        df = df.sort_values([stock_col, date_col])
        
        df['prev_close'] = df.groupby(stock_col)[close_col].shift(1)
        df['overnight_gap'] = (df[open_col] - df['prev_close']) / df['prev_close']
        df['overnight_gap_abs'] = df['overnight_gap'].abs()
        
        df['gap_up'] = df['overnight_gap'] > 0.02
        df['gap_down'] = df['overnight_gap'] < -0.02
        df['gap_significant'] = df['overnight_gap_abs'] > 0.02
        
        return df
    
    @staticmethod
    def adjust_returns_for_gap(
        returns: pd.Series,
        gap_data: pd.DataFrame,
        gap_penalty: float = 0.001,
        date_col: str = "date"
    ) -> pd.Series:
        """
        根据隔夜跳空调整收益
        
        Args:
            returns: 收益序列
            gap_data: 包含跳空数据的DataFrame
            gap_penalty: 跳空惩罚系数
            date_col: 日期列名
            
        Returns:
            pd.Series: 调整后的收益序列
        """
        adjusted_returns = returns.copy()
        
        if 'gap_significant' in gap_data.columns and date_col in gap_data.columns:
            gap_dates = gap_data[gap_data['gap_significant']][date_col].unique()
            
            for gap_date in gap_dates:
                if gap_date in adjusted_returns.index:
                    adjusted_returns.loc[gap_date] -= gap_penalty
        
        return adjusted_returns
    
    @staticmethod
    def get_gap_statistics(
        df: pd.DataFrame,
        stock_col: str = "stock_code"
    ) -> Dict[str, Any]:
        """
        获取跳空统计信息
        
        Args:
            df: 包含隔夜跳空的DataFrame
            stock_col: 股票代码列名
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_days": len(df),
            "gap_up_count": df['gap_up'].sum() if 'gap_up' in df.columns else 0,
            "gap_down_count": df['gap_down'].sum() if 'gap_down' in df.columns else 0,
            "significant_gap_count": df['gap_significant'].sum() if 'gap_significant' in df.columns else 0,
            "avg_gap": df['overnight_gap'].mean() if 'overnight_gap' in df.columns else 0,
            "max_gap_up": df['overnight_gap'].max() if 'overnight_gap' in df.columns else 0,
            "max_gap_down": df['overnight_gap'].min() if 'overnight_gap' in df.columns else 0,
            "gap_volatility": df['overnight_gap'].std() if 'overnight_gap' in df.columns else 0
        }


class HourlyBacktestHandler:
    """
    小时线回测处理器
    
    支持日内小时级别的回测
    """
    
    TRADING_HOURS = [
        (time(9, 30), time(11, 30)),
        (time(13, 0), time(15, 0))
    ]
    
    PRE_MARKET = (time(9, 15), time(9, 25))
    AFTER_HOURS = (time(15, 0), time(15, 30))
    
    @staticmethod
    def is_trading_hour(
        t: time,
        include_pre_market: bool = False,
        include_after_hours: bool = False
    ) -> bool:
        """
        判断是否在交易时段
        
        Args:
            t: 时间
            include_pre_market: 是否包含集合竞价
            include_after_hours: 是否包含盘后
            
        Returns:
            bool: 是否在交易时段
        """
        for start, end in HourlyBacktestHandler.TRADING_HOURS:
            if start <= t <= end:
                return True
        
        if include_pre_market:
            if HourlyBacktestHandler.PRE_MARKET[0] <= t <= HourlyBacktestHandler.PRE_MARKET[1]:
                return True
        
        if include_after_hours:
            if HourlyBacktestHandler.AFTER_HOURS[0] <= t <= HourlyBacktestHandler.AFTER_HOURS[1]:
                return True
        
        return False
    
    @staticmethod
    def filter_trading_hours(
        df: pd.DataFrame,
        datetime_col: str = "datetime",
        include_pre_market: bool = False,
        include_after_hours: bool = False
    ) -> pd.DataFrame:
        """
        过滤交易时段数据
        
        Args:
            df: 数据
            datetime_col: 时间列名
            include_pre_market: 是否包含集合竞价
            include_after_hours: 是否包含盘后
            
        Returns:
            pd.DataFrame: 过滤后的数据
        """
        df = df.copy()
        
        if datetime_col in df.columns:
            df[datetime_col] = pd.to_datetime(df[datetime_col])
            df['_time'] = df[datetime_col].dt.time
            
            mask = df['_time'].apply(
                lambda t: HourlyBacktestHandler.is_trading_hour(
                    t, include_pre_market, include_after_hours
                )
            )
            
            df = df[mask].drop(columns=['_time'])
        
        return df
    
    @staticmethod
    def aggregate_to_daily(
        df: pd.DataFrame,
        datetime_col: str = "datetime",
        ohlcv_cols: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        将小时线聚合为日线
        
        Args:
            df: 小时线数据
            datetime_col: 时间列名
            ohlcv_cols: OHLCV列映射
            
        Returns:
            pd.DataFrame: 日线数据
        """
        if ohlcv_cols is None:
            ohlcv_cols = {
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'amount': 'amount'
            }
        
        df = df.copy()
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df['date'] = df[datetime_col].dt.date
        
        agg_dict = {
            ohlcv_cols['open']: 'first',
            ohlcv_cols['high']: 'max',
            ohlcv_cols['low']: 'min',
            ohlcv_cols['close']: 'last',
            ohlcv_cols['volume']: 'sum',
        }
        
        if ohlcv_cols.get('amount'):
            agg_dict[ohlcv_cols['amount']] = 'sum'
        
        daily_df = df.groupby('date').agg(agg_dict).reset_index()
        
        return daily_df
    
    @staticmethod
    def get_intraday_vwap(
        df: pd.DataFrame,
        datetime_col: str = "datetime",
        close_col: str = "close",
        volume_col: str = "volume",
        amount_col: str = "amount"
    ) -> pd.DataFrame:
        """
        计算日内VWAP
        
        Args:
            df: 小时线数据
            datetime_col: 时间列名
            close_col: 收盘价列名
            volume_col: 成交量列名
            amount_col: 成交额列名
            
        Returns:
            pd.DataFrame: 包含日内VWAP的数据
        """
        df = df.copy()
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df['date'] = df[datetime_col].dt.date
        
        if amount_col in df.columns:
            df['cum_amount'] = df.groupby('date')[amount_col].cumsum()
            df['cum_volume'] = df.groupby('date')[volume_col].cumsum()
            df['intraday_vwap'] = df['cum_amount'] / df['cum_volume']
        else:
            df['cum_close_volume'] = df[close_col] * df[volume_col]
            df['cum_close_volume'] = df.groupby('date')['cum_close_volume'].cumsum()
            df['cum_volume'] = df.groupby('date')[volume_col].cumsum()
            df['intraday_vwap'] = df['cum_close_volume'] / df['cum_volume']
        
        return df


class EnhancedDailyBacktest:
    """
    增强版日线回测器
    
    集成所有增强功能
    """
    
    def __init__(self, config: Optional[EnhancedDailyConfig] = None):
        self.config = config or EnhancedDailyConfig()
    
    def prepare_data(
        self,
        price_df: pd.DataFrame,
        open_col: str = "open",
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        volume_col: str = "volume",
        amount_col: str = "amount"
    ) -> pd.DataFrame:
        """
        准备增强版回测数据
        
        Args:
            price_df: 价格数据
            open_col: 开盘价列名
            high_col: 最高价列名
            low_col: 最低价列名
            close_col: 收盘价列名
            volume_col: 成交量列名
            amount_col: 成交额列名
            
        Returns:
            pd.DataFrame: 增强后的数据
        """
        df = price_df.copy()
        
        df = EnhancedLimitHandler.detect_limit_status(
            df, open_col, high_col, low_col, close_col, "prev_close", volume_col,
            self.config.limit_up_threshold
        )
        
        tradable = EnhancedLimitHandler.get_tradable_stocks(
            df,
            self.config.allow_buy_limit_up,
            self.config.allow_sell_limit_down
        )
        df['buyable'] = tradable['buyable']
        df['sellable'] = tradable['sellable']
        
        df['execution_price_buy'] = ExecutionPriceSimulator.get_execution_price(
            df, self.config.price_type,
            open_col, high_col, low_col, close_col, volume_col, amount_col,
            slippage=0.0, is_buy=True
        )
        df['execution_price_sell'] = ExecutionPriceSimulator.get_execution_price(
            df, self.config.price_type,
            open_col, high_col, low_col, close_col, volume_col, amount_col,
            slippage=0.0, is_buy=False
        )
        
        if self.config.gap_risk_adjustment > 0 or self.config.overnight_gap_penalty > 0:
            df = OvernightGapAnalyzer.calculate_overnight_gap(df, open_col, close_col)
        
        return df
    
    def get_backtest_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取回测统计信息
        
        Args:
            df: 增强后的数据
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = {
            "total_records": len(df),
            "limit_up_count": df['is_limit_up'].sum() if 'is_limit_up' in df.columns else 0,
            "limit_down_count": df['is_limit_down'].sum() if 'is_limit_down' in df.columns else 0,
            "limit_up_at_open_count": df['is_limit_up_at_open'].sum() if 'is_limit_up_at_open' in df.columns else 0,
            "limit_down_at_open_count": df['is_limit_down_at_open'].sum() if 'is_limit_down_at_open' in df.columns else 0,
            "suspended_count": df['is_suspended'].sum() if 'is_suspended' in df.columns else 0,
            "buyable_count": df['buyable'].sum() if 'buyable' in df.columns else 0,
            "sellable_count": df['sellable'].sum() if 'sellable' in df.columns else 0,
        }
        
        if 'overnight_gap' in df.columns:
            gap_stats = OvernightGapAnalyzer.get_gap_statistics(df)
            stats["gap_statistics"] = gap_stats
        
        return stats


def get_enhanced_daily_config(
    price_type: str = "close",
    limit_up_threshold: float = 9.9,
    gap_penalty: float = 0.001,
    **kwargs
) -> EnhancedDailyConfig:
    """
    获取增强版日线配置
    
    Args:
        price_type: 执行价格类型
        limit_up_threshold: 涨跌停阈值
        gap_penalty: 跳空惩罚
        **kwargs: 其他参数
        
    Returns:
        EnhancedDailyConfig: 配置对象
    """
    price_type_map = {
        "open": PriceType.OPEN,
        "close": PriceType.CLOSE,
        "vwap": PriceType.VWAP,
        "high": PriceType.HIGH,
        "low": PriceType.LOW,
        "avg": PriceType.AVG_OPEN_CLOSE
    }
    
    return EnhancedDailyConfig(
        price_type=price_type_map.get(price_type, PriceType.CLOSE),
        limit_up_threshold=limit_up_threshold,
        overnight_gap_penalty=gap_penalty,
        **kwargs
    )
