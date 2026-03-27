"""
异常处理模块
定义系统中所有自定义异常类，并提供全局异常处理装饰器
"""

import functools
import logging
import time
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ========== 异常类定义 ==========

class TradingException(Exception):
    """交易异常基类"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class APIException(TradingException):
    """API调用异常"""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        details = {'status_code': status_code, 'response': response_data}
        super().__init__(message, {k: v for k, v in details.items() if v is not None})
        self.status_code = status_code
        self.response_data = response_data


class WebSocketException(TradingException):
    """WebSocket异常"""
    def __init__(self, message: str, error_code: str = None, original_error: Exception = None):
        details = {'error_code': error_code}
        if original_error:
            details['original_error'] = str(original_error)
        super().__init__(message, details)
        self.error_code = error_code
        self.original_error = original_error


class DataQualityException(TradingException):
    """数据质量异常"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        details = {'field': field, 'value': value}
        super().__init__(message, {k: v for k, v in details.items() if v is not None})
        self.field = field
        self.value = value


class OrderException(TradingException):
    """订单异常"""
    def __init__(self, message: str, order_id: str = None, order_data: dict = None):
        details = {'order_id': order_id, 'order_data': order_data}
        super().__init__(message, {k: v for k, v in details.items() if v is not None})
        self.order_id = order_id
        self.order_data = order_data


class RiskException(TradingException):
    """风险管理异常"""
    def __init__(self, message: str, risk_level: str = None, risk_details: dict = None):
        details = {'risk_level': risk_level}
        if risk_details:
            details.update(risk_details)
        super().__init__(message, details)
        self.risk_level = risk_level


class ConfigException(TradingException):
    """配置异常"""
    def __init__(self, message: str, config_key: str = None):
        details = {'config_key': config_key} if config_key else {}
        super().__init__(message, details)
        self.config_key = config_key


# ========== 全局异常处理器装饰器 ==========

def handle_exceptions(
    reraise: bool = True,
    default_return: Any = None,
    log_level: str = 'ERROR',
    context: str = None
):
    """
    全局异常处理装饰器

    Args:
        reraise: 是否重新抛出异常
        default_return: 异常发生时的默认返回值
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        context: 上下文信息（函数名等）
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            ctx = context or f"{func.__module__}.{func.__name__}"
            try:
                return func(*args, **kwargs)
            except TradingException as e:
                # 已知交易异常
                logger.log(
                    getattr(logging, log_level),
                    f"[{ctx}] TradingException: {e.message}",
                    extra={'details': e.details}
                )
                if reraise:
                    raise
                return default_return
            except Exception as e:
                # 未知异常
                logger.log(
                    getattr(logging, log_level),
                    f"[{ctx}] Unexpected error: {type(e).__name__}: {e}",
                    exc_info=True
                )
                if reraise:
                    raise TradingException(f"Unexpected error in {ctx}: {e}") from e
                return default_return
        return wrapper
    return decorator


def retry_on_exception(
    exceptions: tuple = (Exception,),
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential_backoff: bool = True,
    jitter: bool = False,
    context: str = None
):
    """
    异常重试装饰器（指数退避）

    Args:
        exceptions: 需要重试的异常类型元组
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        exponential_backoff: 是否使用指数退避
        jitter: 是否添加随机抖动
        context: 上下文信息
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            ctx = context or f"{func.__module__}.{func.__name__}"
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries - 1:
                        # 计算延迟
                        if exponential_backoff:
                            delay = base_delay * (2 ** attempt)
                        else:
                            delay = base_delay

                        # 添加随机抖动（±20%）
                        if jitter:
                            import random
                            delay = delay * (0.8 + 0.4 * random.random())

                        logger.warning(
                            f"[{ctx}] Attempt {attempt + 1}/{max_retries} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)

            # 达到最大重试次数
            logger.error(f"[{ctx}] Max retries ({max_retries}) exceeded. Last error: {last_exception}")
            raise TradingException(
                f"Operation failed after {max_retries} attempts in {ctx}",
                details={'last_error': str(last_exception)}
            ) from last_exception

        return wrapper
    return decorator


# ========== 工具函数 ==========

def log_exception(exception: Exception, context: str = None, level: str = 'ERROR'):
    """
    记录异常

    Args:
        exception: 异常对象
        context: 上下文信息
        level: 日志级别
    """
    ctx = context or ''
    log_msg = f"[{ctx}] {type(exception).__name__}: {exception}"

    if isinstance(exception, TradingException):
        logger.log(getattr(logging, level), log_msg, extra={'details': exception.details})
    else:
        logger.log(getattr(logging, level), log_msg, exc_info=True)


class ExceptionContext:
    """
    异常上下文管理器
    用于自动记录和块级异常处理
    """

    def __init__(self, context: str, reraise: bool = False, default_return: Any = None):
        """
        初始化

        Args:
            context: 上下文信息
            reraise: 是否重新抛出异常
            default_return: 异常发生时的默认返回值（用于with语句的返回）
        """
        self.context = context
        self.reraise = reraise
        self.default_return = default_return
        self.exception = None
        self.value = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.exception = exc_val
            log_exception(exc_val, self.context)
            if not self.reraise:
                self.value = self.default_return
                return True  # 抑制异常
        return False
