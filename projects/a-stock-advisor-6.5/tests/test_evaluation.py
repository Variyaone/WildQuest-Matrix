"""
评估系统测试

测试因子评估器、策略评估器、绩效指标计算等核心功能。
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from core.evaluation.factor_evaluator import FactorEvaluator, FactorEvaluationResult
from core.evaluation.strategy_evaluator import StrategyEvaluator, StrategyEvaluationResult
from core.evaluation.metrics import PerformanceMetricsCalculator, MetricResult
from core.evaluation.comparison import PerformanceComparison
from core.evaluation.ranking import PerformanceRanking, RankingResult
from core.evaluation.report import EvaluationReportGenerator, ReportConfig


class TestPerformanceMetricsCalculator:
    """绩效指标计算器测试"""
    
    @pytest.fixture
    def sample_returns(self):
        """生成样本收益率"""
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=252, freq='B')
        returns = pd.Series(np.random.normal(0.001, 0.02, 252), index=dates)
        return returns
    
    def test_total_return(self, sample_returns):
        """测试累计收益率计算"""
        total_return = PerformanceMetricsCalculator.total_return(sample_returns)
        
        assert isinstance(total_return, float)
        assert total_return != 0
    
    def test_annual_return(self, sample_returns):
        """测试年化收益率计算"""
        annual_return = PerformanceMetricsCalculator.annual_return(sample_returns)
        
        assert isinstance(annual_return, float)
    
    def test_volatility(self, sample_returns):
        """测试波动率计算"""
        volatility = PerformanceMetricsCalculator.volatility(sample_returns)
        
        assert volatility > 0
    
    def test_max_drawdown(self, sample_returns):
        """测试最大回撤计算"""
        max_dd = PerformanceMetricsCalculator.max_drawdown(sample_returns)
        
        assert max_dd <= 0
    
    def test_sharpe_ratio(self, sample_returns):
        """测试夏普比率计算"""
        sharpe = PerformanceMetricsCalculator.sharpe_ratio(sample_returns)
        
        assert isinstance(sharpe, float)
    
    def test_sortino_ratio(self, sample_returns):
        """测试索提诺比率计算"""
        sortino = PerformanceMetricsCalculator.sortino_ratio(sample_returns)
        
        assert isinstance(sortino, float)
    
    def test_calmar_ratio(self, sample_returns):
        """测试卡玛比率计算"""
        calmar = PerformanceMetricsCalculator.calmar_ratio(sample_returns)
        
        assert isinstance(calmar, float)
    
    def test_var_cvar(self, sample_returns):
        """测试VaR和CVaR计算"""
        var = PerformanceMetricsCalculator.var(sample_returns, 0.95)
        cvar = PerformanceMetricsCalculator.cvar(sample_returns, 0.95)
        
        assert var <= 0
        assert cvar <= var
    
    def test_win_rate(self):
        """测试胜率计算"""
        trades = [
            {'pnl': 100},
            {'pnl': -50},
            {'pnl': 200},
            {'pnl': -30},
            {'pnl': 150}
        ]
        
        win_rate = PerformanceMetricsCalculator.win_rate(trades)
        
        assert win_rate == 0.6
    
    def test_profit_loss_ratio(self):
        """测试盈亏比计算"""
        trades = [
            {'pnl': 100},
            {'pnl': -50},
            {'pnl': 200},
            {'pnl': -150}
        ]
        
        pl_ratio = PerformanceMetricsCalculator.profit_loss_ratio(trades)
        
        assert pl_ratio == 1.5
    
    def test_ic_calculation(self):
        """测试IC计算"""
        np.random.seed(42)
        factor_values = pd.Series(np.random.randn(100))
        forward_returns = pd.Series(np.random.randn(100))
        
        ic = PerformanceMetricsCalculator.ic_mean(factor_values, forward_returns)
        
        assert isinstance(ic, float)
        assert -1 <= ic <= 1
    
    def test_calculate_all_metrics(self, sample_returns):
        """测试计算所有指标"""
        metrics = PerformanceMetricsCalculator.calculate_all_metrics(sample_returns)
        
        assert 'total_return' in metrics
        assert 'annual_return' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        
        for name, metric in metrics.items():
            assert isinstance(metric, MetricResult)
            assert metric.name != ""


class TestFactorEvaluator:
    """因子评估器测试"""
    
    @pytest.fixture
    def sample_factor_data(self):
        """生成样本因子数据"""
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=100, freq='B')
        stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000651.SZ']
        
        data = {}
        for date in dates:
            data[date] = pd.Series(np.random.randn(len(stocks)), index=stocks)
        
        return pd.DataFrame(data).T
    
    @pytest.fixture
    def sample_return_data(self):
        """生成样本收益数据"""
        np.random.seed(43)
        dates = pd.date_range('2020-01-01', periods=100, freq='B')
        stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000651.SZ']
        
        data = {}
        for date in dates:
            data[date] = pd.Series(np.random.normal(0.001, 0.02, len(stocks)), index=stocks)
        
        return pd.DataFrame(data).T
    
    def test_evaluate_factor(self, sample_factor_data, sample_return_data):
        """测试因子评估"""
        evaluator = FactorEvaluator()
        
        result = evaluator.evaluate(
            factor_data=sample_factor_data,
            return_data=sample_return_data,
            factor_id="F00001",
            factor_name="动量因子"
        )
        
        assert isinstance(result, FactorEvaluationResult)
        assert result.factor_id == "F00001"
        assert result.factor_name == "动量因子"
        assert result.total_score >= 0
    
    def test_factor_ic_calculation(self, sample_factor_data, sample_return_data):
        """测试因子IC计算"""
        evaluator = FactorEvaluator()
        
        ic_result = evaluator._calculate_ic(sample_factor_data, sample_return_data)
        
        assert 'ic_mean' in ic_result
        assert 'ic_std' in ic_result
        assert 'ir' in ic_result
        assert 'trend' in ic_result
    
    def test_group_returns_calculation(self, sample_factor_data, sample_return_data):
        """测试分组收益计算"""
        evaluator = FactorEvaluator(n_groups=5)
        
        group_result = evaluator._calculate_group_returns(sample_factor_data, sample_return_data)
        
        assert 'monotonicity' in group_result
        assert 'long_short_return' in group_result
        assert 0 <= group_result['monotonicity'] <= 1
    
    def test_evaluate_multiple_factors(self, sample_factor_data, sample_return_data):
        """测试多因子评估"""
        evaluator = FactorEvaluator()
        
        factors_data = {
            'factor1': sample_factor_data,
            'factor2': sample_factor_data * 0.5
        }
        
        results = evaluator.evaluate_multiple(factors_data, sample_return_data)
        
        assert len(results) == 2
        for name, result in results.items():
            assert result.rank > 0
            assert result.total_factors == 2


class TestStrategyEvaluator:
    """策略评估器测试"""
    
    @pytest.fixture
    def sample_returns(self):
        """生成样本收益率"""
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=252, freq='B')
        returns = pd.Series(np.random.normal(0.001, 0.02, 252), index=dates)
        return returns
    
    @pytest.fixture
    def sample_benchmark(self):
        """生成样本基准"""
        np.random.seed(43)
        dates = pd.date_range('2020-01-01', periods=252, freq='B')
        returns = pd.Series(np.random.normal(0.0008, 0.015, 252), index=dates)
        return returns
    
    def test_evaluate_strategy(self, sample_returns, sample_benchmark):
        """测试策略评估"""
        evaluator = StrategyEvaluator()
        
        result = evaluator.evaluate(
            returns=sample_returns,
            benchmark_returns=sample_benchmark,
            strategy_id="ST00001",
            strategy_name="多因子策略"
        )
        
        assert isinstance(result, StrategyEvaluationResult)
        assert result.strategy_id == "ST00001"
        assert result.strategy_name == "多因子策略"
        assert result.cumulative_return != 0
    
    def test_strategy_with_trades(self, sample_returns, sample_benchmark):
        """测试带交易记录的策略评估"""
        evaluator = StrategyEvaluator()
        
        trades = [
            {'pnl': 100, 'holding_period': 5},
            {'pnl': -50, 'holding_period': 3},
            {'pnl': 200, 'holding_period': 10}
        ]
        
        result = evaluator.evaluate(
            returns=sample_returns,
            benchmark_returns=sample_benchmark,
            trades=trades
        )
        
        assert result.win_rate > 0
        assert result.trade_count == 3
    
    def test_evaluate_multiple_strategies(self, sample_returns, sample_benchmark):
        """测试多策略评估"""
        evaluator = StrategyEvaluator()
        
        np.random.seed(44)
        returns2 = pd.Series(np.random.normal(0.0008, 0.018, 252), index=sample_returns.index)
        
        strategies_returns = {
            'strategy1': sample_returns,
            'strategy2': returns2
        }
        
        results = evaluator.evaluate_multiple(strategies_returns, sample_benchmark)
        
        assert len(results) == 2
        for name, result in results.items():
            assert result.rank > 0


class TestPerformanceComparison:
    """绩效对比测试"""
    
    @pytest.fixture
    def sample_strategies(self):
        """生成样本策略收益"""
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=252, freq='B')
        
        return {
            'strategy1': pd.Series(np.random.normal(0.001, 0.02, 252), index=dates),
            'strategy2': pd.Series(np.random.normal(0.0008, 0.018, 252), index=dates),
            'strategy3': pd.Series(np.random.normal(0.0012, 0.022, 252), index=dates)
        }
    
    def test_compare_strategies(self, sample_strategies):
        """测试策略对比"""
        comparison = PerformanceComparison()
        
        result = comparison.compare_strategies(sample_strategies)
        
        assert len(result) == 3
        assert 'strategy_name' in result.columns
        assert 'annual_return' in result.columns
        assert 'sharpe_ratio' in result.columns
    
    def test_compare_with_benchmark(self, sample_strategies):
        """测试与基准对比"""
        comparison = PerformanceComparison()
        
        np.random.seed(43)
        dates = pd.date_range('2020-01-01', periods=252, freq='B')
        benchmark = pd.Series(np.random.normal(0.0005, 0.015, 252), index=dates)
        
        result = comparison.compare_with_benchmark(
            sample_strategies['strategy1'],
            benchmark,
            "沪深300"
        )
        
        assert 'strategy' in result
        assert 'benchmark' in result
        assert 'comparison' in result
        assert result['comparison']['alpha'] != 0
    
    def test_compare_periods(self, sample_strategies):
        """测试分阶段对比"""
        comparison = PerformanceComparison()
        
        periods = {
            'Q1': ('2020-01-01', '2020-03-31'),
            'Q2': ('2020-04-01', '2020-06-30')
        }
        
        result = comparison.compare_periods(sample_strategies['strategy1'], periods)
        
        assert len(result) == 2
        assert 'period' in result.columns
        assert 'total_return' in result.columns


class TestPerformanceRanking:
    """绩效排名测试"""
    
    def test_rank_strategies(self):
        """测试策略排名"""
        ranking = PerformanceRanking()
        
        evaluation_results = {
            'strategy1': {
                'annual_return': 0.15,
                'max_drawdown': -0.10,
                'sharpe_ratio': 1.5,
                'stability_score': 80
            },
            'strategy2': {
                'annual_return': 0.10,
                'max_drawdown': -0.15,
                'sharpe_ratio': 1.0,
                'stability_score': 70
            },
            'strategy3': {
                'annual_return': 0.20,
                'max_drawdown': -0.12,
                'sharpe_ratio': 1.8,
                'stability_score': 85
            }
        }
        
        results = ranking.rank_strategies(evaluation_results)
        
        assert len(results) == 3
        assert results[0].rank == 1
        assert results[0].is_top_quartile
    
    def test_rank_by_metric(self):
        """测试按指标排名"""
        ranking = PerformanceRanking()
        
        data = {
            'A': 0.15,
            'B': 0.10,
            'C': 0.20
        }
        
        results = ranking.rank_by_metric(data, higher_is_better=True)
        
        assert len(results) == 3
        assert results[0].name == 'C'
        assert results[0].score == 0.20
    
    def test_get_top_performers(self):
        """测试获取前N名"""
        ranking = PerformanceRanking()
        
        evaluation_results = {
            f'strategy{i}': {
                'annual_return': 0.10 + i * 0.01,
                'max_drawdown': -0.10,
                'sharpe_ratio': 1.0 + i * 0.1,
                'stability_score': 70
            }
            for i in range(10)
        }
        
        results = ranking.rank_strategies(evaluation_results)
        top5 = ranking.get_top_performers(results, 5)
        
        assert len(top5) == 5
        assert top5[0].rank == 1


class TestEvaluationReportGenerator:
    """评估报告生成器测试"""
    
    def test_generate_factor_report(self, tmp_path):
        """测试生成因子报告"""
        config = ReportConfig(output_dir=str(tmp_path))
        generator = EvaluationReportGenerator(config)
        
        result = {
            'factor_id': 'F00001',
            'factor_name': '动量因子',
            'evaluation_date': '2025-01-01',
            'ic_mean': 0.035,
            'ic_std': 0.078,
            'ir': 0.45,
            'total_score': 85,
            'rank': 1,
            'total_factors': 10
        }
        
        file_path = generator.generate_factor_report(result)
        
        assert file_path.endswith(".html")
    
    def test_generate_strategy_report(self, tmp_path):
        """测试生成策略报告"""
        config = ReportConfig(output_dir=str(tmp_path))
        generator = EvaluationReportGenerator(config)
        
        result = {
            'strategy_id': 'ST00001',
            'strategy_name': '多因子策略',
            'evaluation_date': '2025-01-01',
            'cumulative_return': 0.85,
            'annual_return': 0.12,
            'sharpe_ratio': 1.5,
            'max_drawdown': -0.15,
            'total_score': 80,
            'rank': 2,
            'total_strategies': 10
        }
        
        file_path = generator.generate_strategy_report(result)
        
        assert file_path.endswith(".html")
    
    def test_generate_comparison_report(self, tmp_path):
        """测试生成对比报告"""
        config = ReportConfig(output_dir=str(tmp_path))
        generator = EvaluationReportGenerator(config)
        
        comparison_df = pd.DataFrame({
            'strategy_name': ['A', 'B', 'C'],
            'annual_return': [0.15, 0.10, 0.12],
            'sharpe_ratio': [1.5, 1.0, 1.2]
        })
        
        file_path = generator.generate_comparison_report(comparison_df)
        
        assert file_path.endswith(".html")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
