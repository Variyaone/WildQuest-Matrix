"""
监控系统模块

提供完整的监控体系，包括：
- 监控仪表盘 (Dashboard)
- 绩效追踪 (PerformanceTracker)
- 异常告警 (AlertSystem)
- 日志管理 (LogManager)
- 报告生成 (ReportGenerator)
- 归因分析 (AttributionAnalyzer)
- 因子衰减监控 (FactorDecayMonitor)
- 信号质量监控 (SignalQualityMonitor)
- 策略健康监控 (StrategyHealthMonitor)
- 系统健康监控 (SystemHealthMonitor)
- 预警触发器 (AlertTrigger)
- 监控仪表盘 (MonitorDashboard)
"""

from core.monitor.dashboard import Dashboard, DashboardManager
from core.monitor.tracker import PerformanceTracker, PerformanceMetrics
from core.monitor.alert import AlertSystem, Alert, AlertLevel
from core.monitor.log import LogManager, LogType
from core.monitor.report import ReportGenerator, ReportType
from core.monitor.attribution import AttributionAnalyzer, AttributionResult
from core.monitor.factor_decay import FactorDecayMonitor, DecayLevel
from core.monitor.signal_quality import SignalQualityMonitor, QualityLevel
from core.monitor.strategy_health import StrategyHealthMonitor, HealthLevel
from core.monitor.system_health import SystemHealthMonitor, SystemStatus
from core.monitor.alert_trigger import AlertTrigger, AlertCategory, AlertSeverity, get_alert_trigger
from core.monitor.monitor_dashboard import MonitorDashboard, get_monitor_dashboard

__all__ = [
    "Dashboard",
    "DashboardManager",
    "PerformanceTracker",
    "PerformanceMetrics",
    "AlertSystem",
    "Alert",
    "AlertLevel",
    "LogManager",
    "LogType",
    "ReportGenerator",
    "ReportType",
    "AttributionAnalyzer",
    "AttributionResult",
    "FactorDecayMonitor",
    "DecayLevel",
    "SignalQualityMonitor",
    "QualityLevel",
    "StrategyHealthMonitor",
    "HealthLevel",
    "SystemHealthMonitor",
    "SystemStatus",
    "AlertTrigger",
    "AlertCategory",
    "AlertSeverity",
    "get_alert_trigger",
    "MonitorDashboard",
    "get_monitor_dashboard",
]
