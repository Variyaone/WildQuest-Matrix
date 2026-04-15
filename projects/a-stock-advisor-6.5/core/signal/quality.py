"""
信号质量评估模块

评估信号质量，包括胜率、收益、回撤等指标。
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import numpy as np

from .registry import SignalMetadata, SignalPerformance, get_signal_registry
from .generator import GeneratedSignal
from ..infrastructure.exceptions import SignalException


@dataclass
class SignalQualityMetrics:
    """信号质量指标"""
    signal_id: str
    total_signals: int
    winning_signals: int
    losing_signals: int
    win_rate: float
    avg_return: float
    avg_winning_return: float
    avg_losing_return: float
    profit_factor: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    sharpe_ratio: float
    max_drawdown: float
    avg_holding_days: float
    score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "total_signals": self.total_signals,
            "winning_signals": self.winning_signals,
            "losing_signals": self.losing_signals,
            "win_rate": self.win_rate,
            "avg_return": self.avg_return,
            "avg_winning_return": self.avg_winning_return,
            "avg_losing_return": self.avg_losing_return,
            "profit_factor": self.profit_factor,
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "avg_holding_days": self.avg_holding_days,
            "score": self.score
        }


@dataclass
class QualityAssessmentResult:
    """质量评估结果"""
    success: bool
    signal_id: str
    metrics: Optional[SignalQualityMetrics] = None
    grade: str = "C"
    recommendations: List[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class SignalQualityAssessor:
    """
    信号质量评估器
    
    评估信号的历史表现和质量。
    """
    
    GRADE_THRESHOLDS = [
        (90, "A+"),
        (80, "A"),
        (70, "B+"),
        (60, "B"),
        (50, "C+"),
        (40, "C"),
        (30, "D"),
        (0, "F")
    ]
    
    def __init__(self):
        """初始化信号质量评估器"""
        self._registry = get_signal_registry()
    
    def assess(
        self,
        signal_id: str,
        signal_returns: pd.DataFrame,
        return_col: str = "return",
        date_col: str = "date"
    ) -> QualityAssessmentResult:
        """
        评估信号质量
        
        Args:
            signal_id: 信号ID
            signal_returns: 信号收益数据
            return_col: 收益列名
            date_col: 日期列名
            
        Returns:
            QualityAssessmentResult: 评估结果
        """
        try:
            if signal_returns.empty:
                return QualityAssessmentResult(
                    success=False,
                    signal_id=signal_id,
                    error_message="信号收益数据为空"
                )
            
            returns = signal_returns[return_col].dropna()
            
            total_signals = len(returns)
            winning_signals = (returns > 0).sum()
            losing_signals = (returns < 0).sum()
            win_rate = winning_signals / total_signals if total_signals > 0 else 0
            
            avg_return = returns.mean()
            avg_winning_return = returns[returns > 0].mean() if winning_signals > 0 else 0
            avg_losing_return = returns[returns < 0].mean() if losing_signals > 0 else 0
            
            total_profit = returns[returns > 0].sum()
            total_loss = abs(returns[returns < 0].sum())
            profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            
            max_consecutive_wins = self._calculate_max_consecutive(returns, positive=True)
            max_consecutive_losses = self._calculate_max_consecutive(returns, positive=False)
            
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
            max_drawdown = self._calculate_max_drawdown(returns)
            
            avg_holding_days = 5.0
            
            score = self._calculate_score(
                win_rate, avg_return, sharpe_ratio, 
                max_drawdown, profit_factor
            )
            
            metrics = SignalQualityMetrics(
                signal_id=signal_id,
                total_signals=total_signals,
                winning_signals=winning_signals,
                losing_signals=losing_signals,
                win_rate=win_rate,
                avg_return=avg_return,
                avg_winning_return=avg_winning_return,
                avg_losing_return=avg_losing_return,
                profit_factor=profit_factor,
                max_consecutive_wins=max_consecutive_wins,
                max_consecutive_losses=max_consecutive_losses,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                avg_holding_days=avg_holding_days,
                score=score
            )
            
            grade = self._get_grade(score)
            recommendations = self._generate_recommendations(metrics)
            
            performance = SignalPerformance(
                win_rate=win_rate,
                avg_return=avg_return,
                max_drawdown=max_drawdown,
                total_signals=total_signals,
                winning_signals=winning_signals,
                avg_holding_days=avg_holding_days
            )
            self._registry.update_performance(signal_id, performance)
            self._registry.update_score(signal_id, score)
            
            return QualityAssessmentResult(
                success=True,
                signal_id=signal_id,
                metrics=metrics,
                grade=grade,
                recommendations=recommendations
            )
            
        except Exception as e:
            return QualityAssessmentResult(
                success=False,
                signal_id=signal_id,
                error_message=str(e)
            )
    
    def _calculate_max_consecutive(
        self, 
        returns: pd.Series, 
        positive: bool = True
    ) -> int:
        """计算最大连续次数"""
        max_consecutive = 0
        current_consecutive = 0
        
        for ret in returns:
            if (positive and ret > 0) or (not positive and ret < 0):
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """计算夏普比率"""
        if returns.std() == 0:
            return 0.0
        
        annual_return = returns.mean() * 252
        annual_std = returns.std() * np.sqrt(252)
        
        return annual_return / annual_std if annual_std > 0 else 0.0
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """计算最大回撤"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def _calculate_score(
        self,
        win_rate: float,
        avg_return: float,
        sharpe_ratio: float,
        max_drawdown: float,
        profit_factor: float
    ) -> float:
        """计算综合得分"""
        win_rate_score = win_rate * 30
        
        return_score = min(max(avg_return * 100, 0), 20)
        
        sharpe_score = min(max(sharpe_ratio * 10, 0), 20)
        
        drawdown_score = max(0, (1 + max_drawdown) * 15)
        
        pf_score = min(profit_factor * 3, 15)
        
        return win_rate_score + return_score + sharpe_score + drawdown_score + pf_score
    
    def _get_grade(self, score: float) -> str:
        """获取等级"""
        for threshold, grade in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"
    
    def _generate_recommendations(self, metrics: SignalQualityMetrics) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if metrics.win_rate < 0.5:
            recommendations.append("胜率偏低，建议优化信号生成条件")
        
        if metrics.avg_return < 0:
            recommendations.append("平均收益为负，建议重新设计信号逻辑")
        
        if metrics.max_drawdown < -0.2:
            recommendations.append("最大回撤较大，建议增加止损机制")
        
        if metrics.profit_factor < 1.0:
            recommendations.append("盈亏比不佳，建议调整止盈止损策略")
        
        if metrics.sharpe_ratio < 0.5:
            recommendations.append("夏普比率较低，建议提高信号稳定性")
        
        if not recommendations:
            recommendations.append("信号表现良好，建议继续保持")
        
        return recommendations
    
    def compare_signals(
        self,
        metrics_list: List[SignalQualityMetrics]
    ) -> pd.DataFrame:
        """
        比较多个信号的质量
        
        Args:
            metrics_list: 质量指标列表
            
        Returns:
            pd.DataFrame: 比较表格
        """
        data = []
        
        for metrics in metrics_list:
            data.append({
                "signal_id": metrics.signal_id,
                "win_rate": metrics.win_rate,
                "avg_return": metrics.avg_return,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
                "profit_factor": metrics.profit_factor,
                "score": metrics.score
            })
        
        return pd.DataFrame(data).sort_values("score", ascending=False)
    
    def generate_report(
        self,
        result: QualityAssessmentResult
    ) -> str:
        """
        生成评估报告
        
        Args:
            result: 评估结果
            
        Returns:
            str: 报告文本
        """
        if not result.success:
            return f"评估失败: {result.error_message}"
        
        metrics = result.metrics
        
        lines = [
            f"信号质量评估报告 - {result.signal_id}",
            "=" * 50,
            f"综合得分: {metrics.score:.2f} (等级: {result.grade})",
            "",
            "基础指标:",
            "-" * 50,
            f"  总信号数: {metrics.total_signals}",
            f"  盈利信号: {metrics.winning_signals}",
            f"  亏损信号: {metrics.losing_signals}",
            f"  胜率: {metrics.win_rate:.2%}",
            "",
            "收益指标:",
            "-" * 50,
            f"  平均收益: {metrics.avg_return:.2%}",
            f"  平均盈利: {metrics.avg_winning_return:.2%}",
            f"  平均亏损: {metrics.avg_losing_return:.2%}",
            f"  盈亏比: {metrics.profit_factor:.2f}",
            "",
            "风险指标:",
            "-" * 50,
            f"  夏普比率: {metrics.sharpe_ratio:.2f}",
            f"  最大回撤: {metrics.max_drawdown:.2%}",
            f"  最大连续盈利: {metrics.max_consecutive_wins}",
            f"  最大连续亏损: {metrics.max_consecutive_losses}",
            "",
            "建议:",
            "-" * 50,
        ]
        
        for rec in result.recommendations:
            lines.append(f"  - {rec}")
        
        return "\n".join(lines)


_default_assessor: Optional[SignalQualityAssessor] = None


def get_signal_quality_assessor() -> SignalQualityAssessor:
    """获取全局信号质量评估器实例"""
    global _default_assessor
    if _default_assessor is None:
        _default_assessor = SignalQualityAssessor()
    return _default_assessor


def reset_signal_quality_assessor():
    """重置全局信号质量评估器"""
    global _default_assessor
    _default_assessor = None
