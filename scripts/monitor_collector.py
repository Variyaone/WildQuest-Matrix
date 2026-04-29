#!/usr/bin/env python3
"""
WildQuest Matrix - 监控数据收集脚本
用途：收集系统运行数据，包括性能指标、资源使用、执行状态等
"""

import sys
import os
import json
import psutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置
LOG_DIR = project_root / "logs"
MONITOR_LOG = LOG_DIR / "monitor_collector.log"
METRICS_DIR = LOG_DIR / "metrics"

# 确保目录存在
LOG_DIR.mkdir(exist_ok=True)
METRICS_DIR.mkdir(exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(MONITOR_LOG),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MonitorCollector")


class MetricsCollector:
    """监控数据收集器"""
    
    def __init__(self):
        self.project_dir = project_root
        self.metrics = {}
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        logger.info("收集系统指标...")
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用
        memory = psutil.virtual_memory()
        
        # 磁盘使用
        disk = psutil.disk_usage(self.project_dir)
        
        # 网络统计
        network = psutil.net_io_counters()
        
        metrics = {
            'cpu_percent': cpu_percent,
            'memory_total': memory.total,
            'memory_used': memory.used,
            'memory_percent': memory.percent,
            'disk_total': disk.total,
            'disk_used': disk.used,
            'disk_free': disk.free,
            'disk_percent': disk.percent,
            'network_bytes_sent': network.bytes_sent,
            'network_bytes_recv': network.bytes_recv,
        }
        
        logger.info(f"CPU使用率: {cpu_percent}%")
        logger.info(f"内存使用率: {memory.percent}%")
        logger.info(f"磁盘使用率: {disk.percent}%")
        
        return metrics
    
    def collect_process_metrics(self) -> Dict[str, Any]:
        """收集进程指标"""
        logger.info("收集进程指标...")
        
        # 查找Python进程
        python_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if proc.info['name'] == 'Python':
                    python_processes.append({
                        'pid': proc.info['pid'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_percent': proc.info['memory_percent']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        metrics = {
            'python_process_count': len(python_processes),
            'python_processes': python_processes
        }
        
        logger.info(f"Python进程数量: {len(python_processes)}")
        
        return metrics
    
    def collect_project_metrics(self) -> Dict[str, Any]:
        """收集项目指标"""
        logger.info("收集项目指标...")
        
        # 数据目录大小
        data_dir = self.project_dir / "data"
        data_size = 0
        if data_dir.exists():
            for item in data_dir.rglob('*'):
                if item.is_file():
                    data_size += item.stat().st_size
        
        # 日志目录大小
        log_dir = self.project_dir / "logs"
        log_size = 0
        if log_dir.exists():
            for item in log_dir.rglob('*'):
                if item.is_file():
                    log_size += item.stat().st_size
        
        # 代码文件数量
        code_files = 0
        for pattern in ['*.py', '*.md', '*.yaml', '*.json']:
            code_files += len(list(self.project_dir.rglob(pattern)))
        
        metrics = {
            'data_size': data_size,
            'log_size': log_size,
            'code_files': code_files
        }
        
        logger.info(f"数据目录大小: {data_size / (1024**2):.2f} MB")
        logger.info(f"日志目录大小: {log_size / (1024**2):.2f} MB")
        logger.info(f"代码文件数量: {code_files}")
        
        return metrics
    
    def collect_execution_metrics(self) -> Dict[str, Any]:
        """收集执行指标"""
        logger.info("收集执行指标...")
        
        # 检查最近的执行日志
        log_dir = self.project_dir / "logs"
        execution_logs = []
        
        if log_dir.exists():
            # 查找最近的执行日志
            for log_file in log_dir.glob("full_pipeline_*.log"):
                if log_file.is_file():
                    stat = log_file.stat()
                    execution_logs.append({
                        'file': log_file.name,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            # 按修改时间排序
            execution_logs.sort(key=lambda x: x['modified'], reverse=True)
        
        # 检查最近的执行报告
        execution_reports = []
        for report_file in log_dir.glob("execution_report_*.md"):
            if report_file.is_file():
                stat = report_file.stat()
                execution_reports.append({
                    'file': report_file.name,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        execution_reports.sort(key=lambda x: x['modified'], reverse=True)
        
        metrics = {
            'recent_executions': execution_logs[:5],
            'recent_reports': execution_reports[:5]
        }
        
        logger.info(f"最近执行记录: {len(execution_logs)}")
        logger.info(f"最近执行报告: {len(execution_reports)}")
        
        return metrics
    
    def collect_error_metrics(self) -> Dict[str, Any]:
        """收集错误指标"""
        logger.info("收集错误指标...")
        
        # 检查错误日志
        log_dir = self.project_dir / "logs"
        error_logs = []
        
        if log_dir.exists():
            for error_file in log_dir.glob("*error*.log"):
                if error_file.is_file():
                    stat = error_file.stat()
                    error_logs.append({
                        'file': error_file.name,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        error_logs.sort(key=lambda x: x['modified'], reverse=True)
        
        metrics = {
            'error_log_count': len(error_logs),
            'recent_errors': error_logs[:5]
        }
        
        logger.info(f"错误日志数量: {len(error_logs)}")
        
        return metrics
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """收集所有指标"""
        logger.info("=" * 80)
        logger.info("开始收集监控数据")
        logger.info(f"收集时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        self.metrics = {
            'timestamp': datetime.now().isoformat(),
            'system': self.collect_system_metrics(),
            'process': self.collect_process_metrics(),
            'project': self.collect_project_metrics(),
            'execution': self.collect_execution_metrics(),
            'errors': self.collect_error_metrics()
        }
        
        logger.info("=" * 80)
        logger.info("监控数据收集完成")
        logger.info("=" * 80)
        
        # 保存指标
        self.save_metrics()
        
        return self.metrics
    
    def save_metrics(self):
        """保存指标数据"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = METRICS_DIR / f"metrics_{timestamp}.json"
        
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        
        logger.info(f"监控数据已保存: {metrics_file}")
        
        # 同时保存最新的指标
        latest_file = METRICS_DIR / "metrics_latest.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        
        logger.info(f"最新监控数据已保存: {latest_file}")


def main():
    """主函数"""
    collector = MetricsCollector()
    metrics = collector.collect_all_metrics()
    
    logger.info("✅ 监控数据收集完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
