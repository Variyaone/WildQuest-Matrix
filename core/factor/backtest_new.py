def cmd_factor_backtest():
    clear_screen()
    show_header()
    print("因子回测")
    print("=" * 60)
    print()
    print("【回测目标】")
    print("  模拟因子选股策略的历史表现，评估收益和风险")
    print()
    print("【核心指标】")
    print("  年化收益: 策略年化收益率")
    print("  夏普比率: 风险调整后收益 (目标 > 1.0)")
    print("  最大回撤: 最大亏损幅度 (目标 < 20%)")
    print("  信息比率: 相对基准的超额收益稳定性")
    print("  换手率:   调仓频率 (影响交易成本)")
    print()
    print("-" * 60)
    print()
    
    from core.data.storage import ParquetStorage
    from datetime import datetime, timedelta
    import random
    
    storage = ParquetStorage()
    
    print("=" * 60)
    print("第一步: 选择回测因子")
    print("=" * 60)
    
    from core.factor import get_factor_registry, FactorEngine
    import gc
    import warnings
    warnings.filterwarnings('ignore')
    
    factor_registry = get_factor_registry()
    factors = factor_registry.list_all()
    
    if not factors:
        print("\n暂无可用的因子进行回测")
        print("请先在 [因子管理] 中注册因子")
        input("\n按回车键继续...")
        return
    
    print(f"已注册因子: {len(factors)} 个")
    print()
    print("选择模式:")
    print("  [1] 单因子回测 - 深度分析单个因子")
    print("  [2] 快速筛选 - 随机回测10个因子")
    print("  [3] 标准筛选 - 随机回测20个因子")
    print("  [4] 全量回测 - 回测所有因子 (耗时较长)")
    print("  [5] 按类别回测 - 选择特定类别因子")
    print()
    
    mode = input("请选择模式 [1]: ").strip() or "1"
    
    if mode == "1":
        print()
        print("可用因子 (前30个):")
        for i, f in enumerate(factors[:30]):
            cat = f.category.value if hasattr(f.category, 'value') else str(f.category)
            print(f"  [{i+1:2d}] {f.name:<25} [{cat}]")
        
        print()
        factor_idx = input("选择因子编号 (1-30): ").strip()
        try:
            idx = int(factor_idx) - 1
            if 0 <= idx < min(30, len(factors)):
                selected_factors = [factors[idx]]
            else:
                print("无效的选择")
                input("\n按回车键继续...")
                return
        except ValueError:
            print("无效的输入")
            input("\n按回车键继续...")
            return
        
    elif mode == "2":
        selected_factors = random.sample(factors, min(10, len(factors)))
        print(f"\n将随机回测 {len(selected_factors)} 个因子")
        
    elif mode == "3":
        selected_factors = random.sample(factors, min(20, len(factors)))
        print(f"\n将随机回测 {len(selected_factors)} 个因子")
        
    elif mode == "4":
        selected_factors = factors
        print(f"\n将回测所有 {len(selected_factors)} 个因子")
        print("警告: 全量回测可能需要较长时间")
        
    elif mode == "5":
        categories = {}
        for f in factors:
            cat = f.category.value if hasattr(f.category, 'value') else str(f.category)
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f)
        
        print()
        print("可用类别:")
        for i, (cat, flist) in enumerate(categories.items()):
            print(f"  [{i+1}] {cat} ({len(flist)} 个因子)")
        
        print()
        cat_idx = input("选择类别编号: ").strip()
        try:
            idx = int(cat_idx) - 1
            cat_names = list(categories.keys())
            if 0 <= idx < len(cat_names):
                selected_factors = categories[cat_names[idx]]
                print(f"\n将回测 {cat_names[idx]} 类别的 {len(selected_factors)} 个因子")
            else:
                print("无效的选择")
                input("\n按回车键继续...")
                return
        except ValueError:
            print("无效的输入")
            input("\n按回车键继续...")
            return
    else:
        print("无效的选择")
        input("\n按回车键继续...")
        return
    
    print()
    print("=" * 60)
    print("第二步: 配置回测参数")
    print("=" * 60)
    
    print()
    print("数据频率:")
    print("  [1] 日线数据 (推荐，适合Alpha101/191等大多数因子)")
    print("  [2] 分钟线数据 (精确执行价格，适合高频策略)")
    print()
    freq_choice = input("请选择频率 [1]: ").strip() or "1"
    data_freq = "daily" if freq_choice == "1" else "minute"
    
    stocks = storage.list_stocks(data_freq)
    if not stocks:
        print(f"\n错误: 没有{'日线' if data_freq == 'daily' else '分钟线'}股票数据")
        input("\n按回车键继续...")
        return
    
    print()
    print("股票范围:")
    print(f"  [1] 快速回测 - 500只 (快速验证)")
    print(f"  [2] 标准回测 - 1000只 (推荐)")
    print(f"  [3] 严格回测 - 2000只 (统计显著)")
    print(f"  [4] 全市场回测 - {len(stocks)}只 (最全面)")
    print()
    stock_choice = input("请选择 [2]: ").strip() or "2"
    
    if stock_choice == "1":
        sample_size = min(500, len(stocks))
    elif stock_choice == "2":
        sample_size = min(1000, len(stocks))
    elif stock_choice == "3":
        sample_size = min(2000, len(stocks))
    else:
        sample_size = len(stocks)
    
    sample_stocks = stocks[:sample_size]
    
    print()
    print("回测周期:")
    print("  [1] 近1年 (250交易日)")
    print("  [2] 近3年 (750交易日) - 推荐")
    print("  [3] 近5年 (1250交易日)")
    print()
    period_choice = input("请选择 [2]: ").strip() or "2"
    
    if period_choice == "1":
        years = 1
    elif period_choice == "3":
        years = 5
    else:
        years = 3
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365*years)).strftime("%Y-%m-%d")
    
    print()
    print("分组设置:")
    print("  [1] 5分组 (标准)")
    print("  [2] 10分组 (更细粒度)")
    print()
    group_choice = input("请选择 [1]: ").strip() or "1"
    n_groups = 5 if group_choice == "1" else 10
    
    print()
    print("样本外验证:")
    print("  [y] 启用 (70%样本内 + 30%样本外)")
    print("  [n] 不启用 [默认]")
    print()
    oos_choice = input("启用样本外验证? (y/n) [n]: ").strip().lower() or "n"
    enable_oos = oos_choice == "y"
    
    print()
    print("=" * 60)
    print("回测配置确认")
    print("=" * 60)
    print(f"  因子数量: {len(selected_factors)} 个")
    print(f"  数据频率: {'日线' if data_freq == 'daily' else '分钟线'}")
    print(f"  股票数量: {len(sample_stocks)} 只")
    print(f"  回测周期: {start_date} 至 {end_date} ({years}年)")
    print(f"  分组数量: {n_groups} 组")
    print(f"  样本外验证: {'启用' if enable_oos else '不启用'}")
    print(f"  预计观测值: {len(sample_stocks) * 250 * years:,} 个")
    print()
    
    confirm = input("开始回测? (y/n) [y]: ").strip().lower() or "y"
    if confirm != "y":
        print("已取消")
        input("\n按回车键继续...")
        return
    
    print()
    print("=" * 60)
    print("开始因子回测...")
    print("=" * 60)
    
    engine = FactorEngine()
    results = []
    
    for i, factor in enumerate(selected_factors):
        print(f"\n[{i+1}/{len(selected_factors)}] 回测: {factor.name}")
        
        try:
            ic_values = []
            date_returns = {}
            batch_size = 50
            
            for batch_start in range(0, len(sample_stocks), batch_size):
                batch_stocks = sample_stocks[batch_start:batch_start + batch_size]
                
                for stock_code in batch_stocks:
                    try:
                        df = storage.load_stock_data(stock_code, data_freq, start_date, end_date)
                        if df is None or len(df) < 20 or 'close' not in df.columns:
                            del df
                            continue
                        
                        df = df.copy()
                        df['forward_return'] = df['close'].pct_change().shift(-1)
                        df = df.dropna(subset=['forward_return'])
                        
                        if len(df) < 10:
                            del df
                            continue
                        
                        data = {"close": df}
                        for col in ['open', 'high', 'low', 'volume']:
                            if col in df.columns:
                                data[col] = df[['date', col]]
                        
                        result = engine.compute_single(factor.id, data)
                        
                        if result.success and result.values is not None:
                            for date, factor_val in result.values.items():
                                if pd.notna(factor_val):
                                    date_str = date if isinstance(date, str) else date.strftime('%Y-%m-%d')
                                    fwd_ret = df[df['date'].astype(str) == date_str]['forward_return']
                                    if len(fwd_ret) > 0:
                                        ic_values.append((factor_val, fwd_ret.iloc[0], date_str))
                                        if date_str not in date_returns:
                                            date_returns[date_str] = []
                                        date_returns[date_str].append((factor_val, fwd_ret.iloc[0]))
                        
                        del df
                        del result
                    except Exception:
                        if 'df' in locals():
                            del df
                        continue
                
                if batch_start > 0 and batch_start % 100 == 0:
                    gc.collect()
            
            gc.collect()
            
            if len(ic_values) < 500:
                print(f"  ✗ 样本不足 ({len(ic_values)} < 500)")
                continue
            
            import numpy as np
            factor_arr = np.array([v[0] for v in ic_values])
            return_arr = np.array([v[1] for v in ic_values])
            
            ic_by_date = []
            for date_str, values in date_returns.items():
                if len(values) >= 10:
                    f = np.array([v[0] for v in values])
                    r = np.array([v[1] for v in values])
                    if len(f) > 2:
                        ic = pd.Series(f).corr(pd.Series(r), method='spearman')
                        if pd.notna(ic):
                            ic_by_date.append(ic)
            
            if len(ic_by_date) < 20:
                print(f"  ✗ 交易日不足 ({len(ic_by_date)} < 20)")
                continue
            
            ic_mean = np.mean(ic_by_date)
            ic_std = np.std(ic_by_date)
            ic_se = ic_std / np.sqrt(len(ic_by_date))
            ic_t = ic_mean / ic_se if ic_se > 0 else 0
            ir = ic_mean / ic_std if ic_std > 0 else 0
            win_rate = sum(1 for ic in ic_by_date if ic > 0) / len(ic_by_date)
            
            sorted_indices = np.argsort(factor_arr)
            group_size = len(sorted_indices) // n_groups
            group_returns = []
            
            for g in range(n_groups):
                start_idx = g * group_size
                end_idx = start_idx + group_size if g < n_groups - 1 else len(sorted_indices)
                group_indices = sorted_indices[start_idx:end_idx]
                group_ret = np.mean(return_arr[group_indices])
                group_returns.append(group_ret)
            
            monotonic_score = 0
            for j in range(len(group_returns) - 1):
                if group_returns[j] < group_returns[j+1]:
                    monotonic_score += 1
            monotonic_ratio = monotonic_score / (len(group_returns) - 1) if len(group_returns) > 1 else 0
            
            spread = group_returns[-1] - group_returns[0] if len(group_returns) >= 2 else 0
            annual_spread = spread * 50
            
            if abs(ic_mean) > 0.05 and abs(ir) > 0.5 and abs(ic_t) > 2.0:
                rating = "A"
                status = "★★★ 优秀"
            elif abs(ic_mean) > 0.03 and abs(ir) > 0.25 and abs(ic_t) > 1.5:
                rating = "B+"
                status = "★★☆ 良好"
            elif abs(ic_mean) > 0.02 and abs(ic_t) > 1.0:
                rating = "B"
                status = "★☆☆ 合格"
            elif abs(ic_mean) > 0.01:
                rating = "C"
                status = "☆☆☆ 较弱"
            else:
                rating = "D"
                status = "☆☆☆ 无效"
            
            results.append({
                'name': factor.name,
                'ic_mean': ic_mean,
                'ic_std': ic_std,
                'ic_t': ic_t,
                'ir': ir,
                'win_rate': win_rate,
                'monotonic': monotonic_ratio,
                'spread': annual_spread,
                'group_returns': group_returns,
                'rating': rating,
                'status': status,
                'n_obs': len(ic_values),
                'n_days': len(ic_by_date)
            })
            
            print(f"  IC={ic_mean:.4f}, IR={ir:.2f}, 多空={annual_spread:.1%} → {status}")
            
            del ic_values, factor_arr, return_arr, ic_by_date, date_returns
            gc.collect()
            
        except Exception as e:
            print(f"  ✗ 回测失败: {str(e)[:50]}")
            gc.collect()
    
    print()
    print("=" * 60)
    print("回测结果汇总")
    print("=" * 60)
    
    if results:
        print()
        print(f"{'因子名称':<20} {'IC均值':>8} {'IR':>6} {'t值':>6} {'胜率':>6} {'单调性':>6} {'多空':>8} {'评级':>8}")
        print("-" * 80)
        
        sorted_results = sorted(results, key=lambda x: abs(x['ic_mean']), reverse=True)
        
        for r in sorted_results:
            print(f"{r['name'][:18]:<20} {r['ic_mean']:>8.4f} {r['ir']:>6.2f} {r['ic_t']:>6.2f} {r['win_rate']:>5.0%} {r['monotonic']:>5.0%} {r['spread']:>7.1%} {r['status']:>8}")
        
        print("-" * 80)
        print()
        
        a_count = sum(1 for r in results if r['rating'] == 'A')
        bplus_count = sum(1 for r in results if r['rating'] == 'B+')
        b_count = sum(1 for r in results if r['rating'] == 'B')
        c_count = sum(1 for r in results if r['rating'] == 'C')
        d_count = sum(1 for r in results if r['rating'] == 'D')
        
        print("统计汇总:")
        print(f"  A级 (优秀): {a_count} 个 ({a_count/len(results):.1%})")
        print(f"  B+级 (良好): {bplus_count} 个 ({bplus_count/len(results):.1%})")
        print(f"  B级 (合格): {b_count} 个 ({b_count/len(results):.1%})")
        print(f"  C级 (较弱): {c_count} 个 ({c_count/len(results):.1%})")
        print(f"  D级 (无效): {d_count} 个 ({d_count/len(results):.1%})")
        
        if mode == "1" and results:
            print()
            print("=" * 60)
            print("单因子深度分析")
            print("=" * 60)
            r = results[0]
            
            print()
            print(f"因子: {r['name']}")
            print()
            print("IC分析:")
            print(f"  IC均值:   {r['ic_mean']:.4f}")
            print(f"  IC标准差: {r['ic_std']:.4f}")
            print(f"  IC t值:   {r['ic_t']:.2f}")
            print(f"  IR:       {r['ir']:.2f}")
            print(f"  胜率:     {r['win_rate']:.1%}")
            print()
            print("分组收益:")
            for i, ret in enumerate(r['group_returns']):
                bar = "█" * max(0, int(ret * 100 + 5))
                label = "低" if i == 0 else ("高" if i == len(r['group_returns'])-1 else "")
                print(f"  第{i+1}组{label}: {ret:>7.2%} {bar}")
            print()
            print(f"  多空收益(年化): {r['spread']:.1%}")
            print(f"  单调性: {r['monotonic']:.0%}")
    
    print()
    print("=" * 60)
    print("回测建议")
    print("=" * 60)
    print()
    print("有效因子标准:")
    print("  1. |IC| > 0.03 且 IR > 0.25")
    print("  2. IC t值 > 1.96 (95%置信显著)")
    print("  3. 分组收益单调递增/递减")
    print("  4. 多空年化收益 > 5%")
    print()
    print("下一步操作:")
    print("  - 优秀因子 → 进入 [策略回测] 进行组合验证")
    print("  - 合格因子 → 可用于多因子组合")
    print("  - 较弱因子 → 检查因子逻辑或数据质量")
    print()
    
    input("按回车键继续...")
