"""
WildQuest Matrix - 优化模块

针对个人用户（MacBook Air M4 16G）的优化方案：
1. 性能优化（performance.py）- 并行计算、内存优化、智能更新
2. 稳定性优化（stability.py）- 重试机制、断点续传、容错执行
3. 自动化调度（automation.py）- Cronjob、launchd、任务管理
4. 轻量级监控（monitoring.py）- 进度显示、日志记录、执行报告

Author: Variya
Version: 1.0.0
"""

from .performance import (
    ParallelFactorCalculator,
    MemoryOptimizedProcessor,
    SmartDataUpdater,
    optimize_pipeline_execution
)

from .stability import (
    RetryManager,
    CheckpointManager,
    FaultTolerantPipeline,
    resilient_api_call
)

from .automation import (
    AutomationScheduler,
    TaskManager,
    setup_daily_pipeline
)

from .monitoring import (
    ProgressMonitor,
    LoggerManager,
    ExecutionReporter,
    execution_context,
    setup_monitoring
)

__all__ = [
    # Performance
    'ParallelFactorCalculator',
    'MemoryOptimizedProcessor',
    'SmartDataUpdater',
    'optimize_pipeline_execution',
    # Stability
    'RetryManager',
    'CheckpointManager',
    'FaultTolerantPipeline',
    'resilient_api_call',
    # Automation
    'AutomationScheduler',
    'TaskManager',
    'setup_daily_pipeline',
    # Monitoring
    'ProgressMonitor',
    'LoggerManager',
    'ExecutionReporter',
    'execution_context',
    'setup_monitoring',
]

__version__ = '1.0.0'
__author__ = 'Variya'
