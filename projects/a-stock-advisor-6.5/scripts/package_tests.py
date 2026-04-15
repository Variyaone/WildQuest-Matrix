#!/usr/bin/env python3
"""
测试套件打包脚本

将所有测试文件打包成一个可独立运行的测试套件，方便在新系统中校准和重启测试。
"""

import os
import sys
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime


class TestPackager:
    """测试打包器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        self.output_dir = self.project_root / "test_package"
        self.manifest_file = self.output_dir / "manifest.json"
        
    def package(self):
        """打包测试套件"""
        print("="*70)
        print("测试套件打包")
        print("="*70)
        
        # 创建输出目录
        self.output_dir.mkdir(exist_ok=True)
        
        # 收集测试文件
        test_files = self._collect_test_files()
        print(f"\n发现 {len(test_files)} 个测试文件")
        
        # 复制测试文件
        self._copy_test_files(test_files)
        
        # 复制配置文件
        self._copy_config_files()
        
        # 生成清单文件
        manifest = self._generate_manifest(test_files)
        
        # 生成运行脚本
        self._generate_run_script()
        
        # 生成README
        self._generate_readme(manifest)
        
        print(f"\n打包完成！输出目录: {self.output_dir}")
        print(f"清单文件: {self.manifest_file}")
        
        return manifest
    
    def _collect_test_files(self):
        """收集所有测试文件"""
        test_files = []
        
        for file_path in self.tests_dir.rglob("test_*.py"):
            relative_path = file_path.relative_to(self.tests_dir)
            test_files.append({
                "path": str(file_path),
                "relative_path": str(relative_path),
                "size": file_path.stat().st_size,
                "md5": self._calculate_md5(file_path)
            })
        
        return test_files
    
    def _calculate_md5(self, file_path):
        """计算文件MD5"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _copy_test_files(self, test_files):
        """复制测试文件"""
        tests_output = self.output_dir / "tests"
        tests_output.mkdir(exist_ok=True)
        
        for test_file in test_files:
            src_path = Path(test_file["path"])
            dst_path = tests_output / test_file["relative_path"]
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            print(f"  复制: {test_file['relative_path']}")
    
    def _copy_config_files(self):
        """复制配置文件"""
        config_files = [
            "pyproject.toml",
            "pytest.ini",
            "setup.py",
            "conftest.py",
        ]
        
        config_output = self.output_dir / "config"
        config_output.mkdir(exist_ok=True)
        
        for config_file in config_files:
            src_path = self.project_root / config_file
            if src_path.exists():
                shutil.copy2(src_path, config_output / config_file)
                print(f"  复制配置: {config_file}")
    
    def _generate_manifest(self, test_files):
        """生成清单文件"""
        manifest = {
            "version": "6.5.0",
            "created_at": datetime.now().isoformat(),
            "statistics": {
                "total_files": len(test_files),
                "total_size": sum(f["size"] for f in test_files),
                "modules": list(set(f["relative_path"].split("/")[0] if "/" in f["relative_path"] else "root" for f in test_files))
            },
            "files": test_files,
            "coverage_target": 70,
            "current_coverage": 53,
            "requirements": [
                "pytest>=7.0.0",
                "pytest-cov>=4.0.0",
                "pytest-mock>=3.0.0",
                "pandas>=1.5.0",
                "numpy>=1.21.0"
            ]
        }
        
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        return manifest
    
    def _generate_run_script(self):
        """生成运行脚本"""
        run_script = self.output_dir / "run_tests.py"
        
        script_content = '''#!/usr/bin/env python3
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
'''
        
        with open(run_script, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        # 设置可执行权限
        os.chmod(run_script, 0o755)
        
        print(f"  生成运行脚本: run_tests.py")
    
    def _generate_readme(self, manifest):
        """生成README文件"""
        readme_path = self.output_dir / "README.md"
        
        readme_content = f'''# 测试套件

## 概述

这是 A股顾问系统 v{manifest["version"]} 的测试套件包。

## 统计

- **测试文件数**: {manifest["statistics"]["total_files"]}
- **总大小**: {manifest["statistics"]["total_size"] / 1024:.1f} KB
- **当前覆盖率**: {manifest["current_coverage"]}%
- **目标覆盖率**: {manifest["coverage_target"]}%

## 使用方法

### 1. 安装依赖

```bash
pip install pytest pytest-cov pytest-mock pandas numpy
```

### 2. 运行测试

```bash
# 运行所有测试
python run_tests.py

# 运行测试（不含覆盖率）
python run_tests.py --no-cov

# 安静模式
python run_tests.py -q
```

### 3. 查看覆盖率报告

运行测试后，覆盖率报告会生成在 `htmlcov/` 目录下。

## 测试模块

{chr(10).join(f"- {m}" for m in manifest["statistics"]["modules"])}

## 打包时间

{manifest["created_at"]}

## 注意事项

1. 运行测试前请确保项目根目录在 PYTHONPATH 中
2. 部分测试可能需要数据库或网络连接
3. 建议在虚拟环境中运行测试
'''
        
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        print(f"  生成README: README.md")


def main():
    """主函数"""
    packager = TestPackager()
    manifest = packager.package()
    
    print("\n" + "="*70)
    print("打包统计")
    print("="*70)
    print(f"测试文件数: {manifest['statistics']['total_files']}")
    print(f"总大小: {manifest['statistics']['total_size'] / 1024:.1f} KB")
    print(f"模块: {', '.join(manifest['statistics']['modules'])}")
    print(f"\n使用方法:")
    print(f"  cd {packager.output_dir}")
    print(f"  python run_tests.py")


if __name__ == "__main__":
    main()
