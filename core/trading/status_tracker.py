"""
交易状态跟踪模块

功能:
- 跟踪每笔订单的执行状态
- 统计执行完成率
- 记录未执行原因
- 生成执行报告

状态类型:
- 待推送: 订单已生成，等待推送
- 已推送: 订单已推送给交易员
- 已确认: 交易员已确认收到
- 执行中: 交易员正在执行
- 已成交: 交易已完成
- 部分成交: 部分完成
- 已取消: 订单已取消
- 已拒绝: 交易员拒绝执行
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from core.infrastructure.config import get_data_paths
from .order import OrderStatus

logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    PENDING_PUSH = "pending_push"
    PUSHED = "pushed"
    CONFIRMED = "confirmed"
    EXECUTING = "executing"
    FILLED = "filled"
    PARTIAL_FILLED = "partial_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


STATUS_DISPLAY = {
    TradeStatus.PENDING_PUSH: ("⏳", "待推送"),
    TradeStatus.PUSHED: ("📤", "已推送"),
    TradeStatus.CONFIRMED: ("✅", "已确认"),
    TradeStatus.EXECUTING: ("🔄", "执行中"),
    TradeStatus.FILLED: ("✅", "已成交"),
    TradeStatus.PARTIAL_FILLED: ("📊", "部分成交"),
    TradeStatus.CANCELLED: ("❌", "已取消"),
    TradeStatus.REJECTED: ("🚫", "已拒绝"),
}


@dataclass
class StatusRecord:
    record_id: str
    order_id: str
    stock_code: str
    stock_name: str
    side: str
    quantity: int
    price: Optional[float]
    status: TradeStatus
    previous_status: Optional[TradeStatus]
    changed_at: str
    changed_by: str
    reason: str
    notes: str
    execution_time_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return {
            'record_id': self.record_id,
            'order_id': self.order_id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'side': self.side,
            'quantity': self.quantity,
            'price': self.price,
            'status': self.status.value,
            'previous_status': self.previous_status.value if self.previous_status else None,
            'changed_at': self.changed_at,
            'changed_by': self.changed_by,
            'reason': self.reason,
            'notes': self.notes,
            'execution_time_seconds': self.execution_time_seconds,
        }


@dataclass
class OrderTrackingInfo:
    order_id: str
    stock_code: str
    stock_name: str
    side: str
    quantity: int
    price: Optional[float]
    current_status: TradeStatus
    created_at: str
    pushed_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    filled_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    filled_quantity: int = 0
    filled_price: float = 0.0
    trader_id: Optional[str] = None
    cancel_reason: str = ""
    status_history: List[StatusRecord] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'order_id': self.order_id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'side': self.side,
            'quantity': self.quantity,
            'price': self.price,
            'current_status': self.current_status.value,
            'created_at': self.created_at,
            'pushed_at': self.pushed_at,
            'confirmed_at': self.confirmed_at,
            'filled_at': self.filled_at,
            'cancelled_at': self.cancelled_at,
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'trader_id': self.trader_id,
            'cancel_reason': self.cancel_reason,
            'status_history': [r.to_dict() for r in self.status_history],
        }
    
    @property
    def fill_rate(self) -> float:
        if self.quantity <= 0:
            return 0.0
        return self.filled_quantity / self.quantity
    
    @property
    def execution_time_seconds(self) -> Optional[int]:
        if self.filled_at and self.created_at:
            created = datetime.fromisoformat(self.created_at)
            filled = datetime.fromisoformat(self.filled_at)
            return int((filled - created).total_seconds())
        return None


class TradeStatusTracker:
    """交易状态跟踪器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        data_root = self.config.get('data_root')
        if data_root:
            self.path_config = get_data_paths(data_root)
        else:
            self.path_config = get_data_paths()
        
        self.tracking_dir = Path(self.path_config.data_root) / "trading" / "tracking"
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        
        self.tracking_info: Dict[str, OrderTrackingInfo] = {}
        self.status_records: List[StatusRecord] = []
        
        self._load_data()
    
    def _load_data(self):
        tracking_file = self.tracking_dir / "tracking.json"
        if tracking_file.exists():
            try:
                with open(tracking_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for oid, info in data.get('tracking_info', {}).items():
                        self.tracking_info[oid] = OrderTrackingInfo(
                            order_id=info['order_id'],
                            stock_code=info['stock_code'],
                            stock_name=info['stock_name'],
                            side=info['side'],
                            quantity=info['quantity'],
                            price=info.get('price'),
                            current_status=TradeStatus(info['current_status']),
                            created_at=info['created_at'],
                            pushed_at=info.get('pushed_at'),
                            confirmed_at=info.get('confirmed_at'),
                            filled_at=info.get('filled_at'),
                            cancelled_at=info.get('cancelled_at'),
                            filled_quantity=info.get('filled_quantity', 0),
                            filled_price=info.get('filled_price', 0),
                            trader_id=info.get('trader_id'),
                            cancel_reason=info.get('cancel_reason', ''),
                            status_history=[]
                        )
                    
                    for record in data.get('status_records', []):
                        self.status_records.append(StatusRecord(
                            record_id=record['record_id'],
                            order_id=record['order_id'],
                            stock_code=record['stock_code'],
                            stock_name=record['stock_name'],
                            side=record['side'],
                            quantity=record['quantity'],
                            price=record.get('price'),
                            status=TradeStatus(record['status']),
                            previous_status=TradeStatus(record['previous_status']) if record.get('previous_status') else None,
                            changed_at=record['changed_at'],
                            changed_by=record['changed_by'],
                            reason=record.get('reason', ''),
                            notes=record.get('notes', ''),
                            execution_time_seconds=record.get('execution_time_seconds'),
                        ))
                
                logger.info(f"加载跟踪数据: {len(self.tracking_info)} 个订单")
            except Exception as e:
                logger.warning(f"加载跟踪数据失败: {e}")
    
    def _save_data(self):
        tracking_file = self.tracking_dir / "tracking.json"
        try:
            with open(tracking_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'tracking_info': {oid: info.to_dict() for oid, info in self.tracking_info.items()},
                    'status_records': [r.to_dict() for r in self.status_records[-1000:]],
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存跟踪数据失败: {e}")
    
    def generate_record_id(self) -> str:
        return f"SR-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    
    def start_tracking(
        self,
        order_id: str,
        stock_code: str,
        stock_name: str,
        side: str,
        quantity: int,
        price: float = None
    ) -> OrderTrackingInfo:
        now = datetime.now().isoformat()
        
        tracking_info = OrderTrackingInfo(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_name,
            side=side,
            quantity=quantity,
            price=price,
            current_status=TradeStatus.PENDING_PUSH,
            created_at=now
        )
        
        self.tracking_info[order_id] = tracking_info
        
        self._record_status_change(
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_name,
            side=side,
            quantity=quantity,
            price=price,
            new_status=TradeStatus.PENDING_PUSH,
            previous_status=None,
            changed_by="system",
            reason="订单创建"
        )
        
        self._save_data()
        
        logger.info(f"开始跟踪订单: {order_id}")
        
        return tracking_info
    
    def update_status(
        self,
        order_id: str,
        new_status: TradeStatus,
        changed_by: str = "system",
        reason: str = "",
        notes: str = "",
        filled_quantity: int = None,
        filled_price: float = None,
        trader_id: str = None
    ) -> Optional[OrderTrackingInfo]:
        if order_id not in self.tracking_info:
            logger.warning(f"订单未在跟踪中: {order_id}")
            return None
        
        tracking_info = self.tracking_info[order_id]
        previous_status = tracking_info.current_status
        
        if previous_status == new_status:
            return tracking_info
        
        tracking_info.current_status = new_status
        now = datetime.now().isoformat()
        
        if new_status == TradeStatus.PUSHED:
            tracking_info.pushed_at = now
        elif new_status == TradeStatus.CONFIRMED:
            tracking_info.confirmed_at = now
        elif new_status == TradeStatus.FILLED:
            tracking_info.filled_at = now
        elif new_status == TradeStatus.CANCELLED:
            tracking_info.cancelled_at = now
            tracking_info.cancel_reason = reason
        
        if filled_quantity is not None:
            tracking_info.filled_quantity = filled_quantity
        if filled_price is not None:
            tracking_info.filled_price = filled_price
        if trader_id is not None:
            tracking_info.trader_id = trader_id
        
        self._record_status_change(
            order_id=order_id,
            stock_code=tracking_info.stock_code,
            stock_name=tracking_info.stock_name,
            side=tracking_info.side,
            quantity=tracking_info.quantity,
            price=tracking_info.price,
            new_status=new_status,
            previous_status=previous_status,
            changed_by=changed_by,
            reason=reason,
            notes=notes,
            execution_time_seconds=tracking_info.execution_time_seconds
        )
        
        self._save_data()
        
        logger.info(f"状态更新: {order_id} {previous_status.value} -> {new_status.value}")
        
        return tracking_info
    
    def _record_status_change(
        self,
        order_id: str,
        stock_code: str,
        stock_name: str,
        side: str,
        quantity: int,
        price: Optional[float],
        new_status: TradeStatus,
        previous_status: Optional[TradeStatus],
        changed_by: str,
        reason: str,
        notes: str = "",
        execution_time_seconds: int = None
    ):
        record = StatusRecord(
            record_id=self.generate_record_id(),
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_name,
            side=side,
            quantity=quantity,
            price=price,
            status=new_status,
            previous_status=previous_status,
            changed_at=datetime.now().isoformat(),
            changed_by=changed_by,
            reason=reason,
            notes=notes,
            execution_time_seconds=execution_time_seconds
        )
        
        self.status_records.append(record)
        
        if order_id in self.tracking_info:
            self.tracking_info[order_id].status_history.append(record)
    
    def get_tracking_info(self, order_id: str) -> Optional[OrderTrackingInfo]:
        return self.tracking_info.get(order_id)
    
    def get_all_tracking_info(self) -> Dict[str, OrderTrackingInfo]:
        return self.tracking_info.copy()
    
    def get_orders_by_status(self, status: TradeStatus) -> List[OrderTrackingInfo]:
        return [
            info for info in self.tracking_info.values()
            if info.current_status == status
        ]
    
    def get_active_orders(self) -> List[OrderTrackingInfo]:
        active_statuses = [
            TradeStatus.PENDING_PUSH,
            TradeStatus.PUSHED,
            TradeStatus.CONFIRMED,
            TradeStatus.EXECUTING,
            TradeStatus.PARTIAL_FILLED
        ]
        return [
            info for info in self.tracking_info.values()
            if info.current_status in active_statuses
        ]
    
    def get_execution_statistics(self, start_date: str = None, end_date: str = None) -> Dict:
        records = self.status_records
        
        if start_date:
            records = [r for r in records if r.changed_at >= start_date]
        if end_date:
            records = [r for r in records if r.changed_at <= end_date]
        
        total_orders = len(self.tracking_info)
        
        status_counts = {}
        for status in TradeStatus:
            status_counts[status.value] = len([
                info for info in self.tracking_info.values()
                if info.current_status == status
            ])
        
        filled_orders = [
            info for info in self.tracking_info.values()
            if info.current_status in [TradeStatus.FILLED, TradeStatus.PARTIAL_FILLED]
        ]
        
        total_filled_quantity = sum(info.filled_quantity for info in filled_orders)
        total_filled_amount = sum(
            info.filled_quantity * info.filled_price
            for info in filled_orders
        )
        
        execution_times = [
            info.execution_time_seconds for info in filled_orders
            if info.execution_time_seconds is not None
        ]
        
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        cancel_reasons = {}
        for info in self.tracking_info.values():
            if info.current_status == TradeStatus.CANCELLED and info.cancel_reason:
                cancel_reasons[info.cancel_reason] = cancel_reasons.get(info.cancel_reason, 0) + 1
        
        return {
            'total_orders': total_orders,
            'status_distribution': status_counts,
            'filled_orders': len(filled_orders),
            'total_filled_quantity': total_filled_quantity,
            'total_filled_amount': round(total_filled_amount, 2),
            'fill_rate': len(filled_orders) / total_orders if total_orders > 0 else 0,
            'avg_execution_time_seconds': round(avg_execution_time, 1),
            'cancel_reasons': cancel_reasons,
        }
    
    def get_daily_summary(self, date: str = None) -> Dict:
        date = date or datetime.now().strftime('%Y-%m-%d')
        
        day_records = [
            r for r in self.status_records
            if r.changed_at.startswith(date)
        ]
        
        day_orders = set(r.order_id for r in day_records)
        
        filled_records = [
            r for r in day_records
            if r.status == TradeStatus.FILLED
        ]
        
        cancelled_records = [
            r for r in day_records
            if r.status == TradeStatus.CANCELLED
        ]
        
        buy_amount = sum(
            r.quantity * (r.price or 0)
            for r in filled_records
            if r.side == 'buy'
        )
        
        sell_amount = sum(
            r.quantity * (r.price or 0)
            for r in filled_records
            if r.side == 'sell'
        )
        
        return {
            'date': date,
            'total_orders': len(day_orders),
            'filled_count': len(filled_records),
            'cancelled_count': len(cancelled_records),
            'buy_amount': round(buy_amount, 2),
            'sell_amount': round(sell_amount, 2),
            'net_flow': round(sell_amount - buy_amount, 2),
        }
    
    def cleanup_old_records(self, days: int = 30) -> int:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        to_remove = [
            oid for oid, info in self.tracking_info.items()
            if info.current_status in [TradeStatus.FILLED, TradeStatus.CANCELLED, TradeStatus.REJECTED]
            and info.created_at < cutoff
        ]
        
        for oid in to_remove:
            del self.tracking_info[oid]
        
        if to_remove:
            self._save_data()
        
        logger.info(f"清理旧记录: {len(to_remove)} 个")
        return len(to_remove)
    
    def print_summary(self):
        stats = self.get_execution_statistics()
        
        print(f"\n{'='*60}")
        print("📊 交易状态跟踪摘要")
        print(f"{'='*60}")
        print(f"  总订单数: {stats['total_orders']}")
        print(f"  已成交: {stats['filled_orders']}")
        print(f"  成交率: {stats['fill_rate']:.1%}")
        print(f"  总成交数量: {stats['total_filled_quantity']:,}")
        print(f"  总成交金额: ¥{stats['total_filled_amount']:,.2f}")
        print(f"  平均执行时间: {stats['avg_execution_time_seconds']:.0f}秒")
        
        print(f"\n  状态分布:")
        for status, count in stats['status_distribution'].items():
            if count > 0:
                print(f"    {status}: {count}")
        
        if stats['cancel_reasons']:
            print(f"\n  取消原因:")
            for reason, count in stats['cancel_reasons'].items():
                print(f"    {reason}: {count}")
        
        active = self.get_active_orders()
        if active:
            print(f"\n  活跃订单:")
            for info in active[:5]:
                icon, text = STATUS_DISPLAY.get(info.current_status, ("❓", "未知"))
                print(f"    {icon} {info.order_id}: {info.stock_code} {info.side} {info.quantity}")
        
        print(f"{'='*60}\n")
