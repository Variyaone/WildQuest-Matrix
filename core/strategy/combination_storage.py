"""
因子组合结果存储

用于保存和读取因子组合优化的结果
"""

import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from dataclasses import dataclass

from ..infrastructure.logging import get_logger

logger = get_logger("strategy.combination_storage")


@dataclass
class CombinationRecord:
    """因子组合记录"""
    factor_ids: List[str]
    weights: List[float]
    method: str
    config: Dict[str, Any]
    quality_metrics: Optional[Dict[str, float]] = None
    timestamp: Optional[str] = None
    factor_count: int = 0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.factor_count == 0:
            self.factor_count = len(self.factor_ids)


class CombinationResultStorage:
    """因子组合结果存储"""
    
    def __init__(self, storage_dir: str = "data/combination_results"):
        """
        初始化存储
        
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.latest_file = self.storage_dir / "latest_combination.json"
    
    def save(
        self,
        factor_ids: List[str],
        weights: List[float],
        method: str,
        config: Dict[str, Any],
        quality_metrics: Optional[Dict[str, float]] = None
    ) -> bool:
        """
        保存因子组合结果
        
        Args:
            factor_ids: 因子ID列表
            weights: 权重列表
            method: 组合方法
            config: 配置信息
            quality_metrics: 质量指标
            
        Returns:
            是否保存成功
        """
        try:
            result_data = {
                "timestamp": datetime.now().isoformat(),
                "factor_ids": factor_ids,
                "weights": weights,
                "method": method,
                "config": config,
                "quality_metrics": quality_metrics or {},
                "factor_count": len(factor_ids)
            }
            
            with open(self.latest_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"因子组合结果已保存: {len(factor_ids)} 个因子")
            
            return True
            
        except Exception as e:
            logger.error(f"保存因子组合结果失败: {e}")
            return False
    
    def load(self) -> Optional[Dict[str, Any]]:
        """
        读取最新的因子组合结果
        
        Returns:
            因子组合结果，如果不存在则返回None
        """
        try:
            if not self.latest_file.exists():
                logger.warning("没有找到因子组合结果文件")
                return None
            
            with open(self.latest_file, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            
            logger.info(f"读取因子组合结果: {result_data.get('factor_count', 0)} 个因子")
            
            return result_data
            
        except Exception as e:
            logger.error(f"读取因子组合结果失败: {e}")
            return None
    
    def exists(self) -> bool:
        """检查是否存在组合结果"""
        return self.latest_file.exists()
    
    def get_info(self) -> Optional[Dict[str, Any]]:
        """
        获取组合结果的基本信息
        
        Returns:
            基本信息
        """
        result = self.load()
        if not result:
            return None
        
        return {
            "timestamp": result.get("timestamp"),
            "factor_count": result.get("factor_count"),
            "method": result.get("method"),
            "config": result.get("config")
        }


class CombinationStorage(CombinationResultStorage):
    """因子组合存储（兼容旧接口）"""
    
    def save_record(self, record: CombinationRecord) -> bool:
        """
        保存因子组合记录
        
        Args:
            record: 因子组合记录
            
        Returns:
            是否保存成功
        """
        return self.save(
            factor_ids=record.factor_ids,
            weights=record.weights,
            method=record.method,
            config=record.config,
            quality_metrics=record.quality_metrics
        )
    
    def load_record(self) -> Optional[CombinationRecord]:
        """
        读取因子组合记录
        
        Returns:
            因子组合记录，如果不存在则返回None
        """
        data = self.load()
        if not data:
            return None
        
        return CombinationRecord(
            factor_ids=data.get('factor_ids', []),
            weights=data.get('weights', []),
            method=data.get('method', ''),
            config=data.get('config', {}),
            quality_metrics=data.get('quality_metrics'),
            timestamp=data.get('timestamp'),
            factor_count=data.get('factor_count', 0)
        )


_combination_storage = None


def get_combination_storage() -> CombinationStorage:
    """获取因子组合结果存储实例"""
    global _combination_storage
    if _combination_storage is None:
        _combination_storage = CombinationStorage()
    return _combination_storage


def reset_combination_storage():
    """重置因子组合结果存储实例"""
    global _combination_storage
    _combination_storage = None
