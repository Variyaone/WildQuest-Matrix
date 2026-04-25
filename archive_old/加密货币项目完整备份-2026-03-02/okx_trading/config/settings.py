"""
配置管理模块
处理系统配置的加载和访问
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class Settings:
    """系统配置管理类"""

    def __init__(self, config_path: str = None):
        """
        初始化配置

        Args:
            config_path: 配置文件路径（相对于工作目录）
        """
        self.config_path = config_path
        self._config: Dict[str, Any] = {}

        if config_path:
            self.load_config(config_path)

    def load_config(self, config_path: str):
        """
        从JSON文件加载配置

        Args:
            config_path: 配置文件路径
        """
        try:
            # 解析路径
            path = Path(config_path)

            # 如果是相对路径，尝试在常见位置查找
            if not path.is_absolute():
                possible_paths = [
                    Path(config_path),  # 直接路径
                    Path.home() / '.openclaw' / 'workspace-creator' / config_path,  # workspace目录
                    Path('.') / config_path,  # 当前目录
                ]
                for p in possible_paths:
                    if p.exists():
                        path = p
                        break

            if not path.exists():
                logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
                self._config = self._default_config()
                return

            with open(path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)

            logger.info(f"配置加载成功: {path}")

        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            self._config = self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            'api_key': '',
            'secret': '',
            'passphrase': '',
            'base_url': 'https://www.okx.com',
            'simulated': True,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self._config.get(key, default)

    def get_api_key(self) -> str:
        """获取API密钥"""
        return self._config.get('api_key', '')

    def get_secret(self) -> str:
        """获取API密钥Secret"""
        return self._config.get('secret', '')

    def get_passphrase(self) -> str:
        """获取API密钥Passphrase"""
        return self._config.get('passphrase', '')

    def get_base_url(self) -> str:
        """获取API基础URL"""
        return self._config.get('base_url', 'https://www.okx.com')

    def is_simulated(self) -> bool:
        """是否为模拟交易模式"""
        return self._config.get('simulated', True)

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()

    def set(self, key: str, value: Any):
        """
        设置配置项（运行时修改）

        Args:
            key: 配置键
            value: 配置值
        """
        self._config[key] = value

    def save(self, path: str = None):
        """
        保存配置到文件

        Args:
            path: 保存路径
        """
        save_path = Path(path) if path else (Path(self.config_path) if self.config_path else Path('config.json'))

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存: {save_path}")
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
            raise


# 全局配置实例
_global_settings: Optional[Settings] = None


def get_settings(config_path: str = None) -> Settings:
    """
    获取全局配置实例

    Args:
        config_path: 配置文件路径

    Returns:
        Settings实例
    """
    global _global_settings
    if _global_settings is None:
        _global_settings = Settings(config_path)
    return _global_settings
