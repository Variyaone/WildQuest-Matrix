"""
异常告警模块

检测异常情况并发送告警，支持多种告警类型和渠道。
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import pandas as pd
import numpy as np

from core.infrastructure.logging import get_logger


class AlertLevel(Enum):
    """告警级别"""
    CRITICAL = "critical"  # 严重：立即处理
    WARNING = "warning"    # 警告：当日处理
    INFO = "info"          # 信息：仅记录


class AlertType(Enum):
    """告警类型"""
    RETURN = "return"           # 收益类
    RISK = "risk"               # 风险类
    FACTOR = "factor"           # 因子类
    SIGNAL = "signal"           # 信号类
    STRATEGY = "strategy"       # 策略类
    EXECUTION = "execution"     # 执行类
    SYSTEM = "system"           # 系统类


class AlertChannel(Enum):
    """告警渠道"""
    WEBHOOK = "webhook"
    SMS = "sms"
    EMAIL = "email"


@dataclass
class Alert:
    """告警"""
    alert_id: str
    alert_type: AlertType
    level: AlertLevel
    title: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result["alert_type"] = self.alert_type.value
        result["level"] = self.level.value
        result["created_at"] = self.created_at.isoformat()
        result["acknowledged_at"] = self.acknowledged_at.isoformat() if self.acknowledged_at else None
        return result
    
    def acknowledge(self, by: str = "system"):
        """确认告警"""
        self.acknowledged = True
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = by


@dataclass
class AlertRule:
    """告警规则"""
    rule_id: str
    rule_name: str
    alert_type: AlertType
    condition: str
    threshold: float
    level: AlertLevel
    enabled: bool = True
    cooldown_minutes: int = 60
    last_triggered: Optional[datetime] = None
    
    def should_trigger(self, value: float) -> bool:
        """判断是否触发"""
        if not self.enabled:
            return False
        
        if self.last_triggered:
            elapsed = datetime.now() - self.last_triggered
            if elapsed < timedelta(minutes=self.cooldown_minutes):
                return False
        
        if self.condition == ">":
            return value > self.threshold
        elif self.condition == "<":
            return value < self.threshold
        elif self.condition == ">=":
            return value >= self.threshold
        elif self.condition == "<=":
            return value <= self.threshold
        elif self.condition == "==":
            return abs(value - self.threshold) < 1e-9
        elif self.condition == "!=":
            return abs(value - self.threshold) >= 1e-9
        
        return False


class AlertSystem:
    """告警系统"""
    
    DEFAULT_RULES = [
        AlertRule("R001", "单日亏损严重", AlertType.RETURN, "<", -0.03, AlertLevel.CRITICAL),
        AlertRule("R002", "单日亏损警告", AlertType.RETURN, "<", -0.015, AlertLevel.WARNING),
        AlertRule("R003", "连续亏损警告", AlertType.RETURN, "<", -0.005, AlertLevel.WARNING, cooldown_minutes=1440),
        AlertRule("R004", "周度亏损严重", AlertType.RETURN, "<", -0.05, AlertLevel.CRITICAL, cooldown_minutes=10080),
        
        AlertRule("R101", "最大回撤严重", AlertType.RISK, ">", 0.10, AlertLevel.CRITICAL),
        AlertRule("R102", "最大回撤警告", AlertType.RISK, ">", 0.07, AlertLevel.WARNING),
        AlertRule("R103", "波动率警告", AlertType.RISK, ">", 0.30, AlertLevel.WARNING),
        AlertRule("R104", "Beta暴露警告", AlertType.RISK, ">", 0.5, AlertLevel.WARNING),
        
        AlertRule("R201", "因子IC连续负值", AlertType.FACTOR, "<", 0.0, AlertLevel.WARNING),
        AlertRule("R202", "因子IC极低", AlertType.FACTOR, "<", 0.01, AlertLevel.CRITICAL),
        AlertRule("R203", "因子相关性过高", AlertType.FACTOR, ">", 0.8, AlertLevel.WARNING),
        AlertRule("R204", "因子NaN比例过高", AlertType.FACTOR, ">", 0.30, AlertLevel.CRITICAL),
        
        AlertRule("R301", "信号胜率低", AlertType.SIGNAL, "<", 0.50, AlertLevel.WARNING),
        AlertRule("R302", "信号胜率极低", AlertType.SIGNAL, "<", 0.45, AlertLevel.CRITICAL),
        
        AlertRule("R401", "策略夏普低", AlertType.STRATEGY, "<", 0.5, AlertLevel.WARNING),
        AlertRule("R402", "策略夏普极低", AlertType.STRATEGY, "<", 0.0, AlertLevel.CRITICAL),
        
        AlertRule("R501", "订单执行失败", AlertType.EXECUTION, "==", 0, AlertLevel.CRITICAL),
        AlertRule("R502", "换手率过高", AlertType.EXECUTION, ">", 0.30, AlertLevel.WARNING),
        
        AlertRule("R601", "数据更新失败", AlertType.SYSTEM, "==", 0, AlertLevel.CRITICAL),
        AlertRule("R602", "磁盘空间不足", AlertType.SYSTEM, "<", 10, AlertLevel.WARNING),
    ]
    
    def __init__(
        self,
        system_id: str = "main",
        webhook_url: Optional[str] = None,
        storage_path: str = "./data/alerts"
    ):
        self.system_id = system_id
        self.webhook_url = webhook_url
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("monitor.alert")
        
        self.rules: Dict[str, AlertRule] = {r.rule_id: r for r in self.DEFAULT_RULES}
        self.alerts: List[Alert] = []
        self._alert_counter = 0
        
        self._channel_handlers: Dict[AlertChannel, Callable] = {
            AlertChannel.WEBHOOK: self._send_webhook,
            AlertChannel.SMS: self._send_sms,
            AlertChannel.EMAIL: self._send_email,
        }
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules[rule.rule_id] = rule
        self.logger.info(f"添加告警规则: {rule.rule_id} - {rule.rule_name}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            self.logger.info(f"移除告警规则: {rule_id}")
            return True
        return False
    
    def check_and_alert(
        self,
        rule_id: str,
        value: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Alert]:
        """检查并触发告警"""
        rule = self.rules.get(rule_id)
        if not rule:
            self.logger.warning(f"规则不存在: {rule_id}")
            return None
        
        if rule.should_trigger(value):
            alert = self._create_alert(rule, value, context)
            self.alerts.append(alert)
            rule.last_triggered = datetime.now()
            
            self._dispatch_alert(alert)
            return alert
        
        return None
    
    def _create_alert(
        self,
        rule: AlertRule,
        value: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """创建告警"""
        self._alert_counter += 1
        alert_id = f"ALT-{datetime.now().strftime('%Y%m%d')}-{self._alert_counter:04d}"
        
        title = f"[{rule.level.value.upper()}] {rule.rule_name}"
        message = f"指标值: {value:.4f}, 阈值: {rule.condition} {rule.threshold:.4f}"
        
        details = {
            "rule_id": rule.rule_id,
            "value": value,
            "threshold": rule.threshold,
            "condition": rule.condition,
            "context": context or {}
        }
        
        return Alert(
            alert_id=alert_id,
            alert_type=rule.alert_type,
            level=rule.level,
            title=title,
            message=message,
            details=details
        )
    
    def _dispatch_alert(self, alert: Alert):
        """分发告警"""
        channels = self._get_channels_for_level(alert.level)
        
        for channel in channels:
            handler = self._channel_handlers.get(channel)
            if handler:
                try:
                    handler(alert)
                except Exception as e:
                    self.logger.error(f"发送告警失败: {channel.value}, 错误: {e}")
    
    def _get_channels_for_level(self, level: AlertLevel) -> List[AlertChannel]:
        """根据级别获取告警渠道"""
        if level == AlertLevel.CRITICAL:
            return [AlertChannel.WEBHOOK, AlertChannel.SMS]
        elif level == AlertLevel.WARNING:
            return [AlertChannel.WEBHOOK]
        else:
            return []
    
    def _send_webhook(self, alert: Alert):
        """发送Webhook告警"""
        if not self.webhook_url:
            return
        
        payload = {
            "alert_id": alert.alert_id,
            "level": alert.level.value,
            "type": alert.alert_type.value,
            "title": alert.title,
            "message": alert.message,
            "details": alert.details,
            "timestamp": alert.created_at.isoformat()
        }
        
        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            self.logger.info(f"Webhook告警发送成功: {alert.alert_id}")
        else:
            self.logger.error(f"Webhook告警发送失败: {response.status_code}")
    
    def _send_sms(self, alert: Alert):
        """发送短信告警"""
        self.logger.info(f"[SMS] {alert.title}: {alert.message}")
    
    def _send_email(self, alert: Alert):
        """发送邮件告警"""
        self.logger.info(f"[EMAIL] {alert.title}: {alert.message}")
    
    def acknowledge_alert(self, alert_id: str, by: str = "system") -> bool:
        """确认告警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledge(by)
                self.logger.info(f"确认告警: {alert_id}, 操作人: {by}")
                return True
        return False
    
    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """获取未确认的告警"""
        alerts = [a for a in self.alerts if not a.acknowledged]
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return alerts
    
    def get_alerts_by_type(self, alert_type: AlertType) -> List[Alert]:
        """按类型获取告警"""
        return [a for a in self.alerts if a.alert_type == alert_type]
    
    def get_alerts_by_date(self, date: str) -> List[Alert]:
        """按日期获取告警"""
        return [
            a for a in self.alerts
            if a.created_at.strftime("%Y-%m-%d") == date
        ]
    
    def clear_old_alerts(self, days: int = 30):
        """清理旧告警"""
        cutoff = datetime.now() - timedelta(days=days)
        self.alerts = [a for a in self.alerts if a.created_at >= cutoff]
        self.logger.info(f"清理 {days} 天前的告警")
    
    def save(self) -> bool:
        """保存告警数据"""
        file_path = self.storage_path / f"{self.system_id}_alerts.json"
        
        data = {
            "system_id": self.system_id,
            "alerts": [a.to_dict() for a in self.alerts],
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "alert_type": r.alert_type.value,
                    "condition": r.condition,
                    "threshold": r.threshold,
                    "level": r.level.value,
                    "enabled": r.enabled,
                    "cooldown_minutes": r.cooldown_minutes
                }
                for r in self.rules.values()
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"保存告警数据: {self.system_id}")
        return True
    
    def load(self) -> bool:
        """加载告警数据"""
        file_path = self.storage_path / f"{self.system_id}_alerts.json"
        
        if not file_path.exists():
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.alerts = []
            for a in data["alerts"]:
                alert = Alert(
                    alert_id=a["alert_id"],
                    alert_type=AlertType(a["alert_type"]),
                    level=AlertLevel(a["level"]),
                    title=a["title"],
                    message=a["message"],
                    details=a["details"],
                    acknowledged=a["acknowledged"],
                    acknowledged_by=a.get("acknowledged_by")
                )
                if a.get("created_at"):
                    alert.created_at = datetime.fromisoformat(a["created_at"])
                if a.get("acknowledged_at"):
                    alert.acknowledged_at = datetime.fromisoformat(a["acknowledged_at"])
                self.alerts.append(alert)
            
            self.logger.info(f"加载告警数据: {self.system_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"加载告警数据失败: {e}")
            return False
    
    def generate_summary(self, days: int = 7) -> Dict[str, Any]:
        """生成告警摘要"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_alerts = [a for a in self.alerts if a.created_at >= cutoff]
        
        by_level = {}
        for level in AlertLevel:
            by_level[level.value] = len([a for a in recent_alerts if a.level == level])
        
        by_type = {}
        for atype in AlertType:
            by_type[atype.value] = len([a for a in recent_alerts if a.alert_type == atype])
        
        unacknowledged = len([a for a in recent_alerts if not a.acknowledged])
        
        return {
            "period_days": days,
            "total_alerts": len(recent_alerts),
            "unacknowledged": unacknowledged,
            "by_level": by_level,
            "by_type": by_type,
            "critical_alerts": [
                a.to_dict() for a in recent_alerts
                if a.level == AlertLevel.CRITICAL
            ]
        }
