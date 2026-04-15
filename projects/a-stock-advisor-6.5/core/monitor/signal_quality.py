"""
信号质量监控模块

监控信号生成质量，包括胜率、盈亏比、信号强度等指标。
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import pandas as pd
import numpy as np

from core.infrastructure.logging import get_logger


class QualityLevel(Enum):
    """质量级别"""
    EXCELLENT = "excellent"     # 优秀
    GOOD = "good"               # 良好
    NORMAL = "normal"           # 正常
    POOR = "poor"               # 较差
    CRITICAL = "critical"       # 严重


@dataclass
class SignalMetrics:
    """信号指标"""
    signal_id: str
    signal_name: str
    date: str
    
    win_rate_1d: float = 0.0
    win_rate_5d: float = 0.0
    win_rate_20d: float = 0.0
    
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    profit_loss_ratio: float = 0.0
    
    signal_strength: float = 0.0
    signal_count: int = 0
    signal_coverage: float = 0.0
    
    quality_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityStatus:
    """质量状态"""
    signal_id: str
    signal_name: str
    quality_level: QualityLevel
    quality_score: float
    win_rate_trend: str
    strength_trend: str
    warning_messages: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    last_update: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_name": self.signal_name,
            "quality_level": self.quality_level.value,
            "quality_score": self.quality_score,
            "win_rate_trend": self.win_rate_trend,
            "strength_trend": self.strength_trend,
            "warning_messages": self.warning_messages,
            "recommendations": self.recommendations,
            "last_update": self.last_update
        }


class SignalQualityMonitor:
    """信号质量监控器"""
    
    QUALITY_THRESHOLDS = {
        "win_rate_excellent": 0.60,
        "win_rate_good": 0.55,
        "win_rate_normal": 0.50,
        "win_rate_poor": 0.45,
        "win_rate_critical": 0.40,
        "profit_loss_ratio_good": 2.0,
        "profit_loss_ratio_normal": 1.5,
        "profit_loss_ratio_poor": 1.0,
        "signal_strength_min": 0.3,
        "signal_coverage_min": 0.3
    }
    
    def __init__(
        self,
        monitor_id: str = "main",
        storage_path: str = "./data/signal_quality"
    ):
        self.monitor_id = monitor_id
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("monitor.signal_quality")
        
        self.signal_metrics: Dict[str, List[SignalMetrics]] = {}
        self.signal_status: Dict[str, QualityStatus] = {}
    
    def update_signal_metrics(self, metrics: SignalMetrics):
        """更新信号指标"""
        signal_id = metrics.signal_id
        
        if signal_id not in self.signal_metrics:
            self.signal_metrics[signal_id] = []
        
        self.signal_metrics[signal_id].append(metrics)
        
        self.signal_metrics[signal_id].sort(
            key=lambda x: x.date,
            reverse=True
        )
        
        if len(self.signal_metrics[signal_id]) > 252:
            self.signal_metrics[signal_id] = self.signal_metrics[signal_id][:252]
        
        status = self._analyze_quality(signal_id, metrics)
        self.signal_status[signal_id] = status
        
        self.logger.debug(f"更新信号指标: {signal_id}, 胜率: {metrics.win_rate_1d:.2%}")
    
    def _analyze_quality(self, signal_id: str, metrics: SignalMetrics) -> QualityStatus:
        """分析信号质量"""
        warnings = []
        recommendations = []
        
        quality_score = self._calculate_quality_score(metrics)
        
        if quality_score >= 80:
            quality_level = QualityLevel.EXCELLENT
        elif quality_score >= 65:
            quality_level = QualityLevel.GOOD
        elif quality_score >= 50:
            quality_level = QualityLevel.NORMAL
        elif quality_score >= 35:
            quality_level = QualityLevel.POOR
        else:
            quality_level = QualityLevel.CRITICAL
        
        if metrics.win_rate_1d < self.QUALITY_THRESHOLDS["win_rate_critical"]:
            warnings.append(f"日度胜率严重下降: {metrics.win_rate_1d:.2%}")
        elif metrics.win_rate_1d < self.QUALITY_THRESHOLDS["win_rate_poor"]:
            warnings.append(f"日度胜率较低: {metrics.win_rate_1d:.2%}")
        
        if metrics.win_rate_20d < self.QUALITY_THRESHOLDS["win_rate_normal"]:
            warnings.append(f"月度胜率低于正常: {metrics.win_rate_20d:.2%}")
        
        if metrics.profit_loss_ratio < self.QUALITY_THRESHOLDS["profit_loss_ratio_poor"]:
            warnings.append(f"盈亏比过低: {metrics.profit_loss_ratio:.2f}")
        elif metrics.profit_loss_ratio < self.QUALITY_THRESHOLDS["profit_loss_ratio_normal"]:
            warnings.append(f"盈亏比偏低: {metrics.profit_loss_ratio:.2f}")
        
        if metrics.signal_strength < self.QUALITY_THRESHOLDS["signal_strength_min"]:
            warnings.append(f"信号强度过低: {metrics.signal_strength:.4f}")
        
        if metrics.signal_coverage < self.QUALITY_THRESHOLDS["signal_coverage_min"]:
            warnings.append(f"信号覆盖率过低: {metrics.signal_coverage:.2%}")
        
        win_rate_trend = self._analyze_trend(signal_id, "win_rate_1d")
        strength_trend = self._analyze_trend(signal_id, "signal_strength")
        
        if quality_level == QualityLevel.POOR:
            recommendations.append("建议降低信号权重")
        elif quality_level == QualityLevel.CRITICAL:
            recommendations.append("建议暂停使用该信号")
        
        if metrics.profit_loss_ratio < self.QUALITY_THRESHOLDS["profit_loss_ratio_normal"]:
            recommendations.append("建议优化止损策略")
        
        return QualityStatus(
            signal_id=signal_id,
            signal_name=metrics.signal_name,
            quality_level=quality_level,
            quality_score=quality_score,
            win_rate_trend=win_rate_trend,
            strength_trend=strength_trend,
            warning_messages=warnings,
            recommendations=recommendations,
            last_update=metrics.date
        )
    
    def _calculate_quality_score(self, metrics: SignalMetrics) -> float:
        """计算质量评分"""
        score = 0.0
        
        if metrics.win_rate_20d >= self.QUALITY_THRESHOLDS["win_rate_excellent"]:
            score += 40
        elif metrics.win_rate_20d >= self.QUALITY_THRESHOLDS["win_rate_good"]:
            score += 32
        elif metrics.win_rate_20d >= self.QUALITY_THRESHOLDS["win_rate_normal"]:
            score += 24
        elif metrics.win_rate_20d >= self.QUALITY_THRESHOLDS["win_rate_poor"]:
            score += 16
        else:
            score += 8
        
        if metrics.profit_loss_ratio >= self.QUALITY_THRESHOLDS["profit_loss_ratio_good"]:
            score += 30
        elif metrics.profit_loss_ratio >= self.QUALITY_THRESHOLDS["profit_loss_ratio_normal"]:
            score += 22
        elif metrics.profit_loss_ratio >= self.QUALITY_THRESHOLDS["profit_loss_ratio_poor"]:
            score += 14
        else:
            score += 6
        
        score += min(20, metrics.signal_strength * 50)
        
        score += min(10, metrics.signal_coverage * 20)
        
        return min(100, max(0, score))
    
    def _analyze_trend(self, signal_id: str, field: str) -> str:
        """分析趋势"""
        history = self.signal_metrics.get(signal_id, [])
        
        if len(history) < 5:
            return "stable"
        
        values = [getattr(h, field) for h in history[:5]]
        
        if values[0] > values[-1] * 1.1:
            return "improving"
        elif values[0] < values[-1] * 0.9:
            return "declining"
        else:
            return "stable"
    
    def get_signal_status(self, signal_id: str) -> Optional[QualityStatus]:
        """获取信号质量状态"""
        return self.signal_status.get(signal_id)
    
    def get_all_status(self) -> List[QualityStatus]:
        """获取所有信号状态"""
        return list(self.signal_status.values())
    
    def get_low_quality_signals(self, max_level: QualityLevel = QualityLevel.POOR) -> List[QualityStatus]:
        """获取低质量信号列表"""
        level_order = {
            QualityLevel.EXCELLENT: 0,
            QualityLevel.GOOD: 1,
            QualityLevel.NORMAL: 2,
            QualityLevel.POOR: 3,
            QualityLevel.CRITICAL: 4
        }
        
        return [
            status for status in self.signal_status.values()
            if level_order[status.quality_level] >= level_order[max_level]
        ]
    
    def get_signal_history(self, signal_id: str, days: int = 60) -> List[SignalMetrics]:
        """获取信号历史指标"""
        history = self.signal_metrics.get(signal_id, [])
        return history[:days]
    
    def generate_quality_report(self) -> str:
        """生成质量报告"""
        lines = [
            "# 信号质量监控报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**监控信号数量**: {len(self.signal_status)}",
            ""
        ]
        
        by_level = {}
        for level in QualityLevel:
            by_level[level.value] = len([
                s for s in self.signal_status.values()
                if s.quality_level == level
            ])
        
        lines.append("## 质量分布")
        lines.append("")
        for level, count in by_level.items():
            lines.append(f"- {level}: {count}")
        
        low_quality = self.get_low_quality_signals(QualityLevel.POOR)
        if low_quality:
            lines.extend([
                "",
                "## 低质量信号列表",
                ""
            ])
            
            for status in sorted(low_quality, key=lambda x: x.quality_score):
                lines.append(f"### {status.signal_name} ({status.signal_id})")
                lines.append(f"- 质量级别: {status.quality_level.value}")
                lines.append(f"- 质量评分: {status.quality_score:.1f}")
                lines.append(f"- 胜率趋势: {status.win_rate_trend}")
                lines.append(f"- 强度趋势: {status.strength_trend}")
                
                if status.warning_messages:
                    lines.append("- 警告信息:")
                    for msg in status.warning_messages:
                        lines.append(f"  - {msg}")
                
                if status.recommendations:
                    lines.append("- 建议:")
                    for rec in status.recommendations:
                        lines.append(f"  - {rec}")
                
                lines.append("")
        
        return "\n".join(lines)
    
    def save(self) -> bool:
        """保存监控数据"""
        metrics_file = self.storage_path / "signal_metrics.json"
        status_file = self.storage_path / "signal_status.json"
        
        metrics_data = {
            signal_id: [m.to_dict() for m in metrics_list]
            for signal_id, metrics_list in self.signal_metrics.items()
        }
        
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, ensure_ascii=False, indent=2)
        
        status_data = {
            signal_id: status.to_dict()
            for signal_id, status in self.signal_status.items()
        }
        
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info("保存信号质量监控数据")
        return True
    
    def load(self) -> bool:
        """加载监控数据"""
        metrics_file = self.storage_path / "signal_metrics.json"
        status_file = self.storage_path / "signal_status.json"
        
        if metrics_file.exists():
            try:
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    metrics_data = json.load(f)
                
                for signal_id, metrics_list in metrics_data.items():
                    self.signal_metrics[signal_id] = [
                        SignalMetrics(**m) for m in metrics_list
                    ]
            except Exception as e:
                self.logger.error(f"加载信号指标失败: {e}")
        
        if status_file.exists():
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                
                for signal_id, status in status_data.items():
                    self.signal_status[signal_id] = QualityStatus(
                        signal_id=status["signal_id"],
                        signal_name=status["signal_name"],
                        quality_level=QualityLevel(status["quality_level"]),
                        quality_score=status["quality_score"],
                        win_rate_trend=status["win_rate_trend"],
                        strength_trend=status["strength_trend"],
                        warning_messages=status["warning_messages"],
                        recommendations=status["recommendations"],
                        last_update=status["last_update"]
                    )
            except Exception as e:
                self.logger.error(f"加载信号状态失败: {e}")
        
        self.logger.info("加载信号质量监控数据")
        return True
