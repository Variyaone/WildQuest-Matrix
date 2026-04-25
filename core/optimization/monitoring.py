"""
WildQuest Matrix - 轻量级监控模块

针对个人用户的轻量级监控：
1. 进度显示（tqdm 进度条）
2. 日志记录（logging 模块）
3. 执行报告生成

Author: Variya
Version: 1.0.0
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from logging.handlers import RotatingFileHandler
from contextlib import contextmanager


class ProgressMonitor:
    """进度监控器"""

    def __init__(self, ncols: int = 80):
        """
        初始化进度监控器

        Args:
            ncols: 进度条宽度
        """
        self.ncols = ncols

    def with_progress(self, items: List[Any], desc: str = "处理中"):
        """
        带进度条的迭代器

        Args:
            items: 待处理的项目列表
            desc: 描述文本

        Returns:
            迭代器
        """
        try:
            from tqdm import tqdm
            return tqdm(items, desc=desc, ncols=self.ncols)
        except ImportError:
            print(f"tqdm 未安装，使用普通迭代: {desc}")
            return items

    def show_progress(self, current: int, total: int, desc: str = "处理中"):
        """
        显示简单进度

        Args:
            current: 当前进度
            total: 总数
            desc: 描述文本
        """
        percentage = (current / total) * 100 if total > 0 else 0
        bar_length = 40
        filled = int(bar_length * current / total) if total > 0 else 0
        bar = '█' * filled + '░' * (bar_length - filled)

        print(f"\r{desc}: [{bar}] {current}/{total} ({percentage:.1f}%)", end='', flush=True)

        if current == total:
            print()  # 换行


class LoggerManager:
    """日志管理器"""

    def __init__(
        self,
        name: str = "quant_system",
        log_dir: str = "logs",
        log_level: str = "INFO",
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 3
    ):
        """
        初始化日志管理器

        Args:
            name: 日志名称
            log_dir: 日志目录
            log_level: 日志级别
            max_bytes: 单个日志文件最大字节数
            backup_count: 保留的日志文件数量
        """
        self.name = name
        self.log_dir = log_dir
        self.log_level = getattr(logging, log_level.upper())
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)

        # 设置日志
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """
        设置日志记录器

        Returns:
            配置好的日志记录器
        """
        logger = logging.getLogger(self.name)
        logger.setLevel(self.log_level)

        # 清除已有的处理器
        logger.handlers.clear()

        # 文件日志格式
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # 控制台日志格式
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )

        # 文件处理器（自动轮转）
        log_file = os.path.join(self.log_dir, f"{self.name}.log")
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        return logger

    def get_logger(self) -> logging.Logger:
        """
        获取日志记录器

        Returns:
            日志记录器
        """
        return self.logger

    def info(self, message: str) -> None:
        """记录 INFO 级别日志"""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """记录 WARNING 级别日志"""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """记录 ERROR 级别日志"""
        self.logger.error(message)

    def debug(self, message: str) -> None:
        """记录 DEBUG 级别日志"""
        self.logger.debug(message)

    def critical(self, message: str) -> None:
        """记录 CRITICAL 级别日志"""
        self.logger.critical(message)


class ExecutionReporter:
    """执行报告生成器"""

    def __init__(self, report_dir: str = "reports"):
        """
        初始化报告生成器

        Args:
            report_dir: 报告目录
        """
        self.report_dir = report_dir
        os.makedirs(report_dir, exist_ok=True)

    def generate_report(
        self,
        results: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成执行报告

        Args:
            results: 执行结果列表
            metadata: 元数据

        Returns:
            执行报告
        """
        now = datetime.now()

        # 统计信息
        total_steps = len(results)
        success_steps = sum(1 for r in results if r.get('status') == 'success')
        failed_steps = sum(1 for r in results if r.get('status') == 'failed')
        recovered_steps = sum(1 for r in results if r.get('status') == 'recovered')
        total_duration = sum(r.get('duration', 0) for r in results)

        # 构建报告
        report = {
            'timestamp': now.isoformat(),
            'metadata': metadata or {},
            'summary': {
                'total_steps': total_steps,
                'success_steps': success_steps,
                'failed_steps': failed_steps,
                'recovered_steps': recovered_steps,
                'total_duration': total_duration,
                'success_rate': success_steps / total_steps if total_steps > 0 else 0,
                'average_duration': total_duration / total_steps if total_steps > 0 else 0
            },
            'results': results
        }

        return report

    def save_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        保存报告到文件

        Args:
            report: 执行报告
            filename: 文件名，如果为 None 则自动生成

        Returns:
            报告文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"execution_{timestamp}.json"

        report_file = os.path.join(self.report_dir, filename)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"报告已保存: {report_file}")
        return report_file

    def generate_summary_text(self, report: Dict[str, Any]) -> str:
        """
        生成报告摘要文本

        Args:
            report: 执行报告

        Returns:
            摘要文本
        """
        summary = report['summary']

        text = f"""
执行报告摘要
{'=' * 60}
时间: {report['timestamp']}
总步骤: {summary['total_steps']}
成功: {summary['success_steps']}
失败: {summary['failed_steps']}
恢复: {summary['recovered_steps']}
成功率: {summary['success_rate']:.1%}
总耗时: {summary['total_duration']:.2f} 秒
平均耗时: {summary['average_duration']:.2f} 秒
{'=' * 60}
"""

        return text

    def send_notification(
        self,
        report: Dict[str, Any],
        webhook_url: Optional[str] = None
    ) -> bool:
        """
        发送通知（示例）

        Args:
            report: 执行报告
            webhook_url: Webhook URL

        Returns:
            是否成功
        """
        if not webhook_url:
            print("未配置 Webhook URL，跳过通知")
            return False

        try:
            import requests

            summary = report['summary']
            message = f"""
执行完成: 成功 {summary['success_steps']}/{summary['total_steps']}
成功率: {summary['success_rate']:.1%}
总耗时: {summary['total_duration']:.2f} 秒
"""

            payload = {
                'msg_type': 'text',
                'content': {
                    'text': message
                }
            }

            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            print("通知已发送")
            return True

        except Exception as e:
            print(f"发送通知失败: {e}")
            return False


@contextmanager
def execution_context(
    task_name: str,
    logger: Optional[LoggerManager] = None,
    reporter: Optional[ExecutionReporter] = None
):
    """
    执行上下文管理器

    Args:
        task_name: 任务名称
        logger: 日志管理器
        reporter: 报告生成器

    Yields:
        执行上下文
    """
    start_time = datetime.now()

    if logger:
        logger.info(f"任务开始: {task_name}")

    try:
        # 创建执行上下文
        context = {
            'task_name': task_name,
            'start_time': start_time,
            'results': []
        }

        yield context

        # 任务成功完成
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        context['end_time'] = end_time
        context['duration'] = duration
        context['status'] = 'success'

        if logger:
            logger.info(f"任务完成: {task_name}, 耗时 {duration:.2f} 秒")

        if reporter:
            report = reporter.generate_report(context['results'])
            reporter.save_report(report)

    except Exception as e:
        # 任务失败
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        context['end_time'] = end_time
        context['duration'] = duration
        context['status'] = 'failed'
        context['error'] = str(e)

        if logger:
            logger.error(f"任务失败: {task_name}, 错误: {e}")

        raise


def setup_monitoring(
    log_dir: str = "logs",
    report_dir: str = "reports",
    log_level: str = "INFO"
) -> tuple:
    """
    设置监控系统

    Args:
        log_dir: 日志目录
        report_dir: 报告目录
        log_level: 日志级别

    Returns:
        (logger_manager, execution_reporter, progress_monitor)
    """
    logger_manager = LoggerManager(
        log_dir=log_dir,
        log_level=log_level
    )

    execution_reporter = ExecutionReporter(report_dir=report_dir)

    progress_monitor = ProgressMonitor()

    return logger_manager, execution_reporter, progress_monitor


if __name__ == "__main__":
    # 测试代码
    print("轻量级监控模块测试")

    # 测试进度监控
    progress_monitor = ProgressMonitor()
    print("\n测试进度监控:")
    for i in progress_monitor.with_progress(range(10), "测试进度"):
        import time
        time.sleep(0.1)

    # 测试日志管理
    logger_manager = LoggerManager(log_dir="test_logs")
    logger = logger_manager.get_logger()
    logger.info("这是一条 INFO 日志")
    logger.warning("这是一条 WARNING 日志")
    logger.error("这是一条 ERROR 日志")

    # 测试报告生成
    reporter = ExecutionReporter(report_dir="test_reports")
    test_results = [
        {'step_id': 1, 'step_name': '步骤1', 'status': 'success', 'duration': 10.5},
        {'step_id': 2, 'step_name': '步骤2', 'status': 'success', 'duration': 15.3},
        {'step_id': 3, 'step_name': '步骤3', 'status': 'failed', 'duration': 5.2, 'error': '测试错误'},
    ]
    report = reporter.generate_report(test_results)
    reporter.save_report(report)
    print("\n报告摘要:")
    print(reporter.generate_summary_text(report))

    # 测试执行上下文
    print("\n测试执行上下文:")
    with execution_context("测试任务", logger_manager, reporter) as ctx:
        logger.info("执行任务中...")
        ctx['results'].append({'step': 1, 'status': 'success'})

    # 清理测试文件
    import shutil
    if os.path.exists("test_logs"):
        shutil.rmtree("test_logs")
    if os.path.exists("test_reports"):
        shutil.rmtree("test_reports")
