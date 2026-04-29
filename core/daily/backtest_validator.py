"""
多策略回测验证框架

核心策略:
1. 动量策略 - 追踪强势股
2. 均值回归策略 - 超跌反弹
3. 双均线策略 - 经典趋势跟踪
4. 布林带策略 - 波动率突破
5. RSI策略 - 超买超卖
6. MACD策略 - 趋势确认
7. KDJ策略 - 随机指标
8. 量价策略 - 成交量确认
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
from abc import ABC, abstractmethod


@dataclass
class BacktestValidationResult:
    """回测验证结果"""
    success: bool
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_holding_days: float = 0.0
    validation_date: str = ""
    error_message: Optional[str] = None
    strategy_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "total_return": round(self.total_return * 100, 2),
            "annual_return": round(self.annual_return * 100, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "max_drawdown": round(self.max_drawdown * 100, 2),
            "win_rate": round(self.win_rate * 100, 2),
            "profit_factor": round(self.profit_factor, 2),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "avg_holding_days": round(self.avg_holding_days, 1),
            "validation_date": self.validation_date,
            "error_message": self.error_message,
            "strategy_name": self.strategy_name
        }


@dataclass
class StrategyPerformance:
    """策略表现"""
    name: str
    win_rate: float
    total_trades: int
    total_profit: float
    avg_profit_pct: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, commission_rate: float = 0.0003, slippage_rate: float = 0.001):
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.trades: List[Dict[str, Any]] = []
    
    @abstractmethod
    def get_name(self) -> str:
        """策略名称"""
        pass
    
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        """生成信号"""
        pass
    
    def reset(self):
        """重置状态"""
        self.trades = []


class DoubleMAStrategy(BaseStrategy):
    """
    双均线策略 - 经典趋势跟踪
    
    核心逻辑:
    1. 短期均线上穿长期均线 - 金叉买入
    2. 短期均线下穿长期均线 - 死叉卖出
    """
    
    def get_name(self) -> str:
        return "double_ma"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 20:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        ma5 = row.get('ma5', row['close'])
        ma10 = row.get('ma10', row['close'])
        ma20 = row.get('ma20', row['close'])
        
        prev_ma5 = prev_row.get('ma5', prev_row['close'])
        prev_ma10 = prev_row.get('ma10', prev_row['close'])
        prev_ma20 = prev_row.get('ma20', prev_row['close'])
        
        if pd.isna(ma5) or pd.isna(ma10) or pd.isna(ma20):
            return None
        
        golden_cross = prev_ma5 <= prev_ma10 and ma5 > ma10
        trend_up = ma5 > ma20 and ma10 > ma20
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        
        if golden_cross and trend_up and vol_ratio > 1.2:
            return 'buy_double_ma'
        
        return None


class BollingerBandsStrategy(BaseStrategy):
    """
    布林带策略 - 波动率突破
    
    核心逻辑:
    1. 价格触及下轨 - 超卖买入
    2. 价格触及上轨 - 超买卖出
    """
    
    def get_name(self) -> str:
        return "bollinger"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 20:
            return None
        
        row = df.iloc[i]
        close = row['close']
        ma20 = row.get('ma20', close)
        
        std20 = df['close'].iloc[i-20:i].std()
        if pd.isna(std20) or std20 <= 0:
            return None
        
        upper_band = ma20 + 2 * std20
        lower_band = ma20 - 2 * std20
        
        bandwidth = (upper_band - lower_band) / ma20
        if bandwidth < 0.05:
            return None
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        
        if close <= lower_band * 1.01 and rsi < 35:
            return 'buy_bollinger'
        
        return None


class RSIStrategy(BaseStrategy):
    """
    RSI策略 - 超买超卖
    
    核心逻辑:
    1. RSI < 30 超卖 - 买入
    2. RSI > 70 超买 - 卖出
    """
    
    def get_name(self) -> str:
        return "rsi"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 15:
            return None
        
        row = df.iloc[i]
        rsi = row.get('rsi', 50)
        
        if pd.isna(rsi):
            return None
        
        close = row['close']
        ma5 = row.get('ma5', close)
        ma10 = row.get('ma10', close)
        ma20 = row.get('ma20', close)
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        
        prev_rsi = df.iloc[i-1].get('rsi', 50)
        if pd.isna(prev_rsi):
            prev_rsi = 50
        
        rsi_oversold = rsi < 25 and prev_rsi < 25 and rsi > prev_rsi
        trend_support = close > ma20 * 0.95 and ma5 > ma10
        volume_confirm = vol_ratio > 1.0
        
        if rsi_oversold and trend_support and volume_confirm:
            return 'buy_rsi'
        
        return None


class MACDStrategy(BaseStrategy):
    """
    MACD策略 - 趋势确认
    
    核心逻辑:
    1. MACD金叉 - 买入
    2. MACD死叉 - 卖出
    """
    
    def get_name(self) -> str:
        return "macd"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 35:
            return None
        
        close = df['close']
        ema12 = close.ewm(span=12, adjust=False).iloc[i]
        ema26 = close.ewm(span=26, adjust=False).iloc[i]
        macd = ema12 - ema26
        
        prev_ema12 = close.ewm(span=12, adjust=False).iloc[i-1]
        prev_ema26 = close.ewm(span=26, adjust=False).iloc[i-1]
        prev_macd = prev_ema12 - prev_ema26
        
        signal_line = close.ewm(span=9, adjust=False).iloc[i]
        
        row = df.iloc[i]
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        
        macd_cross_up = prev_macd <= 0 and macd > 0
        macd_rising = macd > prev_macd
        volume_confirm = vol_ratio > 1.1
        
        if macd_cross_up and macd_rising and volume_confirm:
            return 'buy_macd'
        
        return None


class KDJStrategy(BaseStrategy):
    """
    KDJ策略 - 随机指标
    
    核心逻辑:
    1. K线上穿D线且J<20 - 买入
    2. K线下穿D线且J>80 - 卖出
    """
    
    def get_name(self) -> str:
        return "kdj"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 15:
            return None
        
        low_list = df['low'].rolling(9, min_periods=9).min()
        high_list = df['high'].rolling(9, min_periods=9).max()
        
        rsv = (df['close'] - low_list) / (high_list - low_list + 1e-10) * 100
        
        k = rsv.ewm(com=2, adjust=False).iloc[i]
        d = k.ewm(com=2, adjust=False) if hasattr(k, 'ewm') else k
        j = 3 * k - 2 * d
        
        prev_k = rsv.ewm(com=2, adjust=False).iloc[i-1]
        prev_d = prev_k.ewm(com=2, adjust=False) if hasattr(prev_k, 'ewm') else prev_k
        
        if pd.isna(k) or pd.isna(d) or pd.isna(j):
            return None
        
        k_cross_d = prev_k <= prev_d and k > d
        j_oversold = j < 30
        
        row = df.iloc[i]
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        
        if k_cross_d and j_oversold and vol_ratio > 0.9:
            return 'buy_kdj'
        
        return None


class VolumePriceStrategy(BaseStrategy):
    """
    量价策略 - 成交量确认
    
    核心逻辑:
    1. 放量上涨 - 买入
    2. 缩量下跌 - 观望
    """
    
    def get_name(self) -> str:
        return "volume_price"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 20:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        close = row['close']
        prev_close = prev_row['close']
        
        volume = row['volume']
        vol_ma5 = row.get('vol_ma5', volume)
        vol_ma20 = row.get('vol_ma20', volume)
        
        price_up = close > prev_close * 1.02
        vol_ratio_5 = volume / vol_ma5 if vol_ma5 > 0 else 1
        vol_ratio_20 = volume / vol_ma20 if vol_ma20 > 0 else 1
        
        volume_break = vol_ratio_5 > 1.5 and vol_ratio_20 > 1.3
        
        ma5 = row.get('ma5', close)
        ma20 = row.get('ma20', close)
        trend_up = close > ma5 > ma20
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = rsi < 70
        
        if price_up and volume_break and trend_up and rsi_ok:
            return 'buy_volume'
        
        return None


class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略 - 超跌反弹
    
    核心逻辑:
    1. 价格跌破布林带下轨
    2. RSI超卖
    3. 成交量萎缩
    """
    
    def get_name(self) -> str:
        return "mean_reversion"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        row = df.iloc[i]
        close = row['close']
        ma20 = row.get('ma20', close)
        std20 = df['close'].iloc[i-20:i].std() if i >= 20 else 0
        lower_band = ma20 - 2 * std20 if std20 > 0 else ma20
        rsi = row.get('rsi', 50)
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        
        if pd.isna(rsi):
            rsi = 50
        
        is_oversold = close <= lower_band * 1.02
        is_rsi_oversold = rsi < 30
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        is_volume_low = vol_ratio < 0.8
        
        prev_close = df['close'].iloc[i-1] if i > 0 else close
        curr_open = row['open']
        is_bullish = close > prev_close and close > curr_open
        
        if is_oversold and (is_rsi_oversold or is_volume_low) and is_bullish:
            return 'buy_reversion'
        
        return None


class MomentumStrategy(BaseStrategy):
    """
    动量策略 - 追踪强势股
    
    核心逻辑:
    1. 价格创新高
    2. 成交量放大
    3. RSI强势区间
    """
    
    def get_name(self) -> str:
        return "momentum"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        row = df.iloc[i]
        close = row['close']
        high_20 = df['high'].iloc[i-20:i].max() if i >= 20 else close
        ma5 = row.get('ma5', close)
        ma20 = row.get('ma20', close)
        rsi = row.get('rsi', 50)
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        
        if pd.isna(rsi):
            rsi = 50
        
        is_new_high = close >= high_20 * 0.98
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        is_strong_trend = close > ma5 > ma20
        is_rsi_strong = 55 < rsi < 80
        
        if is_new_high and vol_ratio > 1.3 and is_strong_trend and is_rsi_strong:
            return 'buy_momentum'
        
        return None


class BreakoutStrategy(BaseStrategy):
    """
    突破策略 - 关键位置突破
    
    核心逻辑:
    1. 突破前期高点
    2. 放量突破
    """
    
    def get_name(self) -> str:
        return "breakout"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 20:
            return None
        
        row = df.iloc[i]
        close = row['close']
        prev_high = df['high'].iloc[i-20:i].max()
        prev_low = df['low'].iloc[i-20:i].min()
        range_pct = (prev_high - prev_low) / prev_low if prev_low > 0 else 0
        
        if range_pct < 0.10:
            return None
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        
        is_breakout = close > prev_high * 1.01
        is_volume_break = vol_ratio > 1.5
        
        if is_breakout and is_volume_break:
            return 'buy_breakout'
        
        return None


class TripleConfirmationStrategy(BaseStrategy):
    """
    三重确认策略 - 需要多个指标同时确认
    
    核心逻辑:
    1. 趋势确认 - 均线多头排列
    2. 动量确认 - RSI处于合理区间
    3. 量价确认 - 放量上涨
    """
    
    def get_name(self) -> str:
        return "triple_confirm"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 30:
            return None
        
        row = df.iloc[i]
        close = row['close']
        ma5 = row.get('ma5', close)
        ma10 = row.get('ma10', close)
        ma20 = row.get('ma20', close)
        rsi = row.get('rsi', 50)
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        
        if pd.isna(rsi):
            rsi = 50
        
        trend_confirm = close > ma5 > ma10 > ma20
        ma5_slope = (ma5 - df['ma5'].iloc[i-3]) / df['ma5'].iloc[i-3] if i >= 3 else 0
        trend_strong = ma5_slope > 0.01
        
        rsi_confirm = 45 <= rsi <= 65
        
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.3 and vol_ratio < 3.0
        
        price_change_5d = (close - df['close'].iloc[i-5]) / df['close'].iloc[i-5] if i >= 5 else 0
        price_confirm = 0.02 <= price_change_5d <= 0.08
        
        if trend_confirm and trend_strong and rsi_confirm and volume_confirm and price_confirm:
            return 'buy_triple'
        
        return None


class TrendFollowStrategy(BaseStrategy):
    """
    趋势跟踪策略 - 严格趋势确认
    
    核心逻辑:
    1. 强趋势确认
    2. 回调买入
    3. 严格止损
    """
    
    def get_name(self) -> str:
        return "trend_follow"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 30:
            return None
        
        row = df.iloc[i]
        close = row['close']
        ma5 = row.get('ma5', close)
        ma10 = row.get('ma10', close)
        ma20 = row.get('ma20', close)
        ma60 = row.get('ma60', close)
        rsi = row.get('rsi', 50)
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        
        if pd.isna(rsi):
            rsi = 50
        
        strong_trend = ma5 > ma10 > ma20 > ma60
        price_above_ma = close > ma5
        
        if i >= 5:
            ma5_prev = df['ma5'].iloc[i-5]
            ma20_prev = df['ma20'].iloc[i-5]
            ma_trend = (ma5 - ma5_prev) > 0 and (ma20 - ma20_prev) > 0
        else:
            ma_trend = False
        
        pullback = False
        if i >= 3:
            for j in range(i-3, i):
                if df['close'].iloc[j] < df['ma5'].iloc[j]:
                    pullback = True
                    break
        
        rsi_ok = 40 <= rsi <= 60
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_ok = vol_ratio > 1.2
        
        if strong_trend and price_above_ma and ma_trend and pullback and rsi_ok and volume_ok:
            return 'buy_trend'
        
        return None


class VolumeBreakoutStrategy(BaseStrategy):
    """
    量价突破策略 - 成交量确认突破
    
    核心逻辑:
    1. 成交量放大
    2. 价格突破
    3. 趋势确认
    """
    
    def get_name(self) -> str:
        return "vol_breakout"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 30:
            return None
        
        row = df.iloc[i]
        close = row['close']
        high_20 = df['high'].iloc[i-20:i].max() if i >= 20 else close
        ma5 = row.get('ma5', close)
        ma20 = row.get('ma20', close)
        rsi = row.get('rsi', 50)
        volume = row['volume']
        vol_ma5 = row.get('vol_ma5', volume)
        vol_ma20 = row.get('vol_ma20', volume)
        
        if pd.isna(rsi):
            rsi = 50
        
        price_breakout = close > high_20 * 0.99
        
        vol_ratio_5 = volume / vol_ma5 if vol_ma5 > 0 else 1
        vol_ratio_20 = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_breakout = vol_ratio_5 > 1.8 and vol_ratio_20 > 1.5
        
        trend_up = close > ma5 > ma20
        
        rsi_ok = rsi < 70
        
        if price_breakout and volume_breakout and trend_up and rsi_ok:
            return 'buy_volbreak'
        
        return None


class MorningStarStrategy(BaseStrategy):
    """
    早晨之星策略 - K线形态
    
    核心逻辑:
    1. 下跌趋势中出现
    2. 三根K线组成：大阴线+小实体+大阳线
    3. 第三根阳线确认反转
    """
    
    def get_name(self) -> str:
        return "morning_star"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 5:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        prev2_row = df.iloc[i-2]
        
        close = row['close']
        open_ = row['open']
        high = row['high']
        low = row['low']
        
        prev_close = prev_row['close']
        prev_open = prev_row['open']
        
        prev2_close = prev2_row['close']
        prev2_open = prev2_row['open']
        
        prev2_body = abs(prev2_close - prev2_open)
        prev2_range = prev2_row['high'] - prev2_row['low']
        
        is_bearish_candle = prev2_close < prev2_open
        is_big_bearish = prev2_body > prev2_range * 0.6
        
        prev_body = abs(prev_close - prev_open)
        prev_range = prev_row['high'] - prev_row['low']
        is_small_body = prev_body < prev2_body * 0.3
        
        curr_body = abs(close - open_)
        curr_range = high - low
        is_bullish_candle = close > open_
        is_big_bullish = curr_body > curr_range * 0.6
        
        close_above_mid = close > (prev2_open + prev2_close) / 2
        
        ma20 = row.get('ma20', close)
        trend_down = prev2_close < ma20
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.2
        
        if (is_bearish_candle and is_big_bearish and 
            is_small_body and 
            is_bullish_candle and is_big_bullish and
            close_above_mid and trend_down and volume_confirm):
            return 'buy_morning_star'
        
        return None


class HammerStrategy(BaseStrategy):
    """
    锤头线策略 - K线形态
    
    核心逻辑:
    1. 下跌趋势中出现
    2. 实体小，下影线长
    3. 次日确认
    """
    
    def get_name(self) -> str:
        return "hammer"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 3:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        close = row['close']
        open_ = row['open']
        high = row['high']
        low = row['low']
        
        body = abs(close - open_)
        range_ = high - low
        
        if range_ == 0:
            return None
        
        lower_shadow = min(close, open_) - low
        upper_shadow = high - max(close, open_)
        
        is_hammer = (lower_shadow > body * 2 and 
                    upper_shadow < body * 0.5 and 
                    body < range_ * 0.3)
        
        prev_close = prev_row['close']
        ma20 = row.get('ma20', close)
        trend_down = prev_close < ma20 * 0.95
        
        next_confirm = close > prev_close
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.0
        
        if is_hammer and trend_down and next_confirm and volume_confirm:
            return 'buy_hammer'
        
        return None


class SupportBounceStrategy(BaseStrategy):
    """
    支撑反弹策略 - 趋势线支撑
    
    核心逻辑:
    1. 上升趋势中
    2. 回调到支撑位
    3. 出现反弹信号
    """
    
    def get_name(self) -> str:
        return "support_bounce"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 30:
            return None
        
        row = df.iloc[i]
        close = row['close']
        ma5 = row.get('ma5', close)
        ma10 = row.get('ma10', close)
        ma20 = row.get('ma20', close)
        ma60 = row.get('ma60', close)
        
        if pd.isna(ma60):
            return None
        
        trend_up = ma20 > ma60
        
        near_support = abs(close - ma20) / ma20 < 0.02 or abs(close - ma60) / ma60 < 0.02
        
        if i >= 2:
            prev_close = df['close'].iloc[i-1]
            prev2_close = df['close'].iloc[i-2]
            bounce = close > prev_close > prev2_close
        else:
            bounce = False
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = rsi < 60
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.1
        
        if trend_up and near_support and bounce and rsi_ok and volume_confirm:
            return 'buy_support'
        
        return None


class GoldenCrossStrategy(BaseStrategy):
    """
    黄金交叉策略 - 葛兰威尔法则
    
    核心逻辑:
    1. 短期均线上穿长期均线
    2. 成交量放大
    3. 趋势确认
    """
    
    def get_name(self) -> str:
        return "golden_cross"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 65:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        ma5 = row.get('ma5', row['close'])
        ma10 = row.get('ma10', row['close'])
        ma20 = row.get('ma20', row['close'])
        ma60 = row.get('ma60', row['close'])
        
        prev_ma5 = prev_row.get('ma5', prev_row['close'])
        prev_ma10 = prev_row.get('ma10', prev_row['close'])
        prev_ma20 = prev_row.get('ma20', prev_row['close'])
        prev_ma60 = prev_row.get('ma60', prev_row['close'])
        
        if pd.isna(ma60) or pd.isna(prev_ma60):
            return None
        
        golden_cross = prev_ma5 <= prev_ma20 and ma5 > ma20
        trend_up = ma5 > ma10 > ma20 > ma60
        
        ma_slope = (ma20 - df['ma20'].iloc[i-5]) / df['ma20'].iloc[i-5] if i >= 5 else 0
        ma_rising = ma_slope > 0.01
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.3
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = rsi < 70
        
        if golden_cross and trend_up and ma_rising and volume_confirm and rsi_ok:
            return 'buy_golden'
        
        return None


class MultiFactorStrategy(BaseStrategy):
    """
    多因子组合策略
    
    核心逻辑:
    1. 因子综合评分
    2. 动态权重
    """
    
    def get_name(self) -> str:
        return "multi_factor"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        row = df.iloc[i]
        close = row['close']
        ma5 = row.get('ma5', close)
        ma10 = row.get('ma10', close)
        ma20 = row.get('ma20', close)
        rsi = row.get('rsi', 50)
        volume = row['volume']
        vol_ma5 = row.get('vol_ma5', volume)
        vol_ma20 = row.get('vol_ma20', volume)
        
        if pd.isna(rsi):
            rsi = 50
        
        score = 0
        
        if close > ma5 > ma10 > ma20:
            score += 25
        elif close > ma5 > ma20:
            score += 15
        elif close > ma5:
            score += 5
        
        if 40 <= rsi <= 60:
            score += 20
        elif 35 <= rsi <= 70:
            score += 10
        
        vol_ratio = vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1
        if 1.0 <= vol_ratio <= 1.5:
            score += 15
        elif 0.8 <= vol_ratio <= 2.0:
            score += 8
        
        if i >= 20:
            price_change = (close - df['close'].iloc[i-20]) / df['close'].iloc[i-20]


class RedThreeSoldiersStrategy(BaseStrategy):
    """
    红三兵策略 - K线形态
    
    核心逻辑:
    1. 连续三根阳线
    2. 每根收盘价逐步抬高
    3. 成交量逐步放大
    """
    
    def get_name(self) -> str:
        return "red_three_soldiers"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 5:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        prev2_row = df.iloc[i-2]
        
        close = row['close']
        open_ = row['open']
        prev_close = prev_row['close']
        prev_open = prev_row['open']
        prev2_close = prev2_row['close']
        prev2_open = prev2_row['open']
        
        curr_bullish = close > open_
        prev_bullish = prev_close > prev_open
        prev2_bullish = prev2_close > prev2_open
        
        rising_close = close > prev_close > prev2_close
        
        curr_body = abs(close - open_)
        prev_body = abs(prev_close - prev_open)
        prev2_body = abs(prev2_close - prev2_open)
        reasonable_bodies = curr_body > 0 and prev_body > 0 and prev2_body > 0
        
        volume = row['volume']
        prev_volume = prev_row['volume']
        prev2_volume = prev2_row['volume']
        volume_increasing = volume > prev_volume > prev2_volume
        
        ma20 = row.get('ma20', close)
        trend_down = prev2_close < ma20 * 0.95
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = rsi < 70
        
        if (curr_bullish and prev_bullish and prev2_bullish and 
            rising_close and reasonable_bodies and volume_increasing and 
            trend_down and rsi_ok):
            return 'buy_red_three'
        
        return None


class BullishEngulfingStrategy(BaseStrategy):
    """
    阳包阴策略 - K线形态
    
    核心逻辑:
    1. 前一根阴线
    2. 当日阳线完全吞没前一根阴线
    3. 成交量放大
    """
    
    def get_name(self) -> str:
        return "bullish_engulfing"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 3:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        close = row['close']
        open_ = row['open']
        high = row['high']
        low = row['low']
        
        prev_close = prev_row['close']
        prev_open = prev_row['open']
        prev_high = prev_row['high']
        prev_low = prev_row['low']
        
        prev_bearish = prev_close < prev_open
        curr_bullish = close > open_
        
        engulfing = (open_ <= prev_close and close >= prev_open and
                    high >= prev_high and low <= prev_low)
        
        curr_body = abs(close - open_)
        prev_body = abs(prev_close - prev_open)
        strong_engulfing = curr_body > prev_body * 1.2
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.3
        
        ma20 = row.get('ma20', close)
        trend_down = prev_close < ma20 * 0.95
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = rsi < 65
        
        if (prev_bearish and curr_bullish and engulfing and strong_engulfing and 
            volume_confirm and trend_down and rsi_ok):
            return 'buy_engulfing'
        
        return None


class GapUpStrategy(BaseStrategy):
    """
    跳空高开策略 - 缺口形态
    
    核心逻辑:
    1. 当日开盘价高于前日最高价
    2. 缺口未回补
    3. 成交量放大
    """
    
    def get_name(self) -> str:
        return "gap_up"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 5:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        open_ = row['open']
        close = row['close']
        high = row['high']
        low = row['low']
        
        prev_high = prev_row['high']
        prev_close = prev_row['close']
        
        gap_up = open_ > prev_high * 1.01
        
        gap_not_filled = low > prev_high
        
        bullish = close > open_
        
        gap_size = (open_ - prev_high) / prev_high
        reasonable_gap = 0.01 < gap_size < 0.05
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.2
        
        ma5 = row.get('ma5', close)
        ma20 = row.get('ma20', close)
        trend_up = ma5 > ma20
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = rsi < 70
        
        if (gap_up and gap_not_filled and bullish and reasonable_gap and 
            volume_confirm and trend_up and rsi_ok):
            return 'buy_gap_up'
        
        return None


class VolumePriceSurgeStrategy(BaseStrategy):
    """
    量价齐升策略 - 量价关系
    
    核心逻辑:
    1. 价格上涨
    2. 成交量放大
    3. 连续确认
    """
    
    def get_name(self) -> str:
        return "vol_price_surge"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 10:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        close = row['close']
        open_ = row['open']
        volume = row['volume']
        
        prev_close = prev_row['close']
        prev_volume = prev_row['volume']
        
        bullish = close > open_
        price_up = close > prev_close
        volume_up = volume > prev_volume
        
        vol_ma5 = row.get('vol_ma5', volume)
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio_5 = volume / vol_ma5 if vol_ma5 > 0 else 1
        vol_ratio_20 = volume / vol_ma20 if vol_ma20 > 0 else 1
        
        strong_volume = vol_ratio_5 > 1.5 and vol_ratio_20 > 1.3
        
        price_change_5d = 0
        if i >= 5:
            price_change_5d = (close - df['close'].iloc[i-5]) / df['close'].iloc[i-5]
        steady_rise = 0.03 < price_change_5d < 0.15
        
        ma5 = row.get('ma5', close)
        ma10 = row.get('ma10', close)
        ma20 = row.get('ma20', close)
        trend_up = close > ma5 > ma10 > ma20
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = rsi < 70
        
        if (bullish and price_up and volume_up and strong_volume and 
            steady_rise and trend_up and rsi_ok):
            return 'buy_vol_price'
        
        return None


class BollingerBounceStrategy(BaseStrategy):
    """
    布林带下轨反弹策略
    
    核心逻辑:
    1. 价格触及下轨
    2. 出现反弹信号
    3. 成交量放大
    """
    
    def get_name(self) -> str:
        return "bollinger_bounce"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 25:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        close = row['close']
        open_ = row['open']
        high = row['high']
        low = row['low']
        
        prev_close = prev_row['close']
        prev_low = prev_row['low']
        
        ma20 = close.rolling(20).mean().iloc[-1] if hasattr(close, 'rolling') else row.get('ma20', close)
        std20 = close.rolling(20).std().iloc[-1] if hasattr(close, 'rolling') else close * 0.02
        
        if isinstance(ma20, pd.Series):
            ma20 = ma20.iloc[-1] if len(ma20) > 0 else close
        if isinstance(std20, pd.Series):
            std20 = std20.iloc[-1] if len(std20) > 0 else close * 0.02
        
        upper = ma20 + 2 * std20
        lower = ma20 - 2 * std20
        
        touched_lower = prev_low <= lower * 1.01
        bounce = close > prev_close and close > open_
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.0
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_oversold = rsi < 40
        
        if touched_lower and bounce and volume_confirm and rsi_oversold:
            return 'buy_bollinger'
        
        return None


class TrendPullbackStrategy(BaseStrategy):
    """
    趋势回调买入策略
    
    核心逻辑:
    1. 强趋势确立
    2. 回调到关键均线
    3. 出现企稳信号
    """
    
    def get_name(self) -> str:
        return "trend_pullback"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 30:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        prev2_row = df.iloc[i-2]
        
        close = row['close']
        ma5 = row.get('ma5', close)
        ma10 = row.get('ma10', close)
        ma20 = row.get('ma20', close)
        ma60 = row.get('ma60', close)
        
        if pd.isna(ma60):
            return None
        
        strong_uptrend = ma20 > ma60 * 1.02
        
        pullback_to_ma20 = abs(close - ma20) / ma20 < 0.02
        pullback_to_ma10 = abs(close - ma10) / ma10 < 0.015
        
        prev_close = prev_row['close']
        prev2_close = prev2_row['close']
        stabilizing = close > prev_close > prev2_close
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 0.8
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = 40 <= rsi <= 60
        
        if (strong_uptrend and (pullback_to_ma20 or pullback_to_ma10) and 
            stabilizing and volume_confirm and rsi_ok):
            return 'buy_pullback'
        
        return None


class Wave3Strategy(BaseStrategy):
    """
    波浪理论第3浪策略
    
    核心逻辑:
    1. 突破第1浪高点
    2. 成交量放大
    3. 趋势确认
    """
    
    def get_name(self) -> str:
        return "wave3"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 40:
            return None
        
        row = df.iloc[i]
        close = row['close']
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        
        high_20 = df['high'].iloc[i-20:i].max()
        low_20 = df['low'].iloc[i-20:i].min()
        
        breakout = close > high_20 * 1.02
        
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_surge = vol_ratio > 1.5
        
        ma5 = row.get('ma5', close)
        ma10 = row.get('ma10', close)
        ma20 = row.get('ma20', close)
        trend_up = ma5 > ma10 > ma20
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = 50 <= rsi <= 70
        
        if breakout and volume_surge and trend_up and rsi_ok:
            return 'buy_wave3'
        
        return None


class ChanBuy1Strategy(BaseStrategy):
    """
    缠论一买策略
    
    核心逻辑:
    1. 底分型确认
    2. 背驰信号
    3. 成交量放大
    """
    
    def get_name(self) -> str:
        return "chan_buy1"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 20:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        prev2_row = df.iloc[i-2]
        
        high = row['high']
        low = row['low']
        close = row['close']
        
        prev_high = prev_row['high']
        prev_low = prev_row['low']
        prev_close = prev_row['close']
        
        prev2_high = prev2_row['high']
        prev2_low = prev2_row['low']
        prev2_close = prev2_row['close']
        
        bottom_fractal = (prev2_low < prev_low and prev2_low < low and
                         prev2_high < prev_high and close > prev_high)
        
        ma20 = row.get('ma20', close)
        ma60 = row.get('ma60', close)
        if pd.isna(ma60):
            ma60 = ma20
        
        divergence = close < ma20 and ma20 < ma60
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.2
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_oversold = rsi < 35
        
        if bottom_fractal and divergence and volume_confirm and rsi_oversold:
            return 'buy_chan1'
        
        return None


class ChanBuy2Strategy(BaseStrategy):
    """
    缠论二买策略
    
    核心逻辑:
    1. 回调不破前低
    2. 趋势向上
    3. 成交量确认
    """
    
    def get_name(self) -> str:
        return "chan_buy2"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 30:
            return None
        
        row = df.iloc[i]
        close = row['close']
        ma5 = row.get('ma5', close)
        ma10 = row.get('ma10', close)
        ma20 = row.get('ma20', close)
        
        trend_up = ma5 > ma10 > ma20
        
        low_10 = df['low'].iloc[i-10:i].min()
        low_20 = df['low'].iloc[i-20:i-10].min()
        
        higher_low = low_10 > low_20 * 0.98
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.0
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = 40 <= rsi <= 60
        
        if trend_up and higher_low and volume_confirm and rsi_ok:
            return 'buy_chan2'
        
        return None


class ChanBuy3Strategy(BaseStrategy):
    """
    缠论三买策略
    
    核心逻辑:
    1. 突破前高
    2. 回调确认
    3. 再次突破
    """
    
    def get_name(self) -> str:
        return "chan_buy3"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 40:
            return None
        
        row = df.iloc[i]
        close = row['close']
        ma5 = row.get('ma5', close)
        ma20 = row.get('ma20', close)
        
        high_20 = df['high'].iloc[i-20:i].max()
        high_40 = df['high'].iloc[i-40:i-20].max()
        
        breakout = close > high_20 * 1.01 and high_20 > high_40
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.3
        
        trend_up = close > ma5 > ma20
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = rsi < 70
        
        if breakout and volume_confirm and trend_up and rsi_ok:
            return 'buy_chan3'
        
        return None


class TurtleBreakoutStrategy(BaseStrategy):
    """
    海龟交易法则突破策略
    
    核心逻辑:
    1. 突破20日高点
    2. 成交量确认
    3. 趋势过滤
    """
    
    def get_name(self) -> str:
        return "turtle_breakout"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 25:
            return None
        
        row = df.iloc[i]
        close = row['close']
        high = row['high']
        
        high_20 = df['high'].iloc[i-20:i].max()
        
        breakout = high >= high_20
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.2
        
        ma5 = row.get('ma5', close)
        ma20 = row.get('ma20', close)
        trend_up = ma5 > ma20
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = rsi < 70
        
        if breakout and volume_confirm and trend_up and rsi_ok:
            return 'buy_turtle'
        
        return None


class DualThrustStrategy(BaseStrategy):
    """
    Dual Thrust策略
    
    核心逻辑:
    1. 突破上轨
    2. 波动率确认
    3. 成交量放大
    """
    
    def get_name(self) -> str:
        return "dual_thrust"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 5:
            return None
        
        row = df.iloc[i]
        open_ = row['open']
        close = row['close']
        high = row['high']
        low = row['low']
        
        prev_high = df['high'].iloc[i-1]
        prev_low = df['low'].iloc[i-1]
        prev_close = df['close'].iloc[i-1]
        
        range_ = prev_high - prev_low
        
        k1 = 0.4
        k2 = 0.6
        
        upper = open_ + k1 * range_
        lower = open_ - k2 * range_
        
        breakout_up = close > upper
        
        volume = row['volume']
        vol_ma5 = row.get('vol_ma5', volume)
        vol_ratio = volume / vol_ma5 if vol_ma5 > 0 else 1
        volume_confirm = vol_ratio > 1.3
        
        rsi = row.get('rsi', 50)
        if pd.isna(rsi):
            rsi = 50
        rsi_ok = rsi < 70
        
        if breakout_up and volume_confirm and rsi_ok:
            return 'buy_dual_thrust'
        
        return None


class RSVStrategy(BaseStrategy):
    """
    RSV反转策略
    
    核心逻辑:
    1. RSV超卖
    2. 价格企稳
    3. 成交量放大
    """
    
    def get_name(self) -> str:
        return "rsv"
    
    def generate_signal(self, df: pd.DataFrame, i: int, market_trend: float) -> Optional[str]:
        if i < 15:
            return None
        
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        close = row['close']
        high = row['high']
        low = row['low']
        
        high_n = df['high'].iloc[i-9:i].max()
        low_n = df['low'].iloc[i-9:i].min()
        
        if high_n == low_n:
            return None
        
        rsv = (close - low_n) / (high_n - low_n) * 100
        prev_close = prev_row['close']
        prev_high_n = df['high'].iloc[i-10:i-1].max()
        prev_low_n = df['low'].iloc[i-10:i-1].min()
        
        if prev_high_n == prev_low_n:
            return None
        
        prev_rsv = (prev_close - prev_low_n) / (prev_high_n - prev_low_n) * 100
        
        rsv_oversold = rsv < 20 and prev_rsv < 20 and rsv > prev_rsv
        
        volume = row['volume']
        vol_ma20 = row.get('vol_ma20', volume)
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        volume_confirm = vol_ratio > 1.0
        
        ma20 = row.get('ma20', close)
        trend_support = close > ma20 * 0.95
        
        if rsv_oversold and volume_confirm and trend_support:
            return 'buy_rsv'
        
        return None


class StrategyBacktestValidator:
    """
    多策略回测验证器
    """
    
    def __init__(
        self,
        initial_capital: float = 1000000.0,
        lookback_days: int = 60,
        commission_rate: float = 0.0003,
        slippage_rate: float = 0.001
    ):
        self.initial_capital = initial_capital
        self.lookback_days = lookback_days
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        
        self.all_strategies: List[BaseStrategy] = [
            Wave3Strategy(commission_rate, slippage_rate),
            ChanBuy1Strategy(commission_rate, slippage_rate),
            ChanBuy2Strategy(commission_rate, slippage_rate),
            ChanBuy3Strategy(commission_rate, slippage_rate),
            TurtleBreakoutStrategy(commission_rate, slippage_rate),
            DualThrustStrategy(commission_rate, slippage_rate),
            RSVStrategy(commission_rate, slippage_rate),
            RedThreeSoldiersStrategy(commission_rate, slippage_rate),
            BullishEngulfingStrategy(commission_rate, slippage_rate),
            GapUpStrategy(commission_rate, slippage_rate),
            VolumePriceSurgeStrategy(commission_rate, slippage_rate),
            BollingerBounceStrategy(commission_rate, slippage_rate),
            TrendPullbackStrategy(commission_rate, slippage_rate),
            MorningStarStrategy(commission_rate, slippage_rate),
            HammerStrategy(commission_rate, slippage_rate),
            SupportBounceStrategy(commission_rate, slippage_rate),
            GoldenCrossStrategy(commission_rate, slippage_rate),
            TripleConfirmationStrategy(commission_rate, slippage_rate),
            TrendFollowStrategy(commission_rate, slippage_rate),
            VolumeBreakoutStrategy(commission_rate, slippage_rate),
            DoubleMAStrategy(commission_rate, slippage_rate),
            BollingerBandsStrategy(commission_rate, slippage_rate),
            RSIStrategy(commission_rate, slippage_rate),
            MACDStrategy(commission_rate, slippage_rate),
            KDJStrategy(commission_rate, slippage_rate),
            VolumePriceStrategy(commission_rate, slippage_rate),
            MeanReversionStrategy(commission_rate, slippage_rate),
            MomentumStrategy(commission_rate, slippage_rate),
            BreakoutStrategy(commission_rate, slippage_rate),
            MultiFactorStrategy(commission_rate, slippage_rate),
        ]
        
        self.strategy_performances: List[StrategyPerformance] = []
        self.selected_strategies: List[BaseStrategy] = []
        self.trades: List[Dict[str, Any]] = []
    
    def evaluate_all_strategies(self, all_dfs: List[pd.DataFrame], market_trend: Dict[str, float]) -> List[StrategyPerformance]:
        """评估所有策略的表现"""
        performances = []
        
        for strategy in self.all_strategies:
            strategy.reset()
            strategy_trades = []
            
            for df in all_dfs:
                try:
                    df_ind = self._prepare_indicators(df.copy())
                    trades = self._backtest_single_strategy(df_ind, df['stock_code'].iloc[0], market_trend, strategy)
                    strategy_trades.extend(trades)
                except Exception:
                    continue
            
            if strategy_trades:
                winning = [t for t in strategy_trades if t['profit'] > 0]
                losing = [t for t in strategy_trades if t['profit'] <= 0]
                
                total_trades = len(strategy_trades)
                win_rate = len(winning) / total_trades if total_trades > 0 else 0
                total_profit = sum(t['profit'] for t in strategy_trades)
                avg_profit_pct = np.mean([t['profit_pct'] for t in strategy_trades]) if strategy_trades else 0
                
                total_win = sum(t['profit'] for t in winning)
                total_loss = abs(sum(t['profit'] for t in losing))
                profit_factor = total_win / total_loss if total_loss > 0 else float('inf') if total_win > 0 else 0
                
                perf = StrategyPerformance(
                    name=strategy.get_name(),
                    win_rate=win_rate,
                    total_trades=total_trades,
                    total_profit=total_profit,
                    avg_profit_pct=avg_profit_pct,
                    sharpe_ratio=0,
                    max_drawdown=0,
                    profit_factor=profit_factor
                )
                performances.append(perf)
            
            strategy.trades = strategy_trades
        
        performances.sort(key=lambda x: (x.win_rate, x.profit_factor), reverse=True)
        
        return performances
    
    def _backtest_single_strategy(
        self,
        df: pd.DataFrame,
        stock_code: str,
        market_trend: Dict[str, float],
        strategy: BaseStrategy
    ) -> List[Dict[str, Any]]:
        """单策略回测"""
        trades = []
        
        position = 0
        entry_price = 0
        entry_date = None
        entry_atr = 0
        cash = 100000.0
        max_price = 0
        holding_days = 0
        
        for i in range(70, len(df)):
            row = df.iloc[i]
            date = row['date']
            close = row['close']
            ma5 = row['ma5']
            ma20 = row['ma20']
            atr = row.get('atr', close * 0.02)
            atr_pct = row.get('atr_pct', 0.02)
            
            if pd.isna(ma5) or pd.isna(ma20):
                continue
            
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)[:10]
            mkt_trend = market_trend.get(date_str, 0.5)
            
            signal = None
            
            if position == 0:
                signal = strategy.generate_signal(df, i, mkt_trend)
            
            if position > 0:
                holding_days += 1
                max_price = max(max_price, close)
                
                loss_pct = (close - entry_price) / entry_price
                drawdown = (max_price - close) / max_price
                
                atr_stop = entry_atr * 2.0 / entry_price if entry_atr > 0 else 0.05
                
                if loss_pct < -min(0.08, atr_stop * 1.5):
                    signal = 'sell_stop'
                elif loss_pct > min(0.15, atr_stop * 3):
                    signal = 'sell_take'
                elif close < ma5 * 0.94:
                    signal = 'sell_trend'
                elif drawdown > 0.08:
                    signal = 'sell_trailing'
                elif holding_days > 15:
                    signal = 'sell_time'
            
            if signal and signal.startswith('buy') and position == 0:
                risk_per_trade = 0.02
                stop_loss = min(0.06, atr_pct * 1.5) if atr_pct > 0 else 0.04
                position_size = (cash * risk_per_trade) / stop_loss
                shares = int(position_size / close / 100) * 100
                
                if shares > 0:
                    cost = shares * close * (1 + self.commission_rate + self.slippage_rate)
                    if cost <= cash * 0.90:
                        cash -= cost
                        position = shares
                        entry_price = close
                        entry_date = date
                        entry_atr = atr
                        max_price = close
                        holding_days = 0
            
            elif signal and signal.startswith('sell') and position > 0:
                revenue = position * close * (1 - self.commission_rate - self.slippage_rate)
                profit = revenue - position * entry_price
                profit_pct = profit / (position * entry_price)
                
                trades.append({
                    'stock_code': stock_code,
                    'entry_date': entry_date,
                    'exit_date': date,
                    'entry_price': entry_price,
                    'exit_price': close,
                    'shares': position,
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'exit_reason': signal,
                    'strategy': strategy.get_name(),
                    'holding_days': holding_days
                })
                
                cash += revenue
                position = 0
                entry_price = 0
                entry_date = None
                entry_atr = 0
                max_price = 0
                holding_days = 0
        
        return trades
    
    def _backtest_combined_strategies(
        self,
        df: pd.DataFrame,
        stock_code: str,
        market_trend: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """组合策略回测 - 多策略投票机制"""
        trades = []
        
        position = 0
        entry_price = 0
        entry_date = None
        entry_atr = 0
        cash = 100000.0
        max_price = 0
        holding_days = 0
        
        for i in range(70, len(df)):
            row = df.iloc[i]
            date = row['date']
            close = row['close']
            ma5 = row['ma5']
            ma20 = row['ma20']
            atr = row.get('atr', close * 0.02)
            atr_pct = row.get('atr_pct', 0.02)
            
            if pd.isna(ma5) or pd.isna(ma20):
                continue
            
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)[:10]
            mkt_trend = market_trend.get(date_str, 0.5)
            
            signal = None
            
            if position == 0:
                buy_votes = 0
                total_votes = len(self.selected_strategies)
                
                for strategy in self.selected_strategies:
                    strat_signal = strategy.generate_signal(df, i, mkt_trend)
                    if strat_signal and strat_signal.startswith('buy'):
                        buy_votes += 1
                
                if total_votes == 1 and buy_votes == 1:
                    signal = 'buy_combined'
                elif total_votes > 0 and buy_votes >= max(2, total_votes * 0.4):
                    signal = 'buy_combined'
            
            if position > 0:
                holding_days += 1
                max_price = max(max_price, close)
                
                loss_pct = (close - entry_price) / entry_price
                drawdown = (max_price - close) / max_price
                
                atr_stop = entry_atr * 2.0 / entry_price if entry_atr > 0 else 0.05
                
                if loss_pct < -min(0.06, atr_stop * 1.5):
                    signal = 'sell_stop'
                elif loss_pct > min(0.12, atr_stop * 2.5):
                    signal = 'sell_take'
                elif close < ma5 * 0.95:
                    signal = 'sell_trend'
                elif drawdown > 0.06:
                    signal = 'sell_trailing'
                elif holding_days > 12:
                    signal = 'sell_time'
            
            if signal and signal.startswith('buy') and position == 0:
                risk_per_trade = 0.02
                stop_loss = min(0.05, atr_pct * 1.5) if atr_pct > 0 else 0.03
                position_size = (cash * risk_per_trade) / stop_loss
                shares = int(position_size / close / 100) * 100
                
                if shares > 0:
                    cost = shares * close * (1 + self.commission_rate + self.slippage_rate)
                    if cost <= cash * 0.90:
                        cash -= cost
                        position = shares
                        entry_price = close
                        entry_date = date
                        entry_atr = atr
                        max_price = close
                        holding_days = 0
            
            elif signal and signal.startswith('sell') and position > 0:
                revenue = position * close * (1 - self.commission_rate - self.slippage_rate)
                profit = revenue - position * entry_price
                profit_pct = profit / (position * entry_price)
                
                exit_date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)[:10]
                entry_date_str = entry_date.strftime('%Y-%m-%d') if hasattr(entry_date, 'strftime') else str(entry_date)[:10]
                
                trades.append({
                    'stock_code': stock_code,
                    'entry_date': entry_date_str,
                    'exit_date': exit_date_str,
                    'entry_price': round(entry_price, 2),
                    'exit_price': round(close, 2),
                    'shares': position,
                    'profit': round(profit, 2),
                    'profit_pct': round(profit_pct, 4),
                    'holding_days': holding_days,
                    'exit_reason': signal,
                    'strategy': 'combined'
                })
                
                cash += revenue
                position = 0
                entry_price = 0
                entry_date = None
                entry_atr = 0
                max_price = 0
                holding_days = 0
        
        return trades
    
    def validate(
        self,
        signal_data: Optional[Dict[str, Any]] = None
    ) -> BacktestValidationResult:
        """执行回测验证"""
        try:
            from core.infrastructure.config import get_data_paths
            
            data_paths = get_data_paths()
            stocks_path = Path(data_paths.stocks_daily_path)
            
            if not stocks_path.exists():
                return BacktestValidationResult(
                    success=False,
                    error_message="数据路径不存在",
                    validation_date=datetime.now().strftime('%Y-%m-%d')
                )

            stock_files = list(stocks_path.glob("*.parquet"))  # 移除股票数量限制
            
            if not stock_files:
                return BacktestValidationResult(
                    success=False,
                    error_message="没有找到股票数据文件",
                    validation_date=datetime.now().strftime('%Y-%m-%d')
                )
            
            self.trades = []
            
            all_dfs = []
            for stock_file in stock_files:
                try:
                    df = pd.read_parquet(stock_file)
                    if df.empty or 'close' not in df.columns:
                        continue
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date')
                    if len(df) < 100:
                        continue
                    df['stock_code'] = stock_file.stem
                    all_dfs.append(df)
                except Exception:
                    continue
            
            if not all_dfs:
                return BacktestValidationResult(
                    success=False,
                    error_message="没有有效股票数据",
                    validation_date=datetime.now().strftime('%Y-%m-%d')
                )
            
            market_trend = self._calculate_market_trend(all_dfs)
            
            print("    - 评估所有策略表现...")
            self.strategy_performances = self.evaluate_all_strategies(all_dfs, market_trend)
            
            for perf in self.strategy_performances[:5]:
                print(f"      {perf.name}: 胜率{perf.win_rate*100:.1f}%, 交易{perf.total_trades}笔, 盈亏比{perf.profit_factor:.2f}")
            
            min_win_rate = 0.51
            min_trades = 30
            
            self.selected_strategies = []
            for perf in self.strategy_performances:
                if perf.win_rate >= min_win_rate and perf.total_trades >= min_trades:
                    strategy = next((s for s in self.all_strategies if s.get_name() == perf.name), None)
                    if strategy:
                        self.selected_strategies.append(strategy)
            
            if not self.selected_strategies:
                min_win_rate = 0.48
                for perf in self.strategy_performances:
                    if perf.win_rate >= min_win_rate and perf.total_trades >= min_trades:
                        strategy = next((s for s in self.all_strategies if s.get_name() == perf.name), None)
                        if strategy:
                            self.selected_strategies.append(strategy)
            
            if not self.selected_strategies:
                self.selected_strategies = [self.all_strategies[i] for i in range(min(5, len(self.all_strategies)))]
            
            print(f"    - 选中策略: {[s.get_name() for s in self.selected_strategies]}")
            
            for df in all_dfs:
                df_ind = self._prepare_indicators(df.copy())
                combined_trades = self._backtest_combined_strategies(df_ind, df['stock_code'].iloc[0], market_trend)
                self.trades.extend(combined_trades)
            
            if not self.trades:
                return BacktestValidationResult(
                    success=False,
                    error_message="回测期间没有有效交易",
                    validation_date=datetime.now().strftime('%Y-%m-%d')
                )
            
            winning = [t for t in self.trades if t['profit'] > 0]
            losing = [t for t in self.trades if t['profit'] <= 0]
            
            total_trades = len(self.trades)
            win_rate = len(winning) / total_trades if total_trades > 0 else 0
            total_profit = sum(t['profit'] for t in self.trades)
            avg_profit_pct = np.mean([t['profit_pct'] for t in self.trades]) if self.trades else 0
            avg_holding_days = np.mean([t['holding_days'] for t in self.trades]) if self.trades else 0
            
            total_win = sum(t['profit'] for t in winning)
            total_loss = abs(sum(t['profit'] for t in losing))
            profit_factor = total_win / total_loss if total_loss > 0 else float('inf') if total_win > 0 else 0
            
            returns = [t['profit_pct'] for t in self.trades]
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 1 and np.std(returns) > 0 else 0
            
            cumulative = 1.0
            max_value = 1.0
            max_drawdown = 0.0
            for t in self.trades:
                cumulative *= (1 + t['profit_pct'])
                max_value = max(max_value, cumulative)
                drawdown = (max_value - cumulative) / max_value
                max_drawdown = max(max_drawdown, drawdown)
            
            total_return = cumulative - 1
            
            if self.trades:
                first_entry = min(t['entry_date'] for t in self.trades)
                last_exit = max(t['exit_date'] for t in self.trades)
                if hasattr(first_entry, 'date'):
                    first_entry = first_entry.date() if hasattr(first_entry, 'date') else first_entry
                if hasattr(last_exit, 'date'):
                    last_exit = last_exit.date() if hasattr(last_exit, 'date') else last_exit
                try:
                    actual_days = (last_exit - first_entry).days if hasattr(last_exit, '__sub__') else 60
                    actual_days = max(actual_days, 1)
                except Exception:
                    actual_days = 60
            else:
                actual_days = 60
            
            if actual_days >= 252:
                annual_return = (1 + total_return) ** (252 / actual_days) - 1 if total_return > -1 else total_return
            elif actual_days >= 60:
                annual_return = (1 + total_return) ** (252 / actual_days) - 1 if total_return > -1 else total_return
                annual_return = min(annual_return, 2.0)
            else:
                annual_return = total_return * (252 / max(actual_days, 1)) if total_return > -1 else total_return
                annual_return = min(annual_return, 1.0)
            
            return BacktestValidationResult(
                success=True,
                annual_return=annual_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                total_trades=total_trades,
                winning_trades=len(winning),
                losing_trades=len(losing),
                profit_factor=profit_factor,
                avg_holding_days=avg_holding_days,
                validation_date=datetime.now().strftime('%Y-%m-%d'),
                strategy_name="combined_strategies"
            )
            
        except Exception as e:
            return BacktestValidationResult(
                success=False,
                error_message=str(e),
                validation_date=datetime.now().strftime('%Y-%m-%d')
            )
    
    def _prepare_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备技术指标"""
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        df['vol_ma5'] = df['volume'].rolling(5).mean()
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std() * np.sqrt(252)
        
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(14).mean()
        df['atr_pct'] = df['atr'] / df['close']
        
        return df
    
    def _calculate_market_trend(self, all_dfs: List[pd.DataFrame]) -> Dict[str, float]:
        """计算市场趋势"""
        market_trend = {}
        
        all_dates = set()
        for df in all_dfs:
            all_dates.update(df['date'].dt.strftime('%Y-%m-%d').tolist())
        
        all_dates = sorted(list(all_dates))
        
        market_returns = {}
        for date_str in all_dates:
            returns = []
            for df in all_dfs:
                date_rows = df[df['date'].dt.strftime('%Y-%m-%d') == date_str]
                if not date_rows.empty and len(date_rows) > 1:
                    ret = date_rows['close'].pct_change().iloc[-1]
                    if not pd.isna(ret):
                        returns.append(ret)
            if returns:
                market_returns[date_str] = np.mean(returns)
        
        sorted_dates = sorted(market_returns.keys())
        market_ma5 = {}
        market_ma20 = {}
        
        for i, date_str in enumerate(sorted_dates):
            if i >= 4:
                market_ma5[date_str] = np.mean([market_returns[d] for d in sorted_dates[i-4:i+1]])
            if i >= 19:
                market_ma20[date_str] = np.mean([market_returns[d] for d in sorted_dates[i-19:i+1]])
        
        for date_str in sorted_dates:
            if date_str in market_ma5 and date_str in market_ma20:
                ma5 = market_ma5[date_str]
                ma20 = market_ma20[date_str]
                
                if ma5 > ma20 and ma5 > 0:
                    market_trend[date_str] = 1.0
                elif ma5 > ma20:
                    market_trend[date_str] = 0.6
                elif ma5 > 0:
                    market_trend[date_str] = 0.4
                else:
                    market_trend[date_str] = 0.2
            elif date_str in market_ma5:
                market_trend[date_str] = 0.5 if market_ma5[date_str] > 0 else 0.3
            else:
                market_trend[date_str] = 0.5
        
        return market_trend
    
    def _backtest_single_stock(
        self,
        df: pd.DataFrame,
        stock_code: str,
        market_trend: Dict[str, float]
    ) -> List[float]:
        """单只股票回测 - 多策略融合"""
        daily_returns = []
        
        position = 0
        entry_price = 0
        entry_date = None
        entry_strategy = ""
        entry_atr = 0
        cash = 100000.0
        initial_cash = cash
        max_price = 0
        holding_days = 0
        
        for i in range(70, len(df)):
            row = df.iloc[i]
            date = row['date']
            close = row['close']
            ma5 = row['ma5']
            ma10 = row['ma10']
            ma20 = row['ma20']
            atr = row.get('atr', close * 0.02)
            atr_pct = row.get('atr_pct', 0.02)
            
            if pd.isna(ma5) or pd.isna(ma20):
                continue
            
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)[:10]
            mkt_trend = market_trend.get(date_str, 0.5)
            
            signal = None
            strategy_name = ""
            
            if position == 0:
                for strategy in self.selected_strategies:
                    sig = strategy.generate_signal(df, i, mkt_trend)
                    if sig:
                        signal = sig
                        strategy_name = strategy.get_name()
                        break
            
            if position > 0:
                holding_days += 1
                max_price = max(max_price, close)
                
                loss_pct = (close - entry_price) / entry_price
                drawdown = (max_price - close) / max_price
                
                atr_stop = entry_atr * 2.0 / entry_price if entry_atr > 0 else 0.05
                
                if loss_pct < -min(0.08, atr_stop * 1.5):
                    signal = 'sell_stop'
                elif loss_pct > min(0.15, atr_stop * 3):
                    signal = 'sell_take'
                elif close < ma5 * 0.94:
                    signal = 'sell_trend'
                elif drawdown > 0.08:
                    signal = 'sell_trailing'
                elif holding_days > 15:
                    signal = 'sell_time'
            
            if signal and signal.startswith('buy') and position == 0:
                risk_per_trade = 0.02
                stop_loss = min(0.06, atr_pct * 1.5) if atr_pct > 0 else 0.04
                position_size = (cash * risk_per_trade) / stop_loss
                shares = int(position_size / close / 100) * 100
                
                if shares > 0:
                    cost = shares * close * (1 + self.commission_rate + self.slippage_rate)
                    if cost <= cash * 0.90:
                        cash -= cost
                        position = shares
                        entry_price = close
                        entry_date = date
                        entry_strategy = strategy_name
                        entry_atr = atr
                        max_price = close
                        holding_days = 0
            
            elif signal and signal.startswith('sell') and position > 0:
                revenue = position * close * (1 - self.commission_rate - self.slippage_rate)
                profit = revenue - position * entry_price
                profit_pct = profit / (position * entry_price)
                
                self.trades.append({
                    'stock_code': stock_code,
                    'entry_date': entry_date,
                    'exit_date': date,
                    'entry_price': entry_price,
                    'exit_price': close,
                    'shares': position,
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'exit_reason': signal,
                    'strategy': entry_strategy,
                    'holding_days': holding_days
                })
                
                cash += revenue
                position = 0
                entry_price = 0
                entry_date = None
                entry_atr = 0
                max_price = 0
                holding_days = 0
            
            total_value = cash + position * close
            daily_return = (total_value - initial_cash) / initial_cash
            daily_returns.append(daily_return)
        
        return daily_returns
    
    def _calculate_metrics(self, all_daily_returns: List[float]) -> BacktestValidationResult:
        """计算回测指标"""
        if not all_daily_returns:
            return BacktestValidationResult(
                success=False,
                error_message="没有有效收益率数据"
            )
        
        returns_arr = np.array(all_daily_returns)
        
        final_return = returns_arr[-1] if len(returns_arr) > 0 else 0
        
        daily_rets = np.diff(returns_arr) if len(returns_arr) > 1 else np.array([0])
        daily_rets = daily_rets[~np.isnan(daily_rets)]
        
        if len(daily_rets) > 0:
            avg_daily_return = np.mean(daily_rets)
            volatility = np.std(daily_rets) * np.sqrt(252)
            
            annual_return = avg_daily_return * 252
            sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        else:
            annual_return = 0
            sharpe_ratio = 0
            volatility = 0
        
        cummax = np.maximum.accumulate(returns_arr)
        valid_mask = cummax > 0
        drawdown = np.zeros_like(returns_arr)
        drawdown[valid_mask] = (returns_arr[valid_mask] - cummax[valid_mask]) / cummax[valid_mask]
        max_drawdown = np.min(drawdown)
        max_drawdown = max(max_drawdown, -0.5)
        
        winning_trades = [t for t in self.trades if t['profit'] > 0]
        losing_trades = [t for t in self.trades if t['profit'] <= 0]
        
        total_trades = len(self.trades)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)
        
        win_rate = winning_count / total_trades if total_trades > 0 else 0
        
        total_profit = sum(t['profit'] for t in winning_trades)
        total_loss = abs(sum(t['profit'] for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf') if total_profit > 0 else 0
        
        avg_holding_days = 0
        if self.trades:
            avg_holding_days = np.mean([t['holding_days'] for t in self.trades])
        
        return BacktestValidationResult(
            success=True,
            total_return=final_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_count,
            losing_trades=losing_count,
            avg_holding_days=avg_holding_days
        )


_validator_instance: Optional[StrategyBacktestValidator] = None


def get_backtest_validator() -> StrategyBacktestValidator:
    """获取回测验证器单例"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = StrategyBacktestValidator()
    return _validator_instance


def validate_strategy(signal_data: Optional[Dict[str, Any]] = None) -> BacktestValidationResult:
    """验证策略"""
    validator = get_backtest_validator()
    return validator.validate(signal_data)
