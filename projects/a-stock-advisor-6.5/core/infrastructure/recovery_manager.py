"""
操作恢复管理器

记录所有关键操作，支持回滚和恢复。
每个操作都有完整的审计追溯，可以恢复到任意历史状态。

关键功能：
1. 操作记录：记录所有关键操作及其前后状态
2. 状态回滚：回滚到指定的历史状态
3. 因子恢复：恢复被标记为INACTIVE的因子
4. 审计追溯：查看所有操作历史

作者: 陈默 (WildQuest Capital)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import shutil


class OperationType(Enum):
    """操作类型"""
    FACTOR_REGISTER = "factor_register"
    FACTOR_UPDATE = "factor_update"
    FACTOR_DEACTIVATE = "factor_deactivate"
    FACTOR_REACTIVATE = "factor_reactivate"
    ALPHA_GENERATE = "alpha_generate"
    STRATEGY_CREATE = "strategy_create"
    STRATEGY_UPDATE = "strategy_update"
    BACKTEST_RUN = "backtest_run"
    OVERRIDE_GATE = "override_gate"


class OperationStatus(Enum):
    """操作状态"""
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PENDING = "pending"


@dataclass
class OperationRecord:
    """操作记录"""
    operation_id: str
    operation_type: OperationType
    timestamp: datetime
    status: OperationStatus
    
    description: str
    operator: str
    
    before_state: Dict[str, Any] = field(default_factory=dict)
    after_state: Dict[str, Any] = field(default_factory=dict)
    
    related_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    override_reason: Optional[str] = None
    rolled_back_at: Optional[datetime] = None
    rolled_back_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "description": self.description,
            "operator": self.operator,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "related_ids": self.related_ids,
            "metadata": self.metadata,
            "override_reason": self.override_reason,
            "rolled_back_at": self.rolled_back_at.isoformat() if self.rolled_back_at else None,
            "rolled_back_by": self.rolled_back_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperationRecord":
        """从字典创建"""
        return cls(
            operation_id=data["operation_id"],
            operation_type=OperationType(data["operation_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            status=OperationStatus(data["status"]),
            description=data["description"],
            operator=data["operator"],
            before_state=data.get("before_state", {}),
            after_state=data.get("after_state", {}),
            related_ids=data.get("related_ids", []),
            metadata=data.get("metadata", {}),
            override_reason=data.get("override_reason"),
            rolled_back_at=datetime.fromisoformat(data["rolled_back_at"]) if data.get("rolled_back_at") else None,
            rolled_back_by=data.get("rolled_back_by")
        )


class RecoveryManager:
    """
    操作恢复管理器
    
    记录所有关键操作，支持回滚和恢复。
    """
    
    def __init__(self, storage_path: str = "./data/recovery"):
        """初始化恢复管理器"""
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        
        self._operations_file = self._storage_path / "operations.json"
        self._snapshots_dir = self._storage_path / "snapshots"
        self._snapshots_dir.mkdir(exist_ok=True)
        
        self._operations: List[OperationRecord] = []
        self._load_operations()
    
    def _load_operations(self):
        """加载操作记录"""
        if self._operations_file.exists():
            try:
                with open(self._operations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._operations = [
                        OperationRecord.from_dict(op) 
                        for op in data.get("operations", [])
                    ]
            except Exception as e:
                print(f"加载操作记录失败: {e}")
    
    def _save_operations(self):
        """保存操作记录"""
        try:
            data = {
                "operations": [op.to_dict() for op in self._operations],
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self._operations_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存操作记录失败: {e}")
    
    def _generate_operation_id(self) -> str:
        """生成操作ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"OP_{timestamp}_{len(self._operations):06d}"
    
    def record_operation(
        self,
        operation_type: OperationType,
        description: str,
        operator: str,
        before_state: Dict[str, Any] = None,
        after_state: Dict[str, Any] = None,
        related_ids: List[str] = None,
        metadata: Dict[str, Any] = None,
        override_reason: Optional[str] = None
    ) -> str:
        """
        记录操作
        
        Args:
            operation_type: 操作类型
            description: 操作描述
            operator: 操作人
            before_state: 操作前状态
            after_state: 操作后状态
            related_ids: 相关ID列表
            metadata: 元数据
            override_reason: 强制继续原因
            
        Returns:
            str: 操作ID
        """
        operation_id = self._generate_operation_id()
        
        record = OperationRecord(
            operation_id=operation_id,
            operation_type=operation_type,
            timestamp=datetime.now(),
            status=OperationStatus.SUCCESS,
            description=description,
            operator=operator,
            before_state=before_state or {},
            after_state=after_state or {},
            related_ids=related_ids or [],
            metadata=metadata or {},
            override_reason=override_reason
        )
        
        self._operations.append(record)
        self._save_operations()
        
        return operation_id
    
    def rollback_operation(
        self,
        operation_id: str,
        rolled_back_by: str = "system"
    ) -> bool:
        """
        回滚操作
        
        Args:
            operation_id: 操作ID
            rolled_back_by: 回滚操作人
            
        Returns:
            bool: 是否成功
        """
        operation = self._find_operation(operation_id)
        
        if not operation:
            print(f"操作不存在: {operation_id}")
            return False
        
        if operation.status == OperationStatus.ROLLED_BACK:
            print(f"操作已回滚: {operation_id}")
            return False
        
        try:
            if operation.operation_type == OperationType.FACTOR_DEACTIVATE:
                self._rollback_factor_deactivate(operation)
            elif operation.operation_type == OperationType.FACTOR_REACTIVATE:
                self._rollback_factor_reactivate(operation)
            elif operation.operation_type == OperationType.STRATEGY_CREATE:
                self._rollback_strategy_create(operation)
            else:
                print(f"不支持回滚的操作类型: {operation.operation_type}")
                return False
            
            operation.status = OperationStatus.ROLLED_BACK
            operation.rolled_back_at = datetime.now()
            operation.rolled_back_by = rolled_back_by
            
            self._save_operations()
            
            print(f"✓ 操作已回滚: {operation_id}")
            return True
            
        except Exception as e:
            print(f"回滚操作失败: {e}")
            return False
    
    def _rollback_factor_deactivate(self, operation: OperationRecord):
        """回滚因子停用操作"""
        from ..factor import get_factor_registry
        
        registry = get_factor_registry()
        
        for factor_id in operation.related_ids:
            before_state = operation.before_state.get(factor_id, {})
            
            if before_state.get("status") == "active":
                from ..factor.registry import FactorStatus
                registry.update(factor_id, status=FactorStatus.ACTIVE)
                print(f"  ✓ 因子 {factor_id} 已恢复为ACTIVE")
    
    def _rollback_factor_reactivate(self, operation: OperationRecord):
        """回滚因子重新激活操作"""
        from ..factor import get_factor_registry
        
        registry = get_factor_registry()
        
        for factor_id in operation.related_ids:
            before_state = operation.before_state.get(factor_id, {})
            
            if before_state.get("status") == "inactive":
                from ..factor.registry import FactorStatus
                registry.update(factor_id, status=FactorStatus.INACTIVE)
                print(f"  ✓ 因子 {factor_id} 已恢复为INACTIVE")
    
    def _rollback_strategy_create(self, operation: OperationRecord):
        """回滚策略创建操作"""
        from ..strategy import get_strategy_registry
        
        registry = get_strategy_registry()
        
        for strategy_id in operation.related_ids:
            registry.delete(strategy_id)
            print(f"  ✓ 策略 {strategy_id} 已删除")
    
    def reactivate_factor(
        self,
        factor_id: str,
        reason: str,
        operator: str = "system"
    ) -> bool:
        """
        重新激活因子
        
        Args:
            factor_id: 因子ID
            reason: 激活原因
            operator: 操作人
            
        Returns:
            bool: 是否成功
        """
        from ..factor import get_factor_registry
        from ..factor.registry import FactorStatus
        
        registry = get_factor_registry()
        factor = registry.get(factor_id)
        
        if not factor:
            print(f"因子不存在: {factor_id}")
            return False
        
        if factor.status == FactorStatus.ACTIVE:
            print(f"因子已是ACTIVE状态: {factor_id}")
            return False
        
        before_state = {
            "status": factor.status.value,
            "quality_metrics": factor.quality_metrics.to_dict() if factor.quality_metrics else None
        }
        
        registry.update(factor_id, status=FactorStatus.ACTIVE)
        
        after_state = {
            "status": "active"
        }
        
        self.record_operation(
            operation_type=OperationType.FACTOR_REACTIVATE,
            description=f"重新激活因子 {factor_id}",
            operator=operator,
            before_state={factor_id: before_state},
            after_state={factor_id: after_state},
            related_ids=[factor_id],
            metadata={"reason": reason}
        )
        
        print(f"✓ 因子 {factor_id} 已重新激活")
        print(f"  原因: {reason}")
        print(f"  操作人: {operator}")
        
        return True
    
    def _find_operation(self, operation_id: str) -> Optional[OperationRecord]:
        """查找操作记录"""
        for op in self._operations:
            if op.operation_id == operation_id:
                return op
        return None
    
    def get_operation_history(
        self,
        operation_type: Optional[OperationType] = None,
        limit: int = 50
    ) -> List[OperationRecord]:
        """
        获取操作历史
        
        Args:
            operation_type: 操作类型（可选）
            limit: 返回数量限制
            
        Returns:
            List[OperationRecord]: 操作记录列表
        """
        operations = self._operations
        
        if operation_type:
            operations = [op for op in operations if op.operation_type == operation_type]
        
        return operations[-limit:]
    
    def get_factor_operations(self, factor_id: str) -> List[OperationRecord]:
        """获取因子相关的所有操作"""
        return [
            op for op in self._operations 
            if factor_id in op.related_ids
        ]
    
    def get_strategy_operations(self, strategy_id: str) -> List[OperationRecord]:
        """获取策略相关的所有操作"""
        return [
            op for op in self._operations 
            if strategy_id in op.related_ids
        ]
    
    def create_snapshot(self, name: str) -> str:
        """
        创建系统快照
        
        Args:
            name: 快照名称
            
        Returns:
            str: 快照ID
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        snapshot_id = f"SNAPSHOT_{timestamp}_{name}"
        
        snapshot_dir = self._snapshots_dir / snapshot_id
        snapshot_dir.mkdir(exist_ok=True)
        
        try:
            factor_registry_path = Path("./data/factors/registry.json")
            if factor_registry_path.exists():
                shutil.copy(factor_registry_path, snapshot_dir / "factor_registry.json")
            
            strategy_registry_path = Path("./data/strategies/registry.json")
            if strategy_registry_path.exists():
                shutil.copy(strategy_registry_path, snapshot_dir / "strategy_registry.json")
            
            alpha_predictions_dir = Path("./data/alpha_predictions")
            if alpha_predictions_dir.exists():
                shutil.copytree(
                    alpha_predictions_dir, 
                    snapshot_dir / "alpha_predictions",
                    dirs_exist_ok=True
                )
            
            snapshot_info = {
                "snapshot_id": snapshot_id,
                "name": name,
                "created_at": datetime.now().isoformat(),
                "created_by": "system"
            }
            
            with open(snapshot_dir / "snapshot_info.json", 'w', encoding='utf-8') as f:
                json.dump(snapshot_info, f, indent=2, ensure_ascii=False)
            
            print(f"✓ 快照已创建: {snapshot_id}")
            return snapshot_id
            
        except Exception as e:
            print(f"创建快照失败: {e}")
            return ""
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """列出所有快照"""
        snapshots = []
        
        for snapshot_dir in self._snapshots_dir.iterdir():
            if snapshot_dir.is_dir():
                info_file = snapshot_dir / "snapshot_info.json"
                if info_file.exists():
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            snapshots.append(json.load(f))
                    except:
                        pass
        
        return sorted(snapshots, key=lambda x: x["created_at"], reverse=True)


def get_recovery_manager() -> RecoveryManager:
    """获取恢复管理器实例"""
    return RecoveryManager()
