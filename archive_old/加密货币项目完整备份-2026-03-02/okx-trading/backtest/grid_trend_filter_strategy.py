"""
混合策略：Grid Trend Filter Strategy

结合趋势过滤和网格交易的核心策略设计：

核心思路：
- 震荡市场：使用网格策略，在价格区间内低买高卖
- 上涨趋势：可使用网格策略，但需要设置止盈
- 下跌趋势：禁用网格，空仓或清仓保护资金

风险控制：
- 硬止损：单笔交易亏损超过5%时强制止损
- 每日止损：当日累计亏损超过3%时停止交易
- 趋势保护：MA20 < MA50时清仓

参数：
- MA短期：20日
- MA长期：50日
- 网格数量：6-8格降低频率
- 价格区间：±15%扩大区间
- 单格金额：$8,000
- 硬止损：-5%
- 每日止损：-3%
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
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
    RANGE = "range"             # 震荡
    TRENDING_UP = "trending_up"  # 上涨
    TRENDING_DOWN = "trending_down"  # 下跌


@dataclass
class DailyPnL:
    """每日盈亏跟踪"""
    date: datetime
    start_equity: float
    losses: List[float] = None
    total_loss: float = 0.0
    stopped: bool = False

    def __post_init__(self):
        if self.losses is None:
            self.losses = []


class GridTrendFilterStrategy(BaseStrategy):
    """
    网格趋势过滤策略

    在震荡市场使用网格策略，在趋势市场切换到保护模式
    """

    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)

        # 趋势过滤器参数
        self.ma_short_period = params.get('ma_short_period', 20)
        self.ma_long_period = params.get('ma_long_period', 50)

        # 网格参数
        self.grid_count = params.get('grid_count', 6)
        self.investment_per_grid = params.get('investment_per_grid', 8000)
        self.price_range_pct = params.get('price_range_pct', 0.30)  # ±15%
        self.symbol = params.get('symbol', 'BTC-USDT')

        # 止损参数
        self.hard_stop_loss_pct = params.get('hard_stop_loss_pct', 0.05)  # 硬止损 -5%
        self.daily_stop_loss_pct = params.get('daily_stop_loss_pct', 0.03)  # 每日止损 -3%

        # 网格状态
        self.grid_levels = []
        self.grid_step = None
        self.low_price = None
        self.high_price = None
        self.grid_buy_prices = set()  # 已买入的网格价格
        self.grid_sell_prices = set()  # 已卖出的网格价格

        # 持仓成本跟踪（用于止损）
        self.entry_costs = {}  # {symbol: {quantity: cost}}

        # 每日盈亏跟踪
        self.daily_pnl = None
        self.current_date = None

        # 市场状态
        self.current_market_state = MarketState.RANGE
        self.ma_short = None
        self.ma_long = None

        # 已处理的价格（用于避免重复触发）
        self.closed_positions_history = []

    def detect_market_state(self, data: pd.DataFrame) -> MarketState:
        """
        检测市场状态

        使用MA判断趋势：
        - MA20 > MA50：上涨
        - MA20 < MA50：下跌
        - 价格在MA20和MA50之间接近：震荡

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

        # 判断市场状态
        ma_diff_pct = abs(ma_short - ma_long) / ma_long if ma_long > 0 else 0

        if ma_diff_pct < 0.01:  # MA相差小于1%，视为震荡
            return MarketState.RANGE
        elif ma_short > ma_long:
            return MarketState.TRENDING_UP
        else:
            return MarketState.TRENDING_DOWN

    def should_enable_grid(self, market_state: MarketState) -> bool:
        """
        判断是否启用网格策略

        Args:
            market_state: 市场状态

        Returns:
            是否启用网格
        """
        if market_state == MarketState.TRENDING_DOWN:
            return False  # 下跌市场禁用网格
        else:
            return True  # 震荡和上涨市场可以使用网格

    def check_stop_loss(
        self,
        positions: Dict[str, Position],
        current_prices: Dict[str, float]
    ) -> List[Order]:
        """
        检查止损

        包括：
        1. 硬止损：单笔交易亏损超过5%时强制止损
        2. 趋势止损：MA20 < MA50时清仓
        3. 每日止损：当日累计亏损超过3%时停止交易

        Args:
            positions: 当前持仓
            current_prices: 当前价格

        Returns:
            止损订单列表
        """
        orders = []

        # 检查每日止损
        if self.daily_pnl and self.daily_pnl.stopped:
            return orders  # 已停止交易，不生成新订单

        # 检查趋势止损（更重要的保护）
        if self.current_market_state == MarketState.TRENDING_DOWN:
            # 下跌趋势，清仓
            print(f"  [趋势止损] 检测到下跌趋势（MA20={self.ma_short:.2f} < MA50={self.ma_long:.2f}），清仓保护")
            for symbol, pos in positions.items():
                current_price = current_prices.get(symbol, pos.current_price)
                orders.append(Order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=pos.quantity,
                    timestamp=datetime.now()
                ))
            return orders

        # 检查硬止损
        for symbol, pos in positions.items():
            if symbol not in self.entry_costs:
                continue

            entry_info = self.entry_costs[symbol]
            current_price = current_prices.get(symbol, pos.current_price)

            # 计算未实现盈亏百分比
            avg_entry_cost = entry_info['total_cost'] / entry_info['total_quantity']
            unrealized_pnl_pct = (current_price - avg_entry_cost) / avg_entry_cost

            # 硬止损：亏损超过5%
            if unrealized_pnl_pct < -self.hard_stop_loss_pct:
                print(f"  [硬止损] {symbol} 亏损 {unrealized_pnl_pct*100:.2f}%，触发止损")
                orders.append(Order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=pos.quantity,
                    timestamp=datetime.now()
                ))

        return orders

    def check_daily_loss_limit(self, daily_equity_start: float, current_equity: float) -> bool:
        """
        检查每日亏损限制

        Args:
            daily_equity_start: 每日权益起始值
            current_equity: 当前权益

        Returns:
            是否应该停止交易
        """
        daily_pnl_pct = (current_equity - daily_equity_start) / daily_equity_start

        if daily_pnl_pct < -self.daily_stop_loss_pct:
            print(f"  [每日止损] 当日亏损 {daily_pnl_pct*100:.2f}% 超过限制 {self.daily_stop_loss_pct*100:.2f}%，停止交易")
            if self.daily_pnl:
                self.daily_pnl.stopped = True
            return True

        return False

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

        # 清空历史记录
        self.grid_buy_prices.clear()
        self.grid_sell_prices.clear()

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

        # 首次处理，初始化每日盈亏跟踪
        if self.current_date is None:
            self.current_date = current_time
            self.daily_pnl = DailyPnL(date=current_time, start_equity=0)
            # 初始化网格（使用收盘价）
            self.setup_grid(df.iloc[-1]['close'])
            return orders

        # 检查是否是新的一天
        if current_time.date() != self.current_date.date():
            # 新的一天，重置每日盈亏跟踪
            self.current_date = current_time
            self.daily_pnl = DailyPnL(date=current_time, start_equity=0)
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

        # 获取当前价格字典（用于止损检查）
        current_prices = {self.symbol: current_price}

        # 1. 首先检查止损
        stop_loss_orders = self.check_stop_loss(positions, current_prices)
        if stop_loss_orders:
            print(f"  [止损触发] 生成了 {len(stop_loss_orders)} 个止损订单")
            return stop_loss_orders

        # 2. 检查是否应该启用网格
        if not self.should_enable_grid(self.current_market_state):
            print(f"  [策略暂停] 市场状态为 {market_state_str}，禁用网格交易")
            return orders

        # 3. 检查每日是否已经停止交易
        if self.daily_pnl and self.daily_pnl.stopped:
            print(f"  [交易暂停] 已触发每日止损限制")
            return orders

        # 4. 检查是否超出网格范围
        if current_price < self.low_price or current_price > self.high_price:
            # 价格超出范围，重新设置网格
            print(f"  [网格重置] 价格 ${current_price:.2f} 超出范围，重新设置网格...")
            self.setup_grid(current_price)
            return orders

        # 获取当前持仓
        current_position = positions.get(self.symbol)
        current_quantity = current_position.quantity if current_position else 0.0

        # 5. 网格交易逻辑
        for i, level_price in enumerate(self.grid_levels):
            # 计算该网格的价格区间
            range_min = level_price - self.grid_step * 0.5
            range_max = level_price + self.grid_step * 0.5

            # 买入信号：价格下跌到网格线附近
            if range_min <= current_price <= level_price + self.grid_step * 0.3:
                # 检查是否已经在该价格附近买入过（冷却机制）
                if not self._bought_near_priceRecently(level_price, self.grid_step * 0.3):
                    # 计算买入数量
                    buy_quantity = self.investment_per_grid / level_price

                    # 限制单次买入不超过总资金的10%
                    # 这里我们简单使用固定金额
                    # 生成买入订单
                    orders.append(Order(
                        symbol=self.symbol,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=buy_quantity,
                        timestamp=current_time
                    ))
                    self.grid_buy_prices.add(level_price)
                    print(f"  [网格买入] 价格 ${current_price:.2f} 接近网格 ${level_price:.2f}, 买入 {buy_quantity:.4f}")

            # 卖出信号：价格上涨到网格线附近
            elif level_price - self.grid_step * 0.3 <= current_price <= range_max:
                # 检查是否在该价格附近卖出过
                if not self._sold_near_priceRecently(level_price, self.grid_step * 0.3):
                    # 检查是否有足够持仓
                    if current_quantity > 0:
                        # 计算卖出数量（1格的数量）
                        sell_quantity = self.investment_per_grid / level_price
                        sell_quantity = min(sell_quantity, current_quantity)

                        # 生成卖出订单
                        orders.append(Order(
                            symbol=self.symbol,
                            side=OrderSide.SELL,
                            order_type=OrderType.MARKET,
                            quantity=sell_quantity,
                            timestamp=current_time
                        ))
                        self.grid_sell_prices.add(level_price)
                        print(f"  [网格卖出] 价格 ${current_price:.2f} 接近网格 ${level_price:.2f}, 卖出 {sell_quantity:.4f}")

        return orders

    def _bought_near_priceRecently(self, price: float, tolerance: float) -> bool:
        """检查是否在价格附近最近买入过"""
        for buy_price in self.grid_buy_prices:
            if abs(buy_price - price) < tolerance:
                return True
        return False

    def _sold_near_priceRecently(self, price: float, tolerance: float) -> bool:
        """检查是否在价格附近最近卖出过"""
        for sell_price in self.grid_sell_prices:
            if abs(sell_price - price) < tolerance:
                return True
        return False

    def on_trade(self, trade: Trade):
        """
        成交回调

        跟踪持仓成本和每日盈亏

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
            # 从entry_costs中扣除
            if trade.symbol in self.entry_costs:
                # 计算该笔交易对应的成本
                cost = trade.quantity * trade.price - trade.commission

                # 实现盈亏
                if trade.symbol in self.entry_costs:
                    avg_cost_per_unit = (
                        self.entry_costs[trade.symbol]['total_cost'] /
                        self.entry_costs[trade.symbol]['total_quantity']
                    )
                    realized_pnl = (trade.price - avg_cost_per_unit) * trade.quantity - trade.commission

                    # 记录到每日盈亏
                    if realized_pnl < 0:
                        self.daily_pnl.losses.append(realized_pnl)
                        self.daily_pnl.total_loss += realized_pnl

                    # 从entry_costs中扣除
                    cost_basis = avg_cost_per_unit * trade.quantity
                    self.entry_costs[trade.symbol]['total_quantity'] -= trade.quantity
                    self.entry_costs[trade.symbol]['total_cost'] -= cost_basis

                    # 如果清仓，移除entry_costs
                    if self.entry_costs[trade.symbol]['total_quantity'] <= 0:
                        del self.entry_costs[trade.symbol]

    def on_order_filled(self, order: Order):
        """
        订单成交回调

        清理网格交易记录

        Args:
            order: 已成交订单
        """
        # 清除对应的价格记录，允许再次触发
        current_price = order.filled_price

        # 清除买入记录
        to_remove_buy = []
        for buy_price in self.grid_buy_prices:
            if abs(buy_price - current_price) < self.grid_step * 0.3:
                to_remove_buy.append(buy_price)
        for price in to_remove_buy:
            self.grid_buy_prices.remove(price)

        # 清除卖出记录
        to_remove_sell = []
        for sell_price in self.grid_sell_prices:
            if abs(sell_price - current_price) < self.grid_step * 0.3:
                to_remove_sell.append(sell_price)
        for price in to_remove_sell:
            self.grid_sell_prices.remove(price)
