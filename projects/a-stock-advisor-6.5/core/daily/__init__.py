"""
日报系统模块

构建完善的日报系统，每日收盘后自动更新数据并生成报告。

模块组成：
- scheduler: 每日任务调度器
- data_updater: 数据更新器
- factor_calculator: 因子计算器
- signal_generator: 信号生成器
- report_generator: 日报生成器
- notifier: 日报推送
- backup: 数据备份
"""

from .scheduler import DailyScheduler, TaskResult, TaskStatus
from .data_updater import DailyDataUpdater, UpdateResult
from .factor_calculator import DailyFactorCalculator, FactorCalcResult
from .signal_generator import DailySignalGenerator, SignalGenResult
from .report_generator import DailyReportGenerator, ReportResult
from .notifier import DailyNotifier, NotifyResult, PreCheckStatus
from .backup import DailyBackup, BackupResult

__all__ = [
    'DailyScheduler',
    'TaskResult',
    'TaskStatus',
    'DailyDataUpdater',
    'UpdateResult',
    'DailyFactorCalculator',
    'FactorCalcResult',
    'DailySignalGenerator',
    'SignalGenResult',
    'DailyReportGenerator',
    'ReportResult',
    'DailyNotifier',
    'NotifyResult',
    'PreCheckStatus',
    'DailyBackup',
    'BackupResult',
]
