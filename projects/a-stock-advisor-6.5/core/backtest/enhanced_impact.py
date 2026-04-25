"""
改进的市场冲击成本模型

基于股票市值、波动率、流动性等多因子计算市场冲击成本。
"""

from dataclasses import dataclass
from typing import Dict, Optional, Any
from datetime import date
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class MarketImpactParams:
    """市场冲击参数"""
    base_impact: float = 0.001
    size_coefficient: float = 0.1
    volatility_coefficient: float = 0.05
    liquidity_coefficient: float = 0.03
    market_cap_coefficient: float = 0.02
    bid_ask_coefficient: float = 0.01


class EnhancedMarketImpactModel:
    """
    增强版市场冲击模型
    
    基于多因子计算市场冲击成本：
    1. 交易规模因子
    2. 波动率因子
    3. 流动性因子
    4. 市值因子
    5. 买卖价差因子
    """
    
    def __init__(self, params: Optional[MarketImpactParams] = None):
        """
        初始化市场冲击模型
        
        Args:
            params: 市场冲击参数
        """
        self.params = params or MarketImpactParams()
    
    def calculate_market_impact(
        self,
        trade_value: float,
        avg_daily_volume: float,
        avg_daily_amount: float,
        volatility: float = 0.02,
        market_cap: Optional[float] = None,
        bid_ask_spread: Optional[float] = None,
        participation_rate: Optional[float] = None
    ) -> float:
        """
        计算市场冲击成本
        
        Args:
            trade_value: 交易金额
            avg_daily_volume: 日均成交量
            avg_daily_amount: 日均成交额
            volatility: 波动率（日度）
            market_cap: 市值
            bid_ask_spread: 买卖价差
            participation_rate: 参与率
            
        Returns:
            float: 市场冲击成本（金额）
        """
        if participation_rate is None:
            participation_rate = trade_value / avg_daily_amount if avg_daily_amount > 0 else 0.01
        
        size_impact = self._calculate_size_impact(participation_rate)
        
        volatility_impact = self._calculate_volatility_impact(volatility)
        
        liquidity_impact = self._calculate_liquidity_impact(avg_daily_amount)
        
        market_cap_impact = self._calculate_market_cap_impact(market_cap)
        
        bid_ask_impact = self._calculate_bid_ask_impact(bid_ask_spread)
        
        total_impact_rate = (
            self.params.base_impact +
            size_impact * self.params.size_coefficient +
            volatility_impact * self.params.volatility_coefficient +
            liquidity_impact * self.params.liquidity_coefficient +
            market_cap_impact * self.params.market_cap_coefficient +
            bid_ask_impact * self.params.bid_ask_coefficient
        )
        
        total_impact_rate = min(total_impact_rate, 0.10)
        
        market_impact = trade_value * total_impact_rate
        
        return market_impact
    
    def _calculate_size_impact(self, participation_rate: float) -> float:
        """计算规模冲击"""
        if participation_rate <= 0:
            return 0.0
        
        return np.sqrt(participation_rate) * 2
    
    def _calculate_volatility_impact(self, volatility: float) -> float:
        """计算波动率冲击"""
        if volatility <= 0:
            return 0.0
        
        return volatility * 10
    
    def _calculate_liquidity_impact(self, avg_daily_amount: float) -> float:
        """计算流动性冲击"""
        if avg_daily_amount <= 0:
            return 1.0
        
        if avg_daily_amount >= 1e9:
            return 0.0
        elif avg_daily_amount >= 5e8:
            return 0.2
        elif avg_daily_amount >= 1e8:
            return 0.5
        elif avg_daily_amount >= 5e7:
            return 0.8
        else:
            return 1.0
    
    def _calculate_market_cap_impact(self, market_cap: Optional[float]) -> float:
        """计算市值冲击"""
        if market_cap is None or market_cap <= 0:
            return 0.5
        
        if market_cap >= 1e11:
            return 0.0
        elif market_cap >= 5e10:
            return 0.2
        elif market_cap >= 1e10:
            return 0.5
        elif market_cap >= 5e9:
            return 0.8
        else:
            return 1.0
    
    def _calculate_bid_ask_impact(self, bid_ask_spread: Optional[float]) -> float:
        """计算买卖价差冲击"""
        if bid_ask_spread is None or bid_ask_spread <= 0:
            return 0.0
        
        return bid_ask_spread * 100
    
    def calculate_impact_from_market_data(
        self,
        stock_code: str,
        trade_value: float,
        target_date: date,
        market_data: pd.DataFrame,
        stock_col: str = "stock_code",
        date_col: str = "date",
        amount_col: str = "amount",
        volume_col: str = "volume",
        close_col: str = "close",
        high_col: str = "high",
        low_col: str = "low"
    ) -> float:
        """
        从市场数据计算市场冲击
        
        Args:
            stock_code: 股票代码
            trade_value: 交易金额
            target_date: 目标日期
            market_data: 市场数据
            stock_col: 股票代码列名
            date_col: 日期列名
            amount_col: 成交额列名
            volume_col: 成交量列名
            close_col: 收盘价列名
            high_col: 最高价列名
            low_col: 最低价列名
            
        Returns:
            float: 市场冲击成本
        """
        stock_data = market_data[market_data[stock_col] == stock_code].copy()
        
        if len(stock_data) == 0:
            logger.warning(f"未找到股票 {stock_code} 的市场数据")
            return trade_value * 0.01
        
        historical_data = stock_data[stock_data[date_col] < target_date].tail(20)
        
        if len(historical_data) == 0:
            return trade_value * 0.01
        
        avg_daily_amount = historical_data[amount_col].mean() if amount_col in historical_data.columns else 1e8
        avg_daily_volume = historical_data[volume_col].mean() if volume_col in historical_data.columns else 1e7
        
        if close_col in historical_data.columns:
            returns = historical_data[close_col].pct_change().dropna()
            volatility = returns.std() if len(returns) > 0 else 0.02
        else:
            volatility = 0.02
        
        if high_col in historical_data.columns and low_col in historical_data.columns and close_col in historical_data.columns:
            last_row = historical_data.iloc[-1]
            bid_ask_spread = (last_row[high_col] - last_row[low_col]) / last_row[close_col]
        else:
            bid_ask_spread = None
        
        return self.calculate_market_impact(
            trade_value=trade_value,
            avg_daily_volume=avg_daily_volume,
            avg_daily_amount=avg_daily_amount,
            volatility=volatility,
            bid_ask_spread=bid_ask_spread
        )


def create_enhanced_impact_model(params: Optional[MarketImpactParams] = None) -> EnhancedMarketImpactModel:
    """创建增强版市场冲击模型"""
    return EnhancedMarketImpactModel(params)
