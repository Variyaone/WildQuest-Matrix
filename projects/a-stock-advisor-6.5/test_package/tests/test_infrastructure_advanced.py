"""
基础设施模块高级测试

测试日志系统、配置管理和错误处理功能。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
import shutil


def test_logging():
    """测试日志系统"""
    print("\n" + "="*70)
    print("测试日志系统")
    print("="*70)
    
    from core.infrastructure import get_logger
    
    # 创建临时日志目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        from core.infrastructure.logging import LoggerManager
        manager = LoggerManager(log_dir=temp_dir, level="DEBUG")
        logger = manager.get_logger("test")
        
        print("\n测试各级别日志...")
        logger.debug("这是一条DEBUG日志")
        logger.info("这是一条INFO日志")
        logger.warning("这是一条WARNING日志")
        logger.error("这是一条ERROR日志")
        
        # 检查日志文件是否创建
        log_files = list(os.listdir(temp_dir))
        print(f"\n日志文件列表: {log_files}")
        
        assert len(log_files) >= 2, "应该创建至少2个日志文件"
        
        print("\n✓ 日志系统测试通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_config():
    """测试配置管理"""
    print("\n" + "="*70)
    print("测试配置管理")
    print("="*70)
    
    from core.infrastructure.config import ConfigManager, AppConfig
    
    # 创建临时配置文件
    temp_dir = tempfile.mkdtemp()
    config_path = os.path.join(temp_dir, "config.yaml")
    
    try:
        # 创建测试配置文件
        config_content = """
app_name: test_app
version: 1.0.0
debug: true
log_level: DEBUG

data:
  data_root: ./test_data
  lookback_days: 180

trading:
  initial_capital: 500000
  commission_rate: 0.00025
"""
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # 加载配置
        manager = ConfigManager(config_path)
        config = manager.config
        
        print("\n测试配置加载...")
        print(f"  应用名称: {config.app_name}")
        print(f"  版本: {config.version}")
        print(f"  调试模式: {config.debug}")
        print(f"  日志级别: {config.log_level}")
        print(f"  数据根目录: {config.data.data_root}")
        print(f"  回溯天数: {config.data.lookback_days}")
        print(f"  初始资金: {config.trading.initial_capital}")
        
        assert config.app_name == "test_app", "应用名称应该匹配"
        assert config.data.lookback_days == 180, "回溯天数应该匹配"
        assert config.trading.initial_capital == 500000, "初始资金应该匹配"
        
        # 测试get方法
        print("\n测试get方法...")
        data_root = manager.get("data.data_root")
        print(f"  data.data_root: {data_root}")
        assert data_root == "./test_data"
        
        # 测试环境变量覆盖
        print("\n测试环境变量覆盖...")
        os.environ["ASA_DATA_LOOKBACK_DAYS"] = "365"
        manager2 = ConfigManager(config_path)
        assert manager2.get("data.lookback_days") == 365, "环境变量应该覆盖配置文件"
        print(f"  环境变量覆盖后 lookback_days: {manager2.get('data.lookback_days')}")
        
        del os.environ["ASA_DATA_LOOKBACK_DAYS"]
        
        print("\n✓ 配置管理测试通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_exceptions():
    """测试错误处理"""
    print("\n" + "="*70)
    print("测试错误处理")
    print("="*70)
    
    from core.infrastructure import (
        AppException, ErrorCode,
        DataFetchException, DataNotFoundException,
        TimeoutException, RiskLimitExceededException,
        handle_exception, safe_execute
    )
    
    # 测试基本异常
    print("\n测试基本异常...")
    try:
        raise AppException("测试错误", code=ErrorCode.UNKNOWN_ERROR)
    except AppException as e:
        print(f"  捕获异常: {e}")
        print(f"  错误代码: {e.code.value}")
        print(f"  字典表示: {e.to_dict()}")
    
    # 测试数据异常
    print("\n测试数据异常...")
    try:
        raise DataFetchException("获取数据失败", source="akshare")
    except DataFetchException as e:
        print(f"  捕获异常: {e}")
        print(f"  详情: {e.details}")
    
    # 测试数据未找到异常
    print("\n测试数据未找到异常...")
    try:
        raise DataNotFoundException("股票数据不存在", data_type="daily", identifier="000001.SZ")
    except DataNotFoundException as e:
        print(f"  捕获异常: {e}")
        print(f"  详情: {e.details}")
    
    # 测试超时异常
    print("\n测试超时异常...")
    try:
        raise TimeoutException("请求超时", timeout_seconds=30)
    except TimeoutException as e:
        print(f"  捕获异常: {e}")
        print(f"  详情: {e.details}")
    
    # 测试风控异常
    print("\n测试风控异常...")
    try:
        raise RiskLimitExceededException(
            "超出仓位限制",
            limit_type="position",
            limit_value=0.15,
            actual_value=0.20
        )
    except RiskLimitExceededException as e:
        print(f"  捕获异常: {e}")
        print(f"  详情: {e.details}")
    
    # 测试异常装饰器
    print("\n测试异常装饰器...")
    
    @handle_exception
    def risky_function():
        raise ValueError("原始错误")
    
    try:
        risky_function()
    except AppException as e:
        print(f"  装饰器转换后的异常: {e}")
        print(f"  原始异常: {e.cause}")
    
    # 测试安全执行
    print("\n测试安全执行...")
    result = safe_execute(lambda: 1/0, default=0, error_message="计算失败")
    print(f"  安全执行结果: {result}")
    assert result == 0, "应该返回默认值"
    
    result = safe_execute(lambda: 10/2, default=0)
    print(f"  正常执行结果: {result}")
    assert result == 5, "应该返回计算结果"
    
    print("\n✓ 错误处理测试通过")


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("基础设施模块高级测试套件")
    print("="*70)
    
    try:
        test_logging()
        test_config()
        test_exceptions()
        
        print("\n" + "="*70)
        print("所有测试通过！")
        print("="*70)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
