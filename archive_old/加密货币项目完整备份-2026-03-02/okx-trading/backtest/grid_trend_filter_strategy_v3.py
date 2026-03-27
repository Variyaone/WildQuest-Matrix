"""
混合策略：Grid Trend Filter Strategy V3

终极版本：
- 只在明确上涨趋势中交易网格
- 震荡市场中减少交易频率
- 下跌市场完全空仓
- 更严格的止盈止损
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


class GridTrendFilterStrategyV3(BaseStrategy):
    """
    网格趋势过滤策略 V3

    核心思路：只在盈利概率高的条件下交易

    规则：
    1. 下跌趋势：完全空仓，不交易
    2. 震荡市场：谨慎交易，大幅减少频率
    3. 上涨趋势：积极使用网格策略
    4. 严格的止盈止损：止盈3%，止损-2%
    """

    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)

        # 趋势过滤器参数
        self.ma_short_period = params.get('ma_short_period', 20)
        self.ma_long_period = params.get('ma_long_period', 50)

        # 网格参数
        self.grid_count = params.get('grid_count', 4)  # 进一步减少到4格
        self.investment_per_grid = params.get('investment_per_grid', 10000)  # 增加到$10,000
        self.price_range_pct = params.get('price_range_pct', 0.15)  # ±7.5%（更小区间）
        self.symbol = params.get('symbol', 'BTC-USDT')

        # 风险控制参数
        self.stop_loss_pct = params.get('stop_loss_pct', 0.02)  # 止损-2%
        self.profit_target_pct = params.get('profit_target_pct', 0.03)  # 止盈3%
        self.trend_threshold = params.get('trend_threshold', 0.01)  # 趋势阈值1%

        # 网格状态
        self.grid_levels = []
        self.grid_step = None
        self.low_price = None
        self.high_price = None

        # 网格交易记录
        self.grid_trades: List[GridTrade] = []
        self.last_action_time = None
        self.min_trade_interval = timedelta(hours=48)  # 最小交易间隔48小时

        # 持仓成本跟踪
        self.entry_costs = {}  # {symbol: {quantity: cost}}

        # 每日盈亏跟踪
        self.daily_pnl: Optional[DailyPnL] = None
        self.current_date = None

        # 市场状态
        self.current_market_state = MarketState.RANGE
        self.ma_short = None
        self.ma_long = None

        # RSI参数（辅助判断超买超卖）
        self.rsi_period = params.get('rsi_period', 14)

    def detect_market_state(self, data: pd.DataFrame) -> MarketState:
        """
        检测市场状态（更严格）

        Args:
            data: 历史数据

        Returns:
            市场状态
        """
        if len(data) < self.ma_long_period:
            return MarketState.RANGE
        if len(data) < self.rsi_period:
            # 数据不足，使用MA判断
            ma_short = data['close'].rolling(window=self.ma_short_period).mean().iloc[-1]
            ma_long = data['close'].rolling(window=self.ma_long_period).mean().iloc[-1]
            self.ma_short = ma_short
            self.ma_long = ma_long
            return MarketState.RANGE

        # 计算MA
        ma_short = data['close'].rolling(window=self.ma_short_period).mean().iloc[-1]
        ma_long = data['close'].rolling(window=self.ma_long_period).mean().iloc[-1]
        current_price = data['close'].iloc[-1]

        # 保存MA值
        self.ma_short = ma_short
        self.ma_long = ma_long

        # 计算RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]

        # 更严格的市场状态判断
        ma_ratio = ma_short / ma_long

        # 上涨趋势：MA20 > MA50 且 RSI < 70（不过热）
        if ma_ratio > (1 + self.trend_threshold) and rsi < 70:
            return MarketState.TRENDING_UP
        # 下跌趋势：MA20 < MA50 或 RSI > 80（极度超买，可能反转）
        elif ma_ratio < (1 - self.trend_threshold) or rsi > 80:
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

        # 趋势止损（最高优先级）
        if self.current_market_state == MarketState.TRENDING_DOWN:
            print(f"  [趋势止损] 下跌趋势，清仓空仓")
            for symbol, pos in positions.items():
                orders.append(Order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=pos.quantity,
                    timestamp=datetime.now()
                ))
            return orders

        # 检查止盈止损
        for symbol, pos in positions.items():
            if symbol not in self.entry_costs:
                continue

            entry_info = self.entry_costs[symbol]
            current_price = current_prices.get(symbol, pos.current_price)

            # 计算未实现盈亏百分比
            avg_entry_cost = entry_info['total_cost'] / entry_info['total_quantity']
            unrealized_pnl_pct = (current_price - avg_entry_cost) / avg_entry_cost

            # 止盈：盈利超过3%
            if unrealized_pnl_pct > self.profit_target_pct:
                print(f"  [止盈] {symbol} 盈利 {unrealized_pnl_pct*100:.2f}%，止盈")
                orders.append(Order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=pos.quantity,
                    timestamp=datetime.now()
                ))

            # 止损：亏损超过2%
            elif unrealized_pnl_pct < -self.stop_loss_pct:
                print(f"  [止损] {symbol} 亏损 {unrealized_pnl_pct*100:.2f}%，止损")
                orders.append(Order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=pos.quantity,
                    timestamp=datetime.now()
                ))

        return orders

    def setup_grid(self, current_price: float) -> None:
        """设置网格区间"""
        self.high_price = current_price * (1 + self.price_range_pct / 2)
        self.low_price = current_price * (1 - self.price_range_pct / 2)
        self.grid_step = (self.high_price - self.low_price) / self.grid_count
        self.grid_levels = [self.low_price + i * self.grid_step for i in range(self.grid_count + 1)]
        self.grid_trades.clear()
        print(f"  [网格设置] 区间: ${self.low_price:.2f} - ${self.high_price:.2f}, {self.grid_count}格, 间距${self.grid_step:.2f}")

    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        positions: Dict[str, Position],
        current_time: datetime
    ) -> List[Order]:
        """
        生成交易信号

        只在上涨趋势中积极交易，震荡市谨慎交易
        """
        orders = []

        if self.symbol not in data:
            return orders

        df = data[self.symbol]

        # 首次处理
        if self.current_date is None:
            self.current_date = current_time
            self.daily_pnl = DailyPnL(date=current_time, start_equity=0)
            self.setup_grid(df.iloc[-1]['close'])
            return orders

        # 新的一天
        if current_time.date() != self.current_date.date():
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

        # 1. 检查止损止盈
        stop_loss_orders = self.check_stop_loss(positions, {self.symbol: current_price})
        if stop_loss_orders:
            return stop_loss_orders

        # 2. 下跌趋势：不允许买入
        if self.current_market_state == MarketState.TRENDING_DOWN:
            print(f"  [空仓模式] 下跌趋势，不交易")
            return orders

        # 3. 检查交易间隔
        if self.last_action_time and (current_time - self.last_action_time) < self.min_trade_interval:
            print(f"  [冷却中] 距离上次交易不足{self.min_trade_interval.total_seconds()/3600:.1f}小时")
            return orders

        # 4. 只在上涨趋势交易网格，震荡市少量交易
        if self.current_market_state != MarketState.TRENDING_UP:
            print(f"  [谨慎模式] 震荡市，减少交易频率")
            # 在震荡市也可以交易，但更谨慎
            pass

        # 5. 网格交易逻辑
        current_position = positions.get(self.symbol)
        current_quantity = current_position.quantity if current_position else 0.0

        # 检查网格区间
        if current_price < self.low_price or current_price > self.high_price:
            if self.current_market_state != MarketState.TRENDING_DOWN:
                print(f"  [网格重置] 价格${current_price:.2f}超出范围")
                self.setup_grid(current_price)
            return orders

        # 寻找最近的网格线
        nearest_grid = min(self.grid_levels, key=lambda x: abs(x - current_price))
        distance_from_grid = abs(current_price - nearest_grid)

        # 买入条件：接近网格线 + 持仓量小 + 在上涨趋势
        if (self.current_market_state == MarketState.TRENDING_UP and
            current_quantity < 0.15 and
            distance_from_grid < self.grid_step * 0.25 and
            current_price < nearest_grid):  # 从下方接近

            # 检查最近是否交易过
            recent_trade = any(
                not gt.is_closed and
                abs(gt.buy_price - current_price) < self.grid_step * 0.3
                for gt in self.grid_trades
            )

            if not recent_trade:
                buy_quantity = self.investment_per_grid / current_price

                orders.append(Order(
                    symbol=self.symbol,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=buy_quantity,
                    timestamp=current_time
                ))

                self.grid_trades.append(GridTrade(
                    buy_price=current_price,
                    buy_quantity=buy_quantity,
                    buy_time=current_time
                ))

                self.last_action_time = current_time
                print(f"  [网格买入] 价格${current_price:.2f}, 数量{buy_quantity:.4f}")

        # 卖出条件：接近网格线 + 有持仓
        elif (current_quantity > 0 and
              distance_from_grid < self.grid_step * 0.25 and
              current_price > nearest_grid):

            # 查找对应的买入单
            for trade in reversed(self.grid_trades):
                if (not trade.is_closed and
                    trade.buy_price is not None and
                    abs(trade.buy_price - nearest_grid) < self.grid_step * 0.5):

                    sell_quantity = min(trade.buy_quantity, current_quantity)

                    orders.append(Order(
                        symbol=self.symbol,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        quantity=sell_quantity,
                        timestamp=current_time
                    ))

                    trade.sell_price = current_price
                    trade.sell_time = current_time
                    trade.is_closed = True

                    self.last_action_time = current_time
                    profit_pct = (current_price / trade.buy_price - 1) * 100
                    print(f"  [网格卖出] 价格${current_price:.2f}, 数量{sell_quantity:.4f}, 收益{profit_pct:.2f}%")
                    break

        return orders

    def on_trade(self, trade: Trade):
        """成交回调"""
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
            if trade.symbol in self.entry_costs:
                avg_cost_per_unit = (
                    self.entry_costs[trade.symbol]['total_cost'] /
                    self.entry_costs[trade.symbol]['total_quantity']
                )
                realized_pnl = (trade.price - avg_cost_per_unit) * trade.quantity - trade.commission

                if self.daily_pnl:
                    self.daily_pnl.total_loss += realized_pnl

                cost_basis = avg_cost_per_unit * trade.quantity
                self.entry_costs[trade.symbol]['total_quantity'] -= trade.quantity
                self.entry_costs[trade.symbol]['total_cost'] -= cost_basis

                if self.entry_costs[trade.symbol]['total_quantity'] <= 0.001:
                    del self.entry_costs[trade.symbol]

    def on_order_filled(self, order: Order):
        """订单成交回调"""
        pass
