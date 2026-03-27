"""
因子迁移模块

将现有因子库（Alpha101、Alpha191、自定义因子）迁移到新的因子库管理系统。
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import numpy as np

from .registry import (
    FactorRegistry, 
    FactorMetadata,
    FactorCategory,
    FactorSubCategory,
    FactorDirection,
    FactorSource,
    get_factor_registry
)
from .classification import FactorClassification
from .engine import FactorEngine, get_factor_engine


@dataclass
class MigrationResult:
    """迁移结果"""
    success: bool
    total_factors: int
    migrated_factors: int
    failed_factors: int
    factor_ids: List[str] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.factor_ids is None:
            self.factor_ids = []
        if self.errors is None:
            self.errors = []


ALPHA101_FACTORS = [
    {
        "name": "动量因子_001",
        "description": "基于收盘价和最高价的动量因子",
        "formula": "(close - delay(close, 10)) / delay(close, 10)",
        "category": FactorCategory.MOMENTUM,
        "sub_category": FactorSubCategory.TIME_SERIES_MOMENTUM,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA101
    },
    {
        "name": "动量因子_002",
        "description": "基于成交量和价格的动量因子",
        "formula": "ts_corr(close, volume, 10)",
        "category": FactorCategory.MOMENTUM,
        "sub_category": FactorSubCategory.CROSS_SECTIONAL_MOMENTUM,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA101
    },
    {
        "name": "动量因子_003",
        "description": "基于最高价和最低价的波动动量",
        "formula": "ts_rank(high - low, 10)",
        "category": FactorCategory.VOLATILITY,
        "sub_category": FactorSubCategory.HISTORICAL_VOLATILITY,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA101
    },
    {
        "name": "成交量因子_001",
        "description": "成交量相对变化率",
        "formula": "volume / ts_mean(volume, 20)",
        "category": FactorCategory.LIQUIDITY,
        "sub_category": FactorSubCategory.VOLUME_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA101
    },
    {
        "name": "反转因子_001",
        "description": "短期价格反转因子",
        "formula": "-1 * ts_delta(close, 5) / delay(close, 5)",
        "category": FactorCategory.TECHNICAL,
        "sub_category": FactorSubCategory.REVERSAL_FACTOR,
        "direction": FactorDirection.NEGATIVE,
        "source": FactorSource.ALPHA101
    },
    {
        "name": "趋势因子_001",
        "description": "均线偏离度因子",
        "formula": "(close - ts_mean(close, 20)) / ts_std(close, 20)",
        "category": FactorCategory.TECHNICAL,
        "sub_category": FactorSubCategory.TREND_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA101
    },
    {
        "name": "波动率因子_001",
        "description": "历史波动率因子",
        "formula": "ts_std(close, 20) / ts_mean(close, 20)",
        "category": FactorCategory.VOLATILITY,
        "sub_category": FactorSubCategory.HISTORICAL_VOLATILITY,
        "direction": FactorDirection.NEGATIVE,
        "source": FactorSource.ALPHA101
    },
    {
        "name": "流动性因子_001",
        "description": "Amihud非流动性因子",
        "formula": "abs(close - delay(close, 1)) / volume",
        "category": FactorCategory.LIQUIDITY,
        "sub_category": FactorSubCategory.LIQUIDITY_INDICATOR,
        "direction": FactorDirection.NEGATIVE,
        "source": FactorSource.ALPHA101
    },
    {
        "name": "动量因子_004",
        "description": "相对强弱因子",
        "formula": "ts_rank(close, 60)",
        "category": FactorCategory.MOMENTUM,
        "sub_category": FactorSubCategory.TIME_SERIES_MOMENTUM,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA101
    },
    {
        "name": "量价因子_001",
        "description": "量价相关性因子",
        "formula": "ts_corr(close, volume, 20)",
        "category": FactorCategory.LIQUIDITY,
        "sub_category": FactorSubCategory.VOLUME_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA101
    }
]


ALPHA191_FACTORS = [
    {
        "name": "动量因子_101",
        "description": "基于收盘价动量的因子",
        "formula": "ts_rank(close / delay(close, 1), 10)",
        "category": FactorCategory.MOMENTUM,
        "sub_category": FactorSubCategory.TIME_SERIES_MOMENTUM,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA191
    },
    {
        "name": "动量因子_102",
        "description": "基于成交量的动量因子",
        "formula": "volume / ts_mean(volume, 10)",
        "category": FactorCategory.LIQUIDITY,
        "sub_category": FactorSubCategory.VOLUME_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA191
    },
    {
        "name": "波动因子_101",
        "description": "日内波动率因子",
        "formula": "(high - low) / delay(close, 1)",
        "category": FactorCategory.VOLATILITY,
        "sub_category": FactorSubCategory.HISTORICAL_VOLATILITY,
        "direction": FactorDirection.NEGATIVE,
        "source": FactorSource.ALPHA191
    },
    {
        "name": "趋势因子_101",
        "description": "价格趋势因子",
        "formula": "ts_mean(close, 5) / ts_mean(close, 20)",
        "category": FactorCategory.TECHNICAL,
        "sub_category": FactorSubCategory.TREND_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA191
    },
    {
        "name": "反转因子_101",
        "description": "短期反转因子",
        "formula": "-1 * (close - delay(close, 1)) / delay(close, 1)",
        "category": FactorCategory.TECHNICAL,
        "sub_category": FactorSubCategory.REVERSAL_FACTOR,
        "direction": FactorDirection.NEGATIVE,
        "source": FactorSource.ALPHA191
    },
    {
        "name": "成交量因子_101",
        "description": "成交量变化因子",
        "formula": "ts_delta(volume, 5) / delay(volume, 5)",
        "category": FactorCategory.LIQUIDITY,
        "sub_category": FactorSubCategory.VOLUME_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA191
    },
    {
        "name": "振幅因子_101",
        "description": "价格振幅因子",
        "formula": "(high - low) / ts_mean(high - low, 20)",
        "category": FactorCategory.VOLATILITY,
        "sub_category": FactorSubCategory.VOLATILITY_CHANGE,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA191
    },
    {
        "name": "换手因子_101",
        "description": "换手率因子",
        "formula": "volume / (close * 100000000)",
        "category": FactorCategory.LIQUIDITY,
        "sub_category": FactorSubCategory.VOLUME_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.ALPHA191
    }
]


CUSTOM_FACTORS = [
    {
        "name": "价值因子_PE",
        "description": "市盈率因子",
        "formula": "pe_ratio",
        "category": FactorCategory.VALUE,
        "sub_category": FactorSubCategory.VALUATION,
        "direction": FactorDirection.NEGATIVE,
        "source": FactorSource.SELF_DEVELOPED,
        "tags": ["估值", "基本面"]
    },
    {
        "name": "价值因子_PB",
        "description": "市净率因子",
        "formula": "pb_ratio",
        "category": FactorCategory.VALUE,
        "sub_category": FactorSubCategory.VALUATION,
        "direction": FactorDirection.NEGATIVE,
        "source": FactorSource.SELF_DEVELOPED,
        "tags": ["估值", "基本面"]
    },
    {
        "name": "质量因子_ROE",
        "description": "净资产收益率因子",
        "formula": "roe",
        "category": FactorCategory.QUALITY,
        "sub_category": FactorSubCategory.PROFITABILITY,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.SELF_DEVELOPED,
        "tags": ["盈利能力", "基本面"]
    },
    {
        "name": "质量因子_ROA",
        "description": "总资产收益率因子",
        "formula": "roa",
        "category": FactorCategory.QUALITY,
        "sub_category": FactorSubCategory.PROFITABILITY,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.SELF_DEVELOPED,
        "tags": ["盈利能力", "基本面"]
    },
    {
        "name": "质量因子_营收增长",
        "description": "营收增长率因子",
        "formula": "revenue_growth",
        "category": FactorCategory.QUALITY,
        "sub_category": FactorSubCategory.GROWTH,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.SELF_DEVELOPED,
        "tags": ["成长能力", "基本面"]
    },
    {
        "name": "质量因子_净利润增长",
        "description": "净利润增长率因子",
        "formula": "profit_growth",
        "category": FactorCategory.QUALITY,
        "sub_category": FactorSubCategory.GROWTH,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.SELF_DEVELOPED,
        "tags": ["成长能力", "基本面"]
    },
    {
        "name": "规模因子_市值",
        "description": "总市值因子",
        "formula": "market_cap",
        "category": FactorCategory.SIZE,
        "sub_category": FactorSubCategory.MARKET_CAP,
        "direction": FactorDirection.NEGATIVE,
        "source": FactorSource.SELF_DEVELOPED,
        "tags": ["规模", "市值"]
    },
    {
        "name": "规模因子_流通市值",
        "description": "流通市值因子",
        "formula": "float_market_cap",
        "category": FactorCategory.SIZE,
        "sub_category": FactorSubCategory.MARKET_CAP,
        "direction": FactorDirection.NEGATIVE,
        "source": FactorSource.SELF_DEVELOPED,
        "tags": ["规模", "市值"]
    },
    {
        "name": "情绪因子_北向资金",
        "description": "北向资金持股变化因子",
        "formula": "north_bound_change",
        "category": FactorCategory.SENTIMENT,
        "sub_category": FactorSubCategory.MARKET_SENTIMENT,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.SELF_DEVELOPED,
        "tags": ["情绪", "资金流向"]
    },
    {
        "name": "情绪因子_分析师评级",
        "description": "分析师评级因子",
        "formula": "analyst_rating",
        "category": FactorCategory.SENTIMENT,
        "sub_category": FactorSubCategory.ANALYST_SENTIMENT,
        "direction": FactorDirection.POSITIVE,
        "source": FactorSource.SELF_DEVELOPED,
        "tags": ["情绪", "分析师"]
    }
]


class FactorMigrator:
    """
    因子迁移器
    
    将现有因子库迁移到新的因子库管理系统。
    """
    
    def __init__(self, registry: Optional[FactorRegistry] = None):
        """
        初始化因子迁移器
        
        Args:
            registry: 因子注册表实例
        """
        self._registry = registry or get_factor_registry()
        self._classification = FactorClassification()
    
    def migrate_alpha101(self) -> MigrationResult:
        """
        迁移Alpha101因子
        
        Returns:
            MigrationResult: 迁移结果
        """
        return self._migrate_factors(ALPHA101_FACTORS, "Alpha101")
    
    def migrate_alpha191(self) -> MigrationResult:
        """
        迁移Alpha191因子
        
        Returns:
            MigrationResult: 迁移结果
        """
        return self._migrate_factors(ALPHA191_FACTORS, "Alpha191")
    
    def migrate_custom_factors(self) -> MigrationResult:
        """
        迁移自定义因子
        
        Returns:
            MigrationResult: 迁移结果
        """
        return self._migrate_factors(CUSTOM_FACTORS, "自定义")
    
    def migrate_all(self) -> Dict[str, MigrationResult]:
        """
        迁移所有因子
        
        Returns:
            Dict[str, MigrationResult]: 各类因子的迁移结果
        """
        return {
            "alpha101": self.migrate_alpha101(),
            "alpha191": self.migrate_alpha191(),
            "custom": self.migrate_custom_factors()
        }
    
    def _migrate_factors(
        self, 
        factors: List[Dict[str, Any]], 
        source_name: str
    ) -> MigrationResult:
        """
        迁移因子列表
        
        Args:
            factors: 因子定义列表
            source_name: 来源名称
            
        Returns:
            MigrationResult: 迁移结果
        """
        migrated_ids = []
        errors = []
        
        for factor_def in factors:
            try:
                metadata = self._registry.register(
                    name=factor_def["name"],
                    description=factor_def["description"],
                    formula=factor_def["formula"],
                    source=factor_def.get("source", FactorSource.SELF_DEVELOPED).value,
                    category=factor_def["category"],
                    sub_category=factor_def["sub_category"],
                    direction=factor_def.get("direction", FactorDirection.POSITIVE),
                    tags=factor_def.get("tags", [])
                )
                migrated_ids.append(metadata.id)
            except Exception as e:
                errors.append(f"{factor_def['name']}: {str(e)}")
        
        return MigrationResult(
            success=len(errors) == 0,
            total_factors=len(factors),
            migrated_factors=len(migrated_ids),
            failed_factors=len(errors),
            factor_ids=migrated_ids,
            errors=errors
        )
    
    def register_factor_with_function(
        self,
        name: str,
        description: str,
        calc_func: Callable,
        category: FactorCategory,
        sub_category: FactorSubCategory,
        direction: FactorDirection = FactorDirection.POSITIVE,
        source: str = "自研",
        tags: Optional[List[str]] = None
    ) -> FactorMetadata:
        """
        注册带计算函数的因子
        
        Args:
            name: 因子名称
            description: 因子描述
            calc_func: 计算函数
            category: 一级分类
            sub_category: 二级分类
            direction: 因子方向
            source: 来源
            tags: 标签列表
            
        Returns:
            FactorMetadata: 注册的因子元数据
        """
        formula = f"custom:{name}"
        
        metadata = self._registry.register(
            name=name,
            description=description,
            formula=formula,
            source=source,
            category=category,
            sub_category=sub_category,
            direction=direction,
            tags=tags or []
        )
        
        engine = get_factor_engine()
        engine.register_custom_factor(metadata.id, calc_func)
        
        return metadata
    
    def get_migration_summary(self) -> Dict[str, Any]:
        """
        获取迁移摘要
        
        Returns:
            Dict[str, Any]: 迁移摘要信息
        """
        stats = self._registry.get_statistics()
        
        return {
            "total_factors": stats["total_count"],
            "by_category": stats["by_category"],
            "by_source": stats["by_source"],
            "avg_score": stats["avg_score"]
        }


def migrate_factors() -> Dict[str, MigrationResult]:
    """
    执行因子迁移
    
    Returns:
        Dict[str, MigrationResult]: 迁移结果
    """
    migrator = FactorMigrator()
    return migrator.migrate_all()


def get_factor_migrator() -> FactorMigrator:
    """获取因子迁移器实例"""
    return FactorMigrator()
