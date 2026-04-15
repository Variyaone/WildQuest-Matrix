"""
交易员确认机制模块

功能:
- 发送交易指令后等待确认
- 超时未确认自动提醒
- 记录确认时间和确认人

确认类型:
- 已收到: 交易员确认收到报告
- 已执行: 交易员确认已下单
- 部分执行: 交易员确认部分成交
- 暂停执行: 交易员决定暂停
- 拒绝执行: 交易员决定不执行
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from core.infrastructure.config import get_data_paths

logger = logging.getLogger(__name__)


class ConfirmationType(Enum):
    RECEIVED = "received"
    EXECUTED = "executed"
    PARTIAL_EXECUTED = "partial_executed"
    PAUSED = "paused"
    REJECTED = "rejected"


class ConfirmationStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


CONFIRMATION_DISPLAY = {
    ConfirmationType.RECEIVED: ("📥", "已收到"),
    ConfirmationType.EXECUTED: ("✅", "已执行"),
    ConfirmationType.PARTIAL_EXECUTED: ("📊", "部分执行"),
    ConfirmationType.PAUSED: ("⏸️", "暂停执行"),
    ConfirmationType.REJECTED: ("❌", "拒绝执行"),
}


@dataclass
class Confirmation:
    confirmation_id: str
    report_id: str
    order_ids: List[str]
    status: ConfirmationStatus
    confirmation_type: Optional[ConfirmationType]
    trader_id: Optional[str]
    confirmed_at: Optional[str]
    timeout_minutes: int
    created_at: str
    updated_at: str
    notes: str
    reminder_sent: bool = False
    reminder_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'confirmation_id': self.confirmation_id,
            'report_id': self.report_id,
            'order_ids': self.order_ids,
            'status': self.status.value,
            'confirmation_type': self.confirmation_type.value if self.confirmation_type else None,
            'trader_id': self.trader_id,
            'confirmed_at': self.confirmed_at,
            'timeout_minutes': self.timeout_minutes,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'notes': self.notes,
            'reminder_sent': self.reminder_sent,
            'reminder_count': self.reminder_count,
        }
    
    @property
    def is_expired(self) -> bool:
        if self.status != ConfirmationStatus.PENDING:
            return False
        
        created = datetime.fromisoformat(self.created_at)
        return datetime.now() > created + timedelta(minutes=self.timeout_minutes)
    
    @property
    def remaining_minutes(self) -> int:
        if self.status != ConfirmationStatus.PENDING:
            return 0
        
        created = datetime.fromisoformat(self.created_at)
        expiry = created + timedelta(minutes=self.timeout_minutes)
        remaining = expiry - datetime.now()
        
        return max(0, int(remaining.total_seconds() / 60))


class TraderConfirmation:
    """交易员确认管理器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        data_root = self.config.get('data_root')
        if data_root:
            self.path_config = get_data_paths(data_root)
        else:
            self.path_config = get_data_paths()
        
        self.confirmations_dir = Path(self.path_config.data_root) / "trading" / "confirmations"
        self.confirmations_dir.mkdir(parents=True, exist_ok=True)
        
        self.default_timeout = self.config.get('default_timeout_minutes', 30)
        self.reminder_interval = self.config.get('reminder_interval_minutes', 10)
        self.max_reminders = self.config.get('max_reminders', 3)
        
        self.confirmations: Dict[str, Confirmation] = {}
        self._load_confirmations()
    
    def _load_confirmations(self):
        confirmations_file = self.confirmations_dir / "confirmations.json"
        if confirmations_file.exists():
            try:
                with open(confirmations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for cid, cdata in data.items():
                        self.confirmations[cid] = Confirmation(
                            confirmation_id=cdata['confirmation_id'],
                            report_id=cdata['report_id'],
                            order_ids=cdata['order_ids'],
                            status=ConfirmationStatus(cdata['status']),
                            confirmation_type=ConfirmationType(cdata['confirmation_type']) if cdata.get('confirmation_type') else None,
                            trader_id=cdata.get('trader_id'),
                            confirmed_at=cdata.get('confirmed_at'),
                            timeout_minutes=cdata.get('timeout_minutes', self.default_timeout),
                            created_at=cdata['created_at'],
                            updated_at=cdata['updated_at'],
                            notes=cdata.get('notes', ''),
                            reminder_sent=cdata.get('reminder_sent', False),
                            reminder_count=cdata.get('reminder_count', 0),
                        )
                logger.info(f"加载确认记录: {len(self.confirmations)} 条")
            except Exception as e:
                logger.warning(f"加载确认记录失败: {e}")
    
    def _save_confirmations(self):
        confirmations_file = self.confirmations_dir / "confirmations.json"
        try:
            with open(confirmations_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {cid: c.to_dict() for cid, c in self.confirmations.items()},
                    f, ensure_ascii=False, indent=2
                )
        except Exception as e:
            logger.error(f"保存确认记录失败: {e}")
    
    def generate_confirmation_id(self) -> str:
        return f"CF-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    
    def create_confirmation(
        self,
        report_id: str,
        order_ids: List[str],
        timeout_minutes: int = None,
        notes: str = ""
    ) -> Confirmation:
        confirmation_id = self.generate_confirmation_id()
        now = datetime.now().isoformat()
        
        confirmation = Confirmation(
            confirmation_id=confirmation_id,
            report_id=report_id,
            order_ids=order_ids,
            status=ConfirmationStatus.PENDING,
            confirmation_type=None,
            trader_id=None,
            confirmed_at=None,
            timeout_minutes=timeout_minutes or self.default_timeout,
            created_at=now,
            updated_at=now,
            notes=notes
        )
        
        self.confirmations[confirmation_id] = confirmation
        self._save_confirmations()
        
        logger.info(f"创建确认请求: {confirmation_id} - 报告 {report_id}")
        
        return confirmation
    
    def confirm(
        self,
        confirmation_id: str,
        confirmation_type: ConfirmationType,
        trader_id: str = None,
        notes: str = ""
    ) -> Optional[Confirmation]:
        if confirmation_id not in self.confirmations:
            logger.warning(f"确认记录不存在: {confirmation_id}")
            return None
        
        confirmation = self.confirmations[confirmation_id]
        
        if confirmation.status != ConfirmationStatus.PENDING:
            logger.warning(f"确认记录状态不允许确认: {confirmation.status.value}")
            return None
        
        confirmation.status = ConfirmationStatus.CONFIRMED
        confirmation.confirmation_type = confirmation_type
        confirmation.trader_id = trader_id
        confirmation.confirmed_at = datetime.now().isoformat()
        confirmation.updated_at = datetime.now().isoformat()
        if notes:
            confirmation.notes = notes
        
        self._save_confirmations()
        
        icon, text = CONFIRMATION_DISPLAY.get(confirmation_type, ("❓", "未知"))
        logger.info(f"确认完成: {confirmation_id} - {text} by {trader_id}")
        
        return confirmation
    
    def reject(
        self,
        confirmation_id: str,
        trader_id: str = None,
        reason: str = ""
    ) -> Optional[Confirmation]:
        return self.confirm(
            confirmation_id=confirmation_id,
            confirmation_type=ConfirmationType.REJECTED,
            trader_id=trader_id,
            notes=reason
        )
    
    def timeout_confirmation(self, confirmation_id: str) -> Optional[Confirmation]:
        if confirmation_id not in self.confirmations:
            return None
        
        confirmation = self.confirmations[confirmation_id]
        
        if confirmation.status != ConfirmationStatus.PENDING:
            return None
        
        if not confirmation.is_expired:
            return None
        
        confirmation.status = ConfirmationStatus.TIMEOUT
        confirmation.updated_at = datetime.now().isoformat()
        confirmation.notes = "超时未确认"
        
        self._save_confirmations()
        
        logger.warning(f"确认超时: {confirmation_id}")
        
        return confirmation
    
    def check_timeouts(self) -> List[Confirmation]:
        timed_out = []
        
        for confirmation in self.confirmations.values():
            if confirmation.status == ConfirmationStatus.PENDING and confirmation.is_expired:
                result = self.timeout_confirmation(confirmation.confirmation_id)
                if result:
                    timed_out.append(result)
        
        return timed_out
    
    def check_reminders(self) -> List[Confirmation]:
        need_reminder = []
        
        for confirmation in self.confirmations.values():
            if confirmation.status != ConfirmationStatus.PENDING:
                continue
            
            if confirmation.reminder_count >= self.max_reminders:
                continue
            
            created = datetime.fromisoformat(confirmation.created_at)
            next_reminder_time = created + timedelta(minutes=self.reminder_interval * (confirmation.reminder_count + 1))
            
            if datetime.now() >= next_reminder_time:
                confirmation.reminder_sent = True
                confirmation.reminder_count += 1
                confirmation.updated_at = datetime.now().isoformat()
                need_reminder.append(confirmation)
        
        if need_reminder:
            self._save_confirmations()
        
        return need_reminder
    
    def get_confirmation(self, confirmation_id: str) -> Optional[Confirmation]:
        return self.confirmations.get(confirmation_id)
    
    def get_pending_confirmations(self) -> List[Confirmation]:
        return [
            c for c in self.confirmations.values()
            if c.status == ConfirmationStatus.PENDING
        ]
    
    def get_confirmations_by_report(self, report_id: str) -> List[Confirmation]:
        return [
            c for c in self.confirmations.values()
            if c.report_id == report_id
        ]
    
    def get_confirmation_summary(self) -> Dict:
        total = len(self.confirmations)
        pending = len([c for c in self.confirmations.values() if c.status == ConfirmationStatus.PENDING])
        confirmed = len([c for c in self.confirmations.values() if c.status == ConfirmationStatus.CONFIRMED])
        timeout = len([c for c in self.confirmations.values() if c.status == ConfirmationStatus.TIMEOUT])
        cancelled = len([c for c in self.confirmations.values() if c.status == ConfirmationStatus.CANCELLED])
        
        type_distribution = {}
        for confirmation in self.confirmations.values():
            if confirmation.confirmation_type:
                ctype = confirmation.confirmation_type.value
                type_distribution[ctype] = type_distribution.get(ctype, 0) + 1
        
        return {
            'total': total,
            'pending': pending,
            'confirmed': confirmed,
            'timeout': timeout,
            'cancelled': cancelled,
            'confirmation_rate': confirmed / total if total > 0 else 0,
            'timeout_rate': timeout / total if total > 0 else 0,
            'type_distribution': type_distribution,
        }
    
    def cancel_confirmation(self, confirmation_id: str, reason: str = "") -> bool:
        if confirmation_id not in self.confirmations:
            return False
        
        confirmation = self.confirmations[confirmation_id]
        
        if confirmation.status != ConfirmationStatus.PENDING:
            return False
        
        confirmation.status = ConfirmationStatus.CANCELLED
        confirmation.updated_at = datetime.now().isoformat()
        confirmation.notes = reason or "已取消"
        
        self._save_confirmations()
        
        logger.info(f"取消确认: {confirmation_id}")
        return True
    
    def print_summary(self):
        summary = self.get_confirmation_summary()
        
        print(f"\n{'='*60}")
        print("📋 确认机制摘要")
        print(f"{'='*60}")
        print(f"  总确认数: {summary['total']}")
        print(f"  待确认: {summary['pending']}")
        print(f"  已确认: {summary['confirmed']}")
        print(f"  超时: {summary['timeout']}")
        print(f"  已取消: {summary['cancelled']}")
        print(f"  确认率: {summary['confirmation_rate']:.1%}")
        print(f"  超时率: {summary['timeout_rate']:.1%}")
        
        pending = self.get_pending_confirmations()
        if pending:
            print(f"\n  待确认列表:")
            for c in pending[:5]:
                remaining = c.remaining_minutes
                print(f"    {c.confirmation_id}: 剩余 {remaining} 分钟")
        
        print(f"{'='*60}\n")
