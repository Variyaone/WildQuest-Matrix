"""
订单执行器模块
负责执行交易订单
"""

import logging
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import sys
from pathlib import Path

# 导入OKX客户端
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
from okx_api_client import OKXClient

logger = logging.getLogger(__name__)


class OrderExecutor(ABC):
    """
    订单执行器基类
    定义订单执行的通用接口
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化执行器

        Args:
            config: 配置参数
        """
        self.config = config
        self.is_initialized = False

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str = 'limit',
        amount: float = None,
        price: float = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        下单

        Args:
            symbol: 交易对
            side: 买卖方向
            order_type: 订单类型
            amount: 数量
            price: 价格（限价单必需）
            **kwargs: 其他参数

        Returns:
            订单信息
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        取消订单

        Args:
            order_id: 订单ID
            symbol: 交易对

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def get_order(self, order_id: str, symbol: str) -> Optional[Dict]:
        """
        查询订单

        Args:
            order_id: 订单ID
            symbol: 交易对

        Returns:
            订单信息
        """
        pass


class OKXOrderExecutor(OrderExecutor):
    """
    OKX订单执行器
    使用OKX API执行订单
    """

    def __init__(self, config_path: str = None, config_dict: dict = None):
        """
        初始化OKX执行器

        Args:
            config_path: 配置文件路径
            config_dict: 配置字典
        """
        super().__init__(config_dict or {})

        self.client = None
        self.orders: Dict[str, Dict] = {}  # 订单缓存 {order_id: order_info}

        # 初始化客户端
        self._init_client(config_path, config_dict)

    def _init_client(self, config_path: str, config_dict: dict):
        """初始化OKX客户端"""
        try:
            self.client = OKXClient(config_path=config_path, config_dict=config_dict)
            self.is_initialized = True
            logger.info("OKX订单执行器初始化成功")
        except Exception as e:
            logger.error(f"OKX客户端初始化失败: {e}")
            raise

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str = 'limit',
        amount: float = None,
        price: float = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        下单

        Args:
            symbol: 交易对，如 'BTC/USDT:USDT'
            side: 买卖方向 'buy' 或 'sell'
            order_type: 订单类型 'limit' 或 'market'
            amount: 数量
            price: 价格（限价单必需）
            **kwargs: 其他参数
                - reduce_only: 是否只减仓
                - post_only: 是否只作为挂单

        Returns:
            订单信息字典
        """
        try:
            if not self.is_initialized:
                raise RuntimeError("执行器未初始化")

            if side not in ['buy', 'sell']:
                raise ValueError(f"无效的买卖方向: {side}")

            if order_type == 'limit' and price is None:
                raise ValueError("限价单需要指定价格")

            if amount is None:
                raise ValueError("必须指定订单数量")

            # 提取额外参数
            reduce_only = kwargs.get('reduce_only', False)
            post_only = kwargs.get('post_only', False)

            # 下单
            order = self.client.place_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                amount=amount,
                price=price,
                reduce_only=reduce_only,
                post_only=post_only
            )

            # 缓存订单
            order_id = order.get('id')
            if order_id:
                self.orders[order_id] = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'side': side,
                    'type': order_type,
                    'amount': amount,
                    'price': price,
                    'status': order.get('status'),
                    'filled_amount': order.get('filled', 0),
                    'order_info': order
                }
                logger.info(f"订单已缓存: {order_id}")

            return order

        except Exception as e:
            logger.error(f"下单失败: {e}")
            raise

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        取消订单

        Args:
            order_id: 订单ID
            symbol: 交易对

        Returns:
            是否成功
        """
        try:
            self.client.cancel_order(order_id, symbol)

            # 从缓存移除
            if order_id in self.orders:
                del self.orders[order_id]

            logger.info(f"订单已取消: {order_id}")
            return True

        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return False

    def get_order(self, order_id: str, symbol: str) -> Optional[Dict]:
        """
        查询订单状态

        Args:
            order_id: 订单ID
            symbol: 交易对

        Returns:
            订单信息
        """
        try:
            order = self.client.get_order(order_id, symbol)

            # 更新缓存
            if order_id in self.orders:
                self.orders[order_id]['status'] = order.get('status')
                self.orders[order_id]['filled_amount'] = order.get('filled', 0)
                self.orders[order_id]['order_info'] = order

            return order

        except Exception as e:
            logger.error(f"查询订单失败: {e}")
            return None

    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """
        获取当前挂单

        Args:
            symbol: 交易对（可选）

        Returns:
            挂单列表
        """
        try:
            orders = self.client.get_open_orders(symbol=symbol)
            return orders

        except Exception as e:
            logger.error(f"获取挂单失败: {e}")
            return []

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        price: float,
        amount: float,
        reduce_only: bool = False,
        post_only: bool = False
    ) -> Dict:
        """
        下限价单

        Args:
            symbol: 交易对
            side: 买卖方向
            price: 价格
            amount: 数量
            reduce_only: 只减仓
            post_only: 只挂单

        Returns:
            订单信息
        """
        return self.place_order(
            symbol=symbol,
            side=side,
            order_type='limit',
            amount=amount,
            price=price,
            reduce_only=reduce_only,
            post_only=post_only
        )

    def place_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        reduce_only: bool = False
    ) -> Dict:
        """
        下市价单

        Args:
            symbol: 交易对
            side: 买卖方向
            amount: 数量
            reduce_only: 只减仓

        Returns:
            订单信息
        """
        return self.place_order(
            symbol=symbol,
            side=side,
            order_type='market',
            amount=amount,
            reduce_only=reduce_only
        )

    def cancel_all_orders(self, symbol: str = None) -> int:
        """
        取消所有挂单

        Args:
            symbol: 交易对（可选）

        Returns:
            取消数量
        """
        try:
            orders = self.get_open_orders(symbol=symbol)
            cancelled = 0

            for order in orders:
                order_id = order.get('id')
                order_symbol = order.get('symbol')

                if self.cancel_order(order_id, order_symbol):
                    cancelled += 1

            logger.info(f"已取消 {cancelled} 个订单")
            return cancelled

        except Exception as e:
            logger.error(f"取消所有订单失败: {e}")
            return 0

    def get_positions(self) -> List[Dict]:
        """
        获取当前持仓

        Returns:
            持仓列表
        """
        try:
            if not self.client:
                return []

            # 使用ccxt获取持仓
            positions = self.client.exchange.fetch_positions()

            # 过滤有仓位的
            active_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]

            return active_positions

        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return []

    def get_balance(self, currency: str = None) -> Dict:
        """
        获取账户余额

        Args:
            currency: 币种（可选）

        Returns:
            余额信息
        """
        try:
            return self.client.get_balance(currency)
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return {}

    def close(self):
        """关闭执行器"""
        if self.client:
            self.client.close()
            logger.info("订单执行器已关闭")

    def get_cached_orders(self) -> Dict[str, Dict]:
        """
        获取缓存的订单

        Returns:
            订单字典
        """
        return self.orders.copy()


class MockExecutor(OrderExecutor):
    """
    模拟执行器（用于测试）
    不实际下单，只记录操作
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化模拟执行器

        Args:
            config: 配置参数
        """
        super().__init__(config or {})
        self.orders: Dict[str, Dict] = {}
        self.order_counter = 0
        self.is_initialized = True
        logger.info("模拟订单执行器初始化成功")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str = 'limit',
        amount: float = None,
        price: float = None,
        **kwargs
    ) -> Dict[str, Any]:
        """模拟下单"""
        self.order_counter += 1
        order_id = f"MOCK-{self.order_counter}"

        order = {
            'id': order_id,
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'amount': amount,
            'price': price,
            'status': 'open',
            'filled': 0,
            'remaining': amount,
        }

        self.orders[order_id] = order
        logger.info(f"[模拟] 订单已创建: {order_id} {side} {amount} @ {price}")

        return order

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """模拟取消订单"""
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'canceled'
            logger.info(f"[模拟] 订单已取消: {order_id}")
            return True
        return False

    def get_order(self, order_id: str, symbol: str) -> Optional[Dict]:
        """模拟查询订单"""
        return self.orders.get(order_id)
