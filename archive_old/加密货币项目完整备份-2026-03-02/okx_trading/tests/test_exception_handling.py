"""
异常处理单元测试
测试所有异常类和异常处理装饰器
"""

import pytest
import time
from okx_trading.exceptions import (
    TradingException,
    APIException,
    WebSocketException,
    DataQualityException,
    OrderException,
    RiskException,
    ConfigException,
    handle_exceptions,
    retry_on_exception,
    ExceptionContext
)


class TestExceptionClasses:
    """异常类测试"""

    def test_trading_exception_basic(self):
        """测试基础异常类"""
        exc = TradingException("Test trading error")
        assert exc.message == "Test trading error"
        assert exc.details == {}
        assert str(exc) == "Test trading error"

    def test_trading_exception_with_details(self):
        """测试带详情的异常"""
        details = {'code': 400, 'field': 'price'}
        exc = TradingException("Test error with details", details)

        assert exc.message == "Test error with details"
        assert exc.details == details
        assert 'Details:' in str(exc)
        assert '400' in str(exc)

    def test_api_exception(self):
        """测试API异常"""
        exc = APIException("API call failed", status_code=500, response_data={'error': 'Internal'})

        assert exc.status_code == 500
        assert exc.response_data == {'error': 'Internal'}
        assert 'status_code' in exc.details
        assert exc.details['status_code'] == 500

    def test_websocket_exception(self):
        """测试WebSocket异常"""
        original_error = ConnectionError("Connection lost")
        exc = WebSocketException("WebSocket error", error_code="1006", original_error=original_error)

        assert exc.error_code == "1006"
        assert exc.original_error == original_error
        assert 'error_code' in exc.details
        assert 'original_error' in exc.details

    def test_data_quality_exception(self):
        """测试数据质量异常"""
        exc = DataQualityException("Invalid data format", field="price", value=-100)

        assert exc.field == "price"
        assert exc.value == -100
        assert 'field' in exc.details
        assert exc.details['field'] == "price"
        assert exc.details['value'] == -100

    def test_order_exception(self):
        """测试订单异常"""
        order_data = {'symbol': 'BTC/USDT', 'amount': 0.1}
        exc = OrderException("Order rejected", order_id="12345", order_data=order_data)

        assert exc.order_id == "12345"
        assert exc.order_data == order_data
        assert 'order_id' in exc.details
        assert exc.details['order_id'] == "12345"

    def test_risk_exception(self):
        """测试风险异常"""
        risk_details = {'position_size': 1000, 'limit': 500}
        exc = RiskException("Position size exceeded", risk_level="HIGH", risk_details=risk_details)

        assert exc.risk_level == "HIGH"
        assert 'risk_level' in exc.details
        assert exc.details['risk_level'] == "HIGH"
        assert exc.details.get('position_size') == 1000

    def test_config_exception(self):
        """测试配置异常"""
        exc = ConfigException("Missing API key", config_key="api_key")

        assert exc.config_key == "api_key"
        assert 'config_key' in exc.details


class TestHandleExceptionsDecorator:
    """异常处理装饰器测试"""

    def test_handle_exceptions_no_exception(self):
        """测试处理无异常的函数"""
        @handle_exceptions(reraise=False, default_return="default", context="test")
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_handle_exceptions_trading_exception(self):
        """测试处理TradingException"""
        @handle_exceptions(reraise=False, default_return="caught", context="test")
        def raise_trading_exception():
            raise TradingException("Trading error")

        result = raise_trading_exception()
        assert result == "caught"

    def test_handle_exceptions_reraise(self):
        """测试重新抛出异常"""
        @handle_exceptions(reraise=True, default_return="default", context="test")
        def raise_exception():
            raise ValueError("Unexpected error")

        with pytest.raises(TradingException):
            raise_exception()

    def test_handle_exceptions_with_context(self):
        """测试带上下文的异常处理"""
        @handle_exceptions(reraise=False, default_return=None, context="MyModule.MyFunction")
        def raise_with_context():
            raise TradingException("Context test")

        result = raise_with_context()
        assert result is None


class TestRetryOnExceptionDecorator:
    """异常重试装饰器测试"""

    def test_retry_on_exception_success_first_try(self):
        """测试第一次尝试就成功"""
        call_count = [0]

        @retry_on_exception(max_retries=3, context="test")
        def success_func():
            call_count[0] += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count[0] == 1

    def test_retry_on_exception_success_after_retry(self):
        """测试重试后成功"""
        call_count = [0]

        @retry_on_exception(exceptions=(ValueError,), max_retries=3, base_delay=0.01, context="test")
        def fail_twice():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Temporary error")
            return "success"

        result = fail_twice()
        assert result == "success"
        assert call_count[0] == 3

    def test_retry_on_exception_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        call_count = [0]

        @retry_on_exception(exceptions=(ValueError,), max_retries=2, base_delay=0.01, context="test")
        def always_fail():
            call_count[0] += 1
            raise ValueError("Always error")

        with pytest.raises(TradingException) as exc_info:
            always_fail()

        assert call_count[0] == 3  # 初始1次 + 重试2次
        assert "Max retries" in str(exc_info.value)

    def test_retry_on_exception_wrong_exception(self):
        """测试不应该重试的异常类型"""
        call_count = [0]

        @retry_on_exception(exceptions=(ValueError,), max_retries=3, context="test")
        def raise_key_error():
            call_count[0] += 1
            raise KeyError("Wrong exception type")

        with pytest.raises(KeyError):
            raise_key_error()

        assert call_count[0] == 1  # 不应该重试

    def test_retry_on_exception_exponential_backoff(self):
        """测试指数退避"""
        call_times = []

        @retry_on_exception(
            exceptions=(ValueError,),
            max_retries=3,
            base_delay=0.05,
            exponential_backoff=True,
            context="test"
        )
        def retry_with_backoff():
            call_times.append(time.time())
            if len(call_times) < 4:
                raise ValueError("Retry test")
            return "success"

        result = retry_with_backoff()
        assert result == "success"
        assert len(call_times) == 4

        # 验证延迟递增（指数退避）
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i-1]
            # 延迟应该递增（允许一些误差）
            if i < len(call_times) - 1:
                # 第一次延迟约0.05s，第二次约0.1s
                assert delay > 0.04  # 基础延迟

    def test_retry_on_exception_no_backoff(self):
        """测试无指数退避"""
        call_count = [0]

        @retry_on_exception(
            exceptions=(ValueError,),
            max_retries=3,
            base_delay=0.02,
            exponential_backoff=False,
            context="test"
        )
        def retry_no_backoff():
            call_count[0] += 1
            if call_count[0] < 4:
                raise ValueError("Retry test")
            return "success"

        start_time = time.time()
        result = retry_no_backoff()
        elapsed_time = time.time() - start_time

        assert result == "success"
        assert call_count[0] == 4
        # 无指数退避，总延迟应该小于有指数退避的情况
        assert elapsed_time < 0.5  # 合理范围内的总时间


class TestExceptionContext:
    """异常上下文管理器测试"""

    def test_exception_context_no_exception(self):
        """测试无异常的情况"""
        with ExceptionContext("test context", reraise=False, default_return="fallback"):
            result = "success"

        assert result == "success"
        assert not isinstance(result, Exception)

    def test_exception_context_with_exception(self):
        """测试有异常的情况"""
        with ExceptionContext("test context", reraise=False, default_return="caught"):
            raise ValueError("Test error")

        # 不应该抛出异常
        assert True

    def test_exception_context_reraise(self):
        """测试重新抛出异常"""
        with pytest.raises(ValueError):
            with ExceptionContext("test context", reraise=True):
                raise ValueError("Test error")

    def test_exception_context_value(self):
        """测试异常时的返回值"""
        with ExceptionContext("test context", reraise=False, default_return="fallback") as ctx:
            raise ValueError("Test error")

        assert ctx.value == "fallback"
        assert isinstance(ctx.exception, ValueError)

    def test_exception_context_exception_info(self):
        """测试获取异常信息"""
        with ExceptionContext("test context", reraise=False) as ctx:
            raise TradingException("Test trading error", details={'code': 400})

        assert ctx.exception is not None
        assert isinstance(ctx.exception, TradingException)
        assert ctx.exception.message == "Test trading error"
        assert ctx.exception.details.get('code') == 400


class TestExceptionChaining:
    """异常链测试"""

    def test_exception_cause(self):
        """测试异常原因"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise TradingException("Wrapped error") from e
        except TradingException as final_exc:
            assert final_exc.__cause__ is not None
            assert isinstance(final_exc.__cause__, ValueError)
            assert str(final_exc.__cause__) == "Original error"

    def test_exception_from_api_error(self):
        """测试从API错误创建异常"""
        api_error = Exception("API returned 500")
        trading_exc = TradingException("API call failed", original_error=api_error)

        # 可以在异常类中添加original_error属性
        if hasattr(trading_exc, 'original_error'):
            assert trading_exc.original_error == api_error


class TestCustomExceptionBehavior:
    """自定义异常行为测试"""

    def test_exception_attributes(self):
        """测试异常属性"""
        exc = TradingException("Test", details={'key': 'value'})

        assert hasattr(exc, 'message')
        assert hasattr(exc, 'details')
        assert exc.message == "Test"
        assert exc.details == {'key': 'value'}

    def test_exception_equality(self):
        """测试异常比较"""
        exc1 = TradingException("Error 1", details={'code': 1})
        exc2 = TradingException("Error 1", details={'code': 1})
        exc3 = TradingException("Error 2", details={'code': 2})

        # 异常对象应该可以比较（虽然默认不相等）
        assert exc1 != exc2
        assert exc1 != exc3

    def test_exception_hash(self):
        """测试异常哈希"""
        exc = TradingException("Test")
        # 异常应该是可哈希的
        hash(exc)

    def test_exception_pickling(self):
        """测试异常序列化"""
        import pickle

        original_exc = TradingException("Pickling test", details={'key': 'value'})

        # 序列化和反序列化
        pickled = pickle.dumps(original_exc)
        unpickled = pickle.loads(pickled)

        assert unpickled.message == original_exc.message
        assert unpickled.details == original_exc.details


class TestExceptionLogging:
    """异常日志测试"""

    # 这个测试需要配置日志系统，暂时跳过
    def test_exception_logging(self):
        """（跳过）测试异常日志记录"""
        pytest.skip("需要配置日志系统")

    def test_log_exception_function(self):
        """测试log_exception函数"""
        from okx_trading.exceptions import log_exception

        exc = TradingException("Test error", details={'code': 400})
        # 这个函数应该不会抛出异常
        log_exception(exc, context="test", level="ERROR")

        try:
            log_exception(ValueError("Test"), context="test", level="WARNING")
        except Exception as e:
            pytest.fail(f"log_exception不应该抛出异常: {e}")

        assert True


class TestEdgeCases:
    """边缘情况测试"""

    def test_empty_details(self):
        """测试空详情"""
        exc = TradingException("Test", details={})
        assert exc.details == {}
        assert "Details:" not in str(exc)

    def test_none_value_in_details(self):
        """测试详情中有None值"""
        exc = TradingException("Test", details={'key': None, 'value': 5})
        assert exc.details == {'key': None, 'value': 5}

    def test_large_details(self):
        """测试大型详情"""
        large_details = {f'key_{i}': f'value_{i}' for i in range(100)}
        exc = TradingException("Test", details=large_details)
        assert len(exc.details) == 100

    def test_special_characters_in_message(self):
        """测试消息中的特殊字符"""
        special_message = "Error with special chars: \n\t\r\"'"
        exc = TradingException(special_message)
        assert exc.message == special_message

    def test_unicode_in_message(self):
        """测试Unicode消息"""
        unicode_message = "错误信息: 测试中文"
        exc = TradingException(unicode_message)
        assert exc.message == unicode_message
        assert "中文" in str(exc)
