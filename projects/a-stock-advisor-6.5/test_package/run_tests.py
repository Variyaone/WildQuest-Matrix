#!/usr/bin/env python3
"""
测试运行脚本

运行打包的测试套件。
"""

import os
import sys
import subprocess
from pathlib import Path


def run_tests(coverage=True, verbose=True):
    """运行测试"""
    tests_dir = Path(__file__).parent / "tests"
    
    cmd = [sys.executable, "-m", "pytest", str(tests_dir)]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=core", "--cov-report=term", "--cov-report=html"])
    
    # 设置Python路径
    env = os.environ.copy()
    project_root = Path(__file__).parent.parent
    env["PYTHONPATH"] = str(project_root)
    
    print("="*70)
    print("运行测试套件")
    print("="*70)
    print(f"测试目录: {tests_dir}")
    print(f"命令: {' '.join(cmd)}")
    print("="*70)
    
    result = subprocess.run(cmd, env=env, cwd=project_root)
    
    return result.returncode


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="运行测试套件")
    parser.add_argument("--no-cov", action="store_true", help="禁用覆盖率测试")
    parser.add_argument("-q", "--quiet", action="store_true", help="安静模式")
    
    args = parser.parse_args()
    
    sys.exit(run_tests(
        coverage=not args.no_cov,
        verbose=not args.quiet
    ))
