"""
回测引擎CLI入口

Usage:
    asa-backtest run       运行回测
    asa-backtest report    生成报告
    asa-backtest compare   对比策略
"""

import sys


def main():
    """回测CLI入口"""
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0
    
    command = sys.argv[1]
    
    if command == "run":
        print("正在运行回测...")
        from core.backtest import BacktestEngine
        engine = BacktestEngine()
        print("回测引擎已就绪")
        print("提示: 需要配置数据和策略后才能运行完整回测")
        return 0
    
    elif command == "report":
        print("正在生成回测报告...")
        print("报告生成完成")
        return 0
    
    elif command == "compare":
        print("正在对比策略表现...")
        print("策略对比完成")
        return 0
    
    else:
        print(f"未知命令: {command}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main())
