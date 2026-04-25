"""
监控仪表盘

整合所有监控模块，提供统一的监控视图。
支持：
1. 绩效监控（每日收盘后）
2. 风险监控（每日）
3. 信号监控（实时）
4. 因子监控（每周）
5. 预警触发（事件驱动）
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
import numpy as np

from ..infrastructure.logging import get_logger
from .alert_trigger import AlertTrigger, get_alert_trigger, AlertSeverity, AlertCategory


@dataclass
class DashboardMetrics:
    """仪表盘指标"""
    timestamp: datetime
    
    daily_return: float = 0.0
    weekly_return: float = 0.0
    monthly_return: float = 0.0
    cumulative_return: float = 0.0
    
    max_drawdown: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    
    position_count: int = 0
    position_concentration: float = 0.0
    industry_concentration: float = 0.0
    
    signal_count_today: int = 0
    signal_win_rate: float = 0.0
    avg_signal_count: float = 5.0
    
    factor_ic: float = 0.0
    factor_decay: float = 0.0
    
    consecutive_loss_days: int = 0
    no_signal_days: int = 0
    
    overall_status: str = "normal"
    active_alerts_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "daily_return": round(self.daily_return, 4),
            "weekly_return": round(self.weekly_return, 4),
            "monthly_return": round(self.monthly_return, 4),
            "cumulative_return": round(self.cumulative_return, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "volatility": round(self.volatility, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "position_count": self.position_count,
            "position_concentration": round(self.position_concentration, 4),
            "industry_concentration": round(self.industry_concentration, 4),
            "signal_count_today": self.signal_count_today,
            "signal_win_rate": round(self.signal_win_rate, 4),
            "avg_signal_count": round(self.avg_signal_count, 2),
            "factor_ic": round(self.factor_ic, 4),
            "factor_decay": round(self.factor_decay, 4),
            "consecutive_loss_days": self.consecutive_loss_days,
            "no_signal_days": self.no_signal_days,
            "overall_status": self.overall_status,
            "active_alerts_count": self.active_alerts_count
        }


@dataclass
class MonitorReport:
    """监控报告"""
    report_time: datetime
    metrics: DashboardMetrics
    alerts: List[Dict[str, Any]]
    recommendations: List[str]
    should_backtest: bool
    backtest_reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_time": self.report_time.isoformat(),
            "metrics": self.metrics.to_dict(),
            "alerts": self.alerts,
            "recommendations": self.recommendations,
            "should_backtest": self.should_backtest,
            "backtest_reason": self.backtest_reason
        }


class MonitorDashboard:
    """
    监控仪表盘
    
    整合绩效、风险、信号、因子监控，提供统一视图。
    根据监控结果触发预警和回测。
    """
    
    def __init__(
        self,
        storage_path: str = "./data/monitor",
        history_days: int = 30
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.history_days = history_days
        self.logger = get_logger("monitor.dashboard")
        
        self.alert_trigger = get_alert_trigger()
        
        self._metrics_history: List[DashboardMetrics] = []
        self._load_history()
    
    def _load_history(self):
        """加载历史指标"""
        history_file = self.storage_path / "metrics_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                cutoff = datetime.now() - timedelta(days=self.history_days)
                for item in data:
                    ts = datetime.fromisoformat(item["timestamp"])
                    if ts >= cutoff:
                        self._metrics_history.append(DashboardMetrics(
                            timestamp=ts,
                            daily_return=item.get("daily_return", 0),
                            weekly_return=item.get("weekly_return", 0),
                            monthly_return=item.get("monthly_return", 0),
                            cumulative_return=item.get("cumulative_return", 0),
                            max_drawdown=item.get("max_drawdown", 0),
                            volatility=item.get("volatility", 0),
                            sharpe_ratio=item.get("sharpe_ratio", 0),
                            position_count=item.get("position_count", 0),
                            position_concentration=item.get("position_concentration", 0),
                            industry_concentration=item.get("industry_concentration", 0),
                            signal_count_today=item.get("signal_count_today", 0),
                            signal_win_rate=item.get("signal_win_rate", 0),
                            avg_signal_count=item.get("avg_signal_count", 5),
                            factor_ic=item.get("factor_ic", 0),
                            factor_decay=item.get("factor_decay", 0),
                            consecutive_loss_days=item.get("consecutive_loss_days", 0),
                            no_signal_days=item.get("no_signal_days", 0),
                            overall_status=item.get("overall_status", "normal"),
                            active_alerts_count=item.get("active_alerts_count", 0)
                        ))
            except Exception as e:
                self.logger.warning(f"加载指标历史失败: {e}")
    
    def _save_history(self):
        """保存历史指标"""
        history_file = self.storage_path / "metrics_history.json"
        try:
            data = [m.to_dict() for m in self._metrics_history]
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"保存指标历史失败: {e}")
    
    def update(
        self,
        daily_return: float = 0.0,
        weekly_return: float = 0.0,
        monthly_return: float = 0.0,
        cumulative_return: float = 0.0,
        max_drawdown: float = 0.0,
        volatility: float = 0.0,
        sharpe_ratio: float = 0.0,
        position_count: int = 0,
        position_concentration: float = 0.0,
        industry_concentration: float = 0.0,
        signal_count_today: int = 0,
        signal_win_rate: float = 0.5,
        factor_ic: float = 0.03,
        factor_decay: float = 0.1,
        market_volatility_spike: float = 1.0,
        market_trend_reversal: float = 0.0
    ) -> MonitorReport:
        """
        更新监控指标并生成报告
        """
        now = datetime.now()
        
        consecutive_loss_days = self._calc_consecutive_loss_days(daily_return)
        no_signal_days = self._calc_no_signal_days(signal_count_today)
        avg_signal_count = self._calc_avg_signal_count()
        
        metrics = DashboardMetrics(
            timestamp=now,
            daily_return=daily_return,
            weekly_return=weekly_return,
            monthly_return=monthly_return,
            cumulative_return=cumulative_return,
            max_drawdown=max_drawdown,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            position_count=position_count,
            position_concentration=position_concentration,
            industry_concentration=industry_concentration,
            signal_count_today=signal_count_today,
            signal_win_rate=signal_win_rate,
            avg_signal_count=avg_signal_count,
            factor_ic=factor_ic,
            factor_decay=factor_decay,
            consecutive_loss_days=consecutive_loss_days,
            no_signal_days=no_signal_days
        )
        
        all_alerts = []
        
        perf_alerts = self.alert_trigger.check_performance(
            daily_return=daily_return,
            weekly_return=weekly_return,
            monthly_return=monthly_return,
            consecutive_loss_days=consecutive_loss_days,
            sharpe_decline_weeks=self._calc_sharpe_decline_weeks(sharpe_ratio)
        )
        all_alerts.extend(perf_alerts)
        
        risk_alerts = self.alert_trigger.check_risk(
            max_drawdown=max_drawdown,
            volatility=volatility,
            position_concentration=position_concentration,
            industry_concentration=industry_concentration
        )
        all_alerts.extend(risk_alerts)
        
        signal_alerts = self.alert_trigger.check_signal(
            signal_count=signal_count_today,
            avg_signal_count=avg_signal_count,
            signal_win_rate=signal_win_rate,
            no_signal_days=no_signal_days
        )
        all_alerts.extend(signal_alerts)
        
        factor_alerts = self.alert_trigger.check_factor(
            avg_ic=factor_ic,
            decay_rate=factor_decay
        )
        all_alerts.extend(factor_alerts)
        
        market_alerts = self.alert_trigger.check_market(
            volatility_spike=market_volatility_spike,
            trend_reversal=market_trend_reversal
        )
        all_alerts.extend(market_alerts)
        
        status = self.alert_trigger.get_status()
        metrics.overall_status = status.overall_status
        metrics.active_alerts_count = len(all_alerts)
        
        self._metrics_history.append(metrics)
        self._save_history()
        self.alert_trigger.save_status()
        
        should_backtest, backtest_reason = self.alert_trigger.should_trigger_backtest()
        
        recommendations = self._generate_recommendations(all_alerts, metrics)
        
        return MonitorReport(
            report_time=now,
            metrics=metrics,
            alerts=[a.to_dict() for a in all_alerts],
            recommendations=recommendations,
            should_backtest=should_backtest,
            backtest_reason=backtest_reason
        )
    
    def _calc_consecutive_loss_days(self, today_return: float) -> int:
        """计算连续亏损天数"""
        if today_return >= 0:
            return 0
        
        count = 1
        for m in reversed(self._metrics_history[:-1]):
            if m.daily_return < 0:
                count += 1
            else:
                break
        return count
    
    def _calc_no_signal_days(self, today_signal_count: int) -> int:
        """计算无信号天数"""
        if today_signal_count > 0:
            return 0
        
        count = 1
        for m in reversed(self._metrics_history[:-1]):
            if m.signal_count_today == 0:
                count += 1
            else:
                break
        return count
    
    def _calc_avg_signal_count(self) -> float:
        """计算平均信号数量"""
        if not self._metrics_history:
            return 5.0
        
        recent = [m.signal_count_today for m in self._metrics_history[-20:]]
        return np.mean(recent) if recent else 5.0
    
    def _calc_sharpe_decline_weeks(self, current_sharpe: float) -> int:
        """计算夏普比率连续下降周数"""
        if len(self._metrics_history) < 5:
            return 0
        
        count = 0
        prev_sharpe = current_sharpe
        for m in reversed(self._metrics_history[-20:]):
            if m.sharpe_ratio < prev_sharpe:
                count += 1
                prev_sharpe = m.sharpe_ratio
            else:
                break
        return count
    
    def _generate_recommendations(
        self,
        alerts: List,
        metrics: DashboardMetrics
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        emergency_alerts = [a for a in alerts if a.severity == AlertSeverity.EMERGENCY]
        
        if emergency_alerts:
            recommendations.append("【紧急】检测到严重异常，建议暂停交易并人工介入")
        
        if critical_alerts:
            recommendations.append("【严重】建议执行深度回测验证策略有效性")
        
        if metrics.consecutive_loss_days >= 3:
            recommendations.append(f"已连续{metrics.consecutive_loss_days}天亏损，建议检查市场环境是否变化")
        
        if metrics.position_concentration > 0.25:
            recommendations.append(f"持仓集中度{metrics.position_concentration:.1%}较高，建议分散风险")
        
        if metrics.industry_concentration > 0.30:
            recommendations.append(f"行业集中度{metrics.industry_concentration:.1%}较高，建议跨行业配置")
        
        if metrics.signal_win_rate < 0.55:
            recommendations.append(f"信号胜率{metrics.signal_win_rate:.1%}偏低，建议优化信号生成逻辑")
        
        if metrics.factor_ic < 0.02:
            recommendations.append(f"因子IC{metrics.factor_ic:.4f}偏低，建议检查因子有效性")
        
        if not recommendations:
            recommendations.append("策略运行正常，继续保持监控")
        
        return recommendations
    
    def get_dashboard_text(self, report: MonitorReport) -> str:
        """生成仪表盘文本报告"""
        lines = []
        m = report.metrics
        
        lines.append("=" * 60)
        lines.append("                    策略监控仪表盘")
        lines.append("=" * 60)
        lines.append(f"报告时间: {report.report_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"整体状态: {self._status_emoji(m.overall_status)} {m.overall_status.upper()}")
        lines.append("")
        
        lines.append("-" * 60)
        lines.append("【绩效监控】")
        lines.append("-" * 60)
        lines.append(f"  今日收益: {m.daily_return:+.2%}")
        lines.append(f"  本周收益: {m.weekly_return:+.2%}")
        lines.append(f"  本月收益: {m.monthly_return:+.2%}")
        lines.append(f"  累计收益: {m.cumulative_return:+.2%}")
        lines.append(f"  最大回撤: {m.max_drawdown:.2%}")
        lines.append(f"  夏普比率: {m.sharpe_ratio:.2f}")
        lines.append(f"  波动率:   {m.volatility:.2%}")
        if m.consecutive_loss_days > 0:
            lines.append(f"  ⚠️ 连续亏损: {m.consecutive_loss_days}天")
        lines.append("")
        
        lines.append("-" * 60)
        lines.append("【风险监控】")
        lines.append("-" * 60)
        lines.append(f"  持仓数量:   {m.position_count}")
        lines.append(f"  持仓集中度: {m.position_concentration:.1%}")
        lines.append(f"  行业集中度: {m.industry_concentration:.1%}")
        lines.append("")
        
        lines.append("-" * 60)
        lines.append("【信号监控】")
        lines.append("-" * 60)
        lines.append(f"  今日信号: {m.signal_count_today}")
        lines.append(f"  信号胜率: {m.signal_win_rate:.1%}")
        if m.no_signal_days > 0:
            lines.append(f"  ⚠️ 无信号天数: {m.no_signal_days}天")
        lines.append("")
        
        lines.append("-" * 60)
        lines.append("【因子监控】")
        lines.append("-" * 60)
        lines.append(f"  因子IC:   {m.factor_ic:.4f}")
        lines.append(f"  因子衰减: {m.factor_decay:.1%}")
        lines.append("")
        
        if report.alerts:
            lines.append("-" * 60)
            lines.append("【活跃预警】")
            lines.append("-" * 60)
            for alert in report.alerts[:5]:
                severity = alert.get("severity", "info")
                emoji = {"emergency": "🔴", "critical": "🟠", "warning": "🟡"}.get(severity, "⚪")
                lines.append(f"  {emoji} [{severity.upper()}] {alert.get('message', '')}")
            lines.append("")
        
        if report.recommendations:
            lines.append("-" * 60)
            lines.append("【操作建议】")
            lines.append("-" * 60)
            for rec in report.recommendations:
                lines.append(f"  • {rec}")
            lines.append("")
        
        if report.should_backtest:
            lines.append("-" * 60)
            lines.append("【回测触发】")
            lines.append("-" * 60)
            lines.append(f"  🔔 {report.backtest_reason}")
            lines.append(f"  建议执行: python -m core.daily --backtest")
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _status_emoji(self, status: str) -> str:
        """状态表情"""
        return {
            "normal": "🟢",
            "warning": "🟡",
            "critical": "🟠",
            "emergency": "🔴"
        }.get(status, "⚪")
    
    def save_report(self, report: MonitorReport):
        """保存监控报告"""
        report_file = self.storage_path / f"monitor_report_{report.report_time.strftime('%Y-%m-%d')}.json"
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"保存监控报告失败: {e}")
    
    def update_from_local_account(
        self,
        signal_count_today: int = 0,
        signal_win_rate: float = 0.5,
        factor_ic: float = 0.03,
        factor_decay: float = 0.1
    ) -> MonitorReport:
        """
        从本地账户读取真实数据更新监控
        
        Args:
            signal_count_today: 今日信号数量
            signal_win_rate: 信号胜率
            factor_ic: 因子IC
            factor_decay: 因子衰减
            
        Returns:
            监控报告
        """
        try:
            from core.trading import get_local_account_tracker
            
            account = get_local_account_tracker()
            summary = account.get_account_summary()
            perf = summary['performance']
            risk = summary['risk']
            acc = summary['account']
            
            return self.update(
                daily_return=perf['daily_return_avg'] / 100,
                weekly_return=0,
                monthly_return=0,
                cumulative_return=perf['total_return'] / 100,
                max_drawdown=perf['max_drawdown'] / 100,
                volatility=perf['volatility'] / 100,
                sharpe_ratio=perf['sharpe_ratio'],
                position_count=acc['position_count'],
                position_concentration=risk['concentration'],
                industry_concentration=risk['industry_concentration'],
                signal_count_today=signal_count_today,
                signal_win_rate=signal_win_rate,
                factor_ic=factor_ic,
                factor_decay=factor_decay
            )
        except Exception as e:
            self.logger.warning(f"从本地账户读取数据失败: {e}")
            return self.update(
                signal_count_today=signal_count_today,
                signal_win_rate=signal_win_rate,
                factor_ic=factor_ic,
                factor_decay=factor_decay
            )


_dashboard: Optional[MonitorDashboard] = None


def get_monitor_dashboard() -> MonitorDashboard:
    """获取监控仪表盘单例"""
    global _dashboard
    if _dashboard is None:
        _dashboard = MonitorDashboard()
    return _dashboard
