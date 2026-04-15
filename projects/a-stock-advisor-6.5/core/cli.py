"""
WildQuest Matrix - 主CLI入口

Usage:
    asa              启动交互式菜单
    asa --help       显示帮助
    asa --version    显示版本
"""

import sys


def main():
    """主CLI入口"""
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0
    
    if "--version" in sys.argv or "-v" in sys.argv:
        print("WildQuest Matrix v6.5.0")
        return 0
    
    from core.main import main as interactive_main
    return interactive_main()


if __name__ == "__main__":
    sys.exit(main())
