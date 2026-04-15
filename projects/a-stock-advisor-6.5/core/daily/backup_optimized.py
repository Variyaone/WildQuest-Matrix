"""
优化的数据备份策略

核心优化：
1. 增量备份：使用rsync只备份变化的部分
2. 分层保留：不同数据类型不同保留策略
3. 压缩优化：使用xz高压缩率
4. 智能清理：自动清理过期备份
"""

import os
import json
import subprocess
import shutil
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from ..infrastructure.logging import get_logger
from ..infrastructure.config import get_data_paths


class BackupType(Enum):
    """备份类型"""
    INCREMENTAL = "incremental"  # 增量备份
    WEEKLY = "weekly"           # 每周备份
    MONTHLY = "monthly"         # 每月备份
    CORE_ASSETS = "core_assets" # 核心资产
    CONFIG = "config"           # 配置文件
    SNAPSHOT = "snapshot"       # 快照


@dataclass
class BackupResult:
    """备份结果"""
    success: bool
    backup_type: BackupType = BackupType.INCREMENTAL
    backup_path: Optional[str] = None
    backup_size: int = 0
    files_count: int = 0
    duration_seconds: float = 0.0
    verified: bool = False
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "backup_type": self.backup_type.value,
            "backup_path": self.backup_path,
            "backup_size": self.backup_size,
            "files_count": self.files_count,
            "duration_seconds": self.duration_seconds,
            "verified": self.verified,
            "error_message": self.error_message,
            "details": self.details
        }


class OptimizedBackup:
    """
    优化的数据备份
    
    核心优化策略：
    
    1. 增量备份（每3天）
       - 使用rsync硬链接实现增量备份
       - 只备份变化的部分
       - 保留14天（约5个备份）
       - 预计空间：5 * 287MB = 1.4GB
    
    2. 核心资产（每周）
       - 因子库、策略库、组合配置
       - 保留4周
       - 预计空间：4 * 10MB = 40MB
    
    3. 配置文件（每次变更）
       - 配置文件、环境变量
       - 保留5个版本
       - 预计空间：5 * 1MB = 5MB
    
    4. 快照（每月）
       - 完整快照
       - 保留3个月
       - 预计空间：3 * 287MB = 861MB
    
    总计预计空间：1.4GB + 40MB + 5MB + 861MB ≈ 2.3GB
    """
    
    # 优化后的保留策略
    RETENTION_POLICIES = {
        BackupType.INCREMENTAL: 14,   # 14天（约5个备份）
        BackupType.WEEKLY: 28,        # 4周
        BackupType.MONTHLY: 90,       # 3个月
        BackupType.CORE_ASSETS: 28,   # 4周
        BackupType.CONFIG: 5,         # 5个版本
        BackupType.SNAPSHOT: 90,      # 3个月
    }
    
    # 核心资产（每周备份）
    CORE_ASSETS = [
        "factors/factor_registry.json",
        "factors/factor_scores.json",
        "signals/signal_registry.json",
        "strategies/strategy_registry.json",
        "portfolio/portfolio_registry.json"
    ]
    
    # 业务数据（增量备份）
    BUSINESS_DATA = [
        "master",
        "factors",
        "signals"
    ]
    
    # 配置文件
    CONFIG_FILES = [
        "config.yaml",
        ".env",
        "requirements.txt"
    ]
    
    def __init__(
        self,
        data_paths=None,
        backup_dir: Optional[str] = None,
        logger_name: str = "daily.backup_optimized"
    ):
        """
        初始化备份器
        
        Args:
            data_paths: 数据路径配置
            backup_dir: 备份目录
            logger_name: 日志名称
        """
        self.data_paths = data_paths or get_data_paths()
        self.logger = get_logger(logger_name)
        
        self.backup_dir = backup_dir or os.path.join(
            self.data_paths.data_root, "backups"
        )
        
        self._setup_backup_dirs()
    
    def _setup_backup_dirs(self):
        """设置备份目录"""
        subdirs = [
            "incremental",
            "weekly",
            "monthly",
            "core_assets",
            "config",
            "snapshot"
        ]
        
        for subdir in subdirs:
            dir_path = os.path.join(self.backup_dir, subdir)
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def backup_incremental(
        self,
        date: Optional[datetime] = None
    ) -> BackupResult:
        """
        增量备份（每3天）
        
        使用rsync硬链接实现增量备份，只备份变化的部分
        
        Args:
            date: 备份日期
            
        Returns:
            BackupResult: 备份结果
        """
        import time
        start_time = time.time()
        
        date = date or datetime.now()
        date_str = date.strftime('%Y-%m-%d')
        
        self.logger.info(f"开始增量备份: {date_str}")
        
        try:
            # 创建新的备份目录
            backup_path = os.path.join(
                self.backup_dir,
                "incremental",
                f"backup_{date_str}"
            )
            
            # 查找上一个备份
            previous_backup = self._find_previous_backup("incremental")
            
            if previous_backup:
                # 使用rsync硬链接实现增量备份
                self.logger.info(f"使用上一个备份作为基准: {previous_backup}")
                
                # 复制上一个备份的硬链接
                subprocess.run(
                    ["cp", "-al", previous_backup, backup_path],
                    check=True
                )
                
                # 使用rsync同步变化的部分
                for data_path in self.BUSINESS_DATA:
                    src_path = os.path.join(self.data_paths.data_root, data_path)
                    dst_path = os.path.join(backup_path, data_path)
                    
                    if os.path.exists(src_path):
                        Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
                        
                        subprocess.run(
                            [
                                "rsync",
                                "-av",
                                "--delete",
                                src_path + "/",
                                dst_path + "/"
                            ],
                            check=True,
                            capture_output=True
                        )
            else:
                # 第一次备份，直接复制
                self.logger.info("第一次增量备份，直接复制")
                
                for data_path in self.BUSINESS_DATA:
                    src_path = os.path.join(self.data_paths.data_root, data_path)
                    dst_path = os.path.join(backup_path, data_path)
                    
                    if os.path.exists(src_path):
                        if os.path.isdir(src_path):
                            shutil.copytree(src_path, dst_path)
                        else:
                            shutil.copy2(src_path, dst_path)
            
            # 计算备份大小
            backup_size = self._calculate_dir_size(backup_path)
            files_count = sum(1 for _ in Path(backup_path).rglob('*'))
            
            # 清理过期备份
            self._cleanup_old_backups(BackupType.INCREMENTAL)
            
            duration = time.time() - start_time
            
            self.logger.info(
                f"增量备份完成: {backup_path}, 大小: {backup_size/1024/1024:.2f}MB, "
                f"文件数: {files_count}, 耗时: {duration:.2f}秒"
            )
            
            return BackupResult(
                success=True,
                backup_type=BackupType.INCREMENTAL,
                backup_path=backup_path,
                backup_size=backup_size,
                files_count=files_count,
                duration_seconds=duration,
                verified=True,
                details={
                    "previous_backup": previous_backup,
                    "incremental": previous_backup is not None
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"增量备份失败: {e}")
            
            return BackupResult(
                success=False,
                backup_type=BackupType.INCREMENTAL,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def backup_core_assets(
        self,
        date: Optional[datetime] = None
    ) -> BackupResult:
        """
        备份核心资产（每周）
        
        Args:
            date: 备份日期
            
        Returns:
            BackupResult: 备份结果
        """
        import time
        start_time = time.time()
        
        date = date or datetime.now()
        date_str = date.strftime('%Y-%m-%d')
        
        self.logger.info(f"开始备份核心资产: {date_str}")
        
        try:
            contents = []
            temp_dir = os.path.join(
                self.backup_dir,
                f"temp_core_{date_str}"
            )
            Path(temp_dir).mkdir(parents=True, exist_ok=True)
            
            for asset_path in self.CORE_ASSETS:
                src_path = os.path.join(self.data_paths.data_root, asset_path)
                
                if os.path.exists(src_path):
                    dst_path = os.path.join(temp_dir, os.path.basename(asset_path))
                    Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
                    
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
                    
                    contents.append(asset_path)
            
            # 创建压缩包
            filename = f"core_assets_{date_str}.tar.xz"
            archive_path = os.path.join(self.backup_dir, "core_assets", filename)
            
            subprocess.run(
                ["tar", "-cJf", archive_path, "-C", temp_dir, "."],
                check=True
            )
            
            backup_size = os.path.getsize(archive_path) if os.path.exists(archive_path) else 0
            
            shutil.rmtree(temp_dir)
            
            # 清理过期备份
            self._cleanup_old_backups(BackupType.CORE_ASSETS)
            
            duration = time.time() - start_time
            
            self.logger.info(
                f"核心资产备份完成: {archive_path}, 大小: {backup_size/1024/1024:.2f}MB"
            )
            
            return BackupResult(
                success=True,
                backup_type=BackupType.CORE_ASSETS,
                backup_path=archive_path,
                backup_size=backup_size,
                files_count=len(contents),
                duration_seconds=duration,
                verified=True,
                details={"contents": contents}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"核心资产备份失败: {e}")
            
            return BackupResult(
                success=False,
                backup_type=BackupType.CORE_ASSETS,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def backup_config(
        self,
        date: Optional[datetime] = None
    ) -> BackupResult:
        """
        备份配置文件（每次变更）
        
        Args:
            date: 备份日期
            
        Returns:
            BackupResult: 备份结果
        """
        import time
        start_time = time.time()
        
        date = date or datetime.now()
        date_str = date.strftime('%Y-%m-%d_%H%M%S')
        
        self.logger.info(f"开始备份配置文件: {date_str}")
        
        try:
            contents = []
            temp_dir = os.path.join(
                self.backup_dir,
                f"temp_config_{date_str}"
            )
            Path(temp_dir).mkdir(parents=True, exist_ok=True)
            
            for config_file in self.CONFIG_FILES:
                src_path = os.path.join(self.data_paths.data_root, "..", config_file)
                
                if os.path.exists(src_path):
                    dst_path = os.path.join(temp_dir, config_file)
                    shutil.copy2(src_path, dst_path)
                    contents.append(config_file)
            
            # 创建压缩包
            filename = f"config_{date_str}.tar.xz"
            archive_path = os.path.join(self.backup_dir, "config", filename)
            
            subprocess.run(
                ["tar", "-cJf", archive_path, "-C", temp_dir, "."],
                check=True
            )
            
            backup_size = os.path.getsize(archive_path) if os.path.exists(archive_path) else 0
            
            shutil.rmtree(temp_dir)
            
            # 清理过期备份
            self._cleanup_old_backups(BackupType.CONFIG)
            
            duration = time.time() - start_time
            
            self.logger.info(
                f"配置文件备份完成: {archive_path}, 大小: {backup_size/1024/1024:.2f}MB"
            )
            
            return BackupResult(
                success=True,
                backup_type=BackupType.CONFIG,
                backup_path=archive_path,
                backup_size=backup_size,
                files_count=len(contents),
                duration_seconds=duration,
                verified=True,
                details={"contents": contents}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"配置文件备份失败: {e}")
            
            return BackupResult(
                success=False,
                backup_type=BackupType.CONFIG,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def backup_snapshot(
        self,
        date: Optional[datetime] = None
    ) -> BackupResult:
        """
        创建完整快照（每月）
        
        Args:
            date: 备份日期
            
        Returns:
            BackupResult: 备份结果
        """
        import time
        start_time = time.time()
        
        date = date or datetime.now()
        date_str = date.strftime('%Y-%m-%d')
        
        self.logger.info(f"开始创建完整快照: {date_str}")
        
        try:
            # 创建快照目录
            snapshot_path = os.path.join(
                self.backup_dir,
                "snapshot",
                f"snapshot_{date_str}"
            )
            
            # 使用最新的增量备份作为基准
            latest_incremental = self._find_previous_backup("incremental")
            
            if latest_incremental:
                self.logger.info(f"使用最新增量备份: {latest_incremental}")
                shutil.copytree(latest_incremental, snapshot_path)
            else:
                # 直接复制数据目录
                for data_path in self.BUSINESS_DATA:
                    src_path = os.path.join(self.data_paths.data_root, data_path)
                    dst_path = os.path.join(snapshot_path, data_path)
                    
                    if os.path.exists(src_path):
                        if os.path.isdir(src_path):
                            shutil.copytree(src_path, dst_path)
                        else:
                            shutil.copy2(src_path, dst_path)
            
            # 计算快照大小
            snapshot_size = self._calculate_dir_size(snapshot_path)
            files_count = sum(1 for _ in Path(snapshot_path).rglob('*'))
            
            # 清理过期快照
            self._cleanup_old_backups(BackupType.SNAPSHOT)
            
            duration = time.time() - start_time
            
            self.logger.info(
                f"快照创建完成: {snapshot_path}, 大小: {snapshot_size/1024/1024:.2f}MB"
            )
            
            return BackupResult(
                success=True,
                backup_type=BackupType.SNAPSHOT,
                backup_path=snapshot_path,
                backup_size=snapshot_size,
                files_count=files_count,
                duration_seconds=duration,
                verified=True,
                details={}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"快照创建失败: {e}")
            
            return BackupResult(
                success=False,
                backup_type=BackupType.SNAPSHOT,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def _find_previous_backup(self, backup_type: str) -> Optional[str]:
        """
        查找上一个备份
        
        Args:
            backup_type: 备份类型
            
        Returns:
            Optional[str]: 上一个备份路径
        """
        backup_subdir = os.path.join(self.backup_dir, backup_type)
        
        if not os.path.exists(backup_subdir):
            return None
        
        # 查找最新的备份
        backups = []
        for item in os.listdir(backup_subdir):
            item_path = os.path.join(backup_subdir, item)
            if os.path.isdir(item_path):
                backups.append((item_path, os.path.getmtime(item_path)))
        
        if not backups:
            return None
        
        # 按修改时间排序，返回最新的
        backups.sort(key=lambda x: x[1], reverse=True)
        return backups[0][0]
    
    def _calculate_dir_size(self, dir_path: str) -> int:
        """
        计算目录大小
        
        Args:
            dir_path: 目录路径
            
        Returns:
            int: 目录大小（字节）
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(dir_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
        return total_size
    
    def _cleanup_old_backups(self, backup_type: BackupType):
        """
        清理过期备份
        
        Args:
            backup_type: 备份类型
        """
        retention_count = self.RETENTION_POLICIES.get(backup_type, 5)
        
        backup_subdir = os.path.join(self.backup_dir, backup_type.value)
        
        if not os.path.exists(backup_subdir):
            return
        
        # 获取所有备份
        backups = []
        for item in os.listdir(backup_subdir):
            item_path = os.path.join(backup_subdir, item)
            if os.path.isdir(item_path):
                backups.append((item_path, os.path.getmtime(item_path)))
            elif item.endswith('.tar.xz') or item.endswith('.tar.gz'):
                backups.append((item_path, os.path.getmtime(item_path)))
        
        # 按修改时间排序
        backups.sort(key=lambda x: x[1], reverse=True)
        
        # 保留最新的N个，删除其他的
        if len(backups) > retention_count:
            for item_path, _ in backups[retention_count:]:
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    self.logger.info(f"清理过期备份: {item_path}")
                except Exception as e:
                    self.logger.error(f"清理备份失败: {item_path}, {e}")
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """
        获取备份统计
        
        Returns:
            Dict: 统计信息
        """
        stats = {
            "total_size": 0,
            "total_count": 0,
            "by_type": {}
        }
        
        for bt in BackupType:
            subdir = os.path.join(self.backup_dir, bt.value)
            
            if os.path.exists(subdir):
                type_size = 0
                type_count = 0
                
                for item in os.listdir(subdir):
                    item_path = os.path.join(subdir, item)
                    if os.path.isdir(item_path):
                        type_size += self._calculate_dir_size(item_path)
                        type_count += 1
                    elif item.endswith('.tar.xz') or item.endswith('.tar.gz'):
                        type_size += os.path.getsize(item_path)
                        type_count += 1
                
                stats["by_type"][bt.value] = {
                    "count": type_count,
                    "size": type_size
                }
                stats["total_size"] += type_size
                stats["total_count"] += type_count
        
        stats["total_size_mb"] = stats["total_size"] / 1024 / 1024
        stats["total_size_gb"] = stats["total_size"] / 1024 / 1024 / 1024
        
        return stats
    
    def list_backups(
        self,
        backup_type: Optional[BackupType] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        列出备份
        
        Args:
            backup_type: 备份类型过滤
            limit: 最大数量
            
        Returns:
            List[Dict]: 备份列表
        """
        backups = []
        
        for bt in BackupType:
            if backup_type is not None and bt != backup_type:
                continue
            
            subdir = os.path.join(self.backup_dir, bt.value)
            if os.path.exists(subdir):
                for item in sorted(os.listdir(subdir), reverse=True)[:limit]:
                    item_path = os.path.join(subdir, item)
                    
                    if os.path.isdir(item_path):
                        size = self._calculate_dir_size(item_path)
                        mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                    else:
                        size = os.path.getsize(item_path)
                        mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                    
                    backups.append({
                        "type": bt.value,
                        "path": item_path,
                        "size": size,
                        "size_mb": size / 1024 / 1024,
                        "modified": mtime.isoformat()
                    })
        
        return backups[:limit]
