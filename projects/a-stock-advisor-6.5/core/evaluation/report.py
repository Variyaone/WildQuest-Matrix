"""
评估报告生成器

生成因子和策略的评估报告。
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
    title: str = "评估报告"
    output_dir: str = "./reports/evaluation"
    format: str = "html"
    include_summary: bool = True
    include_details: bool = True
    include_charts: bool = True
    language: str = "zh_CN"


class EvaluationReportGenerator:
    """
    评估报告生成器
    
    生成因子和策略的评估报告。
    """
    
    def __init__(self, config: Optional[ReportConfig] = None):
        """
        初始化报告生成器
        
        Args:
            config: 报告配置
        """
        self.config = config or ReportConfig()
    
    def generate_factor_report(
        self,
        evaluation_result: Any,
        filename: Optional[str] = None
    ) -> str:
        """
        生成因子评估报告
        
        Args:
            evaluation_result: 因子评估结果
            filename: 文件名
            
        Returns:
            str: 报告文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            factor_id = getattr(evaluation_result, 'factor_id', 'unknown')
            filename = f"factor_evaluation_{factor_id}_{timestamp}"
        
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if hasattr(evaluation_result, 'to_dict'):
            result = evaluation_result.to_dict()
        else:
            result = evaluation_result
        
        if self.config.format == "html":
            report_content = self._generate_factor_html_report(result)
            file_path = output_path / f"{filename}.html"
        else:
            report_content = json.dumps(result, ensure_ascii=False, indent=2)
            file_path = output_path / f"{filename}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return str(file_path)
    
    def generate_strategy_report(
        self,
        evaluation_result: Any,
        filename: Optional[str] = None
    ) -> str:
        """
        生成策略评估报告
        
        Args:
            evaluation_result: 策略评估结果
            filename: 文件名
            
        Returns:
            str: 报告文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            strategy_id = getattr(evaluation_result, 'strategy_id', 'unknown')
            filename = f"strategy_evaluation_{strategy_id}_{timestamp}"
        
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if hasattr(evaluation_result, 'to_dict'):
            result = evaluation_result.to_dict()
        else:
            result = evaluation_result
        
        if self.config.format == "html":
            report_content = self._generate_strategy_html_report(result)
            file_path = output_path / f"{filename}.html"
        else:
            report_content = json.dumps(result, ensure_ascii=False, indent=2)
            file_path = output_path / f"{filename}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return str(file_path)
    
    def generate_comparison_report(
        self,
        comparison_results: pd.DataFrame,
        title: str = "对比报告",
        filename: Optional[str] = None
    ) -> str:
        """
        生成对比报告
        
        Args:
            comparison_results: 对比结果DataFrame
            title: 报告标题
            filename: 文件名
            
        Returns:
            str: 报告文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comparison_report_{timestamp}"
        
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if self.config.format == "html":
            report_content = self._generate_comparison_html_report(comparison_results, title)
            file_path = output_path / f"{filename}.html"
        else:
            report_content = comparison_results.to_json(orient='records', force_ascii=False, indent=2)
            file_path = output_path / f"{filename}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return str(file_path)
    
    def _generate_factor_html_report(self, result: Dict[str, Any]) -> str:
        """生成因子HTML报告"""
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.title} - 因子评估</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 10px; }}
        .section {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 20px;
            font-weight: 700;
            color: #667eea;
        }}
        .metric-value.positive {{ color: #10b981; }}
        .metric-value.negative {{ color: #ef4444; }}
        .metric-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
        .score-bar {{
            background: #e5e7eb;
            border-radius: 10px;
            height: 20px;
            margin: 10px 0;
            overflow: hidden;
        }}
        .score-fill {{
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s;
        }}
        .score-fill.excellent {{ background: #10b981; }}
        .score-fill.good {{ background: #3b82f6; }}
        .score-fill.fair {{ background: #f59e0b; }}
        .score-fill.poor {{ background: #ef4444; }}
        .warning {{ background: #fef3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; }}
        .recommendation {{ background: #d1ecf1; border-left: 4px solid #17a2b8; padding: 10px; margin: 10px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>因子评估报告</h1>
            <div class="subtitle">
                因子编号: {result.get('factor_id', 'N/A')} | 
                因子名称: {result.get('factor_name', 'N/A')} |
                评估日期: {result.get('evaluation_date', 'N/A')}
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📊 预测能力评估</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value {self._get_value_class(result.get('ic_mean', 0))}">
                        {result.get('ic_mean', 0):.4f}
                    </div>
                    <div class="metric-label">IC均值</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('ic_std', 0):.4f}
                    </div>
                    <div class="metric-label">IC标准差</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {self._get_value_class(result.get('ir', 0))}">
                        {result.get('ir', 0):.4f}
                    </div>
                    <div class="metric-label">IR</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('monotonicity', 0):.2f}
                    </div>
                    <div class="metric-label">单调性</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📈 稳定性评估</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('monthly_ic_stability', 0):.2f}
                    </div>
                    <div class="metric-label">月度IC稳定性</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('bull_market_ic', 0):.4f}
                    </div>
                    <div class="metric-label">牛市IC</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('bear_market_ic', 0):.4f}
                    </div>
                    <div class="metric-label">熊市IC</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('sideways_market_ic', 0):.4f}
                    </div>
                    <div class="metric-label">震荡市IC</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">🎯 综合评分</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{result.get('prediction_score', 0)}</div>
                    <div class="metric-label">预测能力得分</div>
                    <div class="score-bar">
                        <div class="score-fill {self._get_score_class(result.get('prediction_score', 0))}" 
                             style="width: {result.get('prediction_score', 0)}%"></div>
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{result.get('stability_score', 0)}</div>
                    <div class="metric-label">稳定性得分</div>
                    <div class="score-bar">
                        <div class="score-fill {self._get_score_class(result.get('stability_score', 0))}" 
                             style="width: {result.get('stability_score', 0)}%"></div>
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{result.get('correlation_score', 0)}</div>
                    <div class="metric-label">相关性得分</div>
                    <div class="score-bar">
                        <div class="score-fill {self._get_score_class(result.get('correlation_score', 0))}" 
                             style="width: {result.get('correlation_score', 0)}%"></div>
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{result.get('utility_score', 0)}</div>
                    <div class="metric-label">实用性得分</div>
                    <div class="score-bar">
                        <div class="score-fill {self._get_score_class(result.get('utility_score', 0))}" 
                             style="width: {result.get('utility_score', 0)}%"></div>
                    </div>
                </div>
            </div>
            <div style="text-align: center; margin-top: 20px;">
                <div style="font-size: 36px; font-weight: 700; color: #667eea;">
                    {result.get('total_score', 0)}
                </div>
                <div style="font-size: 14px; color: #666;">
                    综合得分 (排名: {result.get('rank', 0)}/{result.get('total_factors', 0)})
                </div>
            </div>
        </div>
        
        {self._generate_warnings_section(result.get('warnings', []))}
        
        {self._generate_recommendations_section(result)}
        
        <div class="footer">
            <p>A股投资顾问系统 v6.5 - 因子评估报告</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _generate_strategy_html_report(self, result: Dict[str, Any]) -> str:
        """生成策略HTML报告"""
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.title} - 策略评估</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 10px; }}
        .section {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 20px;
            font-weight: 700;
            color: #667eea;
        }}
        .metric-value.positive {{ color: #10b981; }}
        .metric-value.negative {{ color: #ef4444; }}
        .metric-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>策略评估报告</h1>
            <div class="subtitle">
                策略编号: {result.get('strategy_id', 'N/A')} | 
                策略名称: {result.get('strategy_name', 'N/A')} |
                评估日期: {result.get('evaluation_date', 'N/A')}
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📊 收益评估</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value {self._get_value_class(result.get('cumulative_return', 0))}">
                        {result.get('cumulative_return', 0):.2%}
                    </div>
                    <div class="metric-label">累计收益率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {self._get_value_class(result.get('annual_return', 0))}">
                        {result.get('annual_return', 0):.2%}
                    </div>
                    <div class="metric-label">年化收益率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {self._get_value_class(result.get('excess_return', 0))}">
                        {result.get('excess_return', 0):.2%}
                    </div>
                    <div class="metric-label">超额收益率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('beat_benchmark_ratio', 0):.2%}
                    </div>
                    <div class="metric-label">跑赢基准比例</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">⚠️ 风险评估</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('annual_volatility', 0):.2%}
                    </div>
                    <div class="metric-label">年化波动率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value negative">
                        {result.get('max_drawdown', 0):.2%}
                    </div>
                    <div class="metric-label">最大回撤</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('drawdown_duration', 0)}天
                    </div>
                    <div class="metric-label">回撤持续期</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value negative">
                        {result.get('var_95', 0):.2%}
                    </div>
                    <div class="metric-label">VaR(95%)</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📈 风险调整收益</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('sharpe_ratio', 0):.2f}
                    </div>
                    <div class="metric-label">夏普比率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('sortino_ratio', 0):.2f}
                    </div>
                    <div class="metric-label">索提诺比率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('calmar_ratio', 0):.2f}
                    </div>
                    <div class="metric-label">卡玛比率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('information_ratio', 0):.2f}
                    </div>
                    <div class="metric-label">信息比率</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📋 交易评估</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('win_rate', 0):.2%}
                    </div>
                    <div class="metric-label">胜率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('profit_loss_ratio', 0):.2f}
                    </div>
                    <div class="metric-label">盈亏比</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('turnover_rate', 0):.2%}
                    </div>
                    <div class="metric-label">换手率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">
                        {result.get('trade_count', 0)}
                    </div>
                    <div class="metric-label">交易次数</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">🎯 综合评分</h2>
            <div style="text-align: center;">
                <div style="font-size: 48px; font-weight: 700; color: #667eea;">
                    {result.get('total_score', 0)}
                </div>
                <div style="font-size: 16px; color: #666;">
                    综合得分 (排名: {result.get('rank', 0)}/{result.get('total_strategies', 0)})
                </div>
            </div>
            <div class="metrics-grid" style="margin-top: 20px;">
                <div class="metric-card">
                    <div class="metric-value">{result.get('return_score', 0)}</div>
                    <div class="metric-label">收益得分</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{result.get('risk_control_score', 0)}</div>
                    <div class="metric-label">风险控制得分</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{result.get('risk_adjusted_score', 0)}</div>
                    <div class="metric-label">风险调整得分</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{result.get('trading_efficiency_score', 0)}</div>
                    <div class="metric-label">交易效率得分</div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>A股投资顾问系统 v6.5 - 策略评估报告</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _generate_comparison_html_report(
        self,
        comparison_df: pd.DataFrame,
        title: str
    ) -> str:
        """生成对比HTML报告"""
        table_html = comparison_df.to_html(index=False, classes='comparison-table')
        
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 10px; }}
        .section {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            overflow-x: auto;
        }}
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .comparison-table th,
        .comparison-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .comparison-table th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        .comparison-table tr:hover {{
            background: #f8f9fa;
        }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="subtitle">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="section">
            <h2 style="margin-bottom: 15px;">对比结果</h2>
            {table_html}
        </div>
        
        <div class="footer">
            <p>A股投资顾问系统 v6.5 - 对比报告</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _generate_warnings_section(self, warnings: List[str]) -> str:
        """生成警告部分"""
        if not warnings:
            return ""
        
        warnings_html = "".join([f"<div class='warning'>⚠️ {w}</div>" for w in warnings])
        
        return f"""
        <div class="section">
            <h2 class="section-title">⚠️ 注意事项</h2>
            {warnings_html}
        </div>
        """
    
    def _generate_recommendations_section(self, result: Dict[str, Any]) -> str:
        """生成建议部分"""
        return f"""
        <div class="section">
            <h2 class="section-title">💡 使用建议</h2>
            <div class="recommendation">
                <strong>推荐场景:</strong> {result.get('recommended_usage', 'N/A')}
            </div>
            <div class="recommendation">
                <strong>推荐权重:</strong> {result.get('recommended_weight', 'N/A')}
            </div>
            <div class="recommendation">
                <strong>配对因子:</strong> {', '.join(result.get('paired_factors', [])) or '无'}
            </div>
        </div>
        """
    
    def _get_value_class(self, value: float) -> str:
        """获取值的CSS类"""
        if value > 0:
            return 'positive'
        elif value < 0:
            return 'negative'
        return ''
    
    def _get_score_class(self, score: int) -> str:
        """获取分数的CSS类"""
        if score >= 80:
            return 'excellent'
        elif score >= 60:
            return 'good'
        elif score >= 40:
            return 'fair'
        else:
            return 'poor'
