"""
基础设施模块测试

测试数据路径配置和元数据管理功能。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
import shutil


def test_data_paths():
    """测试数据路径配置"""
    print("\n" + "="*70)
    print("测试数据路径配置")
    print("="*70)
    
    from core.infrastructure.config import DataPathConfig
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        config = DataPathConfig(data_root=temp_dir)
        
        print(f"\n数据根目录: {config.data_root}")
        print(f"主数据路径: {config.master_path}")
        print(f"缓存路径: {config.cache_path}")
        print(f"元数据路径: {config.metadata_path}")
        print(f"备份路径: {config.backup_path}")
        
        # 验证路径存在
        validation = config.validate_paths()
        print(f"\n路径验证结果:")
        for name, exists in validation.items():
            status = "✓" if exists else "✗"
            print(f"  {status} {name}")
        
        # 验证所有路径都存在
        assert all(validation.values()), "所有路径应该存在"
        
        # 测试获取股票文件路径
        stock_path = config.get_stock_file_path("000001.SZ", "daily")
        print(f"\n股票文件路径: {stock_path}")
        assert "000001.SZ.parquet" in stock_path
        
        print("\n✓ 数据路径配置测试通过")
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_metadata_manager():
    """测试元数据管理器"""
    print("\n" + "="*70)
    print("测试元数据管理器")
    print("="*70)
    
    from core.data.metadata import MetadataManager, StockMetadata
    
    # 创建临时数据库
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    
    try:
        manager = MetadataManager(db_path=db_path)
        
        # 测试注册股票
        print("\n测试注册股票...")
        stock = StockMetadata(
            stock_code="000001.SZ",
            stock_name="平安银行",
            exchange="SZ",
            list_date="1991-04-03",
            industry="银行"
        )
        
        success = manager.register_stock(stock)
        assert success, "注册股票应该成功"
        print(f"  ✓ 注册股票: {stock.stock_code}")
        
        # 测试获取股票元数据
        print("\n测试获取股票元数据...")
        retrieved = manager.get_stock_metadata("000001.SZ")
        assert retrieved is not None, "应该能获取到股票元数据"
        assert retrieved.stock_name == "平安银行", "股票名称应该匹配"
        print(f"  ✓ 股票名称: {retrieved.stock_name}")
        print(f"  ✓ 交易所: {retrieved.exchange}")
        
        # 测试更新数据范围
        print("\n测试更新数据范围...")
        manager.update_stock_data_range(
            stock_code="000001.SZ",
            start_date="2020-01-01",
            end_date="2026-03-26",
            record_count=1500
        )
        
        retrieved = manager.get_stock_metadata("000001.SZ")
        assert retrieved.data_start_date == "2020-01-01", "起始日期应该更新"
        assert retrieved.record_count == 1500, "记录数应该更新"
        print(f"  ✓ 数据范围: {retrieved.data_start_date} ~ {retrieved.data_end_date}")
        print(f"  ✓ 记录数: {retrieved.record_count}")
        
        # 测试更新状态
        print("\n测试更新状态...")
        manager.record_update_start("000001.SZ")
        status = manager.get_update_status("000001.SZ")
        assert status is not None, "应该有更新状态"
        print(f"  ✓ 更新状态: {status.status}")
        
        manager.record_update_success("000001.SZ")
        status = manager.get_update_status("000001.SZ")
        assert status.status == "success", "状态应该是success"
        print(f"  ✓ 更新成功")
        
        # 测试数据缺口检测
        print("\n测试数据缺口检测...")
        gaps = manager.detect_gaps(
            stock_list=["000001.SZ", "000002.SZ"],
            expected_end_date="2026-03-28"
        )
        print(f"  ✓ 检测到 {len(gaps)} 个缺口")
        for gap in gaps:
            print(f"    - {gap.stock_code}: {gap.gap_type}")
        
        # 测试获取所有股票
        print("\n测试获取所有股票...")
        stocks = manager.get_all_stocks()
        assert len(stocks) == 1, "应该有1只股票"
        print(f"  ✓ 股票数量: {len(stocks)}")
        
        # 测试导入导出
        print("\n测试导入导出...")
        export_path = os.path.join(temp_dir, "export.json")
        manager.export_to_json(export_path)
        assert os.path.exists(export_path), "导出文件应该存在"
        print(f"  ✓ 导出到: {export_path}")
        
        # 重置并导入
        manager2 = MetadataManager(db_path=db_path + ".new")
        count = manager2.import_from_json(export_path)
        assert count == 1, "应该导入1只股票"
        print(f"  ✓ 导入 {count} 只股票")
        
        print("\n✓ 元数据管理器测试通过")
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("基础设施模块测试套件")
    print("="*70)
    
    try:
        test_data_paths()
        test_metadata_manager()
        
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
