"""
订单撮合器

模拟真实市场成交过程。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np

from .slippage import SlippageModel, SlippageType
from .cost import CostModel, TransactionCost


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Order:
    """订单"""
    order_id: str
    stock_code: str
    direction: str
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: float = 0.0
    filled_value: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    parent_id: Optional[str] = None
    strategy_id: Optional[str] = None
    remarks: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_buy(self) -> bool:
        """是否买入"""
        return self.direction.lower() == 'buy'
    
    @property
    def is_sell(self) -> bool:
        """是否卖出"""
        return self.direction.lower() == 'sell'
    
    @property
    def is_active(self) -> bool:
        """是否活跃"""
        return self.status in [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIAL_FILLED
        ]
    
    @property
    def is_completed(self) -> bool:
        """是否完成"""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]
    
    @property
    def unfilled_quantity(self) -> int:
        """未成交数量"""
        return self.quantity - self.filled_quantity
    
    @property
    def fill_rate(self) -> float:
        """成交比例"""
        return self.filled_quantity / self.quantity if self.quantity > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'order_id': self.order_id,
            'stock_code': self.stock_code,
            'direction': self.direction,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'limit_price': self.limit_price,
            'stop_price': self.stop_price,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'filled_value': self.filled_value,
            'commission': self.commission,
            'slippage': self.slippage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'parent_id': self.parent_id,
            'strategy_id': self.strategy_id,
            'remarks': self.remarks
        }


@dataclass
class MatchResult:
    """撮合结果"""
    success: bool
    order: Order
    filled_quantity: int = 0
    filled_price: float = 0.0
    filled_value: float = 0.0
    transaction_cost: Optional[TransactionCost] = None
    message: str = ""
    market_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'order_id': self.order.order_id,
            'stock_code': self.order.stock_code,
            'direction': self.order.direction,
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'filled_value': self.filled_value,
            'transaction_cost': self.transaction_cost.to_dict() if self.transaction_cost else None,
            'message': self.message
        }


class OrderMatcher:
    """
    订单撮合器
    
    模拟真实市场成交过程。
    """
    
    def __init__(
        self,
        slippage_model: Optional[str] = "percentage",
        cost_model: Optional[str] = "ashare",
        slippage_params: Optional[Dict] = None,
        cost_params: Optional[Dict] = None
    ):
        """
        初始化订单撮合器
        
        Args:
            slippage_model: 滑点模型名称
            cost_model: 成本模型名称
            slippage_params: 滑点模型参数
            cost_params: 成本模型参数
        """
        self.slippage_model = SlippageModel.get(slippage_model) or SlippageModel.create(
            SlippageType.PERCENTAGE, **(slippage_params or {})
        )
        self.cost_model = CostModel.get(cost_model) or CostModel.create(
            "ashare", **(cost_params or {})
        )
        
        self._orders: Dict[str, Order] = {}
        self._order_counter = 0
    
    def create_order(
        self,
        stock_code: str,
        direction: str,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        strategy_id: Optional[str] = None,
        remarks: str = "",
        metadata: Optional[Dict] = None
    ) -> Order:
        """
        创建订单
        
        Args:
            stock_code: 股票代码
            direction: 交易方向 (buy/sell)
            quantity: 数量
            order_type: 订单类型
            price: 价格
            limit_price: 限价
            stop_price: 止损价
            strategy_id: 策略ID
            remarks: 备注
            metadata: 元数据
            
        Returns:
            Order: 订单对象
        """
        self._order_counter += 1
        order_id = f"ORD{self._order_counter:08d}"
        
        order = Order(
            order_id=order_id,
            stock_code=stock_code,
            direction=direction.lower(),
            order_type=order_type,
            quantity=quantity,
            price=price,
            limit_price=limit_price,
            stop_price=stop_price,
            strategy_id=strategy_id,
            remarks=remarks,
            metadata=metadata or {}
        )
        
        self._orders[order_id] = order
        return order
    
    def match(
        self,
        order: Order,
        market_data: Dict[str, Any],
        current_time: Optional[datetime] = None
    ) -> MatchResult:
        """
        撮合订单
        
        Args:
            order: 订单对象
            market_data: 市场数据
            current_time: 当前时间
            
        Returns:
            MatchResult: 撮合结果
        """
        current_time = current_time or datetime.now()
        
        if not self._validate_order(order, market_data):
            order.status = OrderStatus.REJECTED
            order.updated_at = current_time
            return MatchResult(
                success=False,
                order=order,
                message="订单验证失败"
            )
        
        execution_price = self._get_execution_price(order, market_data)
        
        if execution_price is None:
            order.status = OrderStatus.REJECTED
            order.updated_at = current_time
            return MatchResult(
                success=False,
                order=order,
                message="无法获取执行价格"
            )
        
        slippage_result = self.slippage_model.calculate_slippage(
            price=execution_price,
            volume=order.quantity,
            direction=order.direction,
            market_data=market_data
        )
        
        final_price = slippage_result.adjusted_price
        
        if order.order_type == OrderType.LIMIT:
            if order.is_buy and final_price > order.limit_price:
                order.status = OrderStatus.PENDING
                return MatchResult(
                    success=False,
                    order=order,
                    message="限价买单未成交"
                )
            elif order.is_sell and final_price < order.limit_price:
                order.status = OrderStatus.PENDING
                return MatchResult(
                    success=False,
                    order=order,
                    message="限价卖单未成交"
                )
        
        filled_quantity = self._calculate_fill_quantity(order, market_data)
        filled_value = final_price * filled_quantity
        
        transaction_cost = self.cost_model.calculate(
            price=final_price,
            volume=filled_quantity,
            direction=order.direction,
            market_data=market_data
        )
        
        order.status = OrderStatus.FILLED
        order.filled_quantity = filled_quantity
        order.filled_price = final_price
        order.filled_value = filled_value
        order.commission = transaction_cost.commission
        order.slippage = slippage_result.slippage_amount * filled_quantity
        order.updated_at = current_time
        order.filled_at = current_time
        
        return MatchResult(
            success=True,
            order=order,
            filled_quantity=filled_quantity,
            filled_price=final_price,
            filled_value=filled_value,
            transaction_cost=transaction_cost,
            message="订单成交",
            market_data=market_data
        )
    
    def _validate_order(self, order: Order, market_data: Dict[str, Any]) -> bool:
        """验证订单"""
        if order.quantity <= 0:
            return False
        
        if 'close' not in market_data and 'price' not in market_data:
            return False
        
        if order.order_type == OrderType.LIMIT and order.limit_price is None:
            return False
        
        if order.order_type == OrderType.STOP and order.stop_price is None:
            return False
        
        if order.order_type == OrderType.STOP_LIMIT:
            if order.stop_price is None or order.limit_price is None:
                return False
        
        return True
    
    def _get_execution_price(self, order: Order, market_data: Dict[str, Any]) -> Optional[float]:
        """获取执行价格"""
        if order.order_type == OrderType.MARKET:
            if order.is_buy:
                return market_data.get('ask', market_data.get('close', market_data.get('price')))
            else:
                return market_data.get('bid', market_data.get('close', market_data.get('price')))
        
        elif order.order_type == OrderType.LIMIT:
            return order.limit_price
        
        elif order.order_type == OrderType.STOP:
            current_price = market_data.get('close', market_data.get('price'))
            if current_price is None:
                return None
            
            if order.is_sell and current_price <= order.stop_price:
                return current_price
            elif order.is_buy and current_price >= order.stop_price:
                return current_price
            return None
        
        elif order.order_type == OrderType.STOP_LIMIT:
            current_price = market_data.get('close', market_data.get('price'))
            if current_price is None:
                return None
            
            if order.is_sell and current_price <= order.stop_price:
                return order.limit_price
            elif order.is_buy and current_price >= order.stop_price:
                return order.limit_price
            return None
        
        return market_data.get('close', market_data.get('price'))
    
    def _calculate_fill_quantity(self, order: Order, market_data: Dict[str, Any]) -> int:
        """计算成交数量"""
        volume = market_data.get('volume', float('inf'))
        max_fill = int(volume * 0.1)
        
        return min(order.quantity, max_fill) if max_fill > 0 else order.quantity
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self._orders.get(order_id)
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        order = self._orders.get(order_id)
        if order and order.is_active:
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now()
            return True
        return False
    
    def get_active_orders(self) -> List[Order]:
        """获取活跃订单"""
        return [order for order in self._orders.values() if order.is_active]
    
    def get_filled_orders(self) -> List[Order]:
        """获取已成交订单"""
        return [order for order in self._orders.values() if order.status == OrderStatus.FILLED]
    
    def clear_history(self):
        """清除历史订单"""
        self._orders = {
            order_id: order for order_id, order in self._orders.items()
            if order.is_active
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        orders = list(self._orders.values())
        
        if not orders:
            return {'total_orders': 0}
        
        filled_orders = [o for o in orders if o.status == OrderStatus.FILLED]
        
        total_commission = sum(o.commission for o in filled_orders)
        total_slippage = sum(o.slippage for o in filled_orders)
        total_value = sum(o.filled_value for o in filled_orders)
        
        return {
            'total_orders': len(orders),
            'filled_orders': len(filled_orders),
            'pending_orders': len([o for o in orders if o.status == OrderStatus.PENDING]),
            'cancelled_orders': len([o for o in orders if o.status == OrderStatus.CANCELLED]),
            'rejected_orders': len([o for o in orders if o.status == OrderStatus.REJECTED]),
            'total_commission': total_commission,
            'total_slippage': total_slippage,
            'total_value': total_value,
            'fill_rate': len(filled_orders) / len(orders) if orders else 0
        }
