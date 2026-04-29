#!/usr/bin/env python3
"""
WildQuest Matrix - 系统健康检查脚本
用途：检查系统健康状态，包括数据完整性、配置正确性、依赖项等
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置
LOG_DIR = project_root / "logs"
HEALTH_CHECK_LOG = LOG_DIR / "health_check.log"

# 确保日志目录存在
LOG_DIR.mkdir(exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(HEALTH_CHECK_LOG),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("HealthCheck")


class HealthChecker:
    """系统健康检查器"""
    
    def __init__(self):
        self.project_dir = project_root
        self.issues = []
        self.warnings = []
    
    def check_project_structure(self) -> bool:
        """检查项目结构"""
        logger.info("检查项目结构...")
        
        required_dirs = ['core', 'data', 'config', 'scripts', 'logs']
        required_files = ['asa', 'run_full_pipeline.py', 'check_trading_day.py']
        
        all_ok = True
        
        for dir_name in required_dirs:
            dir_path = self.project_dir / dir_name
            if not dir_path.exists():
                self.issues.append(f"缺少目录: {dir_name}")
                all_ok = False
            else:
                logger.info(f"✓ 目录存在: {dir_name}")
        
        for file_name in required_files:
            file_path = self.project_dir / file_name
            if not file_path.exists():
                self.issues.append(f"缺少文件: {file_name}")
                all_ok = False
            else:
                logger.info(f"✓ 文件存在: {file_name}")
        
        return all_ok
    
    def check_data_integrity(self) -> bool:
        """检查数据完整性"""
        logger.info("检查数据完整性...")

        data_dir = self.project_dir / "data"

        if not data_dir.exists():
            self.issues.append("数据目录不存在")
            return False

        # 检查最近的数据更新（检查多个数据源）
        recent_files = []

        # 检查cache目录
        cache_dir = data_dir / "cache"
        if cache_dir.exists():
            for file_path in cache_dir.rglob("*.parquet"):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    recent_files.append((file_path, mtime))

        # 检查历史数据文件
        for file_path in data_dir.glob("history_*.parquet"):
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                recent_files.append((file_path, mtime))

        # 检查股票列表
        stock_list_files = ['stock_list.parquet', 'real_stock_list.parquet', 'a_share_stock_list.parquet']
        for stock_list_file in stock_list_files:
            file_path = data_dir / stock_list_file
            if file_path.exists():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                recent_files.append((file_path, mtime))

        if recent_files:
            recent_files.sort(key=lambda x: x[1], reverse=True)
            latest_file, latest_time = recent_files[0]
            days_since_update = (datetime.now() - latest_time).days

            logger.info(f"最新数据文件: {latest_file.name}")
            logger.info(f"更新时间: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"距离今天: {days_since_update}天")

            if days_since_update > 7:
                self.warnings.append(f"数据已{days_since_update}天未更新")
                return False
        else:
            self.warnings.append("没有找到数据文件")
            return False

        return True
    
    def check_configuration(self) -> bool:
        """检查配置"""
        logger.info("检查配置...")
        
        config_dir = self.project_dir / "config"
        
        if not config_dir.exists():
            self.issues.append("配置目录不存在")
            return False
        
        # 检查环境变量
        env_file = self.project_dir / ".env"
        if env_file.exists():
            logger.info("✓ .env文件存在")
            
            # 检查关键环境变量
            with open(env_file, 'r') as f:
                env_content = f.read()
                
            required_vars = ['FEISHU_WEBHOOK_URL', 'ASA_NOTIFICATION_ENABLED']
            for var in required_vars:
                if var in env_content:
                    logger.info(f"✓ 环境变量已配置: {var}")
                else:
                    self.warnings.append(f"环境变量未配置: {var}")
        else:
            self.warnings.append(".env文件不存在")
        
        return True
    
    def check_dependencies(self) -> bool:
        """检查依赖项"""
        logger.info("检查依赖项...")
        
        venv_dir = self.project_dir / "venv"
        
        if not venv_dir.exists():
            self.issues.append("Python虚拟环境不存在")
            return False
        
        # 检查关键依赖
        required_packages = [
            ('pandas', 'pandas'),
            ('numpy', 'numpy'),
            ('requests', 'requests'),
            ('python-dotenv', 'dotenv')
        ]

        all_ok = True
        for package_name, import_name in required_packages:
            try:
                __import__(import_name)
                logger.info(f"✓ 依赖已安装: {package_name}")
            except ImportError:
                self.issues.append(f"依赖未安装: {package_name}")
                all_ok = False
        
        return all_ok
    
    def check_disk_space(self) -> bool:
        """检查磁盘空间"""
        logger.info("检查磁盘空间...")
        
        import shutil
        
        total, used, free = shutil.disk_usage(self.project_dir)
        
        logger.info(f"总空间: {total / (1024**3):.2f} GB")
        logger.info(f"已使用: {used / (1024**3):.2f} GB")
        logger.info(f"可用空间: {free / (1024**3):.2f} GB")
        
        # 检查可用空间是否小于10GB
        if free < 10 * 1024**3:
            self.warnings.append(f"磁盘空间不足: {free / (1024**3):.2f} GB")
            return False
        
        return True
    
    def check_log_files(self) -> bool:
        """检查日志文件"""
        logger.info("检查日志文件...")
        
        log_dir = self.project_dir / "logs"
        
        if not log_dir.exists():
            self.warnings.append("日志目录不存在")
            return False
        
        # 检查日志文件大小
        log_files = list(log_dir.glob("*.log"))
        total_size = sum(f.stat().st_size for f in log_files)
        
        logger.info(f"日志文件数量: {len(log_files)}")
        logger.info(f"日志总大小: {total_size / (1024**2):.2f} MB")
        
        # 检查是否有异常大的日志文件
        for log_file in log_files:
            size_mb = log_file.stat().st_size / (1024**2)
            if size_mb > 100:
                self.warnings.append(f"日志文件过大: {log_file.name} ({size_mb:.2f} MB)")
        
        return True
    
    def check_crontab(self) -> bool:
        """检查crontab配置"""
        logger.info("检查crontab配置...")
        
        import subprocess
        
        try:
            result = subprocess.run(
                ['crontab', '-l'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                crontab_content = result.stdout
                
                # 检查是否有A股相关的定时任务
                if 'a-stock-advisor' in crontab_content or 'WildQuest' in crontab_content:
                    logger.info("✓ Crontab配置存在")
                    
                    # 检查路径是否正确
                    if '/.hermes/workspace/' in crontab_content:
                        logger.info("✓ Crontab路径正确")
                    else:
                        self.issues.append("Crontab路径可能不正确")
                        return False
                else:
                    self.warnings.append("Crontab中没有找到A股相关任务")
                    return False
            else:
                self.warnings.append("无法读取crontab配置")
                return False
                
        except Exception as e:
            self.warnings.append(f"检查crontab时出错: {e}")
            return False
        
        return True
    
    def run_all_checks(self) -> dict:
        """运行所有检查"""
        logger.info("=" * 80)
        logger.info("开始系统健康检查")
        logger.info(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        results = {
            'project_structure': self.check_project_structure(),
            'data_integrity': self.check_data_integrity(),
            'configuration': self.check_configuration(),
            'dependencies': self.check_dependencies(),
            'disk_space': self.check_disk_space(),
            'log_files': self.check_log_files(),
            'crontab': self.check_crontab(),
        }
        
        # 统计结果
        total_checks = len(results)
        passed_checks = sum(1 for v in results.values() if v)
        
        logger.info("=" * 80)
        logger.info("健康检查完成")
        logger.info(f"总检查项: {total_checks}")
        logger.info(f"通过检查: {passed_checks}")
        logger.info(f"失败检查: {total_checks - passed_checks}")
        logger.info(f"问题数量: {len(self.issues)}")
        logger.info(f"警告数量: {len(self.warnings)}")
        logger.info("=" * 80)
        
        if self.issues:
            logger.error("发现的问题:")
            for issue in self.issues:
                logger.error(f"  - {issue}")
        
        if self.warnings:
            logger.warning("发现的警告:")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")
        
        # 保存检查结果
        self.save_health_report(results)
        
        return {
            'overall_health': passed_checks == total_checks,
            'passed_checks': passed_checks,
            'total_checks': total_checks,
            'issues': self.issues,
            'warnings': self.warnings,
            'details': results
        }
    
    def save_health_report(self, results: dict):
        """保存健康检查报告"""
        report_path = LOG_DIR / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': all(results.values()),
            'passed_checks': sum(1 for v in results.values() if v),
            'total_checks': len(results),
            'issues': self.issues,
            'warnings': self.warnings,
            'details': results
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"健康检查报告已保存: {report_path}")


def main():
    """主函数"""
    checker = HealthChecker()
    result = checker.run_all_checks()
    
    if result['overall_health']:
        logger.info("✅ 系统健康检查通过")
        return 0
    else:
        logger.error("❌ 系统健康检查未通过")
        return 1


if __name__ == "__main__":
    sys.exit(main())
