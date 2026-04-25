"""
Alpha生成模块（改进版）

基于因子组合生成Alpha预测值。
支持实时因子计算、缓存机制和批量处理。
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from collections import defaultdict

from .factor_combiner import FactorCombinationConfig, FactorCombiner, get_factor_combiner
from ..factor import get_factor_storage, get_factor_engine, get_factor_registry
from ..data import get_data_fetcher
from ..infrastructure.logging import get_logger

logger = get_logger("strategy.alpha_generator")


@dataclass
class AlphaGenerationResult:
    """Alpha生成结果"""
    success: bool
    date: str
    
    alpha_values: Dict[str, float] = field(default_factory=dict)
    ranked_stocks: List[str] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    
    factor_ids: List[str] = field(default_factory=list)
    factor_weights: List[float] = field(default_factory=list)
    
    total_stocks: int = 0
    valid_stocks: int = 0
    
    computation_mode: str = "unknown"
    cache_hit: bool = False
    compute_time: float = 0.0
    
    error_message: Optional[str] = None


class FactorValueCache:
    """因子值缓存"""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Dict[str, pd.DataFrame]] = defaultdict(dict)
        self._max_size = max_size
        self._access_count: Dict[str, int] = defaultdict(int)
    
    def get(self, factor_id: str, date: str) -> Optional[pd.DataFrame]:
        """获取缓存的因子值"""
        cache_key = f"{factor_id}_{date}"
        self._access_count[cache_key] += 1
        
        if factor_id in self._cache and date in self._cache[factor_id]:
            return self._cache[factor_id][date].copy()
        return None
    
    def set(self, factor_id: str, date: str, data: pd.DataFrame):
        """设置缓存"""
        if len(self._cache) >= self._max_size:
            self._evict_lru()
        
        if factor_id not in self._cache:
            self._cache[factor_id] = {}
        
        self._cache[factor_id][date] = data.copy()
    
    def _evict_lru(self):
        """清理最少使用的缓存"""
        if not self._access_count:
            return
        
        lru_key = min(self._access_count.items(), key=lambda x: x[1])[0]
        factor_id, date = lru_key.rsplit('_', 1)
        
        if factor_id in self._cache and date in self._cache[factor_id]:
            del self._cache[factor_id][date]
            if not self._cache[factor_id]:
                del self._cache[factor_id]
        
        del self._access_count[lru_key]
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._access_count.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_entries = sum(len(dates) for dates in self._cache.values())
        return {
            "total_factors": len(self._cache),
            "total_entries": total_entries,
            "max_size": self._max_size
        }


class AlphaGenerator:
    """
    Alpha生成器（改进版）
    
    基于因子组合生成Alpha预测值。
    支持实时因子计算、缓存机制和批量处理。
    """
    
    def __init__(
        self,
        enable_cache: bool = True,
        cache_size: int = 1000,
        prefer_realtime: bool = True
    ):
        """
        初始化Alpha生成器
        
        Args:
            enable_cache: 是否启用缓存
            cache_size: 缓存大小
            prefer_realtime: 是否优先使用实时计算
        """
        self._factor_combiner = get_factor_combiner()
        self._factor_storage = get_factor_storage()
        self._factor_engine = get_factor_engine()
        self._factor_registry = get_factor_registry()
        self._data_fetcher = get_data_fetcher()
        
        self._enable_cache = enable_cache
        self._prefer_realtime = prefer_realtime
        
        if enable_cache:
            self._cache = FactorValueCache(max_size=cache_size)
        else:
            self._cache = None
    
    def generate(
        self,
        config: FactorCombinationConfig,
        date: str,
        stock_codes: Optional[List[str]] = None,
        factor_data: Optional[Dict[str, pd.DataFrame]] = None,
        stock_data: Optional[Dict[str, pd.DataFrame]] = None,
        precomputed_factors: Optional[Dict[str, Any]] = None,
        factor_data_by_date: Optional[Dict[str, Dict[str, pd.DataFrame]]] = None
    ) -> AlphaGenerationResult:
        """
        生成Alpha
        
        Args:
            config: 因子组合配置
            date: 日期
            stock_codes: 股票代码列表（可选）
            factor_data: 因子数据（可选，如果不提供则自动获取）
            stock_data: 股票市场数据（可选，用于实时计算）
            precomputed_factors: 预先计算好的因子组合结果（可选）
                包含: factor_ids, weights, method
            factor_data_by_date: 预按日期分组的因子数据（可选，用于性能优化）
                格式: {date: {factor_id: DataFrame}}
                
        Returns:
            Alpha生成结果
        """
        start_time = datetime.now()
        
        try:
            if precomputed_factors:
                factor_ids = precomputed_factors.get('factor_ids', [])
                weights = precomputed_factors.get('weights', [])
                logger.info(f"使用预先计算的因子组合: {len(factor_ids)} 个因子")
            else:
                combination_result = self._factor_combiner.combine(config)
                
                if not combination_result.success:
                    return AlphaGenerationResult(
                        success=False,
                        date=date,
                        error_message=combination_result.error_message,
                        compute_time=(datetime.now() - start_time).total_seconds()
                    )
                
                factor_ids = combination_result.factor_ids
                weights = combination_result.weights
            
            if factor_data is None or len(factor_data) == 0:
                if factor_data_by_date and date in factor_data_by_date:
                    computation_mode = "preprocessed"
                    cache_hit = True
                else:
                    print("    [DEBUG] 调用 _get_factor_data")
                    factor_data, computation_mode, cache_hit = self._get_factor_data(
                        factor_ids=factor_ids,
                        date=date,
                        stock_codes=stock_codes,
                        stock_data=stock_data
                    )
            else:
                computation_mode = "provided"
                cache_hit = False
            
            has_factor_data = (factor_data and len(factor_data) > 0) or \
                              (factor_data_by_date and date in factor_data_by_date)
            
            if not has_factor_data:
                return AlphaGenerationResult(
                    success=False,
                    date=date,
                    error_message="没有可用的因子数据",
                    compute_time=(datetime.now() - start_time).total_seconds()
                )
            
            alpha_values = self._compute_alpha(
                factor_ids=factor_ids,
                weights=weights,
                factor_data=factor_data,
                date=date,
                factor_data_by_date=factor_data_by_date
            )
            
            if not alpha_values:
                return AlphaGenerationResult(
                    success=False,
                    date=date,
                    error_message="无法计算Alpha值",
                    compute_time=(datetime.now() - start_time).total_seconds()
                )
            
            sorted_stocks = sorted(
                alpha_values.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            ranked_stocks = [s[0] for s in sorted_stocks]
            scores = [s[1] for s in sorted_stocks]
            
            from ..infrastructure.quality_gate import get_quality_gate, GateStage
            
            quality_gate = get_quality_gate()
            
            quality_metrics = self._calculate_quality_metrics(factor_ids)
            
            validation_data = {
                'factor_ids': factor_ids,
                'avg_ic': quality_metrics.get('avg_ic', -999),
                'negative_ic_ratio': quality_metrics.get('negative_ic_ratio', 1.0),
                'ranked_stocks': ranked_stocks
            }
            
            gate_result = quality_gate.validate(GateStage.ALPHA_GENERATION, validation_data)
            
            if not gate_result.passed:
                error_messages = [r.message for r in gate_result.blocking_failures]
                logger.warning(f"Alpha生成质量验证失败:")
                for msg in error_messages:
                    logger.warning(f"  {msg}")
                
                logger.warning(f"Alpha已生成但存在质量问题，建议检查因子组合")
            
            compute_time = (datetime.now() - start_time).total_seconds()
            
            return AlphaGenerationResult(
                success=True,
                date=date,
                alpha_values=alpha_values,
                ranked_stocks=ranked_stocks,
                scores=scores,
                factor_ids=factor_ids,
                factor_weights=weights,
                total_stocks=len(alpha_values),
                valid_stocks=len(alpha_values),
                computation_mode=computation_mode,
                cache_hit=cache_hit,
                compute_time=compute_time
            )
            
        except Exception as e:
            logger.error(f"Alpha生成失败: {e}", exc_info=True)
            return AlphaGenerationResult(
                success=False,
                date=date,
                error_message=str(e),
                compute_time=(datetime.now() - start_time).total_seconds()
            )
    
    def _get_factor_data(
        self,
        factor_ids: List[str],
        date: str,
        stock_codes: Optional[List[str]] = None,
        stock_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Tuple[Dict[str, pd.DataFrame], str, bool]:
        """
        获取因子数据
        
        优先级：
        1. 缓存
        2. 预计算的因子值文件
        3. 实时计算
        
        Returns:
            Tuple[因子数据, 计算模式, 是否缓存命中]
        """
        factor_data = {}
        cache_hit = False
        computation_mode = "unknown"
        
        if not factor_ids:
            return {}, "no_factors", False
        
        if self._enable_cache:
            for factor_id in factor_ids:
                cached = self._cache.get(factor_id, date)
                if cached is not None:
                    factor_data[factor_id] = cached
                    cache_hit = True
            
            if len(factor_data) == len(factor_ids):
                return factor_data, "cache", True
        
        if not self._prefer_realtime:
            for factor_id in factor_ids:
                if factor_id in factor_data:
                    continue
                
                df = self._factor_storage.load_factor_data(factor_id)
                if df is not None and not df.empty:
                    factor_data[factor_id] = df
                    computation_mode = "storage"
        
        missing_factors = [fid for fid in factor_ids if fid not in factor_data]
        
        if missing_factors:
            if stock_data is None and stock_codes:
                if len(stock_codes) == 0:
                    return {}, "no_stocks", False
                
                stock_data = self._fetch_stock_data(stock_codes, date)
            
            if stock_data:
                realtime_data = self._compute_factors_realtime(
                    factor_ids=missing_factors,
                    stock_data=stock_data,
                    date=date
                )
                
                factor_data.update(realtime_data)
                computation_mode = "realtime"
        
        if self._enable_cache:
            for factor_id, df in factor_data.items():
                self._cache.set(factor_id, date, df)
        
        return factor_data, computation_mode, cache_hit
    
    def _fetch_stock_data(
        self,
        stock_codes: List[str],
        date: str,
        lookback_days: int = 252
    ) -> Dict[str, pd.DataFrame]:
        """
        获取股票市场数据
        
        自动过滤退市股票和无效数据
        """
        end_date = datetime.strptime(date, '%Y-%m-%d')
        start_date = end_date - timedelta(days=lookback_days)
        
        stock_data = {}
        skipped_count = 0
        
        try:
            from ..data.metadata import get_metadata_manager
            metadata_mgr = get_metadata_manager()
            delisted_stocks = {s.stock_code for s in metadata_mgr.get_delisted_stocks()}
        except Exception:
            delisted_stocks = set()
        
        for stock_code in stock_codes:
            if stock_code in delisted_stocks:
                logger.debug(f"跳过退市股票: {stock_code}")
                skipped_count += 1
                continue
            
            try:
                data = self._data_fetcher.get_history(
                    stock_code,
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d')
                )
                
                if data is not None and not data.empty:
                    stock_data[stock_code] = data
            except Exception as e:
                error_msg = str(e)
                if "delisted" in error_msg.lower() or "退市" in error_msg:
                    logger.info(f"检测到退市股票: {stock_code}")
                    skipped_count += 1
                else:
                    logger.warning(f"获取股票数据失败 {stock_code}: {e}")
        
        if skipped_count > 0:
            logger.info(f"已跳过 {skipped_count} 只退市/无效股票")
        
        return stock_data
    
    def _compute_factors_realtime(
        self,
        factor_ids: List[str],
        stock_data: Dict[str, pd.DataFrame],
        date: str
    ) -> Dict[str, pd.DataFrame]:
        """实时计算因子值"""
        factor_data = {}
        
        for factor_id in factor_ids:
            try:
                factor_meta = self._factor_registry.get(factor_id)
                if factor_meta is None:
                    logger.warning(f"因子不存在: {factor_id}")
                    continue
                
                factor_values_list = []
                
                for stock_code, df in stock_data.items():
                    try:
                        data_dict = self._prepare_data_for_engine(df)
                        
                        result = self._factor_engine.compute_single(
                            factor_id,
                            data_dict,
                            stock_code=stock_code,
                            date_series=df['date'] if 'date' in df.columns else None,
                            original_df=df
                        )
                        
                        if result.success and result.data is not None and len(result.data) > 0:
                            if 'factor_value' in result.data.columns:
                                latest_value = result.data['factor_value'].iloc[-1]
                            else:
                                latest_value = result.data.iloc[-1, 0]
                            
                            factor_values_list.append({
                                'date': date,
                                'stock_code': stock_code,
                                'value': latest_value
                            })
                    except Exception as e:
                        logger.debug(f"计算因子 {factor_id} 失败 {stock_code}: {e}")
                
                if factor_values_list:
                    factor_df = pd.DataFrame(factor_values_list)
                    factor_data[factor_id] = factor_df
                    logger.debug(f"实时计算因子 {factor_id}: {len(factor_df)} 只股票")
                
            except Exception as e:
                logger.error(f"实时计算因子 {factor_id} 失败: {e}")
        
        return factor_data
    
    def _prepare_data_for_engine(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """为因子引擎准备数据"""
        data_dict = {}
        
        required_cols = ['close', 'open', 'high', 'low', 'volume']
        for col in required_cols:
            if col in df.columns:
                data_dict[col] = df[col]
        
        optional_cols = ['amount', 'pct_change', 'turnover']
        for col in optional_cols:
            if col in df.columns:
                data_dict[col] = df[col]
        
        if 'amount' not in data_dict and 'volume' in data_dict:
            data_dict['amount'] = data_dict['volume']
        
        if 'pct_change' not in data_dict and 'close' in data_dict:
            data_dict['pct_change'] = data_dict['close'].pct_change()
        
        return data_dict
    
    def _calculate_quality_metrics(self, factor_ids: List[str]) -> Dict[str, float]:
        """计算因子组合质量指标"""
        if not factor_ids:
            return {'avg_ic': -999, 'negative_ic_ratio': 1.0}
        
        ics = []
        for factor_id in factor_ids:
            factor = self._factor_registry.get(factor_id)
            if factor and factor.quality_metrics:
                ics.append(factor.quality_metrics.ic_mean)
        
        if not ics:
            return {'avg_ic': -999, 'negative_ic_ratio': 1.0}
        
        avg_ic = np.mean(ics)
        negative_count = sum(1 for ic in ics if ic < 0)
        negative_ic_ratio = negative_count / len(ics) if ics else 1.0
        
        return {
            'avg_ic': avg_ic,
            'negative_ic_ratio': negative_ic_ratio
        }
    
    def _compute_alpha(
        self,
        factor_ids: List[str],
        weights: List[float],
        factor_data: Optional[Dict[str, pd.DataFrame]],
        date: str,
        factor_data_by_date: Optional[Dict[str, Dict[str, pd.DataFrame]]] = None
    ) -> Dict[str, float]:
        """计算Alpha值"""
        alpha_values = {}
        factor_values_dict = {}
        
        if factor_data_by_date and date in factor_data_by_date:
            date_factor_data = factor_data_by_date[date]
            for factor_id in factor_ids:
                if factor_id not in date_factor_data:
                    continue
                
                date_data = date_factor_data[factor_id]
                if date_data.empty:
                    continue
                
                stock_col = 'stock_code' if 'stock_code' in date_data.columns else 'code'
                value_col = 'factor_value' if 'factor_value' in date_data.columns else 'value'
                
                if stock_col in date_data.columns and value_col in date_data.columns:
                    stocks = date_data[stock_col].values
                    values = date_data[value_col].values
                    for i in range(len(stocks)):
                        stock_code = stocks[i]
                        if stock_code not in factor_values_dict:
                            factor_values_dict[stock_code] = {}
                        factor_values_dict[stock_code][factor_id] = values[i]
        elif factor_data:
            for factor_id in factor_ids:
                if factor_id not in factor_data:
                    continue
                
                df = factor_data[factor_id]
                
                if 'date' in df.columns:
                    date_data = df[df['date'] == date]
                else:
                    try:
                        date_data = df.loc[date]
                    except KeyError:
                        continue
                
                if date_data.empty:
                    continue
                
                stock_col = 'stock_code' if 'stock_code' in date_data.columns else 'code'
                value_col = 'factor_value' if 'factor_value' in date_data.columns else 'value'
                
                if stock_col in date_data.columns and value_col in date_data.columns:
                    stocks = date_data[stock_col].values
                    values = date_data[value_col].values
                    for i in range(len(stocks)):
                        stock_code = stocks[i]
                        if stock_code not in factor_values_dict:
                            factor_values_dict[stock_code] = {}
                        factor_values_dict[stock_code][factor_id] = values[i]
        
        if not factor_values_dict:
            return {}
        
        factor_directions = {}
        for factor_id in factor_ids:
            factor = self._factor_registry.get(factor_id)
            if factor:
                if factor.quality_metrics and factor.quality_metrics.ic_mean:
                    ic = factor.quality_metrics.ic_mean
                    factor_directions[factor_id] = 1 if ic > 0 else -1
                else:
                    from ..factor.registry import FactorDirection
                    if factor.direction == FactorDirection.NEGATIVE:
                        factor_directions[factor_id] = -1
                    else:
                        factor_directions[factor_id] = 1
            else:
                factor_directions[factor_id] = 1
        
        for stock_code, stock_factor_values in factor_values_dict.items():
            alpha = 0.0
            total_weight = 0.0
            
            for factor_id, weight in zip(factor_ids, weights):
                if factor_id in stock_factor_values:
                    value = stock_factor_values[factor_id]
                    direction = factor_directions.get(factor_id, 1)
                    if not pd.isna(value) and np.isfinite(value):
                        alpha += value * weight * direction
                        total_weight += weight
            
            if total_weight > 0:
                alpha_values[stock_code] = alpha / total_weight
        
        return alpha_values
    
    def generate_batch(
        self,
        config: FactorCombinationConfig,
        dates: List[str],
        stock_codes: Optional[List[str]] = None,
        factor_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Dict[str, AlphaGenerationResult]:
        """
        批量生成Alpha
        
        Args:
            config: 因子组合配置
            dates: 日期列表
            stock_codes: 股票代码列表
            factor_data: 因子数据（可选）
            
        Returns:
            日期到Alpha结果的映射
        """
        results = {}
        
        if stock_codes and factor_data is None:
            all_dates_str = [d for d in dates]
            date_range_start = min(all_dates_str)
            date_range_end = max(all_dates_str)
            
            stock_data = self._fetch_stock_data(
                stock_codes=stock_codes,
                date=date_range_end,
                lookback_days=365
            )
        else:
            stock_data = None
        
        for date in dates:
            result = self.generate(
                config=config,
                date=date,
                stock_codes=stock_codes,
                factor_data=factor_data,
                stock_data=stock_data
            )
            results[date] = result
        
        return results
    
    def get_top_stocks(
        self,
        alpha_result: AlphaGenerationResult,
        top_n: int = 50
    ) -> List[str]:
        """
        获取Alpha最高的股票
        
        Args:
            alpha_result: Alpha生成结果
            top_n: 股票数量
            
        Returns:
            股票代码列表
        """
        if not alpha_result.success:
            return []
        
        return alpha_result.ranked_stocks[:top_n]
    
    def normalize_alpha(
        self,
        alpha_values: Dict[str, float],
        method: str = "zscore"
    ) -> Dict[str, float]:
        """
        标准化Alpha值
        
        Args:
            alpha_values: Alpha值字典
            method: 标准化方法 (zscore, minmax, rank)
            
        Returns:
            标准化后的Alpha值
        """
        if not alpha_values:
            return {}
        
        values = np.array(list(alpha_values.values()))
        stocks = list(alpha_values.keys())
        
        valid_mask = np.isfinite(values)
        if not valid_mask.all():
            values = values[valid_mask]
            stocks = [s for s, v in zip(stocks, valid_mask) if v]
        
        if len(values) == 0:
            return {}
        
        if method == "zscore":
            mean = values.mean()
            std = values.std()
            if std > 0:
                normalized = (values - mean) / std
            else:
                normalized = values - mean
        elif method == "minmax":
            min_val = values.min()
            max_val = values.max()
            if max_val > min_val:
                normalized = (values - min_val) / (max_val - min_val)
            else:
                normalized = np.ones_like(values) * 0.5
        elif method == "rank":
            ranks = pd.Series(values).rank(pct=True)
            normalized = ranks.values
        else:
            normalized = values
        
        return {stock: float(score) for stock, score in zip(stocks, normalized)}
    
    def clear_cache(self):
        """清空缓存"""
        if self._cache:
            self._cache.clear()
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """获取缓存统计"""
        if self._cache:
            return self._cache.get_stats()
        return None


_default_generator: Optional[AlphaGenerator] = None


def get_alpha_generator() -> AlphaGenerator:
    """获取Alpha生成器实例"""
    global _default_generator
    if _default_generator is None:
        _default_generator = AlphaGenerator()
    return _default_generator


def reset_alpha_generator():
    """重置Alpha生成器实例"""
    global _default_generator
    _default_generator = None
