"""
批量录入公开策略和因子

本脚本将从多个公开来源整理适合A股的策略和因子，并录入到策略库和因子库中。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factor.quick_entry import get_factor_quick_entry, get_strategy_quick_entry, QuickEntryResult
from core.factor.registry import FactorCategory, FactorSubCategory, FactorDirection
from core.strategy.registry import StrategyType, RebalanceFrequency, RiskParams
from core.strategy.factor_combiner import FactorCombinationConfig

factor_entry = get_factor_quick_entry()
strategy_entry = get_strategy_quick_entry()

factors_to_add = [
    {
        "name": "动量因子_20日",
        "formula": "close / close.shift(20) - 1",
        "description": "20日价格动量因子，计算过去20个交易日的收益率",
        "source": "学术论文",
        "category": "动量",
        "direction": "正向",
        "tags": ["动量", "趋势", "短期"]
    },
    {
        "name": "动量因子_60日",
        "formula": "close / close.shift(60) - 1",
        "description": "60日价格动量因子，计算过去60个交易日的收益率",
        "source": "学术论文",
        "category": "动量",
        "direction": "正向",
        "tags": ["动量", "趋势", "中期"]
    },
    {
        "name": "残差动量因子",
        "formula": "(close / close.shift(60) - 1) - (benchmark_close / benchmark_close.shift(60) - 1)",
        "description": "60日残差动量因子，扣除基准收益后的超额动量",
        "source": "学术论文",
        "category": "动量",
        "direction": "正向",
        "tags": ["动量", "超额收益", "中期"]
    },
    {
        "name": "反转因子_5日",
        "formula": "-1 * (close / close.shift(5) - 1)",
        "description": "5日反转因子，短期反转效应",
        "source": "学术论文",
        "category": "动量",
        "direction": "反向",
        "tags": ["反转", "短期"]
    },
    {
        "name": "估值因子_PE倒数",
        "formula": "1 / pe_ratio",
        "description": "市盈率倒数因子，PE越低得分越高",
        "source": "学术论文",
        "category": "估值",
        "direction": "正向",
        "tags": ["估值", "价值"]
    },
    {
        "name": "估值因子_PB",
        "formula": "pb_ratio",
        "description": "市净率因子",
        "source": "学术论文",
        "category": "估值",
        "direction": "反向",
        "tags": ["估值", "价值"]
    },
    {
        "name": "质量因子_ROE",
        "formula": "roe",
        "description": "净资产收益率因子",
        "source": "学术论文",
        "category": "质量",
        "direction": "正向",
        "tags": ["质量", "盈利能力"]
    },
    {
        "name": "质量因子_ROA",
        "formula": "roa",
        "description": "总资产收益率因子",
        "source": "学术论文",
        "category": "质量",
        "direction": "正向",
        "tags": ["质量", "盈利能力"]
    },
    {
        "name": "成长因子_净利润增长率",
        "formula": "inc_net_profit_year_on_year",
        "description": "净利润同比增长率因子",
        "source": "学术论文",
        "category": "成长",
        "direction": "正向",
        "tags": ["成长", "盈利增长"]
    },
    {
        "name": "成长因子_营收增长率",
        "formula": "revenue_growth_rate",
        "description": "营业收入同比增长率因子",
        "source": "学术论文",
        "category": "成长",
        "direction": "正向",
        "tags": ["成长", "营收增长"]
    },
    {
        "name": "波动率因子_ATR",
        "formula": "talib.ATR(high, low, close, timeperiod=14)",
        "description": "平均真实波幅因子",
        "source": "学术论文",
        "category": "波动率",
        "direction": "反向",
        "tags": ["波动率", "风险"]
    },
    {
        "name": "波动率因子_标准差",
        "formula": "close.pct_change().rolling(20).std()",
        "description": "20日收益率标准差因子",
        "source": "学术论文",
        "category": "波动率",
        "direction": "反向",
        "tags": ["波动率", "风险"]
    },
    {
        "name": "流动性因子_换手率",
        "formula": "turnover_rate",
        "description": "换手率因子",
        "source": "学术论文",
        "category": "流动性",
        "direction": "正向",
        "tags": ["流动性", "交易活跃度"]
    },
    {
        "name": "流动性因子_成交量",
        "formula": "volume",
        "description": "成交量因子",
        "source": "学术论文",
        "category": "流动性",
        "direction": "正向",
        "tags": ["流动性", "交易活跃度"]
    },
    {
        "name": "规模因子_市值",
        "formula": "market_cap",
        "description": "总市值因子",
        "source": "学术论文",
        "category": "规模",
        "direction": "反向",
        "tags": ["规模", "市值"]
    },
    {
        "name": "规模因子_流通市值",
        "formula": "circulating_market_cap",
        "description": "流通市值因子",
        "source": "学术论文",
        "category": "规模",
        "direction": "反向",
        "tags": ["规模", "市值"]
    },
    {
        "name": "技术因子_MACD",
        "formula": "talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)[0]",
        "description": "MACD指标因子",
        "source": "第三方",
        "category": "技术",
        "direction": "正向",
        "tags": ["技术", "趋势"]
    },
    {
        "name": "技术因子_RSI",
        "formula": "talib.RSI(close, timeperiod=14)",
        "description": "RSI相对强弱指标因子",
        "source": "第三方",
        "category": "技术",
        "direction": "正向",
        "tags": ["技术", "超买超卖"]
    },
    {
        "name": "技术因子_布林带宽度",
        "formula": "(talib.BBANDS(close, timeperiod=20)[0] - talib.BBANDS(close, timeperiod=20)[2]) / talib.BBANDS(close, timeperiod=20)[1]",
        "description": "布林带宽度因子，衡量波动率",
        "source": "第三方",
        "category": "技术",
        "direction": "正向",
        "tags": ["技术", "波动率"]
    },
    {
        "name": "北向资金因子",
        "formula": "north_money_flow_change_rate_5d",
        "description": "北向资金5日变化率因子",
        "source": "第三方",
        "category": "情绪",
        "direction": "正向",
        "tags": ["情绪", "资金流向", "北向资金"]
    },
    {
        "name": "拥挤度因子",
        "formula": "(volume / volume.rolling(20).mean()) * (turnover_rate / turnover_rate.rolling(20).mean())",
        "description": "拥挤度因子，结合成交量和换手率",
        "source": "第三方",
        "category": "情绪",
        "direction": "反向",
        "tags": ["情绪", "拥挤度"]
    },
    {
        "name": "PEG因子",
        "formula": "pe_ratio / inc_net_profit_year_on_year",
        "description": "PEG因子，估值与成长匹配度",
        "source": "学术论文",
        "category": "估值",
        "direction": "反向",
        "tags": ["估值", "成长", "综合"]
    },
    {
        "name": "量价背离因子",
        "formula": "close / close.rolling(20).max() - volume / volume.rolling(20).mean()",
        "description": "量价背离因子，股价创新高但成交量未放大时为负值",
        "source": "第三方",
        "category": "技术",
        "direction": "反向",
        "tags": ["技术", "量价关系"]
    },
    {
        "name": "均线多头排列因子",
        "formula": "(close.rolling(5).mean() > close.rolling(10).mean()) & (close.rolling(10).mean() > close.rolling(20).mean())",
        "description": "均线多头排列因子，5日>10日>20日均线",
        "source": "第三方",
        "category": "技术",
        "direction": "正向",
        "tags": ["技术", "趋势"]
    },
    {
        "name": "冲击成本因子",
        "formula": "0.2 * circulating_market_cap / (volume * turnover_rate)",
        "description": "冲击成本因子，衡量流动性风险",
        "source": "第三方",
        "category": "流动性",
        "direction": "反向",
        "tags": ["流动性", "冲击成本"]
    },
]

strategies_to_add = [
    {
        "name": "A股ETF动量轮动策略",
        "description": "基于动量模型的A股ETF投资策略，月度调仓，选取合成得分前3-5只行业ETF等权配置。因子体系包括动量、资金流/拥挤度、估值/风险。",
        "factors": ["动量因子_20日", "动量因子_60日", "拥挤度因子", "估值因子_PE倒数"],
        "rebalance_freq": "monthly",
        "stock_pool": "A股ETF",
        "max_stocks": 5,
        "source": "雪球-基于动量模型的A股ETF投资策略研究报告",
        "tags": ["ETF轮动", "动量", "月度调仓"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.25,
            "max_industry_weight": 0.30,
            "stop_loss": -0.15,
            "position_limit": 0.95
        }
    },
    {
        "name": "月度大小盘轮动策略",
        "description": "通过国证2000 vs 中证500的20日涨跌幅均值比较判断市场风格，在大盘和小盘风格间切换。大盘风格选市值大、基本面优秀股票，小盘风格选小市值低价股。",
        "factors": ["动量因子_20日", "规模因子_市值", "质量因子_ROE", "质量因子_ROA"],
        "rebalance_freq": "monthly",
        "stock_pool": "全市场",
        "max_stocks": 5,
        "source": "雪球-每天一个量化策略：月度大小盘轮动策略",
        "tags": ["风格轮动", "大小盘", "月度调仓"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.20,
            "max_industry_weight": 0.30,
            "stop_loss": -0.12,
            "position_limit": 0.95
        }
    },
    {
        "name": "多因子行业ETF轮动策略",
        "description": "基于多因子打分模型的行业ETF轮动策略，每月初在全市场一级行业ETF中选取综合评分最高的5只等权配置。因子体系包括估值、动量、财务质量、资金流向。",
        "factors": ["估值因子_PE倒数", "估值因子_PB", "动量因子_20日", "质量因子_ROE", "北向资金因子"],
        "rebalance_freq": "monthly",
        "stock_pool": "行业ETF",
        "max_stocks": 5,
        "source": "雪球-量化策略分享：基于多因子打分模型的行业ETF轮动策略",
        "tags": ["ETF轮动", "多因子", "月度调仓"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.20,
            "max_industry_weight": 0.40,
            "stop_loss": -0.15,
            "position_limit": 0.95
        }
    },
    {
        "name": "低波动价值优选策略",
        "description": "融合价值投资与量化风控理念，通过PEG因子筛选估值合理且盈利增长明确的股票，引入换手率波动率指标过滤短期交易过热的股票。支持日线和月度调仓。",
        "factors": ["PEG因子", "波动率因子_标准差", "流动性因子_换手率", "规模因子_流通市值"],
        "rebalance_freq": "daily",
        "stock_pool": "全市场",
        "max_stocks": 5,
        "source": "东方财富-低波动价值优选量化策略",
        "tags": ["价值投资", "低波动", "日线调仓"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.20,
            "max_industry_weight": 0.30,
            "stop_loss": -0.10,
            "position_limit": 0.95
        }
    },
    {
        "name": "多因子动态调仓模型",
        "description": "基于深证100指数成分股，通过行业分散、趋势跟踪、风险控制三重逻辑实现动态调仓。每周二调仓，支持涨停股跟踪和动态止损。",
        "factors": ["规模因子_流通市值", "技术因子_MACD", "波动率因子_ATR"],
        "rebalance_freq": "weekly",
        "stock_pool": "深证100",
        "max_stocks": 6,
        "source": "聚宽-小市值策略就是选股太过于严格",
        "tags": ["多因子", "周度调仓", "风险控制"],
        "benchmark": "399101.XSHE",
        "risk_params": {
            "max_single_weight": 0.167,
            "max_industry_weight": 0.30,
            "stop_loss": -0.09,
            "position_limit": 0.95
        }
    },
    {
        "name": "市值动量多维度切换策略",
        "description": "通过比较大市值vs小市值股票的10日动量，结合大盘位置判断市场风格，在大市值、小市值、外盘ETF间切换。每周调仓。",
        "factors": ["动量因子_20日", "规模因子_市值", "估值因子_PE倒数", "质量因子_ROE"],
        "rebalance_freq": "weekly",
        "stock_pool": "沪深300+中小板",
        "max_stocks": 3,
        "source": "东方财富-「市值动量」多维度切换策略",
        "tags": ["风格轮动", "市值动量", "周度调仓"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.333,
            "max_industry_weight": 0.40,
            "stop_loss": -0.15,
            "position_limit": 0.95
        }
    },
    {
        "name": "OpenFE多因子融合策略",
        "description": "基于OpenFE驱动下的多因子融合策略，周度调仓，过拟合程度低，鲁棒性好，最大回撤控制优异。",
        "factors": ["动量因子_60日", "波动率因子_标准差", "质量因子_ROE", "估值因子_PE倒数"],
        "rebalance_freq": "weekly",
        "stock_pool": "全市场",
        "max_stocks": 30,
        "source": "未来智库-2025年量化因子掘金系列专题报告",
        "tags": ["多因子融合", "周度调仓", "风险控制"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.033,
            "max_industry_weight": 0.25,
            "stop_loss": -0.15,
            "position_limit": 0.95
        }
    },
    {
        "name": "沪深300增强组合_量价因子",
        "description": "基于中高频量价因子的沪深300增强组合，周频调仓，个股权重偏离上限2%，Barra因子暴露<0.5倍标准差，周双边换手率≤30%。",
        "factors": ["动量因子_20日", "波动率因子_ATR", "流动性因子_换手率", "量价背离因子"],
        "rebalance_freq": "weekly",
        "stock_pool": "沪深300",
        "max_stocks": 50,
        "source": "新浪财经-公募新规下，如何稳定跑赢基准？",
        "tags": ["指数增强", "量价因子", "周度调仓"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.05,
            "max_industry_weight": 0.20,
            "stop_loss": -0.10,
            "position_limit": 0.95
        }
    },
    {
        "name": "聚宽稳健风控策略",
        "description": "基于深证中小板指成分股，通过多维度风险过滤、周期性调仓及复合止损机制构建的中短线量化交易框架。每周二调仓，支持涨停股管理。",
        "factors": ["规模因子_流通市值", "波动率因子_标准差"],
        "rebalance_freq": "weekly",
        "stock_pool": "中小板指",
        "max_stocks": 7,
        "source": "聚宽-量化交易策略代码解析：稳健风控与动态调仓的实战框架",
        "tags": ["稳健风控", "周度调仓", "中小板"],
        "benchmark": "399101.XSHE",
        "risk_params": {
            "max_single_weight": 0.143,
            "max_industry_weight": 0.30,
            "stop_loss": -0.12,
            "position_limit": 0.95
        }
    },
    {
        "name": "聚宽多因子选股策略",
        "description": "基于估值、成长、质量三类因子的多因子选股策略，月度调仓。选取沪深300成分股，等权重买入前20只股票。",
        "factors": ["估值因子_PE倒数", "成长因子_净利润增长率", "质量因子_ROE"],
        "rebalance_freq": "monthly",
        "stock_pool": "沪深300",
        "max_stocks": 20,
        "source": "聚宽-多因子选股模型构建教程",
        "tags": ["多因子选股", "月度调仓", "沪深300"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.05,
            "max_industry_weight": 0.30,
            "stop_loss": -0.10,
            "position_limit": 0.95
        }
    },
    {
        "name": "聚宽最大夏普比率策略",
        "description": "基于沪深300成分股，使用MaxSharpeRatio模型优化组合权重，月度调仓。单只股票权重上限10%，组合总权重100%。",
        "factors": ["动量因子_60日", "波动率因子_标准差"],
        "rebalance_freq": "monthly",
        "stock_pool": "沪深300",
        "max_stocks": 30,
        "source": "聚宽-投资组合优化：构建最大夏普比率策略",
        "tags": ["组合优化", "夏普比率", "月度调仓"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.10,
            "max_industry_weight": 0.30,
            "stop_loss": -0.12,
            "position_limit": 1.0
        }
    },
    {
        "name": "聚宽ETF轮动策略",
        "description": "基于动量因子的ETF轮动策略，每月第一个交易日调仓。选择过去20个交易日收益率最高的前3只ETF持有。",
        "factors": ["动量因子_20日"],
        "rebalance_freq": "monthly",
        "stock_pool": "主流ETF",
        "max_stocks": 3,
        "source": "东方财富-一个能在聚宽平台直接运行的ETF轮动策略",
        "tags": ["ETF轮动", "动量", "月度调仓"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.333,
            "max_industry_weight": 0.50,
            "stop_loss": -0.15,
            "position_limit": 0.95
        }
    },
    {
        "name": "A股量化投资策略框架",
        "description": "基于中国市场特性的多因子动态轮动+事件驱动策略，周度调仓。包含价值、动量、波动率、政策敏感四类因子。",
        "factors": ["估值因子_PE倒数", "动量因子_60日", "波动率因子_ATR", "北向资金因子", "拥挤度因子"],
        "rebalance_freq": "weekly",
        "stock_pool": "沪深300+中证500",
        "max_stocks": 30,
        "source": "雪球-一套基于中国市场特性的A股量化投资策略框架",
        "tags": ["多因子轮动", "事件驱动", "周度调仓"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.05,
            "max_industry_weight": 0.20,
            "stop_loss": -0.15,
            "position_limit": 0.95
        }
    },
    {
        "name": "四象限月度行业轮动策略",
        "description": "采用景气度、情绪面、技术面和宏观四个维度信息构建因子的行业轮动策略，月度调仓。年化超额收益13.85%。",
        "factors": ["动量因子_20日", "技术因子_MACD", "北向资金因子", "波动率因子_标准差"],
        "rebalance_freq": "monthly",
        "stock_pool": "行业指数",
        "max_stocks": 5,
        "source": "国泰海通证券-ETF配置系列(六)——四象限月度行业轮动策略",
        "tags": ["行业轮动", "四象限", "月度调仓"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.20,
            "max_industry_weight": 0.50,
            "stop_loss": -0.15,
            "position_limit": 0.95
        }
    },
    {
        "name": "热点龙头股轮动策略",
        "description": "基于alpha158因子衍生的热点轮动、行业轮动、热点指数映射龙头股策略。年化收益20.25%。",
        "factors": ["动量因子_20日", "动量因子_60日", "波动率因子_ATR", "流动性因子_换手率", "规模因子_市值"],
        "rebalance_freq": "weekly",
        "stock_pool": "全市场",
        "max_stocks": 20,
        "source": "华福证券-从行业轮动到热点轮动再到热点龙头股轮动的演绎",
        "tags": ["热点轮动", "龙头股", "周度调仓"],
        "benchmark": "000300.SH",
        "risk_params": {
            "max_single_weight": 0.05,
            "max_industry_weight": 0.30,
            "stop_loss": -0.12,
            "position_limit": 0.95
        }
    },
]

def main():
    print("=" * 80)
    print("开始批量录入策略和因子")
    print("=" * 80)
    
    print("\n[步骤1] 录入因子到因子库")
    print("-" * 80)
    
    factor_results = []
    factor_id_map = {}
    
    for i, factor_data in enumerate(factors_to_add, 1):
        print(f"\n[{i}/{len(factors_to_add)}] 录入因子: {factor_data['name']}")
        
        result = factor_entry.quick_add(
            name=factor_data["name"],
            formula=factor_data["formula"],
            description=factor_data["description"],
            source=factor_data["source"],
            category=factor_data.get("category"),
            direction=factor_data.get("direction", "正向"),
            tags=factor_data.get("tags", []),
            auto_validate=False
        )
        
        factor_results.append(result)
        
        if result.success:
            factor_id_map[factor_data["name"]] = result.item_id
            print(f"  ✅ 成功: {result.item_id} - {result.message}")
        else:
            print(f"  ❌ 失败: {result.message}")
            if result.warnings:
                for warning in result.warnings:
                    print(f"     ⚠️  {warning}")
    
    print("\n" + "=" * 80)
    print(f"因子录入完成: 成功 {sum(1 for r in factor_results if r.success)} / {len(factor_results)}")
    print("=" * 80)
    
    print("\n[步骤2] 录入策略到策略库")
    print("-" * 80)
    
    strategy_results = []
    
    for i, strategy_data in enumerate(strategies_to_add, 1):
        print(f"\n[{i}/{len(strategies_to_add)}] 录入策略: {strategy_data['name']}")
        
        factor_ids = []
        for factor_name in strategy_data["factors"]:
            if factor_name in factor_id_map:
                factor_ids.append(factor_id_map[factor_name])
            else:
                print(f"  ⚠️  警告: 因子 '{factor_name}' 未找到，跳过")
        
        if not factor_ids:
            print(f"  ❌ 失败: 没有有效的因子")
            strategy_results.append(QuickEntryResult(
                success=False,
                item_id="",
                item_name=strategy_data["name"],
                item_type="strategy",
                message="没有有效的因子"
            ))
            continue
        
        weights = [1.0 / len(factor_ids)] * len(factor_ids)
        
        factor_config = FactorCombinationConfig(
            factor_ids=factor_ids,
            weights=weights,
            combination_method="equal",
            rebalance_frequency=strategy_data["rebalance_freq"]
        )
        
        rebalance_freq_map = {
            "daily": RebalanceFrequency.DAILY,
            "weekly": RebalanceFrequency.WEEKLY,
            "biweekly": RebalanceFrequency.BIWEEKLY,
            "monthly": RebalanceFrequency.MONTHLY,
            "quarterly": RebalanceFrequency.QUARTERLY,
        }
        
        risk_params_data = strategy_data.get("risk_params", {})
        risk_params = RiskParams(
            max_single_weight=risk_params_data.get("max_single_weight", 0.1),
            max_industry_weight=risk_params_data.get("max_industry_weight", 0.3),
            stop_loss=risk_params_data.get("stop_loss", -0.1),
            take_profit=risk_params_data.get("take_profit", 0.2),
            max_drawdown=risk_params_data.get("max_drawdown", -0.15),
            position_limit=risk_params_data.get("position_limit", 0.95)
        )
        
        try:
            from core.strategy.registry import get_strategy_registry
            registry = get_strategy_registry()
            
            strategy = registry.register(
                name=strategy_data["name"],
                description=strategy_data["description"],
                strategy_type=StrategyType.MULTI_FACTOR,
                factor_config=factor_config,
                rebalance_freq=rebalance_freq_map.get(strategy_data["rebalance_freq"], RebalanceFrequency.MONTHLY),
                max_positions=strategy_data["max_stocks"],
                risk_params=risk_params,
                source=strategy_data["source"],
                tags=strategy_data.get("tags", []),
                benchmark=strategy_data.get("benchmark", "000300.SH")
            )
            
            print(f"  ✅ 成功: {strategy.id} - {strategy.name}")
            strategy_results.append(QuickEntryResult(
                success=True,
                item_id=strategy.id,
                item_name=strategy.name,
                item_type="strategy",
                message=f"策略入库成功: {strategy.id}"
            ))
            
        except Exception as e:
            print(f"  ❌ 失败: {str(e)}")
            strategy_results.append(QuickEntryResult(
                success=False,
                item_id="",
                item_name=strategy_data["name"],
                item_type="strategy",
                message=f"入库失败: {str(e)}"
            ))
    
    print("\n" + "=" * 80)
    print(f"策略录入完成: 成功 {sum(1 for r in strategy_results if r.success)} / {len(strategy_results)}")
    print("=" * 80)
    
    print("\n[步骤3] 生成录入报告")
    print("-" * 80)
    
    print("\n因子录入统计:")
    print(f"  总数: {len(factor_results)}")
    print(f"  成功: {sum(1 for r in factor_results if r.success)}")
    print(f"  失败: {sum(1 for r in factor_results if not r.success)}")
    
    print("\n策略录入统计:")
    print(f"  总数: {len(strategy_results)}")
    print(f"  成功: {sum(1 for r in strategy_results if r.success)}")
    print(f"  失败: {sum(1 for r in strategy_results if not r.success)}")
    
    print("\n按调仓频率分类:")
    freq_count = {}
    for strategy_data in strategies_to_add:
        freq = strategy_data["rebalance_freq"]
        freq_count[freq] = freq_count.get(freq, 0) + 1
    
    for freq, count in sorted(freq_count.items()):
        print(f"  {freq}: {count}个策略")
    
    print("\n" + "=" * 80)
    print("批量录入完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()
