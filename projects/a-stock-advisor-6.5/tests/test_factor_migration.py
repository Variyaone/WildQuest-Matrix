"""
测试因子迁移功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factor import (
    FactorMigrator,
    migrate_factors,
    get_factor_registry,
    FactorCategory,
    FactorSubCategory,
    FactorDirection,
    FactorSource
)

print("=" * 60)
print("因子迁移测试")
print("=" * 60)

# 创建迁移器
migrator = FactorMigrator()

# 迁移Alpha101因子
print("\n迁移Alpha101因子...")
result1 = migrator.migrate_alpha101()
print(f"  总数: {result1.total_factors}")
print(f"  成功: {result1.migrated_factors}")
print(f"  失败: {result1.failed_factors}")
if result1.factor_ids:
    print(f"  因子ID: {result1.factor_ids[:3]}...")

# 迁移Alpha191因子
print("\n迁移Alpha191因子...")
result2 = migrator.migrate_alpha191()
print(f"  总数: {result2.total_factors}")
print(f"  成功: {result2.migrated_factors}")
print(f"  失败: {result2.failed_factors}")

# 迁移自定义因子
print("\n迁移自定义因子...")
result3 = migrator.migrate_custom_factors()
print(f"  总数: {result3.total_factors}")
print(f"  成功: {result3.migrated_factors}")
print(f"  失败: {result3.failed_factors}")

# 获取迁移摘要
print("\n迁移摘要:")
summary = migrator.get_migration_summary()
print(f"  总因子数: {summary['total_factors']}")
print(f"  按分类: {summary['by_category']}")
print(f"  按来源: {summary['by_source']}")

# 查看注册表中的因子
print("\n注册表中的因子列表:")
registry = get_factor_registry()
factors = registry.list_all()
print(f"  总数: {len(factors)}")
for f in factors[:5]:
    print(f"    - {f.id}: {f.name} ({f.category.value})")

print("\n" + "=" * 60)
print("因子迁移测试完成!")
print("=" * 60)
