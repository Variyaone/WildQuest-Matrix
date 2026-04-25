"""
因子注册表模块

统一管理所有因子的元数据信息，包括编号、名称、描述、公式、来源等。
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from .classification import (
    FactorCategory, 
    FactorSubCategory, 
    get_factor_classification
)
from ..infrastructure.exceptions import FactorException


class FactorDirection(Enum):
    """因子方向"""
    POSITIVE = "正向"
    NEGATIVE = "反向"


class FactorStatus(Enum):
    """因子状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    DEPRECATED = "deprecated"


class ValidationStatus(Enum):
    """验证状态"""
    NOT_VALIDATED = "not_validated"
    VALIDATED = "validated"
    VALIDATED_OOS = "validated_oos"
    FAILED = "failed"
    EXPIRED = "expired"


class FactorSource(Enum):
    """因子来源"""
    SELF_DEVELOPED = "自研"
    ACADEMIC_PAPER = "学术论文"
    THIRD_PARTY = "第三方"
    ALPHA101 = "Alpha101"
    ALPHA191 = "Alpha191"
    WORLD_QUANT = "WorldQuant"


@dataclass
class FactorQualityMetrics:
    """因子质量指标"""
    ic_mean: float = 0.0
    ic_std: float = 0.0
    ir: float = 0.0
    monotonicity: float = 0.0
    correlation_with_others: float = 0.0
    nan_ratio: float = 0.0
    coverage: float = 0.0
    
    ic_t: float = 0.0
    win_rate: float = 0.0
    annual_spread: float = 0.0
    annual_spread_net: float = 0.0
    turnover: float = 0.0
    min_quantile_return: float = 0.0
    max_quantile_return: float = 0.0
    quantile_spread: float = 0.0
    
    backtest_score: int = 0
    backtest_rating: str = ""
    score_details: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactorQualityMetrics":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class BacktestResult:
    """回测结果"""
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    ic: float = 0.0
    
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    stock_pool: str = "全市场"
    n_stocks: int = 0
    n_groups: int = 5
    holding_period: int = 5
    market_type: str = "all_market"
    enable_oos: bool = False
    train_ratio: float = 0.7
    transaction_costs: bool = True
    credibility_score: float = 0.0
    oos_valid: bool = False
    backtest_version: str = "v2.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacktestResult":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class FactorMetadata:
    """因子元数据"""
    id: str
    name: str
    description: str
    formula: str
    source: str
    category: FactorCategory
    sub_category: FactorSubCategory
    direction: FactorDirection = FactorDirection.POSITIVE
    status: FactorStatus = FactorStatus.ACTIVE
    validation_status: ValidationStatus = ValidationStatus.NOT_VALIDATED
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    validated_at: Optional[str] = None
    quality_metrics: Optional[FactorQualityMetrics] = None
    backtest_results: Dict[str, BacktestResult] = field(default_factory=dict)
    score: float = 0.0
    rank: int = 0
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    credibility_score: float = 0.0
    oos_valid: bool = False
    calc_window: int = 0
    data_processing: str = ""
    default_params: str = ""
    update_schedule: str = "下一交易日早晨9:00前更新"
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "formula": self.formula,
            "source": self.source,
            "category": {
                "level1": self.category.value,
                "level2": self.sub_category.value
            },
            "direction": self.direction.value,
            "status": self.status.value,
            "validation_status": self.validation_status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "validated_at": self.validated_at,
            "quality_metrics": self.quality_metrics.to_dict() if self.quality_metrics else None,
            "backtest_results": {k: v.to_dict() for k, v in self.backtest_results.items()},
            "score": self.score,
            "rank": self.rank,
            "tags": self.tags,
            "parameters": self.parameters,
            "credibility_score": self.credibility_score,
            "oos_valid": self.oos_valid,
            "calc_window": self.calc_window,
            "data_processing": self.data_processing,
            "default_params": self.default_params,
            "update_schedule": self.update_schedule
        }
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactorMetadata":
        classification = get_factor_classification()
        
        category = classification.find_category_by_name(data["category"]["level1"])
        sub_category = classification.find_sub_category_by_name(data["category"]["level2"])
        
        direction = FactorDirection.POSITIVE
        if data.get("direction") == "反向":
            direction = FactorDirection.NEGATIVE
        
        status = FactorStatus.ACTIVE
        for s in FactorStatus:
            if s.value == data.get("status", "active"):
                status = s
                break
        
        validation_status = ValidationStatus.NOT_VALIDATED
        for vs in ValidationStatus:
            if vs.value == data.get("validation_status", "not_validated"):
                validation_status = vs
                break
        
        quality_metrics = None
        if data.get("quality_metrics"):
            quality_metrics = FactorQualityMetrics.from_dict(data["quality_metrics"])
        
        backtest_results = {}
        for k, v in data.get("backtest_results", {}).items():
            backtest_results[k] = BacktestResult.from_dict(v)
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            formula=data["formula"],
            source=data["source"],
            category=category or FactorCategory.MOMENTUM,
            sub_category=sub_category or FactorSubCategory.TIME_SERIES_MOMENTUM,
            direction=direction,
            status=status,
            validation_status=validation_status,
            created_at=data.get("created_at", datetime.now().strftime("%Y-%m-%d")),
            updated_at=data.get("updated_at", datetime.now().strftime("%Y-%m-%d")),
            validated_at=data.get("validated_at"),
            quality_metrics=quality_metrics,
            backtest_results=backtest_results,
            score=data.get("score", 0.0),
            rank=data.get("rank", 0),
            tags=data.get("tags", []),
            parameters=data.get("parameters", {}),
            credibility_score=data.get("credibility_score", 0.0),
            oos_valid=data.get("oos_valid", False),
            calc_window=data.get("calc_window", 0),
            data_processing=data.get("data_processing", ""),
            default_params=data.get("default_params", ""),
            update_schedule=data.get("update_schedule", "下一交易日早晨9:00前更新")
        )


class FactorRegistry:
    """
    因子注册表
    
    统一管理所有因子的元数据信息，支持因子的注册、查询、更新和删除。
    """
    
    FACTOR_ID_PREFIX = "F"
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化因子注册表
        
        Args:
            storage_path: 存储路径
        """
        self._factors: Dict[str, FactorMetadata] = {}
        self._next_id: int = 1
        self._storage_path = storage_path or "./data/factors/registry.json"
        self._classification = get_factor_classification()
        
        self._load_registry()
    
    def _load_registry(self):
        """从文件加载注册表"""
        if os.path.exists(self._storage_path):
            try:
                with open(self._storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for factor_id, factor_data in data.get("factors", {}).items():
                    self._factors[factor_id] = FactorMetadata.from_dict(factor_data)
                
                self._next_id = data.get("next_id", 1)
            except Exception as e:
                print(f"加载因子注册表失败: {e}")
    
    def _save_registry(self):
        """保存注册表到文件"""
        try:
            Path(self._storage_path).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "factors": {fid: f.to_dict() for fid, f in self._factors.items()},
                "next_id": self._next_id,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(self._storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存因子注册表失败: {e}")
    
    def _generate_factor_id(self) -> str:
        """生成因子ID"""
        factor_id = f"{self.FACTOR_ID_PREFIX}{self._next_id:05d}"
        self._next_id += 1
        return factor_id
    
    def register(
        self,
        name: str,
        description: str,
        formula: str,
        source: str,
        category: FactorCategory,
        sub_category: FactorSubCategory,
        direction: FactorDirection = FactorDirection.POSITIVE,
        tags: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> FactorMetadata:
        """
        注册新因子
        
        Args:
            name: 因子名称
            description: 因子描述
            formula: 因子公式
            source: 因子来源
            category: 一级分类
            sub_category: 二级分类
            direction: 因子方向
            tags: 标签列表
            parameters: 参数字典
            
        Returns:
            FactorMetadata: 注册的因子元数据
        """
        factor_id = self._generate_factor_id()
        
        existing = self.get_by_name(name)
        if existing:
            return existing
        
        factor = FactorMetadata(
            id=factor_id,
            name=name,
            description=description,
            formula=formula,
            source=source,
            category=category,
            sub_category=sub_category,
            direction=direction,
            tags=tags or [],
            parameters=parameters or {}
        )
        
        self._factors[factor_id] = factor
        self._save_registry()
        
        return factor
    
    def get(self, factor_id: str) -> Optional[FactorMetadata]:
        """
        获取因子
        
        Args:
            factor_id: 因子ID
            
        Returns:
            Optional[FactorMetadata]: 因子元数据
        """
        return self._factors.get(factor_id)
    
    def get_by_name(self, name: str) -> Optional[FactorMetadata]:
        """根据名称获取因子"""
        for factor in self._factors.values():
            if factor.name == name:
                return factor
        return None
    
    def update(
        self, 
        factor_id: str, 
        **kwargs
    ) -> Optional[FactorMetadata]:
        """
        更新因子信息
        
        Args:
            factor_id: 因子ID
            **kwargs: 要更新的字段
            
        Returns:
            Optional[FactorMetadata]: 更新后的因子元数据
        """
        factor = self._factors.get(factor_id)
        if factor is None:
            return None
        
        for key, value in kwargs.items():
            if hasattr(factor, key):
                setattr(factor, key, value)
        
        factor.updated_at = datetime.now().strftime("%Y-%m-%d")
        self._save_registry()
        
        return factor
    
    def update_quality_metrics(
        self, 
        factor_id: str, 
        metrics: FactorQualityMetrics
    ) -> Optional[FactorMetadata]:
        """更新因子质量指标（带质量门槛验证）"""
        from ..infrastructure.quality_gate import get_quality_gate, GateStage
        from ..infrastructure.recovery_manager import get_recovery_manager, OperationType
        
        quality_gate = get_quality_gate()
        recovery_manager = get_recovery_manager()
        
        factor = self.get(factor_id)
        before_state = {
            "status": factor.status.value if factor else "unknown",
            "quality_metrics": factor.quality_metrics.to_dict() if factor and factor.quality_metrics else None
        }
        
        validation_data = {
            'ic_mean': metrics.ic_mean,
            'ir': metrics.ir,
            'win_rate': metrics.win_rate
        }
        
        gate_result = quality_gate.validate(GateStage.FACTOR_REGISTRATION, validation_data)
        
        if not gate_result.passed:
            error_messages = [r.message for r in gate_result.blocking_failures]
            print(f"⚠️  因子 {factor_id} 质量验证失败:")
            for msg in error_messages:
                print(f"    {msg}")
            
            if factor:
                factor.status = FactorStatus.INACTIVE
                factor.updated_at = datetime.now().strftime("%Y-%m-%d")
                self._save_registry()
                print(f"    因子状态已设置为: INACTIVE")
                print(f"    注意: 因子已入库但标记为INACTIVE，可在修复后重新激活")
                
                after_state = {
                    "status": "inactive",
                    "quality_metrics": metrics.to_dict()
                }
                
                recovery_manager.record_operation(
                    operation_type=OperationType.FACTOR_DEACTIVATE,
                    description=f"因子 {factor_id} 因质量验证失败被停用",
                    operator="quality_gate",
                    before_state={factor_id: before_state},
                    after_state={factor_id: after_state},
                    related_ids=[factor_id],
                    metadata={
                        "validation_errors": error_messages,
                        "ic_mean": metrics.ic_mean,
                        "ir": metrics.ir
                    }
                )
        
        return self.update(factor_id, quality_metrics=metrics)
    
    def update_backtest_result(
        self, 
        factor_id: str, 
        market_type: str, 
        result: BacktestResult
    ) -> Optional[FactorMetadata]:
        """更新因子回测结果"""
        factor = self._factors.get(factor_id)
        if factor is None:
            return None
        
        factor.backtest_results[market_type] = result
        factor.updated_at = datetime.now().strftime("%Y-%m-%d")
        self._save_registry()
        
        return factor
    
    def update_score(self, factor_id: str, score: float, rank: int = 0) -> Optional[FactorMetadata]:
        """更新因子评分和排名"""
        return self.update(factor_id, score=score, rank=rank)
    
    def update_validation_status(
        self,
        factor_id: str,
        validation_status: ValidationStatus,
        credibility_score: float = 0.0,
        oos_valid: bool = False
    ) -> Optional[FactorMetadata]:
        """
        更新因子验证状态
        
        Args:
            factor_id: 因子ID
            validation_status: 验证状态
            credibility_score: 可信度评分
            oos_valid: 样本外验证是否通过
            
        Returns:
            Optional[FactorMetadata]: 更新后的因子元数据
        """
        factor = self._factors.get(factor_id)
        if factor is None:
            return None
        
        factor.validation_status = validation_status
        factor.credibility_score = credibility_score
        factor.oos_valid = oos_valid
        factor.validated_at = datetime.now().strftime("%Y-%m-%d")
        factor.updated_at = datetime.now().strftime("%Y-%m-%d")
        self._save_registry()
        
        return factor
    
    def list_validated(self) -> List[FactorMetadata]:
        """获取已验证通过的因子"""
        return [
            f for f in self._factors.values()
            if f.validation_status in (ValidationStatus.VALIDATED, ValidationStatus.VALIDATED_OOS)
        ]
    
    def list_by_validation_status(self, status: ValidationStatus) -> List[FactorMetadata]:
        """按验证状态获取因子"""
        return [f for f in self._factors.values() if f.validation_status == status]
    
    def delete(self, factor_id: str) -> bool:
        """
        删除因子
        
        Args:
            factor_id: 因子ID
            
        Returns:
            bool: 是否成功
        """
        if factor_id in self._factors:
            del self._factors[factor_id]
            self._save_registry()
            return True
        return False
    
    def set_status(self, factor_id: str, status: FactorStatus) -> Optional[FactorMetadata]:
        """设置因子状态"""
        return self.update(factor_id, status=status)
    
    def list_all(self) -> List[FactorMetadata]:
        """获取所有因子"""
        return list(self._factors.values())
    
    def list_by_category(self, category: FactorCategory) -> List[FactorMetadata]:
        """按一级分类获取因子"""
        return [f for f in self._factors.values() if f.category == category]
    
    def list_by_sub_category(
        self, 
        category: FactorCategory, 
        sub_category: FactorSubCategory
    ) -> List[FactorMetadata]:
        """按二级分类获取因子"""
        return [
            f for f in self._factors.values() 
            if f.category == category and f.sub_category == sub_category
        ]
    
    def list_by_status(self, status: FactorStatus) -> List[FactorMetadata]:
        """按状态获取因子"""
        return [f for f in self._factors.values() if f.status == status]
    
    def list_by_source(self, source: str) -> List[FactorMetadata]:
        """按来源获取因子"""
        return [f for f in self._factors.values() if f.source == source]
    
    def list_by_tags(self, tags: List[str], match_all: bool = False) -> List[FactorMetadata]:
        """按标签获取因子"""
        result = []
        for factor in self._factors.values():
            if match_all:
                if all(tag in factor.tags for tag in tags):
                    result.append(factor)
            else:
                if any(tag in factor.tags for tag in tags):
                    result.append(factor)
        return result
    
    def search(self, keyword: str) -> List[FactorMetadata]:
        """搜索因子（按名称、描述、标签）"""
        keyword = keyword.lower()
        result = []
        for factor in self._factors.values():
            if (keyword in factor.name.lower() or 
                keyword in factor.description.lower() or
                any(keyword in tag.lower() for tag in factor.tags)):
                result.append(factor)
        return result
    
    def get_top_factors(self, n: int = 10, by_score: bool = True) -> List[FactorMetadata]:
        """获取排名前N的因子"""
        factors = list(self._factors.values())
        if by_score:
            factors.sort(key=lambda f: f.score, reverse=True)
        else:
            factors.sort(key=lambda f: f.rank)
        return factors[:n]
    
    def get_factor_count(self) -> int:
        """获取因子总数"""
        return len(self._factors)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_count": len(self._factors),
            "by_category": {},
            "by_status": {},
            "by_source": {},
            "avg_score": 0.0,
            "avg_ic": 0.0,
        }
        
        total_score = 0.0
        total_ic = 0.0
        ic_count = 0
        
        for factor in self._factors.values():
            cat_name = factor.category.value
            stats["by_category"][cat_name] = stats["by_category"].get(cat_name, 0) + 1
            
            status_name = factor.status.value
            stats["by_status"][status_name] = stats["by_status"].get(status_name, 0) + 1
            
            stats["by_source"][factor.source] = stats["by_source"].get(factor.source, 0) + 1
            
            total_score += factor.score
            
            if factor.quality_metrics:
                total_ic += factor.quality_metrics.ic_mean
                ic_count += 1
        
        if self._factors:
            stats["avg_score"] = total_score / len(self._factors)
        
        if ic_count > 0:
            stats["avg_ic"] = total_ic / ic_count
        
        return stats
    
    def export_to_json(self, file_path: str):
        """导出注册表到JSON文件"""
        data = {
            "factors": {fid: f.to_dict() for fid, f in self._factors.items()},
            "statistics": self.get_statistics()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def import_from_json(self, file_path: str, overwrite: bool = False):
        """从JSON文件导入因子"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for factor_id, factor_data in data.get("factors", {}).items():
            if overwrite or factor_id not in self._factors:
                self._factors[factor_id] = FactorMetadata.from_dict(factor_data)
        
        self._save_registry()


_default_registry: Optional[FactorRegistry] = None


def get_factor_registry(storage_path: Optional[str] = None) -> FactorRegistry:
    """获取全局因子注册表实例"""
    global _default_registry
    if storage_path is not None or _default_registry is None:
        _default_registry = FactorRegistry(storage_path)
    return _default_registry


def reset_factor_registry():
    """重置全局因子注册表"""
    global _default_registry
    _default_registry = None
