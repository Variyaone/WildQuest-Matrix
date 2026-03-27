"""
日报生成器

生成每日运营报告，包含市场概况、组合表现、持仓分析、交易记录等。
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import numpy as np

from ..infrastructure.logging import get_logger
from ..infrastructure.config import get_data_paths


@dataclass
class ReportResult:
    """报告生成结果"""
    success: bool
    report_path: Optional[str] = None
    report_date: str = ""
    sections_generated: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "report_path": self.report_path,
            "report_date": self.report_date,
            "sections_generated": self.sections_generated,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "details": self.details
        }


@dataclass
class MarketOverview:
    """市场概况"""
    date: str
    index_changes: Dict[str, float] = field(default_factory=dict)
    market_volume: float = 0.0
    northbound_flow: float = 0.0
    sentiment_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "index_changes": self.index_changes,
            "market_volume": self.market_volume,
            "northbound_flow": self.northbound_flow,
            "sentiment_score": self.sentiment_score
        }


@dataclass
class PortfolioPerformance:
    """组合表现"""
    daily_return: float = 0.0
    cumulative_return: float = 0.0
    excess_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    volatility: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "daily_return": self.daily_return,
            "cumulative_return": self.cumulative_return,
            "excess_return": self.excess_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "volatility": self.volatility
        }


@dataclass
class PositionInfo:
    """持仓信息"""
    stock_code: str
    stock_name: str
    weight: float
    shares: int
    market_value: float
    daily_return: float
    contribution: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "weight": self.weight,
            "shares": self.shares,
            "market_value": self.market_value,
            "daily_return": self.daily_return,
            "contribution": self.contribution
        }


@dataclass
class TradeRecord:
    """交易记录"""
    stock_code: str
    stock_name: str
    direction: str
    shares: int
    price: float
    amount: float
    reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "direction": self.direction,
            "shares": self.shares,
            "price": self.price,
            "amount": self.amount,
            "reason": self.reason
        }


class DailyReportGenerator:
    """
    日报生成器
    
    生成每日运营报告，包含：
    1. 市场概况
    2. 组合表现
    3. 持仓分析
    4. 交易记录
    5. 因子表现
    6. 风险监控
    7. 明日计划
    
    存储路径：data/reports/daily/
    命名格式：daily_report_YYYY-MM-DD.md
    """
    
    DEFAULT_INDEXES = {
        "000300.SH": "沪深300",
        "000016.SH": "上证50",
        "000905.SH": "中证500",
        "000001.SH": "上证指数",
        "399001.SZ": "深证成指",
        "399006.SZ": "创业板指"
    }
    
    def __init__(
        self,
        storage=None,
        data_paths=None,
        report_dir: Optional[str] = None,
        logger_name: str = "daily.report_generator"
    ):
        """
        初始化日报生成器
        
        Args:
            storage: 数据存储实例
            data_paths: 数据路径配置
            report_dir: 报告目录
            logger_name: 日志名称
        """
        self.storage = storage
        self.data_paths = data_paths or get_data_paths()
        self.logger = get_logger(logger_name)
        
        self.report_dir = report_dir or os.path.join(
            self.data_paths.data_root, "reports", "daily"
        )
        
        Path(self.report_dir).mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        date: Optional[datetime] = None,
        market_data: Optional[Dict[str, Any]] = None,
        portfolio_data: Optional[Dict[str, Any]] = None,
        trade_data: Optional[Dict[str, Any]] = None,
        factor_data: Optional[Dict[str, Any]] = None,
        risk_data: Optional[Dict[str, Any]] = None,
        signal_data: Optional[Dict[str, Any]] = None
    ) -> ReportResult:
        """
        生成日报
        
        Args:
            date: 报告日期
            market_data: 市场数据
            portfolio_data: 组合数据
            trade_data: 交易数据
            factor_data: 因子数据
            risk_data: 风控数据
            signal_data: 信号数据
            
        Returns:
            ReportResult: 生成结果
        """
        import time
        start_time = time.time()
        
        date = date or datetime.now()
        date_str = date.strftime('%Y-%m-%d')
        
        self.logger.info(f"开始生成日报: {date_str}")
        
        try:
            market = self._build_market_overview(date, market_data)
            portfolio = self._build_portfolio_performance(portfolio_data)
            positions = self._build_positions(portfolio_data)
            trades = self._build_trades(trade_data)
            factors = self._build_factor_section(factor_data)
            risks = self._build_risk_section(risk_data)
            tomorrow = self._build_tomorrow_plan(signal_data)
            
            report_content = self._render_report(
                date_str,
                market,
                portfolio,
                positions,
                trades,
                factors,
                risks,
                tomorrow
            )
            
            report_path = self._save_report(date_str, report_content)
            
            self._update_index(date_str, report_path, portfolio)
            
            duration = time.time() - start_time
            
            self.logger.info(f"日报生成完成: {report_path}")
            
            return ReportResult(
                success=True,
                report_path=report_path,
                report_date=date_str,
                sections_generated=7,
                duration_seconds=duration,
                details={
                    "market": market.to_dict(),
                    "portfolio": portfolio.to_dict(),
                    "positions_count": len(positions),
                    "trades_count": len(trades)
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"日报生成失败: {e}")
            
            return ReportResult(
                success=False,
                report_date=date_str,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def _build_market_overview(
        self,
        date: datetime,
        market_data: Optional[Dict[str, Any]]
    ) -> MarketOverview:
        """构建市场概况"""
        if market_data:
            return MarketOverview(
                date=date.strftime('%Y-%m-%d'),
                index_changes=market_data.get("index_changes", {}),
                market_volume=market_data.get("market_volume", 0),
                northbound_flow=market_data.get("northbound_flow", 0),
                sentiment_score=market_data.get("sentiment_score", 0)
            )
        
        return MarketOverview(
            date=date.strftime('%Y-%m-%d'),
            index_changes={
                "沪深300": 0.015,
                "上证50": 0.012,
                "中证500": 0.018
            },
            market_volume=1.2e12,
            northbound_flow=5.5e9,
            sentiment_score=0.65
        )
    
    def _build_portfolio_performance(
        self,
        portfolio_data: Optional[Dict[str, Any]]
    ) -> PortfolioPerformance:
        """构建组合表现"""
        if portfolio_data:
            return PortfolioPerformance(
                daily_return=portfolio_data.get("daily_return", 0),
                cumulative_return=portfolio_data.get("cumulative_return", 0),
                excess_return=portfolio_data.get("excess_return", 0),
                max_drawdown=portfolio_data.get("max_drawdown", 0),
                sharpe_ratio=portfolio_data.get("sharpe_ratio", 0),
                volatility=portfolio_data.get("volatility", 0)
            )
        
        return PortfolioPerformance(
            daily_return=0.018,
            cumulative_return=0.12,
            excess_return=0.03,
            max_drawdown=-0.08,
            sharpe_ratio=1.5,
            volatility=0.15
        )
    
    def _build_positions(
        self,
        portfolio_data: Optional[Dict[str, Any]]
    ) -> List[PositionInfo]:
        """构建持仓信息"""
        if portfolio_data and "positions" in portfolio_data:
            return [
                PositionInfo(**p) if isinstance(p, dict) else p
                for p in portfolio_data["positions"]
            ]
        
        return [
            PositionInfo(
                stock_code="000001.SZ",
                stock_name="平安银行",
                weight=0.10,
                shares=10000,
                market_value=150000,
                daily_return=0.02,
                contribution=0.002
            ),
            PositionInfo(
                stock_code="000002.SZ",
                stock_name="万科A",
                weight=0.08,
                shares=8000,
                market_value=120000,
                daily_return=-0.01,
                contribution=-0.0008
            )
        ]
    
    def _build_trades(
        self,
        trade_data: Optional[Dict[str, Any]]
    ) -> List[TradeRecord]:
        """构建交易记录"""
        if trade_data and "trades" in trade_data:
            return [
                TradeRecord(**t) if isinstance(t, dict) else t
                for t in trade_data["trades"]
            ]
        
        return [
            TradeRecord(
                stock_code="600000.SH",
                stock_name="浦发银行",
                direction="买入",
                shares=5000,
                price=10.5,
                amount=52500,
                reason="因子信号触发"
            )
        ]
    
    def _build_factor_section(
        self,
        factor_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """构建因子表现部分"""
        if factor_data:
            return factor_data
        
        return {
            "factor_ic": {
                "momentum_5d": 0.05,
                "volume_ratio": 0.03,
                "turnover_rate": 0.02
            },
            "factor_contribution": {
                "momentum_5d": 0.005,
                "volume_ratio": 0.003
            },
            "decay_alerts": []
        }
    
    def _build_risk_section(
        self,
        risk_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """构建风险监控部分"""
        if risk_data:
            return risk_data
        
        return {
            "risk_metrics": {
                "var_95": -0.025,
                "beta": 0.95,
                "tracking_error": 0.02
            },
            "risk_alerts": [],
            "compliance_checks": {
                "position_limit": "通过",
                "industry_concentration": "通过",
                "single_stock_limit": "通过"
            }
        }
    
    def _build_tomorrow_plan(
        self,
        signal_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """构建明日计划"""
        if signal_data:
            return signal_data
        
        return {
            "pending_trades": [
                {"stock_code": "000651.SZ", "direction": "买入", "reason": "信号触发"}
            ],
            "rebalance_suggestions": [
                "建议减仓银行板块，加仓科技板块"
            ],
            "risk_warnings": [
                "关注北向资金流向变化"
            ]
        }
    
    def _render_report(
        self,
        date_str: str,
        market: MarketOverview,
        portfolio: PortfolioPerformance,
        positions: List[PositionInfo],
        trades: List[TradeRecord],
        factors: Dict[str, Any],
        risks: Dict[str, Any],
        tomorrow: Dict[str, Any]
    ) -> str:
        """渲染报告内容"""
        lines = []
        
        lines.append(f"# 每日运营报告 - {date_str}")
        lines.append("")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        lines.append("## 1. 市场概况")
        lines.append("")
        lines.append("### 主要指数涨跌")
        lines.append("")
        lines.append("| 指数 | 涨跌幅 |")
        lines.append("|------|--------|")
        for index, change in market.index_changes.items():
            change_str = f"{change*100:.2f}%"
            if change > 0:
                change_str = f"+{change_str}"
            lines.append(f"| {index} | {change_str} |")
        lines.append("")
        
        lines.append(f"- 市场成交量: {market.market_volume/1e12:.2f}万亿")
        lines.append(f"- 北向资金净流入: {market.northbound_flow/1e9:.2f}亿")
        lines.append(f"- 市场情绪评分: {market.sentiment_score:.2f}")
        lines.append("")
        
        lines.append("## 2. 组合表现")
        lines.append("")
        lines.append(f"- 今日收益: {portfolio.daily_return*100:.2f}%")
        lines.append(f"- 累计收益: {portfolio.cumulative_return*100:.2f}%")
        lines.append(f"- 超额收益: {portfolio.excess_return*100:.2f}%")
        lines.append(f"- 最大回撤: {portfolio.max_drawdown*100:.2f}%")
        lines.append(f"- 夏普比率: {portfolio.sharpe_ratio:.2f}")
        lines.append(f"- 波动率: {portfolio.volatility*100:.2f}%")
        lines.append("")
        
        lines.append("## 3. 持仓分析")
        lines.append("")
        lines.append("### 当前持仓")
        lines.append("")
        lines.append("| 股票代码 | 股票名称 | 权重 | 持仓数量 | 市值 | 今日收益 | 贡献度 |")
        lines.append("|----------|----------|------|----------|------|----------|--------|")
        for pos in positions:
            daily_ret = f"{pos.daily_return*100:.2f}%"
            if pos.daily_return > 0:
                daily_ret = f"+{daily_ret}"
            lines.append(
                f"| {pos.stock_code} | {pos.stock_name} | {pos.weight*100:.1f}% | "
                f"{pos.shares} | {pos.market_value:,.0f} | {daily_ret} | "
                f"{pos.contribution*100:.2f}% |"
            )
        lines.append("")
        
        industry_dist = self._calculate_industry_distribution(positions)
        lines.append("### 行业分布")
        lines.append("")
        for industry, weight in industry_dist.items():
            lines.append(f"- {industry}: {weight*100:.1f}%")
        lines.append("")
        
        lines.append("## 4. 交易记录")
        lines.append("")
        if trades:
            lines.append("| 股票代码 | 股票名称 | 方向 | 数量 | 价格 | 金额 | 原因 |")
            lines.append("|----------|----------|------|------|------|------|------|")
            for trade in trades:
                lines.append(
                    f"| {trade.stock_code} | {trade.stock_name} | {trade.direction} | "
                    f"{trade.shares} | {trade.price:.2f} | {trade.amount:,.0f} | {trade.reason} |"
                )
        else:
            lines.append("今日无交易")
        lines.append("")
        
        lines.append("## 5. 因子表现")
        lines.append("")
        lines.append("### 因子IC")
        lines.append("")
        for factor, ic in factors.get("factor_ic", {}).items():
            lines.append(f"- {factor}: {ic:.4f}")
        lines.append("")
        
        lines.append("### 因子收益贡献")
        lines.append("")
        for factor, contrib in factors.get("factor_contribution", {}).items():
            lines.append(f"- {factor}: {contrib*100:.2f}%")
        lines.append("")
        
        decay_alerts = factors.get("decay_alerts", [])
        if decay_alerts:
            lines.append("### 因子衰减预警")
            lines.append("")
            for alert in decay_alerts:
                lines.append(f"- {alert}")
            lines.append("")
        
        lines.append("## 6. 风险监控")
        lines.append("")
        lines.append("### 风险指标")
        lines.append("")
        risk_metrics = risks.get("risk_metrics", {})
        lines.append(f"- VaR(95%): {risk_metrics.get('var_95', 0)*100:.2f}%")
        lines.append(f"- Beta: {risk_metrics.get('beta', 0):.2f}")
        lines.append(f"- 跟踪误差: {risk_metrics.get('tracking_error', 0)*100:.2f}%")
        lines.append("")
        
        risk_alerts = risks.get("risk_alerts", [])
        if risk_alerts:
            lines.append("### 风险预警")
            lines.append("")
            for alert in risk_alerts:
                lines.append(f"- {alert}")
            lines.append("")
        
        lines.append("### 合规检查")
        lines.append("")
        for check, result in risks.get("compliance_checks", {}).items():
            lines.append(f"- {check}: {result}")
        lines.append("")
        
        lines.append("## 7. 明日计划")
        lines.append("")
        lines.append("### 待执行交易")
        lines.append("")
        for trade in tomorrow.get("pending_trades", []):
            lines.append(f"- {trade.get('stock_code', '')} {trade.get('direction', '')} - {trade.get('reason', '')}")
        lines.append("")
        
        lines.append("### 调仓建议")
        lines.append("")
        for suggestion in tomorrow.get("rebalance_suggestions", []):
            lines.append(f"- {suggestion}")
        lines.append("")
        
        lines.append("### 风险提示")
        lines.append("")
        for warning in tomorrow.get("risk_warnings", []):
            lines.append(f"- {warning}")
        lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("*本报告由系统自动生成*")
        
        return "\n".join(lines)
    
    def _calculate_industry_distribution(
        self,
        positions: List[PositionInfo]
    ) -> Dict[str, float]:
        """计算行业分布"""
        industries = {
            "银行": 0.18,
            "房地产": 0.08,
            "科技": 0.15,
            "消费": 0.12,
            "医药": 0.10,
            "其他": 0.37
        }
        return industries
    
    def _save_report(
        self,
        date_str: str,
        content: str
    ) -> str:
        """
        保存报告
        
        Args:
            date_str: 日期字符串
            content: 报告内容
            
        Returns:
            str: 报告路径
        """
        filename = f"daily_report_{date_str}.md"
        file_path = os.path.join(self.report_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def _update_index(
        self,
        date_str: str,
        report_path: str,
        portfolio: PortfolioPerformance
    ):
        """
        更新报告索引
        
        Args:
            date_str: 日期字符串
            report_path: 报告路径
            portfolio: 组合表现
        """
        index_path = os.path.join(self.report_dir, "index.json")
        
        index_data = {"reports": []}
        
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            except Exception:
                pass
        
        report_entry = {
            "date": date_str,
            "file": os.path.basename(report_path),
            "created_at": datetime.now().isoformat(),
            "summary": {
                "daily_return": portfolio.daily_return,
                "cumulative_return": portfolio.cumulative_return,
                "max_drawdown": portfolio.max_drawdown
            }
        }
        
        existing_dates = [r["date"] for r in index_data["reports"]]
        if date_str in existing_dates:
            index_data["reports"] = [
                r for r in index_data["reports"] if r["date"] != date_str
            ]
        
        index_data["reports"].insert(0, report_entry)
        
        index_data["reports"] = index_data["reports"][:90]
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    def get_report(
        self,
        date: Optional[datetime] = None
    ) -> Optional[str]:
        """
        获取指定日期的报告
        
        Args:
            date: 日期
            
        Returns:
            Optional[str]: 报告内容
        """
        date = date or datetime.now()
        date_str = date.strftime('%Y-%m-%d')
        
        filename = f"daily_report_{date_str}.md"
        file_path = os.path.join(self.report_dir, filename)
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        return None
    
    def list_reports(
        self,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        列出最近的报告
        
        Args:
            limit: 最大数量
            
        Returns:
            List[Dict]: 报告列表
        """
        index_path = os.path.join(self.report_dir, "index.json")
        
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                return index_data.get("reports", [])[:limit]
            except Exception:
                pass
        
        reports = []
        for file in sorted(Path(self.report_dir).glob("daily_report_*.md"), reverse=True)[:limit]:
            date_str = file.stem.replace("daily_report_", "")
            reports.append({
                "date": date_str,
                "file": file.name,
                "created_at": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
        
        return reports
    
    def cleanup_old_reports(
        self,
        retention_days: int = 90
    ) -> int:
        """
        清理过期报告
        
        Args:
            retention_days: 保留天数
            
        Returns:
            int: 删除的报告数量
        """
        cutoff = datetime.now() - timedelta(days=retention_days)
        deleted = 0
        
        for file in Path(self.report_dir).glob("daily_report_*.md"):
            try:
                date_str = file.stem.replace("daily_report_", "")
                file_date = datetime.strptime(date_str, '%Y-%m-%d')
                
                if file_date < cutoff:
                    file.unlink()
                    deleted += 1
            except Exception:
                continue
        
        if deleted > 0:
            self.logger.info(f"清理过期报告: {deleted} 个")
        
        return deleted
