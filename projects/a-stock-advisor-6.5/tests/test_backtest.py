"""
回测系统测试

测试回测引擎、订单撮合器、绩效分析器等核心功能。
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from core.backtest.engine import BacktestEngine, BacktestConfig, BacktestMode
from core.backtest.matcher import OrderMatcher, Order, OrderType, OrderStatus
from core.backtest.analyzer import PerformanceAnalyzer, PerformanceMetrics
from core.backtest.reporter import BacktestReporter, ReportConfig
from core.backtest.benchmark import BenchmarkManager, Benchmark
from core.backtest.slippage import SlippageModel, SlippageType
from core.backtest.cost import CostModel, TransactionCost


class TestSlippageModel:
    """滑点模型测试"""
    
    def test_fixed_slippage(self):
        """测试固定滑点模型"""
        model = SlippageModel.create(SlippageType.FIXED, slippage_rate=0.001)
        
        result = model.calculate_slippage(
            price=100.0,
            volume=1000,
            direction='buy'
        )
        
        assert result.original_price == 100.0
        assert result.adjusted_price == 100.1
        assert result.slippage_rate == 0.001
    
    def test_percentage_slippage(self):
        """测试百分比滑点模型"""
        model = SlippageModel.create(SlippageType.PERCENTAGE, base_rate=0.001)
        
        result = model.calculate_slippage(
            price=100.0,
            volume=1000,
            direction='sell'
        )
        
        assert result.original_price == 100.0
        assert result.adjusted_price < 100.0
        assert result.slippage_type == SlippageType.PERCENTAGE.value
    
    def test_volume_weighted_slippage(self):
        """测试成交量加权滑点模型"""
        model = SlippageModel.create(SlippageType.VOLUME_WEIGHTED, base_rate=0.0005)
        
        result = model.calculate_slippage(
            price=100.0,
            volume=10000,
            direction='buy',
            market_data={'avg_volume': 50000}
        )
        
        assert result.original_price == 100.0
        assert result.adjusted_price > 100.0


class TestCostModel:
    """成本模型测试"""
    
    def test_ashare_cost_model(self):
        """测试A股成本模型"""
        model = CostModel.create("ashare", commission_rate=0.0003, stamp_duty_rate=0.001)
        
        cost = model.calculate(
            price=100.0,
            volume=1000,
            direction='buy'
        )
        
        assert cost.total_cost > 0
        assert cost.stamp_duty == 0
        
        cost_sell = model.calculate(
            price=100.0,
            volume=1000,
            direction='sell'
        )
        
        assert cost_sell.stamp_duty > 0
        assert cost_sell.total_cost > cost.total_cost
    
    def test_total_cost_calculation(self):
        """测试总成本计算"""
        trades = [
            {'price': 100.0, 'volume': 1000, 'direction': 'buy'},
            {'price': 105.0, 'volume': 1000, 'direction': 'sell'},
        ]
        
        result = CostModel.calculate_total_cost(trades, "ashare")
        
        assert result['trade_count'] == 2
        assert result['total_cost'] > 0


class TestOrderMatcher:
    """订单撮合器测试"""
    
    def test_create_order(self):
        """测试创建订单"""
        matcher = OrderMatcher()
        
        order = matcher.create_order(
            stock_code="000001.SZ",
            direction="buy",
            quantity=1000,
            order_type=OrderType.MARKET
        )
        
        assert order.order_id.startswith("ORD")
        assert order.stock_code == "000001.SZ"
        assert order.direction == "buy"
        assert order.quantity == 1000
        assert order.status == OrderStatus.PENDING
    
    def test_match_market_order(self):
        """测试市价单撮合"""
        matcher = OrderMatcher()
        
        order = matcher.create_order(
            stock_code="000001.SZ",
            direction="buy",
            quantity=1000,
            order_type=OrderType.MARKET
        )
        
        market_data = {
            'close': 10.0,
            'volume': 1000000
        }
        
        result = matcher.match(order, market_data)
        
        assert result.success
        assert result.filled_quantity > 0
        assert result.filled_price > 0
        assert result.transaction_cost is not None
    
    def test_match_limit_order(self):
        """测试限价单撮合"""
        matcher = OrderMatcher(slippage_params={'base_rate': 0})
        
        order = matcher.create_order(
            stock_code="000001.SZ",
            direction="buy",
            quantity=1000,
            order_type=OrderType.LIMIT,
            limit_price=10.0
        )
        
        market_data = {
            'close': 9.5,
            'volume': 1000000
        }
        
        result = matcher.match(order, market_data)
        
        assert result.filled_quantity > 0 or result.message == "限价买单未成交"
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        matcher = OrderMatcher()
        
        for i in range(3):
            order = matcher.create_order(
                stock_code=f"00000{i}.SZ",
                direction="buy",
                quantity=1000,
                order_type=OrderType.MARKET
            )
            matcher.match(order, {'close': 10.0, 'volume': 1000000})
        
        stats = matcher.get_statistics()
        
        assert stats['total_orders'] == 3
        assert stats['filled_orders'] == 3


class TestPerformanceAnalyzer:
    """绩效分析器测试"""
    
    @pytest.fixture
    def sample_returns(self):
        """生成样本收益率"""
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=252, freq='B')
        returns = pd.Series(np.random.normal(0.001, 0.02, 252), index=dates)
        return returns
    
    @pytest.fixture
    def sample_benchmark(self):
        """生成样本基准收益率"""
        np.random.seed(43)
        dates = pd.date_range('2020-01-01', periods=252, freq='B')
        returns = pd.Series(np.random.normal(0.0008, 0.015, 252), index=dates)
        return returns
    
    def test_analyze_returns(self, sample_returns):
        """测试分析收益率"""
        analyzer = PerformanceAnalyzer()
        
        metrics = analyzer.analyze(sample_returns)
        
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.total_return != 0
        assert metrics.annual_return != 0
        assert metrics.volatility > 0
        assert metrics.sharpe_ratio != 0
    
    def test_analyze_with_benchmark(self, sample_returns, sample_benchmark):
        """测试带基准的分析"""
        analyzer = PerformanceAnalyzer()
        
        metrics = analyzer.analyze(sample_returns, sample_benchmark)
        
        assert metrics.excess_return != 0
        assert metrics.information_ratio != 0
        assert metrics.beta != 0
    
    def test_calculate_rolling_metrics(self, sample_returns):
        """测试滚动指标计算"""
        analyzer = PerformanceAnalyzer()
        
        rolling = analyzer.calculate_rolling_metrics(sample_returns, window=20)
        
        assert 'rolling_return' in rolling.columns
        assert 'rolling_volatility' in rolling.columns
        assert 'rolling_sharpe' in rolling.columns
    
    def test_calculate_monthly_returns(self, sample_returns):
        """测试月度收益计算"""
        analyzer = PerformanceAnalyzer()
        
        monthly = analyzer.calculate_monthly_returns(sample_returns)
        
        assert len(monthly) > 0


class TestBenchmarkManager:
    """基准管理器测试"""
    
    def test_create_benchmark(self):
        """测试创建基准"""
        manager = BenchmarkManager()
        
        dates = pd.date_range('2020-01-01', periods=252, freq='B')
        data = pd.DataFrame({
            'date': dates,
            'close': np.random.uniform(3000, 4000, 252)
        })
        
        benchmark = manager.create_from_dataframe(
            data, "000300.SH", "沪深300"
        )
        
        assert benchmark.code == "000300.SH"
        assert benchmark.name == "沪深300"
        assert len(benchmark.data) == 252
    
    def test_compare_with_benchmark(self):
        """测试与基准对比"""
        manager = BenchmarkManager()
        
        dates = pd.date_range('2020-01-01', periods=252, freq='B')
        benchmark_data = pd.DataFrame({
            'date': dates,
            'close': np.random.uniform(3000, 4000, 252)
        })
        manager.create_from_dataframe(benchmark_data, "000300.SH", "沪深300")
        manager.set_default("000300.SH")
        
        np.random.seed(42)
        strategy_returns = pd.Series(
            np.random.normal(0.001, 0.02, 252),
            index=dates
        )
        
        comparison = manager.compare(strategy_returns)
        
        assert 'strategy_annual_return' in comparison or 'error' in comparison


class TestBacktestReporter:
    """回测报告生成器测试"""
    
    def test_generate_html_report(self, tmp_path):
        """测试生成HTML报告"""
        config = ReportConfig(output_dir=str(tmp_path))
        reporter = BacktestReporter(config)
        
        result = {
            'metrics': {
                'total_return': 0.15,
                'annual_return': 0.12,
                'sharpe_ratio': 1.5,
                'max_drawdown': -0.08,
                'trade_count': 50
            },
            'trades': []
        }
        
        file_path = reporter.generate(result, "test_report")
        
        assert file_path.endswith(".html")


class TestBacktestEngine:
    """回测引擎测试"""
    
    @pytest.fixture
    def sample_data(self):
        """生成样本数据"""
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=252, freq='B')
        
        data = []
        for date in dates:
            for stock in ['000001.SZ', '000002.SZ', '600000.SH']:
                data.append({
                    'date': date,
                    'stock_code': stock,
                    'open': np.random.uniform(10, 20),
                    'high': np.random.uniform(10, 20),
                    'low': np.random.uniform(10, 20),
                    'close': np.random.uniform(10, 20),
                    'volume': np.random.randint(100000, 1000000)
                })
        
        return pd.DataFrame(data)
    
    def test_run_backtest(self, sample_data):
        """测试运行回测"""
        config = BacktestConfig(
            initial_capital=1000000,
            start_date='2020-01-01',
            end_date='2020-12-31'
        )
        
        engine = BacktestEngine(config)
        
        def simple_strategy(date, data, portfolio, context):
            if len(portfolio.positions) == 0:
                return [
                    {'stock_code': '000001.SZ', 'weight': 0.5},
                    {'stock_code': '000002.SZ', 'weight': 0.5}
                ]
            return []
        
        result = engine.run(strategy=simple_strategy, data=sample_data)
        
        assert result.success
        assert result.metrics is not None
    
    def test_backtest_config(self):
        """测试回测配置"""
        config = BacktestConfig(
            initial_capital=500000,
            commission_rate=0.0005,
            slippage_rate=0.002
        )
        
        assert config.initial_capital == 500000
        assert config.commission_rate == 0.0005
        assert config.slippage_rate == 0.002


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
