"""
报告生成模块

生成各类运营报告，支持日报、周报、月报、年报。
"""

import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import pandas as pd
import numpy as np

from core.infrastructure.logging import get_logger


class ReportType(Enum):
    """报告类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ANNUAL = "annual"


class ReportFormat(Enum):
    """报告格式"""
    MARKDOWN = "md"
    HTML = "html"
    JSON = "json"


@dataclass
class ReportSection:
    """报告章节"""
    title: str
    content: str
    subsections: List['ReportSection'] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_markdown(self, level: int = 1) -> str:
        """转换为Markdown"""
        lines = [f"{'#' * level} {self.title}", "", self.content]
        
        if self.data:
            lines.append("")
            for key, value in self.data.items():
                lines.append(f"- **{key}**: {value}")
        
        for subsection in self.subsections:
            lines.append("")
            lines.append(subsection.to_markdown(level + 1))
        
        return "\n".join(lines)
    
    def to_html(self) -> str:
        """转换为HTML"""
        html = f"<h2>{self.title}</h2><p>{self.content}</p>"
        
        if self.data:
            html += "<ul>"
            for key, value in self.data.items():
                html += f"<li><strong>{key}</strong>: {value}</li>"
            html += "</ul>"
        
        for subsection in self.subsections:
            html += f"<div class='subsection'>{subsection.to_html()}</div>"
        
        return html


@dataclass
class Report:
    """报告"""
    report_id: str
    report_type: ReportType
    title: str
    date: str
    sections: List[ReportSection] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    
    def to_markdown(self) -> str:
        """转换为Markdown"""
        lines = [
            f"# {self.title}",
            "",
            f"**报告日期**: {self.date}",
            f"**生成时间**: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        for section in self.sections:
            lines.append(section.to_markdown())
            lines.append("")
        
        return "\n".join(lines)
    
    def to_html(self) -> str:
        """转换为HTML"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; margin-top: 20px; }}
        h3 {{ color: #888; }}
        .subsection {{ margin-left: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>{self.title}</h1>
    <p><strong>报告日期</strong>: {self.date}</p>
    <p><strong>生成时间</strong>: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
"""
        
        for section in self.sections:
            html += section.to_html()
        
        html += "</body></html>"
        return html
    
    def to_json(self) -> str:
        """转换为JSON"""
        data = {
            "report_id": self.report_id,
            "report_type": self.report_type.value,
            "title": self.title,
            "date": self.date,
            "generated_at": self.generated_at.isoformat(),
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "data": s.data,
                    "subsections": [
                        {"title": ss.title, "content": ss.content, "data": ss.data}
                        for ss in s.subsections
                    ]
                }
                for s in self.sections
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


class ReportGenerator:
    """报告生成器"""
    
    def __init__(
        self,
        generator_id: str = "main",
        storage_path: str = "./data/reports"
    ):
        self.generator_id = generator_id
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("monitor.report")
        
        for report_type in ReportType:
            (self.storage_path / report_type.value).mkdir(parents=True, exist_ok=True)
    
    def generate_daily_report(
        self,
        target_date: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Report:
        """生成日报"""
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        report_id = f"DAILY-{date_str}"
        
        sections = [
            self._create_market_section(data),
            self._create_portfolio_section(data),
            self._create_trading_section(data),
            self._create_factor_section(data),
            self._create_risk_section(data),
            self._create_plan_section(data)
        ]
        
        report = Report(
            report_id=report_id,
            report_type=ReportType.DAILY,
            title=f"日报 - {date_str}",
            date=date_str,
            sections=[s for s in sections if s]
        )
        
        self._save_report(report)
        return report
    
    def generate_weekly_report(
        self,
        target_date: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Report:
        """生成周报"""
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        report_id = f"WEEKLY-{date_str}"
        
        sections = [
            self._create_weekly_performance_section(data),
            self._create_weekly_factor_section(data),
            self._create_weekly_risk_section(data),
            self._create_weekly_attribution_section(data),
            self._create_next_week_plan_section(data)
        ]
        
        report = Report(
            report_id=report_id,
            report_type=ReportType.WEEKLY,
            title=f"周报 - {date_str}",
            date=date_str,
            sections=[s for s in sections if s]
        )
        
        self._save_report(report)
        return report
    
    def generate_monthly_report(
        self,
        target_date: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Report:
        """生成月报"""
        date_str = target_date or datetime.now().strftime("%Y-%m")
        report_id = f"MONTHLY-{date_str}"
        
        sections = [
            self._create_monthly_performance_section(data),
            self._create_monthly_factor_section(data),
            self._create_monthly_strategy_section(data),
            self._create_monthly_risk_section(data),
            self._create_next_month_plan_section(data)
        ]
        
        report = Report(
            report_id=report_id,
            report_type=ReportType.MONTHLY,
            title=f"月报 - {date_str}",
            date=date_str,
            sections=[s for s in sections if s]
        )
        
        self._save_report(report)
        return report
    
    def generate_annual_report(
        self,
        year: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Report:
        """生成年报"""
        year_str = str(year or datetime.now().year)
        report_id = f"ANNUAL-{year_str}"
        
        sections = [
            self._create_annual_performance_section(data),
            self._create_annual_attribution_section(data),
            self._create_annual_risk_section(data),
            self._create_annual_strategy_section(data),
            self._create_next_year_plan_section(data)
        ]
        
        report = Report(
            report_id=report_id,
            report_type=ReportType.ANNUAL,
            title=f"年报 - {year_str}",
            date=year_str,
            sections=[s for s in sections if s]
        )
        
        self._save_report(report)
        return report
    
    def _create_market_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建市场概况章节"""
        if not data or "market" not in data:
            return ReportSection(
                title="市场概况",
                content="暂无市场数据",
                data={"状态": "数据缺失"}
            )
        
        market = data["market"]
        return ReportSection(
            title="市场概况",
            content="今日市场表现：",
            data={
                "上证指数": f"{market.get('sh_index', 'N/A'):.2f}" if isinstance(market.get('sh_index'), (int, float)) else "N/A",
                "深证成指": f"{market.get('sz_index', 'N/A'):.2f}" if isinstance(market.get('sz_index'), (int, float)) else "N/A",
                "创业板指": f"{market.get('cyb_index', 'N/A'):.2f}" if isinstance(market.get('cyb_index'), (int, float)) else "N/A",
                "成交量": f"{market.get('volume', 'N/A'):.2f}亿" if isinstance(market.get('volume'), (int, float)) else "N/A",
                "涨跌比": market.get('up_down_ratio', 'N/A')
            }
        )
    
    def _create_portfolio_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建组合表现章节"""
        if not data or "portfolio" not in data:
            return ReportSection(
                title="组合表现",
                content="暂无组合数据"
            )
        
        portfolio = data["portfolio"]
        return ReportSection(
            title="组合表现",
            content="今日组合表现：",
            data={
                "总资产": f"{portfolio.get('total_value', 0):,.2f}",
                "日收益率": f"{portfolio.get('daily_return', 0):.2%}",
                "累计收益率": f"{portfolio.get('cumulative_return', 0):.2%}",
                "持仓数量": portfolio.get('position_count', 0)
            }
        )
    
    def _create_trading_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建交易记录章节"""
        if not data or "trading" not in data:
            return ReportSection(
                title="交易记录",
                content="暂无交易数据"
            )
        
        trading = data["trading"]
        return ReportSection(
            title="交易记录",
            content="今日交易情况：",
            data={
                "委托数量": trading.get('order_count', 0),
                "成交数量": trading.get('filled_count', 0),
                "成交率": f"{trading.get('fill_rate', 0):.2%}",
                "交易成本": f"{trading.get('total_cost', 0):,.2f}"
            }
        )
    
    def _create_factor_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建因子表现章节"""
        if not data or "factors" not in data:
            return ReportSection(
                title="因子表现",
                content="暂无因子数据"
            )
        
        factors = data["factors"]
        subsections = []
        
        for factor in factors[:5]:
            subsections.append(ReportSection(
                title=factor.get('name', 'Unknown'),
                content="",
                data={
                    "IC": f"{factor.get('ic', 0):.4f}",
                    "评分": f"{factor.get('score', 0):.2f}",
                    "状态": factor.get('status', 'normal')
                }
            ))
        
        return ReportSection(
            title="因子表现",
            content="主要因子表现：",
            subsections=subsections
        )
    
    def _create_risk_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建风险监控章节"""
        if not data or "risk" not in data:
            return ReportSection(
                title="风险监控",
                content="暂无风险数据"
            )
        
        risk = data["risk"]
        return ReportSection(
            title="风险监控",
            content="风险指标监控：",
            data={
                "最大回撤": f"{risk.get('max_drawdown', 0):.2%}",
                "波动率": f"{risk.get('volatility', 0):.2%}",
                "夏普比率": f"{risk.get('sharpe', 0):.2f}",
                "风险状态": risk.get('status', 'normal')
            }
        )
    
    def _create_plan_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建明日计划章节"""
        plans = data.get("plans", []) if data else []
        
        content = "明日计划：\n"
        if plans:
            for i, plan in enumerate(plans, 1):
                content += f"{i}. {plan}\n"
        else:
            content += "- 继续执行当前策略\n- 监控市场变化\n- 检查持仓风险"
        
        return ReportSection(
            title="明日计划",
            content=content
        )
    
    def _create_weekly_performance_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建周度收益汇总章节"""
        if not data or "performance" not in data:
            return ReportSection(
                title="周度收益汇总",
                content="暂无周度数据"
            )
        
        perf = data["performance"]
        return ReportSection(
            title="周度收益汇总",
            content="本周表现：",
            data={
                "周收益率": f"{perf.get('weekly_return', 0):.2%}",
                "周胜率": f"{perf.get('win_rate', 0):.2%}",
                "周最大回撤": f"{perf.get('max_drawdown', 0):.2%}",
                "周换手率": f"{perf.get('turnover', 0):.2%}"
            }
        )
    
    def _create_weekly_factor_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建周度因子表现章节"""
        return ReportSection(
            title="周度因子表现",
            content="本周因子表现汇总"
        )
    
    def _create_weekly_risk_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建周度风险分析章节"""
        return ReportSection(
            title="周度风险分析",
            content="本周风险分析"
        )
    
    def _create_weekly_attribution_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建周度归因分析章节"""
        return ReportSection(
            title="周度归因分析",
            content="本周收益归因分析"
        )
    
    def _create_next_week_plan_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建下周计划章节"""
        return ReportSection(
            title="下周计划",
            content="下周计划：\n- 继续监控因子表现\n- 优化策略参数\n- 控制组合风险"
        )
    
    def _create_monthly_performance_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建月度绩效总结章节"""
        if not data or "performance" not in data:
            return ReportSection(
                title="月度绩效总结",
                content="暂无月度数据"
            )
        
        perf = data["performance"]
        return ReportSection(
            title="月度绩效总结",
            content="本月表现：",
            data={
                "月收益率": f"{perf.get('monthly_return', 0):.2%}",
                "月夏普比率": f"{perf.get('sharpe', 0):.2f}",
                "月最大回撤": f"{perf.get('max_drawdown', 0):.2%}",
                "月交易天数": perf.get('trading_days', 0)
            }
        )
    
    def _create_monthly_factor_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建月度因子评估章节"""
        return ReportSection(
            title="月度因子评估",
            content="本月因子表现评估"
        )
    
    def _create_monthly_strategy_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建月度策略评估章节"""
        return ReportSection(
            title="月度策略评估",
            content="本月策略表现评估"
        )
    
    def _create_monthly_risk_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建月度风险报告章节"""
        return ReportSection(
            title="月度风险报告",
            content="本月风险分析报告"
        )
    
    def _create_next_month_plan_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建下月计划章节"""
        return ReportSection(
            title="下月计划",
            content="下月计划：\n- 评估因子表现\n- 优化策略配置\n- 完善风控体系"
        )
    
    def _create_annual_performance_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建年度绩效总结章节"""
        return ReportSection(
            title="年度绩效总结",
            content="本年度绩效总结"
        )
    
    def _create_annual_attribution_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建年度归因分析章节"""
        return ReportSection(
            title="年度归因分析",
            content="本年度收益归因分析"
        )
    
    def _create_annual_risk_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建年度风险回顾章节"""
        return ReportSection(
            title="年度风险回顾",
            content="本年度风险回顾"
        )
    
    def _create_annual_strategy_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建年度策略回顾章节"""
        return ReportSection(
            title="年度策略回顾",
            content="本年度策略回顾"
        )
    
    def _create_next_year_plan_section(self, data: Optional[Dict[str, Any]]) -> Optional[ReportSection]:
        """创建下年度计划章节"""
        return ReportSection(
            title="下年度计划",
            content="下年度计划：\n- 优化投资策略\n- 完善风控体系\n- 提升系统稳定性"
        )
    
    def _save_report(self, report: Report, format: ReportFormat = ReportFormat.MARKDOWN):
        """保存报告"""
        report_dir = self.storage_path / report.report_type.value
        report_dir.mkdir(parents=True, exist_ok=True)
        
        if format == ReportFormat.MARKDOWN:
            file_path = report_dir / f"{report.report_id}.md"
            content = report.to_markdown()
        elif format == ReportFormat.HTML:
            file_path = report_dir / f"{report.report_id}.html"
            content = report.to_html()
        else:
            file_path = report_dir / f"{report.report_id}.json"
            content = report.to_json()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.logger.info(f"保存报告: {report.report_id} -> {file_path}")
    
    def load_report(self, report_id: str, report_type: ReportType) -> Optional[Report]:
        """加载报告"""
        report_dir = self.storage_path / report_type.value
        
        for ext in ['.md', '.json', '.html']:
            file_path = report_dir / f"{report_id}{ext}"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.logger.info(f"加载报告: {report_id}")
                return Report(
                    report_id=report_id,
                    report_type=report_type,
                    title=report_id,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    sections=[ReportSection(title="内容", content=content)]
                )
        
        return None
    
    def list_reports(self, report_type: ReportType) -> List[str]:
        """列出报告"""
        report_dir = self.storage_path / report_type.value
        
        if not report_dir.exists():
            return []
        
        reports = []
        for f in report_dir.glob("*"):
            if f.is_file():
                reports.append(f.stem)
        
        return sorted(reports, reverse=True)
    
    def delete_report(self, report_id: str, report_type: ReportType) -> bool:
        """删除报告"""
        report_dir = self.storage_path / report_type.value
        
        for ext in ['.md', '.json', '.html']:
            file_path = report_dir / f"{report_id}{ext}"
            if file_path.exists():
                file_path.unlink()
                self.logger.info(f"删除报告: {report_id}")
                return True
        
        return False
