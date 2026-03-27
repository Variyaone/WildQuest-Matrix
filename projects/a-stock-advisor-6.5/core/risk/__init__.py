"""
风控系统模块

提供完整的风险管理功能，包括：
- 事前风控：交易前检查，防止违规交易
- 事中风控：实时监控交易和持仓风险
- 事后风控：交易后分析和归因
- 风险指标计算：VaR、CVaR、最大回撤、波动率等
- 风险预警：多渠道预警通知
- 风险报告：日报、周报、事件报告等
"""

from .limits import (
    RiskLevel,
    LimitType,
    HardLimits,
    SoftLimits,
    AlertThresholds,
    StopLossConfig,
    BlacklistConfig,
    LiquidityConfig,
    RiskLimits,
    get_risk_limits,
    set_risk_limits,
    reset_risk_limits
)

from .metrics import (
    RiskMetricsResult,
    RiskMetricsCalculator,
    calculate_portfolio_concentration,
    calculate_position_usage
)

from .pre_trade import (
    CheckResult,
    Violation,
    PreTradeCheckResult,
    TradeInstruction,
    PortfolioState,
    PreTradeRiskChecker,
    create_portfolio_state
)

from .intraday import (
    MonitorStatus,
    AlertAction,
    PositionRisk,
    PortfolioRiskSnapshot,
    IntradayAlert,
    StopLossTrigger,
    IntradayRiskMonitor,
    TradingActivityMonitor
)

from .post_trade import (
    AttributionType,
    TradeRecord,
    PositionRecord,
    AttributionResult,
    DrawdownAnalysis,
    ComplianceCheckResult,
    PostTradeAnalysis,
    PostTradeAnalyzer
)

from .alert import (
    AlertType,
    AlertChannel,
    AlertMessage,
    AlertHandler,
    LogAlertHandler,
    EmailAlertHandler,
    WebhookAlertHandler,
    DingTalkAlertHandler,
    RiskAlertManager,
    get_alert_manager,
    set_alert_manager,
    reset_alert_manager
)

from .report import (
    ReportFormat,
    ReportType,
    RiskReport,
    RiskReportGenerator,
    ReportFormatter,
    save_report
)


__all__ = [
    "RiskLevel",
    "LimitType",
    "HardLimits",
    "SoftLimits",
    "AlertThresholds",
    "StopLossConfig",
    "BlacklistConfig",
    "LiquidityConfig",
    "RiskLimits",
    "get_risk_limits",
    "set_risk_limits",
    "reset_risk_limits",
    "RiskMetricsResult",
    "RiskMetricsCalculator",
    "calculate_portfolio_concentration",
    "calculate_position_usage",
    "CheckResult",
    "Violation",
    "PreTradeCheckResult",
    "TradeInstruction",
    "PortfolioState",
    "PreTradeRiskChecker",
    "create_portfolio_state",
    "MonitorStatus",
    "AlertAction",
    "PositionRisk",
    "PortfolioRiskSnapshot",
    "IntradayAlert",
    "StopLossTrigger",
    "IntradayRiskMonitor",
    "TradingActivityMonitor",
    "AttributionType",
    "TradeRecord",
    "PositionRecord",
    "AttributionResult",
    "DrawdownAnalysis",
    "ComplianceCheckResult",
    "PostTradeAnalysis",
    "PostTradeAnalyzer",
    "AlertType",
    "AlertChannel",
    "AlertMessage",
    "AlertHandler",
    "LogAlertHandler",
    "EmailAlertHandler",
    "WebhookAlertHandler",
    "DingTalkAlertHandler",
    "RiskAlertManager",
    "get_alert_manager",
    "set_alert_manager",
    "reset_alert_manager",
    "ReportFormat",
    "ReportType",
    "RiskReport",
    "RiskReportGenerator",
    "ReportFormatter",
    "save_report"
]
