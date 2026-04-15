"""
回测报告生成器

生成可视化回测报告。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import json
import pandas as pd
import numpy as np


@dataclass
class ReportConfig:
    """报告配置"""
    title: str = "回测报告"
    output_dir: str = "./reports"
    format: str = "html"
    include_charts: bool = True
    include_tables: bool = True
    include_details: bool = True
    language: str = "zh_CN"
    theme: str = "default"
    frequency: str = "daily"


class BacktestReporter:
    """
    回测报告生成器
    
    生成可视化回测报告。
    """
    
    def __init__(self, config: Optional[ReportConfig] = None):
        """
        初始化报告生成器
        
        Args:
            config: 报告配置
        """
        self.config = config or ReportConfig()
    
    def generate(
        self,
        backtest_result: Dict[str, Any],
        filename: Optional[str] = None
    ) -> str:
        """
        生成报告
        
        Args:
            backtest_result: 回测结果
            filename: 文件名
            
        Returns:
            str: 报告文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_report_{timestamp}"
        
        frequency = backtest_result.get('config', {}).get('frequency', self.config.frequency)
        if frequency == 'd' or frequency == 'daily':
            freq_dir = "daily"
        elif frequency == 'h' or frequency == 'hourly':
            freq_dir = "hourly"
        elif frequency == 'm' or frequency == 'minute':
            freq_dir = "minute"
        else:
            freq_dir = "daily"
        
        output_path = Path(self.config.output_dir) / freq_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        if self.config.format == "html":
            report_content = self._generate_html_report(backtest_result)
            file_path = output_path / f"{filename}.html"
        else:
            report_content = self._generate_json_report(backtest_result)
            file_path = output_path / f"{filename}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return str(file_path)
    
    def _generate_html_report(self, result: Dict[str, Any]) -> str:
        """生成HTML报告"""
        metrics = result.get('metrics', {})
        trades = result.get('trades', [])
        positions = result.get('positions', {})
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .header .subtitle {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .section {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: 700;
            color: #667eea;
        }}
        .metric-value.positive {{
            color: #10b981;
        }}
        .metric-value.negative {{
            color: #ef4444;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .chart-container {{
            width: 100%;
            height: 300px;
            margin: 15px 0;
        }}
        .summary-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        .summary-label {{
            color: #666;
        }}
        .summary-value {{
            font-weight: 600;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{self.config.title}</h1>
            <div class="subtitle">
                生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
        
        {self._generate_metrics_section(metrics)}
        
        {self._generate_performance_section(metrics)}
        
        {self._generate_risk_section(metrics)}
        
        {self._generate_trade_section(trades)}
        
        <div class="footer">
            <p>A股投资顾问系统 v6.5 - 回测报告</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _generate_metrics_section(self, metrics: Dict[str, Any]) -> str:
        """生成收益指标部分"""
        return f"""
        <div class="section">
            <h2 class="section-title">📊 收益指标</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value {self._get_value_class(metrics.get('total_return', 0))}">
                        {metrics.get('total_return', 0):.2%}
                    </div>
                    <div class="metric-label">累计收益率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {self._get_value_class(metrics.get('annual_return', 0))}">
                        {metrics.get('annual_return', 0):.2%}
                    </div>
                    <div class="metric-label">年化收益率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {self._get_value_class(metrics.get('excess_return', 0))}">
                        {metrics.get('excess_return', 0):.2%}
                    </div>
                    <div class="metric-label">超额收益率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {metrics.get('trade_count', 0)}
                    </div>
                    <div class="metric-label">交易次数</div>
                </div>
            </div>
        </div>
        """
    
    def _generate_performance_section(self, metrics: Dict[str, Any]) -> str:
        """生成绩效指标部分"""
        return f"""
        <div class="section">
            <h2 class="section-title">📈 风险调整收益</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">
                        {metrics.get('sharpe_ratio', 0):.2f}
                    </div>
                    <div class="metric-label">夏普比率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {metrics.get('sortino_ratio', 0):.2f}
                    </div>
                    <div class="metric-label">索提诺比率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {metrics.get('calmar_ratio', 0):.2f}
                    </div>
                    <div class="metric-label">卡玛比率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {metrics.get('information_ratio', 0):.2f}
                    </div>
                    <div class="metric-label">信息比率</div>
                </div>
            </div>
        </div>
        """
    
    def _generate_risk_section(self, metrics: Dict[str, Any]) -> str:
        """生成风险指标部分"""
        return f"""
        <div class="section">
            <h2 class="section-title">⚠️ 风险指标</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value negative">
                        {metrics.get('max_drawdown', 0):.2%}
                    </div>
                    <div class="metric-label">最大回撤</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {metrics.get('volatility', 0):.2%}
                    </div>
                    <div class="metric-label">年化波动率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value negative">
                        {metrics.get('var_95', 0):.2%}
                    </div>
                    <div class="metric-label">VaR(95%)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {metrics.get('max_drawdown_duration', 0)}天
                    </div>
                    <div class="metric-label">回撤持续期</div>
                </div>
            </div>
        </div>
        """
    
    def _generate_trade_section(self, trades: List[Dict]) -> str:
        """生成交易统计部分"""
        if not trades:
            return """
            <div class="section">
                <h2 class="section-title">📋 交易统计</h2>
                <p>无交易记录</p>
            </div>
            """
        
        df = pd.DataFrame(trades)
        
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
        losing_trades = len([t for t in trades if t.get('pnl', 0) < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        return f"""
        <div class="section">
            <h2 class="section-title">📋 交易统计</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{total_trades}</div>
                    <div class="metric-label">总交易次数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value positive">{winning_trades}</div>
                    <div class="metric-label">盈利交易</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value negative">{losing_trades}</div>
                    <div class="metric-label">亏损交易</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {self._get_value_class(win_rate)}">
                        {win_rate:.2%}
                    </div>
                    <div class="metric-label">胜率</div>
                </div>
            </div>
            <div style="margin-top: 20px;">
                <div class="summary-row">
                    <span class="summary-label">总盈亏</span>
                    <span class="summary-value {self._get_value_class(total_pnl)}">
                        {total_pnl:,.2f}
                    </span>
                </div>
                <div class="summary-row">
                    <span class="summary-label">平均盈亏</span>
                    <span class="summary-value {self._get_value_class(avg_pnl)}">
                        {avg_pnl:,.2f}
                    </span>
                </div>
            </div>
        </div>
        """
    
    def _generate_json_report(self, result: Dict[str, Any]) -> str:
        """生成JSON报告"""
        report = {
            'title': self.config.title,
            'generated_at': datetime.now().isoformat(),
            'metrics': result.get('metrics', {}),
            'summary': {
                'total_return': result.get('metrics', {}).get('total_return', 0),
                'annual_return': result.get('metrics', {}).get('annual_return', 0),
                'sharpe_ratio': result.get('metrics', {}).get('sharpe_ratio', 0),
                'max_drawdown': result.get('metrics', {}).get('max_drawdown', 0),
                'trade_count': result.get('metrics', {}).get('trade_count', 0)
            }
        }
        return json.dumps(report, ensure_ascii=False, indent=2)
    
    def _get_value_class(self, value: float) -> str:
        """获取值的CSS类"""
        if value > 0:
            return 'positive'
        elif value < 0:
            return 'negative'
        return ''
    
    def generate_summary_table(
        self,
        results: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        生成多策略对比表
        
        Args:
            results: 多个回测结果列表
            
        Returns:
            pd.DataFrame: 对比表
        """
        rows = []
        
        for result in results:
            metrics = result.get('metrics', {})
            rows.append({
                '策略名称': result.get('strategy_name', 'Unknown'),
                '累计收益': f"{metrics.get('total_return', 0):.2%}",
                '年化收益': f"{metrics.get('annual_return', 0):.2%}",
                '最大回撤': f"{metrics.get('max_drawdown', 0):.2%}",
                '夏普比率': f"{metrics.get('sharpe_ratio', 0):.2f}",
                '胜率': f"{metrics.get('win_rate', 0):.2%}",
                '交易次数': metrics.get('trade_count', 0)
            })
        
        return pd.DataFrame(rows)
    
    def generate_monthly_heatmap(
        self,
        returns: pd.Series
    ) -> str:
        """
        生成月度收益热力图HTML
        
        Args:
            returns: 收益率序列
            
        Returns:
            str: HTML内容
        """
        if isinstance(returns.index, pd.DatetimeIndex):
            monthly = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        else:
            returns_copy = returns.copy()
            returns_copy.index = pd.to_datetime(returns_copy.index)
            monthly = returns_copy.resample('M').apply(lambda x: (1 + x).prod() - 1)
        
        monthly_df = pd.DataFrame({'return': monthly})
        monthly_df['year'] = monthly_df.index.year
        monthly_df['month'] = monthly_df.index.month
        
        pivot = monthly_df.pivot_table(
            values='return',
            index='year',
            columns='month',
            aggfunc='first'
        )
        
        html = """
        <div class="section">
            <h2 class="section-title">📅 月度收益热力图</h2>
            <table>
                <thead>
                    <tr>
                        <th>年份</th>
        """
        
        months = ['1月', '2月', '3月', '4月', '5月', '6月',
                 '7月', '8月', '9月', '10月', '11月', '12月']
        for m in months:
            html += f"<th>{m}</th>"
        html += "</tr></thead><tbody>"
        
        for year in pivot.index:
            html += f"<tr><td>{int(year)}</td>"
            for month in range(1, 13):
                if month in pivot.columns:
                    val = pivot.loc[year, month]
                    if pd.notna(val):
                        color = self._get_heatmap_color(val)
                        html += f'<td style="background-color: {color}; color: white;">{val:.2%}</td>'
                    else:
                        html += '<td>-</td>'
                else:
                    html += '<td>-</td>'
            html += "</tr>"
        
        html += "</tbody></table></div>"
        return html
    
    def _get_heatmap_color(self, value: float) -> str:
        """获取热力图颜色"""
        if value > 0.05:
            return '#059669'
        elif value > 0.02:
            return '#10b981'
        elif value > 0:
            return '#34d399'
        elif value > -0.02:
            return '#f87171'
        elif value > -0.05:
            return '#ef4444'
        else:
            return '#dc2626'
