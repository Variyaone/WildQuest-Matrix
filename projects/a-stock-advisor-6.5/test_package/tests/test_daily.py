"""
日报系统测试

测试日报系统各模块功能。
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.daily.scheduler import (
    DailyScheduler, Task, TaskStatus, TaskResult, create_default_scheduler
)
from core.daily.data_updater import DailyDataUpdater, UpdateResult
from core.daily.factor_calculator import (
    DailyFactorCalculator, FactorCalcResult, FactorFrequency
)
from core.daily.signal_generator import (
    DailySignalGenerator, SignalGenResult, SignalFrequency, SignalType
)
from core.daily.report_generator import DailyReportGenerator, ReportResult
from core.daily.notifier import DailyNotifier, NotifyResult
from core.daily.backup import DailyBackup, BackupResult, BackupType


class TestScheduler(unittest.TestCase):
    """测试任务调度器"""
    
    def test_task_creation(self):
        """测试任务创建"""
        def dummy_func():
            return {"status": "ok"}
        
        task = Task(
            name="test_task",
            func=dummy_func,
            description="测试任务",
            required=True
        )
        
        self.assertEqual(task.name, "test_task")
        self.assertEqual(task.description, "测试任务")
        self.assertTrue(task.required)
    
    def test_scheduler_registration(self):
        """测试任务注册"""
        scheduler = DailyScheduler()
        
        def dummy_func():
            return {"result": "success"}
        
        scheduler.register_task_func(
            name="test_task",
            func=dummy_func,
            description="测试任务"
        )
        
        self.assertEqual(len(scheduler.tasks), 1)
        self.assertEqual(scheduler.tasks[0].name, "test_task")
    
    def test_task_execution(self):
        """测试任务执行"""
        scheduler = DailyScheduler()
        
        def success_func():
            return {"data": "test"}
        
        scheduler.register_task_func(
            name="success_task",
            func=success_func
        )
        
        result = scheduler.run_task("success_task")
        
        self.assertEqual(result.status, TaskStatus.SUCCESS)
        self.assertIn("data", result.details)
    
    def test_task_failure(self):
        """测试任务失败"""
        scheduler = DailyScheduler()
        
        def fail_func():
            raise ValueError("测试错误")
        
        scheduler.register_task_func(
            name="fail_task",
            func=fail_func
        )
        
        result = scheduler.run_task("fail_task")
        
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertIn("测试错误", result.error_message)
    
    def test_scheduler_run(self):
        """测试调度器运行"""
        scheduler = DailyScheduler()
        
        call_order = []
        
        def task1():
            call_order.append(1)
            return {"task": 1}
        
        def task2():
            call_order.append(2)
            return {"task": 2}
        
        scheduler.register_task_func(name="task1", func=task1)
        scheduler.register_task_func(
            name="task2",
            func=task2,
            dependencies=["task1"]
        )
        
        result = scheduler.run()
        
        self.assertTrue(result.success)
        self.assertEqual(call_order, [1, 2])


class TestFactorCalculator(unittest.TestCase):
    """测试因子计算器"""
    
    def test_factor_registration(self):
        """测试因子注册"""
        calculator = DailyFactorCalculator()
        
        def calc_func(date):
            return {"factor_value": 0.5}
        
        calculator.register_factor(
            factor_id="test_factor",
            name="测试因子",
            calc_func=calc_func,
            frequency=FactorFrequency.DAILY
        )
        
        self.assertIn("test_factor", calculator.list_factors())
    
    def test_factor_frequency_check(self):
        """测试因子频率检查"""
        calculator = DailyFactorCalculator()
        
        from core.daily.factor_calculator import FactorInfo
        
        daily_factor = FactorInfo(
            factor_id="daily",
            name="日线因子",
            frequency=FactorFrequency.DAILY
        )
        
        weekly_factor = FactorInfo(
            factor_id="weekly",
            name="周线因子",
            frequency=FactorFrequency.WEEKLY
        )
        
        monday = datetime(2026, 3, 30)
        tuesday = datetime(2026, 3, 31)
        
        should_calc, _ = calculator._should_calculate(daily_factor, monday)
        self.assertTrue(should_calc)
        
        should_calc, _ = calculator._should_calculate(weekly_factor, monday)
        self.assertTrue(should_calc)
        
        should_calc, reason = calculator._should_calculate(weekly_factor, tuesday)
        self.assertFalse(should_calc)
        self.assertIn("周一", reason)


class TestSignalGenerator(unittest.TestCase):
    """测试信号生成器"""
    
    def test_signal_registration(self):
        """测试信号注册"""
        generator = DailySignalGenerator()
        
        def gen_func(date, factor_data):
            return {"signal": "buy"}
        
        generator.register_signal(
            signal_id="test_signal",
            name="测试信号",
            gen_func=gen_func,
            signal_type=SignalType.STOCK_SELECTION,
            frequency=SignalFrequency.DAILY
        )
        
        self.assertIn("test_signal", generator.list_signals())
    
    def test_signal_frequency_check(self):
        """测试信号频率检查"""
        generator = DailySignalGenerator()
        
        from core.daily.signal_generator import SignalInfo
        
        daily_signal = SignalInfo(
            signal_id="daily",
            name="日线信号",
            signal_type=SignalType.STOCK_SELECTION,
            frequency=SignalFrequency.DAILY
        )
        
        weekly_signal = SignalInfo(
            signal_id="weekly",
            name="周线信号",
            signal_type=SignalType.STOCK_SELECTION,
            frequency=SignalFrequency.WEEKLY
        )
        
        monday = datetime(2026, 3, 30)
        tuesday = datetime(2026, 3, 31)
        
        should_gen, _ = generator._should_generate(daily_signal, monday)
        self.assertTrue(should_gen)
        
        should_gen, _ = generator._should_generate(weekly_signal, monday)
        self.assertTrue(should_gen)
        
        should_gen, reason = generator._should_generate(weekly_signal, tuesday)
        self.assertFalse(should_gen)


class TestReportGenerator(unittest.TestCase):
    """测试报告生成器"""
    
    def test_report_generation(self):
        """测试报告生成"""
        generator = DailyReportGenerator()
        
        result = generator.generate(
            date=datetime.now(),
            market_data={
                "index_changes": {"沪深300": 0.015},
                "market_volume": 1.2e12,
                "northbound_flow": 5.5e9
            },
            portfolio_data={
                "daily_return": 0.018,
                "cumulative_return": 0.12
            }
        )
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.report_path)
        self.assertEqual(result.sections_generated, 7)
    
    def test_report_content(self):
        """测试报告内容"""
        generator = DailyReportGenerator()
        
        result = generator.generate()
        
        self.assertTrue(result.success)
        
        with open(result.report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn("每日运营报告", content)
        self.assertIn("市场概况", content)
        self.assertIn("组合表现", content)
        self.assertIn("持仓分析", content)


class TestNotifier(unittest.TestCase):
    """测试推送器"""
    
    def test_pre_check_execution(self):
        """测试前置检查执行"""
        notifier = DailyNotifier()
        
        result = notifier._execute_pre_check()
        
        self.assertIn("passed", result)
        self.assertIn("layers", result)
        self.assertIn("data", result["layers"])
    
    def test_message_building(self):
        """测试消息构建"""
        notifier = DailyNotifier()
        
        from core.daily.notifier import TradeInstruction
        
        trade_instructions = [
            TradeInstruction(
                stock_code="000001.SZ",
                stock_name="平安银行",
                direction="买入",
                shares=1000,
                price_range=(10.0, 10.5),
                amount=10250,
                timing="开盘",
                reason="因子信号触发"
            )
        ]
        
        message = notifier._build_push_message(
            report_content="测试报告",
            report_data={},
            trade_instructions=trade_instructions,
            pre_check_result={"passed": True, "layers": {}}
        )
        
        self.assertIn("timestamp", message)
        self.assertIn("trade_instructions", message)
        self.assertEqual(len(message["trade_instructions"]["buy"]), 1)
    
    def test_notify_without_webhook(self):
        """测试无Webhook时的推送"""
        notifier = DailyNotifier(webhook_url=None)
        
        result = notifier.notify(skip_pre_check=True)
        
        self.assertTrue(result.success)
        self.assertTrue(result.pre_check_passed)


class TestBackup(unittest.TestCase):
    """测试备份器"""
    
    def test_backup_creation(self):
        """测试备份创建"""
        backup = DailyBackup()
        
        result = backup.backup(
            backup_type=BackupType.DAILY,
            include_core=False,
            include_business=False,
            include_reports=False
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.backup_type, BackupType.DAILY)
    
    def test_backup_verification(self):
        """测试备份验证"""
        backup = DailyBackup()
        
        result = backup.backup(
            backup_type=BackupType.DAILY,
            include_core=False,
            include_business=False,
            include_reports=False
        )
        
        self.assertTrue(result.verified)
    
    def test_backup_listing(self):
        """测试备份列表"""
        backup = DailyBackup()
        
        backup.backup(backup_type=BackupType.DAILY, include_core=False)
        
        backups = backup.list_backups(backup_type=BackupType.DAILY)
        
        self.assertGreater(len(backups), 0)
    
    def test_backup_stats(self):
        """测试备份统计"""
        backup = DailyBackup()
        
        stats = backup.get_backup_stats()
        
        self.assertIn("total_size", stats)
        self.assertIn("total_count", stats)
        self.assertIn("by_type", stats)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_daily_workflow(self):
        """测试完整日报流程"""
        scheduler = DailyScheduler()
        
        def data_update():
            return {"stocks_updated": 10}
        
        def factor_calc():
            return {"factors_calculated": 5}
        
        def signal_gen():
            return {"signals_generated": 3}
        
        def report_gen():
            generator = DailyReportGenerator()
            result = generator.generate()
            return {"report_path": result.report_path}
        
        def backup_func():
            backup = DailyBackup()
            result = backup.backup(include_core=False, include_business=False)
            return {"backup_path": result.backup_path}
        
        scheduler.register_task_func(
            name="data_update",
            func=data_update,
            required=True
        )
        scheduler.register_task_func(
            name="factor_calc",
            func=factor_calc,
            dependencies=["data_update"]
        )
        scheduler.register_task_func(
            name="signal_gen",
            func=signal_gen,
            dependencies=["factor_calc"]
        )
        scheduler.register_task_func(
            name="report_gen",
            func=report_gen,
            dependencies=["signal_gen"]
        )
        scheduler.register_task_func(
            name="backup",
            func=backup_func,
            dependencies=["report_gen"],
            required=False
        )
        
        result = scheduler.run()
        
        self.assertTrue(result.success)
        self.assertEqual(result.completed_tasks, 5)
        self.assertEqual(result.failed_tasks, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
