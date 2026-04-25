"""
管线质量门控模块

每个步骤的质量要求和验证机制。
确保每个步骤的输出满足下一步骤的输入要求。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np
from pathlib import Path

from ..infrastructure.logging import get_logger
from ..infrastructure.exceptions import AppException, ErrorCode

logger = get_logger("pipeline.quality_gate")


class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    FAILED = "failed"


class GateStatus(Enum):
    """门控状态"""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass
class QualityMetric:
    """质量指标"""
    name: str
    value: float
    threshold: float
    passed: bool
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "threshold": self.threshold,
            "passed": self.passed,
            "message": self.message
        }


@dataclass
class QualityGateResult:
    """质量门控结果"""
    step_name: str
    status: GateStatus
    quality_level: QualityLevel
    metrics: List[QualityMetric] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def is_pass(self) -> bool:
        return self.status in [GateStatus.PASS, GateStatus.WARNING]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_name": self.step_name,
            "status": self.status.value,
            "quality_level": self.quality_level.value,
            "metrics": [m.to_dict() for m in self.metrics],
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class QualityGate:
    """质量门控基类"""
    
    def __init__(self, step_name: str):
        self.step_name = step_name
        self.logger = get_logger(f"pipeline.quality_gate.{step_name}")
    
    def check(self, **kwargs) -> QualityGateResult:
        """执行质量检查"""
        raise NotImplementedError
    
    def _create_metric(
        self,
        name: str,
        value: float,
        threshold: float,
        higher_is_better: bool = True
    ) -> QualityMetric:
        """创建质量指标"""
        if higher_is_better:
            passed = value >= threshold
            message = f"{name}: {value:.4f} {'≥' if passed else '<'} {threshold:.4f}"
        else:
            passed = value <= threshold
            message = f"{name}: {value:.4f} {'≤' if passed else '>'} {threshold:.4f}"
        
        return QualityMetric(
            name=name,
            value=value,
            threshold=threshold,
            passed=passed,
            message=message
        )


class DataUpdateQualityGate(QualityGate):
    """数据更新质量门控"""
    
    def __init__(self):
        super().__init__("data_update")
    
    def check(
        self,
        stock_count: int,
        data_files: List[str],
        data_completeness: float,
        update_success_rate: float,
        **kwargs
    ) -> QualityGateResult:
        """
        检查数据更新质量
        
        质量要求:
        1. 股票数量 ≥ 3000
        2. 数据文件数量 ≥ 100
        3. 数据完整度 ≥ 0.95
        4. 更新成功率 ≥ 0.98
        """
        metrics = []
        errors = []
        warnings = []
        
        metrics.append(self._create_metric(
            "股票数量",
            stock_count,
            3000,
            higher_is_better=True
        ))
        
        metrics.append(self._create_metric(
            "数据文件数量",
            len(data_files),
            100,
            higher_is_better=True
        ))
        
        metrics.append(self._create_metric(
            "数据完整度",
            data_completeness,
            0.95,
            higher_is_better=True
        ))
        
        metrics.append(self._create_metric(
            "更新成功率",
            update_success_rate,
            0.98,
            higher_is_better=True
        ))
        
        passed_count = sum(1 for m in metrics if m.passed)
        
        if passed_count == 4:
            status = GateStatus.PASS
            quality_level = QualityLevel.EXCELLENT
        elif passed_count == 3:
            status = GateStatus.WARNING
            quality_level = QualityLevel.GOOD
            warnings.append("部分指标未达标")
        elif passed_count == 2:
            status = GateStatus.WARNING
            quality_level = QualityLevel.ACCEPTABLE
            warnings.append("多项指标未达标，建议检查")
        else:
            status = GateStatus.FAIL
            quality_level = QualityLevel.FAILED
            errors.append("数据质量严重不达标")
        
        return QualityGateResult(
            step_name=self.step_name,
            status=status,
            quality_level=quality_level,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
            details={
                "stock_count": stock_count,
                "data_files_count": len(data_files),
                "data_completeness": data_completeness,
                "update_success_rate": update_success_rate
            }
        )


class FactorCalculationQualityGate(QualityGate):
    """因子计算质量门控"""
    
    def __init__(self):
        super().__init__("factor_calculation")
    
    def check(
        self,
        factor_count: int,
        factors_calculated: int,
        factors_failed: int,
        avg_coverage: float,
        avg_nan_ratio: float,
        **kwargs
    ) -> QualityGateResult:
        """
        检查因子计算质量
        
        质量要求:
        1. 因子数量 ≥ 100
        2. 计算成功率 ≥ 0.95
        3. 平均覆盖率 ≥ 0.90
        4. 平均NaN比例 ≤ 0.10
        """
        metrics = []
        errors = []
        warnings = []
        
        metrics.append(self._create_metric(
            "因子数量",
            factor_count,
            100,
            higher_is_better=True
        ))
        
        success_rate = factors_calculated / factor_count if factor_count > 0 else 0
        metrics.append(self._create_metric(
            "计算成功率",
            success_rate,
            0.95,
            higher_is_better=True
        ))
        
        metrics.append(self._create_metric(
            "平均覆盖率",
            avg_coverage,
            0.90,
            higher_is_better=True
        ))
        
        metrics.append(self._create_metric(
            "平均NaN比例",
            avg_nan_ratio,
            0.10,
            higher_is_better=False
        ))
        
        passed_count = sum(1 for m in metrics if m.passed)
        
        if passed_count == 4:
            status = GateStatus.PASS
            quality_level = QualityLevel.EXCELLENT
        elif passed_count >= 3:
            status = GateStatus.WARNING
            quality_level = QualityLevel.GOOD
            warnings.append("部分指标未达标")
        elif passed_count >= 2:
            status = GateStatus.WARNING
            quality_level = QualityLevel.ACCEPTABLE
            warnings.append("多项指标未达标")
        else:
            status = GateStatus.FAIL
            quality_level = QualityLevel.FAILED
            errors.append("因子计算质量严重不达标")
        
        return QualityGateResult(
            step_name=self.step_name,
            status=status,
            quality_level=quality_level,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
            details={
                "factor_count": factor_count,
                "factors_calculated": factors_calculated,
                "factors_failed": factors_failed,
                "avg_coverage": avg_coverage,
                "avg_nan_ratio": avg_nan_ratio
            }
        )


class AlphaGenerationQualityGate(QualityGate):
    """Alpha生成质量门控"""
    
    def __init__(self):
        super().__init__("alpha_generation")
    
    def check(
        self,
        total_stocks: int,
        valid_stocks: int,
        alpha_coverage: float,
        factor_diversity: float,
        **kwargs
    ) -> QualityGateResult:
        """
        检查Alpha生成质量
        
        质量要求:
        1. 有效股票数 ≥ 3000
        2. Alpha覆盖率 ≥ 0.95
        3. 因子多样性 ≥ 0.30
        """
        metrics = []
        errors = []
        warnings = []
        
        metrics.append(self._create_metric(
            "有效股票数",
            valid_stocks,
            3000,
            higher_is_better=True
        ))
        
        metrics.append(self._create_metric(
            "Alpha覆盖率",
            alpha_coverage,
            0.95,
            higher_is_better=True
        ))
        
        metrics.append(self._create_metric(
            "因子多样性",
            factor_diversity,
            0.30,
            higher_is_better=True
        ))
        
        passed_count = sum(1 for m in metrics if m.passed)
        
        if passed_count == 3:
            status = GateStatus.PASS
            quality_level = QualityLevel.EXCELLENT
        elif passed_count == 2:
            status = GateStatus.WARNING
            quality_level = QualityLevel.GOOD
            warnings.append("部分指标未达标")
        elif passed_count == 1:
            status = GateStatus.WARNING
            quality_level = QualityLevel.ACCEPTABLE
            warnings.append("多项指标未达标")
        else:
            status = GateStatus.FAIL
            quality_level = QualityLevel.FAILED
            errors.append("Alpha生成质量严重不达标")
        
        return QualityGateResult(
            step_name=self.step_name,
            status=status,
            quality_level=quality_level,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
            details={
                "total_stocks": total_stocks,
                "valid_stocks": valid_stocks,
                "alpha_coverage": alpha_coverage,
                "factor_diversity": factor_diversity
            }
        )


class BacktestQualityGate(QualityGate):
    """回测质量门控"""
    
    def __init__(self):
        super().__init__("backtest")
    
    def check(
        self,
        sharpe_ratio: float,
        max_drawdown: float,
        win_rate: float,
        annual_return: float,
        total_trades: int,
        **kwargs
    ) -> QualityGateResult:
        """
        检查回测质量
        
        质量要求:
        1. 夏普比率 ≥ 1.5
        2. 最大回撤 ≤ 0.30
        3. 胜率 ≥ 0.50
        4. 年化收益 ≥ 0.10
        5. 交易次数 ≥ 50
        """
        metrics = []
        errors = []
        warnings = []
        
        metrics.append(self._create_metric(
            "夏普比率",
            sharpe_ratio,
            1.5,
            higher_is_better=True
        ))
        
        metrics.append(self._create_metric(
            "最大回撤",
            max_drawdown,
            0.30,
            higher_is_better=False
        ))
        
        metrics.append(self._create_metric(
            "胜率",
            win_rate,
            0.50,
            higher_is_better=True
        ))
        
        metrics.append(self._create_metric(
            "年化收益",
            annual_return,
            0.10,
            higher_is_better=True
        ))
        
        metrics.append(self._create_metric(
            "交易次数",
            total_trades,
            50,
            higher_is_better=True
        ))
        
        passed_count = sum(1 for m in metrics if m.passed)
        
        if passed_count == 5:
            status = GateStatus.PASS
            quality_level = QualityLevel.EXCELLENT
        elif passed_count >= 4:
            status = GateStatus.WARNING
            quality_level = QualityLevel.GOOD
            warnings.append("部分指标未达标")
        elif passed_count >= 3:
            status = GateStatus.WARNING
            quality_level = QualityLevel.ACCEPTABLE
            warnings.append("多项指标未达标")
        else:
            status = GateStatus.FAIL
            quality_level = QualityLevel.FAILED
            errors.append("回测质量严重不达标")
        
        return QualityGateResult(
            step_name=self.step_name,
            status=status,
            quality_level=quality_level,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
            details={
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "win_rate": win_rate,
                "annual_return": annual_return,
                "total_trades": total_trades
            }
        )


class PortfolioOptimizationQualityGate(QualityGate):
    """组合优化质量门控"""
    
    def __init__(self):
        super().__init__("portfolio_optimization")
    
    def check(
        self,
        stock_count: int,
        max_weight: float,
        min_weight: float,
        weight_sum: float,
        concentration: float,
        **kwargs
    ) -> QualityGateResult:
        """
        检查组合优化质量
        
        质量要求:
        1. 股票数量 ≥ 20
        2. 最大权重 ≤ 0.15
        3. 最小权重 ≥ 0.01
        4. 权重和 = 1.0 (误差 ≤ 0.01)
        5. 集中度 ≤ 0.30
        """
        metrics = []
        errors = []
        warnings = []
        
        metrics.append(self._create_metric(
            "股票数量",
            stock_count,
            20,
            higher_is_better=True
        ))
        
        metrics.append(self._create_metric(
            "最大权重",
            max_weight,
            0.15,
            higher_is_better=False
        ))
        
        metrics.append(self._create_metric(
            "最小权重",
            min_weight,
            0.01,
            higher_is_better=True
        ))
        
        weight_sum_error = abs(weight_sum - 1.0)
        metrics.append(self._create_metric(
            "权重和误差",
            weight_sum_error,
            0.01,
            higher_is_better=False
        ))
        
        metrics.append(self._create_metric(
            "集中度",
            concentration,
            0.30,
            higher_is_better=False
        ))
        
        passed_count = sum(1 for m in metrics if m.passed)
        
        if passed_count == 5:
            status = GateStatus.PASS
            quality_level = QualityLevel.EXCELLENT
        elif passed_count >= 4:
            status = GateStatus.WARNING
            quality_level = QualityLevel.GOOD
            warnings.append("部分指标未达标")
        elif passed_count >= 3:
            status = GateStatus.WARNING
            quality_level = QualityLevel.ACCEPTABLE
            warnings.append("多项指标未达标")
        else:
            status = GateStatus.FAIL
            quality_level = QualityLevel.FAILED
            errors.append("组合优化质量严重不达标")
        
        return QualityGateResult(
            step_name=self.step_name,
            status=status,
            quality_level=quality_level,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
            details={
                "stock_count": stock_count,
                "max_weight": max_weight,
                "min_weight": min_weight,
                "weight_sum": weight_sum,
                "concentration": concentration
            }
        )


class RiskCheckQualityGate(QualityGate):
    """风控检查质量门控"""
    
    def __init__(self):
        super().__init__("risk_check")
    
    def check(
        self,
        violations: int,
        warnings_count: int,
        risk_score: float,
        **kwargs
    ) -> QualityGateResult:
        """
        检查风控质量
        
        质量要求:
        1. 违规次数 = 0
        2. 警告次数 ≤ 3
        3. 风险得分 ≥ 0.80
        """
        metrics = []
        errors = []
        warnings = []
        
        metrics.append(self._create_metric(
            "违规次数",
            violations,
            0,
            higher_is_better=False
        ))
        
        metrics.append(self._create_metric(
            "警告次数",
            warnings_count,
            3,
            higher_is_better=False
        ))
        
        metrics.append(self._create_metric(
            "风险得分",
            risk_score,
            0.80,
            higher_is_better=True
        ))
        
        passed_count = sum(1 for m in metrics if m.passed)
        
        if passed_count == 3:
            status = GateStatus.PASS
            quality_level = QualityLevel.EXCELLENT
        elif passed_count >= 2:
            status = GateStatus.WARNING
            quality_level = QualityLevel.GOOD
            warnings.append("部分指标未达标")
        elif passed_count >= 1:
            status = GateStatus.WARNING
            quality_level = QualityLevel.ACCEPTABLE
            warnings.append("多项指标未达标")
        else:
            status = GateStatus.FAIL
            quality_level = QualityLevel.FAILED
            errors.append("风控检查严重不达标")
        
        return QualityGateResult(
            step_name=self.step_name,
            status=status,
            quality_level=quality_level,
            metrics=metrics,
            errors=errors,
            warnings=warnings,
            details={
                "violations": violations,
                "warnings_count": warnings_count,
                "risk_score": risk_score
            }
        )


class PipelineQualityManager:
    """管线质量管理器"""
    
    def __init__(self):
        self.gates = {
            "data_update": DataUpdateQualityGate(),
            "factor_calculation": FactorCalculationQualityGate(),
            "alpha_generation": AlphaGenerationQualityGate(),
            "backtest": BacktestQualityGate(),
            "portfolio_optimization": PortfolioOptimizationQualityGate(),
            "risk_check": RiskCheckQualityGate()
        }
        self.results: Dict[str, QualityGateResult] = {}
        self.logger = get_logger("pipeline.quality_manager")
    
    def check_step(self, step_name: str, **kwargs) -> QualityGateResult:
        """检查单个步骤"""
        if step_name not in self.gates:
            self.logger.error(f"未知的步骤: {step_name}")
            return QualityGateResult(
                step_name=step_name,
                status=GateStatus.FAIL,
                quality_level=QualityLevel.FAILED,
                errors=[f"未知的步骤: {step_name}"]
            )
        
        result = self.gates[step_name].check(**kwargs)
        self.results[step_name] = result
        
        self.logger.info(
            f"步骤 {step_name} 质量检查: {result.status.value} "
            f"(等级: {result.quality_level.value})"
        )
        
        if result.errors:
            for error in result.errors:
                self.logger.error(f"  错误: {error}")
        
        if result.warnings:
            for warning in result.warnings:
                self.logger.warning(f"  警告: {warning}")
        
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """获取质量检查摘要"""
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r.is_pass())
        failed = total - passed
        
        return {
            "total_steps": total,
            "passed_steps": passed,
            "failed_steps": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "results": {name: result.to_dict() for name, result in self.results.items()}
        }
    
    def is_all_passed(self) -> bool:
        """检查是否所有步骤都通过"""
        return all(r.is_pass() for r in self.results.values())


def get_quality_manager() -> PipelineQualityManager:
    """获取质量管理器实例"""
    return PipelineQualityManager()
