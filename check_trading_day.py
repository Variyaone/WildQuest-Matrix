#!/usr/bin/env python3
"""
检查交易日并执行ASA-Quant月常任务
"""
import sys
from datetime import datetime

def check_trading_day(date_str):
    """检查是否为交易日"""
    today = datetime.strptime(date_str, "%Y-%m-%d").date()
    weekday = today.weekday()
    is_trading_day = weekday < 5  # 周一到周五

    print(f'日期: {today}')
    print(f'星期: {"一二三四五六日"[weekday]}')
    print(f'是否交易日: {is_trading_day}')

    return is_trading_day

def main():
    # 检查今天是否为交易日
    is_trading_day = check_trading_day("2026-04-01")

    if is_trading_day:
        print('状态: 是交易日，将执行月常任务')
        print('\n月常任务列表:')
        print('1. 月线因子计算')
        print('2. 行业轮动信号')
        print('3. 策略月回测')
        print('4. 因子池清理')
        print('5. 月报生成')
        print('6. 月备份')
        print('\n注意: 需要ASA-Quant系统支持才能执行这些任务')
        return 0
    else:
        print('状态: 非交易日，跳过所有任务')
        return 1

if __name__ == "__main__":
    sys.exit(main())
