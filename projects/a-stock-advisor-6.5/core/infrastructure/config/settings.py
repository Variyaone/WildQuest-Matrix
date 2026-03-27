"""
配置管理模块

统一的配置管理系统，支持YAML配置文件和环境变量覆盖。
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class DataConfig:
    """数据配置"""
    data_root: str = "./data"
    lookback_days: int = 365
    update_time: str = "20:00"  # 每日更新时间
    max_retry: int = 3
    retry_delay: int = 60  # 秒


@dataclass
class TradingConfig:
    """交易配置"""
    initial_capital: float = 1000000.0  # 初始资金
    commission_rate: float = 0.0003  # 手续费率
    slippage: float = 0.001  # 滑点
    max_position_per_stock: float = 0.15  # 单票最大仓位
    max_positions: int = 20  # 最大持仓数


@dataclass
class RiskConfig:
    """风控配置"""
    max_drawdown: float = 0.15  # 最大回撤
    stop_loss: float = 0.08  # 止损线
    position_limit: float = 0.95  # 仓位上限
    industry_concentration: float = 0.30  # 行业集中度上限


@dataclass
class StrategyConfig:
    """策略配置"""
    rebalance_frequency: str = "weekly"  # 调仓频率
    benchmark: str = "000300.SH"  # 基准指数
    min_stocks: int = 5  # 最小持股数
    max_stocks: int = 20  # 最大持股数


@dataclass
class NotificationConfig:
    """通知配置"""
    enabled: bool = False
    channels: List[str] = field(default_factory=list)  # email/wechat/dingtalk
    webhook_url: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)


@dataclass
class AppConfig:
    """应用配置"""
    app_name: str = "a_stock_advisor"
    version: str = "6.5.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # 子配置
    data: DataConfig = field(default_factory=DataConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)


class ConfigManager:
    """
    配置管理器
    
    管理应用配置，支持从文件加载和环境变量覆盖。
    """
    
    # 默认配置文件路径
    DEFAULT_CONFIG_PATH = "./config.yaml"
    
    # 环境变量前缀
    ENV_PREFIX = "ASA_"
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Optional[AppConfig] = None
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        # 从文件加载
        file_config = self._load_from_file()
        
        # 从环境变量加载
        env_config = self._load_from_env()
        
        # 合并配置（环境变量优先级高）
        merged_config = self._merge_configs(file_config, env_config)
        
        # 创建配置对象
        self._config = self._dict_to_config(merged_config)
    
    def _load_from_file(self) -> Dict[str, Any]:
        """从文件加载配置"""
        if not os.path.exists(self.config_path):
            return {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return {}
    
    def _load_from_env(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.ENV_PREFIX):
                # 去掉前缀
                config_key = key[len(self.ENV_PREFIX):].lower()
                
                # 尝试转换类型
                value = self._convert_type(value)
                
                # 设置配置值（只支持一级嵌套，如 DATA_LOOKBACK_DAYS -> data.lookback_days）
                if '_' in config_key:
                    # 第一个下划线前的部分作为section
                    parts = config_key.split('_', 1)
                    section = parts[0]
                    option = parts[1]
                    if section not in config:
                        config[section] = {}
                    config[section][option] = value
                else:
                    config[config_key] = value
        
        return config
    
    def _convert_type(self, value: str) -> Any:
        """转换字符串值为合适的类型"""
        # 尝试转换为布尔值
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # 尝试转换为整数
        try:
            return int(value)
        except ValueError:
            pass
        
        # 尝试转换为浮点数
        try:
            return float(value)
        except ValueError:
            pass
        
        # 尝试转换为列表
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        return value
    
    def _set_nested_value(self, config: Dict, key: str, value: Any):
        """设置嵌套配置值"""
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """合并配置"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _dict_to_config(self, config_dict: Dict) -> AppConfig:
        """将字典转换为配置对象"""
        # 提取子配置
        data_config = DataConfig(**config_dict.get('data', {}))
        trading_config = TradingConfig(**config_dict.get('trading', {}))
        risk_config = RiskConfig(**config_dict.get('risk', {}))
        strategy_config = StrategyConfig(**config_dict.get('strategy', {}))
        notification_config = NotificationConfig(**config_dict.get('notification', {}))
        
        # 创建主配置
        return AppConfig(
            app_name=config_dict.get('app_name', 'a_stock_advisor'),
            version=config_dict.get('version', '6.5.0'),
            debug=config_dict.get('debug', False),
            log_level=config_dict.get('log_level', 'INFO'),
            data=data_config,
            trading=trading_config,
            risk=risk_config,
            strategy=strategy_config,
            notification=notification_config
        )
    
    @property
    def config(self) -> AppConfig:
        """获取配置对象"""
        return self._config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键（支持点号分隔，如 'data.data_root'）
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            elif isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split('.')
        target = self._config
        
        for k in keys[:-1]:
            target = getattr(target, k)
        
        setattr(target, keys[-1], value)
    
    def save(self, path: Optional[str] = None):
        """
        保存配置到文件
        
        Args:
            path: 保存路径
        """
        save_path = path or self.config_path
        
        # 确保目录存在
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为字典
        config_dict = asdict(self._config)
        
        # 保存为YAML
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)
    
    def reload(self):
        """重新加载配置"""
        self._load_config()


# 全局配置管理器实例
_default_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        ConfigManager: 配置管理器
    """
    global _default_config_manager
    
    if config_path is not None or _default_config_manager is None:
        _default_config_manager = ConfigManager(config_path)
    
    return _default_config_manager


def get_config() -> AppConfig:
    """
    获取配置对象
    
    Returns:
        AppConfig: 配置对象
    """
    return get_config_manager().config


def reset_config_manager():
    """重置全局配置管理器"""
    global _default_config_manager
    _default_config_manager = None
