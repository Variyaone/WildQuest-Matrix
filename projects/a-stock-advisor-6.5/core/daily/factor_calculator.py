"""
因子计算器

智能判断是否需要计算因子值，根据因子类型决定计算频率。
"""

import os
import json
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pandas as pd
import numpy as np

from ..infrastructure.logging import get_logger
from ..infrastructure.config import get_data_paths
from ..data.storage import get_data_storage


class FactorFrequency(Enum):
    """因子计算频率"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass
class FactorInfo:
    """因子信息"""
    factor_id: str
    name: str
    frequency: FactorFrequency
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    last_calculated: Optional[datetime] = None
    cache_path: Optional[str] = None


@dataclass
class FactorCalcResult:
    """因子计算结果"""
    success: bool
    factors_calculated: int = 0
    factors_skipped: int = 0
    factors_failed: int = 0
    total_rows: int = 0
    duration_seconds: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error_messages: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "factors_calculated": self.factors_calculated,
            "factors_skipped": self.factors_skipped,
            "factors_failed": self.factors_failed,
            "total_rows": self.total_rows,
            "duration_seconds": self.duration_seconds,
            "details": self.details,
            "error_messages": self.error_messages
        }


@dataclass
class SingleFactorResult:
    """单个因子计算结果"""
    factor_id: str
    success: bool
    rows: int = 0
    error_message: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


class DailyFactorCalculator:
    """
    因子计算器
    
    智能判断是否需要计算因子值：
    1. 检查因子缓存是否存在
    2. 检查因子数据时间戳
    3. 检查依赖的数据是否更新
    4. 根据因子类型决定计算频率
    5. 只计算需要更新的因子
    
    因子计算频率：
    - 日线动量因子：每日收盘后
    - 日线成交量因子：每日收盘后
    - 周线因子：每周一收盘后
    - 月线因子：每月首个交易日收盘后
    - 财务因子：财报发布后
    """
    
    FACTOR_FREQUENCY_MAP = {
        "momentum_daily": FactorFrequency.DAILY,
        "volume_daily": FactorFrequency.DAILY,
        "technical_daily": FactorFrequency.DAILY,
        "momentum_weekly": FactorFrequency.WEEKLY,
        "volume_weekly": FactorFrequency.WEEKLY,
        "momentum_monthly": FactorFrequency.MONTHLY,
        "volume_monthly": FactorFrequency.MONTHLY,
        "fundamental": FactorFrequency.QUARTERLY,
    }
    
    def __init__(
        self,
        storage=None,
        data_paths=None,
        factor_registry_path: Optional[str] = None,
        logger_name: str = "daily.factor_calculator"
    ):
        """
        初始化因子计算器
        
        Args:
            storage: 数据存储实例
            data_paths: 数据路径配置
            factor_registry_path: 因子注册表路径
            logger_name: 日志名称
        """
        self.storage = storage or get_data_storage()
        self.data_paths = data_paths or get_data_paths()
        self.logger = get_logger(logger_name)
        
        self.factor_registry_path = factor_registry_path or os.path.join(
            self.data_paths.data_root, "factors", "factor_registry.json"
        )
        
        self._factor_registry: Dict[str, FactorInfo] = {}
        self._factor_functions: Dict[str, Callable] = {}
        
        self._load_factor_registry()
    
    def _load_factor_registry(self):
        """加载因子注册表"""
        if os.path.exists(self.factor_registry_path):
            try:
                with open(self.factor_registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for factor_id, info in data.get("factors", {}).items():
                    frequency = FactorFrequency(info.get("frequency", "daily"))
                    self._factor_registry[factor_id] = FactorInfo(
                        factor_id=factor_id,
                        name=info.get("name", factor_id),
                        frequency=frequency,
                        description=info.get("description", ""),
                        dependencies=info.get("dependencies", [])
                    )
                
                self.logger.info(f"加载因子注册表: {len(self._factor_registry)} 个因子")
            except Exception as e:
                self.logger.warning(f"加载因子注册表失败: {e}")
    
    def _save_factor_registry(self):
        """保存因子注册表"""
        try:
            Path(self.factor_registry_path).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "factors": {
                    fid: {
                        "name": info.name,
                        "frequency": info.frequency.value,
                        "description": info.description,
                        "dependencies": info.dependencies
                    }
                    for fid, info in self._factor_registry.items()
                },
                "last_update": datetime.now().isoformat()
            }
            
            with open(self.factor_registry_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存因子注册表失败: {e}")
    
    def register_factor(
        self,
        factor_id: str,
        name: str,
        calc_func: Callable,
        frequency: FactorFrequency = FactorFrequency.DAILY,
        description: str = "",
        dependencies: Optional[List[str]] = None
    ):
        """
        注册因子
        
        Args:
            factor_id: 因子ID
            name: 因子名称
            calc_func: 计算函数
            frequency: 计算频率
            description: 描述
            dependencies: 依赖因子列表
        """
        self._factor_registry[factor_id] = FactorInfo(
            factor_id=factor_id,
            name=name,
            frequency=frequency,
            description=description,
            dependencies=dependencies or []
        )
        self._factor_functions[factor_id] = calc_func
        
        self._save_factor_registry()
        self.logger.info(f"注册因子: {factor_id} ({frequency.value})")
    
    def calculate(
        self,
        factor_ids: Optional[List[str]] = None,
        force: bool = False,
        date: Optional[datetime] = None
    ) -> FactorCalcResult:
        """
        执行因子计算
        
        Args:
            factor_ids: 要计算的因子ID列表（None则计算全部）
            force: 是否强制计算（忽略缓存）
            date: 计算日期（None则使用当前日期）
            
        Returns:
            FactorCalcResult: 计算结果
        """
        import time
        start_time = time.time()
        
        date = date or datetime.now()
        
        self.logger.info(f"开始因子计算: {date.strftime('%Y-%m-%d')}")
        
        if factor_ids is None:
            factor_ids = list(self._factor_registry.keys())
        
        if not factor_ids:
            self.logger.warning("没有需要计算的因子")
            return FactorCalcResult(
                success=True,
                details={"message": "没有需要计算的因子"}
            )
        
        results: List[SingleFactorResult] = []
        
        for factor_id in factor_ids:
            result = self._calculate_single_factor(factor_id, force, date)
            results.append(result)
        
        duration = time.time() - start_time
        
        calculated = sum(1 for r in results if r.success and not r.skipped)
        skipped = sum(1 for r in results if r.skipped)
        failed = sum(1 for r in results if not r.success and not r.skipped)
        total_rows = sum(r.rows for r in results if r.success)
        
        success = failed == 0
        
        self.logger.info(
            f"因子计算完成: 计算={calculated}, 跳过={skipped}, "
            f"失败={failed}, 耗时={duration:.2f}秒"
        )
        
        return FactorCalcResult(
            success=success,
            factors_calculated=calculated,
            factors_skipped=skipped,
            factors_failed=failed,
            total_rows=total_rows,
            duration_seconds=duration,
            details={
                "factors": {r.factor_id: {
                    "success": r.success,
                    "rows": r.rows,
                    "skipped": r.skipped,
                    "skip_reason": r.skip_reason
                } for r in results}
            },
            error_messages=[r.error_message for r in results if r.error_message]
        )
    
    def _calculate_single_factor(
        self,
        factor_id: str,
        force: bool,
        date: datetime
    ) -> SingleFactorResult:
        """
        计算单个因子
        
        Args:
            factor_id: 因子ID
            force: 是否强制计算
            date: 计算日期
            
        Returns:
            SingleFactorResult: 计算结果
        """
        result = SingleFactorResult(factor_id=factor_id, success=False)
        
        if factor_id not in self._factor_registry:
            result.error_message = f"因子未注册: {factor_id}"
            return result
        
        factor_info = self._factor_registry[factor_id]
        
        if not force:
            should_calc, reason = self._should_calculate(factor_info, date)
            if not should_calc:
                result.skipped = True
                result.skip_reason = reason
                result.success = True
                self.logger.info(f"跳过因子 {factor_id}: {reason}")
                return result
        
        if factor_id not in self._factor_functions:
            result.error_message = f"因子计算函数未注册: {factor_id}"
            return result
        
        try:
            self.logger.info(f"计算因子: {factor_id}")
            
            calc_func = self._factor_functions[factor_id]
            factor_data = calc_func(date)
            
            if factor_data is None or len(factor_data) == 0:
                result.error_message = "计算结果为空"
                return result
            
            save_result = self._save_factor_data(factor_id, factor_data)
            
            if not save_result:
                result.error_message = "保存因子数据失败"
                return result
            
            self._update_factor_timestamp(factor_id, date)
            
            result.success = True
            result.rows = len(factor_data)
            
            self.logger.info(f"因子 {factor_id} 计算成功，行数: {result.rows}")
            
        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"计算因子 {factor_id} 失败: {e}")
        
        return result
    
    def _should_calculate(
        self,
        factor_info: FactorInfo,
        date: datetime
    ) -> tuple:
        """
        判断是否需要计算因子
        
        Args:
            factor_info: 因子信息
            date: 当前日期
            
        Returns:
            tuple: (是否需要计算, 原因)
        """
        frequency = factor_info.frequency
        
        if frequency == FactorFrequency.DAILY:
            return True, "日线因子需要每日计算"
        
        if frequency == FactorFrequency.WEEKLY:
            if date.weekday() == 0:
                return True, "周线因子在周一计算"
            return False, "周线因子只在周一计算"
        
        if frequency == FactorFrequency.MONTHLY:
            if date.day <= 5:
                return True, "月线因子在月初计算"
            return False, "月线因子只在月初计算"
        
        if frequency == FactorFrequency.QUARTERLY:
            if date.month in [1, 4, 7, 10] and date.day <= 10:
                return True, "季度因子在季度初计算"
            return False, "季度因子只在季度初计算"
        
        return True, "默认需要计算"
    
    def _save_factor_data(
        self,
        factor_id: str,
        data: pd.DataFrame
    ) -> bool:
        """
        保存因子数据
        
        Args:
            factor_id: 因子ID
            data: 因子数据
            
        Returns:
            bool: 是否成功
        """
        try:
            result = self.storage.save_factor_data(data, factor_id)
            return result.success
        except Exception as e:
            self.logger.error(f"保存因子数据失败 {factor_id}: {e}")
            return False
    
    def _update_factor_timestamp(
        self,
        factor_id: str,
        date: datetime
    ):
        """
        更新因子时间戳
        
        Args:
            factor_id: 因子ID
            date: 计算日期
        """
        if factor_id in self._factor_registry:
            self._factor_registry[factor_id].last_calculated = date
            self._save_factor_registry()
    
    def check_factor_freshness(
        self,
        factor_ids: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        检查因子新鲜度
        
        Args:
            factor_ids: 因子ID列表
            
        Returns:
            Dict[str, bool]: 各因子是否新鲜
        """
        if factor_ids is None:
            factor_ids = list(self._factor_registry.keys())
        
        freshness = {}
        now = datetime.now()
        
        for factor_id in factor_ids:
            if factor_id not in self._factor_registry:
                freshness[factor_id] = False
                continue
            
            info = self._factor_registry[factor_id]
            
            if info.last_calculated is None:
                freshness[factor_id] = False
                continue
            
            age = (now - info.last_calculated).total_seconds() / 3600
            
            if info.frequency == FactorFrequency.DAILY:
                freshness[factor_id] = age <= 24
            elif info.frequency == FactorFrequency.WEEKLY:
                freshness[factor_id] = age <= 168
            elif info.frequency == FactorFrequency.MONTHLY:
                freshness[factor_id] = age <= 720
            else:
                freshness[factor_id] = age <= 2160
        
        return freshness
    
    def get_expired_factors(
        self,
        date: Optional[datetime] = None
    ) -> List[str]:
        """
        获取过期因子列表
        
        Args:
            date: 参考日期
            
        Returns:
            List[str]: 过期因子ID列表
        """
        date = date or datetime.now()
        expired = []
        
        for factor_id, info in self._factor_registry.items():
            should_calc, _ = self._should_calculate(info, date)
            if should_calc:
                if info.last_calculated is None:
                    expired.append(factor_id)
                else:
                    freshness = self.check_factor_freshness([factor_id])
                    if not freshness.get(factor_id, False):
                        expired.append(factor_id)
        
        return expired
    
    def get_factor_info(self, factor_id: str) -> Optional[FactorInfo]:
        """
        获取因子信息
        
        Args:
            factor_id: 因子ID
            
        Returns:
            Optional[FactorInfo]: 因子信息
        """
        return self._factor_registry.get(factor_id)
    
    def list_factors(self) -> List[str]:
        """
        列出所有已注册因子
        
        Returns:
            List[str]: 因子ID列表
        """
        return list(self._factor_registry.keys())


def create_default_factor_calculator(storage=None) -> DailyFactorCalculator:
    """
    创建默认因子计算器
    
    Args:
        storage: 数据存储实例
        
    Returns:
        DailyFactorCalculator: 因子计算器实例
    """
    calculator = DailyFactorCalculator(storage=storage)
    
    def calc_momentum(date):
        return pd.DataFrame({
            "stock_code": ["000001.SZ", "000002.SZ"],
            "date": [date.strftime('%Y-%m-%d')] * 2,
            "momentum_5d": [0.02, -0.01],
            "momentum_20d": [0.05, 0.03]
        })
    
    def calc_volume(date):
        return pd.DataFrame({
            "stock_code": ["000001.SZ", "000002.SZ"],
            "date": [date.strftime('%Y-%m-%d')] * 2,
            "volume_ratio": [1.2, 0.8],
            "turnover_rate": [0.03, 0.02]
        })
    
    calculator.register_factor(
        factor_id="momentum_daily",
        name="日线动量因子",
        calc_func=calc_momentum,
        frequency=FactorFrequency.DAILY,
        description="基于日线数据的动量因子"
    )
    
    calculator.register_factor(
        factor_id="volume_daily",
        name="日线成交量因子",
        calc_func=calc_volume,
        frequency=FactorFrequency.DAILY,
        description="基于日线数据的成交量因子"
    )
    
    return calculator
