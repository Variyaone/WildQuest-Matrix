"""
信号持久化存储模块

管理信号数据的持久化存储。
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import numpy as np

from .registry import SignalMetadata, get_signal_registry
from .generator import GeneratedSignal
from ..infrastructure.exceptions import SignalException


@dataclass
class SignalStorageResult:
    """信号存储结果"""
    success: bool
    signal_id: str
    file_path: Optional[str] = None
    rows_stored: int = 0
    error_message: Optional[str] = None


class SignalStorage:
    """
    信号存储管理器
    
    管理信号数据的持久化存储。
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化信号存储
        
        Args:
            storage_path: 存储根路径
        """
        self.storage_path = storage_path or "./data/signals"
        self._registry = get_signal_registry()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保存储目录存在"""
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        
        subdirs = ["history", "daily", "metadata"]
        for subdir in subdirs:
            Path(os.path.join(self.storage_path, subdir)).mkdir(parents=True, exist_ok=True)
    
    def _get_signal_history_path(self, signal_id: str) -> str:
        """获取信号历史数据文件路径"""
        return os.path.join(self.storage_path, "history", f"{signal_id}.parquet")
    
    def _get_daily_signal_path(self, date: str) -> str:
        """获取每日信号文件路径"""
        return os.path.join(self.storage_path, "daily", f"{date}.parquet")
    
    def _get_signal_metadata_path(self, signal_id: str) -> str:
        """获取信号元数据文件路径"""
        return os.path.join(self.storage_path, "metadata", f"{signal_id}.json")
    
    def save_signals(
        self,
        signals: List[GeneratedSignal],
        compress: str = "zstd"
    ) -> SignalStorageResult:
        """
        保存信号列表
        
        Args:
            signals: 信号列表
            compress: 压缩算法
            
        Returns:
            SignalStorageResult: 存储结果
        """
        if not signals:
            return SignalStorageResult(
                success=False,
                signal_id="",
                error_message="信号列表为空"
            )
        
        try:
            signal_id = signals[0].signal_id
            
            df = pd.DataFrame([s.to_dict() for s in signals])
            
            file_path = self._get_signal_history_path(signal_id)
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            df.to_parquet(file_path, index=False, compression=compress)
            
            return SignalStorageResult(
                success=True,
                signal_id=signal_id,
                file_path=file_path,
                rows_stored=len(signals)
            )
            
        except Exception as e:
            return SignalStorageResult(
                success=False,
                signal_id=signals[0].signal_id if signals else "",
                error_message=str(e)
            )
    
    def save_daily_signals(
        self,
        date: str,
        signals: List[GeneratedSignal],
        compress: str = "zstd"
    ) -> SignalStorageResult:
        """
        保存每日信号
        
        Args:
            date: 日期
            signals: 信号列表
            compress: 压缩算法
            
        Returns:
            SignalStorageResult: 存储结果
        """
        try:
            df = pd.DataFrame([s.to_dict() for s in signals])
            
            file_path = self._get_daily_signal_path(date)
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            df.to_parquet(file_path, index=False, compression=compress)
            
            return SignalStorageResult(
                success=True,
                signal_id=f"daily_{date}",
                file_path=file_path,
                rows_stored=len(signals)
            )
            
        except Exception as e:
            return SignalStorageResult(
                success=False,
                signal_id=f"daily_{date}",
                error_message=str(e)
            )
    
    def load_signal_history(
        self,
        signal_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        加载信号历史数据
        
        Args:
            signal_id: 信号ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Optional[pd.DataFrame]: 信号数据
        """
        try:
            file_path = self._get_signal_history_path(signal_id)
            
            if not os.path.exists(file_path):
                return None
            
            df = pd.read_parquet(file_path)
            
            if start_date:
                df = df[df['date'] >= start_date]
            
            if end_date:
                df = df[df['date'] <= end_date]
            
            return df
            
        except Exception as e:
            print(f"加载信号历史数据失败 {signal_id}: {e}")
            return None
    
    def load_daily_signals(self, date: str) -> Optional[pd.DataFrame]:
        """
        加载每日信号
        
        Args:
            date: 日期
            
        Returns:
            Optional[pd.DataFrame]: 信号数据
        """
        try:
            file_path = self._get_daily_signal_path(date)
            
            if not os.path.exists(file_path):
                return None
            
            return pd.read_parquet(file_path)
            
        except Exception as e:
            print(f"加载每日信号失败 {date}: {e}")
            return None
    
    def append_signals(
        self,
        signal_id: str,
        new_signals: List[GeneratedSignal]
    ) -> SignalStorageResult:
        """
        追加信号数据
        
        Args:
            signal_id: 信号ID
            new_signals: 新信号列表
            
        Returns:
            SignalStorageResult: 存储结果
        """
        try:
            existing_df = self.load_signal_history(signal_id)
            
            new_df = pd.DataFrame([s.to_dict() for s in new_signals])
            
            if existing_df is not None:
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                
                combined_df = combined_df.drop_duplicates(
                    subset=['date', 'stock_code', 'signal_id'],
                    keep='last'
                )
            else:
                combined_df = new_df
            
            file_path = self._get_signal_history_path(signal_id)
            combined_df.to_parquet(file_path, index=False, compression='zstd')
            
            return SignalStorageResult(
                success=True,
                signal_id=signal_id,
                file_path=file_path,
                rows_stored=len(combined_df)
            )
            
        except Exception as e:
            return SignalStorageResult(
                success=False,
                signal_id=signal_id,
                error_message=str(e)
            )
    
    def delete_signal_history(self, signal_id: str) -> bool:
        """
        删除信号历史数据
        
        Args:
            signal_id: 信号ID
            
        Returns:
            bool: 是否成功
        """
        try:
            file_path = self._get_signal_history_path(signal_id)
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return True
            
        except Exception as e:
            print(f"删除信号历史数据失败 {signal_id}: {e}")
            return False
    
    def list_signal_ids(self) -> List[str]:
        """
        列出所有已存储的信号ID
        
        Returns:
            List[str]: 信号ID列表
        """
        history_path = os.path.join(self.storage_path, "history")
        
        if not os.path.exists(history_path):
            return []
        
        signal_ids = []
        for file in Path(history_path).glob("*.parquet"):
            signal_ids.append(file.stem)
        
        return sorted(signal_ids)
    
    def list_daily_dates(self) -> List[str]:
        """
        列出所有已存储的每日信号日期
        
        Returns:
            List[str]: 日期列表
        """
        daily_path = os.path.join(self.storage_path, "daily")
        
        if not os.path.exists(daily_path):
            return []
        
        dates = []
        for file in Path(daily_path).glob("*.parquet"):
            dates.append(file.stem)
        
        return sorted(dates)
    
    def get_signal_statistics(self, signal_id: str) -> Dict[str, Any]:
        """
        获取信号统计信息
        
        Args:
            signal_id: 信号ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        df = self.load_signal_history(signal_id)
        
        if df is None or df.empty:
            return {"exists": False}
        
        return {
            "exists": True,
            "signal_id": signal_id,
            "total_signals": len(df),
            "unique_dates": df['date'].nunique(),
            "unique_stocks": df['stock_code'].nunique(),
            "date_range": {
                "start": df['date'].min(),
                "end": df['date'].max()
            },
            "strength_distribution": df['strength'].value_counts().to_dict() if 'strength' in df.columns else {}
        }
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        获取存储信息
        
        Returns:
            Dict[str, Any]: 存储信息
        """
        signal_ids = self.list_signal_ids()
        daily_dates = self.list_daily_dates()
        
        total_size = 0
        history_path = os.path.join(self.storage_path, "history")
        if os.path.exists(history_path):
            for file in Path(history_path).glob("*.parquet"):
                total_size += os.path.getsize(file)
        
        daily_path = os.path.join(self.storage_path, "daily")
        if os.path.exists(daily_path):
            for file in Path(daily_path).glob("*.parquet"):
                total_size += os.path.getsize(file)
        
        return {
            "storage_path": self.storage_path,
            "total_signals": len(signal_ids),
            "total_daily_files": len(daily_dates),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024)
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
            List[str]: 清理的文件列表
        """
        cutoff_date = datetime.now() - pd.Timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        cleaned = []
        daily_path = os.path.join(self.storage_path, "daily")
        
        if os.path.exists(daily_path):
            for file in Path(daily_path).glob("*.parquet"):
                file_date = file.stem
                if file_date < cutoff_str:
                    if not dry_run:
                        os.remove(file)
                    cleaned.append(str(file))
        
        return cleaned
    
    def export_signals(
        self,
        signal_ids: List[str],
        output_path: str,
        format: str = "parquet"
    ) -> bool:
        """
        导出信号数据
        
        Args:
            signal_ids: 信号ID列表
            output_path: 输出路径
            format: 输出格式
            
        Returns:
            bool: 是否成功
        """
        try:
            dfs = []
            for signal_id in signal_ids:
                df = self.load_signal_history(signal_id)
                if df is not None:
                    dfs.append(df)
            
            if not dfs:
                return False
            
            combined = pd.concat(dfs, ignore_index=True)
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            if format == "parquet":
                combined.to_parquet(output_path, index=False)
            elif format == "csv":
                combined.to_csv(output_path, index=False)
            elif format == "json":
                combined.to_json(output_path, orient='records')
            else:
                combined.to_parquet(output_path, index=False)
            
            return True
            
        except Exception as e:
            print(f"导出信号数据失败: {e}")
            return False


_default_storage: Optional[SignalStorage] = None


def get_signal_storage(storage_path: Optional[str] = None) -> SignalStorage:
    """获取全局信号存储实例"""
    global _default_storage
    if storage_path is not None or _default_storage is None:
        _default_storage = SignalStorage(storage_path)
    return _default_storage


def reset_signal_storage():
    """重置全局信号存储"""
    global _default_storage
    _default_storage = None
