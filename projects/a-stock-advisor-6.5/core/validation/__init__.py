"""
验证模块 - 前置检查系统

提供统一的前置检查机制，确保各层输出结果可信。
"""

from .pre_check import PreCheckManager, get_pre_check_manager, reset_pre_check_manager
from .trust_manager import TrustManager, get_trust_manager, reset_trust_manager
from .reporter import CheckReporter
from .contracts import CheckResult, TrustLevel, TrustLevel
from .freshness import FreshnessPolicy, ExecutionMode, get_freshness_policy, set_execution_mode

__all__ = [
    'PreCheckManager',
    'get_pre_check_manager',
    'reset_pre_check_manager',
    'CheckResult', 
    'TrustLevel',
    'TrustManager',
    'get_trust_manager',
    'reset_trust_manager',
    'CheckReporter',
    'FreshnessPolicy',
    'ExecutionMode',
    'get_freshness_policy',
    'set_execution_mode',
]
