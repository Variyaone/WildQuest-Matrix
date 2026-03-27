"""
趋势增强网格策略 (Trend-Enhanced Grid Strategy)

在网格基础上叠加趋势信号，趋势方向增加仓位，逆趋势减少仓位。
"""
import sys
import os

# 添加回测引擎路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backtest_engine import BaseStrategy, Order, OrderSide, OrderType
from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime
import numpy as np


@dataclass
class TrendState:
    """趋势状态"""
    regime: str  # 'bullish', 'bearish', 'neutral'
    ma_fast: float
    ma_slow: float
    ma_slope: float
    trend_start_time: Optional[datetime]
    trend_base_price: float
    trend_highest_price: float
    trend_start_price: Optional[float] = None  # 趋势开始时的价格，用于计算趋势收益


@dataclass
class GridState:
    """网格状态"""
    low_price: float
    high_price: float
    grid_step: float
    grid_levels: list
    active_orders: dict  # {price: OrderSide}


class TrendEnhancedGridStrategy(BaseStrategy):
    """
    趋势增强网格策略

    策略逻辑：
    1. 计算MA(10)和MA(30)以及MA斜率判断趋势
    2. 根据趋势调整网格仓位：
       - 强上涨趋势(MA斜率>0.5%)：网格仓位×1.5
       - 震荡/弱趋势：网格仓位×1.0（标准）
       - 强下跌趋势(MA斜率<-0.5%)：网格仓位×0.5
    3. 趋势止盈：趋势结束后，+5%利润时全部平仓
    4. 止损：-10%硬止损
    """

    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)

        # 基础参数
        self.symbol = params.get('symbol', 'BTC-USDT')
        self.base_grid_count = params.get('grid_count', 8)  # 基础网格数量
        self.base_price_range_pct = params.get('price_range_pct', 0.10)  # 基础价格区间
        self.base_investment_per_grid = params.get('investment_per_grid', 10000)  # 基础每格金额

        # 趋势参数
        self.ma_fast_period = params.get('ma_fast_period', 10)  # 快MA周期
        self.ma_slow_period = params.get('ma_slow_period', 30)  # 慢MA周期
        self.trend_up_threshold = params.get('trend_up_threshold', 0.005)  # 上涨趋势阈值 0.5%
        self.trend_down_threshold = params.get('trend_down_threshold', -0.005)  # 下跌趋势阈值 -0.5%
        self.position_multiplier_up = params.get('position_multiplier_up', 1.5)  # 上涨趋势仓位倍数
        self.position_multiplier_down = params.get('position_multiplier_down', 0.5)  # 下跌趋势仓位倍数
        self.trend_take_profit_pct = params.get('trend_take_profit_pct', 0.05)  # 趋势止盈比例 +5%

        # 停损参数
        self.stop_loss_pct = params.get('stop_loss_pct', -0.10)  # 止损比例 -10%
        self.min_interval = params.get('min_interval', 24)  # 最小交易间隔（小时）

        # 趋势确认参数
        self.trend_confirmation_period = params.get('trend_confirmation_period', 2)  # 2根K线确认

        # 状态变量
        self.trend_state: Optional[TrendState] = None
        self.grid_state: Optional[GridState] = None

        # 趋势确认历史
        self.trend_confirmation_history = []  # 最近N根K线的趋势判断

        # 交易记录
        self.last_trade_time = None
        self.trend_start_price = None  # 趋势开始时的价格，用于计算趋势收益

    def _calculate_ma(self, data: pd.DataFrame, period: int) -> float:
        """
        计算移动平均线

        Args:
            data: 历史K线数据
            period: MA周期

        Returns:
            MA值
        """
        if len(data) < period:
            return data['close'].iloc[-1]

        ma = data['close'].rolling(window=period).mean()
        return ma.iloc[-1]

    def _calculate_trend(self, data: pd.DataFrame) -> TrendState:
        """
        计算趋势状态

        Args:
            data: 历史K线数据

        Returns:
            趋势状态
        """
        if len(data) < max(self.ma_fast_period, self.ma_slow_period):
            return TrendState(
                regime='neutral',
                ma_fast=data['close'].iloc[-1],
                ma_slow=data['close'].iloc[-1],
                ma_slope=0.0,
                trend_start_time=None,
                trend_base_price=data['close'].iloc[-1],
                trend_highest_price=data['close'].iloc[-1]
            )

        # 计算MA
        ma_fast = self._calculate_ma(data, self.ma_fast_period)
        ma_slow = self._calculate_ma(data, self.ma_slow_period)

        # 计算MA斜率 (相对于慢MA的百分比变化)
        ma_slope = (ma_fast - ma_slow) / ma_slow if ma_slow > 0 else 0.0

        # 判断趋势regime
        if ma_slope > self.trend_up_threshold:
            regime = 'bullish'
        elif ma_slope < self.trend_down_threshold:
            regime = 'bearish'
        else:
            regime = 'neutral'

        # 检查趋势是否发生切换
        if self.trend_state:
            # 趋势切换
            if regime != self.trend_state.regime:
                # 新趋势开始
                trend_start_time = data.index[-1]
                trend_base_price = data['close'].iloc[-1]
                trend_highest_price = data['close'].iloc[-1]
                self.trend_start_price = trend_base_price
            else:
                # 趋势延续
                trend_start_time = self.trend_state.trend_start_time
                trend_base_price = self.trend_state.trend_base_price
                # 更新最高价（仅上涨趋势）
                if regime == 'bullish':
                    trend_highest_price = max(self.trend_state.trend_highest_price, data['close'].iloc[-1])
                else:
                    trend_highest_price = self.trend_state.trend_highest_price
        else:
            # 初始趋势
            trend_start_time = data.index[-1]
            trend_base_price = data['close'].iloc[-1]
            trend_highest_price = data['close'].iloc[-1]
            self.trend_start_price = trend_base_price

        return TrendState(
            regime=regime,
            ma_fast=ma_fast,
            ma_slow=ma_slow,
            ma_slope=ma_slope,
            trend_start_time=trend_start_time,
            trend_base_price=trend_base_price,
            trend_highest_price=trend_highest_price
        )

    def _get_position_multiplier(self, regime: str) -> float:
        """
        根据趋势regime获取仓位倍数

        Args:
            regime: 趋势regime

        Returns:
            仓位倍数
        """
        if regime == 'bullish':
            return self.position_multiplier_up
        elif regime == 'bearish':
            return self.position_multiplier_down
        else:
            return 1.0

    def _check_trend_take_profit(
        self,
        current_price: float,
        trend_state: TrendState,
        positions: Dict[str, Any]
    ) -> bool:
        """
        检查趋势止盈

        Args:
            current_price: 当前价格
            trend_state: 趋势状态
            positions: 当前持仓

        Returns:
            是否触发趋势止盈
        """
        if not trend_state.trend_start_price:
            return False

        # 计算趋势收益
        trend_return = (current_price - trend_state.trend_start_price) / trend_state.trend_start_price

        # 只有上涨趋势才触发趋势止盈
        if trend_state.regime == 'bullish' and trend_return >= self.trend_take_profit_pct:
            # 检查是否有持仓
            position = positions.get(self.symbol)
            if position and position.quantity > 0:
                return True

        return False

    def _check_stop_loss(self, current_price: float, positions: Dict[str, Any]) -> bool:
        """
        检查止损

        Args:
            current_price: 当前价格
            positions: 当前持仓

        Returns:
            是否触发止损
        """
        if not positions:
            return False

        position = positions.get(self.symbol)
        if not position or position.quantity <= 0:
            return False

        # 计算持仓盈亏比例
        pnl_pct = (current_price - position.avg_price) / position.avg_price

        return pnl_pct <= self.stop_loss_pct

    def _setup_grid(self, current_price: float, current_time: datetime):
        """
        设置网格

        Args:
            current_price: 当前价格
            current_time: 当前时间
        """
        # 计算价格区间
        high_price = current_price * (1 + self.base_price_range_pct / 2)
        low_price = current_price * (1 - self.base_price_range_pct / 2)

        # 计算网格间距
        grid_step = (high_price - low_price) / self.base_grid_count

        # 生成网格价格水平
        grid_levels = [low_price + i * grid_step for i in range(self.base_grid_count + 1)]

        # 保存网格状态
        self.grid_state = GridState(
            low_price=low_price,
            high_price=high_price,
            grid_step=grid_step,
            grid_levels=grid_levels,
            active_orders={}
        )

        # print(f"[{current_time}] 趋势网格设置完成: "
        #       f"价格区间 ${low_price:.2f} - ${high_price:.2f}, "
        #       f"网格数量 {self.base_grid_count}, "
        #       f"网格间距 ${grid_step:.2f}")

    def _check_min_interval(self, current_time: datetime) -> bool:
        """
        检查最小交易间隔

        Args:
            current_time: 当前时间

        Returns:
            是否可以交易
        """
        if self.last_trade_time is None:
            return True

        interval_hours = (current_time - self.last_trade_time).total_seconds() / 3600
        return interval_hours >= self.min_interval

    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        positions: Dict[str, Any],
        current_time: datetime
    ) -> list:
        """
        生成交易信号

        Args:
            data: 市场数据 {symbol: DataFrame}
            positions: 当前持仓
            current_time: 当前时间

        Returns:
            订单列表
        """
        orders = []

        if self.symbol not in data:
            return orders

        df = data[self.symbol]
        if len(df) < max(self.ma_fast_period, self.ma_slow_period) + 1:
            return orders

        current_price = float(df['close'].iloc[-1])

        # 计算趋势
        trend_state = self._calculate_trend(df)
        self.trend_state = trend_state

        # 检查止损
        if self._check_stop_loss(current_price, positions):
            # 止损：全部平仓
            position = positions.get(self.symbol)
            if position and position.quantity > 0:
                orders.append(Order(
                    symbol=self.symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=position.quantity,
                    timestamp=current_time
                ))
                # 重置网格和趋势
                self.grid_state = None
                self.trend_start_price = None
                self.last_trade_time = current_time
            return orders

        # 检查趋势止盈
        if self._check_trend_take_profit(current_price, trend_state, positions):
            # 趋势止盈：全部平仓
            position = positions.get(self.symbol)
            if position and position.quantity > 0:
                orders.append(Order(
                    symbol=self.symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=position.quantity,
                    timestamp=current_time
                ))
                # 重置网格和趋势
                self.grid_state = None
                self.trend_start_price = None
                self.last_trade_time = current_time
                # print(f"[{current_time}] 趋势止盈触发，全部平仓")
            return orders

        # 首次设置网格
        if self.grid_state is None:
            self._setup_grid(current_price, current_time)
            return orders

        # 检查是否超出网格范围
        if current_price < self.grid_state.low_price or current_price > self.grid_state.high_price:
            # 价格超出范围，重新设置网格
            self._setup_grid(current_price, current_time)
            self._setup_grid(current_price, current_time)
            return orders

        # 检查最小交易间隔
        if not self._check_min_interval(current_time):
            return orders

        # 获取当前持仓
        current_position = positions.get(self.symbol)
        current_quantity = current_position.quantity if current_position else 0.0

        # 获取仓位倍数
        position_multiplier = self._get_position_multiplier(trend_state.regime)
        base_investment = self.base_investment_per_grid * position_multiplier

        # 检查是否触碰到网格线
        for i, level_price in enumerate(self.grid_state.grid_levels[:-1]):
            # 买入信号：价格下跌到网格线（从上方接近）
            if current_price <= level_price and current_price >= level_price - self.grid_state.grid_step:
                # 检查是否已经在该价格附近买入过
                if not self._bought_near_price(level_price):
                    # 计算买入数量
                    buy_quantity = base_investment / level_price

                    # 生成买入订单
                    orders.append(Order(
                        symbol=self.symbol,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=buy_quantity,
                        timestamp=current_time
                    ))
                    self.grid_state.active_orders[level_price] = OrderSide.BUY
                    self.last_trade_time = current_time

            # 卖出信号：价格上涨到网格线（从下方接近）
            if current_price >= level_price and current_price <= level_price + self.grid_state.grid_step:
                # 检查是否在该价格附近卖出过
                if not self._sold_near_price(level_price):
                    # 检查是否有足够持仓
                    if current_quantity > 0:
                        # 计算卖出数量（每次卖出1格的数量）
                        sell_quantity = base_investment / level_price
                        sell_quantity = min(sell_quantity, current_quantity)

                        # 生成卖出订单
                        orders.append(Order(
                            symbol=self.symbol,
                            side=OrderSide.SELL,
                            order_type=OrderType.MARKET,
                            quantity=sell_quantity,
                            timestamp=current_time
                        ))
                        self.grid_state.active_orders[level_price] = OrderSide.SELL
                        self.last_trade_time = current_time

        return orders

    def _bought_near_price(self, price: float) -> bool:
        """检查是否在价格附近买入过"""
        tolerance = self.grid_state.grid_step * 0.5
        for active_price, side in self.grid_state.active_orders.items():
            if side == OrderSide.BUY and abs(active_price - price) < tolerance:
                return True
        return False

    def _sold_near_price(self, price: float) -> bool:
        """检查是否在价格附近卖出过"""
        tolerance = self.grid_state.grid_step * 0.5
        for active_price, side in self.grid_state.active_orders.items():
            if side == OrderSide.SELL and abs(active_price - price) < tolerance:
                return True
        return False
