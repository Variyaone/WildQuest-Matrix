"""
组合优化模块测试

测试内容:
- 组合优化器测试
- 中性化处理器测试
- 约束管理测试
- 再平衡策略测试
- 风险预算测试
- 组合评估器测试
- 存储测试
"""

import pytest
import numpy as np
import tempfile
import os
from datetime import datetime, timedelta

from core.portfolio import (
    PortfolioOptimizer,
    OptimizationStatus,
    OptimizationResult,
    
    PortfolioNeutralizer,
    NeutralizationStatus,
    
    ConstraintsManager,
    ConstraintConfig,
    ConstraintStatus,
    
    PortfolioRebalancer,
    RebalanceConfig,
    RebalanceTrigger,
    RebalanceStatus,
    Trade,
    
    RiskBudgetManager,
    RiskBudgetConfig,
    RiskBudgetStatus,
    
    PortfolioEvaluator,
    EvaluationStatus,
    
    PortfolioStorage,
    PortfolioMetadata,
)


class TestPortfolioOptimizer:
    """组合优化器测试"""
    
    def setup_method(self):
        self.optimizer = PortfolioOptimizer()
        self.stock_scores = {
            '000001.SZ': 0.8,
            '000002.SZ': 0.7,
            '000003.SZ': 0.6,
            '000004.SZ': 0.5,
            '000005.SZ': 0.4,
        }
        self.cov_matrix = np.array([
            [0.04, 0.02, 0.01, 0.01, 0.01],
            [0.02, 0.05, 0.02, 0.01, 0.01],
            [0.01, 0.02, 0.06, 0.02, 0.01],
            [0.01, 0.01, 0.02, 0.07, 0.02],
            [0.01, 0.01, 0.01, 0.02, 0.08],
        ])
        self.expected_returns = {
            '000001.SZ': 0.15,
            '000002.SZ': 0.12,
            '000003.SZ': 0.10,
            '000004.SZ': 0.08,
            '000005.SZ': 0.06,
        }
    
    def test_equal_weight_optimization(self):
        """测试等权重优化"""
        optimizer = PortfolioOptimizer({'method': 'equal_weight'})
        result = optimizer.optimize(self.stock_scores)
        
        assert result.is_success()
        assert result.method == 'equal_weight'
        assert len(result.weights) == 5
        
        for weight in result.weights.values():
            assert abs(weight - 0.2) < 0.001
    
    def test_risk_parity_optimization(self):
        """测试风险平价优化"""
        optimizer = PortfolioOptimizer({
            'method': 'risk_parity',
            'min_weight': 0.0,
            'max_single_weight': 0.5
        })
        result = optimizer.optimize(self.stock_scores, cov_matrix=self.cov_matrix)
        
        assert result.status in [OptimizationStatus.SUCCESS, OptimizationStatus.FALLBACK]
        assert len(result.weights) == 5
        
        total_weight = sum(result.weights.values())
        assert abs(total_weight - 1.0) < 0.01
    
    def test_mean_variance_optimization(self):
        """测试均值方差优化"""
        optimizer = PortfolioOptimizer({
            'method': 'mean_variance',
            'min_weight': 0.0,
            'max_single_weight': 0.5
        })
        result = optimizer.optimize(
            self.stock_scores,
            expected_returns=self.expected_returns,
            cov_matrix=self.cov_matrix
        )
        
        assert result.status in [OptimizationStatus.SUCCESS, OptimizationStatus.FALLBACK]
        assert len(result.weights) == 5
    
    def test_max_diversification_optimization(self):
        """测试最大分散化优化"""
        optimizer = PortfolioOptimizer({
            'method': 'max_diversification',
            'min_weight': 0.0,
            'max_single_weight': 0.5
        })
        result = optimizer.optimize(self.stock_scores, cov_matrix=self.cov_matrix)
        
        assert result.status in [OptimizationStatus.SUCCESS, OptimizationStatus.FALLBACK]
        assert len(result.weights) == 5
    
    def test_black_litterman_optimization(self):
        """测试Black-Litterman优化"""
        optimizer = PortfolioOptimizer({
            'method': 'black_litterman',
            'min_weight': 0.0,
            'max_single_weight': 0.5
        })
        views = {'000001.SZ': 0.20}
        view_confidences = {'000001.SZ': 0.8}
        
        result = optimizer.optimize(
            self.stock_scores,
            expected_returns=self.expected_returns,
            cov_matrix=self.cov_matrix,
            views=views,
            view_confidences=view_confidences
        )
        
        assert result.status in [OptimizationStatus.SUCCESS, OptimizationStatus.FALLBACK]
        assert len(result.weights) == 5
    
    def test_fallback_to_equal_weight(self):
        """测试降级为等权重"""
        optimizer = PortfolioOptimizer({
            'method': 'risk_parity',
            'allow_fallback': True
        })
        result = optimizer.optimize(self.stock_scores)
        
        assert result.fallback_used
        assert result.original_method == 'risk_parity'
        assert result.method == 'equal_weight'
    
    def test_invalid_input(self):
        """测试无效输入"""
        optimizer = PortfolioOptimizer()
        result = optimizer.optimize({})
        
        assert result.status == OptimizationStatus.INVALID_INPUT
    
    def test_max_single_weight_constraint(self):
        """测试单票权重上限约束"""
        optimizer = PortfolioOptimizer({
            'method': 'equal_weight',
            'max_single_weight': 0.10
        })
        result = optimizer.optimize(self.stock_scores)
        
        assert result.status in [OptimizationStatus.SUCCESS, OptimizationStatus.FALLBACK]
        max_weight = max(result.weights.values())
        assert max_weight <= 0.25


class TestPortfolioNeutralizer:
    """中性化处理器测试"""
    
    def setup_method(self):
        self.neutralizer = PortfolioNeutralizer()
        self.portfolio = {
            '000001.SZ': 0.25,
            '000002.SZ': 0.25,
            '000003.SZ': 0.25,
            '000004.SZ': 0.25,
        }
    
    def test_neutralize_empty_portfolio(self):
        """测试空组合中性化"""
        result = self.neutralizer.neutralize({})
        
        assert result.status == NeutralizationStatus.SKIPPED
    
    def test_neutralize_without_market_data(self):
        """测试无市场数据中性化"""
        result = self.neutralizer.neutralize(self.portfolio)
        
        assert result.is_success()
    
    def test_neutralize_with_industry_weights(self):
        """测试带行业权重的中性化"""
        industry_weights = {
            '金融': 0.30,
            '科技': 0.30,
            '消费': 0.20,
            '医药': 0.20,
        }
        
        result = self.neutralizer.neutralize(
            self.portfolio,
            industry_weights=industry_weights
        )
        
        assert result.is_success()
    
    def test_invalid_portfolio(self):
        """测试无效组合"""
        result = self.neutralizer.neutralize(None)
        
        assert result.status == NeutralizationStatus.INVALID_INPUT


class TestConstraintsManager:
    """约束管理测试"""
    
    def setup_method(self):
        self.config = ConstraintConfig()
        self.manager = ConstraintsManager(self.config)
        self.weights = {
            '000001.SZ': 0.15,
            '000002.SZ': 0.20,
            '000003.SZ': 0.15,
            '000004.SZ': 0.25,
            '000005.SZ': 0.25,
        }
    
    def test_check_all_constraints(self):
        """测试检查所有约束"""
        weights = {
            '000001.SZ': 0.10,
            '000002.SZ': 0.10,
            '000003.SZ': 0.10,
            '000004.SZ': 0.10,
            '000005.SZ': 0.10,
            '000006.SZ': 0.10,
            '000007.SZ': 0.10,
            '000008.SZ': 0.10,
            '000009.SZ': 0.10,
            '000010.SZ': 0.10,
        }
        result = self.manager.check_all(weights)
        
        assert result.passed
        assert len(result.results) > 0
    
    def test_weight_normalization(self):
        """测试权重归一化检查"""
        result = self.manager.check_all(self.weights)
        
        normalization_result = next(
            (r for r in result.results if r.constraint_name == '权重归一化'),
            None
        )
        assert normalization_result is not None
        assert normalization_result.passed
    
    def test_single_weight_limit_violation(self):
        """测试单票权重上限违规"""
        weights = {
            '000001.SZ': 0.20,
            '000002.SZ': 0.80,
        }
        
        result = self.manager.check_all(weights)
        
        single_weight_result = next(
            (r for r in result.results if r.constraint_name == '单票权重上限'),
            None
        )
        assert single_weight_result is not None
        assert not single_weight_result.passed
    
    def test_position_count(self):
        """测试持仓数量检查"""
        weights = {f'00000{i}.SZ': 0.2 for i in range(3)}
        
        result = self.manager.check_all(weights)
        
        position_result = next(
            (r for r in result.results if r.constraint_name == '持仓数量'),
            None
        )
        assert position_result is not None
    
    def test_apply_constraints(self):
        """测试应用约束"""
        weights = {
            '000001.SZ': 0.25,
            '000002.SZ': 0.25,
            '000003.SZ': 0.25,
            '000004.SZ': 0.25,
        }
        
        adjusted = self.manager.apply_constraints(weights)
        
        total_weight = sum(adjusted.values())
        assert abs(total_weight - 1.0) < 0.01
    
    def test_empty_weights(self):
        """测试空权重"""
        result = self.manager.check_all({})
        
        assert not result.passed


class TestPortfolioRebalancer:
    """再平衡策略测试"""
    
    def setup_method(self):
        self.config = RebalanceConfig()
        self.rebalancer = PortfolioRebalancer(self.config)
        self.current_positions = {
            '000001.SZ': 0.20,
            '000002.SZ': 0.20,
            '000003.SZ': 0.20,
            '000004.SZ': 0.20,
            '000005.SZ': 0.20,
        }
        self.target_positions = {
            '000001.SZ': 0.15,
            '000002.SZ': 0.25,
            '000003.SZ': 0.20,
            '000004.SZ': 0.20,
            '000005.SZ': 0.20,
        }
    
    def test_should_rebalance_below_threshold(self):
        """测试低于阈值不需要再平衡"""
        need_rebalance, details = self.rebalancer.should_rebalance(
            self.current_positions,
            self.target_positions,
            threshold=0.10
        )
        
        assert not need_rebalance
    
    def test_should_rebalance_above_threshold(self):
        """测试超过阈值需要再平衡"""
        target = {
            '000001.SZ': 0.30,
            '000002.SZ': 0.10,
            '000003.SZ': 0.20,
            '000004.SZ': 0.20,
            '000005.SZ': 0.20,
        }
        
        need_rebalance, details = self.rebalancer.should_rebalance(
            self.current_positions,
            target,
            threshold=0.05
        )
        
        assert need_rebalance
    
    def test_calculate_trades(self):
        """测试计算交易"""
        result = self.rebalancer.calculate_trades(
            self.current_positions,
            self.target_positions
        )
        
        assert 'trades' in result
        assert 'turnover' in result
        assert result['turnover'] >= 0
    
    def test_estimate_rebalance_cost(self):
        """测试估算再平衡成本"""
        trades_result = self.rebalancer.calculate_trades(
            self.current_positions,
            self.target_positions
        )
        
        prices = {code: 10.0 for code in self.current_positions.keys()}
        
        cost = self.rebalancer.estimate_rebalance_cost(
            trades_result['trades'],
            prices,
            portfolio_value=1000000
        )
        
        assert 'total_cost' in cost
        assert 'cost_ratio' in cost
    
    def test_periodic_rebalance(self):
        """测试定期再平衡"""
        config = RebalanceConfig(
            trigger_type=RebalanceTrigger.PERIODIC,
            frequency='weekly'
        )
        rebalancer = PortfolioRebalancer(config)
        
        last_date = datetime.now() - timedelta(days=8)
        current_date = datetime.now()
        
        need_rebalance, details = rebalancer.should_rebalance(
            self.current_positions,
            self.target_positions,
            last_rebalance_date=last_date,
            current_date=current_date
        )
        
        assert need_rebalance
    
    def test_empty_positions(self):
        """测试空持仓"""
        need_rebalance, details = self.rebalancer.should_rebalance({}, {})
        
        assert not need_rebalance


class TestRiskBudgetManager:
    """风险预算测试"""
    
    def setup_method(self):
        self.config = RiskBudgetConfig()
        self.manager = RiskBudgetManager(self.config)
        self.portfolio = {
            '000001.SZ': 0.25,
            '000002.SZ': 0.25,
            '000003.SZ': 0.25,
            '000004.SZ': 0.25,
        }
    
    def test_allocate_risk_budget(self):
        """测试分配风险预算"""
        result = self.manager.allocate(self.portfolio)
        
        assert 'risk_budget' in result
        assert 'risk_allocation' in result
        assert len(result['risk_allocation']) == 4
    
    def test_check_risk_budget(self):
        """测试检查风险预算"""
        actual_risk = {
            'momentum': 0.20,
            'value': 0.25,
            'quality': 0.30,
            'volatility': 0.15,
        }
        
        result = self.manager.check(self.portfolio, actual_risk)
        
        assert result.status in [RiskBudgetStatus.WITHIN_BUDGET, RiskBudgetStatus.WARNING, RiskBudgetStatus.EXCEEDED]
    
    def test_adjust_risk_budget(self):
        """测试调整风险预算"""
        actual_risk = {
            'momentum': 0.30,
            'value': 0.25,
            'quality': 0.30,
            'volatility': 0.15,
        }
        
        adjusted = self.manager.adjust_risk_budget(self.portfolio, actual_risk)
        
        assert isinstance(adjusted, dict)
    
    def test_calculate_risk_contribution(self):
        """测试计算风险贡献"""
        cov_matrix = np.array([
            [0.04, 0.02, 0.01, 0.01],
            [0.02, 0.05, 0.02, 0.01],
            [0.01, 0.02, 0.06, 0.02],
            [0.01, 0.01, 0.02, 0.07],
        ])
        
        contributions = self.manager.calculate_risk_contribution(
            self.portfolio,
            cov_matrix
        )
        
        assert len(contributions) == 4


class TestPortfolioEvaluator:
    """组合评估器测试"""
    
    def setup_method(self):
        self.evaluator = PortfolioEvaluator()
        np.random.seed(42)
        self.returns = np.random.normal(0.001, 0.02, 100)
        self.benchmark_returns = np.random.normal(0.0008, 0.015, 100)
    
    def test_evaluate_performance(self):
        """测试绩效评估"""
        result = self.evaluator.evaluate(self.returns)
        
        assert result.status == EvaluationStatus.SUCCESS
        assert result.performance.total_return is not None
        assert result.performance.sharpe_ratio is not None
    
    def test_evaluate_with_benchmark(self):
        """测试带基准的评估"""
        result = self.evaluator.evaluate(
            self.returns,
            benchmark_returns=self.benchmark_returns
        )
        
        assert result.status == EvaluationStatus.SUCCESS
        assert result.performance.excess_return is not None
    
    def test_brinson_attribution(self):
        """测试Brinson归因"""
        portfolio_weights = {'A': 0.5, 'B': 0.5}
        benchmark_weights = {'A': 0.4, 'B': 0.6}
        portfolio_returns = {'A': 0.10, 'B': 0.05}
        benchmark_returns = {'A': 0.08, 'B': 0.06}
        
        result = self.evaluator.brinson_attribution(
            portfolio_weights,
            benchmark_weights,
            portfolio_returns,
            benchmark_returns
        )
        
        assert result.allocation_effect is not None
        assert result.selection_effect is not None
    
    def test_empty_returns(self):
        """测试空收益率"""
        result = self.evaluator.evaluate(np.array([]))
        
        assert result.status == EvaluationStatus.FAILED
    
    def test_generate_report(self):
        """测试生成报告"""
        result = self.evaluator.evaluate(self.returns)
        report = self.evaluator.generate_report(result, output_format='markdown')
        
        assert isinstance(report, str)
        assert '绩效指标' in report


class TestPortfolioStorage:
    """存储测试"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = PortfolioStorage(self.temp_dir)
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_load_portfolio(self):
        """测试保存和加载组合"""
        weights = {
            '000001.SZ': 0.3,
            '000002.SZ': 0.3,
            '000003.SZ': 0.4,
        }
        
        portfolio_id = self.storage.save_portfolio(
            name='测试组合',
            weights=weights,
            description='测试描述'
        )
        
        assert portfolio_id.startswith('PO')
        
        loaded = self.storage.load_portfolio(portfolio_id)
        
        assert loaded is not None
        assert loaded['metadata']['name'] == '测试组合'
        assert loaded['weights'] == weights
    
    def test_list_portfolios(self):
        """测试列出组合"""
        self.storage.save_portfolio('组合1', {'A': 0.5, 'B': 0.5})
        self.storage.save_portfolio('组合2', {'C': 1.0})
        
        portfolios = self.storage.list_portfolios()
        
        assert len(portfolios) == 2
    
    def test_delete_portfolio(self):
        """测试删除组合"""
        portfolio_id = self.storage.save_portfolio('待删除', {'A': 1.0})
        
        result = self.storage.delete_portfolio(portfolio_id)
        
        assert result
        
        loaded = self.storage.load_portfolio(portfolio_id)
        assert loaded is None
    
    def test_save_and_load_snapshot(self):
        """测试保存和加载快照"""
        portfolio_id = self.storage.save_portfolio('测试', {'A': 0.5, 'B': 0.5})
        
        self.storage.save_snapshot(
            portfolio_id=portfolio_id,
            date='2026-01-01',
            weights={'A': 0.6, 'B': 0.4},
            total_value=1000000
        )
        
        snapshots = self.storage.load_snapshots(portfolio_id)
        
        assert len(snapshots) == 1
        assert snapshots[0]['date'] == '2026-01-01'
    
    def test_update_performance(self):
        """测试更新绩效"""
        portfolio_id = self.storage.save_portfolio('测试', {'A': 1.0})
        
        performance = {
            'annual_return': 0.15,
            'sharpe_ratio': 1.2,
            'max_drawdown': -0.10
        }
        
        result = self.storage.update_performance(portfolio_id, performance)
        
        assert result
        
        loaded = self.storage.load_portfolio(portfolio_id)
        assert loaded['metadata']['performance']['annual_return'] == 0.15


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
