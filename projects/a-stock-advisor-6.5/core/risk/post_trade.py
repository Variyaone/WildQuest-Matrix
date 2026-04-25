"""
事后风控模块

交易后分析和归因，包括：
- 绩效归因分析
- 风险分解分析
- 回撤分析
- 合规检查
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from enum import Enum

from .limits import RiskLimits, get_risk_limits, RiskLevel
from .metrics import RiskMetricsCalculator, RiskMetricsResult


class AttributionType(Enum):
    """归因类型"""
    INDUSTRY = "industry"
    FACTOR = "factor"
    STOCK = "stock"
    TIMING = "timing"


@dataclass
class TradeRecord:
    """交易记录"""
    trade_id: str
    stock_code: str
    stock_name: str
    direction: str
    quantity: int
    price: float
    amount: float
    commission: float
    slippage: float
    trade_time: datetime
    strategy: str = ""
    signal: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trade_id": self.trade_id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "direction": self.direction,
            "quantity": self.quantity,
            "price": self.price,
            "amount": self.amount,
            "commission": self.commission,
            "slippage": self.slippage,
            "trade_time": self.trade_time.isoformat(),
            "strategy": self.strategy,
            "signal": self.signal
        }


@dataclass
class PositionRecord:
    """持仓记录"""
    stock_code: str
    stock_name: str
    quantity: int
    cost_price: float
    market_value: float
    weight: float
    pnl: float
    pnl_ratio: float
    holding_days: int
    industry: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "quantity": self.quantity,
            "cost_price": self.cost_price,
            "market_value": self.market_value,
            "weight": self.weight,
            "pnl": self.pnl,
            "pnl_ratio": self.pnl_ratio,
            "holding_days": self.holding_days,
            "industry": self.industry
        }


@dataclass
class AttributionResult:
    """归因分析结果"""
    attribution_type: AttributionType
    factor_name: str
    contribution: float
    contribution_ratio: float
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "attribution_type": self.attribution_type.value,
            "factor_name": self.factor_name,
            "contribution": self.contribution,
            "contribution_ratio": self.contribution_ratio,
            "details": self.details
        }


@dataclass
class DrawdownAnalysis:
    """回撤分析结果"""
    max_drawdown: float
    max_drawdown_start: datetime
    max_drawdown_end: datetime
    max_drawdown_duration: int
    current_drawdown: float
    drawdown_periods: List[Dict[str, Any]] = field(default_factory=list)
    recovery_times: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "max_drawdown": self.max_drawdown,
            "max_drawdown_start": self.max_drawdown_start.isoformat(),
            "max_drawdown_end": self.max_drawdown_end.isoformat(),
            "max_drawdown_duration": self.max_drawdown_duration,
            "current_drawdown": self.current_drawdown,
            "drawdown_periods": self.drawdown_periods,
            "recovery_times": self.recovery_times
        }


@dataclass
class ComplianceCheckResult:
    """合规检查结果"""
    check_id: str
    check_name: str
    passed: bool
    violations: List[Dict[str, Any]] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "check_id": self.check_id,
            "check_name": self.check_name,
            "passed": self.passed,
            "violations": self.violations,
            "checked_at": self.checked_at.isoformat()
        }


@dataclass
class PostTradeAnalysis:
    """事后分析结果"""
    analysis_id: str
    analysis_date: date
    period_start: date
    period_end: date
    total_return: float
    benchmark_return: float
    excess_return: float
    risk_metrics: Optional[RiskMetricsResult] = None
    attributions: List[AttributionResult] = field(default_factory=list)
    drawdown_analysis: Optional[DrawdownAnalysis] = None
    compliance_results: List[ComplianceCheckResult] = field(default_factory=list)
    trade_statistics: Dict[str, Any] = field(default_factory=dict)
    position_analysis: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "analysis_id": self.analysis_id,
            "analysis_date": self.analysis_date.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_return": self.total_return,
            "benchmark_return": self.benchmark_return,
            "excess_return": self.excess_return,
            "risk_metrics": self.risk_metrics.to_dict() if self.risk_metrics else None,
            "attributions": [a.to_dict() for a in self.attributions],
            "drawdown_analysis": self.drawdown_analysis.to_dict() if self.drawdown_analysis else None,
            "compliance_results": [c.to_dict() for c in self.compliance_results],
            "trade_statistics": self.trade_statistics,
            "position_analysis": self.position_analysis,
            "created_at": self.created_at.isoformat()
        }


class PostTradeAnalyzer:
    """
    事后风控分析器
    
    执行交易后的分析和归因。
    """
    
    def __init__(
        self,
        risk_limits: Optional[RiskLimits] = None,
        metrics_calculator: Optional[RiskMetricsCalculator] = None
    ):
        self.risk_limits = risk_limits or get_risk_limits()
        self.metrics_calculator = metrics_calculator or RiskMetricsCalculator()
        self._analysis_counter = 0
    
    def analyze(
        self,
        nav_series: np.ndarray,
        returns: np.ndarray,
        benchmark_returns: Optional[np.ndarray] = None,
        positions: Optional[Dict[str, PositionRecord]] = None,
        trades: Optional[List[TradeRecord]] = None,
        industry_mapping: Optional[Dict[str, str]] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ) -> PostTradeAnalysis:
        """
        执行事后分析
        
        Args:
            nav_series: 净值序列
            returns: 收益率序列
            benchmark_returns: 基准收益率序列
            positions: 持仓记录
            trades: 交易记录
            industry_mapping: 行业映射
            period_start: 分析期开始
            period_end: 分析期结束
            
        Returns:
            PostTradeAnalysis: 分析结果
        """
        self._analysis_counter += 1
        analysis_id = f"PTA-{datetime.now().strftime('%Y%m%d')}-{self._analysis_counter:04d}"
        
        today = date.today()
        period_start = period_start or today - timedelta(days=30)
        period_end = period_end or today
        
        total_return = (nav_series[-1] / nav_series[0] - 1) if len(nav_series) > 0 else 0
        benchmark_return = (np.prod(1 + benchmark_returns) - 1) if benchmark_returns is not None and len(benchmark_returns) > 0 else 0
        excess_return = total_return - benchmark_return
        
        risk_metrics = self.metrics_calculator.calculate_all_metrics(
            returns, nav_series, benchmark_returns
        )
        
        attributions = self._calculate_attribution(
            returns, benchmark_returns, positions, industry_mapping
        )
        
        drawdown_analysis = self._analyze_drawdowns(nav_series)
        
        compliance_results = self._check_compliance(positions, trades)
        
        trade_statistics = self._calculate_trade_statistics(trades) if trades else {}
        
        position_analysis = self._analyze_positions(positions) if positions else {}
        
        return PostTradeAnalysis(
            analysis_id=analysis_id,
            analysis_date=today,
            period_start=period_start,
            period_end=period_end,
            total_return=total_return,
            benchmark_return=benchmark_return,
            excess_return=excess_return,
            risk_metrics=risk_metrics,
            attributions=attributions,
            drawdown_analysis=drawdown_analysis,
            compliance_results=compliance_results,
            trade_statistics=trade_statistics,
            position_analysis=position_analysis
        )
    
    def _calculate_attribution(
        self,
        returns: np.ndarray,
        benchmark_returns: Optional[np.ndarray],
        positions: Optional[Dict[str, PositionRecord]],
        industry_mapping: Optional[Dict[str, str]]
    ) -> List[AttributionResult]:
        """计算归因分析"""
        attributions = []
        
        if positions and industry_mapping:
            industry_contributions = {}
            for stock_code, pos in positions.items():
                industry = industry_mapping.get(stock_code, "Unknown")
                if industry not in industry_contributions:
                    industry_contributions[industry] = 0
                industry_contributions[industry] += pos.pnl
            
            total_pnl = sum(industry_contributions.values())
            for industry, contribution in industry_contributions.items():
                attributions.append(AttributionResult(
                    attribution_type=AttributionType.INDUSTRY,
                    factor_name=industry,
                    contribution=contribution,
                    contribution_ratio=contribution / total_pnl if total_pnl != 0 else 0
                ))
        
        if positions:
            stock_contributions = sorted(
                [(pos.stock_code, pos.pnl) for pos in positions.values()],
                key=lambda x: abs(x[1]),
                reverse=True
            )[:10]
            
            total_pnl = sum(pos.pnl for pos in positions.values())
            for stock_code, contribution in stock_contributions:
                attributions.append(AttributionResult(
                    attribution_type=AttributionType.STOCK,
                    factor_name=stock_code,
                    contribution=contribution,
                    contribution_ratio=contribution / total_pnl if total_pnl != 0 else 0
                ))
        
        return attributions
    
    def _analyze_drawdowns(self, nav_series: np.ndarray) -> DrawdownAnalysis:
        """分析回撤"""
        if len(nav_series) < 2:
            return DrawdownAnalysis(
                max_drawdown=0,
                max_drawdown_start=datetime.now(),
                max_drawdown_end=datetime.now(),
                max_drawdown_duration=0,
                current_drawdown=0
            )
        
        max_dd, current_dd, start_idx, end_idx = self.metrics_calculator.calculate_max_drawdown(nav_series)
        
        drawdown_periods = []
        peak = nav_series[0]
        peak_idx = 0
        in_drawdown = False
        dd_start_idx = 0
        
        for i, nav in enumerate(nav_series):
            if nav > peak:
                if in_drawdown:
                    dd_end_idx = i - 1
                    dd = (peak - nav_series[dd_end_idx]) / peak
                    if dd > 0.05:
                        drawdown_periods.append({
                            "start_idx": dd_start_idx,
                            "end_idx": dd_end_idx,
                            "drawdown": dd,
                            "duration": dd_end_idx - dd_start_idx + 1
                        })
                    in_drawdown = False
                peak = nav
                peak_idx = i
            else:
                if not in_drawdown:
                    in_drawdown = True
                    dd_start_idx = peak_idx
        
        recovery_times = [
            p["duration"] for p in drawdown_periods
        ]
        
        return DrawdownAnalysis(
            max_drawdown=max_dd,
            max_drawdown_start=datetime.now() - timedelta(days=len(nav_series) - start_idx),
            max_drawdown_end=datetime.now() - timedelta(days=len(nav_series) - end_idx),
            max_drawdown_duration=end_idx - start_idx,
            current_drawdown=current_dd,
            drawdown_periods=drawdown_periods,
            recovery_times=recovery_times
        )
    
    def _check_compliance(
        self,
        positions: Optional[Dict[str, PositionRecord]],
        trades: Optional[List[TradeRecord]]
    ) -> List[ComplianceCheckResult]:
        """检查合规性"""
        results = []
        
        if positions:
            weight_check = self._check_position_weights(positions)
            results.append(weight_check)
            
            concentration_check = self._check_industry_concentration(positions)
            results.append(concentration_check)
        
        if trades:
            trade_check = self._check_trade_compliance(trades)
            results.append(trade_check)
        
        return results
    
    def _check_position_weights(self, positions: Dict[str, PositionRecord]) -> ComplianceCheckResult:
        """检查持仓权重"""
        violations = []
        hard_limits = self.risk_limits.hard_limits
        
        for stock_code, pos in positions.items():
            if pos.weight > hard_limits.max_single_stock_weight:
                violations.append({
                    "stock_code": stock_code,
                    "violation_type": "weight_exceeded",
                    "actual_value": pos.weight,
                    "limit_value": hard_limits.max_single_stock_weight,
                    "message": f"股票 {stock_code} 权重 {pos.weight:.2%} 超过上限"
                })
        
        return ComplianceCheckResult(
            check_id="COMP-WEIGHT",
            check_name="持仓权重检查",
            passed=len(violations) == 0,
            violations=violations
        )
    
    def _check_industry_concentration(self, positions: Dict[str, PositionRecord]) -> ComplianceCheckResult:
        """检查行业集中度"""
        violations = []
        hard_limits = self.risk_limits.hard_limits
        
        industry_weights = {}
        for pos in positions.values():
            industry = pos.industry or "Unknown"
            industry_weights[industry] = industry_weights.get(industry, 0) + pos.weight
        
        for industry, weight in industry_weights.items():
            if weight > hard_limits.max_industry_concentration:
                violations.append({
                    "industry": industry,
                    "violation_type": "concentration_exceeded",
                    "actual_value": weight,
                    "limit_value": hard_limits.max_industry_concentration,
                    "message": f"行业 {industry} 集中度 {weight:.2%} 超过上限"
                })
        
        return ComplianceCheckResult(
            check_id="COMP-CONC",
            check_name="行业集中度检查",
            passed=len(violations) == 0,
            violations=violations
        )
    
    def _check_trade_compliance(self, trades: List[TradeRecord]) -> ComplianceCheckResult:
        """检查交易合规性"""
        violations = []
        blacklist_config = self.risk_limits.blacklist
        
        for trade in trades:
            if trade.direction == "buy" and blacklist_config.enabled:
                if blacklist_config.is_stock_blocked(trade.stock_code):
                    violations.append({
                        "trade_id": trade.trade_id,
                        "stock_code": trade.stock_code,
                        "violation_type": "blacklist_violation",
                        "message": f"买入黑名单股票 {trade.stock_code}"
                    })
        
        return ComplianceCheckResult(
            check_id="COMP-TRADE",
            check_name="交易合规检查",
            passed=len(violations) == 0,
            violations=violations
        )
    
    def _calculate_trade_statistics(self, trades: List[TradeRecord]) -> Dict[str, Any]:
        """计算交易统计"""
        if not trades:
            return {}
        
        total_trades = len(trades)
        buy_trades = [t for t in trades if t.direction == "buy"]
        sell_trades = [t for t in trades if t.direction == "sell"]
        
        total_amount = sum(t.amount for t in trades)
        total_commission = sum(t.commission for t in trades)
        total_slippage = sum(t.slippage for t in trades)
        
        win_trades = [t for t in sell_trades if t.amount > 0]
        loss_trades = [t for t in sell_trades if t.amount < 0]
        
        win_rate = len(win_trades) / len(sell_trades) if sell_trades else 0
        
        return {
            "total_trades": total_trades,
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
            "total_amount": total_amount,
            "total_commission": total_commission,
            "total_slippage": total_slippage,
            "win_rate": win_rate,
            "win_count": len(win_trades),
            "loss_count": len(loss_trades),
            "avg_trade_amount": total_amount / total_trades
        }
    
    def _analyze_positions(self, positions: Dict[str, PositionRecord]) -> Dict[str, Any]:
        """分析持仓"""
        if not positions:
            return {}
        
        total_pnl = sum(pos.pnl for pos in positions.values())
        total_market_value = sum(pos.market_value for pos in positions.values())
        
        profitable = [pos for pos in positions.values() if pos.pnl > 0]
        losing = [pos for pos in positions.values() if pos.pnl < 0]
        
        avg_holding_days = np.mean([pos.holding_days for pos in positions.values()])
        
        return {
            "position_count": len(positions),
            "total_market_value": total_market_value,
            "total_pnl": total_pnl,
            "profitable_count": len(profitable),
            "losing_count": len(losing),
            "avg_holding_days": avg_holding_days,
            "best_performer": max(positions.values(), key=lambda p: p.pnl_ratio).stock_code if positions else None,
            "worst_performer": min(positions.values(), key=lambda p: p.pnl_ratio).stock_code if positions else None
        }
    
    def generate_summary_report(self, analysis: PostTradeAnalysis) -> str:
        """生成摘要报告"""
        lines = [
            f"=== 事后风控分析报告 ===",
            f"分析ID: {analysis.analysis_id}",
            f"分析日期: {analysis.analysis_date}",
            f"分析区间: {analysis.period_start} ~ {analysis.period_end}",
            "",
            f"【收益概况】",
            f"总收益率: {analysis.total_return:.2%}",
            f"基准收益率: {analysis.benchmark_return:.2%}",
            f"超额收益: {analysis.excess_return:.2%}",
            ""
        ]
        
        if analysis.risk_metrics:
            lines.extend([
                f"【风险指标】",
                f"最大回撤: {analysis.risk_metrics.max_drawdown:.2%}",
                f"年化波动率: {analysis.risk_metrics.annualized_volatility:.2%}",
                f"夏普比率: {analysis.risk_metrics.sharpe_ratio:.2f}",
                f"VaR(95%): {analysis.risk_metrics.var_95:.2%}",
                ""
            ])
        
        if analysis.drawdown_analysis:
            lines.extend([
                f"【回撤分析】",
                f"最大回撤: {analysis.drawdown_analysis.max_drawdown:.2%}",
                f"当前回撤: {analysis.drawdown_analysis.current_drawdown:.2%}",
                f"回撤次数: {len(analysis.drawdown_analysis.drawdown_periods)}",
                ""
            ])
        
        compliance_passed = all(c.passed for c in analysis.compliance_results)
        lines.extend([
            f"【合规检查】",
            f"合规状态: {'通过' if compliance_passed else '存在违规'}",
            f"检查项数: {len(analysis.compliance_results)}",
            ""
        ])
        
        return "\n".join(lines)
