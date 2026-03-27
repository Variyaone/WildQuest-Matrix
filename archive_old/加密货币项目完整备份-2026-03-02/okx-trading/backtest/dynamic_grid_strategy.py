"""
动态网格策略 (Dynamic Grid Strategy)

根据市场波动率动态调整网格参数，以适应不同市场环境。
- 高波动期：扩大网格区间，减少网格数量
- 低波动期：缩小网格区间，增加网格数量
"""

from backtest_engine import BaseStrategy, Order, OrderSide, OrderType
from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime
import numpy as np


@dataclass
class GridState:
    """网格状态"""
    low_price: float
    high_price: float
    grid_step: float
    grid_levels: list
    active_orders: dict  # {price: OrderSide}


class DynamicGridStrategy(BaseStrategy):
    """
    动态网格策略

    策略逻辑：
    1. 计算ATR(14)获取市场波动率
    2. 根据波动率动态调整网格参数
    3. 高波动率(>2%)：扩大区间±7.5%，减少网格数6-8
    4. 低波动率(<1%)：缩小区间±3%，增加网格数10-12
    5. 中等波动率：标准区间±5%，标准网格数8-10
    """

    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)

        # 基础参数
        self.symbol = params.get('symbol', 'BTC-USDT')
        self.base_grid_count = params.get('grid_count', 8)  # 基础网格数量
        self.base_price_range_pct = params.get('price_range_pct', 0.10)  # 基础价格区间
        self.investment_per_grid = params.get('investment_per_grid', 10000)  # 每格金额

        # 动态参数
        self.atr_period = params.get('atr_period', 14)  # ATR周期
        self.high_volatility_threshold = params.get('high_vol_threshold', 0.02)  # 高波动阈值 2%
        self.low_volatility_threshold = params.get('low_vol_threshold', 0.01)  # 低波动阈值 1%
        self.min_interval = params.get('min_interval', 24)  # 最小交易间隔（小时）
        self.stop_loss_pct = params.get('stop_loss_pct', -0.03)  # 止损比例

        # 高波动配置
        self.high_vol_grid_count_range = (6, 8)  # 高波动网格数量范围
        self.high_vol_price_range = 0.075  # 高波动价格区间 ±7.5%

        # 低波动配置
        self.low_vol_grid_count_range = (10, 12)  # 低波动网格数量范围
        self.low_vol_price_range = 0.03  # 低波动价格区间 ±3%

        # 中等波动配置
        self.normal_vol_grid_count_range = (8, 10)  # 中等波动网格数量范围
        self.normal_vol_price_range = 0.05  # 中等波动价格区间 ±5%

        # 网格状态
        self.grid_state: Optional[GridState] = None
        self.last_trade_time = None
        self.last_rebalance_time = None
        self.last_volatility_check_time = None

        # 交易记录
        self.trade_history = []

    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """
        计算AT（平均真实波幅）

        Args:
            data: 历史K线数据
            period: ATR周期

        Returns:
            ATR值
        """
        if len(data) < period + 1:
            return 0.0

        # 计算True Range
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # 计算ATR
        atr = true_range.rolling(window=period).mean()

        return atr.iloc[-1]

    def _calculate_volatility(self, data: pd.DataFrame) -> float:
        """
        计算波动率（ATR / price）

        Args:
            data: 历史K线数据

        Returns:
            波动率
        """
        current_price = data['close'].iloc[-1]
        atr = self._calculate_atr(data, self.atr_period)

        return atr / current_price if current_price > 0 else 0.0

    def _get_grid_config(self, volatility: float) -> tuple:
        """
        根据波动率获取网格配置

        Args:
            volatility: 波动率

        Returns:
            (grid_count, price_range_pct)
        """
        if volatility >= self.high_volatility_threshold:
            # 高波动：扩大区间，减少网格
            grid_count = int(np.random.randint(
                self.high_vol_grid_count_range[0],
                self.high_vol_grid_count_range[1] + 1
            ))
            price_range = self.high_vol_price_range
            volatility_regime = 'high'
        elif volatility <= self.low_volatility_threshold:
            # 低波动：缩小区间，增加网格
            grid_count = int(np.random.randint(
                self.low_vol_grid_count_range[0],
                self.low_vol_grid_count_range[1] + 1
            ))
            price_range = self.low_vol_price_range
            volatility_regime = 'low'
        else:
            # 中等波动：标准配置
            grid_count = int(np.random.randint(
                self.normal_vol_grid_count_range[0],
                self.normal_vol_grid_count_range[1] + 1
            ))
            price_range = self.normal_vol_price_range
            volatility_regime = 'normal'

        return grid_count, price_range, volatility_regime

    def _setup_grid(
        self,
        current_price: float,
        grid_count: int,
        price_range_pct: float,
        current_time: datetime
    ):
        """
        设置网格

        Args:
            current_price: 当前价格
            grid_count: 网格数量
            price_range_pct: 价格区间百分比
            current_time: 当前时间
        """
        # 计算价格区间
        high_price = current_price * (1 + price_range_pct / 2)
        low_price = current_price * (1 - price_range_pct / 2)

        # 计算网格间距
        grid_step = (high_price - low_price) / grid_count

        # 生成网格价格水平
        grid_levels = [low_price + i * grid_step for i in range(grid_count + 1)]

        # 保存网格状态
        self.grid_state = GridState(
            low_price=low_price,
            high_price=high_price,
            grid_step=grid_step,
            grid_levels=grid_levels,
            active_orders={}
        )

        self.last_rebalance_time = current_time

        # 打印网格设置（调试用）
        # print(f"[{current_time}] 动态网格设置完成: "
        #       f"价格区间 ${low_price:.2f} - ${high_price:.2f}, "
        #       f"网格数量 {grid_count}, "
        #       f"网格间距 ${grid_step:.2f}")

    def _check_stop_loss(self, current_price: float, positions: Dict) -> bool:
        """
        检查是否触发止损

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

    def _should_rebalance(self, volatility: float, current_time: datetime) -> bool:
        """
        检查是否需要重新平衡网格（波动率变化）

        Args:
            volatility: 当前波动率
            current_time: 当前时间

        Returns:
            是否需要重新平衡
        """
        if self.last_rebalance_time is None:
            return True

        # 暂时不频繁重平衡，防止过度调整
        # 仅在波动率跨越阈值时重平衡
        prev_grid_count, prev_price_range, prev_regime = self._get_grid_config(
            self.last_volatility if hasattr(self, 'last_volatility') else 0.02
        )
        curr_grid_count, curr_price_range, curr_regime = self._get_grid_config(volatility)

        # 只有当波动率 regime 发生变化时才重平衡
        return curr_regime != getattr(self, 'last_volatility_regime', 'normal')

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
        if len(df) < self.atr_period + 1:
            return orders

        current_price = float(df['close'].iloc[-1])

        # 计算当前波动率
        volatility = self._calculate_volatility(df)
        self.last_volatility = volatility

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
                # 重置网格
                self.grid_state = None
                self.last_trade_time = current_time
            return orders

        # 检查是否需要重平衡
        if self._should_rebalance(volatility, current_time):
            curr_grid_count, curr_price_range, curr_regime = self._get_grid_config(volatility)
            self.last_volatility_regime = curr_regime
            self._setup_grid(current_price, curr_grid_count, curr_price_range, current_time)

        # 首次设置网格
        if self.grid_state is None:
            curr_grid_count, curr_price_range, _ = self._get_grid_config(volatility)
            self._setup_grid(current_price, curr_grid_count, curr_price_range, current_time)
            return orders

        # 检查是否超出网格范围
        if current_price < self.grid_state.low_price or current_price > self.grid_state.high_price:
            # 价格超出范围，重新设置网格
            curr_grid_count, curr_price_range, _ = self._get_grid_config(volatility)
            self._setup_grid(current_price, curr_grid_count, curr_price_range, current_time)
            return orders

        # 检查最小交易间隔
        if not self._check_min_interval(current_time):
            return orders

        # 获取当前持仓
        current_position = positions.get(self.symbol)
        current_quantity = current_position.quantity if current_position else 0.0

        # 检查是否触碰到网格线
        for i, level_price in enumerate(self.grid_state.grid_levels[:-1]):
            # 买入信号：价格下跌到网格线（从上方接近）
            if current_price <= level_price and current_price >= level_price - self.grid_state.grid_step:
                # 检查是否已经在该价格附近买入过
                if not self._bought_near_price(level_price):
                    # 计算买入数量
                    buy_quantity = self.investment_per_grid / level_price

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
