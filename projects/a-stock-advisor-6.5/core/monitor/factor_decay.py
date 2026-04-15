"""
因子衰减监控模块

监控因子预测能力的衰减，及时发现因子失效。
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


class DecayLevel(Enum):
    """衰减级别"""
    NONE = "none"           # 无衰减
    MILD = "mild"           # 轻度衰减
    MODERATE = "moderate"   # 中度衰减
    SEVERE = "severe"       # 重度衰减
    FAILED = "failed"       # 因子失效


class DecayTrend(Enum):
    """衰减趋势"""
    IMPROVING = "improving"     # 改善中
    STABLE = "stable"           # 稳定
    DECLINING = "declining"     # 衰退中


@dataclass
class FactorMetrics:
    """因子指标"""
    factor_id: str
    factor_name: str
    date: str
    
    ic_1d: float = 0.0
    ic_5d: float = 0.0
    ic_20d: float = 0.0
    ic_60d: float = 0.0
    
    ir_20d: float = 0.0
    ir_60d: float = 0.0
    
    monotonicity_20d: float = 0.0
    monotonicity_60d: float = 0.0
    
    nan_ratio: float = 0.0
    coverage: float = 1.0
    
    crowding_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DecayStatus:
    """衰减状态"""
    factor_id: str
    factor_name: str
    decay_level: DecayLevel
    decay_trend: DecayTrend
    ic_trend: str
    warning_messages: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    last_update: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "factor_name": self.factor_name,
            "decay_level": self.decay_level.value,
            "decay_trend": self.decay_trend.value,
            "ic_trend": self.ic_trend,
            "warning_messages": self.warning_messages,
            "recommendations": self.recommendations,
            "last_update": self.last_update
        }


class FactorDecayMonitor:
    """因子衰减监控器"""
    
    DECAY_THRESHOLDS = {
        "ic_5d_warning": 0.0,
        "ic_5d_critical": -0.02,
        "ic_20d_warning": 0.01,
        "ic_20d_critical": 0.0,
        "ic_60d_warning": 0.02,
        "ic_60d_critical": 0.01,
        "monotonicity_warning": 0.5,
        "monotonicity_critical": 0.3,
        "crowding_warning": 0.7,
        "crowding_critical": 0.85,
        "nan_ratio_warning": 0.2,
        "nan_ratio_critical": 0.3
    }
    
    def __init__(
        self,
        monitor_id: str = "main",
        storage_path: str = "./data/factor_decay"
    ):
        self.monitor_id = monitor_id
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("monitor.factor_decay")
        
        self.factor_metrics: Dict[str, List[FactorMetrics]] = {}
        self.factor_status: Dict[str, DecayStatus] = {}
    
    def update_factor_metrics(self, metrics: FactorMetrics):
        """更新因子指标"""
        factor_id = metrics.factor_id
        
        if factor_id not in self.factor_metrics:
            self.factor_metrics[factor_id] = []
        
        self.factor_metrics[factor_id].append(metrics)
        
        self.factor_metrics[factor_id].sort(
            key=lambda x: x.date,
            reverse=True
        )
        
        if len(self.factor_metrics[factor_id]) > 252:
            self.factor_metrics[factor_id] = self.factor_metrics[factor_id][:252]
        
        status = self._analyze_decay(factor_id, metrics)
        self.factor_status[factor_id] = status
        
        self.logger.debug(f"更新因子指标: {factor_id}, IC_5d: {metrics.ic_5d:.4f}")
    
    def _analyze_decay(self, factor_id: str, metrics: FactorMetrics) -> DecayStatus:
        """分析因子衰减"""
        warnings = []
        recommendations = []
        
        decay_level = DecayLevel.NONE
        ic_trend = "stable"
        
        if metrics.ic_5d < self.DECAY_THRESHOLDS["ic_5d_critical"]:
            warnings.append(f"IC_5日均值严重衰减: {metrics.ic_5d:.4f}")
            decay_level = DecayLevel.SEVERE
        elif metrics.ic_5d < self.DECAY_THRESHOLDS["ic_5d_warning"]:
            warnings.append(f"IC_5日均值短期衰减: {metrics.ic_5d:.4f}")
            if decay_level.value < DecayLevel.MILD.value:
                decay_level = DecayLevel.MILD
        
        if metrics.ic_20d < self.DECAY_THRESHOLDS["ic_20d_critical"]:
            warnings.append(f"IC_20日均值严重衰减: {metrics.ic_20d:.4f}")
            decay_level = DecayLevel.SEVERE
        elif metrics.ic_20d < self.DECAY_THRESHOLDS["ic_20d_warning"]:
            warnings.append(f"IC_20日均值中期衰减: {metrics.ic_20d:.4f}")
            if decay_level.value < DecayLevel.MODERATE.value:
                decay_level = DecayLevel.MODERATE
        
        if metrics.ic_60d < self.DECAY_THRESHOLDS["ic_60d_critical"]:
            warnings.append(f"IC_60日均值长期衰减: {metrics.ic_60d:.4f}")
            decay_level = DecayLevel.FAILED
        elif metrics.ic_60d < self.DECAY_THRESHOLDS["ic_60d_warning"]:
            warnings.append(f"IC_60日均值长期衰减警告: {metrics.ic_60d:.4f}")
            if decay_level.value < DecayLevel.SEVERE.value:
                decay_level = DecayLevel.SEVERE
        
        if metrics.monotonicity_20d < self.DECAY_THRESHOLDS["monotonicity_critical"]:
            warnings.append(f"单调性严重下降: {metrics.monotonicity_20d:.4f}")
            if decay_level.value < DecayLevel.SEVERE.value:
                decay_level = DecayLevel.SEVERE
        elif metrics.monotonicity_20d < self.DECAY_THRESHOLDS["monotonicity_warning"]:
            warnings.append(f"单调性下降警告: {metrics.monotonicity_20d:.4f}")
            if decay_level.value < DecayLevel.MODERATE.value:
                decay_level = DecayLevel.MODERATE
        
        if metrics.crowding_score > self.DECAY_THRESHOLDS["crowding_critical"]:
            warnings.append(f"因子过度拥挤: {metrics.crowding_score:.4f}")
            if decay_level.value < DecayLevel.SEVERE.value:
                decay_level = DecayLevel.SEVERE
        elif metrics.crowding_score > self.DECAY_THRESHOLDS["crowding_warning"]:
            warnings.append(f"因子拥挤警告: {metrics.crowding_score:.4f}")
            if decay_level.value < DecayLevel.MODERATE.value:
                decay_level = DecayLevel.MODERATE
        
        if metrics.nan_ratio > self.DECAY_THRESHOLDS["nan_ratio_critical"]:
            warnings.append(f"NaN比例过高: {metrics.nan_ratio:.2%}")
            if decay_level.value < DecayLevel.SEVERE.value:
                decay_level = DecayLevel.SEVERE
        elif metrics.nan_ratio > self.DECAY_THRESHOLDS["nan_ratio_warning"]:
            warnings.append(f"NaN比例警告: {metrics.nan_ratio:.2%}")
            if decay_level.value < DecayLevel.MILD.value:
                decay_level = DecayLevel.MILD
        
        history = self.factor_metrics.get(factor_id, [])
        if len(history) >= 5:
            recent_ic = [h.ic_5d for h in history[:5]]
            if all(ic < 0 for ic in recent_ic):
                ic_trend = "declining"
                warnings.append("IC连续5日为负")
            elif recent_ic[0] > recent_ic[-1]:
                ic_trend = "declining"
            elif recent_ic[0] < recent_ic[-1]:
                ic_trend = "improving"
        
        if decay_level == DecayLevel.MILD:
            recommendations.append("建议降低因子权重")
        elif decay_level == DecayLevel.MODERATE:
            recommendations.append("建议暂停使用该因子")
        elif decay_level == DecayLevel.SEVERE:
            recommendations.append("建议从因子库移除该因子")
        elif decay_level == DecayLevel.FAILED:
            recommendations.append("因子已失效，建议移除")
        
        if metrics.crowding_score > self.DECAY_THRESHOLDS["crowding_warning"]:
            recommendations.append("因子过度拥挤，建议降低权重")
        
        decay_trend = DecayTrend.STABLE
        if ic_trend == "improving":
            decay_trend = DecayTrend.IMPROVING
        elif ic_trend == "declining":
            decay_trend = DecayTrend.DECLINING
        
        return DecayStatus(
            factor_id=factor_id,
            factor_name=metrics.factor_name,
            decay_level=decay_level,
            decay_trend=decay_trend,
            ic_trend=ic_trend,
            warning_messages=warnings,
            recommendations=recommendations,
            last_update=metrics.date
        )
    
    def get_factor_status(self, factor_id: str) -> Optional[DecayStatus]:
        """获取因子衰减状态"""
        return self.factor_status.get(factor_id)
    
    def get_all_status(self) -> List[DecayStatus]:
        """获取所有因子状态"""
        return list(self.factor_status.values())
    
    def get_decaying_factors(self, min_level: DecayLevel = DecayLevel.MILD) -> List[DecayStatus]:
        """获取衰减因子列表"""
        level_order = {
            DecayLevel.NONE: 0,
            DecayLevel.MILD: 1,
            DecayLevel.MODERATE: 2,
            DecayLevel.SEVERE: 3,
            DecayLevel.FAILED: 4
        }
        
        return [
            status for status in self.factor_status.values()
            if level_order[status.decay_level] >= level_order[min_level]
        ]
    
    def get_factor_history(self, factor_id: str, days: int = 60) -> List[FactorMetrics]:
        """获取因子历史指标"""
        history = self.factor_metrics.get(factor_id, [])
        return history[:days]
    
    def calculate_decay_score(self, factor_id: str) -> float:
        """计算因子衰减评分"""
        status = self.factor_status.get(factor_id)
        if not status:
            return 0.0
        
        level_scores = {
            DecayLevel.NONE: 100,
            DecayLevel.MILD: 75,
            DecayLevel.MODERATE: 50,
            DecayLevel.SEVERE: 25,
            DecayLevel.FAILED: 0
        }
        
        base_score = level_scores[status.decay_level]
        
        trend_adjustment = 0
        if status.decay_trend == DecayTrend.IMPROVING:
            trend_adjustment = 5
        elif status.decay_trend == DecayTrend.DECLINING:
            trend_adjustment = -5
        
        return max(0, min(100, base_score + trend_adjustment))
    
    def generate_decay_report(self) -> str:
        """生成衰减报告"""
        lines = [
            "# 因子衰减监控报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**监控因子数量**: {len(self.factor_status)}",
            ""
        ]
        
        by_level = {}
        for level in DecayLevel:
            by_level[level.value] = len([
                s for s in self.factor_status.values()
                if s.decay_level == level
            ])
        
        lines.append("## 衰减分布")
        lines.append("")
        for level, count in by_level.items():
            lines.append(f"- {level}: {count}")
        
        decaying = self.get_decaying_factors(DecayLevel.MILD)
        if decaying:
            lines.extend([
                "",
                "## 衰减因子列表",
                ""
            ])
            
            for status in sorted(decaying, key=lambda x: x.decay_level.value, reverse=True):
                lines.append(f"### {status.factor_name} ({status.factor_id})")
                lines.append(f"- 衰减级别: {status.decay_level.value}")
                lines.append(f"- IC趋势: {status.ic_trend}")
                
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
        metrics_file = self.storage_path / "factor_metrics.json"
        status_file = self.storage_path / "factor_status.json"
        
        metrics_data = {
            factor_id: [m.to_dict() for m in metrics_list]
            for factor_id, metrics_list in self.factor_metrics.items()
        }
        
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, ensure_ascii=False, indent=2)
        
        status_data = {
            factor_id: status.to_dict()
            for factor_id, status in self.factor_status.items()
        }
        
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info("保存因子衰减监控数据")
        return True
    
    def load(self) -> bool:
        """加载监控数据"""
        metrics_file = self.storage_path / "factor_metrics.json"
        status_file = self.storage_path / "factor_status.json"
        
        if metrics_file.exists():
            try:
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    metrics_data = json.load(f)
                
                for factor_id, metrics_list in metrics_data.items():
                    self.factor_metrics[factor_id] = [
                        FactorMetrics(**m) for m in metrics_list
                    ]
            except Exception as e:
                self.logger.error(f"加载因子指标失败: {e}")
        
        if status_file.exists():
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                
                for factor_id, status in status_data.items():
                    self.factor_status[factor_id] = DecayStatus(
                        factor_id=status["factor_id"],
                        factor_name=status["factor_name"],
                        decay_level=DecayLevel(status["decay_level"]),
                        decay_trend=DecayTrend(status["decay_trend"]),
                        ic_trend=status["ic_trend"],
                        warning_messages=status["warning_messages"],
                        recommendations=status["recommendations"],
                        last_update=status["last_update"]
                    )
            except Exception as e:
                self.logger.error(f"加载因子状态失败: {e}")
        
        self.logger.info("加载因子衰减监控数据")
        return True
