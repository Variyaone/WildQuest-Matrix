"""
因子验证调度器

管理因子验证的周期性执行，包括:
- 新因子入库强制验证
- 季度定期复检
- 衰减触发重新验证
- 样本外(OOS)强制验证

验证周期标准:
- 新因子入库: 立即验证 + 强制OOS
- 季度复检: 每季度末执行
- 衰减触发: IC下降超过阈值时触发
- 市场风格切换: 检测到regime change时触发
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import os

import pandas as pd
import numpy as np

from .registry import FactorMetadata, ValidationStatus, get_factor_registry
from .validator import FactorValidator, ValidationResult
from .enhanced_validator import EnhancedFactorValidator, EnhancedValidationResult
from .monitor import DecayLevel, FactorMonitor, get_factor_monitor
from ..infrastructure.logging import get_logger
from ..infrastructure.exceptions import FactorException


class ValidationTrigger(Enum):
    """验证触发类型"""
    NEW_FACTOR = "new_factor"
    QUARTERLY_REVIEW = "quarterly_review"
    DECAY_ALERT = "decay_alert"
    REGIME_CHANGE = "regime_change"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class ValidationLevel(Enum):
    """验证级别"""
    QUICK = "quick"
    STANDARD = "standard"
    STRICT = "strict"
    OOS_REQUIRED = "oos_required"


@dataclass
class ValidationSchedule:
    """验证计划"""
    factor_id: str
    trigger: ValidationTrigger
    level: ValidationLevel
    scheduled_date: datetime
    require_oos: bool = False
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationTaskResult:
    """验证任务结果"""
    factor_id: str
    trigger: ValidationTrigger
    success: bool
    validation_result: Optional[Any] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class ValidationReport:
    """验证报告"""
    report_date: str
    total_scheduled: int
    total_completed: int
    total_failed: int
    results: List[ValidationTaskResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class ValidationScheduler:
    """
    因子验证调度器
    
    管理因子验证的周期性执行，确保因子有效性持续监控。
    
    验证规则:
    1. 新因子入库: 必须通过验证 + OOS测试
    2. 季度复检: 每季度末对所有活跃因子复检
    3. 衰减触发: IC下降超过阈值自动触发
    4. 强制OOS: 新因子和衰减因子必须OOS验证
    """
    
    IC_DECLINE_TRIGGER_THRESHOLD = 0.15
    IR_DECLINE_TRIGGER_THRESHOLD = 0.20
    QUARTERLY_REVIEW_MONTHS = [3, 6, 9, 12]
    OOS_TRAIN_RATIO = 0.7
    
    def __init__(
        self,
        validator: Optional[FactorValidator] = None,
        enhanced_validator: Optional[EnhancedFactorValidator] = None,
        monitor: Optional[FactorMonitor] = None,
        schedule_path: Optional[str] = None
    ):
        """
        初始化验证调度器
        
        Args:
            validator: 基础验证器
            enhanced_validator: 增强验证器
            monitor: 因子监控器
            schedule_path: 调度配置路径
        """
        self._registry = get_factor_registry()
        self._validator = validator or FactorValidator()
        self._enhanced_validator = enhanced_validator
        self._monitor = monitor or get_factor_monitor()
        self.logger = get_logger("factor.validation_scheduler")
        
        self._schedule_path = schedule_path or "data/factors/validation_schedule.json"
        self._pending_schedules: List[ValidationSchedule] = []
        self._last_quarterly_review: Optional[datetime] = None
        
        self._load_schedule()
    
    def _load_schedule(self):
        """加载调度配置"""
        if os.path.exists(self._schedule_path):
            try:
                with open(self._schedule_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._last_quarterly_review = datetime.fromisoformat(
                    data.get("last_quarterly_review", "2000-01-01")
                )
                
                for item in data.get("pending", []):
                    self._pending_schedules.append(ValidationSchedule(
                        factor_id=item["factor_id"],
                        trigger=ValidationTrigger(item["trigger"]),
                        level=ValidationLevel(item["level"]),
                        scheduled_date=datetime.fromisoformat(item["scheduled_date"]),
                        require_oos=item.get("require_oos", False),
                        priority=item.get("priority", 0),
                        metadata=item.get("metadata", {})
                    ))
                
                self.logger.info(f"加载验证调度: {len(self._pending_schedules)} 个待执行任务")
            except Exception as e:
                self.logger.warning(f"加载验证调度失败: {e}")
    
    def _save_schedule(self):
        """保存调度配置"""
        try:
            os.makedirs(os.path.dirname(self._schedule_path), exist_ok=True)
            
            data = {
                "last_quarterly_review": (
                    self._last_quarterly_review.isoformat() 
                    if self._last_quarterly_review else None
                ),
                "pending": [
                    {
                        "factor_id": s.factor_id,
                        "trigger": s.trigger.value,
                        "level": s.level.value,
                        "scheduled_date": s.scheduled_date.isoformat(),
                        "require_oos": s.require_oos,
                        "priority": s.priority,
                        "metadata": s.metadata
                    }
                    for s in self._pending_schedules
                ],
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self._schedule_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存验证调度失败: {e}")
    
    def schedule_new_factor_validation(
        self,
        factor_id: str,
        priority: int = 10
    ) -> ValidationSchedule:
        """
        调度新因子验证
        
        新因子必须:
        1. 通过基础验证
        2. 通过OOS验证
        
        Args:
            factor_id: 因子ID
            priority: 优先级
            
        Returns:
            ValidationSchedule: 验证计划
        """
        schedule = ValidationSchedule(
            factor_id=factor_id,
            trigger=ValidationTrigger.NEW_FACTOR,
            level=ValidationLevel.OOS_REQUIRED,
            scheduled_date=datetime.now(),
            require_oos=True,
            priority=priority,
            metadata={"reason": "新因子入库强制验证"}
        )
        
        self._pending_schedules.append(schedule)
        self._pending_schedules.sort(key=lambda x: -x.priority)
        self._save_schedule()
        
        self.logger.info(f"调度新因子验证: {factor_id}")
        return schedule
    
    def schedule_quarterly_review(
        self,
        date: Optional[datetime] = None
    ) -> List[ValidationSchedule]:
        """
        调度季度复检
        
        每季度末对所有活跃因子进行复检
        
        Args:
            date: 调度日期
            
        Returns:
            List[ValidationSchedule]: 验证计划列表
        """
        date = date or datetime.now()
        
        if date.month not in self.QUARTERLY_REVIEW_MONTHS:
            self.logger.info(f"当前月份 {date.month} 不是季度末，跳过季度复检调度")
            return []
        
        if self._last_quarterly_review:
            months_since_last = (date.year - self._last_quarterly_review.year) * 12 + \
                                (date.month - self._last_quarterly_review.month)
            if months_since_last < 3:
                self.logger.info("距离上次季度复检不足3个月，跳过")
                return []
        
        active_factors = self._registry.list_validated()
        schedules = []
        
        for factor in active_factors:
            schedule = ValidationSchedule(
                factor_id=factor.id,
                trigger=ValidationTrigger.QUARTERLY_REVIEW,
                level=ValidationLevel.STANDARD,
                scheduled_date=date,
                require_oos=False,
                priority=5,
                metadata={"reason": "季度定期复检"}
            )
            schedules.append(schedule)
            self._pending_schedules.append(schedule)
        
        self._pending_schedules.sort(key=lambda x: -x.priority)
        self._last_quarterly_review = date
        self._save_schedule()
        
        self.logger.info(f"调度季度复检: {len(schedules)} 个因子")
        return schedules
    
    def schedule_decay_triggered_validation(
        self,
        factor_id: str,
        decay_level: DecayLevel,
        ic_change: float,
        priority: int = 8
    ) -> ValidationSchedule:
        """
        调度衰减触发的验证
        
        当因子IC下降超过阈值时触发重新验证
        
        Args:
            factor_id: 因子ID
            decay_level: 衰减等级
            ic_change: IC变化比例
            priority: 优先级
            
        Returns:
            ValidationSchedule: 验证计划
        """
        require_oos = decay_level in [DecayLevel.SEVERE, DecayLevel.CRITICAL]
        
        level = ValidationLevel.STRICT if require_oos else ValidationLevel.STANDARD
        
        schedule = ValidationSchedule(
            factor_id=factor_id,
            trigger=ValidationTrigger.DECAY_ALERT,
            level=level,
            scheduled_date=datetime.now(),
            require_oos=require_oos,
            priority=priority,
            metadata={
                "reason": "衰减触发验证",
                "decay_level": decay_level.value,
                "ic_change": ic_change
            }
        )
        
        self._pending_schedules.append(schedule)
        self._pending_schedules.sort(key=lambda x: -x.priority)
        self._save_schedule()
        
        self.logger.warning(
            f"调度衰减触发验证: {factor_id}, 衰减等级={decay_level.value}, IC变化={ic_change:.2%}"
        )
        return schedule
    
    def check_and_schedule_decay_validations(
        self,
        factor_data: Dict[str, pd.DataFrame],
        return_df: pd.DataFrame
    ) -> List[ValidationSchedule]:
        """
        检查因子衰减并调度验证
        
        Args:
            factor_data: 因子数据字典
            return_df: 收益数据
            
        Returns:
            List[ValidationSchedule]: 新调度的验证计划
        """
        report = self._monitor.monitor_all_factors(factor_data, return_df)
        
        new_schedules = []
        
        for metrics in report.factor_metrics:
            if metrics.decay_level in [DecayLevel.MODERATE, DecayLevel.SEVERE, DecayLevel.CRITICAL]:
                ic_change_ratio = metrics.ic_change / abs(metrics.historical_ic) \
                    if metrics.historical_ic != 0 else 0
                
                if abs(ic_change_ratio) >= self.IC_DECLINE_TRIGGER_THRESHOLD:
                    schedule = self.schedule_decay_triggered_validation(
                        metrics.factor_id,
                        metrics.decay_level,
                        ic_change_ratio
                    )
                    new_schedules.append(schedule)
        
        return new_schedules
    
    def execute_validation(
        self,
        schedule: ValidationSchedule,
        factor_df: pd.DataFrame,
        return_df: pd.DataFrame,
        price_df: Optional[pd.DataFrame] = None
    ) -> ValidationTaskResult:
        """
        执行验证任务
        
        Args:
            schedule: 验证计划
            factor_df: 因子数据
            return_df: 收益数据
            price_df: 价格数据（可选）
            
        Returns:
            ValidationTaskResult: 验证结果
        """
        import time
        start_time = time.time()
        
        self.logger.info(
            f"执行验证: {schedule.factor_id}, 触发={schedule.trigger.value}, "
            f"级别={schedule.level.value}, OOS={schedule.require_oos}"
        )
        
        try:
            if schedule.level == ValidationLevel.QUICK:
                result = self._validator.quick_validate(factor_df, return_df)
                success = result.get("ic_mean", 0) != 0
                
            elif schedule.level == ValidationLevel.STANDARD:
                result = self._validator.validate(
                    schedule.factor_id,
                    factor_df,
                    return_df
                )
                success = result.success
                
            elif schedule.level in [ValidationLevel.STRICT, ValidationLevel.OOS_REQUIRED]:
                if self._enhanced_validator:
                    result = self._enhanced_validator.validate_factor(
                        schedule.factor_id,
                        factor_df,
                        return_df,
                        price_df,
                        enable_oos=schedule.require_oos,
                        train_ratio=self.OOS_TRAIN_RATIO
                    )
                    success = result.success
                else:
                    result = self._validator.validate(
                        schedule.factor_id,
                        factor_df,
                        return_df
                    )
                    success = result.success
            else:
                result = self._validator.validate(
                    schedule.factor_id,
                    factor_df,
                    return_df
                )
                success = result.success
            
            self._update_factor_validation_status(
                schedule.factor_id,
                success,
                schedule.require_oos
            )
            
            duration = time.time() - start_time
            
            self.logger.info(
                f"验证完成: {schedule.factor_id}, 成功={success}, 耗时={duration:.2f}秒"
            )
            
            return ValidationTaskResult(
                factor_id=schedule.factor_id,
                trigger=schedule.trigger,
                success=success,
                validation_result=result,
                duration_seconds=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"验证失败: {schedule.factor_id}, 错误={e}")
            
            return ValidationTaskResult(
                factor_id=schedule.factor_id,
                trigger=schedule.trigger,
                success=False,
                error_message=str(e),
                duration_seconds=duration
            )
    
    def execute_pending_validations(
        self,
        factor_data: Dict[str, pd.DataFrame],
        return_df: pd.DataFrame,
        price_df: Optional[pd.DataFrame] = None,
        max_tasks: int = 50
    ) -> ValidationReport:
        """
        执行待处理的验证任务
        
        Args:
            factor_data: 因子数据字典
            return_df: 收益数据
            price_df: 价格数据
            max_tasks: 最大执行任务数
            
        Returns:
            ValidationReport: 验证报告
        """
        results = []
        completed = 0
        failed = 0
        
        tasks_to_execute = self._pending_schedules[:max_tasks]
        
        for schedule in tasks_to_execute:
            if schedule.factor_id not in factor_data:
                self.logger.warning(f"因子数据不存在: {schedule.factor_id}")
                continue
            
            result = self.execute_validation(
                schedule,
                factor_data[schedule.factor_id],
                return_df,
                price_df
            )
            
            results.append(result)
            
            if result.success:
                completed += 1
            else:
                failed += 1
            
            self._pending_schedules.remove(schedule)
        
        self._save_schedule()
        
        summary = self._generate_summary(results)
        
        return ValidationReport(
            report_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_scheduled=len(tasks_to_execute),
            total_completed=completed,
            total_failed=failed,
            results=results,
            summary=summary
        )
    
    def _update_factor_validation_status(
        self,
        factor_id: str,
        success: bool,
        oos_validated: bool
    ):
        """
        更新因子验证状态
        
        Args:
            factor_id: 因子ID
            success: 验证是否成功
            oos_validated: 是否通过OOS验证
        """
        factor = self._registry.get(factor_id)
        if factor is None:
            return
        
        if success:
            if oos_validated:
                new_status = ValidationStatus.VALIDATED_OOS
            else:
                new_status = ValidationStatus.VALIDATED
        else:
            new_status = ValidationStatus.FAILED
        
        factor.validation_status = new_status
        factor.last_validated = datetime.now()
        
        self._registry.update(factor)
    
    def _generate_summary(
        self,
        results: List[ValidationTaskResult]
    ) -> Dict[str, Any]:
        """生成验证摘要"""
        by_trigger = {}
        by_level = {}
        
        for r in results:
            trigger = r.trigger.value
            by_trigger[trigger] = by_trigger.get(trigger, 0) + 1
            
            if r.success:
                by_level["passed"] = by_level.get("passed", 0) + 1
            else:
                by_level["failed"] = by_level.get("failed", 0) + 1
        
        return {
            "by_trigger": by_trigger,
            "by_level": by_level,
            "success_rate": (
                by_level.get("passed", 0) / len(results) * 100 
                if results else 0
            )
        }
    
    def get_pending_count(self) -> int:
        """获取待处理验证任务数"""
        return len(self._pending_schedules)
    
    def get_next_scheduled(self, n: int = 10) -> List[ValidationSchedule]:
        """获取下一个待执行的验证任务"""
        return self._pending_schedules[:n]
    
    def clear_pending(self):
        """清空待处理任务"""
        self._pending_schedules.clear()
        self._save_schedule()


_default_scheduler: Optional[ValidationScheduler] = None


def get_validation_scheduler() -> ValidationScheduler:
    """获取全局验证调度器实例"""
    global _default_scheduler
    if _default_scheduler is None:
        _default_scheduler = ValidationScheduler()
    return _default_scheduler


def reset_validation_scheduler():
    """重置全局验证调度器"""
    global _default_scheduler
    _default_scheduler = None
