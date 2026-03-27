"""
组合持久化存储模块

管理组合数据的持久化存储:
- 组合配置存储
- 组合权重存储
- 组合历史记录
- 组合元数据管理
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import logging

from core.infrastructure.exceptions import AppException, ErrorCode, DataStorageException

logger = logging.getLogger(__name__)


@dataclass
class PortfolioMetadata:
    """组合元数据"""
    id: str
    name: str
    description: str = ""
    optimization_method: str = "equal_weight"
    constraints: Dict[str, Any] = field(default_factory=dict)
    neutralization: Dict[str, bool] = field(default_factory=dict)
    rebalance: Dict[str, Any] = field(default_factory=dict)
    risk_budget: Dict[str, float] = field(default_factory=dict)
    performance: Dict[str, float] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PortfolioMetadata':
        return cls(**data)


@dataclass
class PortfolioSnapshot:
    """组合快照"""
    portfolio_id: str
    date: str
    weights: Dict[str, float]
    prices: Dict[str, float] = field(default_factory=dict)
    values: Dict[str, float] = field(default_factory=dict)
    total_value: float = 0.0
    returns: Dict[str, float] = field(default_factory=dict)
    portfolio_return: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PortfolioSnapshot':
        return cls(**data)


class PortfolioStorage:
    """
    组合持久化存储
    
    功能:
    - 保存/加载组合配置
    - 保存/加载组合权重
    - 管理组合历史记录
    - 管理组合元数据
    """
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "./data/portfolios"
        self._ensure_storage_dirs()
    
    def _ensure_storage_dirs(self):
        """确保存储目录存在"""
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        
        registry_path = os.path.join(self.storage_path, "portfolio_registry.json")
        if not os.path.exists(registry_path):
            self._save_registry({})
    
    def _get_registry_path(self) -> str:
        """获取注册表路径"""
        return os.path.join(self.storage_path, "portfolio_registry.json")
    
    def _load_registry(self) -> Dict[str, Any]:
        """加载注册表"""
        registry_path = self._get_registry_path()
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"注册表JSON解析错误: {e}")
            return {}
    
    def _save_registry(self, registry: Dict[str, Any]):
        """保存注册表"""
        registry_path = self._get_registry_path()
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)
    
    def _get_portfolio_dir(self, portfolio_id: str) -> str:
        """获取组合目录"""
        return os.path.join(self.storage_path, portfolio_id)
    
    def _generate_portfolio_id(self) -> str:
        """生成组合ID"""
        registry = self._load_registry()
        max_id = 0
        for pid in registry.keys():
            if pid.startswith("PO"):
                try:
                    num = int(pid[2:])
                    max_id = max(max_id, num)
                except ValueError:
                    continue
        return f"PO{max_id + 1:05d}"
    
    def save_portfolio(
        self,
        name: str,
        weights: Dict[str, float],
        description: str = "",
        optimization_method: str = "equal_weight",
        constraints: Dict[str, Any] = None,
        neutralization: Dict[str, bool] = None,
        rebalance: Dict[str, Any] = None,
        risk_budget: Dict[str, float] = None,
        portfolio_id: str = None
    ) -> str:
        """
        保存组合
        
        Args:
            name: 组合名称
            weights: 组合权重
            description: 描述
            optimization_method: 优化方法
            constraints: 约束条件
            neutralization: 中性化配置
            rebalance: 再平衡配置
            risk_budget: 风险预算
            portfolio_id: 组合ID（更新时提供）
            
        Returns:
            组合ID
        """
        if portfolio_id is None:
            portfolio_id = self._generate_portfolio_id()
        
        metadata = PortfolioMetadata(
            id=portfolio_id,
            name=name,
            description=description,
            optimization_method=optimization_method,
            constraints=constraints or {},
            neutralization=neutralization or {},
            rebalance=rebalance or {},
            risk_budget=risk_budget or {}
        )
        
        portfolio_dir = self._get_portfolio_dir(portfolio_id)
        Path(portfolio_dir).mkdir(parents=True, exist_ok=True)
        
        metadata_path = os.path.join(portfolio_dir, "metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata.to_dict(), f, ensure_ascii=False, indent=2)
        
        weights_path = os.path.join(portfolio_dir, "weights.json")
        with open(weights_path, 'w', encoding='utf-8') as f:
            json.dump(weights, f, ensure_ascii=False, indent=2)
        
        registry = self._load_registry()
        registry[portfolio_id] = metadata.to_dict()
        self._save_registry(registry)
        
        logger.info(f"保存组合: {portfolio_id} - {name}")
        
        return portfolio_id
    
    def load_portfolio(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        """
        加载组合
        
        Args:
            portfolio_id: 组合ID
            
        Returns:
            组合数据
        """
        portfolio_dir = self._get_portfolio_dir(portfolio_id)
        
        if not os.path.exists(portfolio_dir):
            logger.warning(f"组合不存在: {portfolio_id}")
            return None
        
        metadata_path = os.path.join(portfolio_dir, "metadata.json")
        weights_path = os.path.join(portfolio_dir, "weights.json")
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            with open(weights_path, 'r', encoding='utf-8') as f:
                weights = json.load(f)
            
            return {
                'metadata': metadata,
                'weights': weights
            }
        except FileNotFoundError as e:
            logger.error(f"组合文件不存在: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"组合JSON解析错误: {e}")
            return None
    
    def delete_portfolio(self, portfolio_id: str) -> bool:
        """
        删除组合
        
        Args:
            portfolio_id: 组合ID
            
        Returns:
            是否成功
        """
        portfolio_dir = self._get_portfolio_dir(portfolio_id)
        
        if not os.path.exists(portfolio_dir):
            logger.warning(f"组合不存在: {portfolio_id}")
            return False
        
        import shutil
        shutil.rmtree(portfolio_dir)
        
        registry = self._load_registry()
        if portfolio_id in registry:
            del registry[portfolio_id]
            self._save_registry(registry)
        
        logger.info(f"删除组合: {portfolio_id}")
        
        return True
    
    def list_portfolios(self) -> List[Dict[str, Any]]:
        """
        列出所有组合
        
        Returns:
            组合列表
        """
        registry = self._load_registry()
        return list(registry.values())
    
    def save_snapshot(
        self,
        portfolio_id: str,
        date: str,
        weights: Dict[str, float],
        prices: Dict[str, float] = None,
        values: Dict[str, float] = None,
        total_value: float = 0.0,
        returns: Dict[str, float] = None,
        portfolio_return: float = 0.0
    ) -> bool:
        """
        保存组合快照
        
        Args:
            portfolio_id: 组合ID
            date: 日期
            weights: 权重
            prices: 价格
            values: 持仓价值
            total_value: 总价值
            returns: 收益率
            portfolio_return: 组合收益率
            
        Returns:
            是否成功
        """
        portfolio_dir = self._get_portfolio_dir(portfolio_id)
        
        if not os.path.exists(portfolio_dir):
            logger.warning(f"组合不存在: {portfolio_id}")
            return False
        
        snapshots_dir = os.path.join(portfolio_dir, "snapshots")
        Path(snapshots_dir).mkdir(parents=True, exist_ok=True)
        
        snapshot = PortfolioSnapshot(
            portfolio_id=portfolio_id,
            date=date,
            weights=weights,
            prices=prices or {},
            values=values or {},
            total_value=total_value,
            returns=returns or {},
            portfolio_return=portfolio_return
        )
        
        snapshot_path = os.path.join(snapshots_dir, f"{date}.json")
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"保存组合快照: {portfolio_id} - {date}")
        
        return True
    
    def load_snapshots(
        self,
        portfolio_id: str,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        加载组合快照
        
        Args:
            portfolio_id: 组合ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            快照列表
        """
        portfolio_dir = self._get_portfolio_dir(portfolio_id)
        snapshots_dir = os.path.join(portfolio_dir, "snapshots")
        
        if not os.path.exists(snapshots_dir):
            return []
        
        snapshots = []
        for filename in os.listdir(snapshots_dir):
            if not filename.endswith('.json'):
                continue
            
            date = filename[:-5]
            
            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue
            
            snapshot_path = os.path.join(snapshots_dir, filename)
            try:
                with open(snapshot_path, 'r', encoding='utf-8') as f:
                    snapshot_data = json.load(f)
                snapshots.append(snapshot_data)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"加载快照失败: {filename} - {e}")
        
        snapshots.sort(key=lambda x: x['date'])
        
        return snapshots
    
    def update_performance(
        self,
        portfolio_id: str,
        performance: Dict[str, float]
    ) -> bool:
        """
        更新组合绩效
        
        Args:
            portfolio_id: 组合ID
            performance: 绩效数据
            
        Returns:
            是否成功
        """
        portfolio_data = self.load_portfolio(portfolio_id)
        if portfolio_data is None:
            return False
        
        metadata = portfolio_data['metadata']
        metadata['performance'] = performance
        metadata['updated_at'] = datetime.now().isoformat()
        
        portfolio_dir = self._get_portfolio_dir(portfolio_id)
        metadata_path = os.path.join(portfolio_dir, "metadata.json")
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        registry = self._load_registry()
        if portfolio_id in registry:
            registry[portfolio_id] = metadata
            self._save_registry(registry)
        
        logger.info(f"更新组合绩效: {portfolio_id}")
        
        return True
    
    def get_portfolio_history(
        self,
        portfolio_id: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取组合历史
        
        Args:
            portfolio_id: 组合ID
            limit: 限制数量
            
        Returns:
            历史记录列表
        """
        snapshots = self.load_snapshots(portfolio_id)
        
        if limit > 0:
            snapshots = snapshots[-limit:]
        
        return snapshots


__all__ = [
    'PortfolioMetadata',
    'PortfolioSnapshot',
    'PortfolioStorage',
]
