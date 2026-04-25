"""
预警触发器

基于监控数据触发预警和回测。
核心逻辑：
1. 持续监控绩效、风险、信号等指标
2. 当指标超过阈值时触发预警
3. 预警达到一定级别时触发深度回测
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import pandas as pd
import numpy as np

from ..infrastructure.logging import get_logger


class AlertCategory(Enum):
    """预警类别"""
    PERFORMANCE = "performance"
    RISK = "risk"
    SIGNAL = "signal"
    FACTOR = "factor"
    MARKET = "market"


class AlertSeverity(Enum):
    """预警严重程度"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class AlertCondition:
    """预警条件"""
    name: str
    category: AlertCategory
    description: str
    threshold_warning: float
    threshold_critical: float
    threshold_emergency: float
    current_value: float = 0.0
    triggered: bool = False
    severity: AlertSeverity = AlertSeverity.INFO
    
    def check(self, value: float) -> Tuple[bool, AlertSeverity]:
        """检查是否触发预警"""
        self.current_value = value
        
        if self.threshold_emergency > 0 and value >= self.threshold_emergency:
            self.severity = AlertSeverity.EMERGENCY
            self.triggered = True
            return True, self.severity
        elif self.threshold_critical > 0 and value >= self.threshold_critical:
            self.severity = AlertSeverity.CRITICAL
            self.triggered = True
            return True, self.severity
        elif self.threshold_warning > 0 and value >= self.threshold_warning:
            self.severity = AlertSeverity.WARNING
            self.triggered = True
            return True, self.severity
        
        self.triggered = False
        self.severity = AlertSeverity.INFO
        return False, self.severity


@dataclass
class AlertEvent:
    """预警事件"""
    timestamp: datetime
    category: AlertCategory
    severity: AlertSeverity
    condition_name: str
    current_value: float
    threshold: float
    message: str
    action_required: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "category": self.category.value,
            "severity": self.severity.value,
            "condition_name": self.condition_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "message": self.message,
            "action_required": self.action_required
        }


@dataclass
class MonitorStatus:
    """监控状态"""
    last_check_time: datetime
    performance_status: str = "normal"
    risk_status: str = "normal"
    signal_status: str = "normal"
    factor_status: str = "normal"
    overall_status: str = "normal"
    active_alerts: List[AlertEvent] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_check_time": self.last_check_time.isoformat(),
            "performance_status": self.performance_status,
            "risk_status": self.risk_status,
            "signal_status": self.signal_status,
            "factor_status": self.factor_status,
            "overall_status": self.overall_status,
            "active_alerts": [a.to_dict() for a in self.active_alerts]
        }


class AlertTrigger:
    """
    预警触发器
    
    监控策略运行状态，当指标异常时触发预警。
    预警级别达到CRITICAL时触发深度回测。
    """
    
    PERFORMANCE_CONDITIONS = [
        AlertCondition(
            name="daily_loss",
            category=AlertCategory.PERFORMANCE,
            description="单日亏损",
            threshold_warning=0.015,
            threshold_critical=0.03,
            threshold_emergency=0.05
        ),
        AlertCondition(
            name="weekly_loss",
            category=AlertCategory.PERFORMANCE,
            description="周度亏损",
            threshold_warning=0.03,
            threshold_critical=0.05,
            threshold_emergency=0.08
        ),
        AlertCondition(
            name="monthly_loss",
            category=AlertCategory.PERFORMANCE,
            description="月度亏损",
            threshold_warning=0.05,
            threshold_critical=0.08,
            threshold_emergency=0.12
        ),
        AlertCondition(
            name="consecutive_loss_days",
            category=AlertCategory.PERFORMANCE,
            description="连续亏损天数",
            threshold_warning=3,
            threshold_critical=5,
            threshold_emergency=7
        ),
        AlertCondition(
            name="sharpe_decline_weeks",
            category=AlertCategory.PERFORMANCE,
            description="夏普比率连续下降周数",
            threshold_warning=2,
            threshold_critical=4,
            threshold_emergency=6
        ),
    ]
    
    RISK_CONDITIONS = [
        AlertCondition(
            name="max_drawdown",
            category=AlertCategory.RISK,
            description="最大回撤",
            threshold_warning=0.07,
            threshold_critical=0.10,
            threshold_emergency=0.15
        ),
        AlertCondition(
            name="volatility",
            category=AlertCategory.RISK,
            description="波动率",
            threshold_warning=0.25,
            threshold_critical=0.35,
            threshold_emergency=0.50
        ),
        AlertCondition(
            name="position_concentration",
            category=AlertCategory.RISK,
            description="持仓集中度",
            threshold_warning=0.30,
            threshold_critical=0.40,
            threshold_emergency=0.50
        ),
        AlertCondition(
            name="industry_concentration",
            category=AlertCategory.RISK,
            description="行业集中度",
            threshold_warning=0.35,
            threshold_critical=0.45,
            threshold_emergency=0.55
        ),
    ]
    
    SIGNAL_CONDITIONS = [
        AlertCondition(
            name="signal_count_anomaly",
            category=AlertCategory.SIGNAL,
            description="信号数量异常（偏离均值倍数）",
            threshold_warning=1.5,
            threshold_critical=2.0,
            threshold_emergency=3.0
        ),
        AlertCondition(
            name="signal_win_rate",
            category=AlertCategory.SIGNAL,
            description="信号胜率下降",
            threshold_warning=0.50,
            threshold_critical=0.45,
            threshold_emergency=0.40
        ),
        AlertCondition(
            name="no_signal_days",
            category=AlertCategory.SIGNAL,
            description="无信号天数",
            threshold_warning=3,
            threshold_critical=5,
            threshold_emergency=7
        ),
    ]
    
    FACTOR_CONDITIONS = [
        AlertCondition(
            name="factor_ic_decline",
            category=AlertCategory.FACTOR,
            description="因子IC下降",
            threshold_warning=0.02,
            threshold_critical=0.01,
            threshold_emergency=0.0
        ),
        AlertCondition(
            name="factor_decay_rate",
            category=AlertCategory.FACTOR,
            description="因子衰减率",
            threshold_warning=0.20,
            threshold_critical=0.35,
            threshold_emergency=0.50
        ),
    ]
    
    MARKET_CONDITIONS = [
        AlertCondition(
            name="market_volatility_spike",
            category=AlertCategory.MARKET,
            description="市场波动率飙升",
            threshold_warning=1.5,
            threshold_critical=2.0,
            threshold_emergency=3.0
        ),
        AlertCondition(
            name="market_trend_reversal",
            category=AlertCategory.MARKET,
            description="市场趋势反转幅度",
            threshold_warning=0.03,
            threshold_critical=0.05,
            threshold_emergency=0.08
        ),
    ]
    
    def __init__(
        self,
        storage_path: str = "./data/monitor",
        history_days: int = 30
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.history_days = history_days
        self.logger = get_logger("monitor.alert_trigger")
        
        self.conditions = {
            AlertCategory.PERFORMANCE: self.PERFORMANCE_CONDITIONS.copy(),
            AlertCategory.RISK: self.RISK_CONDITIONS.copy(),
            AlertCategory.SIGNAL: self.SIGNAL_CONDITIONS.copy(),
            AlertCategory.FACTOR: self.FACTOR_CONDITIONS.copy(),
            AlertCategory.MARKET: self.MARKET_CONDITIONS.copy(),
        }
        
        self.alert_history: List[AlertEvent] = []
        self._load_history()
    
    def _load_history(self):
        """加载历史预警"""
        history_file = self.storage_path / "alert_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                cutoff = datetime.now() - timedelta(days=self.history_days)
                for item in data:
                    ts = datetime.fromisoformat(item["timestamp"])
                    if ts >= cutoff:
                        self.alert_history.append(AlertEvent(
                            timestamp=ts,
                            category=AlertCategory(item["category"]),
                            severity=AlertSeverity(item["severity"]),
                            condition_name=item["condition_name"],
                            current_value=item["current_value"],
                            threshold=item["threshold"],
                            message=item["message"],
                            action_required=item["action_required"]
                        ))
            except Exception as e:
                self.logger.warning(f"加载预警历史失败: {e}")
    
    def _save_history(self):
        """保存预警历史"""
        history_file = self.storage_path / "alert_history.json"
        try:
            data = [a.to_dict() for a in self.alert_history]
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"保存预警历史失败: {e}")
    
    def check_performance(
        self,
        daily_return: float = 0.0,
        weekly_return: float = 0.0,
        monthly_return: float = 0.0,
        consecutive_loss_days: int = 0,
        sharpe_decline_weeks: int = 0
    ) -> List[AlertEvent]:
        """检查绩效指标"""
        alerts = []
        values = {
            "daily_loss": abs(daily_return) if daily_return < 0 else 0,
            "weekly_loss": abs(weekly_return) if weekly_return < 0 else 0,
            "monthly_loss": abs(monthly_return) if monthly_return < 0 else 0,
            "consecutive_loss_days": consecutive_loss_days,
            "sharpe_decline_weeks": sharpe_decline_weeks,
        }
        
        for cond in self.conditions[AlertCategory.PERFORMANCE]:
            value = values.get(cond.name, 0)
            triggered, severity = cond.check(value)
            
            if triggered:
                alert = AlertEvent(
                    timestamp=datetime.now(),
                    category=AlertCategory.PERFORMANCE,
                    severity=severity,
                    condition_name=cond.name,
                    current_value=value,
                    threshold=cond.threshold_warning,
                    message=f"{cond.description}达到预警: {value:.4f}",
                    action_required=self._get_action_required(severity, cond.name)
                )
                alerts.append(alert)
                self.alert_history.append(alert)
        
        return alerts
    
    def check_risk(
        self,
        max_drawdown: float = 0.0,
        volatility: float = 0.0,
        position_concentration: float = 0.0,
        industry_concentration: float = 0.0
    ) -> List[AlertEvent]:
        """检查风险指标"""
        alerts = []
        values = {
            "max_drawdown": max_drawdown,
            "volatility": volatility,
            "position_concentration": position_concentration,
            "industry_concentration": industry_concentration,
        }
        
        for cond in self.conditions[AlertCategory.RISK]:
            value = values.get(cond.name, 0)
            triggered, severity = cond.check(value)
            
            if triggered:
                alert = AlertEvent(
                    timestamp=datetime.now(),
                    category=AlertCategory.RISK,
                    severity=severity,
                    condition_name=cond.name,
                    current_value=value,
                    threshold=cond.threshold_warning,
                    message=f"{cond.description}达到预警: {value:.4f}",
                    action_required=self._get_action_required(severity, cond.name)
                )
                alerts.append(alert)
                self.alert_history.append(alert)
        
        return alerts
    
    def check_signal(
        self,
        signal_count: int = 0,
        avg_signal_count: float = 5.0,
        signal_win_rate: float = 0.5,
        no_signal_days: int = 0
    ) -> List[AlertEvent]:
        """检查信号指标"""
        alerts = []
        
        signal_deviation = abs(signal_count - avg_signal_count) / max(avg_signal_count, 1)
        
        values = {
            "signal_count_anomaly": signal_deviation,
            "signal_win_rate": 1 - signal_win_rate,
            "no_signal_days": no_signal_days,
        }
        
        for cond in self.conditions[AlertCategory.SIGNAL]:
            value = values.get(cond.name, 0)
            triggered, severity = cond.check(value)
            
            if triggered:
                alert = AlertEvent(
                    timestamp=datetime.now(),
                    category=AlertCategory.SIGNAL,
                    severity=severity,
                    condition_name=cond.name,
                    current_value=value,
                    threshold=cond.threshold_warning,
                    message=f"{cond.description}达到预警: {value:.4f}",
                    action_required=self._get_action_required(severity, cond.name)
                )
                alerts.append(alert)
                self.alert_history.append(alert)
        
        return alerts
    
    def check_factor(
        self,
        avg_ic: float = 0.03,
        decay_rate: float = 0.1
    ) -> List[AlertEvent]:
        """检查因子指标"""
        alerts = []
        values = {
            "factor_ic_decline": max(0, 0.03 - avg_ic),
            "factor_decay_rate": decay_rate,
        }
        
        for cond in self.conditions[AlertCategory.FACTOR]:
            value = values.get(cond.name, 0)
            triggered, severity = cond.check(value)
            
            if triggered:
                alert = AlertEvent(
                    timestamp=datetime.now(),
                    category=AlertCategory.FACTOR,
                    severity=severity,
                    condition_name=cond.name,
                    current_value=value,
                    threshold=cond.threshold_warning,
                    message=f"{cond.description}达到预警: {value:.4f}",
                    action_required=self._get_action_required(severity, cond.name)
                )
                alerts.append(alert)
                self.alert_history.append(alert)
        
        return alerts
    
    def check_market(
        self,
        volatility_spike: float = 1.0,
        trend_reversal: float = 0.0
    ) -> List[AlertEvent]:
        """检查市场指标"""
        alerts = []
        values = {
            "market_volatility_spike": volatility_spike,
            "market_trend_reversal": abs(trend_reversal),
        }
        
        for cond in self.conditions[AlertCategory.MARKET]:
            value = values.get(cond.name, 0)
            triggered, severity = cond.check(value)
            
            if triggered:
                alert = AlertEvent(
                    timestamp=datetime.now(),
                    category=AlertCategory.MARKET,
                    severity=severity,
                    condition_name=cond.name,
                    current_value=value,
                    threshold=cond.threshold_warning,
                    message=f"{cond.description}达到预警: {value:.4f}",
                    action_required=self._get_action_required(severity, cond.name)
                )
                alerts.append(alert)
                self.alert_history.append(alert)
        
        return alerts
    
    def _get_action_required(self, severity: AlertSeverity, condition_name: str) -> str:
        """获取需要采取的行动"""
        if severity == AlertSeverity.EMERGENCY:
            return "立即停止交易，执行深度回测，人工介入"
        elif severity == AlertSeverity.CRITICAL:
            return "触发深度回测，评估策略有效性"
        elif severity == AlertSeverity.WARNING:
            return "持续监控，准备应对措施"
        else:
            return "记录日志，继续观察"
    
    def should_trigger_backtest(self) -> Tuple[bool, str]:
        """
        判断是否应该触发回测
        
        触发条件：
        1. 任何EMERGENCY级别预警
        2. 多个CRITICAL级别预警
        3. 连续多个WARNING级别预警
        """
        recent_alerts = [
            a for a in self.alert_history
            if a.timestamp >= datetime.now() - timedelta(hours=24)
        ]
        
        emergency_count = sum(1 for a in recent_alerts if a.severity == AlertSeverity.EMERGENCY)
        critical_count = sum(1 for a in recent_alerts if a.severity == AlertSeverity.CRITICAL)
        warning_count = sum(1 for a in recent_alerts if a.severity == AlertSeverity.WARNING)
        
        if emergency_count > 0:
            return True, f"检测到{emergency_count}个紧急预警，需要立即回测"
        
        if critical_count >= 2:
            return True, f"检测到{critical_count}个严重预警，需要深度回测"
        
        if critical_count >= 1 and warning_count >= 3:
            return True, f"检测到{critical_count}个严重预警和{warning_count}个警告，需要回测"
        
        return False, ""
    
    def get_status(self) -> MonitorStatus:
        """获取当前监控状态"""
        recent_alerts = [
            a for a in self.alert_history
            if a.timestamp >= datetime.now() - timedelta(hours=24)
        ]
        
        def get_category_status(category: AlertCategory) -> str:
            cat_alerts = [a for a in recent_alerts if a.category == category]
            if any(a.severity == AlertSeverity.EMERGENCY for a in cat_alerts):
                return "emergency"
            elif any(a.severity == AlertSeverity.CRITICAL for a in cat_alerts):
                return "critical"
            elif any(a.severity == AlertSeverity.WARNING for a in cat_alerts):
                return "warning"
            return "normal"
        
        overall = "normal"
        for cat in AlertCategory:
            status = get_category_status(cat)
            if status == "emergency":
                overall = "emergency"
                break
            elif status == "critical" and overall != "emergency":
                overall = "critical"
            elif status == "warning" and overall not in ["emergency", "critical"]:
                overall = "warning"
        
        return MonitorStatus(
            last_check_time=datetime.now(),
            performance_status=get_category_status(AlertCategory.PERFORMANCE),
            risk_status=get_category_status(AlertCategory.RISK),
            signal_status=get_category_status(AlertCategory.SIGNAL),
            factor_status=get_category_status(AlertCategory.FACTOR),
            overall_status=overall,
            active_alerts=recent_alerts
        )
    
    def save_status(self):
        """保存监控状态"""
        status = self.get_status()
        status_file = self.storage_path / "monitor_status.json"
        try:
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"保存监控状态失败: {e}")
        
        self._save_history()


_alert_trigger: Optional[AlertTrigger] = None


def get_alert_trigger() -> AlertTrigger:
    """获取预警触发器单例"""
    global _alert_trigger
    if _alert_trigger is None:
        _alert_trigger = AlertTrigger()
    return _alert_trigger
