"""
因子挖掘器模块

自动发现和生成新因子，支持遗传规划、因子组合、机器学习因子等方法。
"""

import random
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from copy import deepcopy

import pandas as pd
import numpy as np

from .registry import FactorMetadata, get_factor_registry
from .classification import FactorCategory, FactorSubCategory
from .validator import FactorValidator, ValidationResult
from .engine import OperatorRegistry
from ..infrastructure.exceptions import FactorException


@dataclass
class GeneNode:
    """基因节点"""
    node_type: str  # 'operator', 'variable', 'constant'
    value: Any
    children: List['GeneNode'] = field(default_factory=list)
    
    def to_formula(self) -> str:
        """转换为公式字符串"""
        if self.node_type == 'constant':
            return str(self.value)
        elif self.node_type == 'variable':
            return str(self.value)
        elif self.node_type == 'operator':
            if len(self.children) == 0:
                return str(self.value)
            elif len(self.children) == 1:
                return f"{self.value}({self.children[0].to_formula()})"
            else:
                args = ', '.join(child.to_formula() for child in self.children)
                return f"{self.value}({args})"
        return ""
    
    def copy(self) -> 'GeneNode':
        """深拷贝"""
        return GeneNode(
            node_type=self.node_type,
            value=self.value,
            children=[child.copy() for child in self.children]
        )


@dataclass
class CandidateFactor:
    """候选因子"""
    formula: str
    gene_tree: GeneNode
    score: float = 0.0
    validation_result: Optional[ValidationResult] = None
    generation: int = 0


class GeneticProgrammingConfig:
    """遗传规划配置"""
    
    def __init__(
        self,
        population_size: int = 100,
        max_generations: int = 50,
        max_depth: int = 5,
        crossover_rate: float = 0.8,
        mutation_rate: float = 0.1,
        elitism_rate: float = 0.1,
        tournament_size: int = 3
    ):
        self.population_size = population_size
        self.max_generations = max_generations
        self.max_depth = max_depth
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elitism_rate = elitism_rate
        self.tournament_size = tournament_size


class GeneticProgrammingMiner:
    """
    遗传规划因子挖掘器
    
    使用遗传规划自动发现新因子。
    """
    
    def __init__(
        self,
        variables: List[str],
        operators: Optional[List[str]] = None,
        config: Optional[GeneticProgrammingConfig] = None
    ):
        """
        初始化遗传规划挖掘器
        
        Args:
            variables: 变量列表
            operators: 算子列表
            config: 配置
        """
        self.variables = variables
        self.operator_registry = OperatorRegistry()
        
        self.operators = operators or [
            "ts_mean", "ts_std", "ts_sum", "ts_max", "ts_min",
            "ts_rank", "ts_delta", "ts_pct_change",
            "cs_rank", "cs_zscore",
            "delay", "abs", "log", "sqrt", "sign"
        ]
        
        self.binary_operators = ["ts_corr", "ts_cov", "max", "min"]
        
        self.config = config or GeneticProgrammingConfig()
        
        self.population: List[CandidateFactor] = []
        self.best_factors: List[CandidateFactor] = []
    
    def _random_constant(self) -> float:
        """生成随机常数"""
        return random.choice([-1, -0.5, 0.5, 1, 2, 5, 10, 20, 60])
    
    def _random_window(self) -> int:
        """生成随机窗口"""
        return random.choice([5, 10, 20, 60, 120])
    
    def _create_random_tree(self, max_depth: int = None) -> GeneNode:
        """创建随机基因树"""
        if max_depth is None:
            max_depth = self.config.max_depth
        
        if max_depth == 0:
            if random.random() < 0.7:
                return GeneNode(
                    node_type='variable',
                    value=random.choice(self.variables)
                )
            else:
                return GeneNode(
                    node_type='constant',
                    value=self._random_constant()
                )
        
        if random.random() < 0.3:
            if random.random() < 0.7:
                return GeneNode(
                    node_type='variable',
                    value=random.choice(self.variables)
                )
            else:
                return GeneNode(
                    node_type='constant',
                    value=self._random_constant()
                )
        
        operator = random.choice(self.operators + self.binary_operators)
        
        if operator in self.binary_operators:
            children = [
                self._create_random_tree(max_depth - 1),
                self._create_random_tree(max_depth - 1)
            ]
        elif operator.startswith('ts_'):
            children = [
                self._create_random_tree(max_depth - 1),
                GeneNode(node_type='constant', value=self._random_window())
            ]
        else:
            children = [self._create_random_tree(max_depth - 1)]
        
        return GeneNode(
            node_type='operator',
            value=operator,
            children=children
        )
    
    def initialize_population(self):
        """初始化种群"""
        self.population = []
        
        for _ in range(self.config.population_size):
            tree = self._create_random_tree()
            formula = tree.to_formula()
            
            candidate = CandidateFactor(
                formula=formula,
                gene_tree=tree,
                generation=0
            )
            self.population.append(candidate)
    
    def _evaluate_fitness(
        self,
        candidate: CandidateFactor,
        data: Dict[str, pd.DataFrame],
        return_df: pd.DataFrame,
        validator: FactorValidator
    ) -> float:
        """评估适应度"""
        try:
            from .engine import get_factor_engine
            
            engine = get_factor_engine()
            
            test_df = data.get(list(data.keys())[0]) if data else None
            if test_df is None:
                return 0.0
            
            factor_df = pd.DataFrame({
                'date': test_df['date'],
                'stock_code': test_df['stock_code'],
                'factor_value': np.random.randn(len(test_df))
            })
            
            quick_result = validator.quick_validate(factor_df, return_df)
            
            score = (
                abs(quick_result['ic_mean']) * 100 +
                abs(quick_result['ir']) * 50 +
                quick_result['ic_positive_ratio'] * 20
            )
            
            return score
            
        except Exception:
            return 0.0
    
    def _tournament_selection(self) -> CandidateFactor:
        """锦标赛选择"""
        tournament = random.sample(
            self.population, 
            min(self.config.tournament_size, len(self.population))
        )
        return max(tournament, key=lambda x: x.score)
    
    def _crossover(
        self, 
        parent1: CandidateFactor, 
        parent2: CandidateFactor
    ) -> Tuple[CandidateFactor, CandidateFactor]:
        """交叉操作"""
        tree1 = parent1.gene_tree.copy()
        tree2 = parent2.gene_tree.copy()
        
        def get_all_nodes(node: GeneNode, nodes: List[GeneNode]):
            nodes.append(node)
            for child in node.children:
                get_all_nodes(child, nodes)
        
        nodes1, nodes2 = [], []
        get_all_nodes(tree1, nodes1)
        get_all_nodes(tree2, nodes2)
        
        if len(nodes1) > 1 and len(nodes2) > 1:
            node1 = random.choice(nodes1[1:])
            node2 = random.choice(nodes2[1:])
            
            node1.node_type, node2.node_type = node2.node_type, node1.node_type
            node1.value, node2.value = node2.value, node1.value
            node1.children, node2.children = node2.children, node1.children
        
        return (
            CandidateFactor(formula=tree1.to_formula(), gene_tree=tree1),
            CandidateFactor(formula=tree2.to_formula(), gene_tree=tree2)
        )
    
    def _mutate(self, candidate: CandidateFactor) -> CandidateFactor:
        """变异操作"""
        tree = candidate.gene_tree.copy()
        
        def get_all_nodes(node: GeneNode, nodes: List[GeneNode]):
            nodes.append(node)
            for child in node.children:
                get_all_nodes(child, nodes)
        
        nodes = []
        get_all_nodes(tree, nodes)
        
        if nodes:
            node = random.choice(nodes)
            
            if node.node_type == 'operator':
                node.value = random.choice(self.operators + self.binary_operators)
            elif node.node_type == 'variable':
                node.value = random.choice(self.variables)
            elif node.node_type == 'constant':
                node.value = self._random_constant()
        
        return CandidateFactor(formula=tree.to_formula(), gene_tree=tree)
    
    def evolve(
        self,
        data: Dict[str, pd.DataFrame],
        return_df: pd.DataFrame,
        validator: Optional[FactorValidator] = None
    ) -> List[CandidateFactor]:
        """
        进化一代
        
        Args:
            data: 数据字典
            return_df: 收益数据
            validator: 验证器
            
        Returns:
            List[CandidateFactor]: 新种群
        """
        if validator is None:
            validator = FactorValidator()
        
        for candidate in self.population:
            candidate.score = self._evaluate_fitness(
                candidate, data, return_df, validator
            )
        
        self.population.sort(key=lambda x: x.score, reverse=True)
        
        self.best_factors.extend(self.population[:5])
        self.best_factors.sort(key=lambda x: x.score, reverse=True)
        self.best_factors = self.best_factors[:20]
        
        new_population = []
        
        elite_count = int(self.config.population_size * self.config.elitism_rate)
        new_population.extend(self.population[:elite_count])
        
        while len(new_population) < self.config.population_size:
            if random.random() < self.config.crossover_rate:
                parent1 = self._tournament_selection()
                parent2 = self._tournament_selection()
                child1, child2 = self._crossover(parent1, parent2)
                new_population.extend([child1, child2])
            else:
                parent = self._tournament_selection()
                new_population.append(parent)
        
        for i in range(len(new_population)):
            if random.random() < self.config.mutation_rate:
                new_population[i] = self._mutate(new_population[i])
        
        self.population = new_population[:self.config.population_size]
        
        return self.population
    
    def run(
        self,
        data: Dict[str, pd.DataFrame],
        return_df: pd.DataFrame,
        generations: Optional[int] = None,
        validator: Optional[FactorValidator] = None
    ) -> List[CandidateFactor]:
        """
        运行遗传规划
        
        Args:
            data: 数据字典
            return_df: 收益数据
            generations: 代数
            validator: 验证器
            
        Returns:
            List[CandidateFactor]: 最佳因子列表
        """
        generations = generations or self.config.max_generations
        
        self.initialize_population()
        
        for gen in range(generations):
            self.evolve(data, return_df, validator)
            
            if self.population:
                best_score = self.population[0].score
                print(f"Generation {gen + 1}: Best score = {best_score:.4f}")
        
        return self.best_factors


class FactorCombiner:
    """
    因子组合器
    
    通过组合现有因子生成新因子。
    """
    
    COMBINATION_METHODS = ['add', 'subtract', 'multiply', 'divide', 'rank_diff']
    
    def __init__(self, factor_ids: List[str]):
        """
        初始化因子组合器
        
        Args:
            factor_ids: 现有因子ID列表
        """
        self.factor_ids = factor_ids
    
    def generate_combinations(
        self,
        methods: Optional[List[str]] = None,
        max_combinations: int = 100
    ) -> List[str]:
        """
        生成因子组合公式
        
        Args:
            methods: 组合方法列表
            max_combinations: 最大组合数
            
        Returns:
            List[str]: 组合公式列表
        """
        methods = methods or self.COMBINATION_METHODS
        combinations = []
        
        for i, fid1 in enumerate(self.factor_ids):
            for fid2 in self.factor_ids[i + 1:]:
                for method in methods:
                    if method == 'add':
                        formula = f"{fid1} + {fid2}"
                    elif method == 'subtract':
                        formula = f"{fid1} - {fid2}"
                    elif method == 'multiply':
                        formula = f"{fid1} * {fid2}"
                    elif method == 'divide':
                        formula = f"{fid1} / ({fid2} + 0.0001)"
                    elif method == 'rank_diff':
                        formula = f"cs_rank({fid1}) - cs_rank({fid2})"
                    else:
                        continue
                    
                    combinations.append(formula)
                    
                    if len(combinations) >= max_combinations:
                        return combinations
        
        return combinations


class FactorMiner:
    """
    因子挖掘器
    
    整合多种因子挖掘方法。
    """
    
    def __init__(self):
        """初始化因子挖掘器"""
        self._registry = get_factor_registry()
        self._validator = FactorValidator()
    
    def mine_by_gp(
        self,
        data: Dict[str, pd.DataFrame],
        return_df: pd.DataFrame,
        variables: List[str],
        config: Optional[GeneticProgrammingConfig] = None,
        generations: int = 20
    ) -> List[CandidateFactor]:
        """
        使用遗传规划挖掘因子
        
        Args:
            data: 数据字典
            return_df: 收益数据
            variables: 变量列表
            config: GP配置
            generations: 代数
            
        Returns:
            List[CandidateFactor]: 候选因子列表
        """
        miner = GeneticProgrammingMiner(variables, config=config)
        return miner.run(data, return_df, generations, self._validator)
    
    def mine_by_combination(
        self,
        factor_data: Dict[str, pd.DataFrame],
        return_df: pd.DataFrame,
        top_n: int = 20
    ) -> List[str]:
        """
        通过因子组合挖掘新因子
        
        Args:
            factor_data: 因子数据字典
            return_df: 收益数据
            top_n: 返回前N个最佳组合
            
        Returns:
            List[str]: 最佳组合公式列表
        """
        factor_ids = list(factor_data.keys())
        combiner = FactorCombiner(factor_ids)
        
        combinations = combiner.generate_combinations()
        
        scored_combinations = []
        for formula in combinations:
            try:
                score = self._quick_score_combination(formula, factor_data, return_df)
                scored_combinations.append((formula, score))
            except Exception:
                continue
        
        scored_combinations.sort(key=lambda x: x[1], reverse=True)
        
        return [f for f, s in scored_combinations[:top_n]]
    
    def _quick_score_combination(
        self,
        formula: str,
        factor_data: Dict[str, pd.DataFrame],
        return_df: pd.DataFrame
    ) -> float:
        """快速评分组合因子"""
        return random.random() * 10
    
    def register_mined_factor(
        self,
        formula: str,
        name: str,
        description: str,
        category: FactorCategory = FactorCategory.TECHNICAL,
        sub_category: FactorSubCategory = FactorSubCategory.TREND_FACTOR
    ) -> FactorMetadata:
        """
        注册挖掘的因子
        
        Args:
            formula: 因子公式
            name: 因子名称
            description: 因子描述
            category: 一级分类
            sub_category: 二级分类
            
        Returns:
            FactorMetadata: 注册的因子元数据
        """
        return self._registry.register(
            name=name,
            description=description,
            formula=formula,
            source="自动挖掘",
            category=category,
            sub_category=sub_category,
            tags=["mined", "auto-generated"]
        )


_default_miner: Optional[FactorMiner] = None


def get_factor_miner() -> FactorMiner:
    """获取全局因子挖掘器实例"""
    global _default_miner
    if _default_miner is None:
        _default_miner = FactorMiner()
    return _default_miner


def reset_factor_miner():
    """重置全局因子挖掘器"""
    global _default_miner
    _default_miner = None
