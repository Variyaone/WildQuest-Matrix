#!/usr/bin/env python3
"""
导入RDAgent因子到因子库

Usage:
    python scripts/import_rdagent_factors.py
    python scripts/import_rdagent_factors.py --workspace /path/to/workspace
    python scripts/import_rdagent_factors.py --output converted_factors.json
    python scripts/import_rdagent_factors.py --validate
"""

import sys
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.rdagent_integration import import_rdagent_factors_to_library


def main():
    parser = argparse.ArgumentParser(
        description="导入RDAgent生成的因子到因子库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认路径导入因子
  python scripts/import_rdagent_factors.py
  
  # 指定workspace路径
  python scripts/import_rdagent_factors.py --workspace /path/to/RD-Agent_workspace
  
  # 指定输出文件
  python scripts/import_rdagent_factors.py --output my_factors.json
  
  # 导入并自动验证
  python scripts/import_rdagent_factors.py --validate
        """
    )
    
    parser.add_argument(
        "--workspace",
        type=str,
        default="git_ignore_folder/RD-Agent_workspace",
        help="RDAgent workspace路径 (默认: git_ignore_folder/RD-Agent_workspace)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="converted_rdagent_factors.json",
        help="转换后的因子JSON文件路径 (默认: converted_rdagent_factors.json)"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="导入后自动验证因子"
    )
    
    args = parser.parse_args()
    
    workspace_path = Path(args.workspace)
    if not workspace_path.exists():
        print(f"✗ Workspace路径不存在: {workspace_path}")
        print(f"  请确保RDAgent workspace存在，或使用 --workspace 指定正确路径")
        return 1
    
    print("=" * 60)
    print("RDAgent因子导入工具")
    print("=" * 60)
    print(f"Workspace: {workspace_path}")
    print(f"输出文件: {args.output}")
    print(f"自动验证: {'是' if args.validate else '否'}")
    print("=" * 60)
    print()
    
    result = import_rdagent_factors_to_library(
        workspace_path=str(workspace_path),
        output_file=args.output,
        auto_validate=args.validate,
    )
    
    print("\n" + "=" * 60)
    print("导入结果汇总")
    print("=" * 60)
    print(f"总计: {result['total']} 个因子")
    print(f"成功: {result['success']} 个")
    print(f"跳过: {result['skipped']} 个")
    print(f"失败: {result['failed']} 个")
    
    if result['errors']:
        print("\n错误详情:")
        for error in result['errors']:
            print(f"  - {error}")
    
    if result['success'] > 0:
        print("\n✓ 因子已成功导入因子库")
        print("  可以使用以下命令查看:")
        print("  python -c \"from core.factor import get_factor_registry; reg = get_factor_registry(); print([f.name for f in reg.list_all()[:10]])\"")
        return 0
    else:
        print("\n✗ 没有成功导入任何因子")
        return 1


if __name__ == "__main__":
    sys.exit(main())
