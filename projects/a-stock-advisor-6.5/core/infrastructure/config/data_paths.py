"""
数据路径配置模块

定义主数据、缓存、元数据索引的统一存储路径。
"""

import os
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass


def normalize_stock_code(stock_code: str) -> str:
    """
    标准化股票代码，提取纯6位数字代码
    
    支持输入格式:
    - 'sh.000001', 'sz.000001' -> '000001'
    - 'sh000001', 'sz000001' -> '000001'
    - '000001.XSHG', '000001.XSHE' -> '000001'
    - '000001.SS', '000001.SZ' -> '000001'
    - '000001' -> '000001'
    """
    if not stock_code:
        return stock_code
    
    import re
    code = str(stock_code).strip()
    code = re.sub(r'^(sh|sz|SH|SZ)\.', '', code)
    code = re.sub(r'^(sh|sz|SH|SZ)', '', code)
    code = re.sub(r'\.(XSHG|XSHE|SS|SZ)$', '', code, flags=re.IGNORECASE)
    
    return code


@dataclass
class DataPathConfig:
    """
    数据路径配置
    
    统一管理所有数据存储路径，包括主数据、缓存、元数据、备份等。
    """
    
    # 根目录
    data_root: str = "./data"
    
    def __post_init__(self):
        """初始化后创建所有目录"""
        self._ensure_directories()
    
    @property
    def master_path(self) -> str:
        """主数据存储路径（持久化）"""
        return os.path.join(self.data_root, "master")
    
    @property
    def cache_path(self) -> str:
        """缓存数据路径（临时）"""
        return os.path.join(self.data_root, "cache")
    
    @property
    def metadata_path(self) -> str:
        """元数据索引路径"""
        return os.path.join(self.data_root, "metadata")
    
    @property
    def backup_path(self) -> str:
        """备份数据路径"""
        return os.path.join(self.data_root, "backups")
    
    # 主数据子目录
    @property
    def stocks_path(self) -> str:
        """股票主数据路径"""
        return os.path.join(self.master_path, "stocks")
    
    @property
    def stocks_daily_path(self) -> str:
        """股票日线数据路径"""
        return os.path.join(self.stocks_path, "daily")
    
    @property
    def stocks_hourly_path(self) -> str:
        """股票小时线数据路径"""
        return os.path.join(self.stocks_path, "hourly")
    
    @property
    def stocks_minute_path(self) -> str:
        """股票分钟线数据路径"""
        return os.path.join(self.stocks_path, "minute")
    
    @property
    def financials_path(self) -> str:
        """财务数据路径"""
        return os.path.join(self.master_path, "financials")
    
    @property
    def northbound_path(self) -> str:
        """北向资金数据路径"""
        return os.path.join(self.master_path, "northbound")
    
    @property
    def reference_path(self) -> str:
        """参考数据路径（股票列表、交易日历等）"""
        return os.path.join(self.master_path, "reference")
    
    # 缓存子目录
    @property
    def api_cache_path(self) -> str:
        """API响应缓存路径"""
        return os.path.join(self.cache_path, "api_responses")
    
    @property
    def computed_cache_path(self) -> str:
        """计算结果缓存路径"""
        return os.path.join(self.cache_path, "computed")
    
    @property
    def temp_path(self) -> str:
        """临时文件路径"""
        return os.path.join(self.cache_path, "temp")
    
    # 因子/信号/组合数据路径
    @property
    def factors_path(self) -> str:
        """因子数据路径"""
        return os.path.join(self.data_root, "factors")
    
    @property
    def signals_path(self) -> str:
        """信号数据路径"""
        return os.path.join(self.data_root, "signals")
    
    @property
    def portfolio_path(self) -> str:
        """组合数据路径"""
        return os.path.join(self.data_root, "portfolio")
    
    @property
    def reports_path(self) -> str:
        """报告数据路径"""
        return os.path.join(self.data_root, "reports")
    
    # 元数据文件路径
    @property
    def metadata_db_path(self) -> str:
        """SQLite索引数据库路径"""
        return os.path.join(self.metadata_path, "index.db")
    
    @property
    def stock_registry_path(self) -> str:
        """股票注册表路径"""
        return os.path.join(self.metadata_path, "stock_registry.json")
    
    @property
    def update_status_path(self) -> str:
        """更新状态记录路径"""
        return os.path.join(self.metadata_path, "update_status.json")
    
    @property
    def quality_scores_path(self) -> str:
        """数据质量分数路径"""
        return os.path.join(self.metadata_path, "quality_scores.json")
    
    def _ensure_directories(self):
        """确保所有目录存在"""
        directories = [
            # 主数据目录
            self.master_path,
            self.stocks_path,
            self.stocks_daily_path,
            self.stocks_hourly_path,
            self.stocks_minute_path,
            self.financials_path,
            self.northbound_path,
            self.reference_path,
            # 缓存目录
            self.cache_path,
            self.api_cache_path,
            self.computed_cache_path,
            self.temp_path,
            # 元数据目录
            self.metadata_path,
            # 备份目录
            self.backup_path,
            os.path.join(self.backup_path, "daily"),
            os.path.join(self.backup_path, "snapshots"),
            # 因子/信号/组合目录
            self.factors_path,
            self.signals_path,
            self.portfolio_path,
            self.reports_path,
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def get_stock_file_path(self, stock_code: str, data_type: str = "daily") -> str:
        """
        获取股票数据文件路径
        
        Args:
            stock_code: 股票代码
            data_type: 数据类型 (daily/hourly/minute)
            
        Returns:
            str: 文件路径
        """
        normalized_code = normalize_stock_code(stock_code)
        
        if data_type == "daily":
            base_path = self.stocks_daily_path
        elif data_type == "hourly":
            base_path = self.stocks_hourly_path
        elif data_type == "minute":
            base_path = self.stocks_minute_path
        else:
            raise ValueError(f"未知的数据类型: {data_type}")
        
        return os.path.join(base_path, f"{normalized_code}.parquet")
    
    def get_factor_path(self, factor_id: str) -> str:
        """
        获取因子数据路径
        
        Args:
            factor_id: 因子ID
            
        Returns:
            str: 因子数据目录路径
        """
        factor_dir = os.path.join(self.factors_path, factor_id)
        Path(factor_dir).mkdir(parents=True, exist_ok=True)
        return factor_dir
    
    def get_signal_path(self, signal_id: str) -> str:
        """
        获取信号数据路径
        
        Args:
            signal_id: 信号ID
            
        Returns:
            str: 信号数据目录路径
        """
        signal_dir = os.path.join(self.signals_path, signal_id)
        Path(signal_dir).mkdir(parents=True, exist_ok=True)
        return signal_dir
    
    def validate_paths(self) -> Dict[str, bool]:
        """
        验证所有路径是否存在
        
        Returns:
            Dict[str, bool]: 各路径的存在状态
        """
        paths = {
            "data_root": self.data_root,
            "master": self.master_path,
            "cache": self.cache_path,
            "metadata": self.metadata_path,
            "backup": self.backup_path,
            "stocks_daily": self.stocks_daily_path,
            "factors": self.factors_path,
            "signals": self.signals_path,
            "portfolio": self.portfolio_path,
        }
        
        return {name: os.path.exists(path) for name, path in paths.items()}
    
    def to_dict(self) -> Dict[str, str]:
        """
        转换为字典
        
        Returns:
            Dict[str, str]: 路径配置字典
        """
        return {
            "data_root": self.data_root,
            "master": self.master_path,
            "cache": self.cache_path,
            "metadata": self.metadata_path,
            "backup": self.backup_path,
            "stocks": self.stocks_path,
            "stocks_daily": self.stocks_daily_path,
            "financials": self.financials_path,
            "reference": self.reference_path,
            "factors": self.factors_path,
            "signals": self.signals_path,
            "portfolio": self.portfolio_path,
            "reports": self.reports_path,
            "metadata_db": self.metadata_db_path,
            "stock_registry": self.stock_registry_path,
            "update_status": self.update_status_path,
        }


# 全局数据路径配置实例
_default_config: Optional[DataPathConfig] = None


def get_data_paths(data_root: Optional[str] = None) -> DataPathConfig:
    """
    获取数据路径配置实例
    
    Args:
        data_root: 数据根目录（None则使用默认实例）
        
    Returns:
        DataPathConfig: 数据路径配置
    """
    global _default_config
    
    if data_root is not None or _default_config is None:
        root = data_root or "./data"
        _default_config = DataPathConfig(data_root=root)
    
    return _default_config


def reset_data_paths():
    """重置数据路径配置"""
    global _default_config
    _default_config = None
