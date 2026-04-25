"""
网格交易策略模块
实现经典的网格交易策略，包含价格突破检测和自动扩展机制
"""

import logging
from typing import Dict, List, Optional, Any
from .base import BaseStrategy, Signal, Position
from ..exceptions import RiskException

logger = logging.getLogger(__name__)


class GridStrategy(BaseStrategy):
    """
    网格交易策略
    在指定价格区间内设置多个网格，自动买卖
    包含价格突破检测和区间扩展功能
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化网格策略

        Args:
            name: 策略名称
            config: 策略配置
                - instrument_id: 交易对
                - upper_price: 上轨价格
                - lower_price: 下轨价格
                - grid_count: 网格数量
                - grid_amount: 单格金额
                - position_side: 仓位方向 ('long' or 'short')
                - breakout_threshold: 突破阈值（百分比，默认10%）
                - expand_percent: 突破后扩展百分比（默认5%）
                - extreme_breakdown_threshold: 极端突破阈值（默认15%）
        """
        super().__init__(name, config)

        # 网格参数
        self.instrument_id = config.get('instrument_id', 'BTC-USDT-SWAP')
        self.upper_price = config.get('upper_price', 50000)
        self.lower_price = config.get('lower_price', 45000)
        self.grid_count = config.get('grid_count', 10)
        self.grid_amount = config.get('grid_amount', 100)  # USDT
        self.position_side = config.get('position_side', 'long')

        # 价格突破参数
        self.breakout_threshold = config.get('breakout_threshold', 10.0)  # %
        self.expand_percent = config.get('expand_percent', 5.0)  # %
        self.extreme_breakdown_threshold = config.get('extreme_breakdown_threshold', 15.0)  # %

        # 初始价格区间（用于计算突破）
        self.initial_upper = self.upper_price
        self.initial_lower = self.lower_price

        # 突破状态
        self.breakout_count = 0
        self.max_expand_count = 3  # 最大扩展次数
        self.last_expand_time = 0
        self.expand_cooldown = 3600  # 扩展冷却时间（秒）

        # 计算网格
        self.grid_size = (self.upper_price - self.lower_price) / self.grid_count
        self.grid_levels = self._calculate_grid_levels()

        # 网格状态：记录每个网格是否已挂单
        self.grid_orders: Dict[int, Dict] = {}  # {level_index: {order_id, type, price, amount}}

        # 当前持仓
        self.current_size = 0.0
        self.current_value = 0.0  # 当前持仓价值

        # 盈亏统计
        self.total_pnl = 0.0
        self.realized_pnl = 0.0

        # 记录历史价格（用于突破检测）
        self.price_history: List[float] = []
        self.max_history_size = 100

        logger.info(f"网格策略初始化: {self.instrument_id}")
        logger.info(f"价格区间: {self.lower_price} - {self.upper_price}")
        logger.info(f"网格数量: {self.grid_count}, 单格金额: {self.grid_amount} USDT")
        logger.info(f"突破阈值: ±{self.breakout_threshold}%, 扩展比例: ±{self.expand_percent}%")

    def _calculate_grid_levels(self) -> List[Dict]:
        """
        计算网格价格层级

        Returns:
            网格层级列表
        """
        levels = []
        for i in range(self.grid_count + 1):
            price = self.lower_price + i * self.grid_size
            amount = self.grid_amount / price
            levels.append({
                'index': i,
                'price': price,
                'amount': amount
            })

        return levels

    @property
    def grid_profit(self) -> float:
        """单网格利润百分比"""
        return (self.grid_size / self.lower_price) * 100

    def initialize(self) -> bool:
        """
        初始化策略

        Returns:
            是否成功
        """
        if not self.validate_config([
            'instrument_id', 'upper_price', 'lower_price',
            'grid_count', 'grid_amount'
        ]):
            return False

        # 验证价格区间
        if self.upper_price <= self.lower_price:
            logger.error("上轨价格必须大于下轨价格")
            return False

        if self.grid_count < 2:
            logger.error("网格数量必须大于等于2")
            return False

        self.is_initialized = True
        logger.info(f"网格策略初始化成功")
        logger.info(f"单网格利润: {self.grid_profit:.4f}%")

        return True

    def on_data(self, data: Dict) -> Optional[Signal]:
        """
        处理K线数据

        Args:
            data: K线数据

        Returns:
            交易信号
        """
        self.update_cache(data)

        # 提取当前价格
        current_price = self._extract_price(data)
        if current_price is None:
            return None

        # 检查价格突破
        breakout_signal = self._check_price_breakout(current_price)
        if breakout_signal:
            return breakout_signal

        # 检查网格触发
        return self._check_grid_triggers(current_price)

    def _extract_price(self, data: Dict) -> Optional[float]:
        """
        从数据中提取价格

        Args:
            data: 数据

        Returns:
            当前价格
        """
        price = None

        if 'price' in data:
            price = float(data['price'])
        elif 'last' in data:
            price = float(data['last'])
        elif 'candle' in data and data['candle']:
            candle = data['candle']
            if isinstance(candle, list) and len(candle) > 0:
                price = float(candle[4])  # close
            elif isinstance(candle, dict) and 'close' in candle:
                price = float(candle['close'])

        # 记录价格历史
        if price is not None:
            self.price_history.append(price)
            if len(self.price_history) > self.max_history_size:
                self.price_history.pop(0)

        return price

    def generate_signal(self) -> Optional[Signal]:
        """
        生成网格信号（手动调用）

        Returns:
            交易信号
        """
        latest_data = self.get_latest_data(1)
        if not latest_data:
            return None

        current_price = self._extract_price(latest_data[0])
        if current_price is None:
            return None

        # 检查价格突破
        breakout_signal = self._check_price_breakout(current_price)
        if breakout_signal:
            return breakout_signal

        return self._check_grid_triggers(current_price)

    def _check_price_breakout(self, current_price: float) -> Optional[Signal]:
        """
        检查价格是否突破区间

        Args:
            current_price: 当前价格

        Returns:
            突破处理信号（平仓或扩展），无突破返回None
        """
        current_time = int(__import__('time').time())

        # 计算突破百分比
        price_range = self.initial_upper - self.initial_lower
        upper_breakout_percent = ((current_price - self.initial_upper) / price_range) * 100
        lower_breakdown_percent = ((self.initial_lower - current_price) / price_range) * 100

        # 极端突破检测（触发止损平仓）
        if upper_breakout_percent >= self.extreme_breakdown_threshold:
            logger.warning(f"极端向上突破: {upper_breakout_percent:.2f}% >= {self.extreme_breakdown_threshold}%")
            if self.current_size > 0:
                return Signal(
                    signal_type='sell',
                    instrument_id=self.instrument_id,
                    price=current_price,
                    amount=abs(self.current_size),
                    reason=f"极端向上突破触发止损: {current_price} > {self.initial_upper} * (1 + {self.extreme_breakdown_threshold}%)",
                    metadata={'type': 'extreme_breakout_stop_loss'}
                )

        if lower_breakdown_percent >= self.extreme_breakdown_threshold:
            logger.warning(f"极端向下突破: {lower_breakdown_percent:.2f}% >= {self.extreme_breakdown_threshold}%")
            if self.current_size > 0:
                return Signal(
                    signal_type='sell',
                    instrument_id=self.instrument_id,
                    price=current_price,
                    amount=abs(self.current_size),
                    reason=f"极端向下突破触发止损: {current_price} < {self.initial_lower} * (1 - {self.extreme_breakdown_threshold}%)",
                    metadata={'type': 'extreme_breakdown_stop_loss'}
                )

        # 普通突破检测（触发区间扩展）
        if upper_breakout_percent >= self.breakout_threshold:
            # 检查冷却时间
            if current_time - self.last_expand_time >= self.expand_cooldown:
                if self.breakout_count < self.max_expand_count:
                    return self._expand_range('up', current_price)
            else:
                logger.debug(f"扩展冷却中，剩余: {self.expand_cooldown - (current_time - self.last_expand_time)}s")

        if lower_breakdown_percent >= self.breakout_threshold:
            if current_time - self.last_expand_time >= self.expand_cooldown:
                if self.breakout_count < self.max_expand_count:
                    return self._expand_range('down', current_price)
            else:
                logger.debug(f"扩展冷却中，剩余: {self.expand_cooldown - (current_time - self.last_expand_time)}s")

        return None

    def _expand_range(self, direction: str, current_price: float) -> Optional[Signal]:
        """
        扩展价格区间

        Args:
            direction: 扩展方向 ('up' or 'down')
            current_price: 当前价格

        Returns:
            扩展信号
        """
        import time

        old_upper = self.upper_price
        old_lower = self.lower_price

        if direction == 'up':
            # 向上扩展：上轨增加 expand_percent%
            expansion_amount = old_upper * (self.expand_percent / 100)
            self.upper_price += expansion_amount
            logger.info(f"向上扩展区间: {old_upper} -> {self.upper_price}")
        else:
            # 向下扩展：下轨减少 expand_percent%
            expansion_amount = old_lower * (self.expand_percent / 100)
            self.lower_price -= expansion_amount
            logger.info(f"向下扩展区间: {old_lower} -> {self.lower_price}")

        # 重新计算网格
        self.grid_size = (self.upper_price - self.lower_price) / self.grid_count
        self.grid_levels = self._calculate_grid_levels()

        # 更新状态
        self.breakout_count += 1
        self.last_expand_time = int(time.time())

        logger.info(
            f"区间已扩展: [{old_lower}, {old_upper}] -> [{self.lower_price}, {self.upper_price}], "
            f"扩展次数: {self.breakout_count}/{self.max_expand_count}"
        )

        # 发送信号通知（不是交易信号，用于通知）
        return Signal(
            signal_type='info',
            instrument_id=self.instrument_id,
            price=current_price,
            amount=0,
            reason=f"价格突破触发区间{direction}扩展: 新区间 [{self.lower_price:.2f}, {self.upper_price:.2f}]",
            metadata={
                'type': 'range_expansion',
                'direction': direction,
                'old_lower': old_lower,
                'old_upper': old_upper,
                'new_lower': self.lower_price,
                'new_upper': self.upper_price,
                'breakout_count': self.breakout_count
            }
        )

    def _check_grid_triggers(self, current_price: float) -> Optional[Signal]:
        """
        检查网格触发条件

        Args:
            current_price: 当前价格

        Returns:
            交易信号
        """
        # 检查价格是否在区间外
        if current_price > self.upper_price:
            logger.debug(f"价格超出上轨: {current_price} > {self.upper_price}")
            return None
        if current_price < self.lower_price:
            logger.debug(f"价格低于下轨: {current_price} < {self.lower_price}")
            return None

        # 做多策略：跌到网格线买入，涨到网格线卖出
        if self.position_side == 'long':
            return self._check_long_grid(current_price)
        # 做空策略：涨到网格线卖出，跌到网格线买入
        else:
            return self._check_short_grid(current_price)

    def _check_long_grid(self, current_price: float) -> Optional[Signal]:
        """
        做多网格逻辑

        Args:
            current_price: 当前价格

        Returns:
            交易信号
        """
        # 寻找最近的买入网格线
        buy_signals = []

        for level in self.grid_levels:
            price = level['price']

            # 价格从上向下穿过网格线 - 买入信号
            if current_price <= price * 1.001:  # 稍微放宽容忍度
                # 检查该网格是否已有未成交的买单
                if level['index'] not in self.grid_orders:
                    buy_signals.append((price, level))

        if buy_signals:
            # 选择最接近的网格
            buy_signals.sort(key=lambda x: abs(x[0] - current_price))
            price, level = buy_signals[0]

            signal = Signal(
                signal_type='buy',
                instrument_id=self.instrument_id,
                price=price,
                amount=level['amount'],
                reason=f"价格 {current_price} 跌至网格 {price}, 执行买入"
            )
            self.grid_orders[level['index']] = {
                'type': 'buy',
                'price': price,
                'amount': level['amount'],
                'timestamp': int(__import__('time').time())
            }
            logger.info(f"生成买入信号: {signal.reason}")
            return signal

        # 检查卖出条件
        # 如果有持仓，且当前价格高于买入价格
        if self.current_size > 0:
            for level in self.grid_levels:
                price = level['price']

                # 价格从下向上穿过网格线
                if current_price >= price * 0.999 and level['index'] > 0:
                    prev_level = self.grid_levels[level['index'] - 1]

                    # 检查是否有该层级的买入记录
                    if prev_level['index'] in self.grid_orders:
                        order = self.grid_orders[prev_level['index']]

                        # 卖出信号
                        signal = Signal(
                            signal_type='sell',
                            instrument_id=self.instrument_id,
                            price=price,
                            amount=order['amount'],
                            reason=f"价格 {current_price} 涨至网格 {price}, 执行卖出"
                        )

                        # 计算利润
                        profit = (price - order['price']) * order['amount']
                        self.realized_pnl += profit
                        self.breakout_count = max(0, self.breakout_count - 1)  # 成功后减少突破计数

                        # 移除买入记录
                        del self.grid_orders[prev_level['index']]

                        logger.info(f"生成卖出信号: {signal.reason}, 利润: {profit:.4f} USDT")
                        return signal

        return None

    def _check_short_grid(self, current_price: float) -> Optional[Signal]:
        """
        做空网格逻辑

        Args:
            current_price: 当前价格

        Returns:
            交易信号
        """
        # 涨到网格线 - 卖出（开空）
        for level in self.grid_levels:
            price = level['price']

            if current_price >= price * 0.999:
                if level['index'] not in self.grid_orders:
                    signal = Signal(
                        signal_type='sell',
                        instrument_id=self.instrument_id,
                        price=price,
                        amount=level['amount'],
                        reason=f"价格 {current_price} 涨至网格 {price}, 开空单"
                    )
                    self.grid_orders[level['index']] = {
                        'type': 'sell',
                        'price': price,
                        'amount': level['amount'],
                        'timestamp': int(__import__('time').time())
                    }
                    logger.info(f"生成卖出信号: {signal.reason}")
                    return signal

        # 跌到网格线 - 买入（平空）
        if self.current_size < 0:
            for level in self.grid_levels:
                price = level['price']

                if current_price <= price * 1.001 and level['index'] < len(self.grid_levels) - 1:
                    next_level = self.grid_levels[level['index'] + 1]

                    if next_level['index'] in self.grid_orders:
                        order = self.grid_orders[next_level['index']]

                        signal = Signal(
                            signal_type='buy',
                            instrument_id=self.instrument_id,
                            price=price,
                            amount=order['amount'],
                            reason=f"价格 {current_price} 跌至网格 {price}, 平空单"
                        )

                        profit = (order['price'] - price) * order['amount']
                        self.realized_pnl += profit
                        self.breakout_count = max(0, self.breakout_count - 1)

                        del self.grid_orders[next_level['index']]

                        logger.info(f"生成买入信号: {signal.reason}, 利润: {profit:.4f} USDT")
                        return signal

        return None

    def on_order_filled(self, order: Dict[str, Any]):
        """
        订单成交处理

        Args:
            order: 订单信息
        """
        super().on_order_filled(order)

        if order.get('instrument_id') != self.instrument_id:
            return

        side = order.get('side')
        amount = order.get('filled_amount', order.get('amount', 0))
        price = order.get('price')

        if side == 'buy':
            self.current_size += amount
            self.current_value += amount * price
        elif side == 'sell':
            self.current_size -= amount
            self.current_value -= amount * price

        logger.info(f"当前持仓: {self.current_size:.4f}, 价值: {self.current_value:.2f} USDT")

    def get_stats(self) -> Dict:
        """
        获取策略统计

        Returns:
            统计信息
        """
        stats = super().get_stats()
        stats.update({
            'grid_count': self.grid_count,
            'grid_size': self.grid_size,
            'grid_profit_percent': self.grid_profit,
            'grid_levels': len(self.grid_levels),
            'active_orders': len(self.grid_orders),
            'current_size': self.current_size,
            'current_value': self.current_value,
            'realized_pnl': self.realized_pnl,
            'price_range': f"{self.lower_price} - {self.upper_price}",
            'initial_range': f"{self.initial_lower} - {self.initial_upper}",
            'breakout_count': self.breakout_count,
            'breakout_threshold': self.breakout_threshold,
            'expand_percent': self.expand_percent,
        })
        return stats

    def reset(self):
        """重置策略状态"""
        self.grid_orders.clear()
        self.current_size = 0.0
        self.current_value = 0.0
        self.breakout_count = 0
        self.upper_price = self.initial_upper
        self.lower_price = self.initial_lower
        self.grid_size = (self.upper_price - self.lower_price) / self.grid_count
        self.grid_levels = self._calculate_grid_levels()
        logger.info(f"网格策略已重置")
