"""
质量控制门槛模块

在关键节点强制验证，确保每个阶段输出符合质量标准。
验证失败时记录警告，允许用户在了解风险的情况下继续操作。
所有操作都有完整的审计追溯，支持回滚和恢复。

关键节点：
1. 因子入库 - 验证因子质量
2. Alpha生成 - 验证因子组合质量
3. 策略创建 - 验证Alpha有效性
4. 回测验证 - 验证策略表现
5. 实盘准入 - 验证所有前置条件

作者: 陈默 (WildQuest Capital)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import json
from pathlib import Path


class GateStage(Enum):
    """门槛阶段"""
    FACTOR_REGISTRATION = "factor_registration"
    ALPHA_GENERATION = "alpha_generation"
    STRATEGY_CREATION = "strategy_creation"
    BACKTEST_VALIDATION = "backtest_validation"
    LIVE_TRADING = "live_trading"


class ValidationStatus(Enum):
    """验证状态"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    OVERRIDE = "override"


@dataclass
class ValidationRule:
    """验证规则"""
    rule_id: str
    rule_name: str
    stage: GateStage
    description: str
    check_func: callable
    error_message: str
    is_blocking: bool = True
    allow_override: bool = True
    threshold: Optional[float] = None


@dataclass
class ValidationResult:
    """验证结果"""
    rule_id: str
    rule_name: str
    status: ValidationStatus
    message: str
    actual_value: Optional[float] = None
    threshold: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    override_reason: Optional[str] = None


@dataclass
class GateResult:
    """门槛验证结果"""
    stage: GateStage
    passed: bool
    results: List[ValidationResult] = field(default_factory=list)
    blocking_failures: List[ValidationResult] = field(default_factory=list)
    warnings: List[ValidationResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    override_allowed: bool = True
    override_reason: Optional[str] = None
    overridden_by: Optional[str] = None
    overridden_at: Optional[datetime] = None
    
    def add_result(self, result: ValidationResult):
        """添加验证结果"""
        self.results.append(result)
        
        if result.status == ValidationStatus.FAIL:
            self.blocking_failures.append(result)
            self.passed = False
        elif result.status == ValidationStatus.WARNING:
            self.warnings.append(result)
        
        if not result.details.get('allow_override', True):
            self.override_allowed = False
    
    def can_override(self) -> bool:
        """检查是否允许强制继续"""
        return self.override_allowed and len(self.blocking_failures) > 0
    
    def override(self, reason: str, user: str = "system"):
        """强制继续（记录原因和操作人）"""
        self.override_reason = reason
        self.overridden_by = user
        self.overridden_at = datetime.now()
        self.passed = True
        
        for result in self.blocking_failures:
            result.status = ValidationStatus.OVERRIDE
            result.override_reason = reason
    
    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        return {
            "stage": self.stage.value,
            "passed": self.passed,
            "total_rules": len(self.results),
            "passed_rules": sum(1 for r in self.results if r.status == ValidationStatus.PASS),
            "failed_rules": len(self.blocking_failures),
            "warning_rules": len(self.warnings),
            "override_allowed": self.override_allowed,
            "override_reason": self.override_reason,
            "overridden_by": self.overridden_by,
            "overridden_at": self.overridden_at.isoformat() if self.overridden_at else None,
            "timestamp": self.timestamp.isoformat()
        }


class QualityGate:
    """
    质量门槛验证器
    
    在关键节点强制验证，确保每个阶段输出符合质量标准。
    """
    
    def __init__(self):
        """初始化质量门槛"""
        self._rules: Dict[GateStage, List[ValidationRule]] = {
            GateStage.FACTOR_REGISTRATION: self._init_factor_rules(),
            GateStage.ALPHA_GENERATION: self._init_alpha_rules(),
            GateStage.STRATEGY_CREATION: self._init_strategy_rules(),
            GateStage.BACKTEST_VALIDATION: self._init_backtest_rules(),
            GateStage.LIVE_TRADING: self._init_live_rules()
        }
        self._audit_log: List[Dict[str, Any]] = []
    
    def _init_factor_rules(self) -> List[ValidationRule]:
        """初始化因子入库验证规则"""
        return [
            ValidationRule(
                rule_id="F001",
                rule_name="因子IC最小值",
                stage=GateStage.FACTOR_REGISTRATION,
                description="因子IC必须 >= 0.02",
                check_func=lambda metrics: metrics.get('ic_mean', -999) >= 0.02,
                error_message="因子IC不满足最小要求（需要 >= 0.02）",
                is_blocking=True,
                threshold=0.02
            ),
            ValidationRule(
                rule_id="F002",
                rule_name="因子IR最小值",
                stage=GateStage.FACTOR_REGISTRATION,
                description="因子IR必须 >= 0.3",
                check_func=lambda metrics: abs(metrics.get('ir', 0)) >= 0.3,
                error_message="因子IR不满足最小要求（需要 >= 0.3）",
                is_blocking=True,
                threshold=0.3
            ),
            ValidationRule(
                rule_id="F003",
                rule_name="因子IC非负",
                stage=GateStage.FACTOR_REGISTRATION,
                description="因子IC必须为正值",
                check_func=lambda metrics: metrics.get('ic_mean', -999) > 0,
                error_message="因子IC为负值，因子已失效",
                is_blocking=True,
                threshold=0.0
            ),
            ValidationRule(
                rule_id="F004",
                rule_name="因子胜率检查",
                stage=GateStage.FACTOR_REGISTRATION,
                description="因子胜率必须 >= 50%",
                check_func=lambda metrics: metrics.get('win_rate', 0) >= 0.50,
                error_message="因子胜率低于50%，预测能力不足",
                is_blocking=False,
                threshold=0.50
            )
        ]
    
    def _init_alpha_rules(self) -> List[ValidationRule]:
        """初始化Alpha生成验证规则"""
        return [
            ValidationRule(
                rule_id="A001",
                rule_name="因子数量最小值",
                stage=GateStage.ALPHA_GENERATION,
                description="至少需要3个有效因子",
                check_func=lambda data: len(data.get('factor_ids', [])) >= 3,
                error_message="有效因子数量不足（需要 >= 3个）",
                is_blocking=True,
                threshold=3
            ),
            ValidationRule(
                rule_id="A002",
                rule_name="平均IC最小值",
                stage=GateStage.ALPHA_GENERATION,
                description="因子组合平均IC必须 >= 0.02",
                check_func=lambda data: data.get('avg_ic', -999) >= 0.02,
                error_message="因子组合平均IC不满足要求（需要 >= 0.02）",
                is_blocking=True,
                threshold=0.02
            ),
            ValidationRule(
                rule_id="A003",
                rule_name="平均IC非负",
                stage=GateStage.ALPHA_GENERATION,
                description="因子组合平均IC必须为正值",
                check_func=lambda data: data.get('avg_ic', -999) > 0,
                error_message="因子组合平均IC为负值，Alpha预测能力为负",
                is_blocking=True,
                threshold=0.0
            ),
            ValidationRule(
                rule_id="A004",
                rule_name="负IC因子比例",
                stage=GateStage.ALPHA_GENERATION,
                description="负IC因子比例必须 < 30%",
                check_func=lambda data: data.get('negative_ic_ratio', 1.0) < 0.30,
                error_message="负IC因子比例过高（需要 < 30%）",
                is_blocking=True,
                threshold=0.30
            ),
            ValidationRule(
                rule_id="A005",
                rule_name="股票池最小值",
                stage=GateStage.ALPHA_GENERATION,
                description="Alpha预测股票数必须 >= 20",
                check_func=lambda data: len(data.get('ranked_stocks', [])) >= 20,
                error_message="Alpha预测股票数量不足（需要 >= 20）",
                is_blocking=False,
                threshold=20
            )
        ]
    
    def _init_strategy_rules(self) -> List[ValidationRule]:
        """初始化策略创建验证规则"""
        return [
            ValidationRule(
                rule_id="S001",
                rule_name="Alpha有效性验证",
                stage=GateStage.STRATEGY_CREATION,
                description="必须使用有效的Alpha预测",
                check_func=lambda data: data.get('alpha_valid', False),
                error_message="Alpha预测无效或不存在",
                is_blocking=True
            ),
            ValidationRule(
                rule_id="S002",
                rule_name="因子组合质量验证",
                stage=GateStage.STRATEGY_CREATION,
                description="因子组合平均IC必须 >= 0.02",
                check_func=lambda data: data.get('avg_ic', -999) >= 0.02,
                error_message="因子组合质量不满足要求",
                is_blocking=True,
                threshold=0.02
            ),
            ValidationRule(
                rule_id="S003",
                rule_name="回测验证状态",
                stage=GateStage.STRATEGY_CREATION,
                description="策略必须通过回测验证",
                check_func=lambda data: data.get('backtest_passed', False),
                error_message="策略未通过回测验证",
                is_blocking=False
            ),
            ValidationRule(
                rule_id="S004",
                rule_name="风控参数完整性",
                stage=GateStage.STRATEGY_CREATION,
                description="风控参数必须完整设置",
                check_func=lambda data: all([
                    data.get('max_single_weight'),
                    data.get('max_industry_weight'),
                    data.get('stop_loss'),
                    data.get('take_profit')
                ]),
                error_message="风控参数不完整",
                is_blocking=True
            )
        ]
    
    def _init_backtest_rules(self) -> List[ValidationRule]:
        """初始化回测验证规则"""
        return [
            ValidationRule(
                rule_id="B001",
                rule_name="年化收益率最小值",
                stage=GateStage.BACKTEST_VALIDATION,
                description="年化收益率必须 >= 8%",
                check_func=lambda data: data.get('annual_return', 0) >= 0.08,
                error_message="年化收益率不满足要求（需要 >= 8%）",
                is_blocking=True,
                threshold=0.08
            ),
            ValidationRule(
                rule_id="B002",
                rule_name="夏普比率最小值",
                stage=GateStage.BACKTEST_VALIDATION,
                description="夏普比率必须 >= 1.0",
                check_func=lambda data: data.get('sharpe_ratio', 0) >= 1.0,
                error_message="夏普比率不满足要求（需要 >= 1.0）",
                is_blocking=True,
                threshold=1.0
            ),
            ValidationRule(
                rule_id="B003",
                rule_name="最大回撤限制",
                stage=GateStage.BACKTEST_VALIDATION,
                description="最大回撤必须 >= -20%",
                check_func=lambda data: data.get('max_drawdown', -999) >= -0.20,
                error_message="最大回撤超过限制（需要 >= -20%）",
                is_blocking=True,
                threshold=-0.20
            ),
            ValidationRule(
                rule_id="B004",
                rule_name="胜率最小值",
                stage=GateStage.BACKTEST_VALIDATION,
                description="胜率必须 >= 55%",
                check_func=lambda data: data.get('win_rate', 0) >= 0.55,
                error_message="胜率不满足要求（需要 >= 55%）",
                is_blocking=False,
                threshold=0.55
            ),
            ValidationRule(
                rule_id="B005",
                rule_name="回测样本量",
                stage=GateStage.BACKTEST_VALIDATION,
                description="回测交易次数必须 >= 50",
                check_func=lambda data: data.get('total_trades', 0) >= 50,
                error_message="回测样本量不足（需要 >= 50次交易）",
                is_blocking=True,
                threshold=50
            )
        ]
    
    def _init_live_rules(self) -> List[ValidationRule]:
        """初始化实盘准入验证规则"""
        return [
            ValidationRule(
                rule_id="L001",
                rule_name="回测验证通过",
                stage=GateStage.LIVE_TRADING,
                description="必须通过回测验证",
                check_func=lambda data: data.get('backtest_passed', False),
                error_message="未通过回测验证，禁止实盘",
                is_blocking=True
            ),
            ValidationRule(
                rule_id="L002",
                rule_name="样本外验证通过",
                stage=GateStage.LIVE_TRADING,
                description="必须通过样本外验证",
                check_func=lambda data: data.get('oos_passed', False),
                error_message="未通过样本外验证，禁止实盘",
                is_blocking=True
            ),
            ValidationRule(
                rule_id="L003",
                rule_name="风控参数验证",
                stage=GateStage.LIVE_TRADING,
                description="风控参数必须符合HardLimits",
                check_func=lambda data: data.get('risk_params_valid', False),
                error_message="风控参数不符合要求",
                is_blocking=True
            ),
            ValidationRule(
                rule_id="L004",
                rule_name="审计日志完整",
                stage=GateStage.LIVE_TRADING,
                description="必须有完整的审计日志",
                check_func=lambda data: data.get('audit_log_complete', False),
                error_message="审计日志不完整",
                is_blocking=True
            ),
            ValidationRule(
                rule_id="L005",
                rule_name="多级审批通过",
                stage=GateStage.LIVE_TRADING,
                description="必须通过多级审批",
                check_func=lambda data: data.get('multi_approval_passed', False),
                error_message="未通过多级审批",
                is_blocking=True
            )
        ]
    
    def validate(
        self,
        stage: GateStage,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> GateResult:
        """
        执行门槛验证
        
        Args:
            stage: 验证阶段
            data: 验证数据
            context: 上下文信息
            
        Returns:
            GateResult: 验证结果
        """
        result = GateResult(stage=stage, passed=True)
        rules = self._rules.get(stage, [])
        
        for rule in rules:
            try:
                passed = rule.check_func(data)
                
                if passed:
                    validation_result = ValidationResult(
                        rule_id=rule.rule_id,
                        rule_name=rule.rule_name,
                        status=ValidationStatus.PASS,
                        message=f"✓ {rule.description}",
                        threshold=rule.threshold,
                        details={'allow_override': rule.allow_override}
                    )
                else:
                    validation_result = ValidationResult(
                        rule_id=rule.rule_id,
                        rule_name=rule.rule_name,
                        status=ValidationStatus.FAIL if rule.is_blocking else ValidationStatus.WARNING,
                        message=f"✗ {rule.error_message}",
                        threshold=rule.threshold,
                        details={'allow_override': rule.allow_override}
                    )
                
                result.add_result(validation_result)
                
            except Exception as e:
                validation_result = ValidationResult(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    status=ValidationStatus.FAIL,
                    message=f"✗ 验证异常: {str(e)}",
                    threshold=rule.threshold
                )
                result.add_result(validation_result)
        
        self._log_validation(stage, result, context)
        
        return result
    
    def _log_validation(
        self,
        stage: GateStage,
        result: GateResult,
        context: Optional[Dict[str, Any]] = None
    ):
        """记录验证日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage.value,
            "passed": result.passed,
            "summary": result.get_summary(),
            "context": context or {},
            "failures": [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "message": r.message
                }
                for r in result.blocking_failures
            ]
        }
        
        self._audit_log.append(log_entry)
        self._save_audit_log()
    
    def _save_audit_log(self):
        """保存审计日志"""
        log_dir = Path("data/quality_gates")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"gate_log_{datetime.now().strftime('%Y%m%d')}.json"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self._audit_log, f, indent=2, ensure_ascii=False)
    
    def get_rules(self, stage: GateStage) -> List[ValidationRule]:
        """获取指定阶段的验证规则"""
        return self._rules.get(stage, [])
    
    def get_audit_log(self, stage: Optional[GateStage] = None) -> List[Dict[str, Any]]:
        """获取审计日志"""
        if stage:
            return [log for log in self._audit_log if log['stage'] == stage.value]
        return self._audit_log


def get_quality_gate() -> QualityGate:
    """获取质量门槛实例"""
    return QualityGate()
