"""
RDAgent Menu Integration

Menu functions for RDAgent integration.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

from .runner import RDAgentRunner, RDAgentScenario
from .config import RDAgentConfig


def cmd_rdagent_factor():
    """RDAgent智能因子挖掘 - 基于微软RDAgent框架"""
    from core.main import clear_screen, show_header
    
    clear_screen()
    show_header()
    print("RDAgent 智能因子挖掘")
    print("-" * 40)
    print()
    print("微软 RDAgent 是首个以数据为中心的多智能体框架，")
    print("通过 LLM 驱动因子-模型协同优化，自动化量化策略研发。")
    print()
    print("GitHub: https://github.com/microsoft/RD-Agent")
    print("Gitee镜像: https://gitee.com/variyaone/RD-Agent")
    print()
    
    config = RDAgentConfig()
    runner = RDAgentRunner(config)
    
    health = runner.health_check()
    
    if not health["rdagent_installed"]:
        print("=" * 50)
        print("RDAgent 未安装")
        print("=" * 50)
        print()
        print(f"虚拟环境: {config.venv_path}")
        print(f"环境状态: {'✓ 存在' if health['venv_exists'] else '✗ 不存在'}")
        print()
        print("安装步骤:")
        print("  1. 创建 Python 3.10 虚拟环境:")
        print("     python3.10 -m venv .venv-rdagent")
        print("  2. 安装 RDAgent:")
        print("     .venv-rdagent/bin/pip install rdagent")
        print()
        print("系统要求:")
        print("  - Python 3.10 或 3.11")
        print("  - Docker (必须)")
        print("  - LLM API Key (OpenAI/DeepSeek/Azure/NVIDIA)")
        print()
        
        install = input("是否现在安装? (y/n): ").strip().lower()
        if install == 'y':
            print("\n请手动执行安装命令")
        
        input("\n按回车键继续...")
        return
    
    print("=" * 50)
    print("RDAgent 已安装")
    print(f"环境: {config.venv_path}")
    print("=" * 50)
    print()
    
    env_file = Path(config.env_file) if config.env_file else None
    if env_file and env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
        except Exception:
            pass
    
    print("LLM 配置状态:")
    print("-" * 40)
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        print("✓ LLM API: 已配置")
        chat_model = os.getenv("CHAT_MODEL", "未设置")
        print(f"  Chat Model: {chat_model}")
    else:
        print("✗ LLM API: 未配置")
    print()
    
    print("=" * 50)
    print("RDAgent 场景选择")
    print("=" * 50)
    print()
    print("  [1] 因子挖掘        - 自动发现新因子并生成代码")
    print("  [2] 模型设计        - 自动设计股票收益预测模型")
    print("  [3] 因子-模型协同   - 同时优化因子和预测模型")
    print("  [4] 报告因子提取    - 从金融报告提取因子想法")
    print("  [5] 论文模型提取    - 从论文提取模型架构")
    print("  [6] 启动UI          - 启动RDAgent监控界面")
    print()
    print("  [b] 返回")
    print()
    
    choice = input("请选择: ").strip().lower()
    
    if choice == "b":
        return
    
    scenarios = {
        "1": RDAgentScenario.FIN_FACTOR,
        "2": RDAgentScenario.FIN_MODEL,
        "3": RDAgentScenario.FIN_QUANT,
        "4": RDAgentScenario.FIN_FACTOR_REPORT,
        "5": RDAgentScenario.GENERAL_MODEL,
    }
    
    if choice in scenarios:
        scenario = scenarios[choice]
        extra_args = _get_scenario_args(choice)
        
        if extra_args is None:
            return
        
        print()
        print(f"正在启动 {scenario.value}...")
        print()
        
        try:
            if scenario == RDAgentScenario.FIN_FACTOR_REPORT:
                report_folder = input("请输入报告文件夹路径: ").strip()
                if not report_folder:
                    print("✗ 必须提供报告文件夹路径")
                    input("\n按回车键继续...")
                    return
                result = runner.run_fin_factor_report(report_folder)
            elif scenario == RDAgentScenario.GENERAL_MODEL:
                paper_url = input("请输入论文URL (支持arXiv): ").strip()
                if not paper_url:
                    print("✗ 必须提供论文URL")
                    input("\n按回车键继续...")
                    return
                result = runner.run_general_model(paper_url)
            else:
                result = runner.run_scenario(scenario)
            
            if result.returncode == 0:
                print("\n✓ 执行成功")
            else:
                print(f"\n✗ 执行失败: {result.stderr}")
        except Exception as e:
            print(f"\n✗ 执行出错: {e}")
        
        input("\n按回车键继续...")
    elif choice == "6":
        print("\n正在启动 UI...")
        print("访问地址: http://localhost:19899")
        print()
        
        try:
            subprocess.Popen(
                [config.get_rdagent_path(), "ui", "--port", "19899"],
                env=os.environ.copy()
            )
            print("✓ UI 已启动")
        except Exception as e:
            print(f"✗ 启动失败: {e}")
        
        input("\n按回车键继续...")


def _get_scenario_args(choice: str) -> Optional[list]:
    """获取场景参数"""
    if choice in ["1", "2", "3"]:
        print()
        print("运行配置:")
        print("  [1] 快速测试      - 1个循环 (约5-10分钟)")
        print("  [2] 标准运行      - 3个循环 (约15-30分钟)")
        print("  [3] 深度挖掘      - 10个循环 (约1-2小时)")
        print("  [4] 持续运行      - 指定时间 (如2h, 30m)")
        print("  [5] 无限运行      - 直到手动停止 (Ctrl+C)")
        print()
        
        mode = input("请选择运行模式 (默认1): ").strip() or "1"
        
        if mode == "1":
            return ["--loop-n", "1"]
        elif mode == "2":
            return ["--loop-n", "3"]
        elif mode == "3":
            return ["--loop-n", "10"]
        elif mode == "4":
            duration = input("运行时长 (如 2h, 30m, 1d): ").strip()
            if duration:
                return ["--all-duration", duration]
            return ["--loop-n", "1"]
        elif mode == "5":
            return []
        else:
            return ["--loop-n", "1"]
    
    return []
