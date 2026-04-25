"""
日志系统模块

统一的日志系统，支持分级日志、文件日志、控制台日志。
"""

import os
import sys
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredLogFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加额外字段
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        # 如果有异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class ColoredConsoleFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        "DEBUG": "\033[36m",      # 青色
        "INFO": "\033[32m",       # 绿色
        "WARNING": "\033[33m",    # 黄色
        "ERROR": "\033[31m",      # 红色
        "CRITICAL": "\033[35m",   # 紫色
        "RESET": "\033[0m",       # 重置
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 获取颜色
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        
        # 格式化时间
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        
        # 格式化消息
        message = f"{color}[{timestamp}] [{record.levelname}] {record.name}: {record.getMessage()}{reset}"
        
        # 如果有异常信息
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        
        return message


class LoggerManager:
    """
    日志管理器
    
    统一管理所有模块的日志记录。
    """
    
    def __init__(
        self,
        log_dir: str = "./logs",
        app_name: str = "a_stock_advisor",
        level: str = "INFO",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        初始化日志管理器
        
        Args:
            log_dir: 日志目录
            app_name: 应用名称
            level: 日志级别
            max_bytes: 单个日志文件最大大小
            backup_count: 备份文件数量
        """
        self.log_dir = log_dir
        self.app_name = app_name
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # 确保日志目录存在
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # 存储已创建的logger
        self._loggers: Dict[str, logging.Logger] = {}
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        获取logger实例
        
        Args:
            name: logger名称
            
        Returns:
            logging.Logger: logger实例
        """
        if name in self._loggers:
            return self._loggers[name]
        
        # 创建logger
        logger = logging.getLogger(f"{self.app_name}.{name}")
        logger.setLevel(self.level)
        
        # 避免重复添加handler
        if logger.handlers:
            self._loggers[name] = logger
            return logger
        
        # 添加控制台handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        console_formatter = ColoredConsoleFormatter()
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # 添加文件handler（普通日志）
        log_file = os.path.join(self.log_dir, f"{self.app_name}.log")
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(self.level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # 添加结构化日志handler（JSON格式）
        structured_log_file = os.path.join(self.log_dir, f"{self.app_name}_structured.log")
        structured_handler = RotatingFileHandler(
            structured_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding="utf-8"
        )
        structured_handler.setLevel(self.level)
        structured_formatter = StructuredLogFormatter()
        structured_handler.setFormatter(structured_formatter)
        logger.addHandler(structured_handler)
        
        # 错误日志单独文件
        error_log_file = os.path.join(self.log_dir, f"{self.app_name}_error.log")
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)
        
        self._loggers[name] = logger
        return logger
    
    def set_level(self, level: str):
        """
        设置日志级别
        
        Args:
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        """
        self.level = getattr(logging, level.upper(), logging.INFO)
        for logger in self._loggers.values():
            logger.setLevel(self.level)
            for handler in logger.handlers:
                handler.setLevel(self.level)


# 全局日志管理器实例
_default_logger_manager: Optional[LoggerManager] = None


def get_logger_manager() -> LoggerManager:
    """
    获取全局日志管理器实例
    
    Returns:
        LoggerManager: 日志管理器
    """
    global _default_logger_manager
    if _default_logger_manager is None:
        _default_logger_manager = LoggerManager()
    return _default_logger_manager


def get_logger(name: str) -> logging.Logger:
    """
    获取logger实例
    
    Args:
        name: logger名称
        
    Returns:
        logging.Logger: logger实例
    """
    return get_logger_manager().get_logger(name)


def reset_logger_manager():
    """重置全局日志管理器"""
    global _default_logger_manager
    _default_logger_manager = None
