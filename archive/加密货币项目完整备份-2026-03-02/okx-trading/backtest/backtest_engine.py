"""
OKX Trading - 完善的回测引擎

基于Qlib、VNPy、ai_quant_trade的实践经验，实现了包含以下功能的回测引擎：
1. 订单簿深度检查
2. 滑点模拟
3. 市场冲击
4. 手续费模拟
5. 完整的回测结果输出
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from datetime import datetime
import json
from abc import ABC, abstractmethod


# ==================== 数据类型定义 ====================

class OrderType(Enum):
    """订单类型"""
    MARKET = 'market'      # 市价单
    LIMIT = 'limit'        # 限价单


class OrderSide(Enum):
    """订单方向"""
    BUY = 'buy'            # 买入
    SELL = 'sell'          # 卖出


class OrderStatus(Enum):
    """订单状态"""
    PENDING = 'pending'    # 待执行
    FILLED = 'filled'      # 完全成交
    PARTIAL = 'partial'    # 部分成交
    REJECTED = 'rejected'  # 被拒绝
    CANCELLED = 'cancelled'  # 已取消


@dataclass
class Order:
    """订单"""
    symbol: str                # 标的代码
    side: OrderSide            # 方向（买入/卖出）
    order_type: OrderType      # 订单类型
    quantity: float            # 数量
    price: Optional[float] = None     # 限价单价格
    timestamp: Optional[datetime] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    slippage: float = 0.0      # 实际滑点
    market_impact: float = 0.0      # 市场冲击
    commission: float = 0.0    # 手续费


@dataclass
class Trade:
    """成交记录"""
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime
    order_id: str
    slippage: float
    market_impact: float
    commission: float


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float
    avg_price: float
    total_cost: float
    current_price: float
    unrealized_pnl: float = 0.0


@dataclass
class BacktestMetrics:
    """回测指标"""
    # 收益指标
    total_return: float = 0.0
    annual_return: float = 0.0
    cumulative_return: float = 0.0

    # 风险指标
    max_drawdown: float = 0.0
    volatility: float = 0.0
    downside_volatility: float = 0.0

    # 风险调整收益
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0

    # 交易指标
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0

    # 持仓指标
    avg_holding_time: float = 0.0  # 平均持仓时间（小时）

    # 手续费统计
    total_commission: float = 0.0
    total_slippage: float = 0.0
    total_market_impact: float = 0.0


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    equity_curve: pd.Series
    metrics: BacktestMetrics
    trades: List[Trade] = field(default_factory=list)
    positions_history: List[Dict[str, Position]] = field(default_factory=list)


# ==================== 市场环境模拟 ====================

class MarketEnvironment:
    """
    市场环境模拟器
    从历史数据推断市场微观结构
    """

    def __init__(self, data: pd.DataFrame, symbol: str):
        """
        初始化市场环境

        Args:
            data: 历史K线数据，需包含 open/high/low/close/volume
            symbol: 标的代码
        """
        self.data = data.copy()
        self.symbol = symbol

        # 计算ATR（用于订单簿深度推断）
        self.data['atr'] = self._calculate_atr(period=14)

        # 计算日均交易量
        self.avg_volume = self.data['volume'].mean()

        # 计算平均价差（用于滑点估算）
        self.data['price_range'] = self.data['high'] - self.data['low']
        self.avg_spread = self.data['price_range'].mean() * 0.01  # 假设价差为日内波动的1%

    def _calculate_atr(self, period: int) -> pd.Series:
        """计算ATR（平均真实波幅）"""
        high_low = self.data['high'] - self.data['low']
        high_close = np.abs(self.data['high'] - self.data['close'].shift())
        low_close = np.abs(self.data['low'] - self.data['close'].shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        return atr

    def get_orderbook_depth(self, timestamp: datetime, price: float) -> Dict[str, float]:
        """
        推断订单簿深度

        从历史数据推断订单簿深度，基于：
        1. ATR（波动越大，流动性可能越差）
        2. 成交量（成交量越大，流动性越好）
        3. 价格位置（距离开盘价越远，流动性可能越差）

        Args:
            timestamp: 时间点
            price: 当前价格

        Returns:
            {'bid_depth': 委买深度, 'ask_depth': 委卖深度, 'total_depth': 总深度}
        """
        # 找到对应时间的数据
        idx = self.data.index.get_indexer([timestamp], method='nearest')[0]
        if idx < 0:
            idx = 0

        row = self.data.iloc[idx]

        # 基于ATR推断深度（ATR越大，深度越小）
        atr = row['atr']
        base_depth_mult = 1.0 / (atr / price * 10)  # 波动率越大，深度越小

        # 基于成交量调整
        volume_mult = row['volume'] / self.avg_volume

        # 计算深度
        total_depth = price * volume_mult * base_depth_mult * 1000  # 基础深度

        # 买卖盘深度分布（假设对称）
        bid_depth = total_depth * 0.5
        ask_depth = total_depth * 0.5

        return {
            'bid_depth': bid_depth,
            'ask_depth': ask_depth,
            'total_depth': total_depth
        }

    def get_liquidity(self, timestamp: datetime, price: float) -> float:
        """
        获取市场流动性

        Args:
            timestamp: 时间点
            price: 当前价格

        Returns:
            流动性指标（越大流动性越好）
        """
        depth = self.get_orderbook_depth(timestamp, price)
        return depth['total_depth']


# ==================== 订单执行器 ====================

class OrderExecutor:
    """
    订单执行器
    模拟真实交易执行，包含滑点、市场冲击、手续费
    """

    def __init__(
        self,
        maker_commission: float = 0.0008,    # Maker手续费 0.08%
        taker_commission: float = 0.0010,    # Taker手续费 0.1%
        slippage_model: str = 'size_based',  # 滑点模型
        market_impact_model: str = 'linear'  # 市场冲击模型
    ):
        """
        初始化订单执行器

        Args:
            maker_commission: Maker手续费率
            taker_commission: Taker手续费率
            slippage_model: 滑点模型（'size_based', 'linear', 'exponential'）
            market_impact_model: 市场冲击模型（'linear', 'sqrt', 'exponential'）
        """
        self.maker_commission = maker_commission
        self.taker_commission = taker_commission
        self.slippage_model = slippage_model
        self.market_impact_model = market_impact_model

        # 滑点参数
        self.slippage_params = {
            'min_slippage': 0.0005,      # 最小滑点 0.05%
            'max_slippage': 0.0020,      # 最大滑点 0.2%
            'market_order_premium': 0.5, # 市价单滑点加成
        }

        # 市场冲击参数
        self.market_impact_params = {
            'coeff': 0.0001,  # 市场冲击系数
        }

    def execute_order(
        self,
        order: Order,
        market_price: float,
        liquidity: float,
        market_env: MarketEnvironment
    ) -> tuple[OrderStatus, float, float, float]:
        """
        执行订单

        考虑以下因素：
        1. 订单簿深度检查
        2. 滑点计算
        3. 市场冲击计算
        4. 手续费计算

        Args:
            order: 订单
            market_price: 市场价格
            liquidity: 市场流动性
            market_env: 市场环境

        Returns:
            (订单状态, 成交价格, 实际滑点, 市场冲击)
        """
        order_value = order.quantity * market_price

        # 1. 检查订单簿深度
        if order.order_type == OrderType.MARKET:
            # 市价单立即执行，检查是否有足够流动性
            required_depth = order_value
            available_depth = liquidity * 0.3  # 假设只使用30%的即时深度

            if required_depth > available_depth:
                # 深度不足，拒绝执行
                order.status = OrderStatus.REJECTED
                return OrderStatus.REJECTED, market_price, 0.0, 0.0

        # 2. 计算滑点
        slippage = self._calculate_slippage(order, liquidity, market_price)

        # 3. 计算市场冲击
        market_impact = self._calculate_market_impact(order, market_price, market_env.avg_volume)

        # 4. 计算成交价格
        if order.side == OrderSide.BUY:
            # 买入：价格 = 市场价 + 滑点 + 市场冲击
            execution_price = market_price * (1 + slippage + market_impact)
        else:
            # 卖出：价格 = 市场价 - 滑点 - 市场冲击
            execution_price = market_price * (1 - slippage - market_impact)

        # 5. 计算手续费
        commission = self._calculate_commission(order, execution_price)

        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = execution_price
        order.slippage = slippage
        order.market_impact = market_impact
        order.commission = commission

        return OrderStatus.FILLED, execution_price, slippage, market_impact

    def _calculate_slippage(
        self,
        order: Order,
        liquidity: float,
        market_price: float
    ) -> float:
        """
        计算滑点

        基于订单大小和流动性的滑点模型：
        - 大滑点发生在订单量大、流动性低的情况
        - 市价单滑点更大

        Args:
            order: 订单
            liquidity: 流动性
            market_price: 市场价格

        Returns:
            滑点率（比例）
        """
        order_value = order.quantity * market_price

        # 1. 基础滑点：订单占比
        trade_ratio = order_value / liquidity if liquidity > 0 else 1.0

        # 2. 市价单加成
        market_order_penalty = 0
        if order.order_type == OrderType.MARKET:
            market_order_penalty = self.slippage_params['market_order_premium']

        # 3. 根据模型计算滑点
        if self.slippage_model == 'size_based':
            # 基于订单大小
            slippage = (
                self.slippage_params['min_slippage'] +
                (self.slippage_params['max_slippage'] - self.slippage_params['min_slippage']) *
                min(trade_ratio, 1.0)
            ) * (1 + market_order_penalty)

        elif self.slippage_model == 'linear':
            # 线性模型
            slippage = (
                self.slippage_params['min_slippage'] +
                self.market_impact_params['coeff'] * trade_ratio
            ) * (1 + market_order_penalty)

        elif self.slippage_model == 'exponential':
            # 指数模型（大订单滑点急剧增加）
            slippage = self.slippage_params['min_slippage'] * np.exp(
                5 * trade_ratio * (1 + market_order_penalty)
            )
            slippage = min(slippage, self.slippage_params['max_slippage'] * 2)

        else:
            slippage = self.slippage_params['min_slippage']

        return slippage

    def _calculate_market_impact(
        self,
        order: Order,
        market_price: float,
        avg_volume: float
    ) -> float:
        """
        计算市场冲击

        市场冲击模型：
        - 大订单会推高买入价格或压低卖出价格
        - 基于订单大小和日均交易量的比率

        Args:
            order: 订单
            market_price: 市场价格
            avg_volume: 日均交易量

        Returns:
            市场冲击率（比例）
        """
        order_value = order.quantity * market_price

        # 订单占日均交易量的比例
        daily_ratio = order_value / (avg_volume * market_price) if avg_volume > 0 else 0

        if self.market_impact_model == 'linear':
            # 线性模型
            market_impact = self.market_impact_params['coeff'] * daily_ratio

        elif self.market_impact_model == 'sqrt':
            # 平方根模型（阿尔法法则）
            market_impact = self.market_impact_params['coeff'] * np.sqrt(daily_ratio)

        elif self.market_impact_model == 'exponential':
            # 指数模型（极端情况）
            market_impact = self.market_impact_params['coeff'] * np.exp(daily_ratio * 10)

        else:
            market_impact = 0.0

        # 限制最大冲击（防止模型发散）
        market_impact = min(market_impact, 0.01)  # 最大1%的冲击

        return market_impact

    def _calculate_commission(
        self,
        order: Order,
        execution_price: float
    ) -> float:
        """
        计算手续费

        OKX费率：
        - Maker: 0.08%
        - Taker: 0.1%

        Args:
            order: 订单
            execution_price: 成交价格

        Returns:
            手续费金额
        """
        order_value = order.quantity * execution_price

        # 判断是Maker还是Taker
        if order.order_type == OrderType.LIMIT:
            # 限价单通常是Maker
            commission_rate = self.maker_commission
        else:
            # 市价单是Taker
            commission_rate = self.taker_commission

        commission = order_value * commission_rate

        return commission


# ==================== 策略基类 ====================

class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, name: str, params: Dict[str, Any]):
        self.name = name
        self.params = params

    @abstractmethod
    def generate_signals(
        self,
        data: pd.DataFrame,
        positions: Dict[str, Position],
        current_time: datetime
    ) -> List[Order]:
        """
        生成交易信号

        Args:
            data: 当前和历史数据
            positions: 当前持仓
            current_time: 当前时间

        Returns:
            订单列表
        """
        pass

    def on_trade(self, trade: Trade):
        """成交回调"""
        pass

    def on_order_filled(self, order: Order):
        """订单成交回调"""
        pass


# ==================== 网格策略 ====================

class GridStrategy(BaseStrategy):
    """
    网格交易策略

    在指定的价格区间内均匀布置网格，价格触碰到网格线时自动买卖。

    策略逻辑：
    1. 设定价格区间 [low_price, high_price]
    2. 将区间分为N个网格，每个网格间距 = (high_price - low_price) / N
    3. 价格上涨触碰网格线时卖出
    4. 价格下跌触碰网格线时买入
    5. 每个网格固定投资金额
    """

    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        self.grid_count = params.get('grid_count', 10)  # 网格数量
        self.investment_per_grid = params.get('investment_per_grid', 10000)  # 每格金额
        self.price_range_pct = params.get('price_range_pct', 0.20)  # 价格区间百分比（±10%）
        self.symbol = params.get('symbol', 'BTC-USDT')

        # 动态计算的网格参数
        self.low_price = None
        self.high_price = None
        self.grid_step = None
        self.grid_levels = []

        # 跟踪已挂的网格订单
        self.active_orders = {}  # {price: OrderType}

    def setup_grid(self, data: Dict[str, pd.DataFrame], current_price: float):
        """
        设置网格区间和价格水平

        Args:
            data: 市场数据
            current_price: 当前价格
        """
        # 计算价格区间
        self.high_price = current_price * (1 + self.price_range_pct / 2)
        self.low_price = current_price * (1 - self.price_range_pct / 2)

        # 计算网格间距
        self.grid_step = (self.high_price - self.low_price) / self.grid_count

        # 生成网格价格水平
        self.grid_levels = [self.low_price + i * self.grid_step for i in range(self.grid_count + 1)]

        print(f"网格设置完成:")
        print(f"  价格区间: ${self.low_price:.2f} - ${self.high_price:.2f}")
        print(f"  网格数量: {self.grid_count}")
        print(f"  网格间距: ${self.grid_step:.2f}")

    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        positions: Dict[str, Position],
        current_time: datetime
    ) -> List[Order]:
        """
        生成网格交易信号

        Args:
            data: 市场数据
            positions: 持仓
            current_time: 当前时间

        Returns:
            订单列表
        """
        orders = []

        if self.symbol not in data:
            return orders

        df = data[self.symbol]
        current_price = df.iloc[-1]['close']

        # 首次设置网格
        if self.low_price is None:
            self.setup_grid(data, current_price)
            return orders

        # 检查是否超出网格范围
        if current_price < self.low_price or current_price > self.high_price:
            # 价格超出范围，重新设置网格
            print(f"价格 ${current_price:.2f} 超出网格范围，重新设置网格...")
            self.setup_grid(data, current_price)
            return orders

        # 获取当前持仓
        current_position = positions.get(self.symbol)
        current_quantity = current_position.quantity if current_position else 0.0

        # 检查是否触碰到网格线
        for i, level_price in enumerate(self.grid_levels[:-1]):  # 最后一个线不触发
            # 买入信号：价格下跌到网格线（从上方接近）
            if current_price <= level_price and current_price >= level_price - self.grid_step:
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
                    self.active_orders[level_price] = OrderSide.BUY

            # 卖出信号：价格上涨到网格线（从下方接近）
            if current_price >= level_price and current_price <= level_price + self.grid_step:
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
                        self.active_orders[level_price] = OrderSide.SELL

        return orders

    def _bought_near_price(self, price: float) -> bool:
        """检查是否在价格附近买入过"""
        for active_price, side in self.active_orders.items():
            if side == OrderSide.BUY and abs(active_price - price) < self.grid_step * 0.5:
                return True
        return False

    def _sold_near_price(self, price: float) -> bool:
        """检查是否在价格附近卖出过"""
        for active_price, side in self.active_orders.items():
            if side == OrderSide.SELL and abs(active_price - price) < self.grid_step * 0.5:
                return True
        return False


# ==================== 回测引擎 ====================

class BacktestEngine:
    """
    回测引擎

    核心功能：
    1. 模拟真实市场环境（订单簿深度、流动性）
    2. 精确模拟订单执行（滑点、市场冲击、手续费）
    3. 跟踪持仓和资金
    4. 生成完整的回测报告
    """

    def __init__(
        self,
        initial_capital: float,
        maker_commission: float = 0.0008,
        taker_commission: float = 0.0010,
        slippage_model: str = 'size_based',
        market_impact_model: str = 'linear'
    ):
        """
        初始化回测引擎

        Args:
            initial_capital: 初始资金
            maker_commission: Maker手续费率
            taker_commission: Taker手续费率
            slippage_model: 滑点模型
            market_impact_model: 市场冲击模型
        """
        self.initial_capital = initial_capital
        self.available_cash = initial_capital
        self.total_equity = initial_capital

        # 订单执行器
        self.executor = OrderExecutor(
            maker_commission=maker_commission,
            taker_commission=taker_commission,
            slippage_model=slippage_model,
            market_impact_model=market_impact_model
        )

        # 回测状态
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict[str, Any]] = []
        self.order_count = 0

        # 字典：symbol -> (datetime -> price)，用于持仓成本记录
        self.entry_times: Dict[str, datetime] = {}

    def run_backtest(
        self,
        data: Dict[str, pd.DataFrame],
        strategy: BaseStrategy,
        params: Optional[Dict[str, Any]] = None
    ) -> BacktestResult:
        """
        运行回测

        Args:
            data: 历史数据字典 {symbol: DataFrame}
            strategy: 策略实例
            params: 策略参数

        Returns:
            回测结果
        """
        print(f"开始回测: {strategy.name}")
        print(f"初始资金: ${self.initial_capital:,.2f}")

        # 更新策略参数
        if params:
            strategy.params.update(params)

        # 创建市场环境
        market_envs = {
            symbol: MarketEnvironment(df, symbol)
            for symbol, df in data.items()
        }

        # 获取时间索引
        all_dates = set()
        for df in data.values():
            all_dates.update(df.index)
        dates = sorted(all_dates)

        # 初始记录
        self._record_equity(dates[0] if dates else datetime.now())

        # 遍历每个交易日
        for i, current_date in enumerate(dates):
            # 更新持仓价值
            self._update_positions_value(data, current_date)

            # 生成策略信号
            current_data = {
                symbol: df.loc[df.index[:i+1]]
                for symbol, df in data.items()
            }

            orders = strategy.generate_signals(
                current_data,
                self.positions,
                current_date
            )

            # 执行订单
            for order in orders:
                self._execute_order(order, data, current_date, market_envs)

            # 记录权益曲线
            self._record_equity(current_date)

            # 阶段性输出
            if (i + 1) % 100 == 0:
                print(f"  已处理 {i+1}/{len(dates)} 个交易日")

        # 最终更新持仓价值
        if dates:
            self._update_positions_value(data, dates[-1])
            self._record_equity(dates[-1])

        print(f"回测完成")
        print(f"最终资金: ${self.total_equity:,.2f}")
        print(f"总交易次数: {len(self.trades)}")

        # 生成回测结果
        result = self._generate_result(strategy.name, dates[0] if dates else None, dates[-1] if dates else None)

        return result

    def _execute_order(
        self,
        order: Order,
        data: Dict[str, pd.DataFrame],
        current_date: datetime,
        market_envs: Dict[str, MarketEnvironment]
    ):
        """
        执行订单

        Args:
            order: 订单
            data: 数据
            current_date: 当前日期
            market_envs: 市场环境
        """
        order.timestamp = current_date
        order_id = f"order_{self.order_count}"
        self.order_count += 1

        # 获取当前价格
        if order.symbol not in data:
            order.status = OrderStatus.REJECTED
            return

        idx = data[order.symbol].index.get_indexer([current_date], method='nearest')[0]
        if idx < 0:
            order.status = OrderStatus.REJECTED
            return

        market_price = data[order.symbol].iloc[idx]['close']

        # 获取市场环境
        market_env = market_envs.get(order.symbol)
        if not market_env:
            order.status = OrderStatus.REJECTED
            return

        # 获取流动性
        liquidity = market_env.get_liquidity(current_date, market_price)

        # 执行订单
        status, execution_price, slippage, market_impact = self.executor.execute_order(
            order, market_price, liquidity, market_env
        )

        if status == OrderStatus.REJECTED:
            print(f"  订单被拒绝: {order.symbol} {order.side.value} {order.quantity}")
            return

        # 计算手续费
        commission = order.commission

        # 记录成交
        trade = Trade(
            symbol=order.symbol,
            side=order.side,
            quantity=order.filled_quantity,
            price=execution_price,
            timestamp=current_date,
            order_id=order_id,
            slippage=slippage,
            market_impact=market_impact,
            commission=commission
        )
        self.trades.append(trade)

        # 更新持仓和资金
        if order.side == OrderSide.BUY:
            # 买入
            order_value = order.quantity * execution_price
            total_cost = order_value + commission

            if total_cost > self.available_cash:
                # 资金不足
                order.status = OrderStatus.REJECTED
                return

            self.available_cash -= total_cost

            if order.symbol in self.positions:
                # 已有持仓，加仓
                pos = self.positions[order.symbol]
                old_quantity = pos.quantity
                old_cost = pos.total_cost

                new_quantity = old_quantity + order.quantity
                new_cost = old_cost + total_cost

                pos.quantity = new_quantity
                pos.avg_price = new_cost / new_quantity
                pos.total_cost = new_cost
                pos.current_price = execution_price
            else:
                # 新建持仓
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    avg_price=execution_price,
                    total_cost=total_cost,
                    current_price=execution_price
                )
                self.entry_times[order.symbol] = current_date

        elif order.side == OrderSide.SELL:
            # 卖出
            if order.symbol not in self.positions:
                # 没有持仓
                order.status = OrderStatus.REJECTED
                return

            pos = self.positions[order.symbol]

            if order.quantity > pos.quantity:
                # 卖出数量超过持仓
                order.status = OrderStatus.REJECTED
                return

            # 计算收益
            order_value = order.quantity * execution_price
            net_proceeds = order_value - commission

            # 计算实现盈亏
            cost_basis = (pos.total_cost / pos.quantity) * order.quantity
            realized_pnl = net_proceeds - cost_basis

            # 更新资金
            self.available_cash += net_proceeds

            # 更新或删除持仓
            if order.quantity == pos.quantity:
                # 全部卖出
                del self.positions[order.symbol]
                if order.symbol in self.entry_times:
                    del self.entry_times[order.symbol]
            else:
                # 部分卖出
                remaining_quantity = pos.quantity - order.quantity
                remaining_cost = pos.total_cost - cost_basis

                pos.quantity = remaining_quantity
                pos.total_cost = remaining_cost
                pos.current_price = execution_price

        # 更新总权益
        self._update_total_equity(data, current_date)

        # 回调
        strategy = getattr(self, '_current_strategy', None)
        if strategy:
            strategy.on_trade(trade)
            strategy.on_order_filled(order)

    def _update_positions_value(self, data: Dict[str, pd.DataFrame], current_date: datetime):
        """更新持仓价值"""
        for symbol, position in self.positions.items():
            if symbol in data:
                idx = data[symbol].index.get_indexer([current_date], method='nearest')[0]
                if idx >= 0:
                    position.current_price = data[symbol].iloc[idx]['close']
                    position.unrealized_pnl = (
                        (position.current_price - position.avg_price) * position.quantity
                    )

    def _update_total_equity(self, data: Dict[str, pd.DataFrame], current_date: datetime):
        """更新总权益"""
        positions_value = sum(
            pos.quantity * pos.current_price
            for pos in self.positions.values()
        )
        self.total_equity = self.available_cash + positions_value

    def _record_equity(self, current_date: datetime):
        """记录权益曲线"""
        self.equity_curve.append({
            'timestamp': current_date,
            'equity': self.total_equity,
            'cash': self.available_cash,
            'positions_value': self.total_equity - self.available_cash
        })

    def _generate_result(
        self,
        strategy_name: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> BacktestResult:
        """生成回测结果"""
        # 生成权益曲线Series
        equity_series = pd.Series(
            [e['equity'] for e in self.equity_curve],
            index=[e['timestamp'] for e in self.equity_curve]
        )

        # 计算收益率
        returns = equity_series.pct_change().dropna()

        # 计算指标
        metrics = self._calculate_metrics(equity_series, returns, self.trades)

        # 生成回测结果
        result = BacktestResult(
            strategy_name=strategy_name,
            start_date=start_date or datetime.min,
            end_date=end_date or datetime.max,
            initial_capital=self.initial_capital,
            final_capital=self.total_equity,
            equity_curve=equity_series,
            metrics=metrics,
            trades=self.trades,
            positions_history=[]
        )

        return result

    def _calculate_metrics(
        self,
        equity_curve: pd.Series,
        returns: pd.Series,
        trades: List[Trade]
    ) -> BacktestMetrics:
        """计算回测指标"""
        metrics = BacktestMetrics()

        # 收益指标
        if len(equity_curve) > 0:
            metrics.total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1)
            metrics.cumulative_return = metrics.total_return

            # 年化收益率（假设252个交易日）
            if len(equity_curve) > 0:
                years = len(equity_curve) / 252
                if years > 0:
                    metrics.annual_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1/years) - 1

        # 风险指标
        if len(returns) > 0:
            metrics.volatility = returns.std() * np.sqrt(252)  # 年化波动率

            # 下行波动率
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0:
                metrics.downside_volatility = downside_returns.std() * np.sqrt(252)

            # 最大回撤
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            metrics.max_drawdown = drawdown.min() if len(drawdown) > 0 else 0

        # 风险调整收益
        if len(returns) > 0 and metrics.volatility > 0:
            # 夏普比率（假设无风险利率3%）
            risk_free_rate = 0.03
            excess_returns = returns - risk_free_rate / 252
            metrics.sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252)

            # 索提诺比率
            if metrics.downside_volatility > 0:
                metrics.sortino_ratio = returns.mean() / metrics.downside_volatility * np.sqrt(252)

        # 卡尔玛比率
        if metrics.max_drawdown != 0:
            metrics.calmar_ratio = metrics.annual_return / abs(metrics.max_drawdown)

        # 交易指标
        metrics.total_trades = len(trades)

        if metrics.total_trades > 0:
            # 计算胜率
            winning_trades = [t for t in trades if self._is_winning_trade(t)]
            metrics.win_rate = len(winning_trades) / metrics.total_trades

            # 计算盈亏比
            profits = [self._calc_trade_profit(t) for t in winning_trades]
            losses = [self._calc_trade_profit(t) for t in trades if not self._is_winning_trade(t)]

            if profits:
                metrics.avg_win = np.mean(profits)

            if losses:
                metrics.avg_loss = np.mean(losses)  # 负值

            if losses and metrics.avg_loss != 0:
                metrics.profit_factor = sum(profits) / abs(sum(losses))

            # 平均持仓时间
            if self.entry_times:
                holding_times = []
                trade_positions = {}

                # 按symbol分组交易
                for trade in trades:
                    symbol = trade.symbol
                    if symbol not in trade_positions:
                        trade_positions[symbol] = []

                    if trade.side == OrderSide.BUY:
                        trade_positions[symbol].append({'buy': trade.timestamp, 'sell': None})
                    elif trade.side == OrderSide.SELL and trade_positions[symbol]:
                        if not trade_positions[symbol][-1]['sell']:
                            trade_positions[symbol][-1]['sell'] = trade.timestamp
                            duration = (trade.timestamp - trade_positions[symbol][-1]['buy']).total_seconds() / 3600
                            holding_times.append(duration)

                if holding_times:
                    metrics.avg_holding_time = np.mean(holding_times)

        # 手续费和滑点统计
        metrics.total_commission = sum(t.commission for t in trades)
        metrics.total_slippage = sum(t.slippage for t in trades)
        metrics.total_market_impact = sum(t.market_impact for t in trades)

        return metrics

    def _is_winning_trade(self, trade: Trade) -> bool:
        """判断是否是盈利交易"""
        if trade.side == OrderSide.SELL:
            # 需要找到对应的买入单
            for t in reversed(self.trades):
                if t.symbol == trade.symbol and t.side == OrderSide.BUY and t.timestamp < trade.timestamp:
                    return trade.price > t.price
        return trade.price > 0  # 简化处理

    def _calc_trade_profit(self, trade: Trade) -> float:
        """计算交易盈亏"""
        if trade.side == OrderSide.SELL:
            for t in reversed(self.trades):
                if t.symbol == trade.symbol and t.side == OrderSide.BUY and t.timestamp < trade.timestamp:
                    return (trade.price - t.price) * trade.quantity - trade.commission - t.commission
        return 0.0

    def generate_report(self, result: BacktestResult, filepath: Optional[str] = None) -> Dict[str, Any]:
        """
        生成JSON格式回测报告

        Args:
            result: 回测结果
            filepath: 报告输出路径（可选）

        Returns:
            报告字典
        """
        report = {
            'strategy_name': result.strategy_name,
            'backtest_period': {
                'start': result.start_date.isoformat() if result.start_date else None,
                'end': result.end_date.isoformat() if result.end_date else None,
            },
            'capital': {
                'initial': result.initial_capital,
                'final': result.final_capital,
            },
            'returns': {
                'total': result.metrics.total_return,
                'total_pct': f"{result.metrics.total_return * 100:.2f}%",
                'annual': result.metrics.annual_return,
                'annual_pct': f"{result.metrics.annual_return * 100:.2f}%",
            },
            'risk_metrics': {
                'max_drawdown': result.metrics.max_drawdown,
                'max_drawdown_pct': f"{result.metrics.max_drawdown * 100:.2f}%",
                'volatility': result.metrics.volatility,
                'volatility_pct': f"{result.metrics.volatility * 100:.2f}%",
            },
            'risk_adjusted_returns': {
                'sharpe_ratio': result.metrics.sharpe_ratio,
                'sortino_ratio': result.metrics.sortino_ratio,
                'calmar_ratio': result.metrics.calmar_ratio,
            },
            'trading_metrics': {
                'total_trades': result.metrics.total_trades,
                'win_rate': result.metrics.win_rate,
                'win_rate_pct': f"{result.metrics.win_rate * 100:.2f}%",
                'profit_factor': result.metrics.profit_factor,
                'avg_win': result.metrics.avg_win,
                'avg_loss': result.metrics.avg_loss,
                'avg_holding_time_hours': result.metrics.avg_holding_time,
            },
            'costs': {
                'total_commission': result.metrics.total_commission,
                'total_slippage': result.metrics.total_slippage,
                'total_market_impact': result.metrics.total_market_impact,
            },
            'trades': [
                {
                    'symbol': t.symbol,
                    'side': t.side.value,
                    'quantity': t.quantity,
                    'price': t.price,
                    'timestamp': t.timestamp.isoformat(),
                    'slippage': t.slippage,
                    'market_impact': t.market_impact,
                    'commission': t.commission,
                }
                for t in result.trades
            ],
            'equity_curve': [
                {
                    'timestamp': e['timestamp'].isoformat(),
                    'equity': e['equity'],
                    'cash': e['cash'],
                    'positions_value': e['positions_value'],
                }
                for e in [
                    {'timestamp': ts, 'equity': val, 'cash': 0.0, 'positions_value': 0.0}
                    for ts, val in result.equity_curve.items()
                ]
            ]
        }

        # 保存到文件
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"回测报告已保存到: {filepath}")

        return report


# ==================== 辅助函数 ====================

def print_backtest_summary(result: BacktestResult):
    """
    打印回测摘要

    Args:
        result: 回测结果
    """
    print("\n" + "="*70)
    print(f"回测报告 - {result.strategy_name}")
    print("="*70)

    print("\n【资金】")
    print(f"初始资金: ${result.initial_capital:,.2f}")
    print(f"最终资金: ${result.final_capital:,.2f}")
    print(f"总收益率: {result.metrics.total_return * 100:+.2f}%")
    print(f"年化收益率: {result.metrics.annual_return * 100:+.2f}%")

    print("\n【风险指标】")
    print(f"最大回撤: {result.metrics.max_drawdown * 100:.2f}%")
    print(f"年化波动率: {result.metrics.volatility * 100:.2f}%")

    print("\n【风险调整收益】")
    print(f"夏普比率: {result.metrics.sharpe_ratio:.4f}")
    print(f"索提诺比率: {result.metrics.sortino_ratio:.4f}")
    print(f"卡尔玛比率: {result.metrics.calmar_ratio:.4f}")

    print("\n【交易指标】")
    print(f"总交易次数: {result.metrics.total_trades}")
    print(f"胜率: {result.metrics.win_rate * 100:.2f}%")
    print(f"盈亏比: {result.metrics.profit_factor:.4f}")
    print(f"平均盈利: ${result.metrics.avg_win:.2f}")
    print(f"平均亏损: ${result.metrics.avg_loss:.2f}")
    print(f"平均持仓时间: {result.metrics.avg_holding_time:.2f} 小时")

    print("\n【成本分析】")
    print(f"手续费总额: ${result.metrics.total_commission:,.2f}")
    print(f"滑点总额: {result.metrics.total_slippage:.4f}")
    print(f"市场冲击总额: {result.metrics.total_market_impact:.4f}")

    print("\n" + "="*70)


def create_sample_strategy(strategy_name: str = "SampleStrategy") -> BaseStrategy:
    """
    创建示例策略（用于测试）

    这是一个简单的均线交叉策略：
    - 快线上穿慢线：买入
    - 快线下穿慢线：卖出

    Args:
        strategy_name: 策略名称

    Returns:
        策略实例
    """
    class SampleStrategy(BaseStrategy):
        def __init__(self, name: str, params: Dict[str, Any]):
            super().__init__(name, params)
            self.fast_period = params.get('fast_period', 10)
            self.slow_period = params.get('slow_period', 30)
            self.position_size = params.get('position_size', 100)  # 固定持仓数量

        def generate_signals(
            self,
            data: Dict[str, pd.DataFrame],
            positions: Dict[str, Position],
            current_time: datetime
        ) -> List[Order]:
            orders = []

            for symbol, df in data.items():
                if len(df) < self.slow_period:
                    continue

                # 计算均线
                df['fast_ma'] = df['close'].rolling(window=self.fast_period).mean()
                df['slow_ma'] = df['close'].rolling(window=self.slow_period).mean()

                # 获取当前行
                current_row = df.iloc[-1]
                prev_row = df.iloc[-2] if len(df) > 1 else current_row

                # 均线交叉信号
                fast_ma = current_row['fast_ma']
                slow_ma = current_row['slow_ma']
                prev_fast_ma = prev_row['fast_ma']
                prev_slow_ma = prev_row['slow_ma']

                # 买入信号：快线上穿慢线
                if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
                    if symbol not in positions:
                        orders.append(Order(
                            symbol=symbol,
                            side=OrderSide.BUY,
                            order_type=OrderType.MARKET,
                            quantity=self.position_size
                        ))

                # 卖出信号：快线下穿慢线
                elif prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
                    if symbol in positions:
                        orders.append(Order(
                            symbol=symbol,
                            side=OrderSide.SELL,
                            order_type=OrderType.MARKET,
                            quantity=positions[symbol].quantity
                        ))

            return orders

    return SampleStrategy(strategy_name, {})


# ==================== 示例使用 ====================

if __name__ == "__main__":
    # 创建示例数据
    import pandas as pd
    from datetime import datetime, timedelta

    # 生成模拟数据
    np.random.seed(42)
    n_days = 500
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(n_days)]

    # 生成价格走势（布朗运动）
    returns = np.random.normal(0.001, 0.02, n_days)
    price = 100 * np.cumprod(1 + returns)

    data = pd.DataFrame({
        'date': dates,
        'open': price * (1 + np.random.normal(0, 0.005, n_days)),
        'high': price * (1 + np.abs(np.random.normal(0, 0.01, n_days))),
        'low': price * (1 - np.abs(np.random.normal(0, 0.01, n_days))),
        'close': price,
        'volume': np.random.uniform(1000000, 10000000, n_days)
    })
    data = data.set_index('date')

    # 创建回测引擎
    engine = BacktestEngine(
        initial_capital=100000,
        maker_commission=0.0008,
        taker_commission=0.0010,
        slippage_model='size_based',
        market_impact_model='linear'
    )

    # 创建策略
    strategy = create_sample_strategy("MoveAverageStrategy")
    strategy.params = {
        'fast_period': 10,
        'slow_period': 30,
        'position_size': 50
    }

    # 运行回测
    result = engine.run_backtest(
        data={'BTC-USDT': data},
        strategy=strategy
    )

    # 打印摘要
    print_backtest_summary(result)

    # 生成报告
    report = engine.generate_report(result, 'backtest_report.json')
    print("\nJSON报告已生成")
