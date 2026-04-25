"""
订单管理模块

功能:
- 订单生成: 根据目标持仓计算买卖数量
- 订单状态管理: 待推送/已推送/已确认/执行中/已成交/部分成交/已取消/已拒绝
- 订单查询和统计
- 订单验证

硬性要求验证:
- H1: 订单有效性 (数量>0, 价格合理)
- H2: 资金充足 (可用资金>=所需资金)
- H3: 持仓充足 (卖出数量<=持仓数量)
- H4: 交易时间 (在交易时段内)
"""

import json
import logging
from datetime import datetime, time
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from core.infrastructure.config import get_data_paths
from core.infrastructure.exceptions import (
    OrderException,
    InsufficientFundsException,
    PositionException,
)

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    PENDING_PUSH = "pending_push"
    PUSHED = "pushed"
    CONFIRMED = "confirmed"
    EXECUTING = "executing"
    FILLED = "filled"
    PARTIAL_FILLED = "partial_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


STATUS_DISPLAY = {
    OrderStatus.PENDING_PUSH: ("⏳", "待推送"),
    OrderStatus.PUSHED: ("📤", "已推送"),
    OrderStatus.CONFIRMED: ("✅", "已确认"),
    OrderStatus.EXECUTING: ("🔄", "执行中"),
    OrderStatus.FILLED: ("✅", "已成交"),
    OrderStatus.PARTIAL_FILLED: ("📊", "部分成交"),
    OrderStatus.CANCELLED: ("❌", "已取消"),
    OrderStatus.REJECTED: ("🚫", "已拒绝"),
}

SIDE_DISPLAY = {
    OrderSide.BUY: ("🟢", "买入"),
    OrderSide.SELL: ("🔴", "卖出"),
}


@dataclass
class TradeOrder:
    order_id: str
    stock_code: str
    stock_name: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING_PUSH
    filled_quantity: int = 0
    filled_price: float = 0.0
    filled_amount: float = 0.0
    commission: float = 0.0
    stamp_tax: float = 0.0
    transfer_fee: float = 0.0
    signal_strength: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    factors: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    pushed_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    filled_at: Optional[str] = None
    trader_id: Optional[str] = None
    notes: str = ""
    
    @property
    def amount(self) -> float:
        if self.price:
            return self.quantity * self.price
        return 0.0
    
    @property
    def total_cost(self) -> float:
        return self.commission + self.stamp_tax + self.transfer_fee
    
    @property
    def fill_rate(self) -> float:
        if self.quantity <= 0:
            return 0.0
        return self.filled_quantity / self.quantity
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "amount": self.amount,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "filled_amount": self.filled_amount,
            "commission": self.commission,
            "stamp_tax": self.stamp_tax,
            "transfer_fee": self.transfer_fee,
            "total_cost": self.total_cost,
            "fill_rate": self.fill_rate,
            "signal_strength": self.signal_strength,
            "confidence": self.confidence,
            "reason": self.reason,
            "factors": self.factors,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "pushed_at": self.pushed_at,
            "confirmed_at": self.confirmed_at,
            "filled_at": self.filled_at,
            "trader_id": self.trader_id,
            "notes": self.notes,
        }
    
    def display(self) -> str:
        status_icon, status_text = STATUS_DISPLAY.get(self.status, ("❓", "未知"))
        side_icon, side_text = SIDE_DISPLAY.get(self.side, ("❓", "未知"))
        
        lines = [
            f"  {status_icon} 订单ID: {self.order_id}",
            f"     股票: {self.stock_code} {self.stock_name}",
            f"     方向: {side_icon} {side_text}",
            f"     类型: {self.order_type.value}",
            f"     数量: {self.quantity:,}",
        ]
        
        if self.price:
            lines.append(f"     价格: ¥{self.price:.2f}")
            lines.append(f"     金额: ¥{self.amount:,.2f}")
        else:
            lines.append("     价格: 市价")
        
        lines.append(f"     状态: {status_text}")
        
        if self.status in [OrderStatus.FILLED, OrderStatus.PARTIAL_FILLED]:
            lines.extend([
                f"     成交数量: {self.filled_quantity:,} ({self.fill_rate:.1%})",
                f"     成交价格: ¥{self.filled_price:.2f}",
                f"     成交金额: ¥{self.filled_amount:,.2f}",
            ])
        
        if self.reason:
            lines.append(f"     原因: {self.reason}")
        
        return "\n".join(lines)


class OrderValidator:
    """订单验证器"""
    
    TRADING_START = time(9, 30)
    TRADING_END = time(15, 0)
    LUNCH_START = time(11, 30)
    LUNCH_END = time(13, 0)
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.min_order_quantity = self.config.get('min_order_quantity', 100)
        self.max_order_quantity = self.config.get('max_order_quantity', 1000000)
        self.min_order_price = self.config.get('min_order_price', 0.1)
        self.max_order_price = self.config.get('max_order_price', 10000)
    
    def validate_order(self, order: TradeOrder, context: Dict = None) -> Dict:
        """
        验证订单有效性
        
        Returns:
            Dict: {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        context = context or {}
        errors = []
        warnings = []
        
        if order.quantity <= 0:
            errors.append(f"H1违反: 订单数量必须大于0，当前: {order.quantity}")
        
        if order.quantity % 100 != 0:
            warnings.append(f"订单数量{order.quantity}不是100的整数倍")
        
        if order.quantity < self.min_order_quantity:
            errors.append(f"订单数量小于最小限制{self.min_order_quantity}")
        
        if order.quantity > self.max_order_quantity:
            errors.append(f"订单数量超过最大限制{self.max_order_quantity}")
        
        if order.price is not None:
            if order.price <= 0:
                errors.append(f"H1违反: 订单价格必须大于0，当前: {order.price}")
            elif order.price < self.min_order_price:
                errors.append(f"订单价格低于最小限制{self.min_order_price}")
            elif order.price > self.max_order_price:
                errors.append(f"订单价格超过最大限制{self.max_order_price}")
        
        if order.side == OrderSide.BUY:
            available_cash = context.get('available_cash', 0)
            required_amount = order.amount if order.price else order.quantity * context.get('estimated_price', 10)
            if available_cash < required_amount:
                errors.append(f"H2违反: 资金不足，需要¥{required_amount:,.2f}，可用¥{available_cash:,.2f}")
        
        if order.side == OrderSide.SELL:
            available_quantity = context.get('available_quantity', 0)
            if available_quantity < order.quantity:
                errors.append(f"H3违反: 持仓不足，需要{order.quantity}股，可用{available_quantity}股")
        
        if not self._is_trading_time():
            warnings.append("H4提醒: 当前不在交易时段")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _is_trading_time(self) -> bool:
        now = datetime.now().time()
        weekday = datetime.now().weekday()
        
        if weekday >= 5:
            return False
        
        morning = self.TRADING_START <= now <= self.LUNCH_START
        afternoon = self.LUNCH_END <= now <= self.TRADING_END
        
        return morning or afternoon


class OrderManager:
    """订单管理器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        data_root = self.config.get('data_root')
        if data_root:
            self.path_config = get_data_paths(data_root)
        else:
            self.path_config = get_data_paths()
        self.orders_file = Path(self.path_config.data_root) / "trading" / "orders.json"
        self.validator = OrderValidator(self.config.get('validator', {}))
        
        self.orders: Dict[str, TradeOrder] = {}
        self.order_history: List[Dict] = []
        
        self._ensure_directories()
        self._load_orders()
    
    def _ensure_directories(self):
        self.orders_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_orders(self):
        if self.orders_file.exists():
            try:
                with open(self.orders_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.order_history = data.get('order_history', [])
                logger.info(f"加载历史订单: {len(self.order_history)} 条")
            except Exception as e:
                logger.warning(f"加载订单历史失败: {e}")
    
    def _save_orders(self):
        try:
            with open(self.orders_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'active_orders': {oid: o.to_dict() for oid, o in self.orders.items()},
                    'order_history': self.order_history,
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存订单失败: {e}")
    
    def generate_order_id(self, stock_code: str) -> str:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        return f"ORD-{stock_code}-{timestamp}"
    
    def create_order(
        self,
        stock_code: str,
        stock_name: str,
        side: OrderSide,
        quantity: int,
        price: float = None,
        order_type: OrderType = OrderType.MARKET,
        signal_strength: float = 0.0,
        confidence: float = 0.0,
        reason: str = "",
        factors: List[str] = None,
        context: Dict = None
    ) -> TradeOrder:
        order_id = self.generate_order_id(stock_code)
        
        order = TradeOrder(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_name,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            signal_strength=signal_strength,
            confidence=confidence,
            reason=reason,
            factors=factors or []
        )
        
        validation = self.validator.validate_order(order, context)
        if not validation['valid']:
            order.status = OrderStatus.REJECTED
            order.notes = "; ".join(validation['errors'])
            logger.warning(f"订单验证失败: {order.notes}")
        
        self.orders[order_id] = order
        self._save_orders()
        
        logger.info(f"创建订单: {order_id} - {stock_code} {side.value} {quantity}")
        
        return order
    
    def create_orders_from_target_positions(
        self,
        target_positions: Dict[str, Dict],
        current_positions: Dict[str, Dict],
        prices: Dict[str, float],
        available_cash: float
    ) -> List[TradeOrder]:
        orders = []
        
        all_stocks = set(target_positions.keys()) | set(current_positions.keys())
        
        for stock_code in all_stocks:
            target = target_positions.get(stock_code, {})
            current = current_positions.get(stock_code, {})
            
            target_quantity = target.get('quantity', 0)
            current_quantity = current.get('quantity', 0)
            price = prices.get(stock_code, 0)
            
            diff = target_quantity - current_quantity
            
            if diff == 0:
                continue
            
            side = OrderSide.BUY if diff > 0 else OrderSide.SELL
            quantity = abs(diff)
            
            context = {
                'available_cash': available_cash,
                'available_quantity': current_quantity,
                'estimated_price': price
            }
            
            order = self.create_order(
                stock_code=stock_code,
                stock_name=target.get('stock_name', current.get('stock_name', '')),
                side=side,
                quantity=quantity,
                price=price,
                order_type=OrderType.LIMIT if price else OrderType.MARKET,
                reason=f"目标持仓调整: {current_quantity} -> {target_quantity}",
                context=context
            )
            
            orders.append(order)
            
            if side == OrderSide.BUY:
                available_cash -= quantity * price if price else 0
        
        logger.info(f"根据目标持仓生成 {len(orders)} 个订单")
        return orders
    
    def update_status(self, order_id: str, status: OrderStatus, **kwargs) -> bool:
        if order_id not in self.orders:
            logger.warning(f"订单不存在: {order_id}")
            return False
        
        order = self.orders[order_id]
        old_status = order.status
        order.status = status
        order.updated_at = datetime.now().isoformat()
        
        if status == OrderStatus.PUSHED:
            order.pushed_at = datetime.now().isoformat()
        elif status == OrderStatus.CONFIRMED:
            order.confirmed_at = datetime.now().isoformat()
        elif status == OrderStatus.FILLED:
            order.filled_at = datetime.now().isoformat()
            self.order_history.append(order.to_dict())
        
        for key, value in kwargs.items():
            if hasattr(order, key):
                setattr(order, key, value)
        
        self._save_orders()
        
        logger.info(f"订单状态更新: {order_id} {old_status.value} -> {status.value}")
        return True
    
    def fill_order(
        self,
        order_id: str,
        filled_quantity: int,
        filled_price: float,
        commission: float = 0,
        stamp_tax: float = 0,
        transfer_fee: float = 0
    ) -> bool:
        if order_id not in self.orders:
            logger.warning(f"订单不存在: {order_id}")
            return False
        
        order = self.orders[order_id]
        
        order.filled_quantity = filled_quantity
        order.filled_price = filled_price
        order.filled_amount = filled_quantity * filled_price
        order.commission = commission
        order.stamp_tax = stamp_tax
        order.transfer_fee = transfer_fee
        order.updated_at = datetime.now().isoformat()
        
        if filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.now().isoformat()
            self.order_history.append(order.to_dict())
        else:
            order.status = OrderStatus.PARTIAL_FILLED
        
        self._save_orders()
        
        logger.info(f"订单成交: {order_id}, 数量: {filled_quantity}, 价格: {filled_price}")
        return True
    
    def cancel_order(self, order_id: str, reason: str = "") -> bool:
        if order_id not in self.orders:
            logger.warning(f"订单不存在: {order_id}")
            return False
        
        order = self.orders[order_id]
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            logger.warning(f"订单状态不允许取消: {order.status.value}")
            return False
        
        order.status = OrderStatus.CANCELLED
        order.notes = reason
        order.updated_at = datetime.now().isoformat()
        
        self.order_history.append(order.to_dict())
        self._save_orders()
        
        logger.info(f"订单取消: {order_id}")
        return True
    
    def get_order(self, order_id: str) -> Optional[TradeOrder]:
        return self.orders.get(order_id)
    
    def get_active_orders(self) -> List[TradeOrder]:
        return [
            o for o in self.orders.values()
            if o.status in [
                OrderStatus.PENDING_PUSH,
                OrderStatus.PUSHED,
                OrderStatus.CONFIRMED,
                OrderStatus.EXECUTING,
                OrderStatus.PARTIAL_FILLED
            ]
        ]
    
    def get_orders_by_status(self, status: OrderStatus) -> List[TradeOrder]:
        return [o for o in self.orders.values() if o.status == status]
    
    def get_orders_by_stock(self, stock_code: str) -> List[TradeOrder]:
        return [o for o in self.orders.values() if o.stock_code == stock_code]
    
    def get_order_summary(self) -> Dict:
        status_counts = {}
        for status in OrderStatus:
            status_counts[status.value] = len([
                o for o in self.orders.values() if o.status == status
            ])
        
        active_orders = self.get_active_orders()
        total_buy_amount = sum(
            o.amount for o in active_orders
            if o.side == OrderSide.BUY and o.price
        )
        total_sell_amount = sum(
            o.amount for o in active_orders
            if o.side == OrderSide.SELL and o.price
        )
        
        return {
            'total_orders': len(self.orders),
            'active_orders': len(active_orders),
            'history_count': len(self.order_history),
            'status_distribution': status_counts,
            'total_buy_amount': total_buy_amount,
            'total_sell_amount': total_sell_amount,
        }
    
    def print_summary(self):
        summary = self.get_order_summary()
        
        print("\n" + "="*60)
        print("📋 订单管理摘要")
        print("="*60)
        print(f"  总订单数: {summary['total_orders']}")
        print(f"  活跃订单: {summary['active_orders']}")
        print(f"  历史记录: {summary['history_count']}")
        print(f"  待买入金额: ¥{summary['total_buy_amount']:,.2f}")
        print(f"  待卖出金额: ¥{summary['total_sell_amount']:,.2f}")
        
        print("\n  状态分布:")
        for status, count in summary['status_distribution'].items():
            if count > 0:
                print(f"    {status}: {count}")
        
        active = self.get_active_orders()
        if active:
            print("\n  活跃订单:")
            for order in active[:5]:
                print(order.display())
        
        print("="*60 + "\n")
    
    def clear_completed_orders(self) -> int:
        completed_statuses = [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED
        ]
        
        to_remove = [
            oid for oid, o in self.orders.items()
            if o.status in completed_statuses
        ]
        
        for oid in to_remove:
            del self.orders[oid]
        
        if to_remove:
            self._save_orders()
        
        logger.info(f"清理已完成订单: {len(to_remove)} 个")
        return len(to_remove)
