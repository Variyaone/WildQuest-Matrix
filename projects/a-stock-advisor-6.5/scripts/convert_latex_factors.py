#!/usr/bin/env python3
"""
Convert LaTeX formulas in factor library to Python code.

Usage:
    python scripts/convert_latex_factors.py [--dry-run]
"""

import json
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    dry_run = "--dry-run" in sys.argv
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("错误: OPENAI_API_KEY 环境变量未设置")
        print("请设置环境变量后再运行:")
        print("  export OPENAI_API_KEY='your-api-key'")
        return 1
    
    print("API Key 已配置")
    print("正在检查因子库中的 LaTeX 公式...")
    
    registry_path = project_root / "data" / "factors" / "registry.json"
    
    with open(registry_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    latex_patterns = ['\\frac', '\\sum', '\\int', '\\prod', '\\sqrt', '\\log', '\\exp']
    latex_factors = []
    
    for fid, factor in data['factors'].items():
        formula = factor.get('formula', '')
        has_code = factor.get('parameters', {}).get('code', '')
        
        if not has_code:
            for p in latex_patterns:
                if p in formula:
                    latex_factors.append({
                        'id': fid,
                        'name': factor['name'],
                        'formula': formula,
                        'description': factor.get('description', ''),
                        'variables': factor.get('parameters', {}).get('variables', {})
                    })
                    break
    
    print(f"\n找到 {len(latex_factors)} 个需要转换的 LaTeX 公式因子:")
    for f in latex_factors[:5]:
        print(f"  - {f['id']}: {f['name']}")
        print(f"    公式: {f['formula'][:60]}...")
    
    if len(latex_factors) > 5:
        print(f"  ... 还有 {len(latex_factors)-5} 个")
    
    if not latex_factors:
        print("\n没有需要转换的 LaTeX 公式因子")
        return 0
    
    if dry_run:
        print("\n[DRY RUN] 不执行实际转换")
        return 0
    
    print(f"\n开始转换...")
    from core.rdagent_integration.latex_converter import convert_factor_to_code
    
    converted = 0
    failed = 0
    
    for f in latex_factors:
        print(f"\n[{converted+failed+1}/{len(latex_factors)}] {f['name']}")
        success, python_code, error = convert_factor_to_code(
            f['name'], f['formula'], f['description'], f['variables']
        )
        
        if success:
            data['factors'][f['id']]['formula'] = python_code
            data['factors'][f['id']]['parameters']['code'] = python_code
            data['factors'][f['id']]['parameters']['original_latex'] = f['formula']
            converted += 1
            print(f"  ✓ 转换成功")
            print(f"    Python: {python_code[:100]}...")
        else:
            failed += 1
            print(f"  ✗ 转换失败: {error}")
    
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n转换完成: 成功 {converted} 个, 失败 {failed} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
