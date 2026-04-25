"""
推送前置检查器

在推送前强制检查所有前置条件，包括：
1. 策略质量指标（胜率、IC、IR、夏普比率等）
2. 前置操作完成状态
3. 风控指标合规性

任何一项不通过，必须重新执行前置步骤后才能推送。
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class CheckSeverity(Enum):
    """检查严重程度"""
    CRITICAL = "critical"    # 必须通过，否则禁止推送
    WARNING = "warning"      # 警告，可以推送但需确认
    INFO = "info"            # 信息性检查


@dataclass
class CheckItem:
    """检查项"""
    id: str
    name: str
    severity: CheckSeverity
    passed: bool = False
    actual_value: Any = None
    expected_value: Any = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PrePushCheckResult:
    """推送前置检查结果"""
    passed: bool
    critical_failures: List[CheckItem] = field(default_factory=list)
    warnings: List[CheckItem] = field(default_factory=list)
    all_checks: List[CheckItem] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    retry_required: bool = False
    retry_layers: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "critical_failures": [self._item_to_dict(i) for i in self.critical_failures],
            "warnings": [self._item_to_dict(i) for i in self.warnings],
            "all_checks": [self._item_to_dict(i) for i in self.all_checks],
            "timestamp": self.timestamp,
            "retry_required": self.retry_required,
            "retry_layers": self.retry_layers
        }
    
    def _item_to_dict(self, item: CheckItem) -> Dict[str, Any]:
        return {
            "id": item.id,
            "name": item.name,
            "severity": item.severity.value,
            "passed": item.passed,
            "actual_value": str(item.actual_value),
            "expected_value": str(item.expected_value),
            "message": item.message
        }


class PrePushChecker:
    """
    推送前置检查器
    
    强制检查所有推送前置条件，确保推送内容可信。
    
    检查维度：
    1. 策略质量指标
       - 胜率 >= 55%
       - IC均值 >= 0.02
       - IR信息比率 >= 0.3
       - 夏普比率 >= 1.0
       - 最大回撤 <= 20%
    
    2. 前置操作完成状态
       - 数据更新完成
       - 因子计算完成
       - 信号生成完成
       - 策略执行完成
       - 组合优化完成
       - 风控检查完成
    
    3. 风控指标合规性
       - 单票权重 <= 12%
       - 行业集中度 <= 30%
       - 总仓位 <= 95%
       - 止损线设置正确
    """
    
    STRATEGY_QUALITY_CHECKS = {
        "win_rate": {
            "name": "策略胜率",
            "threshold": 0.55,
            "severity": CheckSeverity.CRITICAL,
            "compare": ">="
        },
        "ic_mean": {
            "name": "IC均值",
            "threshold": 0.02,
            "severity": CheckSeverity.CRITICAL,
            "compare": ">="
        },
        "ir_ratio": {
            "name": "IR信息比率",
            "threshold": 0.3,
            "severity": CheckSeverity.CRITICAL,
            "compare": ">="
        },
        "sharpe_ratio": {
            "name": "夏普比率",
            "threshold": 1.0,
            "severity": CheckSeverity.WARNING,
            "compare": ">="
        },
        "max_drawdown": {
            "name": "最大回撤",
            "threshold": 0.20,
            "severity": CheckSeverity.CRITICAL,
            "compare": "<="
        },
        "calmar_ratio": {
            "name": "卡玛比率",
            "threshold": 1.5,
            "severity": CheckSeverity.WARNING,
            "compare": ">="
        }
    }
    
    REQUIRED_PRE_STEPS = [
        {"id": "data_update", "name": "数据更新", "layer": "data"},
        {"id": "factor_calc", "name": "因子计算", "layer": "factor"},
        {"id": "signal_gen", "name": "信号生成", "layer": "strategy"},
        {"id": "strategy_exec", "name": "策略执行", "layer": "strategy"},
        {"id": "portfolio_opt", "name": "组合优化", "layer": "portfolio"},
        {"id": "risk_check", "name": "风控检查", "layer": "risk"},
    ]
    
    RISK_CONTROL_CHECKS = {
        "max_single_weight": {
            "name": "单票权重上限",
            "threshold": 0.12,
            "severity": CheckSeverity.CRITICAL,
            "compare": "<="
        },
        "industry_concentration": {
            "name": "行业集中度",
            "threshold": 0.30,
            "severity": CheckSeverity.CRITICAL,
            "compare": "<="
        },
        "total_position": {
            "name": "总仓位上限",
            "threshold": 0.95,
            "severity": CheckSeverity.CRITICAL,
            "compare": "<="
        },
        "stop_loss_set": {
            "name": "止损线设置",
            "threshold": True,
            "severity": CheckSeverity.CRITICAL,
            "compare": "=="
        }
    }
    
    def __init__(
        self,
        strategy_quality_thresholds: Optional[Dict[str, float]] = None,
        custom_checks: Optional[List[Callable]] = None
    ):
        """
        初始化推送前置检查器
        
        Args:
            strategy_quality_thresholds: 自定义策略质量阈值
            custom_checks: 自定义检查函数列表
        """
        self.quality_thresholds = {**self.STRATEGY_QUALITY_CHECKS}
        if strategy_quality_thresholds:
            for key, value in strategy_quality_thresholds.items():
                if key in self.quality_thresholds:
                    self.quality_thresholds[key]["threshold"] = value
        
        self.custom_checks = custom_checks or []
        self._step_completion_status: Dict[str, bool] = {}
    
    def check_all(
        self,
        strategy_metrics: Optional[Dict[str, float]] = None,
        pre_step_status: Optional[Dict[str, bool]] = None,
        risk_metrics: Optional[Dict[str, Any]] = None
    ) -> PrePushCheckResult:
        """
        执行所有推送前置检查
        
        Args:
            strategy_metrics: 策略质量指标
            pre_step_status: 前置步骤完成状态
            risk_metrics: 风控指标
            
        Returns:
            PrePushCheckResult: 检查结果
        """
        all_checks: List[CheckItem] = []
        critical_failures: List[CheckItem] = []
        warnings: List[CheckItem] = []
        
        strategy_metrics = strategy_metrics or {}
        pre_step_status = pre_step_status or {}
        risk_metrics = risk_metrics or {}
        
        for check_id, check_info in self._check_strategy_quality(strategy_metrics).items():
            all_checks.append(check_info)
            if not check_info.passed:
                if check_info.severity == CheckSeverity.CRITICAL:
                    critical_failures.append(check_info)
                else:
                    warnings.append(check_info)
        
        step_result = self._check_pre_steps(pre_step_status)
        for check_id, check_info in step_result.items():
            all_checks.append(check_info)
            if not check_info.passed:
                critical_failures.append(check_info)
        
        for check_id, check_info in self._check_risk_controls(risk_metrics).items():
            all_checks.append(check_info)
            if not check_info.passed:
                if check_info.severity == CheckSeverity.CRITICAL:
                    critical_failures.append(check_info)
                else:
                    warnings.append(check_info)
        
        for custom_check in self.custom_checks:
            try:
                check_item = custom_check()
                if isinstance(check_item, CheckItem):
                    all_checks.append(check_item)
                    if not check_item.passed:
                        if check_item.severity == CheckSeverity.CRITICAL:
                            critical_failures.append(check_item)
                        else:
                            warnings.append(check_item)
            except Exception as e:
                check_item = CheckItem(
                    id="custom_check_error",
                    name="自定义检查异常",
                    severity=CheckSeverity.WARNING,
                    passed=False,
                    message=str(e)
                )
                all_checks.append(check_item)
                warnings.append(check_item)
        
        retry_layers = self._determine_retry_layers(critical_failures, pre_step_status)
        
        return PrePushCheckResult(
            passed=len(critical_failures) == 0,
            critical_failures=critical_failures,
            warnings=warnings,
            all_checks=all_checks,
            retry_required=len(retry_layers) > 0,
            retry_layers=retry_layers
        )
    
    def _check_strategy_quality(self, metrics: Dict[str, float]) -> Dict[str, CheckItem]:
        """检查策略质量指标"""
        results = {}
        
        for check_id, check_info in self.STRATEGY_QUALITY_CHECKS.items():
            actual_value = metrics.get(check_id)
            threshold = check_info["threshold"]
            
            if actual_value is None:
                passed = False
                message = f"{check_info['name']}: 数据缺失"
            else:
                if check_info["compare"] == ">=":
                    passed = actual_value >= threshold
                elif check_info["compare"] == "<=":
                    passed = actual_value <= threshold
                else:
                    passed = actual_value == threshold
                
                message = f"{check_info['name']}: {actual_value:.4f} (要求{check_info['compare']}{threshold})"
            
            results[check_id] = CheckItem(
                id=check_id,
                name=check_info["name"],
                severity=check_info["severity"],
                passed=passed,
                actual_value=actual_value,
                expected_value=f"{check_info['compare']}{threshold}",
                message=message
            )
        
        return results
    
    def _check_pre_steps(self, step_status: Dict[str, bool]) -> Dict[str, CheckItem]:
        """检查前置步骤完成状态"""
        results = {}
        
        for step in self.REQUIRED_PRE_STEPS:
            step_id = step["id"]
            passed = step_status.get(step_id, False)
            
            results[step_id] = CheckItem(
                id=step_id,
                name=step["name"],
                severity=CheckSeverity.CRITICAL,
                passed=passed,
                actual_value="完成" if passed else "未完成",
                expected_value="完成",
                message=f"{step['name']}: {'✓ 已完成' if passed else '✗ 未完成'}",
                details={"layer": step["layer"]}
            )
        
        return results
    
    def _check_risk_controls(self, metrics: Dict[str, Any]) -> Dict[str, CheckItem]:
        """检查风控指标"""
        results = {}
        
        for check_id, check_info in self.RISK_CONTROL_CHECKS.items():
            actual_value = metrics.get(check_id)
            threshold = check_info["threshold"]
            
            if actual_value is None:
                passed = False
                message = f"{check_info['name']}: 数据缺失"
            else:
                if check_info["compare"] == ">=":
                    passed = actual_value >= threshold
                elif check_info["compare"] == "<=":
                    passed = actual_value <= threshold
                else:
                    passed = actual_value == threshold
                
                if isinstance(threshold, float):
                    message = f"{check_info['name']}: {actual_value:.2%} (要求{check_info['compare']}{threshold:.0%})"
                else:
                    message = f"{check_info['name']}: {actual_value} (要求{check_info['compare']}{threshold})"
            
            results[check_id] = CheckItem(
                id=check_id,
                name=check_info["name"],
                severity=check_info["severity"],
                passed=passed,
                actual_value=actual_value,
                expected_value=f"{check_info['compare']}{threshold}",
                message=message
            )
        
        return results
    
    def _determine_retry_layers(
        self,
        failures: List[CheckItem],
        step_status: Dict[str, bool]
    ) -> List[str]:
        """确定需要重试的层级"""
        retry_layers = set()
        
        for failure in failures:
            for step in self.REQUIRED_PRE_STEPS:
                if failure.id == step["id"]:
                    retry_layers.add(step["layer"])
                    break
            
            if failure.id in ["win_rate", "ic_mean", "ir_ratio", "sharpe_ratio"]:
                retry_layers.add("factor")
                retry_layers.add("strategy")
            
            if failure.id in ["max_single_weight", "industry_concentration", "total_position"]:
                retry_layers.add("portfolio")
                retry_layers.add("risk")
        
        layer_order = ["data", "factor", "strategy", "portfolio", "risk"]
        return [layer for layer in layer_order if layer in retry_layers]
    
    def mark_step_completed(self, step_id: str):
        """标记步骤完成"""
        self._step_completion_status[step_id] = True
    
    def mark_step_failed(self, step_id: str):
        """标记步骤失败"""
        self._step_completion_status[step_id] = False
    
    def get_step_status(self) -> Dict[str, bool]:
        """获取所有步骤状态"""
        return self._step_completion_status.copy()
    
    def reset(self):
        """重置状态"""
        self._step_completion_status.clear()


_default_pre_push_checker: Optional[PrePushChecker] = None


def get_pre_push_checker() -> PrePushChecker:
    """获取全局推送前置检查器"""
    global _default_pre_push_checker
    if _default_pre_push_checker is None:
        _default_pre_push_checker = PrePushChecker()
    return _default_pre_push_checker


def reset_pre_push_checker():
    """重置全局推送前置检查器"""
    global _default_pre_push_checker
    _default_pre_push_checker = None
