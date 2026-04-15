"""
手动成交录入模块

功能:
- 接收交易员录入的成交信息
- 验证成交数据有效性
- 更新订单状态
- 更新持仓记录

录入内容:
- 订单ID (关联原订单)
- 股票代码
- 买卖方向
- 成交数量
- 成交价格
- 成交时间
- 备注 (可选)
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from core.infrastructure.config import get_data_paths
from core.infrastructure.exceptions import OrderException, PositionException

logger = logging.getLogger(__name__)


@dataclass
class TradeEntry:
    entry_id: str
    order_id: Optional[str]
    stock_code: str
    stock_name: str
    side: str
    quantity: int
    price: float
    amount: float
    commission: float
    stamp_tax: float
    transfer_fee: float
    total_cost: float
    trade_time: str
    trader_id: Optional[str]
    notes: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'entry_id': self.entry_id,
            'order_id': self.order_id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'side': self.side,
            'quantity': self.quantity,
            'price': self.price,
            'amount': self.amount,
            'commission': self.commission,
            'stamp_tax': self.stamp_tax,
            'transfer_fee': self.transfer_fee,
            'total_cost': self.total_cost,
            'trade_time': self.trade_time,
            'trader_id': self.trader_id,
            'notes': self.notes,
            'created_at': self.created_at,
            'validated': self.validated,
            'validation_errors': self.validation_errors,
        }


class ManualEntryValidator:
    """成交录入验证器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.min_quantity = self.config.get('min_quantity', 100)
        self.min_price = self.config.get('min_price', 0.01)
        self.max_price = self.config.get('max_price', 10000)
        self.commission_rate = self.config.get('commission_rate', 0.0003)
        self.min_commission = self.config.get('min_commission', 5)
        self.stamp_tax_rate = self.config.get('stamp_tax_rate', 0.001)
        self.transfer_fee_rate = self.config.get('transfer_fee_rate', 0.00002)
    
    def validate_entry(self, entry: TradeEntry, context: Dict = None) -> Dict:
        context = context or {}
        errors = []
        warnings = []
        
        if entry.quantity <= 0:
            errors.append(f"成交数量必须大于0，当前: {entry.quantity}")
        
        if entry.quantity % 100 != 0:
            warnings.append(f"成交数量{entry.quantity}不是100的整数倍")
        
        if entry.quantity < self.min_quantity:
            warnings.append(f"成交数量小于最小限制{self.min_quantity}")
        
        if entry.price <= 0:
            errors.append(f"成交价格必须大于0，当前: {entry.price}")
        elif entry.price < self.min_price:
            errors.append(f"成交价格低于最小限制{self.min_price}")
        elif entry.price > self.max_price:
            errors.append(f"成交价格超过最大限制{self.max_price}")
        
        expected_commission = max(entry.amount * self.commission_rate, self.min_commission)
        if abs(entry.commission - expected_commission) > expected_commission * 0.5:
            warnings.append(f"佣金与预期差异较大: {entry.commission:.2f} vs {expected_commission:.2f}")
        
        if entry.side == 'sell':
            expected_stamp_tax = entry.amount * self.stamp_tax_rate
            if abs(entry.stamp_tax - expected_stamp_tax) > expected_stamp_tax * 0.5:
                warnings.append(f"印花税与预期差异较大: {entry.stamp_tax:.2f} vs {expected_stamp_tax:.2f}")
        else:
            if entry.stamp_tax > 0:
                warnings.append("买入交易不应有印花税")
        
        if entry.order_id:
            order = context.get('order')
            if order:
                if entry.quantity > order.quantity:
                    errors.append(f"成交数量{entry.quantity}超过订单数量{order.quantity}")
                
                if order.stock_code != entry.stock_code:
                    errors.append(f"股票代码不匹配: 订单{order.stock_code} vs 成交{entry.stock_code}")
                
                if order.side.value != entry.side:
                    errors.append(f"买卖方向不匹配: 订单{order.side.value} vs 成交{entry.side}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def calculate_fees(self, amount: float, side: str) -> Dict:
        commission = max(amount * self.commission_rate, self.min_commission)
        stamp_tax = amount * self.stamp_tax_rate if side == 'sell' else 0
        transfer_fee = amount * self.transfer_fee_rate
        total_cost = commission + stamp_tax + transfer_fee
        
        return {
            'commission': round(commission, 2),
            'stamp_tax': round(stamp_tax, 2),
            'transfer_fee': round(transfer_fee, 2),
            'total_cost': round(total_cost, 2)
        }


class ManualEntry:
    """手动成交录入管理器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        data_root = self.config.get('data_root')
        if data_root:
            self.path_config = get_data_paths(data_root)
        else:
            self.path_config = get_data_paths()
        
        self.entries_dir = Path(self.path_config.data_root) / "trading" / "entries"
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        
        self.validator = ManualEntryValidator(self.config.get('validator', {}))
        
        self.entries: List[TradeEntry] = []
        self._load_entries()
    
    def _load_entries(self):
        entries_file = self.entries_dir / "entries.json"
        if entries_file.exists():
            try:
                with open(entries_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = [
                        TradeEntry(**entry) for entry in data
                    ]
                logger.info(f"加载成交录入: {len(self.entries)} 条")
            except Exception as e:
                logger.warning(f"加载成交录入失败: {e}")
    
    def _save_entries(self):
        entries_file = self.entries_dir / "entries.json"
        try:
            with open(entries_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [e.to_dict() for e in self.entries],
                    f, ensure_ascii=False, indent=2
                )
        except Exception as e:
            logger.error(f"保存成交录入失败: {e}")
    
    def generate_entry_id(self) -> str:
        return f"TE-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    
    def create_entry(
        self,
        stock_code: str,
        stock_name: str,
        side: str,
        quantity: int,
        price: float,
        order_id: str = None,
        trade_time: str = None,
        trader_id: str = None,
        notes: str = "",
        auto_calculate_fees: bool = True,
        commission: float = None,
        stamp_tax: float = None,
        transfer_fee: float = None,
        context: Dict = None
    ) -> TradeEntry:
        entry_id = self.generate_entry_id()
        amount = quantity * price
        
        if auto_calculate_fees:
            fees = self.validator.calculate_fees(amount, side)
            commission = commission or fees['commission']
            stamp_tax = stamp_tax or fees['stamp_tax']
            transfer_fee = transfer_fee or fees['transfer_fee']
        else:
            commission = commission or 0
            stamp_tax = stamp_tax or 0
            transfer_fee = transfer_fee or 0
        
        total_cost = commission + stamp_tax + transfer_fee
        
        entry = TradeEntry(
            entry_id=entry_id,
            order_id=order_id,
            stock_code=stock_code,
            stock_name=stock_name,
            side=side.lower(),
            quantity=quantity,
            price=price,
            amount=round(amount, 2),
            commission=round(commission, 2),
            stamp_tax=round(stamp_tax, 2),
            transfer_fee=round(transfer_fee, 2),
            total_cost=round(total_cost, 2),
            trade_time=trade_time or datetime.now().isoformat(),
            trader_id=trader_id,
            notes=notes
        )
        
        validation = self.validator.validate_entry(entry, context)
        entry.validated = validation['valid']
        entry.validation_errors = validation['errors']
        
        self.entries.append(entry)
        self._save_entries()
        
        if entry.validated:
            logger.info(f"成交录入: {entry.entry_id} - {stock_code} {side} {quantity}@{price}")
        else:
            logger.warning(f"成交录入验证失败: {entry.entry_id} - {entry.validation_errors}")
        
        return entry
    
    def create_entry_from_order(
        self,
        order_id: str,
        filled_quantity: int,
        filled_price: float,
        order_manager: Any = None,
        position_manager: Any = None,
        trader_id: str = None,
        notes: str = ""
    ) -> TradeEntry:
        if order_manager is None:
            raise ValueError("需要提供 order_manager")
        
        order = order_manager.get_order(order_id)
        if not order:
            raise OrderException(f"订单不存在: {order_id}", order_id=order_id)
        
        context = {'order': order}
        
        entry = self.create_entry(
            stock_code=order.stock_code,
            stock_name=order.stock_name,
            side=order.side.value,
            quantity=filled_quantity,
            price=filled_price,
            order_id=order_id,
            trader_id=trader_id,
            notes=notes,
            context=context
        )
        
        if entry.validated:
            order_manager.fill_order(
                order_id=order_id,
                filled_quantity=filled_quantity,
                filled_price=filled_price,
                commission=entry.commission,
                stamp_tax=entry.stamp_tax,
                transfer_fee=entry.transfer_fee
            )
            
            if position_manager:
                position_manager.update_position_from_trade(
                    stock_code=order.stock_code,
                    stock_name=order.stock_name,
                    side=order.side.value,
                    quantity=filled_quantity,
                    price=filled_price,
                    commission=entry.commission,
                    stamp_tax=entry.stamp_tax,
                    transfer_fee=entry.transfer_fee,
                    trade_id=entry.entry_id,
                    notes=notes
                )
        
        return entry
    
    def get_entry(self, entry_id: str) -> Optional[TradeEntry]:
        for entry in self.entries:
            if entry.entry_id == entry_id:
                return entry
        return None
    
    def get_entries_by_order(self, order_id: str) -> List[TradeEntry]:
        return [e for e in self.entries if e.order_id == order_id]
    
    def get_entries_by_stock(self, stock_code: str) -> List[TradeEntry]:
        return [e for e in self.entries if e.stock_code == stock_code]
    
    def get_entries_by_date(self, date: str) -> List[TradeEntry]:
        return [e for e in self.entries if e.trade_time.startswith(date)]
    
    def get_today_entries(self) -> List[TradeEntry]:
        today = datetime.now().strftime('%Y-%m-%d')
        return self.get_entries_by_date(today)
    
    def get_entry_summary(self, start_date: str = None, end_date: str = None) -> Dict:
        entries = self.entries
        
        if start_date:
            entries = [e for e in entries if e.trade_time >= start_date]
        if end_date:
            entries = [e for e in entries if e.trade_time <= end_date]
        
        buy_entries = [e for e in entries if e.side == 'buy']
        sell_entries = [e for e in entries if e.side == 'sell']
        
        total_buy_amount = sum(e.amount for e in buy_entries)
        total_sell_amount = sum(e.amount for e in sell_entries)
        total_commission = sum(e.commission for e in entries)
        total_stamp_tax = sum(e.stamp_tax for e in entries)
        total_transfer_fee = sum(e.transfer_fee for e in entries)
        total_cost = sum(e.total_cost for e in entries)
        
        return {
            'total_entries': len(entries),
            'buy_entries': len(buy_entries),
            'sell_entries': len(sell_entries),
            'total_buy_amount': round(total_buy_amount, 2),
            'total_sell_amount': round(total_sell_amount, 2),
            'total_commission': round(total_commission, 2),
            'total_stamp_tax': round(total_stamp_tax, 2),
            'total_transfer_fee': round(total_transfer_fee, 2),
            'total_cost': round(total_cost, 2),
            'net_flow': round(total_sell_amount - total_buy_amount, 2),
            'validated_entries': len([e for e in entries if e.validated]),
            'invalid_entries': len([e for e in entries if not e.validated]),
        }
    
    def delete_entry(self, entry_id: str) -> bool:
        for i, entry in enumerate(self.entries):
            if entry.entry_id == entry_id:
                self.entries.pop(i)
                self._save_entries()
                logger.info(f"删除成交录入: {entry_id}")
                return True
        
        logger.warning(f"成交录入不存在: {entry_id}")
        return False
    
    def update_entry(
        self,
        entry_id: str,
        quantity: int = None,
        price: float = None,
        notes: str = None
    ) -> Optional[TradeEntry]:
        entry = self.get_entry(entry_id)
        if not entry:
            logger.warning(f"成交录入不存在: {entry_id}")
            return None
        
        if quantity is not None:
            entry.quantity = quantity
            entry.amount = round(quantity * entry.price, 2)
        
        if price is not None:
            entry.price = price
            entry.amount = round(entry.quantity * price, 2)
        
        if notes is not None:
            entry.notes = notes
        
        fees = self.validator.calculate_fees(entry.amount, entry.side)
        entry.commission = fees['commission']
        entry.stamp_tax = fees['stamp_tax']
        entry.transfer_fee = fees['transfer_fee']
        entry.total_cost = fees['total_cost']
        
        self._save_entries()
        logger.info(f"更新成交录入: {entry_id}")
        
        return entry
    
    def print_summary(self):
        summary = self.get_entry_summary()
        
        print(f"\n{'='*60}")
        print("📝 成交录入摘要")
        print(f"{'='*60}")
        print(f"  总录入数: {summary['total_entries']}")
        print(f"  买入记录: {summary['buy_entries']}")
        print(f"  卖出记录: {summary['sell_entries']}")
        print(f"  买入金额: ¥{summary['total_buy_amount']:,.2f}")
        print(f"  卖出金额: ¥{summary['total_sell_amount']:,.2f}")
        print(f"  总费用: ¥{summary['total_cost']:,.2f}")
        print(f"  验证通过: {summary['validated_entries']}")
        print(f"  验证失败: {summary['invalid_entries']}")
        
        today_entries = self.get_today_entries()
        if today_entries:
            print(f"\n  今日录入:")
            for entry in today_entries[:5]:
                side_icon = "🟢" if entry.side == 'buy' else "🔴"
                print(f"    {side_icon} {entry.stock_code} {entry.quantity}@{entry.price}")
        
        print(f"{'='*60}\n")
