#!/usr/bin/env python3
"""
重新导入RDAgent因子（使用表达式格式）
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.factor.registry import get_factor_registry, FactorSource
from core.rdagent_integration import convert_rdagent_factors
import json


def main():
    """重新导入RDAgent因子"""
    
    registry = get_factor_registry()
    
    print('=' * 60)
    print('Step 1: 删除旧的RDAgent因子')
    print('=' * 60)
    
    # 找出所有RDAgent因子
    all_factors = registry.list_all()
    rdagent_factors = [f for f in all_factors if 'RDAgent' in f.description or 'RDAgent' in f.source]
    
    print(f'找到 {len(rdagent_factors)} 个RDAgent因子')
    
    # 删除这些因子
    deleted_count = 0
    for factor in rdagent_factors:
        try:
            registry.delete(factor.id)
            deleted_count += 1
            print(f'  ✓ 删除: {factor.name} ({factor.id})')
        except Exception as e:
            print(f'  ✗ 删除失败 {factor.name}: {e}')
    
    print(f'\n已删除 {deleted_count} 个因子')
    
    print('\n' + '=' * 60)
    print('Step 2: 转换RDAgent因子（使用表达式格式）')
    print('=' * 60)
    
    # 转换因子
    factors = convert_rdagent_factors(
        workspace_path="git_ignore_folder/RD-Agent_workspace",
        output_file="converted_rdagent_factors_v2.json"
    )
    
    print(f'\n转换了 {len(factors)} 个因子')
    
    # 显示前5个因子的公式
    print('\n前5个因子的公式格式:')
    for i, f in enumerate(factors[:5], 1):
        print(f'{i}. {f.name}')
        print(f'   公式: {f.formula[:100]}...')
        print(f'   是否包含def: {"def" in f.formula}')
        print()
    
    print('=' * 60)
    print('Step 3: 导入因子到因子库')
    print('=' * 60)
    
    # 导入因子
    from core.rdagent_integration.rdagent_factor_converter import import_converted_factors
    
    result = import_converted_factors(
        factors_file="converted_rdagent_factors_v2.json",
        auto_validate=False
    )
    
    print(f'\n导入结果:')
    print(f'  总计: {result["total"]}')
    print(f'  成功: {result["success"]}')
    print(f'  失败: {result["failed"]}')
    print(f'  跳过: {result["skipped"]}')
    
    if result['errors']:
        print(f'\n错误:')
        for error in result['errors'][:5]:
            print(f'  - {error}')
    
    print('\n' + '=' * 60)
    print('Step 4: 验证因子公式格式')
    print('=' * 60)
    
    # 检查新导入的因子
    all_factors = registry.list_all()
    new_rdagent = [f for f in all_factors if 'RDAgent' in f.description][:5]
    
    print(f'\n检查前5个新导入的因子:')
    for i, f in enumerate(new_rdagent, 1):
        print(f'{i}. {f.name} ({f.id})')
        print(f'   公式: {f.formula[:80]}...')
        print(f'   是否包含def: {"def" in f.formula}')
        print()


if __name__ == "__main__":
    main()
