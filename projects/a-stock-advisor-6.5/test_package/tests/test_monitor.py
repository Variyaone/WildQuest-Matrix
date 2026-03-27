"""
监控系统测试模块

测试所有监控组件的功能。
"""

import unittest
import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.monitor.dashboard import Dashboard, DashboardManager, PanelType, RefreshFrequency
from core.monitor.tracker import PerformanceTracker, PerformanceMetrics, TrackingPeriod, BenchmarkType
from core.monitor.alert import AlertSystem, Alert, AlertLevel, AlertType
from core.monitor.log import LogManager, LogType
from core.monitor.report import ReportGenerator, ReportType
from core.monitor.attribution import AttributionAnalyzer, AttributionType, AttributionResult
from core.monitor.factor_decay import FactorDecayMonitor, DecayLevel, FactorMetrics
from core.monitor.signal_quality import SignalQualityMonitor, QualityLevel, SignalMetrics
from core.monitor.strategy_health import StrategyHealthMonitor, HealthLevel
from core.monitor.system_health import SystemHealthMonitor, SystemStatus


class TestDashboard(unittest.TestCase):
    """测试监控仪表盘"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dashboard = Dashboard("test_dashboard", "Test Dashboard")
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_dashboard_creation(self):
        """测试仪表盘创建"""
        self.assertEqual(self.dashboard.dashboard_id, "test_dashboard")
        self.assertEqual(self.dashboard.name, "Test Dashboard")
        self.assertEqual(len(self.dashboard.panels), 6)
    
    def test_update_panel(self):
        """测试更新面板"""
        data = {"total_value": 1000000, "daily_return": 0.01}
        result = self.dashboard.update_panel("portfolio_overview", data)
        self.assertTrue(result)
        
        panel = self.dashboard.get_panel("portfolio_overview")
        self.assertIsNotNone(panel)
        self.assertEqual(panel.data["total_value"], 1000000)
    
    def test_dashboard_to_dict(self):
        """测试仪表盘转换为字典"""
        data = self.dashboard.to_dict()
        self.assertEqual(data["dashboard_id"], "test_dashboard")
        self.assertEqual(len(data["panels"]), 6)
    
    def test_dashboard_manager(self):
        """测试仪表盘管理器"""
        manager = DashboardManager(self.temp_dir)
        
        dashboard = manager.create_dashboard("managed_dashboard", "Managed Dashboard")
        self.assertIsNotNone(dashboard)
        
        result = manager.save_dashboard("managed_dashboard")
        self.assertTrue(result)
        
        loaded = manager.load_dashboard("managed_dashboard")
        self.assertIsNotNone(loaded)


class TestPerformanceTracker(unittest.TestCase):
    """测试绩效追踪"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = PerformanceTracker(
            "test_tracker",
            BenchmarkType.HS300,
            self.temp_dir
        )
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_add_daily_performance(self):
        """测试添加日度绩效"""
        self.tracker.add_daily_performance(
            date="2026-03-28",
            daily_return=0.01,
            turnover_rate=0.05,
            commission=100.0,
            position_count=10
        )
        
        self.assertEqual(len(self.tracker.daily_performances), 1)
        self.assertEqual(self.tracker.daily_performances[0].daily_return, 0.01)
    
    def test_calculate_metrics(self):
        """测试计算绩效指标"""
        for i in range(10):
            self.tracker.add_daily_performance(
                date=(datetime.now() - timedelta(days=10-i)).strftime("%Y-%m-%d"),
                daily_return=0.001 * (i + 1),
                turnover_rate=0.05,
                commission=100.0
            )
        
        metrics = self.tracker.calculate_metrics(TrackingPeriod.DAILY)
        self.assertIsNotNone(metrics)
        self.assertGreater(metrics.trading_days, 0)
    
    def test_save_and_load(self):
        """测试保存和加载"""
        self.tracker.add_daily_performance(
            date="2026-03-28",
            daily_return=0.01
        )
        
        self.assertTrue(self.tracker.save())
        
        new_tracker = PerformanceTracker("test_tracker", storage_path=self.temp_dir)
        self.assertTrue(new_tracker.load())
        self.assertEqual(len(new_tracker.daily_performances), 1)


class TestAlertSystem(unittest.TestCase):
    """测试异常告警"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.alert_system = AlertSystem("test_alerts", storage_path=self.temp_dir)
        for rule in self.alert_system.rules.values():
            rule.last_triggered = None
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_default_rules(self):
        """测试默认规则"""
        self.assertGreater(len(self.alert_system.rules), 0)
    
    def test_check_and_alert(self):
        """测试检查并触发告警"""
        alert = self.alert_system.check_and_alert("R001", -0.04)
        self.assertIsNotNone(alert)
        if alert:
            self.assertEqual(alert.level, AlertLevel.CRITICAL)
    
    def test_acknowledge_alert(self):
        """测试确认告警"""
        self.alert_system.check_and_alert("R001", -0.04)
        
        alerts = self.alert_system.get_active_alerts()
        if alerts:
            alert_id = alerts[0].alert_id
            self.assertTrue(self.alert_system.acknowledge_alert(alert_id))
    
    def test_generate_summary(self):
        """测试生成摘要"""
        self.alert_system.check_and_alert("R001", -0.04)
        
        summary = self.alert_system.generate_summary(days=7)
        self.assertIn("total_alerts", summary)


class TestLogManager(unittest.TestCase):
    """测试日志管理"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_trade(self):
        """测试记录交易日志"""
        log_manager = LogManager(self.temp_dir)
        log_manager.log_trade(
            operation="ORDER",
            message="买入订单",
            details={"stock": "000001.SZ", "amount": 1000}
        )
        
        self.assertIn(LogType.TRADE, log_manager._loggers)
    
    def test_log_strategy(self):
        """测试记录策略日志"""
        log_manager = LogManager(self.temp_dir)
        log_manager.log_strategy(
            operation="SIGNAL",
            message="生成买入信号",
            details={"signal_id": "S001"}
        )
        
        self.assertIn(LogType.STRATEGY, log_manager._loggers)
    
    def test_get_log_stats(self):
        """测试获取日志统计"""
        log_manager = LogManager(self.temp_dir)
        log_manager.log_trade("ORDER", "测试")
        log_manager.log_strategy("SIGNAL", "测试")
        
        stats = log_manager.get_log_stats()
        self.assertIn("trade", stats)
        self.assertIn("strategy", stats)


class TestReportGenerator(unittest.TestCase):
    """测试报告生成"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.generator = ReportGenerator("test_generator", self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_generate_daily_report(self):
        """测试生成日报"""
        report = self.generator.generate_daily_report(
            "2026-03-28",
            {
                "market": {"sh_index": 3200.0, "sz_index": 10500.0},
                "portfolio": {"total_value": 1000000, "daily_return": 0.01}
            }
        )
        
        self.assertIsNotNone(report)
        self.assertEqual(report.report_type, ReportType.DAILY)
    
    def test_generate_weekly_report(self):
        """测试生成周报"""
        report = self.generator.generate_weekly_report("2026-03-28")
        self.assertIsNotNone(report)
        self.assertEqual(report.report_type, ReportType.WEEKLY)
    
    def test_report_to_markdown(self):
        """测试报告转换为Markdown"""
        report = self.generator.generate_daily_report("2026-03-28")
        md = report.to_markdown()
        self.assertIn("# 日报", md)


class TestAttributionAnalyzer(unittest.TestCase):
    """测试归因分析"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = AttributionAnalyzer("test_analyzer", self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_analyze_industry(self):
        """测试行业归因"""
        portfolio_returns = pd.DataFrame({
            "return": [0.02, 0.01, -0.01]
        }, index=["科技", "金融", "消费"])
        
        portfolio_weights = pd.DataFrame({
            "weight": [0.4, 0.3, 0.3]
        }, index=["科技", "金融", "消费"])
        
        result = self.analyzer.analyze_industry(portfolio_returns, portfolio_weights)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.attribution_type, AttributionType.INDUSTRY)
        self.assertEqual(len(result.items), 3)


class TestFactorDecayMonitor(unittest.TestCase):
    """测试因子衰减监控"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = FactorDecayMonitor("test_monitor", self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_update_factor_metrics(self):
        """测试更新因子指标"""
        metrics = FactorMetrics(
            factor_id="F001",
            factor_name="动量因子",
            date="2026-03-28",
            ic_5d=0.03,
            ic_20d=0.025,
            ic_60d=0.02
        )
        
        self.monitor.update_factor_metrics(metrics)
        
        status = self.monitor.get_factor_status("F001")
        self.assertIsNotNone(status)
    
    def test_decay_detection(self):
        """测试衰减检测"""
        metrics = FactorMetrics(
            factor_id="F002",
            factor_name="测试因子",
            date="2026-03-28",
            ic_5d=-0.01,
            ic_20d=0.005,
            ic_60d=0.01
        )
        
        self.monitor.update_factor_metrics(metrics)
        
        status = self.monitor.get_factor_status("F002")
        self.assertIn(status.decay_level, [DecayLevel.MILD, DecayLevel.MODERATE, DecayLevel.SEVERE])
    
    def test_generate_decay_report(self):
        """测试生成衰减报告"""
        metrics = FactorMetrics(
            factor_id="F001",
            factor_name="动量因子",
            date="2026-03-28",
            ic_5d=0.03
        )
        self.monitor.update_factor_metrics(metrics)
        
        report = self.monitor.generate_decay_report()
        self.assertIn("# 因子衰减监控报告", report)


class TestSignalQualityMonitor(unittest.TestCase):
    """测试信号质量监控"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = SignalQualityMonitor("test_monitor", self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_update_signal_metrics(self):
        """测试更新信号指标"""
        metrics = SignalMetrics(
            signal_id="S001",
            signal_name="突破信号",
            date="2026-03-28",
            win_rate_1d=0.55,
            win_rate_20d=0.58,
            profit_loss_ratio=1.8,
            signal_strength=0.6
        )
        
        self.monitor.update_signal_metrics(metrics)
        
        status = self.monitor.get_signal_status("S001")
        self.assertIsNotNone(status)
    
    def test_quality_level(self):
        """测试质量级别"""
        metrics = SignalMetrics(
            signal_id="S002",
            signal_name="低质量信号",
            date="2026-03-28",
            win_rate_1d=0.40,
            win_rate_20d=0.42,
            profit_loss_ratio=0.8,
            signal_strength=0.2
        )
        
        self.monitor.update_signal_metrics(metrics)
        
        status = self.monitor.get_signal_status("S002")
        self.assertIn(status.quality_level, [QualityLevel.POOR, QualityLevel.CRITICAL])


class TestStrategyHealthMonitor(unittest.TestCase):
    """测试策略健康监控"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = StrategyHealthMonitor("test_monitor", self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_update_strategy_health(self):
        """测试更新策略健康"""
        status = self.monitor.update_strategy_health(
            strategy_id="STR001",
            strategy_name="动量策略",
            performance={
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.08,
                "calmar_ratio": 1.5,
                "benchmark_correlation": 0.7
            },
            parameter={
                "parameter_drift": 0.05,
                "parameter_sensitivity": 0.1,
                "parameter_stability": 0.95
            },
            execution={
                "execution_rate": 0.98,
                "fill_rate": 0.99,
                "turnover_rate": 0.15,
                "trading_cost": 0.001
            },
            environment={
                "market_match": 0.85,
                "factor_match": 0.90
            }
        )
        
        self.assertIsNotNone(status)
        self.assertIn(status.health_level, [HealthLevel.EXCELLENT, HealthLevel.GOOD])
    
    def test_health_score_calculation(self):
        """测试健康评分计算"""
        status = self.monitor.update_strategy_health(
            strategy_id="STR002",
            strategy_name="测试策略",
            performance={"sharpe_ratio": 0.3, "max_drawdown": 0.20}
        )
        
        self.assertGreaterEqual(status.health_score, 0)
        self.assertLessEqual(status.health_score, 100)


class TestSystemHealthMonitor(unittest.TestCase):
    """测试系统健康监控"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = SystemHealthMonitor("test_monitor", self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_check_system_health(self):
        """测试检查系统健康"""
        report = self.monitor.check_system_health(
            data_info={
                "update_status": "normal",
                "quality_score": 95.0,
                "delay_hours": 1.0,
                "completeness": 99.0
            },
            task_info={
                "success_rate": 98.0,
                "failed_count": 1,
                "queue_size": 5
            }
        )
        
        self.assertIsNotNone(report)
        self.assertIn(report.system_status, [SystemStatus.HEALTHY, SystemStatus.WARNING])
    
    def test_resource_health(self):
        """测试资源健康"""
        report = self.monitor.check_system_health()
        
        self.assertIsNotNone(report.resource_health)
        self.assertGreaterEqual(report.resource_health.cpu_usage, 0)
        self.assertGreaterEqual(report.resource_health.memory_usage, 0)
    
    def test_generate_health_report(self):
        """测试生成健康报告"""
        self.monitor.check_system_health()
        
        report = self.monitor.generate_health_report()
        self.assertIn("# 系统健康报告", report)


class TestMonitorIntegration(unittest.TestCase):
    """监控系统集成测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_monitoring_workflow(self):
        """测试完整监控流程"""
        tracker = PerformanceTracker("integration_test", storage_path=self.temp_dir)
        alert_system = AlertSystem("integration_test", storage_path=self.temp_dir)
        report_generator = ReportGenerator("integration_test", self.temp_dir)
        
        for i in range(5):
            daily_return = 0.005 * (i + 1)
            tracker.add_daily_performance(
                date=(datetime.now() - timedelta(days=5-i)).strftime("%Y-%m-%d"),
                daily_return=daily_return,
                turnover_rate=0.05,
                commission=100.0
            )
            
            if daily_return < -0.015:
                alert_system.check_and_alert("R002", daily_return)
        
        metrics = tracker.calculate_metrics(TrackingPeriod.DAILY)
        self.assertIsNotNone(metrics)
        
        report = report_generator.generate_daily_report(
            data={
                "portfolio": {
                    "total_value": 1000000,
                    "daily_return": metrics.total_return
                }
            }
        )
        self.assertIsNotNone(report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
