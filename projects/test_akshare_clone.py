#!/usr/bin/env python3
"""
测试克隆的AKShare项目

测试内容：
1. 导入克隆的AKShare模块
2. 测试基本功能
3. 对比与pip安装版本的区别
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_cloned_akshare():
    """测试克隆的AKShare项目"""
    
    # 添加克隆项目到路径
    akshare_path = Path("/Users/variya/.openclaw/workspace/projects/akshare-github")
    sys.path.insert(0, str(akshare_path))
    
    logger.info("="*60)
    logger.info("测试克隆的AKShare项目")
    logger.info("="*60)
    logger.info(f"项目路径: {akshare_path}")
    
    try:
        # 导入AKShare
        import akshare as ak
        version = getattr(ak, '__version__', 'unknown')
        logger.info(f"✓ 成功导入AKShare，版本: {version}")
        logger.info(f"  模块路径: {ak.__file__}")
        
        # 测试1: 获取股票列表
        logger.info("\n测试1: 获取股票列表...")
        try:
            df = ak.stock_info_a_code_name()
            if df is not None and len(df) > 0:
                logger.info(f"  ✓ 成功获取 {len(df)} 只股票")
                logger.info(f"  示例: {df.iloc[0]['code']} - {df.iloc[0]['name']}")
            else:
                logger.error("  ✗ 获取股票列表失败：无数据")
        except Exception as e:
            logger.error(f"  ✗ 获取股票列表失败: {e}")
        
        # 测试2: 获取历史数据
        logger.info("\n测试2: 获取历史数据...")
        test_code = "000001"
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        end_date = datetime.now().strftime('%Y%m%d')
        
        try:
            df = ak.stock_zh_a_hist(
                symbol=test_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if df is not None and len(df) > 0:
                logger.info(f"  ✓ 成功获取 {test_code} 历史数据")
                logger.info(f"  数据量: {len(df)} 条")
                logger.info(f"  列: {list(df.columns)}")
                print("\n数据预览:")
                print(df.head())
            else:
                logger.warning(f"  ⚠ {test_code} 无数据")
        except Exception as e:
            logger.error(f"  ✗ 获取 {test_code} 历史数据失败: {e}")
        
        # 测试3: 获取实时行情
        logger.info("\n测试3: 获取实时行情...")
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and len(df) > 0:
                logger.info(f"  ✓ 成功获取实时行情，共 {len(df)} 只股票")
                
                # 查找测试股票
                stock_data = df[df['代码'] == test_code]
                if len(stock_data) > 0:
                    row = stock_data.iloc[0]
                    logger.info(f"  {row['名称']} ({test_code}):")
                    logger.info(f"    最新价: {row['最新价']}")
                    logger.info(f"    涨跌幅: {row['涨跌幅']}%")
                else:
                    logger.warning(f"  ⚠ 未找到股票 {test_code}")
            else:
                logger.warning("  ⚠ 无实时行情数据（可能非交易时间）")
        except Exception as e:
            logger.error(f"  ✗ 获取实时行情失败: {e}")
        
        logger.info("\n" + "="*60)
        logger.info("✓ AKShare克隆项目测试完成")
        logger.info("="*60)
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ 导入AKShare失败: {e}")
        logger.error("  请确保克隆的项目完整且依赖已安装")
        return False
    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def compare_with_pip_version():
    """对比克隆版本与pip安装版本"""
    
    logger.info("\n" + "="*60)
    logger.info("对比克隆版本与pip安装版本")
    logger.info("="*60)
    
    # 测试pip安装版本
    logger.info("\n测试pip安装版本:")
    try:
        import importlib
        import akshare as ak_pip
        pip_version = getattr(ak_pip, '__version__', 'unknown')
        pip_path = ak_pip.__file__
        logger.info(f"  版本: {pip_version}")
        logger.info(f"  路径: {pip_path}")
    except Exception as e:
        logger.error(f"  ✗ pip版本测试失败: {e}")
    
    # 测试克隆版本
    logger.info("\n测试克隆版本:")
    akshare_path = Path("/Users/variya/.openclaw/workspace/projects/akshare-github")
    sys.path.insert(0, str(akshare_path))
    
    try:
        import importlib
        import akshare as ak_clone
        clone_version = getattr(ak_clone, '__version__', 'unknown')
        clone_path = ak_clone.__file__
        logger.info(f"  版本: {clone_version}")
        logger.info(f"  路径: {clone_path}")
    except Exception as e:
        logger.error(f"  ✗ 克隆版本测试失败: {e}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='测试克隆的AKShare项目')
    parser.add_argument('--compare', action='store_true', help='对比克隆版本与pip版本')
    
    args = parser.parse_args()
    
    if args.compare:
        compare_with_pip_version()
    else:
        test_cloned_akshare()
