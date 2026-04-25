"""
策略基类模块
定义所有交易策略的通用接口
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """交易信号"""
    signal_type: str  # 'buy', 'sell', 'close'
    instrument_id: str
    price: float
    amount: Optional[float] = None
    reason: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class Position:
    """仓位信息"""
    instrument_id: str
    side: str  # 'long', 'short'
    size: float
    entry_price: float
    unrealized_pnl: float = 0.0
    margin: float = 0.0


class BaseStrategy(ABC):
    """
    交易策略基类
    所有策略都应继承此类并实现其抽象方法
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化策略

        Args:
            name: 策略名称
            config: 策略配置参数
        """
        self.name = name
        self.config = config
        self.is_initialized = False
        self.is_running = False

        # 仓位管理
        self.positions: Dict[str, Position] = {}

        # 数据缓存
        self.data_cache: List[Dict] = []
        self.max_cache_size = config.get('max_cache_size', 1000)

        # 统计信息
        self.stats = {
            'total_signals': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'trades_executed': 0,
        }

        logger.info(f"策略初始化: {name}")

    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化策略
        进行必要的设置、验证参数、初始化指标等

        Returns:
            是否初始化成功
        """
        pass

    @abstractmethod
    def on_data(self, data: Dict) -> Optional[Signal]:
        """
        处理新数据并生成交易信号

        Args:
            data: 市场数据（K线、行情等）

        Returns:
            交易信号，如果没有则返回None
        """
        pass

    @abstractmethod
    def generate_signal(self) -> Optional[Signal]:
        """
        基于当前市场状态生成交易信号
        这是策略的核心逻辑

        Returns:
            交易信号，如果没有则返回None
        """
        pass

    def update_position(self, instrument_id: str, position: Position):
        """
        更新仓位信息

        Args:
            instrument_id: 交易对
            position: 仓位信息
        """
        self.positions[instrument_id] = position
        logger.debug(f"仓位更新: {instrument_id} - {position.side} {position.size}")

    def get_position(self, instrument_id: str) -> Optional[Position]:
        """
        获取指定交易对的仓位

        Args:
            instrument_id: 交易对

        Returns:
            仓位信息，如果没有则返回None
        """
        return self.positions.get(instrument_id)

    def get_all_positions(self) -> Dict[str, Position]:
        """
        获取所有仓位

        Returns:
            所有仓位字典
        """
        return self.positions.copy()

    def on_order_filled(self, order: Dict[str, Any]):
        """
        订单成交回调

        Args:
            order: 订单信息
        """
        instrument_id = order.get('instrument_id')
        side = order.get('side')
        amount = order.get('filled_amount', 0)
        price = order.get('price')

        logger.info(f"订单成交: {instrument_id} {side} {amount} @ {price}")
        self.stats['trades_executed'] += 1

    def on_error(self, error: Exception):
        """
        错误处理回调

        Args:
            error: 错误对象
        """
        logger.error(f"策略错误 [{self.name}]: {error}")

    def start(self):
        """启动策略"""
        if not self.is_initialized:
            self.initialize()

        self.is_running = True
        logger.info(f"策略启动: {self.name}")

    def stop(self):
        """停止策略"""
        self.is_running = False
        logger.info(f"策略停止: {self.name}")

    def get_stats(self) -> Dict:
        """
        获取策略统计信息

        Returns:
            统计信息字典
        """
        return {
            'name': self.name,
            'is_running': self.is_running,
            'positions': len(self.positions),
            'signals': self.stats,
        }

    def validate_config(self, required_keys: List[str]) -> bool:
        """
        验证配置参数

        Args:
            required_keys: 必需的配置键列表

        Returns:
            是否验证通过
        """
        missing_keys = []
        for key in required_keys:
            if key not in self.config or self.config[key] is None:
                missing_keys.append(key)

        if missing_keys:
            logger.error(f"配置参数缺失: {missing_keys}")
            return False

        return True

    def update_cache(self, data: Dict):
        """
        更新数据缓存

        Args:
            data: 新数据
        """
        self.data_cache.append(data)

        # 限制缓存大小
        if len(self.data_cache) > self.max_cache_size:
            self.data_cache.pop(0)

    def get_latest_closes(self, count: int = 100) -> List[float]:
        """
        获取最近的收盘价

        Args:
            count: 数量

        Returns:
            收盘价列表
        """
        closes = []
        for data in reversed(self.data_cache[-count:]):
            if 'close' in data:
                closes.append(data['close'])
            elif 'candle' in data and data['candle']:
                candle = data['candle'][-1]
                closes.append(float(candle[4]))  # close在索引4
        return closes

    def get_latest_data(self, count: int = 100) -> List[Dict]:
        """
        获取最近的数据

        Args:
            count: 数量

        Returns:
            数据列表
        """
        return self.data_cache[-count:]


class DummyStrategy(BaseStrategy):
    """
    虚拟策略（用于测试）
    """

    def initialize(self) -> bool:
        """初始化策略"""
        self.is_initialized = True
        logger.info(f"虚拟策略初始化完成: {self.name}")
        return True

    def on_data(self, data: Dict) -> Optional[Signal]:
        """处理数据"""
        self.update_cache(data)
        return self.generate_signal()

    def generate_signal(self) -> Optional[Signal]:
        """生成信号（虚拟策略不生成信号）"""
        return None
