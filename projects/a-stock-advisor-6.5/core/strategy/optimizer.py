"""
策略优化器模块

自动优化策略参数，支持网格搜索、贝叶斯优化、遗传算法。
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import itertools
import random

import pandas as pd
import numpy as np

from .registry import (
    StrategyMetadata, 
    StrategyPerformance,
    SignalConfig,
    RiskParams,
    RebalanceFrequency,
    get_strategy_registry
)
from .backtester import StrategyBacktester, BacktestResult, get_strategy_backtester
from ..infrastructure.exceptions import StrategyException


class OptimizationMethod(Enum):
    """优化方法"""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    GENETIC = "genetic"


class OptimizationTarget(Enum):
    """优化目标"""
    SHARPE_RATIO = "sharpe_ratio"
    TOTAL_RETURN = "total_return"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"


@dataclass
class ParameterRange:
    """参数范围"""
    name: str
    values: List[Any]
    param_type: str = "discrete"
    
    def get_random_value(self) -> Any:
        """获取随机值"""
        return random.choice(self.values)


@dataclass
class OptimizationResult:
    """优化结果"""
    success: bool
    strategy_id: str
    best_params: Dict[str, Any]
    best_score: float
    best_performance: Optional[StrategyPerformance] = None
    all_results: List[Dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    error_message: Optional[str] = None


class GridSearchOptimizer:
    """网格搜索优化器"""
    
    def __init__(self, param_ranges: List[ParameterRange]):
        self.param_ranges = param_ranges
    
    def generate_combinations(self) -> List[Dict[str, Any]]:
        """生成所有参数组合"""
        param_names = [p.name for p in self.param_ranges]
        param_values = [p.values for p in self.param_ranges]
        
        combinations = []
        for values in itertools.product(*param_values):
            combinations.append(dict(zip(param_names, values)))
        
        return combinations


class RandomSearchOptimizer:
    """随机搜索优化器"""
    
    def __init__(
        self, 
        param_ranges: List[ParameterRange],
        n_iterations: int = 100
    ):
        self.param_ranges = param_ranges
        self.n_iterations = n_iterations
    
    def generate_random_params(self) -> Dict[str, Any]:
        """生成随机参数"""
        return {p.name: p.get_random_value() for p in self.param_ranges}


class GeneticOptimizer:
    """遗传算法优化器"""
    
    def __init__(
        self,
        param_ranges: List[ParameterRange],
        population_size: int = 50,
        n_generations: int = 20,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8
    ):
        self.param_ranges = param_ranges
        self.population_size = population_size
        self.n_generations = n_generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.population: List[Dict[str, Any]] = []
    
    def initialize_population(self):
        """初始化种群"""
        self.population = []
        for _ in range(self.population_size):
            individual = {p.name: p.get_random_value() for p in self.param_ranges}
            self.population.append(individual)
    
    def crossover(
        self, 
        parent1: Dict[str, Any], 
        parent2: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """交叉操作"""
        child1 = {}
        child2 = {}
        
        for key in parent1.keys():
            if random.random() < 0.5:
                child1[key] = parent1[key]
                child2[key] = parent2[key]
            else:
                child1[key] = parent2[key]
                child2[key] = parent1[key]
        
        return child1, child2
    
    def mutate(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        """变异操作"""
        mutated = individual.copy()
        
        for param in self.param_ranges:
            if random.random() < self.mutation_rate:
                mutated[param.name] = param.get_random_value()
        
        return mutated
    
    def select(self, fitness_scores: List[float]) -> int:
        """锦标赛选择"""
        tournament_size = 3
        tournament = random.sample(
            list(range(len(fitness_scores))), 
            min(tournament_size, len(fitness_scores))
        )
        
        best_idx = tournament[0]
        for idx in tournament[1:]:
            if fitness_scores[idx] > fitness_scores[best_idx]:
                best_idx = idx
        
        return best_idx


class StrategyOptimizer:
    """策略优化器"""
    
    def __init__(self):
        self._registry = get_strategy_registry()
        self._backtester = get_strategy_backtester()
    
    def optimize(
        self,
        strategy: Union[str, StrategyMetadata],
        param_ranges: List[ParameterRange],
        price_data: pd.DataFrame,
        factor_data: Dict[str, pd.DataFrame],
        method: OptimizationMethod = OptimizationMethod.GRID_SEARCH,
        target: OptimizationTarget = OptimizationTarget.SHARPE_RATIO,
        n_iterations: int = 100
    ) -> OptimizationResult:
        """优化策略参数"""
        if isinstance(strategy, str):
            strategy_meta = self._registry.get(strategy)
            if strategy_meta is None:
                return OptimizationResult(
                    success=False,
                    strategy_id=strategy,
                    best_params={},
                    best_score=0,
                    error_message=f"策略不存在: {strategy}"
                )
        else:
            strategy_meta = strategy
        
        try:
            if method == OptimizationMethod.RANDOM_SEARCH:
                return self._random_search(
                    strategy_meta, param_ranges, price_data,
                    factor_data, target, n_iterations
                )
            elif method == OptimizationMethod.GENETIC:
                return self._genetic_optimize(
                    strategy_meta, param_ranges, price_data,
                    factor_data, target, n_iterations
                )
            else:
                return self._grid_search(
                    strategy_meta, param_ranges, price_data,
                    factor_data, target
                )
                
        except Exception as e:
            return OptimizationResult(
                success=False,
                strategy_id=strategy_meta.id,
                best_params={},
                best_score=0,
                error_message=str(e)
            )
    
    def _grid_search(
        self,
        strategy: StrategyMetadata,
        param_ranges: List[ParameterRange],
        price_data: pd.DataFrame,
        factor_data: Dict[str, pd.DataFrame],
        target: OptimizationTarget
    ) -> OptimizationResult:
        """网格搜索"""
        optimizer = GridSearchOptimizer(param_ranges)
        combinations = optimizer.generate_combinations()
        
        all_results = []
        best_score = float('-inf')
        best_params = {}
        best_performance = None
        
        for params in combinations:
            modified_strategy = self._apply_params(strategy, params)
            
            result = self._backtester.backtest(
                modified_strategy,
                price_data,
                factor_data
            )
            
            if result.success:
                score = self._get_target_score(result, target)
                
                all_results.append({
                    "params": params,
                    "score": score,
                    "performance": result.performance.to_dict() if result.performance else {}
                })
                
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_performance = result.performance
        
        return OptimizationResult(
            success=True,
            strategy_id=strategy.id,
            best_params=best_params,
            best_score=best_score,
            best_performance=best_performance,
            all_results=all_results,
            iterations=len(combinations)
        )
    
    def _random_search(
        self,
        strategy: StrategyMetadata,
        param_ranges: List[ParameterRange],
        price_data: pd.DataFrame,
        factor_data: Dict[str, pd.DataFrame],
        target: OptimizationTarget,
        n_iterations: int
    ) -> OptimizationResult:
        """随机搜索"""
        optimizer = RandomSearchOptimizer(param_ranges, n_iterations)
        
        all_results = []
        best_score = float('-inf')
        best_params = {}
        best_performance = None
        
        for _ in range(n_iterations):
            params = optimizer.generate_random_params()
            modified_strategy = self._apply_params(strategy, params)
            
            result = self._backtester.backtest(
                modified_strategy,
                price_data,
                factor_data
            )
            
            if result.success:
                score = self._get_target_score(result, target)
                
                all_results.append({
                    "params": params,
                    "score": score
                })
                
                if score > best_score:
                    best_score = score
                    best_params = params
                    best_performance = result.performance
        
        return OptimizationResult(
            success=True,
            strategy_id=strategy.id,
            best_params=best_params,
            best_score=best_score,
            best_performance=best_performance,
            all_results=all_results,
            iterations=n_iterations
        )
    
    def _genetic_optimize(
        self,
        strategy: StrategyMetadata,
        param_ranges: List[ParameterRange],
        price_data: pd.DataFrame,
        factor_data: Dict[str, pd.DataFrame],
        target: OptimizationTarget,
        n_iterations: int
    ) -> OptimizationResult:
        """遗传算法优化"""
        optimizer = GeneticOptimizer(
            param_ranges,
            n_generations=max(n_iterations // 10, 5),
            population_size=20
        )
        
        optimizer.initialize_population()
        
        all_results = []
        best_score = float('-inf')
        best_params = {}
        best_performance = None
        
        for gen in range(optimizer.n_generations):
            fitness_scores = []
            
            for individual in optimizer.population:
                modified_strategy = self._apply_params(strategy, individual)
                
                result = self._backtester.backtest(
                    modified_strategy,
                    price_data,
                    factor_data
                )
                
                if result.success:
                    score = self._get_target_score(result, target)
                    fitness_scores.append(score)
                    
                    all_results.append({
                        "params": individual,
                        "score": score,
                        "generation": gen
                    })
                    
                    if score > best_score:
                        best_score = score
                        best_params = individual
                        best_performance = result.performance
                else:
                    fitness_scores.append(0)
            
            new_population = []
            
            sorted_indices = np.argsort(fitness_scores)[::-1]
            elite_count = max(2, len(optimizer.population) // 5)
            
            for idx in sorted_indices[:elite_count]:
                new_population.append(optimizer.population[idx])
            
            while len(new_population) < optimizer.population_size:
                parent1_idx = optimizer.select(fitness_scores)
                parent2_idx = optimizer.select(fitness_scores)
                
                parent1 = optimizer.population[parent1_idx]
                parent2 = optimizer.population[parent2_idx]
                
                if random.random() < optimizer.crossover_rate:
                    child1, child2 = optimizer.crossover(parent1, parent2)
                else:
                    child1, child2 = parent1.copy(), parent2.copy()
                
                child1 = optimizer.mutate(child1)
                child2 = optimizer.mutate(child2)
                
                new_population.extend([child1, child2])
            
            optimizer.population = new_population[:optimizer.population_size]
        
        return OptimizationResult(
            success=True,
            strategy_id=strategy.id,
            best_params=best_params,
            best_score=best_score,
            best_performance=best_performance,
            all_results=all_results,
            iterations=optimizer.n_generations * optimizer.population_size
        )
    
    def _apply_params(
        self,
        strategy: StrategyMetadata,
        params: Dict[str, Any]
    ) -> StrategyMetadata:
        """应用参数到策略"""
        modified = StrategyMetadata(
            id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            strategy_type=strategy.strategy_type,
            signals=SignalConfig(
                signal_ids=strategy.signals.signal_ids.copy(),
                weights=strategy.signals.weights.copy(),
                combination_method=strategy.signals.combination_method
            ),
            rebalance_freq=strategy.rebalance_freq,
            max_positions=strategy.max_positions,
            risk_params=RiskParams(**strategy.risk_params.to_dict()),
            tags=strategy.tags.copy(),
            parameters=strategy.parameters.copy()
        )
        
        for key, value in params.items():
            if key == 'max_positions':
                modified.max_positions = value
            elif key == 'max_single_weight':
                modified.risk_params.max_single_weight = value
            elif key == 'max_industry_weight':
                modified.risk_params.max_industry_weight = value
            elif key == 'stop_loss':
                modified.risk_params.stop_loss = value
            elif key == 'take_profit':
                modified.risk_params.take_profit = value
            elif key.startswith('signal_weight_'):
                idx = int(key.split('_')[-1])
                if idx < len(modified.signals.weights):
                    modified.signals.weights[idx] = value
            else:
                modified.parameters[key] = value
        
        return modified
    
    def _get_target_score(
        self, 
        result: BacktestResult, 
        target: OptimizationTarget
    ) -> float:
        """获取优化目标得分"""
        if result.performance is None:
            return float('-inf')
        
        if target == OptimizationTarget.SHARPE_RATIO:
            return result.performance.sharpe_ratio
        elif target == OptimizationTarget.TOTAL_RETURN:
            return result.performance.annual_return
        elif target == OptimizationTarget.MAX_DRAWDOWN:
            return -result.performance.max_drawdown
        elif target == OptimizationTarget.WIN_RATE:
            return result.performance.win_rate
        
        return result.performance.sharpe_ratio
    
    def apply_optimized_params(
        self,
        strategy_id: str,
        params: Dict[str, Any]
    ) -> Optional[StrategyMetadata]:
        """应用优化后的参数"""
        return self._registry.update(strategy_id, parameters=params)


_default_optimizer: Optional[StrategyOptimizer] = None


def get_strategy_optimizer() -> StrategyOptimizer:
    """获取全局策略优化器实例"""
    global _default_optimizer
    if _default_optimizer is None:
        _default_optimizer = StrategyOptimizer()
    return _default_optimizer


def reset_strategy_optimizer():
    """重置全局策略优化器"""
    global _default_optimizer
    _default_optimizer = None
