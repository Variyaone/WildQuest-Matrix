"""
信号注册表模块

统一管理所有信号的元数据信息，包括编号、名称、描述、生成规则、来源、历史胜率等。
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path
from enum import Enum

from ..infrastructure.exceptions import SignalException


class SignalType(Enum):
    """信号类型"""
    STOCK_SELECTION = "选股信号"
    TIMING = "择时信号"
    RISK_ALERT = "风险预警"
    REBALANCE = "调仓信号"
    CUSTOM = "自定义信号"


class SignalDirection(Enum):
    """信号方向"""
    BUY = "买入"
    SELL = "卖出"
    HOLD = "持有"
    REDUCE = "减仓"
    INCREASE = "加仓"


class SignalStatus(Enum):
    """信号状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    DEPRECATED = "deprecated"


class SignalStrength(Enum):
    """信号强度"""
    STRONG = "强"
    MEDIUM = "中"
    WEAK = "弱"


@dataclass
class SignalPerformance:
    """信号历史表现"""
    win_rate: float = 0.0
    avg_return: float = 0.0
    max_drawdown: float = 0.0
    total_signals: int = 0
    winning_signals: int = 0
    avg_holding_days: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalPerformance":
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class SignalRules:
    """信号生成规则"""
    factors: List[str] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)
    threshold: float = 0.0
    conditions: List[str] = field(default_factory=list)
    combination_method: str = "weighted_sum"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalRules":
        field_names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in field_names})


@dataclass
class SignalMetadata:
    """信号元数据"""
    id: str
    name: str
    description: str
    signal_type: SignalType
    direction: SignalDirection
    rules: SignalRules
    source: str = "自研"
    status: SignalStatus = SignalStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    historical_performance: Optional[SignalPerformance] = None
    score: float = 0.0
    rank: int = 0
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "signal_type": self.signal_type.value,
            "direction": self.direction.value,
            "rules": self.rules.to_dict(),
            "source": self.source,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "historical_performance": self.historical_performance.to_dict() if self.historical_performance else None,
            "score": self.score,
            "rank": self.rank,
            "tags": self.tags,
            "parameters": self.parameters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalMetadata":
        signal_type = SignalType.STOCK_SELECTION
        for st in SignalType:
            if st.value == data.get("signal_type"):
                signal_type = st
                break
        
        direction = SignalDirection.BUY
        for sd in SignalDirection:
            if sd.value == data.get("direction"):
                direction = sd
                break
        
        status = SignalStatus.ACTIVE
        for ss in SignalStatus:
            if ss.value == data.get("status", "active"):
                status = ss
                break
        
        rules = SignalRules.from_dict(data.get("rules", {}))
        
        performance = None
        if data.get("historical_performance"):
            performance = SignalPerformance.from_dict(data["historical_performance"])
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            signal_type=signal_type,
            direction=direction,
            rules=rules,
            source=data.get("source", "自研"),
            status=status,
            created_at=data.get("created_at", datetime.now().strftime("%Y-%m-%d")),
            updated_at=data.get("updated_at", datetime.now().strftime("%Y-%m-%d")),
            historical_performance=performance,
            score=data.get("score", 0.0),
            rank=data.get("rank", 0),
            tags=data.get("tags", []),
            parameters=data.get("parameters", {})
        )


class SignalRegistry:
    """
    信号注册表
    
    统一管理所有信号的元数据信息。
    """
    
    SIGNAL_ID_PREFIX = "S"
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化信号注册表
        
        Args:
            storage_path: 存储路径
        """
        self._signals: Dict[str, SignalMetadata] = {}
        self._next_id: int = 1
        self._storage_path = storage_path or "./data/signals/registry.json"
        
        self._load_registry()
    
    def _load_registry(self):
        """从文件加载注册表"""
        if os.path.exists(self._storage_path):
            try:
                with open(self._storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for signal_id, signal_data in data.get("signals", {}).items():
                    self._signals[signal_id] = SignalMetadata.from_dict(signal_data)
                
                self._next_id = data.get("next_id", 1)
            except Exception as e:
                print(f"加载信号注册表失败: {e}")
    
    def _save_registry(self):
        """保存注册表到文件"""
        try:
            Path(self._storage_path).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "signals": {sid: s.to_dict() for sid, s in self._signals.items()},
                "next_id": self._next_id,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(self._storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存信号注册表失败: {e}")
    
    def _generate_signal_id(self) -> str:
        """生成信号ID"""
        signal_id = f"{self.SIGNAL_ID_PREFIX}{self._next_id:05d}"
        self._next_id += 1
        return signal_id
    
    def register(
        self,
        name: str,
        description: str,
        signal_type: SignalType,
        direction: SignalDirection,
        rules: SignalRules,
        source: str = "自研",
        tags: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> SignalMetadata:
        """
        注册新信号
        
        Args:
            name: 信号名称
            description: 信号描述
            signal_type: 信号类型
            direction: 信号方向
            rules: 生成规则
            source: 信号来源
            tags: 标签列表
            parameters: 参数字典
            
        Returns:
            SignalMetadata: 注册的信号元数据
        """
        signal_id = self._generate_signal_id()
        
        signal = SignalMetadata(
            id=signal_id,
            name=name,
            description=description,
            signal_type=signal_type,
            direction=direction,
            rules=rules,
            source=source,
            tags=tags or [],
            parameters=parameters or {}
        )
        
        self._signals[signal_id] = signal
        self._save_registry()
        
        return signal
    
    def get(self, signal_id: str) -> Optional[SignalMetadata]:
        """获取信号"""
        return self._signals.get(signal_id)
    
    def get_by_name(self, name: str) -> Optional[SignalMetadata]:
        """根据名称获取信号"""
        for signal in self._signals.values():
            if signal.name == name:
                return signal
        return None
    
    def update(
        self, 
        signal_id: str, 
        **kwargs
    ) -> Optional[SignalMetadata]:
        """更新信号信息"""
        signal = self._signals.get(signal_id)
        if signal is None:
            return None
        
        for key, value in kwargs.items():
            if hasattr(signal, key):
                setattr(signal, key, value)
        
        signal.updated_at = datetime.now().strftime("%Y-%m-%d")
        self._save_registry()
        
        return signal
    
    def update_performance(
        self, 
        signal_id: str, 
        performance: SignalPerformance
    ) -> Optional[SignalMetadata]:
        """更新信号历史表现"""
        return self.update(signal_id, historical_performance=performance)
    
    def update_score(self, signal_id: str, score: float, rank: int = 0) -> Optional[SignalMetadata]:
        """更新信号评分和排名"""
        return self.update(signal_id, score=score, rank=rank)
    
    def delete(self, signal_id: str) -> bool:
        """删除信号"""
        if signal_id in self._signals:
            del self._signals[signal_id]
            self._save_registry()
            return True
        return False
    
    def set_status(self, signal_id: str, status: SignalStatus) -> Optional[SignalMetadata]:
        """设置信号状态"""
        return self.update(signal_id, status=status)
    
    def list_all(self) -> List[SignalMetadata]:
        """获取所有信号"""
        return list(self._signals.values())
    
    def list_by_type(self, signal_type: SignalType) -> List[SignalMetadata]:
        """按类型获取信号"""
        return [s for s in self._signals.values() if s.signal_type == signal_type]
    
    def list_by_direction(self, direction: SignalDirection) -> List[SignalMetadata]:
        """按方向获取信号"""
        return [s for s in self._signals.values() if s.direction == direction]
    
    def list_by_status(self, status: SignalStatus) -> List[SignalMetadata]:
        """按状态获取信号"""
        return [s for s in self._signals.values() if s.status == status]
    
    def list_by_tags(self, tags: List[str], match_all: bool = False) -> List[SignalMetadata]:
        """按标签获取信号"""
        result = []
        for signal in self._signals.values():
            if match_all:
                if all(tag in signal.tags for tag in tags):
                    result.append(signal)
            else:
                if any(tag in signal.tags for tag in tags):
                    result.append(signal)
        return result
    
    def search(self, keyword: str) -> List[SignalMetadata]:
        """搜索信号"""
        keyword = keyword.lower()
        result = []
        for signal in self._signals.values():
            if (keyword in signal.name.lower() or 
                keyword in signal.description.lower() or
                any(keyword in tag.lower() for tag in signal.tags)):
                result.append(signal)
        return result
    
    def get_top_signals(self, n: int = 10) -> List[SignalMetadata]:
        """获取排名前N的信号"""
        signals = list(self._signals.values())
        signals.sort(key=lambda s: s.score, reverse=True)
        return signals[:n]
    
    def get_signal_count(self) -> int:
        """获取信号总数"""
        return len(self._signals)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_count": len(self._signals),
            "by_type": {},
            "by_direction": {},
            "by_status": {},
            "avg_score": 0.0,
            "avg_win_rate": 0.0
        }
        
        total_score = 0.0
        total_win_rate = 0.0
        win_rate_count = 0
        
        for signal in self._signals.values():
            type_name = signal.signal_type.value
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1
            
            direction_name = signal.direction.value
            stats["by_direction"][direction_name] = stats["by_direction"].get(direction_name, 0) + 1
            
            status_name = signal.status.value
            stats["by_status"][status_name] = stats["by_status"].get(status_name, 0) + 1
            
            total_score += signal.score
            
            if signal.historical_performance:
                total_win_rate += signal.historical_performance.win_rate
                win_rate_count += 1
        
        if self._signals:
            stats["avg_score"] = total_score / len(self._signals)
        
        if win_rate_count > 0:
            stats["avg_win_rate"] = total_win_rate / win_rate_count
        
        return stats
    
    def export_to_json(self, file_path: str):
        """导出注册表到JSON文件"""
        data = {
            "signals": {sid: s.to_dict() for sid, s in self._signals.items()},
            "statistics": self.get_statistics()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


_default_registry: Optional[SignalRegistry] = None


def get_signal_registry(storage_path: Optional[str] = None) -> SignalRegistry:
    """获取全局信号注册表实例"""
    global _default_registry
    if storage_path is not None or _default_registry is None:
        _default_registry = SignalRegistry(storage_path)
    return _default_registry


def reset_signal_registry():
    """重置全局信号注册表"""
    global _default_registry
    _default_registry = None
