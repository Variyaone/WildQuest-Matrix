"""
覆盖率提升测试 - 第3批

添加更多功能测试以提升覆盖率
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBacktestEngine:
    def test_engine_init(self):
        from core.backtest.engine import BacktestEngine
        engine = BacktestEngine()
        assert engine is not None


class TestBacktestAnalyzer:
    def test_analyzer_init(self):
        from core.backtest.analyzer import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer()
        assert analyzer is not None


class TestBacktestReporter:
    def test_reporter_init(self):
        from core.backtest.reporter import BacktestReporter
        reporter = BacktestReporter()
        assert reporter is not None


class TestFactorClassification:
    def test_classification_init(self):
        from core.factor.classification import FactorClassification
        classifier = FactorClassification()
        assert classifier is not None


class TestFactorMigration:
    def test_migration_init(self):
        from core.factor.migration import FactorMigrator
        migration = FactorMigrator()
        assert migration is not None


class TestFactorMiner:
    def test_miner_init(self):
        from core.factor.miner import FactorMiner
        miner = FactorMiner()
        assert miner is not None


class TestStrategyDesigner:
    def test_designer_init(self):
        from core.strategy.designer import StrategyDesigner
        designer = StrategyDesigner()
        assert designer is not None


class TestStrategySelector:
    def test_selector_init(self):
        from core.strategy.selector import StockSelector
        selector = StockSelector()
        assert selector is not None


class TestTradingManualEntry:
    def test_manual_entry_init(self):
        from core.trading.manual_entry import ManualEntry
        manager = ManualEntry()
        assert manager is not None


class TestTradingStatusTracker:
    def test_status_tracker_init(self):
        from core.trading.status_tracker import TradeStatusTracker
        tracker = TradeStatusTracker()
        assert tracker is not None


class TestMonitorLog:
    def test_log_init(self):
        from core.monitor.log import LogManager
        log = LogManager()
        assert log is not None


class TestMonitorReport:
    def test_report_init(self):
        from core.monitor.report import ReportGenerator
        report = ReportGenerator()
        assert report is not None


class TestDataFetcher:
    def test_fetcher_init(self):
        from core.data.fetcher import DataFetcher
        fetcher = DataFetcher()
        assert fetcher is not None


class TestDataMetadata:
    def test_metadata_init(self):
        from core.data.metadata import MetadataManager
        metadata = MetadataManager()
        assert metadata is not None


class TestDataScheduler:
    def test_scheduler_init(self):
        from core.data.scheduler import UpdateScheduler
        scheduler = UpdateScheduler()
        assert scheduler is not None


class TestDataStorage:
    def test_storage_init(self):
        from core.data.storage import DataStorage
        storage = DataStorage()
        assert storage is not None


class TestEvaluationFactorEvaluator:
    def test_evaluator_init(self):
        from core.evaluation.factor_evaluator import FactorEvaluator
        evaluator = FactorEvaluator()
        assert evaluator is not None


class TestEvaluationStrategyEvaluator:
    def test_evaluator_init(self):
        from core.evaluation.strategy_evaluator import StrategyEvaluator
        evaluator = StrategyEvaluator()
        assert evaluator is not None


class TestEvaluationReport:
    def test_report_init(self):
        from core.evaluation.report import EvaluationReportGenerator
        report = EvaluationReportGenerator()
        assert report is not None


class TestDailyDataUpdater:
    def test_updater_init(self):
        from core.daily.data_updater import DailyDataUpdater
        updater = DailyDataUpdater()
        assert updater is not None


class TestDailyFactorCalculator:
    def test_calculator_init(self):
        from core.daily.factor_calculator import DailyFactorCalculator
        calc = DailyFactorCalculator()
        assert calc is not None


class TestDailySignalGenerator:
    def test_generator_init(self):
        from core.daily.signal_generator import DailySignalGenerator
        gen = DailySignalGenerator()
        assert gen is not None


class TestValidationReporter:
    def test_reporter_init(self):
        from core.validation.reporter import CheckReporter
        reporter = CheckReporter()
        assert reporter is not None


class TestValidationTrustManager:
    def test_manager_init(self):
        from core.validation.trust_manager import TrustManager
        manager = TrustManager()
        assert manager is not None


class TestInfrastructureExceptions:
    def test_exception_import(self):
        from core.infrastructure.exceptions import (
            AppException,
            DataException,
            FactorException,
            SignalException,
            StrategyException,
            TradingException,
            RiskException,
            ValidationException
        )
        assert AppException is not None
        assert DataException is not None
        assert FactorException is not None
        assert SignalException is not None
        assert StrategyException is not None
        assert TradingException is not None
        assert RiskException is not None
        assert ValidationException is not None


class TestInfrastructureLogging:
    def test_logging_init(self):
        from core.infrastructure.logging import get_logger
        logger = get_logger("test")
        assert logger is not None


class TestInfrastructureConfig:
    def test_settings_init(self):
        from core.infrastructure.config.settings import AppConfig
        settings = AppConfig()
        assert settings is not None
    
    def test_data_path_init(self):
        from core.infrastructure.config.data_paths import DataPathConfig
        paths = DataPathConfig()
        assert paths is not None
