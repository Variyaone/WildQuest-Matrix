"""
回测引擎
提供完善的交易策略回测功能，包含滑点模拟、市场冲击、订单簿深度检查
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import random

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class BacktestOrder:
    """回测订单"""
    order_id: str
    instrument_id: str
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market', 'limit'
    price: float
    amount: float
    filled_amount: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    filled_avg_price: float = 0.0
    slippage: float = 0.0
    rejected_reason: str = None
    created_at: int = 0
    filled_at: int = 0
    metadata: Dict = None


@dataclass
class BacktestTrade:
    """回测成交记录"""
    trade_id: str
    order_id: str
    instrument_id: str
    side: str
    price: float
    amount: float
    slippage: float
    timestamp: int


@dataclass
class BacktestPosition:
    """回测持仓"""
    instrument_id: str
    side: str  # 'long' or 'short'
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    margin: float


@dataclass
class BacktestResult:
    """回测结果"""
    # 基本信息
    start_time: int
    end_time: int
    duration_seconds: int

    # 交易统计
    total_trades: int
    win_trades: int
    loss_trades: int
    win_rate: float

    # 收益统计
    total_pnl: float
    total_pnl_percent: float
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float

    # 订单统计
    total_orders: int
    filled_orders: int
    rejected_orders: int
    fill_rate: float

    # 成本统计
    total_slippage: float
    avg_slippage: float
    total_commission: float

    # 持仓统计
    max_position_size: float
    max_position_value: float

    # 策略指标
    avg_trade_pnl: float
    profit_factor: float

    # 详细交易记录
    trades: List[Dict]
    orders: List[Dict]

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    def save_to_file(self, filepath: str):
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        logger.info(f"回测结果已保存: {filepath}")


class BacktestEngine:
    """
    回测引擎
    提供完善的交易策略回测功能
    """

    def __init__(
        self,
        config: Dict[str, Any] = None
    ):
        """
        初始化回测引擎

        Args:
            config: 回测配置
                - initial_balance: 初始资金
                - commission_rate: 手续费率（默认0.05%）
                - slippage_min: 最小滑点（百分比，默认0.05%）
                - slippage_max: 最大滑点（百分比，默认0.2%）
                - market_impact_threshold: 市场影响阈值（USDT，默认1000）
                - orderbook_check_depth: 订单簿检查深度（默认20）
                - min_orderbook_liquidity: 最小订单簿流动性（USDT，默认100）
        """
        self.config = config or {}

        # 初始资金
        self.initial_balance = self.config.get('initial_balance', 10000.0)
        self.current_balance = self.initial_balance

        # 交易成本
        self.commission_rate = self.config.get('commission_rate', 0.0005)  # 0.05%
        self.slippage_min = self.config.get('slippage_min', 0.0005)  # 0.05%
        self.slippage_max = self.config.get('slippage_max', 0.002)  # 0.2%

        # 市场影响参数
        self.market_impact_threshold = self.config.get('market_impact_threshold', 1000.0)
        self.market_impact_factor = 0.0001  # 每超出1000 USDT，额外增加0.01%的滑点

        # 订单簿检查
        self.orderbook_check_depth = self.config.get('orderbook_check_depth', 20)
        self.min_orderbook_liquidity = self.config.get('min_orderbook_liquidity', 100.0)

        # 数据存储
        self.orders: Dict[str, BacktestOrder] = {}
        self.trades: List[BacktestTrade] = []
        self.positions: Dict[str, BacktestPosition] = {}

        # 统计
        self.order_counter = 0
        self.trade_counter = 0

        # 回测状态
        self.is_running = False
        self.current_time = 0
        self.current_price = 0.0
        self.current_orderbook: Dict = None

        # 信号处理回调
        self.on_signal_callback: Optional[Callable] = None

        logger.info(
            f"回测引擎初始化: 初始资金 {self.initial_balance:.2f} USDT, "
            f"手续费 {self.commission_rate*100:.3f}%, "
            f"滑点范围 {self.slippage_min*100:.3f}%-{self.slippage_max*100:.3f}%"
        )

    def _generate_order_id(self) -> str:
        """生成订单ID"""
        self.order_counter += 1
        return f"BT_{int(time.time() * 1000)}_{self.order_counter}"

    def _generate_trade_id(self) -> str:
        """生成成交ID"""
        self.trade_counter += 1
        return f"TR_{int(time.time() * 1000)}_{self.trade_counter}"

    def _calculate_slippage(self, order_value: float, side: str) -> float:
        """
        计算滑点

        Args:
            order_value: 订单价值
            side: 买卖方向

        Returns:
            滑点百分比
        """
        # 基础滑点（随机）
        base_slippage = random.uniform(self.slippage_min, self.slippage_max)

        # 市场影响滑点（大订单增加滑点）
        market_impact = 0.0
        if order_value > self.market_impact_threshold:
            excess = order_value - self.market_impact_threshold
            market_impact = (excess / 1000.0) * self.market_impact_factor

        total_slippage = base_slippage + market_impact

        logger.debug(
            f"滑点计算: 订单价值 {order_value:.2f}, 基础滑点 {base_slippage*100:.4f}%, "
            f"市场影响 {market_impact*100:.4f}%, 总计 {total_slippage*100:.4f}%"
        )

        return total_slippage

    def _calculate_commission(self, amount: float, price: float) -> float:
        """
        计算手续费

        Args:
            amount: 数量
            price: 价格

        Returns:
            手续费
        """
        return amount * price * self.commission_rate

    def _check_orderbook_liquidity(self, order_value: float, side: str) -> bool:
        """
        检查订单簿流动性

        Args:
            order_value: 订单价值
            side: 买卖方向

        Returns:
            是否有足够流动性
        """
        if not self.current_orderbook:
            # 没有订单簿数据，使用简单检查
            return order_value >= self.min_orderbook_liquidity

        orderbook = self.current_orderbook

        if side == 'buy':
            # 买单流动性: 检查订单簿卖方深度
            asks = orderbook.get('asks', [])[:self.orderbook_check_depth]
            available_liquidity = sum(float(a[1]) * float(a[0]) for a in asks)
        else:
            # 卖单流动性: 检查订单簿买方深度
            bids = orderbook.get('bids', [])[:self.orderbook_check_depth]
            available_liquidity = sum(float(b[1]) * float(b[0]) for b in bids)

        has_liquidity = available_liquidity >= self.min_orderbook_liquidity

        logger.debug(
            f"订单簿流动性检查: 订单价值 {order_value:.2f}, "
            f"可用流动性 {available_liquidity:.2f}, "
            f"{'充足' if has_liquidity else '不足'}"
        )

        return has_liquidity

    def _execute_order(self, order: BacktestOrder, current_price: float, current_orderbook: Dict = None):
        """
        执行订单

        Args:
            order: 订单
            current_price: 当前价格
            current_orderbook: 当前订单簿
        """
        try:
            order_value = order.price * order.amount

            # 1. 检查订单簿流动性
            if not self._check_orderbook_liquidity(order_value, order.side):
                order.status = OrderStatus.REJECTED
                order.rejected_reason = "订单簿流动性不足"
                logger.warning(f"订单被拒绝: {order.order_id}, 原因: {order.rejected_reason}")
                return

            # 2. 计算滑点
            slippage = self._calculate_slippage(order_value, order.side)

            # 3. 计算实际成交价格
            if order.side == 'buy':
                # 买单滑点向上
                fill_price = order.price * (1 + slippage)
            else:
                # 卖单滑点向下
                fill_price = order.price * (1 - slippage)

            # 4. 计算手续费
            commission = self._calculate_commission(order.amount, fill_price)

            # 5. 更新订单状态
            order.status = OrderStatus.FILLED
            order.filled_amount = order.amount
            order.filled_avg_price = fill_price
            order.slippage = slippage
            order.filled_at = self.current_time

            # 6. 更新资金
            if order.side == 'buy':
                cost = order.amount * fill_price + commission
                self.current_balance -= cost
                logger.info(
                    f"买单成交: {order.order_id}, 价格 {fill_price:.4f}, "
                    f"数量 {order.amount:.4f}, 成本 {cost:.4f}, 滑点 {slippage*100:.4f}%"
                )
            else:
                proceeds = order.amount * fill_price - commission
                self.current_balance += proceeds
                logger.info(
                    f"卖单成交: {order.order_id}, 价格 {fill_price:.4f}, "
                    f"数量 {order.amount:.4f}, 收入 {proceeds:.4f}, 滑点 {slippage*100:.4f}%"
                )

            # 7. 更新持仓
            self._update_position(order, fill_price)

            # 8. 记录成交
            trade = BacktestTrade(
                trade_id=self._generate_trade_id(),
                order_id=order.order_id,
                instrument_id=order.instrument_id,
                side=order.side,
                price=fill_price,
                amount=order.amount,
                slippage=slippage,
                timestamp=self.current_time
            )
            self.trades.append(trade)

        except Exception as e:
            logger.error(f"执行订单失败: {e}")
            order.status = OrderStatus.REJECTED
            order.rejected_reason = str(e)

    def _update_position(self, order: BacktestOrder, fill_price: float):
        """
        更新持仓

        Args:
            order: 订单
            fill_price: 成交价格
        """
        instrument_id = order.instrument_id

        if instrument_id not in self.positions:
            # 新建持仓
            side = 'long' if order.side == 'buy' else 'short'
            self.positions[instrument_id] = BacktestPosition(
                instrument_id=instrument_id,
                side=side,
                size=order.amount if order.side == 'buy' else -order.amount,
                entry_price=fill_price,
                current_price=fill_price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                margin=order.amount * fill_price
            )
        else:
            # 更新现有持仓
            position = self.positions[instrument_id]

            if order.side == 'buy':
                position.size += order.amount

                # 计算新入场价格（加权平均）
                total_value = abs(position.size - order.amount) * position.entry_price + order.amount * fill_price
                position.entry_price = total_value / abs(position.size) if position.size != 0 else fill_price
            else:
                position.size -= order.amount

                # 计算已实现盈亏
                realized_pnl = order.amount * (fill_price - position.entry_price) if position.side == 'long' else order.amount * (position.entry_price - fill_price)
                position.realized_pnl += realized_pnl

            # 持仓为0，删除
            if abs(position.size) < 1e-8:
                del self.positions[instrument_id]

    def place_order(
        self,
        instrument_id: str,
        side: str,
        order_type: str,
        price: float,
        amount: float,
        metadata: Dict = None
    ) -> BacktestOrder:
        """
        下单

        Args:
            instrument_id: 交易对
            side: 买卖方向
            order_type: 订单类型
            price: 价格
            amount: 数量
            metadata: 元数据

        Returns:
            订单对象
        """
        order = BacktestOrder(
            order_id=self._generate_order_id(),
            instrument_id=instrument_id,
            side=side,
            order_type=order_type,
            price=price,
            amount=amount,
            created_at=self.current_time,
            metadata=metadata or {}
        )

        self.orders[order.order_id] = order

        # 市价单立即成交
        if order_type == 'market':
            self._execute_order(order, self.current_price, self.current_orderbook)

        logger.info(f"下单: {order.order_id}, {side} {amount} {instrument_id} @ {price}")
        return order

    def run_backtest(
        self,
        data: List[Dict],
        strategy_func: Callable[[Dict], Optional[Dict]]
    ) -> BacktestResult:
        """
        运行回测

        Args:
            data: 历史数据列表，每条包含 price, volume, orderbook(可选) 等
            strategy_func: 策略函数，接收数据，返回信号或None

        Returns:
            回测结果
        """
        logger.info(f"开始回测: {len(data)} 条数据")

        self.is_running = True
        start_time = time.time()

        if data:
            self.current_time = data[0].get('timestamp', int(time.time() * 1000))

        for i, data_point in enumerate(data):
            try:
                # 更新当前状态
                self.current_price = float(data_point.get('price', data_point.get('close', 0)))
                self.current_orderbook = data_point.get('orderbook')

                # 更新持仓价格和未实现盈亏
                self._update_positions_pnl()

                # 生成并执行策略信号
                signal = strategy_func(data_point)
                if signal:
                    self._handle_signal(signal)

                # 检查挂单成交（限价单）
                self._check_pending_orders()

                if i % 1000 == 0:
                    logger.debug(f"回测进度: {i}/{len(data)} ({i/len(data)*100:.1f}%)")

            except Exception as e:
                logger.error(f"回测数据处理失败 [数据点 {i}]: {e}")

        # 强制平仓所有持仓
        self._close_all_positions()

        end_time = time.time()
        duration = end_time - start_time

        logger.info(f"回测完成: 耗时 {duration:.2f}s, 最终余额 {self.current_balance:.2f} USDT")

        # 生成回测结果
        return self._generate_result(start_time, end_time, data[0] if data else None, data[-1] if data else None)

    def _update_positions_pnl(self):
        """更新所有持仓的未实现盈亏"""
        for position in self.positions.values():
            position.current_price = self.current_price

            if position.side == 'long':
                position.unrealized_pnl = (self.current_price - position.entry_price) * position.size
            else:
                position.unrealized_pnl = (position.entry_price - self.current_price) * abs(position.size)

    def _handle_signal(self, signal: Dict):
        """
        处理策略信号

        Args:
            signal: 信号字典
        """
        signal_type = signal.get('signal_type')

        if signal_type in ['buy', 'sell']:
            self.place_order(
                instrument_id=signal.get('instrument_id'),
                side=signal_type,
                order_type=signal.get('order_type', 'market'),
                price=float(signal.get('price', self.current_price)),
                amount=float(signal.get('amount', 0)),
                metadata={'reason': signal.get('reason')}
            )

    def _check_pending_orders(self):
        """检查并处理挂单"""
        for order in self.orders.values():
            if order.status == OrderStatus.PENDING and order.order_type == 'limit':
                # 检查限价单是否触发
                should_fill = False

                if order.side == 'buy' and self.current_price <= order.price:
                    should_fill = True
                elif order.side == 'sell' and self.current_price >= order.price:
                    should_fill = True

                if should_fill:
                    self._execute_order(order, self.current_price, self.current_orderbook)

    def _close_all_positions(self):
        """平仓所有持仓"""
        for position in self.positions.copy().values():
            if position.side == 'long':
                self.place_order(
                    instrument_id=position.instrument_id,
                    side='sell',
                    order_type='market',
                    price=self.current_price,
                    amount=abs(position.size),
                    metadata={'reason': '回测结束平仓'}
                )
            else:
                self.place_order(
                    instrument_id=position.instrument_id,
                    side='buy',
                    order_type='market',
                    price=self.current_price,
                    amount=abs(position.size),
                    metadata={'reason': '回测结束平仓'}
                )

    def _generate_result(
        self,
        start_time: float,
        end_time: float,
        first_data: Dict,
        last_data: Dict
    ) -> BacktestResult:
        """
        生成回测结果

        Args:
            start_time: 开始时间
            end_time: 结束时间
            first_data: 第一条数据
            last_data: 最后一条数据

        Returns:
            回测结果
        """
        # 基本统计
        total_trades = len(self.trades)
        filled_orders = sum(1 for o in self.orders.values() if o.status == OrderStatus.FILLED)
        rejected_orders = sum(1 for o in self.orders.values() if o.status == OrderStatus.REJECTED)

        # 盈亏统计
        total_pnl = self.current_balance - self.initial_balance
        total_pnl_percent = (total_pnl / self.initial_balance) * 100

        # 成本统计
        total_slippage = sum(o.slippage for o in self.orders.values() if o.status == OrderStatus.FILLED)
        avg_slippage = total_slippage / len([o for o in self.orders.values() if o.status == OrderStatus.FILLED]) if filled_orders > 0 else 0

        # 胜负统计
        win_trades = sum(1 for t in self.trades if t.side == 'sell')  # 简化：所有卖单都视为盈利
        loss_trades = total_trades - win_trades
        win_rate = win_trades / total_trades * 100 if total_trades > 0 else 0

        # 最大回撤
        balance_history = []
        position_values = []
        peak_balance = self.initial_balance

        # 重建资金曲线（简化版）
        balance = self.initial_balance
        balance_history.append(balance)

        for trade in self.trades:
            if trade.side == 'buy':
                balance -= trade.amount * trade.price * (1 + self.commission_rate)
            else:
                balance += trade.amount * trade.price * (1 - self.commission_rate)
            balance_history.append(balance)

            if balance > peak_balance:
                peak_balance = balance

        max_drawdown = peak_balance - min(balance_history)
        max_drawdown_percent = (max_drawdown / peak_balance) * 100 if peak_balance > 0 else 0

        # 夏普比率（简化版）
        if len(balance_history) > 1:
            returns = []
            for i in range(1, len(balance_history)):
                if balance_history[i-1] > 0:
                    returns.append((balance_history[i] - balance_history[i-1]) / balance_history[i-1])

            if returns:
                import statistics
                avg_return = statistics.mean(returns)
                std_return = statistics.stdev(returns) if len(returns) > 1 else 0
                sharpe_ratio = (avg_return / std_return * (252**0.5)) if std_return > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0

        # 平均每笔交易盈亏
        avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0

        # 盈利因子
        gross_profit = sum(t.amount * t.slippage for t in self.trades if t.side == 'sell')  # 简化
        gross_loss = sum(t.amount * t.slippage for t in self.trades if t.side == 'buy')  # 简化
        profit_factor = gross_profit / abs(gross_loss) if gross_loss != 0 else float('inf')

        # 时间信息
        data_start_time = first_data.get('timestamp', 0) if first_data else 0
        data_end_time = last_data.get('timestamp', 0) if last_data else 0
        duration_seconds = (data_end_time - data_start_time) / 1000 if data_start_time and data_end_time else 0

        return BacktestResult(
            start_time=data_start_time,
            end_time=data_end_time,
            duration_seconds=int(duration_seconds),

            # 交易统计
            total_trades=total_trades,
            win_trades=win_trades,
            loss_trades=loss_trades,
            win_rate=win_rate,

            # 收益统计
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            sharpe_ratio=sharpe_ratio,

            # 订单统计
            total_orders=len(self.orders),
            filled_orders=filled_orders,
            rejected_orders=rejected_orders,
            fill_rate=filled_orders / len(self.orders) * 100 if self.orders else 0,

            # 成本统计
            total_slippage=total_slippage,
            avg_slippage=avg_slippage,
            total_commission=sum(t.amount * t.price * self.commission_rate for t in self.trades),

            # 持仓统计
            max_position_size=max(p.size for p in self.positions.values()) if self.positions else 0,
            max_position_value=max(p.size * p.current_price for p in self.positions.values()) if self.positions else 0,

            # 策略指标
            avg_trade_pnl=avg_trade_pnl,
            profit_factor=profit_factor if profit_factor != float('inf') else 0,

            # 详细记录
            trades=[asdict(t) for t in self.trades],
            orders=[asdict(o) for o in self.orders.values()]
        )

    def reset(self):
        """重置回测引擎"""
        self.current_balance = self.initial_balance
        self.orders.clear()
        self.trades.clear()
        self.positions.clear()
        self.order_counter = 0
        self.trade_counter = 0
        self.is_running = False
        logger.info("回测引擎已重置")
