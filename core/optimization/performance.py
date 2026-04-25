"""
WildQuest Matrix - 性能优化模块

针对个人用户（MacBook Air M4 16G）的性能优化：
1. 并行化因子计算（利用 M4 多核）
2. 内存优化（分块处理避免 OOM）
3. 智能增量更新（只下载缺失数据）

Author: Variya
Version: 1.0.0
"""

import multiprocessing
import gc
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


class ParallelFactorCalculator:
    """并行因子计算器，利用 M4 多核性能"""

    def __init__(self, max_workers: Optional[int] = None):
        """
        初始化并行计算器

        Args:
            max_workers: 最大工作进程数，默认为 CPU 核心数 - 2
        """
        # M4 有 8-10 个核心，留 2 个给系统
        self.max_workers = max_workers or (multiprocessing.cpu_count() - 2)
        print(f"并行计算器初始化，使用 {self.max_workers} 个工作进程")

    def calculate_factors(
        self,
        factor_ids: List[str],
        calculate_func: Callable,
        market_data: pd.DataFrame,
        **kwargs
    ) -> Dict[str, Any]:
        """
        并行计算多个因子

        Args:
            factor_ids: 因子 ID 列表
            calculate_func: 因子计算函数
            market_data: 市场数据
            **kwargs: 其他参数

        Returns:
            因子计算结果字典
        """
        results = {}
        failed_factors = []

        print(f"开始并行计算 {len(factor_ids)} 个因子...")

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_factor = {
                executor.submit(calculate_func, fid, market_data, **kwargs): fid
                for fid in factor_ids
            }

            # 收集结果
            for future in as_completed(future_to_factor):
                factor_id = future_to_factor[future]
                try:
                    result = future.result()
                    results[factor_id] = result
                    print(f"✓ 因子 {factor_id} 计算完成")
                except Exception as e:
                    print(f"✗ 因子 {factor_id} 计算失败: {e}")
                    failed_factors.append({
                        'factor_id': factor_id,
                        'error': str(e),
                        'timestamp': datetime.now()
                    })

        print(f"因子计算完成: 成功 {len(results)}/{len(factor_ids)}")
        if failed_factors:
            print(f"失败的因子: {[f['factor_id'] for f in failed_factors]}")

        return {
            'results': results,
            'failed_factors': failed_factors,
            'success_rate': len(results) / len(factor_ids) if factor_ids else 0
        }


class MemoryOptimizedProcessor:
    """内存优化处理器，分块处理避免 OOM"""

    def __init__(self, chunk_size: int = 50):
        """
        初始化内存优化处理器

        Args:
            chunk_size: 每批处理的股票数量，默认 50
        """
        self.chunk_size = chunk_size
        print(f"内存优化处理器初始化，每批处理 {chunk_size} 只股票")

    def process_in_chunks(
        self,
        items: List[Any],
        process_func: Callable,
        **kwargs
    ) -> pd.DataFrame:
        """
        分块处理数据

        Args:
            items: 待处理的项目列表
            process_func: 处理函数
            **kwargs: 其他参数

        Returns:
            处理结果合并后的 DataFrame
        """
        results = []
        total_chunks = (len(items) + self.chunk_size - 1) // self.chunk_size

        for i in range(0, len(items), self.chunk_size):
            chunk = items[i:i + self.chunk_size]
            chunk_num = i // self.chunk_size + 1

            print(f"处理第 {chunk_num}/{total_chunks} 批，共 {len(chunk)} 个项目")

            try:
                # 处理这一批
                chunk_result = process_func(chunk, **kwargs)
                results.append(chunk_result)

                # 及时释放内存
                del chunk_result
                gc.collect()

            except Exception as e:
                print(f"第 {chunk_num} 批处理失败: {e}")
                continue

        # 合并所有结果
        if results:
            final_result = pd.concat(results, ignore_index=True)
            print(f"分块处理完成，共 {len(final_result)} 条记录")
            return final_result
        else:
            print("所有批次都失败了")
            return pd.DataFrame()


class SmartDataUpdater:
    """智能数据更新器，只下载缺失数据"""

    def __init__(self, lookback_days: int = 365):
        """
        初始化智能数据更新器

        Args:
            lookback_days: 回溯天数
        """
        self.lookback_days = lookback_days
        print(f"智能数据更新器初始化，回溯 {lookback_days} 天")

    def get_missing_dates(
        self,
        stock_code: str,
        last_date: datetime,
        current_date: datetime
    ) -> List[datetime]:
        """
        获取缺失的交易日

        Args:
            stock_code: 股票代码
            last_date: 最后数据日期
            current_date: 当前日期

        Returns:
            缺失的交易日列表
        """
        # 这里应该调用交易日历 API
        # 简化实现：返回所有工作日
        missing_dates = []
        date = last_date + timedelta(days=1)

        while date <= current_date:
            # 排除周末
            if date.weekday() < 5:  # 0-4 是周一到周五
                missing_dates.append(date)
            date += timedelta(days=1)

        return missing_dates

    def update_stock_data(
        self,
        stock_code: str,
        download_func: Callable,
        **kwargs
    ) -> Dict[str, Any]:
        """
        更新单只股票的数据

        Args:
            stock_code: 股票代码
            download_func: 下载函数
            **kwargs: 其他参数

        Returns:
            更新结果
        """
        # 检查最新数据日期
        last_date = self._get_last_data_date(stock_code)
        current_date = datetime.now().date()

        if last_date >= current_date:
            return {
                'stock_code': stock_code,
                'updated': False,
                'reason': '数据已是最新',
                'rows_added': 0
            }

        # 获取缺失的交易日
        missing_dates = self.get_missing_dates(stock_code, last_date, current_date)

        if not missing_dates:
            return {
                'stock_code': stock_code,
                'updated': False,
                'reason': '没有缺失的交易日',
                'rows_added': 0
            }

        # 下载缺失的数据
        try:
            data = download_func(stock_code, missing_dates, **kwargs)
            rows_added = len(data)

            return {
                'stock_code': stock_code,
                'updated': True,
                'rows_added': rows_added,
                'date_range': f"{missing_dates[0]} ~ {missing_dates[-1]}"
            }
        except Exception as e:
            return {
                'stock_code': stock_code,
                'updated': False,
                'error': str(e),
                'rows_added': 0
            }

    def update_all_stocks(
        self,
        stock_list: List[str],
        download_func: Callable,
        **kwargs
    ) -> Dict[str, Any]:
        """
        更新所有股票的数据

        Args:
            stock_list: 股票列表
            download_func: 下载函数
            **kwargs: 其他参数

        Returns:
            更新结果汇总
        """
        results = []
        updated_count = 0
        total_rows_added = 0

        print(f"开始智能更新 {len(stock_list)} 只股票的数据...")

        for stock_code in stock_list:
            result = self.update_stock_data(stock_code, download_func, **kwargs)
            results.append(result)

            if result['updated']:
                updated_count += 1
                total_rows_added += result['rows_added']
                print(f"✓ {stock_code}: 新增 {result['rows_added']} 条数据")

        print(f"智能更新完成: 更新了 {updated_count}/{len(stock_list)} 只股票，共 {total_rows_added} 条数据")

        return {
            'total_stocks': len(stock_list),
            'updated_stocks': updated_count,
            'total_rows_added': total_rows_added,
            'results': results
        }

    def _get_last_data_date(self, stock_code: str) -> datetime:
        """
        获取股票最后数据日期

        Args:
            stock_code: 股票代码

        Returns:
            最后数据日期
        """
        # 这里应该从数据库或文件中读取
        # 简化实现：返回一个默认值
        return datetime.now() - timedelta(days=self.lookback_days)


def optimize_pipeline_execution(
    factor_ids: List[str],
    stock_list: List[str],
    calculate_func: Callable,
    download_func: Callable,
    **kwargs
) -> Dict[str, Any]:
    """
    优化管线执行流程

    Args:
        factor_ids: 因子 ID 列表
        stock_list: 股票列表
        calculate_func: 因子计算函数
        download_func: 数据下载函数
        **kwargs: 其他参数

    Returns:
        执行结果
    """
    start_time = datetime.now()

    # 1. 智能数据更新
    print("\n" + "="*60)
    print("步骤 1: 智能数据更新")
    print("="*60)

    data_updater = SmartDataUpdater()
    data_update_result = data_updater.update_all_stocks(stock_list, download_func)

    # 2. 并行因子计算
    print("\n" + "="*60)
    print("步骤 2: 并行因子计算")
    print("="*60)

    parallel_calculator = ParallelFactorCalculator()
    # 这里需要先获取市场数据
    # market_data = get_market_data(stock_list)
    # factor_calc_result = parallel_calculator.calculate_factors(
    #     factor_ids, calculate_func, market_data
    # )

    # 3. 内存优化处理
    print("\n" + "="*60)
    print("步骤 3: 内存优化处理")
    print("="*60)

    memory_processor = MemoryOptimizedProcessor()
    # 这里需要定义处理函数
    # process_result = memory_processor.process_in_chunks(
    #     stock_list, process_func
    # )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "="*60)
    print("优化管线执行完成")
    print("="*60)
    print(f"总耗时: {duration:.2f} 秒")

    return {
        'start_time': start_time,
        'end_time': end_time,
        'duration': duration,
        'data_update': data_update_result,
        # 'factor_calc': factor_calc_result,
        # 'memory_process': process_result,
    }


if __name__ == "__main__":
    # 测试代码
    print("性能优化模块测试")

    # 测试并行计算
    calculator = ParallelFactorCalculator()
    print(f"使用 {calculator.max_workers} 个工作进程")

    # 测试内存优化
    processor = MemoryOptimizedProcessor(chunk_size=50)
    print(f"每批处理 {processor.chunk_size} 个项目")

    # 测试智能更新
    updater = SmartDataUpdater()
    print(f"回溯 {updater.lookback_days} 天")
