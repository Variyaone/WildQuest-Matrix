"""
每日任务调度器

管理每日收盘后的任务执行顺序，确保各模块按正确顺序执行。
"""

import time
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..infrastructure.logging import get_logger


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskResult:
    """任务执行结果"""
    task_name: str
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_name": self.task_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "details": self.details
        }


@dataclass
class ScheduleResult:
    """调度执行结果"""
    success: bool
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    skipped_tasks: int
    total_duration: float
    task_results: List[TaskResult]
    start_time: datetime
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "total_duration": self.total_duration,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "task_results": [r.to_dict() for r in self.task_results]
        }


class Task:
    """任务定义"""
    
    def __init__(
        self,
        name: str,
        func: Callable,
        description: str = "",
        required: bool = True,
        dependencies: Optional[List[str]] = None,
        time_window: Optional[tuple] = None,
        retry_count: int = 0,
        retry_delay: int = 60
    ):
        """
        初始化任务
        
        Args:
            name: 任务名称
            func: 任务执行函数
            description: 任务描述
            required: 是否必须成功（失败时是否中断后续任务）
            dependencies: 依赖的任务名称列表
            time_window: 执行时间窗口 (start_hour, end_hour)
            retry_count: 重试次数
            retry_delay: 重试延迟（秒）
        """
        self.name = name
        self.func = func
        self.description = description
        self.required = required
        self.dependencies = dependencies or []
        self.time_window = time_window
        self.retry_count = retry_count
        self.retry_delay = retry_delay


class DailyScheduler:
    """
    每日任务调度器
    
    管理每日收盘后的任务执行顺序：
    
    1. 数据更新（15:30-16:00）
    2. 数据过期检查（16:00-16:15）
    3. 因子计算（16:15-17:00）
    4. 信号生成（17:00-17:30）
    5. 策略执行（17:30-18:00）
    6. 组合优化（18:00-18:30）
    7. 风控检查（18:30-19:00）
    8. 日报生成（19:00-19:30）
    9. 数据备份（19:30-20:00）
    """
    
    DEFAULT_TASKS = [
        {
            "name": "data_update",
            "description": "数据更新",
            "time_window": (15, 30, 16, 0),
            "required": True,
            "retry_count": 3
        },
        {
            "name": "data_check",
            "description": "数据过期检查",
            "time_window": (16, 0, 16, 15),
            "required": True,
            "dependencies": ["data_update"]
        },
        {
            "name": "factor_calc",
            "description": "因子计算",
            "time_window": (16, 15, 17, 0),
            "required": True,
            "dependencies": ["data_check"]
        },
        {
            "name": "signal_gen",
            "description": "信号生成",
            "time_window": (17, 0, 17, 30),
            "required": True,
            "dependencies": ["factor_calc"]
        },
        {
            "name": "strategy_exec",
            "description": "策略执行",
            "time_window": (17, 30, 18, 0),
            "required": True,
            "dependencies": ["signal_gen"]
        },
        {
            "name": "portfolio_opt",
            "description": "组合优化",
            "time_window": (18, 0, 18, 30),
            "required": True,
            "dependencies": ["strategy_exec"]
        },
        {
            "name": "risk_check",
            "description": "风控检查",
            "time_window": (18, 30, 19, 0),
            "required": True,
            "dependencies": ["portfolio_opt"]
        },
        {
            "name": "report_gen",
            "description": "日报生成",
            "time_window": (19, 0, 19, 30),
            "required": True,
            "dependencies": ["risk_check"]
        },
        {
            "name": "backup",
            "description": "数据备份",
            "time_window": (19, 30, 20, 0),
            "required": False,
            "dependencies": ["report_gen"]
        }
    ]
    
    def __init__(
        self,
        tasks: Optional[List[Task]] = None,
        stop_on_failure: bool = True,
        logger_name: str = "daily.scheduler"
    ):
        """
        初始化调度器
        
        Args:
            tasks: 任务列表（None则使用默认任务）
            stop_on_failure: 必要任务失败时是否停止后续任务
            logger_name: 日志名称
        """
        self.tasks = tasks or []
        self.stop_on_failure = stop_on_failure
        self.logger = get_logger(logger_name)
        
        self._task_results: Dict[str, TaskResult] = {}
        self._current_date: Optional[datetime] = None
    
    def register_task(self, task: Task):
        """
        注册任务
        
        Args:
            task: 任务对象
        """
        self.tasks.append(task)
        self.logger.info(f"注册任务: {task.name}")
    
    def register_task_func(
        self,
        name: str,
        func: Callable,
        **kwargs
    ):
        """
        注册任务函数
        
        Args:
            name: 任务名称
            func: 任务函数
            **kwargs: 其他参数
        """
        task = Task(name=name, func=func, **kwargs)
        self.register_task(task)
    
    def _check_dependencies(self, task: Task) -> bool:
        """
        检查任务依赖是否满足
        
        Args:
            task: 任务对象
            
        Returns:
            bool: 依赖是否满足
        """
        for dep_name in task.dependencies:
            if dep_name not in self._task_results:
                return False
            result = self._task_results[dep_name]
            if result.status != TaskStatus.SUCCESS:
                return False
        return True
    
    def _check_time_window(self, task: Task) -> bool:
        """
        检查是否在执行时间窗口内
        
        Args:
            task: 任务对象
            
        Returns:
            bool: 是否在时间窗口内
        """
        if task.time_window is None:
            return True
        
        now = datetime.now()
        start_h, start_m, end_h, end_m = task.time_window
        start_time = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
        end_time = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
        
        return start_time <= now <= end_time
    
    def _execute_task(self, task: Task) -> TaskResult:
        """
        执行单个任务
        
        Args:
            task: 任务对象
            
        Returns:
            TaskResult: 执行结果
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"开始执行任务: {task.name}")
            
            result_data = task.func()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(f"任务完成: {task.name}, 耗时: {duration:.2f}秒")
            
            return TaskResult(
                task_name=task.name,
                status=TaskStatus.SUCCESS,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                details=result_data if isinstance(result_data, dict) else {"result": result_data}
            )
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"任务失败: {task.name}, 错误: {str(e)}")
            
            return TaskResult(
                task_name=task.name,
                status=TaskStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def _execute_task_with_retry(self, task: Task) -> TaskResult:
        """
        带重试的任务执行
        
        Args:
            task: 任务对象
            
        Returns:
            TaskResult: 执行结果
        """
        last_result = None
        
        for attempt in range(task.retry_count + 1):
            result = self._execute_task(task)
            
            if result.status == TaskStatus.SUCCESS:
                return result
            
            last_result = result
            
            if attempt < task.retry_count:
                self.logger.warning(
                    f"任务 {task.name} 失败，{task.retry_delay}秒后重试 "
                    f"(尝试 {attempt + 1}/{task.retry_count})"
                )
                time.sleep(task.retry_delay)
        
        return last_result
    
    def run(
        self,
        date: Optional[datetime] = None,
        task_names: Optional[List[str]] = None
    ) -> ScheduleResult:
        """
        执行调度
        
        Args:
            date: 执行日期（None则使用当前日期）
            task_names: 要执行的任务名称列表（None则执行全部）
            
        Returns:
            ScheduleResult: 调度结果
        """
        self._current_date = date or datetime.now()
        self._task_results.clear()
        
        schedule_start = datetime.now()
        
        self.logger.info(f"开始每日调度: {self._current_date.strftime('%Y-%m-%d')}")
        
        completed = 0
        failed = 0
        skipped = 0
        
        for task in self.tasks:
            if task_names and task.name not in task_names:
                continue
            
            if not self._check_dependencies(task):
                self.logger.warning(f"任务 {task.name} 依赖未满足，跳过")
                skipped += 1
                self._task_results[task.name] = TaskResult(
                    task_name=task.name,
                    status=TaskStatus.SKIPPED,
                    start_time=datetime.now(),
                    details={"reason": "依赖未满足"}
                )
                continue
            
            if not self._check_time_window(task):
                self.logger.warning(f"任务 {task.name} 不在执行时间窗口内")
            
            result = self._execute_task_with_retry(task)
            self._task_results[task.name] = result
            
            if result.status == TaskStatus.SUCCESS:
                completed += 1
            elif result.status == TaskStatus.SKIPPED:
                skipped += 1
            else:
                failed += 1
                
                if task.required and self.stop_on_failure:
                    self.logger.error(
                        f"必要任务 {task.name} 失败，停止后续任务执行"
                    )
                    break
        
        schedule_end = datetime.now()
        total_duration = (schedule_end - schedule_start).total_seconds()
        
        success = failed == 0
        
        self.logger.info(
            f"调度完成: 成功={completed}, 失败={failed}, 跳过={skipped}, "
            f"总耗时={total_duration:.2f}秒"
        )
        
        return ScheduleResult(
            success=success,
            total_tasks=len(self.tasks),
            completed_tasks=completed,
            failed_tasks=failed,
            skipped_tasks=skipped,
            total_duration=total_duration,
            task_results=list(self._task_results.values()),
            start_time=schedule_start,
            end_time=schedule_end
        )
    
    def run_task(self, task_name: str) -> TaskResult:
        """
        执行单个任务
        
        Args:
            task_name: 任务名称
            
        Returns:
            TaskResult: 执行结果
        """
        for task in self.tasks:
            if task.name == task_name:
                return self._execute_task_with_retry(task)
        
        return TaskResult(
            task_name=task_name,
            status=TaskStatus.FAILED,
            start_time=datetime.now(),
            error_message=f"任务不存在: {task_name}"
        )
    
    def get_task_result(self, task_name: str) -> Optional[TaskResult]:
        """
        获取任务结果
        
        Args:
            task_name: 任务名称
            
        Returns:
            Optional[TaskResult]: 任务结果
        """
        return self._task_results.get(task_name)
    
    def get_all_results(self) -> Dict[str, TaskResult]:
        """
        获取所有任务结果
        
        Returns:
            Dict[str, TaskResult]: 任务结果字典
        """
        return self._task_results.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取执行摘要
        
        Returns:
            Dict: 执行摘要
        """
        results = list(self._task_results.values())
        
        return {
            "date": self._current_date.strftime('%Y-%m-%d') if self._current_date else None,
            "total_tasks": len(self.tasks),
            "executed_tasks": len(results),
            "success_count": sum(1 for r in results if r.status == TaskStatus.SUCCESS),
            "failed_count": sum(1 for r in results if r.status == TaskStatus.FAILED),
            "skipped_count": sum(1 for r in results if r.status == TaskStatus.SKIPPED),
            "total_duration": sum(r.duration_seconds for r in results),
            "tasks": {r.task_name: r.to_dict() for r in results}
        }


def create_default_scheduler(
    data_updater=None,
    factor_calculator=None,
    signal_generator=None,
    report_generator=None,
    notifier=None,
    backup=None
) -> DailyScheduler:
    """
    创建默认调度器
    
    Args:
        data_updater: 数据更新器实例
        factor_calculator: 因子计算器实例
        signal_generator: 信号生成器实例
        report_generator: 日报生成器实例
        notifier: 通知器实例
        backup: 备份器实例
        
    Returns:
        DailyScheduler: 调度器实例
    """
    scheduler = DailyScheduler()
    
    if data_updater:
        scheduler.register_task_func(
            name="data_update",
            func=data_updater.update,
            description="数据更新",
            required=True,
            retry_count=3,
            retry_delay=60
        )
    
    if factor_calculator:
        scheduler.register_task_func(
            name="factor_calc",
            func=factor_calculator.calculate,
            description="因子计算",
            required=True,
            dependencies=["data_update"]
        )
    
    if signal_generator:
        scheduler.register_task_func(
            name="signal_gen",
            func=signal_generator.generate,
            description="信号生成",
            required=True,
            dependencies=["factor_calc"]
        )
    
    if report_generator:
        scheduler.register_task_func(
            name="report_gen",
            func=report_generator.generate,
            description="日报生成",
            required=True,
            dependencies=["signal_gen"]
        )
    
    if notifier:
        scheduler.register_task_func(
            name="notify",
            func=notifier.notify,
            description="日报推送",
            required=False,
            dependencies=["report_gen"]
        )
    
    if backup:
        scheduler.register_task_func(
            name="backup",
            func=backup.backup,
            description="数据备份",
            required=False,
            dependencies=["report_gen"]
        )
    
    return scheduler
