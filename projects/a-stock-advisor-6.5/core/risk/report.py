"""
风险报告模块

生成各类风险报告，支持多种输出格式。
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from enum import Enum
from pathlib import Path
import io

from .limits import RiskLimits, get_risk_limits, RiskLevel
from .metrics import RiskMetricsResult, RiskMetricsCalculator
from .pre_trade import PreTradeCheckResult
from .intraday import PortfolioRiskSnapshot
from .post_trade import PostTradeAnalysis
from .alert import AlertMessage


class ReportFormat(Enum):
    """报告格式"""
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    CSV = "csv"


class ReportType(Enum):
    """报告类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    INCIDENT = "incident"
    COMPLIANCE = "compliance"
    SUMMARY = "summary"


@dataclass
class RiskReport:
    """风险报告"""
    report_id: str
    report_type: ReportType
    report_date: date
    generated_at: datetime
    title: str
    summary: str
    sections: Dict[str, Any] = field(default_factory=dict)
    risk_metrics: Optional[RiskMetricsResult] = None
    alerts: List[AlertMessage] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "report_type": self.report_type.value,
            "report_date": self.report_date.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "title": self.title,
            "summary": self.summary,
            "sections": self.sections,
            "risk_metrics": self.risk_metrics.to_dict() if self.risk_metrics else None,
            "alerts": [a.to_dict() for a in self.alerts],
            "recommendations": self.recommendations
        }


class RiskReportGenerator:
    """
    风险报告生成器
    
    生成各类风险报告。
    """
    
    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        self.risk_limits = risk_limits or get_risk_limits()
        self._report_counter = 0
    
    def generate_daily_report(
        self,
        risk_metrics: Optional[RiskMetricsResult] = None,
        snapshot: Optional[PortfolioRiskSnapshot] = None,
        alerts: Optional[List[AlertMessage]] = None,
        pre_trade_result: Optional[PreTradeCheckResult] = None
    ) -> RiskReport:
        """
        生成日报
        
        Args:
            risk_metrics: 风险指标
            snapshot: 组合快照
            alerts: 预警列表
            pre_trade_result: 事前检查结果
            
        Returns:
            RiskReport: 风险报告
        """
        self._report_counter += 1
        report_id = f"RPT-DAILY-{datetime.now().strftime('%Y%m%d')}-{self._report_counter:04d}"
        
        today = date.today()
        
        sections = {}
        
        if risk_metrics:
            sections["风险指标"] = {
                "最大回撤": f"{risk_metrics.max_drawdown:.2%}",
                "当前回撤": f"{risk_metrics.current_drawdown:.2%}",
                "年化波动率": f"{risk_metrics.annualized_volatility:.2%}",
                "VaR(95%)": f"{risk_metrics.var_95:.2%}",
                "CVaR(95%)": f"{risk_metrics.cvar_95:.2%}",
                "夏普比率": f"{risk_metrics.sharpe_ratio:.2f}",
                "Beta": f"{risk_metrics.beta:.2f}"
            }
        
        if snapshot:
            sections["持仓概况"] = {
                "总资产": f"{snapshot.total_capital:,.0f}",
                "持仓市值": f"{snapshot.total_position:,.0f}",
                "现金": f"{snapshot.cash:,.0f}",
                "仓位比例": f"{snapshot.position_ratio:.2%}",
                "持仓数量": len(snapshot.position_risks),
                "当日盈亏": f"{snapshot.day_pnl:,.0f}",
                "当日收益率": f"{snapshot.day_pnl_ratio:.2%}"
            }
            
            if snapshot.industry_concentration:
                industry_section = {}
                for industry, weight in sorted(
                    snapshot.industry_concentration.items(),
                    key=lambda x: x[1],
                    reverse=True
                ):
                    industry_section[industry] = f"{weight:.2%}"
                sections["行业分布"] = industry_section
        
        if pre_trade_result:
            sections["事前检查"] = {
                "检查结果": "通过" if pre_trade_result.passed else "拒绝",
                "违规项数": len(pre_trade_result.violations),
                "警告项数": len(pre_trade_result.warnings),
                "检查项总数": pre_trade_result.total_checks,
                "通过项数": pre_trade_result.passed_checks
            }
        
        alerts = alerts or []
        critical_alerts = [a for a in alerts if a.risk_level == RiskLevel.CRITICAL]
        high_alerts = [a for a in alerts if a.risk_level == RiskLevel.HIGH]
        
        sections["预警统计"] = {
            "预警总数": len(alerts),
            "严重预警": len(critical_alerts),
            "高等级预警": len(high_alerts),
            "未确认预警": len([a for a in alerts if not a.acknowledged])
        }
        
        summary = self._generate_summary(risk_metrics, snapshot, alerts)
        recommendations = self._generate_recommendations(risk_metrics, snapshot, alerts)
        
        return RiskReport(
            report_id=report_id,
            report_type=ReportType.DAILY,
            report_date=today,
            generated_at=datetime.now(),
            title=f"风险日报 - {today}",
            summary=summary,
            sections=sections,
            risk_metrics=risk_metrics,
            alerts=alerts,
            recommendations=recommendations
        )
    
    def generate_weekly_report(
        self,
        daily_reports: List[RiskReport],
        post_trade_analysis: Optional[PostTradeAnalysis] = None
    ) -> RiskReport:
        """
        生成周报
        
        Args:
            daily_reports: 日报列表
            post_trade_analysis: 事后分析
            
        Returns:
            RiskReport: 周报
        """
        self._report_counter += 1
        week_start = date.today() - timedelta(days=date.today().weekday())
        report_id = f"RPT-WEEKLY-{week_start.strftime('%Y%m%d')}-{self._report_counter:04d}"
        
        sections = {}
        
        if daily_reports:
            total_alerts = sum(len(r.alerts) for r in daily_reports)
            critical_days = sum(1 for r in daily_reports if any(a.risk_level == RiskLevel.CRITICAL for a in r.alerts))
            
            sections["本周概况"] = {
                "报告天数": len(daily_reports),
                "预警总数": total_alerts,
                "严重预警天数": critical_days,
                "平均预警数": f"{total_alerts / len(daily_reports):.1f}"
            }
        
        if post_trade_analysis:
            sections["绩效分析"] = {
                "总收益率": f"{post_trade_analysis.total_return:.2%}",
                "基准收益率": f"{post_trade_analysis.benchmark_return:.2%}",
                "超额收益": f"{post_trade_analysis.excess_return:.2%}"
            }
            
            if post_trade_analysis.risk_metrics:
                sections["风险分析"] = {
                    "最大回撤": f"{post_trade_analysis.risk_metrics.max_drawdown:.2%}",
                    "年化波动率": f"{post_trade_analysis.risk_metrics.annualized_volatility:.2%}",
                    "夏普比率": f"{post_trade_analysis.risk_metrics.sharpe_ratio:.2f}",
                    "卡玛比率": f"{post_trade_analysis.risk_metrics.calmar_ratio:.2f}"
                }
        
        summary = self._generate_weekly_summary(daily_reports, post_trade_analysis)
        recommendations = self._generate_weekly_recommendations(daily_reports, post_trade_analysis)
        
        return RiskReport(
            report_id=report_id,
            report_type=ReportType.WEEKLY,
            report_date=week_start,
            generated_at=datetime.now(),
            title=f"风险周报 - {week_start}",
            summary=summary,
            sections=sections,
            risk_metrics=post_trade_analysis.risk_metrics if post_trade_analysis else None,
            alerts=[],
            recommendations=recommendations
        )
    
    def generate_incident_report(
        self,
        incident_type: str,
        incident_description: str,
        affected_stocks: List[str],
        risk_metrics: Optional[RiskMetricsResult] = None,
        alerts: Optional[List[AlertMessage]] = None,
        actions_taken: Optional[List[str]] = None
    ) -> RiskReport:
        """
        生成事件报告
        
        Args:
            incident_type: 事件类型
            incident_description: 事件描述
            affected_stocks: 受影响股票
            risk_metrics: 风险指标
            alerts: 相关预警
            actions_taken: 已采取措施
            
        Returns:
            RiskReport: 事件报告
        """
        self._report_counter += 1
        report_id = f"RPT-INCIDENT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._report_counter:04d}"
        
        sections = {
            "事件信息": {
                "事件类型": incident_type,
                "发生时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "事件描述": incident_description,
                "受影响股票": ", ".join(affected_stocks)
            }
        }
        
        if actions_taken:
            sections["已采取措施"] = {
                f"措施{i+1}": action for i, action in enumerate(actions_taken)
            }
        
        if risk_metrics:
            sections["当前风险状态"] = {
                "当前回撤": f"{risk_metrics.current_drawdown:.2%}",
                "最大回撤": f"{risk_metrics.max_drawdown:.2%}",
                "VaR(95%)": f"{risk_metrics.var_95:.2%}"
            }
        
        summary = f"发生{incident_type}事件: {incident_description}"
        recommendations = self._generate_incident_recommendations(incident_type, affected_stocks)
        
        return RiskReport(
            report_id=report_id,
            report_type=ReportType.INCIDENT,
            report_date=date.today(),
            generated_at=datetime.now(),
            title=f"风险事件报告 - {incident_type}",
            summary=summary,
            sections=sections,
            risk_metrics=risk_metrics,
            alerts=alerts or [],
            recommendations=recommendations
        )
    
    def generate_compliance_report(
        self,
        post_trade_analysis: Optional[PostTradeAnalysis] = None,
        violations: Optional[List[Dict[str, Any]]] = None
    ) -> RiskReport:
        """
        生成合规报告
        
        Args:
            post_trade_analysis: 事后分析
            violations: 违规记录
            
        Returns:
            RiskReport: 合规报告
        """
        self._report_counter += 1
        report_id = f"RPT-COMPLIANCE-{datetime.now().strftime('%Y%m%d')}-{self._report_counter:04d}"
        
        sections = {}
        
        if post_trade_analysis and post_trade_analysis.compliance_results:
            passed_count = sum(1 for c in post_trade_analysis.compliance_results if c.passed)
            total_count = len(post_trade_analysis.compliance_results)
            
            sections["合规检查概况"] = {
                "检查项总数": total_count,
                "通过项数": passed_count,
                "违规项数": total_count - passed_count,
                "合规率": f"{passed_count / total_count:.1%}" if total_count > 0 else "N/A"
            }
            
            for result in post_trade_analysis.compliance_results:
                sections[result.check_name] = {
                    "状态": "通过" if result.passed else "违规",
                    "违规项数": len(result.violations)
                }
        
        violations = violations or []
        if violations:
            sections["违规详情"] = {
                f"违规{i+1}": v for i, v in enumerate(violations[:10])
            }
        
        summary = self._generate_compliance_summary(post_trade_analysis, violations)
        recommendations = self._generate_compliance_recommendations(violations)
        
        return RiskReport(
            report_id=report_id,
            report_type=ReportType.COMPLIANCE,
            report_date=date.today(),
            generated_at=datetime.now(),
            title="合规检查报告",
            summary=summary,
            sections=sections,
            alerts=[],
            recommendations=recommendations
        )
    
    def _generate_summary(
        self,
        risk_metrics: Optional[RiskMetricsResult],
        snapshot: Optional[PortfolioRiskSnapshot],
        alerts: List[AlertMessage]
    ) -> str:
        """生成摘要"""
        parts = []
        
        if snapshot:
            parts.append(f"当前仓位{snapshot.position_ratio:.1%}")
            parts.append(f"当日收益{snapshot.day_pnl_ratio:.2%}")
        
        if risk_metrics:
            parts.append(f"最大回撤{risk_metrics.max_drawdown:.2%}")
        
        if alerts:
            critical = len([a for a in alerts if a.risk_level == RiskLevel.CRITICAL])
            if critical > 0:
                parts.append(f"存在{critical}条严重预警")
            else:
                parts.append(f"共{len(alerts)}条预警")
        else:
            parts.append("无预警")
        
        return "，".join(parts)
    
    def _generate_recommendations(
        self,
        risk_metrics: Optional[RiskMetricsResult],
        snapshot: Optional[PortfolioRiskSnapshot],
        alerts: List[AlertMessage]
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if risk_metrics:
            if risk_metrics.current_drawdown > 0.10:
                recommendations.append("当前回撤较大，建议降低仓位或增加对冲")
            
            if risk_metrics.sharpe_ratio < 0.5:
                recommendations.append("夏普比率偏低，建议优化策略或调整持仓")
        
        if snapshot:
            if snapshot.position_ratio > 0.90:
                recommendations.append("仓位较高，建议保留更多现金应对风险")
            
            if len(snapshot.position_risks) < 5:
                recommendations.append("持仓数量较少，建议适当分散投资")
        
        for alert in alerts:
            if alert.risk_level == RiskLevel.CRITICAL:
                recommendations.append(f"需立即处理: {alert.message}")
        
        return recommendations
    
    def _generate_weekly_summary(
        self,
        daily_reports: List[RiskReport],
        post_trade_analysis: Optional[PostTradeAnalysis]
    ) -> str:
        """生成周报摘要"""
        parts = []
        
        if daily_reports:
            total_alerts = sum(len(r.alerts) for r in daily_reports)
            parts.append(f"本周共{len(daily_reports)}个交易日")
            parts.append(f"累计预警{total_alerts}条")
        
        if post_trade_analysis:
            parts.append(f"周收益率{post_trade_analysis.total_return:.2%}")
        
        return "，".join(parts)
    
    def _generate_weekly_recommendations(
        self,
        daily_reports: List[RiskReport],
        post_trade_analysis: Optional[PostTradeAnalysis]
    ) -> List[str]:
        """生成周报建议"""
        recommendations = []
        
        if daily_reports:
            critical_count = sum(
                len([a for a in r.alerts if a.risk_level == RiskLevel.CRITICAL])
                for r in daily_reports
            )
            if critical_count > 3:
                recommendations.append("本周严重预警较多，建议全面审视风险控制")
        
        if post_trade_analysis:
            if post_trade_analysis.total_return < 0:
                recommendations.append("本周收益为负，建议分析原因并调整策略")
            
            if post_trade_analysis.risk_metrics and post_trade_analysis.risk_metrics.max_drawdown > 0.10:
                recommendations.append("本周回撤较大，建议加强风险控制")
        
        return recommendations
    
    def _generate_incident_recommendations(
        self,
        incident_type: str,
        affected_stocks: List[str]
    ) -> List[str]:
        """生成事件报告建议"""
        recommendations = []
        
        if incident_type == "stop_loss":
            recommendations.append("检查止损机制是否正常工作")
            recommendations.append("评估是否需要调整止损阈值")
        elif incident_type == "concentration":
            recommendations.append("考虑降低相关行业或股票的持仓")
            recommendations.append("增加组合分散度")
        elif incident_type == "liquidity":
            recommendations.append("关注相关股票的流动性风险")
            recommendations.append("考虑分批交易降低冲击成本")
        
        return recommendations
    
    def _generate_compliance_summary(
        self,
        post_trade_analysis: Optional[PostTradeAnalysis],
        violations: List[Dict[str, Any]]
    ) -> str:
        """生成合规摘要"""
        if violations:
            return f"发现{len(violations)}项违规，需及时处理"
        else:
            return "合规检查通过，未发现违规项"
    
    def _generate_compliance_recommendations(
        self,
        violations: List[Dict[str, Any]]
    ) -> List[str]:
        """生成合规建议"""
        recommendations = []
        
        if violations:
            recommendations.append("及时处理所有违规项")
            recommendations.append("加强日常合规监控")
            recommendations.append("定期审查风控规则的有效性")
        
        return recommendations


class ReportFormatter:
    """报告格式化器"""
    
    @staticmethod
    def to_text(report: RiskReport) -> str:
        """转换为文本格式"""
        lines = [
            "=" * 60,
            report.title,
            "=" * 60,
            "",
            f"报告ID: {report.report_id}",
            f"生成时间: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "【摘要】",
            report.summary,
            ""
        ]
        
        for section_name, section_data in report.sections.items():
            lines.append(f"【{section_name}】")
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    lines.append(f"  {key}: {value}")
            else:
                lines.append(f"  {section_data}")
            lines.append("")
        
        if report.alerts:
            lines.append("【预警详情】")
            for alert in report.alerts[:10]:
                lines.append(f"  [{alert.risk_level.value.upper()}] {alert.message}")
            lines.append("")
        
        if report.recommendations:
            lines.append("【建议】")
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"  {i}. {rec}")
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    @staticmethod
    def to_json(report: RiskReport) -> str:
        """转换为JSON格式"""
        return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    
    @staticmethod
    def to_markdown(report: RiskReport) -> str:
        """转换为Markdown格式"""
        lines = [
            f"# {report.title}",
            "",
            f"> 报告ID: {report.report_id}",
            f"> 生成时间: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 摘要",
            "",
            report.summary,
            ""
        ]
        
        for section_name, section_data in report.sections.items():
            lines.append(f"## {section_name}")
            lines.append("")
            if isinstance(section_data, dict):
                lines.append("| 指标 | 值 |")
                lines.append("|------|------|")
                for key, value in section_data.items():
                    lines.append(f"| {key} | {value} |")
            else:
                lines.append(str(section_data))
            lines.append("")
        
        if report.alerts:
            lines.append("## 预警详情")
            lines.append("")
            for alert in report.alerts[:10]:
                lines.append(f"- **[{alert.risk_level.value.upper()}]** {alert.message}")
            lines.append("")
        
        if report.recommendations:
            lines.append("## 建议")
            lines.append("")
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def to_html(report: RiskReport) -> str:
        """转换为HTML格式"""
        lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{report.title}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; }",
            "h2 { color: #666; border-bottom: 1px solid #ccc; padding-bottom: 5px; }",
            "table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f2f2f2; }",
            ".critical { color: #d32f2f; }",
            ".high { color: #f57c00; }",
            ".medium { color: #fbc02d; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{report.title}</h1>",
            f"<p><strong>报告ID:</strong> {report.report_id}</p>",
            f"<p><strong>生成时间:</strong> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>",
            "<h2>摘要</h2>",
            f"<p>{report.summary}</p>"
        ]
        
        for section_name, section_data in report.sections.items():
            lines.append(f"<h2>{section_name}</h2>")
            if isinstance(section_data, dict):
                lines.append("<table>")
                lines.append("<tr><th>指标</th><th>值</th></tr>")
                for key, value in section_data.items():
                    lines.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
                lines.append("</table>")
            else:
                lines.append(f"<p>{section_data}</p>")
        
        if report.alerts:
            lines.append("<h2>预警详情</h2>")
            lines.append("<ul>")
            for alert in report.alerts[:10]:
                css_class = alert.risk_level.value
                lines.append(f'<li class="{css_class}">[{alert.risk_level.value.upper()}] {alert.message}</li>')
            lines.append("</ul>")
        
        if report.recommendations:
            lines.append("<h2>建议</h2>")
            lines.append("<ol>")
            for rec in report.recommendations:
                lines.append(f"<li>{rec}</li>")
            lines.append("</ol>")
        
        lines.extend([
            "</body>",
            "</html>"
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def format(report: RiskReport, format_type: ReportFormat) -> str:
        """格式化报告"""
        if format_type == ReportFormat.TEXT:
            return ReportFormatter.to_text(report)
        elif format_type == ReportFormat.JSON:
            return ReportFormatter.to_json(report)
        elif format_type == ReportFormat.MARKDOWN:
            return ReportFormatter.to_markdown(report)
        elif format_type == ReportFormat.HTML:
            return ReportFormatter.to_html(report)
        else:
            return ReportFormatter.to_text(report)


def save_report(report: RiskReport, path: str, format_type: ReportFormat = ReportFormat.TEXT):
    """保存报告到文件"""
    content = ReportFormatter.format(report, format_type)
    
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)
