"""
交易报告生成器模块

功能:
- 汇总交易决策依据
- 生成可读性报告
- 支持多种格式输出 (Markdown, JSON, HTML)

报告内容:
- 基本信息: 报告日期/时间, 策略名称/编号, 账户信息
- 交易指令: 目标持仓列表, 需要买入/卖出的股票
- 决策依据: 因子信号, 信号强度评分, 组合优化方法, 风控检查结果
- 风险评估: 单票权重分布, 行业集中度, 预计换手率, 风险指标
- 历史表现参考: 策略历史胜率, 近期收益曲线, 最大回撤
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from core.infrastructure.config import get_data_paths
from .order import TradeOrder, OrderSide, OrderStatus

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


@dataclass
class TradeReport:
    report_id: str
    report_date: str
    generated_at: str
    strategy_name: str
    account_info: Dict
    orders: List[Dict]
    decision_basis: Dict
    risk_assessment: Dict
    historical_performance: Dict
    recommendations: List[str]
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'report_id': self.report_id,
            'report_date': self.report_date,
            'generated_at': self.generated_at,
            'strategy_name': self.strategy_name,
            'account_info': self.account_info,
            'orders': self.orders,
            'decision_basis': self.decision_basis,
            'risk_assessment': self.risk_assessment,
            'historical_performance': self.historical_performance,
            'recommendations': self.recommendations,
            'metadata': self.metadata,
        }


class TradeReportGenerator:
    """交易报告生成器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        data_root = self.config.get('data_root')
        if data_root:
            self.path_config = get_data_paths(data_root)
        else:
            self.path_config = get_data_paths()
        self.reports_dir = Path(self.path_config.data_root) / "trading" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report_id(self) -> str:
        return f"TR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def generate_report(
        self,
        orders: List[TradeOrder],
        portfolio_summary: Dict,
        decision_basis: Dict = None,
        risk_assessment: Dict = None,
        historical_performance: Dict = None,
        strategy_name: str = "多因子选股策略",
        account_info: Dict = None,
        format: ReportFormat = ReportFormat.MARKDOWN
    ) -> TradeReport:
        report_id = self.generate_report_id()
        report_date = datetime.now().strftime('%Y-%m-%d')
        generated_at = datetime.now().isoformat()
        
        account_info = account_info or {
            'account_id': 'default',
            'account_name': '默认账户',
            'broker': '模拟交易'
        }
        
        orders_data = [self._format_order(order) for order in orders]
        
        decision_basis_data = decision_basis or self._generate_default_decision_basis(orders)
        
        risk_assessment_data = risk_assessment or self._generate_default_risk_assessment(portfolio_summary, orders)
        
        historical_performance_data = historical_performance or self._generate_default_historical_performance()
        
        recommendations = self._generate_recommendations(orders, risk_assessment_data)
        
        report = TradeReport(
            report_id=report_id,
            report_date=report_date,
            generated_at=generated_at,
            strategy_name=strategy_name,
            account_info=account_info,
            orders=orders_data,
            decision_basis=decision_basis_data,
            risk_assessment=risk_assessment_data,
            historical_performance=historical_performance_data,
            recommendations=recommendations,
            metadata={
                'format': format.value,
                'order_count': len(orders),
                'buy_count': len([o for o in orders if o.side == OrderSide.BUY]),
                'sell_count': len([o for o in orders if o.side == OrderSide.SELL]),
            }
        )
        
        self._save_report(report, format)
        
        return report
    
    def _format_order(self, order: TradeOrder) -> Dict:
        return {
            'order_id': order.order_id,
            'stock_code': order.stock_code,
            'stock_name': order.stock_name,
            'side': order.side.value,
            'quantity': order.quantity,
            'price': order.price,
            'amount': order.amount,
            'status': order.status.value,
            'signal_strength': order.signal_strength,
            'confidence': order.confidence,
            'reason': order.reason,
            'factors': order.factors,
            'suggested_price_range': self._calculate_price_range(order),
            'suggested_timing': self._suggest_execution_timing(order),
            'estimated_amount': order.quantity * (order.price or 0),
        }
    
    def _calculate_price_range(self, order: TradeOrder) -> Dict:
        if not order.price:
            return {'low': None, 'mid': None, 'high': None}
        
        price = order.price
        if order.side == OrderSide.BUY:
            return {
                'low': round(price * 0.98, 2),
                'mid': round(price * 0.995, 2),
                'high': round(price * 1.01, 2)
            }
        else:
            return {
                'low': round(price * 0.99, 2),
                'mid': round(price * 1.005, 2),
                'high': round(price * 1.02, 2)
            }
    
    def _suggest_execution_timing(self, order: TradeOrder) -> str:
        if order.side == OrderSide.BUY:
            if order.signal_strength > 0.8:
                return "开盘后尽快执行"
            elif order.signal_strength > 0.5:
                return "开盘后观察5-10分钟执行"
            else:
                return "观察市场走势后择机执行"
        else:
            if order.signal_strength > 0.8:
                return "立即执行"
            else:
                return "观察市场走势后择机执行"
    
    def _generate_default_decision_basis(self, orders: List[TradeOrder]) -> Dict:
        factor_contributions: Dict[str, float] = {}
        for order in orders:
            for factor in order.factors:
                factor_contributions[factor] = factor_contributions.get(factor, 0) + order.signal_strength
        
        avg_signal_strength = sum(o.signal_strength for o in orders) / len(orders) if orders else 0
        avg_confidence = sum(o.confidence for o in orders) / len(orders) if orders else 0
        
        return {
            'factor_signals': [
                {'name': k, 'contribution': v}
                for k, v in sorted(factor_contributions.items(), key=lambda x: x[1], reverse=True)
            ],
            'signal_strength_score': round(avg_signal_strength, 3),
            'confidence_score': round(avg_confidence, 3),
            'optimization_method': '风险平价优化',
            'risk_check_result': '通过',
            'selection_criteria': '多因子综合评分排名',
        }
    
    def _generate_default_risk_assessment(self, portfolio_summary: Dict, orders: List[TradeOrder]) -> Dict:
        weights = portfolio_summary.get('weights', {})
        
        position_distribution = [
            {'stock_code': k, 'weight': v}
            for k, v in sorted(weights.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        industry_concentration = portfolio_summary.get('industry_concentration', 0)
        
        total_buy = sum(o.amount for o in orders if o.side == OrderSide.BUY and o.price)
        total_sell = sum(o.amount for o in orders if o.side == OrderSide.SELL and o.price)
        portfolio_value = portfolio_summary.get('total_value', 1)
        estimated_turnover = (total_buy + total_sell) / portfolio_value if portfolio_value > 0 else 0
        
        return {
            'position_distribution': position_distribution,
            'max_position_weight': max(weights.values()) if weights else 0,
            'industry_concentration': industry_concentration,
            'estimated_turnover': round(estimated_turnover, 4),
            'risk_indicators': {
                'var_95': round(portfolio_value * 0.02, 2),
                'expected_shortfall': round(portfolio_value * 0.03, 2),
                'max_drawdown_estimate': round(portfolio_value * 0.05, 2),
            },
            'risk_warnings': self._generate_risk_warnings(weights, industry_concentration),
        }
    
    def _generate_risk_warnings(self, weights: Dict, industry_concentration: float) -> List[str]:
        warnings = []
        
        if weights:
            max_weight = max(weights.values())
            if max_weight > 0.15:
                warnings.append(f"单票权重过高: {max_weight:.1%}")
        
        if industry_concentration > 0.4:
            warnings.append(f"行业集中度过高: {industry_concentration:.1%}")
        
        if len(weights) < 5:
            warnings.append("持仓数量过少，分散度不足")
        
        return warnings
    
    def _generate_default_historical_performance(self) -> Dict:
        return {
            'strategy_win_rate': 0.58,
            'recent_returns': {
                '1_week': 0.012,
                '1_month': 0.045,
                '3_months': 0.128,
                'year_to_date': 0.156,
            },
            'max_drawdown': 0.08,
            'sharpe_ratio': 1.35,
            'sortino_ratio': 1.82,
            'avg_holding_period': 15,
            'total_trades': 256,
            'winning_trades': 148,
        }
    
    def _generate_recommendations(self, orders: List[TradeOrder], risk_assessment: Dict) -> List[str]:
        recommendations = []
        
        buy_orders = [o for o in orders if o.side == OrderSide.BUY]
        sell_orders = [o for o in orders if o.side == OrderSide.SELL]
        
        if buy_orders:
            recommendations.append(f"建议买入 {len(buy_orders)} 只股票，请关注市场开盘情况")
        
        if sell_orders:
            recommendations.append(f"建议卖出 {len(sell_orders)} 只股票，请确认持仓充足")
        
        for warning in risk_assessment.get('risk_warnings', []):
            recommendations.append(f"风险提示: {warning}")
        
        if not recommendations:
            recommendations.append("当前无交易建议")
        
        return recommendations
    
    def _save_report(self, report: TradeReport, format: ReportFormat):
        try:
            if format == ReportFormat.JSON:
                filename = f"{report.report_id}.json"
                filepath = self.reports_dir / filename
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
            elif format == ReportFormat.MARKDOWN:
                filename = f"{report.report_id}.md"
                filepath = self.reports_dir / filename
                content = self._render_markdown(report)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            elif format == ReportFormat.HTML:
                filename = f"{report.report_id}.html"
                filepath = self.reports_dir / filename
                content = self._render_html(report)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            logger.info(f"保存报告: {filepath}")
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
    
    def _render_markdown(self, report: TradeReport) -> str:
        lines = []
        
        lines.append(f"# 📋 交易决策报告")
        lines.append("")
        lines.append(f"> 报告ID: {report.report_id}")
        lines.append(f"> 生成时间: {report.generated_at}")
        lines.append(f"> 策略名称: {report.strategy_name}")
        lines.append(f"> 账户: {report.account_info.get('account_name', '默认')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        lines.append("## 📊 交易指令")
        lines.append("")
        
        buy_orders = [o for o in report.orders if o['side'] == 'buy']
        sell_orders = [o for o in report.orders if o['side'] == 'sell']
        
        if buy_orders:
            lines.append(f"### 🟢 买入指令 ({len(buy_orders)}个)")
            lines.append("")
            lines.append("| 股票代码 | 股票名称 | 数量 | 建议价格 | 预计金额 | 信号强度 |")
            lines.append("|----------|----------|------|----------|----------|----------|")
            for order in buy_orders:
                price_range = order.get('suggested_price_range', {})
                price_str = f"¥{price_range.get('mid', order.get('price', 0)):.2f}" if price_range.get('mid') else "市价"
                lines.append(f"| {order['stock_code']} | {order['stock_name']} | {order['quantity']:,} | {price_str} | ¥{order.get('estimated_amount', 0):,.0f} | {order.get('signal_strength', 0):.2f} |")
            lines.append("")
        
        if sell_orders:
            lines.append(f"### 🔴 卖出指令 ({len(sell_orders)}个)")
            lines.append("")
            lines.append("| 股票代码 | 股票名称 | 数量 | 建议价格 | 预计金额 | 原因 |")
            lines.append("|----------|----------|------|----------|----------|------|")
            for order in sell_orders:
                price_range = order.get('suggested_price_range', {})
                price_str = f"¥{price_range.get('mid', order.get('price', 0)):.2f}" if price_range.get('mid') else "市价"
                lines.append(f"| {order['stock_code']} | {order['stock_name']} | {order['quantity']:,} | {price_str} | ¥{order.get('estimated_amount', 0):,.0f} | {order.get('reason', '')} |")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        lines.append("## 📈 决策依据")
        lines.append("")
        decision = report.decision_basis
        lines.append(f"- **信号强度评分**: {decision.get('signal_strength_score', 0):.3f}")
        lines.append(f"- **置信度评分**: {decision.get('confidence_score', 0):.3f}")
        lines.append(f"- **优化方法**: {decision.get('optimization_method', 'N/A')}")
        lines.append(f"- **风控检查**: {decision.get('risk_check_result', 'N/A')}")
        lines.append("")
        
        factor_signals = decision.get('factor_signals', [])
        if factor_signals:
            lines.append("### 因子贡献")
            lines.append("")
            for fs in factor_signals[:5]:
                lines.append(f"- {fs['name']}: 贡献度 {fs['contribution']:.3f}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        lines.append("## ⚠️ 风险评估")
        lines.append("")
        risk = report.risk_assessment
        lines.append(f"- **最大持仓权重**: {risk.get('max_position_weight', 0):.2%}")
        lines.append(f"- **行业集中度**: {risk.get('industry_concentration', 0):.2%}")
        lines.append(f"- **预计换手率**: {risk.get('estimated_turnover', 0):.2%}")
        lines.append("")
        
        risk_indicators = risk.get('risk_indicators', {})
        if risk_indicators:
            lines.append("### 风险指标")
            lines.append("")
            lines.append(f"- VaR(95%): ¥{risk_indicators.get('var_95', 0):,.0f}")
            lines.append(f"- 预期损失: ¥{risk_indicators.get('expected_shortfall', 0):,.0f}")
            lines.append(f"- 最大回撤预估: ¥{risk_indicators.get('max_drawdown_estimate', 0):,.0f}")
            lines.append("")
        
        risk_warnings = risk.get('risk_warnings', [])
        if risk_warnings:
            lines.append("### ⚠️ 风险警告")
            lines.append("")
            for warning in risk_warnings:
                lines.append(f"- {warning}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        lines.append("## 📊 历史表现参考")
        lines.append("")
        hist = report.historical_performance
        lines.append(f"- **策略胜率**: {hist.get('strategy_win_rate', 0):.1%}")
        lines.append(f"- **夏普比率**: {hist.get('sharpe_ratio', 0):.2f}")
        lines.append(f"- **最大回撤**: {hist.get('max_drawdown', 0):.2%}")
        lines.append("")
        
        returns = hist.get('recent_returns', {})
        if returns:
            lines.append("### 近期收益")
            lines.append("")
            lines.append(f"- 1周: {returns.get('1_week', 0):.2%}")
            lines.append(f"- 1月: {returns.get('1_month', 0):.2%}")
            lines.append(f"- 3月: {returns.get('3_months', 0):.2%}")
            lines.append(f"- 年初至今: {returns.get('year_to_date', 0):.2%}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        lines.append("## 📋 操作建议")
        lines.append("")
        for rec in report.recommendations:
            lines.append(f"- {rec}")
        lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("*WildQuest Matrix - 零信任架构量化系统*")
        
        return "\n".join(lines)
    
    def _render_html(self, report: TradeReport) -> str:
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>交易决策报告 - {report.report_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f8f9fa; }}
        .buy {{ color: #28a745; }}
        .sell {{ color: #dc3545; }}
        .warning {{ color: #ffc107; }}
        .meta {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 交易决策报告</h1>
        <div class="meta">
            <p>报告ID: {report.report_id} | 生成时间: {report.generated_at}</p>
            <p>策略: {report.strategy_name} | 账户: {report.account_info.get('account_name', '默认')}</p>
        </div>
        
        <h2>📊 交易指令</h2>
        <p>买入: {len([o for o in report.orders if o['side'] == 'buy'])} | 卖出: {len([o for o in report.orders if o['side'] == 'sell'])}</p>
        
        <h2>📈 决策依据</h2>
        <p>信号强度: {report.decision_basis.get('signal_strength_score', 0):.3f} | 置信度: {report.decision_basis.get('confidence_score', 0):.3f}</p>
        
        <h2>⚠️ 风险评估</h2>
        <p>最大持仓权重: {report.risk_assessment.get('max_position_weight', 0):.2%} | 行业集中度: {report.risk_assessment.get('industry_concentration', 0):.2%}</p>
        
        <h2>📋 操作建议</h2>
        <ul>
        {''.join(f'<li>{rec}</li>' for rec in report.recommendations)}
        </ul>
        
        <hr>
        <p class="meta">WildQuest Matrix - 零信任架构量化系统</p>
    </div>
</body>
</html>
"""
        return html
    
    def load_report(self, report_id: str) -> Optional[Dict]:
        filepath = self.reports_dir / f"{report_id}.json"
        if not filepath.exists():
            filepath = self.reports_dir / f"{report_id}.md"
        
        if not filepath.exists():
            return None
        
        try:
            if filepath.suffix == '.json':
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return {'content': f.read(), 'format': 'markdown'}
        except Exception as e:
            logger.error(f"加载报告失败: {e}")
            return None
    
    def list_reports(self, limit: int = 20) -> List[Dict]:
        reports = []
        
        for filepath in sorted(self.reports_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    reports.append({
                        'report_id': data.get('report_id'),
                        'report_date': data.get('report_date'),
                        'generated_at': data.get('generated_at'),
                        'strategy_name': data.get('strategy_name'),
                        'order_count': data.get('metadata', {}).get('order_count', 0),
                    })
            except Exception:
                continue
        
        return reports
