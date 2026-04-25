#!/usr/bin/env python3
"""
备份策略迁移脚本

从旧的备份策略迁移到新的优化策略
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.infrastructure.logging import get_logger
from core.infrastructure.config import get_data_paths


class BackupMigration:
    """备份策略迁移"""
    
    def __init__(self):
        """初始化迁移器"""
        self.logger = get_logger("backup.migration")
        self.data_paths = get_data_paths()
        self.backup_dir = os.path.join(self.data_paths.data_root, "backups")
        self.temp_backup_dir = "/tmp/backup_migration"
    
    def pre_migration_check(self) -> dict:
        """
        迁移前检查
        
        Returns:
            dict: 检查结果
        """
        self.logger.info("开始迁移前检查...")
        
        result = {
            "disk_space": {},
            "backup_size": {},
            "rsync_available": False,
            "can_migrate": False
        }
        
        # 检查磁盘空间
        try:
            df_output = subprocess.run(
                ["df", "-h", self.data_paths.data_root],
                capture_output=True,
                text=True,
                check=True
            ).stdout
            
            lines = df_output.split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                result["disk_space"] = {
                    "total": parts[1],
                    "used": parts[2],
                    "available": parts[3],
                    "usage_percent": parts[4]
                }
        except Exception as e:
            self.logger.error(f"检查磁盘空间失败: {e}")
        
        # 检查当前备份大小
        try:
            backup_size = 0
            for root, dirs, files in os.walk(self.backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        backup_size += os.path.getsize(file_path)
            
            result["backup_size"] = {
                "total_bytes": backup_size,
                "total_mb": backup_size / 1024 / 1024,
                "total_gb": backup_size / 1024 / 1024 / 1024
            }
        except Exception as e:
            self.logger.error(f"检查备份大小失败: {e}")
        
        # 检查rsync是否可用
        try:
            subprocess.run(
                ["rsync", "--version"],
                capture_output=True,
                check=True
            )
            result["rsync_available"] = True
        except Exception as e:
            self.logger.error(f"rsync不可用: {e}")
        
        # 判断是否可以迁移
        result["can_migrate"] = (
            result["rsync_available"] and
            result["backup_size"].get("total_gb", 0) < 50  # 备份小于50GB
        )
        
        self.logger.info(f"迁移前检查完成: {result}")
        return result
    
    def create_temp_backup(self) -> bool:
        """
        创建临时备份
        
        Returns:
            bool: 是否成功
        """
        self.logger.info("创建临时备份...")
        
        try:
            # 创建临时目录
            Path(self.temp_backup_dir).mkdir(parents=True, exist_ok=True)
            
            # 复制当前备份
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            temp_backup_path = os.path.join(self.temp_backup_dir, f"backups_{timestamp}")
            
            if os.path.exists(self.backup_dir):
                shutil.copytree(self.backup_dir, temp_backup_path)
                self.logger.info(f"临时备份创建成功: {temp_backup_path}")
                return True
            else:
                self.logger.warning("备份目录不存在，跳过临时备份")
                return True
                
        except Exception as e:
            self.logger.error(f"创建临时备份失败: {e}")
            return False
    
    def cleanup_old_backups(self) -> dict:
        """
        清理旧备份
        
        Returns:
            dict: 清理结果
        """
        self.logger.info("开始清理旧备份...")
        
        result = {
            "deleted_files": 0,
            "freed_space": 0,
            "details": []
        }
        
        try:
            # 清理daily备份（保留最近7天）
            daily_dir = os.path.join(self.backup_dir, "daily")
            if os.path.exists(daily_dir):
                cutoff = datetime.now() - timedelta(days=7)
                
                for filename in os.listdir(daily_dir):
                    if filename.endswith('.tar.gz'):
                        file_path = os.path.join(daily_dir, filename)
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_mtime < cutoff:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            result["deleted_files"] += 1
                            result["freed_space"] += file_size
                            result["details"].append({
                                "file": filename,
                                "size": file_size,
                                "date": file_mtime.isoformat()
                            })
            
            # 清理weekly备份（保留最近4周）
            weekly_dir = os.path.join(self.backup_dir, "weekly")
            if os.path.exists(weekly_dir):
                cutoff = datetime.now() - timedelta(days=28)
                
                for filename in os.listdir(weekly_dir):
                    if filename.endswith('.tar.gz'):
                        file_path = os.path.join(weekly_dir, filename)
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_mtime < cutoff:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            result["deleted_files"] += 1
                            result["freed_space"] += file_size
                            result["details"].append({
                                "file": filename,
                                "size": file_size,
                                "date": file_mtime.isoformat()
                            })
            
            # 清理monthly备份（保留最近3个月）
            monthly_dir = os.path.join(self.backup_dir, "monthly")
            if os.path.exists(monthly_dir):
                cutoff = datetime.now() - timedelta(days=90)
                
                for filename in os.listdir(monthly_dir):
                    if filename.endswith('.tar.gz'):
                        file_path = os.path.join(monthly_dir, filename)
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_mtime < cutoff:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            result["deleted_files"] += 1
                            result["freed_space"] += file_size
                            result["details"].append({
                                "file": filename,
                                "size": file_size,
                                "date": file_mtime.isoformat()
                            })
            
            result["freed_space_mb"] = result["freed_space"] / 1024 / 1024
            result["freed_space_gb"] = result["freed_space"] / 1024 / 1024 / 1024
            
            self.logger.info(
                f"清理完成: 删除{result['deleted_files']}个文件, "
                f"释放{result['freed_space_mb']:.2f}MB空间"
            )
            
        except Exception as e:
            self.logger.error(f"清理旧备份失败: {e}")
        
        return result
    
    def setup_new_backup_dirs(self) -> bool:
        """
        设置新的备份目录
        
        Returns:
            bool: 是否成功
        """
        self.logger.info("设置新的备份目录...")
        
        try:
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
            
            self.logger.info("新备份目录设置完成")
            return True
            
        except Exception as e:
            self.logger.error(f"设置新备份目录失败: {e}")
            return False
    
    def migrate_latest_backup(self) -> bool:
        """
        迁移最新的备份到新策略
        
        Returns:
            bool: 是否成功
        """
        self.logger.info("迁移最新备份...")
        
        try:
            # 查找最新的daily备份
            daily_dir = os.path.join(self.backup_dir, "daily")
            if not os.path.exists(daily_dir):
                self.logger.warning("daily备份目录不存在")
                return True
            
            # 找到最新的备份文件
            latest_backup = None
            latest_mtime = 0
            
            for filename in os.listdir(daily_dir):
                if filename.endswith('.tar.gz'):
                    file_path = os.path.join(daily_dir, filename)
                    file_mtime = os.path.getmtime(file_path)
                    
                    if file_mtime > latest_mtime:
                        latest_mtime = file_mtime
                        latest_backup = file_path
            
            if not latest_backup:
                self.logger.warning("没有找到最新的备份")
                return True
            
            self.logger.info(f"最新备份: {latest_backup}")
            
            # 解压到新的incremental目录
            incremental_dir = os.path.join(self.backup_dir, "incremental")
            date_str = datetime.fromtimestamp(latest_mtime).strftime('%Y-%m-%d')
            backup_path = os.path.join(incremental_dir, f"backup_{date_str}")
            
            # 创建临时解压目录
            temp_extract_dir = os.path.join(
                self.backup_dir,
                f"temp_extract_{date_str}"
            )
            Path(temp_extract_dir).mkdir(parents=True, exist_ok=True)
            
            # 解压
            subprocess.run(
                ["tar", "-xzf", latest_backup, "-C", temp_extract_dir],
                check=True
            )
            
            # 移动到目标目录
            if os.path.exists(temp_extract_dir):
                # 找到解压后的根目录
                extracted_items = os.listdir(temp_extract_dir)
                if len(extracted_items) == 1:
                    extract_root = os.path.join(temp_extract_dir, extracted_items[0])
                else:
                    extract_root = temp_extract_dir
                
                shutil.move(extract_root, backup_path)
            
            # 清理临时目录
            shutil.rmtree(temp_extract_dir)
            
            self.logger.info(f"最新备份迁移完成: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"迁移最新备份失败: {e}")
            return False
    
    def run_migration(self) -> dict:
        """
        执行完整的迁移流程
        
        Returns:
            dict: 迁移结果
        """
        self.logger.info("开始备份策略迁移...")
        
        result = {
            "success": False,
            "steps": {},
            "error": None
        }
        
        try:
            # 1. 迁移前检查
            self.logger.info("步骤1: 迁移前检查")
            check_result = self.pre_migration_check()
            result["steps"]["pre_check"] = check_result
            
            if not check_result["can_migrate"]:
                result["error"] = "迁移前检查失败，无法迁移"
                return result
            
            # 2. 创建临时备份
            self.logger.info("步骤2: 创建临时备份")
            temp_backup_success = self.create_temp_backup()
            result["steps"]["temp_backup"] = {"success": temp_backup_success}
            
            if not temp_backup_success:
                result["error"] = "创建临时备份失败"
                return result
            
            # 3. 清理旧备份
            self.logger.info("步骤3: 清理旧备份")
            cleanup_result = self.cleanup_old_backups()
            result["steps"]["cleanup"] = cleanup_result
            
            # 4. 设置新备份目录
            self.logger.info("步骤4: 设置新备份目录")
            setup_success = self.setup_new_backup_dirs()
            result["steps"]["setup"] = {"success": setup_success}
            
            if not setup_success:
                result["error"] = "设置新备份目录失败"
                return result
            
            # 5. 迁移最新备份
            self.logger.info("步骤5: 迁移最新备份")
            migrate_success = self.migrate_latest_backup()
            result["steps"]["migrate"] = {"success": migrate_success}
            
            if not migrate_success:
                result["error"] = "迁移最新备份失败"
                return result
            
            result["success"] = True
            self.logger.info("备份策略迁移完成")
            
        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"迁移失败: {e}")
        
        return result
    
    def rollback(self) -> bool:
        """
        回滚迁移
        
        Returns:
            bool: 是否成功
        """
        self.logger.info("开始回滚迁移...")
        
        try:
            # 恢复临时备份
            if os.path.exists(self.temp_backup_dir):
                # 找到最新的临时备份
                backups = [
                    d for d in os.listdir(self.temp_backup_dir)
                    if d.startswith("backups_")
                ]
                
                if backups:
                    latest_backup = sorted(backups)[-1]
                    temp_backup_path = os.path.join(self.temp_backup_dir, latest_backup)
                    
                    # 删除当前备份目录
                    if os.path.exists(self.backup_dir):
                        shutil.rmtree(self.backup_dir)
                    
                    # 恢复备份
                    shutil.copytree(temp_backup_path, self.backup_dir)
                    
                    self.logger.info(f"回滚完成: {temp_backup_path}")
                    return True
            
            self.logger.warning("没有找到临时备份，无法回滚")
            return False
            
        except Exception as e:
            self.logger.error(f"回滚失败: {e}")
            return False


def main():
    """主函数"""
    print("=" * 60)
    print("备份策略迁移工具")
    print("=" * 60)
    
    migration = BackupMigration()
    
    # 迁移前检查
    print("\n1. 迁移前检查...")
    check_result = migration.pre_migration_check()
    
    print(f"磁盘空间: {check_result['disk_space']}")
    print(f"当前备份大小: {check_result['backup_size'].get('total_gb', 0):.2f}GB")
    print(f"rsync可用: {check_result['rsync_available']}")
    print(f"可以迁移: {check_result['can_migrate']}")
    
    if not check_result["can_migrate"]:
        print("\n❌ 迁移前检查失败，无法迁移")
        return
    
    # 确认迁移
    print("\n2. 确认迁移")
    print("即将执行以下操作:")
    print("  - 创建临时备份")
    print("  - 清理旧备份（保留7天daily、4周weekly、3个月monthly）")
    print("  - 设置新的备份目录")
    print("  - 迁移最新备份")
    
    confirm = input("\n是否继续? (yes/no): ")
    if confirm.lower() != "yes":
        print("❌ 用户取消迁移")
        return
    
    # 执行迁移
    print("\n3. 执行迁移...")
    result = migration.run_migration()
    
    if result["success"]:
        print("\n✅ 迁移成功!")
        print(f"清理文件数: {result['steps']['cleanup'].get('deleted_files', 0)}")
        print(f"释放空间: {result['steps']['cleanup'].get('freed_space_mb', 0):.2f}MB")
    else:
        print(f"\n❌ 迁移失败: {result['error']}")
        
        # 询问是否回滚
        rollback = input("是否回滚? (yes/no): ")
        if rollback.lower() == "yes":
            print("\n4. 回滚迁移...")
            if migration.rollback():
                print("✅ 回滚成功")
            else:
                print("❌ 回滚失败")


if __name__ == "__main__":
    main()
