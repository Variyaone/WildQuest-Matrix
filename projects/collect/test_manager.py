"""测试数据管理器"""
from data_manager import StockDataManager
import os

print("=" * 60)
print("测试数据管理器")
print("=" * 60)

manager = StockDataManager()

print("\n1. 数据概览:")
summary = manager.get_summary()
for k, v in summary.items():
    print(f"   {k}: {v}")

print("\n2. 扫描已有数据:")
report = manager.scan_existing_data()
print(f"   已有 {len(report)} 只股票数据")
for code, info in list(report.items())[:5]:
    status = "✓" if info["is_valid"] else "✗"
    print(f"   {status} {code}: {info['record_count']} 条, {info['date_range']}")

print("\n3. 检查数据质量:")
quality = manager.check_data_quality()
print(f"   有效: {quality['valid']}, 无效: {quality['invalid']}")

print("\n4. 测试断点续传 - 下载新股票:")
result = manager.download_stock("601398", "工商银行", "2010-01-01")
print(f"   下载结果: {'成功' if result else '失败'}")

print("\n5. 查看下载进度:")
progress = manager.get_data_status("601398")
if progress:
    print(f"   状态: {progress.status}")
    print(f"   记录数: {progress.record_count}")
    print(f"   数据源: {progress.source}")
    print(f"   最后更新: {progress.last_update}")

print("\n6. 测试增量更新 (再次下载同一股票):")
result = manager.download_stock("601398", "工商银行", "2010-01-01")
print(f"   结果: {'跳过(已是最新)' if result else '失败'}")

print("\n测试完成!")
