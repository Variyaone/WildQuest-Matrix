"""
WildQuest Matrix - 智能管线执行器

集成质量门控系统，实现：
1. 自动化固定流程
2. 关键决策 LLM 审查
3. 断点续传
4. 状态管理
5. 避免重复执行

Author: Variya
Version: 1.0.0
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

from .quality_gate import (
    QualityGateManager,
    SmartPipelineExecutor,
    GateStatus,
    ReviewDecision,
)


class IntelligentPipeline:
    """智能管线执行器"""

    def __init__(
        self,
        pipeline_id: str,
        state_dir: str = "./pipeline_states",
        enable_llm_review: bool = True,
        auto_resume: bool = True,
    ):
        """
        初始化智能管线

        Args:
            pipeline_id: 管线 ID
            state_dir: 状态文件存储目录
            enable_llm_review: 是否启用 LLM 审查
            auto_resume: 是否自动从断点恢复
        """
        self.pipeline_id = pipeline_id
        self.enable_llm_review = enable_llm_review
        self.auto_resume = auto_resume

        # 创建质量门控管理器
        self.quality_manager = QualityGateManager(state_dir)

        # 创建智能管线执行器
        self.executor = SmartPipelineExecutor(self.quality_manager)

        # 步骤执行函数
        self.step_executors = {}
        self.step_checkers = {}

        # 初始化步骤
        self._init_steps()

    def _init_steps(self):
        """初始化步骤执行函数"""
        # 这里应该注册实际的步骤执行函数
        # 简化实现：使用占位函数
        pass

    def register_step_executor(self, step_id: int, executor: Callable):
        """
        注册步骤执行函数

        Args:
            step_id: 步骤 ID
            executor: 执行函数
        """
        self.step_executors[step_id] = executor

    def register_step_checker(self, step_id: int, checker: Callable):
        """
        注册步骤检查函数

        Args:
            step_id: 步骤 ID
            checker: 检查函数
        """
        self.step_checkers[step_id] = checker

    def execute(
        self,
        mode: str = "standard",
        force_restart: bool = False,
    ) -> Dict[str, Any]:
        """
        执行管线

        Args:
            mode: 执行模式 (standard, fast, live, backtest)
            force_restart: 是否强制重新开始

        Returns:
            执行结果
        """
        print(f"\n{'='*60}")
        print(f"智能管线执行器")
        print(f"{'='*60}")
        print(f"管线 ID: {self.pipeline_id}")
        print(f"执行模式: {mode}")
        print(f"LLM 审查: {'启用' if self.enable_llm_review else '禁用'}")
        print(f"自动恢复: {'启用' if self.auto_resume else '禁用'}")
        print(f"强制重启: {'是' if force_restart else '否'}")
        print(f"{'='*60}\n")

        # 检查是否可以恢复
        resume = False
        if not force_restart and self.auto_resume:
            existing_state = self.quality_manager.load_state(self.pipeline_id)
            if existing_state and existing_state.status != "completed":
                print(f"发现未完成的管线，从步骤 {existing_state.current_step} 恢复")
                resume = True

        # 执行管线
        result = self.executor.execute_pipeline(
            pipeline_id=self.pipeline_id,
            step_executors=self.step_executors,
            step_checkers=self.step_checkers,
            resume=resume,
        )

        return result

    def get_status(self) -> Dict[str, Any]:
        """
        获取管线状态

        Returns:
            管线状态
        """
        state = self.quality_manager.load_state(self.pipeline_id)

        if state is None:
            return {
                'pipeline_id': self.pipeline_id,
                'status': 'not_started',
                'message': '管线未开始',
            }

        return {
            'pipeline_id': state.pipeline_id,
            'status': state.status,
            'current_step': state.current_step,
            'total_steps': state.total_steps,
            'completed_steps': len(state.completed_steps),
            'failed_steps': len(state.failed_steps),
            'start_time': state.start_time.isoformat(),
            'end_time': state.end_time.isoformat() if state.end_time else None,
            'failed_gates': self.quality_manager.get_failed_gates(),
            'review_required_gates': self.quality_manager.get_review_required_gates(),
        }

    def get_report(self) -> Dict[str, Any]:
        """
        获取质量报告

        Returns:
            质量报告
        """
        return self.quality_manager.generate_report()

    def manual_review(
        self,
        gate_name: str,
        decision: str,
        comment: Optional[str] = None,
    ) -> bool:
        """
        手动审查

        Args:
            gate_name: 门控名称
            decision: 审查决策 (approve, reject, modify, defer)
            comment: 审查评论

        Returns:
            是否成功
        """
        state = self.quality_manager.load_state(self.pipeline_id)

        if state is None:
            print(f"未找到管线状态: {self.pipeline_id}")
            return False

        if gate_name not in state.gate_results:
            print(f"未找到门控: {gate_name}")
            return False

        gate_result = state.gate_results[gate_name]

        if gate_result.status != GateStatus.REVIEW_REQUIRED:
            print(f"门控 {gate_name} 不需要审查")
            return False

        # 更新审查结果
        gate_result.review_decision = ReviewDecision(decision)
        gate_result.review_comment = comment

        # 保存状态
        self.quality_manager.save_state()

        print(f"手动审查完成: {gate_name} -> {decision}")
        return True

    def retry_failed_step(self, step_id: int) -> bool:
        """
        重试失败的步骤

        Args:
            step_id: 步骤 ID

        Returns:
            是否成功
        """
        state = self.quality_manager.load_state(self.pipeline_id)

        if state is None:
            print(f"未找到管线状态: {self.pipeline_id}")
            return False

        if step_id not in state.failed_steps:
            print(f"步骤 {step_id} 不在失败列表中")
            return False

        # 从失败步骤中移除
        state.failed_steps.remove(step_id)

        # 重置当前步骤
        state.current_step = step_id

        # 保存状态
        self.quality_manager.save_state()

        print(f"重试步骤 {step_id}")
        return True

    def clear_state(self) -> bool:
        """
        清除管线状态

        Returns:
            是否成功
        """
        state_file = os.path.join(
            self.quality_manager.state_dir,
            f"{self.pipeline_id}.json"
        )

        if os.path.exists(state_file):
            os.remove(state_file)
            print(f"清除管线状态: {self.pipeline_id}")
            return True

        print(f"管线状态不存在: {self.pipeline_id}")
        return False


def create_intelligent_pipeline(
    pipeline_id: str,
    config: Optional[Dict[str, Any]] = None,
) -> IntelligentPipeline:
    """
    创建智能管线

    Args:
        pipeline_id: 管线 ID
        config: 配置字典

    Returns:
        智能管线实例
    """
    config = config or {}

    pipeline = IntelligentPipeline(
        pipeline_id=pipeline_id,
        state_dir=config.get('state_dir', './pipeline_states'),
        enable_llm_review=config.get('enable_llm_review', True),
        auto_resume=config.get('auto_resume', True),
    )

    # 注册步骤执行函数
    # 这里应该根据实际需求注册
    # 示例：
    # pipeline.register_step_executor(0, execute_position_check)
    # pipeline.register_step_executor(1, execute_data_update)
    # ...

    return pipeline


if __name__ == "__main__":
    # 测试代码
    print("智能管线执行器测试")

    # 创建智能管线
    pipeline = create_intelligent_pipeline("test_pipeline")

    # 获取状态
    status = pipeline.get_status()
    print(f"管线状态: {json.dumps(status, indent=2)}")

    # 执行管线
    # result = pipeline.execute(mode="standard")
    # print(f"执行结果: {json.dumps(result, indent=2, default=str)}")
