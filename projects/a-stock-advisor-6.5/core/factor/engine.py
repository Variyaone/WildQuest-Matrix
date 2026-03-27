"""
因子计算引擎模块

高效计算因子值，支持公式表达式解析、插件式因子扩展、批量并行计算和增量更新。
"""

import re
import ast
import operator
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import functools

import pandas as pd
import numpy as np

from .registry import FactorMetadata, get_factor_registry
from ..infrastructure.exceptions import FactorException


@dataclass
class FactorComputeResult:
    """因子计算结果"""
    success: bool
    factor_id: str
    data: Optional[pd.DataFrame] = None
    error_message: Optional[str] = None
    compute_time: float = 0.0
    stock_count: int = 0
    date_count: int = 0


class OperatorRegistry:
    """
    算子注册表
    
    管理所有可用的计算算子。
    """
    
    def __init__(self):
        """初始化算子注册表"""
        self._operators: Dict[str, Callable] = {}
        self._register_builtin_operators()
    
    def _register_builtin_operators(self):
        """注册内置算子"""
        self.register("ts_mean", lambda x, window: x.rolling(window=window).mean())
        self.register("ts_std", lambda x, window: x.rolling(window=window).std())
        self.register("ts_sum", lambda x, window: x.rolling(window=window).sum())
        self.register("ts_max", lambda x, window: x.rolling(window=window).max())
        self.register("ts_min", lambda x, window: x.rolling(window=window).min())
        self.register("ts_rank", lambda x, window: x.rolling(window=window).rank(pct=True))
        self.register("ts_delta", lambda x, window: x.diff(window))
        self.register("ts_pct_change", lambda x, window: x.pct_change(window))
        self.register("ts_corr", lambda x, y, window: x.rolling(window=window).corr(y))
        self.register("ts_cov", lambda x, y, window: x.rolling(window=window).cov(y))
        
        self.register("cs_rank", lambda x: x.rank(pct=True))
        self.register("cs_zscore", lambda x: (x - x.mean()) / x.std())
        self.register("cs_demean", lambda x: x - x.mean())
        self.register("cs_scale", lambda x: x / x.abs().sum())
        
        self.register("delay", lambda x, window: x.shift(window))
        self.register("abs", np.abs)
        self.register("log", np.log)
        self.register("log1p", np.log1p)
        self.register("sqrt", np.sqrt)
        self.register("square", np.square)
        self.register("sign", np.sign)
        
        self.register("max", np.maximum)
        self.register("min", np.minimum)
        self.register("sum", np.nansum)
        self.register("mean", np.nanmean)
        self.register("std", np.nanstd)
        
    def register(self, name: str, func: Callable):
        """
        注册算子
        
        Args:
            name: 算子名称
            func: 算子函数
        """
        self._operators[name] = func
    
    def get(self, name: str) -> Optional[Callable]:
        """获取算子"""
        return self._operators.get(name)
    
    def list_operators(self) -> List[str]:
        """列出所有算子"""
        return list(self._operators.keys())


class FormulaParser:
    """
    公式解析器
    
    解析因子公式表达式，支持变量、算子和数学运算。
    """
    
    def __init__(self, operator_registry: OperatorRegistry):
        """
        初始化公式解析器
        
        Args:
            operator_registry: 算子注册表
        """
        self.operators = operator_registry
        self._cache: Dict[str, Any] = {}
    
    def parse(self, formula: str) -> ast.AST:
        """
        解析公式
        
        Args:
            formula: 公式字符串
            
        Returns:
            AST: 抽象语法树
        """
        if formula in self._cache:
            return self._cache[formula]
        
        try:
            tree = ast.parse(formula, mode='eval')
            self._cache[formula] = tree
            return tree
        except SyntaxError as e:
            raise FactorException(f"公式语法错误: {formula}", details={"error": str(e)})
    
    def extract_variables(self, formula: str) -> List[str]:
        """
        提取公式中的变量名
        
        Args:
            formula: 公式字符串
            
        Returns:
            List[str]: 变量名列表
        """
        tree = self.parse(formula)
        variables = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if not self.operators.get(node.id):
                    variables.add(node.id)
        
        return sorted(list(variables))
    
    def validate_formula(self, formula: str) -> bool:
        """
        验证公式有效性
        
        Args:
            formula: 公式字符串
            
        Returns:
            bool: 是否有效
        """
        try:
            self.parse(formula)
            return True
        except Exception:
            return False


class FactorComputeContext:
    """
    因子计算上下文
    
    管理计算过程中的数据和变量。
    """
    
    def __init__(self, data: Dict[str, pd.DataFrame]):
        """
        初始化计算上下文
        
        Args:
            data: 数据字典，键为数据名，值为DataFrame
        """
        self._data = data
        self._cache: Dict[str, Any] = {}
    
    def get(self, name: str) -> Optional[pd.DataFrame]:
        """获取数据"""
        if name in self._cache:
            return self._cache[name]
        return self._data.get(name)
    
    def set(self, name: str, value: Any):
        """设置数据"""
        self._cache[name] = value
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


class FactorEngine:
    """
    因子计算引擎
    
    支持公式表达式解析、插件式因子扩展、批量并行计算和增量更新。
    """
    
    def __init__(
        self, 
        n_workers: int = 4,
        use_multiprocessing: bool = False
    ):
        """
        初始化因子计算引擎
        
        Args:
            n_workers: 工作进程/线程数
            use_multiprocessing: 是否使用多进程
        """
        self.n_workers = n_workers
        self.use_multiprocessing = use_multiprocessing
        self.operator_registry = OperatorRegistry()
        self.formula_parser = FormulaParser(self.operator_registry)
        self._registry = get_factor_registry()
        self._custom_factors: Dict[str, Callable] = {}
    
    def register_custom_factor(self, factor_id: str, compute_func: Callable):
        """
        注册自定义因子计算函数
        
        Args:
            factor_id: 因子ID
            compute_func: 计算函数
        """
        self._custom_factors[factor_id] = compute_func
    
    def register_operator(self, name: str, func: Callable):
        """
        注册自定义算子
        
        Args:
            name: 算子名称
            func: 算子函数
        """
        self.operator_registry.register(name, func)
    
    def compute_single(
        self,
        factor: Union[str, FactorMetadata],
        data: Dict[str, pd.DataFrame],
        **kwargs
    ) -> FactorComputeResult:
        """
        计算单个因子
        
        Args:
            factor: 因子ID或因子元数据
            data: 计算所需的数据字典
            **kwargs: 额外参数
            
        Returns:
            FactorComputeResult: 计算结果
        """
        start_time = datetime.now()
        
        if isinstance(factor, str):
            factor_meta = self._registry.get(factor)
            if factor_meta is None:
                return FactorComputeResult(
                    success=False,
                    factor_id=factor,
                    error_message=f"因子不存在: {factor}"
                )
        else:
            factor_meta = factor
        
        factor_id = factor_meta.id
        
        try:
            if factor_id in self._custom_factors:
                result_df = self._custom_factors[factor_id](data, **kwargs)
            else:
                result_df = self._compute_by_formula(factor_meta, data, **kwargs)
            
            compute_time = (datetime.now() - start_time).total_seconds()
            
            stock_count = 0
            date_count = 0
            if result_df is not None and len(result_df) > 0:
                if 'stock_code' in result_df.columns:
                    stock_count = result_df['stock_code'].nunique()
                if 'date' in result_df.columns:
                    date_count = result_df['date'].nunique()
            
            return FactorComputeResult(
                success=True,
                factor_id=factor_id,
                data=result_df,
                compute_time=compute_time,
                stock_count=stock_count,
                date_count=date_count
            )
            
        except Exception as e:
            return FactorComputeResult(
                success=False,
                factor_id=factor_id,
                error_message=str(e)
            )
    
    def _compute_by_formula(
        self,
        factor: FactorMetadata,
        data: Dict[str, pd.DataFrame],
        **kwargs
    ) -> pd.DataFrame:
        """
        通过公式计算因子
        
        Args:
            factor: 因子元数据
            data: 数据字典
            **kwargs: 额外参数
            
        Returns:
            pd.DataFrame: 因子值DataFrame
        """
        formula = factor.formula
        params = {**factor.parameters, **kwargs}
        
        variables = self.formula_parser.extract_variables(formula)
        
        missing_vars = [v for v in variables if v not in data]
        if missing_vars:
            raise FactorException(
                f"缺少必要数据: {missing_vars}",
                factor_id=factor.id
            )
        
        context = FactorComputeContext(data)
        
        result = self._evaluate_formula(formula, context, params)
        
        if isinstance(result, pd.Series):
            result = result.to_frame('factor_value')
        elif isinstance(result, np.ndarray):
            if 'date' in data and 'stock_code' in data:
                sample_df = list(data.values())[0]
                result = pd.DataFrame({
                    'date': sample_df['date'],
                    'stock_code': sample_df['stock_code'],
                    'factor_value': result
                })
        
        return result
    
    def _evaluate_formula(
        self,
        formula: str,
        context: FactorComputeContext,
        params: Dict[str, Any]
    ) -> Any:
        """
        评估公式表达式
        
        Args:
            formula: 公式字符串
            context: 计算上下文
            params: 参数字典
            
        Returns:
            Any: 计算结果
        """
        tree = self.formula_parser.parse(formula)
        return self._eval_node(tree.body, context, params)
    
    def _eval_node(self, node: ast.AST, context: FactorComputeContext, params: Dict[str, Any]) -> Any:
        """递归评估AST节点"""
        if isinstance(node, ast.Constant):
            return node.value
        
        elif isinstance(node, ast.Num):
            return node.n
        
        elif isinstance(node, ast.Str):
            return node.s
        
        elif isinstance(node, ast.Name):
            name = node.id
            
            if name in params:
                return params[name]
            
            op_func = self.operator_registry.get(name)
            if op_func:
                return op_func
            
            return context.get(name)
        
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, context, params)
            right = self._eval_node(node.right, context, params)
            
            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.FloorDiv: operator.floordiv,
                ast.Mod: operator.mod,
                ast.Pow: operator.pow,
            }
            
            op_func = ops.get(type(node.op))
            if op_func:
                return op_func(left, right)
            raise FactorException(f"不支持的二元运算: {type(node.op)}")
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, context, params)
            
            if isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.Not):
                return not operand
            
            raise FactorException(f"不支持的一元运算: {type(node.op)}")
        
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context, params)
            
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context, params)
                
                ops = {
                    ast.Eq: operator.eq,
                    ast.NotEq: operator.ne,
                    ast.Lt: operator.lt,
                    ast.LtE: operator.le,
                    ast.Gt: operator.gt,
                    ast.GtE: operator.ge,
                }
                
                op_func = ops.get(type(op))
                if op_func:
                    if not op_func(left, right):
                        return False
                left = right
            
            return True
        
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            
            if func_name is None:
                raise FactorException(f"不支持的函数调用")
            
            func = self.operator_registry.get(func_name)
            if func is None:
                raise FactorException(f"未知算子: {func_name}")
            
            args = [self._eval_node(arg, context, params) for arg in node.args]
            kwargs = {
                kw.arg: self._eval_node(kw.value, context, params)
                for kw in node.keywords
            }
            
            return func(*args, **kwargs)
        
        elif isinstance(node, ast.Subscript):
            value = self._eval_node(node.value, context, params)
            slice_val = self._eval_node(node.slice, context, params)
            return value[slice_val]
        
        elif isinstance(node, ast.Attribute):
            value = self._eval_node(node.value, context, params)
            return getattr(value, node.attr)
        
        elif isinstance(node, ast.Index):
            return self._eval_node(node.value, context, params)
        
        else:
            raise FactorException(f"不支持的AST节点类型: {type(node)}")
    
    def compute_batch(
        self,
        factor_ids: List[str],
        data: Dict[str, pd.DataFrame],
        parallel: bool = True
    ) -> Dict[str, FactorComputeResult]:
        """
        批量计算因子
        
        Args:
            factor_ids: 因子ID列表
            data: 数据字典
            parallel: 是否并行计算
            
        Returns:
            Dict[str, FactorComputeResult]: 计算结果字典
        """
        results = {}
        
        if parallel and len(factor_ids) > 1:
            executor_class = ProcessPoolExecutor if self.use_multiprocessing else ThreadPoolExecutor
            
            with executor_class(max_workers=self.n_workers) as executor:
                futures = {
                    executor.submit(self.compute_single, fid, data): fid
                    for fid in factor_ids
                }
                
                for future in futures:
                    fid = futures[future]
                    try:
                        results[fid] = future.result()
                    except Exception as e:
                        results[fid] = FactorComputeResult(
                            success=False,
                            factor_id=fid,
                            error_message=str(e)
                        )
        else:
            for fid in factor_ids:
                results[fid] = self.compute_single(fid, data)
        
        return results
    
    def compute_incremental(
        self,
        factor_id: str,
        data: Dict[str, pd.DataFrame],
        previous_data: Optional[pd.DataFrame] = None,
        lookback: int = 252
    ) -> FactorComputeResult:
        """
        增量计算因子
        
        Args:
            factor_id: 因子ID
            data: 新数据
            previous_data: 历史因子数据
            lookback: 回看天数
            
        Returns:
            FactorComputeResult: 计算结果
        """
        factor_meta = self._registry.get(factor_id)
        if factor_meta is None:
            return FactorComputeResult(
                success=False,
                factor_id=factor_id,
                error_message=f"因子不存在: {factor_id}"
            )
        
        result = self.compute_single(factor_meta, data)
        
        if result.success and previous_data is not None and result.data is not None:
            combined = pd.concat([previous_data, result.data], ignore_index=True)
            
            if 'date' in combined.columns:
                combined['date'] = pd.to_datetime(combined['date'])
                combined = combined.sort_values('date')
                
                unique_dates = combined['date'].unique()
                if len(unique_dates) > lookback:
                    cutoff_date = unique_dates[-lookback]
                    combined = combined[combined['date'] >= cutoff_date]
            
            result.data = combined
        
        return result
    
    def get_required_data(self, factor_id: str) -> List[str]:
        """
        获取因子计算所需的数据字段
        
        Args:
            factor_id: 因子ID
            
        Returns:
            List[str]: 数据字段列表
        """
        factor = self._registry.get(factor_id)
        if factor is None:
            return []
        
        return self.formula_parser.extract_variables(factor.formula)
    
    def validate_factor_data(self, factor_id: str, data: Dict[str, pd.DataFrame]) -> bool:
        """
        验证数据是否满足因子计算需求
        
        Args:
            factor_id: 因子ID
            data: 数据字典
            
        Returns:
            bool: 是否满足
        """
        required = self.get_required_data(factor_id)
        return all(field in data for field in required)


_default_engine: Optional[FactorEngine] = None


def get_factor_engine(n_workers: int = 4, use_multiprocessing: bool = False) -> FactorEngine:
    """获取全局因子计算引擎实例"""
    global _default_engine
    if _default_engine is None:
        _default_engine = FactorEngine(n_workers, use_multiprocessing)
    return _default_engine


def reset_factor_engine():
    """重置全局因子计算引擎"""
    global _default_engine
    _default_engine = None
