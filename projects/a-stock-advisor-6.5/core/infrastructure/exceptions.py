"""
错误处理模块

定义统一的错误类型和错误处理机制。
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(Enum):
    """错误代码"""
    # 系统错误 (1000-1999)
    UNKNOWN_ERROR = 1000
    CONFIG_ERROR = 1001
    INITIALIZATION_ERROR = 1002
    
    # 数据错误 (2000-2999)
    DATA_FETCH_ERROR = 2000
    DATA_CLEAN_ERROR = 2001
    DATA_STORAGE_ERROR = 2002
    DATA_VALIDATION_ERROR = 2003
    DATA_NOT_FOUND = 2004
    
    # 网络错误 (3000-3999)
    NETWORK_ERROR = 3000
    TIMEOUT_ERROR = 3001
    API_ERROR = 3002
    RATE_LIMIT_ERROR = 3003
    
    # 交易错误 (4000-4999)
    TRADING_ERROR = 4000
    ORDER_ERROR = 4001
    POSITION_ERROR = 4002
    INSUFFICIENT_FUNDS = 4003
    
    # 风控错误 (5000-5999)
    RISK_ERROR = 5000
    RISK_LIMIT_EXCEEDED = 5001
    BLACKLIST_VIOLATION = 5002
    
    # 策略错误 (6000-6999)
    STRATEGY_ERROR = 6000
    FACTOR_ERROR = 6001
    SIGNAL_ERROR = 6002
    
    # 验证错误 (7000-7999)
    VALIDATION_ERROR = 7000
    CONTRACT_VIOLATION = 7001


class AppException(Exception):
    """
    应用异常基类
    
    所有自定义异常的基类。
    """
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化异常
        
        Args:
            message: 错误消息
            code: 错误代码
            details: 详细信息
            cause: 原始异常
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_code": self.code.value,
            "error_name": self.code.name,
            "message": self.message,
            "details": self.details
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        base_msg = f"[{self.code.name}] {self.message}"
        if self.cause:
            base_msg += f" (caused by: {self.cause})"
        return base_msg


# ==================== 数据相关异常 ====================

class DataException(AppException):
    """数据异常基类"""
    pass


class DataFetchException(DataException):
    """数据获取异常"""
    
    def __init__(self, message: str, source: str = "", details: Optional[Dict] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.DATA_FETCH_ERROR,
            details={"source": source, **(details or {})},
            cause=cause
        )


class DataCleanException(DataException):
    """数据清洗异常"""
    
    def __init__(self, message: str, details: Optional[Dict] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.DATA_CLEAN_ERROR,
            details=details,
            cause=cause
        )


class DataStorageException(DataException):
    """数据存储异常"""
    
    def __init__(self, message: str, operation: str = "", details: Optional[Dict] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.DATA_STORAGE_ERROR,
            details={"operation": operation, **(details or {})},
            cause=cause
        )


class DataValidationException(DataException):
    """数据验证异常"""
    
    def __init__(self, message: str, validation_errors: Optional[list] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.DATA_VALIDATION_ERROR,
            details={"validation_errors": validation_errors or []},
            cause=cause
        )


class DataNotFoundException(DataException):
    """数据未找到异常"""
    
    def __init__(self, message: str, data_type: str = "", identifier: str = "", cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.DATA_NOT_FOUND,
            details={"data_type": data_type, "identifier": identifier},
            cause=cause
        )


# ==================== 网络相关异常 ====================

class NetworkException(AppException):
    """网络异常基类"""
    pass


class TimeoutException(NetworkException):
    """超时异常"""
    
    def __init__(self, message: str, timeout_seconds: float = 0, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.TIMEOUT_ERROR,
            details={"timeout_seconds": timeout_seconds},
            cause=cause
        )


class APIException(NetworkException):
    """API异常"""
    
    def __init__(self, message: str, api_name: str = "", status_code: int = 0, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.API_ERROR,
            details={"api_name": api_name, "status_code": status_code},
            cause=cause
        )


class RateLimitException(NetworkException):
    """速率限制异常"""
    
    def __init__(self, message: str, retry_after: int = 0, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMIT_ERROR,
            details={"retry_after": retry_after},
            cause=cause
        )


# ==================== 交易相关异常 ====================

class TradingException(AppException):
    """交易异常基类"""
    pass


class OrderException(TradingException):
    """订单异常"""
    
    def __init__(self, message: str, order_id: str = "", details: Optional[Dict] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.ORDER_ERROR,
            details={"order_id": order_id, **(details or {})},
            cause=cause
        )


class PositionException(TradingException):
    """持仓异常"""
    
    def __init__(self, message: str, stock_code: str = "", cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.POSITION_ERROR,
            details={"stock_code": stock_code},
            cause=cause
        )


class InsufficientFundsException(TradingException):
    """资金不足异常"""
    
    def __init__(self, message: str, required: float = 0, available: float = 0, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.INSUFFICIENT_FUNDS,
            details={"required": required, "available": available},
            cause=cause
        )


# ==================== 风控相关异常 ====================

class RiskException(AppException):
    """风控异常基类"""
    pass


class RiskLimitExceededException(RiskException):
    """风控限制超出异常"""
    
    def __init__(self, message: str, limit_type: str = "", limit_value: float = 0, actual_value: float = 0, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.RISK_LIMIT_EXCEEDED,
            details={
                "limit_type": limit_type,
                "limit_value": limit_value,
                "actual_value": actual_value
            },
            cause=cause
        )


class BlacklistViolationException(RiskException):
    """黑名单违规异常"""
    
    def __init__(self, message: str, stock_code: str = "", cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.BLACKLIST_VIOLATION,
            details={"stock_code": stock_code},
            cause=cause
        )


# ==================== 策略相关异常 ====================

class StrategyException(AppException):
    """策略异常基类"""
    pass


class FactorException(StrategyException):
    """因子异常"""
    
    def __init__(self, message: str, factor_id: str = "", cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.FACTOR_ERROR,
            details={"factor_id": factor_id},
            cause=cause
        )


class SignalException(StrategyException):
    """信号异常"""
    
    def __init__(self, message: str, signal_id: str = "", cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.SIGNAL_ERROR,
            details={"signal_id": signal_id},
            cause=cause
        )


# ==================== 验证相关异常 ====================

class ValidationException(AppException):
    """验证异常基类"""
    pass


class ContractViolationException(ValidationException):
    """契约违反异常"""
    
    def __init__(self, message: str, layer: str = "", requirement_id: str = "", cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.CONTRACT_VIOLATION,
            details={"layer": layer, "requirement_id": requirement_id},
            cause=cause
        )


# ==================== 错误处理工具 ====================

def handle_exception(func):
    """
    异常处理装饰器
    
    捕获函数中的异常并转换为AppException。
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppException:
            # 已经是AppException，直接抛出
            raise
        except Exception as e:
            # 转换为AppException
            raise AppException(
                message=str(e),
                code=ErrorCode.UNKNOWN_ERROR,
                cause=e
            )
    return wrapper


def safe_execute(func, default=None, error_message="执行失败"):
    """
    安全执行函数
    
    捕获异常并返回默认值。
    
    Args:
        func: 要执行的函数
        default: 异常时的默认值
        error_message: 错误消息
        
    Returns:
        函数返回值或默认值
    """
    try:
        return func()
    except Exception as e:
        # 可以在这里记录日志
        print(f"{error_message}: {e}")
        return default
