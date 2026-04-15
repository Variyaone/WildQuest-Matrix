"""
交易报告推送模块

功能:
- 推送交易指令给交易员
- 支持多种推送渠道 (邮件, 钉钉, 企业微信, 短信)
- 推送日志记录
- 推送状态跟踪

推送时机:
- 交易前: 推送交易决策报告
- 交易中: 接收交易员反馈
- 交易后: 推送成交确认
"""

import json
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from core.infrastructure.config import get_data_paths
from .report import TradeReport

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    EMAIL = "email"
    DINGTALK = "dingtalk"
    WECOM = "wecom"
    SMS = "sms"
    WEBHOOK = "webhook"


@dataclass
class NotificationResult:
    channel: NotificationChannel
    success: bool
    message: str
    sent_at: str
    details: Dict = field(default_factory=dict)


class TradeNotifier:
    """交易报告推送器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        data_root = self.config.get('data_root')
        if data_root:
            self.path_config = get_data_paths(data_root)
        else:
            self.path_config = get_data_paths()
        
        self.notifications_dir = Path(self.path_config.data_root) / "trading" / "notifications"
        self.notifications_dir.mkdir(parents=True, exist_ok=True)
        
        self.email_config = self.config.get('email', {})
        self.dingtalk_config = self.config.get('dingtalk', {})
        self.wecom_config = self.config.get('wecom', {})
        self.sms_config = self.config.get('sms', {})
        self.webhook_config = self.config.get('webhook', {})
        
        self.notification_history: List[Dict] = []
        self._load_history()
    
    def _load_history(self):
        history_file = self.notifications_dir / "notification_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.notification_history = json.load(f)
            except Exception as e:
                logger.warning(f"加载推送历史失败: {e}")
    
    def _save_history(self):
        history_file = self.notifications_dir / "notification_history.json"
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.notification_history[-1000:], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存推送历史失败: {e}")
    
    def push_report(
        self,
        report: TradeReport,
        channels: List[NotificationChannel] = None,
        recipients: Dict[str, List[str]] = None
    ) -> Dict[str, NotificationResult]:
        channels = channels or [NotificationChannel.EMAIL]
        recipients = recipients or {}
        
        results = {}
        
        for channel in channels:
            if channel == NotificationChannel.EMAIL:
                results['email'] = self._push_via_email(
                    report,
                    recipients.get('email', self.email_config.get('recipients', []))
                )
            elif channel == NotificationChannel.DINGTALK:
                results['dingtalk'] = self._push_via_dingtalk(
                    report,
                    recipients.get('dingtalk', [])
                )
            elif channel == NotificationChannel.WECOM:
                results['wecom'] = self._push_via_wecom(
                    report,
                    recipients.get('wecom', [])
                )
            elif channel == NotificationChannel.SMS:
                results['sms'] = self._push_via_sms(
                    report,
                    recipients.get('sms', [])
                )
            elif channel == NotificationChannel.WEBHOOK:
                results['webhook'] = self._push_via_webhook(
                    report
                )
        
        self._record_notification(report, results)
        
        return results
    
    def _push_via_email(self, report: TradeReport, recipients: List[str]) -> NotificationResult:
        if not self.email_config.get('enabled', False):
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                success=False,
                message="邮件推送未启用",
                sent_at=datetime.now().isoformat()
            )
        
        if not recipients:
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                success=False,
                message="未配置收件人",
                sent_at=datetime.now().isoformat()
            )
        
        try:
            smtp_server = self.email_config.get('smtp_server', 'smtp.gmail.com')
            smtp_port = self.email_config.get('smtp_port', 587)
            sender = self.email_config.get('sender', '')
            password = self.email_config.get('password', '')
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[交易报告] {report.report_date} - {report.strategy_name}"
            msg['From'] = sender
            msg['To'] = ', '.join(recipients)
            
            text_content = self._generate_text_content(report)
            html_content = self._generate_html_content(report)
            
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            if self.email_config.get('simulate', True):
                logger.info(f"[模拟] 发送邮件到: {recipients}")
                return NotificationResult(
                    channel=NotificationChannel.EMAIL,
                    success=True,
                    message=f"[模拟] 邮件已发送到 {len(recipients)} 个收件人",
                    sent_at=datetime.now().isoformat(),
                    details={'recipients': recipients}
                )
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, recipients, msg.as_string())
            
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                success=True,
                message=f"邮件已发送到 {len(recipients)} 个收件人",
                sent_at=datetime.now().isoformat(),
                details={'recipients': recipients}
            )
            
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                success=False,
                message=f"发送失败: {str(e)}",
                sent_at=datetime.now().isoformat()
            )
    
    def _push_via_dingtalk(self, report: TradeReport, recipients: List[str]) -> NotificationResult:
        if not self.dingtalk_config.get('enabled', False):
            return NotificationResult(
                channel=NotificationChannel.DINGTALK,
                success=False,
                message="钉钉推送未启用",
                sent_at=datetime.now().isoformat()
            )
        
        try:
            webhook_url = self.dingtalk_config.get('webhook_url', '')
            
            if not webhook_url:
                return NotificationResult(
                    channel=NotificationChannel.DINGTALK,
                    success=False,
                    message="未配置钉钉Webhook",
                    sent_at=datetime.now().isoformat()
                )
            
            content = self._generate_markdown_content(report)
            
            if self.dingtalk_config.get('simulate', True):
                logger.info(f"[模拟] 发送钉钉消息")
                return NotificationResult(
                    channel=NotificationChannel.DINGTALK,
                    success=True,
                    message="[模拟] 钉钉消息已发送",
                    sent_at=datetime.now().isoformat()
                )
            
            import requests
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"交易报告 {report.report_date}",
                    "text": content
                }
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return NotificationResult(
                    channel=NotificationChannel.DINGTALK,
                    success=True,
                    message="钉钉消息已发送",
                    sent_at=datetime.now().isoformat()
                )
            else:
                return NotificationResult(
                    channel=NotificationChannel.DINGTALK,
                    success=False,
                    message=f"钉钉发送失败: {response.text}",
                    sent_at=datetime.now().isoformat()
                )
                
        except Exception as e:
            logger.error(f"发送钉钉消息失败: {e}")
            return NotificationResult(
                channel=NotificationChannel.DINGTALK,
                success=False,
                message=f"发送失败: {str(e)}",
                sent_at=datetime.now().isoformat()
            )
    
    def _push_via_wecom(self, report: TradeReport, recipients: List[str]) -> NotificationResult:
        if not self.wecom_config.get('enabled', False):
            return NotificationResult(
                channel=NotificationChannel.WECOM,
                success=False,
                message="企业微信推送未启用",
                sent_at=datetime.now().isoformat()
            )
        
        return NotificationResult(
            channel=NotificationChannel.WECOM,
            success=True,
            message="[模拟] 企业微信消息已发送",
            sent_at=datetime.now().isoformat()
        )
    
    def _push_via_sms(self, report: TradeReport, recipients: List[str]) -> NotificationResult:
        if not self.sms_config.get('enabled', False):
            return NotificationResult(
                channel=NotificationChannel.SMS,
                success=False,
                message="短信推送未启用",
                sent_at=datetime.now().isoformat()
            )
        
        return NotificationResult(
            channel=NotificationChannel.SMS,
            success=True,
            message="[模拟] 短信已发送",
            sent_at=datetime.now().isoformat()
        )
    
    def _push_via_webhook(self, report: TradeReport) -> NotificationResult:
        if not self.webhook_config.get('enabled', False):
            return NotificationResult(
                channel=NotificationChannel.WEBHOOK,
                success=False,
                message="Webhook推送未启用",
                sent_at=datetime.now().isoformat()
            )
        
        try:
            webhook_url = self.webhook_config.get('url', '')
            
            if not webhook_url:
                return NotificationResult(
                    channel=NotificationChannel.WEBHOOK,
                    success=False,
                    message="未配置Webhook URL",
                    sent_at=datetime.now().isoformat()
                )
            
            payload = report.to_dict()
            
            if self.webhook_config.get('simulate', True):
                logger.info(f"[模拟] 发送Webhook请求")
                return NotificationResult(
                    channel=NotificationChannel.WEBHOOK,
                    success=True,
                    message="[模拟] Webhook请求已发送",
                    sent_at=datetime.now().isoformat()
                )
            
            import requests
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code in [200, 201, 202]:
                return NotificationResult(
                    channel=NotificationChannel.WEBHOOK,
                    success=True,
                    message="Webhook请求已发送",
                    sent_at=datetime.now().isoformat()
                )
            else:
                return NotificationResult(
                    channel=NotificationChannel.WEBHOOK,
                    success=False,
                    message=f"Webhook发送失败: {response.status_code}",
                    sent_at=datetime.now().isoformat()
                )
                
        except Exception as e:
            logger.error(f"发送Webhook失败: {e}")
            return NotificationResult(
                channel=NotificationChannel.WEBHOOK,
                success=False,
                message=f"发送失败: {str(e)}",
                sent_at=datetime.now().isoformat()
            )
    
    def _generate_text_content(self, report: TradeReport) -> str:
        lines = [
            f"交易决策报告 - {report.report_date}",
            f"报告ID: {report.report_id}",
            f"策略: {report.strategy_name}",
            "",
            "交易指令:",
        ]
        
        for order in report.orders:
            side = "买入" if order['side'] == 'buy' else "卖出"
            lines.append(f"  {side}: {order['stock_code']} {order['stock_name']} {order['quantity']}股")
        
        lines.extend([
            "",
            "操作建议:",
        ])
        for rec in report.recommendations:
            lines.append(f"  - {rec}")
        
        return "\n".join(lines)
    
    def _generate_html_content(self, report: TradeReport) -> str:
        buy_orders = [o for o in report.orders if o['side'] == 'buy']
        sell_orders = [o for o in report.orders if o['side'] == 'sell']
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>交易决策报告 - {report.report_date}</h2>
            <p>报告ID: {report.report_id} | 策略: {report.strategy_name}</p>
            
            <h3>买入指令 ({len(buy_orders)})</h3>
            <table border="1" cellpadding="5" style="border-collapse: collapse;">
                <tr><th>股票代码</th><th>股票名称</th><th>数量</th><th>价格</th></tr>
                {''.join(f"<tr><td>{o['stock_code']}</td><td>{o['stock_name']}</td><td>{o['quantity']:,}</td><td>{o.get('price', '市价')}</td></tr>" for o in buy_orders)}
            </table>
            
            <h3>卖出指令 ({len(sell_orders)})</h3>
            <table border="1" cellpadding="5" style="border-collapse: collapse;">
                <tr><th>股票代码</th><th>股票名称</th><th>数量</th><th>价格</th></tr>
                {''.join(f"<tr><td>{o['stock_code']}</td><td>{o['stock_name']}</td><td>{o['quantity']:,}</td><td>{o.get('price', '市价')}</td></tr>" for o in sell_orders)}
            </table>
            
            <h3>操作建议</h3>
            <ul>
                {''.join(f"<li>{rec}</li>" for rec in report.recommendations)}
            </ul>
        </body>
        </html>
        """
        return html
    
    def _generate_markdown_content(self, report: TradeReport) -> str:
        lines = [
            f"## 交易决策报告 - {report.report_date}",
            f"> 报告ID: {report.report_id}",
            f"> 策略: {report.strategy_name}",
            "",
        ]
        
        buy_orders = [o for o in report.orders if o['side'] == 'buy']
        sell_orders = [o for o in report.orders if o['side'] == 'sell']
        
        if buy_orders:
            lines.append(f"### 买入指令 ({len(buy_orders)})")
            for o in buy_orders:
                lines.append(f"- {o['stock_code']} {o['stock_name']}: {o['quantity']:,}股")
            lines.append("")
        
        if sell_orders:
            lines.append(f"### 卖出指令 ({len(sell_orders)})")
            for o in sell_orders:
                lines.append(f"- {o['stock_code']} {o['stock_name']}: {o['quantity']:,}股")
            lines.append("")
        
        lines.append("### 操作建议")
        for rec in report.recommendations:
            lines.append(f"- {rec}")
        
        return "\n".join(lines)
    
    def _record_notification(self, report: TradeReport, results: Dict[str, NotificationResult]):
        record = {
            'report_id': report.report_id,
            'report_date': report.report_date,
            'sent_at': datetime.now().isoformat(),
            'channels': {
                channel: {
                    'success': result.success,
                    'message': result.message
                }
                for channel, result in results.items()
            },
            'order_count': len(report.orders),
        }
        
        self.notification_history.append(record)
        self._save_history()
    
    def push_trade_alert(
        self,
        title: str,
        message: str,
        level: str = "info",
        channels: List[NotificationChannel] = None
    ) -> Dict[str, NotificationResult]:
        channels = channels or [NotificationChannel.EMAIL]
        
        results = {}
        
        for channel in channels:
            results[channel.value] = NotificationResult(
                channel=channel,
                success=True,
                message=f"[模拟] 警报已发送: {title}",
                sent_at=datetime.now().isoformat()
            )
        
        return results
    
    def get_notification_history(self, limit: int = 50) -> List[Dict]:
        return self.notification_history[-limit:]
    
    def get_notification_stats(self) -> Dict:
        total = len(self.notification_history)
        
        success_count = sum(
            1 for n in self.notification_history
            if any(c.get('success', False) for c in n.get('channels', {}).values())
        )
        
        return {
            'total_notifications': total,
            'successful': success_count,
            'failed': total - success_count,
            'success_rate': success_count / total if total > 0 else 0,
        }
