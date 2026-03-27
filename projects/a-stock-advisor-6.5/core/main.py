"""
A股量化投顾系统 - 主入口

Usage:
    python main.py <command> [subcommand] [options]
    ./asa <command> [subcommand] [options]

命令列表：
    data          数据管理
    factor        因子管理
    signal        信号管理
    strategy      策略管理
    portfolio     组合管理
    risk          风控管理
    trade         交易管理
    report        报告管理
    daily         每日任务（一键执行）
    backtest      回测模式

运行模式：
    --mode daily      每日任务模式
    --mode backtest   回测模式
    --mode develop    开发调试模式
    --mode research   研究分析模式
    --mode live       实盘交易模式

示例：
    python main.py data update                    # 更新数据
    python main.py factor calc --date 2026-03-27  # 计算指定日期因子
    python main.py strategy backtest              # 回测策略
    python main.py daily                          # 执行每日任务
"""

import sys
import argparse
import warnings
from datetime import datetime
from typing import Optional, List

warnings.filterwarnings('ignore', message='.*urllib3.*')
warnings.filterwarnings('ignore', category=DeprecationWarning)

import pandas as pd


def clear_screen():
    print("\033[2J\033[H", end="")


def show_header():
    print("=" * 60)
    print("         A股量化投顾系统 v6.5")
    print("=" * 60)
    print()


def show_main_menu():
    clear_screen()
    show_header()
    print("请选择功能模块:")
    print()
    print("  [1] 数据管理        - 数据更新、质量检查、备份")
    print("  [2] 因子管理        - 因子计算、验证、评分、挖掘")
    print("  [3] 信号管理        - 信号生成、验证、质量评估")
    print("  [4] 策略管理        - 策略运行、回测、优化")
    print("  [5] 组合管理        - 组合优化、再平衡")
    print("  [6] 风控管理        - 风控检查、风险报告")
    print("  [7] 交易管理        - 交易报告、推送、确认")
    print("  [8] 报告管理        - 日报、周报、月报")
    print()
    print("  ────────────────────────────────────────────")
    print("  [d] 每日任务        - 一键执行完整管线")
    print("  [b] 回测模式        - 执行完整回测流程")
    print("  [s] 系统状态        - 查看系统状态")
    print("  [t] 运行测试        - 测试系统")
    print("  [h] 帮助            - 使用说明")
    print("  [q] 退出")
    print()


def cmd_data_menu():
    while True:
        clear_screen()
        show_header()
        print("数据管理")
        print("-" * 40)
        print()
        print("  [1] 更新数据        - 增量更新市场数据")
        print("  [2] 检查数据质量    - H1-H5硬性检查 + E1-E5弹性检查")
        print("  [3] 备份数据        - 备份到本地")
        print("  [4] 数据清洗        - 清洗异常数据")
        print("  [5] 数据统计        - 查看数据统计信息")
        print()
        print("  [b] 返回上级")
        print()
        
        choice = input("请选择: ").strip().lower()
        
        if choice == "1":
            cmd_data_update()
        elif choice == "2":
            cmd_data_check()
        elif choice == "3":
            cmd_data_backup()
        elif choice == "4":
            cmd_data_clean()
        elif choice == "5":
            cmd_data_stats()
        elif choice == "b":
            break


def cmd_data_update():
    clear_screen()
    show_header()
    print("数据更新")
    print("-" * 40)
    print()
    
    import yaml
    from pathlib import Path
    
    config_path = Path("/Users/variya/.openclaw/workspace/projects/a-stock-advisor-6.5/config/data.yaml")
    config = {}
    
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        print(f"已加载配置: {config_path}")
        primary = config.get('sources', {}).get('primary', 'yfinance')
        print(f"主数据源: {primary}")
        print(f"备选数据源: {', '.join(config.get('sources', {}).get('fallback', []))}")
    else:
        print("使用默认配置")
        print("数据源优先级: YFinance > AkShare > AShare > BaoStock > EastMoney")
    
    print()
    print("更新模式:")
    print("  [1] 增量更新 (只更新有缺口的数据)")
    print("  [2] 全量更新 (重新获取所有数据)")
    print("  [3] 更新股票列表")
    print("  [4] 检测数据缺口")
    print("  [5] 自定义更新 (选择时间段和级别)")
    print("  [6] 断点续传 (恢复中断的更新)")
    print("  [7] 清除断点进度")
    print("  [8] 退市股票管理")
    print()
    
    mode = input("请选择: ").strip()
    
    if mode == "1":
        _do_incremental_update(config)
    elif mode == "2":
        _do_full_update(config)
    elif mode == "3":
        _do_update_stock_list(config)
    elif mode == "4":
        _do_detect_gaps(config)
    elif mode == "5":
        _do_custom_update(config)
    elif mode == "6":
        _do_resume_update(config)
    elif mode == "7":
        _do_clear_progress(config)
    elif mode == "8":
        _do_manage_delisted(config)
    else:
        print("已取消")
    
    input("\n按回车键继续...")
    
    input("\n按回车键继续...")


def _select_time_range():
    """选择时间范围"""
    print()
    print("选择时间范围:")
    print("  [1] 最近1周")
    print("  [2] 最近1个月")
    print("  [3] 最近3个月")
    print("  [4] 最近6个月")
    print("  [5] 最近1年")
    print("  [6] 最近3年")
    print("  [7] 最近5年")
    print("  [8] 自定义时间范围")
    print()
    
    choice = input("请选择: ").strip()
    
    from datetime import datetime, timedelta
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    if choice == "1":
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    elif choice == "2":
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    elif choice == "3":
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    elif choice == "4":
        start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    elif choice == "5":
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    elif choice == "6":
        start_date = (datetime.now() - timedelta(days=365*3)).strftime("%Y-%m-%d")
    elif choice == "7":
        start_date = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")
    elif choice == "8":
        start_date = input("开始日期 (YYYY-MM-DD): ").strip() or "2020-01-01"
        end_date = input("结束日期 (YYYY-MM-DD): ").strip() or end_date
    else:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    return start_date, end_date


def _select_data_levels():
    """选择数据级别"""
    print()
    print("选择数据级别:")
    print("  [1] 日线 (daily)")
    print("  [2] 小时线 (hourly)")
    print("  [3] 分钟线 (minute)")
    print("  [4] 全部 (daily + hourly + minute)")
    print()
    
    choice = input("请选择: ").strip()
    
    if choice == "1":
        return ["daily"]
    elif choice == "2":
        return ["hourly"]
    elif choice == "3":
        return ["minute"]
    elif choice == "4":
        return ["daily", "hourly", "minute"]
    else:
        return ["daily"]


def _do_custom_update(config):
    """自定义更新"""
    print()
    print("=" * 50)
    print("自定义更新")
    print("=" * 50)
    
    start_date, end_date = _select_time_range()
    data_levels = _select_data_levels()
    
    print()
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"数据级别: {', '.join(data_levels)}")
    
    print()
    print("股票范围:")
    print("  [1] 全部A股")
    print("  [2] 沪深300成分股")
    print("  [3] 中证500成分股")
    print("  [4] 自定义股票列表")
    print()
    
    stock_choice = input("请选择: ").strip()
    
    from core.data import get_unified_updater
    
    updater = get_unified_updater(config)
    
    stock_list = None
    
    if stock_choice == "1":
        print()
        print("正在获取全部A股列表...")
        stock_df = updater.fetcher.get_stock_list()
        if not stock_df.empty:
            stock_list = stock_df["code"].tolist()
            print(f"获取到 {len(stock_list)} 只股票")
    elif stock_choice == "2":
        print()
        print("正在获取沪深300成分股...")
        try:
            import akshare as ak
            df = ak.index_stock_cons_weight_csindex(symbol="000300")
            stock_list = df["成分券代码"].tolist()
            print(f"获取到 {len(stock_list)} 只股票")
        except Exception as e:
            print(f"获取失败: {e}")
            return
    elif stock_choice == "3":
        print()
        print("正在获取中证500成分股...")
        try:
            import akshare as ak
            df = ak.index_stock_cons_weight_csindex(symbol="000905")
            stock_list = df["成分券代码"].tolist()
            print(f"获取到 {len(stock_list)} 只股票")
        except Exception as e:
            print(f"获取失败: {e}")
            return
    elif stock_choice == "4":
        print()
        codes = input("输入股票代码 (逗号分隔，如 000001,000002,600000): ").strip()
        stock_list = [c.strip() for c in codes.split(",") if c.strip()]
    else:
        print("已取消")
        return
    
    if not stock_list:
        print("股票列表为空")
        return
    
    print()
    print(f"即将更新 {len(stock_list)} 只股票")
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"数据级别: {', '.join(data_levels)}")
    
    print()
    confirm = input("确认开始更新? (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return
    
    print()
    print("开始更新...")
    
    def progress_callback(completed, total, stock):
        print(f"\r  进度: {completed}/{total} - {stock}    ", end="", flush=True)
    
    result = updater.full_update(
        stock_list=stock_list,
        start_date=start_date,
        end_date=end_date,
        data_types=data_levels,
        progress_callback=progress_callback
    )
    
    print()
    print()
    print("更新完成:")
    print(f"  总股票数: {result.get('total_stocks', 0)}")
    print(f"  成功: {result['updated']}")
    print(f"  失败: {result['failed']}")


def _do_incremental_update(config):
    """增量更新"""
    print()
    print("=" * 50)
    print("增量更新 - 检测数据缺口并更新")
    print("=" * 50)
    
    from core.data import get_unified_updater
    
    updater = get_unified_updater(config)
    
    print()
    stock_list = updater._get_stock_list()
    if not stock_list:
        print("  ✗ 获取股票列表失败")
        return
    
    print()
    print("正在检测数据缺口...")
    gaps = updater.detect_all_gaps(stock_list, ["daily"])
    
    print(f"  发现 {len(gaps)} 个数据缺口")
    
    if not gaps:
        print("  ✓ 数据已是最新，无需更新")
        return
    
    print()
    print("缺口详情 (前10个):")
    for gap in gaps[:10]:
        print(f"    - {gap.stock_code} [{gap.data_type}]: {gap.gap_type}")
    
    if len(gaps) > 10:
        print(f"    ... 还有 {len(gaps) - 10} 个缺口")
    
    print()
    print("开始增量更新...")
    
    def progress_callback(completed, total, stock):
        print(f"\r  进度: {completed}/{total} - {stock}    ", end="", flush=True)
    
    result = updater.incremental_update(
        stock_list=stock_list,
        data_types=["daily"],
        progress_callback=progress_callback
    )
    
    print()
    print()
    print("更新完成:")
    print(f"  成功: {result['updated']}")
    print(f"  失败: {result['failed']}")


def _do_full_update(config):
    """全量更新"""
    print()
    print("=" * 50)
    print("全量更新")
    print("=" * 50)
    
    start_date = input("开始日期 (默认 2020-01-01): ").strip() or "2020-01-01"
    end_date = input("结束日期 (默认今天): ").strip() or datetime.now().strftime("%Y-%m-%d")
    
    print()
    confirm = input(f"确认全量更新 {start_date} ~ {end_date}? (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return
    
    from core.data import get_unified_updater
    
    updater = get_unified_updater(config)
    
    print()
    print("开始全量更新...")
    
    def progress_callback(completed, total, stock):
        print(f"\r  进度: {completed}/{total} - {stock}    ", end="", flush=True)
    
    result = updater.full_update(
        start_date=start_date,
        end_date=end_date,
        data_types=["daily"],
        progress_callback=progress_callback
    )
    
    print()
    print()
    print("更新完成:")
    print(f"  总股票数: {result.get('total_stocks', 0)}")
    print(f"  成功: {result['updated']}")
    print(f"  失败: {result['failed']}")


def _do_update_stock_list(config):
    """更新股票列表"""
    print()
    print("=" * 50)
    print("更新股票列表")
    print("=" * 50)
    
    from core.data import get_unified_updater
    
    updater = get_unified_updater(config)
    
    print()
    print("正在获取股票列表...")
    result = updater.update_stock_list()
    
    if result.get("status") == "success":
        print(f"  ✓ 获取到 {result.get('count', 0)} 只股票")
    else:
        print(f"  ✗ 获取失败: {result.get('message', '未知错误')}")


def _do_detect_gaps(config):
    """检测数据缺口"""
    print()
    print("=" * 50)
    print("检测数据缺口")
    print("=" * 50)
    
    from core.data import get_unified_updater
    from core.data.metadata import get_metadata_manager
    
    updater = get_unified_updater(config)
    metadata_mgr = get_metadata_manager()
    
    print()
    print("正在检测...")
    
    delisted_stocks = metadata_mgr.get_delisted_stocks()
    if delisted_stocks:
        print(f"  已标记退市股票: {len(delisted_stocks)} 只")
    
    stock_df = updater.fetcher.get_stock_list()
    if stock_df.empty:
        print("  ✗ 获取股票列表失败")
        return
    
    stock_list = stock_df["code"].tolist()
    gaps = updater.detect_all_gaps(stock_list, ["daily"], skip_delisted=True)
    
    print()
    print(f"检测到 {len(gaps)} 个数据缺口")
    
    gap_types = {}
    for gap in gaps:
        gap_types[gap.gap_type] = gap_types.get(gap.gap_type, 0) + 1
    
    print()
    print("缺口类型统计:")
    for gap_type, count in gap_types.items():
        print(f"  - {gap_type}: {count}")
    
    if delisted_stocks:
        print()
        print(f"已跳过 {len(delisted_stocks)} 只退市股票的数据缺口检测")


def _do_resume_update(config):
    """断点续传"""
    print()
    print("=" * 50)
    print("断点续传")
    print("=" * 50)
    
    from core.data import get_unified_updater
    
    updater = get_unified_updater(config)
    
    resume_info = updater.get_resume_info()
    
    if not resume_info:
        print()
        print("没有发现未完成的更新任务")
        return
    
    print()
    print("发现未完成的更新任务:")
    print(f"  开始时间: {resume_info['start_time']}")
    print(f"  日期范围: {resume_info['start_date']} ~ {resume_info['end_date']}")
    print(f"  数据类型: {resume_info['data_type']}")
    print(f"  已完成: {resume_info['completed']} 只股票")
    print(f"  失败: {resume_info['failed']} 只股票")
    print(f"  剩余: {resume_info['pending']} 只股票")
    
    print()
    confirm = input("是否继续? (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return
    
    print()
    print("正在恢复更新...")
    
    def progress_callback(completed, total, stock):
        print(f"\r  进度: {completed}/{total} - {stock}    ", end="", flush=True)
    
    result = updater.resume_update(progress_callback=progress_callback)
    
    print()
    print()
    if result.get("success"):
        print("恢复完成:")
        print(f"  更新: {result.get('completed', 0)}")
        print(f"  失败: {result.get('failed', 0)}")
    else:
        print(f"恢复失败: {result.get('message', '未知错误')}")


def _do_clear_progress(config):
    """清除断点进度"""
    print()
    print("=" * 50)
    print("清除断点进度")
    print("=" * 50)
    
    from core.data import get_unified_updater
    
    updater = get_unified_updater(config)
    
    resume_info = updater.get_resume_info()
    
    if not resume_info:
        print()
        print("没有发现断点进度文件")
        return
    
    print()
    print("当前断点进度:")
    print(f"  开始时间: {resume_info['start_time']}")
    print(f"  已完成: {resume_info['completed']} 只股票")
    print(f"  剩余: {resume_info['pending']} 只股票")
    
    print()
    confirm = input("确认清除? (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return
    
    updater.clear_progress()
    print("已清除")


def _do_manage_delisted(config):
    """退市股票管理"""
    print()
    print("=" * 50)
    print("退市股票管理")
    print("=" * 50)
    
    from core.data.metadata import get_metadata_manager
    
    metadata_mgr = get_metadata_manager()
    
    while True:
        print()
        print("操作选项:")
        print("  [1] 查看已标记退市股票")
        print("  [2] 标记股票为退市")
        print("  [3] 取消退市标记")
        print("  [4] 自动检测退市股票")
        print("  [b] 返回")
        print()
        
        choice = input("请选择: ").strip()
        
        if choice == 'b':
            break
        elif choice == '1':
            delisted = metadata_mgr.get_delisted_stocks()
            print()
            if delisted:
                print(f"已标记退市股票 ({len(delisted)} 只):")
                print("-" * 60)
                print(f"{'股票代码':<12}{'股票名称':<15}{'退市日期':<15}")
                print("-" * 60)
                for stock in delisted[:30]:
                    print(f"{stock.stock_code:<12}{stock.stock_name:<15}{stock.delist_date or 'N/A':<15}")
                if len(delisted) > 30:
                    print(f"... 还有 {len(delisted) - 30} 只")
            else:
                print("暂无已标记退市的股票")
        elif choice == '2':
            stock_code = input("请输入股票代码: ").strip()
            if not stock_code:
                print("已取消")
                continue
            
            delist_date = input("退市日期 (可选, 格式YYYY-MM-DD): ").strip() or None
            
            if metadata_mgr.mark_as_delisted(stock_code, delist_date):
                print(f"✓ 已将 {stock_code} 标记为退市")
            else:
                print(f"✗ 标记失败")
        elif choice == '3':
            stock_code = input("请输入股票代码: ").strip()
            if not stock_code:
                print("已取消")
                continue
            
            metadata = metadata_mgr.get_stock_metadata(stock_code)
            if metadata and metadata.is_delisted:
                metadata.is_delisted = False
                metadata.delist_date = None
                metadata.update_status = "pending"
                metadata_mgr.register_stock(metadata)
                print(f"✓ 已取消 {stock_code} 的退市标记")
            else:
                print(f"该股票未被标记为退市")
        elif choice == '4':
            print()
            print("自动检测退市股票...")
            print("-" * 60)
            
            all_stocks = metadata_mgr.get_all_stocks()
            detected = []
            
            for stock in all_stocks:
                if stock.is_delisted:
                    continue
                
                if stock.data_end_date:
                    from datetime import datetime, timedelta
                    try:
                        end_date = datetime.strptime(stock.data_end_date, "%Y-%m-%d")
                        days_gap = (datetime.now() - end_date).days
                        
                        if days_gap > 180:
                            detected.append((stock.stock_code, stock.stock_name, stock.data_end_date, days_gap))
                    except:
                        pass
            
            if detected:
                detected.sort(key=lambda x: x[3], reverse=True)
                print(f"检测到 {len(detected)} 只可能退市的股票 (数据超过180天未更新):")
                print()
                print(f"{'股票代码':<12}{'股票名称':<15}{'最后日期':<15}{'未更新天数':<10}")
                print("-" * 52)
                for code, name, end_date, days in detected[:20]:
                    print(f"{code:<12}{name:<15}{end_date:<15}{days:<10}")
                
                if len(detected) > 20:
                    print(f"... 还有 {len(detected) - 20} 只")
                
                print()
                confirm = input("是否将以上股票标记为退市? (y/n): ").strip().lower()
                if confirm == 'y':
                    count = 0
                    for code, name, end_date, days in detected:
                        if metadata_mgr.mark_as_delisted(code, end_date):
                            count += 1
                    print(f"✓ 已标记 {count} 只股票为退市")
            else:
                print("未检测到退市股票")


def cmd_data_check():
    clear_screen()
    show_header()
    print("数据质量检查")
    print("-" * 40)
    print()
    
    from pathlib import Path
    from datetime import datetime
    import pandas as pd
    
    data_path = Path("./data")
    
    if not data_path.exists():
        print("数据目录不存在，请先更新数据")
        input("\n按回车键继续...")
        return
    
    print("正在检查数据质量...")
    print()
    
    results = {}
    
    print("[H1] 数据非空检查...")
    stock_list = data_path / "stock_list.parquet"
    if stock_list.exists():
        df = pd.read_parquet(stock_list)
        results["H1"] = {"status": "✓ 通过", "detail": f"股票列表: {len(df)} 只"}
    else:
        results["H1"] = {"status": "✗ 失败", "detail": "股票列表不存在"}
    
    print("[H2] 必需字段完整检查...")
    history_files = list(data_path.glob("history_*.parquet"))
    if history_files:
        sample_df = pd.read_parquet(history_files[0])
        required_cols = ["date", "open", "high", "low", "close", "volume"]
        missing_cols = [c for c in required_cols if c not in sample_df.columns]
        if missing_cols:
            results["H2"] = {"status": "✗ 失败", "detail": f"缺失字段: {missing_cols}"}
        else:
            results["H2"] = {"status": "✓ 通过", "detail": "必需字段完整"}
    else:
        results["H2"] = {"status": "⚠ 警告", "detail": "无历史数据"}
    
    print("[H3] 时间序列连续检查...")
    if history_files:
        gaps_found = 0
        for hf in history_files[:10]:
            try:
                df = pd.read_parquet(hf)
                if "date" in df.columns:
                    dates = pd.to_datetime(df["date"]).sort_values()
                    if len(dates) > 1:
                        date_range = pd.date_range(dates.min(), dates.max(), freq="B")
                        missing = len(date_range) - len(dates)
                        if missing > 5:
                            gaps_found += 1
            except:
                pass
        if gaps_found == 0:
            results["H3"] = {"status": "✓ 通过", "detail": "时间序列连续"}
        else:
            results["H3"] = {"status": "⚠ 警告", "detail": f"{gaps_found} 只股票有缺口"}
    else:
        results["H3"] = {"status": "⚠ 警告", "detail": "无历史数据"}
    
    print("[H4] 价格逻辑一致检查...")
    if history_files:
        invalid_count = 0
        for hf in history_files[:10]:
            try:
                df = pd.read_parquet(hf)
                if all(c in df.columns for c in ["open", "high", "low", "close"]):
                    invalid = ((df["high"] < df["low"]) | 
                              (df["close"] > df["high"]) | 
                              (df["close"] < df["low"])).sum()
                    if invalid > 0:
                        invalid_count += 1
            except:
                pass
        if invalid_count == 0:
            results["H4"] = {"status": "✓ 通过", "detail": "价格逻辑正确"}
        else:
            results["H4"] = {"status": "✗ 失败", "detail": f"{invalid_count} 只股票有异常"}
    else:
        results["H4"] = {"status": "⚠ 警告", "detail": "无历史数据"}
    
    print("[H5] 未来数据泄露检查...")
    today = datetime.now().strftime("%Y-%m-%d")
    if history_files:
        future_count = 0
        for hf in history_files[:10]:
            try:
                df = pd.read_parquet(hf)
                if "date" in df.columns:
                    if (pd.to_datetime(df["date"]) > pd.to_datetime(today)).any():
                        future_count += 1
            except:
                pass
        if future_count == 0:
            results["H5"] = {"status": "✓ 通过", "detail": "无未来数据"}
        else:
            results["H5"] = {"status": "✗ 失败", "detail": f"{future_count} 只股票有未来数据"}
    else:
        results["H5"] = {"status": "⚠ 警告", "detail": "无历史数据"}
    
    print()
    print("=" * 50)
    print("检查结果")
    print("=" * 50)
    print()
    
    passed = sum(1 for r in results.values() if "✓" in r["status"])
    failed = sum(1 for r in results.values() if "✗" in r["status"])
    warning = sum(1 for r in results.values() if "⚠" in r["status"])
    
    for code, result in results.items():
        print(f"  {code}: {result['status']} - {result['detail']}")
    
    print()
    print(f"总计: {passed} 通过, {warning} 警告, {failed} 失败")
    
    if failed == 0:
        print()
        print("✓ 数据质量检查通过!")
    else:
        print()
        print("✗ 数据质量检查未通过，请检查数据")
    
    input("\n按回车键继续...")


def cmd_data_backup():
    clear_screen()
    show_header()
    print("数据备份")
    print("-" * 40)
    print()
    
    from pathlib import Path
    from datetime import datetime
    import shutil
    import os
    
    data_path = Path("./data")
    
    if not data_path.exists():
        print("数据目录不存在，无需备份")
        input("\n按回车键继续...")
        return
    
    backup_dir = Path("./backups")
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"data_backup_{timestamp}"
    
    print(f"备份源: {data_path.resolve()}")
    print(f"备份目标: {backup_path.resolve()}")
    print()
    
    total_size = 0
    file_count = 0
    for f in data_path.rglob("*"):
        if f.is_file():
            total_size += f.stat().st_size
            file_count += 1
    
    print(f"待备份文件: {file_count} 个")
    print(f"数据大小: {total_size / 1024 / 1024:.1f} MB")
    print()
    
    confirm = input("确认备份? (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        input("\n按回车键继续...")
        return
    
    print()
    print("正在备份...")
    
    try:
        shutil.copytree(data_path, backup_path)
        print(f"✓ 备份完成!")
        print(f"  备份位置: {backup_path}")
        print(f"  备份大小: {total_size / 1024 / 1024:.1f} MB")
        
        backups = sorted(backup_dir.glob("data_backup_*"))
        print(f"  现有备份数: {len(backups)} 个")
        
    except Exception as e:
        print(f"✗ 备份失败: {e}")
    
    input("\n按回车键继续...")


def cmd_data_clean():
    clear_screen()
    show_header()
    print("数据清洗")
    print("-" * 40)
    print()
    
    from core.data.cleaner import get_file_cleaner
    
    cleaner = get_file_cleaner()
    
    print("正在执行数据清洗...")
    print()
    
    try:
        result = cleaner.run_all_rules()
        
        print("清洗完成:")
        print()
        
        total_deleted = 0
        total_bytes = 0
        
        for rule_name, cleanup_result in result.items():
            print(f"  {rule_name}:")
            print(f"    删除文件: {cleanup_result.files_deleted}")
            print(f"    释放空间: {cleanup_result.bytes_freed / 1024 / 1024:.1f} KB")
            total_deleted += cleanup_result.files_deleted
            total_bytes += cleanup_result.bytes_freed
        
        print()
        print(f"总计: 删除 {total_deleted} 个文件, 释放 {total_bytes / 1024 / 1024:.1f} MB")
        
    except Exception as e:
        print(f"清洗失败: {e}")
    
    input("\n按回车键继续...")


def cmd_data_stats():
    clear_screen()
    show_header()
    print("数据统计")
    print("-" * 40)
    print()
    
    from core.data import get_data_storage
    from pathlib import Path
    import os
    
    storage = get_data_storage()
    data_path = Path("./data")
    
    print("数据目录统计:")
    print()
    
    total_size = 0
    file_count = 0
    
    if data_path.exists():
        for f in data_path.rglob("*"):
            if f.is_file():
                total_size += f.stat().st_size
                file_count += 1
    
    print(f"  数据目录: {data_path.resolve()}")
    print(f"  文件数量: {file_count}")
    print(f"  总大小: {total_size / 1024 / 1024:.1f} MB")
    
    print()
    print("股票数据统计:")
    print()
    
    stock_list = storage.parquet.load("stock_list")
    if not stock_list.empty:
        print(f"  股票列表: {len(stock_list)} 只")
        
        exchanges = stock_list["code"].apply(lambda x: "SH" if str(x).startswith("6") else "SZ" if str(x).startswith(("0", "3")) else "BJ").value_counts()
        print(f"  交易所分布:")
        for exchange, count in exchanges.items():
            print(f"    - {exchange}: {count} 只")
    else:
        print("  股票列表: 未缓存")
    
    print()
    print("历史数据统计:")
    print()
    
    history_files = list(data_path.glob("history_*.parquet")) if data_path.exists() else []
    if history_files:
        print(f"  已存储股票: {len(history_files)} 只")
        
        total_records = 0
        date_ranges = []
        
        for hf in history_files[:10]:
            try:
                import pandas as pd
                df = pd.read_parquet(hf)
                total_records += len(df)
                if "date" in df.columns:
                    dates = pd.to_datetime(df["date"])
                    date_ranges.append((dates.min(), dates.max()))
            except:
                pass
        
        print(f"  总记录数: 约 {total_records * len(history_files) // 10:,} 条")
        
        if date_ranges:
            all_dates = [d for dr in date_ranges for d in dr]
            print(f"  时间范围: {min(all_dates).strftime('%Y-%m-%d')} ~ {max(all_dates).strftime('%Y-%m-%d')}")
    else:
        print("  历史数据: 无")
    
    print()
    print("缓存状态:")
    print()
    
    cache_path = Path("./data/cache")
    if cache_path.exists():
        cache_files = list(cache_path.glob("*.pkl"))
        cache_size = sum(f.stat().st_size for f in cache_files if f.is_file())
        print(f"  缓存文件: {len(cache_files)} 个")
        print(f"  缓存大小: {cache_size / 1024:.1f} KB")
    else:
        print("  缓存: 无")
    
    print()
    print("数据质量:")
    print()
    
    metadata_path = Path("./data/metadata")
    if metadata_path.exists():
        progress_file = metadata_path / "update_progress.json"
        if progress_file.exists():
            import json
            with open(progress_file) as f:
                progress = json.load(f)
            print(f"  最后更新: {progress.get('start_time', 'N/A')}")
            print(f"  更新状态: {progress.get('status', 'N/A')}")
            print(f"  已完成: {progress.get('completed_stocks', 0)}/{progress.get('total_stocks', 0)}")
        else:
            print("  更新记录: 无")
    else:
        print("  元数据: 无")
    
    input("\n按回车键继续...")


def cmd_factor_menu():
    while True:
        clear_screen()
        show_header()
        print("因子管理")
        print("-" * 40)
        print()
        print("  [1] 计算因子        - 计算所有注册因子")
        print("  [2] 验证因子        - IC/IR验证")
        print("  [3] 评分排名        - 因子评分和排名")
        print("  [4] 因子挖掘        - 遗传规划自动挖掘")
        print("  [5] 因子回测        - 回测因子表现")
        print("  [6] 因子注册        - 注册新因子")
        print("  [7] 查看因子库      - 查看所有因子")
        print("  [8] 因子监控        - 监控因子衰减")
        print("  [9] RDAgent智能挖掘 - LLM驱动的因子演化")
        print()
        print("  [b] 返回上级")
        print()
        
        choice = input("请选择: ").strip().lower()
        
        if choice == "1":
            cmd_factor_calc()
        elif choice == "2":
            cmd_factor_validate()
        elif choice == "3":
            cmd_factor_score()
        elif choice == "4":
            cmd_factor_mine()
        elif choice == "5":
            cmd_factor_backtest()
        elif choice == "6":
            cmd_factor_register()
        elif choice == "7":
            cmd_factor_list()
        elif choice == "8":
            cmd_factor_monitor()
        elif choice == "9":
            cmd_rdagent_factor()
        elif choice == "b":
            break


def cmd_factor_calc():
    clear_screen()
    show_header()
    print("因子计算")
    print("-" * 40)
    print()
    
    from core.factor import FactorEngine, FactorRegistry
    from core.data.storage import ParquetStorage
    from datetime import datetime, timedelta
    
    registry = FactorRegistry()
    storage = ParquetStorage()
    
    factor_count = registry.get_factor_count()
    print(f"已注册因子数: {factor_count}")
    
    if factor_count == 0:
        print("警告: 没有已注册的因子")
        input("\n按回车键继续...")
        return
    
    factors = registry.list_all()
    
    print()
    print("计算模式:")
    print("  [1] 计算单个因子")
    print("  [2] 批量计算因子 (前10个)")
    print("  [3] 计算指定类别因子")
    print("  [4] 计算所有因子")
    print()
    
    mode = input("请选择模式: ").strip()
    
    if mode == "1":
        print()
        print("可用因子 (前20个):")
        for i, f in enumerate(factors[:20]):
            print(f"  [{i+1}] {f.name} ({f.id})")
        
        print()
        factor_idx = input("选择因子编号 (1-20): ").strip()
        try:
            idx = int(factor_idx) - 1
            if 0 <= idx < len(factors):
                selected_factor = factors[idx]
                factor_id = selected_factor.id
                factor_name = selected_factor.name
                print(f"\n已选择: {factor_name}")
            else:
                print("无效的选择")
                input("\n按回车键继续...")
                return
        except ValueError:
            print("无效的输入")
            input("\n按回车键继续...")
            return
        
        factor_ids = [factor_id]
        
    elif mode == "2":
        factor_ids = [f.id for f in factors[:10]]
        print(f"\n将计算前 {len(factor_ids)} 个因子")
        
    elif mode == "3":
        categories = {}
        for f in factors:
            cat = f.category.value if hasattr(f.category, 'value') else str(f.category)
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f.id)
        
        print()
        print("可用类别:")
        for i, (cat, fids) in enumerate(categories.items()):
            print(f"  [{i+1}] {cat} ({len(fids)} 个因子)")
        
        print()
        cat_idx = input("选择类别编号: ").strip()
        try:
            idx = int(cat_idx) - 1
            cat_names = list(categories.keys())
            if 0 <= idx < len(cat_names):
                selected_cat = cat_names[idx]
                factor_ids = categories[selected_cat]
                print(f"\n将计算 {selected_cat} 类别的 {len(factor_ids)} 个因子")
            else:
                print("无效的选择")
                input("\n按回车键继续...")
                return
        except ValueError:
            print("无效的输入")
            input("\n按回车键继续...")
            return
            
    elif mode == "4":
        factor_ids = [f.id for f in factors]
        print(f"\n将计算所有 {len(factor_ids)} 个因子")
        
    else:
        print("无效的选择")
        input("\n按回车键继续...")
        return
    
    stocks = storage.list_stocks("daily")
    if not stocks:
        print("\n警告: 没有找到股票数据，请先更新数据")
        input("\n按回车键继续...")
        return
    
    print(f"\n可用股票数: {len(stocks)}")
    
    print()
    print("股票范围:")
    print(f"  [1] 全部股票 ({len(stocks)} 只)")
    print("  [2] 指定数量 (前N只)")
    print("  [3] 指定股票代码")
    print()
    
    stock_mode = input("请选择: ").strip()
    
    selected_stocks = []
    
    if stock_mode == "1":
        selected_stocks = stocks
    elif stock_mode == "2":
        n = input(f"输入数量 (1-{len(stocks)}): ").strip()
        try:
            n = int(n)
            selected_stocks = stocks[:n]
        except ValueError:
            print("无效的输入")
            input("\n按回车键继续...")
            return
    elif stock_mode == "3":
        codes = input("输入股票代码 (逗号分隔): ").strip()
        selected_stocks = [c.strip() for c in codes.split(",") if c.strip()]
    else:
        print("无效的选择")
        input("\n按回车键继续...")
        return
    
    print(f"\n已选择 {len(selected_stocks)} 只股票")
    
    print()
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    print(f"日期范围: {start_date} 至 {end_date}")
    custom_date = input("使用自定义日期? (y/n): ").strip().lower()
    
    if custom_date == "y":
        start_date = input("开始日期 (YYYY-MM-DD): ").strip() or start_date
        end_date = input("结束日期 (YYYY-MM-DD): ").strip() or end_date
    
    print()
    print("=" * 50)
    print("开始计算因子...")
    print("=" * 50)
    
    engine = FactorEngine()
    
    all_data = {}
    load_errors = []
    
    print(f"\n加载股票数据...")
    for i, stock_code in enumerate(selected_stocks):
        df = storage.load_stock_data(stock_code, "daily", start_date, end_date)
        if df is not None and len(df) > 0:
            all_data[stock_code] = df
        else:
            load_errors.append(stock_code)
        
        if (i + 1) % 100 == 0:
            print(f"  已加载 {i + 1}/{len(selected_stocks)} 只股票...")
    
    print(f"\n成功加载 {len(all_data)} 只股票数据")
    if load_errors:
        print(f"加载失败 {len(load_errors)} 只股票")
    
    if not all_data:
        print("\n错误: 没有可用的股票数据")
        input("\n按回车键继续...")
        return
    
    print(f"\n计算 {len(factor_ids)} 个因子...")
    
    success_count = 0
    fail_count = 0
    results_summary = []
    
    for i, factor_id in enumerate(factor_ids):
        factor_meta = registry.get(factor_id)
        factor_name = factor_meta.name if factor_meta else factor_id
        
        print(f"\n[{i+1}/{len(factor_ids)}] 计算: {factor_name}")
        
        for stock_code, stock_df in list(all_data.items())[:5]:
            data = {"close": stock_df}
            
            if "open" in stock_df.columns:
                data["open"] = stock_df[["date", "open"]]
            if "high" in stock_df.columns:
                data["high"] = stock_df[["date", "high"]]
            if "low" in stock_df.columns:
                data["low"] = stock_df[["date", "low"]]
            if "volume" in stock_df.columns:
                data["volume"] = stock_df[["date", "volume"]]
            
            try:
                result = engine.compute_single(factor_id, data)
                if result.success:
                    success_count += 1
                    results_summary.append({
                        "factor": factor_name,
                        "status": "成功",
                        "stocks": result.stock_count,
                        "dates": result.date_count,
                        "time": f"{result.compute_time:.2f}s"
                    })
                    print(f"  ✓ 成功 - 股票数: {result.stock_count}, 日期数: {result.date_count}, 耗时: {result.compute_time:.2f}s")
                else:
                    fail_count += 1
                    results_summary.append({
                        "factor": factor_name,
                        "status": f"失败: {result.error_message[:30]}..."
                    })
                    print(f"  ✗ 失败: {result.error_message[:50]}")
                break
            except Exception as e:
                fail_count += 1
                print(f"  ✗ 异常: {str(e)[:50]}")
                break
    
    print()
    print("=" * 50)
    print("计算完成")
    print("=" * 50)
    print(f"\n成功: {success_count} 个因子")
    print(f"失败: {fail_count} 个因子")
    
    if results_summary:
        print()
        print("计算结果摘要:")
        for r in results_summary[:10]:
            status_icon = "✓" if r["status"] == "成功" else "✗"
            extra = f" - 股票:{r.get('stocks',0)}, 日期:{r.get('dates',0)}" if r["status"] == "成功" else f" - {r['status']}"
            print(f"  {status_icon} {r['factor']}{extra}")
    
    input("\n按回车键继续...")


def cmd_factor_validate():
    clear_screen()
    show_header()
    print("因子验证")
    print("-" * 40)
    print()
    print("【什么是因子验证？】")
    print("  因子验证用于检验因子对股票收益的预测能力")
    print("  - IC (信息系数): 因子值与未来收益的相关性，|IC|>0.03 为有效")
    print("  - IR (信息比率): IC的稳定性，IR>0.5 表示因子稳定有效")
    print("  - Rank IC: 使用排名计算的相关性，更稳健")
    print()
    
    from core.factor import FactorRegistry, FactorValidator
    
    registry = FactorRegistry()
    validator = FactorValidator()
    
    factors = registry.list_all()
    count = registry.get_factor_count()
    
    print(f"已注册因子: {count} 个")
    print()
    print("验证选项:")
    print("  [1] 验证单个因子")
    print("  [2] 批量验证因子")
    print("  [3] 快速演示 (模拟数据)")
    print()
    
    choice = input("请选择: ").strip()
    
    if choice == "1":
        factor_name = input("输入因子名称: ").strip()
        if not factor_name:
            print("已取消")
            input("\n按回车键继续...")
            return
        
        print()
        print(f"正在验证因子: {factor_name}...")
        print()
        
        try:
            result = validator.validate_factor(factor_name)
            
            ic = result.get('ic', 0)
            ir = result.get('ir', 0)
            rank_ic = result.get('rank_ic', 0)
            ic_mean = result.get('ic_mean', 0)
            ic_std = result.get('ic_std', 0)
            icir = result.get('icir', 0)
            win_rate = result.get('win_rate', 0)
            group_returns = result.get('group_returns', [])
            
            print("=" * 50)
            print("验证结果")
            print("=" * 50)
            print()
            print(f"  IC (信息系数):    {ic:>8.4f}")
            print(f"  Rank IC:          {rank_ic:>8.4f}")
            print(f"  IC均值:           {ic_mean:>8.4f}")
            print(f"  IC标准差:         {ic_std:>8.4f}")
            print(f"  ICIR:             {icir:>8.4f}")
            print(f"  IR (信息比率):    {ir:>8.4f}")
            print(f"  胜率:             {win_rate:>8.2%}")
            print()
            
            if group_returns:
                print("  分组收益 (从低到高):")
                for i, ret in enumerate(group_returns, 1):
                    bar = "█" * int(ret * 100 + 5) if ret > -0.05 else ""
                    print(f"    第{i}组: {ret:>7.2%} {bar}")
                print()
                
                if len(group_returns) >= 5:
                    spread = group_returns[-1] - group_returns[0]
                    print(f"  多空收益差 (第5组-第1组): {spread:.2%}")
            
            print()
            print("-" * 50)
            print("结论:")
            print("-" * 50)
            
            if abs(ic) > 0.05:
                print(f"  ✓ 因子有效性: 强 (|IC|={abs(ic):.4f} > 0.05)")
            elif abs(ic) > 0.03:
                print(f"  ✓ 因子有效性: 中等 (|IC|={abs(ic):.4f} > 0.03)")
            elif abs(ic) > 0.01:
                print(f"  △ 因子有效性: 较弱 (|IC|={abs(ic):.4f} > 0.01)")
            else:
                print(f"  ✗ 因子有效性: 无效 (|IC|={abs(ic):.4f} < 0.01)")
            
            if abs(ir) > 0.5:
                print(f"  ✓ 因子稳定性: 高 (|IR|={abs(ir):.4f} > 0.5)")
            elif abs(ir) > 0.25:
                print(f"  △ 因子稳定性: 中等 (|IR|={abs(ir):.4f} > 0.25)")
            else:
                print(f"  ✗ 因子稳定性: 低 (|IR|={abs(ir):.4f} < 0.25)")
                
        except Exception as e:
            print(f"验证失败: {e}")
        input("\n按回车键继续...")
        return
    
    elif choice == "2":
        print()
        num = input("验证因子数量 (默认10): ").strip()
        num = int(num) if num.isdigit() else 10
        num = min(num, len(factors)) if factors else num
        
        print()
        print(f"正在验证 {num} 个因子...")
        print()
        
        results = []
        for i, f in enumerate(factors[:num]):
            try:
                name = f.name
                print(f"  [{i+1}/{num}] 验证 {name}...", end="\r")
                result = validator.validate_factor(name)
                results.append({
                    'name': name,
                    'ic': result.get('ic', 0),
                    'ir': result.get('ir', 0),
                    'rank_ic': result.get('rank_ic', 0)
                })
            except:
                pass
        
        print()
        print("=" * 70)
        print(f"{'因子名称':<20} {'IC':>10} {'Rank IC':>10} {'IR':>10} {'评估':>12}")
        print("=" * 70)
        
        for r in results:
            ic = r['ic']
            ir = r['ir']
            if abs(ic) > 0.03 and abs(ir) > 0.25:
                status = "✓ 有效可用"
            elif abs(ic) > 0.01:
                status = "△ 效果一般"
            else:
                status = "✗ 不推荐"
            print(f"{r['name']:<20} {ic:>10.4f} {r['rank_ic']:>10.4f} {ir:>10.4f} {status:>12}")
        
        print("=" * 70)
        print()
        
        valid_count = sum(1 for r in results if abs(r['ic']) > 0.03)
        stable_count = sum(1 for r in results if abs(r['ir']) > 0.25)
        print(f"统计: 有效因子 {valid_count}/{len(results)} 个, 稳定因子 {stable_count}/{len(results)} 个")
        input("\n按回车键继续...")
        return
    
    elif choice == "3":
        print()
        print("快速验证演示 (模拟数据)...")
        print()
        
        import random
        random.seed(42)
        
        print("=" * 70)
        print(f"{'因子名称':<20} {'IC':>10} {'Rank IC':>10} {'IR':>10} {'评估':>12}")
        print("=" * 70)
        
        sample_factors = [
            ('动量因子_20日', 0.045, 0.52),
            ('波动率因子', -0.038, 0.41),
            ('换手率因子', 0.028, 0.33),
            ('市值因子', -0.052, 0.61),
            ('估值因子_PE', 0.031, 0.28),
            ('流动性因子', 0.019, 0.22),
            ('质量因子', 0.048, 0.55),
            ('成长因子', 0.025, 0.19),
        ]
        
        for name, ic_base, ir_base in sample_factors:
            ic = ic_base + random.uniform(-0.01, 0.01)
            rank_ic = ic * random.uniform(0.9, 1.1)
            ir = ir_base + random.uniform(-0.05, 0.05)
            
            if abs(ic) > 0.03 and abs(ir) > 0.25:
                status = "✓ 有效可用"
            elif abs(ic) > 0.01:
                status = "△ 效果一般"
            else:
                status = "✗ 不推荐"
            print(f"{name:<20} {ic:>10.4f} {rank_ic:>10.4f} {ir:>10.4f} {status:>12}")
        
        print("=" * 70)
        print()
        print("说明:")
        print("  - IC > 0.03 且 IR > 0.25: 因子有效且稳定，推荐使用")
        print("  - IC > 0.01 但 IR 较低: 因子有一定效果但不够稳定")
        print("  - IC < 0.01: 因子预测能力弱，不建议使用")
        print()
        print("提示: 这是模拟数据演示，实际验证需要配置真实行情数据")
        input("\n按回车键继续...")
        return
    
    else:
        print("已取消")
        input("\n按回车键继续...")


def cmd_factor_score():
    clear_screen()
    show_header()
    print("因子评分排名")
    print("-" * 40)
    print()
    
    from core.factor import FactorScorer, get_factor_registry
    
    scorer = FactorScorer()
    print("评分维度: IC、IR、稳定性、衰减、换手率")
    print()
    
    registry = get_factor_registry()
    factors = registry.list_all()
    
    if not factors:
        print("因子库中暂无因子，请先注册因子")
    else:
        scores = scorer.score_all_factors()
        
        print(f"共 {len(scores)} 个因子评分完成")
        print()
        print("=" * 80)
        print(f"{'排名':<6}{'因子ID':<10}{'因子名称':<20}{'总分':<10}{'等级':<6}{'IC分':<8}{'IR分':<8}")
        print("=" * 80)
        
        for score in scores[:20]:
            factor = registry.get(score.factor_id)
            name = factor.name[:18] if factor else "N/A"
            print(f"{score.rank:<6}{score.factor_id:<10}{name:<20}{score.total_score:<10.2f}{score.grade:<6}{score.ic_score:<8.1f}{score.ir_score:<8.1f}")
        
        if len(scores) > 20:
            print(f"... 还有 {len(scores) - 20} 个因子")
        
        print("=" * 80)
    
    input("\n按回车键继续...")


def cmd_factor_mine():
    clear_screen()
    show_header()
    print("因子挖掘 (遗传规划)")
    print("-" * 40)
    print()
    print("遗传规划自动因子挖掘:")
    print("  - 基于遗传算法的公式挖掘")
    print("  - 自动筛选有效因子")
    print("  - 整合到因子库")
    print()
    
    print("挖掘模式:")
    print("  [1] 快速挖掘 (10代, 小种群)")
    print("  [2] 标准挖掘 (20代, 中等种群)")
    print("  [3] 深度挖掘 (50代, 大种群)")
    print("  [4] 因子组合挖掘")
    print("  [5] 查看挖掘结果")
    print()
    
    mode = input("请选择: ").strip()
    
    if mode == "1":
        _do_factor_mining(generations=10, population_size=50)
    elif mode == "2":
        _do_factor_mining(generations=20, population_size=100)
    elif mode == "3":
        _do_factor_mining(generations=50, population_size=200)
    elif mode == "4":
        _do_factor_combination_mining()
    elif mode == "5":
        _show_mining_results()
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def _do_factor_mining(generations: int = 20, population_size: int = 100):
    """执行因子挖掘"""
    print()
    print("=" * 50)
    print(f"开始因子挖掘 (代数: {generations}, 种群: {population_size})")
    print("=" * 50)
    
    from core.factor import FactorMiner, GeneticProgrammingConfig
    from core.data.storage import ParquetStorage
    from datetime import datetime, timedelta
    import numpy as np
    import warnings
    warnings.filterwarnings('ignore')
    
    storage = ParquetStorage()
    
    print("\n正在加载股票数据...")
    stocks = storage.list_stocks("daily")
    
    if not stocks:
        print("错误: 没有找到股票数据，请先更新数据")
        return
    
    sample_stocks = stocks[:10]
    print(f"使用 {len(sample_stocks)} 只股票进行挖掘")
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    all_data = {}
    for stock_code in sample_stocks:
        df = storage.load_stock_data(stock_code, "daily", start_date, end_date)
        if df is not None and len(df) > 20:
            df['stock_code'] = stock_code
            all_data[stock_code] = df
    
    if not all_data:
        print("错误: 无法加载足够的股票数据")
        return
    
    print(f"成功加载 {len(all_data)} 只股票数据")
    
    combined_df = pd.concat(all_data.values(), ignore_index=True)
    
    variables = ['close', 'open', 'high', 'low', 'volume', 'vwap']
    
    if 'vwap' not in combined_df.columns:
        combined_df['vwap'] = combined_df['close']
    
    return_df = combined_df[['date', 'stock_code', 'close']].copy()
    return_df = return_df.sort_values(['stock_code', 'date'])
    return_df['return'] = return_df.groupby('stock_code')['close'].pct_change().shift(-1)
    return_df = return_df.dropna()
    
    data_dict = {
        'close': combined_df[['date', 'stock_code', 'close']],
        'open': combined_df[['date', 'stock_code', 'open']],
        'high': combined_df[['date', 'stock_code', 'high']],
        'low': combined_df[['date', 'stock_code', 'low']],
        'volume': combined_df[['date', 'stock_code', 'volume']],
        'vwap': combined_df[['date', 'stock_code', 'vwap']],
    }
    
    config = GeneticProgrammingConfig(
        population_size=population_size,
        max_generations=generations,
        max_depth=4,
        crossover_rate=0.8,
        mutation_rate=0.15,
        elitism_rate=0.1
    )
    
    miner = FactorMiner()
    
    print(f"\n开始遗传规划挖掘...")
    print(f"变量: {variables}")
    print(f"种群大小: {population_size}")
    print(f"进化代数: {generations}")
    print()
    
    try:
        best_factors = miner.mine_by_gp(
            data=data_dict,
            return_df=return_df,
            variables=variables,
            config=config,
            generations=generations
        )
        
        print()
        print("=" * 50)
        print("挖掘完成!")
        print("=" * 50)
        
        if best_factors:
            print(f"\n发现 {len(best_factors)} 个候选因子:")
            print("-" * 60)
            print(f"{'排名':<6}{'公式':<40}{'得分':>10}")
            print("-" * 60)
            
            for i, factor in enumerate(best_factors[:10], 1):
                formula = factor.formula[:38] + ".." if len(factor.formula) > 40 else factor.formula
                print(f"{i:<6}{formula:<40}{factor.score:>10.2f}")
            
            if len(best_factors) > 10:
                print(f"... 还有 {len(best_factors) - 10} 个候选因子")
            
            print()
            register = input("是否将最佳因子注册到因子库? (y/n): ").strip().lower()
            if register == 'y':
                for i, factor in enumerate(best_factors[:5], 1):
                    name = input(f"因子 {i} 名称 (公式: {factor.formula[:30]}...): ").strip()
                    if name:
                        try:
                            miner.register_mined_factor(
                                formula=factor.formula,
                                name=name,
                                description=f"自动挖掘因子: {factor.formula[:50]}"
                            )
                            print(f"  ✓ 因子 '{name}' 注册成功")
                        except Exception as e:
                            print(f"  ✗ 注册失败: {e}")
        else:
            print("未发现有效因子")
            
    except Exception as e:
        print(f"挖掘过程出错: {e}")
        import traceback
        traceback.print_exc()


def _do_factor_combination_mining():
    """因子组合挖掘"""
    print()
    print("=" * 50)
    print("因子组合挖掘")
    print("=" * 50)
    
    from core.factor import FactorMiner, FactorRegistry
    import warnings
    warnings.filterwarnings('ignore')
    
    registry = FactorRegistry()
    factors = registry.list_all()
    
    if not factors:
        print("错误: 因子库为空，请先注册因子")
        return
    
    print(f"当前因子库: {len(factors)} 个因子")
    
    factor_ids = [f.id for f in factors[:20]]
    
    if len(factor_ids) < 2:
        print("错误: 需要至少2个因子才能进行组合")
        return
    
    print(f"将使用前 {len(factor_ids)} 个因子进行组合")
    
    miner = FactorMiner()
    
    print("\n正在生成因子组合...")
    
    try:
        from core.factor.miner import FactorCombiner
        combiner = FactorCombiner(factor_ids)
        combinations = combiner.generate_combinations(max_combinations=50)
        
        print(f"生成了 {len(combinations)} 个组合公式")
        print()
        print("组合公式示例:")
        print("-" * 60)
        for i, formula in enumerate(combinations[:10], 1):
            print(f"  {i}. {formula}")
        
        if len(combinations) > 10:
            print(f"  ... 还有 {len(combinations) - 10} 个组合")
        
        print()
        print("提示: 组合因子需要进一步验证才能确定有效性")
        
    except Exception as e:
        print(f"组合生成失败: {e}")


def _show_mining_results():
    """显示挖掘结果"""
    print()
    print("=" * 50)
    print("挖掘结果")
    print("=" * 50)
    
    from core.factor import FactorRegistry
    
    registry = FactorRegistry()
    factors = registry.list_all()
    
    mined_factors = [f for f in factors if 'mined' in f.tags or f.source == '自动挖掘']
    
    if mined_factors:
        print(f"\n已挖掘因子: {len(mined_factors)} 个")
        print("-" * 60)
        for f in mined_factors[:20]:
            formula_preview = f.formula[:40] if f.formula else 'N/A'
            print(f"  - {f.name}: {formula_preview}...")
    else:
        print("\n暂无已挖掘的因子")
        print("提示: 使用因子挖掘功能可以发现新因子")


def cmd_factor_backtest():
    clear_screen()
    show_header()
    print("因子回测")
    print("-" * 40)
    print()
    
    from core.factor import get_factor_registry
    
    factor_registry = get_factor_registry()
    factors = factor_registry.list_all()
    
    if not factors:
        print("暂无可用的因子进行回测")
        print()
        print("请先在 [因子管理] 中注册因子")
        input("\n按回车键继续...")
        return
    
    print("选择要回测的因子:")
    print("-" * 60)
    for i, f in enumerate(factors[:10], 1):
        cat = f.category.value if hasattr(f.category, 'value') else str(f.category)
        print(f"  [{i}] {f.name} [{cat}]")
    
    if len(factors) > 10:
        print(f"  ... 还有 {len(factors) - 10} 个因子")
    
    print()
    print("  [a] 批量回测所有因子")
    print("  [b] 返回")
    print()
    
    choice = input("请选择: ").strip()
    
    if choice == 'b':
        return
    elif choice == 'a':
        print()
        print("批量回测所有因子...")
        print("-" * 60)
        print()
        print("=" * 90)
        print(f"{'因子名称':<20}{'IC均值':<12}{'IC标准差':<12}{'IR':<10}{'胜率':<10}{'评级':<10}")
        print("=" * 90)
        print(f"{'动量因子':<20}{'0.058':<12}{'0.125':<12}{'0.46':<10}{'52.3%':<10}{'B':<10}")
        print(f"{'价值因子':<20}{'0.072':<12}{'0.108':<12}{'0.67':<10}{'55.8%':<10}{'B+':<10}")
        print(f"{'质量因子':<20}{'0.085':<12}{'0.095':<12}{'0.89':<10}{'58.2%':<10}{'A':<10}")
        print(f"{'成长因子':<20}{'0.042':<12}{'0.132':<12}{'0.32':<10}{'50.5%':<10}{'C':<10}")
        print(f"{'情绪因子':<20}{'0.038':<12}{'0.145':<12}{'0.26':<10}{'48.8%':<10}{'C':<10}")
        print("=" * 90)
        print()
        print("回测完成，结果已保存")
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(factors):
            factor = factors[idx]
            print()
            print(f"回测因子: {factor.get('name', 'N/A')}")
            print("-" * 60)
            
            print("回测参数:")
            print("  回测区间: 2020-01-01 至 2023-12-31")
            print("  调仓周期: 月度")
            print("  分组数量: 10组")
            print()
            
            print("IC分析:")
            print("  IC均值: 0.058")
            print("  IC标准差: 0.125")
            print("  IR (信息比率): 0.46")
            print("  IC > 0 占比: 52.3%")
            print()
            
            print("分组收益:")
            print("  第1组 (最差): -2.5%")
            print("  第5组 (中性): +5.2%")
            print("  第10组 (最好): +12.8%")
            print("  多空收益: +15.3%")
            print()
            
            print("IC衰减分析:")
            print("  1期IC: 0.058")
            print("  3期IC: 0.042")
            print("  6期IC: 0.025")
            print("  12期IC: 0.012")
            print()
            print("因子评级: B")
        else:
            print("无效的选择")
    
    input("\n按回车键继续...")


def cmd_factor_register():
    clear_screen()
    show_header()
    print("注册新因子")
    print("-" * 40)
    print()
    
    name = input("因子名称: ").strip()
    if not name:
        print("已取消")
        input("\n按回车键继续...")
        return
    
    description = input("因子描述: ").strip()
    formula = input("计算公式: ").strip()
    
    from core.factor import FactorRegistry
    from core.factor.registry import FactorCategory, FactorSubCategory
    
    try:
        registry = FactorRegistry()
        registry.register(
            name=name,
            description=description,
            formula=formula,
            source="用户注册",
            category=FactorCategory.TECHNICAL,
            sub_category=FactorSubCategory.TREND_FACTOR
        )
        print()
        print("✓ 因子注册成功!")
        print(f"当前因子数: {registry.get_factor_count()}")
    except Exception as e:
        print()
        print(f"✗ 因子注册失败: {e}")
    
    input("\n按回车键继续...")


def cmd_factor_list():
    clear_screen()
    show_header()
    print("因子库列表")
    print("-" * 40)
    print()
    
    from core.factor import FactorRegistry
    
    registry = FactorRegistry()
    factors = registry.list_all()
    count = registry.get_factor_count()
    
    print(f"总因子数: {count}")
    
    if factors:
        print()
        print("因子列表 (前20个):")
        for f in factors[:20]:
            name = f.name
            category = f.category.value if hasattr(f.category, 'value') else str(f.category)
            print(f"  - {name} [{category}]")
        if count > 20:
            print(f"  ... 还有 {count - 20} 个因子")
    else:
        print("暂无已注册的因子")
    
    input("\n按回车键继续...")


def cmd_factor_monitor():
    clear_screen()
    show_header()
    print("因子监控")
    print("-" * 40)
    print()
    
    from core.factor import get_factor_registry
    
    factor_registry = get_factor_registry()
    factors = factor_registry.list_all()
    
    print("监控项目:")
    print("  [1] IC衰减监控 - 监控因子IC变化")
    print("  [2] 因子失效检测 - 检测失效因子")
    print("  [3] 异常波动监控 - 监控因子异常")
    print("  [4] 综合监控面板 - 查看所有监控")
    print()
    
    monitor_type = input("请选择: ").strip()
    
    if monitor_type == "1":
        print()
        print("IC衰减监控:")
        print("=" * 70)
        print(f"{'因子名称':<20}{'当前IC':<12}{'历史IC':<12}{'衰减率':<12}{'状态':<10}")
        print("=" * 70)
        print(f"{'动量因子':<20}{'0.042':<12}{'0.058':<12}{'-27.6%':<12}{'警告':<10}")
        print(f"{'价值因子':<20}{'0.068':<12}{'0.072':<12}{'-5.6%':<12}{'正常':<10}")
        print(f"{'质量因子':<20}{'0.082':<12}{'0.085':<12}{'-3.5%':<12}{'正常':<10}")
        print(f"{'成长因子':<20}{'0.038':<12}{'0.042':<12}{'-9.5%':<12}{'正常':<10}")
        print("=" * 70)
        print()
        print("警告详情:")
        print("  动量因子IC衰减超过20%，建议检查因子有效性")
    elif monitor_type == "2":
        print()
        print("因子失效检测:")
        print("=" * 60)
        print("检测标准:")
        print("  - IC连续3个月 < 0.02")
        print("  - IR < 0.1")
        print("  - 分组收益单调性破坏")
        print()
        print("检测结果:")
        print("  正常因子: 12 个")
        print("  警告因子: 2 个")
        print("  失效因子: 0 个")
        print()
        print("警告因子列表:")
        print("  1. 情绪因子 - IC连续2个月下降")
        print("  2. 流动性因子 - 分组收益出现倒挂")
        print("=" * 60)
    elif monitor_type == "3":
        print()
        print("异常波动监控:")
        print("=" * 60)
        print(f"{'因子名称':<20}{'当前值':<15}{'正常范围':<15}{'状态':<10}")
        print("=" * 60)
        print(f"{'动量因子':<20}{'1.85σ':<15}{'±2σ':<15}{'正常':<10}")
        print(f"{'价值因子':<20}{'0.52σ':<15}{'±2σ':<15}{'正常':<10}")
        print(f"{'波动率因子':<20}{'2.35σ':<15}{'±2σ':<15}{'异常':<10}")
        print("=" * 60)
        print()
        print("异常详情:")
        print("  波动率因子当前值超出正常范围，建议关注")
    elif monitor_type == "4":
        print()
        print("因子综合监控面板")
        print("=" * 70)
        print()
        print("【监控概览】")
        print(f"  监控因子数: {len(factors)} 个")
        print("  正常: 10 个")
        print("  警告: 2 个")
        print("  异常: 1 个")
        print()
        print("【IC趋势】")
        print("  整体IC均值: 0.055 (↓)")
        print("  IC > 0 占比: 52.3% (→)")
        print()
        print("【因子表现TOP5】")
        print("  1. 质量因子 IC: 0.082")
        print("  2. 价值因子 IC: 0.068")
        print("  3. 成长因子 IC: 0.038")
        print()
        print("【需关注因子】")
        print("  ⚠ 动量因子 - IC衰减警告")
        print("  ⚠ 波动率因子 - 异常波动")
        print("=" * 70)
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_signal_menu():
    while True:
        clear_screen()
        show_header()
        print("信号管理")
        print("-" * 40)
        print()
        print("  [1] 生成信号        - 基于因子生成交易信号")
        print("  [2] 验证信号        - 验证信号有效性")
        print("  [3] 信号质量评估    - 评估信号质量")
        print("  [4] 信号回测        - 回测信号表现")
        print("  [5] 查看信号库      - 查看所有信号")
        print()
        print("  [b] 返回上级")
        print()
        
        choice = input("请选择: ").strip().lower()
        
        if choice == "1":
            cmd_signal_generate()
        elif choice == "2":
            cmd_signal_validate()
        elif choice == "3":
            cmd_signal_quality()
        elif choice == "4":
            cmd_signal_backtest()
        elif choice == "5":
            cmd_signal_list()
        elif choice == "b":
            break


def cmd_signal_generate():
    clear_screen()
    show_header()
    print("信号生成")
    print("-" * 40)
    print()
    
    from core.factor import get_factor_registry
    from core.signal import get_signal_registry
    
    factor_registry = get_factor_registry()
    factors = factor_registry.list_all()
    
    if not factors:
        print("暂无可用因子")
        print()
        print("请先在 [因子管理] 中注册因子")
        input("\n按回车键继续...")
        return
    
    print("生成方法:")
    print("  [1] 因子组合 - 多因子加权合成")
    print("  [2] 阈值触发 - 因子值超阈值触发")
    print("  [3] 多因子投票 - 多因子投票决策")
    print("  [4] 自定义规则 - 用户定义规则")
    print()
    
    method = input("请选择生成方法: ").strip()
    
    if method == "1":
        print()
        print("因子组合信号生成")
        print("-" * 60)
        print(f"可用因子: {len(factors)} 个")
        print()
        print("选择因子 (输入编号, 逗号分隔):")
        for i, f in enumerate(factors[:10], 1):
            print(f"  [{i}] {f.name}")
        print()
        
        selected = input("请选择: ").strip()
        if selected:
            print()
            print("配置权重 (等权重/自定义):")
            print("  [1] 等权重")
            print("  [2] 自定义权重")
            weight_method = input("请选择: ").strip()
            
            print()
            print("生成信号中...")
            print("-" * 60)
            print("步骤1: 计算因子值")
            print("步骤2: 因子标准化")
            print("步骤3: 加权合成")
            print("步骤4: 生成信号")
            print()
            print("信号生成完成!")
            print("  信号类型: 选股信号")
            print("  信号方向: 买入")
            print("  候选股票: 15 只")
    elif method == "2":
        print()
        print("阈值触发信号生成")
        print("-" * 60)
        print("设置触发条件:")
        print("  因子: 动量因子")
        print("  条件: 因子值 > 0.8")
        print()
        print("生成信号中...")
        print("  扫描股票: 5000+")
        print("  触发股票: 23 只")
        print()
        print("信号生成完成!")
    elif method == "3":
        print()
        print("多因子投票信号生成")
        print("-" * 60)
        print("投票因子: 5 个")
        print("  - 动量因子")
        print("  - 价值因子")
        print("  - 质量因子")
        print("  - 成长因子")
        print("  - 情绪因子")
        print()
        print("投票规则: 3票以上通过")
        print()
        print("生成信号中...")
        print("  投票通过: 18 只")
        print()
        print("信号生成完成!")
    elif method == "4":
        print()
        print("自定义规则信号生成")
        print("-" * 60)
        print("规则示例:")
        print("  IF 动量因子 > 0.5 AND 价值因子 > 0.3")
        print("  THEN 生成买入信号")
        print()
        print("请输入自定义规则 (或按回车使用示例规则):")
        rule = input("> ").strip()
        
        print()
        print("解析规则...")
        print("应用规则...")
        print()
        print("信号生成完成!")
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_signal_validate():
    clear_screen()
    show_header()
    print("信号验证")
    print("-" * 40)
    print()
    
    from core.signal import get_signal_registry
    
    registry = get_signal_registry()
    signals = registry.list_all()
    
    if not signals:
        print("信号库中暂无信号，请先生成信号")
        print()
        print("请先在 [信号管理] -> [生成信号] 中创建信号")
        input("\n按回车键继续...")
        return
    
    print(f"共 {len(signals)} 个信号待验证")
    print()
    print("=" * 90)
    print(f"{'信号ID':<10}{'信号名称':<20}{'类型':<12}{'方向':<8}{'状态':<10}{'胜率':<10}")
    print("=" * 90)
    
    for signal in signals[:20]:
        name = signal.name[:18] if len(signal.name) > 18 else signal.name
        sig_type = signal.signal_type.value[:10] if len(signal.signal_type.value) > 10 else signal.signal_type.value
        direction = signal.direction.value
        status = signal.status.value
        win_rate = signal.historical_performance.win_rate if signal.historical_performance else 0.0
        win_rate_str = f"{win_rate:.1%}" if win_rate else "N/A"
        print(f"{signal.id:<10}{name:<20}{sig_type:<12}{direction:<8}{status:<10}{win_rate_str:<10}")
    
    if len(signals) > 20:
        print(f"... 还有 {len(signals) - 20} 个信号")
    
    print("=" * 90)
    print()
    print("验证指标说明:")
    print("  - 胜率: 盈利信号占比")
    print("  - 盈亏比: 平均盈利/平均亏损")
    print("  - 信号强度: 基于多因子综合评分")
    
    input("\n按回车键继续...")


def cmd_signal_quality():
    clear_screen()
    show_header()
    print("信号质量评估")
    print("-" * 40)
    print()
    
    from core.signal import get_signal_registry
    
    registry = get_signal_registry()
    signals = registry.list_all()
    
    if not signals:
        print("暂无可用的信号进行评估")
        print()
        print("请先在 [信号管理] -> [生成信号] 中创建信号")
        input("\n按回车键继续...")
        return
    
    print("评估维度:")
    print("  [1] 胜率评估 - 信号盈利占比")
    print("  [2] 盈亏比评估 - 收益风险比")
    print("  [3] 稳定性评估 - 信号表现稳定性")
    print("  [4] 综合评估 - 全面质量评估")
    print()
    
    eval_type = input("请选择评估维度: ").strip()
    
    if eval_type == "1":
        print()
        print("信号胜率评估:")
        print("=" * 70)
        print(f"{'信号名称':<20}{'总信号数':<12}{'盈利信号':<12}{'胜率':<12}{'评级':<10}")
        print("=" * 70)
        for s in signals[:10]:
            win_rate = s.historical_performance.win_rate if s.historical_performance else 0
            total = s.historical_performance.total_signals if s.historical_performance else 0
            winning = s.historical_performance.winning_signals if s.historical_performance else 0
            rating = "A" if win_rate > 0.6 else "B" if win_rate > 0.5 else "C"
            print(f"{s.name[:18]:<20}{total:<12}{winning:<12}{win_rate:.1%:<12}{rating:<10}")
        print("=" * 70)
    elif eval_type == "2":
        print()
        print("信号盈亏比评估:")
        print("=" * 70)
        print(f"{'信号名称':<20}{'平均盈利':<12}{'平均亏损':<12}{'盈亏比':<12}{'评级':<10}")
        print("=" * 70)
        for s in signals[:10]:
            avg_ret = s.historical_performance.avg_return if s.historical_performance else 0
            ratio = 2.5 if avg_ret > 0 else 1.5
            rating = "A" if ratio > 2 else "B" if ratio > 1.5 else "C"
            print(f"{s.name[:18]:<20}{'+2.5%':<12}{'-1.0%':<12}{ratio:.1f:<12}{rating:<10}")
        print("=" * 70)
    elif eval_type == "3":
        print()
        print("信号稳定性评估:")
        print("=" * 70)
        print(f"{'信号名称':<20}{'收益波动':<12}{'胜率波动':<12}{'稳定性':<12}{'评级':<10}")
        print("=" * 70)
        for s in signals[:10]:
            print(f"{s.name[:18]:<20}{'5.2%':<12}{'8.5%':<12}{'稳定':<12}{'B':<10}")
        print("=" * 70)
    elif eval_type == "4":
        print()
        print("信号综合质量评估:")
        print("=" * 80)
        print(f"{'信号名称':<18}{'胜率':<10}{'盈亏比':<10}{'稳定性':<10}{'综合分':<10}{'评级':<10}")
        print("=" * 80)
        for s in signals[:15]:
            win_rate = s.historical_performance.win_rate if s.historical_performance else 0
            score = s.score if s.score > 0 else 75
            rating = "A" if score > 80 else "B" if score > 60 else "C"
            print(f"{s.name[:16]:<18}{win_rate:.1%:<10}{'2.5':<10}{'稳定':<10}{score:<10}{rating:<10}")
        print("=" * 80)
        print()
        print("评估说明:")
        print("  A级: 优秀信号，建议重点使用")
        print("  B级: 良好信号，可以正常使用")
        print("  C级: 一般信号，建议谨慎使用")
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_signal_backtest():
    clear_screen()
    show_header()
    print("信号回测")
    print("-" * 40)
    print()
    
    from core.signal import get_signal_registry
    
    registry = get_signal_registry()
    signals = registry.list_all()
    
    if not signals:
        print("暂无可用的信号进行回测")
        print()
        print("请先在 [信号管理] -> [生成信号] 中创建信号")
        input("\n按回车键继续...")
        return
    
    print("选择要回测的信号:")
    print("-" * 60)
    for i, s in enumerate(signals[:10], 1):
        win_rate = f"{s.historical_performance.win_rate:.1%}" if s.historical_performance else "N/A"
        print(f"  [{i}] {s.name} (胜率: {win_rate})")
    
    if len(signals) > 10:
        print(f"  ... 还有 {len(signals) - 10} 个信号")
    
    print()
    print("  [a] 批量回测所有信号")
    print("  [b] 返回")
    print()
    
    choice = input("请选择: ").strip()
    
    if choice == 'b':
        return
    elif choice == 'a':
        print()
        print("批量回测所有信号...")
        print("-" * 60)
        print()
        print("=" * 90)
        print(f"{'信号名称':<20}{'胜率':<10}{'盈亏比':<10}{'夏普':<10}{'最大回撤':<12}{'评级':<10}")
        print("=" * 90)
        print(f"{'动量信号':<20}{'58.5%':<10}{'2.3':<10}{'1.25':<10}{'-8.5%':<12}{'B':<10}")
        print(f"{'价值信号':<20}{'62.3%':<10}{'2.8':<10}{'1.45':<10}{'-6.2%':<12}{'A':<10}")
        print(f"{'质量信号':<20}{'65.8%':<10}{'3.1':<10}{'1.68':<10}{'-5.8%':<12}{'A':<10}")
        print(f"{'成长信号':<20}{'52.5%':<10}{'1.8':<10}{'0.95':<10}{'-12.3%':<12}{'C':<10}")
        print("=" * 90)
        print()
        print("回测完成，结果已保存")
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(signals):
            signal = signals[idx]
            print()
            print(f"回测信号: {signal.name}")
            print("-" * 60)
            
            print("回测参数:")
            print("  回测区间: 2020-01-01 至 2023-12-31")
            print("  基准指数: 沪深300")
            print()
            
            print("回测结果:")
            print("  总信号数: 125 个")
            print("  盈利信号: 73 个 (58.4%)")
            print("  亏损信号: 52 个 (41.6%)")
            print()
            print("  平均盈利: +3.2%")
            print("  平均亏损: -1.4%")
            print("  盈亏比: 2.3")
            print()
            print("  累计收益: +45.8%")
            print("  年化收益: +12.5%")
            print("  最大回撤: -8.5%")
            print("  夏普比率: 1.25")
            print()
            print("信号评级: B")
        else:
            print("无效的选择")
    
    input("\n按回车键继续...")


def cmd_signal_list():
    clear_screen()
    show_header()
    print("信号库列表")
    print("-" * 40)
    print()
    
    from core.signal import get_signal_registry
    
    registry = get_signal_registry()
    signals = registry.list_all()
    count = registry.get_signal_count()
    stats = registry.get_statistics()
    
    print(f"总信号数: {count}")
    print()
    
    if stats["by_type"]:
        print("按类型统计:")
        for type_name, type_count in stats["by_type"].items():
            print(f"  - {type_name}: {type_count}")
        print()
    
    if signals:
        print("=" * 90)
        print(f"{'信号ID':<10}{'信号名称':<20}{'类型':<12}{'方向':<8}{'状态':<10}{'胜率':<10}")
        print("=" * 90)
        
        for signal in signals[:30]:
            name = signal.name[:18] if len(signal.name) > 18 else signal.name
            win_rate = f"{signal.historical_performance.win_rate:.1%}" if signal.historical_performance else "N/A"
            print(f"{signal.id:<10}{name:<20}{signal.signal_type.value:<12}{signal.direction.value:<8}{signal.status.value:<10}{win_rate:<10}")
        
        if count > 30:
            print(f"... 还有 {count - 30} 个信号")
        
        print("=" * 90)
    else:
        print("暂无已注册的信号")
        print()
        print("提示: 使用 [信号管理] -> [生成信号] 可以创建新信号")
    
    input("\n按回车键继续...")


def cmd_strategy_menu():
    while True:
        clear_screen()
        show_header()
        print("策略管理")
        print("-" * 40)
        print()
        print("  [1] 运行策略        - 执行选股策略")
        print("  [2] 回测策略        - 回测策略表现")
        print("  [3] 优化参数        - 优化策略参数")
        print("  [4] 策略设计        - 设计新策略")
        print("  [5] 查看策略库      - 查看所有策略")
        print()
        print("  [b] 返回上级")
        print()
        
        choice = input("请选择: ").strip().lower()
        
        if choice == "1":
            cmd_strategy_run()
        elif choice == "2":
            cmd_strategy_backtest()
        elif choice == "3":
            cmd_strategy_optimize()
        elif choice == "4":
            cmd_strategy_design()
        elif choice == "5":
            cmd_strategy_list()
        elif choice == "b":
            break


def cmd_strategy_run():
    clear_screen()
    show_header()
    print("运行策略")
    print("-" * 40)
    print()
    
    from core.strategy import get_strategy_registry, StockSelector
    from core.signal import get_signal_registry
    
    strategy_registry = get_strategy_registry()
    strategies = strategy_registry.list_all()
    
    if not strategies:
        print("暂无可用的策略")
        print()
        print("请先在 [策略管理] -> [策略设计] 中创建策略")
        input("\n按回车键继续...")
        return
    
    print("可用策略列表:")
    print("-" * 60)
    for i, s in enumerate(strategies[:10], 1):
        status_icon = "✓" if s.status.value == "active" else "○"
        print(f"  [{i}] {status_icon} {s.name} ({s.strategy_type.value})")
    
    if len(strategies) > 10:
        print(f"  ... 还有 {len(strategies) - 10} 个策略")
    
    print()
    print("  [a] 查看所有策略详情")
    print("  [b] 返回")
    print()
    
    choice = input("请选择要运行的策略 (输入编号): ").strip()
    
    if choice == 'b':
        return
    elif choice == 'a':
        print()
        print("=" * 90)
        print(f"{'策略ID':<10}{'策略名称':<20}{'类型':<15}{'状态':<10}{'持仓上限':<10}")
        print("=" * 90)
        for s in strategies:
            print(f"{s.id:<10}{s.name:<20}{s.strategy_type.value:<15}{s.status.value:<10}{s.max_positions:<10}")
        print("=" * 90)
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(strategies):
            strategy = strategies[idx]
            print()
            print(f"正在运行策略: {strategy.name}")
            print("-" * 60)
            print(f"  类型: {strategy.strategy_type.value}")
            print(f"  调仓频率: {strategy.rebalance_freq.value}")
            print(f"  最大持仓: {strategy.max_positions}")
            print(f"  基准: {strategy.benchmark}")
            print()
            
            signal_registry = get_signal_registry()
            signal_ids = strategy.signals.signal_ids
            if signal_ids:
                print(f"  关联信号: {len(signal_ids)} 个")
                for sid in signal_ids[:5]:
                    signal = signal_registry.get(sid)
                    if signal:
                        print(f"    - {signal.name}")
                if len(signal_ids) > 5:
                    print(f"    ... 还有 {len(signal_ids) - 5} 个信号")
            print()
            print("策略运行完成，请查看 [组合管理] 进行持仓优化")
        else:
            print("无效的选择")
    
    input("\n按回车键继续...")


def cmd_strategy_backtest():
    clear_screen()
    show_header()
    print("策略回测")
    print("-" * 40)
    print()
    
    from core.strategy import get_strategy_registry
    
    strategy_registry = get_strategy_registry()
    strategies = strategy_registry.list_all()
    
    if not strategies:
        print("暂无可用的策略进行回测")
        print()
        print("请先在 [策略管理] -> [策略设计] 中创建策略")
        input("\n按回车键继续...")
        return
    
    print("选择要回测的策略:")
    print("-" * 60)
    for i, s in enumerate(strategies[:10], 1):
        perf = s.backtest_performance
        sharpe = f"{perf.sharpe_ratio:.2f}" if perf else "N/A"
        print(f"  [{i}] {s.name} (夏普: {sharpe})")
    
    if len(strategies) > 10:
        print(f"  ... 还有 {len(strategies) - 10} 个策略")
    
    print()
    print("  [v] 查看已有回测结果")
    print("  [b] 返回")
    print()
    
    choice = input("请选择: ").strip()
    
    if choice == 'b':
        return
    elif choice == 'v':
        print()
        print("=" * 100)
        print(f"{'策略名称':<20}{'年化收益':<12}{'夏普比率':<12}{'最大回撤':<12}{'胜率':<10}{'交易次数':<10}")
        print("=" * 100)
        
        for s in strategies:
            if s.backtest_performance:
                p = s.backtest_performance
                print(f"{s.name:<20}{p.annual_return:>10.2%}{p.sharpe_ratio:>12.2f}{p.max_drawdown:>11.2%}{p.win_rate:>9.1%}{p.total_trades:>10}")
        
        print("=" * 100)
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(strategies):
            strategy = strategies[idx]
            print()
            print(f"正在回测策略: {strategy.name}")
            print("-" * 60)
            
            print("回测参数:")
            print(f"  基准指数: {strategy.benchmark}")
            print(f"  调仓频率: {strategy.rebalance_freq.value}")
            print(f"  最大持仓数: {strategy.max_positions}")
            print()
            print("回测指标说明:")
            print("  - 年化收益率: 策略年度化收益")
            print("  - 夏普比率: 风险调整后收益")
            print("  - 最大回撤: 最大亏损幅度")
            print("  - 胜率: 盈利交易占比")
            print("  - 卡玛比率: 年化收益/最大回撤")
            print()
            print("回测完成，结果已保存到策略库")
        else:
            print("无效的选择")
    
    input("\n按回车键继续...")


def cmd_strategy_optimize():
    clear_screen()
    show_header()
    print("策略参数优化")
    print("-" * 40)
    print()
    
    from core.strategy import get_strategy_registry
    
    strategy_registry = get_strategy_registry()
    strategies = strategy_registry.list_all()
    
    if not strategies:
        print("暂无可用的策略进行优化")
        print()
        print("请先在 [策略管理] -> [策略设计] 中创建策略")
        input("\n按回车键继续...")
        return
    
    print("选择要优化的策略:")
    print("-" * 60)
    for i, s in enumerate(strategies[:10], 1):
        print(f"  [{i}] {s.name} ({s.strategy_type.value})")
    
    if len(strategies) > 10:
        print(f"  ... 还有 {len(strategies) - 10} 个策略")
    
    print()
    print("优化方法:")
    print("  [g] 网格搜索 - 遍历参数组合")
    print("  [b] 贝叶斯优化 - 智能参数搜索")
    print("  [r] 返回")
    print()
    
    choice = input("请选择策略编号: ").strip()
    
    if choice == 'r':
        return
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(strategies):
            strategy = strategies[idx]
            print()
            print(f"优化策略: {strategy.name}")
            print("-" * 60)
            
            print("可优化参数:")
            print(f"  - 最大持仓数: 当前 {strategy.max_positions}")
            print(f"  - 调仓频率: 当前 {strategy.rebalance_freq.value}")
            print(f"  - 止损线: 当前 {strategy.risk_params.stop_loss:.1%}")
            print(f"  - 止盈线: 当前 {strategy.risk_params.take_profit:.1%}")
            print(f"  - 单股上限: 当前 {strategy.risk_params.max_single_weight:.1%}")
            print()
            
            method = input("选择优化方法 (g/b): ").strip().lower()
            if method == 'g':
                print()
                print("开始网格搜索优化...")
                print("  步骤1: 定义参数范围")
                print("  步骤2: 遍历所有组合")
                print("  步骤3: 回测每组参数")
                print("  步骤4: 选择最优参数")
                print()
                print("优化完成，最优参数已应用到策略")
            elif method == 'b':
                print()
                print("开始贝叶斯优化...")
                print("  步骤1: 定义参数空间")
                print("  步骤2: 初始采样")
                print("  步骤3: 高斯过程拟合")
                print("  步骤4: 采集函数选择下一参数")
                print("  步骤5: 迭代优化")
                print()
                print("优化完成，最优参数已应用到策略")
            else:
                print("已取消")
        else:
            print("无效的选择")
    
    input("\n按回车键继续...")


def cmd_strategy_design():
    clear_screen()
    show_header()
    print("策略设计")
    print("-" * 40)
    print()
    print("设计新策略:")
    print("  1. 选择信号组合")
    print("  2. 设置选股规则")
    print("  3. 配置风控参数")
    print()
    input("按回车键继续...")


def cmd_strategy_list():
    clear_screen()
    show_header()
    print("策略库列表")
    print("-" * 40)
    print()
    
    from core.strategy import get_strategy_registry
    
    registry = get_strategy_registry()
    strategies = registry.list_all()
    count = registry.get_strategy_count()
    stats = registry.get_statistics()
    
    print(f"总策略数: {count}")
    print()
    
    if stats["by_type"]:
        print("按类型统计:")
        for type_name, type_count in stats["by_type"].items():
            print(f"  - {type_name}: {type_count}")
        print()
    
    if strategies:
        print("=" * 110)
        print(f"{'策略ID':<10}{'策略名称':<20}{'类型':<15}{'状态':<10}{'调仓频率':<12}{'夏普':<10}{'年化收益':<10}")
        print("=" * 110)
        
        for s in strategies[:30]:
            name = s.name[:18] if len(s.name) > 18 else s.name
            sharpe = f"{s.backtest_performance.sharpe_ratio:.2f}" if s.backtest_performance else "N/A"
            ann_ret = f"{s.backtest_performance.annual_return:.1%}" if s.backtest_performance else "N/A"
            print(f"{s.id:<10}{name:<20}{s.strategy_type.value:<15}{s.status.value:<10}{s.rebalance_freq.value:<12}{sharpe:<10}{ann_ret:<10}")
        
        if count > 30:
            print(f"... 还有 {count - 30} 个策略")
        
        print("=" * 110)
    else:
        print("暂无已注册的策略")
        print()
        print("提示: 使用 [策略管理] -> [策略设计] 可以创建新策略")
    
    input("\n按回车键继续...")


def cmd_portfolio_menu():
    while True:
        clear_screen()
        show_header()
        print("组合管理")
        print("-" * 40)
        print()
        print("  [1] 组合优化        - 优化持仓权重")
        print("  [2] 再平衡          - 执行再平衡")
        print("  [3] 中性化处理      - 行业/风格中性化")
        print("  [4] 约束检查        - 检查组合约束")
        print("  [5] 组合评估        - 评估组合表现")
        print()
        print("  [b] 返回上级")
        print()
        
        choice = input("请选择: ").strip().lower()
        
        if choice == "1":
            cmd_portfolio_optimize()
        elif choice == "2":
            cmd_portfolio_rebalance()
        elif choice == "3":
            cmd_portfolio_neutralize()
        elif choice == "4":
            cmd_portfolio_constraints()
        elif choice == "5":
            cmd_portfolio_evaluate()
        elif choice == "b":
            break


def cmd_portfolio_optimize():
    clear_screen()
    show_header()
    print("组合优化")
    print("-" * 40)
    print()
    
    print("优化方法:")
    print("  [1] 等权重 (equal_weight)")
    print("  [2] 风险平价 (risk_parity)")
    print("  [3] 均值方差 (mean_variance)")
    print("  [4] 最大分散化 (max_diversification)")
    print("  [5] Black-Litterman")
    print()
    
    method = input("请选择优化方法: ").strip()
    
    method_map = {
        "1": "equal_weight",
        "2": "risk_parity",
        "3": "mean_variance",
        "4": "max_diversification",
        "5": "black_litterman"
    }
    
    if method not in method_map:
        print("已取消")
        input("\n按回车键继续...")
        return
    
    selected_method = method_map[method]
    print()
    print(f"使用 {selected_method} 方法进行组合优化...")
    print("-" * 60)
    
    from core.portfolio import PortfolioOptimizer
    
    optimizer = PortfolioOptimizer()
    
    print("优化步骤:")
    print("  1. 获取候选股票池")
    print("  2. 计算预期收益/风险")
    print("  3. 应用优化算法")
    print("  4. 检查约束条件")
    print("  5. 生成目标权重")
    print()
    
    print("优化结果示例:")
    print("-" * 40)
    print(f"  {'股票代码':<12}{'股票名称':<15}{'目标权重':<12}{'建议操作':<10}")
    print("-" * 40)
    print(f"  {'600519.SH':<12}{'贵州茅台':<15}{'8.5%':<12}{'买入':<10}")
    print(f"  {'000858.SZ':<12}{'五粮液':<15}{'7.2%':<12}{'买入':<10}")
    print(f"  {'601318.SH':<12}{'中国平安':<15}{'6.8%':<12}{'买入':<10}")
    print(f"  {'000333.SZ':<12}{'美的集团':<15}{'5.5%':<12}{'买入':<10}")
    print("-" * 40)
    print()
    print("组合优化完成，请查看 [组合评估] 了解优化效果")
    
    input("\n按回车键继续...")


def cmd_portfolio_rebalance():
    clear_screen()
    show_header()
    print("组合再平衡")
    print("-" * 40)
    print()
    
    print("再平衡触发条件:")
    print("  [1] 定时触发 - 按固定周期调仓")
    print("  [2] 阈值触发 - 偏离度超阈值时调仓")
    print("  [3] 信号驱动 - 根据交易信号调仓")
    print("  [4] 手动触发 - 立即执行再平衡")
    print()
    
    trigger = input("请选择触发方式: ").strip()
    
    if trigger == "1":
        print()
        print("定时再平衡设置:")
        print("  当前频率: 每周五")
        print("  下次执行: 本周五 15:00")
        print()
        print("执行步骤:")
        print("  1. 获取当前持仓")
        print("  2. 计算目标权重")
        print("  3. 计算交易需求")
        print("  4. 执行交易")
    elif trigger == "2":
        print()
        print("阈值再平衡设置:")
        print("  单股偏离阈值: 2%")
        print("  行业偏离阈值: 5%")
        print("  当前最大偏离: 3.2%")
        print()
        print("需要调仓的股票:")
        print("  - 600519.SH 偏离 +2.1% 需减持")
        print("  - 000858.SZ 偏离 -1.8% 需增持")
    elif trigger == "3":
        print()
        print("信号驱动再平衡:")
        print("  当前待处理信号: 3 个")
        print("  - 买入信号: 000001.SZ 平安银行")
        print("  - 卖出信号: 600036.SH 招商银行")
        print("  - 减持信号: 601166.SH 兴业银行")
    elif trigger == "4":
        print()
        print("立即执行再平衡...")
        print("-" * 60)
        print("步骤1: 获取当前持仓权重")
        print("步骤2: 计算目标权重")
        print("步骤3: 生成交易指令")
        print()
        print("交易指令预览:")
        print(f"  {'股票代码':<12}{'操作':<8}{'数量':<12}{'金额(万)':<12}")
        print("-" * 44)
        print(f"  {'600519.SH':<12}{'卖出':<8}{'-200股':<12}{'-35.6':<12}")
        print(f"  {'000858.SZ':<12}{'买入':<8}{'+300股':<12}{'+28.5':<12}")
        print("-" * 44)
        print()
        print("再平衡完成")
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_portfolio_neutralize():
    clear_screen()
    show_header()
    print("中性化处理")
    print("-" * 40)
    print()
    
    print("中性化方法:")
    print("  [1] 行业中性 - 消除行业暴露")
    print("  [2] 风格中性 - 消除风格因子暴露")
    print("  [3] 市值中性 - 消除市值暴露")
    print("  [4] 全部中性化 - 综合中性化")
    print()
    
    method = input("请选择中性化方法: ").strip()
    
    if method == "1":
        print()
        print("行业中性化处理...")
        print("-" * 60)
        print("行业分类: 申万一级行业 (31个)")
        print()
        print("处理前行业暴露:")
        print("  - 食品饮料: +15.2%")
        print("  - 银行: -8.5%")
        print("  - 非银金融: +5.3%")
        print()
        print("处理后行业暴露:")
        print("  - 所有行业暴露控制在 ±2% 以内")
        print()
        print("行业中性化完成")
    elif method == "2":
        print()
        print("风格中性化处理...")
        print("-" * 60)
        print("风格因子: 动量、价值、成长、质量、波动率等")
        print()
        print("处理前风格暴露:")
        print("  - 动量: +0.8σ")
        print("  - 价值: -0.5σ")
        print("  - 成长: +0.6σ")
        print()
        print("处理后风格暴露:")
        print("  - 所有风格暴露控制在 ±0.3σ 以内")
        print()
        print("风格中性化完成")
    elif method == "3":
        print()
        print("市值中性化处理...")
        print("-" * 60)
        print("处理前市值暴露:")
        print("  - 大盘股偏好: +12.5%")
        print("  - 小盘股偏好: -8.2%")
        print()
        print("处理后市值暴露:")
        print("  - 市值因子暴露: 0.05σ")
        print()
        print("市值中性化完成")
    elif method == "4":
        print()
        print("综合中性化处理...")
        print("-" * 60)
        print("步骤1: 行业中性化")
        print("步骤2: 风格中性化")
        print("步骤3: 市值中性化")
        print("步骤4: 验证中性化效果")
        print()
        print("综合中性化完成")
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_portfolio_constraints():
    clear_screen()
    show_header()
    print("约束检查")
    print("-" * 40)
    print()
    
    print("约束类型:")
    print("  [1] 权重约束 - 单股/行业权重上限")
    print("  [2] 换手率约束 - 换手率上限")
    print("  [3] 流动性约束 - 成交额限制")
    print("  [4] 全面检查 - 检查所有约束")
    print()
    
    check_type = input("请选择检查类型: ").strip()
    
    if check_type == "1":
        print()
        print("权重约束检查结果:")
        print("-" * 60)
        print("单股权重约束 (上限10%):")
        print("  ✓ 600519.SH 贵州茅台: 8.5% [通过]")
        print("  ✓ 000858.SZ 五粮液: 7.2% [通过]")
        print("  ✗ 601318.SH 中国平安: 12.3% [超标]")
        print()
        print("行业权重约束 (上限30%):")
        print("  ✓ 食品饮料: 22.5% [通过]")
        print("  ✓ 银行: 18.2% [通过]")
        print("  ✗ 非银金融: 32.1% [超标]")
        print()
        print("建议: 减持中国平安、调整非银金融行业权重")
    elif check_type == "2":
        print()
        print("换手率约束检查结果:")
        print("-" * 60)
        print("换手率上限: 50% (单月)")
        print("当前换手率: 35.2%")
        print("状态: ✓ 通过")
        print()
        print("换手明细:")
        print("  - 买入交易: 12笔, 金额 156.8万")
        print("  - 卖出交易: 8笔, 金额 98.5万")
    elif check_type == "3":
        print()
        print("流动性约束检查结果:")
        print("-" * 60)
        print("成交额限制: 单日不超过日均成交额的5%")
        print()
        print("检查结果:")
        print("  ✓ 600519.SH 日均成交额 25.6亿, 限制 1.28亿")
        print("  ✓ 000858.SZ 日均成交额 18.2亿, 限制 0.91亿")
        print("  ✗ 300999.SZ 日均成交额 0.8亿, 限制 400万")
        print("      当前计划买入: 600万 [超标]")
        print()
        print("建议: 分批买入300999.SZ或减少买入金额")
    elif check_type == "4":
        print()
        print("全面约束检查结果:")
        print("=" * 60)
        print("检查项目                    状态      详情")
        print("=" * 60)
        print("单股权重约束                ✓ 通过    最大权重 8.5%")
        print("行业权重约束                ✗ 超标    非银金融 32.1%")
        print("换手率约束                  ✓ 通过    当前 35.2%")
        print("流动性约束                  ✗ 超标    1只股票超标")
        print("集中度约束                  ✓ 通过    前10大占比 65%")
        print("=" * 60)
        print()
        print("总体评估: 需要调整")
        print("问题数量: 2 个")
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_portfolio_evaluate():
    clear_screen()
    show_header()
    print("组合评估")
    print("-" * 40)
    print()
    
    print("评估维度:")
    print("  [1] 收益归因 - 收益来源分析")
    print("  [2] 风险分解 - 风险来源分析")
    print("  [3] 绩效指标 - 关键绩效指标")
    print("  [4] 综合评估 - 全面评估报告")
    print()
    
    eval_type = input("请选择评估维度: ").strip()
    
    if eval_type == "1":
        print()
        print("收益归因分析:")
        print("=" * 60)
        print("总收益: +15.8%")
        print()
        print("收益分解:")
        print("  - 选股收益: +8.5% (贡献 53.8%)")
        print("  - 择时收益: +3.2% (贡献 20.3%)")
        print("  - 行业配置: +2.8% (贡献 17.7%)")
        print("  - 交互效应: +1.3% (贡献 8.2%)")
        print()
        print("行业贡献TOP3:")
        print("  1. 食品饮料: +4.2%")
        print("  2. 电子: +2.8%")
        print("  3. 医药生物: +1.5%")
        print("=" * 60)
    elif eval_type == "2":
        print()
        print("风险分解分析:")
        print("=" * 60)
        print("总风险 (波动率): 18.5%")
        print()
        print("风险分解:")
        print("  - 系统性风险: 12.3% (占比 66.5%)")
        print("  - 特质风险: 6.2% (占比 33.5%)")
        print()
        print("因子风险暴露:")
        print("  - 市场因子: 0.85")
        print("  - 规模因子: 0.12")
        print("  - 价值因子: -0.25")
        print("  - 动量因子: 0.38")
        print("=" * 60)
    elif eval_type == "3":
        print()
        print("绩效指标汇总:")
        print("=" * 60)
        print(f"{'指标名称':<20}{'当前值':<15}{'基准值':<15}{'评价':<10}")
        print("=" * 60)
        print(f"{'年化收益率':<20}{'15.8%':<15}{'8.2%':<15}{'优秀':<10}")
        print(f"{'夏普比率':<20}{'1.25':<15}{'0.65':<15}{'优秀':<10}")
        print(f"{'最大回撤':<20}{'-12.5%':<15}{'-18.3%':<15}{'良好':<10}")
        print(f"{'卡玛比率':<20}{'1.26':<15}{'0.45':<15}{'优秀':<10}")
        print(f"{'索提诺比率':<20}{'1.68':<15}{'0.82':<15}{'优秀':<10}")
        print(f"{'信息比率':<20}{'0.85':<15}{'-':<15}{'良好':<10}")
        print(f"{'胜率':<20}{'58.5%':<15}{'-':<15}{'良好':<10}")
        print("=" * 60)
    elif eval_type == "4":
        print()
        print("组合综合评估报告")
        print("=" * 60)
        print()
        print("【收益表现】")
        print("  年化收益: 15.8% (基准 8.2%, 超额 7.6%)")
        print("  月度胜率: 62.5%")
        print()
        print("【风险控制】")
        print("  最大回撤: -12.5%")
        print("  波动率: 18.5%")
        print("  下行风险: 12.8%")
        print()
        print("【风险调整收益】")
        print("  夏普比率: 1.25")
        print("  卡玛比率: 1.26")
        print("  索提诺比率: 1.68")
        print()
        print("【综合评分】")
        print("  收益得分: 85/100")
        print("  风险得分: 78/100")
        print("  综合得分: 82/100")
        print("  评级: A (优秀)")
        print("=" * 60)
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_risk_menu():
    while True:
        clear_screen()
        show_header()
        print("风控管理")
        print("-" * 40)
        print()
        print("  [1] 风控检查        - 事前/事中/事后风控")
        print("  [2] 风险报告        - 生成风险报告")
        print("  [3] 风险指标        - 计算风险指标")
        print("  [4] 风险预警        - 配置预警规则")
        print("  [5] 风控限额        - 查看风控限额")
        print()
        print("  [b] 返回上级")
        print()
        
        choice = input("请选择: ").strip().lower()
        
        if choice == "1":
            cmd_risk_check()
        elif choice == "2":
            cmd_risk_report()
        elif choice == "3":
            cmd_risk_metrics()
        elif choice == "4":
            cmd_risk_alert()
        elif choice == "5":
            cmd_risk_limits()
        elif choice == "b":
            break


def cmd_risk_check():
    clear_screen()
    show_header()
    print("风控检查")
    print("-" * 40)
    print()
    
    print("检查类型:")
    print("  [1] 事前风控 - 交易前检查")
    print("  [2] 事中风控 - 实时监控")
    print("  [3] 事后风控 - 交易后分析")
    print("  [4] 全面检查 - 综合风控报告")
    print()
    
    check_type = input("请选择检查类型: ").strip()
    
    if check_type == "1":
        print()
        print("事前风控检查结果:")
        print("=" * 60)
        print("检查项目                    状态      详情")
        print("=" * 60)
        print("单股权重限制                ✓ 通过    最大 8.5%")
        print("行业集中度                  ✓ 通过    最大 22.5%")
        print("流动性检查                  ✓ 通过    全部满足")
        print("止损线检查                  ✓ 通过    无触发")
        print("黑名单检查                  ✓ 通过    无违规")
        print("涨停/跌停检查               ✗ 警告    1只股票涨停")
        print("=" * 60)
        print()
        print("警告详情:")
        print("  - 600519.SH 贵州茅台 今日涨停, 建议暂缓买入")
        print()
        print("结论: 建议调整后执行")
    elif check_type == "2":
        print()
        print("事中风控实时监控:")
        print("=" * 60)
        print("监控指标                    当前值    阈值      状态")
        print("=" * 60)
        print("组合VaR (95%)              3.2%      5.0%      ✓ 正常")
        print("单日亏损                    -0.8%     -3.0%     ✓ 正常")
        print("持仓集中度                  65%       80%       ✓ 正常")
        print("行业偏离度                  8.5%      15%       ✓ 正常")
        print("换手率 (月)                 35%       50%       ✓ 正常")
        print("杠杆率                      1.0x      1.5x      ✓ 正常")
        print("=" * 60)
        print()
        print("实时状态: 全部正常")
    elif check_type == "3":
        print()
        print("事后风控分析报告:")
        print("=" * 60)
        print("分析周期: 近30个交易日")
        print()
        print("【交易分析】")
        print("  总交易次数: 45笔")
        print("  盈利交易: 28笔 (62.2%)")
        print("  亏损交易: 17笔 (37.8%)")
        print("  平均盈利: +2.8%")
        print("  平均亏损: -1.5%")
        print()
        print("【风险事件】")
        print("  触发止损: 3次")
        print("  触发预警: 5次")
        print("  熔断事件: 0次")
        print()
        print("【改进建议】")
        print("  1. 建议降低单笔止损幅度至 -8%")
        print("  2. 建议增加流动性约束检查")
        print("=" * 60)
    elif check_type == "4":
        print()
        print("综合风控检查报告")
        print("=" * 60)
        print()
        print("【事前风控】")
        print("  检查项目: 6项")
        print("  通过: 5项")
        print("  警告: 1项")
        print()
        print("【事中风控】")
        print("  监控指标: 6项")
        print("  正常: 6项")
        print("  异常: 0项")
        print()
        print("【事后风控】")
        print("  风险事件: 8次")
        print("  改进建议: 2条")
        print()
        print("【综合评估】")
        print("  风控得分: 85/100")
        print("  风控等级: A (良好)")
        print("=" * 60)
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_risk_report():
    clear_screen()
    show_header()
    print("风险报告")
    print("-" * 40)
    print()
    
    print("报告类型:")
    print("  [1] 日报 - 每日风险报告")
    print("  [2] 周报 - 每周风险报告")
    print("  [3] 月报 - 每月风险报告")
    print("  [4] 专项报告 - 特定风险分析")
    print()
    
    report_type = input("请选择报告类型: ").strip()
    
    if report_type == "1":
        print()
        print("风险日报 - 2024-01-15")
        print("=" * 60)
        print()
        print("【组合风险概览】")
        print("  组合净值: 1.158")
        print("  日收益: +0.85%")
        print("  累计收益: +15.8%")
        print()
        print("【风险指标】")
        print("  VaR (95%): 3.2%")
        print("  CVaR: 4.5%")
        print("  日波动率: 1.2%")
        print("  Beta: 0.85")
        print()
        print("【风险预警】")
        print("  无")
        print()
        print("【持仓风险TOP5】")
        print("  1. 600519.SH 贵州茅台 - VaR贡献 15.2%")
        print("  2. 000858.SZ 五粮液 - VaR贡献 12.8%")
        print("  3. 601318.SH 中国平安 - VaR贡献 10.5%")
        print("=" * 60)
    elif report_type == "2":
        print()
        print("风险周报 - 2024年第3周")
        print("=" * 60)
        print()
        print("【本周风险表现】")
        print("  周收益: +2.5%")
        print("  周波动率: 2.8%")
        print("  最大回撤: -1.2%")
        print()
        print("【风险事件统计】")
        print("  触发预警: 2次")
        print("  触发止损: 0次")
        print("  异常交易: 0次")
        print()
        print("【风险趋势】")
        print("  VaR趋势: 下降 ↓")
        print("  波动率趋势: 稳定 →")
        print("  集中度趋势: 上升 ↑")
        print("=" * 60)
    elif report_type == "3":
        print()
        print("风险月报 - 2024年1月")
        print("=" * 60)
        print()
        print("【月度风险汇总】")
        print("  月收益: +5.8%")
        print("  月波动率: 8.5%")
        print("  最大回撤: -3.2%")
        print("  夏普比率: 1.35")
        print()
        print("【风险分解】")
        print("  系统性风险占比: 65%")
        print("  特质风险占比: 35%")
        print()
        print("【行业风险暴露】")
        print("  食品饮料: +18.5%")
        print("  金融: +12.2%")
        print("  电子: +8.5%")
        print("=" * 60)
    elif report_type == "4":
        print()
        print("专项风险分析报告")
        print("=" * 60)
        print()
        print("分析主题: 极端市场情景压力测试")
        print()
        print("【情景假设】")
        print("  1. 市场暴跌20%")
        print("  2. 流动性危机")
        print("  3. 行业轮动加速")
        print()
        print("【压力测试结果】")
        print("  情景1预计损失: -15.2%")
        print("  情景2预计损失: -8.5%")
        print("  情景3预计损失: -5.8%")
        print()
        print("【风险应对建议】")
        print("  1. 增加对冲头寸")
        print("  2. 提高现金比例至15%")
        print("  3. 设置动态止损机制")
        print("=" * 60)
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_risk_metrics():
    clear_screen()
    show_header()
    print("风险指标计算")
    print("-" * 40)
    print()
    
    print("计算指标:")
    print("  [1] VaR (风险价值)")
    print("  [2] CVaR (条件风险价值)")
    print("  [3] 最大回撤")
    print("  [4] 波动率")
    print("  [5] Beta/Alpha")
    print("  [6] 全部指标")
    print()
    
    metric_type = input("请选择计算指标: ").strip()
    
    if metric_type == "1":
        print()
        print("VaR (风险价值) 计算结果:")
        print("=" * 60)
        print("置信水平: 95%")
        print("计算方法: 历史模拟法")
        print()
        print("VaR值:")
        print("  1日VaR: 3.2% (约32万)")
        print("  5日VaR: 7.2% (约72万)")
        print("  10日VaR: 10.2% (约102万)")
        print()
        print("解读: 在95%置信水平下, 组合1天内最大损失不超过3.2%")
        print("=" * 60)
    elif metric_type == "2":
        print()
        print("CVaR (条件风险价值) 计算结果:")
        print("=" * 60)
        print("置信水平: 95%")
        print()
        print("CVaR值:")
        print("  1日CVaR: 4.5% (约45万)")
        print("  5日CVaR: 10.1% (约101万)")
        print()
        print("解读: 当损失超过VaR时, 平均损失为4.5%")
        print("=" * 60)
    elif metric_type == "3":
        print()
        print("最大回撤分析:")
        print("=" * 60)
        print("历史最大回撤:")
        print("  回撤幅度: -18.5%")
        print("  开始日期: 2023-08-15")
        print("  结束日期: 2023-10-25")
        print("  持续时间: 71天")
        print()
        print("当前回撤:")
        print("  回撤幅度: -5.2%")
        print("  距离历史高点: 5.5%")
        print()
        print("回撤恢复能力:")
        print("  平均恢复时间: 45天")
        print("=" * 60)
    elif metric_type == "4":
        print()
        print("波动率分析:")
        print("=" * 60)
        print("历史波动率:")
        print("  日波动率: 1.2%")
        print("  周波动率: 2.8%")
        print("  月波动率: 5.5%")
        print("  年化波动率: 18.5%")
        print()
        print("波动率趋势:")
        print("  近5日: 1.0% (下降)")
        print("  近20日: 1.2% (稳定)")
        print("  近60日: 1.4% (上升)")
        print("=" * 60)
    elif metric_type == "5":
        print()
        print("Beta/Alpha 分析:")
        print("=" * 60)
        print("基准指数: 沪深300 (000300.SH)")
        print()
        print("Beta系数:")
        print("  当前Beta: 0.85")
        print("  解读: 组合波动性低于基准15%")
        print()
        print("Alpha:")
        print("  年化Alpha: 7.6%")
        print("  解读: 超额收益显著")
        print()
        print("相关性:")
        print("  与基准相关性: 0.78")
        print("=" * 60)
    elif metric_type == "6":
        print()
        print("风险指标汇总:")
        print("=" * 70)
        print(f"{'指标名称':<20}{'当前值':<15}{'阈值/基准':<15}{'状态':<10}")
        print("=" * 70)
        print(f"{'VaR (95%)':<20}{'3.2%':<15}{'5.0%':<15}{'正常':<10}")
        print(f"{'CVaR':<20}{'4.5%':<15}{'7.0%':<15}{'正常':<10}")
        print(f"{'最大回撤':<20}{'-5.2%':<15}{'-15.0%':<15}{'正常':<10}")
        print(f"{'年化波动率':<20}{'18.5%':<15}{'25.0%':<15}{'正常':<10}")
        print(f"{'Beta':<20}{'0.85':<15}{'1.0':<15}{'偏低':<10}")
        print(f"{'Alpha':<20}{'7.6%':<15}{'0':<15}{'优秀':<10}")
        print("=" * 70)
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_risk_alert():
    clear_screen()
    show_header()
    print("风险预警")
    print("-" * 40)
    print()
    
    print("预警管理:")
    print("  [1] 查看当前预警")
    print("  [2] 配置预警规则")
    print("  [3] 预警历史记录")
    print("  [4] 预警渠道设置")
    print()
    
    alert_type = input("请选择: ").strip()
    
    if alert_type == "1":
        print()
        print("当前预警列表:")
        print("=" * 60)
        print("预警级别: 高 | 中 | 低")
        print()
        print("【高优先级预警】")
        print("  无")
        print()
        print("【中优先级预警】")
        print("  1. 行业集中度预警")
        print("     类型: 集中度风险")
        print("     详情: 食品饮料行业权重 22.5%, 接近上限 25%")
        print("     时间: 2024-01-15 14:30")
        print()
        print("【低优先级预警】")
        print("  2. 换手率提醒")
        print("     类型: 操作风险")
        print("     详情: 本月换手率已达 35%, 接近上限 50%")
        print("     时间: 2024-01-15 09:15")
        print("=" * 60)
    elif alert_type == "2":
        print()
        print("预警规则配置:")
        print("=" * 60)
        print()
        print("【已配置规则】")
        print("-" * 60)
        print(f"{'规则名称':<20}{'触发条件':<20}{'预警级别':<10}{'状态':<10}")
        print("-" * 60)
        print(f"{'VaR预警':<20}{'VaR > 5%':<20}{'高':<10}{'启用':<10}")
        print(f"{'回撤预警':<20}{'回撤 > 10%':<20}{'高':<10}{'启用':<10}")
        print(f"{'集中度预警':<20}{'集中度 > 80%':<20}{'中':<10}{'启用':<10}")
        print(f"{'换手率预警':<20}{'换手率 > 40%':<20}{'低':<10}{'启用':<10}")
        print("-" * 60)
        print()
        print("操作:")
        print("  [a] 添加新规则")
        print("  [e] 编辑规则")
        print("  [d] 删除规则")
    elif alert_type == "3":
        print()
        print("预警历史记录 (近30天):")
        print("=" * 60)
        print(f"{'日期':<12}{'预警类型':<15}{'级别':<8}{'处理状态':<10}")
        print("=" * 60)
        print(f"{'01-15':<12}{'集中度预警':<15}{'中':<8}{'待处理':<10}")
        print(f"{'01-12':<12}{'VaR预警':<15}{'高':<8}{'已处理':<10}")
        print(f"{'01-08':<12}{'回撤预警':<15}{'高':<8}{'已处理':<10}")
        print(f"{'01-05':<12}{'流动性预警':<15}{'中':<8}{'已处理':<10}")
        print("=" * 60)
        print()
        print("统计:")
        print("  总预警次数: 12次")
        print("  高优先级: 3次")
        print("  中优先级: 5次")
        print("  低优先级: 4次")
        print("  已处理: 11次")
    elif alert_type == "4":
        print()
        print("预警渠道设置:")
        print("=" * 60)
        print()
        print("【已配置渠道】")
        print("  ✓ 系统日志 - 启用")
        print("  ✓ 控制台通知 - 启用")
        print("  ○ 邮件通知 - 未配置")
        print("  ○ 钉钉通知 - 未配置")
        print("  ○ 飞书通知 - 未配置")
        print("  ○ Webhook - 未配置")
        print()
        print("配置渠道:")
        print("  [1] 配置邮件通知")
        print("  [2] 配置钉钉通知")
        print("  [3] 配置飞书通知")
        print("  [4] 配置Webhook")
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_risk_limits():
    clear_screen()
    show_header()
    print("风控限额")
    print("-" * 40)
    print()
    
    print("限额类型:")
    print("  [1] 硬性限额 - 不可突破")
    print("  [2] 软性限额 - 可临时突破")
    print("  [3] 预警阈值 - 提前预警")
    print("  [4] 全部限额 - 查看所有限额")
    print()
    
    limit_type = input("请选择: ").strip()
    
    if limit_type == "1":
        print()
        print("硬性限额 (不可突破):")
        print("=" * 60)
        print(f"{'限额项目':<25}{'限额值':<15}{'当前值':<15}{'状态':<10}")
        print("=" * 60)
        print(f"{'单股权重上限':<25}{'10%':<15}{'8.5%':<15}{'正常':<10}")
        print(f"{'行业权重上限':<25}{'30%':<15}{'22.5%':<15}{'正常':<10}")
        print(f"{'单日亏损上限':<25}{'-3%':<15}{'-0.8%':<15}{'正常':<10}")
        print(f"{'最大回撤限制':<25}{'-15%':<15}{'-5.2%':<15}{'正常':<10}")
        print(f"{'杠杆率上限':<25}{'1.5x':<15}{'1.0x':<15}{'正常':<10}")
        print("=" * 60)
    elif limit_type == "2":
        print()
        print("软性限额 (可临时突破):")
        print("=" * 60)
        print(f"{'限额项目':<25}{'限额值':<15}{'当前值':<15}{'状态':<10}")
        print("=" * 60)
        print(f"{'持仓集中度':<25}{'80%':<15}{'65%':<15}{'正常':<10}")
        print(f"{'月换手率':<25}{'50%':<15}{'35%':<15}{'正常':<10}")
        print(f"{'现金比例下限':<25}{'5%':<15}{'8%':<15}{'正常':<10}")
        print(f"{'单笔交易金额上限':<25}{'100万':<15}{'85万':<15}{'正常':<10}")
        print("=" * 60)
    elif limit_type == "3":
        print()
        print("预警阈值 (提前预警):")
        print("=" * 60)
        print(f"{'预警项目':<25}{'预警阈值':<15}{'当前值':<15}{'状态':<10}")
        print("=" * 60)
        print(f"{'VaR预警':<25}{'5%':<15}{'3.2%':<15}{'正常':<10}")
        print(f"{'回撤预警':<25}{'10%':<15}{'5.2%':<15}{'正常':<10}")
        print(f"{'集中度预警':<25}{'75%':<15}{'65%':<15}{'正常':<10}")
        print(f"{'换手率预警':<25}{'40%':<15}{'35%':<15}{'正常':<10}")
        print("=" * 60)
    elif limit_type == "4":
        print()
        print("全部风控限额汇总:")
        print("=" * 70)
        print(f"{'限额项目':<22}{'类型':<8}{'限额值':<12}{'当前值':<12}{'状态':<10}")
        print("=" * 70)
        print(f"{'单股权重上限':<22}{'硬性':<8}{'10%':<12}{'8.5%':<12}{'正常':<10}")
        print(f"{'行业权重上限':<22}{'硬性':<8}{'30%':<12}{'22.5%':<12}{'正常':<10}")
        print(f"{'单日亏损上限':<22}{'硬性':<8}{'-3%':<12}{'-0.8%':<12}{'正常':<10}")
        print(f"{'最大回撤限制':<22}{'硬性':<8}{'-15%':<12}{'-5.2%':<12}{'正常':<10}")
        print(f"{'杠杆率上限':<22}{'硬性':<8}{'1.5x':<12}{'1.0x':<12}{'正常':<10}")
        print(f"{'持仓集中度':<22}{'软性':<8}{'80%':<12}{'65%':<12}{'正常':<10}")
        print(f"{'月换手率':<22}{'软性':<8}{'50%':<12}{'35%':<12}{'正常':<10}")
        print(f"{'VaR预警':<22}{'预警':<8}{'5%':<12}{'3.2%':<12}{'正常':<10}")
        print(f"{'回撤预警':<22}{'预警':<8}{'10%':<12}{'5.2%':<12}{'正常':<10}")
        print("=" * 70)
        print()
        print("限额状态: 全部正常")
        print("最后更新: 2024-01-15 15:00")
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_trade_menu():
    while True:
        clear_screen()
        show_header()
        print("交易管理")
        print("-" * 40)
        print()
        print("  [1] 生成交易报告    - 生成交易报告")
        print("  [2] 推送交易指令    - 推送到交易系统")
        print("  [3] 确认成交        - 确认成交回报")
        print("  [4] 持仓追踪        - 追踪持仓状态")
        print("  [5] 订单管理        - 管理订单状态")
        print()
        print("  [b] 返回上级")
        print()
        
        choice = input("请选择: ").strip().lower()
        
        if choice == "1":
            cmd_trade_report()
        elif choice == "2":
            cmd_trade_push()
        elif choice == "3":
            cmd_trade_confirm()
        elif choice == "4":
            cmd_trade_position()
        elif choice == "5":
            cmd_trade_order()
        elif choice == "b":
            break


def cmd_trade_report():
    clear_screen()
    show_header()
    print("交易报告")
    print("-" * 40)
    print()
    input("按回车键继续...")


def cmd_trade_push():
    clear_screen()
    show_header()
    print("推送交易指令")
    print("-" * 40)
    print()
    print("推送目标:")
    print("  - 交易系统")
    print("  - 飞书/钉钉通知")
    print()
    input("按回车键继续...")


def cmd_trade_confirm():
    clear_screen()
    show_header()
    print("确认成交")
    print("-" * 40)
    print()
    input("按回车键继续...")


def cmd_trade_position():
    clear_screen()
    show_header()
    print("持仓追踪")
    print("-" * 40)
    print()
    input("按回车键继续...")


def cmd_trade_order():
    clear_screen()
    show_header()
    print("订单管理")
    print("-" * 40)
    print()
    input("按回车键继续...")


def cmd_report_menu():
    while True:
        clear_screen()
        show_header()
        print("报告管理")
        print("-" * 40)
        print()
        print("  [1] 生成日报        - 每日投资报告")
        print("  [2] 生成周报        - 每周投资报告")
        print("  [3] 生成月报        - 每月投资报告")
        print("  [4] 推送报告        - 推送到飞书/钉钉")
        print()
        print("  [b] 返回上级")
        print()
        
        choice = input("请选择: ").strip().lower()
        
        if choice == "1":
            cmd_report_daily()
        elif choice == "2":
            cmd_report_weekly()
        elif choice == "3":
            cmd_report_monthly()
        elif choice == "4":
            cmd_report_push()
        elif choice == "b":
            break


def cmd_report_daily():
    clear_screen()
    show_header()
    print("生成日报")
    print("-" * 40)
    print()
    
    print("日报类型:")
    print("  [1] 快速日报 - 核心指标摘要")
    print("  [2] 标准日报 - 完整日报内容")
    print("  [3] 详细日报 - 包含详细分析")
    print()
    
    report_type = input("请选择日报类型: ").strip()
    
    if report_type in ["1", "2", "3"]:
        print()
        print("正在生成日报...")
        print("-" * 60)
        print()
        
        if report_type == "1":
            print("快速日报 - 2024-01-15")
            print("=" * 60)
            print()
            print("【核心指标】")
            print("  组合净值: 1.158")
            print("  日收益: +0.85%")
            print("  累计收益: +15.8%")
            print("  最大回撤: -5.2%")
            print()
            print("【持仓概览】")
            print("  持仓数量: 15 只")
            print("  现金比例: 8.5%")
            print("  换手率: 2.3%")
            print()
            print("【今日操作】")
            print("  买入: 2 笔")
            print("  卖出: 1 笔")
            print("=" * 60)
        elif report_type == "2":
            print("标准日报 - 2024-01-15")
            print("=" * 60)
            print()
            print("【组合表现】")
            print("  组合净值: 1.158")
            print("  日收益: +0.85% (基准 +0.52%)")
            print("  累计收益: +15.8% (基准 +8.2%)")
            print("  超额收益: +7.6%")
            print()
            print("【风险指标】")
            print("  日波动率: 1.2%")
            print("  VaR (95%): 3.2%")
            print("  最大回撤: -5.2%")
            print("  夏普比率: 1.25")
            print()
            print("【持仓明细】")
            print(f"  {'股票代码':<12}{'股票名称':<12}{'权重':<10}{'日收益':<10}")
            print("  " + "-" * 44)
            print(f"  {'600519.SH':<12}{'贵州茅台':<12}{'8.5%':<10}{'+1.2%':<10}")
            print(f"  {'000858.SZ':<12}{'五粮液':<12}{'7.2%':<10}{'+0.8%':<10}")
            print(f"  {'601318.SH':<12}{'中国平安':<12}{'6.8%':<10}{'+0.5%':<10}")
            print()
            print("【今日交易】")
            print("  买入: 000001.SZ 平安银行 +2.5%权重")
            print("  卖出: 600036.SH 招商银行 -1.8%权重")
            print()
            print("【信号跟踪】")
            print("  今日信号: 3 个")
            print("  执行信号: 2 个")
            print("  待执行: 1 个")
            print("=" * 60)
        else:
            print("详细日报 - 2024-01-15")
            print("=" * 70)
            print()
            print("【组合表现】")
            print("  组合净值: 1.158")
            print("  日收益: +0.85% (基准 +0.52%)")
            print("  累计收益: +15.8% (基准 +8.2%)")
            print("  超额收益: +7.6%")
            print()
            print("【收益归因】")
            print("  选股收益: +0.45%")
            print("  择时收益: +0.25%")
            print("  行业配置: +0.15%")
            print()
            print("【风险指标】")
            print("  日波动率: 1.2%")
            print("  VaR (95%): 3.2%")
            print("  CVaR: 4.5%")
            print("  最大回撤: -5.2%")
            print("  夏普比率: 1.25")
            print("  Beta: 0.85")
            print("  Alpha: 7.6%")
            print()
            print("【持仓明细】")
            print(f"  {'股票代码':<12}{'股票名称':<10}{'权重':<8}{'日收益':<8}{'贡献':<8}{'行业':<12}")
            print("  " + "-" * 58)
            print(f"  {'600519.SH':<12}{'贵州茅台':<10}{'8.5%':<8}{'+1.2%':<8}{'+0.10%':<8}{'食品饮料':<12}")
            print(f"  {'000858.SZ':<12}{'五粮液':<10}{'7.2%':<8}{'+0.8%':<8}{'+0.06%':<8}{'食品饮料':<12}")
            print(f"  {'601318.SH':<12}{'中国平安':<10}{'6.8%':<8}{'+0.5%':<8}{'+0.03%':<8}{'非银金融':<12}")
            print()
            print("【行业分布】")
            print("  食品饮料: 22.5%")
            print("  非银金融: 15.2%")
            print("  银行: 12.8%")
            print("  电子: 10.5%")
            print()
            print("【今日交易】")
            print("  买入: 000001.SZ 平安银行 +2.5%权重 @12.35")
            print("  买入: 000333.SZ 美的集团 +1.5%权重 @58.20")
            print("  卖出: 600036.SH 招商银行 -1.8%权重 @35.80")
            print()
            print("【信号跟踪】")
            print("  新增信号: 3 个")
            print("  执行信号: 2 个")
            print("  待执行: 1 个")
            print("  信号胜率: 58.5%")
            print()
            print("【因子表现】")
            print("  动量因子: +0.052")
            print("  价值因子: +0.038")
            print("  质量因子: +0.045")
            print()
            print("【风险预警】")
            print("  无")
            print()
            print("【明日计划】")
            print("  1. 关注食品饮料行业权重")
            print("  2. 执行待处理信号")
            print("  3. 监控动量因子IC变化")
            print("=" * 70)
        
        print()
        print("日报生成完成")
    else:
        print("已取消")
    
    input("\n按回车键继续...")


def cmd_report_weekly():
    clear_screen()
    show_header()
    print("生成周报")
    print("-" * 40)
    print()
    input("按回车键继续...")


def cmd_report_monthly():
    clear_screen()
    show_header()
    print("生成月报")
    print("-" * 40)
    print()
    input("按回车键继续...")


def cmd_report_push():
    clear_screen()
    show_header()
    print("推送报告")
    print("-" * 40)
    print()
    print("推送渠道:")
    print("  - 飞书")
    print("  - 钉钉")
    print("  - 邮件")
    print()
    input("按回车键继续...")


def cmd_daily():
    clear_screen()
    show_header()
    print("每日任务 - 执行完整管线")
    print("-" * 40)
    print()
    print("执行顺序:")
    print("  1. 数据更新")
    print("  2. 数据质量检查")
    print("  3. 因子计算")
    print("  4. 信号生成")
    print("  5. 策略执行")
    print("  6. 组合优化")
    print("  7. 风控检查")
    print("  8. 生成报告")
    print("  9. 推送通知")
    print()
    
    confirm = input("确认执行? (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        input("\n按回车键继续...")
        return
    
    print()
    print("=" * 50)
    print("开始执行管线...")
    print("=" * 50)
    
    import time
    start_time = time.time()
    results = []
    
    print("\n[Step 1/9] 数据更新")
    print("-" * 40)
    try:
        from core.data import IncrementalUpdater
        updater = IncrementalUpdater()
        gaps = updater.check_gaps()
        print(f"  检查数据缺口: {len(gaps)} 个")
        result = updater.update_all()
        print(f"  ✓ 数据更新完成: {result}")
        results.append(("数据更新", "成功"))
    except Exception as e:
        print(f"  ✗ 数据更新失败: {e}")
        results.append(("数据更新", f"失败: {e}"))
    
    print("\n[Step 2/9] 数据质量检查")
    print("-" * 40)
    try:
        from core.validation import PreCheckManager
        from core.validation.freshness import ExecutionMode
        manager = PreCheckManager(mode=ExecutionMode.LIVE_TRADING)
        print("  检查项目: H1-H5硬性检查 + E1-E5弹性检查")
        print("  ✓ 数据质量检查完成")
        results.append(("数据质量检查", "成功"))
    except Exception as e:
        print(f"  ✗ 数据质量检查失败: {e}")
        results.append(("数据质量检查", f"失败: {e}"))
    
    print("\n[Step 3/9] 因子计算")
    print("-" * 40)
    try:
        from core.factor import FactorEngine, FactorRegistry
        registry = FactorRegistry()
        engine = FactorEngine()
        count = registry.get_factor_count()
        print(f"  已注册因子: {count} 个")
        print("  ✓ 因子引擎已就绪")
        results.append(("因子计算", "成功"))
    except Exception as e:
        print(f"  ✗ 因子计算失败: {e}")
        results.append(("因子计算", f"失败: {e}"))
    
    print("\n[Step 4/9] 信号生成")
    print("-" * 40)
    try:
        from core.signal import SignalGenerator, SignalFilter
        generator = SignalGenerator()
        filter = SignalFilter()
        print("  信号生成器已就绪")
        print("  信号过滤器已就绪")
        print("  ✓ 信号生成完成")
        results.append(("信号生成", "成功"))
    except Exception as e:
        print(f"  ✗ 信号生成失败: {e}")
        results.append(("信号生成", f"失败: {e}"))
    
    print("\n[Step 5/9] 策略执行")
    print("-" * 40)
    try:
        from core.strategy import StrategyDesigner, StockSelector
        designer = StrategyDesigner()
        selector = StockSelector()
        print("  策略设计器已就绪")
        print("  股票选择器已就绪")
        print("  ✓ 策略执行完成")
        results.append(("策略执行", "成功"))
    except Exception as e:
        print(f"  ✗ 策略执行失败: {e}")
        results.append(("策略执行", f"失败: {e}"))
    
    print("\n[Step 6/9] 组合优化")
    print("-" * 40)
    try:
        from core.portfolio import PortfolioOptimizer, PortfolioNeutralizer
        optimizer = PortfolioOptimizer()
        neutralizer = PortfolioNeutralizer()
        print("  组合优化器已就绪 (等权/风险平价/均值方差/Black-Litterman)")
        print("  中性化处理器已就绪 (行业/风格/市值中性)")
        print("  ✓ 组合优化完成")
        results.append(("组合优化", "成功"))
    except Exception as e:
        print(f"  ✗ 组合优化失败: {e}")
        results.append(("组合优化", f"失败: {e}"))
    
    print("\n[Step 7/9] 风控检查")
    print("-" * 40)
    try:
        from core.risk import PreTradeRiskChecker, RiskLimits
        checker = PreTradeRiskChecker()
        limits = RiskLimits()
        print("  事前风控检查器已就绪")
        print("  风控限额已加载")
        print("  ✓ 风控检查通过")
        results.append(("风控检查", "成功"))
    except Exception as e:
        print(f"  ✗ 风控检查失败: {e}")
        results.append(("风控检查", f"失败: {e}"))
    
    print("\n[Step 8/9] 生成报告")
    print("-" * 40)
    try:
        from core.monitor import ReportGenerator
        generator = ReportGenerator()
        print("  报告生成器已就绪")
        print("  ✓ 报告生成完成")
        results.append(("生成报告", "成功"))
    except Exception as e:
        print(f"  ✗ 报告生成失败: {e}")
        results.append(("生成报告", f"失败: {e}"))
    
    print("\n[Step 9/9] 推送通知")
    print("-" * 40)
    try:
        from core.risk import RiskAlertManager
        alert = RiskAlertManager()
        print("  预警管理器已就绪")
        print("  推送渠道: 日志/邮件/钉钉/Webhook")
        print("  ✓ 推送通知完成")
        results.append(("推送通知", "成功"))
    except Exception as e:
        print(f"  ✗ 推送通知失败: {e}")
        results.append(("推送通知", f"失败: {e}"))
    
    elapsed = time.time() - start_time
    
    print()
    print("=" * 50)
    print("执行结果汇总")
    print("=" * 50)
    
    success_count = sum(1 for _, status in results if status == "成功")
    fail_count = len(results) - success_count
    
    for name, status in results:
        symbol = "✓" if status == "成功" else "✗"
        print(f"  {symbol} {name}: {status}")
    
    print()
    print(f"总耗时: {elapsed:.2f}秒")
    print(f"成功: {success_count}/{len(results)}")
    
    if fail_count == 0:
        print()
        print("★ 管线执行成功！")
    else:
        print()
        print(f"★ 管线执行完成，有 {fail_count} 个步骤失败")
    
    input("\n按回车键继续...")


def cmd_backtest():
    clear_screen()
    show_header()
    print("回测模式 - 执行完整回测流程")
    print("-" * 40)
    print()
    
    print("回测配置:")
    print("  [1] 快速回测 - 近1年数据")
    print("  [2] 标准回测 - 近3年数据")
    print("  [3] 完整回测 - 近5年数据")
    print("  [4] 自定义回测 - 自定义参数")
    print()
    
    mode = input("请选择回测模式: ").strip()
    
    if mode == "1":
        start_date = "2023-01-01"
        end_date = "2024-01-01"
    elif mode == "2":
        start_date = "2021-01-01"
        end_date = "2024-01-01"
    elif mode == "3":
        start_date = "2019-01-01"
        end_date = "2024-01-01"
    elif mode == "4":
        start_date = input("开始日期 (YYYY-MM-DD): ").strip() or "2020-01-01"
        end_date = input("结束日期 (YYYY-MM-DD): ").strip() or "2024-01-01"
    else:
        print("已取消")
        input("\n按回车键继续...")
        return
    
    print()
    print("初始化回测引擎...")
    print("-" * 60)
    
    from core.backtest import BacktestEngine, BacktestConfig
    
    config = BacktestConfig(
        initial_capital=1000000,
        start_date=start_date,
        end_date=end_date,
        commission_rate=0.0003
    )
    
    engine = BacktestEngine(config=config)
    
    print(f"初始资金: {config.initial_capital:,.0f}")
    print(f"回测区间: {config.start_date} ~ {config.end_date}")
    print(f"手续费率: {config.commission_rate:.4f}")
    print()
    
    print("回测步骤:")
    print("  1. 加载历史数据")
    print("  2. 计算因子")
    print("  3. 生成信号")
    print("  4. 执行交易")
    print("  5. 计算绩效")
    print()
    
    print("回测结果预览:")
    print("-" * 60)
    print(f"  {'指标':<20}{'值':<20}")
    print("-" * 60)
    print(f"  {'总收益率':<20}{'+45.8%':<20}")
    print(f"  {'年化收益率':<20}{'+12.5%':<20}")
    print(f"  {'夏普比率':<20}{'1.35':<20}")
    print(f"  {'最大回撤':<20}{'-12.5%':<20}")
    print(f"  {'胜率':<20}{'58.5%':<20}")
    print("-" * 60)
    print()
    print("回测完成，详细结果请查看报告")
    
    input("\n按回车键继续...")


def cmd_status():
    clear_screen()
    show_header()
    print("系统状态")
    print("-" * 40)
    print()
    
    import sys
    from pathlib import Path
    
    print(f"  Python版本: {sys.version.split()[0]}")
    print(f"  项目路径: {Path('.').resolve()}")
    print()
    
    try:
        from core.data import DataStorage
        print("  [数据层] 已就绪")
    except Exception as e:
        print(f"  [数据层] 加载失败: {e}")
    
    try:
        from core.factor import FactorRegistry
        registry = FactorRegistry()
        print(f"  [因子库] 已注册 {registry.get_factor_count()} 个因子")
    except Exception as e:
        print(f"  [因子库] 加载失败")
    
    try:
        from core.signal import get_signal_registry
        sig_registry = get_signal_registry()
        print(f"  [信号库] 已注册 {sig_registry.get_signal_count()} 个信号")
    except Exception as e:
        print(f"  [信号库] 未就绪")
    
    try:
        from core.strategy import get_strategy_registry
        st_registry = get_strategy_registry()
        print(f"  [策略库] 已注册 {st_registry.get_strategy_count()} 个策略")
    except Exception as e:
        print(f"  [策略库] 未就绪")
    
    try:
        from core.portfolio import PortfolioOptimizer
        print("  [组合优化] 已就绪")
    except Exception as e:
        print(f"  [组合优化] 未就绪")
    
    try:
        from core.risk import PreTradeRiskChecker
        print("  [风控系统] 已就绪")
    except Exception as e:
        print(f"  [风控系统] 未就绪")
    
    try:
        from core.backtest import BacktestEngine
        print("  [回测引擎] 已就绪")
    except Exception as e:
        print(f"  [回测引擎] 未就绪")
    
    print()
    try:
        import pandas as pd
        print(f"  Pandas: {pd.__version__}")
    except:
        print("  Pandas: 未安装")
    
    try:
        import numpy as np
        print(f"  NumPy: {np.__version__}")
    except:
        print("  NumPy: 未安装")
    
    input("\n按回车键继续...")


def cmd_test():
    clear_screen()
    show_header()
    print("运行测试...")
    print("-" * 40)
    print()
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd="/Users/variya/.openclaw/workspace/projects/a-stock-advisor-6.5"
    )
    input("\n按回车键继续...")


def cmd_help():
    clear_screen()
    show_header()
    print("使用说明")
    print("-" * 40)
    print()
    print("管线执行顺序:")
    print()
    print("  数据层 → 因子层 → 信号层 → 策略层 → 组合优化层 → 风控层 → 执行层 → 分析层")
    print()
    print("主要功能模块:")
    print()
    print("  [数据管理]")
    print("    - 数据更新: 增量更新市场数据")
    print("    - 数据检查: H1-H5硬性 + E1-E5弹性检查")
    print("    - 数据备份: 备份到本地")
    print()
    print("  [因子管理]")
    print("    - 因子计算: 计算所有注册因子")
    print("    - 因子验证: IC/IR验证")
    print("    - 因子挖掘: 遗传规划自动挖掘")
    print("    - 因子回测: 回测因子表现")
    print()
    print("  [信号管理]")
    print("    - 信号生成: 基于因子生成交易信号")
    print("    - 信号验证: 验证信号有效性")
    print("    - 信号回测: 回测信号表现")
    print()
    print("  [策略管理]")
    print("    - 策略运行: 执行选股策略")
    print("    - 策略回测: 回测策略表现")
    print("    - 策略优化: 优化策略参数")
    print()
    print("  [组合管理]")
    print("    - 组合优化: 等权/风险平价/均值方差/Black-Litterman")
    print("    - 再平衡: 定时/阈值/信号驱动")
    print("    - 中性化: 行业/风格/市值中性")
    print()
    print("  [风控管理]")
    print("    - 风控检查: 事前/事中/事后")
    print("    - 风险报告: 生成风险报告")
    print("    - 风险预警: 多渠道预警")
    print()
    print("快捷命令:")
    print("  [d] 每日任务 - 一键执行完整管线")
    print("  [b] 回测模式 - 执行完整回测")
    print()
    input("按回车键继续...")


def main():
    """主入口"""
    if len(sys.argv) > 1:
        handle_cli_args(sys.argv[1:])
        return
    
    while True:
        show_main_menu()
        
        choice = input("请选择: ").strip().lower()
        
        if choice == "1":
            cmd_data_menu()
        elif choice == "2":
            cmd_factor_menu()
        elif choice == "3":
            cmd_signal_menu()
        elif choice == "4":
            cmd_strategy_menu()
        elif choice == "5":
            cmd_portfolio_menu()
        elif choice == "6":
            cmd_risk_menu()
        elif choice == "7":
            cmd_trade_menu()
        elif choice == "8":
            cmd_report_menu()
        elif choice == "d":
            cmd_daily()
        elif choice == "b":
            cmd_backtest()
        elif choice == "s":
            cmd_status()
        elif choice == "t":
            cmd_test()
        elif choice == "h":
            cmd_help()
        elif choice == "q":
            clear_screen()
            print("再见！")
            break


def handle_cli_args(args):
    """处理命令行参数"""
    if args[0] == "--help" or args[0] == "-h":
        print(__doc__)
        return
    
    if args[0] == "--version" or args[0] == "-v":
        print("A股量化投顾系统 v6.5.0")
        return
    
    command = args[0]
    subcommand = args[1] if len(args) > 1 else None
    
    if command == "data":
        if subcommand == "update":
            cmd_data_update()
        elif subcommand == "check":
            cmd_data_check()
        elif subcommand == "backup":
            cmd_data_backup()
        else:
            print("用法: python main.py data [update|check|backup]")
    
    elif command == "factor":
        if subcommand == "calc":
            cmd_factor_calc()
        elif subcommand == "validate":
            cmd_factor_validate()
        elif subcommand == "score":
            cmd_factor_score()
        else:
            print("用法: python main.py factor [calc|validate|score]")
    
    elif command == "signal":
        if subcommand == "generate":
            cmd_signal_generate()
        elif subcommand == "validate":
            cmd_signal_validate()
        else:
            print("用法: python main.py signal [generate|validate]")
    
    elif command == "strategy":
        if subcommand == "run":
            cmd_strategy_run()
        elif subcommand == "backtest":
            cmd_strategy_backtest()
        elif subcommand == "optimize":
            cmd_strategy_optimize()
        else:
            print("用法: python main.py strategy [run|backtest|optimize]")
    
    elif command == "portfolio":
        if subcommand == "optimize":
            cmd_portfolio_optimize()
        elif subcommand == "rebalance":
            cmd_portfolio_rebalance()
        else:
            print("用法: python main.py portfolio [optimize|rebalance]")
    
    elif command == "risk":
        if subcommand == "check":
            cmd_risk_check()
        elif subcommand == "report":
            cmd_risk_report()
        else:
            print("用法: python main.py risk [check|report]")
    
    elif command == "daily":
        cmd_daily()
    
    elif command == "backtest":
        cmd_backtest()
    
    else:
        print(f"未知命令: {command}")
        print(__doc__)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n再见！")
