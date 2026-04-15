"""
风险预警模块

风险超阈值时发送预警通知，支持多种通知渠道。
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import threading
from queue import Queue
import logging

from .limits import RiskLimits, get_risk_limits, RiskLevel


class AlertType(Enum):
    """预警类型"""
    DRAWDOWN = "drawdown"
    CONCENTRATION = "concentration"
    LIQUIDITY = "liquidity"
    VOLATILITY = "volatility"
    STOP_LOSS = "stop_loss"
    BLACKLIST = "blacklist"
    POSITION_LIMIT = "position_limit"
    CUSTOM = "custom"


class AlertChannel(Enum):
    """预警渠道"""
    EMAIL = "email"
    WECHAT = "wechat"
    DINGTALK = "dingtalk"
    SMS = "sms"
    WEBHOOK = "webhook"
    LOG = "log"


@dataclass
class AlertMessage:
    """预警消息"""
    alert_id: str
    alert_type: AlertType
    risk_level: RiskLevel
    title: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    stock_codes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    channels: List[AlertChannel] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "risk_level": self.risk_level.value,
            "title": self.title,
            "message": self.message,
            "details": self.details,
            "stock_codes": self.stock_codes,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "channels": [c.value for c in self.channels]
        }
    
    def format_message(self) -> str:
        """格式化消息"""
        lines = [
            f"【{self.title}】",
            f"预警等级: {self.risk_level.value.upper()}",
            f"预警类型: {self.alert_type.value}",
            f"时间: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"详情: {self.message}",
        ]
        
        if self.stock_codes:
            lines.append(f"相关股票: {', '.join(self.stock_codes)}")
        
        if self.details:
            lines.append("")
            lines.append("详细信息:")
            for key, value in self.details.items():
                lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)


class AlertHandler(ABC):
    """预警处理器基类"""
    
    @abstractmethod
    def send(self, alert: AlertMessage) -> bool:
        """发送预警"""
        pass
    
    @abstractmethod
    def get_channel(self) -> AlertChannel:
        """获取渠道"""
        pass


class LogAlertHandler(AlertHandler):
    """日志预警处理器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("risk_alert")
    
    def get_channel(self) -> AlertChannel:
        return AlertChannel.LOG
    
    def send(self, alert: AlertMessage) -> bool:
        try:
            message = alert.format_message()
            if alert.risk_level == RiskLevel.CRITICAL:
                self.logger.critical(message)
            elif alert.risk_level == RiskLevel.HIGH:
                self.logger.error(message)
            elif alert.risk_level == RiskLevel.MEDIUM:
                self.logger.warning(message)
            else:
                self.logger.info(message)
            return True
        except Exception as e:
            self.logger.error(f"发送日志预警失败: {e}")
            return False


class EmailAlertHandler(AlertHandler):
    """邮件预警处理器"""
    
    def __init__(
        self,
        smtp_server: str = "smtp.example.com",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        from_addr: str = "",
        to_addrs: List[str] = None,
        use_tls: bool = True
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_addr = from_addr
        self.to_addrs = to_addrs or []
        self.use_tls = use_tls
    
    def get_channel(self) -> AlertChannel:
        return AlertChannel.EMAIL
    
    def send(self, alert: AlertMessage) -> bool:
        if not self.to_addrs:
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_addr
            msg['To'] = ', '.join(self.to_addrs)
            msg['Subject'] = f"[{alert.risk_level.value.upper()}] {alert.title}"
            
            body = alert.format_message()
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            
            return True
        except Exception as e:
            logging.error(f"发送邮件预警失败: {e}")
            return False


class WebhookAlertHandler(AlertHandler):
    """Webhook预警处理器"""
    
    def __init__(
        self,
        webhook_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10
    ):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
    
    def get_channel(self) -> AlertChannel:
        return AlertChannel.WEBHOOK
    
    def send(self, alert: AlertMessage) -> bool:
        try:
            import requests
            
            payload = alert.to_dict()
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            return response.status_code == 200
        except Exception as e:
            logging.error(f"发送Webhook预警失败: {e}")
            return False


class DingTalkAlertHandler(AlertHandler):
    """钉钉预警处理器"""
    
    def __init__(self, webhook_url: str, secret: str = ""):
        self.webhook_url = webhook_url
        self.secret = secret
    
    def get_channel(self) -> AlertChannel:
        return AlertChannel.DINGTALK
    
    def send(self, alert: AlertMessage) -> bool:
        try:
            import requests
            import hmac
            import hashlib
            import base64
            import time
            import urllib.parse
            
            url = self.webhook_url
            if self.secret:
                timestamp = str(round(time.time() * 1000))
                string_to_sign = f"{timestamp}\n{self.secret}"
                hmac_code = hmac.new(
                    self.secret.encode('utf-8'),
                    string_to_sign.encode('utf-8'),
                    digestmod=hashlib.sha256
                ).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
            
            message = alert.format_message()
            
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logging.error(f"发送钉钉预警失败: {e}")
            return False


class RiskAlertManager:
    """
    风险预警管理器
    
    管理风险预警的生成、发送和记录。
    """
    
    def __init__(
        self,
        risk_limits: Optional[RiskLimits] = None,
        handlers: Optional[List[AlertHandler]] = None
    ):
        self.risk_limits = risk_limits or get_risk_limits()
        self.handlers = handlers or [LogAlertHandler()]
        
        self._alerts: List[AlertMessage] = []
        self._alert_counter = 0
        self._alert_queue: Queue = Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
    
    def add_handler(self, handler: AlertHandler):
        """添加预警处理器"""
        self.handlers.append(handler)
    
    def start_async(self):
        """启动异步发送"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()
    
    def stop_async(self):
        """停止异步发送"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
            self._worker_thread = None
    
    def _worker(self):
        """异步发送工作线程"""
        while self._running:
            try:
                alert = self._alert_queue.get(timeout=1)
                self._send_alert(alert)
            except:
                pass
    
    def create_alert(
        self,
        alert_type: AlertType,
        risk_level: RiskLevel,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        stock_codes: Optional[List[str]] = None,
        channels: Optional[List[AlertChannel]] = None
    ) -> AlertMessage:
        """创建预警"""
        self._alert_counter += 1
        alert_id = f"ALERT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._alert_counter:04d}"
        
        return AlertMessage(
            alert_id=alert_id,
            alert_type=alert_type,
            risk_level=risk_level,
            title=title,
            message=message,
            details=details or {},
            stock_codes=stock_codes or [],
            channels=channels or [AlertChannel.LOG]
        )
    
    def send_alert(self, alert: AlertMessage, async_mode: bool = False) -> bool:
        """
        发送预警
        
        Args:
            alert: 预警消息
            async_mode: 是否异步发送
            
        Returns:
            是否发送成功
        """
        self._alerts.append(alert)
        
        if async_mode:
            self._alert_queue.put(alert)
            return True
        else:
            return self._send_alert(alert)
    
    def _send_alert(self, alert: AlertMessage) -> bool:
        """实际发送预警"""
        success = False
        
        for handler in self.handlers:
            if handler.get_channel() in alert.channels:
                try:
                    if handler.send(alert):
                        success = True
                except Exception as e:
                    logging.error(f"预警发送失败 [{handler.get_channel().value}]: {e}")
        
        return success
    
    def check_and_alert(
        self,
        current_drawdown: float,
        industry_concentration: Dict[str, float],
        single_stock_weights: Dict[str, float],
        volatility: float = 0.0,
        position_ratio: float = 0.0
    ) -> List[AlertMessage]:
        """
        检查风险并生成预警
        
        Args:
            current_drawdown: 当前回撤
            industry_concentration: 行业集中度
            single_stock_weights: 单票权重
            volatility: 波动率
            position_ratio: 仓位比例
            
        Returns:
            List[AlertMessage]: 生成的预警列表
        """
        alerts = []
        thresholds = self.risk_limits.alert_thresholds
        
        if current_drawdown >= thresholds.drawdown_critical:
            alert = self.create_alert(
                alert_type=AlertType.DRAWDOWN,
                risk_level=RiskLevel.CRITICAL,
                title="回撤预警-临界",
                message=f"当前回撤 {current_drawdown:.2%} 已达到临界阈值 {thresholds.drawdown_critical:.2%}",
                details={"current_drawdown": current_drawdown, "threshold": thresholds.drawdown_critical}
            )
            alerts.append(alert)
        elif current_drawdown >= thresholds.drawdown_warning:
            alert = self.create_alert(
                alert_type=AlertType.DRAWDOWN,
                risk_level=RiskLevel.HIGH,
                title="回撤预警",
                message=f"当前回撤 {current_drawdown:.2%} 已达到预警阈值 {thresholds.drawdown_warning:.2%}",
                details={"current_drawdown": current_drawdown, "threshold": thresholds.drawdown_warning}
            )
            alerts.append(alert)
        
        for industry, weight in industry_concentration.items():
            if weight >= thresholds.industry_concentration_critical:
                alert = self.create_alert(
                    alert_type=AlertType.CONCENTRATION,
                    risk_level=RiskLevel.HIGH,
                    title="行业集中度预警-临界",
                    message=f"行业 {industry} 集中度 {weight:.2%} 已达到临界阈值",
                    details={"industry": industry, "weight": weight, "threshold": thresholds.industry_concentration_critical}
                )
                alerts.append(alert)
            elif weight >= thresholds.industry_concentration_warning:
                alert = self.create_alert(
                    alert_type=AlertType.CONCENTRATION,
                    risk_level=RiskLevel.MEDIUM,
                    title="行业集中度预警",
                    message=f"行业 {industry} 集中度 {weight:.2%} 已达到预警阈值",
                    details={"industry": industry, "weight": weight, "threshold": thresholds.industry_concentration_warning}
                )
                alerts.append(alert)
        
        for stock, weight in single_stock_weights.items():
            if weight >= thresholds.single_stock_weight_critical:
                alert = self.create_alert(
                    alert_type=AlertType.POSITION_LIMIT,
                    risk_level=RiskLevel.HIGH,
                    title="单票权重预警-临界",
                    message=f"股票 {stock} 权重 {weight:.2%} 已达到临界阈值",
                    stock_codes=[stock],
                    details={"stock": stock, "weight": weight, "threshold": thresholds.single_stock_weight_critical}
                )
                alerts.append(alert)
            elif weight >= thresholds.single_stock_weight_warning:
                alert = self.create_alert(
                    alert_type=AlertType.POSITION_LIMIT,
                    risk_level=RiskLevel.MEDIUM,
                    title="单票权重预警",
                    message=f"股票 {stock} 权重 {weight:.2%} 已达到预警阈值",
                    stock_codes=[stock],
                    details={"stock": stock, "weight": weight, "threshold": thresholds.single_stock_weight_warning}
                )
                alerts.append(alert)
        
        if volatility > 0 and volatility >= thresholds.volatility_critical:
            alert = self.create_alert(
                alert_type=AlertType.VOLATILITY,
                risk_level=RiskLevel.HIGH,
                title="波动率预警-临界",
                message=f"当前波动率 {volatility:.2%} 已达到临界阈值",
                details={"volatility": volatility, "threshold": thresholds.volatility_critical}
            )
            alerts.append(alert)
        elif volatility > 0 and volatility >= thresholds.volatility_warning:
            alert = self.create_alert(
                alert_type=AlertType.VOLATILITY,
                risk_level=RiskLevel.MEDIUM,
                title="波动率预警",
                message=f"当前波动率 {volatility:.2%} 已达到预警阈值",
                details={"volatility": volatility, "threshold": thresholds.volatility_warning}
            )
            alerts.append(alert)
        
        for alert in alerts:
            self.send_alert(alert)
        
        return alerts
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """确认预警"""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now()
                return True
        return False
    
    def get_alerts(
        self,
        alert_type: Optional[AlertType] = None,
        risk_level: Optional[RiskLevel] = None,
        acknowledged: Optional[bool] = None,
        since: Optional[datetime] = None
    ) -> List[AlertMessage]:
        """获取预警列表"""
        alerts = self._alerts.copy()
        
        if alert_type is not None:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        if risk_level is not None:
            alerts = [a for a in alerts if a.risk_level == risk_level]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        if since is not None:
            alerts = [a for a in alerts if a.created_at >= since]
        
        return alerts
    
    def get_unacknowledged_alerts(self) -> List[AlertMessage]:
        """获取未确认的预警"""
        return [a for a in self._alerts if not a.acknowledged]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """获取预警摘要"""
        total = len(self._alerts)
        unacknowledged = len(self.get_unacknowledged_alerts())
        
        by_level = {}
        for level in RiskLevel:
            by_level[level.value] = len([a for a in self._alerts if a.risk_level == level])
        
        by_type = {}
        for alert_type in AlertType:
            by_type[alert_type.value] = len([a for a in self._alerts if a.alert_type == alert_type])
        
        return {
            "total_alerts": total,
            "unacknowledged": unacknowledged,
            "by_level": by_level,
            "by_type": by_type
        }
    
    def clear_old_alerts(self, days: int = 30) -> int:
        """清理旧预警"""
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self._alerts)
        self._alerts = [a for a in self._alerts if a.created_at >= cutoff]
        return original_count - len(self._alerts)


_default_alert_manager: Optional[RiskAlertManager] = None


def get_alert_manager() -> RiskAlertManager:
    """获取全局预警管理器"""
    global _default_alert_manager
    if _default_alert_manager is None:
        _default_alert_manager = RiskAlertManager()
    return _default_alert_manager


def set_alert_manager(manager: RiskAlertManager):
    """设置全局预警管理器"""
    global _default_alert_manager
    _default_alert_manager = manager


def reset_alert_manager():
    """重置全局预警管理器"""
    global _default_alert_manager
    _default_alert_manager = None
