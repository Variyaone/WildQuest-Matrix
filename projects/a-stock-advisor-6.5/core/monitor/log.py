"""
日志管理模块

集中管理所有日志，支持分类存储、归档和查询。
"""

import os
import json
import gzip
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from core.infrastructure.logging import get_logger, LoggerManager


class LogType(Enum):
    """日志类型"""
    TRADE = "trade"         # 交易日志
    STRATEGY = "strategy"   # 策略日志
    FACTOR = "factor"       # 因子日志
    DATA = "data"           # 数据日志
    SYSTEM = "system"       # 系统日志
    AUDIT = "audit"         # 审计日志


class RetentionPolicy(Enum):
    """保留策略"""
    PERMANENT = -1      # 永久保留
    THREE_YEARS = 1095  # 3年
    ONE_YEAR = 365      # 1年
    NINETY_DAYS = 90    # 90天


@dataclass
class LogConfig:
    """日志配置"""
    log_type: LogType
    file_name: str
    retention_days: int
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    def get_retention_policy(self) -> RetentionPolicy:
        """获取保留策略"""
        if self.retention_days == -1:
            return RetentionPolicy.PERMANENT
        elif self.retention_days >= 1095:
            return RetentionPolicy.THREE_YEARS
        elif self.retention_days >= 365:
            return RetentionPolicy.ONE_YEAR
        else:
            return RetentionPolicy.NINETY_DAYS


DEFAULT_LOG_CONFIGS = {
    LogType.TRADE: LogConfig(LogType.TRADE, "trade.log", -1),      # 永久保留
    LogType.STRATEGY: LogConfig(LogType.STRATEGY, "strategy.log", 1095),  # 3年
    LogType.FACTOR: LogConfig(LogType.FACTOR, "factor.log", 365),  # 1年
    LogType.DATA: LogConfig(LogType.DATA, "data.log", 365),        # 1年
    LogType.SYSTEM: LogConfig(LogType.SYSTEM, "system.log", 90),   # 90天
    LogType.AUDIT: LogConfig(LogType.AUDIT, "audit.log", -1),      # 永久保留
}


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: str
    module: str
    operation: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "module": self.module,
            "operation": self.operation,
            "message": self.message,
            "details": self.details
        }
    
    def to_log_line(self) -> str:
        """转换为日志行"""
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        details_str = json.dumps(self.details, ensure_ascii=False) if self.details else ""
        return f"[{ts}] [{self.level}] [{self.module}] [{self.operation}] {self.message} {details_str}"


class LogManager:
    """日志管理器"""
    
    def __init__(
        self,
        log_dir: str = "./logs",
        app_name: str = "a_stock_advisor"
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.app_name = app_name
        self.logger = get_logger("monitor.log_manager")
        
        self.log_configs: Dict[LogType, LogConfig] = DEFAULT_LOG_CONFIGS.copy()
        self._loggers: Dict[LogType, logging.Logger] = {}
        self._handlers: Dict[LogType, RotatingFileHandler] = {}
        
        self._init_loggers()
    
    def _init_loggers(self):
        """初始化各类日志记录器"""
        for log_type, config in self.log_configs.items():
            self._create_logger(log_type, config)
    
    def _create_logger(self, log_type: LogType, config: LogConfig) -> logging.Logger:
        """创建日志记录器"""
        logger = logging.getLogger(f"{self.app_name}.{log_type.value}")
        logger.setLevel(logging.DEBUG)
        
        if logger.handlers:
            self._loggers[log_type] = logger
            return logger
        
        log_file = self.log_dir / config.file_name
        
        handler = RotatingFileHandler(
            log_file,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count,
            encoding="utf-8"
        )
        handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
        self._loggers[log_type] = logger
        self._handlers[log_type] = handler
        
        return logger
    
    def log(
        self,
        log_type: LogType,
        level: str,
        module: str,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录日志"""
        logger = self._loggers.get(log_type)
        if not logger:
            self.logger.warning(f"日志类型不存在: {log_type}")
            return
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level.upper(),
            module=module,
            operation=operation,
            message=message,
            details=details or {}
        )
        
        log_line = entry.to_log_line()
        
        level_map = {
            "DEBUG": logger.debug,
            "INFO": logger.info,
            "WARNING": logger.warning,
            "ERROR": logger.error,
            "CRITICAL": logger.critical
        }
        
        log_func = level_map.get(level.upper(), logger.info)
        log_func(log_line)
    
    def log_trade(
        self,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录交易日志"""
        self.log(LogType.TRADE, "INFO", "TRADE", operation, message, details)
    
    def log_strategy(
        self,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录策略日志"""
        self.log(LogType.STRATEGY, "INFO", "STRATEGY", operation, message, details)
    
    def log_factor(
        self,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录因子日志"""
        self.log(LogType.FACTOR, "INFO", "FACTOR", operation, message, details)
    
    def log_data(
        self,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录数据日志"""
        self.log(LogType.DATA, "INFO", "DATA", operation, message, details)
    
    def log_system(
        self,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录系统日志"""
        self.log(LogType.SYSTEM, "INFO", "SYSTEM", operation, message, details)
    
    def log_audit(
        self,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录审计日志"""
        self.log(LogType.AUDIT, "INFO", "AUDIT", operation, message, details)
    
    def query_logs(
        self,
        log_type: LogType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        level: Optional[str] = None,
        module: Optional[str] = None,
        operation: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> List[LogEntry]:
        """查询日志"""
        config = self.log_configs.get(log_type)
        if not config:
            return []
        
        log_file = self.log_dir / config.file_name
        if not log_file.exists():
            return []
        
        entries = []
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                entry = self._parse_log_line(line.strip())
                if not entry:
                    continue
                
                if start_date and entry.timestamp < start_date:
                    continue
                if end_date and entry.timestamp > end_date:
                    continue
                if level and entry.level != level.upper():
                    continue
                if module and entry.module != module:
                    continue
                if operation and entry.operation != operation:
                    continue
                if keyword and keyword.lower() not in entry.message.lower():
                    continue
                
                entries.append(entry)
        
        return entries
    
    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """解析日志行"""
        try:
            import re
            pattern = r'\[(.*?)\] \[(.*?)\] \[(.*?)\] \[(.*?)\] (.+)'
            match = re.match(pattern, line)
            
            if not match:
                return None
            
            timestamp_str, level, module, operation, rest = match.groups()
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            
            message = rest
            details = {}
            
            if rest.endswith("}"):
                import re as re2
                json_match = re2.search(r'(\{.*\})$', rest)
                if json_match:
                    try:
                        details = json.loads(json_match.group(1))
                        message = rest[:json_match.start()].strip()
                    except json.JSONDecodeError:
                        pass
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                module=module,
                operation=operation,
                message=message,
                details=details
            )
        
        except Exception:
            return None
    
    def archive_logs(self, log_type: LogType, archive_dir: str = "./logs/archive"):
        """归档日志"""
        config = self.log_configs.get(log_type)
        if not config:
            return False
        
        log_file = self.log_dir / config.file_name
        if not log_file.exists():
            return False
        
        archive_path = Path(archive_dir)
        archive_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = archive_path / f"{config.file_name}.{timestamp}.gz"
        
        with open(log_file, 'rb') as f_in:
            with gzip.open(archive_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("")
        
        self.logger.info(f"归档日志: {log_type.value} -> {archive_file}")
        return True
    
    def clean_old_logs(self):
        """清理过期日志"""
        for log_type, config in self.log_configs.items():
            if config.retention_days == -1:
                continue
            
            log_file = self.log_dir / config.file_name
            if not log_file.exists():
                continue
            
            cutoff = datetime.now() - timedelta(days=config.retention_days)
            
            entries = self.query_logs(log_type)
            kept_entries = [e for e in entries if e.timestamp >= cutoff]
            
            if len(kept_entries) < len(entries):
                with open(log_file, 'w', encoding='utf-8') as f:
                    for entry in kept_entries:
                        f.write(entry.to_log_line() + "\n")
                
                removed = len(entries) - len(kept_entries)
                self.logger.info(f"清理日志: {log_type.value}, 移除 {removed} 条记录")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """获取日志统计"""
        stats = {}
        
        for log_type, config in self.log_configs.items():
            log_file = self.log_dir / config.file_name
            
            if log_file.exists():
                size = log_file.stat().st_size
                entries = self.query_logs(log_type)
                
                stats[log_type.value] = {
                    "file": config.file_name,
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "entry_count": len(entries),
                    "retention_days": config.retention_days,
                    "retention_policy": config.get_retention_policy().value
                }
        
        return stats
    
    def export_logs(
        self,
        log_type: LogType,
        output_path: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "json"
    ) -> bool:
        """导出日志"""
        entries = self.query_logs(log_type, start_date, end_date)
        
        if not entries:
            return False
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            data = [e.to_dict() for e in entries]
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                for entry in entries:
                    f.write(entry.to_log_line() + "\n")
        
        self.logger.info(f"导出日志: {log_type.value} -> {output_file}")
        return True
