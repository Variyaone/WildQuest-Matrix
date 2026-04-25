"""
混合策略：Grid Trend Filter Strategy V2

改进版本：
- 更激进的风险控制：检测到下跌趋势后立即清仓
- 改进的止盈机制
- 减少网格交易频率
- 避免在下跌市场中继续买入
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from backtest_engine import (
    BaseStrategy,
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    Position,
    Trade
)


class MarketState(Enum):
    """市场状态"""
    RANGE = "range"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"


@dataclass
class DailyPnL:
    """每日盈亏跟踪"""
    date: datetime
    start_equity: float
    losses: List[float] = field(default_factory=list)
    total_loss: float = 0.0
    stopped: bool = False


@dataclass
class GridTrade:
    """网格交易记录"""
    buy_price: float
    buy_quantity: float
    buy_time: datetime
    sell_price: Optional[float] = None
    sell_time: Optional[datetime] = None
    is_closed: bool = False


class GridTrendFilterStrategyV2(BaseStrategy):
    """
    网格趋势过滤策略 V2

    改进点：
    1. 更敏感的趋势检测
    2. 下跌趋势时立即清仓，不再买入
    3. 改进的网格逻辑，只在震荡市买入
    """

    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)

        # 趋势过滤器参数
        self.ma_short_period = params.get('ma_short_period', 20)
        self.ma_long_period = params.get('ma_long_period', 50)

        # 网格参数
        self.grid_count = params.get('grid_count', 6)
        self.investment_per_grid = params.get('investment_per_grid', 8000)
        self.price_range_pct = params.get('price_range_pct', 0.20)  # ±10%（缩小区间）
        self.symbol = params.get('symbol', 'BTC-USDT')

        # 风险控制参数
        self.hard_stop_loss_pct = params.get('hard_stop_loss_pct', 0.03)  # 硬止损 -3%
        self.trend_stop_threshold = params.get('trend_stop_threshold', 0.005)  # 趋势转向阈值 0.5%
        self.profit_target_pct = params.get('profit_target_pct', 0.02)  # 止盈目标 2%

        # 网格状态
        self.grid_levels = []
        self.grid_step = None
        self.low_price = None
        self.high_price = None

        # 网格交易记录
        self.grid_trades: List[GridTrade] = []
        self.last_buy_price = None
        self.last_sell_price = None
        self.buy_cooldown_until = None
        self.sell_cooldown_until = None

        # 持仓成本跟踪
        self.entry_costs = {}  # {symbol: {quantity: cost}}

        # 每日盈亏跟踪
        self.daily_pnl: Optional[DailyPnL] = None
        self.current_date = None

        # 市场状态
        self.current_market_state = MarketState.RANGE
        self.ma_short = None
        self.ma_long = None

        # 确保网格买入有冷却时间
        self.cooldown_bars = params.get('cooldown_bars', 24)  # 冷却24小时（24条数据）

    def detect_market_state(self, data: pd.DataFrame) -> MarketState:
        """
        检测市场状态（改进版）

        使用更敏感的趋势判断：
        - MA20 > MA50 * 1.005：上涨
        - MA20 < MA50 * 0.995：下跌
        - 其他：震荡

        Args:
            data: 历史数据

        Returns:
            市场状态
        """
        if len(data) < self.ma_long_period:
            return MarketState.RANGE

        # 计算MA
        ma_short = data['close'].rolling(window=self.ma_short_period).mean().iloc[-1]
        ma_long = data['close'].rolling(window=self.ma_long_period).mean().iloc[-1]
        current_price = data['close'].iloc[-1]

        # 保存MA值
        self.ma_short = ma_short
        self.ma_long = ma_long

        # 使用阈值进行判断
        ma_ratio = ma_short / ma_long

        if ma_ratio > (1 + self.trend_stop_threshold):
            return MarketState.TRENDING_UP
        elif ma_ratio < (1 - self.trend_stop_threshold):
            return MarketState.TRENDING_DOWN
        else:
            return MarketState.RANGE

    def check_stop_loss(
        self,
        positions: Dict[str, Position],
        current_prices: Dict[str, float]
    ) -> List[Order]:
        """
        检查止损和止盈

        Args:
            positions: 当前持仓
            current_prices: 当前价格

        Returns:
            订单列表
        """
        orders = []

        # 检查每日止损
        if self.daily_pnl and self.daily_pnl.stopped:
            # 已停止交易，只允许平仓
            pass

        # 检查趋势止损（最重要）
        if self.current_market_state == MarketState.TRENDING_DOWN:
            # 下跌趋势，立即清仓
            print(f"  [趋势止损] 检测到下跌趋势（MA20={self.ma_short:.2f} < MA50={self.ma_long:.2f}），清仓")
            for symbol, pos in positions.items():
                orders.append(Order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=pos.quantity,
                    timestamp=datetime.now()
                ))
            return orders

        # 检查止盈（针对网格交易）
        for symbol, pos in positions.items():
            if symbol not in self.entry_costs:
                continue

            entry_info = self.entry_costs[symbol]
            current_price = current_prices.get(symbol, pos.current_price)

            # 计算未实现盈亏百分比
            avg_entry_cost = entry_info['total_cost'] / entry_info['total_quantity']
            unrealized_pnl_pct = (current_price - avg_entry_cost) / avg_entry_cost

            # 止盈：盈利超过2%
            if unrealized_pnl_pct > self.profit_target_pct:
                print(f"  [止盈] {symbol} 盈利 {unrealized_pnl_pct*100:.2f}%，达到止盈目标")
                orders.append(Order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=pos.quantity,
                    timestamp=datetime.now()
                ))

        return orders

    def setup_grid(self, current_price: float) -> None:
        """
        设置网格区间和价格水平

        Args:
            current_price: 当前价格
        """
        # 计算价格区间
        self.high_price = current_price * (1 + self.price_range_pct / 2)
        self.low_price = current_price * (1 - self.price_range_pct / 2)

        # 计算网格间距
        self.grid_step = (self.high_price - self.low_price) / self.grid_count

        # 生成网格价格水平
        self.grid_levels = [self.low_price + i * self.grid_step for i in range(self.grid_count + 1)]

        # 清空网格交易记录
        self.grid_trades.clear()
        self.last_buy_price = None
        self.last_sell_price = None

        print(f"  [网格设置] 区间: ${self.low_price:.2f} - ${self.high_price:.2f}, 数量: {self.grid_count}, 间距: ${self.grid_step:.2f}")

    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        positions: Dict[str, Position],
        current_time: datetime
    ) -> List[Order]:
        """
        生成交易信号

        Args:
            data: 市场数据
            positions: 当前持仓
            current_time: 当前时间

        Returns:
            订单列表
        """
        orders = []

        if self.symbol not in data:
            return orders

        df = data[self.symbol]

        # 首次处理，初始化
        if self.current_date is None:
            self.current_date = current_time
            self.daily_pnl = DailyPnL(date=current_time, start_equity=0)
            self.setup_grid(df.iloc[-1]['close'])
            return orders

        # 检查是否是新的一天
        if current_time.date() != self.current_date.date():
            self.current_date = current_time
            self.daily_pnl = DailyPnL(date=current_time, start_equity=0)
            # 重置冷却时间
            self.buy_cooldown_until = None
            self.sell_cooldown_until = None
            print(f"  [新交易日] {current_time.date()}")

        # 检测市场状态
        self.current_market_state = self.detect_market_state(df)
        market_state_str = {
            MarketState.RANGE: "震荡",
            MarketState.TRENDING_UP: "上涨",
            MarketState.TRENDING_DOWN: "下跌"
        }[self.current_market_state]

        ma_short_str = f"{self.ma_short:.2f}" if self.ma_short is not None else "N/A"
        ma_long_str = f"{self.ma_long:.2f}" if self.ma_long is not None else "N/A"
        print(f"  [市场状态] {market_state_str} (MA20={ma_short_str}, MA50={ma_long_str})")

        current_price = df.iloc[-1]['close']

        # 检查冷却时间
        in_buy_cooldown = self.buy_cooldown_until is not None and current_time < self.buy_cooldown_until
        in_sell_cooldown = self.sell_cooldown_until is not None and current_time < self.sell_cooldown_until

        # 获取当前持仓
        current_position = positions.get(self.symbol)
        current_quantity = current_position.quantity if current_position else 0.0

        # 1. 首先检查止损和止盈
        stop_loss_orders = self.check_stop_loss(positions, {self.symbol: current_price})
        if stop_loss_orders:
            return stop_loss_orders

        # 2. 下跌趋势时，只允许卖出，不允许买入
        if self.current_market_state == MarketState.TRENDING_DOWN:
            print(f"  [下跌趋势] 禁止买入")
            return orders

        # 3. 检查每日是否已经停止交易
        if self.daily_pnl and self.daily_pnl.stopped:
            print(f"  [交易暂停] 已触发每日止损限制")
            return orders

        # 4. 检查网格区间
        if current_price < self.low_price * 0.9 or current_price > self.high_price * 1.1:
            # 价格超出范围，重新设置网格（但在趋势向下时不设置）
            if self.current_market_state != MarketState.TRENDING_DOWN:
                print(f"  [网格重置] 价格 ${current_price:.2f} 超出范围")
                self.setup_grid(current_price)
            return orders

        # 5. 网格交易逻辑（只在震荡和上涨市场）
        if self.current_market_state == MarketState.RANGE or self.current_market_state == MarketState.TRENDING_UP:
            # 检查是否超过网格范围
            if current_price < self.low_price or current_price > self.high_price:
                if self.current_market_state != MarketState.TRENDING_DOWN:
                    self.setup_grid(current_price)
                return orders

            # 寻找最近的网格线
            nearest_grid = min(self.grid_levels, key=lambda x: abs(x - current_price))
            distance_from_grid = abs(current_price - nearest_grid)

            # 买入信号：价格下跌到网格线附近且有持仓空间
            if (not in_buy_cooldown and
                current_quantity < 0.2 and  # 限制最大持仓
                distance_from_grid < self.grid_step * 0.3 and
                current_price < nearest_grid):  # 从下方接近

                # 检查是否已经在这个价格附近买入过
                recent_buy = any(
                    gt.buy_price is not None and
                    abs(gt.buy_price - current_price) < self.grid_step * 0.3 and
                    not gt.is_closed
                    for gt in self.grid_trades
                )

                if not recent_buy:
                    # 买入
                    buy_quantity = self.investment_per_grid / current_price

                    orders.append(Order(
                        symbol=self.symbol,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=buy_quantity,
                        timestamp=current_time
                    ))

                    # 记录网格交易
                    self.grid_trades.append(GridTrade(
                        buy_price=current_price,
                        buy_quantity=buy_quantity,
                        buy_time=current_time
                    ))

                    # 设置冷却时间
                    self.buy_cooldown_until = current_time + timedelta(hours=self.cooldown_bars)
                    print(f"  [网格买入] 价格 ${current_price:.2f}，数量 {buy_quantity:.4f}，冷却 {self.cooldown_bars}h")

            # 卖出信号：价格上涨到网格线附近且有持仓
            elif (not in_sell_cooldown and
                  current_quantity > 0 and
                  distance_from_grid < self.grid_step * 0.3 and
                  current_price > nearest_grid):  # 从下方接近

                # 检查是否有未平仓的网格交易
                for trade in self.grid_trades:
                    if (not trade.is_closed and
                        trade.buy_price is not None and
                        abs(trade.buy_price - current_price) < self.grid_step * 0.2):  # 接近买入价时卖出

                        # 卖出
                        sell_quantity = min(trade.buy_quantity, current_quantity)

                        orders.append(Order(
                            symbol=self.symbol,
                            side=OrderSide.SELL,
                            order_type=OrderType.MARKET,
                            quantity=sell_quantity,
                            timestamp=current_time
                        ))

                        # 关闭网格交易
                        trade.sell_price = current_price
                        trade.sell_time = current_time
                        trade.is_closed = True

                        # 设置冷却时间
                        self.sell_cooldown_until = current_time + timedelta(hours=self.cooldown_bars)
                        print(f"  [网格卖出] 价格 ${current_price:.2f}，数量 {sell_quantity:.4f}，收益 {(current_price/trade.buy_price-1)*100:.2f}%")
                        break

        return orders

    def on_trade(self, trade: Trade):
        """
        成交回调

        Args:
            trade: 成交记录
        """
        # 记录持仓成本
        if trade.side == OrderSide.BUY:
            if trade.symbol not in self.entry_costs:
                self.entry_costs[trade.symbol] = {
                    'total_quantity': 0.0,
                    'total_cost': 0.0
                }

            cost = trade.quantity * trade.price + trade.commission
            self.entry_costs[trade.symbol]['total_quantity'] += trade.quantity
            self.entry_costs[trade.symbol]['total_cost'] += cost

        elif trade.side == OrderSide.SELL:
            # 记录每日盈亏
            if trade.symbol in self.entry_costs:
                avg_cost_per_unit = (
                    self.entry_costs[trade.symbol]['total_cost'] /
                    self.entry_costs[trade.symbol]['total_quantity']
                )
                realized_pnl = (trade.price - avg_cost_per_unit) * trade.quantity - trade.commission

                if self.daily_pnl:
                    self.daily_pnl.total_loss += realized_pnl

                # 从entry_costs中扣除
                cost_basis = avg_cost_per_unit * trade.quantity
                self.entry_costs[trade.symbol]['total_quantity'] -= trade.quantity
                self.entry_costs[trade.symbol]['total_cost'] -= cost_basis

                if self.entry_costs[trade.symbol]['total_quantity'] <= 0.001:
                    del self.entry_costs[trade.symbol]

    def on_order_filled(self, order: Order):
        """订单成交回调"""
        pass
