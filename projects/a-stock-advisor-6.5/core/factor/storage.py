"""
因子持久化存储模块

管理因子数据的持久化存储，支持Parquet格式和增量更新。
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import numpy as np

from .registry import FactorMetadata, get_factor_registry
from ..infrastructure.config import get_data_paths
from ..infrastructure.exceptions import FactorException


@dataclass
class StorageResult:
    """存储结果"""
    success: bool
    factor_id: str
    file_path: Optional[str] = None
    rows_stored: int = 0
    error_message: Optional[str] = None


class FactorStorage:
    """
    因子存储管理器
    
    管理因子数据的持久化存储。
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化因子存储
        
        Args:
            storage_path: 存储根路径
        """
        self.storage_path = storage_path or "./data/factors"
        self._registry = get_factor_registry()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保存储目录存在"""
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        
        subdirs = ["data", "metadata", "cache"]
        for subdir in subdirs:
            Path(os.path.join(self.storage_path, subdir)).mkdir(parents=True, exist_ok=True)
    
    def _get_factor_data_path(self, factor_id: str) -> str:
        """获取因子数据文件路径"""
        return os.path.join(self.storage_path, "data", f"{factor_id}.parquet")
    
    def _get_factor_metadata_path(self, factor_id: str) -> str:
        """获取因子元数据文件路径"""
        return os.path.join(self.storage_path, "metadata", f"{factor_id}.json")
    
    def save_factor_data(
        self,
        factor_id: str,
        df: pd.DataFrame,
        compress: str = "zstd"
    ) -> StorageResult:
        """
        保存因子数据
        
        Args:
            factor_id: 因子ID
            df: 因子数据DataFrame
            compress: 压缩算法
            
        Returns:
            StorageResult: 存储结果
        """
        try:
            file_path = self._get_factor_data_path(factor_id)
            
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            df.to_parquet(file_path, index=False, compression=compress)
            
            return StorageResult(
                success=True,
                factor_id=factor_id,
                file_path=file_path,
                rows_stored=len(df)
            )
            
        except Exception as e:
            return StorageResult(
                success=False,
                factor_id=factor_id,
                error_message=str(e)
            )
    
    def load_factor_data(
        self,
        factor_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        stock_codes: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        """
        加载因子数据
        
        Args:
            factor_id: 因子ID
            start_date: 开始日期
            end_date: 结束日期
            stock_codes: 股票代码列表
            
        Returns:
            Optional[pd.DataFrame]: 因子数据
        """
        try:
            file_path = self._get_factor_data_path(factor_id)
            
            if not os.path.exists(file_path):
                return None
            
            df = pd.read_parquet(file_path)
            
            if start_date and 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df[df['date'] >= start_date]
            
            if end_date and 'date' in df.columns:
                df = df[df['date'] <= end_date]
            
            if stock_codes and 'stock_code' in df.columns:
                df = df[df['stock_code'].isin(stock_codes)]
            
            return df
            
        except Exception as e:
            print(f"加载因子数据失败 {factor_id}: {e}")
            return None
    
    def delete_factor_data(self, factor_id: str) -> bool:
        """
        删除因子数据
        
        Args:
            factor_id: 因子ID
            
        Returns:
            bool: 是否成功
        """
        try:
            file_path = self._get_factor_data_path(factor_id)
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            metadata_path = self._get_factor_metadata_path(factor_id)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            
            return True
            
        except Exception as e:
            print(f"删除因子数据失败 {factor_id}: {e}")
            return False
    
    def save_factor_metadata(
        self,
        factor: FactorMetadata
    ) -> StorageResult:
        """
        保存因子元数据
        
        Args:
            factor: 因子元数据
            
        Returns:
            StorageResult: 存储结果
        """
        try:
            file_path = self._get_factor_metadata_path(factor.id)
            
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(factor.to_dict(), f, ensure_ascii=False, indent=2)
            
            return StorageResult(
                success=True,
                factor_id=factor.id,
                file_path=file_path
            )
            
        except Exception as e:
            return StorageResult(
                success=False,
                factor_id=factor.id,
                error_message=str(e)
            )
    
    def load_factor_metadata(self, factor_id: str) -> Optional[FactorMetadata]:
        """
        加载因子元数据
        
        Args:
            factor_id: 因子ID
            
        Returns:
            Optional[FactorMetadata]: 因子元数据
        """
        try:
            file_path = self._get_factor_metadata_path(factor_id)
            
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return FactorMetadata.from_dict(data)
            
        except Exception as e:
            print(f"加载因子元数据失败 {factor_id}: {e}")
            return None
    
    def append_factor_data(
        self,
        factor_id: str,
        new_df: pd.DataFrame,
        date_col: str = "date"
    ) -> StorageResult:
        """
        追加因子数据
        
        Args:
            factor_id: 因子ID
            new_df: 新数据
            date_col: 日期列名
            
        Returns:
            StorageResult: 存储结果
        """
        try:
            existing_df = self.load_factor_data(factor_id)
            
            if existing_df is None:
                return self.save_factor_data(factor_id, new_df)
            
            if date_col in existing_df.columns and date_col in new_df.columns:
                existing_df[date_col] = pd.to_datetime(existing_df[date_col])
                new_df[date_col] = pd.to_datetime(new_df[date_col])
                
                max_existing_date = existing_df[date_col].max()
                new_df = new_df[new_df[date_col] > max_existing_date]
                
                if new_df.empty:
                    return StorageResult(
                        success=True,
                        factor_id=factor_id,
                        rows_stored=0
                    )
            
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            
            return self.save_factor_data(factor_id, combined_df)
            
        except Exception as e:
            return StorageResult(
                success=False,
                factor_id=factor_id,
                error_message=str(e)
            )
    
    def list_stored_factors(self) -> List[str]:
        """
        列出所有已存储的因子
        
        Returns:
            List[str]: 因子ID列表
        """
        data_path = os.path.join(self.storage_path, "data")
        
        if not os.path.exists(data_path):
            return []
        
        factors = []
        for file in Path(data_path).glob("*.parquet"):
            factors.append(file.stem)
        
        return sorted(factors)
    
    def get_storage_info(self, factor_id: str) -> Dict[str, Any]:
        """
        获取因子存储信息
        
        Args:
            factor_id: 因子ID
            
        Returns:
            Dict[str, Any]: 存储信息
        """
        info = {
            "factor_id": factor_id,
            "exists": False
        }
        
        data_path = self._get_factor_data_path(factor_id)
        if os.path.exists(data_path):
            info["exists"] = True
            info["data_path"] = data_path
            info["data_size"] = os.path.getsize(data_path)
            
            try:
                df = pd.read_parquet(data_path)
                info["rows"] = len(df)
                info["columns"] = list(df.columns)
                
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    info["start_date"] = df['date'].min().strftime('%Y-%m-%d')
                    info["end_date"] = df['date'].max().strftime('%Y-%m-%d')
                
                if 'stock_code' in df.columns:
                    info["stock_count"] = df['stock_code'].nunique()
                    
            except Exception as e:
                info["error"] = str(e)
        
        metadata_path = self._get_factor_metadata_path(factor_id)
        if os.path.exists(metadata_path):
            info["metadata_path"] = metadata_path
            info["metadata_size"] = os.path.getsize(metadata_path)
        
        return info
    
    def batch_save(
        self,
        factor_data: Dict[str, pd.DataFrame],
        parallel: bool = False
    ) -> Dict[str, StorageResult]:
        """
        批量保存因子数据
        
        Args:
            factor_data: 因子数据字典
            parallel: 是否并行保存
            
        Returns:
            Dict[str, StorageResult]: 保存结果
        """
        results = {}
        
        if parallel:
            from concurrent.futures import ThreadPoolExecutor
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(self.save_factor_data, fid, df): fid
                    for fid, df in factor_data.items()
                }
                
                for future in futures:
                    fid = futures[future]
                    try:
                        results[fid] = future.result()
                    except Exception as e:
                        results[fid] = StorageResult(
                            success=False,
                            factor_id=fid,
                            error_message=str(e)
                        )
        else:
            for fid, df in factor_data.items():
                results[fid] = self.save_factor_data(fid, df)
        
        return results
    
    def batch_load(
        self,
        factor_ids: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        批量加载因子数据
        
        Args:
            factor_ids: 因子ID列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, pd.DataFrame]: 因子数据字典
        """
        results = {}
        
        for fid in factor_ids:
            df = self.load_factor_data(fid, start_date, end_date)
            if df is not None:
                results[fid] = df
        
        return results
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """
        获取存储统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        factors = self.list_stored_factors()
        
        total_size = 0
        total_rows = 0
        
        for fid in factors:
            info = self.get_storage_info(fid)
            total_size += info.get("data_size", 0)
            total_rows += info.get("rows", 0)
        
        return {
            "total_factors": len(factors),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "total_rows": total_rows,
            "storage_path": self.storage_path
        }
    
    def cleanup_old_data(
        self,
        days_to_keep: int = 365,
        dry_run: bool = True
    ) -> List[str]:
        """
        清理过期数据
        
        Args:
            days_to_keep: 保留天数
            dry_run: 是否仅模拟运行
            
        Returns:
            List[str]: 清理的因子ID列表
        """
        cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=days_to_keep)
        cleaned = []
        
        for fid in self.list_stored_factors():
            info = self.get_storage_info(fid)
            
            if info.get("end_date"):
                end_date = pd.Timestamp(info["end_date"])
                if end_date < cutoff_date:
                    if not dry_run:
                        self.delete_factor_data(fid)
                    cleaned.append(fid)
        
        return cleaned


_default_storage: Optional[FactorStorage] = None


def get_factor_storage(storage_path: Optional[str] = None) -> FactorStorage:
    """获取全局因子存储实例"""
    global _default_storage
    if storage_path is not None or _default_storage is None:
        _default_storage = FactorStorage(storage_path)
    return _default_storage


def reset_factor_storage():
    """重置全局因子存储"""
    global _default_storage
    _default_storage = None
