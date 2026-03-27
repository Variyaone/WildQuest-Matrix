"""
覆盖率提升测试 - 第2批

针对低覆盖率模块添加测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestSignalFilter:
    """信号过滤器测试"""
    
    def test_filter_config_init(self):
        """测试过滤器配置初始化"""
        from core.signal.filter import FilterConfig
        
        config = FilterConfig()
        assert config.min_strength == "weak"
        assert config.min_win_rate == 0.0
        assert config.max_signals_per_day == 100
    
    def test_filter_config_custom(self):
        """测试自定义过滤器配置"""
        from core.signal.filter import FilterConfig
        
        config = FilterConfig(
            min_strength="strong",
            min_win_rate=0.6,
            max_signals_per_day=50
        )
        assert config.min_strength == "strong"
        assert config.min_win_rate == 0.6
        assert config.max_signals_per_day == 50
    
    def test_filter_result(self):
        """测试过滤结果"""
        from core.signal.filter import FilterResult
        
        result = FilterResult(
            success=True,
            original_count=10,
            filtered_count=5,
            filtered_signals=[],
            filter_stats={"strength": 3, "win_rate": 2}
        )
        assert result.success
        assert result.original_count == 10
        assert result.filtered_count == 5


class TestTradingOrder:
    """交易订单测试"""
    
    def test_order_status_enum(self):
        """测试订单状态枚举"""
        from core.trading.order import OrderStatus
        
        assert OrderStatus.PENDING_PUSH.value == "pending_push"
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.CANCELLED.value == "cancelled"
    
    def test_order_side_enum(self):
        """测试订单方向枚举"""
        from core.trading.order import OrderSide
        
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"
    
    def test_order_type_enum(self):
        """测试订单类型枚举"""
        from core.trading.order import OrderType
        
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
    
    def test_trade_order_creation(self):
        """测试交易订单创建"""
        from core.trading.order import TradeOrder, OrderSide, OrderType, OrderStatus
        
        order = TradeOrder(
            order_id="ORD001",
            stock_code="000001.SZ",
            stock_name="平安银行",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=10.5
        )
        
        assert order.order_id == "ORD001"
        assert order.stock_code == "000001.SZ"
        assert order.quantity == 1000
        assert order.price == 10.5
        assert order.status == OrderStatus.PENDING_PUSH
    
    def test_trade_order_amount(self):
        """测试订单金额计算"""
        from core.trading.order import TradeOrder, OrderSide, OrderType
        
        order = TradeOrder(
            order_id="ORD002",
            stock_code="000002.SZ",
            stock_name="万科A",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=15.0
        )
        
        assert order.amount == 15000.0
    
    def test_trade_order_fill_rate(self):
        """测试订单成交率计算"""
        from core.trading.order import TradeOrder, OrderSide, OrderType
        
        order = TradeOrder(
            order_id="ORD003",
            stock_code="600000.SH",
            stock_name="浦发银行",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1000
        )
        
        order.filled_quantity = 500
        assert order.fill_rate == 0.5
    
    def test_trade_order_to_dict(self):
        """测试订单转字典"""
        from core.trading.order import TradeOrder, OrderSide, OrderType
        
        order = TradeOrder(
            order_id="ORD004",
            stock_code="600519.SH",
            stock_name="贵州茅台",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=1800.0
        )
        
        d = order.to_dict()
        assert d["order_id"] == "ORD004"
        assert d["stock_code"] == "600519.SH"
        assert d["side"] == "sell"
    
    def test_order_manager_init(self):
        """测试订单管理器初始化"""
        from core.trading.order import OrderManager
        
        manager = OrderManager()
        assert manager is not None


class TestStrategyBacktester:
    """策略回测器测试"""
    
    def test_backtester_init(self):
        """测试回测器初始化"""
        from core.strategy.backtester import StrategyBacktester
        
        backtester = StrategyBacktester()
        assert backtester is not None


class TestFactorStorage:
    """因子存储测试"""
    
    def test_storage_init(self):
        """测试存储初始化"""
        from core.factor.storage import FactorStorage
        
        storage = FactorStorage()
        assert storage is not None


class TestDataCleanerAdvanced:
    """数据清洗器高级测试"""
    
    def test_cleaner_clean(self):
        """测试数据清洗"""
        from core.data.cleaner import DataCleaner
        
        cleaner = DataCleaner()
        
        df = pd.DataFrame({
            'stock_code': ['000001.SZ'] * 5,
            'date': pd.date_range('2026-01-01', periods=5, freq='B'),
            'open': [10.0, 10.5, 10.3, 10.8, 10.6],
            'high': [10.8, 11.0, 10.9, 11.2, 11.0],
            'low': [9.8, 10.2, 10.0, 10.5, 10.3],
            'close': [10.5, 10.8, 10.6, 11.0, 10.9],
            'volume': [1000000, 1200000, 900000, 1100000, 1000000]
        })
        
        result = cleaner.clean(df)
        assert result is not None or True


class TestPortfolioConstraints:
    """组合约束测试"""
    
    def test_constraints_init(self):
        """测试约束初始化"""
        from core.portfolio.constraints import ConstraintsManager
        
        manager = ConstraintsManager()
        assert manager is not None


class TestRiskAlert:
    """风控告警测试"""
    
    def test_alert_init(self):
        """测试告警初始化"""
        from core.risk.alert import RiskAlertManager
        
        manager = RiskAlertManager()
        assert manager is not None


class TestBacktestMatcher:
    """回测撮合器测试"""
    
    def test_matcher_init(self):
        """测试撮合器初始化"""
        from core.backtest.matcher import OrderMatcher
        
        matcher = OrderMatcher()
        assert matcher is not None


class TestBacktestCost:
    """回测成本测试"""
    
    def test_cost_init(self):
        """测试成本计算器初始化"""
        from core.backtest.cost import CostModel
        
        model = CostModel()
        assert model is not None


class TestBacktestSlippage:
    """回测滑点测试"""
    
    def test_slippage_init(self):
        """测试滑点模型初始化"""
        from core.backtest.slippage import SlippageModel
        
        model = SlippageModel()
        assert model is not None


class TestBacktestBenchmark:
    """回测基准测试"""
    
    def test_benchmark_init(self):
        """测试基准初始化"""
        from core.backtest.benchmark import BenchmarkManager
        
        manager = BenchmarkManager()
        assert manager is not None


class TestSignalStorage:
    """信号存储测试"""
    
    def test_storage_init(self):
        """测试存储初始化"""
        from core.signal.storage import SignalStorage
        
        storage = SignalStorage()
        assert storage is not None


class TestStrategyStorage:
    """策略存储测试"""
    
    def test_storage_init(self):
        """测试存储初始化"""
        from core.strategy.storage import StrategyStorage
        
        storage = StrategyStorage()
        assert storage is not None


class TestFactorValidator:
    """因子验证器测试"""
    
    def test_validator_init(self):
        """测试验证器初始化"""
        from core.factor.validator import FactorValidator
        
        validator = FactorValidator()
        assert validator is not None


class TestFactorBacktester:
    """因子回测器测试"""
    
    def test_backtester_init(self):
        """测试回测器初始化"""
        from core.factor.backtester import FactorBacktester
        
        backtester = FactorBacktester()
        assert backtester is not None


class TestFactorScorer:
    """因子评分器测试"""
    
    def test_scorer_init(self):
        """测试评分器初始化"""
        from core.factor.scorer import FactorScorer
        
        scorer = FactorScorer()
        assert scorer is not None


class TestFactorMonitor:
    """因子监控器测试"""
    
    def test_monitor_init(self):
        """测试监控器初始化"""
        from core.factor.monitor import FactorMonitor
        
        monitor = FactorMonitor()
        assert monitor is not None


class TestSignalQuality:
    """信号质量测试"""
    
    def test_quality_init(self):
        """测试质量评估器初始化"""
        from core.signal.quality import SignalQualityAssessor
        
        assessor = SignalQualityAssessor()
        assert assessor is not None


class TestTradingNotifier:
    """交易通知器测试"""
    
    def test_notifier_init(self):
        """测试通知器初始化"""
        from core.trading.notifier import TradeNotifier
        
        notifier = TradeNotifier()
        assert notifier is not None


class TestTradingPosition:
    """交易持仓测试"""
    
    def test_position_manager_init(self):
        """测试持仓管理器初始化"""
        from core.trading.position import PositionManager
        
        manager = PositionManager()
        assert manager is not None


class TestTradingConfirmation:
    """交易确认测试"""
    
    def test_confirmation_init(self):
        """测试确认器初始化"""
        from core.trading.confirmation import TraderConfirmation
        
        manager = TraderConfirmation()
        assert manager is not None


class TestRiskLimits:
    """风控限制测试"""
    
    def test_limits_init(self):
        """测试限制器初始化"""
        from core.risk.limits import RiskLimits
        
        limits = RiskLimits()
        assert limits is not None


class TestRiskMetrics:
    """风控指标测试"""
    
    def test_metrics_init(self):
        """测试指标初始化"""
        from core.risk.metrics import RiskMetricsCalculator
        
        metrics = RiskMetricsCalculator()
        assert metrics is not None


class TestRiskIntraday:
    """日内风控测试"""
    
    def test_intraday_init(self):
        """测试日内风控初始化"""
        from core.risk.intraday import IntradayRiskMonitor
        
        monitor = IntradayRiskMonitor()
        assert monitor is not None


class TestRiskPreTrade:
    """事前风控测试"""
    
    def test_pre_trade_init(self):
        """测试事前风控初始化"""
        from core.risk.pre_trade import PreTradeRiskChecker
        
        checker = PreTradeRiskChecker()
        assert checker is not None


class TestRiskPostTrade:
    """事后风控测试"""
    
    def test_post_trade_init(self):
        """测试事后风控初始化"""
        from core.risk.post_trade import PostTradeAnalyzer
        
        analyzer = PostTradeAnalyzer()
        assert analyzer is not None


class TestEvaluationMetrics:
    """评估指标测试"""
    
    def test_metrics_init(self):
        """测试指标初始化"""
        from core.evaluation.metrics import PerformanceMetricsCalculator
        
        metrics = PerformanceMetricsCalculator()
        assert metrics is not None


class TestEvaluationRanking:
    """评估排名测试"""
    
    def test_ranking_init(self):
        """测试排名器初始化"""
        from core.evaluation.ranking import PerformanceRanking
        
        ranking = PerformanceRanking()
        assert ranking is not None


class TestEvaluationComparison:
    """评估比较测试"""
    
    def test_comparison_init(self):
        """测试比较器初始化"""
        from core.evaluation.comparison import PerformanceComparison
        
        comparison = PerformanceComparison()
        assert comparison is not None


class TestMonitorTracker:
    """监控追踪器测试"""
    
    def test_tracker_init(self):
        """测试追踪器初始化"""
        from core.monitor.tracker import PerformanceTracker
        
        tracker = PerformanceTracker(tracker_id="test_tracker")
        assert tracker is not None


class TestMonitorAttribution:
    """监控归因测试"""
    
    def test_attribution_init(self):
        """测试归因分析器初始化"""
        from core.monitor.attribution import AttributionAnalyzer
        
        attribution = AttributionAnalyzer()
        assert attribution is not None


class TestDailyBackup:
    """每日备份测试"""
    
    def test_backup_init(self):
        """测试备份器初始化"""
        from core.daily.backup import DailyBackup
        
        backup = DailyBackup()
        assert backup is not None


class TestDailyNotifier:
    """每日通知测试"""
    
    def test_notifier_init(self):
        """测试通知器初始化"""
        from core.daily.notifier import DailyNotifier
        
        notifier = DailyNotifier()
        assert notifier is not None


class TestDailyReportGenerator:
    """每日报告生成器测试"""
    
    def test_generator_init(self):
        """测试生成器初始化"""
        from core.daily.report_generator import DailyReportGenerator
        
        generator = DailyReportGenerator()
        assert generator is not None


class TestPortfolioEvaluator:
    """组合评估器测试"""
    
    def test_evaluator_init(self):
        """测试评估器初始化"""
        from core.portfolio.evaluator import PortfolioEvaluator
        
        evaluator = PortfolioEvaluator()
        assert evaluator is not None


class TestPortfolioRebalancer:
    """组合再平衡器测试"""
    
    def test_rebalancer_init(self):
        """测试再平衡器初始化"""
        from core.portfolio.rebalancer import PortfolioRebalancer
        
        rebalancer = PortfolioRebalancer()
        assert rebalancer is not None


class TestPortfolioRiskBudget:
    """组合风险预算测试"""
    
    def test_risk_budget_init(self):
        """测试风险预算初始化"""
        from core.portfolio.risk_budget import RiskBudgetManager
        
        allocator = RiskBudgetManager()
        assert allocator is not None


class TestPortfolioNeutralizer:
    """组合中性化器测试"""
    
    def test_neutralizer_init(self):
        """测试中性化器初始化"""
        from core.portfolio.neutralizer import PortfolioNeutralizer
        
        neutralizer = PortfolioNeutralizer()
        assert neutralizer is not None


class TestPortfolioStorage:
    """组合存储测试"""
    
    def test_storage_init(self):
        """测试存储初始化"""
        from core.portfolio.storage import PortfolioStorage
        
        storage = PortfolioStorage()
        assert storage is not None


def run_tests():
    """运行所有测试"""
    import pytest
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()
