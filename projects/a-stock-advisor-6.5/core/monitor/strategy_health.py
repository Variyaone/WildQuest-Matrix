"""
策略健康监控模块

监控策略运行健康状态，包括表现健康、参数健康、执行健康等。
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


class HealthLevel(Enum):
    """健康级别"""
    EXCELLENT = "excellent"     # 优秀 (≥85分)
    GOOD = "good"               # 良好 (70-84分)
    NORMAL = "normal"           # 一般 (60-69分)
    POOR = "poor"               # 较差 (<60分)


@dataclass
class PerformanceHealth:
    """表现健康指标"""
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    calmar_ratio: float = 0.0
    benchmark_correlation: float = 0.0
    score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ParameterHealth:
    """参数健康指标"""
    parameter_drift: float = 0.0
    parameter_sensitivity: float = 0.0
    parameter_stability: float = 1.0
    score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionHealth:
    """执行健康指标"""
    execution_rate: float = 1.0
    fill_rate: float = 1.0
    turnover_rate: float = 0.0
    trading_cost: float = 0.0
    score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EnvironmentHealth:
    """环境健康指标"""
    market_match: float = 1.0
    factor_match: float = 1.0
    liquidity_match: float = 1.0
    volatility_match: float = 1.0
    score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyHealthStatus:
    """策略健康状态"""
    strategy_id: str
    strategy_name: str
    health_level: HealthLevel
    health_score: float
    
    performance_health: PerformanceHealth = field(default_factory=PerformanceHealth)
    parameter_health: ParameterHealth = field(default_factory=ParameterHealth)
    execution_health: ExecutionHealth = field(default_factory=ExecutionHealth)
    environment_health: EnvironmentHealth = field(default_factory=EnvironmentHealth)
    
    warning_messages: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    last_update: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "health_level": self.health_level.value,
            "health_score": self.health_score,
            "performance_health": self.performance_health.to_dict(),
            "parameter_health": self.parameter_health.to_dict(),
            "execution_health": self.execution_health.to_dict(),
            "environment_health": self.environment_health.to_dict(),
            "warning_messages": self.warning_messages,
            "recommendations": self.recommendations,
            "last_update": self.last_update
        }


class StrategyHealthMonitor:
    """策略健康监控器"""
    
    HEALTH_WEIGHTS = {
        "performance": 0.40,
        "parameter": 0.20,
        "execution": 0.20,
        "environment": 0.20
    }
    
    PERFORMANCE_THRESHOLDS = {
        "sharpe_excellent": 1.5,
        "sharpe_good": 1.0,
        "sharpe_normal": 0.5,
        "sharpe_poor": 0.0,
        "max_drawdown_excellent": 0.05,
        "max_drawdown_good": 0.10,
        "max_drawdown_normal": 0.15,
        "max_drawdown_poor": 0.20,
        "calmar_excellent": 2.0,
        "calmar_good": 1.5,
        "calmar_normal": 1.0,
        "calmar_poor": 0.5
    }
    
    def __init__(
        self,
        monitor_id: str = "main",
        storage_path: str = "./data/strategy_health"
    ):
        self.monitor_id = monitor_id
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("monitor.strategy_health")
        
        self.strategy_status: Dict[str, StrategyHealthStatus] = {}
        self.health_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def update_strategy_health(
        self,
        strategy_id: str,
        strategy_name: str,
        performance: Optional[Dict[str, float]] = None,
        parameter: Optional[Dict[str, float]] = None,
        execution: Optional[Dict[str, float]] = None,
        environment: Optional[Dict[str, float]] = None
    ) -> StrategyHealthStatus:
        """更新策略健康状态"""
        perf_health = self._calculate_performance_health(performance or {})
        param_health = self._calculate_parameter_health(parameter or {})
        exec_health = self._calculate_execution_health(execution or {})
        env_health = self._calculate_environment_health(environment or {})
        
        health_score = (
            perf_health.score * self.HEALTH_WEIGHTS["performance"] +
            param_health.score * self.HEALTH_WEIGHTS["parameter"] +
            exec_health.score * self.HEALTH_WEIGHTS["execution"] +
            env_health.score * self.HEALTH_WEIGHTS["environment"]
        )
        
        if health_score >= 85:
            health_level = HealthLevel.EXCELLENT
        elif health_score >= 70:
            health_level = HealthLevel.GOOD
        elif health_score >= 60:
            health_level = HealthLevel.NORMAL
        else:
            health_level = HealthLevel.POOR
        
        warnings = self._generate_warnings(
            perf_health, param_health, exec_health, env_health
        )
        recommendations = self._generate_recommendations(
            health_level, perf_health, param_health, exec_health, env_health
        )
        
        status = StrategyHealthStatus(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            health_level=health_level,
            health_score=health_score,
            performance_health=perf_health,
            parameter_health=param_health,
            execution_health=exec_health,
            environment_health=env_health,
            warning_messages=warnings,
            recommendations=recommendations,
            last_update=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        self.strategy_status[strategy_id] = status
        self._record_history(strategy_id, status)
        
        self.logger.info(f"更新策略健康: {strategy_id}, 得分: {health_score:.1f}")
        return status
    
    def _calculate_performance_health(self, data: Dict[str, float]) -> PerformanceHealth:
        """计算表现健康"""
        sharpe = data.get("sharpe_ratio", 0.0)
        max_dd = data.get("max_drawdown", 0.0)
        calmar = data.get("calmar_ratio", 0.0)
        correlation = data.get("benchmark_correlation", 0.0)
        
        score = 0.0
        
        if sharpe >= self.PERFORMANCE_THRESHOLDS["sharpe_excellent"]:
            score += 30
        elif sharpe >= self.PERFORMANCE_THRESHOLDS["sharpe_good"]:
            score += 24
        elif sharpe >= self.PERFORMANCE_THRESHOLDS["sharpe_normal"]:
            score += 18
        elif sharpe >= self.PERFORMANCE_THRESHOLDS["sharpe_poor"]:
            score += 12
        else:
            score += 6
        
        if max_dd <= self.PERFORMANCE_THRESHOLDS["max_drawdown_excellent"]:
            score += 30
        elif max_dd <= self.PERFORMANCE_THRESHOLDS["max_drawdown_good"]:
            score += 24
        elif max_dd <= self.PERFORMANCE_THRESHOLDS["max_drawdown_normal"]:
            score += 18
        elif max_dd <= self.PERFORMANCE_THRESHOLDS["max_drawdown_poor"]:
            score += 12
        else:
            score += 6
        
        if calmar >= self.PERFORMANCE_THRESHOLDS["calmar_excellent"]:
            score += 20
        elif calmar >= self.PERFORMANCE_THRESHOLDS["calmar_good"]:
            score += 16
        elif calmar >= self.PERFORMANCE_THRESHOLDS["calmar_normal"]:
            score += 12
        elif calmar >= self.PERFORMANCE_THRESHOLDS["calmar_poor"]:
            score += 8
        else:
            score += 4
        
        if correlation < 0.9:
            score += 20
        elif correlation < 0.95:
            score += 15
        else:
            score += 10
        
        return PerformanceHealth(
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            calmar_ratio=calmar,
            benchmark_correlation=correlation,
            score=min(100, max(0, score))
        )
    
    def _calculate_parameter_health(self, data: Dict[str, float]) -> ParameterHealth:
        """计算参数健康"""
        drift = data.get("parameter_drift", 0.0)
        sensitivity = data.get("parameter_sensitivity", 0.0)
        stability = data.get("parameter_stability", 1.0)
        
        score = 0.0
        
        if drift < 0.1:
            score += 40
        elif drift < 0.2:
            score += 30
        elif drift < 0.3:
            score += 20
        else:
            score += 10
        
        if sensitivity < 0.1:
            score += 30
        elif sensitivity < 0.2:
            score += 22
        elif sensitivity < 0.3:
            score += 14
        else:
            score += 6
        
        score += stability * 30
        
        return ParameterHealth(
            parameter_drift=drift,
            parameter_sensitivity=sensitivity,
            parameter_stability=stability,
            score=min(100, max(0, score))
        )
    
    def _calculate_execution_health(self, data: Dict[str, float]) -> ExecutionHealth:
        """计算执行健康"""
        exec_rate = data.get("execution_rate", 1.0)
        fill_rate = data.get("fill_rate", 1.0)
        turnover = data.get("turnover_rate", 0.0)
        cost = data.get("trading_cost", 0.0)
        
        score = 0.0
        
        if exec_rate >= 0.99:
            score += 30
        elif exec_rate >= 0.95:
            score += 24
        elif exec_rate >= 0.90:
            score += 18
        else:
            score += 12
        
        if fill_rate >= 0.99:
            score += 30
        elif fill_rate >= 0.95:
            score += 24
        elif fill_rate >= 0.90:
            score += 18
        else:
            score += 12
        
        if turnover <= 0.10:
            score += 20
        elif turnover <= 0.20:
            score += 16
        elif turnover <= 0.30:
            score += 12
        else:
            score += 8
        
        if cost <= 0.001:
            score += 20
        elif cost <= 0.002:
            score += 16
        elif cost <= 0.003:
            score += 12
        else:
            score += 8
        
        return ExecutionHealth(
            execution_rate=exec_rate,
            fill_rate=fill_rate,
            turnover_rate=turnover,
            trading_cost=cost,
            score=min(100, max(0, score))
        )
    
    def _calculate_environment_health(self, data: Dict[str, float]) -> EnvironmentHealth:
        """计算环境健康"""
        market_match = data.get("market_match", 1.0)
        factor_match = data.get("factor_match", 1.0)
        liquidity_match = data.get("liquidity_match", 1.0)
        volatility_match = data.get("volatility_match", 1.0)
        
        score = (
            market_match * 25 +
            factor_match * 25 +
            liquidity_match * 25 +
            volatility_match * 25
        )
        
        return EnvironmentHealth(
            market_match=market_match,
            factor_match=factor_match,
            liquidity_match=liquidity_match,
            volatility_match=volatility_match,
            score=min(100, max(0, score))
        )
    
    def _generate_warnings(
        self,
        perf: PerformanceHealth,
        param: ParameterHealth,
        exec: ExecutionHealth,
        env: EnvironmentHealth
    ) -> List[str]:
        """生成警告信息"""
        warnings = []
        
        if perf.sharpe_ratio < 0.5:
            warnings.append(f"夏普比率过低: {perf.sharpe_ratio:.2f}")
        
        if perf.max_drawdown > 0.15:
            warnings.append(f"最大回撤过大: {perf.max_drawdown:.2%}")
        
        if perf.benchmark_correlation > 0.95:
            warnings.append(f"与基准相关性过高: {perf.benchmark_correlation:.2f}")
        
        if param.parameter_drift > 0.2:
            warnings.append(f"参数漂移过大: {param.parameter_drift:.2%}")
        
        if exec.execution_rate < 0.95:
            warnings.append(f"执行率过低: {exec.execution_rate:.2%}")
        
        if exec.turnover_rate > 0.30:
            warnings.append(f"换手率过高: {exec.turnover_rate:.2%}")
        
        if env.market_match < 0.7:
            warnings.append(f"市场环境匹配度低: {env.market_match:.2%}")
        
        return warnings
    
    def _generate_recommendations(
        self,
        level: HealthLevel,
        perf: PerformanceHealth,
        param: ParameterHealth,
        exec: ExecutionHealth,
        env: EnvironmentHealth
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if level == HealthLevel.POOR:
            recommendations.append("建议暂停策略，进行全面检查")
        elif level == HealthLevel.NORMAL:
            recommendations.append("建议关注策略表现，适时调整")
        
        if perf.sharpe_ratio < 0.5:
            recommendations.append("建议优化策略逻辑，提升收益风险比")
        
        if perf.max_drawdown > 0.15:
            recommendations.append("建议加强风险控制，降低最大回撤")
        
        if param.parameter_drift > 0.2:
            recommendations.append("建议重新校准策略参数")
        
        if exec.turnover_rate > 0.30:
            recommendations.append("建议降低换手频率，减少交易成本")
        
        if env.market_match < 0.7:
            recommendations.append("建议调整策略以适应当前市场环境")
        
        return recommendations
    
    def _record_history(self, strategy_id: str, status: StrategyHealthStatus):
        """记录历史"""
        if strategy_id not in self.health_history:
            self.health_history[strategy_id] = []
        
        self.health_history[strategy_id].append({
            "date": status.last_update,
            "health_score": status.health_score,
            "health_level": status.health_level.value
        })
        
        if len(self.health_history[strategy_id]) > 365:
            self.health_history[strategy_id] = self.health_history[strategy_id][-365:]
    
    def get_strategy_status(self, strategy_id: str) -> Optional[StrategyHealthStatus]:
        """获取策略健康状态"""
        return self.strategy_status.get(strategy_id)
    
    def get_all_status(self) -> List[StrategyHealthStatus]:
        """获取所有策略状态"""
        return list(self.strategy_status.values())
    
    def get_unhealthy_strategies(self) -> List[StrategyHealthStatus]:
        """获取不健康策略列表"""
        return [
            status for status in self.strategy_status.values()
            if status.health_level in [HealthLevel.NORMAL, HealthLevel.POOR]
        ]
    
    def get_health_history(self, strategy_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """获取健康历史"""
        history = self.health_history.get(strategy_id, [])
        return history[-days:]
    
    def generate_health_report(self) -> str:
        """生成健康报告"""
        lines = [
            "# 策略健康监控报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**监控策略数量**: {len(self.strategy_status)}",
            ""
        ]
        
        by_level = {}
        for level in HealthLevel:
            by_level[level.value] = len([
                s for s in self.strategy_status.values()
                if s.health_level == level
            ])
        
        lines.append("## 健康分布")
        lines.append("")
        for level, count in by_level.items():
            lines.append(f"- {level}: {count}")
        
        for status in self.strategy_status.values():
            lines.extend([
                "",
                f"## {status.strategy_name} ({status.strategy_id})",
                "",
                f"**健康级别**: {status.health_level.value}",
                f"**健康得分**: {status.health_score:.1f}",
                "",
                "### 表现健康",
                f"- 夏普比率: {status.performance_health.sharpe_ratio:.2f}",
                f"- 最大回撤: {status.performance_health.max_drawdown:.2%}",
                f"- 卡玛比率: {status.performance_health.calmar_ratio:.2f}",
                f"- 得分: {status.performance_health.score:.1f}",
                "",
                "### 参数健康",
                f"- 参数漂移: {status.parameter_health.parameter_drift:.2%}",
                f"- 参数稳定性: {status.parameter_health.parameter_stability:.2%}",
                f"- 得分: {status.parameter_health.score:.1f}",
                "",
                "### 执行健康",
                f"- 执行率: {status.execution_health.execution_rate:.2%}",
                f"- 成交率: {status.execution_health.fill_rate:.2%}",
                f"- 换手率: {status.execution_health.turnover_rate:.2%}",
                f"- 得分: {status.execution_health.score:.1f}",
                "",
                "### 环境健康",
                f"- 市场匹配度: {status.environment_health.market_match:.2%}",
                f"- 因子匹配度: {status.environment_health.factor_match:.2%}",
                f"- 得分: {status.environment_health.score:.1f}"
            ])
            
            if status.warning_messages:
                lines.extend(["", "### 警告信息"])
                for msg in status.warning_messages:
                    lines.append(f"- {msg}")
            
            if status.recommendations:
                lines.extend(["", "### 建议"])
                for rec in status.recommendations:
                    lines.append(f"- {rec}")
        
        return "\n".join(lines)
    
    def save(self) -> bool:
        """保存监控数据"""
        status_file = self.storage_path / "strategy_status.json"
        history_file = self.storage_path / "health_history.json"
        
        status_data = {
            strategy_id: status.to_dict()
            for strategy_id, status in self.strategy_status.items()
        }
        
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(self.health_history, f, ensure_ascii=False, indent=2)
        
        self.logger.info("保存策略健康监控数据")
        return True
    
    def load(self) -> bool:
        """加载监控数据"""
        status_file = self.storage_path / "strategy_status.json"
        history_file = self.storage_path / "health_history.json"
        
        if status_file.exists():
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                
                for strategy_id, data in status_data.items():
                    self.strategy_status[strategy_id] = StrategyHealthStatus(
                        strategy_id=data["strategy_id"],
                        strategy_name=data["strategy_name"],
                        health_level=HealthLevel(data["health_level"]),
                        health_score=data["health_score"],
                        performance_health=PerformanceHealth(**data["performance_health"]),
                        parameter_health=ParameterHealth(**data["parameter_health"]),
                        execution_health=ExecutionHealth(**data["execution_health"]),
                        environment_health=EnvironmentHealth(**data["environment_health"]),
                        warning_messages=data["warning_messages"],
                        recommendations=data["recommendations"],
                        last_update=data["last_update"]
                    )
            except Exception as e:
                self.logger.error(f"加载策略状态失败: {e}")
        
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.health_history = json.load(f)
            except Exception as e:
                self.logger.error(f"加载健康历史失败: {e}")
        
        self.logger.info("加载策略健康监控数据")
        return True
