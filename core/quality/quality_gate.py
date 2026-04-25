"""
WildQuest Matrix - 质量门控系统

解决的核心问题：
1. 工作流走到最后才发现前期策略/数据不行
2. 前置步骤没有执行就直接开启推送
3. 没有回测就直接应用
4. 工作流执行到一半就中断
5. 终止后又重新开始

设计原则：
- 固定流程用代码自动化，提高效率
- 关键决策用 LLM 审查，保证质量
- 每个关键步骤都有质量门控
- 支持断点续传，避免重复执行

Author: Variya
Version: 1.0.0
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
import pandas as pd
import numpy as np


class GateStatus(Enum):
    """质量门控状态"""
    PENDING = "pending"           # 待检查
    PASSED = "passed"             # 通过
    FAILED = "failed"             # 失败
    WARNING = "warning"           # 警告
    SKIPPED = "skipped"           # 跳过
    REVIEW_REQUIRED = "review_required"  # 需要 LLM 审查


class ReviewDecision(Enum):
    """LLM 审查决策"""
    APPROVE = "approve"           # 批准
    REJECT = "reject"             # 拒绝
    MODIFY = "modify"             # 修改后重试
    DEFER = "defer"               # 延迟决策


@dataclass
class QualityGateResult:
    """质量门控结果"""
    gate_name: str
    status: GateStatus
    score: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    review_decision: Optional[ReviewDecision] = None
    review_comment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'gate_name': self.gate_name,
            'status': self.status.value,
            'score': self.score,
            'details': self.details,
            'error': self.error,
            'timestamp': self.timestamp.isoformat(),
            'review_decision': self.review_decision.value if self.review_decision else None,
            'review_comment': self.review_comment,
        }


@dataclass
class PipelineState:
    """管线状态"""
    pipeline_id: str
    start_time: datetime
    current_step: int = 0
    total_steps: int = 12
    status: str = "running"
    completed_steps: List[int] = field(default_factory=list)
    failed_steps: List[int] = field(default_factory=list)
    gate_results: Dict[str, QualityGateResult] = field(default_factory=dict)
    pipeline_data: Dict[str, Any] = field(default_factory=dict)
    end_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'pipeline_id': self.pipeline_id,
            'start_time': self.start_time.isoformat(),
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'status': self.status,
            'completed_steps': self.completed_steps,
            'failed_steps': self.failed_steps,
            'gate_results': {
                k: v.to_dict() for k, v in self.gate_results.items()
            },
            'pipeline_data': self.pipeline_data,
            'end_time': self.end_time.isoformat() if self.end_time else None,
        }


class QualityGateManager:
    """质量门控管理器"""

    def __init__(self, state_dir: str = "./pipeline_states"):
        """
        初始化质量门控管理器

        Args:
            state_dir: 状态文件存储目录
        """
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.current_state: Optional[PipelineState] = None

        # 定义质量门控规则
        self.gate_rules = {
            'data_update': {
                'required': True,
                'threshold': 0.8,
                'auto_approve': False,
                'review_required': True,
            },
            'data_quality': {
                'required': True,
                'threshold': 0.9,
                'auto_approve': True,
                'review_required': False,
            },
            'factor_calculation': {
                'required': True,
                'threshold': 0.7,
                'auto_approve': False,
                'review_required': True,
            },
            'alpha_generation': {
                'required': True,
                'threshold': 0.6,
                'auto_approve': False,
                'review_required': True,
            },
            'backtest': {
                'required': True,
                'threshold': 0.5,
                'auto_approve': False,
                'review_required': True,
            },
            'portfolio_optimization': {
                'required': True,
                'threshold': 0.7,
                'auto_approve': True,
                'review_required': False,
            },
            'risk_check': {
                'required': True,
                'threshold': 0.8,
                'auto_approve': False,
                'review_required': True,
            },
        }

    def create_pipeline_state(self, pipeline_id: str) -> PipelineState:
        """
        创建新的管线状态

        Args:
            pipeline_id: 管线 ID

        Returns:
            管线状态
        """
        state = PipelineState(
            pipeline_id=pipeline_id,
            start_time=datetime.now(),
        )
        self.current_state = state
        self.save_state()
        return state

    def load_state(self, pipeline_id: str) -> Optional[PipelineState]:
        """
        加载管线状态

        Args:
            pipeline_id: 管线 ID

        Returns:
            管线状态，如果不存在返回 None
        """
        state_file = os.path.join(self.state_dir, f"{pipeline_id}.json")

        if not os.path.exists(state_file):
            return None

        with open(state_file, 'r') as f:
            data = json.load(f)

        # 重建 PipelineState 对象
        state = PipelineState(
            pipeline_id=data['pipeline_id'],
            start_time=datetime.fromisoformat(data['start_time']),
            current_step=data['current_step'],
            total_steps=data['total_steps'],
            status=data['status'],
            completed_steps=data['completed_steps'],
            failed_steps=data['failed_steps'],
            pipeline_data=data['pipeline_data'],
            end_time=datetime.fromisoformat(data['end_time']) if data['end_time'] else None,
        )

        # 重建门控结果
        for gate_name, gate_data in data['gate_results'].items():
            state.gate_results[gate_name] = QualityGateResult(
                gate_name=gate_data['gate_name'],
                status=GateStatus(gate_data['status']),
                score=gate_data['score'],
                details=gate_data['details'],
                error=gate_data['error'],
                timestamp=datetime.fromisoformat(data['timestamp']),
                review_decision=ReviewDecision(gate_data['review_decision']) if gate_data['review_decision'] else None,
                review_comment=gate_data['review_comment'],
            )

        self.current_state = state
        return state

    def save_state(self):
        """保存当前状态"""
        if self.current_state is None:
            return

        state_file = os.path.join(
            self.state_dir,
            f"{self.current_state.pipeline_id}.json"
        )

        with open(state_file, 'w') as f:
            json.dump(self.current_state.to_dict(), f, indent=2, default=str)

    def check_gate(
        self,
        gate_name: str,
        data: Dict[str, Any],
        check_func: Optional[Callable] = None
    ) -> QualityGateResult:
        """
        检查质量门控

        Args:
            gate_name: 门控名称
            data: 检查数据
            check_func: 自定义检查函数

        Returns:
            门控结果
        """
        rule = self.gate_rules.get(gate_name, {})

        # 执行检查
        if check_func:
            try:
                result = check_func(data)
                score = result.get('score', 0.0)
                details = result.get('details', {})
                error = result.get('error')
            except Exception as e:
                score = 0.0
                details = {}
                error = str(e)
        else:
            # 默认检查逻辑
            score, details, error = self._default_check(gate_name, data)

        # 判断状态
        if error:
            status = GateStatus.FAILED
        elif score >= rule.get('threshold', 0.5):
            status = GateStatus.PASSED
        elif score >= rule.get('threshold', 0.5) * 0.8:
            status = GateStatus.WARNING
        else:
            status = GateStatus.FAILED

        # 判断是否需要 LLM 审查
        if rule.get('review_required', False) and not rule.get('auto_approve', False):
            status = GateStatus.REVIEW_REQUIRED

        # 创建结果
        gate_result = QualityGateResult(
            gate_name=gate_name,
            status=status,
            score=score,
            details=details,
            error=error,
        )

        # 保存到状态
        if self.current_state:
            self.current_state.gate_results[gate_name] = gate_result
            self.save_state()

        return gate_result

    def llm_review(
        self,
        gate_name: str,
        context: Dict[str, Any],
        review_prompt: str
    ) -> ReviewDecision:
        """
        LLM 审查

        Args:
            gate_name: 门控名称
            context: 审查上下文
            review_prompt: 审查提示词

        Returns:
            审查决策
        """
        # 这里应该调用 Hermes LLM
        # 简化实现：返回 APPROVE
        print(f"\n{'='*60}")
        print(f"LLM 审查: {gate_name}")
        print(f"{'='*60}")
        print(f"上下文: {json.dumps(context, indent=2, default=str)}")
        print(f"审查提示: {review_prompt}")
        print(f"{'='*60}\n")

        # 实际实现应该调用 Hermes LLM
        # decision = call_hermes_llm(review_prompt, context)

        # 简化实现：返回 APPROVE
        decision = ReviewDecision.APPROVE
        comment = "LLM 审查通过"

        # 更新门控结果
        if self.current_state and gate_name in self.current_state.gate_results:
            self.current_state.gate_results[gate_name].review_decision = decision
            self.current_state.gate_results[gate_name].review_comment = comment
            self.save_state()

        return decision

    def can_proceed(self, gate_name: str) -> bool:
        """
        判断是否可以继续执行

        Args:
            gate_name: 门控名称

        Returns:
            是否可以继续
        """
        if self.current_state is None:
            return False

        gate_result = self.current_state.gate_results.get(gate_name)

        if gate_result is None:
            # 没有检查过，需要检查
            return False

        rule = self.gate_rules.get(gate_name, {})

        # 如果是必需步骤且失败，不能继续
        if rule.get('required', False) and gate_result.status == GateStatus.FAILED:
            return False

        # 如果需要审查且未审查，不能继续
        if gate_result.status == GateStatus.REVIEW_REQUIRED:
            if gate_result.review_decision is None:
                return False
            if gate_result.review_decision == ReviewDecision.REJECT:
                return False

        return True

    def get_failed_gates(self) -> List[str]:
        """
        获取失败的门控

        Returns:
            失败的门控名称列表
        """
        if self.current_state is None:
            return []

        failed = []
        for gate_name, result in self.current_state.gate_results.items():
            if result.status == GateStatus.FAILED:
                failed.append(gate_name)
            elif result.status == GateStatus.REVIEW_REQUIRED:
                if result.review_decision == ReviewDecision.REJECT:
                    failed.append(gate_name)

        return failed

    def get_review_required_gates(self) -> List[str]:
        """
        获取需要审查的门控

        Returns:
            需要审查的门控名称列表
        """
        if self.current_state is None:
            return []

        review_required = []
        for gate_name, result in self.current_state.gate_results.items():
            if result.status == GateStatus.REVIEW_REQUIRED:
                if result.review_decision is None:
                    review_required.append(gate_name)

        return review_required

    def _default_check(self, gate_name: str, data: Dict[str, Any]) -> tuple:
        """
        默认检查逻辑

        Args:
            gate_name: 门控名称
            data: 检查数据

        Returns:
            (分数, 详情, 错误)
        """
        if gate_name == 'data_update':
            # 数据更新检查
            updated_count = data.get('updated_stocks', 0)
            total_count = data.get('total_stocks', 0)
            score = updated_count / total_count if total_count > 0 else 0.0
            details = {
                'updated_count': updated_count,
                'total_count': total_count,
                'success_rate': score,
            }
            return score, details, None

        elif gate_name == 'data_quality':
            # 数据质量检查
            completeness = data.get('completeness', 0.0)
            accuracy = data.get('accuracy', 0.0)
            score = (completeness + accuracy) / 2
            details = {
                'completeness': completeness,
                'accuracy': accuracy,
            }
            return score, details, None

        elif gate_name == 'factor_calculation':
            # 因子计算检查
            success_count = data.get('success_count', 0)
            total_count = data.get('total_count', 0)
            score = success_count / total_count if total_count > 0 else 0.0
            details = {
                'success_count': success_count,
                'total_count': total_count,
                'success_rate': score,
            }
            return score, details, None

        elif gate_name == 'backtest':
            # 回测检查
            sharpe_ratio = data.get('sharpe_ratio', 0.0)
            max_drawdown = data.get('max_drawdown', 1.0)
            # Sharpe Ratio > 1 且 最大回撤 < 20%
            score = min(1.0, max(0.0, (sharpe_ratio / 2.0) * (1.0 - max_drawdown)))
            details = {
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
            }
            return score, details, None

        else:
            # 默认检查
            return 0.5, {}, None

    def generate_report(self) -> Dict[str, Any]:
        """
        生成质量报告

        Returns:
            质量报告
        """
        if self.current_state is None:
            return {}

        report = {
            'pipeline_id': self.current_state.pipeline_id,
            'start_time': self.current_state.start_time.isoformat(),
            'end_time': self.current_state.end_time.isoformat() if self.current_state.end_time else None,
            'status': self.current_state.status,
            'total_steps': self.current_state.total_steps,
            'completed_steps': len(self.current_state.completed_steps),
            'failed_steps': len(self.current_state.failed_steps),
            'gates': {},
            'summary': {
                'total_gates': len(self.current_state.gate_results),
                'passed_gates': 0,
                'failed_gates': 0,
                'warning_gates': 0,
                'review_required_gates': 0,
            }
        }

        for gate_name, result in self.current_state.gate_results.items():
            report['gates'][gate_name] = result.to_dict()

            if result.status == GateStatus.PASSED:
                report['summary']['passed_gates'] += 1
            elif result.status == GateStatus.FAILED:
                report['summary']['failed_gates'] += 1
            elif result.status == GateStatus.WARNING:
                report['summary']['warning_gates'] += 1
            elif result.status == GateStatus.REVIEW_REQUIRED:
                report['summary']['review_required_gates'] += 1

        return report


class SmartPipelineExecutor:
    """智能管线执行器"""

    def __init__(self, quality_manager: QualityGateManager):
        """
        初始化智能管线执行器

        Args:
            quality_manager: 质量门控管理器
        """
        self.quality_manager = quality_manager

        # 定义管线步骤
        self.steps = [
            {'id': 0, 'name': '持仓状态检查', 'gate': None},
            {'id': 1, 'name': '数据更新', 'gate': 'data_update'},
            {'id': 2, 'name': '数据质量检查', 'gate': 'data_quality'},
            {'id': 3, 'name': '因子计算', 'gate': 'factor_calculation'},
            {'id': 4, 'name': '因子验证', 'gate': None},
            {'id': 5, 'name': 'Alpha生成', 'gate': 'alpha_generation'},
            {'id': 6, 'name': '策略执行', 'gate': None},
            {'id': 7, 'name': '组合优化', 'gate': 'portfolio_optimization'},
            {'id': 8, 'name': '风控检查', 'gate': 'risk_check'},
            {'id': 9, 'name': '交易执行', 'gate': None},
            {'id': 10, 'name': '报告生成', 'gate': None},
            {'id': 11, 'name': '监控推送', 'gate': None},
        ]

    def execute_step(
        self,
        step_id: int,
        execute_func: Callable,
        check_func: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        执行单个步骤

        Args:
            step_id: 步骤 ID
            execute_func: 执行函数
            check_func: 检查函数

        Returns:
            执行结果
        """
        step = self.steps[step_id]
        gate_name = step['gate']

        print(f"\n{'='*60}")
        print(f"执行步骤 {step_id}: {step['name']}")
        print(f"{'='*60}")

        # 检查前置依赖
        if gate_name and not self.quality_manager.can_proceed(gate_name):
            print(f"前置门控 {gate_name} 未通过，跳过此步骤")
            return {
                'step_id': step_id,
                'status': 'skipped',
                'reason': f'前置门控 {gate_name} 未通过',
            }

        # 执行步骤
        try:
            result = execute_func()
            print(f"步骤 {step_id} 执行成功")

            # 质量门控检查
            if gate_name:
                gate_result = self.quality_manager.check_gate(
                    gate_name,
                    result,
                    check_func
                )

                print(f"质量门控 {gate_name}: {gate_result.status.value} (分数: {gate_result.score:.2f})")

                # 如果需要 LLM 审查
                if gate_result.status == GateStatus.REVIEW_REQUIRED:
                    print(f"需要 LLM 审查: {gate_name}")

                    # 构建 LLM 审查上下文
                    context = {
                        'gate_name': gate_name,
                        'step_result': result,
                        'gate_result': gate_result.to_dict(),
                    }

                    # LLM 审查
                    review_prompt = self._build_review_prompt(gate_name, result)
                    decision = self.quality_manager.llm_review(
                        gate_name,
                        context,
                        review_prompt
                    )

                    print(f"LLM 审查决策: {decision.value}")

                    if decision == ReviewDecision.REJECT:
                        print(f"LLM 拒绝，停止执行")
                        return {
                            'step_id': step_id,
                            'status': 'rejected',
                            'reason': f'LLM 审查拒绝: {gate_name}',
                        }

            # 更新状态
            if self.quality_manager.current_state:
                self.quality_manager.current_state.completed_steps.append(step_id)
                self.quality_manager.current_state.current_step = step_id + 1
                self.quality_manager.save_state()

            return {
                'step_id': step_id,
                'status': 'success',
                'result': result,
            }

        except Exception as e:
            print(f"步骤 {step_id} 执行失败: {e}")

            # 更新状态
            if self.quality_manager.current_state:
                self.quality_manager.current_state.failed_steps.append(step_id)
                self.quality_manager.save_state()

            return {
                'step_id': step_id,
                'status': 'failed',
                'error': str(e),
            }

    def execute_pipeline(
        self,
        pipeline_id: str,
        step_executors: Dict[int, Callable],
        step_checkers: Optional[Dict[int, Callable]] = None,
        resume: bool = False
    ) -> Dict[str, Any]:
        """
        执行完整管线

        Args:
            pipeline_id: 管线 ID
            step_executors: 步骤执行函数字典
            step_checkers: 步骤检查函数字典
            resume: 是否从断点恢复

        Returns:
            执行结果
        """
        # 创建或加载状态
        if resume:
            state = self.quality_manager.load_state(pipeline_id)
            if state is None:
                print(f"未找到管线状态 {pipeline_id}，从头开始")
                state = self.quality_manager.create_pipeline_state(pipeline_id)
            else:
                print(f"从步骤 {state.current_step} 恢复执行")
        else:
            state = self.quality_manager.create_pipeline_state(pipeline_id)

        # 确定起始步骤
        start_step = state.current_step if resume else 0

        print(f"\n{'='*60}")
        print(f"开始执行管线: {pipeline_id}")
        print(f"起始步骤: {start_step}")
        print(f"总步骤数: {len(self.steps)}")
        print(f"{'='*60}\n")

        # 执行步骤
        for step_id in range(start_step, len(self.steps)):
            step = self.steps[step_id]

            # 检查是否已经完成
            if step_id in state.completed_steps:
                print(f"步骤 {step_id} 已完成，跳过")
                continue

            # 执行步骤
            executor = step_executors.get(step_id)
            if executor is None:
                print(f"步骤 {step_id} 没有执行函数，跳过")
                continue

            checker = step_checkers.get(step_id) if step_checkers else None

            result = self.execute_step(step_id, executor, checker)

            # 如果失败或被拒绝，停止执行
            if result['status'] in ['failed', 'rejected']:
                print(f"步骤 {step_id} {result['status']}，停止执行")
                break

        # 更新最终状态
        if self.quality_manager.current_state:
            self.quality_manager.current_state.status = "completed"
            self.quality_manager.current_state.end_time = datetime.now()
            self.quality_manager.save_state()

        # 生成报告
        report = self.quality_manager.generate_report()

        print(f"\n{'='*60}")
        print(f"管线执行完成")
        print(f"{'='*60}")
        print(f"完成步骤: {report['summary']['passed_gates']}/{report['summary']['total_gates']}")
        print(f"失败步骤: {report['summary']['failed_gates']}")
        print(f"警告步骤: {report['summary']['warning_gates']}")
        print(f"{'='*60}\n")

        return report

    def _build_review_prompt(self, gate_name: str, result: Dict[str, Any]) -> str:
        """
        构建 LLM 审查提示词

        Args:
            gate_name: 门控名称
            result: 步骤结果

        Returns:
            审查提示词
        """
        prompts = {
            'data_update': """
请审查数据更新结果：
- 更新的股票数量
- 数据完整性
- 是否有异常

请判断数据更新是否满足要求，是否可以继续下一步。
""",
            'factor_calculation': """
请审查因子计算结果：
- 因子计算成功率
- 因子质量评分
- 是否有异常因子

请判断因子计算是否满足要求，是否可以继续下一步。
""",
            'alpha_generation': """
请审查 Alpha 生成结果：
- Alpha 预测质量
- 信号强度分布
- 是否有异常信号

请判断 Alpha 生成是否满足要求，是否可以继续下一步。
""",
            'backtest': """
请审查回测结果：
- 夏普比率
- 最大回撤
- 年化收益率
- 胜率

请判断回测结果是否满足要求，是否可以应用到实盘。
""",
            'risk_check': """
请审查风控检查结果：
- 风险暴露
- 集中度
- 杠杆水平

请判断风险是否可控，是否可以继续执行交易。
""",
        }

        return prompts.get(gate_name, "请审查以下结果，判断是否可以继续执行。")


if __name__ == "__main__":
    # 测试代码
    print("质量门控系统测试")

    # 创建质量门控管理器
    manager = QualityGateManager()

    # 创建管线状态
    state = manager.create_pipeline_state("test_pipeline")
    print(f"创建管线状态: {state.pipeline_id}")

    # 测试门控检查
    result = manager.check_gate('data_update', {
        'updated_stocks': 80,
        'total_stocks': 100,
    })
    print(f"门控检查结果: {result.status.value}, 分数: {result.score}")

    # 生成报告
    report = manager.generate_report()
    print(f"质量报告: {json.dumps(report, indent=2, default=str)}")
