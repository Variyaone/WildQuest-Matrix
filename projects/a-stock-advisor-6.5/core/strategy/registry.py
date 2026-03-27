"""
策略注册表模块

统一管理所有策略的元数据信息，包括编号、名称、描述、类型、信号组合规则、持仓策略、风控参数等。
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from ..infrastructure.exceptions import StrategyException


class StrategyType(Enum):
    """策略类型"""
    STOCK_SELECTION = "选股策略"
    TIMING = "择时策略"
    ARBITRAGE = "套利策略"
    TREND_FOLLOWING = "趋势跟踪"
    MEAN_REVERSION = "均值回归"
    MULTI_FACTOR = "多因子策略"
    CUSTOM = "自定义策略"


class StrategyStatus(Enum):
    """策略状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    DEPRECATED = "deprecated"


class RebalanceFrequency(Enum):
    """调仓频率"""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass
class RiskParams:
    """风控参数"""
    max_single_weight: float = 0.1
    max_industry_weight: float = 0.3
    stop_loss: float = -0.1
    take_profit: float = 0.2
    max_drawdown: float = -0.15
    position_limit: float = 0.95
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "RiskParams":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class StrategyPerformance:
    """策略表现"""
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    profit_factor: float = 0.0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0
    information_ratio: float = 0.0
    beta: float = 1.0
    alpha: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyPerformance":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class SignalConfig:
    """信号配置"""
    signal_ids: List[str] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)
    combination_method: str = "weighted_sum"
    min_signal_strength: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalConfig":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class StrategyMetadata:
    """策略元数据"""
    id: str
    name: str
    description: str
    strategy_type: StrategyType
    signals: SignalConfig
    rebalance_freq: RebalanceFrequency
    max_positions: int
    risk_params: RiskParams
    source: str = "自研"
    status: StrategyStatus = StrategyStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    backtest_performance: Optional[StrategyPerformance] = None
    live_performance: Optional[StrategyPerformance] = None
    score: float = 0.0
    rank: int = 0
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    benchmark: str = "000300.SH"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "strategy_type": self.strategy_type.value,
            "signals": self.signals.to_dict(),
            "rebalance_freq": self.rebalance_freq.value,
            "max_positions": self.max_positions,
            "risk_params": self.risk_params.to_dict(),
            "source": self.source,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "backtest_performance": self.backtest_performance.to_dict() if self.backtest_performance else None,
            "live_performance": self.live_performance.to_dict() if self.live_performance else None,
            "score": self.score,
            "rank": self.rank,
            "tags": self.tags,
            "parameters": self.parameters,
            "benchmark": self.benchmark
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyMetadata":
        strategy_type = StrategyType.STOCK_SELECTION
        for st in StrategyType:
            if st.value == data.get("strategy_type"):
                strategy_type = st
                break
        
        status = StrategyStatus.ACTIVE
        for ss in StrategyStatus:
            if ss.value == data.get("status", "active"):
                status = ss
                break
        
        rebalance_freq = RebalanceFrequency.WEEKLY
        for rf in RebalanceFrequency:
            if rf.value == data.get("rebalance_freq"):
                rebalance_freq = rf
                break
        
        signals = SignalConfig.from_dict(data.get("signals", {}))
        risk_params = RiskParams.from_dict(data.get("risk_params", {}))
        
        backtest_perf = None
        if data.get("backtest_performance"):
            backtest_perf = StrategyPerformance.from_dict(data["backtest_performance"])
        
        live_perf = None
        if data.get("live_performance"):
            live_perf = StrategyPerformance.from_dict(data["live_performance"])
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            strategy_type=strategy_type,
            signals=signals,
            rebalance_freq=rebalance_freq,
            max_positions=data.get("max_positions", 20),
            risk_params=risk_params,
            source=data.get("source", "自研"),
            status=status,
            created_at=data.get("created_at", datetime.now().strftime("%Y-%m-%d")),
            updated_at=data.get("updated_at", datetime.now().strftime("%Y-%m-%d")),
            backtest_performance=backtest_perf,
            live_performance=live_perf,
            score=data.get("score", 0.0),
            rank=data.get("rank", 0),
            tags=data.get("tags", []),
            parameters=data.get("parameters", {}),
            benchmark=data.get("benchmark", "000300.SH")
        )


class StrategyRegistry:
    """
    策略注册表
    
    统一管理所有策略的元数据信息。
    """
    
    STRATEGY_ID_PREFIX = "ST"
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化策略注册表
        
        Args:
            storage_path: 存储路径
        """
        self._strategies: Dict[str, StrategyMetadata] = {}
        self._next_id: int = 1
        self._storage_path = storage_path or "./data/strategies/registry.json"
        
        self._load_registry()
    
    def _load_registry(self):
        """从文件加载注册表"""
        if os.path.exists(self._storage_path):
            try:
                with open(self._storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for strategy_id, strategy_data in data.get("strategies", {}).items():
                    self._strategies[strategy_id] = StrategyMetadata.from_dict(strategy_data)
                
                self._next_id = data.get("next_id", 1)
            except Exception as e:
                print(f"加载策略注册表失败: {e}")
    
    def _save_registry(self):
        """保存注册表到文件"""
        try:
            Path(self._storage_path).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "strategies": {sid: s.to_dict() for sid, s in self._strategies.items()},
                "next_id": self._next_id,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(self._storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存策略注册表失败: {e}")
    
    def _generate_strategy_id(self) -> str:
        """生成策略ID"""
        strategy_id = f"{self.STRATEGY_ID_PREFIX}{self._next_id:05d}"
        self._next_id += 1
        return strategy_id
    
    def register(
        self,
        name: str,
        description: str,
        strategy_type: StrategyType,
        signals: SignalConfig,
        rebalance_freq: RebalanceFrequency,
        max_positions: int,
        risk_params: RiskParams,
        source: str = "自研",
        tags: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        benchmark: str = "000300.SH"
    ) -> StrategyMetadata:
        """注册新策略"""
        strategy_id = self._generate_strategy_id()
        
        strategy = StrategyMetadata(
            id=strategy_id,
            name=name,
            description=description,
            strategy_type=strategy_type,
            signals=signals,
            rebalance_freq=rebalance_freq,
            max_positions=max_positions,
            risk_params=risk_params,
            source=source,
            tags=tags or [],
            parameters=parameters or {},
            benchmark=benchmark
        )
        
        self._strategies[strategy_id] = strategy
        self._save_registry()
        
        return strategy
    
    def get(self, strategy_id: str) -> Optional[StrategyMetadata]:
        """获取策略"""
        return self._strategies.get(strategy_id)
    
    def get_by_name(self, name: str) -> Optional[StrategyMetadata]:
        """根据名称获取策略"""
        for strategy in self._strategies.values():
            if strategy.name == name:
                return strategy
        return None
    
    def update(
        self, 
        strategy_id: str, 
        **kwargs
    ) -> Optional[StrategyMetadata]:
        """更新策略信息"""
        strategy = self._strategies.get(strategy_id)
        if strategy is None:
            return None
        
        for key, value in kwargs.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)
        
        strategy.updated_at = datetime.now().strftime("%Y-%m-%d")
        self._save_registry()
        
        return strategy
    
    def update_backtest_performance(
        self, 
        strategy_id: str, 
        performance: StrategyPerformance
    ) -> Optional[StrategyMetadata]:
        """更新回测表现"""
        return self.update(strategy_id, backtest_performance=performance)
    
    def update_live_performance(
        self, 
        strategy_id: str, 
        performance: StrategyPerformance
    ) -> Optional[StrategyMetadata]:
        """更新实盘表现"""
        return self.update(strategy_id, live_performance=performance)
    
    def update_score(self, strategy_id: str, score: float, rank: int = 0) -> Optional[StrategyMetadata]:
        """更新评分和排名"""
        return self.update(strategy_id, score=score, rank=rank)
    
    def delete(self, strategy_id: str) -> bool:
        """删除策略"""
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            self._save_registry()
            return True
        return False
    
    def set_status(self, strategy_id: str, status: StrategyStatus) -> Optional[StrategyMetadata]:
        """设置策略状态"""
        return self.update(strategy_id, status=status)
    
    def list_all(self) -> List[StrategyMetadata]:
        """获取所有策略"""
        return list(self._strategies.values())
    
    def list_by_type(self, strategy_type: StrategyType) -> List[StrategyMetadata]:
        """按类型获取策略"""
        return [s for s in self._strategies.values() if s.strategy_type == strategy_type]
    
    def list_by_status(self, status: StrategyStatus) -> List[StrategyMetadata]:
        """按状态获取策略"""
        return [s for s in self._strategies.values() if s.status == status]
    
    def list_by_tags(self, tags: List[str], match_all: bool = False) -> List[StrategyMetadata]:
        """按标签获取策略"""
        result = []
        for strategy in self._strategies.values():
            if match_all:
                if all(tag in strategy.tags for tag in tags):
                    result.append(strategy)
            else:
                if any(tag in strategy.tags for tag in tags):
                    result.append(strategy)
        return result
    
    def search(self, keyword: str) -> List[StrategyMetadata]:
        """搜索策略"""
        keyword = keyword.lower()
        result = []
        for strategy in self._strategies.values():
            if (keyword in strategy.name.lower() or 
                keyword in strategy.description.lower() or
                any(keyword in tag.lower() for tag in strategy.tags)):
                result.append(strategy)
        return result
    
    def get_top_strategies(self, n: int = 10) -> List[StrategyMetadata]:
        """获取排名前N的策略"""
        strategies = list(self._strategies.values())
        strategies.sort(key=lambda s: s.score, reverse=True)
        return strategies[:n]
    
    def get_strategy_count(self) -> int:
        """获取策略总数"""
        return len(self._strategies)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_count": len(self._strategies),
            "by_type": {},
            "by_status": {},
            "avg_score": 0.0,
            "avg_sharpe": 0.0
        }
        
        total_score = 0.0
        total_sharpe = 0.0
        sharpe_count = 0
        
        for strategy in self._strategies.values():
            type_name = strategy.strategy_type.value
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1
            
            status_name = strategy.status.value
            stats["by_status"][status_name] = stats["by_status"].get(status_name, 0) + 1
            
            total_score += strategy.score
            
            if strategy.backtest_performance:
                total_sharpe += strategy.backtest_performance.sharpe_ratio
                sharpe_count += 1
        
        if self._strategies:
            stats["avg_score"] = total_score / len(self._strategies)
        
        if sharpe_count > 0:
            stats["avg_sharpe"] = total_sharpe / sharpe_count
        
        return stats
    
    def export_to_json(self, file_path: str):
        """导出注册表到JSON文件"""
        data = {
            "strategies": {sid: s.to_dict() for sid, s in self._strategies.items()},
            "statistics": self.get_statistics()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


_default_registry: Optional[StrategyRegistry] = None


def get_strategy_registry(storage_path: Optional[str] = None) -> StrategyRegistry:
    """获取全局策略注册表实例"""
    global _default_registry
    if storage_path is not None or _default_registry is None:
        _default_registry = StrategyRegistry(storage_path)
    return _default_registry


def reset_strategy_registry():
    """重置全局策略注册表"""
    global _default_registry
    _default_registry = None
