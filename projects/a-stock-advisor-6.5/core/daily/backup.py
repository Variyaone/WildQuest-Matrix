"""
数据备份

每日备份重要数据和核心资产，支持增量备份和完整性验证。
"""

import os
import json
import tarfile
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
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CORE_ASSETS = "core_assets"
    CONFIG = "config"


@dataclass
class BackupResult:
    """备份结果"""
    success: bool
    backup_type: BackupType = BackupType.DAILY
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


@dataclass
class BackupInfo:
    """备份信息"""
    date: str
    backup_type: BackupType
    file_path: str
    size: int
    created_at: str
    contents: List[str]
    verified: bool
    checksum: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "backup_type": self.backup_type.value,
            "file_path": self.file_path,
            "size": self.size,
            "created_at": self.created_at,
            "contents": self.contents,
            "verified": self.verified,
            "checksum": self.checksum
        }


class DailyBackup:
    """
    数据备份
    
    每日备份重要数据和核心资产：
    
    备份分类：
    - 核心资产（每日备份，永久保留）
      - 因子库
      - 信号库
      - 策略库
      - 组合配置
    
    - 业务数据（每日备份，保留90天）
      - 主数据
      - 因子数据
      - 信号数据
      - 交易记录
    
    - 报告数据（每周备份，保留180天）
      - 日报
      - 周报
      - 月报
    
    - 系统配置（每次变更备份，保留10个版本）
      - 配置文件
      - 环境变量
      - 依赖清单
    
    存储路径：data/backups/
    """
    
    RETENTION_POLICIES = {
        BackupType.DAILY: 90,
        BackupType.WEEKLY: 180,
        BackupType.MONTHLY: 1095,
        BackupType.CORE_ASSETS: -1,
        BackupType.CONFIG: 10
    }
    
    CORE_ASSETS = [
        "factors/factor_registry.json",
        "factors/factor_scores.json",
        "signals/signal_registry.json",
        "strategies/strategy_registry.json",
        "portfolio/portfolio_registry.json"
    ]
    
    BUSINESS_DATA = [
        "master",
        "factors",
        "signals",
        "trades"
    ]
    
    REPORT_DATA = [
        "reports/daily",
        "reports/weekly",
        "reports/monthly"
    ]
    
    CONFIG_FILES = [
        "config.yaml",
        ".env",
        "requirements.txt"
    ]
    
    def __init__(
        self,
        data_paths=None,
        backup_dir: Optional[str] = None,
        logger_name: str = "daily.backup"
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
        subdirs = ["daily", "weekly", "monthly", "core_assets", "config"]
        
        for subdir in subdirs:
            dir_path = os.path.join(self.backup_dir, subdir)
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def backup(
        self,
        backup_type: BackupType = BackupType.DAILY,
        date: Optional[datetime] = None,
        include_core: bool = True,
        include_business: bool = True,
        include_reports: bool = False
    ) -> BackupResult:
        """
        执行备份
        
        Args:
            backup_type: 备份类型
            date: 备份日期
            include_core: 是否包含核心资产
            include_business: 是否包含业务数据
            include_reports: 是否包含报告数据
            
        Returns:
            BackupResult: 备份结果
        """
        import time
        start_time = time.time()
        
        date = date or datetime.now()
        date_str = date.strftime('%Y-%m-%d')
        
        self.logger.info(f"开始备份: {backup_type.value} - {date_str}")
        
        try:
            contents = []
            temp_dir = self._create_temp_backup_dir(date_str, backup_type)
            
            if include_core:
                core_files = self._backup_core_assets(temp_dir)
                contents.extend(core_files)
            
            if include_business:
                business_files = self._backup_business_data(temp_dir)
                contents.extend(business_files)
            
            if include_reports:
                report_files = self._backup_reports(temp_dir)
                contents.extend(report_files)
            
            backup_path = self._create_archive(temp_dir, date_str, backup_type)
            
            checksum = self._calculate_checksum(backup_path)
            
            verified = self._verify_backup(backup_path)
            
            backup_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
            
            self._update_backup_index(
                date_str, backup_type, backup_path, backup_size, contents, verified, checksum
            )
            
            shutil.rmtree(temp_dir)
            
            self._cleanup_old_backups(backup_type)
            
            duration = time.time() - start_time
            
            self.logger.info(
                f"备份完成: {backup_path}, 大小: {backup_size/1024/1024:.2f}MB, "
                f"文件数: {len(contents)}, 耗时: {duration:.2f}秒"
            )
            
            return BackupResult(
                success=True,
                backup_type=backup_type,
                backup_path=backup_path,
                backup_size=backup_size,
                files_count=len(contents),
                duration_seconds=duration,
                verified=verified,
                details={
                    "contents": contents[:20],
                    "checksum": checksum
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"备份失败: {e}")
            
            return BackupResult(
                success=False,
                backup_type=backup_type,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def _create_temp_backup_dir(
        self,
        date_str: str,
        backup_type: BackupType
    ) -> str:
        """创建临时备份目录"""
        temp_dir = os.path.join(
            self.backup_dir,
            f"temp_{backup_type.value}_{date_str}"
        )
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    def _backup_core_assets(self, temp_dir: str) -> List[str]:
        """备份核心资产"""
        copied = []
        
        for asset_path in self.CORE_ASSETS:
            src_path = os.path.join(self.data_paths.data_root, asset_path)
            
            if os.path.exists(src_path):
                dst_path = os.path.join(temp_dir, "core_assets", os.path.basename(asset_path))
                Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
                
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
                
                copied.append(asset_path)
        
        self.logger.info(f"核心资产备份完成: {len(copied)} 个文件")
        return copied
    
    def _backup_business_data(self, temp_dir: str) -> List[str]:
        """备份业务数据"""
        copied = []
        
        for data_path in self.BUSINESS_DATA:
            src_path = os.path.join(self.data_paths.data_root, data_path)
            
            if os.path.exists(src_path):
                dst_path = os.path.join(temp_dir, "business", data_path.replace("/", "_"))
                Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
                
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
                
                copied.append(data_path)
        
        self.logger.info(f"业务数据备份完成: {len(copied)} 个目录")
        return copied
    
    def _backup_reports(self, temp_dir: str) -> List[str]:
        """备份报告数据"""
        copied = []
        
        for report_path in self.REPORT_DATA:
            src_path = os.path.join(self.data_paths.data_root, report_path)
            
            if os.path.exists(src_path):
                dst_path = os.path.join(temp_dir, "reports", report_path.replace("/", "_"))
                Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
                
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
                
                copied.append(report_path)
        
        self.logger.info(f"报告数据备份完成: {len(copied)} 个目录")
        return copied
    
    def _create_archive(
        self,
        temp_dir: str,
        date_str: str,
        backup_type: BackupType
    ) -> str:
        """创建压缩包"""
        if backup_type == BackupType.DAILY:
            filename = f"backup_daily_{date_str}.tar.gz"
        elif backup_type == BackupType.WEEKLY:
            week_num = datetime.strptime(date_str, '%Y-%m-%d').isocalendar()[1]
            filename = f"backup_weekly_{date_str[:4]}-W{week_num:02d}.tar.gz"
        elif backup_type == BackupType.MONTHLY:
            filename = f"backup_monthly_{date_str[:7]}.tar.gz"
        elif backup_type == BackupType.CORE_ASSETS:
            filename = f"core_assets_{date_str}.tar.gz"
        else:
            filename = f"backup_config_{date_str}.tar.gz"
        
        archive_path = os.path.join(self.backup_dir, backup_type.value, filename)
        
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(temp_dir, arcname=os.path.basename(temp_dir))
        
        return archive_path
    
    def _calculate_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _verify_backup(self, backup_path: str) -> bool:
        """验证备份完整性"""
        try:
            if not os.path.exists(backup_path):
                return False
            
            if os.path.getsize(backup_path) == 0:
                return False
            
            with tarfile.open(backup_path, 'r:gz') as tar:
                members = tar.getmembers()
                if len(members) == 0:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"备份验证失败: {e}")
            return False
    
    def _update_backup_index(
        self,
        date_str: str,
        backup_type: BackupType,
        backup_path: str,
        backup_size: int,
        contents: List[str],
        verified: bool,
        checksum: str
    ):
        """更新备份索引"""
        index_path = os.path.join(self.backup_dir, "index.json")
        
        index_data = {"backups": []}
        
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            except Exception:
                pass
        
        backup_info = {
            "date": date_str,
            "type": backup_type.value,
            "file": os.path.basename(backup_path),
            "size": backup_size,
            "created_at": datetime.now().isoformat(),
            "contents": contents,
            "verified": verified,
            "checksum": checksum
        }
        
        existing = [
            i for i, b in enumerate(index_data["backups"])
            if not (b["date"] == date_str and b["type"] == backup_type.value)
        ]
        index_data["backups"] = [index_data["backups"][i] for i in existing]
        
        index_data["backups"].insert(0, backup_info)
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    def _cleanup_old_backups(self, backup_type: BackupType):
        """清理过期备份"""
        retention_days = self.RETENTION_POLICIES.get(backup_type, 90)
        
        if retention_days < 0:
            self.logger.info(f"{backup_type.value} 备份永久保留")
            return
        
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        backup_subdir = os.path.join(self.backup_dir, backup_type.value)
        
        if not os.path.exists(backup_subdir):
            return
        
        deleted = 0
        
        for filename in os.listdir(backup_subdir):
            if not filename.endswith('.tar.gz'):
                continue
            
            file_path = os.path.join(backup_subdir, filename)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if file_mtime < cutoff:
                os.remove(file_path)
                deleted += 1
        
        if deleted > 0:
            self.logger.info(f"清理过期备份: {deleted} 个")
    
    def restore(
        self,
        backup_path: str,
        restore_dir: Optional[str] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        恢复备份
        
        Args:
            backup_path: 备份文件路径
            restore_dir: 恢复目录（None则恢复到原位置）
            overwrite: 是否覆盖现有文件
            
        Returns:
            Dict: 恢复结果
        """
        self.logger.info(f"开始恢复备份: {backup_path}")
        
        if not os.path.exists(backup_path):
            return {
                "success": False,
                "error": "备份文件不存在"
            }
        
        try:
            if not self._verify_backup(backup_path):
                return {
                    "success": False,
                    "error": "备份文件验证失败"
                }
            
            temp_extract_dir = os.path.join(
                self.backup_dir,
                f"restore_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            Path(temp_extract_dir).mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(temp_extract_dir)
            
            extracted_dirs = os.listdir(temp_extract_dir)
            if len(extracted_dirs) == 1:
                extract_root = os.path.join(temp_extract_dir, extracted_dirs[0])
            else:
                extract_root = temp_extract_dir
            
            restore_target = restore_dir or self.data_paths.data_root
            
            files_restored = 0
            
            for item in os.listdir(extract_root):
                src = os.path.join(extract_root, item)
                dst = os.path.join(restore_target, item)
                
                if os.path.exists(dst):
                    if overwrite:
                        if os.path.isdir(dst):
                            shutil.rmtree(dst)
                        else:
                            os.remove(dst)
                    else:
                        continue
                
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                    files_restored += sum(1 for _ in Path(dst).rglob('*'))
                else:
                    shutil.copy2(src, dst)
                    files_restored += 1
            
            shutil.rmtree(temp_extract_dir)
            
            self.logger.info(f"备份恢复完成: {files_restored} 个文件")
            
            return {
                "success": True,
                "files_restored": files_restored,
                "restore_dir": restore_target
            }
            
        except Exception as e:
            self.logger.error(f"备份恢复失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_backups(
        self,
        backup_type: Optional[BackupType] = None,
        limit: int = 30
    ) -> List[BackupInfo]:
        """
        列出备份
        
        Args:
            backup_type: 备份类型过滤
            limit: 最大数量
            
        Returns:
            List[BackupInfo]: 备份列表
        """
        index_path = os.path.join(self.backup_dir, "index.json")
        
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                backups = []
                for b in index_data.get("backups", []):
                    bt = BackupType(b["type"])
                    if backup_type is None or bt == backup_type:
                        backups.append(BackupInfo(
                            date=b["date"],
                            backup_type=bt,
                            file_path=os.path.join(self.backup_dir, bt.value, b["file"]),
                            size=b["size"],
                            created_at=b["created_at"],
                            contents=b["contents"],
                            verified=b["verified"],
                            checksum=b.get("checksum")
                        ))
                
                return backups[:limit]
            except Exception:
                pass
        
        backups = []
        
        for bt in [BackupType.DAILY, BackupType.WEEKLY, BackupType.MONTHLY]:
            if backup_type is not None and bt != backup_type:
                continue
            
            subdir = os.path.join(self.backup_dir, bt.value)
            if os.path.exists(subdir):
                for filename in sorted(os.listdir(subdir), reverse=True)[:limit]:
                    if filename.endswith('.tar.gz'):
                        file_path = os.path.join(subdir, filename)
                        backups.append(BackupInfo(
                            date=filename.split('_')[-1].replace('.tar.gz', ''),
                            backup_type=bt,
                            file_path=file_path,
                            size=os.path.getsize(file_path),
                            created_at=datetime.fromtimestamp(
                                os.path.getmtime(file_path)
                            ).isoformat(),
                            contents=[],
                            verified=True
                        ))
        
        return backups[:limit]
    
    def get_backup_info(self, backup_path: str) -> Optional[BackupInfo]:
        """
        获取备份信息
        
        Args:
            backup_path: 备份路径
            
        Returns:
            Optional[BackupInfo]: 备份信息
        """
        index_path = os.path.join(self.backup_dir, "index.json")
        
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                filename = os.path.basename(backup_path)
                
                for b in index_data.get("backups", []):
                    if b["file"] == filename:
                        return BackupInfo(
                            date=b["date"],
                            backup_type=BackupType(b["type"]),
                            file_path=backup_path,
                            size=b["size"],
                            created_at=b["created_at"],
                            contents=b["contents"],
                            verified=b["verified"],
                            checksum=b.get("checksum")
                        )
            except Exception:
                pass
        
        return None
    
    def verify_all_backups(self) -> Dict[str, Any]:
        """
        验证所有备份
        
        Returns:
            Dict: 验证结果
        """
        results = {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "details": []
        }
        
        backups = self.list_backups(limit=1000)
        
        for backup in backups:
            results["total"] += 1
            
            verified = self._verify_backup(backup.file_path)
            
            if verified:
                results["valid"] += 1
            else:
                results["invalid"] += 1
            
            results["details"].append({
                "file": backup.file_path,
                "verified": verified
            })
        
        self.logger.info(
            f"备份验证完成: 总计={results['total']}, "
            f"有效={results['valid']}, 无效={results['invalid']}"
        )
        
        return results
    
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
                
                for filename in os.listdir(subdir):
                    if filename.endswith('.tar.gz'):
                        file_path = os.path.join(subdir, filename)
                        type_size += os.path.getsize(file_path)
                        type_count += 1
                
                stats["by_type"][bt.value] = {
                    "count": type_count,
                    "size": type_size
                }
                stats["total_size"] += type_size
                stats["total_count"] += type_count
        
        stats["total_size_mb"] = stats["total_size"] / 1024 / 1024
        
        return stats
