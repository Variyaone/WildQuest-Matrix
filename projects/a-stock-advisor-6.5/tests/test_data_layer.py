"""
数据层测试

测试数据获取、清洗、存储、调度功能。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
import shutil


def test_fetcher():
    """测试数据获取器"""
    print("\n" + "="*70)
    print("测试数据获取器")
    print("="*70)
    
    from core.data import MockDataSource, DataFetcher
    
    # 使用模拟数据源
    mock_source = MockDataSource()
    fetcher = DataFetcher(primary_source=mock_source)
    
    # 测试获取日线数据
    print("\n测试获取日线数据...")
    result = fetcher.fetch_daily_data("000001.SZ", "2026-01-01", "2026-01-31")
    print(f"  成功: {result.success}")
    print(f"  数据源: {result.source}")
    print(f"  耗时: {result.fetch_time:.3f}s")
    
    if result.success:
        print(f"  数据行数: {len(result.data)}")
        print(f"  列: {list(result.data.columns)}")
        print(f"  前5行:")
        print(result.data.head().to_string())
    
    assert result.success, "获取数据应该成功"
    assert len(result.data) > 0, "数据不应该为空"
    
    # 测试获取股票列表
    print("\n测试获取股票列表...")
    result = fetcher.fetch_stock_list()
    print(f"  成功: {result.success}")
    if result.success:
        print(f"  股票数量: {len(result.data)}")
        print(result.data.to_string())
    
    print("\n✓ 数据获取器测试通过")


def test_cleaner():
    """测试数据清洗器"""
    print("\n" + "="*70)
    print("测试数据清洗器")
    print("="*70)
    
    import pandas as pd
    import numpy as np
    from core.data import DataCleaner
    
    cleaner = DataCleaner()
    
    # 创建测试数据（包含一些问题）
    print("\n创建测试数据...")
    df = pd.DataFrame({
        'stock_code': ['000001.SZ'] * 10,
        'date': pd.date_range('2026-01-01', periods=10, freq='B').strftime('%Y-%m-%d'),
        'open': [10.0, 10.5, 10.3, 10.8, 10.6, 10.9, 11.0, 10.8, 11.2, 11.5],
        'high': [10.8, 11.0, 10.9, 11.2, 11.0, 11.3, 11.5, 11.2, 11.8, 12.0],
        'low': [9.8, 10.2, 10.0, 10.5, 10.3, 10.6, 10.8, 10.5, 10.9, 11.2],
        'close': [10.5, 10.8, 10.6, 11.0, 10.9, 11.2, 11.3, 11.0, 11.5, 11.8],
        'volume': np.random.randint(1000000, 10000000, 10)
    })
    
    # 添加一些问题数据
    # 价格逻辑错误：high < close
    df.loc[2, 'high'] = 10.0  # 应该被修复
    # 缺失值
    df.loc[5, 'volume'] = np.nan
    
    print(f"  原始数据行数: {len(df)}")
    print(f"  原始数据:\n{df.to_string()}")
    
    # 清洗数据
    print("\n清洗数据...")
    result = cleaner.clean(df)
    print(f"  成功: {result.success}")
    
    if result.success:
        print(f"  变更记录:")
        for key, value in result.changes.items():
            print(f"    {key}: {value}")
        print(f"\n  清洗后数据:\n{result.data.to_string()}")
    
    assert result.success, "清洗应该成功"
    assert result.changes['price_logic_fixed'] > 0, "应该修复价格逻辑"
    
    print("\n✓ 数据清洗器测试通过")


def test_storage():
    """测试数据存储"""
    print("\n" + "="*70)
    print("测试数据存储")
    print("="*70)
    
    import pandas as pd
    from core.data import DataStorage
    from core.infrastructure.config import DataPathConfig
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        paths = DataPathConfig(data_root=temp_dir)
        storage = DataStorage(paths)
        
        # 创建测试数据
        df = pd.DataFrame({
            'stock_code': ['000001.SZ'] * 5,
            'date': ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-06', '2026-01-07'],
            'open': [10.0, 10.5, 10.3, 10.8, 10.6],
            'high': [10.8, 11.0, 10.9, 11.2, 11.0],
            'low': [9.8, 10.2, 10.0, 10.5, 10.3],
            'close': [10.5, 10.8, 10.6, 11.0, 10.9],
            'volume': [1000000, 1200000, 1100000, 1300000, 1150000]
        })
        
        # 测试保存
        print("\n测试保存股票数据...")
        result = storage.stock_storage.save_stock_data(df, "000001.SZ", "daily")
        print(f"  成功: {result.success}")
        print(f"  文件路径: {result.file_path}")
        print(f"  存储行数: {result.rows_stored}")
        
        assert result.success, "保存应该成功"
        assert os.path.exists(result.file_path), "文件应该存在"
        
        # 测试加载
        print("\n测试加载股票数据...")
        loaded_df = storage.stock_storage.load_stock_data("000001.SZ", "daily")
        print(f"  加载成功: {loaded_df is not None}")
        print(f"  数据行数: {len(loaded_df)}")
        print(f"  数据:\n{loaded_df.to_string()}")
        
        assert loaded_df is not None, "加载应该成功"
        assert len(loaded_df) == len(df), "数据行数应该一致"
        
        # 测试日期过滤
        print("\n测试日期过滤...")
        filtered_df = storage.stock_storage.load_stock_data(
            "000001.SZ", "daily",
            start_date="2026-01-02",
            end_date="2026-01-06"
        )
        print(f"  过滤后行数: {len(filtered_df)}")
        print(f"  数据:\n{filtered_df.to_string()}")
        
        # 测试列出股票
        print("\n测试列出股票...")
        stocks = storage.stock_storage.list_stocks("daily")
        print(f"  股票列表: {stocks}")
        
        assert "000001.SZ" in stocks, "应该包含测试股票"
        
        # 测试获取数据信息
        print("\n测试获取数据信息...")
        info = storage.stock_storage.get_data_info("000001.SZ", "daily")
        print(f"  信息: {info}")
        
        print("\n✓ 数据存储测试通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_scheduler():
    """测试更新调度器"""
    print("\n" + "="*70)
    print("测试更新调度器")
    print("="*70)
    
    import tempfile
    import shutil
    from core.data import UpdateScheduler, MockDataSource, DataFetcher
    from core.infrastructure.config import DataPathConfig
    from core.data.metadata import MetadataManager
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        paths = DataPathConfig(data_root=temp_dir)
        metadata = MetadataManager(db_path=os.path.join(temp_dir, "metadata.db"))
        
        # 使用模拟数据源
        mock_source = MockDataSource()
        fetcher = DataFetcher(primary_source=mock_source)
        
        scheduler = UpdateScheduler(
            fetcher=fetcher,
            metadata=metadata
        )
        scheduler.storage.paths = paths
        
        # 测试初始化股票列表
        print("\n测试初始化股票列表...")
        stock_codes = scheduler.initialize_stock_list()
        print(f"  初始化股票数: {len(stock_codes)}")
        
        # 测试更新单只股票
        print("\n测试更新单只股票...")
        result = scheduler.update_stock(
            stock_code="000001.SZ",
            start_date="2026-01-01",
            end_date="2026-01-31"
        )
        print(f"  成功: {result.success}")
        print(f"  更新行数: {result.rows_updated}")
        
        assert result.success, "更新应该成功"
        assert result.rows_updated > 0, "应该更新数据"
        
        # 测试检测更新任务
        print("\n测试检测更新任务...")
        tasks = scheduler.detect_update_tasks(["000001.SZ", "000002.SZ"])
        print(f"  检测到的任务数: {len(tasks)}")
        for task in tasks:
            print(f"    - {task.stock_code}: {task.start_date} ~ {task.end_date} (优先级{task.priority})")
        
        print("\n✓ 更新调度器测试通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("数据层测试套件")
    print("="*70)
    
    try:
        test_fetcher()
        test_cleaner()
        test_storage()
        test_scheduler()
        
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
