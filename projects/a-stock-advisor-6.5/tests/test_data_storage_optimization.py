"""
阶段3：数据存储优化测试

测试数据压缩器和文件清理器功能。
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import unittest

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data.compressor import (
    DataCompressor, CompressionResult, CompressionStats,
    StorageOptimizer, get_data_compressor, get_storage_optimizer
)
from core.data.cleaner import (
    FileCleaner, FileCleanupResult, CleanupRule,
    DataCleanupScheduler, get_file_cleaner, get_cleanup_scheduler
)


class TestDataCompressor(unittest.TestCase):
    """测试数据压缩器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.compressor = DataCompressor()
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_compress_csv_to_parquet(self):
        """测试CSV压缩为Parquet"""
        csv_path = os.path.join(self.temp_dir, 'test.csv')
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=100),
            'open': np.random.randn(100) * 10 + 100,
            'high': np.random.randn(100) * 10 + 105,
            'low': np.random.randn(100) * 10 + 95,
            'close': np.random.randn(100) * 10 + 100,
            'volume': np.random.randint(1000000, 10000000, 100)
        })
        df.to_csv(csv_path, index=False)
        
        result = self.compressor.compress_file(csv_path)
        
        self.assertTrue(result.success)
        self.assertTrue(result.compressed_path.endswith('.parquet'))
        self.assertLess(result.compression_ratio, 1.0)
        self.assertTrue(os.path.exists(result.compressed_path))
    
    def test_optimize_parquet(self):
        """测试Parquet优化"""
        parquet_path = os.path.join(self.temp_dir, 'test.parquet')
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=1000),
            'value': np.random.randn(1000)
        })
        df.to_parquet(parquet_path, compression='snappy')
        
        original_size = os.path.getsize(parquet_path)
        
        result = self.compressor.compress_file(
            parquet_path,
            compression='zstd'
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.original_size, original_size)
    
    def test_optimize_dtypes(self):
        """测试数据类型优化"""
        df = pd.DataFrame({
            'int_col': [1, 2, 3, 4, 5] * 1000,
            'float_col': [1.0, 2.0, 3.0, 4.0, 5.0] * 1000,
            'str_col': ['A', 'B', 'C'] * 1666 + ['D', 'D']
        })
        
        optimized = self.compressor._optimize_dataframe_dtypes(df)
        
        self.assertIn(optimized['int_col'].dtype, [np.int8, np.int16, np.int32, np.uint8, np.uint16, np.uint32])
        self.assertEqual(optimized['float_col'].dtype, np.float32)
        self.assertEqual(str(optimized['str_col'].dtype), 'category')
    
    def test_compress_directory(self):
        """测试目录压缩"""
        for i in range(3):
            csv_path = os.path.join(self.temp_dir, f'stock_{i}.csv')
            df = pd.DataFrame({
                'date': pd.date_range('2023-01-01', periods=100),
                'close': np.random.randn(100) * 10 + 100
            })
            df.to_csv(csv_path, index=False)
        
        stats = self.compressor.compress_directory(
            self.temp_dir,
            recursive=False,
            delete_original=False
        )
        
        self.assertEqual(stats.total_files, 3)
        self.assertEqual(stats.success_count, 3)
        self.assertEqual(stats.failed_count, 0)
        self.assertGreater(stats.total_saved, 0)
    
    def test_compression_estimate(self):
        """测试压缩估算"""
        csv_path = os.path.join(self.temp_dir, 'test.csv')
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=1000),
            'value': np.random.randn(1000)
        })
        df.to_csv(csv_path, index=False)
        
        estimate = self.compressor.get_compression_estimate(csv_path)
        
        self.assertIn('original_size', estimate)
        self.assertIn('estimated_compressed_size', estimate)
        self.assertIn('estimated_ratio', estimate)


class TestFileCleaner(unittest.TestCase):
    """测试文件清理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.cleaner = FileCleaner(data_root=self.temp_dir, dry_run=False)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_files(self, count: int, age_days: int = 0, prefix: str = 'file'):
        """创建测试文件"""
        for i in range(count):
            file_path = os.path.join(self.temp_dir, f'{prefix}_{i}.tmp')
            with open(file_path, 'w') as f:
                f.write('test content' * 100)
            
            if age_days > 0:
                old_time = (datetime.now() - timedelta(days=age_days)).timestamp()
                os.utime(file_path, (old_time, old_time))
    
    def test_cleanup_old_files(self):
        """测试清理旧文件"""
        self._create_test_files(5, age_days=0, prefix='new')
        self._create_test_files(5, age_days=60, prefix='old')
        
        result = self.cleaner.cleanup_old_files(
            directory=self.temp_dir,
            max_age_days=30,
            pattern='*.tmp'
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.files_deleted, 5)
        self.assertEqual(result.files_kept, 5)
    
    def test_cleanup_by_count(self):
        """测试按数量清理"""
        self._create_test_files(20)
        
        result = self.cleaner.cleanup_by_count(
            directory=self.temp_dir,
            pattern='*.tmp',
            max_count=10
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.files_deleted, 10)
        self.assertEqual(result.files_kept, 10)
    
    def test_cleanup_empty_directories(self):
        """测试清理空目录"""
        empty_dir = os.path.join(self.temp_dir, 'empty_dir')
        os.makedirs(empty_dir)
        
        nested_empty = os.path.join(self.temp_dir, 'nested', 'empty')
        os.makedirs(nested_empty)
        
        self.assertTrue(os.path.exists(empty_dir))
        self.assertTrue(os.path.exists(nested_empty))
        
        result = self.cleaner.cleanup_empty_directories()
        
        self.assertTrue(result.success)
        self.assertGreater(result.files_deleted, 0)
    
    def test_dry_run_mode(self):
        """测试模拟运行模式"""
        self._create_test_files(5, age_days=60)
        
        dry_cleaner = FileCleaner(data_root=self.temp_dir, dry_run=True)
        result = dry_cleaner.cleanup_old_files(
            directory=self.temp_dir,
            max_age_days=30,
            pattern='*.tmp'
        )
        
        self.assertEqual(result.files_deleted, 5)
        
        files_remaining = list(Path(self.temp_dir).glob('*.tmp'))
        self.assertEqual(len(files_remaining), 5)
    
    def test_cleanup_preview(self):
        """测试清理预览"""
        self._create_test_files(5, age_days=60)
        
        preview = self.cleaner.get_cleanup_preview()
        
        self.assertIn('data_root', preview)
        self.assertIn('rules', preview)
        self.assertIn('total_files', preview)


class TestDataCleanupScheduler(unittest.TestCase):
    """测试数据清理调度器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.cleaner = FileCleaner(data_root=self.temp_dir)
        self.scheduler = DataCleanupScheduler(file_cleaner=self.cleaner)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_should_run(self):
        """测试任务调度判断"""
        self.assertTrue(self.scheduler.should_run('test_task', 'daily'))
        
        self.scheduler._last_run['test_task'] = datetime.now()
        self.assertFalse(self.scheduler.should_run('test_task', 'daily'))
    
    def test_get_status(self):
        """测试获取状态"""
        status = self.scheduler.get_status()
        
        self.assertIn('last_run', status)
        self.assertIn('config', status)


class TestStorageOptimizer(unittest.TestCase):
    """测试存储优化器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.optimizer = StorageOptimizer()
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_storage_report(self):
        """测试存储报告生成"""
        report = self.optimizer.get_storage_report()
        
        self.assertIn('generated_at', report)
        self.assertIn('directories', report)
        self.assertIn('total_size', report)


class TestGlobalInstances(unittest.TestCase):
    """测试全局实例"""
    
    def test_get_data_compressor(self):
        """测试获取压缩器实例"""
        compressor = get_data_compressor()
        self.assertIsInstance(compressor, DataCompressor)
    
    def test_get_storage_optimizer(self):
        """测试获取存储优化器实例"""
        optimizer = get_storage_optimizer()
        self.assertIsInstance(optimizer, StorageOptimizer)
    
    def test_get_file_cleaner(self):
        """测试获取文件清理器实例"""
        cleaner = get_file_cleaner()
        self.assertIsInstance(cleaner, FileCleaner)
    
    def test_get_cleanup_scheduler(self):
        """测试获取清理调度器实例"""
        scheduler = get_cleanup_scheduler()
        self.assertIsInstance(scheduler, DataCleanupScheduler)


if __name__ == '__main__':
    unittest.main(verbosity=2)
